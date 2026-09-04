from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .brokers import ProposalBroker
from .contracts import HEX64, TaskIntakeV1, canonical_digest
from .execution_contracts import (
    ExecutionContractError,
    ExecutionSelectionV1,
    RunManifestV1,
    TaskPacketV1,
    WorkspaceResultV1,
)
from .models import Actor, ExecutionStage, FailureClass, LeaseGrant, RunRole, TaskStatus
from .protocol import CanonicalEvent
from .semantic_adjudication import adjudicate
from .semantic_bridge import SemanticValidationInputsV1, build_semantic_subject
from .semantic_contracts import (
    MAX_ITEMS,
    SemanticCoverageV1,
    SemanticFindingV1,
    SemanticSubjectV1,
    ValidatorIdentityV1,
)
from .semantic_repair import (
    RepairChildTaskBindingV1,
    RepairLifecycleResult,
    SemanticRepairRequestV1,
)
from .workspace import (
    ArtifactAttestationRequest,
    ArtifactAttestationV1,
    WorkspaceError,
    WorkspaceSnapshotV1,
)
from .store import FenceError, StoreUnavailable


class AuthorizationError(PermissionError):
    pass


class SnapshotBrokerUnavailable(RuntimeError):
    pass


class SnapshotBrokerIntegrityError(RuntimeError):
    pass


REPAIR_CHILD_BROKER_ACTOR_KIND = "repair_broker"
REPAIR_CHILD_BROKER_ACTOR_ID = "semantic-repair-child-broker"


@dataclass(frozen=True)
class ClaimRequest:
    owner: str
    role: RunRole
    repositories: tuple[str, ...]
    lease_seconds: int


@dataclass(frozen=True)
class ExecutionTerminalCompletion:
    proposal: object
    result: WorkspaceResultV1


