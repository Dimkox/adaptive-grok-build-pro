from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from ..execution_contracts import PROTOCOL_VERSION
from ..protocol import EventStreamParser, ProtocolLimits, strict_json_object


class AdapterError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


@dataclass(frozen=True)
class AdapterConformance:
    provider_id: str
    native_version: str
    distribution_digest_hint: str
    capabilities: tuple[str, ...]
    missing_capabilities: tuple[str, ...]
    fixture_conformant: bool
    execution_eligible: bool


def native_records(raw: bytes, *, max_bytes: int = 1_000_000, max_records: int = 1_000) -> tuple[dict[str, Any], ...]:
    if len(raw) > max_bytes:
        raise AdapterError("native_stream_too_large")
    lines = raw.splitlines()
    if len(lines) > max_records:
        raise AdapterError("native_event_limit")
    try:
        return tuple(strict_json_object(line) for line in lines if line)
    except ValueError as exc:
        raise AdapterError("invalid_native_stream", str(exc)) from exc


def canonicalize(
    events: list[dict[str, Any]],
    *,
    task_id: str,
    run_id: str,
    packet_digest: str,
    capabilities: tuple[str, ...],
) -> tuple[dict[str, Any], ...]:
    parser = EventStreamParser(task_id, run_id, packet_digest, capabilities, ProtocolLimits())
    for event in events:
        parser.feed(json.dumps(event, sort_keys=True, separators=(",", ":")).encode() + b"\n")
    return tuple(item.to_dict() for item in parser.finish())


def event(identity: tuple[str, str, str], sequence: int, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    task_id, run_id, packet_digest = identity
    return {
        "protocol_version": PROTOCOL_VERSION,
        "task_id": task_id,
        "run_id": run_id,
        "packet_digest": packet_digest,
        "sequence": sequence,
        "event_type": event_type,
        "payload": payload,
    }
