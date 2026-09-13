"""Offline landing host configuration and private filesystem validation."""

from __future__ import annotations

import os
from pathlib import Path
import stat

from .settings import SettingsError


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
