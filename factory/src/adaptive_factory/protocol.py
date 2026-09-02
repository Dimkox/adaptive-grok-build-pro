from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .execution_contracts import PROTOCOL_VERSION


_TERMINAL = frozenset({"run.completed", "run.failed", "run.needs_human"})
_EVENTS = frozenset(
    {
        "adapter.ready",
        "run.started",
        "stage.reported",
        "note.proposed",
        "artifact.proposed",
        "usage.reported",
        *_TERMINAL,
    }
)
_CAPABILITY = {
    "note.proposed": "notes",
    "artifact.proposed": "artifacts",
    "usage.reported": "usage",
    "run.completed": "structured_output",
    "run.failed": "structured_output",
    "run.needs_human": "structured_output",
}
_FORBIDDEN_KEYS = frozenset(
    {
        "reasoning",
        "scratchpad",
        "chain_of_thought",
        "analysis",
        "raw_prompt",
        "prompt",
        "stdout",
        "stderr",
        "native_stream",
    }
)
_NOTE_TYPES_V1 = frozenset({"finding", "conclusion", "decision.record"})
MAX_DURABLE_PATH_BYTES = 1024
_STRUCTURAL_SECRET = re.compile(
    r"(?i)(?:-----BEGIN|-----END|(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]+|"
    r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|\bBearer[ \t]+[A-Za-z0-9._~+/=-]+|"
    r"(?<![A-Za-z0-9_-])(?:[A-Za-z0-9]+[_-])*Authorization[ \t]*[=:]|"
    r"(?<![A-Za-z0-9_-])(?:[\"'])?(?:[a-z0-9]+[_-])*(?:api[_-]?key|"
    r"access[_-]?token|session[_-]?token|client[_-]?secret|refresh[_-]?token|"
    r"password|credential|secret[_-]?key|private[_-]?key|token|secret)"
    r"(?:[_-][a-z0-9]+)*(?:[\"'])?(?![A-Za-z0-9_-])[ \t]*[:=])"
)
_PAYLOAD_FIELDS = {
    "adapter.ready": frozenset(
        {"provider_id", "adapter_id", "adapter_version", "native_version", "model_id", "capabilities"}
    ),
    "run.started": frozenset({"stage"}),
    "stage.reported": frozenset({"stage", "status"}),
    "note.proposed": frozenset({"note_type", "body", "evidence"}),
    "artifact.proposed": frozenset({"artifact_class", "path", "sha256", "size_bytes", "media_type"}),
    "usage.reported": frozenset(
        {
            "provider_call_id",
            "price_table_digest",
            "input_tokens",
            "output_tokens",
            "reasoning_tokens",
            "cost_usd_micros",
            "output_bytes",
        }
    ),
    "run.completed": frozenset({"summary"}),
    "run.failed": frozenset({"failure_class", "diagnostic"}),
    "run.needs_human": frozenset({"reason", "diagnostic"}),
}


class ProtocolError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def validate_note_type(value: object) -> str:
    """Return a closed durable note category or reject private/native streams."""
    if not isinstance(value, str):
        raise ProtocolError("payload_fields")
    if value not in _NOTE_TYPES_V1:
        raise ProtocolError("forbidden_content", "note_type")
    return value


def contains_structural_secret(value: str) -> bool:
    return bool(_STRUCTURAL_SECRET.search(value))


@dataclass(frozen=True)
class ProtocolLimits:
    max_line_bytes: int = 65_536
    max_stream_bytes: int = 1_000_000
    max_events: int = 1_000
    max_depth: int = 12
    max_nodes: int = 4_096
    max_string_bytes: int = 65_536

    def __post_init__(self) -> None:
        for value in self.__dict__.values():
            if type(value) is not int or value < 1:
                raise ProtocolError("invalid_limits")


