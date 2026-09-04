from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from time import monotonic as system_monotonic
from typing import Callable, Literal, Protocol
from uuid import UUID

from .models import Actor
from .workspace import WorkspaceHandle, WorkspaceReleaseOutcome


_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_WORKSPACE = re.compile(r"^workspace:[0-9a-f]{64}$")
_RECOVERY_BUDGET_SECONDS = 30.0
_RECOVERY_DB_TIMEOUT_SECONDS = 3.0
_RECOVERY_CYCLE_RESERVE_SECONDS = 12.0
_RECOVERY_OUTCOME_RESERVE_SECONDS = 3.5


def _run_id(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid_run_id")
    try:
        if str(UUID(value)) != value:
            raise ValueError
    except ValueError as exc:
        raise ValueError("invalid_run_id") from exc
    return value


def _timestamp(value: datetime) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError("invalid_updated_at")
    return value


@dataclass(frozen=True, order=True)
class ExecutionRecoveryCursor:
    updated_at: datetime
    run_id: str

    def __post_init__(self) -> None:
        _timestamp(self.updated_at)
        _run_id(self.run_id)


@dataclass(frozen=True)
class ExecutionRecoveryCandidate:
    task_id: str
    run_id: str
    manifest_digest: str
    workspace_handle: str
    updated_at: datetime
    source: Literal["fresh", "cleanup_retry"] = "fresh"

    def __post_init__(self) -> None:
        _run_id(self.task_id)
        _run_id(self.run_id)
        if (
            not isinstance(self.manifest_digest, str)
            or not _HEX64.fullmatch(self.manifest_digest)
        ):
            raise ValueError("invalid_manifest_digest")
        if (
            not isinstance(self.workspace_handle, str)
            or not _WORKSPACE.fullmatch(self.workspace_handle)
        ):
            raise ValueError("invalid_workspace_handle")
        _timestamp(self.updated_at)
        if type(self.source) is not str or self.source not in {
            "fresh",
            "cleanup_retry",
        }:
            raise ValueError("invalid_recovery_source")

    @property
    def cursor(self) -> ExecutionRecoveryCursor:
        return ExecutionRecoveryCursor(self.updated_at, self.run_id)


@dataclass(frozen=True)
class ExecutionRecoveryClaim:
    candidate: ExecutionRecoveryCandidate
    claim_token: str
    claim_fence: int
    claim_expires_at: datetime
    transition: str
    advances_discovery_cursor: bool

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, ExecutionRecoveryCandidate):
            raise ValueError("invalid_recovery_candidate")
        _run_id(self.claim_token)
        if type(self.claim_fence) is not int or not 1 <= self.claim_fence < 2**63:
            raise ValueError("invalid_recovery_claim_fence")
        _timestamp(self.claim_expires_at)
        if self.transition not in {"orphaned", "cancelled", "cleanup_retry"}:
            raise ValueError("invalid_recovery_transition")
        if type(self.advances_discovery_cursor) is not bool:
            raise ValueError("invalid_recovery_cursor_authority")


@dataclass(frozen=True)
class ExecutionRecoveryNotDue:
    candidate: ExecutionRecoveryCandidate

    def __post_init__(self) -> None:
        if (
            not isinstance(self.candidate, ExecutionRecoveryCandidate)
            or self.candidate.source != "fresh"
        ):
            raise ValueError("invalid_recovery_not_due")


