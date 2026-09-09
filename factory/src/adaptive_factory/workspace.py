from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from typing import Callable, Literal, Mapping, Protocol

from .contracts import canonical_digest
from .protocol import MAX_DURABLE_PATH_BYTES, contains_structural_secret


_CREDENTIAL_NAME = re.compile(r"(?i)(?:key|token|secret|password|credential|trust_ci|openai|github|grok)")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_WORKSPACE = re.compile(r"^workspace:[0-9a-f]{64}$")
_MEDIA_TYPE = re.compile(r"^[a-z0-9.+-]+/[a-z0-9.+-]+$")


class WorkspaceError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


@dataclass(frozen=True)
class WorkspaceHandle:
    task_id: str
    run_id: str
    value: str


@dataclass(frozen=True)
class WorkspaceReleaseOutcome:
    status: Literal["released", "already_absent"]

    def __post_init__(self) -> None:
        if type(self.status) is not str or self.status not in {
            "released",
            "already_absent",
        }:
            raise WorkspaceError("workspace_release_outcome")


@dataclass(frozen=True)
class WorkspacePolicy:
    allowed_paths: tuple[str, ...]
    allowed_operations: tuple[str, ...]
    environment_names: tuple[str, ...]
    network_destinations: tuple[str, ...]


@dataclass(frozen=True)
class WorkspaceDecision:
    allowed: bool
    code: str


@dataclass(frozen=True)
class WorkspaceSnapshotV1:
    contract_version: int
    repository_id: str
    workspace_handle: str
    input_head_sha: str
    result_head_sha: str
    diff_digest: str
    diff_lines: int
    source: str
    workspace_snapshot_digest: str

    @classmethod
    def from_facts(cls, data: Mapping[str, object]) -> "WorkspaceSnapshotV1":
        fields = set(cls.__dataclass_fields__) - {"workspace_snapshot_digest"}
        if not isinstance(data, Mapping) or set(data) != fields:
            raise WorkspaceError("snapshot_fields")
        if data["contract_version"] != 1 or data["source"] != "trusted_git_broker":
            raise WorkspaceError("snapshot_source")
        repository = data["repository_id"]
        workspace = data["workspace_handle"]
        input_head = data["input_head_sha"]
        result_head = data["result_head_sha"]
        diff_digest = data["diff_digest"]
        diff_lines = data["diff_lines"]
        if not isinstance(repository, str) or not _IDENTIFIER.fullmatch(repository):
            raise WorkspaceError("snapshot_repository")
        if not isinstance(workspace, str) or not _WORKSPACE.fullmatch(workspace):
            raise WorkspaceError("snapshot_workspace")
        if not isinstance(input_head, str) or not _HEX40.fullmatch(input_head):
            raise WorkspaceError("snapshot_input_head")
        if not isinstance(result_head, str) or not _HEX40.fullmatch(result_head):
            raise WorkspaceError("snapshot_result_head")
        if not isinstance(diff_digest, str) or not _HEX64.fullmatch(diff_digest):
            raise WorkspaceError("snapshot_diff")
        if type(diff_lines) is not int or not 0 <= diff_lines <= 1_000_000:
            raise WorkspaceError("snapshot_diff_lines")
        values = {
            "contract_version": 1,
            "repository_id": repository,
            "workspace_handle": workspace,
            "input_head_sha": input_head,
            "result_head_sha": result_head,
            "diff_digest": diff_digest,
            "diff_lines": diff_lines,
            "source": "trusted_git_broker",
        }
        digest = canonical_digest({"contract": "adaptive-factory.workspace-snapshot/v1", **values})
        return cls(**values, workspace_snapshot_digest=digest)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "WorkspaceSnapshotV1":
        fields = set(cls.__dataclass_fields__)
        if not isinstance(data, Mapping) or set(data) != fields:
            raise WorkspaceError("snapshot_fields")
        facts = {name: data[name] for name in fields - {"workspace_snapshot_digest"}}
        result = cls.from_facts(facts)
        supplied = data["workspace_snapshot_digest"]
        if supplied != result.workspace_snapshot_digest:
            raise WorkspaceError("snapshot_digest_mismatch")
        return result

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "repository_id": self.repository_id,
            "workspace_handle": self.workspace_handle,
            "input_head_sha": self.input_head_sha,
            "result_head_sha": self.result_head_sha,
            "diff_digest": self.diff_digest,
            "diff_lines": self.diff_lines,
            "source": self.source,
            "workspace_snapshot_digest": self.workspace_snapshot_digest,
        }


