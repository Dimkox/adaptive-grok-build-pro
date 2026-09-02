from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .brokers import ProposalBroker
from .contracts import TaskIntakeV1, canonical_digest
from .execution_contracts import (
    ExecutionContractError,
    ExecutionSelectionV1,
    PROTOCOL_VERSION,
    RunManifestV1,
    TaskPacketV1,
)
from .models import Actor, ExecutionStage, FailureClass, LeaseGrant, RunRole
from .protocol import CanonicalEvent
from .workspace import WorkspaceSnapshotV1
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
    def __init__(self, store, *, snapshot_broker=None, execution_registry=None) -> None:
        self.store = store
        self.snapshot_broker = snapshot_broker
        self.execution_registry = execution_registry

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

    def intake(self, payload, *, actor: Actor, now: datetime):
        intake = TaskIntakeV1.from_dict(payload, now=now) if not isinstance(payload, TaskIntakeV1) else payload
        self._require(actor, "task:submit", intake.repository_id)
        return self.store.intake(intake, actor, now)

    def get_task(self, task_id: str, *, actor: Actor):
        self._require(actor, "task:read")
        task = self.store.get_task(task_id)
        self._require(actor, "task:read", task.repository_id)
        return task

    def get_workspace_result(self, task_id: str, workspace_result_digest: str, *, actor: Actor):
        self._require(actor, "task:read")
        task = self.store.get_task(task_id)
        self._require(actor, "task:read", task.repository_id)
        return self.store.workspace_result(task_id, workspace_result_digest)

    def list_tasks(self, *, repository_id: str, limit: int, cursor: str | None, actor: Actor):
        self._require(actor, "task:list", repository_id)
        return self.store.list_tasks(repository_id=repository_id, limit=limit, cursor_task_id=cursor)

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

    def claim_execution(
        self,
        *,
        owner: str,
        role: RunRole,
        repositories: Iterable[str],
        lease_seconds: int,
        selection,
        actor: Actor,
        now: datetime,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ):
        self._require(actor, "task:execute")
        if actor.kind != "worker" or owner != actor.actor_id:
            raise AuthorizationError("execution claim requires the bound worker")
        repositories = tuple(sorted(set(repositories)))
        if not repositories or any(
            "*" not in actor.repositories and repository not in actor.repositories for repository in repositories
        ):
            raise AuthorizationError("execution claim repository is outside worker authorization")
        selected = selection if isinstance(selection, ExecutionSelectionV1) else ExecutionSelectionV1.from_dict(selection)
        if self.execution_registry is None:
            raise ExecutionContractError("provider_ineligible")
        selected = self.execution_registry.resolve(selected, role=role.value)
        lease_key = (
            canonical_digest({"command": idempotency_key, "phase": "execution_lease"})
            if idempotency_key is not None
            else None
        )
        grant = self.claim(
            owner=owner,
            role=role,
            repositories=repositories,
            lease_seconds=lease_seconds,
            actor=actor,
            now=now,
            idempotency_key=lease_key,
            correlation_id=correlation_id,
        )
        if grant is None:
            return None
        try:
            if grant.owner != owner or grant.role is not role:
                raise ExecutionContractError("grant_identity_mismatch")
            material = self.store.execution_material(grant)
            selected_data = selected.to_dict()
            packet = TaskPacketV1.from_dict(
                {
                    "contract_version": 1,
                    "protocol_version": "adaptive-factory.execution/v1",
                    "task_id": grant.task_id,
                    "run_id": grant.run_id,
                    "owner": grant.owner,
                    "fence": grant.fence,
                    "role": grant.role.value,
                    "repository_id": material["repository_id"],
                    "legacy_intent_digest": material["legacy_intent_digest"],
                    "authority": {
                        "exact_base_sha": material["exact_base_sha"],
                        "exact_head_sha": material["exact_head_sha"],
                        "route_id": material["route_id"],
                        "change_id": material["change_id"],
                        "spec_digest": material["spec_digest"],
                        "architecture_digest": material["architecture_digest"],
                        "governance_digest": material["governance_digest"],
                        "policy_digest": material["policy_digest"],
                        "prompt_template_digest": selected.prompt_template_digest,
                        "role_definition_digest": selected.role_definition_digest,
                        "tool_policy_digest": selected.tool_policy_digest,
                        "output_schema_digest": selected.output_schema_digest,
                    },
                    "provider": selected_data["provider"],
                    "capability_policy": selected_data["capability_policy"],
                    "plan": selected_data["plan"],
                    "workspace_handle": selected.workspace_handle,
                    "acceptance_ids": material["acceptance_ids"],
                    "limits": material["limits"],
                },
            )
            manifest = RunManifestV1.from_packet(packet, deadline=material["deadline"])
            start_key = (
                canonical_digest(
                    {"command": idempotency_key, "phase": "execution_start", "packet_digest": packet.packet_digest}
                )
                if idempotency_key is not None
                else None
            )
            return self._fenced(
                lambda: self.store.start_execution(
                    grant,
                    packet,
                    manifest,
                    actor,
                    idempotency_key=start_key,
                    correlation_id=correlation_id,
                )
            )
        except Exception as exc:
            failure = (
                FailureClass.VALIDATION
                if isinstance(exc, (ExecutionContractError, KeyError, TypeError, ValueError))
                else FailureClass.DATABASE_UNAVAILABLE
            )
            cleanup_key = canonical_digest({
                "command": idempotency_key,
                "fence": grant.fence,
                "phase": "execution_claim_cleanup",
                "run_id": grant.run_id,
            })
            try:
                self.store.release(
                    grant,
                    failure,
                    actor,
                    now,
                    idempotency_key=cleanup_key,
                    correlation_id=correlation_id,
                )
            except Exception as cleanup_error:
                raise ExecutionContractError("execution_claim_cleanup_failed") from cleanup_error
            raise

    def advance_execution(
        self,
        grant: LeaseGrant,
        *,
        packet_digest: str,
        stage: ExecutionStage,
        actor: Actor,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ):
        self._require_grant_actor(grant, actor, "task:execute")
        if stage in {
            ExecutionStage.COMPLETED,
            ExecutionStage.FAILED,
            ExecutionStage.NEEDS_HUMAN,
            ExecutionStage.CANCELLED,
            ExecutionStage.ORPHANED,
        }:
            raise ExecutionContractError("terminal_requires_finalize")
        return self._fenced(
            lambda: self.store.advance_execution(
                grant,
                packet_digest,
                stage,
                actor,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
        )

    def finalize_execution(
        self,
        grant: LeaseGrant,
        *,
        packet_digest: str,
        actor: Actor,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ):
        self._require_grant_actor(grant, actor, "task:execute")
        replay = self.store.execution_finalization_replay(
            grant, packet_digest, actor, idempotency_key=idempotency_key
        )
        if replay is not None:
            return replay
        if self.snapshot_broker is None:
            raise ExecutionContractError("workspace_snapshot_unavailable")
        request = self.store.workspace_snapshot_request(grant, packet_digest)
        snapshot = self.snapshot_broker.snapshot(request)
        if not isinstance(snapshot, WorkspaceSnapshotV1):
            raise ExecutionContractError("workspace_snapshot_unavailable")
        return self._fenced(
            lambda: self.store.finalize_execution(
                grant,
                packet_digest,
                snapshot,
                actor,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
        )

    def commit_execution_proposal(
        self,
        grant: LeaseGrant,
        *,
        packet_digest: str,
        sequence: int,
        event_type: str,
        payload,
        actor: Actor,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ):
        self._require_grant_actor(grant, actor, "task:execute")
        if type(sequence) is not int or sequence < 1:
            raise ValueError("invalid proposal sequence")
        context = self.store.proposal_context(grant, packet_digest)
        event = CanonicalEvent(
            PROTOCOL_VERSION,
            grant.task_id,
            grant.run_id,
            packet_digest,
            sequence,
            event_type,
            payload,
        )
        proposal = ProposalBroker().accept(event, context, owner=grant.owner, fence=grant.fence)
        return self._fenced(
            lambda: self.store.commit_execution_proposal(
                grant,
                proposal,
                actor,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
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
