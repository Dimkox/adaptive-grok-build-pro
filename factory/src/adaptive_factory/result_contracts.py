"""Closed, immutable contracts for results admitted to another model."""

from __future__ import annotations

from dataclasses import dataclass
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


def _result_safe_text(value: Any, name: str, maximum: int = 128) -> str:
    value = safe_text(value, name, maximum)
    try:
        if _redact(value, maximum) != value:
            raise ContractError("secret_content", name)
    except BrokerError as exc:
        raise ContractError("invalid_text", name) from exc
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
        if data["channel"] not in RESULT_CHANNELS:
            raise ContractError("invalid_channel")
        if data["status"] != "unavailable":
            raise ContractError("channel_not_qualified")
        if data["interception_point"] is not None:
            raise ContractError("unproved_interception_point")
        safe_text(data["limitation"], "limitation", 128)
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
        if data["channel"] not in RESULT_CHANNELS:
            raise ContractError("invalid_channel")
        if data["channel"] == "native_tool_result":
            if data["status"] != "qualified":
                raise ContractError("channel_qualification_missing")
            if data["interception_point"] != "factory.result-admission/native-tool-result/v1":
                raise ContractError("unproved_interception_point")
            if data["limitation"] != "default_off_authenticated_uds":
                raise ContractError("qualification_limitation_mismatch")
        else:
            if data["status"] != "unavailable":
                raise ContractError("channel_not_qualified")
            if data["interception_point"] is not None:
                raise ContractError("unproved_interception_point")
            safe_text(data["limitation"], "limitation", 128)
        return cls(**data)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "channel": self.channel, "status": self.status,
            "interception_point": self.interception_point, "limitation": self.limitation,
        }


RESULT_CHANNEL_QUALIFICATION_V2 = tuple(
    ResultChannelQualificationV2.from_dict({
        **row.to_dict(),
        **({
            "status": "qualified",
            "interception_point": "factory.result-admission/native-tool-result/v1",
            "limitation": "default_off_authenticated_uds",
        } if row.channel == "native_tool_result" else {}),
    })
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
    """Frozen 04 predecessor wire; retained for compatibility, never admitted by 04A."""

    _frozen: FrozenWire

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResultEnvelopeV1":
        fields = {
            "schema_version", "channel", "content_type", "outcome", "reason_code",
            "completeness", "policy_version", "sanitized_payload",
            "sanitized_payload_digest",
        }
        closed(data, fields)
        version(data)
        if data["channel"] not in RESULT_CHANNELS:
            raise ContractError("invalid_channel")
        safe_text(data["content_type"], "content_type", 128)
        if data["outcome"] not in RESULT_OUTCOMES:
            raise ContractError("invalid_outcome")
        safe_text(data["reason_code"], "reason_code", 128)
        if data["completeness"] not in RESULT_COMPLETENESS:
            raise ContractError("invalid_completeness")
        safe_text(data["policy_version"], "policy_version", 128)
        payload = data["sanitized_payload"]
        if payload is not None:
            _result_payload_text(payload)
        if data["outcome"] in {"allow", "redacted"} and payload is None:
            raise ContractError("missing_sanitized_payload")
        if data["outcome"] in {"rejected", "unavailable"} and payload is not None:
            raise ContractError("forbidden_sanitized_payload")
        expected = "complete" if data["outcome"] in {"allow", "redacted"} else "missing"
        if data["completeness"] != expected:
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
    _frozen: FrozenWire

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResultEnvelopeV2":
        fields = {
            "repository_id", "task_id", "run_id", "fence", "packet_digest",
            "attempt_id", "source_operation", "source_digest",
            "schema_version", "channel", "content_type", "outcome",
            "reason_code", "completeness", "policy_version", "sanitized_payload",
            "sanitized_payload_digest",
        }
        closed(data, fields)
        version(data, 2)
        identity(data["repository_id"])
        identity(data["source_operation"])
        for key in ("task_id", "run_id", "attempt_id"):
            try:
                if str(UUID(data[key])) != data[key]:
                    raise ValueError
            except (ValueError, TypeError, AttributeError) as exc:
                raise ContractError("invalid_uuid", key) from exc
        integer(data["fence"], "fence", 1)
        digest(data["packet_digest"])
        digest(data["source_digest"])
        if data["channel"] not in RESULT_CHANNELS:
            raise ContractError("invalid_channel")
        _result_safe_text(data["content_type"], "content_type", 128)
        if data["outcome"] not in RESULT_OUTCOMES:
            raise ContractError("invalid_outcome")
        _result_safe_text(data["reason_code"], "reason_code", 128)
        if data["completeness"] not in RESULT_COMPLETENESS:
            raise ContractError("invalid_completeness")
        _result_safe_text(data["policy_version"], "policy_version", 128)
        payload = data["sanitized_payload"]
        if payload is not None:
            _result_payload_text(payload)
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
