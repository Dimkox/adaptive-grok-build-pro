"""Exact host composition and explicit phases for the design-partner pilot."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import os
from pathlib import Path
import re
import stat

from .authority import AuthorityError
from .cli import RuntimeConfig
from .codex_executor import (
    AppServerCodexRunner,
    CodexExecutor,
    CodexSandboxProbe,
    SubprocessCodexRunner,
)
from .contracts import canonical_json
from .coordinator import PilotCoordinator, PreparedPilot
from .github import GitHubPublication, PublicationError
from .issue_source import IssueSource
from .live_github import (
    PinnedGitHubTransport,
    verify_pinned_executable,
)
from .profile import CODEX_OUTPUT_SCHEMA
from .runtime_authority import RuntimeGrantLoader
from .store import PilotStore, PilotStoreError
from .validation import (
    BubblewrapTestRunner,
    CandidateValidator,
    ExactValidationWorkspace,
    LandingSemanticGate,
)
from .workspace import ExactGitWorkspace, WorkspacePolicy


LIVE_ACCEPTANCE_IDS = ("AC-ISSUE-001", "AC-ISSUE-002")


class LivePilotError(RuntimeError):
    pass


class ApiKeyCapability:
    """Expose CODEX_API_KEY only to the owning provider subprocess."""

    def __init__(self, environment: Mapping[str, str]) -> None:
        self._environment = environment

    def preflight(self) -> None:
        value = self._environment.get("CODEX_API_KEY")
        if (
            not isinstance(value, str)
            or not value
            or len(value.encode("utf-8")) > 16_384
            or "\x00" in value
        ):
            raise LivePilotError("provider_credential_unavailable")

    def environment(self) -> Mapping[str, str]:
        self.preflight()
        return {"CODEX_API_KEY": self._environment["CODEX_API_KEY"]}


class PilotPhases:
    def __init__(
        self,
        profile,
        store: PilotStore,
        coordinator: PilotCoordinator,
        workspaces: ExactGitWorkspace,
        publication: GitHubPublication,
        transport: PinnedGitHubTransport,
        authority_loader: RuntimeGrantLoader,
        *,
        job_id: str,
        issue_number: int,
        provider_preflight: Callable[[], None],
    ) -> None:
        self._profile = profile
        self._store = store
        self._coordinator = coordinator
        self._workspaces = workspaces
        self._publication = publication
        self._transport = transport
        self._authority_loader = authority_loader
        self._job_id = job_id
        self._issue_number = issue_number
        self._provider_preflight = provider_preflight

    def prepare(self) -> Mapping[str, object]:
        try:
            current = self._store.get(self._job_id)
        except PilotStoreError as exc:
            if str(exc) != "not_found":
                raise
            current = None
        if current is None or current.state in {"issue_snapshotted", "workspace_ready"}:
            self._provider_preflight()
        prepared = self._coordinator.prepare_candidate(
            job_id=self._job_id,
            issue_number=self._issue_number,
            acceptance_ids=LIVE_ACCEPTANCE_IDS,
        )
        if prepared.job.state != "gate_passed":
            return _job_result("prepare", prepared.job, external_effect=False)
        request = self._publication.branch_request(self._job_id)
        return {
            **_job_result("prepare", prepared.job, external_effect=False),
            "branch_request": _branch_request_result(request),
        }

    def publish_branch(self) -> Mapping[str, object]:
        job = self._store.get(self._job_id)
        if job.state not in {"gate_passed", "branch_intent", "branch_observed"}:
            raise LivePilotError("branch_phase_state")
        if job.candidate is None:
            raise LivePilotError("candidate_unavailable")
        workspace = self._workspaces.recover(self._job_id, job.candidate)
        prepared = PreparedPilot(job, workspace)
        request = self._publication.branch_request(self._job_id)
        effect_before = self._store.get_effect(self._job_id, "branch_push")
        push = self._coordinator.publish_branch(
            prepared,
            self._authority_loader.load(),
            self._transport,
        )
        current = self._store.get(self._job_id)
        proposal = self._publication.proposal_request(self._job_id, push)
        return {
            **_job_result(
                "publish-branch",
                current,
                external_effect=effect_before is None
                and push.outcome == "created_exact",
            ),
            "push_receipt": {
                "request_digest": push.request_digest,
                "resource": push.resource,
                "branch_ref": push.branch_ref,
                "candidate_sha": push.candidate_sha,
                "outcome": push.outcome,
                "receipt_digest": push.receipt_digest,
            },
            "proposal_request": _proposal_request_result(proposal),
        }

    def publish_proposal(self) -> Mapping[str, object]:
        job = self._store.get(self._job_id)
        if job.state == "merge_gate_unavailable" and job.proposal is not None and job.outcome is not None:
            return _proposal_result(job, external_effect=False)
        if job.state not in {"branch_observed", "pr_intent", "pr_observed", "awaiting_human"}:
            raise LivePilotError("proposal_phase_state")
        if job.candidate is None:
            raise LivePilotError("candidate_unavailable")
        workspace = self._workspaces.recover(self._job_id, job.candidate)
        prepared = PreparedPilot(job, workspace)
        push = self._publication.push_receipt(self._job_id)
        request = self._publication.proposal_request(self._job_id, push)
        effect_before = self._store.get_effect(self._job_id, "proposal_create")
        proposal, _outcome = self._coordinator.publish_proposal(
            prepared,
            push,
            self._authority_loader.load(),
            self._transport,
        )
        current = self._store.get(self._job_id)
        effect_after = self._store.get_effect(self._job_id, "proposal_create")
        return _proposal_result(
            current,
            external_effect=effect_before is None
            and effect_after is not None
            and effect_after.outcome is not None
            and proposal.proposal_grant_id == effect_after.grant_id
            and effect_after.outcome.get("outcome") == "created_exact",
        )


def run_live_phase(phase: str, config: RuntimeConfig) -> Mapping[str, object]:
    control = Path(__file__).resolve().parents[1]
    if phase == "status":
        return _read_status(config, control)
    runtime: PilotPhases | None = None
    store: PilotStore | None = None
    try:
        runtime, store = _build(config, control, os.environ)
        if phase == "prepare":
            return runtime.prepare()
        if phase == "publish-branch":
            return runtime.publish_branch()
        if phase == "publish-proposal":
            return runtime.publish_proposal()
        raise LivePilotError("unknown_phase")
    except (AuthorityError, PilotStoreError, PublicationError, LivePilotError) as exc:
        raise LivePilotError(_error_code(exc)) from exc
    except Exception as exc:
        raise LivePilotError("live_phase_failed") from exc
    finally:
        if store is not None:
            store.close()


def _build(
    config: RuntimeConfig,
    control: Path,
    environment: Mapping[str, str],
) -> tuple[PilotPhases, PilotStore]:
    _validate_roots(config, control)
    for path, digest in (
        (config.profile.codex_executable, config.profile.codex_sha256),
        (config.profile.python_executable, config.profile.python_sha256),
        (config.git_executable, config.git_sha256),
        (config.gh_executable, config.gh_sha256),
        (config.bwrap_executable, config.bwrap_sha256),
    ):
        verify_pinned_executable(path, digest)
    store = PilotStore(config.state_root, control_repository=control)
    try:
        output_schema = _materialize_output_schema(config.state_root)
        transport = PinnedGitHubTransport(
            gh_executable=config.gh_executable,
            gh_sha256=config.gh_sha256,
            git_executable=config.git_executable,
            git_sha256=config.git_sha256,
            auth_environment=lambda: _host_paths(
                environment, ("HOME", "GH_CONFIG_DIR", "XDG_CONFIG_HOME")
            ),
        )
        issue_source = IssueSource(
            config.profile,
            transport,
            source_adapter_digest=transport.source_adapter_digest,
            auth_principal_digest=transport.auth_principal_digest,
        )
        workspaces = ExactGitWorkspace(
            config.source_repository,
            config.workspace_root,
            control_repository=control,
            policy=WorkspacePolicy(
                config.profile.profile_digest,
                config.profile.base_sha,
                config.profile.base_tree,
                config.profile.allowed_write_paths,
                config.profile.max_diff_bytes,
            ),
            git_executable=config.git_executable,
        )
        if config.profile.provider_mode == "app_server_chatgpt":
            provider_runner = AppServerCodexRunner(
                config.profile,
                auth_environment=lambda: _host_paths(
                    environment, ("HOME", "CODEX_HOME")
                ),
            )
            provider_preflight = lambda: None
        else:
            capability = ApiKeyCapability(environment)
            provider_runner = SubprocessCodexRunner(capability.environment)
            provider_preflight = capability.preflight
        executor = CodexExecutor(
            config.profile,
            store,
            workspaces,
            probe=CodexSandboxProbe(config.profile),
            runner=provider_runner,
            output_schema_path=output_schema,
        )
        validation_workspaces = ExactValidationWorkspace(
            config.validation_root,
            control_repository=control,
            git_executable=config.git_executable,
        )
        validator = CandidateValidator(
            config.profile,
            store,
            validation_workspaces,
            runner=BubblewrapTestRunner(
                config.profile, executable=config.bwrap_executable
            ),
            gate=LandingSemanticGate(config.profile),
        )
        publication = GitHubPublication(config.profile, store)
        coordinator = PilotCoordinator(
            config.profile,
            store,
            issue_source,
            workspaces,
            executor,
            validator,
            publication,
        )
        phases = PilotPhases(
            config.profile,
            store,
            coordinator,
            workspaces,
            publication,
            transport,
            RuntimeGrantLoader(control, git_executable=config.git_executable),
            job_id=config.job_id,
            issue_number=config.issue_number,
            provider_preflight=provider_preflight,
        )
        return phases, store
    except BaseException:
        store.close()
        raise


def _read_status(config: RuntimeConfig, control: Path) -> Mapping[str, object]:
    _validate_roots(config, control)
    try:
        store = PilotStore(
            config.state_root,
            control_repository=control,
            read_only=True,
        )
    except PilotStoreError as exc:
        raise LivePilotError(_error_code(exc)) from exc
    try:
        job = store.get(config.job_id)
        result = _job_result("status", job, external_effect=False)
        if job.proposal is not None:
            result = {**result, "proposal": _proposal_identity(job.proposal)}
        return result
    finally:
        store.close()


def _branch_request_result(request) -> dict[str, object]:
    return {
        "action": "git-push-branch",
        "request_digest": request.request_digest,
        "resource": request.resource,
        "branch_ref": request.branch_ref,
        "candidate_sha": request.candidate_sha,
    }


def _proposal_request_result(request) -> dict[str, object]:
    return {
        "action": "external-write",
        "request_digest": request.request_digest,
        "resource": request.resource,
        "head_ref": request.head_ref,
        "head_sha": request.head_sha,
        "draft": True,
    }


def _job_result(phase: str, job, *, external_effect: bool) -> dict[str, object]:
    return {
        "schema_version": 1,
        "phase": phase,
        "job_id": job.job_id,
        "state": job.state,
        "reason": job.reason_code,
        "external_effect": external_effect,
    }


def _proposal_identity(proposal) -> dict[str, object]:
    return {
        "pr_number": proposal.pr_number,
        "pr_node_id": proposal.pr_node_id,
        "pr_url": proposal.pr_url,
        "head_sha": proposal.head_sha,
        "draft": proposal.draft,
        "merge_eligible": proposal.merge_eligible,
        "proposal_digest": proposal.proposal_digest,
    }


def _proposal_result(job, *, external_effect: bool) -> dict[str, object]:
    if job.proposal is None or job.outcome is None:
        raise LivePilotError("proposal_outcome_unavailable")
    return {
        **_job_result("publish-proposal", job, external_effect=external_effect),
        "proposal": _proposal_identity(job.proposal),
        "trust_ci_status": job.outcome.trust_ci_status,
        "human_decision": job.outcome.human_decision,
    }


def _validate_roots(config: RuntimeConfig, control: Path) -> None:
    try:
        source_path = Path(os.path.abspath(config.source_repository))
        source_metadata = source_path.lstat()
        source = source_path.resolve(strict=True)
        control_path = Path(os.path.abspath(control))
        control_metadata = control_path.lstat()
        control = control_path.resolve(strict=True)
    except OSError as exc:
        raise LivePilotError("runtime_path_unavailable") from exc
    if (
        not stat.S_ISDIR(source_metadata.st_mode)
        or stat.S_ISLNK(source_metadata.st_mode)
        or source != source_path
        or not stat.S_ISDIR(control_metadata.st_mode)
        or stat.S_ISLNK(control_metadata.st_mode)
        or control != control_path
    ):
        raise LivePilotError("runtime_path_boundary")
    roots = tuple(
        _prospective_private_root(root)
        for root in (config.state_root, config.workspace_root, config.validation_root)
    )
    for absolute in roots:
        if any(
            absolute == boundary
            or boundary in absolute.parents
            or absolute in boundary.parents
            for boundary in (source, control)
        ):
            raise LivePilotError("runtime_path_boundary")
    for index, first in enumerate(roots):
        for second in roots[index + 1 :]:
            if first == second or first in second.parents or second in first.parents:
                raise LivePilotError("runtime_path_boundary")


def _prospective_private_root(root: Path) -> Path:
    absolute = Path(os.path.abspath(root))
    try:
        metadata = absolute.lstat()
    except FileNotFoundError:
        try:
            resolved = absolute.parent.resolve(strict=True) / absolute.name
        except OSError as exc:
            raise LivePilotError("runtime_path_unavailable") from exc
    except OSError as exc:
        raise LivePilotError("runtime_path_unavailable") from exc
    else:
        if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise LivePilotError("runtime_path_boundary")
        try:
            resolved = absolute.resolve(strict=True)
        except OSError as exc:
            raise LivePilotError("runtime_path_unavailable") from exc
    if resolved != absolute:
        raise LivePilotError("runtime_path_boundary")
    return resolved


def _materialize_output_schema(state_root: Path) -> Path:
    target = state_root / "codex-output-schema.json"
    expected = canonical_json(CODEX_OUTPUT_SCHEMA)
    try:
        descriptor = os.open(
            target,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
    except FileExistsError:
        descriptor = None
    except OSError as exc:
        raise LivePilotError("output_schema_unavailable") from exc
    if descriptor is not None:
        try:
            os.write(descriptor, expected)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    try:
        metadata = target.lstat()
        actual = target.read_bytes()
    except OSError as exc:
        raise LivePilotError("output_schema_unavailable") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or metadata.st_mode & 0o077
        or actual != expected
    ):
        raise LivePilotError("output_schema_mismatch")
    return target


def _host_paths(environment: Mapping[str, str], keys: tuple[str, ...]) -> dict[str, str]:
    result = {key: environment[key] for key in keys if environment.get(key)}
    if "HOME" not in result or any(
        not Path(value).is_absolute() or "\x00" in value for value in result.values()
    ):
        raise LivePilotError("host_auth_unavailable")
    return result


def _error_code(exc: Exception) -> str:
    value = str(exc).split(":", 1)[0]
    return value if re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value) else "live_phase_failed"
