from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import PurePosixPath
import re
import unicodedata
from typing import Any, ClassVar, Mapping, Self

from .contracts import HEX40, HEX64, canonical_digest, canonical_json


SITE_ID = "therealaidarkfactory.online"
CANONICAL_ORIGIN = "https://therealaidarkfactory.online/"
MEDIA_TYPES = {
    "text": frozenset({"text/plain"}),
    "audio": frozenset({"audio/wav", "audio/mpeg", "audio/ogg"}),
    "image": frozenset({"image/png", "image/jpeg", "image/webp"}),
    "pdf": frozenset({"application/pdf"}),
    "docx": frozenset(
        {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    ),
}
MAX_INPUT_BYTES = {
    "text": 1_048_576,
    "audio": 25 * 1_048_576,
    "image": 10 * 1_048_576,
    "pdf": 20 * 1_048_576,
    "docx": 10 * 1_048_576,
}
MAX_JSON_BYTES = 1_048_576
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}$")
_MEDIA_TYPE = re.compile(r"^[a-z0-9.+-]+/[a-z0-9.+-]+$")
_LOCALE = re.compile(r"^[a-z]{2}(?:-[A-Z]{2})?$")
_VERSION = re.compile(r"^[0-9]+(?:\.[0-9]+){1,2}(?:[-+][A-Za-z0-9.-]+)?$")
_PROHIBITED_CONTENT = re.compile(
    r"(?i)(?:<|>|javascript:|data:|shell\.exec|git\s+push|system\s+prompt|use\s+tool|credential|password)"
)
_SECTION_KINDS = frozenset({"hero", "proof", "features", "workflow", "faq", "cta", "footer", "roadmap"})


