from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import unicodedata
from typing import Any, Mapping


HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
ACCEPTANCE_ID = re.compile(r"^AC-[0-9]{3,6}$")


class ContractError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def _canonical(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if hasattr(value, "__dataclass_fields__"):
        return _canonical(asdict(value))
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def canonical_json(value: Any) -> bytes:
    return json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _closed(data: Mapping[str, Any], expected: set[str]) -> None:
    unknown = set(data) - expected
    missing = expected - set(data)
    if unknown:
        raise ContractError("unknown_fields", ",".join(sorted(unknown)))
    if missing:
        raise ContractError("missing_fields", ",".join(sorted(missing)))


def _text(value: Any, name: str, maximum: int = 128) -> str:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > maximum:
        raise ContractError("invalid_text", name)
    if unicodedata.normalize("NFC", value) != value or any(ord(char) < 32 for char in value):
        raise ContractError("invalid_text", name)
    return value


def _id(value: Any, name: str) -> str:
    value = _text(value, name)
    if not ID.fullmatch(value):
        raise ContractError("invalid_identifier", name)
    return value


def _hex(value: Any, name: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ContractError("invalid_sha" if pattern is HEX40 else "invalid_digest", name)
    return value


def _time(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise ContractError("invalid_time", name)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("invalid_time", name) from exc
    if parsed.tzinfo is None:
        raise ContractError("invalid_time", name)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class ArchitectureHandoffV1:
    architecture_contract_version: int
    architecture_digest: str
    architecture_evidence_digest: str
    exact_base_sha: str
    exact_head_sha: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ArchitectureHandoffV1":
        fields = set(cls.__dataclass_fields__)
        _closed(data, fields)
        if data["architecture_contract_version"] != 1:
            raise ContractError("unsupported_version", "architecture")
        return cls(
            1,
            _hex(data["architecture_digest"], "architecture_digest", HEX64),
            _hex(data["architecture_evidence_digest"], "architecture_evidence_digest", HEX64),
            _hex(data["exact_base_sha"], "architecture.exact_base_sha", HEX40),
            _hex(data["exact_head_sha"], "architecture.exact_head_sha", HEX40),
        )


@dataclass(frozen=True)
class GovernanceHandoffV1:
    governance_contract_version: int
    governance_digest: str
    governance_evidence_digest: str
    architecture_digest: str
    exact_base_sha: str
    exact_head_sha: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GovernanceHandoffV1":
        fields = set(cls.__dataclass_fields__)
        _closed(data, fields)
        if data["governance_contract_version"] != 1:
            raise ContractError("unsupported_version", "governance")
        return cls(
            1,
            _hex(data["governance_digest"], "governance_digest", HEX64),
            _hex(data["governance_evidence_digest"], "governance_evidence_digest", HEX64),
            _hex(data["architecture_digest"], "governance.architecture_digest", HEX64),
            _hex(data["exact_base_sha"], "governance.exact_base_sha", HEX40),
            _hex(data["exact_head_sha"], "governance.exact_head_sha", HEX40),
        )


@dataclass(frozen=True)
class M0AuthorityV1:
    observed_at: datetime | None = None
    check_name: str | None = None
    exact_head_sha: str | None = None
    bootstrap_exception: str | None = None
    issuer: str | None = None
    scope: str | None = None
    expires_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], now: datetime) -> "M0AuthorityV1":
        observed = {"observed_at", "check_name", "exact_head_sha"}
        exception = {"bootstrap_exception", "issuer", "scope", "expires_at"}
        if set(data) == observed:
            at = _time(data["observed_at"], "observed_at")
            age = (now.astimezone(timezone.utc) - at).total_seconds()
            if age < 0 or age > 300:
                raise ContractError("stale_m0")
            check_name = _text(data["check_name"], "check_name", 256)
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/@:-]{0,255}", check_name):
                raise ContractError("invalid_identifier", "check_name")
            return cls(
                observed_at=at,
                check_name=check_name,
                exact_head_sha=_hex(data["exact_head_sha"], "m0.exact_head_sha", HEX40),
            )
        if set(data) == exception:
            expires = _time(data["expires_at"], "expires_at")
            if expires <= now.astimezone(timezone.utc):
                raise ContractError("stale_m0", "bootstrap exception expired")
            return cls(
                bootstrap_exception=_id(data["bootstrap_exception"], "bootstrap_exception"),
                issuer=_id(data["issuer"], "issuer"),
                scope=_id(data["scope"], "scope"),
                expires_at=expires,
            )
        raise ContractError("m0_authority", "must be one closed authority form")


