from __future__ import annotations

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
_AC_RE = re.compile(r"^AC-[0-9]{3,6}$")
_COVERAGE_SPEC_RE = re.compile(r"^engineering/changes/[^/]{1,256}/change-spec\.yaml$")


def empty_criterion_coverage() -> dict[str, Any]:
    return {"spec_count": 0, "criterion_total": 0, "criterion_mapped": 0, "unmapped_ids": []}


def _valid_coverage_id(value: str) -> bool:
    if _AC_RE.fullmatch(value):
        return True
    path, separator, criterion_id = value.rpartition("#")
    return bool(
        separator
        and len(value) <= 512
        and _COVERAGE_SPEC_RE.fullmatch(path)
        and _AC_RE.fullmatch(criterion_id)
        and "\0" not in path
        and not any(0xD800 <= ord(character) <= 0xDFFF for character in path)
    )


def normalize_criterion_coverage(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {"spec_count", "criterion_total", "criterion_mapped", "unmapped_ids"}
    if set(value) != required:
        raise ValueError("criterion_coverage must contain exact bounded keys")
    numbers: dict[str, int] = {}
    for key in ("spec_count", "criterion_total", "criterion_mapped"):
        number = value[key]
        if isinstance(number, bool) or not isinstance(number, int) or not 0 <= number <= 10_000:
            raise ValueError(f"criterion_coverage.{key} must be a bounded nonnegative integer")
        numbers[key] = number
    if numbers["spec_count"] > 100 or numbers["criterion_mapped"] > numbers["criterion_total"]:
        raise ValueError("criterion_coverage counts are inconsistent")
    raw_ids = value["unmapped_ids"]
    if not isinstance(raw_ids, list) or len(raw_ids) > 500 or not all(isinstance(item, str) and _valid_coverage_id(item) for item in raw_ids):
        raise ValueError("criterion_coverage.unmapped_ids must be bounded stable AC IDs")
    ids = sorted(set(raw_ids))
    if len(ids) != len(raw_ids) or len(ids) != numbers["criterion_total"] - numbers["criterion_mapped"]:
        raise ValueError("criterion_coverage unmapped IDs do not match counts")
    return {**numbers, "unmapped_ids": ids}


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
        if self.schema_version != 1:
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
    spec_digest: str | None = None
    criterion_coverage: dict[str, Any] = field(default_factory=empty_criterion_coverage)
    _metadata_present: bool = field(default=True, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.schema_version != 1:
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
            tuple(sorted({str(item) for item in self.changed_files})),
        )
        object.__setattr__(
            self,
            "approved_scopes",
            tuple(sorted({str(item).strip() for item in self.approved_scopes if str(item).strip()})),
        )
        if self.spec_digest is not None:
            object.__setattr__(self, "spec_digest", require_digest(self.spec_digest, "spec_digest"))
        if not isinstance(self.criterion_coverage, Mapping):
            raise ValueError("criterion_coverage must be an object")
        object.__setattr__(self, "criterion_coverage", normalize_criterion_coverage(self.criterion_coverage))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AttestationPayload":
        try:
            core = (
                "schema_version", "attestation_id", "job_id", "repository", "pr_number",
                "base_sha", "head_sha", "policy_digest", "status", "command_results",
                "changed_files", "approved_scopes", "started_at", "completed_at", "key_id",
            )
            values = {name: data[name] for name in core}
            values["command_results"] = tuple(dict(item) for item in values["command_results"])
            values["changed_files"] = tuple(str(item) for item in values["changed_files"])
            values["approved_scopes"] = tuple(str(item) for item in values["approved_scopes"])
            present = "spec_digest" in data or "criterion_coverage" in data
            if present and not {"spec_digest", "criterion_coverage"}.issubset(data):
                raise ValueError("attestation metadata fields must be present together")
            values["spec_digest"] = data.get("spec_digest")
            values["criterion_coverage"] = data.get("criterion_coverage", empty_criterion_coverage())
            values["_metadata_present"] = present
            return cls(**values)
        except (KeyError, TypeError) as exc:
            raise ValueError("malformed attestation payload") from exc

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("_metadata_present", None)
        if not self._metadata_present:
            data.pop("spec_digest", None)
            data.pop("criterion_coverage", None)
        data["command_results"] = list(self.command_results)
        data["changed_files"] = list(self.changed_files)
        data["approved_scopes"] = list(self.approved_scopes)
        return data


@dataclass(frozen=True)
class AttestationEnvelope:
    payload: AttestationPayload
    signature: str
    _signed_payload: dict[str, Any] | None = field(default=None, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AttestationEnvelope":
        try:
            signature = str(data["signature"]).strip()
            if not signature:
                raise ValueError("signature is empty")
            original = dict(data["payload"])
            return cls(payload=AttestationPayload.from_dict(original), signature=signature, _signed_payload=original)
        except (KeyError, TypeError) as exc:
            raise ValueError("malformed attestation envelope") from exc

    def to_dict(self) -> dict[str, Any]:
        return {"payload": dict(self._signed_payload) if self._signed_payload is not None else self.payload.to_dict(), "signature": self.signature}


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
