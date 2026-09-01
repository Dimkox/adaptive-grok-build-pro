from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .contracts import TaskIntakeV1
from .models import Actor, FailureClass, LeaseGrant, RunRole


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

    @staticmethod
    def _require(actor: Actor, scope: str, repository: str | None = None) -> None:
        if scope not in actor.scopes:
            raise AuthorizationError(f"missing scope: {scope}")
        if repository is not None and "*" not in actor.repositories and repository not in actor.repositories:
            raise AuthorizationError("repository is outside actor authorization")

    def intake(self, payload, *, actor: Actor, now: datetime):
        intake = TaskIntakeV1.from_dict(payload, now=now) if not isinstance(payload, TaskIntakeV1) else payload
        self._require(actor, "task:submit", intake.repository_id)
        return self.store.intake(intake, actor, now)

    def get_task(self, task_id: str, *, actor: Actor):
        self._require(actor, "task:read")
        task = self.store.get_task(task_id)
        self._require(actor, "task:read", task.repository_id)
        return task

    def list_tasks(self, *, repository_id: str, limit: int, cursor: str | None, actor: Actor):
        self._require(actor, "task:list", repository_id)
        return self.store.list_tasks(repository_id=repository_id, limit=limit, cursor_task_id=cursor)

    def claim(
        self, *, owner: str, role: RunRole, repositories: Iterable[str], lease_seconds: int, actor: Actor, now: datetime
    ):
        self._require(actor, "task:claim")
        repositories = tuple(sorted(set(repositories)))
        if not repositories or any(
            "*" not in actor.repositories and repository not in actor.repositories for repository in repositories
        ):
            raise AuthorizationError("claim repository is outside actor authorization")
        if not 30 <= lease_seconds <= 300:
            raise ValueError("lease_seconds must be between 30 and 300")
        return self.store.claim(ClaimRequest(owner, role, repositories, lease_seconds), actor, now)

    def heartbeat(self, grant: LeaseGrant, *, actor: Actor, now: datetime):
        self._require(actor, "task:heartbeat")
        return self.store.heartbeat(grant, actor, now)

    def release(self, grant: LeaseGrant, *, outcome: str | FailureClass, actor: Actor, now: datetime):
        self._require(actor, "task:release")
        if isinstance(outcome, str) and outcome != "completed":
            outcome = FailureClass(outcome)
        return self.store.release(grant, outcome, actor, now)

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
    ):
        self._require(actor, "task:budget")
        return self.store.reserve_budget(
            grant, cost_usd_micros, token_units, wall_seconds, reason_digest, idempotency_key, actor
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
    ):
        self._require(actor, "task:budget")
        return self.store.observe_usage(
            grant, provider_call_id, price_table_digest, cost_usd_micros, token_units, output_bytes, actor
        )

    def set_kill(
        self, *, scope_key: str, enabled: bool, reason: str, idempotency_key: str, actor: Actor, now: datetime
    ):
        self._require(actor, "factory:kill")
        if actor.kind != "operator":
            raise AuthorizationError("kill switch requires operator actor")
        return self.store.set_kill(scope_key, enabled, reason, idempotency_key, actor, now)

    def reconcile(self, *, actor: Actor, now: datetime, limit: int = 100, cursor: str | None = None):
        self._require(actor, "factory:reconcile")
        if actor.kind != "operator" or not 1 <= limit <= 100:
            raise AuthorizationError("bounded operator reconciliation required")
        return self.store.reconcile(actor, now, limit, cursor)

    def cancel(self, task_id: str, *, reason: str, idempotency_key: str, actor: Actor, now: datetime):
        self._require(actor, "task:cancel")
        task = self.store.get_task(task_id)
        self._require(actor, "task:cancel", task.repository_id)
        return self.store.cancel(task_id, reason, idempotency_key, actor, now)
