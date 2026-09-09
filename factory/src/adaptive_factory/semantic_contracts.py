from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import re
from typing import Any, ClassVar, Mapping, Self

from .contracts import ContractError, HEX40, HEX64, _closed, _hex, _id as _base_id, _time, canonical_digest, canonical_json


MAX_JSON_BYTES = 1_000_000
MAX_ITEMS = 256
SAFE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$")
REQUIREMENT_KINDS = {
    "acceptance_criterion",
    "invariant",
    "forbidden_outcome",
    "architecture_rule",
    "non_functional_requirement",
}
VALIDATOR_CAPABILITIES = {"repository_read", "semantic_validate"}
FORBIDDEN_VALIDATOR_CAPABILITIES = {
    "application_write",
    "adjudicate",
    "external_write",
    "network",
    "credential_read",
}
RISK_LEVELS = {"none", "low", "medium", "high", "critical"}


def _object(data: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(data, Mapping) or any(not isinstance(key, str) for key in data):
        raise ContractError("invalid_object", name)
    return data


def _text(value: Any, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError("invalid_text", name)
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ContractError("invalid_text", name) from exc
    if len(encoded) > maximum or any(ord(char) < 32 for char in value):
        raise ContractError("invalid_text", name)
    import unicodedata

    if unicodedata.normalize("NFC", value) != value:
        raise ContractError("invalid_text", name)
    return value


def _id(value: Any, name: str) -> str:
    try:
        return _base_id(value, name)
    except UnicodeEncodeError as exc:
        raise ContractError("invalid_identifier", name) from exc


def _reference(value: Any, name: str) -> str:
    text = _text(value, name, 256)
    if not SAFE_REF.fullmatch(text):
        raise ContractError("invalid_reference", name)
    return text


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ContractError("invalid_integer", name)
    return value


def _sorted_unique(values: Any, name: str, parser, *, allow_empty: bool = True) -> tuple[Any, ...]:
    if not isinstance(values, list) or len(values) > MAX_ITEMS or (not allow_empty and not values):
        raise ContractError(name)
    parsed = tuple(parser(item) for item in values)
    keys = tuple(_sort_key(item) for item in parsed)
    if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
        raise ContractError(name)
    return parsed


def _sort_key(value: Any) -> str:
    if isinstance(value, RequirementRefV1):
        return value.key
    if isinstance(value, CoverageEntryV1):
        return value.requirement.key
    return str(value)


def _parse_json(raw: str | bytes | bytearray, name: str) -> Mapping[str, Any]:
    if not isinstance(raw, (str, bytes, bytearray)):
        raise ContractError("invalid_json", name)
    try:
        payload = raw.encode("utf-8") if isinstance(raw, str) else bytes(raw)
    except UnicodeEncodeError as exc:
        raise ContractError("invalid_json", name) from exc
    if len(payload) > MAX_JSON_BYTES:
        raise ContractError("json_too_large", name)

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ContractError("duplicate_json_key", key)
            result[key] = value
        return result

    try:
        decoded = json.loads(payload, object_pairs_hook=pairs)
    except ContractError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("invalid_json", name) from exc
    if not isinstance(decoded, dict):
        raise ContractError("invalid_json_object", name)
    return decoded


def _to_dict(value: Any) -> dict[str, Any]:
    return json.loads(canonical_json(asdict(value)))


class JsonContract:
    @classmethod
    def from_json(cls, raw: str | bytes | bytearray) -> Self:
        return cls.from_dict(_parse_json(raw, cls.__name__))

    def to_dict(self) -> dict[str, Any]:
        return _to_dict(self)

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True)
class RequirementRefV1(JsonContract):
    kind: str
    requirement_id: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RequirementRefV1":
        data = _object(data, "requirement")
        _closed(data, {"kind", "requirement_id"})
        if data["kind"] not in REQUIREMENT_KINDS:
            raise ContractError("requirement_kind")
        return cls(data["kind"], _id(data["requirement_id"], "requirement_id"))

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.requirement_id}"