def _pairs(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError("duplicate_key", key)
        result[key] = value
    return result


def strict_json_object(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProtocolError("invalid_utf8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ProtocolError("nonfinite_number", value)),
        )
    except ProtocolError:
        raise
    except json.JSONDecodeError as exc:
        raise ProtocolError("invalid_json") from exc
    if not isinstance(value, dict):
        raise ProtocolError("invalid_event")
    return value


def _walk(value: Any, limits: ProtocolLimits, *, depth: int = 1, count: list[int] | None = None) -> None:
    count = count if count is not None else [0]
    count[0] += 1
    if count[0] > limits.max_nodes:
        raise ProtocolError("structure_too_large")
    if depth > limits.max_depth:
        raise ProtocolError("structure_too_deep")
    if isinstance(value, dict):
        for key, item in value.items():
            if key.casefold() in _FORBIDDEN_KEYS:
                raise ProtocolError("forbidden_content", key)
            _walk(key, limits, depth=depth + 1, count=count)
            _walk(item, limits, depth=depth + 1, count=count)
    elif isinstance(value, list):
        for item in value:
            _walk(item, limits, depth=depth + 1, count=count)
    elif isinstance(value, str):
        try:
            encoded = value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ProtocolError("invalid_utf8") from exc
        if len(encoded) > limits.max_string_bytes:
            raise ProtocolError("string_too_large")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ProtocolError("nonfinite_number")
    elif value is not None and not isinstance(value, (bool, int, float)):
        raise ProtocolError("invalid_value")


def validate_event_payload(
    event_type: str,
    payload: Any,
    limits: ProtocolLimits | None = None,
) -> None:
    limits = limits or ProtocolLimits()
    if not isinstance(event_type, str) or event_type not in _EVENTS:
        raise ProtocolError("unknown_event")
    _walk(payload, limits)
    allowed = _PAYLOAD_FIELDS.get(event_type)
    if allowed is None or not isinstance(payload, dict) or not set(payload).issubset(allowed):
        raise ProtocolError("payload_fields")
    if event_type == "adapter.ready":
        if set(payload) < {"provider_id", "capabilities"}:
            raise ProtocolError("payload_fields")
        if any(
            name in payload and not isinstance(payload[name], str)
            for name in allowed - {"capabilities"}
        ):
            raise ProtocolError("payload_fields")
        capabilities = payload["capabilities"]
        if (
            not isinstance(capabilities, list)
            or not all(isinstance(value, str) for value in capabilities)
            or tuple(capabilities) != tuple(sorted(set(capabilities)))
        ):
            raise ProtocolError("capability_list")
        return
    if set(payload) != allowed:
        raise ProtocolError("payload_fields")
    if event_type in {"run.started", "stage.reported"}:
        if not all(isinstance(value, str) for value in payload.values()):
            raise ProtocolError("payload_fields")
    elif event_type == "note.proposed":
        validate_note_type(payload["note_type"])
        if (
            not isinstance(payload["body"], str)
            or not isinstance(payload["evidence"], list)
            or not all(isinstance(value, str) for value in payload["evidence"])
        ):
            raise ProtocolError("payload_fields")
    elif event_type == "artifact.proposed":
        if (
            not all(
                isinstance(payload[name], str)
                for name in ("artifact_class", "path", "sha256", "media_type")
            )
            or type(payload["size_bytes"]) is not int
        ):
            raise ProtocolError("payload_fields")
    elif event_type == "usage.reported":
        if (
            not isinstance(payload["provider_call_id"], str)
            or not isinstance(payload["price_table_digest"], str)
            or any(
                type(payload[name]) is not int
                for name in (
                    "input_tokens", "output_tokens", "reasoning_tokens",
                    "cost_usd_micros", "output_bytes",
                )
            )
        ):
            raise ProtocolError("payload_fields")
    elif event_type in _TERMINAL and not all(
        isinstance(value, str) for value in payload.values()
    ):
        raise ProtocolError("payload_fields")


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in sorted(value.items())})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True)
class CanonicalEvent:
    protocol_version: str
    task_id: str
    run_id: str
    packet_digest: str
    sequence: int
    event_type: str
    payload: Mapping[str, Any]

    @classmethod
    def from_payload(
        cls,
        *,
        task_id: str,
        run_id: str,
        packet_digest: str,
        sequence: int,
        event_type: str,
        payload: Any,
        limits: ProtocolLimits | None = None,
    ) -> "CanonicalEvent":
        if type(sequence) is not int or sequence < 1:
            raise ProtocolError("invalid_sequence")
        validate_event_payload(event_type, payload, limits)
        return cls(
            PROTOCOL_VERSION,
            task_id,
            run_id,
            packet_digest,
            sequence,
            event_type,
            _freeze(dict(payload)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "packet_digest": self.packet_digest,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "payload": _thaw(self.payload),
        }


class EventStreamParser:
    def __init__(
        self,
        task_id: str,
        run_id: str,
        packet_digest: str,
        declared_capabilities: tuple[str, ...],
        limits: ProtocolLimits | None = None,
    ) -> None:
        self.task_id = task_id
        self.run_id = run_id
        self.packet_digest = packet_digest
        self.capabilities = frozenset(declared_capabilities)
        self.limits = limits or ProtocolLimits()
        self._buffer = bytearray()
        self._bytes = 0
        self._events: list[CanonicalEvent] = []
        self._terminal = False

    def feed(self, chunk: bytes) -> tuple[CanonicalEvent, ...]:
        if not isinstance(chunk, bytes):
            raise ProtocolError("invalid_bytes")
        self._bytes += len(chunk)
        if self._bytes > self.limits.max_stream_bytes:
            raise ProtocolError("stream_too_large")
        self._buffer.extend(chunk)
        emitted: list[CanonicalEvent] = []
        while True:
            newline = self._buffer.find(b"\n")
            if newline < 0:
                if len(self._buffer) > self.limits.max_line_bytes:
                    raise ProtocolError("line_too_large")
                break
            raw = bytes(self._buffer[:newline])
            del self._buffer[: newline + 1]
            if len(raw) > self.limits.max_line_bytes:
                raise ProtocolError("line_too_large")
            if not raw:
                raise ProtocolError("invalid_json")
            event = self._parse(raw)
            self._events.append(event)
            emitted.append(event)
        return tuple(emitted)

    def _parse(self, raw: bytes) -> CanonicalEvent:
        if len(self._events) >= self.limits.max_events:
            raise ProtocolError("event_limit")
        if self._terminal:
            raise ProtocolError("after_terminal")
        value = strict_json_object(raw)
        _walk(value, self.limits)
        fields = {
            "protocol_version",
            "task_id",
            "run_id",
            "packet_digest",
            "sequence",
            "event_type",
            "payload",
        }
        if set(value) != fields:
            raise ProtocolError("event_fields")
        if value["protocol_version"] != PROTOCOL_VERSION:
            raise ProtocolError("unsupported_version")
        if (value["task_id"], value["run_id"], value["packet_digest"]) != (
            self.task_id,
            self.run_id,
            self.packet_digest,
        ):
            raise ProtocolError("identity_mismatch")
        if type(value["sequence"]) is not int or value["sequence"] != len(self._events) + 1:
            raise ProtocolError("invalid_sequence")
        event_type = value["event_type"]
        if not isinstance(event_type, str) or event_type not in _EVENTS:
            raise ProtocolError("unknown_event")
        required_capability = _CAPABILITY.get(event_type)
        if required_capability and required_capability not in self.capabilities:
            raise ProtocolError("undeclared_capability", required_capability)
        payload = value["payload"]
        validate_event_payload(event_type, payload, self.limits)
        if event_type == "adapter.ready":
            capabilities = payload["capabilities"]
            if not set(capabilities).issubset(self.capabilities):
                raise ProtocolError("undeclared_capability")
        if event_type in _TERMINAL:
            self._terminal = True
        return CanonicalEvent.from_payload(
            task_id=self.task_id,
            run_id=self.run_id,
            packet_digest=self.packet_digest,
            sequence=value["sequence"],
            event_type=event_type,
            payload=payload,
            limits=self.limits,
        )

    def finish(self) -> tuple[CanonicalEvent, ...]:
        if self._buffer:
            raise ProtocolError("partial_line")
        if not self._terminal:
            raise ProtocolError("missing_terminal")
        return tuple(self._events)
