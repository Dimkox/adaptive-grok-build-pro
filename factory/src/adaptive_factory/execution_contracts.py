from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import PurePosixPath
import re
import unicodedata
from typing import Any, Mapping

from .contracts import HEX40, HEX64, TaskLimitsV1
from .models import FailureClass


PROTOCOL_VERSION = "adaptive-factory.execution/v1"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_VERSION = re.compile(r"^[0-9]+(?:\.[0-9]+){1,2}(?:[-+][A-Za-z0-9.-]+)?$")
_WORKSPACE = re.compile(r"^workspace:[0-9a-f]{64}$")
_STAGES = ("prepare", "invoke", "collect", "finalize")
_OWNERS = frozenset({"broker", "adapter", "control_plane"})


class ExecutionContractError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def _closed(data: Mapping[str, Any], fields: set[str]) -> None:
    if not isinstance(data, Mapping):
        raise ExecutionContractError("invalid_object")
    unknown = set(data) - fields
    missing = fields - set(data)
    if unknown:
        raise ExecutionContractError("unknown_fields", ",".join(sorted(unknown)))
    if missing:
        raise ExecutionContractError("missing_fields", ",".join(sorted(missing)))


def _text(value: Any, name: str, maximum: int = 128) -> str:
    if not isinstance(value, str) or not value or unicodedata.normalize("NFC", value) != value:
        raise ExecutionContractError("invalid_text", name)
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ExecutionContractError("invalid_text", name) from exc
    if len(encoded) > maximum or any(ord(char) < 32 for char in value):
        raise ExecutionContractError("invalid_text", name)
    return value


def _identifier(value: Any, name: str) -> str:
    value = _text(value, name)
    if not _IDENTIFIER.fullmatch(value):
        raise ExecutionContractError("invalid_identifier", name)
    return value


