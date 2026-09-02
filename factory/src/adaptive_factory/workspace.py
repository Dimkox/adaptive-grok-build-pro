from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from typing import Callable, Mapping


_CREDENTIAL_NAME = re.compile(r"(?i)(?:key|token|secret|password|credential|trust_ci|openai|github|grok)")


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
class WorkspacePolicy:
    allowed_paths: tuple[str, ...]
    allowed_operations: tuple[str, ...]
    environment_names: tuple[str, ...]
    network_destinations: tuple[str, ...]


@dataclass(frozen=True)
class WorkspaceDecision:
    allowed: bool
    code: str


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