@dataclass(frozen=True)
class WorkspaceSnapshotUnavailable:
    status: str = "unavailable"
    disposition: str = "needs_human"
    reason: str = "fake_runtime_no_git_evidence"


@dataclass(frozen=True)
class WorkspaceSnapshotRequest:
    task_id: str
    run_id: str
    repository_id: str
    workspace_handle: str
    input_head_sha: str


@dataclass(frozen=True)
class ArtifactAttestationRequest:
    task_id: str
    run_id: str
    repository_id: str
    packet_digest: str
    workspace_handle: str
    producer_sequence: int
    fence: int
    author_role: str
    artifact_class: str
    path: str
    sha256: str
    size_bytes: int
    media_type: str

    @classmethod
    def from_facts(cls, data: Mapping[str, object]) -> "ArtifactAttestationRequest":
        if not isinstance(data, Mapping) or set(data) != set(cls.__dataclass_fields__):
            raise WorkspaceError("artifact_attestation_fields")
        identifiers = (data["task_id"], data["run_id"], data["repository_id"])
        if any(not isinstance(value, str) or not _IDENTIFIER.fullmatch(value) for value in identifiers):
            raise WorkspaceError("artifact_attestation_identity")
        if not isinstance(data["packet_digest"], str) or not _HEX64.fullmatch(data["packet_digest"]):
            raise WorkspaceError("artifact_attestation_packet")
        if not isinstance(data["workspace_handle"], str) or not _WORKSPACE.fullmatch(data["workspace_handle"]):
            raise WorkspaceError("artifact_attestation_workspace")
        if type(data["producer_sequence"]) is not int or not 1 <= data["producer_sequence"] <= 100_000:
            raise WorkspaceError("artifact_attestation_sequence")
        if type(data["fence"]) is not int or not 1 <= data["fence"] < 2**63:
            raise WorkspaceError("artifact_attestation_fence")
        if data["author_role"] != "writer":
            raise WorkspaceError("artifact_attestation_role")
        if not isinstance(data["artifact_class"], str) or not _IDENTIFIER.fullmatch(data["artifact_class"]):
            raise WorkspaceError("artifact_attestation_class")
        path = data["path"]
        if not isinstance(path, str) or not path or "\x00" in path:
            raise WorkspaceError("artifact_attestation_path")
        try:
            path_bytes = path.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise WorkspaceError("artifact_attestation_path") from exc
        if len(path_bytes) > MAX_DURABLE_PATH_BYTES or contains_structural_secret(path):
            raise WorkspaceError("artifact_attestation_path")
        candidate = PurePosixPath(path)
        if candidate.is_absolute() or ".." in candidate.parts or ".git" in candidate.parts or str(candidate) != path:
            raise WorkspaceError("artifact_attestation_path")
        if not isinstance(data["sha256"], str) or not _HEX64.fullmatch(data["sha256"]):
            raise WorkspaceError("artifact_attestation_digest")
        if type(data["size_bytes"]) is not int or not 0 <= data["size_bytes"] <= 1_000_000_000:
            raise WorkspaceError("artifact_attestation_size")
        if not isinstance(data["media_type"], str) or not _MEDIA_TYPE.fullmatch(data["media_type"]):
            raise WorkspaceError("artifact_attestation_media")
        return cls(**data)

    def to_dict(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @property
    def request_digest(self) -> str:
        return canonical_digest(
            {
                "contract": "adaptive-factory.artifact-attestation-request/v1",
                **self.to_dict(),
            }
        )


@dataclass(frozen=True)
class ArtifactAttestationV1:
    contract_version: int
    task_id: str
    run_id: str
    repository_id: str
    packet_digest: str
    workspace_handle: str
    producer_sequence: int
    fence: int
    author_role: str
    artifact_class: str
    path: str
    sha256: str
    size_bytes: int
    media_type: str
    source: str
    artifact_attestation_digest: str

    @classmethod
    def from_facts(cls, data: Mapping[str, object]) -> "ArtifactAttestationV1":
        fields = set(cls.__dataclass_fields__) - {"artifact_attestation_digest"}
        if not isinstance(data, Mapping) or set(data) != fields:
            raise WorkspaceError("artifact_attestation_fields")
        if type(data["contract_version"]) is not int or data["contract_version"] != 1 \
                or data["source"] != "trusted_workspace_broker":
            raise WorkspaceError("artifact_attestation_source")
        request = ArtifactAttestationRequest.from_facts(
            {name: data[name] for name in ArtifactAttestationRequest.__dataclass_fields__}
        )
        values = {
            "contract_version": 1,
            **request.to_dict(),
            "source": "trusted_workspace_broker",
        }
        digest = canonical_digest(
            {"contract": "adaptive-factory.artifact-attestation/v1", **values}
        )
        return cls(**values, artifact_attestation_digest=digest)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "ArtifactAttestationV1":
        fields = set(cls.__dataclass_fields__)
        if not isinstance(data, Mapping) or set(data) != fields:
            raise WorkspaceError("artifact_attestation_fields")
        result = cls.from_facts(
            {name: data[name] for name in fields - {"artifact_attestation_digest"}}
        )
        if data["artifact_attestation_digest"] != result.artifact_attestation_digest:
            raise WorkspaceError("artifact_attestation_digest_mismatch")
        return result

    def to_dict(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


class ArtifactAttestationBroker(Protocol):
    """Read-only artifact verification keyed by the canonical request digest.

    Repeated calls for the same ``request_digest`` must be deterministic and
    idempotent: they return the same attestation without external mutation or
    granting authority. Concurrent duplicate reads are allowed; durable
    attestation and proposal records remain the control plane's responsibility.
    """

    def attest_artifact(
        self, request: ArtifactAttestationRequest
    ) -> ArtifactAttestationV1 | ArtifactAttestationUnavailable:
        ...


@dataclass(frozen=True)
class ArtifactAttestationUnavailable:
    status: str = "unavailable"
    disposition: str = "needs_human"
    reason: str = "fake_runtime_no_artifact_evidence"


class FakeWorkspaceBroker:
    def __init__(self, *, symlinks: tuple[str, ...] = ()) -> None:
        self._policies: dict[WorkspaceHandle, WorkspacePolicy] = {}
        self._symlinks = tuple(PurePosixPath(value) for value in symlinks)

    def register(self, handle: WorkspaceHandle, policy: WorkspacePolicy) -> None:
        if handle in self._policies:
            raise WorkspaceError("duplicate_workspace")
        if policy.network_destinations:
            raise WorkspaceError("network_forbidden")
        self._policies[handle] = policy

    def release(
        self, handle: WorkspaceHandle, *, timeout_seconds: float
    ) -> WorkspaceReleaseOutcome:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not 0 < timeout_seconds < 30
        ):
            raise WorkspaceError("workspace_release_timeout")
        if self._policies.pop(handle, None) is None:
            return WorkspaceReleaseOutcome("already_absent")
        return WorkspaceReleaseOutcome("released")

    def _policy(self, handle: WorkspaceHandle) -> WorkspacePolicy:
        try:
            return self._policies[handle]
        except KeyError as exc:
            raise WorkspaceError("unknown_workspace") from exc

    def authorize(
        self,
        handle: WorkspaceHandle,
        *,
        operation: str,
        path: str | None = None,
        network_destination: str | None = None,
    ) -> WorkspaceDecision:
        policy = self._policy(handle)
        if operation == "network" or network_destination is not None:
            raise WorkspaceError("network_forbidden")
        if operation not in policy.allowed_operations:
            raise WorkspaceError("operation_forbidden")
        if path is None:
            raise WorkspaceError("path_required")
        candidate = PurePosixPath(path)
        if candidate.is_absolute() or ".." in candidate.parts or str(candidate) != path:
            raise WorkspaceError("path_escape")
        if ".git" in candidate.parts:
            raise WorkspaceError("git_boundary")
        if any(candidate == link or link in candidate.parents for link in self._symlinks):
            raise WorkspaceError("symlink_boundary")
        if not any(candidate == PurePosixPath(root) or PurePosixPath(root) in candidate.parents for root in policy.allowed_paths):
            raise WorkspaceError("path_forbidden")
        return WorkspaceDecision(True, "allowed")

    def sanitize_environment(self, handle: WorkspaceHandle, source: Mapping[str, str]) -> dict[str, str]:
        policy = self._policy(handle)
        result = {}
        for name in sorted(policy.environment_names):
            if name in source and not _CREDENTIAL_NAME.search(name):
                value = source[name]
                if not isinstance(value, str) or "\x00" in value:
                    raise WorkspaceError("invalid_environment")
                result[name] = value
        return result

    def attest_artifact(
        self, _request: ArtifactAttestationRequest
    ) -> ArtifactAttestationUnavailable:
        return ArtifactAttestationUnavailable()


class FakeGitBroker:
    _READ_ONLY = frozenset({"status", "diff", "show"})
    _EXTERNAL = frozenset({"push", "fetch", "remote", "pr", "merge", "tag"})

    def __init__(self, workspace: FakeWorkspaceBroker) -> None:
        self.workspace = workspace

    def perform(self, handle: WorkspaceHandle, operation: str) -> WorkspaceDecision:
        self.workspace._policy(handle)
        if operation in self._EXTERNAL:
            raise WorkspaceError("external_git_forbidden")
        if operation not in self._READ_ONLY:
            raise WorkspaceError("git_operation_forbidden")
        return WorkspaceDecision(True, "allowed")

    def snapshot(
        self,
        request: WorkspaceSnapshotRequest | WorkspaceHandle,
        *,
        timeout_seconds: float,
    ) -> WorkspaceSnapshotUnavailable:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not 0 < timeout_seconds <= 5
        ):
            raise WorkspaceError("snapshot_timeout")
        if isinstance(request, WorkspaceHandle):
            self.workspace._policy(request)
        return WorkspaceSnapshotUnavailable()


@dataclass(frozen=True)
class HostIsolationReport:
    status: str
    reasons: tuple[str, ...]
    sandbox_launcher: str | None
    id_mapper: str | None
    egress_boundary: str | None

    @classmethod
    def probe(
        cls,
        command_lookup: Callable[[str], str | None],
        userns_probe: Callable[[], tuple[bool, str]],
    ) -> "HostIsolationReport":
        sandbox = command_lookup("bwrap") or command_lookup("podman")
        id_mapper = command_lookup("newuidmap")
        egress = command_lookup("slirp4netns") or command_lookup("pasta")
        userns_ok, userns_detail = userns_probe()
        reasons = []
        if not sandbox:
            reasons.append("sandbox_launcher")
        if not id_mapper:
            reasons.append("id_mapper")
        if not egress:
            reasons.append("egress_boundary")
        if not userns_ok:
            reasons.append(f"userns:{userns_detail}")
        return cls("ready" if not reasons else "blocked", tuple(reasons), sandbox, id_mapper, egress)