@dataclass(frozen=True)
class TaskLimitsV1:
    wall_seconds: int = 14_400
    max_cost_usd_micros: int = 25_000_000
    max_token_units: int = 2_000_000
    max_output_bytes: int = 10_000_000
    max_events: int = 100_000
    infrastructure_retries: int = 2
    semantic_repairs: int = 3

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TaskLimitsV1":
        fields = set(cls.__dataclass_fields__)
        _closed(data, fields)
        limits = cls(**data)
        ceilings = cls()
        for name in fields:
            value = getattr(limits, name)
            if type(value) is not int or value < 0 or value > getattr(ceilings, name):
                raise ContractError("limit_exceeded", name)
        if not 1 <= limits.semantic_repairs <= 3:
            raise ContractError("limit_exceeded", "semantic_repairs")
        return limits


@dataclass(frozen=True)
class TaskIntakeV1:
    contract_version: int
    request_id: str
    repository_id: str
    source_type: str
    source_id: str
    source_digest: str
    route_id: str
    change_id: str
    exact_base_sha: str
    spec_digest: str
    architecture: ArchitectureHandoffV1
    governance: GovernanceHandoffV1
    policy_digest: str
    m0_authority: M0AuthorityV1
    acceptance_ids: tuple[str, ...]
    limits: TaskLimitsV1
    intent_digest: str
    idempotency_key: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, now: datetime | None = None) -> "TaskIntakeV1":
        input_fields = set(cls.__dataclass_fields__) - {"intent_digest", "idempotency_key"}
        _closed(data, input_fields)
        if data["contract_version"] != 1:
            raise ContractError("unsupported_version", "intake")
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        architecture = ArchitectureHandoffV1.from_dict(data["architecture"])
        governance = GovernanceHandoffV1.from_dict(data["governance"])
        if (
            architecture.architecture_digest != governance.architecture_digest
            or architecture.exact_base_sha != governance.exact_base_sha
            or architecture.exact_head_sha != governance.exact_head_sha
        ):
            raise ContractError("handoff_mismatch")
        authority = M0AuthorityV1.from_dict(data["m0_authority"], now)
        if authority.exact_head_sha and authority.exact_head_sha != governance.exact_head_sha:
            raise ContractError("handoff_mismatch", "m0 exact head")
        policy_digest = _hex(data["policy_digest"], "policy_digest", HEX64)
        if authority.check_name and not authority.check_name.endswith("@" + policy_digest[:12]):
            raise ContractError("m0_policy_mismatch")
        acceptance = data["acceptance_ids"]
        if (
            not isinstance(acceptance, list)
            or not acceptance
            or acceptance != sorted(set(acceptance))
            or any(not isinstance(item, str) or not ACCEPTANCE_ID.fullmatch(item) for item in acceptance)
        ):
            raise ContractError("acceptance_ids")
        source_type = data["source_type"]
        if source_type not in {"manual", "api", "github_issue_projection"}:
            raise ContractError("source_type")
        normalized = {
            "contract_version": 1,
            "request_id": _id(data["request_id"], "request_id"),
            "repository_id": _id(data["repository_id"], "repository_id"),
            "source_type": source_type,
            "source_id": _id(data["source_id"], "source_id"),
            "source_digest": _hex(data["source_digest"], "source_digest", HEX64),
            "route_id": _id(data["route_id"], "route_id"),
            "change_id": _id(data["change_id"], "change_id"),
            "exact_base_sha": _hex(data["exact_base_sha"], "exact_base_sha", HEX40),
            "spec_digest": _hex(data["spec_digest"], "spec_digest", HEX64),
            "architecture": architecture,
            "governance": governance,
            "policy_digest": policy_digest,
            "m0_authority": authority,
            "acceptance_ids": tuple(acceptance),
            "limits": TaskLimitsV1.from_dict(data["limits"]),
        }
        intent_digest = canonical_digest(normalized)
        work_identity = {
            key: value
            for key, value in normalized.items()
            if key not in {"request_id", "m0_authority"}
        }
        idempotency_key = canonical_digest(
            {
                "contract": "adaptive-factory.work-identity/v1",
                "work": work_identity,
            }
        )
        return cls(**normalized, intent_digest=intent_digest, idempotency_key=idempotency_key)

    def to_dict(self) -> dict[str, Any]:
        return _canonical(asdict(self))
