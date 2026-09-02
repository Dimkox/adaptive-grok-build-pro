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
CHANGE_CLASSES = frozenset({"ai", "api", "bugfix", "data", "feature", "integration", "release", "security"})
MAX_COHORT_ITEMS = 10_000
MAX_EVIDENCE_COUNT = 1_000_000
MAX_REVIEW_SECONDS = 604_800


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


def _boolean(value: Any, name: str) -> bool:
    if type(value) is not bool:
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


@dataclass(frozen=True)
class ShadowCohortKeyV1(_ShadowValue):
    schema_version: int
    repository_id: str
    change_class: str
    agent_digest: str
    validator_digest: str
    model_digest: str
    prompt_digest: str
    policy_digest: str
    runner_digest: str
    holdout_digest: str
    authority_digest: str

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-shadow-cohort-key/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "shadow_cohort_key")
        _identifier(self.repository_id, "repository_id")
        if self.change_class not in CHANGE_CLASSES:
            raise ContractError("invalid_contract", "change_class")
        for name in (
            "agent_digest",
            "validator_digest",
            "model_digest",
            "prompt_digest",
            "policy_digest",
            "runner_digest",
            "holdout_digest",
            "authority_digest",
        ):
            _hex(getattr(self, name), name, HEX64)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ShadowCohortKeyV1":
        data = _object(data, "shadow_cohort_key")
        _closed(data, _field_names(cls))
        return cls(
            _version(data["schema_version"], "shadow_cohort_key"),
            _identifier(data["repository_id"], "repository_id"),
            data["change_class"],
            *(
                _hex(data[name], name, HEX64)
                for name in (
                    "agent_digest",
                    "validator_digest",
                    "model_digest",
                    "prompt_digest",
                    "policy_digest",
                    "runner_digest",
                    "holdout_digest",
                    "authority_digest",
                )
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "repository_id": self.repository_id,
            "change_class": self.change_class,
            "agent_digest": self.agent_digest,
            "validator_digest": self.validator_digest,
            "model_digest": self.model_digest,
            "prompt_digest": self.prompt_digest,
            "policy_digest": self.policy_digest,
            "runner_digest": self.runner_digest,
            "holdout_digest": self.holdout_digest,
            "authority_digest": self.authority_digest,
        }


@dataclass(frozen=True)
class ShadowOutcomeV1(_ShadowValue):
    schema_version: int
    outcome_id: str
    bundle_digest: str
    cohort_key_digest: str
    human_evidence_digest: str
    human_decision: str
    first_pass_accepted: bool
    rework_required: bool
    validator_false_negative: bool
    validator_false_positive_or_disagreement: bool
    repair_cycles: int
    cost_within_budget: bool
    latency_within_slo: bool
    deadline_met: bool
    token_budget_met: bool
    human_review_seconds: int
    critical_high_miss_count: int
    security_miss_count: int
    unauthorized_effect_count: int
    rollback_count: int
    escaped_defect_count: int
    duplicate_dispatch_count: int
    unaccounted_call_count: int
    injection_attempt_count: int
    injection_contained_count: int

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-shadow-outcome/v1"
    COUNT_FIELDS: ClassVar[tuple[str, ...]] = (
        "critical_high_miss_count",
        "security_miss_count",
        "unauthorized_effect_count",
        "rollback_count",
        "escaped_defect_count",
        "duplicate_dispatch_count",
        "unaccounted_call_count",
        "injection_attempt_count",
        "injection_contained_count",
    )
    BOOL_FIELDS: ClassVar[tuple[str, ...]] = (
        "first_pass_accepted",
        "rework_required",
        "validator_false_negative",
        "validator_false_positive_or_disagreement",
        "cost_within_budget",
        "latency_within_slo",
        "deadline_met",
        "token_budget_met",
    )

    def __post_init__(self) -> None:
        _version(self.schema_version, "shadow_outcome")
        _identifier(self.outcome_id, "outcome_id")
        _hex(self.bundle_digest, "bundle_digest", HEX64)
        _hex(self.cohort_key_digest, "cohort_key_digest", HEX64)
        _hex(self.human_evidence_digest, "human_evidence_digest", HEX64)
        if self.human_decision not in {"merged_accepted", "not_merged"}:
            raise ContractError("invalid_contract", "human_decision")
        for name in self.BOOL_FIELDS:
            _boolean(getattr(self, name), name)
        _integer(self.repair_cycles, "repair_cycles", 0, 3)
        _integer(self.human_review_seconds, "human_review_seconds", 1, MAX_REVIEW_SECONDS)
        for name in self.COUNT_FIELDS:
            _integer(getattr(self, name), name, 0, MAX_EVIDENCE_COUNT)
        if self.first_pass_accepted and self.rework_required:
            raise ContractError("invalid_contract", "first_pass_rework")
        if self.first_pass_accepted and self.human_decision != "merged_accepted":
            raise ContractError("invalid_contract", "first_pass_human_decision")
        if self.injection_contained_count > self.injection_attempt_count:
            raise ContractError("invalid_contract", "injection_contained_count")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ShadowOutcomeV1":
        data = _object(data, "shadow_outcome")
        _closed(data, _field_names(cls))
        return cls(
            _version(data["schema_version"], "shadow_outcome"),
            _identifier(data["outcome_id"], "outcome_id"),
            _hex(data["bundle_digest"], "bundle_digest", HEX64),
            _hex(data["cohort_key_digest"], "cohort_key_digest", HEX64),
            _hex(data["human_evidence_digest"], "human_evidence_digest", HEX64),
            data["human_decision"],
            *(_boolean(data[name], name) for name in cls.BOOL_FIELDS[:4]),
            _integer(data["repair_cycles"], "repair_cycles", 0, 3),
            *(_boolean(data[name], name) for name in cls.BOOL_FIELDS[4:]),
            _integer(data["human_review_seconds"], "human_review_seconds", 1, MAX_REVIEW_SECONDS),
            *(
                _integer(data[name], name, 0, MAX_EVIDENCE_COUNT)
                for name in cls.COUNT_FIELDS
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "outcome_id": self.outcome_id,
            "bundle_digest": self.bundle_digest,
            "cohort_key_digest": self.cohort_key_digest,
            "human_evidence_digest": self.human_evidence_digest,
            "human_decision": self.human_decision,
            "first_pass_accepted": self.first_pass_accepted,
            "rework_required": self.rework_required,
            "validator_false_negative": self.validator_false_negative,
            "validator_false_positive_or_disagreement": self.validator_false_positive_or_disagreement,
            "repair_cycles": self.repair_cycles,
            "cost_within_budget": self.cost_within_budget,
            "latency_within_slo": self.latency_within_slo,
            "deadline_met": self.deadline_met,
            "token_budget_met": self.token_budget_met,
            "human_review_seconds": self.human_review_seconds,
            "critical_high_miss_count": self.critical_high_miss_count,
            "security_miss_count": self.security_miss_count,
            "unauthorized_effect_count": self.unauthorized_effect_count,
            "rollback_count": self.rollback_count,
            "escaped_defect_count": self.escaped_defect_count,
            "duplicate_dispatch_count": self.duplicate_dispatch_count,
            "unaccounted_call_count": self.unaccounted_call_count,
            "injection_attempt_count": self.injection_attempt_count,
            "injection_contained_count": self.injection_contained_count,
        }


@dataclass(frozen=True)
class ShadowCohortV1(_ShadowValue):
    schema_version: int
    cohort_id: str
    key: ShadowCohortKeyV1
    observation_days: int
    release_cycle_complete: bool
    baseline_review_seconds: tuple[int, ...]
    outcomes: tuple[ShadowOutcomeV1, ...]

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-shadow-cohort/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "shadow_cohort")
        _identifier(self.cohort_id, "cohort_id")
        if not isinstance(self.key, ShadowCohortKeyV1):
            raise ContractError("invalid_contract", "key")
        _integer(self.observation_days, "observation_days", 0, 3_650)
        _boolean(self.release_cycle_complete, "release_cycle_complete")
        if not isinstance(self.baseline_review_seconds, tuple) or len(self.baseline_review_seconds) > MAX_COHORT_ITEMS:
            raise ContractError("invalid_contract", "baseline_review_seconds")
        for value in self.baseline_review_seconds:
            _integer(value, "baseline_review_seconds", 1, MAX_REVIEW_SECONDS)
        if self.baseline_review_seconds != tuple(sorted(self.baseline_review_seconds)):
            raise ContractError("invalid_contract", "baseline_order")
        if not isinstance(self.outcomes, tuple) or not self.outcomes:
            raise ContractError("insufficient_sample")
        if len(self.outcomes) > MAX_COHORT_ITEMS:
            raise ContractError("invalid_contract", "cohort_size")
        if any(not isinstance(outcome, ShadowOutcomeV1) for outcome in self.outcomes):
            raise ContractError("invalid_contract", "outcomes")
        outcome_ids = tuple(outcome.outcome_id for outcome in self.outcomes)
        bundle_digests = tuple(outcome.bundle_digest for outcome in self.outcomes)
        if outcome_ids != tuple(sorted(outcome_ids)):
            raise ContractError("invalid_contract", "outcome_order")
        if len(set(outcome_ids)) != len(outcome_ids) or len(set(bundle_digests)) != len(bundle_digests):
            raise ContractError("replay")
        if any(outcome.cohort_key_digest != self.key.digest for outcome in self.outcomes):
            raise ContractError("cohort_mismatch")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ShadowCohortV1":
        data = _object(data, "shadow_cohort")
        _closed(data, _field_names(cls))
        baseline = data["baseline_review_seconds"]
        outcomes = data["outcomes"]
        if not isinstance(baseline, list) or len(baseline) > MAX_COHORT_ITEMS:
            raise ContractError("invalid_contract", "baseline_review_seconds")
        if not isinstance(outcomes, list):
            raise ContractError("invalid_contract", "outcomes")
        if not outcomes:
            raise ContractError("insufficient_sample")
        if len(outcomes) > MAX_COHORT_ITEMS:
            raise ContractError("invalid_contract", "cohort_size")
        return cls(
            _version(data["schema_version"], "shadow_cohort"),
            _identifier(data["cohort_id"], "cohort_id"),
            ShadowCohortKeyV1.from_dict(data["key"]),
            _integer(data["observation_days"], "observation_days", 0, 3_650),
            _boolean(data["release_cycle_complete"], "release_cycle_complete"),
            tuple(
                _integer(value, "baseline_review_seconds", 1, MAX_REVIEW_SECONDS)
                for value in baseline
            ),
            tuple(ShadowOutcomeV1.from_dict(outcome) for outcome in outcomes),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "cohort_id": self.cohort_id,
            "key": self.key.to_dict(),
            "observation_days": self.observation_days,
            "release_cycle_complete": self.release_cycle_complete,
            "baseline_review_seconds": list(self.baseline_review_seconds),
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
        }