@dataclass(frozen=True)
class ValidatorIdentityV1(JsonContract):
    validator_id: str
    role: str
    capabilities: tuple[str, ...]
    definition_digest: str
    model_digest: str
    context_digest: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ValidatorIdentityV1":
        data = _object(data, "validator")
        fields = {"validator_id", "role", "capabilities", "definition_digest", "model_digest", "context_digest"}
        _closed(data, fields)
        if data["role"] != "semantic_validator":
            raise ContractError("validator_role")
        capabilities = _sorted_unique(
            data["capabilities"], "validator_capabilities", lambda item: _id(item, "capability"), allow_empty=False
        )
        return cls(
            _id(data["validator_id"], "validator_id"),
            "semantic_validator",
            capabilities,
            _hex(data["definition_digest"], "definition_digest", HEX64),
            _hex(data["model_digest"], "model_digest", HEX64),
            _hex(data["context_digest"], "context_digest", HEX64),
        )

    def validate_for(self, subject: "SemanticSubjectV1") -> None:
        if self.validator_id == subject.original_writer_id:
            raise ContractError("validator_is_original_writer")
        if self.context_digest == subject.original_writer_context_digest:
            raise ContractError("validator_context_not_independent")
        capabilities = set(self.capabilities)
        if not VALIDATOR_CAPABILITIES <= capabilities:
            raise ContractError("validator_capability_missing")
        forbidden = capabilities & FORBIDDEN_VALIDATOR_CAPABILITIES
        if forbidden:
            raise ContractError("validator_capability_forbidden", ",".join(sorted(forbidden)))


@dataclass(frozen=True)
class SemanticSubjectV1(JsonContract):
    schema_version: int
    subject_id: str
    requirements: tuple[RequirementRefV1, ...]
    exact_base_sha: str
    exact_head_sha: str
    spec_digest: str
    architecture_digest: str
    authority_digest: str
    diff_digest: str
    deterministic_evidence_digest: str
    holdout_evidence_digest: str
    review_evidence_digest: str
    original_writer_id: str
    original_writer_context_digest: str
    risk_level: str
    diff_lines: int
    diff_limit: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SemanticSubjectV1":
        data = _object(data, "semantic_subject")
        fields = set(cls.__dataclass_fields__)
        _closed(data, fields)
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", "semantic_subject")
        requirements = _sorted_unique(
            data["requirements"], "requirements", RequirementRefV1.from_dict, allow_empty=False
        )
        risk = data["risk_level"]
        if risk not in RISK_LEVELS - {"none"}:
            raise ContractError("risk_level")
        diff_lines = _integer(data["diff_lines"], "diff_lines", 0, 1_000_000)
        diff_limit = _integer(data["diff_limit"], "diff_limit", 1, 1_000_000)
        return cls(
            1,
            _id(data["subject_id"], "subject_id"),
            requirements,
            _hex(data["exact_base_sha"], "exact_base_sha", HEX40),
            _hex(data["exact_head_sha"], "exact_head_sha", HEX40),
            _hex(data["spec_digest"], "spec_digest", HEX64),
            _hex(data["architecture_digest"], "architecture_digest", HEX64),
            _hex(data["authority_digest"], "authority_digest", HEX64),
            _hex(data["diff_digest"], "diff_digest", HEX64),
            _hex(data["deterministic_evidence_digest"], "deterministic_evidence_digest", HEX64),
            _hex(data["holdout_evidence_digest"], "holdout_evidence_digest", HEX64),
            _hex(data["review_evidence_digest"], "review_evidence_digest", HEX64),
            _id(data["original_writer_id"], "original_writer_id"),
            _hex(data["original_writer_context_digest"], "original_writer_context_digest", HEX64),
            risk,
            diff_lines,
            diff_limit,
        )

    @property
    def requirement_set_digest(self) -> str:
        return canonical_digest(self.to_dict()["requirements"])

    @property
    def requirement_keys(self) -> tuple[str, ...]:
        return tuple(item.key for item in self.requirements)


