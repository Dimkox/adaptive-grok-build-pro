from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
import json
import math
import time
import uuid

from .contracts import HEX64, TaskIntakeV1, canonical_digest, canonical_json
from .brokers import (
    ArtifactProposal,
    BrokerError,
    NoteProposal,
    ProposalBroker,
    ProposalContext,
    TerminalProposal,
    UsageProposal,
    proposal_idempotency_key,
)
from .execution_contracts import RunManifestV1, TaskPacketV1, WorkspaceResultV1, workspace_evidence_digest
from .migrations import discover_migrations
from .models import (
    Actor,
    ExecutionGrant,
    ExecutionStage,
    FactoryAttemptV1,
    FactoryEventHistoryPageV1,
    FactoryEventV1,
    FactoryRunAttemptV1,
    FactoryRunHistoryPageV1,
    FactoryRunV1,
    FailureClass,
    LeaseGrant,
    RunRole,
    RunStatus,
    TaskProjection,
    TaskStatus,
)
from .protocol import CanonicalEvent, PROTOCOL_VERSION
from .recovery import (
    ExecutionRecoveryCandidate,
    ExecutionRecoveryClaim,
    ExecutionRecoveryCursor,
    ExecutionRecoveryNotDue,
    ExecutionRecoveryPage,
)
from .semantic_bridge import (
    SemanticBridgeResult,
    SemanticExecutionBindingV1,
    SemanticValidationInputsV1,
)
from .semantic_adjudication import adjudicate
from .semantic_contracts import (
    MAX_ITEMS,
    SemanticCoverageV1,
    SemanticFindingV1,
    SemanticSubjectV1,
    SemanticVerdictV1,
    ValidatorIdentityV1,
)
from .semantic_repair import (
    RepairChildTaskBindingV1,
    RepairLifecycleResult,
    SemanticRepairRequestV1,
)
from .state import (
    TransitionCommand,
    TransitionOperation,
    authorize_transition,
    classify_retry,
)
from .workspace import (
    ArtifactAttestationUnavailable,
    ArtifactAttestationV1,
    WorkspaceSnapshotRequest,
    WorkspaceSnapshotV1,
)


class StoreError(RuntimeError):
    pass


class FenceError(StoreError):
    pass


class BudgetError(StoreError):
    pass


class AuthorityError(StoreError):
    pass


class MetricsUnavailable(StoreError):
    pass


class StoreUnavailable(StoreError):
    pass


class TransitionError(StoreError):
    pass


class IntegrityError(StoreError):
    pass


def _validate_capability_session(cursor, capability_role: str, label: str) -> None:
    cursor.execute(
        """SELECT rolcanlogin,rolinherit,rolsuper,rolcreaterole,rolcreatedb,
        rolreplication,rolbypassrls,COALESCE(rolconfig,ARRAY[]::text[])
        FROM pg_roles WHERE rolname=session_user"""
    )
    identity = cursor.fetchone()
    if identity is None or identity[:7] != (True, False, False, False, False, False, False) \
            or tuple(identity[7]) != ():
        raise StoreError(f"{label} login is not least privilege")
    if cursor.connection.info.server_version >= 160000:
        cursor.execute(
            """SELECT r.rolname,m.admin_option,m.inherit_option,m.set_option
            FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.roleid
            JOIN pg_roles u ON u.oid=m.member WHERE u.rolname=session_user"""
        )
        membership = cursor.fetchall()
        expected_membership = [(capability_role, False, False, True)]
    else:
        cursor.execute(
            """SELECT r.rolname,m.admin_option FROM pg_auth_members m
            JOIN pg_roles r ON r.oid=m.roleid JOIN pg_roles u ON u.oid=m.member
            WHERE u.rolname=session_user"""
        )
        membership = cursor.fetchall()
        expected_membership = [(capability_role, False)]
    if membership != expected_membership:
        raise StoreError(f"{label} login has excess role membership")
    cursor.execute(
        """SELECT rolcanlogin,rolinherit,rolsuper,rolcreaterole,rolcreatedb,
        rolreplication,rolbypassrls,COALESCE(rolconfig,ARRAY[]::text[])
        FROM pg_roles WHERE rolname=%s""",
        (capability_role,),
    )
    capability = cursor.fetchone()
    expected_config = (
        ("search_path=factory, pg_catalog",) if capability_role == "factory_runtime" else ()
    )
    if capability is None or capability[:7] != (False, False, False, False, False, False, False) \
            or tuple(capability[7]) != expected_config:
        raise StoreError(f"{label} capability role is not isolated")
    cursor.execute(
        """SELECT
        EXISTS(SELECT 1 FROM pg_auth_members membership
          JOIN pg_roles member ON member.oid=membership.member
          WHERE member.rolname=%s),
        ARRAY(SELECT member.rolname FROM pg_auth_members membership
          JOIN pg_roles role ON role.oid=membership.roleid
          JOIN pg_roles member ON member.oid=membership.member
          WHERE role.rolname=%s ORDER BY member.rolname),
        session_user""",
        (capability_role, capability_role),
    )
    outbound_membership, inbound_members, session_user = cursor.fetchone()
    if outbound_membership or tuple(inbound_members) != (session_user,):
        raise StoreError(f"{label} capability role is not isolated")
    cursor.execute(
        """WITH login AS (SELECT oid FROM pg_roles WHERE rolname=session_user)
        SELECT
          (SELECT datdba=(SELECT oid FROM login) FROM pg_database WHERE datname=current_database())
          OR EXISTS(SELECT 1 FROM pg_namespace WHERE nspowner=(SELECT oid FROM login))
          OR EXISTS(SELECT 1 FROM pg_class WHERE relowner=(SELECT oid FROM login))
          OR EXISTS(SELECT 1 FROM pg_proc WHERE proowner=(SELECT oid FROM login))
          OR EXISTS(SELECT 1 FROM pg_type WHERE typowner=(SELECT oid FROM login))
          OR EXISTS(SELECT 1 FROM pg_database d
            CROSS JOIN LATERAL aclexplode(d.datacl) a
            WHERE d.datacl IS NOT NULL AND a.grantee=(SELECT oid FROM login)
              AND NOT (
                d.datname=current_database() AND a.privilege_type='CONNECT'
                AND NOT a.is_grantable
              ))
          OR EXISTS(SELECT 1 FROM pg_namespace n
            CROSS JOIN LATERAL aclexplode(n.nspacl) a
            WHERE n.nspacl IS NOT NULL AND a.grantee=(SELECT oid FROM login))
          OR EXISTS(SELECT 1 FROM pg_class c
            CROSS JOIN LATERAL aclexplode(c.relacl) a
            WHERE c.relacl IS NOT NULL AND a.grantee=(SELECT oid FROM login))
          OR EXISTS(SELECT 1 FROM pg_attribute c
            CROSS JOIN LATERAL aclexplode(c.attacl) a
            WHERE c.attacl IS NOT NULL AND a.grantee=(SELECT oid FROM login))
          OR EXISTS(SELECT 1 FROM pg_proc p
            CROSS JOIN LATERAL aclexplode(p.proacl) a
            WHERE p.proacl IS NOT NULL AND a.grantee=(SELECT oid FROM login))
          OR EXISTS(SELECT 1 FROM pg_type t
            CROSS JOIN LATERAL aclexplode(t.typacl) a
            WHERE t.typacl IS NOT NULL AND a.grantee=(SELECT oid FROM login))
          OR EXISTS(SELECT 1 FROM pg_default_acl d
            CROSS JOIN LATERAL aclexplode(d.defaclacl) a
            WHERE d.defaclrole=(SELECT oid FROM login) OR a.grantee=(SELECT oid FROM login))"""
    )
    if cursor.fetchone()[0]:
        raise StoreError(f"{label} login has direct database authority")


@dataclass(frozen=True)
class IntakeResult:
    task: TaskProjection
    created: bool


@dataclass(frozen=True)
class ReconcileResult:
    candidates: int
    repaired: int
    cursor: str | None


@dataclass(frozen=True)
class UsageResult:
    observation_id: str
    created: bool


@dataclass(frozen=True)
class TerminalizationResult:
    changed: bool
    accounting_quarantined: bool
    from_state: TaskStatus | None = None
    operation: TransitionOperation | None = None


class PostgresArtifactAttestationStore:
    """Dedicated capability boundary; its login must not inherit factory_runtime."""

    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise StoreError("artifact attestor database URL is required")
        self.database_url = database_url

    def _connect(self):
        import psycopg

        connection = psycopg.connect(self.database_url, connect_timeout=5)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path=pg_catalog")
                cursor.execute("SET lock_timeout='5s'; SET statement_timeout='5s'")
                _validate_capability_session(
                    cursor, "factory_artifact_attestor", "artifact attestor"
                )
                cursor.execute("SET ROLE factory_artifact_attestor")
                cursor.execute("SET search_path=pg_catalog,factory")
                cursor.execute("SELECT current_user,current_setting('search_path')")
                if cursor.fetchone() != ("factory_artifact_attestor", "pg_catalog, factory"):
                    raise StoreError("artifact attestor capability unavailable")
            return connection
        except Exception:
            connection.close()
            raise

    def readiness(self) -> dict[str, str]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT session_user,current_user")
            session_user, current_user = cursor.fetchone()
            return {"session_user": session_user, "database_role": current_user}

    def record_artifact_attestation(
        self, attestation: ArtifactAttestationV1
    ) -> ArtifactAttestationV1 | ArtifactAttestationUnavailable:
        import psycopg

        try:
            with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
                cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
                cursor.execute(
                    "SELECT factory.execution_record_artifact_attestation(%s::jsonb)",
                    (json.dumps(attestation.to_dict(), sort_keys=True, separators=(",", ":")),),
                )
                value = cursor.fetchone()[0]
        except (psycopg.DataError, psycopg.IntegrityError) as exc:
            raise IntegrityError("database integrity violation") from exc
        except psycopg.Error:
            return ArtifactAttestationUnavailable(reason="trusted_artifact_attestation_unavailable")
        if value is None:
            return ArtifactAttestationUnavailable(reason="trusted_artifact_attestation_rejected")
        if isinstance(value, str):
            value = json.loads(value)
        try:
            return ArtifactAttestationV1.from_dict(value)
        except (TypeError, ValueError) as exc:
            raise StoreError("corrupt artifact attestation envelope") from exc


class PostgresSemanticCoordinatorStore:
    """Subject-only M6 coordinator capability with no execution or evidence writes."""

    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise StoreError("semantic coordinator database URL is required")
        self.database_url = database_url

    def _connect(self):
        import psycopg

        connection = psycopg.connect(self.database_url, connect_timeout=5)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path=pg_catalog")
                cursor.execute("SET lock_timeout='5s'; SET statement_timeout='5s'")
                _validate_capability_session(
                    cursor, "factory_semantic_coordinator", "semantic coordinator"
                )
                cursor.execute("SET ROLE factory_semantic_coordinator")
                cursor.execute("SET search_path=pg_catalog,factory")
                cursor.execute("SELECT current_user,current_setting('search_path')")
                if cursor.fetchone() != (
                    "factory_semantic_coordinator",
                    "pg_catalog, factory",
                ):
                    raise StoreError("semantic coordinator capability unavailable")
            return connection
        except Exception:
            connection.close()
            raise

    def readiness(self) -> dict[str, str]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT session_user,current_user")
            session_user, current_user = cursor.fetchone()
            return {"session_user": session_user, "database_role": current_user}

    @staticmethod
    def _material(value) -> dict[str, object] | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, dict) or set(value) != {
            "result",
            "snapshot",
            "packet",
            "manifest",
            "terminal_proposal",
            "artifact_proposals",
            "artifact_attestations",
        }:
            raise StoreError("stored semantic execution material is corrupt")
        try:
            packet_wire = dict(value["packet"])
            packet_digest = packet_wire.pop("packet_digest")
            packet = TaskPacketV1.from_dict(packet_wire)
            if packet.packet_digest != packet_digest:
                raise StoreError("stored semantic packet digest mismatch")
            manifest_wire = dict(value["manifest"])
            manifest_digest = manifest_wire.pop("manifest_digest")
            manifest = RunManifestV1.from_packet(packet, deadline=manifest_wire["deadline"])
            if manifest.to_dict() != {**manifest_wire, "manifest_digest": manifest_digest}:
                raise StoreError("stored semantic manifest mismatch")
            result = WorkspaceResultV1.from_dict(value["result"])
            snapshot = WorkspaceSnapshotV1.from_dict(value["snapshot"])
            terminal = TerminalProposal(**value["terminal_proposal"])
            artifacts = tuple(ArtifactProposal(**item) for item in value["artifact_proposals"])
            attestations = tuple(
                ArtifactAttestationV1.from_dict(item)
                for item in value["artifact_attestations"]
            )
            if (
                result.task_id != packet.task_id
                or result.run_id != packet.run_id
                or result.task_packet_digest != packet.packet_digest
                or result.run_manifest_digest != manifest.manifest_digest
                or snapshot.repository_id != packet.repository_id
                or snapshot.workspace_handle != packet.workspace_handle
                or snapshot.input_head_sha != packet.authority.exact_head_sha
                or snapshot.result_head_sha != result.exact_head_sha
                or snapshot.workspace_snapshot_digest != result.workspace_snapshot_digest
                or terminal.idempotency_key != proposal_idempotency_key(terminal)
                or terminal.idempotency_key != result.terminal_proposal_digest
            ):
                raise StoreError("stored semantic execution material binding mismatch")
            return {
                "packet": packet,
                "manifest": manifest,
                "snapshot": snapshot,
                "result": result,
                "terminal_proposal": terminal,
                "artifact_proposals": artifacts,
                "artifact_attestations": attestations,
            }
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, StoreError):
                raise
            raise StoreError("stored semantic execution material is corrupt") from exc

    def execution_material(
        self, task_id: str, workspace_result_digest: str
    ) -> dict[str, object]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SET statement_timeout='5s'")
            cursor.execute(
                "SELECT factory.semantic_execution_material(%s,%s)",
                (task_id, workspace_result_digest),
            )
            material = self._material(cursor.fetchone()[0])
        if material is None:
            raise KeyError(workspace_result_digest)
        result = material["result"]
        if not isinstance(result, WorkspaceResultV1) or (
            result.task_id != task_id
            or result.workspace_result_digest != workspace_result_digest
        ):
            raise StoreError("requested semantic execution material mismatch")
        return material

    @staticmethod
    def _record(value) -> SemanticBridgeResult | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = json.loads(value)
        expected = {
            "envelope_digest",
            "binding_digest",
            "validation_inputs_digest",
            "subject_digest",
            "binding",
            "validation_inputs",
            "subject",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise StoreError("stored semantic subject record is corrupt")
        try:
            binding = SemanticExecutionBindingV1.from_dict(value["binding"])
            validation_inputs = SemanticValidationInputsV1.from_dict(
                value["validation_inputs"]
            )
            subject = SemanticSubjectV1.from_dict(value["subject"])
            record = SemanticBridgeResult(binding, validation_inputs, subject)
        except (TypeError, ValueError) as exc:
            raise StoreError("stored semantic subject record is corrupt") from exc
        if (
            value["binding_digest"] != binding.digest
            or value["validation_inputs_digest"] != validation_inputs.digest
            or value["subject_digest"] != subject.digest
            or value["envelope_digest"] != record.envelope_digest
            or validation_inputs.workspace_result_digest
            != binding.workspace_result_digest
            or subject.deterministic_evidence_digest != binding.digest
            or subject.holdout_evidence_digest
            != validation_inputs.holdout_evidence_digest
            or subject.review_evidence_digest
            != validation_inputs.review_evidence_digest
            or subject.original_writer_id != binding.owner
            or subject.original_writer_context_digest
            != validation_inputs.original_writer_context_digest
        ):
            raise StoreError("stored semantic subject digest mismatch")
        return record

    def publish_subject(
        self,
        material: dict[str, object],
        record: SemanticBridgeResult,
        *,
        idempotency_key: str,
    ) -> SemanticBridgeResult:
        packet = material.get("packet")
        if not isinstance(packet, TaskPacketV1) or not isinstance(
            record, SemanticBridgeResult
        ):
            raise StoreError("semantic publication material is invalid")
        binding_document = {
            "contract": "adaptive-factory.semantic-execution-binding/v1",
            **record.binding.to_dict(),
        }
        inputs_document = {
            "contract": "adaptive-factory.semantic-validation-inputs/v1",
            **record.validation_inputs.to_dict(),
        }
        envelope_document = {
            "contract": "adaptive-factory.semantic-subject-envelope/v1",
            "binding_digest": record.binding.digest,
            "validation_inputs_digest": record.validation_inputs.digest,
            "subject_digest": record.subject.digest,
        }
        authority_document = {
            "contract": "adaptive-factory.semantic-authority-binding/v1",
            "authority": packet.to_dict(include_digest=False)["authority"],
        }
        authority_digest = canonical_digest(authority_document)
        if (
            record.subject.authority_digest != authority_digest
            or record.binding.task_packet_digest != packet.packet_digest
        ):
            raise StoreError("semantic publication authority mismatch")
        request_document = {
            "contract": "adaptive-factory.semantic-subject-publication/v1",
            "idempotency_key": idempotency_key,
            "binding_digest": record.binding.digest,
            "validation_inputs_digest": record.validation_inputs.digest,
            "subject_digest": record.subject.digest,
            "envelope_digest": record.envelope_digest,
        }

        def encoded(document: dict[str, object]) -> str:
            return canonical_json(document).decode("utf-8")

        request_canonical = encoded(request_document)
        binding_canonical = encoded(binding_document)
        inputs_canonical = encoded(inputs_document)
        subject_canonical = encoded(record.subject.to_dict())
        envelope_canonical = encoded(envelope_document)
        authority_canonical = encoded(authority_document)
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            cursor.execute(
                "SELECT factory.semantic_publish_subject(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    idempotency_key,
                    canonical_digest(request_document),
                    request_canonical,
                    record.binding.digest,
                    binding_canonical,
                    record.validation_inputs.digest,
                    inputs_canonical,
                    record.subject.digest,
                    subject_canonical,
                    record.envelope_digest,
                    envelope_canonical,
                    authority_digest,
                    authority_canonical,
                ),
            )
            response = cursor.fetchone()[0]
        if isinstance(response, str):
            response = json.loads(response)
        if response != envelope_document:
            raise StoreError("semantic subject publication rejected")
        return record

    def subject_by_digest(
        self, task_id: str, subject_digest: str
    ) -> SemanticBridgeResult:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SET statement_timeout='5s'")
            cursor.execute(
                "SELECT factory.semantic_subject_by_digest(%s,%s)",
                (task_id, subject_digest),
            )
            record = self._record(cursor.fetchone()[0])
        if record is None:
            raise KeyError(subject_digest)
        if (
            record.binding.task_id != task_id
            or record.subject.digest != subject_digest
        ):
            raise StoreError("requested semantic subject mismatch")
        return record

    def create_assignment(
        self,
        subject: SemanticSubjectV1,
        validator: ValidatorIdentityV1,
        *,
        idempotency_key: str,
    ) -> dict[str, str]:
        if not isinstance(subject, SemanticSubjectV1) or not isinstance(
            validator, ValidatorIdentityV1
        ):
            raise StoreError("semantic assignment input is invalid")
        validator.validate_for(subject)
        assignment_document = {
            "schema_version": 1,
            "subject_digest": subject.digest,
            "validator": validator.to_dict(),
        }
        assignment_digest = canonical_digest(assignment_document)
        request_document = {
            "contract": "adaptive-factory.semantic-assignment-command/v1",
            "idempotency_key": idempotency_key,
            "assignment_digest": assignment_digest,
            "subject_digest": subject.digest,
        }
        request_canonical = canonical_json(request_document).decode("utf-8")
        assignment_canonical = canonical_json(assignment_document).decode("utf-8")
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            cursor.execute(
                "SELECT factory.semantic_create_assignment(%s,%s,%s,%s,%s)",
                (
                    idempotency_key,
                    canonical_digest(request_document),
                    request_canonical,
                    assignment_digest,
                    assignment_canonical,
                ),
            )
            response = cursor.fetchone()[0]
        if isinstance(response, str):
            response = json.loads(response)
        expected = {
            "assignment_digest": assignment_digest,
            "subject_digest": subject.digest,
            "validator_id": validator.validator_id,
        }
        if response != expected:
            raise StoreError("semantic assignment rejected")
        return expected

    @staticmethod
    def _verdict_record(value) -> dict[str, object] | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = json.loads(value)
        expected_keys = {
            "verdict_digest",
            "evidence_set_digest",
            "subject_digest",
            "verdict",
        }
        if not isinstance(value, dict) or set(value) != expected_keys:
            raise StoreError("stored semantic verdict is corrupt")
        try:
            verdict = SemanticVerdictV1.from_dict(value["verdict"])
        except (TypeError, ValueError) as exc:
            raise StoreError("stored semantic verdict is corrupt") from exc
        if (
            value["verdict_digest"] != verdict.digest
            or value["subject_digest"] != verdict.subject_digest
            or not isinstance(value["evidence_set_digest"], str)
            or not HEX64.fullmatch(value["evidence_set_digest"])
        ):
            raise StoreError("stored semantic verdict digest mismatch")
        return {
            "verdict_digest": verdict.digest,
            "evidence_set_digest": value["evidence_set_digest"],
            "subject_digest": verdict.subject_digest,
            "verdict": verdict.to_dict(),
        }

    def verdict_by_subject(
        self, task_id: str, subject_digest: str
    ) -> dict[str, object]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SET statement_timeout='5s'")
            cursor.execute(
                "SELECT factory.semantic_verdict_by_subject(%s,%s)",
                (task_id, subject_digest),
            )
            record = self._verdict_record(cursor.fetchone()[0])
        if record is None:
            raise KeyError(subject_digest)
        if record["subject_digest"] != subject_digest:
            raise StoreError("requested semantic verdict mismatch")
        return record

    def request_repair(
        self,
        task_id: str,
        repair_request: SemanticRepairRequestV1,
        *,
        idempotency_key: str,
    ) -> RepairLifecycleResult:
        if not isinstance(repair_request, SemanticRepairRequestV1):
            raise StoreError("semantic repair request is invalid")
        request_document = {
            "contract": "adaptive-factory.semantic-repair-command/v1",
            "idempotency_key": idempotency_key,
            "task_id": task_id,
            "repair_request": repair_request.to_dict(),
        }
        request_digest = canonical_digest(request_document)
        request_canonical = canonical_json(request_document).decode("utf-8")
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            cursor.execute(
                "SELECT factory.semantic_plan_repair(%s,%s,%s,%s)",
                (idempotency_key, request_digest, request_canonical, task_id),
            )
            response = cursor.fetchone()[0]
        if isinstance(response, str):
            response = json.loads(response)
        try:
            result = RepairLifecycleResult.from_dict(response)
        except (TypeError, ValueError) as exc:
            raise StoreError("stored semantic repair result is corrupt") from exc
        if (
            result.subject_digest != repair_request.subject_digest
            or result.verdict_digest != repair_request.verdict_digest
            or result.cycle != repair_request.requested_cycle
        ):
            raise StoreError("stored semantic repair result binding mismatch")
        if result.decision == "repair":
            child = result.child_proposal
            directive = result.directive
            if (
                child is None
                or directive is None
                or child.parent_task_id != task_id
                or child.parent_workspace_result_digest
                != repair_request.expected_workspace_result_digest
                or child.parent_fence != repair_request.expected_fence
                or child.parent_exact_head_sha != repair_request.expected_head_sha
                or child.writer_id != repair_request.writer_id
                or child.context_digest != repair_request.context_digest
                or child.exact_base_sha != repair_request.expected_base_sha
                or child.architecture_digest
                != repair_request.expected_architecture_digest
                or child.authority_digest != repair_request.expected_authority_digest
                or child.diff_digest != repair_request.expected_diff_digest
                or child.previous_child_proposal_digest
                != repair_request.previous_child_proposal_digest
                or directive.exact_head_sha != repair_request.expected_head_sha
            ):
                raise StoreError("stored semantic repair child binding mismatch")
        elif (
            result.escalation is None
            or result.escalation.request_digest != request_digest
        ):
            raise StoreError("stored semantic repair escalation binding mismatch")
        return result

    def bind_repair_child(
        self, binding: RepairChildTaskBindingV1
    ) -> RepairChildTaskBindingV1:
        if not isinstance(binding, RepairChildTaskBindingV1):
            raise StoreError("semantic repair child binding is invalid")
        canonical = canonical_json(binding.to_dict()).decode("utf-8")
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            cursor.execute(
                "SELECT factory.semantic_bind_repair_child(%s,%s)",
                (binding.digest, canonical),
            )
            response = cursor.fetchone()[0]
        if isinstance(response, str):
            response = json.loads(response)
        try:
            persisted = RepairChildTaskBindingV1.from_dict(response)
        except (TypeError, ValueError) as exc:
            raise StoreError("semantic repair child binding rejected") from exc
        if persisted != binding or persisted.digest != binding.digest:
            raise StoreError("semantic repair child binding mismatch")
        return persisted