@dataclass(frozen=True)
class ExecutionRecoveryPage:
    candidates: tuple[ExecutionRecoveryCandidate, ...]
    scanned_through: ExecutionRecoveryCursor | None
    exhausted: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(self.candidates, tuple)
            or any(
                not isinstance(candidate, ExecutionRecoveryCandidate)
                for candidate in self.candidates
            )
            or (
                self.scanned_through is not None
                and not isinstance(self.scanned_through, ExecutionRecoveryCursor)
            )
            or type(self.exhausted) is not bool
        ):
            raise ValueError("invalid_recovery_page")
        fresh_cursors = tuple(
            candidate.cursor
            for candidate in self.candidates
            if candidate.source == "fresh"
        )
        expected_scan = max(fresh_cursors) if fresh_cursors else None
        run_ids = tuple(candidate.run_id for candidate in self.candidates)
        manifest_digests = tuple(
            candidate.manifest_digest for candidate in self.candidates
        )
        if (
            len(set(run_ids)) != len(run_ids)
            or len(set(manifest_digests)) != len(manifest_digests)
            or self.scanned_through != expected_scan
        ):
            raise ValueError("invalid_recovery_page")


@dataclass(frozen=True)
class ExecutionRecoveryResult:
    candidates: int
    orphaned: int
    cleanup_failed: int
    terminalize_failed: int
    cursor: ExecutionRecoveryCursor | None
    cancelled: int = 0


class ExecutionRecoveryStore(Protocol):
    def execution_recovery_candidates(
        self, *, limit: int, cursor: ExecutionRecoveryCursor | None
    ) -> ExecutionRecoveryPage: ...

    def claim_execution_recovery(
        self,
        candidate: ExecutionRecoveryCandidate,
        actor: Actor,
        *,
        timeout_seconds: float = 5.0,
    ) -> ExecutionRecoveryClaim | ExecutionRecoveryNotDue | None: ...

    def record_execution_cleanup_success(
        self, claim: ExecutionRecoveryClaim, *, timeout_seconds: float = 5.0
    ) -> None: ...

    def record_execution_cleanup_failure(
        self, claim: ExecutionRecoveryClaim, *, timeout_seconds: float = 5.0
    ) -> None: ...


class WorkspaceReleaser(Protocol):
    """Exact-handle idempotent release that must honor the supplied timeout.

    Calls are at least once: a retry after claim expiry may overlap an older call.
    Implementations must return ``already_absent`` after a prior release and must
    not affect any workspace other than the exact handle.
    """

    def release(
        self, handle: WorkspaceHandle, *, timeout_seconds: float
    ) -> WorkspaceReleaseOutcome: ...