@dataclass(frozen=True)
class SemanticFindingV1(JsonContract):
    schema_version: int
    subject_digest: str
    finding_id: str
    requirement: RequirementRefV1
    severity: str
    category: str
    rule_id: str
    message: str
    evidence_refs: tuple[str, ...]
    reproduction: str
    repairable: bool
    validator: ValidatorIdentityV1
    created_at: datetime

    SEVERITIES: ClassVar[set[str]] = {"minor", "major", "critical", "blocker"}
    CATEGORIES: ClassVar[set[str]] = {
        "requirement_unsatisfied",
        "evidence_gap",
        "test_gap",
        "architecture_violation",
        "security_boundary",
        "authority_violation",
        "contradiction",
    }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SemanticFindingV1":
        data = _object(data, "semantic_finding")
        fields = {
            "schema_version", "subject_digest", "finding_id", "requirement", "severity", "category",
            "rule_id", "message", "evidence_refs", "reproduction", "repairable", "validator", "created_at",
        }
        _closed(data, fields)
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", "semantic_finding")
        if data["severity"] not in cls.SEVERITIES:
            raise ContractError("finding_severity")
        if data["category"] not in cls.CATEGORIES:
            raise ContractError("finding_category")
        if type(data["repairable"]) is not bool:
            raise ContractError("finding_repairable")
        evidence = _sorted_unique(data["evidence_refs"], "evidence_refs", lambda item: _reference(item, "evidence_ref"))
        return cls(
            1,
            _hex(data["subject_digest"], "subject_digest", HEX64),
            _id(data["finding_id"], "finding_id"),
            RequirementRefV1.from_dict(data["requirement"]),
            data["severity"],
            data["category"],
            _id(data["rule_id"], "rule_id"),
            _text(data["message"], "message", 4096),
            evidence,
            _text(data["reproduction"], "reproduction", 4096),
            data["repairable"],
            ValidatorIdentityV1.from_dict(data["validator"]),
            _time(data["created_at"], "created_at"),
        )

    @property
    def identity_digest(self) -> str:
        return canonical_digest(
            {
                "contract": "adaptive-factory.semantic-finding-identity/v1",
                "requirement": self.requirement,
                "severity": self.severity,
                "category": self.category,
                "rule_id": self.rule_id,
            }
        )

    def validate_for(self, subject: SemanticSubjectV1) -> None:
        if self.subject_digest != subject.digest:
            raise ContractError("stale_semantic_evidence", "finding")
        if self.requirement.key not in set(subject.requirement_keys):
            raise ContractError("finding_requirement_set")
        self.validator.validate_for(subject)


@dataclass(frozen=True)
class CoverageEntryV1(JsonContract):
    requirement: RequirementRefV1
    status: str
    evidence_refs: tuple[str, ...]

    STATUSES: ClassVar[set[str]] = {"proven", "unproven", "contradicted", "out_of_scope"}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CoverageEntryV1":
        data = _object(data, "coverage_entry")
        fields = {"requirement", "status", "evidence_refs"}
        _closed(data, fields)
        if data["status"] not in cls.STATUSES:
            raise ContractError("coverage_status")
        return cls(
            RequirementRefV1.from_dict(data["requirement"]),
            data["status"],
            _sorted_unique(data["evidence_refs"], "evidence_refs", lambda item: _reference(item, "evidence_ref")),
        )


