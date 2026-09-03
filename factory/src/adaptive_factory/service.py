from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .contracts import TaskIntakeV1
from .models import Actor, FailureClass, LeaseGrant, RunRole, TaskStatus
from .store import FenceError


class AuthorizationError(PermissionError):
    pass


@dataclass(frozen=True)
class ClaimRequest:
    owner: str
    role: RunRole
    repositories: tuple[str, ...]
    lease_seconds: int


class FactoryService:
    def __init__(self, store) -> None:
        self.store = store

    def readiness(self):
        return self.store.readiness()

    def metrics(self, *, actor: Actor):
        self._require(actor, "factory:reconcile")
        if actor.kind != "operator" or "*" not in actor.repositories:
            raise AuthorizationError("metrics require operator actor")
        return self.store.metrics()

    @staticmethod
    def _require(actor: Actor, scope: str, repository: str | None = None) -> None:
        if scope not in actor.scopes:
            raise AuthorizationError(f"missing scope: {scope}")
        if repository is not None and "*" not in actor.repositories and repository not in actor.repositories:
            raise AuthorizationError("repository is outside actor authorization")

    def intake(
        self,
        payload,
        *,
        actor: Actor,
        now: datetime,
        correlation_id: str | None = None,
    ):
        intake = TaskIntakeV1.from_dict(payload, now=now) if not isinstance(payload, TaskIntakeV1) else payload
        self._require(actor, "task:submit", intake.repository_id)
        return self.store.intake(
            intake, actor, now, correlation_id=correlation_id
        )

    def get_task(self, task_id: str, *, actor: Actor):
        self._require(actor, "task:read")
        task = self.store.get_task(task_id)
        self._require(actor, "task:read", task.repository_id)
        return task

    def list_tasks(self, *, repository_id: str, limit: int, cursor: str | None, actor: Actor):
        self._require(actor, "task:list", repository_id)
        return self.store.list_tasks(repository_id=repository_id, limit=limit, cursor_task_id=cursor)

    def list_task_runs(self, task_id: str, *, limit: int, cursor: str | None, actor: Actor):
        self._require(actor, "task:read")
        return self.store.list_task_runs(
            task_id,
            limit=limit,
            cursor_run_id=cursor,
            authorize_repository=lambda repository_id: self._require(
                actor, "task:read", repository_id
            ),
        )

    def list_task_events(self, task_id: str, *, limit: int, cursor: int | None, actor: Actor):
        self._require(actor, "task:read")
        return self.store.list_task_events(
            task_id,
            limit=limit,
            cursor_sequence=cursor,
            authorize_repository=lambda repository_id: self._require(
                actor, "task:read", repository_id
            ),
        )

    def claim(
        self, *, owner: str, role: RunRole, repositories: Iterable[str], lease_seconds: int, actor: Actor, now: datetime,
        idempotency_key: str | None = None, correlation_id: str | None = None
    ):
        self._require(actor, "task:claim")
        repositories = tuple(sorted(set(repositories)))
        if not repositories or any(
            "*" not in actor.repositories and repository not in actor.repositories for repository in repositories
        ):
            raise AuthorizationError("claim repository is outside actor authorization")
        if not 30 <= lease_seconds <= 300:
            raise ValueError("lease_seconds must be between 30 and 300")
        if actor.kind != "worker":
            raise AuthorizationError("claim requires worker actor")
        return self.store.claim(
            ClaimRequest(actor.actor_id, role, repositories, lease_seconds), actor, now,
            idempotency_key=idempotency_key, correlation_id=correlation_id,
        )

    def _require_grant_actor(self, grant: LeaseGrant, actor: Actor, scope: str) -> None:
        self._require(actor, scope)
        if actor.kind != "worker" or grant.owner != actor.actor_id:
            raise AuthorizationError("lease grant belongs to another worker")
        task = self.store.get_task(grant.task_id)
        self._require(actor, scope, task.repository_id)

    def _fenced(self, operation):
        try:
            return operation()
        except FenceError:
            self._record_fence_rejection_best_effort()
            raise

    def _record_fence_rejection_best_effort(self) -> bool:
        try:
            self.store.record_fence_rejection()
        except Exception:
            return False
        return True

    def heartbeat(self, grant: LeaseGrant, *, actor: Actor, now: datetime, idempotency_key: str | None = None, correlation_id: str | None = None):
        self._require_grant_actor(grant, actor, "task:heartbeat")
        return self._fenced(
            lambda: self.store.heartbeat(
                grant, actor, now, idempotency_key=idempotency_key, correlation_id=correlation_id
            )
        )

    def release(self, grant: LeaseGrant, *, outcome: str | FailureClass, actor: Actor, now: datetime, idempotency_key: str | None = None, correlation_id: str | None = None):
        self._require_grant_actor(grant, actor, "task:release")
        if isinstance(outcome, str) and outcome != "completed":
            outcome = FailureClass(outcome)
        return self._fenced(
            lambda: self.store.release(
                grant, outcome, actor, now, idempotency_key=idempotency_key, correlation_id=correlation_id
            )
        )

    def transition_phase(
        self,
        grant: LeaseGrant,
        *,
        target: TaskStatus,
        actor: Actor,
        now: datetime,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> TaskStatus:
        self._require_grant_actor(grant, actor, "task:release")
        if not isinstance(target, TaskStatus) or target not in {
            TaskStatus.ANALYZING,
            TaskStatus.IMPLEMENTING,
            TaskStatus.VERIFYING,
            TaskStatus.REVIEWING,
        }:
            raise ValueError("target must be the next worker phase")
        return self._fenced(
            lambda: self.store.transition_phase(
                grant,
                target,
                actor,
                now,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
        )

    def reserve_budget(
        self,
        grant: LeaseGrant,
        *,
        cost_usd_micros: int,
        token_units: int,
        wall_seconds: int,
        reason_digest: str,
        idempotency_key: str,
        actor: Actor,
        correlation_id: str | None = None,
    ):
        self._require_grant_actor(grant, actor, "task:budget")
        return self._fenced(
            lambda: self.store.reserve_budget(
                grant, cost_usd_micros, token_units, wall_seconds, reason_digest, idempotency_key, actor,
                correlation_id=correlation_id,
            )
        )

    def observe_usage(
        self,
        grant: LeaseGrant,
        *,
        provider_call_id: str,
        price_table_digest: str | None,
        cost_usd_micros: int,
        token_units: int,
        output_bytes: int,
        actor: Actor,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ):
        self._require_grant_actor(grant, actor, "task:budget")
        return self._fenced(
            lambda: self.store.observe_usage(
                grant, provider_call_id, price_table_digest, cost_usd_micros, token_units, output_bytes, actor,
                idempotency_key=idempotency_key, correlation_id=correlation_id,
            )
        )

    def set_kill(
        self, *, scope_key: str, enabled: bool, reason: str, idempotency_key: str, actor: Actor, now: datetime,
        correlation_id: str | None = None
    ):
        self._require(actor, "factory:kill")
        if actor.kind != "operator":
            raise AuthorizationError("kill switch requires operator actor")
        if scope_key == "global":
            if "*" not in actor.repositories:
                raise AuthorizationError("global kill requires wildcard repository authority")
        elif scope_key.startswith("repository:"):
            self._require(actor, "factory:kill", scope_key.removeprefix("repository:"))
        return self.store.set_kill(scope_key, enabled, reason, idempotency_key, actor, now, correlation_id=correlation_id)

    def reconcile(self, *, actor: Actor, now: datetime, limit: int = 100, cursor: str | None = None, idempotency_key: str | None = None, correlation_id: str | None = None):
        self._require(actor, "factory:reconcile")
        if actor.kind != "operator" or "*" not in actor.repositories or not 1 <= limit <= 100:
            raise AuthorizationError("bounded operator reconciliation required")
        return self.store.reconcile(actor, now, limit, cursor, idempotency_key=idempotency_key, correlation_id=correlation_id)

    def cancel(self, task_id: str, *, reason: str, idempotency_key: str, actor: Actor, now: datetime, correlation_id: str | None = None):
        self._require(actor, "task:cancel")
        return self.store.cancel(
            task_id,
            reason,
            idempotency_key,
            actor,
            now,
            correlation_id=correlation_id,
            authorize_repository=lambda repository_id: self._require(
                actor,
                "task:cancel",
                repository_id,
            ),
        )
