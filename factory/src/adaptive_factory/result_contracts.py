"""Closed, immutable contracts for results admitted to another model."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from typing import Any, Mapping
import unicodedata
from uuid import UUID

from .brokers import BrokerError, _redact
from .contracts import ContractError, canonical_digest
from .v15_contracts import FrozenWire, closed, digest, identity, integer, safe_text, version


RESULT_OUTCOMES = frozenset({"allow", "redacted", "rejected", "unavailable"})
RESULT_COMPLETENESS = frozenset({"complete", "missing"})
RESULT_CHANNELS = frozenset(
    {
        "native_tool_result", "synthetic_child_report", "attachment", "artifact_cache",
        "resume", "external_cli", "unknown",
    }
)

_SENSITIVE_KEY = re.compile(
    r"(?i)(?:^|[_-])(?:authorization|api[_-]?key|access[_-]?token|"
    r"session[_-]?token|client[_-]?secret|refresh[_-]?token|password|"
    r"credentials?|secret[_-]?key|private[_-]?key|token|secret)(?:$|[_-])"
)


def sensitive_key(value: str) -> bool:
    return bool(_SENSITIVE_KEY.search(value))

def _metadata_text(value: Any, name: str) -> str:
    try:
        return safe_text(value, name, 128)
    except UnicodeError:
        raise ContractError("invalid_text", name) from None


def strict_json(value: str) -> Any:
    def pairs(items):
        result = {}
        for key, child in items:
            if key in result:
                raise ContractError("duplicate_json_key")
            result[key] = child
        return result

    return json.loads(value, object_pairs_hook=pairs)


def _structured_payload(value: str) -> None:
    try:
        parsed = strict_json(value)
        records = 0

        def visit(item, depth):
            nonlocal records
            if depth > 64:
                raise ContractError("invalid_result_payload")
            if isinstance(item, dict):
                records += len(item)
                for key in item:
                    _result_payload_text(key)
                if any(sensitive_key(key) for key in item):
                    raise ContractError("secret_content")
                for child in item.values():
                    visit(child, depth + 1)
            elif isinstance(item, list):
                records += len(item)
                for child in item:
                    visit(child, depth + 1)
            elif isinstance(item, float) and not math.isfinite(item):
                raise ContractError("invalid_result_payload")
            elif isinstance(item, str):
                _result_payload_text(item)
            if records > 100_000:
                raise ContractError("invalid_result_payload")

        visit(parsed, 1)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ContractError("invalid_result_payload") from exc


def _result_payload_text(value: Any) -> str:
    if not isinstance(value, str):
        raise ContractError("invalid_result_payload")
    try:
        raw = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ContractError("invalid_result_payload") from exc
    if (
        len(raw) > 1_000_000
        or unicodedata.normalize("NFC", value) != value
        or any(ord(char) < 32 and char not in {"\n", "\t"} for char in value)
    ):
        raise ContractError("invalid_result_payload")
    try:
        if _redact(value, 1_000_000) != value:
            raise ContractError("secret_content")
    except BrokerError as exc:
        raise ContractError("invalid_result_payload") from exc
    return value


@dataclass(frozen=True)
class ResultChannelQualificationV1:
    channel: str
    status: str
    interception_point: str | None
    limitation: str | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResultChannelQualificationV1":
        closed(data, {"channel", "status", "interception_point", "limitation"})
        if not isinstance(data["channel"], str) or data["channel"] not in RESULT_CHANNELS:
            raise ContractError("invalid_channel")
        if data["status"] != "unavailable":
            raise ContractError("channel_not_qualified")
        if data["interception_point"] is not None:
            raise ContractError("unproved_interception_point")
        _metadata_text(data["limitation"], "limitation")
        return cls(**data)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "channel": self.channel,
            "status": self.status,
            "interception_point": self.interception_point,
            "limitation": self.limitation,
        }


RESULT_CHANNEL_QUALIFICATION = (
    ResultChannelQualificationV1("native_tool_result", "unavailable", None, "runtime_wiring_missing"),
    ResultChannelQualificationV1("synthetic_child_report", "unavailable", None, "runtime_wiring_missing"),
    ResultChannelQualificationV1("attachment", "unavailable", None, "no_safe_decoder"),
    ResultChannelQualificationV1("artifact_cache", "unavailable", None, "no_interception_evidence"),
    ResultChannelQualificationV1("resume", "unavailable", None, "no_interception_evidence"),
    ResultChannelQualificationV1("external_cli", "unavailable", None, "no_interception_evidence"),
    ResultChannelQualificationV1("unknown", "unavailable", None, "invalid_channel_metadata"),
)


def result_channel_qualification_wire() -> list[dict[str, str | None]]:
    return [row.to_dict() for row in RESULT_CHANNEL_QUALIFICATION]


def result_channel_qualification_from_wire(
    data: Any,
) -> tuple[ResultChannelQualificationV1, ...]:
    if not isinstance(data, list) or len(data) != len(RESULT_CHANNELS):
        raise ContractError("qualification_channel_set")
    rows = tuple(ResultChannelQualificationV1.from_dict(row) for row in data)
    channels = [row.channel for row in rows]
    if len(set(channels)) != len(channels) or set(channels) != RESULT_CHANNELS:
        raise ContractError("qualification_channel_set")
    return rows


@dataclass(frozen=True)
class ResultChannelQualificationV2:
    channel: str
    status: str
    interception_point: str | None
    limitation: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResultChannelQualificationV2":
        closed(data, {"channel", "status", "interception_point", "limitation"})
        if not isinstance(data["channel"], str) or data["channel"] not in RESULT_CHANNELS:
            raise ContractError("invalid_channel")
        if data["status"] != "unavailable":
            raise ContractError("channel_not_qualified")
        if data["interception_point"] is not None:
            raise ContractError("unproved_interception_point")
        _metadata_text(data["limitation"], "limitation")
        return cls(**data)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "channel": self.channel, "status": self.status,
            "interception_point": self.interception_point, "limitation": self.limitation,
        }


RESULT_CHANNEL_QUALIFICATION_V2 = tuple(
    ResultChannelQualificationV2.from_dict(row.to_dict())
    for row in RESULT_CHANNEL_QUALIFICATION
)


def result_channel_qualification_v2_wire() -> list[dict[str, str | None]]:
    return [row.to_dict() for row in RESULT_CHANNEL_QUALIFICATION_V2]


def result_channel_qualification_v2_from_wire(
    data: Any,
) -> tuple[ResultChannelQualificationV2, ...]:
    if not isinstance(data, list) or len(data) != len(RESULT_CHANNELS):
        raise ContractError("qualification_channel_set")
    rows = tuple(ResultChannelQualificationV2.from_dict(row) for row in data)
    channels = [row.channel for row in rows]
    if len(set(channels)) != len(channels) or set(channels) != RESULT_CHANNELS:
        raise ContractError("qualification_channel_set")
    return rows


@dataclass(frozen=True)
class ResultEnvelopeV1:
    _frozen: FrozenWire

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResultEnvelopeV1":
        fields = {
            "schema_version", "channel", "content_type", "outcome",
            "reason_code", "completeness", "policy_version", "sanitized_payload",
            "sanitized_payload_digest",
        }
        closed(data, fields)
        version(data)
        if not isinstance(data["channel"], str) or data["channel"] not in RESULT_CHANNELS:
            raise ContractError("invalid_channel")
        _metadata_text(data["content_type"], "content_type")
        if not isinstance(data["outcome"], str) or data["outcome"] not in RESULT_OUTCOMES:
            raise ContractError("invalid_outcome")
        _metadata_text(data["reason_code"], "reason_code")
        if not isinstance(data["completeness"], str) or data["completeness"] not in RESULT_COMPLETENESS:
            raise ContractError("invalid_completeness")
        _metadata_text(data["policy_version"], "policy_version")
        payload = data["sanitized_payload"]
        if payload is not None:
            _result_payload_text(payload)
            if data["channel"] == "unknown":
                raise ContractError("invalid_channel_payload")
            if data["content_type"] not in {"application/json", "text/plain"}:
                raise ContractError("unsupported_payload_content_type")
            if data["content_type"] == "application/json":
                _structured_payload(payload)
        if data["outcome"] in {"allow", "redacted"} and payload is None:
            raise ContractError("missing_sanitized_payload")
        if data["outcome"] in {"rejected", "unavailable"} and payload is not None:
            raise ContractError("forbidden_sanitized_payload")
        expected_completeness = "complete" if data["outcome"] in {"allow", "redacted"} else "missing"
        if data["completeness"] != expected_completeness:
            raise ContractError("outcome_completeness_mismatch")
        digest(data["sanitized_payload_digest"])
        if canonical_digest(payload) != data["sanitized_payload_digest"]:
            raise ContractError("sanitized_payload_digest_mismatch")
        return cls(FrozenWire.freeze(dict(data)))

    def to_dict(self) -> dict[str, Any]:
        return self._frozen.to_dict()

    @property
    def record_digest(self) -> str:
        return self._frozen.record_digest

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        data = self.to_dict()
        if name not in data:
            raise AttributeError(name)
        return data[name]


@dataclass(frozen=True)
class ResultEnvelopeV2:
    """Additive admission identity wrapped around the unchanged V1 payload contract."""

    _frozen: FrozenWire

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResultEnvelopeV2":
        identity_fields = {
            "repository_id", "task_id", "run_id", "fence", "packet_digest",
            "attempt_id", "source_operation", "source_digest",
        }
        v1_fields = {
            "schema_version", "channel", "content_type", "outcome", "reason_code",
            "completeness", "policy_version", "sanitized_payload",
            "sanitized_payload_digest",
        }
        closed(data, identity_fields | v1_fields)
        version(data, 2)
        identity(data["repository_id"])
        identity(data["source_operation"])
        for key in ("task_id", "run_id", "attempt_id"):
            try:
                if not isinstance(data[key], str) or str(UUID(data[key])) != data[key]:
                    raise ValueError
            except (ValueError, AttributeError) as exc:
                raise ContractError("invalid_uuid", key) from exc
        integer(data["fence"], "fence", 1)
        digest(data["packet_digest"])
        digest(data["source_digest"])
        ResultEnvelopeV1.from_dict({
            key: (1 if key == "schema_version" else data[key]) for key in v1_fields
        })
        return cls(FrozenWire.freeze(dict(data)))

    def to_dict(self) -> dict[str, Any]:
        return self._frozen.to_dict()

    @property
    def record_digest(self) -> str:
        return self._frozen.record_digest

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        data = self.to_dict()
        if name not in data:
            raise AttributeError(name)
        return data[name]