@dataclass(frozen=True)
class SemanticCoverageV1(JsonContract):
    schema_version: int
    subject_digest: str
    validator: ValidatorIdentityV1
    entries: tuple[CoverageEntryV1, ...]
    coverage_millionths: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SemanticCoverageV1":
        data = _object(data, "semantic_coverage")
        fields = set(cls.__dataclass_fields__)
        _closed(data, fields)
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", "semantic_coverage")
        millionths = _integer(data["coverage_millionths"], "coverage_millionths", 0, 1_000_000)
        if millionths != 1_000_000:
            raise ContractError("coverage_millionths")
        return cls(
            1,
            _hex(data["subject_digest"], "subject_digest", HEX64),
            ValidatorIdentityV1.from_dict(data["validator"]),
            _sorted_unique(data["entries"], "coverage_entries", CoverageEntryV1.from_dict, allow_empty=False),
            millionths,
        )

    def validate_for(self, subject: SemanticSubjectV1) -> None:
        if self.subject_digest != subject.digest:
            raise ContractError("stale_semantic_evidence", "coverage")
        if tuple(item.requirement.key for item in self.entries) != subject.requirement_keys:
            raise ContractError("coverage_requirement_set")
        self.validator.validate_for(subject)


@dataclass(frozen=True)
class SemanticVerdictV1(JsonContract):
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

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SemanticVerdictV1":
        data = _object(data, "semantic_verdict")
        fields = set(cls.__dataclass_fields__)
        _closed(data, fields)
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", "semantic_verdict")
        if data["decision"] not in {"pass", "repair", "needs_human"}:
            raise ContractError("semantic_decision")
        if data["decision_source"] != "deterministic_adjudicator":
            raise ContractError("decision_source")
        if data["residual_risk"] not in RISK_LEVELS:
            raise ContractError("residual_risk")
        def digest_list(value, name):
            return _sorted_unique(value, name, lambda item: _hex(item, name, HEX64))

        def key_list(value, name):
            return _sorted_unique(value, name, lambda item: _reference(item, name))
        return cls(
            1,
            _hex(data["subject_digest"], "subject_digest", HEX64),
            data["decision"],
            "deterministic_adjudicator",
            digest_list(data["finding_identity_digests"], "finding_identity_digests"),
            digest_list(data["duplicate_identity_digests"], "duplicate_identity_digests"),
            key_list(data["correlated_requirement_keys"], "correlated_requirement_keys"),
            key_list(data["contradicted_requirement_keys"], "contradicted_requirement_keys"),
            key_list(data["unsupported_pass_requirement_keys"], "unsupported_pass_requirement_keys"),
            data["residual_risk"],
        )

    def validate_for(self, subject: SemanticSubjectV1) -> None:
        if self.subject_digest != subject.digest:
            raise ContractError("stale_semantic_evidence", "verdict")


@dataclass(frozen=True)
class RepairDirectiveV1(JsonContract):
    schema_version: int
    subject_digest: str
    verdict_digest: str
    cycle: int
    writer_id: str
    context_digest: str
    exact_head_sha: str
    finding_identity_digests: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RepairDirectiveV1":
        data = _object(data, "repair_directive")
        fields = set(cls.__dataclass_fields__)
        _closed(data, fields)
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", "repair_directive")
        return cls(
            1,
            _hex(data["subject_digest"], "subject_digest", HEX64),
            _hex(data["verdict_digest"], "verdict_digest", HEX64),
            _integer(data["cycle"], "repair_cycle", 1, 3),
            _id(data["writer_id"], "writer_id"),
            _hex(data["context_digest"], "context_digest", HEX64),
            _hex(data["exact_head_sha"], "exact_head_sha", HEX40),
            _sorted_unique(
                data["finding_identity_digests"],
                "finding_identity_digests",
                lambda item: _hex(item, "finding_identity_digest", HEX64),
            ),
        )

    def validate_for(self, subject: SemanticSubjectV1, verdict: SemanticVerdictV1 | None = None) -> None:
        if self.subject_digest != subject.digest or self.exact_head_sha != subject.exact_head_sha:
            raise ContractError("stale_semantic_evidence", "directive")
        if self.writer_id != subject.original_writer_id:
            raise ContractError("repair_writer_mismatch")
        if verdict is not None:
            verdict.validate_for(subject)
            if self.verdict_digest != verdict.digest:
                raise ContractError("stale_semantic_evidence", "directive verdict")
