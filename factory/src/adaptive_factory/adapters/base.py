from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from ..execution_contracts import ExecutionContractError, ExecutionSelectionV1, PROTOCOL_VERSION
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
    adapter_id: str | None = None
    adapter_version: str | None = None
    adapter_digest: str | None = None
    native_digest: str | None = None


@dataclass(frozen=True)
class TrustedExecutionProfile:
    selection: ExecutionSelectionV1
    conformance: AdapterConformance
    allowed_roles: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            not self.allowed_roles
            or self.allowed_roles != tuple(sorted(set(self.allowed_roles)))
            or any(role not in {"reader", "writer"} for role in self.allowed_roles)
        ):
            raise ExecutionContractError("invalid_trusted_profile")


class AdapterRegistry:
    _READER_WRITE_TOOLS = frozenset({"apply_patch", "exec", "git_write", "shell", "write_file"})
    _READER_WRITE_ARTIFACTS = frozenset({"commit", "patch", "workspace_mutation"})
    _READER_WRITE_CAPABILITIES = frozenset({"artifacts", "git_write", "workspace_write"})

    def __init__(self, profiles: tuple[TrustedExecutionProfile, ...]) -> None:
        if len(profiles) > 32:
            raise ExecutionContractError("trusted_profile_limit")
        self._profiles = {profile.selection.provider.provider_id: profile for profile in profiles}
        if len(self._profiles) != len(profiles):
            raise ExecutionContractError("duplicate_trusted_profile")

    def resolve(self, requested: ExecutionSelectionV1, *, role: str) -> ExecutionSelectionV1:
        profile = self._profiles.get(requested.provider.provider_id)
        if profile is None:
            raise ExecutionContractError("provider_ineligible")
        conformance = profile.conformance
        if not conformance.fixture_conformant or not conformance.execution_eligible:
            raise ExecutionContractError("provider_ineligible")
        provider = profile.selection.provider
        exact = (
            (conformance.provider_id, provider.provider_id),
            (conformance.adapter_id, provider.adapter_id),
            (conformance.adapter_version, provider.adapter_version),
            (conformance.adapter_digest, provider.adapter_digest),
            (conformance.native_version, provider.native_version),
            (conformance.native_digest, provider.native_digest),
            (conformance.capabilities, provider.capabilities),
        )
        if any(observed is None or observed != expected for observed, expected in exact):
            raise ExecutionContractError("provider_conformance_mismatch")
        if requested.to_dict() != profile.selection.to_dict():
            raise ExecutionContractError("selection_mismatch")
        if role not in profile.allowed_roles:
            raise ExecutionContractError("role_capability_forbidden")
        if role == "reader" and (
            self._READER_WRITE_TOOLS.intersection(requested.capability_policy.allowed_tools)
            or self._READER_WRITE_ARTIFACTS.intersection(requested.capability_policy.artifact_classes)
            or self._READER_WRITE_CAPABILITIES.intersection(requested.provider.capabilities)
        ):
            raise ExecutionContractError("role_capability_forbidden")
        return profile.selection


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
