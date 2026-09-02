from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
from typing import Any, ClassVar, Mapping

from .contracts import ContractError, HEX40, HEX64, _closed, _hex, _id, canonical_json


MAX_FENCE = 9_223_372_036_854_775_807
MANUAL_HANDOFF_INSTRUCTIONS = (
    "human_decides_merge",
    "inspect_local_bundle",
    "obtain_human_review",
    "verify_exact_sha_trust_ci",
)


def _object(data: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(data, Mapping) or any(not isinstance(key, str) for key in data):
        raise ContractError("invalid_contract", name)
    return data


def _version(value: Any, name: str) -> int:
    if type(value) is not int or value != 1:
        raise ContractError("unsupported_version", name)
    return 1


def _identifier(value: Any, name: str) -> str:
    try:
        return _id(value, name)
    except UnicodeEncodeError as exc:
        raise ContractError("invalid_identifier", name) from exc


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ContractError("invalid_contract", name)
    return value


def _accepted(value: Any) -> str:
    if value != "accepted":
        raise ContractError("dependency_not_accepted")
    return "accepted"


def _domain_digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + canonical_json(value)).hexdigest()


def _field_names(contract: type[Any]) -> set[str]:
    return {field.name for field in fields(contract)}


class _ShadowValue:
    DOMAIN: ClassVar[str]

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    @property
    def digest(self) -> str:
        return _domain_digest(self.DOMAIN, self.to_dict())


@dataclass(frozen=True)
class M4ControlPlaneBridgeV1(_ShadowValue):
    schema_version: int
    product_sha: str
    dependency_state: str
    task_id: str
    run_id: str
    fence: int
    task_packet_digest: str
    exact_head_sha: str
    task_record_digest: str
    control_plane_evidence_digest: str

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-m4-control-plane-bridge/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "m4")
        _hex(self.product_sha, "m4.product_sha", HEX40)
        _accepted(self.dependency_state)
        _identifier(self.task_id, "m4.task_id")
        _identifier(self.run_id, "m4.run_id")
        _integer(self.fence, "m4.fence", 1, MAX_FENCE)
        _hex(self.task_packet_digest, "m4.task_packet_digest", HEX64)
        _hex(self.exact_head_sha, "m4.exact_head_sha", HEX40)
        _hex(self.task_record_digest, "m4.task_record_digest", HEX64)
        _hex(self.control_plane_evidence_digest, "m4.control_plane_evidence_digest", HEX64)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "M4ControlPlaneBridgeV1":
        data = _object(data, "m4")
        _closed(data, _field_names(cls))
        return cls(
            _version(data["schema_version"], "m4"),
            _hex(data["product_sha"], "m4.product_sha", HEX40),
            _accepted(data["dependency_state"]),
            _identifier(data["task_id"], "m4.task_id"),
            _identifier(data["run_id"], "m4.run_id"),
            _integer(data["fence"], "m4.fence", 1, MAX_FENCE),
            _hex(data["task_packet_digest"], "m4.task_packet_digest", HEX64),
            _hex(data["exact_head_sha"], "m4.exact_head_sha", HEX40),
            _hex(data["task_record_digest"], "m4.task_record_digest", HEX64),
            _hex(data["control_plane_evidence_digest"], "m4.control_plane_evidence_digest", HEX64),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "product_sha": self.product_sha,
            "dependency_state": self.dependency_state,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "fence": self.fence,
            "task_packet_digest": self.task_packet_digest,
            "exact_head_sha": self.exact_head_sha,
            "task_record_digest": self.task_record_digest,
            "control_plane_evidence_digest": self.control_plane_evidence_digest,
        }


