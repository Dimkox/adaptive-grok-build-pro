"""Closed, private caller configuration and fixed provider order."""

from dataclasses import dataclass
from pathlib import Path
import re

from .landing_contracts import landing_digest, strict_json_object
from .landing_host_config import _check_ancestry, _private_directory
from .landing_http import HttpLandingProfile
from .landing_renderer import TARGET_BASE_SHA, TARGET_BASE_TREE, TARGET_REPOSITORY_ID
from .settings import SettingsError, read_private_file


PROVIDER_ORDER = ("qwen-intl", "grok-vision", "openai", "anthropic", "openrouter")
JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def absolute_path(value):
    if not isinstance(value, str) or not value.startswith("/") or str(Path(value)) != value or Path(value).anchor == "//" or ".." in Path(value).parts:
        raise SettingsError("absolute normalized caller path required")
    return Path(value)


def check_socket_ancestry(socket_path):
    # Stopping a systemd service may remove its runtime directory. Validate
    # the nearest existing ancestor, including dangling links, without
    # requiring operators to recreate a stopped service's private directory.
    for parent in socket_path.parents:
        try:
            parent.lstat()
        except FileNotFoundError:
            continue
        _check_ancestry(parent)
        return
    raise SettingsError("landing directory ancestry is not trusted")


@dataclass(frozen=True)
class BackendSpec:
    profile_id: str
    socket_path: Path
    token_file: Path
    profile_digest: str


@dataclass(frozen=True)
class FailoverConfig:
    control_repository: Path
    source_path: Path
    journal_path: Path
    actor_id: str
    repository_id: str
    exact_base_sha: str
    exact_base_tree: str
    deadline_seconds: int
    retention_seconds: int
    backends: tuple[BackendSpec, ...]
    digest: str

    @classmethod
    def from_dict(cls, value):
        fields = {"schema_version", "control_repository", "source_path", "journal_path", "actor_id",
                  "repository_id", "exact_base_sha", "exact_base_tree", "deadline_seconds", "retention_seconds", "backends"}
        if not isinstance(value, dict) or set(value) != fields or type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise SettingsError("closed caller configuration required")
        paths = {name: absolute_path(value[name]) for name in ("control_repository", "source_path", "journal_path")}
        roots = tuple(paths.values())
        if any(a == b or a in b.parents or b in a.parents for i, a in enumerate(roots) for b in roots[i + 1:]):
            raise SettingsError("caller roots must be disjoint")
        for path in roots:
            _check_ancestry(path)
        _private_directory(paths["journal_path"], repository_root=paths["control_repository"])
        if not isinstance(value["actor_id"], str) or not JOB_ID.fullmatch(value["actor_id"]):
            raise SettingsError("explicit caller actor required")
        if (value["repository_id"], value["exact_base_sha"], value["exact_base_tree"]) != (TARGET_REPOSITORY_ID, TARGET_BASE_SHA, TARGET_BASE_TREE):
            raise SettingsError("caller source identity mismatch")
        if (type(value["deadline_seconds"]) is not int or not 30 <= value["deadline_seconds"] <= 1800
                or type(value["retention_seconds"]) is not int or not value["deadline_seconds"] <= value["retention_seconds"] <= 86400):
            raise SettingsError("bounded caller deadlines required")
        items = value["backends"]
        if not isinstance(items, list) or not 1 <= len(items) <= 5:
            raise SettingsError("one to five ordered backends required")
        backends = []
        for ordinal, item in enumerate(items):
            if not isinstance(item, dict) or set(item) != {"profile_id", "socket_path", "token_file", "profile_digest"} or item["profile_id"] != PROVIDER_ORDER[ordinal]:
                raise SettingsError("fixed provider order required")
            profile = HttpLandingProfile.for_provider(item["profile_id"], available=True)
            if item["profile_digest"] != profile.profile_digest:
                raise SettingsError("caller profile identity mismatch")
            socket, token = absolute_path(item["socket_path"]), absolute_path(item["token_file"])
            check_socket_ancestry(socket)
            _check_ancestry(token.parent)
            for leaf in (socket, token):
                if any(leaf == root or root in leaf.parents for root in roots):
                    raise SettingsError("caller sockets and credentials must be outside data roots")
            backends.append(BackendSpec(item["profile_id"], socket, token, profile.profile_digest))
        if len({item.socket_path for item in backends}) != len(backends) or len({item.token_file for item in backends}) != len(backends):
            raise SettingsError("independent backend identities required")
        return cls(**paths, **{name: value[name] for name in (
            "actor_id", "repository_id", "exact_base_sha", "exact_base_tree", "deadline_seconds", "retention_seconds",
        )}, backends=tuple(backends), digest=landing_digest("landing-failover-config-v1", value))


def load_failover_config(path):
    path = absolute_path(str(path))
    value = FailoverConfig.from_dict(strict_json_object(read_private_file(path, 32_768), maximum=32_768))
    if any(path == root or root in path.parents for root in (value.control_repository, value.source_path, value.journal_path)):
        raise SettingsError("caller configuration must be outside data roots")
    return value