class FactoryService:
    def __init__(
        self,
        store,
        *,
        snapshot_broker=None,
        artifact_broker=None,
        artifact_attestation_store=None,
        execution_registry=None,
        semantic_store=None,
        semantic_validator_store=None,
        semantic_adjudicator_store=None,
        repair_child_broker=None,
    ) -> None:
        self.store = store
        self.snapshot_broker = snapshot_broker
        self.artifact_broker = artifact_broker
        self.artifact_attestation_store = artifact_attestation_store
        self.execution_registry = execution_registry
        self.semantic_store = semantic_store
        self.semantic_validator_store = semantic_validator_store
        self.semantic_adjudicator_store = semantic_adjudicator_store
        self.repair_child_broker = repair_child_broker

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
        reserved_broker_identity = (
            actor.kind == REPAIR_CHILD_BROKER_ACTOR_KIND
            or actor.actor_id == REPAIR_CHILD_BROKER_ACTOR_ID
        )
        if reserved_broker_identity:
            if (
                actor.kind != REPAIR_CHILD_BROKER_ACTOR_KIND
                or actor.actor_id != REPAIR_CHILD_BROKER_ACTOR_ID
            ):
                raise AuthorizationError("repair child broker identity is invalid")
            if (
                intake.source_type != "api"
                or intake.source_id != intake.source_digest
                or HEX64.fullmatch(intake.source_id) is None
            ):
                raise AuthorizationError(
                    "repair child broker intake requires an exact proposal source"
                )
        return self.store.intake(
            intake, actor, now, correlation_id=correlation_id
        )

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

    def publish_semantic_subject(
        self,
        task_id: str,
        workspace_result_digest: str,
        validation_inputs,
        *,
        actor: Actor,
        idempotency_key: str,
        correlation_id: str | None = None,
    ):
        self._require(actor, "semantic:publish")
        if actor.kind != "operator":
            raise AuthorizationError("semantic publication requires coordinator actor")
        task = self.store.get_task(task_id)
        self._require(actor, "semantic:publish", task.repository_id)
        if self.semantic_store is None:
            raise AuthorizationError("semantic coordinator capability unavailable")
        inputs = (
            validation_inputs
            if isinstance(validation_inputs, SemanticValidationInputsV1)
            else SemanticValidationInputsV1.from_dict(validation_inputs)
        )
        if inputs.workspace_result_digest != workspace_result_digest:
            raise ExecutionContractError("semantic_result_digest_mismatch")
        material = self.semantic_store.execution_material(
            task_id, workspace_result_digest
        )
        packet = material.get("packet")
        if not isinstance(packet, TaskPacketV1) or packet.repository_id != task.repository_id:
            raise ExecutionContractError("semantic_repository_mismatch")
        record = build_semantic_subject(**material, validation_inputs=inputs)
        return self.semantic_store.publish_subject(
            material, record, idempotency_key=idempotency_key
        )

    def get_semantic_subject(
        self, task_id: str, subject_digest: str, *, actor: Actor
    ):
        self._require(actor, "semantic:read")
        task = self.store.get_task(task_id)
        self._require(actor, "semantic:read", task.repository_id)
        if self.semantic_store is None:
            raise AuthorizationError("semantic coordinator capability unavailable")
        return self.semantic_store.subject_by_digest(task_id, subject_digest)

    def create_semantic_assignment(
        self,
        task_id: str,
        subject_digest: str,
        validator,
        *,
        actor: Actor,
        idempotency_key: str,
        correlation_id: str | None = None,
    ):
        self._require(actor, "semantic:assign")
        if actor.kind != "operator":
            raise AuthorizationError("semantic assignment requires coordinator actor")
        task = self.store.get_task(task_id)
        self._require(actor, "semantic:assign", task.repository_id)
        if self.semantic_store is None:
            raise AuthorizationError("semantic coordinator capability unavailable")
        record = self.semantic_store.subject_by_digest(task_id, subject_digest)
        root = getattr(record, "subject", None)
        if not isinstance(root, SemanticSubjectV1) or root.digest != subject_digest:
            raise ExecutionContractError("semantic_subject_digest_mismatch")
        proof = (
            validator
            if isinstance(validator, ValidatorIdentityV1)
            else ValidatorIdentityV1.from_dict(validator)
        )
        proof.validate_for(root)
        return self.semantic_store.create_assignment(
            root, proof, idempotency_key=idempotency_key
        )

    def submit_semantic_evidence(
        self,
        task_id: str,
        subject_digest: str,
        assignment_digest: str,
        findings,
        coverage,
        *,
        actor: Actor,
        idempotency_key: str,
        correlation_id: str | None = None,
    ):
        self._require(actor, "semantic:validate")
        if actor.kind != "validator":
            raise AuthorizationError("semantic evidence requires validator actor")
        task = self.store.get_task(task_id)
        self._require(actor, "semantic:validate", task.repository_id)
        if self.semantic_validator_store is None:
            raise AuthorizationError("semantic validator capability unavailable")
        if not isinstance(findings, (list, tuple)) or len(findings) > MAX_ITEMS:
            raise ExecutionContractError("semantic_findings_invalid")
        finding_values = tuple(
            value
            if isinstance(value, SemanticFindingV1)
            else SemanticFindingV1.from_dict(value)
            for value in findings
        )
        coverage_value = (
            coverage
            if isinstance(coverage, SemanticCoverageV1)
            else SemanticCoverageV1.from_dict(coverage)
        )
        if (
            coverage_value.subject_digest != subject_digest
            or coverage_value.validator.validator_id != actor.actor_id
            or any(
                value.subject_digest != subject_digest
                or value.validator != coverage_value.validator
                for value in finding_values
            )
        ):
            raise AuthorizationError("semantic evidence identity mismatch")
        return self.semantic_validator_store.append_evidence(
            subject_digest,
            assignment_digest,
            finding_values,
            coverage_value,
            idempotency_key=idempotency_key,
        )

    def adjudicate_semantic_subject(
        self,
        task_id: str,
        subject_digest: str,
        *,
        actor: Actor,
        idempotency_key: str,
        correlation_id: str | None = None,
    ):
        self._require(actor, "semantic:adjudicate")
        if actor.kind != "adjudicator":
            raise AuthorizationError("semantic adjudication requires adjudicator actor")
        task = self.store.get_task(task_id)
        self._require(actor, "semantic:adjudicate", task.repository_id)
        if self.semantic_adjudicator_store is None:
            raise AuthorizationError("semantic adjudicator capability unavailable")
        material = self.semantic_adjudicator_store.adjudication_material(
            task_id, subject_digest
        )
        root = material.get("subject")
        findings = material.get("findings")
        coverages = material.get("coverages")
        if (
            not isinstance(root, SemanticSubjectV1)
            or root.digest != subject_digest
            or not isinstance(findings, tuple)
            or not isinstance(coverages, tuple)
        ):
            raise ExecutionContractError("semantic_adjudication_material_mismatch")
        verdict = adjudicate(root, findings, coverages)
        return self.semantic_adjudicator_store.append_verdict(
            material, verdict, idempotency_key=idempotency_key
        )

    def get_semantic_verdict(
        self, task_id: str, subject_digest: str, *, actor: Actor
    ):
        self._require(actor, "semantic:read")
        task = self.store.get_task(task_id)
        self._require(actor, "semantic:read", task.repository_id)
        if self.semantic_store is None:
            raise AuthorizationError("semantic coordinator capability unavailable")
        return self.semantic_store.verdict_by_subject(task_id, subject_digest)

    def request_semantic_repair(
        self,
        task_id: str,
        repair_request,
        *,
        actor: Actor,
        idempotency_key: str,
        correlation_id: str | None = None,
    ) -> RepairLifecycleResult:
        self._require(actor, "semantic:repair")
        if actor.kind != "operator":
            raise AuthorizationError("semantic repair requires coordinator actor")
        task = self.store.get_task(task_id)
        self._require(actor, "semantic:repair", task.repository_id)
        if self.semantic_store is None:
            raise AuthorizationError("semantic coordinator capability unavailable")
        request = (
            repair_request
            if isinstance(repair_request, SemanticRepairRequestV1)
            else SemanticRepairRequestV1.from_dict(repair_request)
        )
        result = self.semantic_store.request_repair(
            task_id, request, idempotency_key=idempotency_key
        )
        if not isinstance(result, RepairLifecycleResult):
            raise ExecutionContractError("semantic_repair_result_invalid")
        if result.decision == "repair":
            if result.child_proposal is None:
                raise ExecutionContractError("semantic_repair_child_missing")
            if self.repair_child_broker is None:
                raise ExecutionContractError("repair_child_broker_unavailable")
            binding_wire = self.repair_child_broker.propose_repair_child(
                result.child_proposal,
                idempotency_key=result.child_proposal_digest,
            )
            try:
                binding = (
                    binding_wire
                    if isinstance(binding_wire, RepairChildTaskBindingV1)
                    else RepairChildTaskBindingV1.from_dict(binding_wire)
                )
            except (TypeError, ValueError) as exc:
                raise ExecutionContractError("repair_child_binding_invalid") from exc
            if binding.child_proposal_digest != result.child_proposal_digest:
                raise ExecutionContractError("repair_child_binding_mismatch")
            persisted = self.semantic_store.bind_repair_child(binding)
            if persisted != binding:
                raise ExecutionContractError("repair_child_binding_persistence_mismatch")
        return result

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
        try:
            if self.snapshot_broker is None:
                raise SnapshotBrokerUnavailable("trusted workspace snapshot unavailable")
            request = self.store.workspace_snapshot_request(grant, packet_digest)
            try:
                snapshot = self.snapshot_broker.snapshot(request, timeout_seconds=5.0)
            except TimeoutError as exc:
                raise SnapshotBrokerUnavailable(
                    "trusted workspace snapshot unavailable"
                ) from exc
            except (TypeError, WorkspaceError) as exc:
                raise SnapshotBrokerIntegrityError(
                    "trusted workspace snapshot is invalid"
                ) from exc
            if not isinstance(snapshot, WorkspaceSnapshotV1):
                if isinstance(snapshot, WorkspaceSnapshotUnavailable):
                    raise SnapshotBrokerUnavailable(
                        "trusted workspace snapshot unavailable"
                    )
                raise SnapshotBrokerIntegrityError(
                    "trusted workspace snapshot is invalid"
                )
            try:
                snapshot = WorkspaceSnapshotV1.from_dict(snapshot.to_dict())
            except WorkspaceError as exc:
                raise SnapshotBrokerIntegrityError(
                    "trusted workspace snapshot is invalid"
                ) from exc
            if (
                snapshot.repository_id != request.repository_id
                or snapshot.workspace_handle != request.workspace_handle
                or snapshot.input_head_sha != request.input_head_sha
            ):
                raise SnapshotBrokerIntegrityError(
                    "trusted workspace snapshot binding mismatch"
                )
            return self.store.finalize_execution(
                grant,
                packet_digest,
                snapshot,
                actor,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
        except (
            FenceError,
            StoreUnavailable,
            SnapshotBrokerIntegrityError,
            SnapshotBrokerUnavailable,
        ) as error:
            try:
                replay = self.store.execution_finalization_replay(
                    grant, packet_digest, actor, idempotency_key=idempotency_key
                )
            except (FenceError, StoreUnavailable):
                replay = None
            if replay is not None:
                return replay
            if isinstance(error, FenceError):
                self._record_fence_rejection_best_effort()
            raise

    def commit_terminal_and_finalize(
        self,
        grant: LeaseGrant,
        *,
        packet_digest: str,
        sequence: int,
        event_type: str,
        payload,
        actor: Actor,
        idempotency_key: str,
        correlation_id: str | None = None,
    ) -> ExecutionTerminalCompletion:
        if (
            type(idempotency_key) is not str
            or len(idempotency_key) != 64
            or any(character not in "0123456789abcdef" for character in idempotency_key)
        ):
            raise ExecutionContractError("terminal_idempotency_required")

        def phase_key(phase: str) -> str:
            return canonical_digest(
                {
                    "contract": "adaptive-factory.execution-terminal-phase/v1",
                    "command": idempotency_key,
                    "phase": phase,
                }
            )

        proposal_key = phase_key("proposal")
        finalize_key = phase_key("finalize")
        event = CanonicalEvent.from_payload(
            task_id=grant.task_id,
            run_id=grant.run_id,
            packet_digest=packet_digest,
            sequence=sequence,
            event_type=event_type,
            payload=payload,
        )
        self._require_grant_actor(grant, actor, "task:execute")
        self._fenced(
            lambda: self.store.begin_execution_terminal_composite(
                grant,
                event,
                actor,
                proposal_key=proposal_key,
                finalize_key=finalize_key,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
        )
        proposal = self.commit_execution_proposal(
            grant,
            packet_digest=packet_digest,
            sequence=sequence,
            event_type=event_type,
            payload=payload,
            actor=actor,
            idempotency_key=proposal_key,
            correlation_id=correlation_id,
        )
        result = self.finalize_execution(
            grant,
            packet_digest=packet_digest,
            actor=actor,
            idempotency_key=finalize_key,
            correlation_id=correlation_id,
        )
        return ExecutionTerminalCompletion(proposal, result)

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
        event = CanonicalEvent.from_payload(
            task_id=grant.task_id,
            run_id=grant.run_id,
            packet_digest=packet_digest,
            sequence=sequence,
            event_type=event_type,
            payload=payload,
        )
        replay = self.store.execution_proposal_replay(
            grant, event, actor, idempotency_key=idempotency_key
        )
        if replay is not None:
            return replay
        try:
            context = self.store.proposal_context(grant, packet_digest)
            proposal_broker = ProposalBroker()
            artifact_attestation_digest = None
            if event_type == "artifact.proposed":
                proposal_broker.accept(
                    event,
                    context,
                    owner=grant.owner,
                    fence=grant.fence,
                    artifact_attestation_digest="0" * 64,
                )
                try:
                    request = ArtifactAttestationRequest.from_facts({
                        "task_id": context.task_id,
                        "run_id": context.run_id,
                        "repository_id": context.repository_id,
                        "packet_digest": context.packet_digest,
                        "workspace_handle": context.workspace_handle,
                        "producer_sequence": event.sequence,
                        "fence": grant.fence,
                        "author_role": context.role,
                        "artifact_class": event.payload["artifact_class"],
                        "path": event.payload["path"],
                        "sha256": event.payload["sha256"],
                        "size_bytes": event.payload["size_bytes"],
                        "media_type": event.payload["media_type"],
                    })
                except WorkspaceError as exc:
                    raise ExecutionContractError("artifact_attestation_invalid") from exc
                if self.artifact_broker is None:
                    raise ExecutionContractError("artifact_attestation_unavailable")
                attestation = self.artifact_broker.attest_artifact(request)
                if not isinstance(attestation, ArtifactAttestationV1):
                    raise ExecutionContractError("artifact_attestation_unavailable")
                try:
                    attestation = ArtifactAttestationV1.from_dict(attestation.to_dict())
                except ValueError as exc:
                    raise ExecutionContractError("artifact_attestation_invalid") from exc
                if any(
                    getattr(attestation, name) != value
                    for name, value in request.to_dict().items()
                ):
                    raise ExecutionContractError("artifact_attestation_mismatch")
                if self.artifact_attestation_store is None:
                    raise ExecutionContractError("artifact_attestation_unavailable")
                recorded = self.artifact_attestation_store.record_artifact_attestation(attestation)
                if not isinstance(recorded, ArtifactAttestationV1):
                    raise ExecutionContractError("artifact_attestation_unavailable")
                try:
                    recorded = ArtifactAttestationV1.from_dict(recorded.to_dict())
                except ValueError as exc:
                    raise ExecutionContractError("artifact_attestation_invalid") from exc
                if recorded != attestation:
                    raise ExecutionContractError("artifact_attestation_mismatch")
                artifact_attestation_digest = attestation.artifact_attestation_digest
            proposal = proposal_broker.accept(
                event,
                context,
                owner=grant.owner,
                fence=grant.fence,
                artifact_attestation_digest=artifact_attestation_digest,
            )
            return self.store.commit_execution_proposal(
                grant,
                proposal,
                actor,
                event=event,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
        except FenceError as error:
            try:
                replay = self.store.execution_proposal_replay(
                    grant, event, actor, idempotency_key=idempotency_key
                )
            except FenceError:
                replay = None
            if replay is not None:
                return replay
            self._record_fence_rejection_best_effort()
            raise error
        except (StoreUnavailable, ExecutionContractError) as error:
            try:
                replay = self.store.execution_proposal_replay(
                    grant, event, actor, idempotency_key=idempotency_key
                )
            except (FenceError, StoreUnavailable):
                replay = None
            if replay is not None:
                return replay
            raise error

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