class ExecutionRecovery:
    def __init__(
        self,
        store: ExecutionRecoveryStore,
        workspace: WorkspaceReleaser,
        actor: Actor,
        *,
        monotonic: Callable[[], float] = system_monotonic,
    ) -> None:
        if (
            not isinstance(actor, Actor)
            or actor.kind != "operator"
            or "factory:reconcile" not in actor.scopes
            or "*" not in actor.repositories
        ):
            raise ValueError("invalid_recovery_actor")
        self.store = store
        self.workspace = workspace
        self.actor = actor
        self.monotonic = monotonic

    def reconcile(
        self, *, limit: int = 100, cursor: ExecutionRecoveryCursor | None = None
    ) -> ExecutionRecoveryResult:
        if type(limit) is not int or not 2 <= limit <= 100:
            raise ValueError("invalid_recovery_limit")
        if cursor is not None and not isinstance(cursor, ExecutionRecoveryCursor):
            raise ValueError("invalid_recovery_cursor")
        started_at = self.monotonic()
        page = self.store.execution_recovery_candidates(limit=limit, cursor=cursor)
        if not isinstance(page, ExecutionRecoveryPage):
            raise ValueError("invalid_recovery_page")
        safe_cursor = cursor
        fresh_blocked = False
        page_consumed = True
        attempted = 0
        orphaned = cancelled = cleanup_failed = terminalize_failed = 0
        fresh = [candidate for candidate in page.candidates if candidate.source == "fresh"]
        retries = [
            candidate
            for candidate in page.candidates
            if candidate.source == "cleanup_retry"
        ]
        ordered = []
        while fresh or retries:
            if fresh:
                ordered.append(fresh.pop(0))
            if retries:
                ordered.append(retries.pop(0))
        for candidate in ordered:
            if candidate.source == "fresh" and fresh_blocked:
                continue
            remaining = _RECOVERY_BUDGET_SECONDS - (
                self.monotonic() - started_at
            )
            # libpq rounds a one-second connect timeout up to a two-second
            # effective minimum. A claim or outcome therefore reserves three
            # seconds (connect + statement), in addition to the five-second
            # broker deadline and scheduling margin.
            if remaining <= _RECOVERY_CYCLE_RESERVE_SECONDS:
                page_consumed = False
                break
            attempted += 1
            try:
                decision = self.store.claim_execution_recovery(
                    candidate,
                    self.actor,
                    timeout_seconds=_RECOVERY_DB_TIMEOUT_SECONDS,
                )
                if isinstance(decision, ExecutionRecoveryNotDue):
                    if decision.candidate != candidate:
                        terminalize_failed += 1
                        fresh_blocked = True
                    else:
                        safe_cursor = max(
                            value
                            for value in (safe_cursor, candidate.cursor)
                            if value is not None
                        )
                    continue
                claim = decision
                if claim is None or claim.candidate != candidate:
                    terminalize_failed += 1
                    if candidate.source == "fresh":
                        fresh_blocked = True
                    continue
                if claim.transition == "orphaned":
                    orphaned += 1
                elif claim.transition == "cancelled":
                    cancelled += 1
                if claim.advances_discovery_cursor and not fresh_blocked:
                    safe_cursor = max(
                        value
                        for value in (safe_cursor, candidate.cursor)
                        if value is not None
                    )
            except Exception:
                terminalize_failed += 1
                if candidate.source == "fresh":
                    fresh_blocked = True
                continue
            handle = WorkspaceHandle(
                claim.candidate.task_id,
                claim.candidate.run_id,
                claim.candidate.workspace_handle,
            )
            try:
                remaining = _RECOVERY_BUDGET_SECONDS - (
                    self.monotonic() - started_at
                )
                if remaining <= 5.0 + _RECOVERY_OUTCOME_RESERVE_SECONDS:
                    raise TimeoutError("recovery broker margin exhausted")
                cleanup = self.workspace.release(
                    handle,
                    timeout_seconds=min(
                        5.0, remaining - _RECOVERY_OUTCOME_RESERVE_SECONDS
                    ),
                )
                if type(cleanup) is not WorkspaceReleaseOutcome:
                    raise ValueError("workspace_cleanup_failed")
            except Exception:
                cleanup_failed += 1
                remaining = _RECOVERY_BUDGET_SECONDS - (
                    self.monotonic() - started_at
                )
                try:
                    if remaining < _RECOVERY_OUTCOME_RESERVE_SECONDS:
                        raise TimeoutError("recovery failure outcome margin exhausted")
                    self.store.record_execution_cleanup_failure(
                        claim, timeout_seconds=_RECOVERY_DB_TIMEOUT_SECONDS
                    )
                except Exception:
                    terminalize_failed += 1
                continue
            try:
                remaining = _RECOVERY_BUDGET_SECONDS - (
                    self.monotonic() - started_at
                )
                if remaining < _RECOVERY_OUTCOME_RESERVE_SECONDS:
                    raise TimeoutError("recovery success outcome margin exhausted")
                self.store.record_execution_cleanup_success(
                    claim, timeout_seconds=_RECOVERY_DB_TIMEOUT_SECONDS
                )
            except Exception:
                cleanup_failed += 1
        if not fresh_blocked and page_consumed and not page.exhausted:
            if page.scanned_through is None or safe_cursor != page.scanned_through:
                raise ValueError("invalid_recovery_page_watermark")
        if not fresh_blocked and page.exhausted and page_consumed:
            safe_cursor = None
        return ExecutionRecoveryResult(
            attempted,
            orphaned,
            cleanup_failed,
            terminalize_failed,
            safe_cursor,
            cancelled,
        )
