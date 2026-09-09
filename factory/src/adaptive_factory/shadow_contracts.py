from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
from typing import Any, ClassVar, Mapping

from .contracts import (
    ContractError,
    HEX40,
    HEX64,
    _closed,
    _hex,
    _id,
    canonical_digest,
    canonical_json,
)


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
    task_id: str
    run_id: str
    owner: str
    role: str
    fence: int
    intent_digest: str
    lease_packet_digest: str

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-m4-control-plane-bridge/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "m4")
        _identifier(self.task_id, "m4.task_id")
        _identifier(self.run_id, "m4.run_id")
        _identifier(self.owner, "m4.owner")
        if self.role != "writer":
            raise ContractError("writer_required", "m4.role")
        _integer(self.fence, "m4.fence", 1, MAX_FENCE)
        _hex(self.intent_digest, "m4.intent_digest", HEX64)
        _hex(self.lease_packet_digest, "m4.lease_packet_digest", HEX64)
        if self.intent_digest != self.lease_packet_digest:
            raise ContractError("stale_binding", "m4.lease_packet_digest")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "M4ControlPlaneBridgeV1":
        data = _object(data, "m4")
        _closed(data, _field_names(cls))
        return cls(
            _version(data["schema_version"], "m4"),
            _identifier(data["task_id"], "m4.task_id"),
            _identifier(data["run_id"], "m4.run_id"),
            _identifier(data["owner"], "m4.owner"),
            data["role"],
            _integer(data["fence"], "m4.fence", 1, MAX_FENCE),
            _hex(data["intent_digest"], "m4.intent_digest", HEX64),
            _hex(data["lease_packet_digest"], "m4.lease_packet_digest", HEX64),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "owner": self.owner,
            "role": self.role,
            "fence": self.fence,
            "intent_digest": self.intent_digest,
            "lease_packet_digest": self.lease_packet_digest,
        }


@dataclass(frozen=True)
class M5ExecutionBridgeV1(_ShadowValue):
    schema_version: int
    task_id: str
    run_id: str
    owner: str
    role: str
    fence: int
    repository_id: str
    legacy_intent_digest: str
    task_packet_digest: str
    run_manifest_digest: str
    workspace_snapshot_digest: str
    workspace_result_digest: str
    authority_exact_head_sha: str
    snapshot_input_head_sha: str
    snapshot_result_head_sha: str
    result_exact_head_sha: str

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-m5-execution-bridge/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "m5")
        _identifier(self.task_id, "m5.task_id")
        _identifier(self.run_id, "m5.run_id")
        _identifier(self.owner, "m5.owner")
        if self.role != "writer":
            raise ContractError("writer_required", "m5.role")
        _integer(self.fence, "m5.fence", 1, MAX_FENCE)
        _identifier(self.repository_id, "m5.repository_id")
        _hex(self.legacy_intent_digest, "m5.legacy_intent_digest", HEX64)
        _hex(self.task_packet_digest, "m5.task_packet_digest", HEX64)
        _hex(self.run_manifest_digest, "m5.run_manifest_digest", HEX64)
        _hex(self.workspace_snapshot_digest, "m5.workspace_snapshot_digest", HEX64)
        _hex(self.workspace_result_digest, "m5.workspace_result_digest", HEX64)
        for name in (
            "authority_exact_head_sha",
            "snapshot_input_head_sha",
            "snapshot_result_head_sha",
            "result_exact_head_sha",
        ):
            _hex(getattr(self, name), f"m5.{name}", HEX40)
        if self.authority_exact_head_sha != self.snapshot_input_head_sha:
            raise ContractError("stale_binding", "m5.snapshot_input_head_sha")
        if self.snapshot_result_head_sha != self.result_exact_head_sha:
            raise ContractError("stale_binding", "m5.snapshot_result_head_sha")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "M5ExecutionBridgeV1":
        data = _object(data, "m5")
        _closed(data, _field_names(cls))
        return cls(
            _version(data["schema_version"], "m5"),
            _identifier(data["task_id"], "m5.task_id"),
            _identifier(data["run_id"], "m5.run_id"),
            _identifier(data["owner"], "m5.owner"),
            data["role"],
            _integer(data["fence"], "m5.fence", 1, MAX_FENCE),
            _identifier(data["repository_id"], "m5.repository_id"),
            _hex(data["legacy_intent_digest"], "m5.legacy_intent_digest", HEX64),
            _hex(data["task_packet_digest"], "m5.task_packet_digest", HEX64),
            _hex(data["run_manifest_digest"], "m5.run_manifest_digest", HEX64),
            _hex(data["workspace_snapshot_digest"], "m5.workspace_snapshot_digest", HEX64),
            _hex(data["workspace_result_digest"], "m5.workspace_result_digest", HEX64),
            _hex(data["authority_exact_head_sha"], "m5.authority_exact_head_sha", HEX40),
            _hex(data["snapshot_input_head_sha"], "m5.snapshot_input_head_sha", HEX40),
            _hex(data["snapshot_result_head_sha"], "m5.snapshot_result_head_sha", HEX40),
            _hex(data["result_exact_head_sha"], "m5.result_exact_head_sha", HEX40),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "owner": self.owner,
            "role": self.role,
            "fence": self.fence,
            "repository_id": self.repository_id,
            "legacy_intent_digest": self.legacy_intent_digest,
            "task_packet_digest": self.task_packet_digest,
            "run_manifest_digest": self.run_manifest_digest,
            "workspace_snapshot_digest": self.workspace_snapshot_digest,
            "workspace_result_digest": self.workspace_result_digest,
            "authority_exact_head_sha": self.authority_exact_head_sha,
            "snapshot_input_head_sha": self.snapshot_input_head_sha,
            "snapshot_result_head_sha": self.snapshot_result_head_sha,
            "result_exact_head_sha": self.result_exact_head_sha,
        }


