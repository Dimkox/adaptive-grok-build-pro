from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_B64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_RFC3339_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_PROMOTION_REPOSITORY_RE = re.compile(r"^[a-z0-9_.-]+/[a-z0-9_.-]+$")
_ENVIRONMENT_RE = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


def canonical_json(data: Any) -> bytes:
    """Return the only JSON representation used for hashes and signatures."""
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def require_sha(value: str, field_name: str) -> str:
    normalized = str(value).strip().lower()
    if not _SHA_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be an exact lowercase 40-hex SHA")
    return normalized


def require_digest(value: str, field_name: str) -> str:
    normalized = str(value).strip().lower()
    if not _DIGEST_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase 64-hex SHA-256 digest")
    return normalized


def require_repository(value: str) -> str:
    normalized = str(value).strip()
    if not _REPOSITORY_RE.fullmatch(normalized):
        raise ValueError("repository must be owner/name")
    return normalized


def _strict_mapping(data: Mapping[str, Any], fields: set[str], label: str) -> None:
    if not isinstance(data, Mapping) or set(data) != fields:
        raise ValueError(f"malformed {label}")


def _reject_non_finite_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def require_uuid_v1_5(value: str, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or not _UUID_RE.fullmatch(value)
        or str(uuid.UUID(value)) != value
    ):
        raise ValueError(f"{field_name} must be a canonical UUID")
    return value


_require_uuid = require_uuid_v1_5


def _require_base64url(value: str, field_name: str, decoded_length: int) -> str:
    expected_length = {32: 43, 64: 86}.get(decoded_length)
    if not isinstance(value, str) or (expected_length is not None and len(value) != expected_length) or not _B64URL_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be unpadded base64url")
    try:
        decoded = base64.b64decode(
            value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
        )
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError(f"{field_name} must be unpadded base64url") from exc
    canonical = base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=")
    if len(decoded) != decoded_length or canonical != value:
        raise ValueError(f"{field_name} must encode exactly {decoded_length} bytes")
    return value