@dataclass(frozen=True)
class M5ExecutionBridgeV1(_ShadowValue):
    schema_version: int
    product_sha: str
    dependency_state: str
    task_id: str
    run_id: str
    fence: int
    task_packet_digest: str
    exact_head_sha: str
    run_manifest_digest: str
    workspace_result_digest: str
    execution_authority_digest: str

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-m5-execution-bridge/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "m5")
        _hex(self.product_sha, "m5.product_sha", HEX40)
        _accepted(self.dependency_state)
        _identifier(self.task_id, "m5.task_id")
        _identifier(self.run_id, "m5.run_id")
        _integer(self.fence, "m5.fence", 1, MAX_FENCE)
        _hex(self.task_packet_digest, "m5.task_packet_digest", HEX64)
        _hex(self.exact_head_sha, "m5.exact_head_sha", HEX40)
        _hex(self.run_manifest_digest, "m5.run_manifest_digest", HEX64)
        _hex(self.workspace_result_digest, "m5.workspace_result_digest", HEX64)
        _hex(self.execution_authority_digest, "m5.execution_authority_digest", HEX64)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "M5ExecutionBridgeV1":
        data = _object(data, "m5")
        _closed(data, _field_names(cls))
        return cls(
            _version(data["schema_version"], "m5"),
            _hex(data["product_sha"], "m5.product_sha", HEX40),
            _accepted(data["dependency_state"]),
            _identifier(data["task_id"], "m5.task_id"),
            _identifier(data["run_id"], "m5.run_id"),
            _integer(data["fence"], "m5.fence", 1, MAX_FENCE),
            _hex(data["task_packet_digest"], "m5.task_packet_digest", HEX64),
            _hex(data["exact_head_sha"], "m5.exact_head_sha", HEX40),
            _hex(data["run_manifest_digest"], "m5.run_manifest_digest", HEX64),
            _hex(data["workspace_result_digest"], "m5.workspace_result_digest", HEX64),
            _hex(data["execution_authority_digest"], "m5.execution_authority_digest", HEX64),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "product_sha": self.product_sha,
            "dependency_state": self.dependency_state,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "fence": self.fence,
            "task_packet_digest": self.task_packet_digest,
            "exact_head_sha": self.exact_head_sha,
            "run_manifest_digest": self.run_manifest_digest,
            "workspace_result_digest": self.workspace_result_digest,
            "execution_authority_digest": self.execution_authority_digest,
        }


