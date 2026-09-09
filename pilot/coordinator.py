"""Finite single-run composition over the pilot's narrow injected ports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol

from .authority import LiteralGrantAuthority
from .contracts import DesignPartnerOutcomeV1, contract_digest
from .github import GitHubPublication, GitHubTransport, PushReceiptV1
from .profile import PilotProfileV1
from .store import PilotJob, PilotStore, PilotStoreError
from .workspace import PreparedWorkspace


class CoordinatorError(RuntimeError):
    pass


class IssueSnapshots(Protocol):
    def snapshot(self, *, job_id: str, issue_number: int, acceptance_ids: tuple[str, ...]): ...


class Workspaces(Protocol):
    def prepare(self, job_id: str) -> PreparedWorkspace: ...

    def recover(self, job_id: str, candidate=None) -> PreparedWorkspace: ...

    def cleanup(self, workspace: PreparedWorkspace) -> None: ...


class CandidateExecutor(Protocol):
    def run(self, issue, workspace: PreparedWorkspace, *, command_key: str): ...


class CandidateValidator(Protocol):
    def validate(self, candidate, workspace: PreparedWorkspace, *, command_key: str): ...


@dataclass(frozen=True)
class PreparedPilot:
    job: PilotJob
    workspace: PreparedWorkspace | None


class PilotCoordinator:
    """Advance exactly one serial run; callers explicitly authorize each effect."""

    _FINAL = {"merge_gate_unavailable", "merged_accepted", "closed_rejected", "needs_human", "rejected"}

    def __init__(
        self,
        profile: PilotProfileV1,
        store: PilotStore,
        issue_source: IssueSnapshots,
        workspaces: Workspaces,
        executor: CandidateExecutor,
        validator: CandidateValidator,
        publication: GitHubPublication,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._profile = profile
        self._store = store
        self._issue_source = issue_source
        self._workspaces = workspaces
        self._executor = executor
        self._validator = validator
        self._publication = publication
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def prepare_candidate(
        self,
        *,
        job_id: str,
        issue_number: int,
        acceptance_ids: tuple[str, ...],
    ) -> PreparedPilot:
        workspace: PreparedWorkspace | None = None
        try:
            job = self._store.get(job_id)
        except PilotStoreError as exc:
            if str(exc) != "not_found":
                raise CoordinatorError("store_unavailable") from exc
            snapshot = self._issue_source.snapshot(
                job_id=job_id,
                issue_number=issue_number,
                acceptance_ids=acceptance_ids,
            )
            job, _created = self._store.create_or_replay(
                snapshot, command_key=_command_key(job_id, "submit")
            )
        if (
            job.snapshot.issue_number != issue_number
            or job.snapshot.acceptance_ids != acceptance_ids
            or job.snapshot.profile_digest != self._profile.profile_digest
        ):
            raise CoordinatorError("run_binding")
        if job.state in self._FINAL:
            return PreparedPilot(job, None)
        try:
            if job.state in {"workspace_ready", "candidate_sealed", "gate_passed"}:
                workspace = self._workspaces.recover(job_id, job.candidate)
            if job.state == "issue_snapshotted":
                workspace = self._workspaces.prepare(job_id)
                job = self._store.mark_workspace_ready(
                    job_id, workspace_digest=workspace.workspace_digest
                )
            if job.state == "workspace_ready":
                if workspace is None:
                    raise CoordinatorError("workspace_recovery_required")
                self._executor.run(
                    job.snapshot,
                    workspace,
                    command_key=_command_key(job_id, "codex"),
                )
                job = self._store.get(job_id)
            if job.state == "candidate_sealed":
                if workspace is None or job.candidate is None:
                    raise CoordinatorError("workspace_recovery_required")
                self._validator.validate(
                    job.candidate,
                    workspace,
                    command_key=_command_key(job_id, "validation"),
                )
                job = self._store.get(job_id)
            if job.state != "gate_passed":
                raise CoordinatorError("local_gate_non_pass")
            return PreparedPilot(job, workspace)
        except BaseException:
            if workspace is not None and self._store.get(job_id).state in self._FINAL:
                self._workspaces.cleanup(workspace)
            raise

    def publish_branch(
        self,
        prepared: PreparedPilot,
        authority: LiteralGrantAuthority,
        transport: GitHubTransport,
    ) -> PushReceiptV1:
        if prepared.workspace is None:
            raise CoordinatorError("workspace_recovery_required")
        request = self._publication.branch_request(prepared.job.job_id)
        return self._publication.publish_branch(
            request,
            prepared.workspace,
            authority,
            transport,
            command_key=_command_key(prepared.job.job_id, "branch-push"),
        )

    def publish_proposal(
        self,
        prepared: PreparedPilot,
        push: PushReceiptV1,
        authority: LiteralGrantAuthority,
        transport: GitHubTransport,
    ) -> tuple[object, DesignPartnerOutcomeV1]:
        request = self._publication.proposal_request(prepared.job.job_id, push)
        proposal = self._publication.publish_proposal(
            request,
            push,
            authority,
            transport,
            command_key=_command_key(prepared.job.job_id, "proposal-create"),
        )
        if self._profile.trust_ci_profile is not None:
            raise CoordinatorError("trust_ci_observer_required")
        now = self._clock()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise CoordinatorError("clock")
        outcome = DesignPartnerOutcomeV1.from_facts(
            {
                "schema_version": 1,
                "job_id": proposal.job_id,
                "profile_digest": proposal.profile_digest,
                "proposal_digest": proposal.proposal_digest,
                "pr_number": proposal.pr_number,
                "head_sha": proposal.head_sha,
                "trust_ci_status": "unavailable",
                "required_check": None,
                "human_decision": "pending",
                "human_actor": None,
                "decision_at": None,
                "merge_commit_sha": None,
                "merge_tree": None,
                "status": "merge_gate_unavailable",
                "observed_at": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        )
        self._store.store_outcome(proposal.job_id, outcome)
        if prepared.workspace is not None:
            self._workspaces.cleanup(prepared.workspace)
        return proposal, outcome


def _command_key(job_id: str, stage: str) -> str:
    return contract_digest("coordinator-command", {"job_id": job_id, "stage": stage})