class _PostgresSemanticRoleStore:
    capability_role = ""
    capability_label = "semantic"

    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise StoreError(f"{self.capability_label} database URL is required")
        self.database_url = database_url

    def _connect(self):
        import psycopg

        connection = psycopg.connect(self.database_url, connect_timeout=5)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path=pg_catalog")
                cursor.execute("SET lock_timeout='5s'; SET statement_timeout='5s'")
                _validate_capability_session(
                    cursor, self.capability_role, self.capability_label
                )
                cursor.execute(f"SET ROLE {self.capability_role}")
                cursor.execute("SET search_path=pg_catalog,factory")
                cursor.execute("SELECT current_user,current_setting('search_path')")
                if cursor.fetchone() != (
                    self.capability_role,
                    "pg_catalog, factory",
                ):
                    raise StoreError(f"{self.capability_label} capability unavailable")
            return connection
        except Exception:
            connection.close()
            raise


class PostgresSemanticValidatorStore(_PostgresSemanticRoleStore):
    capability_role = "factory_semantic_validator"
    capability_label = "semantic validator"

    @staticmethod
    def _identity_document(finding: SemanticFindingV1) -> dict[str, object]:
        return {
            "contract": "adaptive-factory.semantic-finding-identity/v1",
            "requirement": finding.requirement.to_dict(),
            "severity": finding.severity,
            "category": finding.category,
            "rule_id": finding.rule_id,
        }

    def append_evidence(
        self,
        subject_digest: str,
        assignment_digest: str,
        findings: tuple[SemanticFindingV1, ...],
        coverage: SemanticCoverageV1,
        *,
        idempotency_key: str,
    ) -> dict[str, object]:
        if (
            not isinstance(findings, tuple)
            or len(findings) > MAX_ITEMS
            or not isinstance(coverage, SemanticCoverageV1)
            or coverage.subject_digest != subject_digest
            or any(
                not isinstance(value, SemanticFindingV1)
                or value.subject_digest != subject_digest
                or value.validator != coverage.validator
                for value in findings
            )
        ):
            raise StoreError("semantic evidence input is invalid")
        finding_values = tuple(sorted(findings, key=lambda value: value.digest))
        if len({value.digest for value in finding_values}) != len(finding_values):
            raise StoreError("semantic finding digest is duplicated")
        evidence_document = {
            "contract": "adaptive-factory.semantic-evidence-submission/v1",
            "subject_digest": subject_digest,
            "assignment_digest": assignment_digest,
            "findings": [
                {
                    "finding_digest": value.digest,
                    "identity_digest": value.identity_digest,
                    "canonical": canonical_json(value.to_dict()).decode("utf-8"),
                    "identity_canonical": canonical_json(
                        self._identity_document(value)
                    ).decode("utf-8"),
                }
                for value in finding_values
            ],
            "coverage": {
                "coverage_digest": coverage.digest,
                "canonical": canonical_json(coverage.to_dict()).decode("utf-8"),
            },
        }
        evidence_set_digest = canonical_digest(evidence_document)
        request_document = {
            "contract": "adaptive-factory.semantic-evidence-command/v1",
            "idempotency_key": idempotency_key,
            "assignment_digest": assignment_digest,
            "evidence_set_digest": evidence_set_digest,
        }
        request_canonical = canonical_json(request_document).decode("utf-8")
        evidence_canonical = canonical_json(evidence_document).decode("utf-8")
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            cursor.execute(
                "SELECT factory.semantic_append_evidence(%s,%s,%s,%s,%s,%s,%s)",
                (
                    idempotency_key,
                    canonical_digest(request_document),
                    request_canonical,
                    subject_digest,
                    assignment_digest,
                    evidence_set_digest,
                    evidence_canonical,
                ),
            )
            response = cursor.fetchone()[0]
        if isinstance(response, str):
            response = json.loads(response)
        expected = {
            "evidence_set_digest": evidence_set_digest,
            "subject_digest": subject_digest,
            "assignment_digest": assignment_digest,
            "finding_digests": [value.digest for value in finding_values],
            "coverage_digest": coverage.digest,
        }
        if response != expected:
            raise StoreError("semantic evidence publication rejected")
        return expected


class PostgresSemanticAdjudicatorStore(_PostgresSemanticRoleStore):
    capability_role = "factory_semantic_adjudicator"
    capability_label = "semantic adjudicator"

    @staticmethod
    def _material(value) -> dict[str, object] | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, dict) or set(value) != {
            "subject_digest",
            "subject",
            "assignments",
            "findings",
            "coverages",
        }:
            raise StoreError("stored semantic adjudication material is corrupt")
        try:
            root = SemanticSubjectV1.from_dict(value["subject"])
            if value["subject_digest"] != root.digest:
                raise StoreError("stored semantic subject digest mismatch")
            assignment_records = value["assignments"]
            finding_records = value["findings"]
            coverage_records = value["coverages"]
            if (
                not isinstance(assignment_records, list)
                or not 1 <= len(assignment_records) <= MAX_ITEMS
                or not isinstance(finding_records, list)
                or len(finding_records) > MAX_ITEMS
                or not isinstance(coverage_records, list)
                or len(coverage_records) > MAX_ITEMS
            ):
                raise StoreError("stored semantic evidence set is invalid")

            assignment_bodies: dict[str, dict[str, object]] = {}
            assignment_validators: dict[str, ValidatorIdentityV1] = {}
            assignment_order: list[str] = []
            for record in assignment_records:
                if not isinstance(record, dict) or set(record) != {
                    "assignment_digest",
                    "body",
                }:
                    raise StoreError("stored semantic assignment is corrupt")
                digest = record["assignment_digest"]
                body = record["body"]
                if (
                    not isinstance(digest, str)
                    or not HEX64.fullmatch(digest)
                    or not isinstance(body, dict)
                    or set(body) != {"schema_version", "subject_digest", "validator"}
                    or body["schema_version"] != 1
                    or body["subject_digest"] != root.digest
                    or canonical_digest(body) != digest
                    or digest in assignment_bodies
                ):
                    raise StoreError("stored semantic assignment digest mismatch")
                proof = ValidatorIdentityV1.from_dict(body["validator"])
                proof.validate_for(root)
                assignment_order.append(digest)
                assignment_bodies[digest] = body
                assignment_validators[digest] = proof
            if assignment_order != sorted(assignment_order):
                raise StoreError("stored semantic assignments are not canonical")

            findings_by_assignment = {digest: [] for digest in assignment_order}
            finding_values: list[SemanticFindingV1] = []
            finding_order: list[str] = []
            for record in finding_records:
                if not isinstance(record, dict) or set(record) != {
                    "finding_digest",
                    "assignment_digest",
                    "body",
                }:
                    raise StoreError("stored semantic finding is corrupt")
                digest = record["finding_digest"]
                assignment_digest = record["assignment_digest"]
                finding = SemanticFindingV1.from_dict(record["body"])
                finding.validate_for(root)
                if (
                    digest != finding.digest
                    or assignment_digest not in assignment_bodies
                    or finding.validator != assignment_validators[assignment_digest]
                    or digest in finding_order
                ):
                    raise StoreError("stored semantic finding digest mismatch")
                finding_order.append(digest)
                finding_values.append(finding)
                findings_by_assignment[assignment_digest].append(digest)
            if finding_order != sorted(finding_order):
                raise StoreError("stored semantic findings are not canonical")

            coverage_by_assignment: dict[str, str] = {}
            coverage_values: list[SemanticCoverageV1] = []
            coverage_order: list[str] = []
            for record in coverage_records:
                if not isinstance(record, dict) or set(record) != {
                    "coverage_digest",
                    "assignment_digest",
                    "body",
                }:
                    raise StoreError("stored semantic coverage is corrupt")
                digest = record["coverage_digest"]
                assignment_digest = record["assignment_digest"]
                coverage = SemanticCoverageV1.from_dict(record["body"])
                coverage.validate_for(root)
                if (
                    digest != coverage.digest
                    or assignment_digest not in assignment_bodies
                    or coverage.validator != assignment_validators[assignment_digest]
                    or assignment_digest in coverage_by_assignment
                ):
                    raise StoreError("stored semantic coverage digest mismatch")
                coverage_order.append(digest)
                coverage_values.append(coverage)
                coverage_by_assignment[assignment_digest] = digest
            if coverage_order != sorted(coverage_order) or set(coverage_by_assignment) != set(
                assignment_bodies
            ):
                raise StoreError("stored semantic coverage set is incomplete")

            evidence_set = {
                "contract": "adaptive-factory.semantic-adjudication-evidence-set/v1",
                "subject_digest": root.digest,
                "assignments": [
                    {
                        "assignment_digest": digest,
                        "finding_digests": findings_by_assignment[digest],
                        "coverage_digest": coverage_by_assignment[digest],
                    }
                    for digest in assignment_order
                ],
            }
            return {
                "subject": root,
                "findings": tuple(finding_values),
                "coverages": tuple(coverage_values),
                "evidence_set": evidence_set,
                "evidence_set_digest": canonical_digest(evidence_set),
                "assignment_bodies": assignment_bodies,
            }
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, StoreError):
                raise
            raise StoreError("stored semantic adjudication material is corrupt") from exc

    def adjudication_material(
        self, task_id: str, subject_digest: str
    ) -> dict[str, object]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SET statement_timeout='5s'")
            cursor.execute(
                "SELECT factory.semantic_adjudication_material(%s,%s)",
                (task_id, subject_digest),
            )
            material = self._material(cursor.fetchone()[0])
        if material is None:
            raise KeyError(subject_digest)
        root = material["subject"]
        if not isinstance(root, SemanticSubjectV1) or root.digest != subject_digest:
            raise StoreError("requested semantic adjudication material mismatch")
        return material

    def append_verdict(
        self,
        material: dict[str, object],
        verdict: SemanticVerdictV1,
        *,
        idempotency_key: str,
    ) -> dict[str, object]:
        root = material.get("subject")
        findings = material.get("findings")
        coverages = material.get("coverages")
        evidence_set = material.get("evidence_set")
        evidence_set_digest = material.get("evidence_set_digest")
        if (
            not isinstance(root, SemanticSubjectV1)
            or not isinstance(findings, tuple)
            or not isinstance(coverages, tuple)
            or not isinstance(evidence_set, dict)
            or evidence_set_digest != canonical_digest(evidence_set)
            or not isinstance(verdict, SemanticVerdictV1)
            or verdict != adjudicate(root, findings, coverages)
        ):
            raise StoreError("semantic verdict input is invalid")
        request_document = {
            "contract": "adaptive-factory.semantic-adjudication-command/v1",
            "idempotency_key": idempotency_key,
            "subject_digest": root.digest,
            "evidence_set_digest": evidence_set_digest,
            "verdict_digest": verdict.digest,
        }
        request_canonical = canonical_json(request_document).decode("utf-8")
        evidence_canonical = canonical_json(evidence_set).decode("utf-8")
        verdict_canonical = canonical_json(verdict.to_dict()).decode("utf-8")
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            cursor.execute(
                "SELECT factory.semantic_append_verdict(%s,%s,%s,%s,%s,%s,%s)",
                (
                    idempotency_key,
                    canonical_digest(request_document),
                    request_canonical,
                    evidence_set_digest,
                    evidence_canonical,
                    verdict.digest,
                    verdict_canonical,
                ),
            )
            response = PostgresSemanticCoordinatorStore._verdict_record(
                cursor.fetchone()[0]
            )
        expected = {
            "verdict_digest": verdict.digest,
            "evidence_set_digest": evidence_set_digest,
            "subject_digest": root.digest,
            "verdict": verdict.to_dict(),
        }
        if response != expected:
            raise StoreError("semantic verdict publication rejected")
        return expected


