"""Offline landing host configuration and private filesystem validation."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat

from .landing_contracts import strict_json_object
from .settings import FactorySettings, SettingsError, read_private_file


@dataclass(frozen=True)
class LandingHostConfig:
    settings: FactorySettings
    control_repository: Path
    publication_state: Path


def load_host_config(path: Path) -> LandingHostConfig:
    # A double-slash anchor can alias / on the host while Path comparisons
    # treat it as a different root, defeating the disjointness checks below.
    if path.anchor == "//":
        raise SettingsError("absolute normalized landing host paths required")
    data = strict_json_object(read_private_file(path, 16_384), maximum=16_384)
    expected = {"schema_version", "control_repository", "socket_path", "actors_file",
                "state_path", "quarantine_path", "source_path", "scratch_path",
                "output_path", "publication_state_path", "live_enabled", "selected_profile"}
    if set(data) != expected or type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise SettingsError("closed landing host configuration required")
    selectable = ("qwen-omni", "qwen-omni-intl", "grok-vision", "qwen-intl",
                  "openai", "anthropic", "openrouter")
    if type(data["live_enabled"]) is not bool or data["selected_profile"] not in selectable:
        raise SettingsError("explicit landing capability profile required")
    paths = {}
    for name in expected - {"schema_version", "live_enabled", "selected_profile"}:
        value = data[name]
        if (not isinstance(value, str) or not value.startswith("/")
                or Path(value).anchor == "//" or ".." in Path(value).parts):
            raise SettingsError("absolute normalized landing host paths required")
        paths[name] = Path(value)
    settings = FactorySettings(
        database_url="", socket_path=paths["socket_path"], actors_file=paths["actors_file"],
        landing_state_path=paths["state_path"], landing_quarantine_path=paths["quarantine_path"],
        landing_source_path=paths["source_path"], landing_scratch_path=paths["scratch_path"],
        landing_output_path=paths["output_path"], landing_live_enabled=data["live_enabled"],
        landing_provider=data["selected_profile"] if data["live_enabled"] else "unavailable",
    )
    settings.validate_landing()
    roots = [paths[name] for name in (
        "state_path", "quarantine_path", "source_path", "scratch_path", "output_path",
        "publication_state_path", "control_repository",
    )]
    if any(left == right or left in right.parents or right in left.parents
           for index, left in enumerate(roots) for right in roots[index + 1:]):
        raise SettingsError("landing host roots must be disjoint")
    for secret_path in (paths["actors_file"], paths["socket_path"], path):
        if any(secret_path == root or root in secret_path.parents for root in roots):
            raise SettingsError("configuration and sockets must be outside durable data roots")
    return LandingHostConfig(settings, paths["control_repository"], paths["publication_state_path"])


def _check_ancestry(path: Path) -> None:
    for component in (path, *path.parents):
        metadata = component.lstat()
        root_sticky = metadata.st_uid == 0 and bool(metadata.st_mode & stat.S_ISVTX)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or metadata.st_uid not in {0, os.geteuid()}
            or (metadata.st_mode & 0o022 and not root_sticky)
        ):
            raise SettingsError("landing directory ancestry is not trusted")


def _private_directory(path: Path, *, repository_root: Path) -> None:
    _check_ancestry(path)
    metadata = path.lstat()
    if (
        metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700
        or path == repository_root or repository_root in path.parents
        or path in repository_root.parents
    ):
        raise SettingsError("landing runtime roots must be private and outside the repository")
