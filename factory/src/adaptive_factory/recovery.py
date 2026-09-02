from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Protocol
from uuid import UUID

from .workspace import WorkspaceHandle


_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_WORKSPACE = re.compile(r"^workspace:[0-9a-f]{64}$")


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
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
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

    def __post_init__(self) -> None:
        _run_id(self.task_id)
        _run_id(self.run_id)
        if not isinstance(self.manifest_digest, str) or not _HEX64.fullmatch(self.manifest_digest):
            raise ValueError("invalid_manifest_digest")
        if not isinstance(self.workspace_handle, str) or not _WORKSPACE.fullmatch(self.workspace_handle):
            raise ValueError("invalid_workspace_handle")
        _timestamp(self.updated_at)

    @property
    def cursor(self) -> ExecutionRecoveryCursor:
        return ExecutionRecoveryCursor(self.updated_at, self.run_id)


@dataclass(frozen=True)
class ExecutionRecoveryResult:
    candidates: int
    orphaned: int
    cleanup_failed: int
    terminalize_failed: int
    cursor: ExecutionRecoveryCursor | None


class ExecutionRecoveryStore(Protocol):
    def execution_recovery_candidates(
        self, *, limit: int, cursor: ExecutionRecoveryCursor | None,
    ) -> tuple[ExecutionRecoveryCandidate, ...]: ...

    def record_execution_cleanup_success(self, candidate: ExecutionRecoveryCandidate) -> None: ...

    def terminalize_execution_orphan(self, candidate: ExecutionRecoveryCandidate) -> str: ...

    def record_execution_cleanup_failure(self, candidate: ExecutionRecoveryCandidate) -> None: ...


class WorkspaceReleaser(Protocol):
    def release(self, handle: WorkspaceHandle) -> str: ...


class ExecutionRecovery:
    def __init__(self, store: ExecutionRecoveryStore, workspace: WorkspaceReleaser) -> None:
        self.store = store
        self.workspace = workspace

    def reconcile(
        self, *, limit: int = 100, cursor: ExecutionRecoveryCursor | None = None,
    ) -> ExecutionRecoveryResult:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("invalid_recovery_limit")
        if cursor is not None and not isinstance(cursor, ExecutionRecoveryCursor):
            raise ValueError("invalid_recovery_cursor")
        candidates = self.store.execution_recovery_candidates(limit=limit, cursor=cursor)
        safe_cursor = cursor
        blocked = False
        orphaned = cleanup_failed = terminalize_failed = 0
        for candidate in candidates:
            success = False
            handle = WorkspaceHandle(
                candidate.task_id, candidate.run_id, candidate.workspace_handle,
            )
            try:
                cleanup = self.workspace.release(handle)
                if cleanup not in {"fake_released", "fake_absent"}:
                    raise ValueError("workspace_cleanup_failed")
            except Exception:
                cleanup_failed += 1
                blocked = True
                try:
                    self.store.record_execution_cleanup_failure(candidate)
                except Exception:
                    pass
                continue
            if cleanup == "fake_released":
                try:
                    self.store.record_execution_cleanup_success(candidate)
                except Exception:
                    terminalize_failed += 1
                    blocked = True
                    continue
            try:
                outcome = self.store.terminalize_execution_orphan(candidate)
                if outcome == "orphaned":
                    orphaned += 1
                    success = True
                elif outcome == "already_terminal":
                    success = True
                else:
                    terminalize_failed += 1
                    blocked = True
            except Exception:
                terminalize_failed += 1
                blocked = True
            if success and not blocked:
                safe_cursor = candidate.cursor
        return ExecutionRecoveryResult(
            len(candidates), orphaned, cleanup_failed, terminalize_failed, safe_cursor,
        )