class PostgresFactoryStore:
    _CONNECT_TIMEOUT_SECONDS = 5
    _MUTATION_LOCK_TIMEOUT = "5s"
    _MUTATION_STATEMENT_TIMEOUT = "5s"
    _RECONCILIATION_TIMEOUT_SECONDS = 5.0
    _RECONCILIATION_COMMIT_RESERVE_SECONDS = 0.1

    @staticmethod
    def _apply_task_transition(
        cursor,
        task_id: str,
        current: TaskStatus,
        target: TaskStatus,
        command: TransitionCommand,
        *,
        clear_current: bool = False,
        current_run_id: str | None = None,
        current_fence: int | None = None,
        terminal: bool = False,
        accounting_blocked: bool | None = None,
    ) -> TaskStatus:
        """Authorize and mutate a task row already locked by the caller.

        Lease-closing callers must keep the global capacity-to-task lock order, so
        this primitive deliberately does not acquire a lock of its own.
        """
        set_current = current_run_id is not None or current_fence is not None
        if clear_current and set_current:
            raise StoreError("task transition cannot clear and set a lease")
        if set_current and (current_run_id is None or current_fence is None):
            raise StoreError("task transition requires a complete lease pointer")
        decision = authorize_transition(current, target, command)
        if decision.code != "allowed":
            raise TransitionError("task transition denied")
        update_accounting = accounting_blocked is not None
        cursor.execute(
            """UPDATE factory.tasks SET state=%s,
            current_run_id=CASE WHEN %s::boolean THEN NULL::uuid
              WHEN %s::boolean THEN %s::uuid ELSE current_run_id END,
            current_fence=CASE WHEN %s::boolean THEN NULL::bigint
              WHEN %s::boolean THEN %s::bigint ELSE current_fence END,
            terminal_at=CASE WHEN %s::boolean THEN clock_timestamp() ELSE terminal_at END,
            accounting_blocked=CASE WHEN %s::boolean THEN %s::boolean ELSE accounting_blocked END,
            updated_at=clock_timestamp()
            WHERE task_id=%s AND state=%s RETURNING state""",
            (
                target.value,
                clear_current,
                set_current,
                current_run_id,
                clear_current,
                set_current,
                current_fence,
                terminal,
                update_accounting,
                accounting_blocked if accounting_blocked is not None else False,
                task_id,
                current.value,
            ),
        )
        row = cursor.fetchone()
        if row is None:
            raise StoreError("locked task state changed during transition")
        return current

    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise StoreError("database URL is required")
        self.database_url = database_url

    def _connect(
        self,
        *,
        connect_timeout: int | None = None,
        lock_timeout: str | None = None,
        statement_timeout: str | None = None,
        transaction_timeout: str | None = None,
    ):
        import psycopg

        connect_timeout = connect_timeout or self._CONNECT_TIMEOUT_SECONDS
        lock_timeout = lock_timeout or self._MUTATION_LOCK_TIMEOUT
        statement_timeout = statement_timeout or self._MUTATION_STATEMENT_TIMEOUT
        connection = None
        try:
            options = (
                f"-c lock_timeout={lock_timeout} "
                f"-c statement_timeout={statement_timeout}"
            )
            connection = psycopg.connect(
                self.database_url,
                connect_timeout=connect_timeout,
                options=options,
            )
            if transaction_timeout is not None:
                if connection.info.server_version < 170000:
                    raise StoreError("execution recovery requires PostgreSQL 17")
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('transaction_timeout',%s,false)",
                        (transaction_timeout,),
                    )
            with connection.cursor() as cursor:
                cursor.execute("SET search_path=pg_catalog")
                _validate_capability_session(cursor, "factory_runtime", "runtime")
                cursor.execute("SET ROLE factory_runtime")
                cursor.execute("SET search_path=pg_catalog,factory")
                cursor.execute("SELECT current_user,current_setting('search_path')")
                if cursor.fetchone() != ("factory_runtime", "pg_catalog, factory"):
                    raise StoreError("runtime capability unavailable")
        except (
            psycopg.InterfaceError,
            psycopg.OperationalError,
            psycopg.errors.LockNotAvailable,
            psycopg.errors.QueryCanceled,
            psycopg.errors.TransactionTimeout,
        ) as exc:
            if connection is not None:
                connection.close()
            raise StoreUnavailable("database unavailable") from exc
        except Exception:
            if connection is not None:
                connection.close()
            raise
        return connection

    def _set_transaction_bounds(
        self,
        cursor,
        *,
        lock_timeout: str | None = None,
        statement_timeout: str | None = None,
        transaction_timeout: str | None = None,
    ) -> None:
        bounds = (
            lock_timeout or self._MUTATION_LOCK_TIMEOUT,
            statement_timeout or self._MUTATION_STATEMENT_TIMEOUT,
        )
        if transaction_timeout is None:
            cursor.execute(
                "SELECT set_config('lock_timeout',%s,true),"
                "set_config('statement_timeout',%s,true)",
                bounds,
            )
        else:
            cursor.execute(
                "SELECT set_config('lock_timeout',%s,true),"
                "set_config('statement_timeout',%s,true),"
                "set_config('transaction_timeout',%s,true)",
                (*bounds, transaction_timeout),
            )

    @contextmanager
    def _transaction(
        self,
        *,
        connect_timeout: int | None = None,
        lock_timeout: str | None = None,
        statement_timeout: str | None = None,
        transaction_timeout: str | None = None,
    ):
        import psycopg

        try:
            with self._connect(
                connect_timeout=connect_timeout,
                lock_timeout=lock_timeout,
                statement_timeout=statement_timeout,
                transaction_timeout=transaction_timeout,
            ) as connection:
                with connection.transaction(), connection.cursor() as cursor:
                    self._set_transaction_bounds(
                        cursor,
                        lock_timeout=lock_timeout,
                        statement_timeout=statement_timeout,
                        transaction_timeout=transaction_timeout,
                    )
                    yield cursor
        except (StoreUnavailable, IntegrityError):
            raise
        except (psycopg.DataError, psycopg.IntegrityError) as exc:
            raise IntegrityError("database integrity violation") from exc
        except (
            psycopg.InterfaceError,
            psycopg.OperationalError,
            psycopg.errors.LockNotAvailable,
            psycopg.errors.QueryCanceled,
            psycopg.errors.TransactionTimeout,
        ) as exc:
            raise StoreUnavailable("database unavailable") from exc

    def readiness(self) -> dict[str, object]:
        with self._transaction() as cursor:
            cursor.execute(
                "SELECT session_user,current_user,COALESCE(max(version),0) "
                "FROM factory.schema_migrations GROUP BY session_user,current_user"
            )
            session_user, role, version = cursor.fetchone()
            capacity_consistent = self._capacity_consistent(cursor)
            accounting_consistent = self._accounting_consistent(cursor)
            return {
                "status": "ready" if version == len(discover_migrations()) and capacity_consistent and accounting_consistent else "not_ready",
                "session_user": session_user,
                "database_role": role,
                "schema_version": version,
                "capacity_consistent": capacity_consistent,
                "accounting_consistent": accounting_consistent,
            }

    @staticmethod
    def _require_recovery_actor(actor: Actor) -> None:
        if (
            not isinstance(actor, Actor)
            or actor.kind != "operator"
            or "factory:reconcile" not in actor.scopes
            or "*" not in actor.repositories
        ):
            raise AuthorityError("global recovery authority is required")

    @staticmethod
    def _recovery_timeouts(timeout_seconds: float) -> tuple[int, str, str, str]:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds < 3.0
        ):
            raise StoreError("invalid execution recovery timeout")
        bounded_seconds = min(5.0, float(timeout_seconds))
        connect_timeout = 2
        statement_milliseconds = max(
            1, int((bounded_seconds - connect_timeout) * 1000)
        )
        lock_milliseconds = min(500, statement_milliseconds)
        return (
            connect_timeout,
            f"{lock_milliseconds}ms",
            f"{statement_milliseconds}ms",
            f"{statement_milliseconds}ms",
        )

    def _require_single_host_recovery_url(self) -> None:
        from psycopg.conninfo import conninfo_to_dict

        try:
            values = conninfo_to_dict(self.database_url)
        except Exception as exc:
            raise StoreError("invalid execution recovery database URL") from exc
        if values.get("service") or not (
            values.get("host") or values.get("hostaddr")
        ) or any(
            value and "," in value
            for value in (
                values.get("host", ""),
                values.get("hostaddr", ""),
                values.get("port", ""),
            )
        ):
            raise StoreError("execution recovery requires a single database host")

    @staticmethod
    def _recovery_candidate(value) -> ExecutionRecoveryCandidate:
        expected = {
            "task_id",
            "run_id",
            "manifest_digest",
            "workspace_handle",
            "updated_at",
            "source",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise IntegrityError("database recovery candidate shape is invalid")
        return ExecutionRecoveryCandidate(
            value["task_id"],
            value["run_id"],
            value["manifest_digest"].strip(),
            value["workspace_handle"],
            datetime.fromisoformat(value["updated_at"].replace("Z", "+00:00")),
            value["source"],
        )

    @classmethod
    def _recovery_claim(cls, value) -> ExecutionRecoveryClaim:
        if isinstance(value, str):
            value = json.loads(value)
        expected_keys = {
            "task_id",
            "run_id",
            "manifest_digest",
            "workspace_handle",
            "updated_at",
            "claim_token",
            "claim_fence",
            "claim_expires_at",
            "transition",
            "advances_discovery_cursor",
            "source",
        }
        if not isinstance(value, dict) or set(value) != expected_keys:
            raise IntegrityError("database recovery claim shape is invalid")
        candidate = ExecutionRecoveryCandidate(
            value["task_id"],
            value["run_id"],
            value["manifest_digest"],
            value["workspace_handle"],
            datetime.fromisoformat(value["updated_at"].replace("Z", "+00:00")),
            value["source"],
        )
        return ExecutionRecoveryClaim(
            candidate,
            value["claim_token"],
            value["claim_fence"],
            datetime.fromisoformat(
                value["claim_expires_at"].replace("Z", "+00:00")
            ),
            value["transition"],
            value["advances_discovery_cursor"],
        )

    def execution_recovery_candidates(
        self, *, limit: int, cursor: ExecutionRecoveryCursor | None
    ) -> ExecutionRecoveryPage:
        if type(limit) is not int or not 2 <= limit <= 100:
            raise StoreError("invalid execution recovery limit")
        if cursor is not None and not isinstance(cursor, ExecutionRecoveryCursor):
            raise StoreError("invalid execution recovery cursor")
        self._require_single_host_recovery_url()
        with self._transaction(
            connect_timeout=2,
            lock_timeout="500ms",
            statement_timeout="3s",
            transaction_timeout="3s",
        ) as db:
            db.execute(
                "SELECT factory.execution_recovery_candidates(%s,%s,%s)",
                (
                    limit,
                    None if cursor is None else cursor.updated_at,
                    None if cursor is None else cursor.run_id,
                ),
            )
            value = db.fetchone()[0]
            if isinstance(value, str):
                value = json.loads(value)
            if not isinstance(value, dict) or set(value) != {
                "candidates",
                "scanned_through",
                "exhausted",
            }:
                raise IntegrityError("database recovery page shape is invalid")
            raw_cursor = value["scanned_through"]
            scanned_through = None
            if raw_cursor is not None:
                if not isinstance(raw_cursor, dict) or set(raw_cursor) != {
                    "updated_at",
                    "run_id",
                }:
                    raise IntegrityError("database recovery cursor shape is invalid")
                scanned_through = ExecutionRecoveryCursor(
                    datetime.fromisoformat(
                        raw_cursor["updated_at"].replace("Z", "+00:00")
                    ),
                    raw_cursor["run_id"],
                )
            if (
                not isinstance(value["candidates"], list)
                or len(value["candidates"]) > limit
                or type(value["exhausted"]) is not bool
            ):
                raise IntegrityError("database recovery candidates are invalid")
            candidates = tuple(
                self._recovery_candidate(candidate)
                for candidate in value["candidates"]
            )
            if (
                len({candidate.run_id for candidate in candidates})
                != len(candidates)
                or len({candidate.manifest_digest for candidate in candidates})
                != len(candidates)
            ):
                raise IntegrityError("database recovery candidates are duplicated")
            fresh_cursors = tuple(
                candidate.cursor
                for candidate in candidates
                if candidate.source == "fresh"
            )
            if fresh_cursors != tuple(sorted(fresh_cursors)) or (
                cursor is not None
                and any(candidate_cursor <= cursor for candidate_cursor in fresh_cursors)
            ):
                raise IntegrityError("database recovery candidates are unordered")
            return ExecutionRecoveryPage(
                candidates,
                scanned_through,
                value["exhausted"],
            )

    def claim_execution_recovery(
        self,
        candidate: ExecutionRecoveryCandidate,
        actor: Actor,
        *,
        timeout_seconds: float = 5.0,
    ) -> ExecutionRecoveryClaim | ExecutionRecoveryNotDue | None:
        if not isinstance(candidate, ExecutionRecoveryCandidate):
            raise StoreError("invalid execution recovery candidate")
        self._require_recovery_actor(actor)
        self._require_single_host_recovery_url()
        (
            connect_timeout,
            lock_timeout,
            statement_timeout,
            transaction_timeout,
        ) = self._recovery_timeouts(timeout_seconds)
        released_here = False
        with self._transaction(
            connect_timeout=connect_timeout,
            lock_timeout=lock_timeout,
            statement_timeout=statement_timeout,
            transaction_timeout=transaction_timeout,
        ) as db:
            db.execute(
                "SELECT factory.execution_recovery_context(%s,%s,%s,%s,%s)",
                (
                    candidate.task_id,
                    candidate.run_id,
                    candidate.manifest_digest,
                    candidate.workspace_handle,
                    candidate.updated_at,
                ),
            )
            context = db.fetchone()[0]
            if context is None:
                return None
            if isinstance(context, str):
                context = json.loads(context)
            if context in ({"released": True}, {"existing_job": True}):
                context = None
            expected_context = {
                "task_state",
                "current_run_id",
                "current_fence",
                "repair_count",
                "repair_limit",
                "owner",
                "role",
                "fence",
                "expires_at",
                "packet_digest",
                "run_state",
                "run_released",
                "allocation_released",
                "recovery_due",
                "released",
            }
            if context is not None and (
                not isinstance(context, dict) or set(context) != expected_context
            ):
                raise IntegrityError("database recovery context shape is invalid")
            if context is not None and (
                context["released"]
                or context["run_released"]
                or context["allocation_released"]
            ):
                raise IntegrityError("execution recovery release state is inconsistent")
            if context is not None:
                if (
                    context["task_state"] != "leased"
                    or context["current_run_id"] != candidate.run_id
                    or context["current_fence"] != context["fence"]
                    or context["run_state"] != "leased"
                ):
                    return None
                if not context["recovery_due"]:
                    if candidate.source != "fresh":
                        return None
                    return ExecutionRecoveryNotDue(candidate)
                grant = LeaseGrant(
                    candidate.task_id,
                    candidate.run_id,
                    context["owner"],
                    RunRole(context["role"]),
                    context["fence"],
                    datetime.fromisoformat(
                        context["expires_at"].replace("Z", "+00:00")
                    ),
                    context["packet_digest"].strip(),
                )
                failure = (
                    FailureClass.PROVIDER_QUALITY
                    if context["repair_count"] >= context["repair_limit"]
                    else FailureClass.WORKER_LOST
                )
                self._release_locked(
                    db,
                    grant,
                    failure,
                    actor,
                    allow_expired=True,
                )
                db.execute(
                    "UPDATE factory.runs SET state='expired' WHERE run_id=%s",
                    (candidate.run_id,),
                )
                if context["repair_count"] < context["repair_limit"]:
                    db.execute(
                        "UPDATE factory.tasks SET repair_count=repair_count+1 WHERE task_id=%s",
                        (candidate.task_id,),
                    )
                released_here = True
            db.execute(
                "SELECT factory.execution_recovery_claim(%s,%s,%s,%s,%s,%s)",
                (
                    candidate.task_id,
                    candidate.run_id,
                    candidate.manifest_digest,
                    candidate.workspace_handle,
                    candidate.updated_at,
                    30,
                ),
            )
            value = db.fetchone()[0]
            if value is None:
                if released_here:
                    raise StoreError("recovery claim lost after canonical release")
                return None
            claim = self._recovery_claim(value)
            if claim.candidate != candidate:
                raise IntegrityError("database recovery authority mismatch")
            return claim

    def record_execution_cleanup_success(
        self, claim: ExecutionRecoveryClaim, *, timeout_seconds: float = 5.0
    ) -> None:
        if not isinstance(claim, ExecutionRecoveryClaim):
            raise StoreError("invalid execution recovery claim")
        self._require_single_host_recovery_url()
        (
            connect_timeout,
            lock_timeout,
            statement_timeout,
            transaction_timeout,
        ) = self._recovery_timeouts(timeout_seconds)
        with self._transaction(
            connect_timeout=connect_timeout,
            lock_timeout=lock_timeout,
            statement_timeout=statement_timeout,
            transaction_timeout=transaction_timeout,
        ) as db:
            db.execute(
                "SELECT factory.execution_recovery_cleanup_succeeded("
                "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    claim.candidate.task_id,
                    claim.candidate.run_id,
                    claim.candidate.manifest_digest,
                    claim.candidate.workspace_handle,
                    claim.candidate.updated_at,
                    claim.candidate.source,
                    claim.claim_token,
                    claim.claim_fence,
                    claim.transition,
                    claim.advances_discovery_cursor,
                ),
            )
            if not db.fetchone()[0]:
                raise FenceError("stale execution cleanup claim")

    def record_execution_cleanup_failure(
        self, claim: ExecutionRecoveryClaim, *, timeout_seconds: float = 5.0
    ) -> None:
        if not isinstance(claim, ExecutionRecoveryClaim):
            raise StoreError("invalid execution recovery claim")
        self._require_single_host_recovery_url()
        (
            connect_timeout,
            lock_timeout,
            statement_timeout,
            transaction_timeout,
        ) = self._recovery_timeouts(timeout_seconds)
        with self._transaction(
            connect_timeout=connect_timeout,
            lock_timeout=lock_timeout,
            statement_timeout=statement_timeout,
            transaction_timeout=transaction_timeout,
        ) as db:
            db.execute(
                "SELECT factory.execution_recovery_cleanup_failed("
                "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    claim.candidate.task_id,
                    claim.candidate.run_id,
                    claim.candidate.manifest_digest,
                    claim.candidate.workspace_handle,
                    claim.candidate.updated_at,
                    claim.candidate.source,
                    claim.claim_token,
                    claim.claim_fence,
                    claim.transition,
                    claim.advances_discovery_cursor,
                ),
            )
            if not db.fetchone()[0]:
                raise FenceError("stale execution cleanup claim")

    @staticmethod
    def _accounting_consistent(cursor) -> bool:
        cursor.execute(
            """SELECT NOT EXISTS (
            SELECT 1 FROM factory.tasks t
            WHERE (
              t.state IN ('queued','retry','ready_for_human') AND (
                t.accounting_blocked OR t.cost_reserved_micros<>0 OR t.tokens_reserved<>0
                OR t.wall_reserved_seconds<>0 OR EXISTS (
                  SELECT 1 FROM factory.budget_reservations b
                  WHERE b.task_id=t.task_id AND b.released_at IS NULL
                )
              )
            ) OR (
              t.state IN ('superseded','cancelled','dead','needs_human')
              AND NOT t.accounting_blocked AND (
                t.cost_reserved_micros<>0 OR t.tokens_reserved<>0
                OR t.wall_reserved_seconds<>0 OR EXISTS (
                  SELECT 1 FROM factory.budget_reservations b
                  WHERE b.task_id=t.task_id AND b.released_at IS NULL
                )
              )
            ))"""
        )
        return bool(cursor.fetchone()[0])

    @staticmethod
    def _capacity_consistent(cursor) -> bool:
        cursor.execute(
            """SELECT count(*) FILTER (WHERE scope_key IN ('global:reader','global:writer'))=2
            AND bool_and(active_count = CASE
              WHEN scope_key='global:reader' THEN (SELECT count(*) FROM factory.capacity_allocations WHERE role='reader' AND released_at IS NULL)
              WHEN scope_key='global:writer' THEN (SELECT count(*) FROM factory.capacity_allocations WHERE role='writer' AND released_at IS NULL)
              ELSE (SELECT count(*) FROM factory.capacity_allocations
                    WHERE role='reader' AND released_at IS NULL
                    AND repository_id=substring(c.scope_key FROM 12 FOR char_length(c.scope_key)-18))
            END) FROM factory.capacity_counters c"""
        )
        return bool(cursor.fetchone()[0])

    def metrics(self) -> dict[str, dict[str, int]]:
        try:
            with self._connect(
                connect_timeout=2,
                lock_timeout="500ms",
                statement_timeout="3s",
                transaction_timeout="3s",
            ) as connection, connection.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout='5s'")
                cursor.execute("SET LOCAL lock_timeout='500ms'")
                cursor.execute("SET LOCAL transaction_timeout='3s'")
                cursor.execute("SELECT factory.read_combined_metrics_snapshot()")
                snapshot = cursor.fetchone()[0]
                legacy = snapshot["legacy"]
                execution = snapshot["execution"]
                if set(legacy) != {
                    "singleton", "accepted", "superseded", "queued", "retry", "dead",
                    "transition_events", "live_leases", "reclaimed", "fence_rejected",
                    "active_capacity", "cost_reserved_micros", "cost_observed_micros",
                    "tokens_reserved", "tokens_observed", "wall_reserved_seconds",
                    "output_observed_bytes", "accounting_blocked", "active_kills",
                    "reconciliation_runs", "reconciliation_candidates", "repaired",
                } or set(execution) != {
                    "singleton", "execution_claimed", "stage_prepared", "stage_running",
                    "stage_collecting", "stage_completed", "stage_failed",
                    "stage_needs_human", "stage_cancelled", "stage_orphaned",
                    "proposal_note", "proposal_artifact", "proposal_usage",
                    "proposal_terminal", "recovery_claimed", "recovery_orphaned",
                    "recovery_cancelled", "cleanup_succeeded", "cleanup_failed",
                }:
                    raise ValueError("metrics snapshot shape is invalid")
        except Exception as exc:
            raise MetricsUnavailable("metrics snapshot unavailable") from exc
        intake, superseded, queued, retry, dead = (
            legacy["accepted"], legacy["superseded"], legacy["queued"],
            legacy["retry"], legacy["dead"],
        )
        transition_events = legacy["transition_events"]
        live_leases, reclaimed, fence_rejected = (
            legacy["live_leases"], legacy["reclaimed"], legacy["fence_rejected"],
        )
        active_capacity = legacy["active_capacity"]
        reserved_cost, observed_cost = (
            legacy["cost_reserved_micros"], legacy["cost_observed_micros"],
        )
        reserved_tokens, observed_tokens = (
            legacy["tokens_reserved"], legacy["tokens_observed"],
        )
        reserved_wall = legacy["wall_reserved_seconds"]
        observed_output = legacy["output_observed_bytes"]
        blocked, kills = legacy["accounting_blocked"], legacy["active_kills"]
        reconciliation_runs = legacy["reconciliation_runs"]
        reconciliation_candidates = legacy["reconciliation_candidates"]
        repaired = legacy["repaired"]
        execution_claimed = execution["execution_claimed"]
        stage_prepared, stage_running = execution["stage_prepared"], execution["stage_running"]
        stage_collecting, stage_completed = (
            execution["stage_collecting"], execution["stage_completed"],
        )
        stage_failed = execution["stage_failed"]
        stage_needs_human = execution["stage_needs_human"]
        stage_cancelled, stage_orphaned = (
            execution["stage_cancelled"], execution["stage_orphaned"],
        )
        proposal_note, proposal_artifact = (
            execution["proposal_note"], execution["proposal_artifact"],
        )
        proposal_usage, proposal_terminal = (
            execution["proposal_usage"], execution["proposal_terminal"],
        )
        recovery_claimed, recovery_orphaned, recovery_cancelled = (
            execution["recovery_claimed"], execution["recovery_orphaned"],
            execution["recovery_cancelled"],
        )
        cleanup_succeeded, cleanup_failed = (
            execution["cleanup_succeeded"], execution["cleanup_failed"],
        )
        return {
            "factory_intake_and_rejection_outcomes_total": {
                "accepted": intake, "superseded": superseded, "queued": queued, "retry": retry,
                "dead": dead, "transition_events": transition_events,
            },
            "factory_lease_reclaim_and_fence_rejection_total": {
                "live_leases": live_leases, "reclaimed": reclaimed, "fence_rejected": fence_rejected,
            },
            "factory_capacity_budget_kill_and_reconcile_outcomes_total": {
                "active_capacity": active_capacity, "cost_reserved_micros": reserved_cost,
                "cost_observed_micros": observed_cost, "tokens_reserved": reserved_tokens,
                "tokens_observed": observed_tokens, "wall_reserved_seconds": reserved_wall,
                "output_observed_bytes": observed_output, "accounting_blocked": blocked,
                "active_kills": kills, "reconciliation_runs": reconciliation_runs,
                "reconciliation_candidates": reconciliation_candidates, "repaired": repaired,
            },
            "factory_execution_claim_and_stage_outcomes_total": {
                "claimed": execution_claimed,
                "prepared": stage_prepared,
                "running": stage_running,
                "collecting": stage_collecting,
                "completed": stage_completed,
                "failed": stage_failed,
                "needs_human": stage_needs_human,
                "cancelled": stage_cancelled,
                "orphaned": stage_orphaned,
            },
            "factory_execution_protocol_and_proposal_outcomes_total": {
                "note": proposal_note,
                "artifact": proposal_artifact,
                "usage": proposal_usage,
                "terminal": proposal_terminal,
            },
            "factory_execution_orphan_and_cleanup_outcomes_total": {
                "claimed": recovery_claimed,
                "orphaned": recovery_orphaned,
                "cancelled": recovery_cancelled,
                "workspace_released": cleanup_succeeded,
                "cleanup_failed": cleanup_failed,
            },
        }

    def record_fence_rejection(self) -> None:
        with self._transaction(
            connect_timeout=1,
            lock_timeout="100ms",
            statement_timeout="250ms",
        ) as cursor:
            cursor.execute("SELECT factory.increment_fence_rejected()")

    def _command_replay(self, cursor, key: str | None, actor: Actor, action: str, request: dict):
        if key is None:
            return False, None, canonical_digest(request)
        digest = canonical_digest(request)
        cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (key,))
        cursor.execute(
            "SELECT actor_id,action,request_digest,result FROM factory.command_results WHERE idempotency_key=%s",
            (key,),
        )
        row = cursor.fetchone()
        if row is None:
            return False, None, digest
        if (row[0], row[1], row[2].strip()) != (actor.actor_id, action, digest):
            raise StoreError("idempotency key reused with different command")
        return True, row[3], digest

    @staticmethod
    def _record_command(cursor, key: str | None, actor: Actor, action: str, digest: str, correlation: str | None, result: dict) -> None:
        if key is None:
            return
        cursor.execute(
            "INSERT INTO factory.command_results(idempotency_key,actor_id,action,request_digest,correlation_id,result) VALUES (%s,%s,%s,%s,%s,%s::jsonb)",
            (key, actor.actor_id, action, digest, correlation or key, json.dumps(result, sort_keys=True, separators=(",", ":"))),
        )

    @staticmethod
    def _verify_m0_authority(cursor, intake: TaskIntakeV1) -> bool:
        authority = intake.m0_authority
        if authority.observed_at is not None:
            cursor.execute(
                "SELECT factory.m0_observation_valid(%s,%s,%s,%s,%s)",
                (
                    authority.observed_at,
                    authority.check_name,
                    authority.exact_head_sha,
                    intake.repository_id,
                    intake.policy_digest,
                ),
            )
        else:
            cursor.execute(
                "SELECT factory.m0_exception_valid(%s,%s,%s,%s,%s,%s)",
                (
                    authority.bootstrap_exception,
                    authority.issuer,
                    authority.scope,
                    authority.expires_at,
                    intake.repository_id,
                    intake.policy_digest,
                ),
            )
        return bool(cursor.fetchone()[0])

    @staticmethod
    def _projection(row) -> TaskProjection:
        return TaskProjection(str(row[0]), row[1], TaskStatus(row[2]), row[3], row[4].strip(), row[5].strip(), row[6])

    @staticmethod
    def _task_select() -> str:
        return "SELECT t.task_id,t.repository_id,t.state,t.generation,i.intent_digest,t.packet_digest,t.deadline_at FROM factory.tasks t JOIN factory.accepted_intents i ON i.intent_id=t.intent_id"

    @staticmethod
    def _intake_command_key(request_id: str) -> str:
        return canonical_digest(
            {
                "contract": "adaptive-factory.intake-command/v1",
                "request_id": request_id,
            }
        )

    @staticmethod
    def _intake_command_result(result: IntakeResult) -> dict:
        return {
            "task_id": result.task.task_id,
            "repository_id": result.task.repository_id,
            "status": result.task.status.value,
            "generation": result.task.generation,
            "intent_digest": result.task.intent_digest,
            "packet_digest": result.task.packet_digest,
            "deadline_at": result.task.deadline_at.isoformat().replace("+00:00", "Z"),
            "created": result.created,
        }

    @staticmethod
    def _intake_result_from_command(result: dict) -> IntakeResult:
        expected = {
            "task_id",
            "repository_id",
            "status",
            "generation",
            "intent_digest",
            "packet_digest",
            "deadline_at",
            "created",
        }
        try:
            if set(result) != expected or type(result["created"]) is not bool:
                raise ValueError("invalid shape")
            if type(result["generation"]) is not int or result["generation"] < 1:
                raise ValueError("invalid generation")
            if not HEX64.fullmatch(result["intent_digest"]) or not HEX64.fullmatch(
                result["packet_digest"]
            ):
                raise ValueError("invalid digest")
            deadline = datetime.fromisoformat(result["deadline_at"].replace("Z", "+00:00"))
            if deadline.tzinfo is None:
                raise ValueError("invalid deadline")
            task = TaskProjection(
                str(uuid.UUID(result["task_id"])),
                result["repository_id"],
                TaskStatus(result["status"]),
                result["generation"],
                result["intent_digest"],
                result["packet_digest"],
                deadline,
            )
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise StoreError("stored intake command result is invalid") from exc
        return IntakeResult(task, result["created"])

    def _event(
        self, cursor, task_id: str, actor: Actor, action: str, idempotency_key: str,
        metadata: dict | None = None, *, mandatory_cleanup: bool = False,
    ) -> None:
        cursor.execute(
            """SELECT t.event_limit,
            count(e.event_id) FILTER (WHERE NOT e.mandatory_cleanup),
            COALESCE(max(e.event_sequence),0)
            FROM factory.tasks t LEFT JOIN factory.task_events e ON e.task_id=t.task_id
            WHERE t.task_id=%s GROUP BY t.event_limit""",
            (task_id,),
        )
        event_limit, ordinary_count, previous_sequence = cursor.fetchone()
        if not mandatory_cleanup and ordinary_count >= event_limit:
            raise BudgetError("event budget exceeded")
        sequence = previous_sequence + 1
        cursor.execute(
            "INSERT INTO factory.task_events(event_id,task_id,event_sequence,idempotency_key,actor_id,action,metadata,mandatory_cleanup) VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s) ON CONFLICT(task_id,idempotency_key) DO NOTHING",
            (
                uuid.uuid4(),
                task_id,
                sequence,
                idempotency_key,
                actor.actor_id,
                action,
                json.dumps(metadata or {}, separators=(",", ":")),
                mandatory_cleanup,
            ),
        )

    @staticmethod
    def _ordinary_event_capacity_available(cursor, task_id: str) -> bool:
        cursor.execute(
            """SELECT count(e.event_id) FILTER (WHERE NOT e.mandatory_cleanup) < t.event_limit
            FROM factory.tasks t LEFT JOIN factory.task_events e ON e.task_id=t.task_id
            WHERE t.task_id=%s GROUP BY t.event_limit""",
            (task_id,),
        )
        row = cursor.fetchone()
        return bool(row and row[0])

    def _audit(
        self,
        cursor,
        task_id: str,
        actor: Actor,
        action: str,
        resource: str,
        reason: str,
        correlation_id: str,
        metadata: dict | None = None,
        run_id: str | None = None,
    ) -> None:
        cursor.execute("SELECT last_digest FROM factory.audit_heads WHERE task_id=%s FOR UPDATE", (task_id,))
        row = cursor.fetchone()
        previous = row[0].strip() if row else "0" * 64
        if row is None:
            cursor.execute("INSERT INTO factory.audit_heads(task_id,last_digest) VALUES (%s,%s)", (task_id, previous))
        cursor.execute("SELECT clock_timestamp()")
        received_at = cursor.fetchone()[0]
        bounded = metadata or {}
        digest = canonical_digest(
            {
                "digest_version": 2,
                "previous_digest": previous,
                "task_id": task_id,
                "run_id": run_id,
                "correlation_id": correlation_id,
                "actor": actor.actor_id,
                "action": action,
                "resource": resource,
                "reason": reason,
                "received_at": received_at,
                "metadata_digest": canonical_digest(bounded),
            }
        )
        cursor.execute(
            "INSERT INTO factory.audit_log(task_id,run_id,previous_digest,current_digest,actor_id,action,resource,reason,correlation_id,metadata,created_at,digest_version) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,2)",
            (
                task_id,
                run_id,
                previous,
                digest,
                actor.actor_id,
                action,
                resource,
                reason,
                correlation_id,
                json.dumps(bounded, separators=(",", ":")),
                received_at,
            ),
        )
        cursor.execute("UPDATE factory.audit_heads SET last_digest=%s WHERE task_id=%s", (digest, task_id))

    def intake(
        self,
        intake: TaskIntakeV1,
        actor: Actor,
        now: datetime,
        *,
        correlation_id: str | None = None,
    ) -> IntakeResult:
        with self._transaction() as cursor:
            audit_correlation = correlation_id or intake.request_id
            command_key = self._intake_command_key(intake.request_id)
            replay, prior, request_digest = self._command_replay(
                cursor,
                command_key,
                actor,
                "intake",
                intake.to_dict(),
            )
            if replay:
                return self._intake_result_from_command(prior)
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                (f"{intake.repository_id}\x1f{intake.source_type}\x1f{intake.source_id}",),
            )
            repair_source_candidate = (
                intake.source_type == "api"
                and HEX64.fullmatch(intake.source_id) is not None
            )
            repair_intake_status = "ordinary"
            if repair_source_candidate:
                cursor.execute(
                    """SELECT factory.semantic_repair_intake_status(
                    %s,%s,%s,%s,%s,%s,%s)""",
                    (
                        intake.repository_id,
                        intake.source_type,
                        intake.source_id,
                        intake.source_digest,
                        intake.governance.exact_head_sha,
                        actor.kind,
                        actor.actor_id,
                    ),
                )
                repair_intake_status = cursor.fetchone()[0]
                if repair_intake_status == "digest_mismatch":
                    raise StoreError("repair proposal source digest mismatch")
                if repair_intake_status == "actor_mismatch":
                    raise StoreError(
                        "repair proposal source requires the exact repair child broker"
                    )
                if repair_intake_status == "not_pending":
                    raise StoreError(
                        "repair child broker source is not a pending proposal"
                    )
                if repair_intake_status == "head_mismatch":
                    raise StoreError(
                        "repair child intake head does not match proposal parent head"
                    )
                if repair_intake_status not in {"allowed", "bound"}:
                    if repair_intake_status != "ordinary":
                        raise StoreError("repair child intake is not authorized")
                if repair_intake_status in {"allowed", "bound"} and (
                    intake.m0_authority.exact_head_sha
                    != intake.governance.exact_head_sha
                ):
                    raise StoreError(
                        "repair child intake head does not match proposal parent head"
                    )
            if not self._verify_m0_authority(cursor, intake):
                raise AuthorityError("M0 authority is not trusted for repository/policy/action")
            cursor.execute(
                "INSERT INTO factory.intake_identities(repository_id,source_type,source_id) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                (intake.repository_id, intake.source_type, intake.source_id),
            )
            cursor.execute(
                self._task_select() + " WHERE i.idempotency_key=%s ORDER BY t.generation DESC LIMIT 1",
                (intake.idempotency_key,),
            )
            duplicate = cursor.fetchone()
            if duplicate:
                result = IntakeResult(self._projection(duplicate), False)
                self._record_command(
                    cursor,
                    command_key,
                    actor,
                    "intake",
                    request_digest,
                    audit_correlation,
                    self._intake_command_result(result),
                )
                return result
            if repair_intake_status == "bound":
                raise StoreError("bound repair proposal source cannot be superseded")
            cursor.execute(
                "SELECT task_id FROM factory.tasks WHERE repository_id=%s AND source_type=%s AND source_id=%s AND state NOT IN ('ready_for_human','dead','cancelled','superseded')",
                (intake.repository_id, intake.source_type, intake.source_id),
            )
            old_ids = [str(row[0]) for row in cursor.fetchall()]
            for old_id in old_ids:
                terminalization = self._terminalize_task(cursor, old_id, TaskStatus.SUPERSEDED)
                if not terminalization.changed:
                    continue
                cursor.execute("SET LOCAL lock_timeout='500ms'")
                cursor.execute("SET LOCAL transaction_timeout='3s'")
                cursor.execute(
                    "SELECT factory.execution_recovery_cancel_task(%s)", (old_id,)
                )
                execution_projection = cursor.fetchone()[0]
                if execution_projection not in {
                    "cancelled",
                    "no_execution",
                    "already_terminal",
                }:
                    raise StoreError("execution supersede projection failed")
                key = canonical_digest({"action": "superseded", "replacement": intake.intent_digest})
                metadata = {
                    "replacement_intent_digest": intake.intent_digest,
                    "accounting_quarantined": terminalization.accounting_quarantined,
                    "from_state": terminalization.from_state.value,
                    "target": TaskStatus.SUPERSEDED.value,
                    "operation": terminalization.operation.value,
                }
                self._event(
                    cursor, old_id, actor, "superseded", key,
                    metadata, mandatory_cleanup=True,
                )
                self._audit(
                    cursor,
                    old_id,
                    actor,
                    "superseded",
                    f"task:{old_id}",
                    "frozen_input_changed",
                    audit_correlation,
                    metadata,
                )
            cursor.execute(
                "SELECT COALESCE(max(generation),0)+1 FROM factory.tasks WHERE repository_id=%s AND source_type=%s AND source_id=%s",
                (intake.repository_id, intake.source_type, intake.source_id),
            )
            generation = cursor.fetchone()[0]
            intent_id, task_id = uuid.uuid4(), uuid.uuid4()
            body = json.dumps(intake.to_dict(), sort_keys=True, separators=(",", ":"))
            cursor.execute(
                """INSERT INTO factory.accepted_intents(intent_id,intent_digest,idempotency_key,repository_id,source_type,source_id,source_digest,exact_base_sha,spec_digest,architecture_digest,governance_digest,policy_digest,body)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
                (
                    intent_id,
                    intake.intent_digest,
                    intake.idempotency_key,
                    intake.repository_id,
                    intake.source_type,
                    intake.source_id,
                    intake.source_digest,
                    intake.exact_base_sha,
                    intake.spec_digest,
                    intake.architecture.architecture_digest,
                    intake.governance.governance_digest,
                    intake.policy_digest,
                    body,
                ),
            )
            cursor.execute(
                """INSERT INTO factory.tasks(
                task_id,intent_id,repository_id,source_type,source_id,state,generation,
                packet_digest,deadline_at,cost_limit_micros,token_limit,
                output_limit_bytes,event_limit,repair_limit,wall_limit_seconds,
                infrastructure_retries,intake_actor_kind,intake_actor_id)
                VALUES (%s,%s,%s,%s,%s,'queued',%s,%s,
                now()+(%s * interval '1 second'),%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING deadline_at""",
                (
                    task_id,
                    intent_id,
                    intake.repository_id,
                    intake.source_type,
                    intake.source_id,
                    generation,
                    intake.intent_digest,
                    intake.limits.wall_seconds,
                    intake.limits.max_cost_usd_micros,
                    intake.limits.max_token_units,
                    intake.limits.max_output_bytes,
                    intake.limits.max_events,
                    intake.limits.semantic_repairs,
                    intake.limits.wall_seconds,
                    intake.limits.infrastructure_retries,
                    actor.kind,
                    actor.actor_id,
                ),
            )
            deadline = cursor.fetchone()[0]
            self._event(
                cursor, str(task_id), actor, "intake_queued", intake.idempotency_key, {"generation": generation}
            )
            self._audit(
                cursor,
                str(task_id),
                actor,
                "intake",
                f"task:{task_id}",
                "accepted",
                audit_correlation,
                {"intent_digest": intake.intent_digest},
            )
            result = IntakeResult(
                TaskProjection(
                    str(task_id),
                    intake.repository_id,
                    TaskStatus.QUEUED,
                    generation,
                    intake.intent_digest,
                    intake.intent_digest,
                    deadline,
                ),
                True,
            )
            self._record_command(
                cursor,
                command_key,
                actor,
                "intake",
                request_digest,
                audit_correlation,
                self._intake_command_result(result),
            )
            return result

    def get_task(self, task_id: str) -> TaskProjection:
        with self._transaction() as cursor:
            return self._get_task(cursor, task_id)

    def _get_task(self, cursor, task_id: str) -> TaskProjection:
        cursor.execute(self._task_select() + " WHERE t.task_id=%s", (task_id,))
        row = cursor.fetchone()
        if not row:
            raise KeyError(task_id)
        return self._projection(row)

    def list_tasks(
        self, *, repository_id: str | None = None, limit: int = 100, cursor_task_id: str | None = None
    ) -> tuple[TaskProjection, ...]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        conditions, params = [], []
        if repository_id:
            conditions.append("t.repository_id=%s")
            params.append(repository_id)
        if cursor_task_id:
            conditions.append("t.task_id>%s")
            params.append(cursor_task_id)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        with self._transaction() as db:
            db.execute(self._task_select() + where + " ORDER BY t.task_id LIMIT %s", (*params, limit))
            return tuple(self._projection(row) for row in db.fetchall())

    def list_task_runs(
        self,
        task_id: str,
        *,
        limit: int,
        cursor_run_id: str | None,
        authorize_repository: Callable[[str], None] | None = None,
    ) -> FactoryRunHistoryPageV1:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        if cursor_run_id is not None:
            try:
                cursor_run_id = self._history_uuid(cursor_run_id)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid run cursor") from exc
        with self._transaction() as cursor:
            task = self._get_task(cursor, task_id)
            if authorize_repository is not None:
                authorize_repository(task.repository_id)
            cursor_fence = 0
            if cursor_run_id is not None:
                cursor.execute(
                    "SELECT fence FROM factory.runs WHERE task_id=%s AND run_id=%s",
                    (task_id, cursor_run_id),
                )
                cursor_row = cursor.fetchone()
                if cursor_row is None:
                    raise ValueError("invalid run cursor")
                cursor_fence = cursor_row[0]
            cursor.execute(
                """WITH page AS MATERIALIZED (
                  SELECT run_id,task_id,owner_id,role,packet_digest,fence,state,
                    lease_expires_at,deadline_at,created_at,released_at
                  FROM factory.runs
                  WHERE task_id=%s AND fence>%s
                  ORDER BY fence
                  LIMIT %s
                )
                SELECT p.run_id,p.task_id,p.owner_id,p.role,p.packet_digest,p.fence,p.state,
                  p.lease_expires_at,p.deadline_at,p.created_at,p.released_at,
                  a.attempt_id,a.task_id,a.run_id,a.attempt_no,a.failure_class,
                  a.failure_code,a.failure_digest,a.created_at,a.finished_at
                FROM page p LEFT JOIN factory.attempts a ON a.run_id=p.run_id
                ORDER BY p.fence,a.attempt_no,a.attempt_id""",
                (task_id, cursor_fence, limit + 1),
            )
            rows = cursor.fetchall()

        try:
            grouped: dict[str, list] = {}
            order: list[str] = []
            for row in rows:
                run_id = self._history_uuid(row[0])
                if run_id not in grouped:
                    grouped[run_id] = []
                    order.append(run_id)
                grouped[run_id].append(row)
            if any(
                len(grouped[run_id]) != 1 or grouped[run_id][0][11] is None
                for run_id in order
            ):
                raise ValueError("one attempt per run required")

            all_items = tuple(
                self._run_attempt_snapshot(grouped[run_id][0], task_id)
                for run_id in order
            )
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise StoreUnavailable("run attempt history invariant failed") from exc

        has_more = len(all_items) > limit
        items = all_items[:limit]
        next_cursor = items[-1].run.run_id if has_more else None
        return FactoryRunHistoryPageV1(items, next_cursor)

    def list_task_events(
        self,
        task_id: str,
        *,
        limit: int,
        cursor_sequence: int | None,
        authorize_repository: Callable[[str], None] | None = None,
    ) -> FactoryEventHistoryPageV1:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        if (
            cursor_sequence is not None
            and (
                type(cursor_sequence) is not int
                or not 0 <= cursor_sequence <= 9_223_372_036_854_775_807
            )
        ):
            raise ValueError("cursor must be nonnegative")
        with self._transaction() as cursor:
            task = self._get_task(cursor, task_id)
            if authorize_repository is not None:
                authorize_repository(task.repository_id)
            cursor.execute(
                """SELECT event_id,task_id,event_sequence,idempotency_key,actor_id,action,
                  metadata,mandatory_cleanup,created_at
                FROM factory.task_events
                WHERE task_id=%s AND event_sequence>%s
                ORDER BY event_sequence
                LIMIT %s""",
                (task_id, cursor_sequence or 0, limit + 1),
            )
            rows = cursor.fetchall()
        try:
            all_items = tuple(
                self._event_snapshot(row, task_id)
                for row in rows
            )
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise StoreUnavailable("event history invariant failed") from exc
        has_more = len(all_items) > limit
        items = all_items[:limit]
        next_cursor = items[-1].event_sequence if has_more else None
        return FactoryEventHistoryPageV1(items, next_cursor)

    @staticmethod
    def _history_uuid(value) -> str:
        parsed = str(uuid.UUID(str(value)))
        if str(value) != parsed:
            raise ValueError("noncanonical UUID")
        return parsed

    @staticmethod
    def _history_datetime(value, *, nullable: bool = False) -> datetime | None:
        if value is None and nullable:
            return None
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timezone-aware timestamp required")
        return value

    @staticmethod
    def _history_text(value, *, maximum: int = 128) -> str:
        if (
            not isinstance(value, str)
            or not value
            or len(value.encode("utf-8")) > maximum
            or any(ord(character) < 32 for character in value)
        ):
            raise ValueError("invalid history text")
        return value

    @staticmethod
    def _history_digest(value) -> str:
        if not isinstance(value, str):
            raise ValueError("invalid history digest")
        value = value.strip()
        if not HEX64.fullmatch(value):
            raise ValueError("invalid history digest")
        return value

    @classmethod
    def _run_attempt_snapshot(cls, row, requested_task_id: str) -> FactoryRunAttemptV1:
        run_id = cls._history_uuid(row[0])
        run_task_id = cls._history_uuid(row[1])
        attempt_id = cls._history_uuid(row[11])
        attempt_task_id = cls._history_uuid(row[12])
        attempt_run_id = cls._history_uuid(row[13])
        if (
            run_task_id != requested_task_id
            or attempt_task_id != requested_task_id
            or attempt_run_id != run_id
        ):
            raise ValueError("history identity mismatch")
        fence, attempt_no = row[5], row[14]
        if type(fence) is not int or not 1 <= fence <= 9_223_372_036_854_775_807:
            raise ValueError("invalid run fence")
        if type(attempt_no) is not int or not 1 <= attempt_no <= 3:
            raise ValueError("invalid attempt number")
        failure_evidence = row[15:18]
        if not (all(value is None for value in failure_evidence) or all(value is not None for value in failure_evidence)):
            raise ValueError("partial attempt failure evidence")
        failure_class = FailureClass(row[15]) if row[15] is not None else None
        failure_code = cls._history_text(row[16]) if row[16] is not None else None
        failure_digest = cls._history_digest(row[17]) if row[17] is not None else None
        run = FactoryRunV1(
            run_id=run_id,
            task_id=run_task_id,
            owner=cls._history_text(row[2]),
            role=RunRole(row[3]),
            packet_digest=cls._history_digest(row[4]),
            fence=fence,
            state=RunStatus(row[6]),
            lease_expires_at=cls._history_datetime(row[7]),
            deadline_at=cls._history_datetime(row[8]),
            created_at=cls._history_datetime(row[9]),
            released_at=cls._history_datetime(row[10], nullable=True),
        )
        attempt = FactoryAttemptV1(
            attempt_id=attempt_id,
            task_id=attempt_task_id,
            run_id=attempt_run_id,
            attempt_no=attempt_no,
            failure_class=failure_class,
            failure_code=failure_code,
            failure_digest=failure_digest,
            created_at=cls._history_datetime(row[18]),
            finished_at=cls._history_datetime(row[19], nullable=True),
        )
        return FactoryRunAttemptV1(run, attempt)

    @classmethod
    def _validate_event_metadata(cls, metadata: Mapping[str, object]) -> None:
        allowed = {
            "generation",
            "run_id",
            "fence",
            "role",
            "attempts",
            "infrastructure_retries",
            "replacement_intent_digest",
            "accounting_quarantined",
            "from_state",
            "target",
            "reason",
            "operation",
        }
        if set(metadata) - allowed:
            raise ValueError("event metadata contains an unknown field")
        if "generation" in metadata and (
            type(metadata["generation"]) is not int
            or not 1 <= metadata["generation"] <= 2_147_483_647
        ):
            raise ValueError("invalid event generation")
        if "run_id" in metadata:
            cls._history_uuid(metadata["run_id"])
        if "fence" in metadata and (
            type(metadata["fence"]) is not int
            or not 1 <= metadata["fence"] <= 9_223_372_036_854_775_807
        ):
            raise ValueError("invalid event fence")
        if "role" in metadata:
            RunRole(metadata["role"])
        for name, maximum in (("attempts", 3), ("infrastructure_retries", 2)):
            if name in metadata and (
                type(metadata[name]) is not int
                or not 0 <= metadata[name] <= maximum
            ):
                raise ValueError(f"invalid event {name}")
        if "replacement_intent_digest" in metadata:
            cls._history_digest(metadata["replacement_intent_digest"])
        if "accounting_quarantined" in metadata and type(
            metadata["accounting_quarantined"]
        ) is not bool:
            raise ValueError("invalid accounting quarantine marker")
        for name in ("from_state", "target"):
            if name in metadata:
                TaskStatus(metadata[name])
        if "reason" in metadata:
            cls._history_text(metadata["reason"])
        if "operation" in metadata:
            TransitionOperation(metadata["operation"])

    @classmethod
    def _event_snapshot(cls, row, requested_task_id: str) -> FactoryEventV1:
        event_id = cls._history_uuid(row[0])
        event_task_id = cls._history_uuid(row[1])
        if event_task_id != requested_task_id:
            raise ValueError("event task mismatch")
        sequence = row[2]
        if type(sequence) is not int or not 1 <= sequence <= 9_223_372_036_854_775_807:
            raise ValueError("invalid event sequence")
        if not isinstance(row[6], Mapping):
            raise ValueError("event metadata must be an object")
        cls._validate_event_metadata(row[6])
        if type(row[7]) is not bool:
            raise ValueError("invalid mandatory cleanup marker")
        return FactoryEventV1(
            event_id=event_id,
            task_id=event_task_id,
            event_sequence=sequence,
            idempotency_key=cls._history_digest(row[3]),
            actor_id=cls._history_text(row[4]),
            action=cls._history_text(row[5]),
            metadata=row[6],
            mandatory_cleanup=row[7],
            created_at=cls._history_datetime(row[8]),
        )

    def verify_audit_chain(self, task_id: str) -> bool:
        with self._transaction() as cursor:
            cursor.execute(
                """SELECT previous_digest,current_digest,task_id,run_id,correlation_id,actor_id,action,resource,reason,created_at,metadata,digest_version
                FROM factory.audit_log WHERE task_id=%s ORDER BY audit_id LIMIT 100001""",
                (task_id,),
            )
            rows = cursor.fetchall()
            if not rows or len(rows) > 100_000:
                return False
            previous = "0" * 64
            for row in rows:
                recorded_previous, recorded_current, stored_task_id, run_id, correlation_id, actor, action, resource, reason, received_at, metadata, digest_version = row
                if recorded_previous.strip() != previous:
                    return False
                envelope = {
                    "previous_digest": previous,
                    "actor": actor,
                    "action": action,
                    "resource": resource,
                    "reason": reason,
                    "received_at": received_at,
                    "metadata_digest": canonical_digest(metadata),
                }
                if digest_version == 2:
                    envelope.update(
                        {
                            "digest_version": 2,
                            "task_id": str(stored_task_id),
                            "run_id": str(run_id) if run_id is not None else None,
                            "correlation_id": correlation_id,
                        }
                    )
                expected = canonical_digest(envelope)
                if recorded_current.strip() != expected:
                    return False
                previous = expected
            cursor.execute("SELECT last_digest FROM factory.audit_heads WHERE task_id=%s", (task_id,))
            head = cursor.fetchone()
            return bool(head and head[0].strip() == previous)

    def _is_killed(self, cursor, repositories: tuple[str, ...]) -> bool:
        scopes = ("global",) + tuple(f"repository:{item}" for item in repositories)
        cursor.execute(
            "SELECT bool_or(enabled) FROM (SELECT DISTINCT ON (scope_key) scope_key,enabled FROM factory.kill_switches WHERE scope_key=ANY(%s) ORDER BY scope_key,created_at DESC,switch_id DESC) current",
            (list(scopes),),
        )
        return bool(cursor.fetchone()[0])

    def claim(self, request, actor: Actor, now: datetime, *, idempotency_key: str | None = None, correlation_id: str | None = None) -> LeaseGrant | None:
        if actor.kind != "worker" or request.owner != actor.actor_id:
            raise StoreError("claim owner must match worker actor")
        with self._transaction() as cursor:
            command = {
                "owner": request.owner,
                "role": request.role.value,
                "repositories": list(request.repositories),
                "lease_seconds": request.lease_seconds,
            }
            replay, prior, request_digest = self._command_replay(cursor, idempotency_key, actor, "claim", command)
            if replay:
                value = prior["grant"]
                if value is None:
                    return None
                return LeaseGrant(
                    value["task_id"], value["run_id"], value["owner"], RunRole(value["role"]), value["fence"],
                    datetime.fromisoformat(value["expires_at"].replace("Z", "+00:00")), value["packet_digest"]
                )
            def no_grant() -> None:
                self._record_command(
                    cursor, idempotency_key, actor, "claim", request_digest, correlation_id, {"grant": None}
                )
                return None
            if self._is_killed(cursor, request.repositories):
                return no_grant()
            cursor.execute(
                "SELECT * FROM factory.capacity_eligible_repositories(%s,%s)",
                (request.role.value, list(request.repositories)),
            )
            eligible_repositories = tuple(row[0] for row in cursor.fetchall())
            if not eligible_repositories:
                return no_grant()
            cursor.execute(
                """SELECT t.task_id,t.repository_id,t.packet_digest,t.deadline_at,t.infrastructure_retries,t.state
                FROM factory.tasks t WHERE t.state IN ('queued','retry') AND t.repository_id=ANY(%s)
                AND t.deadline_at>clock_timestamp() AND NOT t.accounting_blocked
                AND t.cost_reserved_micros=0 AND t.tokens_reserved=0 AND t.wall_reserved_seconds=0
                AND NOT EXISTS (SELECT 1 FROM factory.budget_reservations b
                  WHERE b.task_id=t.task_id AND b.released_at IS NULL)
                AND factory.semantic_task_claimable(
                  t.task_id,t.intent_id,t.intake_actor_kind,t.intake_actor_id,
                  %s,%s
                )
                ORDER BY t.created_at,t.task_id FOR UPDATE SKIP LOCKED LIMIT 1""",
                (list(eligible_repositories), request.owner, request.role.value),
            )
            row = cursor.fetchone()
            if not row:
                return no_grant()
            task_id, repository_id, packet_digest, deadline, infrastructure_retries, task_state = row
            current = TaskStatus(task_state)
            cursor.execute("SELECT COALESCE(max(attempt_no),0)+1 FROM factory.attempts WHERE task_id=%s", (task_id,))
            attempt_no = cursor.fetchone()[0]
            if attempt_no > infrastructure_retries + 1:
                completed_attempts = attempt_no - 1
                evidence = {
                    "attempts": completed_attempts,
                    "infrastructure_retries": infrastructure_retries,
                    "from_state": current.value,
                    "target": TaskStatus.DEAD.value,
                    "operation": TransitionOperation.RETRY_EXHAUSTED.value,
                }
                key = canonical_digest(
                    {
                        "action": "retry_exhausted",
                        "task_id": str(task_id),
                        **evidence,
                    }
                )
                self._apply_task_transition(
                    cursor,
                    str(task_id),
                    current,
                    TaskStatus.DEAD,
                    TransitionCommand(
                        "control_plane",
                        TaskStatus.DEAD,
                        TransitionOperation.RETRY_EXHAUSTED,
                    ),
                    terminal=True,
                )
                self._event(
                    cursor,
                    str(task_id),
                    actor,
                    "retry_exhausted",
                    key,
                    evidence,
                    mandatory_cleanup=True,
                )
                self._audit(
                    cursor,
                    str(task_id),
                    actor,
                    "claim",
                    f"task:{task_id}",
                    "retry_exhausted",
                    correlation_id or idempotency_key or key,
                    evidence,
                )
                return no_grant()
            cursor.execute(
                "INSERT INTO factory.lease_sequences(task_id,last_fence) VALUES (%s,1) ON CONFLICT(task_id) DO UPDATE SET last_fence=factory.lease_sequences.last_fence+1 RETURNING last_fence",
                (task_id,),
            )
            fence = cursor.fetchone()[0]
            run_id = uuid.uuid4()
            cursor.execute(
                "SELECT LEAST(clock_timestamp()+(%s * interval '1 second'),%s)", (request.lease_seconds, deadline)
            )
            expires = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO factory.runs(run_id,task_id,owner_id,role,packet_digest,fence,state,lease_expires_at,deadline_at) VALUES (%s,%s,%s,%s,%s,%s,'leased',%s,%s)",
                (run_id, task_id, request.owner, request.role.value, packet_digest, fence, expires, deadline),
            )
            cursor.execute(
                "INSERT INTO factory.attempts(attempt_id,task_id,run_id,attempt_no) VALUES (%s,%s,%s,%s)",
                (uuid.uuid4(), task_id, run_id, attempt_no),
            )
            cursor.execute(
                "SELECT factory.capacity_allocate(%s,%s,%s,%s,%s)",
                (uuid.uuid4(), run_id, task_id, repository_id, request.role.value),
            )
            if not cursor.fetchone()[0]:
                raise StoreError("capacity changed during claim")
            self._apply_task_transition(
                cursor,
                str(task_id),
                current,
                TaskStatus.LEASED,
                TransitionCommand(
                    "control_plane", TaskStatus.LEASED, TransitionOperation.CLAIM
                ),
                current_run_id=str(run_id),
                current_fence=fence,
            )
            key = canonical_digest({"action": "claim", "run_id": str(run_id), "fence": fence})
            metadata = {
                "from_state": current.value,
                "target": TaskStatus.LEASED.value,
                "operation": TransitionOperation.CLAIM.value,
                "run_id": str(run_id),
                "fence": fence,
                "role": request.role.value,
            }
            self._event(
                cursor,
                str(task_id),
                actor,
                "claimed",
                key,
                metadata,
            )
            self._audit(
                cursor,
                str(task_id),
                actor,
                "claim",
                f"run:{run_id}",
                "scheduled",
                correlation_id or idempotency_key or key,
                metadata,
                str(run_id),
            )
            grant = LeaseGrant(
                str(task_id), str(run_id), request.owner, request.role, fence, expires, packet_digest.strip()
            )
            self._record_command(
                cursor, idempotency_key, actor, "claim", request_digest, correlation_id,
                {"grant": {
                    "task_id": grant.task_id, "run_id": grant.run_id, "owner": grant.owner,
                    "role": grant.role.value, "fence": grant.fence,
                    "expires_at": grant.expires_at.isoformat().replace("+00:00", "Z"),
                    "packet_digest": grant.packet_digest,
                }},
            )
            return grant

    def execution_material(self, grant: LeaseGrant) -> dict[str, object]:
        with self._transaction() as cursor:
            self._lock_grant(cursor, grant)
            cursor.execute(
                """SELECT t.repository_id,t.packet_digest,t.deadline_at,i.body
                FROM factory.tasks t JOIN factory.accepted_intents i ON i.intent_id=t.intent_id
                WHERE t.task_id=%s AND t.current_run_id=%s""",
                (grant.task_id, grant.run_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise FenceError("stale or expired fence")
            repository_id, legacy_digest, deadline, body = row
            if isinstance(body, str):
                body = json.loads(body)
            try:
                return {
                    "repository_id": repository_id,
                    "legacy_intent_digest": legacy_digest.strip(),
                    "route_id": body["route_id"],
                    "change_id": body["change_id"],
                    "exact_base_sha": body["exact_base_sha"],
                    "exact_head_sha": body["governance"]["exact_head_sha"],
                    "spec_digest": body["spec_digest"],
                    "architecture_digest": body["architecture"]["architecture_digest"],
                    "governance_digest": body["governance"]["governance_digest"],
                    "policy_digest": body["policy_digest"],
                    "acceptance_ids": body["acceptance_ids"],
                    "limits": body["limits"],
                    "deadline": deadline.isoformat().replace("+00:00", "Z"),
                }
            except (KeyError, TypeError) as exc:
                raise StoreError("accepted intent cannot build an execution packet") from exc

    def start_execution(
        self,
        grant: LeaseGrant,
        packet,
        manifest,
        actor: Actor,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> ExecutionGrant:
        with self._transaction() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            self._lock_grant(cursor, grant)
            command = {
                "run_id": grant.run_id,
                "legacy_packet_digest": grant.packet_digest,
                "execution_packet_digest": packet.packet_digest,
                "manifest_digest": manifest.manifest_digest,
            }
            replay, prior, request_digest = self._command_replay(
                cursor, idempotency_key, actor, "execution_start", command
            )
            if replay:
                return ExecutionGrant(
                    grant,
                    prior["packet_digest"],
                    prior["manifest_digest"],
                    prior["workspace_handle"],
                    prior["provider_id"],
                    ExecutionStage(prior["stage"]),
                )
            cursor.execute(
                "SELECT factory.execution_start(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)",
                (
                    grant.task_id,
                    grant.run_id,
                    grant.owner,
                    grant.fence,
                    grant.packet_digest,
                    packet.packet_digest,
                    manifest.manifest_digest,
                    manifest.workspace_handle,
                    manifest.provider_id,
                    json.dumps(packet.to_dict(), sort_keys=True, separators=(",", ":")),
                    json.dumps(manifest.to_dict(), sort_keys=True, separators=(",", ":")),
                ),
            )
            if not cursor.fetchone()[0]:
                raise FenceError("stale or expired fence")
            result = ExecutionGrant(
                grant,
                packet.packet_digest,
                manifest.manifest_digest,
                manifest.workspace_handle,
                manifest.provider_id,
                ExecutionStage.PREPARED,
            )
            recorded = {
                "packet_digest": result.packet_digest,
                "manifest_digest": result.manifest_digest,
                "workspace_handle": result.workspace_handle,
                "provider_id": result.provider_id,
                "stage": result.stage.value,
            }
            self._record_command(
                cursor,
                idempotency_key,
                actor,
                "execution_start",
                request_digest,
                correlation_id,
                recorded,
            )
            self._audit(
                cursor,
                grant.task_id,
                actor,
                "execution_start",
                f"run:{grant.run_id}",
                "packet_manifest_persisted",
                correlation_id or idempotency_key or packet.packet_digest,
                {"packet_digest": packet.packet_digest, "manifest_digest": manifest.manifest_digest},
                grant.run_id,
            )
            return result

    def advance_execution(
        self,
        grant: LeaseGrant,
        packet_digest: str,
        stage: ExecutionStage,
        actor: Actor,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> ExecutionStage:
        with self._transaction() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            self._lock_grant(cursor, grant)
            command = {"run_id": grant.run_id, "packet_digest": packet_digest, "stage": stage.value}
            replay, prior, request_digest = self._command_replay(
                cursor, idempotency_key, actor, "execution_advance", command
            )
            if replay:
                return ExecutionStage(prior["stage"])
            cursor.execute(
                "SELECT factory.execution_advance(%s,%s,%s,%s,%s,%s,%s)",
                (
                    grant.task_id,
                    grant.run_id,
                    grant.owner,
                    grant.fence,
                    grant.packet_digest,
                    packet_digest,
                    stage.value,
                ),
            )
            if not cursor.fetchone()[0]:
                raise FenceError("stale execution stage or fence")
            self._record_command(
                cursor,
                idempotency_key,
                actor,
                "execution_advance",
                request_digest,
                correlation_id,
                {"stage": stage.value},
            )
            return stage

    def _proposal_context(self, cursor, grant: LeaseGrant, packet_digest: str) -> ProposalContext:
        locked_grant = self._lock_grant(cursor, grant)
        cursor.execute(
            "SELECT factory.execution_proposal_context(%s,%s,%s,%s,%s,%s)",
            (
                grant.task_id, grant.run_id, grant.owner, grant.fence,
                grant.packet_digest, packet_digest,
            ),
        )
        row = cursor.fetchone()
        if row is None or row[0] is None:
            raise FenceError("stale execution packet or terminal manifest")
        body = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        limits = body["limits"]
        return ProposalContext(
            grant.task_id,
            grant.run_id,
            grant.owner,
            grant.fence,
            packet_digest,
            locked_grant[1],
            body["repository_id"],
            body["workspace_handle"],
            tuple(body["capability_policy"]["allowed_paths"]),
            tuple(body["capability_policy"]["artifact_classes"]),
            min(65_536, limits["max_output_bytes"]),
            limits["max_output_bytes"],
            limits["max_output_bytes"],
            limits["max_cost_usd_micros"],
            limits["max_token_units"],
            tuple(body["provider"]["capabilities"]),
        )

    def proposal_context(self, grant: LeaseGrant, packet_digest: str) -> ProposalContext:
        with self._transaction() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            return self._proposal_context(cursor, grant, packet_digest)

    @staticmethod
    def _execution_proposal_command(grant: LeaseGrant, event: CanonicalEvent) -> dict:
        return {
            "contract": "adaptive-factory.execution-propose-command/v1",
            "grant": {
                "task_id": grant.task_id,
                "run_id": grant.run_id,
                "owner": grant.owner,
                "role": grant.role.value,
                "fence": grant.fence,
                "legacy_packet_digest": grant.packet_digest,
            },
            "event": event.to_dict(),
        }

    @staticmethod
    def _proposal_kind(event_type: str) -> str:
        if event_type == "note.proposed":
            return "note"
        if event_type == "artifact.proposed":
            return "artifact"
        if event_type == "usage.reported":
            return "usage"
        if event_type in {"run.completed", "run.failed", "run.needs_human"}:
            return "terminal"
        raise StoreError("unsupported execution proposal")

    @classmethod
    def _stored_execution_proposal(
        cls,
        cursor,
        grant: LeaseGrant,
        event: CanonicalEvent,
        result: dict,
    ):
        if not isinstance(result, dict) or set(result) != {
            "proposal_kind", "sequence", "proposal_idempotency_key"
        }:
            raise StoreError("persisted execution proposal command is corrupt")
        expected_kind = cls._proposal_kind(event.event_type)
        proposal_digest = result["proposal_idempotency_key"]
        if (
            result["proposal_kind"] != expected_kind
            or type(result["sequence"]) is not int
            or result["sequence"] != event.sequence
            or not isinstance(proposal_digest, str)
            or not HEX64.fullmatch(proposal_digest)
        ):
            raise StoreError("persisted execution proposal command is corrupt")
        cursor.execute(
            "SELECT factory.execution_proposal_by_key(%s,%s,%s)",
            (grant.task_id, grant.run_id, proposal_digest),
        )
        envelope = cursor.fetchone()[0]
        if envelope is None:
            raise StoreError("persisted execution proposal is missing")
        if isinstance(envelope, str):
            envelope = json.loads(envelope)
        if not isinstance(envelope, dict) or set(envelope) != {
            "task_id", "run_id", "packet_digest", "producer_sequence", "proposal_kind",
            "idempotency_key", "body",
        }:
            raise StoreError("persisted execution proposal is corrupt")
        task_id = envelope["task_id"]
        run_id = envelope["run_id"]
        packet_digest = envelope["packet_digest"]
        sequence = envelope["producer_sequence"]
        kind = envelope["proposal_kind"]
        stored_digest = envelope["idempotency_key"]
        body = envelope["body"]
        if (
            str(task_id) != grant.task_id
            or str(run_id) != grant.run_id
            or packet_digest != event.packet_digest
            or sequence != event.sequence
            or kind != expected_kind
            or stored_digest != proposal_digest
        ):
            raise StoreError("persisted execution proposal is corrupt")
        classes = {
            "note": NoteProposal,
            "artifact": ArtifactProposal,
            "usage": UsageProposal,
            "terminal": TerminalProposal,
        }
        proposal_type = classes.get(kind)
        if proposal_type is None or not isinstance(body, dict) or set(body) != set(proposal_type.__dataclass_fields__):
            raise StoreError("persisted execution proposal is corrupt")
        try:
            if proposal_type is NoteProposal:
                if not isinstance(body.get("evidence"), list):
                    raise TypeError("invalid persisted evidence")
                body["evidence"] = tuple(body["evidence"])
            proposal = proposal_type(**body)
        except (TypeError, ValueError) as exc:
            raise StoreError("persisted execution proposal is corrupt") from exc
        if (
            proposal.task_id != grant.task_id
            or proposal.run_id != grant.run_id
            or proposal.packet_digest != event.packet_digest
            or proposal.fence != grant.fence
            or proposal.author_role != grant.role.value
            or proposal.sequence != sequence
            or proposal.idempotency_key != stored_digest
            or proposal.idempotency_key != proposal_digest
            or proposal_idempotency_key(proposal) != proposal_digest
            or (
                isinstance(proposal, TerminalProposal)
                and proposal.terminal_type != event.event_type
            )
        ):
            raise StoreError("persisted execution proposal is corrupt")
        return proposal

    def execution_proposal_replay(
        self,
        grant: LeaseGrant,
        event: CanonicalEvent,
        actor: Actor,
        *,
        idempotency_key: str | None,
    ):
        if idempotency_key is None:
            return None
        if (
            actor.kind != "worker"
            or actor.actor_id != grant.owner
            or "task:execute" not in actor.scopes
        ):
            raise StoreError("execution proposal replay requires bound worker actor")
        command = self._execution_proposal_command(grant, event)
        with self._transaction() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            replay, prior, _request_digest = self._command_replay(
                cursor, idempotency_key, actor, "execution_propose", command
            )
            if replay:
                return self._stored_execution_proposal(
                    cursor, grant, event, prior
                )
            self._proposal_context(cursor, grant, event.packet_digest)
            return None

    def begin_execution_terminal_composite(
        self,
        grant: LeaseGrant,
        event: CanonicalEvent,
        actor: Actor,
        *,
        proposal_key: str,
        finalize_key: str,
        idempotency_key: str,
        correlation_id: str | None = None,
    ) -> None:
        if (
            actor.kind != "worker"
            or actor.actor_id != grant.owner
            or "task:execute" not in actor.scopes
            or not isinstance(idempotency_key, str)
            or not HEX64.fullmatch(idempotency_key)
            or event.protocol_version != PROTOCOL_VERSION
            or event.task_id != grant.task_id
            or event.run_id != grant.run_id
            or self._proposal_kind(event.event_type) != "terminal"
        ):
            raise StoreError("invalid execution terminal composite command")
        expected_keys = {
            phase: canonical_digest(
                {
                    "contract": "adaptive-factory.execution-terminal-phase/v1",
                    "command": idempotency_key,
                    "phase": phase,
                }
            )
            for phase in ("proposal", "finalize")
        }
        if (
            proposal_key != expected_keys["proposal"]
            or finalize_key != expected_keys["finalize"]
            or proposal_key == finalize_key
        ):
            raise StoreError("invalid execution terminal phase keys")
        command = {
            "contract": "adaptive-factory.execution-terminal-composite-command/v1",
            "proposal_command": self._execution_proposal_command(grant, event),
            "proposal_key": proposal_key,
            "finalize_key": finalize_key,
        }
        marker = {"proposal_key": proposal_key, "finalize_key": finalize_key}
        with self._transaction() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            replay, prior, request_digest = self._command_replay(
                cursor,
                idempotency_key,
                actor,
                "execution_terminal_composite",
                command,
            )
            if replay:
                if prior != marker:
                    raise IntegrityError("persisted terminal composite marker is corrupt")
                return
            context = self._proposal_context(cursor, grant, event.packet_digest)
            try:
                proposal = ProposalBroker().accept(
                    event,
                    context,
                    owner=grant.owner,
                    fence=grant.fence,
                )
            except BrokerError as exc:
                raise StoreError("execution terminal command semantics are invalid") from exc
            if not isinstance(proposal, TerminalProposal):
                raise StoreError("execution terminal command is not terminal")
            self._record_command(
                cursor,
                idempotency_key,
                actor,
                "execution_terminal_composite",
                request_digest,
                correlation_id,
                marker,
            )

    def commit_execution_proposal(
        self,
        grant: LeaseGrant,
        proposal,
        actor: Actor,
        *,
        event: CanonicalEvent,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ):
        if (
            actor.kind != "worker"
            or actor.actor_id != grant.owner
            or "task:execute" not in actor.scopes
        ):
            raise StoreError("execution proposal commit requires bound worker actor")
        kinds = {
            NoteProposal: "note",
            ArtifactProposal: "artifact",
            UsageProposal: "usage",
            TerminalProposal: "terminal",
        }
        kind = kinds.get(type(proposal))
        if kind is None:
            raise StoreError("unsupported execution proposal")
        expected_kind = self._proposal_kind(event.event_type)
        if (
            kind != expected_kind
            or event.protocol_version != PROTOCOL_VERSION
            or event.task_id != grant.task_id
            or event.run_id != grant.run_id
            or proposal.task_id != grant.task_id
            or proposal.run_id != grant.run_id
            or proposal.packet_digest != event.packet_digest
            or proposal.fence != grant.fence
            or proposal.sequence != event.sequence
            or proposal.author_role != grant.role.value
            or proposal.idempotency_key != proposal_idempotency_key(proposal)
            or (
                isinstance(proposal, TerminalProposal)
                and proposal.terminal_type != event.event_type
            )
        ):
            raise StoreError("execution proposal does not match command")
        body = asdict(proposal)
        command = self._execution_proposal_command(grant, event)
        with self._transaction() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            replay, prior, request_digest = self._command_replay(
                cursor, idempotency_key, actor, "execution_propose", command
            )
            if replay:
                return self._stored_execution_proposal(
                    cursor, grant, event, prior
                )
            context = self._proposal_context(cursor, grant, event.packet_digest)
            attestation_digest = (
                proposal.artifact_attestation_digest
                if isinstance(proposal, ArtifactProposal)
                else None
            )
            try:
                expected_proposal = ProposalBroker().accept(
                    event,
                    context,
                    owner=grant.owner,
                    fence=grant.fence,
                    artifact_attestation_digest=attestation_digest,
                )
            except BrokerError as exc:
                raise StoreError("execution proposal event semantics are invalid") from exc
            if expected_proposal != proposal:
                raise StoreError("execution proposal does not match event semantics")
            cursor.execute(
                "SELECT factory.execution_propose(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
                (
                    grant.task_id, grant.run_id, grant.owner, grant.fence, grant.packet_digest,
                    proposal.packet_digest, proposal.sequence, proposal.idempotency_key, kind,
                    json.dumps(body, sort_keys=True, separators=(",", ":")),
                ),
            )
            if not cursor.fetchone()[0]:
                raise FenceError("stale execution proposal or fence")
            self._record_command(
                cursor, idempotency_key, actor, "execution_propose", request_digest,
                correlation_id, {
                    "proposal_kind": kind,
                    "sequence": proposal.sequence,
                    "proposal_idempotency_key": proposal.idempotency_key,
                },
            )
            return proposal

    @staticmethod
    def _workspace_bundle(value) -> tuple[WorkspaceResultV1, WorkspaceSnapshotV1, TaskPacketV1, RunManifestV1] | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = json.loads(value)
        try:
            packet_wire = dict(value["packet"])
            packet_digest = packet_wire.pop("packet_digest")
            packet = TaskPacketV1.from_dict(packet_wire)
            if packet.packet_digest != packet_digest:
                raise StoreError("stored workspace packet digest mismatch")
            manifest_wire = dict(value["manifest"])
            manifest_digest = manifest_wire.pop("manifest_digest")
            manifest = RunManifestV1.from_packet(packet, deadline=manifest_wire["deadline"])
            if manifest.to_dict() != {**manifest_wire, "manifest_digest": manifest_digest}:
                raise StoreError("stored workspace manifest mismatch")
            result = WorkspaceResultV1.from_dict(value["result"])
            snapshot = WorkspaceSnapshotV1.from_dict(value["snapshot"])
            row = value["row"]
            expected_row = {
                "workspace_result_digest": result.workspace_result_digest,
                "task_id": result.task_id,
                "run_id": result.run_id,
                "task_packet_digest": result.task_packet_digest,
                "run_manifest_digest": result.run_manifest_digest,
                "exact_head_sha": result.exact_head_sha,
                "workspace_snapshot_digest": result.workspace_snapshot_digest,
                "terminal_stage": result.terminal_stage,
                "terminal_proposal_digest": result.terminal_proposal_digest,
                "terminal_proposal_kind": "terminal",
                "artifact_manifest_digest": result.artifact_manifest_digest,
                "note_manifest_digest": result.note_manifest_digest,
                "usage_evidence_digest": result.usage_evidence_digest,
                "diagnostics_digest": result.diagnostics_digest,
                "m4_status": result.m4_status,
                "failure_class": result.failure_class,
                "failure_reason": result.failure_reason,
            }
            if row != expected_row:
                raise StoreError("stored workspace row mismatch")
            if (
                result.task_id != packet.task_id
                or result.run_id != packet.run_id
                or result.task_packet_digest != packet.packet_digest
                or result.run_manifest_digest != manifest.manifest_digest
                or snapshot.repository_id != packet.repository_id
                or snapshot.workspace_handle != packet.workspace_handle
                or snapshot.input_head_sha != packet.authority.exact_head_sha
                or snapshot.result_head_sha != result.exact_head_sha
                or snapshot.workspace_snapshot_digest != result.workspace_snapshot_digest
            ):
                raise StoreError("stored workspace bundle binding mismatch")
            return result, snapshot, packet, manifest
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, StoreError):
                raise
            raise StoreError("stored workspace bundle is corrupt") from exc

    def finalize_execution(
        self,
        grant: LeaseGrant,
        packet_digest: str,
        snapshot: WorkspaceSnapshotV1,
        actor: Actor,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> WorkspaceResultV1:
        command = {
            "task_id": grant.task_id,
            "run_id": grant.run_id,
            "packet_digest": packet_digest,
        }
        with self._transaction() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            replay, prior, request_digest = self._command_replay(
                cursor, idempotency_key, actor, "execution_finalize", command
            )
            if replay:
                cursor.execute(
                    "SELECT factory.execution_result_for_run(%s,%s)",
                    (grant.task_id, grant.run_id),
                )
                bundle = self._workspace_bundle(cursor.fetchone()[0])
                if bundle is None or prior.get("result") != bundle[0].to_dict():
                    raise StoreError("persisted finalization command is corrupt")
                return bundle[0]
            cursor.execute("SELECT factory.execution_result_for_run(%s,%s)", (grant.task_id, grant.run_id))
            existing = self._workspace_bundle(cursor.fetchone()[0])
            if existing is not None:
                result, stored_snapshot, _packet, _manifest = existing
                if (
                    result.task_packet_digest != packet_digest
                    or stored_snapshot.workspace_snapshot_digest != snapshot.workspace_snapshot_digest
                ):
                    raise StoreError("workspace result already exists with different facts")
                self._record_command(
                    cursor, idempotency_key, actor, "execution_finalize", request_digest,
                    correlation_id, {"result": result.to_dict()},
                )
                return result
            cursor.execute(
                "SELECT factory.execution_finalize_context(%s,%s,%s,%s,%s,%s)",
                (
                    grant.task_id, grant.run_id, grant.owner, grant.fence,
                    grant.packet_digest, packet_digest,
                ),
            )
            context = cursor.fetchone()[0]
            if context is None:
                raise FenceError("execution cannot be finalized")
            if isinstance(context, str):
                context = json.loads(context)
            if (
                snapshot.repository_id != context["repository_id"]
                or snapshot.workspace_handle != context["workspace_handle"]
                or snapshot.input_head_sha != context["input_head_sha"]
            ):
                raise FenceError("workspace snapshot does not bind execution")
            result = WorkspaceResultV1.from_facts(
                {
                    "contract_version": 1,
                    "task_id": grant.task_id,
                    "run_id": grant.run_id,
                    "task_packet_digest": packet_digest,
                    "run_manifest_digest": context["run_manifest_digest"],
                    "exact_head_sha": snapshot.result_head_sha,
                    "workspace_snapshot_digest": snapshot.workspace_snapshot_digest,
                    "terminal_stage": context["terminal_stage"],
                    "terminal_proposal_digest": context["terminal_proposal_digest"],
                    "artifact_manifest_digest": workspace_evidence_digest(
                        "artifacts", context["artifact_digests"]
                    ),
                    "note_manifest_digest": workspace_evidence_digest("notes", context["note_digests"]),
                    "usage_evidence_digest": workspace_evidence_digest("usage", context["usage_digests"]),
                    "diagnostics_digest": workspace_evidence_digest(
                        "diagnostics", context["diagnostic_digests"]
                    ),
                    "m4_status": context["m4_status"],
                    "failure_class": context["failure_class"],
                    "failure_reason": context["failure_reason"],
                }
            )
            cursor.execute(
                "SELECT factory.execution_finalize_commit(%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)",
                (
                    grant.task_id, grant.run_id, grant.owner, grant.fence, grant.packet_digest,
                    packet_digest, result.workspace_result_digest,
                    json.dumps(snapshot.to_dict(), sort_keys=True, separators=(",", ":")),
                    json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":")),
                ),
            )
            if not cursor.fetchone()[0]:
                raise FenceError("execution finalization rejected")
            status = TaskStatus(result.m4_status)
            release_key = canonical_digest(
                {
                    "action": "execution_finalize",
                    "fence": grant.fence,
                    "run_id": grant.run_id,
                    "target": status.value,
                }
            )
            self._event(
                cursor,
                grant.task_id,
                actor,
                "released",
                release_key,
                {
                    "target": status.value,
                    "workspace_result_digest": result.workspace_result_digest,
                },
                mandatory_cleanup=True,
            )
            self._audit(
                cursor,
                grant.task_id,
                actor,
                "execution_finalize",
                f"run:{grant.run_id}",
                status.value,
                correlation_id or release_key,
                {
                    "fence": grant.fence,
                    "workspace_result_digest": result.workspace_result_digest,
                },
                grant.run_id,
            )
            self._record_command(
                cursor, idempotency_key, actor, "execution_finalize", request_digest,
                correlation_id, {"result": result.to_dict()},
            )
            return result

    def execution_finalization_replay(
        self,
        grant: LeaseGrant,
        packet_digest: str,
        actor: Actor,
        *,
        idempotency_key: str | None,
    ) -> WorkspaceResultV1 | None:
        if idempotency_key is None:
            return None
        command = {"task_id": grant.task_id, "run_id": grant.run_id, "packet_digest": packet_digest}
        with self._transaction() as cursor:
            replay, prior, _request_digest = self._command_replay(
                cursor, idempotency_key, actor, "execution_finalize", command
            )
            if not replay:
                return None
            cursor.execute(
                "SELECT factory.execution_result_for_run(%s,%s)",
                (grant.task_id, grant.run_id),
            )
            bundle = self._workspace_bundle(cursor.fetchone()[0])
            if bundle is None:
                raise StoreError("persisted finalization result is missing")
            result, _snapshot, _packet, _manifest = bundle
            if prior.get("result") != result.to_dict() or result.task_packet_digest != packet_digest:
                raise StoreError("persisted finalization command is corrupt")
            return result

    def workspace_snapshot_request(self, grant: LeaseGrant, packet_digest: str) -> WorkspaceSnapshotRequest:
        with self._transaction() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            cursor.execute(
                "SELECT factory.execution_finalize_context(%s,%s,%s,%s,%s,%s)",
                (
                    grant.task_id, grant.run_id, grant.owner, grant.fence,
                    grant.packet_digest, packet_digest,
                ),
            )
            context = cursor.fetchone()[0]
            if context is None:
                cursor.execute("SELECT factory.execution_result_for_run(%s,%s)", (grant.task_id, grant.run_id))
                existing = self._workspace_bundle(cursor.fetchone()[0])
                if existing is None:
                    raise FenceError("execution snapshot context unavailable")
                result, snapshot, _packet, _manifest = existing
                return WorkspaceSnapshotRequest(
                    result.task_id,
                    result.run_id,
                    snapshot.repository_id,
                    snapshot.workspace_handle,
                    snapshot.input_head_sha,
                )
            if isinstance(context, str):
                context = json.loads(context)
            return WorkspaceSnapshotRequest(
                grant.task_id,
                grant.run_id,
                context["repository_id"],
                context["workspace_handle"],
                context["input_head_sha"],
            )

    def workspace_result(self, task_id: str, workspace_result_digest: str):
        with self._transaction() as cursor:
            cursor.execute("SET LOCAL statement_timeout='5s'")
            cursor.execute(
                "SELECT factory.execution_result_by_digest(%s,%s)",
                (task_id, workspace_result_digest),
            )
            bundle = self._workspace_bundle(cursor.fetchone()[0])
            if bundle is None:
                raise KeyError(workspace_result_digest)
            result, snapshot, packet, manifest = bundle
            if result.workspace_result_digest != workspace_result_digest:
                raise StoreError("requested workspace result digest mismatch")
            return {"result": result, "snapshot": snapshot, "packet": packet, "manifest": manifest}

    @staticmethod
    def _lock_capacity_for_run(cursor, run_id: str) -> bool:
        cursor.execute("SELECT factory.capacity_lock_run(%s)", (run_id,))
        return bool(cursor.fetchone()[0])

    def _close_active_lease(self, cursor, task_id: str) -> None:
        cursor.execute(
            """SELECT r.run_id,r.role,a.repository_id FROM factory.tasks t
            JOIN factory.runs r ON r.run_id=t.current_run_id
            JOIN factory.capacity_allocations a ON a.run_id=r.run_id
            WHERE t.task_id=%s AND r.released_at IS NULL""",
            (task_id,),
        )
        candidate = cursor.fetchone()
        if candidate is None:
            return
        run_id, _role, _repository_id = candidate
        if not self._lock_capacity_for_run(cursor, str(run_id)):
            return
        cursor.execute(
            """SELECT r.run_id FROM factory.tasks t JOIN factory.runs r ON r.run_id=t.current_run_id
            JOIN factory.capacity_allocations a ON a.run_id=r.run_id
            WHERE t.task_id=%s AND r.run_id=%s AND r.released_at IS NULL FOR UPDATE OF t,r""",
            (task_id, run_id),
        )
        if cursor.fetchone() is None:
            return
        cursor.execute("UPDATE factory.runs SET state='released',released_at=clock_timestamp() WHERE run_id=%s", (run_id,))
        cursor.execute("UPDATE factory.attempts SET finished_at=clock_timestamp() WHERE run_id=%s", (run_id,))
        cursor.execute("SELECT factory.capacity_release(%s)", (run_id,))
        if not cursor.fetchone()[0]:
            raise StoreError("live lease capacity was not released")
        cursor.execute(
            "UPDATE factory.tasks SET current_run_id=NULL,current_fence=NULL WHERE task_id=%s AND current_run_id=%s",
            (task_id, run_id),
        )

    def _terminalize_task(
        self,
        cursor,
        task_id: str,
        target: TaskStatus,
    ) -> TerminalizationResult:
        if target not in {TaskStatus.CANCELLED, TaskStatus.SUPERSEDED}:
            raise StoreError("unsupported terminal transition")
        terminal = tuple(status.value for status in (TaskStatus.READY_FOR_HUMAN, TaskStatus.DEAD, TaskStatus.CANCELLED, TaskStatus.SUPERSEDED))
        operation = (
            TransitionOperation.CANCEL
            if target is TaskStatus.CANCELLED
            else TransitionOperation.SUPERSEDE
        )
        for _attempt in range(3):
            self._close_active_lease(cursor, task_id)
            cursor.execute(
                """SELECT state,accounting_blocked OR cost_reserved_micros<>0
                  OR tokens_reserved<>0 OR wall_reserved_seconds<>0 OR EXISTS (
                    SELECT 1 FROM factory.budget_reservations b
                    WHERE b.task_id=tasks.task_id AND b.released_at IS NULL
                  )
                FROM factory.tasks
                WHERE task_id=%s AND current_run_id IS NULL
                AND state<>ALL(%s) FOR UPDATE""",
                (task_id, list(terminal)),
            )
            locked = cursor.fetchone()
            if locked is not None:
                current = TaskStatus(locked[0])
                accounting_quarantined = bool(locked[1])
                self._apply_task_transition(
                    cursor,
                    task_id,
                    current,
                    target,
                    TransitionCommand("control_plane", target, operation),
                    clear_current=True,
                    terminal=True,
                    accounting_blocked=accounting_quarantined,
                )
                return TerminalizationResult(
                    True,
                    accounting_quarantined,
                    current,
                    operation,
                )
            cursor.execute(
                "SELECT state,current_run_id,accounting_blocked FROM factory.tasks WHERE task_id=%s",
                (task_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise KeyError(task_id)
            if row[0] in terminal:
                return TerminalizationResult(False, bool(row[2]))
        raise StoreError("terminal transition could not stabilize live lease")

    def _close_orphan_run(self, cursor, run_id: str, task_id: str, role: str, repository_id: str, actor: Actor) -> bool:
        if not self._lock_capacity_for_run(cursor, run_id):
            return False
        cursor.execute(
            """SELECT r.run_id FROM factory.runs r JOIN factory.capacity_allocations a ON a.run_id=r.run_id
            WHERE r.run_id=%s AND r.task_id=%s AND r.released_at IS NULL AND a.released_at IS NULL
            FOR UPDATE OF r""",
            (run_id, task_id),
        )
        if cursor.fetchone() is None:
            return False
        cursor.execute("UPDATE factory.runs SET state='expired',released_at=clock_timestamp() WHERE run_id=%s", (run_id,))
        cursor.execute(
            """UPDATE factory.attempts SET failure_class='worker_lost',failure_code='orphaned_projection',
            failure_digest=%s,finished_at=clock_timestamp() WHERE run_id=%s""",
            (canonical_digest({"failure": "orphaned_projection"}), run_id),
        )
        cursor.execute("SELECT factory.capacity_release(%s)", (run_id,))
        if not cursor.fetchone()[0]:
            raise StoreError("orphan capacity was not released")
        key = canonical_digest({"action": "reconcile_orphan", "run_id": run_id})
        self._event(
            cursor, task_id, actor, "orphan_reconciled", key, {"run_id": run_id}, mandatory_cleanup=True
        )
        self._audit(cursor, task_id, actor, "reconcile_orphan", f"run:{run_id}", "orphaned_projection", key, run_id=run_id)
        return True

    def _terminalize_expired_unleased_task(
        self,
        cursor,
        task_id: str,
        actor: Actor,
        correlation_id: str | None,
    ) -> bool:
        cursor.execute(
            """SELECT state,current_run_id,accounting_blocked
            OR cost_reserved_micros<>0 OR tokens_reserved<>0
            OR wall_reserved_seconds<>0 OR EXISTS (
              SELECT 1 FROM factory.budget_reservations b
              WHERE b.task_id=tasks.task_id AND b.released_at IS NULL
            ),deadline_at<=clock_timestamp()
            FROM factory.tasks WHERE task_id=%s FOR UPDATE""",
            (task_id,),
        )
        task_row = cursor.fetchone()
        if task_row is None:
            raise StoreError("reconciliation task is missing")
        state, current_run_id, accounting_quarantined, task_deadline_expired = task_row
        if not (
            state in {TaskStatus.QUEUED.value, TaskStatus.RETRY.value}
            and current_run_id is None
            and task_deadline_expired
        ):
            return False
        target = TaskStatus.NEEDS_HUMAN if accounting_quarantined else TaskStatus.DEAD
        operation = TransitionOperation.RECONCILE_DEADLINE
        self._apply_task_transition(
            cursor,
            task_id,
            TaskStatus(state),
            target,
            TransitionCommand("control_plane", target, operation),
            clear_current=True,
            terminal=target is TaskStatus.DEAD,
            accounting_blocked=bool(accounting_quarantined),
        )
        key = canonical_digest(
            {
                "action": "reconcile_deadline",
                "task_id": str(task_id),
                "from_state": state,
                "target": target.value,
            }
        )
        metadata = {
            "from_state": state,
            "target": target.value,
            "operation": operation.value,
            "accounting_quarantined": bool(accounting_quarantined),
        }
        self._event(
            cursor,
            task_id,
            actor,
            "deadline_expired",
            key,
            metadata,
            mandatory_cleanup=True,
        )
        self._audit(
            cursor,
            task_id,
            actor,
            "reconcile_deadline",
            f"task:{task_id}",
            "deadline_expired",
            correlation_id or key,
            metadata,
        )
        return True

    def _lock_grant(self, cursor, grant: LeaseGrant, *, allow_expired: bool = False):
        cursor.execute(
            """SELECT r.task_id,r.role,a.repository_id,at.attempt_no,t.infrastructure_retries,t.state
            FROM factory.runs r JOIN factory.tasks t ON t.task_id=r.task_id
            JOIN factory.capacity_allocations a ON a.run_id=r.run_id
            JOIN factory.attempts at ON at.run_id=r.run_id
            WHERE r.run_id=%s AND r.task_id=%s AND r.owner_id=%s AND r.role=%s
            AND r.fence=%s AND r.packet_digest=%s
            AND r.state='leased' AND r.released_at IS NULL
            AND a.released_at IS NULL
            AND (%s OR r.lease_expires_at>clock_timestamp())
            AND t.current_run_id=r.run_id AND t.current_fence=r.fence
            AND t.state IN ('leased','analyzing','implementing','verifying','reviewing')
            AND (%s OR t.deadline_at>clock_timestamp())
            FOR UPDATE OF r,t""",
            (
                grant.run_id,
                grant.task_id,
                grant.owner,
                grant.role.value,
                grant.fence,
                grant.packet_digest,
                allow_expired,
                allow_expired,
            ),
        )
        row = cursor.fetchone()
        if not row:
            raise FenceError("stale or expired fence")
        return row

    def heartbeat(self, grant: LeaseGrant, actor: Actor, now: datetime, *, idempotency_key: str | None = None, correlation_id: str | None = None) -> LeaseGrant:
        with self._transaction() as cursor:
            command = {"grant": {"task_id": grant.task_id, "run_id": grant.run_id, "owner": grant.owner, "role": grant.role.value, "fence": grant.fence, "packet_digest": grant.packet_digest}}
            replay, prior, request_digest = self._command_replay(cursor, idempotency_key, actor, "heartbeat", command)
            if replay:
                return LeaseGrant(grant.task_id, grant.run_id, grant.owner, grant.role, grant.fence, datetime.fromisoformat(prior["expires_at"].replace("Z", "+00:00")), grant.packet_digest)
            self._lock_grant(cursor, grant)
            cursor.execute(
                "UPDATE factory.runs SET lease_expires_at=LEAST(clock_timestamp()+interval '30 seconds',deadline_at) WHERE run_id=%s RETURNING lease_expires_at",
                (grant.run_id,),
            )
            expires = cursor.fetchone()[0]
            result = LeaseGrant(
                grant.task_id, grant.run_id, grant.owner, grant.role, grant.fence, expires, grant.packet_digest
            )
            self._record_command(cursor, idempotency_key, actor, "heartbeat", request_digest, correlation_id, {"expires_at": expires.isoformat().replace("+00:00", "Z")})
            return result

    def transition_phase(
        self,
        grant: LeaseGrant,
        target: TaskStatus,
        actor: Actor,
        now: datetime,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> TaskStatus:
        del now
        with self._transaction() as cursor:
            command = {
                "grant": {
                    "task_id": grant.task_id,
                    "run_id": grant.run_id,
                    "owner": grant.owner,
                    "role": grant.role.value,
                    "fence": grant.fence,
                    "packet_digest": grant.packet_digest,
                },
                "target": target.value,
            }
            replay, prior, request_digest = self._command_replay(
                cursor, idempotency_key, actor, "transition_phase", command
            )
            if replay:
                return TaskStatus(prior["status"])
            task_id, _role, _repository_id, _attempt_no, _retries, task_state = self._lock_grant(
                cursor, grant
            )
            current = TaskStatus(task_state)
            operation = TransitionOperation.PHASE
            self._apply_task_transition(
                cursor,
                str(task_id),
                current,
                target,
                TransitionCommand("worker", target, operation),
            )
            metadata = {
                "from_state": current.value,
                "target": target.value,
                "operation": operation.value,
                "run_id": grant.run_id,
                "fence": grant.fence,
            }
            event_key = canonical_digest(
                {
                    "action": "phase_transitioned",
                    "run_id": grant.run_id,
                    "fence": grant.fence,
                    "target": target.value,
                }
            )
            self._event(
                cursor,
                str(task_id),
                actor,
                "phase_transitioned",
                event_key,
                metadata,
            )
            self._audit(
                cursor,
                str(task_id),
                actor,
                "phase_transition",
                f"run:{grant.run_id}",
                target.value,
                correlation_id or idempotency_key or event_key,
                metadata,
                grant.run_id,
            )
            self._record_command(
                cursor,
                idempotency_key,
                actor,
                "transition_phase",
                request_digest,
                correlation_id,
                {"status": target.value},
            )
            return target

    def _release_locked(
        self, cursor, grant: LeaseGrant, outcome: str | FailureClass, actor: Actor, *, allow_expired: bool = False,
        deadline_expired: bool = False, correlation_id: str | None = None
    ) -> TaskStatus:
        cursor.execute("SELECT repository_id FROM factory.tasks WHERE task_id=%s", (grant.task_id,))
        repository = cursor.fetchone()
        if repository is None:
            raise FenceError("stale or expired fence")
        if not self._lock_capacity_for_run(cursor, grant.run_id):
            raise FenceError("stale or expired fence")
        task_id, _role, _repository_id, attempt_no, infrastructure_retries, task_state = self._lock_grant(
            cursor, grant, allow_expired=allow_expired
        )
        current = TaskStatus(task_state)
        accounting_quarantined = False
        if isinstance(outcome, FailureClass):
            cursor.execute(
                """SELECT accounting_blocked OR cost_reserved_micros<>0 OR tokens_reserved<>0
                OR wall_reserved_seconds<>0 OR EXISTS (
                  SELECT 1 FROM factory.budget_reservations
                  WHERE task_id=%s AND released_at IS NULL
                ) FROM factory.tasks WHERE task_id=%s""",
                (grant.task_id, grant.task_id),
            )
            accounting_quarantined = bool(cursor.fetchone()[0])
            if deadline_expired:
                target = TaskStatus.NEEDS_HUMAN if accounting_quarantined else TaskStatus.DEAD
                failure_code = "deadline_expired"
            else:
                decision = classify_retry(
                    outcome,
                    attempt_no=attempt_no,
                    infrastructure_retries=infrastructure_retries,
                )
                target = TaskStatus.RETRY if decision.retry else (decision.terminal or TaskStatus.NEEDS_HUMAN)
                failure_code = outcome.value
            if accounting_quarantined:
                target = TaskStatus.NEEDS_HUMAN
            cursor.execute(
                "UPDATE factory.attempts SET failure_class=%s,failure_code=%s,failure_digest=%s,finished_at=clock_timestamp() WHERE run_id=%s",
                (
                    outcome.value,
                    failure_code,
                    canonical_digest({"failure": failure_code}),
                    grant.run_id,
                ),
            )
        elif outcome == "completed":
            cursor.execute(
                """SELECT t.accounting_blocked,
                EXISTS(SELECT 1 FROM factory.usage_observations u WHERE u.task_id=t.task_id AND u.run_id=%s),
                EXISTS(SELECT 1 FROM factory.budget_reservations b WHERE b.task_id=t.task_id AND b.released_at IS NULL),
                t.cost_reserved_micros,t.tokens_reserved,t.wall_reserved_seconds
                FROM factory.tasks t WHERE t.task_id=%s""",
                (grant.run_id, grant.task_id),
            )
            blocked, has_usage, has_reservation, reserved_cost, reserved_tokens, reserved_wall = cursor.fetchone()
            if blocked or not has_usage or has_reservation or any((reserved_cost, reserved_tokens, reserved_wall)):
                raise BudgetError("completion requires settled accounting")
            target = TaskStatus.READY_FOR_HUMAN
            cursor.execute("UPDATE factory.attempts SET finished_at=clock_timestamp() WHERE run_id=%s", (grant.run_id,))
        else:
            raise StoreError("unsupported release outcome")
        if target is TaskStatus.RETRY and not self._ordinary_event_capacity_available(cursor, grant.task_id):
            target = TaskStatus.NEEDS_HUMAN
        cursor.execute(
            "UPDATE factory.runs SET state=%s,released_at=clock_timestamp() WHERE run_id=%s",
            ("failed" if isinstance(outcome, FailureClass) else "completed", grant.run_id),
        )
        cursor.execute("SELECT factory.capacity_release(%s)", (grant.run_id,))
        if not cursor.fetchone()[0]:
            raise StoreError("lease capacity was not released")
        terminal = target in {TaskStatus.DEAD, TaskStatus.READY_FOR_HUMAN}
        operation = (
            TransitionOperation.RECONCILE_EXPIRED
            if allow_expired
            else (
                TransitionOperation.RELEASE_FAILURE
                if isinstance(outcome, FailureClass)
                else TransitionOperation.RELEASE_COMPLETED
            )
        )
        actor_kind = "control_plane" if allow_expired else "worker"
        self._apply_task_transition(
            cursor,
            str(task_id),
            current,
            target,
            TransitionCommand(actor_kind, target, operation),
            clear_current=True,
            terminal=terminal,
            accounting_blocked=True if accounting_quarantined else None,
        )
        release_identity = {
            "action": "release",
            "run_id": grant.run_id,
            "fence": grant.fence,
            "target": target.value,
        }
        if deadline_expired:
            release_identity["reason"] = "deadline_expired"
        key = canonical_digest(release_identity)
        event_metadata = {
            "from_state": current.value,
            "target": target.value,
            "operation": operation.value,
            "run_id": grant.run_id,
            "fence": grant.fence,
        }
        audit_reason = target.value
        if deadline_expired:
            event_metadata.update(
                {
                    "reason": "deadline_expired",
                    "accounting_quarantined": accounting_quarantined,
                }
            )
            audit_reason = "deadline_expired"
        self._event(
            cursor, str(task_id), actor, "released", key, event_metadata, mandatory_cleanup=True
        )
        self._audit(
            cursor,
            str(task_id),
            actor,
            "release",
            f"run:{grant.run_id}",
            audit_reason,
            correlation_id or key,
            event_metadata,
            grant.run_id,
        )
        return target

    def _set_reconciliation_statement_timeout(
        self,
        cursor,
        deadline: float,
        *,
        reserve_seconds: float = 0.0,
    ) -> bool:
        remaining = deadline - time.monotonic() - reserve_seconds
        if remaining <= 0:
            return False
        milliseconds = max(1, int(remaining * 1000))
        cursor.execute(
            "SELECT set_config('statement_timeout',%s,true)",
            (f"{milliseconds}ms",),
        )
        return True

    def _set_reconciliation_transaction_timeout(self, cursor, deadline: float) -> None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise StoreUnavailable("reconciliation deadline exceeded")
        milliseconds = max(1, int(remaining * 1000))
        cursor.execute(
            "SELECT set_config('transaction_timeout',%s,true)",
            (f"{milliseconds}ms",),
        )

    def release(self, grant: LeaseGrant, outcome: str | FailureClass, actor: Actor, now: datetime, *, idempotency_key: str | None = None, correlation_id: str | None = None) -> TaskStatus:
        with self._transaction() as cursor:
            outcome_value = outcome.value if isinstance(outcome, FailureClass) else outcome
            command = {"task_id": grant.task_id, "run_id": grant.run_id, "fence": grant.fence, "outcome": outcome_value}
            replay, prior, request_digest = self._command_replay(cursor, idempotency_key, actor, "release", command)
            if replay:
                return TaskStatus(prior["status"])
            result = self._release_locked(cursor, grant, outcome, actor, correlation_id=correlation_id)
            self._record_command(cursor, idempotency_key, actor, "release", request_digest, correlation_id, {"status": result.value})
            return result

    def reserve_budget(
        self, grant: LeaseGrant, cost: int, tokens: int, wall: int, reason_digest: str, key: str, actor: Actor,
        *, correlation_id: str | None = None,
    ) -> str:
        if (
            any(type(value) is not int or value < 0 for value in (cost, tokens, wall))
            or not HEX64.fullmatch(reason_digest)
            or not HEX64.fullmatch(key)
        ):
            raise BudgetError("invalid budget evidence")
        with self._transaction() as cursor:
            command = {
                "task_id": grant.task_id, "run_id": grant.run_id, "fence": grant.fence,
                "cost_usd_micros": cost, "token_units": tokens, "wall_seconds": wall,
                "reason_digest": reason_digest,
            }
            replay, prior, request_digest = self._command_replay(cursor, key, actor, "reserve_budget", command)
            if replay:
                return prior["reservation_id"]
            self._lock_grant(cursor, grant)
            cursor.execute(
                """SELECT reservation_id,task_id,run_id,cost_usd_micros,token_units,wall_seconds,reason_digest
                FROM factory.budget_reservations WHERE idempotency_key=%s""",
                (key,),
            )
            duplicate = cursor.fetchone()
            if duplicate:
                expected = (grant.task_id, grant.run_id, cost, tokens, wall, reason_digest)
                actual = (str(duplicate[1]), str(duplicate[2]), duplicate[3], duplicate[4], duplicate[5], duplicate[6].strip())
                if actual != expected:
                    raise StoreError("idempotency key reused with different budget request")
                reservation_id = str(duplicate[0])
                self._record_command(
                    cursor, key, actor, "reserve_budget", request_digest, correlation_id,
                    {"reservation_id": reservation_id},
                )
                return reservation_id
            cursor.execute(
                "SELECT cost_limit_micros,token_limit,wall_limit_seconds,cost_reserved_micros,cost_observed_micros,tokens_reserved,tokens_observed,wall_reserved_seconds,accounting_blocked FROM factory.tasks WHERE task_id=%s FOR UPDATE",
                (grant.task_id,),
            )
            cost_limit, token_limit, wall_limit, reserved_cost, observed_cost, reserved_tokens, observed_tokens, reserved_wall, blocked = cursor.fetchone()
            if (
                blocked
                or reserved_cost + observed_cost + cost > cost_limit
                or reserved_tokens + observed_tokens + tokens > token_limit
                or reserved_wall + wall > wall_limit
            ):
                raise BudgetError("budget exceeded or accounting blocked")
            reservation_id = uuid.uuid4()
            cursor.execute(
                "INSERT INTO factory.budget_reservations(reservation_id,task_id,run_id,idempotency_key,cost_usd_micros,token_units,wall_seconds,reason_digest) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(idempotency_key) DO NOTHING RETURNING reservation_id",
                (reservation_id, grant.task_id, grant.run_id, key, cost, tokens, wall, reason_digest),
            )
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    "UPDATE factory.tasks SET cost_reserved_micros=cost_reserved_micros+%s,tokens_reserved=tokens_reserved+%s,wall_reserved_seconds=wall_reserved_seconds+%s WHERE task_id=%s",
                    (cost, tokens, wall, grant.task_id),
                )
            result = str(row[0] if row else reservation_id)
            self._record_command(
                cursor, key, actor, "reserve_budget", request_digest, correlation_id,
                {"reservation_id": result},
            )
            return result

    def observe_usage(
        self,
        grant: LeaseGrant,
        provider_call_id: str,
        price_table_digest: str | None,
        cost: int,
        tokens: int,
        output: int,
        actor: Actor,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> UsageResult:
        if (
            not isinstance(provider_call_id, str)
            or not 1 <= len(provider_call_id.encode("utf-8")) <= 128
            or any(type(value) is not int or value < 0 for value in (cost, tokens, output))
        ):
            raise BudgetError("invalid usage evidence")
        blocked_reason = None
        result = None
        with self._transaction() as cursor:
            command = {
                "task_id": grant.task_id, "run_id": grant.run_id, "fence": grant.fence,
                "provider_call_id": provider_call_id, "price_table_digest": price_table_digest,
                "cost_usd_micros": cost, "token_units": tokens, "output_bytes": output,
            }
            replay, prior, request_digest = self._command_replay(
                cursor, idempotency_key, actor, "observe_usage", command
            )
            if replay:
                if "error" in prior:
                    raise BudgetError(prior["error"])
                return UsageResult(prior["observation_id"], prior["created"])
            self._lock_grant(cursor, grant)
            if not isinstance(price_table_digest, str) or not HEX64.fullmatch(price_table_digest):
                blocked_reason = "missing_price_table"
            else:
                cursor.execute(
                    """SELECT observation_id,price_table_digest,cost_usd_micros,token_units,output_bytes
                    FROM factory.usage_observations WHERE run_id=%s AND provider_call_id=%s""",
                    (grant.run_id, provider_call_id),
                )
                duplicate = cursor.fetchone()
                if duplicate:
                    if (duplicate[1].strip(), duplicate[2], duplicate[3], duplicate[4]) != (price_table_digest, cost, tokens, output):
                        raise StoreError("provider call id reused with different usage evidence")
                    result = UsageResult(str(duplicate[0]), False)
                    self._record_command(
                        cursor, idempotency_key, actor, "observe_usage", request_digest, correlation_id,
                        {"observation_id": result.observation_id, "created": result.created},
                    )
                    return result
                cursor.execute(
                    """SELECT COALESCE(sum(cost_usd_micros),0),COALESCE(sum(token_units),0),COALESCE(sum(wall_seconds),0)
                    FROM factory.budget_reservations WHERE task_id=%s AND run_id=%s AND released_at IS NULL""",
                    (grant.task_id, grant.run_id),
                )
                released_cost, released_tokens, released_wall = cursor.fetchone()
                cursor.execute(
                    "UPDATE factory.budget_reservations SET released_at=clock_timestamp() WHERE task_id=%s AND run_id=%s AND released_at IS NULL",
                    (grant.task_id, grant.run_id),
                )
                cursor.execute(
                    """UPDATE factory.tasks SET cost_reserved_micros=cost_reserved_micros-%s,
                    tokens_reserved=tokens_reserved-%s,wall_reserved_seconds=wall_reserved_seconds-%s WHERE task_id=%s""",
                    (released_cost, released_tokens, released_wall, grant.task_id),
                )
                cursor.execute(
                    """SELECT cost_limit_micros,token_limit,output_limit_bytes,cost_observed_micros,tokens_observed,
                    COALESCE((SELECT sum(output_bytes) FROM factory.usage_observations WHERE task_id=t.task_id),0)
                    FROM factory.tasks t WHERE task_id=%s FOR UPDATE""",
                    (grant.task_id,),
                )
                cost_limit, token_limit, output_limit, observed_cost, observed_tokens, observed_output = (
                    cursor.fetchone()
                )
                if (
                    observed_cost + cost > cost_limit
                    or observed_tokens + tokens > token_limit
                    or observed_output + output > output_limit
                ):
                    blocked_reason = "usage_limit_exceeded"
                else:
                    observation_id = uuid.uuid4()
                    cursor.execute(
                        """INSERT INTO factory.usage_observations
                        (observation_id,task_id,run_id,provider_call_id,price_table_digest,cost_usd_micros,token_units,output_bytes)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (
                            observation_id,
                            grant.task_id,
                            grant.run_id,
                            provider_call_id,
                            price_table_digest,
                            cost,
                            tokens,
                            output,
                        ),
                    )
                    cursor.execute(
                        "UPDATE factory.tasks SET cost_observed_micros=cost_observed_micros+%s,tokens_observed=tokens_observed+%s WHERE task_id=%s",
                        (cost, tokens, grant.task_id),
                    )
                    result = UsageResult(str(observation_id), True)
            if blocked_reason:
                cursor.execute(
                    "UPDATE factory.tasks SET accounting_blocked=true,updated_at=clock_timestamp() WHERE task_id=%s",
                    (grant.task_id,),
                )
                key = canonical_digest(
                    {"action": "accounting_blocked", "run_id": grant.run_id, "reason": blocked_reason}
                )
                self._audit(
                    cursor,
                    grant.task_id,
                    actor,
                    "accounting_blocked",
                    f"run:{grant.run_id}",
                    blocked_reason,
                    correlation_id or key,
                    run_id=grant.run_id,
                )
                self._record_command(
                    cursor, idempotency_key, actor, "observe_usage", request_digest, correlation_id,
                    {"error": "accounting blocked"},
                )
            elif result is not None:
                self._record_command(
                    cursor, idempotency_key, actor, "observe_usage", request_digest, correlation_id,
                    {"observation_id": result.observation_id, "created": result.created},
                )
        if blocked_reason:
            raise BudgetError("accounting blocked")
        assert result is not None
        return result

    def set_kill(self, scope: str, enabled: bool, reason: str, key: str, actor: Actor, now: datetime, *, correlation_id: str | None = None) -> bool:
        if scope != "global" and not scope.startswith("repository:"):
            raise StoreError("invalid kill scope")
        if not HEX64.fullmatch(key) or not reason or len(reason) > 128:
            raise StoreError("invalid kill evidence")
        with self._transaction() as cursor:
            command = {"scope": scope, "enabled": enabled, "reason": reason}
            replay, prior, request_digest = self._command_replay(cursor, key, actor, "set_kill", command)
            if replay:
                return bool(prior["enabled"])
            cursor.execute(
                "INSERT INTO factory.kill_switches(switch_id,scope_key,enabled,actor_id,reason,idempotency_key) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(idempotency_key) DO NOTHING RETURNING enabled",
                (uuid.uuid4(), scope, enabled, actor.actor_id, reason, key),
            )
            row = cursor.fetchone()
            actual = bool(row[0]) if row else enabled
            self._record_command(cursor, key, actor, "set_kill", request_digest, correlation_id, {"enabled": actual})
            return actual

    def reconcile(self, actor: Actor, now: datetime, limit: int, cursor_id: str | None, *, idempotency_key: str | None = None, correlation_id: str | None = None) -> ReconcileResult:
        import psycopg

        deadline = time.monotonic() + self._RECONCILIATION_TIMEOUT_SECONDS
        repaired = 0
        last = None
        with self._transaction() as cursor:
            self._set_reconciliation_transaction_timeout(cursor, deadline)
            if not self._set_reconciliation_statement_timeout(cursor, deadline):
                raise StoreUnavailable("reconciliation deadline exceeded")
            if not self._capacity_consistent(cursor):
                raise StoreError("capacity counters do not match live allocations")
            command = {"limit": limit, "cursor": cursor_id}
            replay, prior, request_digest = self._command_replay(cursor, idempotency_key, actor, "reconcile", command)
            if replay:
                return ReconcileResult(prior["candidates"], prior["repaired"], prior["cursor"])
            cursor.execute(
                """WITH candidates AS (
                  SELECT r.run_id,r.task_id,r.owner_id,r.role,r.fence,r.lease_expires_at,
                    r.packet_digest,a.repository_id,'run'::text AS candidate_kind
                  FROM factory.runs r JOIN factory.capacity_allocations a ON a.run_id=r.run_id
                  WHERE r.released_at IS NULL AND a.released_at IS NULL
                    AND r.lease_expires_at<=clock_timestamp()
                  UNION ALL
                  SELECT NULL::uuid,t.task_id,NULL::text,NULL::text,NULL::bigint,t.deadline_at,
                    t.packet_digest,t.repository_id,'task_deadline'::text
                  FROM factory.tasks t
                  WHERE t.state IN ('queued','retry') AND t.current_run_id IS NULL
                    AND t.deadline_at<=clock_timestamp()
                    AND NOT EXISTS (
                      SELECT 1 FROM factory.runs live_run
                      JOIN factory.capacity_allocations live_allocation
                        ON live_allocation.run_id=live_run.run_id
                      WHERE live_run.task_id=t.task_id AND live_run.released_at IS NULL
                        AND live_allocation.released_at IS NULL
                    )
                )
                SELECT run_id,task_id,owner_id,role,fence,lease_expires_at,packet_digest,
                  repository_id,candidate_kind FROM candidates
                WHERE (%s::uuid IS NULL OR task_id>%s::uuid) ORDER BY task_id LIMIT %s""",
                (cursor_id, cursor_id, limit),
            )
            rows = cursor.fetchall()
            reconciliation_id = uuid.uuid4()
            cursor.execute(
                "INSERT INTO factory.reconciliation_runs(reconciliation_id,cursor_task_id,status,candidates) VALUES (%s,%s,'running',%s)",
                (reconciliation_id, cursor_id, len(rows)),
            )
            for row in rows:
                if not self._set_reconciliation_statement_timeout(
                    cursor,
                    deadline,
                    reserve_seconds=self._RECONCILIATION_COMMIT_RESERVE_SECONDS,
                ):
                    break
                run_id, task_id, owner, role, fence, expires, packet, repository_id, candidate_kind = row
                cursor.execute("SAVEPOINT reconcile_candidate")
                try:
                    if candidate_kind == "task_deadline":
                        if self._terminalize_expired_unleased_task(
                            cursor,
                            str(task_id),
                            actor,
                            correlation_id,
                        ):
                            repaired += 1
                        last = str(task_id)
                    elif not self._lock_capacity_for_run(cursor, str(run_id)):
                        last = str(task_id)
                    else:
                        cursor.execute(
                            """SELECT repair_count,repair_limit,state,current_run_id,current_fence,
                            deadline_at<=clock_timestamp() FROM factory.tasks WHERE task_id=%s FOR UPDATE""",
                            (task_id,),
                        )
                        task_row = cursor.fetchone()
                        if task_row is None:
                            raise StoreError("reconciliation task is missing")
                        repair_count, repair_limit, state, current_run_id, current_fence, task_deadline_expired = task_row
                        grant = LeaseGrant(
                            str(task_id), str(run_id), owner, RunRole(role), fence, expires, packet.strip()
                        )
                        failure = (
                            FailureClass.WORKER_LOST
                            if task_deadline_expired or repair_count < repair_limit
                            else FailureClass.PROVIDER_QUALITY
                        )
                        if (
                            state
                            in {
                                TaskStatus.LEASED.value,
                                TaskStatus.ANALYZING.value,
                                TaskStatus.IMPLEMENTING.value,
                                TaskStatus.VERIFYING.value,
                                TaskStatus.REVIEWING.value,
                            }
                            and str(current_run_id) == str(run_id)
                            and current_fence == fence
                        ):
                            self._release_locked(
                                cursor,
                                grant,
                                failure,
                                actor,
                                allow_expired=True,
                                deadline_expired=task_deadline_expired,
                            )
                            cursor.execute("UPDATE factory.runs SET state='expired' WHERE run_id=%s", (run_id,))
                            if not task_deadline_expired and repair_count < repair_limit:
                                cursor.execute(
                                    "UPDATE factory.tasks SET repair_count=repair_count+1 WHERE task_id=%s",
                                    (task_id,),
                                )
                            repaired += 1
                        elif self._close_orphan_run(
                            cursor, str(run_id), str(task_id), role, repository_id, actor
                        ):
                            self._terminalize_expired_unleased_task(
                                cursor,
                                str(task_id),
                                actor,
                                correlation_id,
                            )
                            repaired += 1
                        last = str(task_id)
                except psycopg.errors.QueryCanceled:
                    cursor.execute("ROLLBACK TO SAVEPOINT reconcile_candidate")
                    cursor.execute("RELEASE SAVEPOINT reconcile_candidate")
                    break
                else:
                    cursor.execute("RELEASE SAVEPOINT reconcile_candidate")
            if not self._set_reconciliation_statement_timeout(cursor, deadline):
                raise StoreUnavailable("reconciliation deadline exceeded")
            cursor.execute(
                "UPDATE factory.reconciliation_runs SET status='completed',repaired=%s,finished_at=clock_timestamp(),cursor_task_id=%s WHERE reconciliation_id=%s",
                (repaired, last, reconciliation_id),
            )
            result = ReconcileResult(len(rows), repaired, last)
            self._record_command(cursor, idempotency_key, actor, "reconcile", request_digest, correlation_id, {"candidates": result.candidates, "repaired": result.repaired, "cursor": result.cursor})
        return result

    def cancel(
        self,
        task_id: str,
        reason: str,
        key: str,
        actor: Actor,
        now: datetime,
        *,
        correlation_id: str | None = None,
        authorize_repository: Callable[[str], None] | None = None,
    ) -> TaskProjection:
        with self._transaction() as cursor:
            task = self._get_task(cursor, task_id)
            if authorize_repository is not None:
                authorize_repository(task.repository_id)
            command = {"task_id": task_id, "reason": reason}
            replay, _prior, request_digest = self._command_replay(cursor, key, actor, "cancel", command)
            if replay:
                return self._get_task(cursor, task_id)
            terminalization = self._terminalize_task(cursor, task_id, TaskStatus.CANCELLED)
            if terminalization.changed:
                cursor.execute("SET LOCAL lock_timeout='500ms'")
                cursor.execute("SET LOCAL transaction_timeout='3s'")
                cursor.execute(
                    "SELECT factory.execution_recovery_cancel_task(%s)", (task_id,)
                )
                execution_projection = cursor.fetchone()[0]
                if execution_projection not in {
                    "cancelled",
                    "no_execution",
                    "already_terminal",
                }:
                    raise StoreError("execution cancellation projection failed")
                metadata = {
                    "reason": reason,
                    "accounting_quarantined": terminalization.accounting_quarantined,
                    "from_state": terminalization.from_state.value,
                    "target": TaskStatus.CANCELLED.value,
                    "operation": terminalization.operation.value,
                }
                self._event(
                    cursor, task_id, actor, "cancelled", key, metadata, mandatory_cleanup=True
                )
                self._audit(
                    cursor,
                    task_id,
                    actor,
                    "cancel",
                    f"task:{task_id}",
                    reason,
                    correlation_id or key,
                    metadata,
                )
            self._record_command(cursor, key, actor, "cancel", request_digest, correlation_id, {"task_id": task_id})
            return self._get_task(cursor, task_id)