@dataclass(frozen=True)
class M6SemanticBridgeV1(_ShadowValue):
    schema_version: int
    product_sha: str
    dependency_state: str
    task_id: str
    run_id: str
    fence: int
    task_packet_digest: str
    exact_head_sha: str
    semantic_subject_digest: str
    semantic_verdict_digest: str
    semantic_evidence_digest: str
    semantic_decision: str
    coverage_millionths: int
    contradicted_requirement_count: int
    unsupported_pass_requirement_count: int

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-m6-semantic-bridge/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "m6")
        _hex(self.product_sha, "m6.product_sha", HEX40)
        _accepted(self.dependency_state)
        _identifier(self.task_id, "m6.task_id")
        _identifier(self.run_id, "m6.run_id")
        _integer(self.fence, "m6.fence", 1, MAX_FENCE)
        _hex(self.task_packet_digest, "m6.task_packet_digest", HEX64)
        _hex(self.exact_head_sha, "m6.exact_head_sha", HEX40)
        _hex(self.semantic_subject_digest, "m6.semantic_subject_digest", HEX64)
        _hex(self.semantic_verdict_digest, "m6.semantic_verdict_digest", HEX64)
        _hex(self.semantic_evidence_digest, "m6.semantic_evidence_digest", HEX64)
        if self.semantic_decision != "pass":
            raise ContractError("semantic_not_pass")
        coverage = _integer(self.coverage_millionths, "m6.coverage_millionths", 0, 1_000_000)
        contradictions = _integer(
            self.contradicted_requirement_count,
            "m6.contradicted_requirement_count",
            0,
            256,
        )
        unsupported = _integer(
            self.unsupported_pass_requirement_count,
            "m6.unsupported_pass_requirement_count",
            0,
            256,
        )
        if coverage != 1_000_000:
            raise ContractError("incomplete_evidence")
        if contradictions:
            raise ContractError("contradictory_evidence")
        if unsupported:
            raise ContractError("incomplete_evidence", "unsupported_pass")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "M6SemanticBridgeV1":
        data = _object(data, "m6")
        _closed(data, _field_names(cls))
        return cls(
            _version(data["schema_version"], "m6"),
            _hex(data["product_sha"], "m6.product_sha", HEX40),
            _accepted(data["dependency_state"]),
            _identifier(data["task_id"], "m6.task_id"),
            _identifier(data["run_id"], "m6.run_id"),
            _integer(data["fence"], "m6.fence", 1, MAX_FENCE),
            _hex(data["task_packet_digest"], "m6.task_packet_digest", HEX64),
            _hex(data["exact_head_sha"], "m6.exact_head_sha", HEX40),
            _hex(data["semantic_subject_digest"], "m6.semantic_subject_digest", HEX64),
            _hex(data["semantic_verdict_digest"], "m6.semantic_verdict_digest", HEX64),
            _hex(data["semantic_evidence_digest"], "m6.semantic_evidence_digest", HEX64),
            data["semantic_decision"],
            _integer(data["coverage_millionths"], "m6.coverage_millionths", 0, 1_000_000),
            _integer(
                data["contradicted_requirement_count"],
                "m6.contradicted_requirement_count",
                0,
                256,
            ),
            _integer(
                data["unsupported_pass_requirement_count"],
                "m6.unsupported_pass_requirement_count",
                0,
                256,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "product_sha": self.product_sha,
            "dependency_state": self.dependency_state,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "fence": self.fence,
            "task_packet_digest": self.task_packet_digest,
            "exact_head_sha": self.exact_head_sha,
            "semantic_subject_digest": self.semantic_subject_digest,
            "semantic_verdict_digest": self.semantic_verdict_digest,
            "semantic_evidence_digest": self.semantic_evidence_digest,
            "semantic_decision": self.semantic_decision,
            "coverage_millionths": self.coverage_millionths,
            "contradicted_requirement_count": self.contradicted_requirement_count,
            "unsupported_pass_requirement_count": self.unsupported_pass_requirement_count,
        }


@dataclass(frozen=True)
class ShadowTaskEvidenceV1(_ShadowValue):
    schema_version: int
    m4: M4ControlPlaneBridgeV1
    m5: M5ExecutionBridgeV1
    m6: M6SemanticBridgeV1
    local_evidence_digest: str
    receipt_set_digest: str
    source_bundle_digest: str

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-shadow-task-evidence/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "shadow_task_evidence")
        if not isinstance(self.m4, M4ControlPlaneBridgeV1):
            raise ContractError("invalid_contract", "m4")
        if not isinstance(self.m5, M5ExecutionBridgeV1):
            raise ContractError("invalid_contract", "m5")
        if not isinstance(self.m6, M6SemanticBridgeV1):
            raise ContractError("invalid_contract", "m6")
        bindings = (
            "task_id",
            "run_id",
            "fence",
            "task_packet_digest",
            "exact_head_sha",
        )
        for field in bindings:
            if len({getattr(self.m4, field), getattr(self.m5, field), getattr(self.m6, field)}) != 1:
                raise ContractError("stale_binding", field)
        _hex(self.local_evidence_digest, "local_evidence_digest", HEX64)
        _hex(self.receipt_set_digest, "receipt_set_digest", HEX64)
        _hex(self.source_bundle_digest, "source_bundle_digest", HEX64)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ShadowTaskEvidenceV1":
        data = _object(data, "shadow_task_evidence")
        _closed(data, _field_names(cls))
        return cls(
            _version(data["schema_version"], "shadow_task_evidence"),
            M4ControlPlaneBridgeV1.from_dict(data["m4"]),
            M5ExecutionBridgeV1.from_dict(data["m5"]),
            M6SemanticBridgeV1.from_dict(data["m6"]),
            _hex(data["local_evidence_digest"], "local_evidence_digest", HEX64),
            _hex(data["receipt_set_digest"], "receipt_set_digest", HEX64),
            _hex(data["source_bundle_digest"], "source_bundle_digest", HEX64),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "m4": self.m4.to_dict(),
            "m5": self.m5.to_dict(),
            "m6": self.m6.to_dict(),
            "local_evidence_digest": self.local_evidence_digest,
            "receipt_set_digest": self.receipt_set_digest,
            "source_bundle_digest": self.source_bundle_digest,
        }