def _require_rfc3339_z(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _RFC3339_Z_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be UTC RFC 3339 seconds with Z")
    parse_datetime(value)
    return value


def _require_text(value: str, field_name: str, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or not value
        or len(value.encode("utf-8")) > maximum
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ValueError(f"{field_name} is invalid")
    return value


def _require_promotion_repository(value: str) -> str:
    if (
        not isinstance(value, str)
        or not _PROMOTION_REPOSITORY_RE.fullmatch(value)
        or any(part in {'.', '..'} for part in value.split('/'))
    ):
        raise ValueError("repository must be lowercase owner/name")
    return value


def _require_exact_sha(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be an exact lowercase 40-hex SHA")
    return value


def _require_exact_digest(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase 64-hex SHA-256 digest")
    return value


def _require_environment(value: str) -> str:
    if not isinstance(value, str) or not _ENVIRONMENT_RE.fullmatch(value):
        raise ValueError("target_environment must be a lowercase identifier")
    return value


_PROMOTION_FIELDS = {"schema_version", "promotion_id", "nonce", "actor", "key_id", "repository", "merged_commit_sha", "artifact_sha256", "target_environment", "policy_epoch", "source_attestation_id", "reason", "issued_at", "expires_at"}
_PROMOTION_ENVELOPE_FIELDS = {"payload", "algorithm", "signature"}
_PROTECTED_BRANCH_ATTESTATION_FIELDS = {"schema_version", "source_attestation_id", "merge_fact_id", "repository", "protected_ref", "merged_commit_sha", "policy_epoch", "artifact_sha256", "runner_digest", "holdout_digest", "image_digest", "result", "issued_at", "key_id"}
_PROTECTED_BRANCH_ATTESTATION_ENVELOPE_FIELDS = {"payload", "algorithm", "signature"}


@dataclass(frozen=True)
class JobRequest:
    repository: str
    pr_number: int
    base_sha: str
    head_sha: str
    head_ref: str
    base_ref: str
    pipeline: str = "pull_request"

    def __post_init__(self) -> None:
        object.__setattr__(self, "repository", require_repository(self.repository))
        if isinstance(self.pr_number, bool) or self.pr_number <= 0:
            raise ValueError("pr_number must be positive")
        object.__setattr__(self, "base_sha", require_sha(self.base_sha, "base_sha"))
        object.__setattr__(self, "head_sha", require_sha(self.head_sha, "head_sha"))
        if not self.head_ref.strip() or not self.base_ref.strip() or not self.pipeline.strip():
            raise ValueError("refs and pipeline must be non-empty")

    def idempotency_key(self, policy_digest: str) -> str:
        digest = require_digest(policy_digest, "policy_digest")
        return hashlib.sha256(
            canonical_json(
                {
                    "repository": self.repository,
                    "pr_number": self.pr_number,
                    "head_sha": self.head_sha,
                    "pipeline": self.pipeline,
                    "policy_digest": digest,
                }
            )
        ).hexdigest()


@dataclass
class Job:
    job_id: str
    repository: str
    pr_number: int
    base_sha: str
    head_sha: str
    head_ref: str
    base_ref: str
    pipeline: str
    policy_digest: str
    idempotency_key: str
    status: str = "queued"
    attempts: int = 0
    max_attempts: int = 3
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    failure_code: str | None = None
    result: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for name in ("lease_expires_at", "created_at", "updated_at", "started_at", "finished_at"):
            value = data[name]
            data[name] = value.isoformat() if value is not None else None
        return data


@dataclass(frozen=True)
class ApprovalPayload:
    schema_version: int
    approval_id: str
    nonce: str
    actor: str
    key_id: str
    repository: str
    pr_number: int
    base_sha: str
    head_sha: str
    policy_digest: str
    scope: str
    reason: str
    issued_at: str
    expires_at: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("unsupported approval schema_version")
        if not self.approval_id.strip() or len(self.nonce.strip()) < 16:
            raise ValueError("approval_id and a strong nonce are required")
        if not self.actor.strip() or not self.key_id.strip():
            raise ValueError("approval actor and key_id are required")
        object.__setattr__(self, "repository", require_repository(self.repository))
        if isinstance(self.pr_number, bool) or self.pr_number <= 0:
            raise ValueError("pr_number must be positive")
        object.__setattr__(self, "base_sha", require_sha(self.base_sha, "base_sha"))
        object.__setattr__(self, "head_sha", require_sha(self.head_sha, "head_sha"))
        object.__setattr__(self, "policy_digest", require_digest(self.policy_digest, "policy_digest"))
        if not self.scope.strip() or not self.reason.strip():
            raise ValueError("scope and reason are required")
        issued = parse_datetime(self.issued_at)
        expires = parse_datetime(self.expires_at)
        if expires <= issued:
            raise ValueError("approval expiry must be after issue time")

    @classmethod
    def new(
        cls,
        *,
        actor: str,
        key_id: str,
        repository: str,
        pr_number: int,
        base_sha: str,
        head_sha: str,
        policy_digest: str,
        scope: str,
        reason: str,
        now: datetime | None = None,
        ttl_seconds: int = 900,
    ) -> "ApprovalPayload":
        if isinstance(ttl_seconds, bool) or ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        current = (now or utc_now()).astimezone(timezone.utc)
        return cls(
            schema_version=1,
            approval_id=str(uuid.uuid4()),
            nonce=secrets.token_urlsafe(24),
            actor=actor.strip(),
            key_id=key_id.strip(),
            repository=repository,
            pr_number=pr_number,
            base_sha=base_sha,
            head_sha=head_sha,
            policy_digest=policy_digest,
            scope=scope.strip(),
            reason=reason.strip(),
            issued_at=current.isoformat(),
            expires_at=(current + timedelta(seconds=ttl_seconds)).isoformat(),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ApprovalPayload":
        try:
            return cls(**{name: data[name] for name in cls.__dataclass_fields__})
        except (KeyError, TypeError) as exc:
            raise ValueError("malformed approval payload") from exc

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class ApprovalEnvelope:
    payload: ApprovalPayload
    signature: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ApprovalEnvelope":
        try:
            signature = str(data["signature"]).strip()
            if not signature:
                raise ValueError("signature is empty")
            return cls(payload=ApprovalPayload.from_dict(data["payload"]), signature=signature)
        except (KeyError, TypeError) as exc:
            raise ValueError("malformed approval envelope") from exc

    def to_dict(self) -> dict[str, Any]:
        return {"payload": self.payload.to_dict(), "signature": self.signature}


@dataclass(frozen=True)
class AttestationPayload:
    schema_version: int
    attestation_id: str
    job_id: str
    repository: str
    pr_number: int
    base_sha: str
    head_sha: str
    policy_digest: str
    status: str
    command_results: tuple[dict[str, Any], ...]
    changed_files: tuple[str, ...]
    approved_scopes: tuple[str, ...]
    started_at: str
    completed_at: str
    key_id: str

    def __post_init__(self) -> None:
        if isinstance(self.schema_version, bool) or self.schema_version != 1:
            raise ValueError("unsupported attestation schema_version")
        if not self.attestation_id.strip() or not self.job_id.strip() or not self.key_id.strip():
            raise ValueError("attestation identity fields are required")
        object.__setattr__(self, "repository", require_repository(self.repository))
        if isinstance(self.pr_number, bool) or self.pr_number <= 0:
            raise ValueError("pr_number must be positive")
        object.__setattr__(self, "base_sha", require_sha(self.base_sha, "base_sha"))
        object.__setattr__(self, "head_sha", require_sha(self.head_sha, "head_sha"))
        object.__setattr__(self, "policy_digest", require_digest(self.policy_digest, "policy_digest"))
        if self.status not in {"passed", "failed"}:
            raise ValueError("attestation status must be passed or failed")
        if parse_datetime(self.completed_at) < parse_datetime(self.started_at):
            raise ValueError("attestation completion precedes start")
        object.__setattr__(
            self,
            "changed_files",
            tuple(sorted({str(item).replace("\\", "/").lstrip("./") for item in self.changed_files})),
        )
        object.__setattr__(
            self,
            "approved_scopes",
            tuple(sorted({str(item).strip() for item in self.approved_scopes if str(item).strip()})),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AttestationPayload":
        try:
            values = {name: data[name] for name in cls.__dataclass_fields__}
            values["command_results"] = tuple(dict(item) for item in values["command_results"])
            values["changed_files"] = tuple(str(item) for item in values["changed_files"])
            values["approved_scopes"] = tuple(str(item) for item in values["approved_scopes"])
            return cls(**values)
        except (KeyError, TypeError) as exc:
            raise ValueError("malformed attestation payload") from exc

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["command_results"] = list(self.command_results)
        data["changed_files"] = list(self.changed_files)
        data["approved_scopes"] = list(self.approved_scopes)
        return data


@dataclass(frozen=True)
class AttestationEnvelope:
    payload: AttestationPayload
    signature: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AttestationEnvelope":
        try:
            signature = str(data["signature"]).strip()
            if not signature:
                raise ValueError("signature is empty")
            return cls(payload=AttestationPayload.from_dict(data["payload"]), signature=signature)
        except (KeyError, TypeError) as exc:
            raise ValueError("malformed attestation envelope") from exc

    def to_dict(self) -> dict[str, Any]:
        return {"payload": self.payload.to_dict(), "signature": self.signature}


@dataclass(frozen=True)
class PromotionPayload:
    schema_version: int
    promotion_id: str
    nonce: str
    actor: str
    key_id: str
    repository: str
    merged_commit_sha: str
    artifact_sha256: str
    target_environment: str
    policy_epoch: str
    source_attestation_id: str
    reason: str
    issued_at: str
    expires_at: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("unsupported promotion schema_version")
        _require_uuid(self.promotion_id, "promotion_id")
        _require_base64url(self.nonce, "nonce", 32)
        object.__setattr__(self, "actor", _require_text(self.actor, "actor", 128))
        object.__setattr__(self, "key_id", _require_text(self.key_id, "key_id", 128))
        object.__setattr__(self, "repository", _require_promotion_repository(self.repository))
        if not isinstance(self.merged_commit_sha, str) or not _SHA_RE.fullmatch(self.merged_commit_sha):
            raise ValueError("merged_commit_sha must be an exact lowercase 40-hex SHA")
        if not isinstance(self.artifact_sha256, str) or not _DIGEST_RE.fullmatch(self.artifact_sha256):
            raise ValueError("artifact_sha256 must be a lowercase 64-hex SHA-256 digest")
        if not isinstance(self.policy_epoch, str) or not _DIGEST_RE.fullmatch(self.policy_epoch):
            raise ValueError("policy_epoch must be a lowercase 64-hex SHA-256 digest")
        object.__setattr__(self, "source_attestation_id", _require_uuid(self.source_attestation_id, "source_attestation_id"))
        object.__setattr__(self, "target_environment", _require_environment(self.target_environment))
        object.__setattr__(self, "reason", _require_text(self.reason, "reason", 512))
        issued = parse_datetime(_require_rfc3339_z(self.issued_at, "issued_at"))
        expires = parse_datetime(_require_rfc3339_z(self.expires_at, "expires_at"))
        if expires <= issued:
            raise ValueError("promotion expiry must be after issue time")

    @classmethod
    def new(
        cls,
        *,
        actor: str,
        key_id: str,
        repository: str,
        merged_commit_sha: str,
        artifact_sha256: str,
        target_environment: str,
        policy_epoch: str,
        source_attestation_id: str,
        reason: str,
        now: datetime | None = None,
        ttl_seconds: int = 900,
    ) -> "PromotionPayload":
        if isinstance(ttl_seconds, bool) or ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        current = (now or utc_now()).astimezone(timezone.utc).replace(microsecond=0)
        return cls(
            schema_version=1,
            promotion_id=str(uuid.uuid4()),
            nonce=base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("="),
            actor=actor,
            key_id=key_id,
            repository=repository,
            merged_commit_sha=merged_commit_sha,
            artifact_sha256=artifact_sha256,
            target_environment=target_environment,
            policy_epoch=policy_epoch,
            source_attestation_id=source_attestation_id,
            reason=reason,
            issued_at=current.strftime("%Y-%m-%dT%H:%M:%SZ"),
            expires_at=(current + timedelta(seconds=ttl_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PromotionPayload":
        _strict_mapping(data, _PROMOTION_FIELDS, "promotion payload")
        return cls(**dict(data))

    @classmethod
    def from_json(cls, raw: str) -> "PromotionPayload":
        return cls.from_dict(json.loads(raw, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_non_finite_json_constant))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class PromotionEnvelope:
    payload: PromotionPayload
    algorithm: str
    signature: str

    def __post_init__(self) -> None:
        if not isinstance(self.payload, PromotionPayload) or self.algorithm != "Ed25519":
            raise ValueError("malformed promotion envelope")
        _require_base64url(self.signature, "signature", 64)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PromotionEnvelope":
        _strict_mapping(data, _PROMOTION_ENVELOPE_FIELDS, "promotion envelope")
        return cls(PromotionPayload.from_dict(data["payload"]), data["algorithm"], data["signature"])

    @classmethod
    def from_json(cls, raw: str) -> "PromotionEnvelope":
        return cls.from_dict(json.loads(raw, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_non_finite_json_constant))

    def to_dict(self) -> dict[str, Any]:
        return {"payload": self.payload.to_dict(), "algorithm": self.algorithm, "signature": self.signature}

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class PromotionExpectedBinding:
    repository: str
    merged_commit_sha: str
    artifact_sha256: str
    target_environment: str
    policy_epoch: str
    source_attestation_id: str

    def __post_init__(self) -> None:
        _require_promotion_repository(self.repository)
        _require_exact_sha(self.merged_commit_sha, "merged_commit_sha")
        _require_exact_digest(self.artifact_sha256, "artifact_sha256")
        _require_environment(self.target_environment)
        _require_exact_digest(self.policy_epoch, "policy_epoch")
        require_uuid_v1_5(self.source_attestation_id, "source_attestation_id")


@dataclass(frozen=True)
class PromotionEvent:
    schema_version: int
    event_id: str
    event_type: str
    occurred_at: str
    promotion_id: str | None
    correlation_id: str
    operation_id: str | None
    actor: str | None
    key_id: str | None
    repository: str | None
    merged_commit_sha: str | None
    artifact_sha256: str | None
    target_environment: str | None
    policy_epoch: str | None
    outcome: str
    reason_code: str
    details: dict[str, str | int | bool | None]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("unsupported promotion event schema_version")
        _require_uuid(self.event_id, "event_id")
        if self.promotion_id is not None:
            _require_uuid(self.promotion_id, "promotion_id")
        if self.event_type not in {"promotion.accepted", "promotion.rejected", "promotion.consumed", "deployment.completed", "deployment.failed", "deployment.reconciled"}:
            raise ValueError("invalid promotion event type")
        if self.operation_id is not None:
            _require_uuid(self.operation_id, "operation_id")
        _require_text(self.correlation_id, "correlation_id", 128)
        for field_name, maximum in (("actor", 128), ("key_id", 128)):
            value = getattr(self, field_name)
            if value is not None:
                _require_text(value, field_name, maximum)
        if self.repository is not None:
            _require_promotion_repository(self.repository)
        if self.merged_commit_sha is not None:
            _require_exact_sha(self.merged_commit_sha, "merged_commit_sha")
        if self.artifact_sha256 is not None:
            _require_exact_digest(self.artifact_sha256, "artifact_sha256")
        if self.target_environment is not None:
            _require_environment(self.target_environment)
        if self.policy_epoch is not None:
            _require_exact_digest(self.policy_epoch, "policy_epoch")
        if self.outcome not in {"accepted", "rejected", "consumed", "completed", "failed", "reconciled"}:
            raise ValueError("invalid promotion event outcome")
        if not re.fullmatch(r"^[a-z][a-z0-9_]*$", self.reason_code) or len(self.reason_code) > 128:
            raise ValueError("invalid promotion event reason_code")
        if not isinstance(self.details, dict) or len(self.details) > 16:
            raise ValueError("invalid promotion event details")
        for key, value in self.details.items():
            if not isinstance(key, str) or not re.fullmatch(r"^[a-z][a-z0-9_]{0,63}$", key):
                raise ValueError("invalid promotion event details")
            if value is None or isinstance(value, bool):
                continue
            if type(value) is int and -(2**63) <= value <= 2**63 - 1:
                continue
            if isinstance(value, str):
                _require_text(value, f"details.{key}", 512)
                continue
            raise ValueError("invalid promotion event details")
        _require_rfc3339_z(self.occurred_at, "occurred_at")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PromotionEvent":
        _strict_mapping(data, {"schema_version", "event_id", "event_type", "occurred_at", "promotion_id", "correlation_id", "operation_id", "actor", "key_id", "repository", "merged_commit_sha", "artifact_sha256", "target_environment", "policy_epoch", "outcome", "reason_code", "details"}, "promotion event")
        return cls(**dict(data))

    @classmethod
    def from_json(cls, raw: str) -> "PromotionEvent":
        return cls.from_dict(json.loads(raw, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_non_finite_json_constant))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProtectedBranchAttestationPayload:
    schema_version: int
    source_attestation_id: str
    merge_fact_id: str
    repository: str
    protected_ref: str
    merged_commit_sha: str
    policy_epoch: str
    runner_digest: str
    holdout_digest: str
    image_digest: str
    artifact_sha256: str
    result: str
    issued_at: str
    key_id: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("invalid protected-branch attestation")
        _require_uuid(self.source_attestation_id, "source_attestation_id")
        _require_uuid(self.merge_fact_id, "merge_fact_id")
        _require_promotion_repository(self.repository)
        if (
            not isinstance(self.protected_ref, str)
            or not self.protected_ref.startswith("refs/heads/")
            or self.protected_ref == "refs/heads/"
            or len(self.protected_ref.encode("utf-8")) > 255
        ):
            raise ValueError("invalid protected ref")
        _require_exact_sha(self.merged_commit_sha, "merged_commit_sha")
        for field_name in (
            "policy_epoch",
            "runner_digest",
            "holdout_digest",
            "image_digest",
            "artifact_sha256",
        ):
            _require_exact_digest(getattr(self, field_name), field_name)
        if self.result != "passed":
            raise ValueError("protected-branch attestation must be passed")
        _require_text(self.key_id, "key_id", 128)
        _require_rfc3339_z(self.issued_at, "issued_at")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProtectedBranchAttestationPayload":
        _strict_mapping(data, _PROTECTED_BRANCH_ATTESTATION_FIELDS, "protected-branch attestation")
        return cls(**dict(data))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class ProtectedBranchAttestationEnvelope:
    payload: ProtectedBranchAttestationPayload
    algorithm: str
    signature: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.payload, ProtectedBranchAttestationPayload)
            or self.algorithm != "Ed25519"
        ):
            raise ValueError("malformed protected-branch attestation envelope")
        _require_base64url(self.signature, "signature", 64)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProtectedBranchAttestationEnvelope":
        _strict_mapping(
            data,
            _PROTECTED_BRANCH_ATTESTATION_ENVELOPE_FIELDS,
            "protected-branch attestation envelope",
        )
        return cls(ProtectedBranchAttestationPayload.from_dict(data["payload"]), data["algorithm"], data["signature"])

    @classmethod
    def from_json(cls, raw: str) -> "ProtectedBranchAttestationEnvelope":
        return cls.from_dict(json.loads(raw, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_non_finite_json_constant))

    def to_dict(self) -> dict[str, Any]:
        return {"payload": self.payload.to_dict(), "algorithm": self.algorithm, "signature": self.signature}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


@dataclass(frozen=True)
class Checkout:
    path: Path
    changed_files: tuple[str, ...]


@dataclass(frozen=True)
class CommandResult:
    name: str
    status: str
    exit_code: int
    duration_seconds: float
    stdout_tail: str
    stderr_tail: str
    output_sha256: str

    def __post_init__(self) -> None:
        if not self.name.strip() or self.status not in {"pass", "fail"}:
            raise ValueError("invalid command result")
        if self.duration_seconds < 0:
            raise ValueError("duration cannot be negative")
        require_digest(self.output_sha256, "output_sha256")

    def attestation_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "exit_code": self.exit_code,
            "duration_seconds": round(self.duration_seconds, 6),
            "output_sha256": self.output_sha256,
        }


@dataclass(frozen=True)
class RunOutcome:
    job_id: str
    status: str
    details: dict[str, Any]