@dataclass(frozen=True)
class M6PassVerdictV1:
    schema_version: int
    subject_digest: str
    decision: str
    decision_source: str
    finding_identity_digests: tuple[str, ...]
    duplicate_identity_digests: tuple[str, ...]
    correlated_requirement_keys: tuple[str, ...]
    contradicted_requirement_keys: tuple[str, ...]
    unsupported_pass_requirement_keys: tuple[str, ...]
    residual_risk: str

    def __post_init__(self) -> None:
        _version(self.schema_version, "m6.verdict")
        _hex(self.subject_digest, "m6.verdict.subject_digest", HEX64)
        if self.decision != "pass" or self.decision_source != "deterministic_adjudicator":
            raise ContractError("semantic_not_pass")
        for name in (
            "finding_identity_digests",
            "duplicate_identity_digests",
            "correlated_requirement_keys",
            "contradicted_requirement_keys",
            "unsupported_pass_requirement_keys",
        ):
            if getattr(self, name) != ():
                raise ContractError("semantic_not_pass", name)
        if self.residual_risk != "none":
            raise ContractError("semantic_not_pass", "residual_risk")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "M6PassVerdictV1":
        data = _object(data, "m6.verdict")
        _closed(data, _field_names(cls))
        list_fields = (
            "finding_identity_digests",
            "duplicate_identity_digests",
            "correlated_requirement_keys",
            "contradicted_requirement_keys",
            "unsupported_pass_requirement_keys",
        )
        if any(not isinstance(data[name], list) for name in list_fields):
            raise ContractError("invalid_contract", "m6.verdict")
        return cls(
            _version(data["schema_version"], "m6.verdict"),
            _hex(data["subject_digest"], "m6.verdict.subject_digest", HEX64),
            data["decision"],
            data["decision_source"],
            *(tuple(data[name]) for name in list_fields),
            data["residual_risk"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "subject_digest": self.subject_digest,
            "decision": self.decision,
            "decision_source": self.decision_source,
            "finding_identity_digests": list(self.finding_identity_digests),
            "duplicate_identity_digests": list(self.duplicate_identity_digests),
            "correlated_requirement_keys": list(self.correlated_requirement_keys),
            "contradicted_requirement_keys": list(self.contradicted_requirement_keys),
            "unsupported_pass_requirement_keys": list(self.unsupported_pass_requirement_keys),
            "residual_risk": self.residual_risk,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True)
class M6SemanticBridgeV1(_ShadowValue):
    schema_version: int
    task_id: str
    run_id: str
    owner: str
    role: str
    fence: int
    repository_id: str
    legacy_intent_digest: str
    task_packet_digest: str
    run_manifest_digest: str
    workspace_snapshot_digest: str
    workspace_result_digest: str
    binding_input_head_sha: str
    binding_exact_head_sha: str
    subject_exact_head_sha: str
    envelope_digest: str
    binding_digest: str
    validation_inputs_digest: str
    subject_digest: str
    evidence_set_digest: str
    verdict_digest: str
    verdict: M6PassVerdictV1

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-m6-semantic-bridge/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "m6")
        _identifier(self.task_id, "m6.task_id")
        _identifier(self.run_id, "m6.run_id")
        _identifier(self.owner, "m6.owner")
        if self.role != "writer":
            raise ContractError("writer_required", "m6.role")
        _integer(self.fence, "m6.fence", 1, MAX_FENCE)
        _identifier(self.repository_id, "m6.repository_id")
        for name in (
            "legacy_intent_digest",
            "task_packet_digest",
            "run_manifest_digest",
            "workspace_snapshot_digest",
            "workspace_result_digest",
            "envelope_digest",
            "binding_digest",
            "validation_inputs_digest",
            "subject_digest",
            "evidence_set_digest",
            "verdict_digest",
        ):
            _hex(getattr(self, name), f"m6.{name}", HEX64)
        for name in ("binding_input_head_sha", "binding_exact_head_sha", "subject_exact_head_sha"):
            _hex(getattr(self, name), f"m6.{name}", HEX40)
        if not isinstance(self.verdict, M6PassVerdictV1):
            raise ContractError("invalid_contract", "m6.verdict")
        if self.verdict.subject_digest != self.subject_digest:
            raise ContractError("stale_binding", "m6.verdict.subject_digest")
        if self.verdict.digest != self.verdict_digest:
            raise ContractError("digest_mismatch", "m6.verdict_digest")
        expected_envelope = canonical_digest(
            {
                "contract": "adaptive-factory.semantic-subject-envelope/v1",
                "binding_digest": self.binding_digest,
                "validation_inputs_digest": self.validation_inputs_digest,
                "subject_digest": self.subject_digest,
            }
        )
        if expected_envelope != self.envelope_digest:
            raise ContractError("digest_mismatch", "m6.envelope_digest")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "M6SemanticBridgeV1":
        data = _object(data, "m6")
        _closed(data, _field_names(cls))
        return cls(
            _version(data["schema_version"], "m6"),
            _identifier(data["task_id"], "m6.task_id"),
            _identifier(data["run_id"], "m6.run_id"),
            _identifier(data["owner"], "m6.owner"),
            data["role"],
            _integer(data["fence"], "m6.fence", 1, MAX_FENCE),
            _identifier(data["repository_id"], "m6.repository_id"),
            _hex(data["legacy_intent_digest"], "m6.legacy_intent_digest", HEX64),
            _hex(data["task_packet_digest"], "m6.task_packet_digest", HEX64),
            _hex(data["run_manifest_digest"], "m6.run_manifest_digest", HEX64),
            _hex(data["workspace_snapshot_digest"], "m6.workspace_snapshot_digest", HEX64),
            _hex(data["workspace_result_digest"], "m6.workspace_result_digest", HEX64),
            _hex(data["binding_input_head_sha"], "m6.binding_input_head_sha", HEX40),
            _hex(data["binding_exact_head_sha"], "m6.binding_exact_head_sha", HEX40),
            _hex(data["subject_exact_head_sha"], "m6.subject_exact_head_sha", HEX40),
            _hex(data["envelope_digest"], "m6.envelope_digest", HEX64),
            _hex(data["binding_digest"], "m6.binding_digest", HEX64),
            _hex(data["validation_inputs_digest"], "m6.validation_inputs_digest", HEX64),
            _hex(data["subject_digest"], "m6.subject_digest", HEX64),
            _hex(data["evidence_set_digest"], "m6.evidence_set_digest", HEX64),
            _hex(data["verdict_digest"], "m6.verdict_digest", HEX64),
            M6PassVerdictV1.from_dict(data["verdict"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "owner": self.owner,
            "role": self.role,
            "fence": self.fence,
            "repository_id": self.repository_id,
            "legacy_intent_digest": self.legacy_intent_digest,
            "task_packet_digest": self.task_packet_digest,
            "run_manifest_digest": self.run_manifest_digest,
            "workspace_snapshot_digest": self.workspace_snapshot_digest,
            "workspace_result_digest": self.workspace_result_digest,
            "binding_input_head_sha": self.binding_input_head_sha,
            "binding_exact_head_sha": self.binding_exact_head_sha,
            "subject_exact_head_sha": self.subject_exact_head_sha,
            "envelope_digest": self.envelope_digest,
            "binding_digest": self.binding_digest,
            "validation_inputs_digest": self.validation_inputs_digest,
            "subject_digest": self.subject_digest,
            "evidence_set_digest": self.evidence_set_digest,
            "verdict_digest": self.verdict_digest,
            "verdict": self.verdict.to_dict(),
        }


@dataclass(frozen=True)
class ShadowTaskEvidenceV1(_ShadowValue):
    schema_version: int
    m4: M4ControlPlaneBridgeV1
    m5: M5ExecutionBridgeV1
    m6: M6SemanticBridgeV1

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-shadow-task-evidence/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "shadow_task_evidence")
        if not isinstance(self.m4, M4ControlPlaneBridgeV1):
            raise ContractError("invalid_contract", "m4")
        if not isinstance(self.m5, M5ExecutionBridgeV1):
            raise ContractError("invalid_contract", "m5")
        if not isinstance(self.m6, M6SemanticBridgeV1):
            raise ContractError("invalid_contract", "m6")
        bindings = ("task_id", "run_id", "owner", "role", "fence")
        for field in bindings:
            if len({getattr(self.m4, field), getattr(self.m5, field), getattr(self.m6, field)}) != 1:
                raise ContractError("stale_binding", field)
        if not (
            self.m4.intent_digest
            == self.m4.lease_packet_digest
            == self.m5.legacy_intent_digest
            == self.m6.legacy_intent_digest
        ):
            raise ContractError("stale_binding", "legacy_intent_digest")
        for field in (
            "repository_id",
            "task_packet_digest",
            "run_manifest_digest",
            "workspace_snapshot_digest",
            "workspace_result_digest",
        ):
            if getattr(self.m5, field) != getattr(self.m6, field):
                raise ContractError("stale_binding", field)
        if self.m6.binding_input_head_sha != self.m5.authority_exact_head_sha:
            raise ContractError("stale_binding", "binding_input_head_sha")
        if not (
            self.m5.result_exact_head_sha
            == self.m6.binding_exact_head_sha
            == self.m6.subject_exact_head_sha
        ):
            raise ContractError("stale_binding", "subject_exact_head_sha")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ShadowTaskEvidenceV1":
        data = _object(data, "shadow_task_evidence")
        _closed(data, _field_names(cls))
        return cls(
            _version(data["schema_version"], "shadow_task_evidence"),
            M4ControlPlaneBridgeV1.from_dict(data["m4"]),
            M5ExecutionBridgeV1.from_dict(data["m5"]),
            M6SemanticBridgeV1.from_dict(data["m6"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "m4": self.m4.to_dict(),
            "m5": self.m5.to_dict(),
            "m6": self.m6.to_dict(),
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
        if self.status != "blocked_pending_durable_lookup":
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
            "status": "blocked_pending_durable_lookup",
            "evidence": evidence.to_dict(),
            "operator_handoff": operator_handoff.to_dict(),
        }
        return cls(
            1,
            "blocked_pending_durable_lookup",
            evidence,
            operator_handoff,
            _domain_digest(cls.DOMAIN, unsigned),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReadyForPrBundleV1":
        data = _object(data, "ready_for_pr_bundle")
        _closed(data, _field_names(cls))
        version = _version(data["schema_version"], "ready_for_pr_bundle")
        status = data["status"]
        if status != "blocked_pending_durable_lookup":
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