@dataclass(frozen=True)
class OperatorHandoffProposalV1(_ShadowValue):
    schema_version: int
    subject_digest: str
    external_capability: str
    recommended_action: str
    instructions: tuple[str, ...]

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-operator-handoff-proposal/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "operator_handoff")
        _hex(self.subject_digest, "subject_digest", HEX64)
        if self.external_capability != "absent":
            raise ContractError("external_capability_forbidden")
        if self.recommended_action != "human_review":
            raise ContractError("invalid_recommendation")
        if self.instructions != MANUAL_HANDOFF_INSTRUCTIONS:
            raise ContractError("invalid_instructions")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OperatorHandoffProposalV1":
        data = _object(data, "operator_handoff")
        _closed(data, _field_names(cls))
        instructions = data["instructions"]
        if not isinstance(instructions, list):
            raise ContractError("invalid_instructions")
        return cls(
            _version(data["schema_version"], "operator_handoff"),
            _hex(data["subject_digest"], "subject_digest", HEX64),
            data["external_capability"],
            data["recommended_action"],
            tuple(instructions),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "subject_digest": self.subject_digest,
            "external_capability": self.external_capability,
            "recommended_action": self.recommended_action,
            "instructions": list(self.instructions),
        }


@dataclass(frozen=True)
class ReadyForPrBundleV1(_ShadowValue):
    schema_version: int
    status: str
    evidence: ShadowTaskEvidenceV1
    operator_handoff: OperatorHandoffProposalV1
    bundle_digest: str

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-ready-for-pr-bundle/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "ready_for_pr_bundle")
        if self.status != "ready_for_human":
            raise ContractError("invalid_bundle_status")
        if not isinstance(self.evidence, ShadowTaskEvidenceV1):
            raise ContractError("invalid_contract", "evidence")
        if not isinstance(self.operator_handoff, OperatorHandoffProposalV1):
            raise ContractError("invalid_contract", "operator_handoff")
        if self.operator_handoff.subject_digest != self.evidence.digest:
            raise ContractError("stale_binding", "operator_handoff.subject_digest")
        supplied = _hex(self.bundle_digest, "bundle_digest", HEX64)
        if supplied != self._expected_digest():
            raise ContractError("digest_mismatch", "bundle_digest")

    def _unsigned_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "evidence": self.evidence.to_dict(),
            "operator_handoff": self.operator_handoff.to_dict(),
        }

    def _expected_digest(self) -> str:
        return _domain_digest(self.DOMAIN, self._unsigned_dict())

    @classmethod
    def from_components(
        cls,
        *,
        evidence: ShadowTaskEvidenceV1,
        operator_handoff: OperatorHandoffProposalV1,
    ) -> "ReadyForPrBundleV1":
        if not isinstance(evidence, ShadowTaskEvidenceV1):
            raise ContractError("invalid_contract", "evidence")
        if not isinstance(operator_handoff, OperatorHandoffProposalV1):
            raise ContractError("invalid_contract", "operator_handoff")
        if operator_handoff.subject_digest != evidence.digest:
            raise ContractError("stale_binding", "operator_handoff.subject_digest")
        unsigned = {
            "schema_version": 1,
            "status": "ready_for_human",
            "evidence": evidence.to_dict(),
            "operator_handoff": operator_handoff.to_dict(),
        }
        return cls(1, "ready_for_human", evidence, operator_handoff, _domain_digest(cls.DOMAIN, unsigned))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReadyForPrBundleV1":
        data = _object(data, "ready_for_pr_bundle")
        _closed(data, _field_names(cls))
        version = _version(data["schema_version"], "ready_for_pr_bundle")
        status = data["status"]
        if status != "ready_for_human":
            raise ContractError("invalid_bundle_status")
        evidence = ShadowTaskEvidenceV1.from_dict(data["evidence"])
        operator_handoff = OperatorHandoffProposalV1.from_dict(data["operator_handoff"])
        supplied = _hex(data["bundle_digest"], "bundle_digest", HEX64)
        unsigned = {
            "schema_version": version,
            "status": status,
            "evidence": evidence.to_dict(),
            "operator_handoff": operator_handoff.to_dict(),
        }
        if supplied != _domain_digest(cls.DOMAIN, unsigned):
            raise ContractError("digest_mismatch", "bundle_digest")
        return cls(version, status, evidence, operator_handoff, supplied)

    def to_dict(self) -> dict[str, Any]:
        return {**self._unsigned_dict(), "bundle_digest": self.bundle_digest}

    @property
    def digest(self) -> str:
        return self.bundle_digest

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())
