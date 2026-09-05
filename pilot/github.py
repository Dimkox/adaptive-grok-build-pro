"""One non-force branch publication and one draft proposal publication."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
from typing import Callable, Mapping, Protocol

from .authority import GrantUseV1, LiteralGrantAuthority, operation_resource
from .contracts import PullRequestProposalV1, canonical_json, contract_digest
from .profile import PilotProfileV1
from .store import EffectRecord, PilotJob, PilotStore
from .workspace import PreparedWorkspace


class PublicationError(RuntimeError):
    pass


@dataclass(frozen=True)
class BranchPushRequestV1:
    schema_version: int
    job_id: str
    profile_digest: str
    issue_snapshot_digest: str
    validation_digest: str
    repository_id: str
    github_name: str
    git_url: str
    base_ref: str
    base_sha: str
    base_tree: str
    candidate_digest: str
    candidate_sha: str
    candidate_tree: str
    diff_sha256: str
    branch_ref: str
    force: bool
    delete: bool
    tags: bool
    request_digest: str

    @classmethod
    def from_chain(cls, profile: PilotProfileV1, job: PilotJob) -> "BranchPushRequestV1":
        candidate, validation = _validated_chain(
            profile, job, {"gate_passed", "branch_intent", "branch_observed"}
        )
        short = f"{profile.branch_prefix}{job.snapshot.issue_number}-{candidate.candidate_sha[:12]}"
        if not re.fullmatch(r"adaptive-pilot/issue-[1-9][0-9]*-[0-9a-f]{12}", short):
            raise PublicationError("branch_ref")
        facts = {
            "schema_version": 1,
            "job_id": job.job_id,
            "profile_digest": profile.profile_digest,
            "issue_snapshot_digest": job.snapshot.issue_snapshot_digest,
            "validation_digest": validation.validation_digest,
            "repository_id": profile.repository_id,
            "github_name": profile.github_name,
            "git_url": profile.git_url,
            "base_ref": profile.base_ref,
            "base_sha": profile.base_sha,
            "base_tree": profile.base_tree,
            "candidate_digest": candidate.candidate_digest,
            "candidate_sha": candidate.candidate_sha,
            "candidate_tree": candidate.candidate_tree,
            "diff_sha256": candidate.diff_sha256,
            "branch_ref": "refs/heads/" + short,
            "force": False,
            "delete": False,
            "tags": False,
        }
        return cls(**facts, request_digest=contract_digest("branch-push-request", facts))

    @property
    def resource(self) -> str:
        return operation_resource("branch_push", self.request_digest)

    @property
    def head_ref(self) -> str:
        return self.branch_ref.removeprefix("refs/heads/")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PushReceiptV1:
    schema_version: int
    job_id: str
    request_digest: str
    resource: str
    grant_id: str
    grant_digest: str
    candidate_digest: str
    candidate_sha: str
    branch_ref: str
    observed_sha: str
    outcome: str
    completed_at: str
    receipt_digest: str

    @classmethod
    def from_facts(cls, facts: Mapping[str, object]) -> "PushReceiptV1":
        value = dict(facts)
        if value.get("schema_version") != 1 or value.get("outcome") not in {"already_exact", "created_exact", "reconciled_exact"}:
            raise PublicationError("push_receipt")
        if value.get("resource") != operation_resource("branch_push", str(value.get("request_digest", ""))):
            raise PublicationError("push_receipt")
        if value.get("candidate_sha") != value.get("observed_sha"):
            raise PublicationError("push_receipt")
        digest = contract_digest("branch-push-receipt", value)
        return cls(**value, receipt_digest=digest)

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> "PushReceiptV1":
        value = dict(raw)
        supplied = value.pop("receipt_digest", None)
        record = cls.from_facts(value)
        if supplied != record.receipt_digest:
            raise PublicationError("push_receipt")
        return record

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ProposalCreateRequestV1:
    schema_version: int
    job_id: str
    profile_digest: str
    issue_snapshot_digest: str
    validation_digest: str
    push_receipt_digest: str
    repository_id: str
    github_name: str
    base_ref: str
    base_sha: str
    head_ref: str
    head_sha: str
    head_tree: str
    candidate_digest: str
    title: str
    body: str
    marker: str
    draft: bool
    maintainer_can_modify: bool
    request_digest: str

    @classmethod
    def from_chain(cls, profile: PilotProfileV1, job: PilotJob, push: PushReceiptV1) -> "ProposalCreateRequestV1":
        candidate, validation = _validated_chain(
            profile,
            job,
            {"branch_observed", "pr_intent", "pr_observed", "awaiting_human"},
        )
        expected_branch = f"{profile.branch_prefix}{job.snapshot.issue_number}-{candidate.candidate_sha[:12]}"
        if (
            push.job_id != job.job_id
            or push.candidate_digest != candidate.candidate_digest
            or push.candidate_sha != candidate.candidate_sha
            or push.branch_ref != "refs/heads/" + expected_branch
        ):
            raise PublicationError("push_binding")
        marker = f"<!-- adaptive-pilot-candidate:{candidate.candidate_digest} -->"
        title = f"Adaptive pilot proposal for issue #{job.snapshot.issue_number}"
        body = (
            f"Refs #{job.snapshot.issue_number}\n\n"
            "Generated by the bounded single-operator design-partner pilot. "
            "Local validation is preflight evidence only.\n\n"
            f"{marker}"
        )
        facts = {
            "schema_version": 1,
            "job_id": job.job_id,
            "profile_digest": profile.profile_digest,
            "issue_snapshot_digest": job.snapshot.issue_snapshot_digest,
            "validation_digest": validation.validation_digest,
            "push_receipt_digest": push.receipt_digest,
            "repository_id": profile.repository_id,
            "github_name": profile.github_name,
            "base_ref": profile.base_ref.removeprefix("refs/heads/"),
            "base_sha": profile.base_sha,
            "head_ref": expected_branch,
            "head_sha": candidate.candidate_sha,
            "head_tree": candidate.candidate_tree,
            "candidate_digest": candidate.candidate_digest,
            "title": title,
            "body": body,
            "marker": marker,
            "draft": True,
            "maintainer_can_modify": False,
        }
        return cls(**facts, request_digest=contract_digest("proposal-create-request", facts))

    @property
    def resource(self) -> str:
        return operation_resource("proposal_create", self.request_digest)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PublicationObservation:
    base_sha: str
    issue_node_id: str
    issue_updated_at: str
    branch_sha: str | None
    observed_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ProposalObservation:
    number: int
    node_id: str
    url: str
    head_ref: str
    head_sha: str
    base_ref: str
    draft: bool
    marker: str
    state: str
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class GitHubTransport(Protocol):
    def observe(self, request: BranchPushRequestV1 | ProposalCreateRequestV1) -> PublicationObservation: ...

    def push_exact(self, request: BranchPushRequestV1, writer: PreparedWorkspace) -> None: ...

    def find_proposals(self, request: ProposalCreateRequestV1) -> tuple[ProposalObservation, ...]: ...

    def create_draft(self, request: ProposalCreateRequestV1) -> None: ...


class GitHubPublication:
    def __init__(self, profile: PilotProfileV1, store: PilotStore, *, clock: Callable[[], datetime] | None = None) -> None:
        self._profile = profile
        self._store = store
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def branch_request(self, job_id: str) -> BranchPushRequestV1:
        return BranchPushRequestV1.from_chain(self._profile, self._store.get(job_id))

    def proposal_request(self, job_id: str, push: PushReceiptV1) -> ProposalCreateRequestV1:
        return ProposalCreateRequestV1.from_chain(self._profile, self._store.get(job_id), push)

    def publish_branch(
        self,
        request: BranchPushRequestV1,
        writer: PreparedWorkspace,
        authority: LiteralGrantAuthority,
        transport: GitHubTransport,
        *,
        command_key: str,
    ) -> PushReceiptV1:
        job = self._store.get(request.job_id)
        _assert_branch_binding(self._profile, job, request, writer)
        existing = self._store.get_effect(request.job_id, "branch_push")
        if existing is not None and existing.state == "completed":
            return _stored_push_receipt(existing)
        if existing is None:
            use = authority.authorize("branch_push", request.request_digest)
            _record, owns_write = self._store.prepare_effect(
                request.job_id,
                "branch_push",
                command_key=command_key,
                resource=request.resource,
                request=request.to_dict(),
                authority=use.to_dict(),
                candidate_digest=request.candidate_digest,
            )
        else:
            use = _stored_grant(existing)
            owns_write = False
        before = _safe_observe(transport, request)
        failure = _freshness_failure(job, self._profile, before)
        if failure:
            return self._fail_effect(request.job_id, "branch_push", failure, before)
        if before.branch_sha == request.candidate_sha:
            outcome = "already_exact" if owns_write else "reconciled_exact"
            return self._complete_push(request, use, before, outcome)
        if before.branch_sha is not None:
            return self._fail_effect(request.job_id, "branch_push", "conflict", before)
        if not owns_write:
            return self._fail_effect(request.job_id, "branch_push", "no_effect", before)
        self._store.mark_effect_in_flight(request.job_id, "branch_push")
        try:
            transport.push_exact(request, writer)
        except Exception:
            pass
        after = _safe_observe(transport, request)
        failure = _freshness_failure(job, self._profile, after)
        if failure:
            return self._fail_effect(request.job_id, "branch_push", failure, after)
        if after.branch_sha == request.candidate_sha:
            return self._complete_push(request, use, after, "created_exact")
        if after.branch_sha is None:
            return self._fail_effect(request.job_id, "branch_push", "no_effect", after)
        return self._fail_effect(request.job_id, "branch_push", "conflict", after)

    def publish_proposal(
        self,
        request: ProposalCreateRequestV1,
        push: PushReceiptV1,
        authority: LiteralGrantAuthority,
        transport: GitHubTransport,
        *,
        command_key: str,
    ) -> PullRequestProposalV1:
        job = self._store.get(request.job_id)
        _assert_proposal_binding(self._profile, job, request, push)
        existing = self._store.get_effect(request.job_id, "proposal_create")
        if existing is not None and existing.state == "completed" and job.proposal is not None:
            return job.proposal
        if existing is None:
            use = authority.authorize("proposal_create", request.request_digest)
            _record, owns_write = self._store.prepare_effect(
                request.job_id,
                "proposal_create",
                command_key=command_key,
                resource=request.resource,
                request=request.to_dict(),
                authority=use.to_dict(),
                candidate_digest=request.candidate_digest,
            )
        else:
            use = _stored_grant(existing)
            owns_write = False
        before = _safe_observe(transport, request)
        failure = _freshness_failure(job, self._profile, before)
        if failure or before.branch_sha != request.head_sha:
            return self._fail_effect(request.job_id, "proposal_create", failure or "conflict", before)
        proposals = _safe_find(transport, request)
        match = _exact_proposal(request, proposals)
        if match is not None:
            outcome = "already_exact" if owns_write else "reconciled_exact"
            return self._complete_proposal(request, push, use, match, outcome)
        if proposals:
            return self._fail_effect(request.job_id, "proposal_create", "conflict", before)
        if not owns_write:
            return self._fail_effect(request.job_id, "proposal_create", "no_effect", before)
        self._store.mark_effect_in_flight(request.job_id, "proposal_create")
        try:
            transport.create_draft(request)
        except Exception:
            pass
        proposals = _safe_find(transport, request)
        match = _exact_proposal(request, proposals)
        if match is not None:
            return self._complete_proposal(request, push, use, match, "created_exact")
        if proposals:
            return self._fail_effect(request.job_id, "proposal_create", "conflict", before)
        return self._fail_effect(request.job_id, "proposal_create", "no_effect", before)

    def _complete_push(self, request: BranchPushRequestV1, use: GrantUseV1, observation: PublicationObservation, outcome: str) -> PushReceiptV1:
        receipt = PushReceiptV1.from_facts(
            {
                "schema_version": 1,
                "job_id": request.job_id,
                "request_digest": request.request_digest,
                "resource": request.resource,
                "grant_id": use.grant_id,
                "grant_digest": use.grant_use_digest,
                "candidate_digest": request.candidate_digest,
                "candidate_sha": request.candidate_sha,
                "branch_ref": request.branch_ref,
                "observed_sha": str(observation.branch_sha),
                "outcome": outcome,
                "completed_at": observation.observed_at,
            }
        )
        self._store.complete_effect(
            request.job_id,
            "branch_push",
            outcome=outcome,
            observation={"receipt": receipt.to_dict(), "remote": observation.to_dict()},
            success=True,
        )
        return receipt

    def _complete_proposal(self, request: ProposalCreateRequestV1, push: PushReceiptV1, use: GrantUseV1, observed: ProposalObservation, outcome: str) -> PullRequestProposalV1:
        proposal = PullRequestProposalV1.from_facts(
            {
                "schema_version": 1,
                "job_id": request.job_id,
                "profile_digest": request.profile_digest,
                "validation_digest": request.validation_digest,
                "repository_id": request.repository_id,
                "base_ref": request.base_ref,
                "base_sha": request.base_sha,
                "head_ref": request.head_ref,
                "head_sha": request.head_sha,
                "head_tree": request.head_tree,
                "push_resource": push.resource,
                "push_grant_id": push.grant_id,
                "push_grant_digest": push.grant_digest,
                "push_outcome": push.outcome,
                "proposal_resource": request.resource,
                "proposal_grant_id": use.grant_id,
                "proposal_grant_digest": use.grant_use_digest,
                "pr_number": observed.number,
                "pr_node_id": observed.node_id,
                "pr_url": observed.url,
                "draft": True,
                "maintainer_can_modify": False,
                "status": "proposal_created_merge_gate_unavailable",
                "merge_eligible": False,
                "created_at": observed.created_at,
            }
        )
        self._store.complete_effect(
            request.job_id,
            "proposal_create",
            outcome=outcome,
            observation={"proposal": proposal.to_dict(), "remote": observed.to_dict()},
            success=True,
        )
        self._store.store_proposal(request.job_id, proposal)
        return proposal

    def _fail_effect(self, job_id: str, kind: str, outcome: str, observation: PublicationObservation):
        self._store.complete_effect(job_id, kind, outcome=outcome, observation={"remote": observation.to_dict()}, success=False)
        raise PublicationError(outcome)


class ExactGitPushCommand:
    """Build the sole permitted ref publication command; execution is host-owned."""

    def __init__(self, executable: str = "/usr/bin/git") -> None:
        self._executable = executable

    def invocation(self, request: BranchPushRequestV1, writer: PreparedWorkspace) -> tuple[tuple[str, ...], dict[str, str]]:
        if (
            request.force
            or request.delete
            or request.tags
            or (writer.base_sha, writer.base_tree) != (request.base_sha, request.base_tree)
        ):
            raise PublicationError("push_binding")
        argv = (
            self._executable,
            f"--git-dir={writer.git_dir}",
            "push",
            "--porcelain",
            "--no-force",
            "--",
            request.git_url,
            f"{request.candidate_sha}:{request.branch_ref}",
        )
        environment = {
            "HOME": str(writer.root),
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C",
            "TZ": "UTC",
            "GIT_TERMINAL_PROMPT": "0",
        }
        return argv, environment


class GhDraftProposalCommand:
    """Build one closed pull-request POST request; transport owns opaque auth."""

    def __init__(self, executable: str = "/usr/bin/gh") -> None:
        self._executable = executable

    def invocation(self, request: ProposalCreateRequestV1) -> tuple[tuple[str, ...], dict[str, object]]:
        if not request.draft or request.maintainer_can_modify:
            raise PublicationError("unsafe_proposal")
        argv = (
            self._executable,
            "api",
            "--method",
            "POST",
            f"repos/{request.github_name}/pulls",
            "--input",
            "-",
        )
        payload = {
            "title": request.title,
            "body": request.body,
            "base": request.base_ref,
            "head": request.head_ref,
            "draft": True,
            "maintainer_can_modify": False,
        }
        return argv, payload


def _validated_chain(profile: PilotProfileV1, job: PilotJob, states: set[str]):
    candidate, validation = job.candidate, job.validation
    if (
        job.state not in states
        or job.profile_digest != profile.profile_digest
        or job.snapshot.profile_digest != profile.profile_digest
        or job.snapshot.repository_id != profile.repository_id
        or (job.snapshot.base_ref, job.snapshot.base_sha, job.snapshot.base_tree) != (profile.base_ref, profile.base_sha, profile.base_tree)
        or candidate is None
        or validation is None
        or validation.decision != "pass"
        or candidate.issue_snapshot_digest != job.snapshot.issue_snapshot_digest
        or validation.candidate_digest != candidate.candidate_digest
        or (validation.candidate_sha, validation.candidate_tree) != (candidate.candidate_sha, candidate.candidate_tree)
    ):
        raise PublicationError("chain_binding")
    return candidate, validation


def _assert_branch_binding(profile: PilotProfileV1, job: PilotJob, request: BranchPushRequestV1, writer: PreparedWorkspace) -> None:
    expected = BranchPushRequestV1.from_chain(profile, job)
    if request != expected or (
        writer.workspace_digest != expected.candidate_digest and writer.workspace_digest != job.candidate.workspace_digest
    ) or (writer.base_sha, writer.base_tree) != (profile.base_sha, profile.base_tree):
        raise PublicationError("request_binding")


def _assert_proposal_binding(profile: PilotProfileV1, job: PilotJob, request: ProposalCreateRequestV1, push: PushReceiptV1) -> None:
    expected = ProposalCreateRequestV1.from_chain(profile, job, push)
    if request != expected or push.outcome not in {"already_exact", "created_exact", "reconciled_exact"}:
        raise PublicationError("request_binding")


def _freshness_failure(job: PilotJob, profile: PilotProfileV1, observation: PublicationObservation) -> str | None:
    if observation.base_sha != profile.base_sha:
        return "stale_base"
    if (observation.issue_node_id, observation.issue_updated_at) != (job.snapshot.issue_node_id, job.snapshot.updated_at):
        return "stale_issue"
    return None


def _safe_observe(transport: GitHubTransport, request: BranchPushRequestV1 | ProposalCreateRequestV1) -> PublicationObservation:
    try:
        value = transport.observe(request)
    except Exception as exc:
        raise PublicationError("external_outcome_ambiguous") from exc
    if not isinstance(value, PublicationObservation):
        raise PublicationError("external_outcome_ambiguous")
    return value


def _safe_find(transport: GitHubTransport, request: ProposalCreateRequestV1) -> tuple[ProposalObservation, ...]:
    try:
        value = transport.find_proposals(request)
    except Exception as exc:
        raise PublicationError("external_outcome_ambiguous") from exc
    if not isinstance(value, tuple) or any(not isinstance(item, ProposalObservation) for item in value):
        raise PublicationError("external_outcome_ambiguous")
    return value


def _exact_proposal(request: ProposalCreateRequestV1, observations: tuple[ProposalObservation, ...]) -> ProposalObservation | None:
    if len(observations) != 1:
        return None
    item = observations[0]
    if (
        item.head_ref,
        item.head_sha,
        item.base_ref,
        item.draft,
        item.marker,
        item.state,
    ) != (request.head_ref, request.head_sha, request.base_ref, True, request.marker, "open"):
        return None
    return item


def _stored_grant(effect: EffectRecord) -> GrantUseV1:
    try:
        return GrantUseV1(**dict(effect.authority))
    except (TypeError, ValueError) as exc:
        raise PublicationError("grant_record") from exc


def _stored_push_receipt(effect: EffectRecord) -> PushReceiptV1:
    try:
        return PushReceiptV1.from_dict(effect.outcome["receipt"])
    except (KeyError, TypeError, PublicationError) as exc:
        raise PublicationError("push_receipt") from exc