class LandingContractError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def _object(data: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(data, Mapping) or any(not isinstance(key, str) for key in data):
        raise LandingContractError("invalid_object", name)
    return data


def _closed(data: Mapping[str, Any], fields: set[str]) -> None:
    unknown = set(data) - fields
    missing = fields - set(data)
    if unknown:
        raise LandingContractError("unknown_fields", ",".join(sorted(unknown)))
    if missing:
        raise LandingContractError("missing_fields", ",".join(sorted(missing)))


def _text(value: Any, name: str, maximum: int, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not value and not allow_empty):
        raise LandingContractError("invalid_text", name)
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise LandingContractError("invalid_text", name) from exc
    if len(encoded) > maximum or unicodedata.normalize("NFC", value) != value:
        raise LandingContractError("invalid_text", name)
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise LandingContractError("invalid_text", name)
    return value


def _plain(value: Any, name: str, maximum: int, *, allow_empty: bool = False) -> str:
    text = _text(value, name, maximum, allow_empty=allow_empty)
    if _PROHIBITED_CONTENT.search(text):
        raise LandingContractError("unsafe_content", name)
    return text


def _identifier(value: Any, name: str) -> str:
    value = _text(value, name, 128)
    if not _IDENTIFIER.fullmatch(value):
        raise LandingContractError("invalid_identifier", name)
    return value


def _hex(value: Any, name: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise LandingContractError("invalid_sha" if pattern is HEX40 else "invalid_digest", name)
    return value


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise LandingContractError("invalid_integer", name)
    return value


def _time(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise LandingContractError("invalid_time", name)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LandingContractError("invalid_time", name) from exc
    if parsed.tzinfo is None:
        raise LandingContractError("invalid_time", name)
    return parsed.astimezone(timezone.utc)


def _sorted_unique(
    values: Any,
    name: str,
    parser,
    *,
    maximum: int = 32,
    allow_empty: bool = True,
) -> tuple[Any, ...]:
    if not isinstance(values, list) or len(values) > maximum or (not values and not allow_empty):
        raise LandingContractError(name)
    parsed = tuple(parser(item) for item in values)
    keys = tuple(json.dumps(item.to_dict() if hasattr(item, "to_dict") else item, sort_keys=True) for item in parsed)
    if keys != tuple(sorted(set(keys))):
        raise LandingContractError(name)
    return parsed


def strict_json_object(raw: str | bytes | bytearray, *, maximum: int = MAX_JSON_BYTES) -> Mapping[str, Any]:
    if not isinstance(raw, (str, bytes, bytearray)):
        raise LandingContractError("invalid_json")
    try:
        payload = raw.encode("utf-8") if isinstance(raw, str) else bytes(raw)
        text = payload.decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError) as exc:
        raise LandingContractError("invalid_json") from exc
    if len(payload) > maximum:
        raise LandingContractError("json_too_large")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise LandingContractError("duplicate_json_key", key)
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise LandingContractError("nonfinite_json", value)

    try:
        decoded = json.loads(text, object_pairs_hook=pairs, parse_constant=reject_constant)
    except LandingContractError:
        raise
    except json.JSONDecodeError as exc:
        raise LandingContractError("invalid_json") from exc
    if not isinstance(decoded, dict):
        raise LandingContractError("invalid_json_object")
    return decoded


def landing_digest(kind: str, value: Mapping[str, Any]) -> str:
    if not isinstance(kind, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", kind):
        raise LandingContractError("invalid_digest_domain")
    return canonical_digest({"contract": f"adaptive-factory.landing-{kind}/v1", **value})


def _to_dict(value: Any) -> dict[str, Any]:
    return json.loads(canonical_json(asdict(value)))


class _LandingRecord:
    DOMAIN: ClassVar[str]
    DIGEST_FIELD: ClassVar[str]

    @classmethod
    def from_json(cls, raw: str | bytes | bytearray) -> Self:
        return cls.from_dict(strict_json_object(raw))

    def to_dict(self) -> dict[str, Any]:
        return _to_dict(self)

    @property
    def digest(self) -> str:
        return getattr(self, self.DIGEST_FIELD)


def _validate_supplied(record: _LandingRecord, supplied: Any, name: str) -> None:
    if supplied != record.digest:
        raise LandingContractError("digest_mismatch", name)


@dataclass(frozen=True)
class LandingInputV1(_LandingRecord):
    schema_version: int
    job_id: str
    tenant_id: str
    repository_id: str
    exact_base_sha: str
    exact_base_tree: str
    site_id: str
    media_kind: str
    media_type: str
    byte_length: int
    content_sha256: str
    quarantine_ref_digest: str
    received_at: datetime
    expires_at: datetime
    input_digest: str

    DOMAIN = "input"
    DIGEST_FIELD = "input_digest"

    @classmethod
    def from_facts(cls, data: Mapping[str, Any]) -> "LandingInputV1":
        data = _object(data, "landing_input")
        fields = set(cls.__dataclass_fields__) - {"input_digest"}
        _closed(data, fields)
        if data["schema_version"] != 1:
            raise LandingContractError("unsupported_version", "landing_input")
        kind = data["media_kind"]
        media_type = data["media_type"]
        if kind not in MEDIA_TYPES or media_type not in MEDIA_TYPES[kind]:
            raise LandingContractError("media_type")
        length = _integer(data["byte_length"], "byte_length", 1, MAX_INPUT_BYTES[kind])
        received = _time(data["received_at"], "received_at")
        expires = _time(data["expires_at"], "expires_at")
        lifetime = (expires - received).total_seconds()
        if not 0 < lifetime <= 86_400:
            raise LandingContractError("input_expiry")
        values = {
            "schema_version": 1,
            "job_id": _identifier(data["job_id"], "job_id"),
            "tenant_id": _identifier(data["tenant_id"], "tenant_id"),
            "repository_id": _identifier(data["repository_id"], "repository_id"),
            "exact_base_sha": _hex(data["exact_base_sha"], "exact_base_sha", HEX40),
            "exact_base_tree": _hex(data["exact_base_tree"], "exact_base_tree", HEX40),
            "site_id": _identifier(data["site_id"], "site_id"),
            "media_kind": kind,
            "media_type": media_type,
            "byte_length": length,
            "content_sha256": _hex(data["content_sha256"], "content_sha256", HEX64),
            "quarantine_ref_digest": _hex(data["quarantine_ref_digest"], "quarantine_ref_digest", HEX64),
            "received_at": received,
            "expires_at": expires,
        }
        if values["site_id"] != SITE_ID:
            raise LandingContractError("site_id")
        digest = landing_digest(cls.DOMAIN, json.loads(canonical_json(values)))
        return cls(**values, input_digest=digest)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LandingInputV1":
        data = _object(data, "landing_input")
        _closed(data, set(cls.__dataclass_fields__))
        result = cls.from_facts({key: data[key] for key in data if key != "input_digest"})
        _validate_supplied(result, data["input_digest"], "input_digest")
        return result


@dataclass(frozen=True)
class LandingSectionV1:
    kind: str
    heading: str
    body: str
    items: tuple[str, ...]
    cta_label: str
    cta_path: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LandingSectionV1":
        data = _object(data, "landing_section")
        _closed(data, set(cls.__dataclass_fields__))
        kind = data["kind"]
        if kind not in _SECTION_KINDS:
            raise LandingContractError("section_kind")
        items = _sorted_unique(data["items"], "section_items", lambda item: _plain(item, "item", 512), maximum=12)
        cta_label = _plain(data["cta_label"], "cta_label", 128, allow_empty=True)
        cta_path = _text(data["cta_path"], "cta_path", 256, allow_empty=True)
        if cta_path and (not cta_path.startswith("/") or cta_path.startswith("//") or ".." in PurePosixPath(cta_path).parts):
            raise LandingContractError("cta_path")
        return cls(
            kind,
            _plain(data["heading"], "heading", 256),
            _plain(data["body"], "body", 2_048, allow_empty=True),
            items,
            cta_label,
            cta_path,
        )

    def to_dict(self) -> dict[str, Any]:
        return _to_dict(self)


@dataclass(frozen=True)
class LandingAssetV1:
    path: str
    media_type: str
    alt_text: str
    sha256: str
    rights_ref: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LandingAssetV1":
        data = _object(data, "landing_asset")
        _closed(data, set(cls.__dataclass_fields__))
        path = _text(data["path"], "asset_path", 256)
        candidate = PurePosixPath(path)
        if candidate.is_absolute() or ".." in candidate.parts or str(candidate) != path or not path.startswith("assets/"):
            raise LandingContractError("asset_path")
        media_type = data["media_type"]
        if media_type not in MEDIA_TYPES["image"]:
            raise LandingContractError("asset_media_type")
        return cls(
            path,
            media_type,
            _plain(data["alt_text"], "alt_text", 512),
            _hex(data["sha256"], "asset_sha256", HEX64),
            _identifier(data["rights_ref"], "rights_ref"),
        )

    def to_dict(self) -> dict[str, Any]:
        return _to_dict(self)


@dataclass(frozen=True)
class StaticLandingSpecV1(_LandingRecord):
    schema_version: int
    input_digest: str
    site_id: str
    canonical_origin: str
    locale: str
    direction: str
    title: str
    description: str
    robots_policy: str
    sections: tuple[LandingSectionV1, ...]
    assets: tuple[LandingAssetV1, ...]
    source_claim_refs: tuple[str, ...]
    spec_digest: str

    DOMAIN = "static-spec"
    DIGEST_FIELD = "spec_digest"

    @classmethod
    def from_facts(cls, data: Mapping[str, Any]) -> "StaticLandingSpecV1":
        data = _object(data, "static_landing_spec")
        fields = set(cls.__dataclass_fields__) - {"spec_digest"}
        _closed(data, fields)
        if data["schema_version"] != 1:
            raise LandingContractError("unsupported_version", "static_landing_spec")
        if data["site_id"] != SITE_ID or data["canonical_origin"] != CANONICAL_ORIGIN:
            raise LandingContractError("site_identity")
        locale = data["locale"]
        if not isinstance(locale, str) or not _LOCALE.fullmatch(locale):
            raise LandingContractError("locale")
        if data["direction"] not in {"ltr", "rtl"}:
            raise LandingContractError("direction")
        if data["robots_policy"] != "noindex_nofollow":
            raise LandingContractError("robots_policy")
        sections_raw = data["sections"]
        if not isinstance(sections_raw, list) or not 1 <= len(sections_raw) <= 12:
            raise LandingContractError("sections")
        sections = tuple(LandingSectionV1.from_dict(item) for item in sections_raw)
        assets = _sorted_unique(data["assets"], "assets", LandingAssetV1.from_dict, maximum=32)
        refs = _sorted_unique(data["source_claim_refs"], "source_claim_refs", lambda item: _identifier(item, "source_claim_ref"), maximum=64, allow_empty=False)
        values = {
            "schema_version": 1,
            "input_digest": _hex(data["input_digest"], "input_digest", HEX64),
            "site_id": SITE_ID,
            "canonical_origin": CANONICAL_ORIGIN,
            "locale": locale,
            "direction": data["direction"],
            "title": _plain(data["title"], "title", 70),
            "description": _plain(data["description"], "description", 200),
            "robots_policy": "noindex_nofollow",
            "sections": sections,
            "assets": assets,
            "source_claim_refs": refs,
        }
        digest = landing_digest(cls.DOMAIN, json.loads(canonical_json(values)))
        return cls(**values, spec_digest=digest)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StaticLandingSpecV1":
        data = _object(data, "static_landing_spec")
        _closed(data, set(cls.__dataclass_fields__))
        result = cls.from_facts({key: data[key] for key in data if key != "spec_digest"})
        _validate_supplied(result, data["spec_digest"], "spec_digest")
        return result


@dataclass(frozen=True)
class LandingProviderEvidenceV1(_LandingRecord):
    schema_version: int
    input_digest: str
    profile_digest: str
    provider_id: str
    adapter_id: str
    adapter_version: str
    model_id: str
    prompt_template_digest: str
    tool_policy_digest: str
    output_schema_digest: str
    decoder_digest: str
    request_digest: str
    response_digest: str
    usage_input_units: int
    usage_output_units: int
    started_at: datetime
    completed_at: datetime
    disposition: str
    provider_evidence_digest: str

    DOMAIN = "provider-evidence"
    DIGEST_FIELD = "provider_evidence_digest"

    @classmethod
    def from_facts(cls, data: Mapping[str, Any]) -> "LandingProviderEvidenceV1":
        data = _object(data, "landing_provider_evidence")
        fields = set(cls.__dataclass_fields__) - {"provider_evidence_digest"}
        _closed(data, fields)
        if data["schema_version"] != 1:
            raise LandingContractError("unsupported_version", "provider_evidence")
        version = _text(data["adapter_version"], "adapter_version", 64)
        if not _VERSION.fullmatch(version):
            raise LandingContractError("adapter_version")
        if data["disposition"] not in {"fixture_ready", "provider_unavailable", "rejected"}:
            raise LandingContractError("provider_disposition")
        started = _time(data["started_at"], "started_at")
        completed = _time(data["completed_at"], "completed_at")
        if completed < started:
            raise LandingContractError("provider_time_order")
        values = {
            "schema_version": 1,
            "input_digest": _hex(data["input_digest"], "input_digest", HEX64),
            "profile_digest": _hex(data["profile_digest"], "profile_digest", HEX64),
            "provider_id": _identifier(data["provider_id"], "provider_id"),
            "adapter_id": _identifier(data["adapter_id"], "adapter_id"),
            "adapter_version": version,
            "model_id": _identifier(data["model_id"], "model_id"),
            "prompt_template_digest": _hex(data["prompt_template_digest"], "prompt_template_digest", HEX64),
            "tool_policy_digest": _hex(data["tool_policy_digest"], "tool_policy_digest", HEX64),
            "output_schema_digest": _hex(data["output_schema_digest"], "output_schema_digest", HEX64),
            "decoder_digest": _hex(data["decoder_digest"], "decoder_digest", HEX64),
            "request_digest": _hex(data["request_digest"], "request_digest", HEX64),
            "response_digest": _hex(data["response_digest"], "response_digest", HEX64),
            "usage_input_units": _integer(data["usage_input_units"], "usage_input_units", 0, 10_000_000),
            "usage_output_units": _integer(data["usage_output_units"], "usage_output_units", 0, 10_000_000),
            "started_at": started,
            "completed_at": completed,
            "disposition": data["disposition"],
        }
        digest = landing_digest(cls.DOMAIN, json.loads(canonical_json(values)))
        return cls(**values, provider_evidence_digest=digest)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LandingProviderEvidenceV1":
        data = _object(data, "landing_provider_evidence")
        _closed(data, set(cls.__dataclass_fields__))
        result = cls.from_facts({key: data[key] for key in data if key != "provider_evidence_digest"})
        _validate_supplied(result, data["provider_evidence_digest"], "provider_evidence_digest")
        return result


@dataclass(frozen=True)
class LandingAttemptV1(_LandingRecord):
    schema_version: int
    input_digest: str
    spec_digest: str
    profile_digest: str
    ordinal: int
    exact_base_sha: str
    exact_head_sha: str
    workspace_result_digest: str
    renderer_digest: str
    writer_id: str
    context_digest: str
    evaluator_digest: str
    prior_attempt_digest: str | None
    outcome: str
    started_at: datetime
    completed_at: datetime
    attempt_digest: str

    DOMAIN = "attempt"
    DIGEST_FIELD = "attempt_digest"

    @classmethod
    def from_facts(cls, data: Mapping[str, Any]) -> "LandingAttemptV1":
        data = _object(data, "landing_attempt")
        fields = set(cls.__dataclass_fields__) - {"attempt_digest"}
        _closed(data, fields)
        if data["schema_version"] != 1:
            raise LandingContractError("unsupported_version", "landing_attempt")
        ordinal = _integer(data["ordinal"], "attempt_ordinal", 1, 3)
        prior = data["prior_attempt_digest"]
        if ordinal == 1:
            if prior is not None:
                raise LandingContractError("prior_attempt_digest")
        else:
            prior = _hex(prior, "prior_attempt_digest", HEX64)
        if data["outcome"] not in {"candidate", "repair", "needs_human"}:
            raise LandingContractError("attempt_outcome")
        started = _time(data["started_at"], "started_at")
        completed = _time(data["completed_at"], "completed_at")
        if completed < started:
            raise LandingContractError("attempt_time_order")
        values = {
            "schema_version": 1,
            "input_digest": _hex(data["input_digest"], "input_digest", HEX64),
            "spec_digest": _hex(data["spec_digest"], "spec_digest", HEX64),
            "profile_digest": _hex(data["profile_digest"], "profile_digest", HEX64),
            "ordinal": ordinal,
            "exact_base_sha": _hex(data["exact_base_sha"], "exact_base_sha", HEX40),
            "exact_head_sha": _hex(data["exact_head_sha"], "exact_head_sha", HEX40),
            "workspace_result_digest": _hex(data["workspace_result_digest"], "workspace_result_digest", HEX64),
            "renderer_digest": _hex(data["renderer_digest"], "renderer_digest", HEX64),
            "writer_id": _identifier(data["writer_id"], "writer_id"),
            "context_digest": _hex(data["context_digest"], "context_digest", HEX64),
            "evaluator_digest": _hex(data["evaluator_digest"], "evaluator_digest", HEX64),
            "prior_attempt_digest": prior,
            "outcome": data["outcome"],
            "started_at": started,
            "completed_at": completed,
        }
        digest = landing_digest(cls.DOMAIN, json.loads(canonical_json(values)))
        return cls(**values, attempt_digest=digest)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LandingAttemptV1":
        data = _object(data, "landing_attempt")
        _closed(data, set(cls.__dataclass_fields__))
        result = cls.from_facts({key: data[key] for key in data if key != "attempt_digest"})
        _validate_supplied(result, data["attempt_digest"], "attempt_digest")
        return result


@dataclass(frozen=True)
class LandingEvaluationV1(_LandingRecord):
    schema_version: int
    attempt_digest: str
    candidate_head_sha: str
    evaluator_id: str
    context_digest: str
    policy_digest: str
    rubric_digest: str
    decision: str
    reason_codes: tuple[str, ...]
    requirement_digests: tuple[str, ...]
    finding_digests: tuple[str, ...]
    created_at: datetime
    evaluation_digest: str

    DOMAIN = "evaluation"
    DIGEST_FIELD = "evaluation_digest"

    @classmethod
    def from_facts(cls, data: Mapping[str, Any]) -> "LandingEvaluationV1":
        data = _object(data, "landing_evaluation")
        fields = set(cls.__dataclass_fields__) - {"evaluation_digest"}
        _closed(data, fields)
        if data["schema_version"] != 1:
            raise LandingContractError("unsupported_version", "landing_evaluation")
        decision = data["decision"]
        if decision not in {"pass", "repair", "needs_human"}:
            raise LandingContractError("evaluation_decision")
        reasons = _sorted_unique(data["reason_codes"], "reason_codes", lambda item: _identifier(item, "reason_code"), maximum=32)
        requirements = _sorted_unique(data["requirement_digests"], "requirement_digests", lambda item: _hex(item, "requirement_digest", HEX64), maximum=32)
        findings = _sorted_unique(data["finding_digests"], "finding_digests", lambda item: _hex(item, "finding_digest", HEX64), maximum=32)
        if decision == "repair" and not reasons:
            raise LandingContractError("repair_reason_required")
        values = {
            "schema_version": 1,
            "attempt_digest": _hex(data["attempt_digest"], "attempt_digest", HEX64),
            "candidate_head_sha": _hex(data["candidate_head_sha"], "candidate_head_sha", HEX40),
            "evaluator_id": _identifier(data["evaluator_id"], "evaluator_id"),
            "context_digest": _hex(data["context_digest"], "context_digest", HEX64),
            "policy_digest": _hex(data["policy_digest"], "policy_digest", HEX64),
            "rubric_digest": _hex(data["rubric_digest"], "rubric_digest", HEX64),
            "decision": decision,
            "reason_codes": reasons,
            "requirement_digests": requirements,
            "finding_digests": findings,
            "created_at": _time(data["created_at"], "created_at"),
        }
        digest = landing_digest(cls.DOMAIN, json.loads(canonical_json(values)))
        return cls(**values, evaluation_digest=digest)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LandingEvaluationV1":
        data = _object(data, "landing_evaluation")
        _closed(data, set(cls.__dataclass_fields__))
        result = cls.from_facts({key: data[key] for key in data if key != "evaluation_digest"})
        _validate_supplied(result, data["evaluation_digest"], "evaluation_digest")
        return result


@dataclass(frozen=True)
class SiteArtifactV1(_LandingRecord):
    schema_version: int
    site_id: str
    canonical_origin: str
    source_sha: str
    source_tree: str
    candidate_sha: str
    candidate_tree: str
    input_digest: str
    spec_digest: str
    profile_digest: str
    attempt_digest: str
    evaluation_digest: str
    manifest_digest: str
    zip_sha256: str
    sidecar_sha256: str
    member_count: int
    byte_length: int
    disposition: str
    artifact_digest: str

    DOMAIN = "site-artifact"
    DIGEST_FIELD = "artifact_digest"

    @classmethod
    def from_facts(cls, data: Mapping[str, Any]) -> "SiteArtifactV1":
        data = _object(data, "site_artifact")
        fields = set(cls.__dataclass_fields__) - {"artifact_digest"}
        _closed(data, fields)
        if data["schema_version"] != 1:
            raise LandingContractError("unsupported_version", "site_artifact")
        if data["site_id"] != SITE_ID or data["canonical_origin"] != CANONICAL_ORIGIN:
            raise LandingContractError("site_identity")
        if data["disposition"] != "artifact_ready":
            raise LandingContractError("artifact_disposition")
        values = {
            "schema_version": 1,
            "site_id": SITE_ID,
            "canonical_origin": CANONICAL_ORIGIN,
            "source_sha": _hex(data["source_sha"], "source_sha", HEX40),
            "source_tree": _hex(data["source_tree"], "source_tree", HEX40),
            "candidate_sha": _hex(data["candidate_sha"], "candidate_sha", HEX40),
            "candidate_tree": _hex(data["candidate_tree"], "candidate_tree", HEX40),
            "input_digest": _hex(data["input_digest"], "input_digest", HEX64),
            "spec_digest": _hex(data["spec_digest"], "spec_digest", HEX64),
            "profile_digest": _hex(data["profile_digest"], "profile_digest", HEX64),
            "attempt_digest": _hex(data["attempt_digest"], "attempt_digest", HEX64),
            "evaluation_digest": _hex(data["evaluation_digest"], "evaluation_digest", HEX64),
            "manifest_digest": _hex(data["manifest_digest"], "manifest_digest", HEX64),
            "zip_sha256": _hex(data["zip_sha256"], "zip_sha256", HEX64),
            "sidecar_sha256": _hex(data["sidecar_sha256"], "sidecar_sha256", HEX64),
            "member_count": _integer(data["member_count"], "member_count", 1, 1_024),
            "byte_length": _integer(data["byte_length"], "byte_length", 1, 100 * 1_048_576),
            "disposition": "artifact_ready",
        }
        digest = landing_digest(cls.DOMAIN, values)
        return cls(**values, artifact_digest=digest)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SiteArtifactV1":
        data = _object(data, "site_artifact")
        _closed(data, set(cls.__dataclass_fields__))
        result = cls.from_facts({key: data[key] for key in data if key != "artifact_digest"})
        _validate_supplied(result, data["artifact_digest"], "artifact_digest")
        return result