def _hex(value: Any, name: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ExecutionContractError("invalid_digest" if pattern is HEX64 else "invalid_sha", name)
    return value


def _sorted_unique(values: Any, name: str, *, maximum: int = 64) -> tuple[str, ...]:
    if not isinstance(values, list) or len(values) > maximum:
        raise ExecutionContractError("invalid_list", name)
    result = tuple(_identifier(value, name) for value in values)
    if result != tuple(sorted(set(result))):
        raise ExecutionContractError("invalid_list", name)
    return result


def _path_list(values: Any) -> tuple[str, ...]:
    result = _sorted_unique(values, "allowed_paths")
    for value in result:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or ".git" in path.parts or str(path) != value:
            raise ExecutionContractError("invalid_path", value)
    return result


def _canonical(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(value)
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            _canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (UnicodeEncodeError, TypeError, ValueError) as exc:
        raise ExecutionContractError("noncanonical_value") from exc


def _domain_digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + _canonical_bytes(value)).hexdigest()


def workspace_evidence_digest(kind: str, digests: Any) -> str:
    if kind not in {"artifacts", "notes", "usage", "diagnostics"}:
        raise ExecutionContractError("invalid_evidence_kind")
    if not isinstance(digests, (list, tuple)) or len(digests) > 100_000:
        raise ExecutionContractError("invalid_list", kind)
    parsed = tuple(_hex(value, kind, HEX64) for value in digests)
    if parsed != tuple(sorted(set(parsed))):
        raise ExecutionContractError("invalid_list", kind)
    return _domain_digest(f"adaptive-factory.workspace-{kind}/v1", parsed)


@dataclass(frozen=True)
class AuthorityBindingV1:
    exact_base_sha: str
    exact_head_sha: str
    route_id: str
    change_id: str
    spec_digest: str
    architecture_digest: str
    governance_digest: str
    policy_digest: str
    prompt_template_digest: str
    role_definition_digest: str
    tool_policy_digest: str
    output_schema_digest: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AuthorityBindingV1":
        fields = set(cls.__dataclass_fields__)
        _closed(data, fields)
        return cls(
            _hex(data["exact_base_sha"], "exact_base_sha", HEX40),
            _hex(data["exact_head_sha"], "exact_head_sha", HEX40),
            _identifier(data["route_id"], "route_id"),
            _identifier(data["change_id"], "change_id"),
            _hex(data["spec_digest"], "spec_digest", HEX64),
            _hex(data["architecture_digest"], "architecture_digest", HEX64),
            _hex(data["governance_digest"], "governance_digest", HEX64),
            _hex(data["policy_digest"], "policy_digest", HEX64),
            _hex(data["prompt_template_digest"], "prompt_template_digest", HEX64),
            _hex(data["role_definition_digest"], "role_definition_digest", HEX64),
            _hex(data["tool_policy_digest"], "tool_policy_digest", HEX64),
            _hex(data["output_schema_digest"], "output_schema_digest", HEX64),
        )


@dataclass(frozen=True)
class ProviderProfileV1:
    provider_id: str
    adapter_id: str
    adapter_version: str
    adapter_digest: str
    native_version: str
    native_digest: str
    model_id: str
    capabilities: tuple[str, ...]
    eligible: bool

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProviderProfileV1":
        fields = set(cls.__dataclass_fields__)
        _closed(data, fields)
        if data["eligible"] is not True:
            raise ExecutionContractError("provider_ineligible")
        versions = []
        for name in ("adapter_version", "native_version"):
            value = _text(data[name], name)
            if not _VERSION.fullmatch(value):
                raise ExecutionContractError("invalid_version", name)
            versions.append(value)
        return cls(
            _identifier(data["provider_id"], "provider_id"),
            _identifier(data["adapter_id"], "adapter_id"),
            versions[0],
            _hex(data["adapter_digest"], "adapter_digest", HEX64),
            versions[1],
            _hex(data["native_digest"], "native_digest", HEX64),
            _identifier(data["model_id"], "model_id"),
            _sorted_unique(data["capabilities"], "capabilities"),
            True,
        )

    @property
    def profile_digest(self) -> str:
        return _domain_digest("adaptive-factory.provider-profile/v1", self)


@dataclass(frozen=True)
class CapabilityPolicyV1:
    allowed_paths: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    network_destinations: tuple[str, ...]
    artifact_classes: tuple[str, ...]
    environment_names: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CapabilityPolicyV1":
        fields = set(cls.__dataclass_fields__)
        _closed(data, fields)
        if data["network_destinations"] != []:
            raise ExecutionContractError("network_forbidden")
        return cls(
            _path_list(data["allowed_paths"]),
            _sorted_unique(data["allowed_tools"], "allowed_tools"),
            (),
            _sorted_unique(data["artifact_classes"], "artifact_classes"),
            _sorted_unique(data["environment_names"], "environment_names"),
        )


@dataclass(frozen=True)
class ExecutionStageV1:
    name: str
    owner: str
    wall_seconds: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExecutionStageV1":
        _closed(data, {"name", "owner", "wall_seconds"})
        name = _identifier(data["name"], "stage.name")
        owner = _identifier(data["owner"], "stage.owner")
        if name not in _STAGES or owner not in _OWNERS:
            raise ExecutionContractError("invalid_stage")
        wall = data["wall_seconds"]
        if type(wall) is not int or not 1 <= wall <= 14_400:
            raise ExecutionContractError("limit_exceeded", "stage.wall_seconds")
        return cls(name, owner, wall)


@dataclass(frozen=True)
class ExecutionPlanV1:
    stages: tuple[ExecutionStageV1, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExecutionPlanV1":
        _closed(data, {"stages"})
        if not isinstance(data["stages"], list):
            raise ExecutionContractError("invalid_list", "stages")
        stages = tuple(ExecutionStageV1.from_dict(item) for item in data["stages"])
        if tuple(item.name for item in stages) != _STAGES:
            raise ExecutionContractError("stage_order")
        return cls(stages)


@dataclass(frozen=True)
class ExecutionSelectionV1:
    provider: ProviderProfileV1
    capability_policy: CapabilityPolicyV1
    plan: ExecutionPlanV1
    workspace_handle: str
    prompt_template_digest: str
    role_definition_digest: str
    tool_policy_digest: str
    output_schema_digest: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExecutionSelectionV1":
        fields = set(cls.__dataclass_fields__)
        _closed(data, fields)
        workspace = data["workspace_handle"]
        if not isinstance(workspace, str) or not _WORKSPACE.fullmatch(workspace):
            raise ExecutionContractError("invalid_workspace")
        return cls(
            ProviderProfileV1.from_dict(data["provider"]),
            CapabilityPolicyV1.from_dict(data["capability_policy"]),
            ExecutionPlanV1.from_dict(data["plan"]),
            workspace,
            _hex(data["prompt_template_digest"], "prompt_template_digest", HEX64),
            _hex(data["role_definition_digest"], "role_definition_digest", HEX64),
            _hex(data["tool_policy_digest"], "tool_policy_digest", HEX64),
            _hex(data["output_schema_digest"], "output_schema_digest", HEX64),
        )

    def to_dict(self) -> dict[str, Any]:
        return _canonical(asdict(self))


@dataclass(frozen=True)
class TaskPacketV1:
    contract_version: int
    protocol_version: str
    task_id: str
    run_id: str
    owner: str
    fence: int
    role: str
    repository_id: str
    legacy_intent_digest: str
    authority: AuthorityBindingV1
    provider: ProviderProfileV1
    capability_policy: CapabilityPolicyV1
    plan: ExecutionPlanV1
    workspace_handle: str
    acceptance_ids: tuple[str, ...]
    limits: TaskLimitsV1
    packet_digest: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TaskPacketV1":
        fields = set(cls.__dataclass_fields__) - {"packet_digest"}
        _closed(data, fields)
        if data["contract_version"] != 1 or data["protocol_version"] != PROTOCOL_VERSION:
            raise ExecutionContractError("unsupported_version")
        fence = data["fence"]
        if type(fence) is not int or fence < 1:
            raise ExecutionContractError("invalid_fence")
        role = data["role"]
        if role not in {"reader", "writer"}:
            raise ExecutionContractError("invalid_role")
        workspace = data["workspace_handle"]
        if not isinstance(workspace, str) or not _WORKSPACE.fullmatch(workspace):
            raise ExecutionContractError("invalid_workspace")
        try:
            limits = TaskLimitsV1.from_dict(data["limits"])
        except ValueError as exc:
            raise ExecutionContractError(getattr(exc, "code", "invalid_limits"), str(exc)) from exc
        values = {
            "contract_version": 1,
            "protocol_version": PROTOCOL_VERSION,
            "task_id": _identifier(data["task_id"], "task_id"),
            "run_id": _identifier(data["run_id"], "run_id"),
            "owner": _identifier(data["owner"], "owner"),
            "fence": fence,
            "role": role,
            "repository_id": _identifier(data["repository_id"], "repository_id"),
            "legacy_intent_digest": _hex(data["legacy_intent_digest"], "legacy_intent_digest", HEX64),
            "authority": AuthorityBindingV1.from_dict(data["authority"]),
            "provider": ProviderProfileV1.from_dict(data["provider"]),
            "capability_policy": CapabilityPolicyV1.from_dict(data["capability_policy"]),
            "plan": ExecutionPlanV1.from_dict(data["plan"]),
            "workspace_handle": workspace,
            "acceptance_ids": _sorted_unique(data["acceptance_ids"], "acceptance_ids"),
            "limits": limits,
        }
        if sum(stage.wall_seconds for stage in values["plan"].stages) > limits.wall_seconds:
            raise ExecutionContractError("limit_exceeded", "plan.wall_seconds")
        digest = _domain_digest("adaptive-factory.task-packet/v1", values)
        return cls(**values, packet_digest=digest)

    @property
    def canonical_bytes(self) -> bytes:
        return _canonical_bytes(self.to_dict(include_digest=False))

    def to_dict(self, *, include_digest: bool = True) -> dict[str, Any]:
        value = _canonical(asdict(self))
        if not include_digest:
            value.pop("packet_digest")
        return value


@dataclass(frozen=True)
class RunManifestV1:
    contract_version: int
    task_id: str
    run_id: str
    packet_digest: str
    provider_id: str
    adapter_id: str
    native_version: str
    model_id: str
    workspace_handle: str
    deadline: str
    stage: str
    manifest_digest: str

    @classmethod
    def from_packet(cls, packet: TaskPacketV1, *, deadline: str) -> "RunManifestV1":
        try:
            parsed = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise ExecutionContractError("invalid_time", "deadline") from exc
        if parsed.tzinfo is None:
            raise ExecutionContractError("invalid_time", "deadline")
        normalized_deadline = parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        values = {
            "contract_version": 1,
            "task_id": packet.task_id,
            "run_id": packet.run_id,
            "packet_digest": packet.packet_digest,
            "provider_id": packet.provider.provider_id,
            "adapter_id": packet.provider.adapter_id,
            "native_version": packet.provider.native_version,
            "model_id": packet.provider.model_id,
            "workspace_handle": packet.workspace_handle,
            "deadline": normalized_deadline,
            "stage": "prepared",
        }
        return cls(**values, manifest_digest=_domain_digest("adaptive-factory.run-manifest/v1", values))

    def to_dict(self) -> dict[str, Any]:
        return _canonical(asdict(self))


@dataclass(frozen=True)
class WorkspaceResultV1:
    contract_version: int
    task_id: str
    run_id: str
    task_packet_digest: str
    run_manifest_digest: str
    exact_head_sha: str
    workspace_snapshot_digest: str
    terminal_stage: str
    terminal_proposal_digest: str
    artifact_manifest_digest: str
    note_manifest_digest: str
    usage_evidence_digest: str
    diagnostics_digest: str
    m4_status: str
    failure_class: str | None
    failure_reason: str | None
    workspace_result_digest: str

    @classmethod
    def from_facts(cls, data: Mapping[str, Any]) -> "WorkspaceResultV1":
        fields = set(cls.__dataclass_fields__) - {"workspace_result_digest"}
        _closed(data, fields)
        if data["contract_version"] != 1:
            raise ExecutionContractError("unsupported_version")
        terminal = data["terminal_stage"]
        if terminal not in {"completed", "failed", "needs_human"}:
            raise ExecutionContractError("invalid_terminal")
        terminal_digest = data["terminal_proposal_digest"]
        terminal_digest = _hex(terminal_digest, "terminal_proposal_digest", HEX64)
        m4_status = data["m4_status"]
        if not isinstance(m4_status, str):
            raise ExecutionContractError("invalid_m4_disposition")
        failure_class = data["failure_class"]
        failure_reason = data["failure_reason"]
        if terminal == "completed":
            if (
                m4_status != "ready_for_human"
                or failure_class is not None
                or failure_reason is not None
            ):
                raise ExecutionContractError("invalid_m4_disposition")
        elif terminal == "failed":
            if m4_status not in {"retry", "needs_human", "dead"}:
                raise ExecutionContractError("invalid_m4_disposition")
            try:
                failure_class = FailureClass(failure_class).value
            except (TypeError, ValueError) as exc:
                raise ExecutionContractError("invalid_failure_class") from exc
            failure_reason = _text(failure_reason, "failure_reason", 4096)
        else:
            if m4_status != "needs_human" or failure_class is not None:
                raise ExecutionContractError("invalid_m4_disposition")
            failure_reason = _text(failure_reason, "failure_reason", 4096)
        values = {
            "contract_version": 1,
            "task_id": _identifier(data["task_id"], "task_id"),
            "run_id": _identifier(data["run_id"], "run_id"),
            "task_packet_digest": _hex(data["task_packet_digest"], "task_packet_digest", HEX64),
            "run_manifest_digest": _hex(data["run_manifest_digest"], "run_manifest_digest", HEX64),
            "exact_head_sha": _hex(data["exact_head_sha"], "exact_head_sha", HEX40),
            "workspace_snapshot_digest": _hex(
                data["workspace_snapshot_digest"], "workspace_snapshot_digest", HEX64
            ),
            "terminal_stage": terminal,
            "terminal_proposal_digest": terminal_digest,
            "artifact_manifest_digest": _hex(
                data["artifact_manifest_digest"], "artifact_manifest_digest", HEX64
            ),
            "note_manifest_digest": _hex(data["note_manifest_digest"], "note_manifest_digest", HEX64),
            "usage_evidence_digest": _hex(data["usage_evidence_digest"], "usage_evidence_digest", HEX64),
            "diagnostics_digest": _hex(data["diagnostics_digest"], "diagnostics_digest", HEX64),
            "m4_status": m4_status,
            "failure_class": failure_class,
            "failure_reason": failure_reason,
        }
        return cls(
            **values,
            workspace_result_digest=_domain_digest("adaptive-factory.workspace-result/v1", values),
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "WorkspaceResultV1":
        fields = set(cls.__dataclass_fields__)
        _closed(data, fields)
        facts = {name: data[name] for name in fields - {"workspace_result_digest"}}
        result = cls.from_facts(facts)
        supplied = _hex(data["workspace_result_digest"], "workspace_result_digest", HEX64)
        if supplied != result.workspace_result_digest:
            raise ExecutionContractError("digest_mismatch", "workspace_result_digest")
        return result

    def to_dict(self, *, include_digest: bool = True) -> dict[str, Any]:
        value = _canonical(asdict(self))
        if not include_digest:
            value.pop("workspace_result_digest")
        return value
