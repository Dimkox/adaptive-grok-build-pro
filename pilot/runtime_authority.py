"""Current-control binding and exact local-grant loading for live publication."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import importlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any

from .authority import AuthorityError, ControlBinding, LiteralGrantAuthority
from .contracts import HEX40, HEX64


CONTROL_REPOSITORY = "Dimkox/adaptive-grok-build-pro"
ROUTE_ID = "0ce2d62a018e"
CHANGE_ID = "20260905-feature-implement-a-single-operator-codex-github-0ce2d6"
_GITHUB_REMOTE = re.compile(
    r"(?:github\.com[:/])([^/\s]+/[^/\s]+?)(?:\.git)?$"
)


class RuntimeAuthorityError(AuthorityError):
    pass


class RuntimeGrantLoader:
    """Load grants only after independently observing the exact control state."""

    def __init__(
        self,
        control_repository: Path,
        *,
        git_executable: str = "/usr/bin/git",
        fingerprint: Callable[[Path], str] | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        root = Path(control_repository)
        if not root.is_absolute():
            raise RuntimeAuthorityError("control_repository")
        try:
            metadata = root.lstat()
            resolved = root.resolve(strict=True)
        except OSError as exc:
            raise RuntimeAuthorityError("control_repository") from exc
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or resolved != root
        ):
            raise RuntimeAuthorityError("control_repository")
        executable = Path(git_executable)
        try:
            executable_metadata = executable.lstat()
        except OSError as exc:
            raise RuntimeAuthorityError("git_executable") from exc
        if (
            not executable.is_absolute()
            or not stat.S_ISREG(executable_metadata.st_mode)
            or stat.S_ISLNK(executable_metadata.st_mode)
            or executable_metadata.st_mode & 0o111 == 0
        ):
            raise RuntimeAuthorityError("git_executable")
        self._root = resolved
        self._git_executable = str(executable)
        self._fingerprint = fingerprint or _adaptive_tree_fingerprint
        self._now = now

    def binding(self) -> ControlBinding:
        if Path(self._git("rev-parse", "--show-toplevel")).resolve(strict=True) != self._root:
            raise RuntimeAuthorityError("control_repository")
        remote = self._git("config", "--get", "remote.origin.url")
        match = _GITHUB_REMOTE.search(remote)
        if match is None or match.group(1).removesuffix(".git") != CONTROL_REPOSITORY:
            raise RuntimeAuthorityError("control_repository")
        head = self._git("rev-parse", "HEAD")
        if HEX40.fullmatch(head) is None:
            raise RuntimeAuthorityError("control_head")
        route = _read_json_object(
            self._root / ".grok-stack" / "runtime" / "active-route.json",
            "active_route",
        )
        change = _read_json_object(
            self._root / ".grok-stack" / "runtime" / "active-change.json",
            "active_change",
        )
        if route.get("route_id") != ROUTE_ID or route.get("change_id") != CHANGE_ID:
            raise RuntimeAuthorityError("active_route")
        if change.get("change_id") != CHANGE_ID:
            raise RuntimeAuthorityError("active_change")
        fingerprint = self._fingerprint(self._root)
        if not isinstance(fingerprint, str) or HEX64.fullmatch(fingerprint) is None:
            raise RuntimeAuthorityError("tree_fingerprint")
        return ControlBinding(
            repository=CONTROL_REPOSITORY,
            route_id=ROUTE_ID,
            change_id=CHANGE_ID,
            git_head=head,
            tree_fingerprint=fingerprint,
        )

    def load(self) -> LiteralGrantAuthority:
        binding = self.binding()
        grants = _read_grants(
            self._root / ".grok-stack" / "runtime" / "approvals.json"
        )
        return LiteralGrantAuthority(binding, grants, now=self._now)

    def _git(self, *arguments: str) -> str:
        environment = {
            "HOME": str(self._root),
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C",
            "TZ": "UTC",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "/bin/false",
        }
        try:
            completed = subprocess.run(
                (self._git_executable, *arguments),
                cwd=self._root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeAuthorityError("control_git") from exc
        if (
            completed.returncode != 0
            or len(completed.stdout) > 4096
            or len(completed.stderr) > 4096
        ):
            raise RuntimeAuthorityError("control_git")
        try:
            return completed.stdout.decode("utf-8").strip()
        except UnicodeError as exc:
            raise RuntimeAuthorityError("control_git") from exc


def _read_json_object(path: Path, code: str) -> dict[str, Any]:
    value = _read_json(path, code, maximum=131_072, private=False)
    if not isinstance(value, dict):
        raise RuntimeAuthorityError(code)
    return value


def _read_grants(path: Path) -> tuple[dict[str, Any], ...]:
    try:
        value = _read_json(path, "grant_store", maximum=1_048_576, private=True)
    except FileNotFoundError:
        return ()
    if (
        not isinstance(value, list)
        or len(value) > 200
        or any(not isinstance(item, dict) for item in value)
    ):
        raise RuntimeAuthorityError("grant_store")
    return tuple(dict(item) for item in value)


def _read_json(path: Path, code: str, *, maximum: int, private: bool) -> Any:
    try:
        metadata = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_nlink != 1
            or metadata.st_size > maximum
            or (private and metadata.st_mode & 0o077)
        ):
            raise RuntimeAuthorityError(code)
        raw = path.read_bytes()
        return json.loads(raw.decode("utf-8"))
    except FileNotFoundError:
        raise
    except RuntimeAuthorityError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeAuthorityError(code) from exc


def _adaptive_tree_fingerprint(root: Path) -> str:
    package_root = root / ".grok-stack"
    try:
        metadata = package_root.lstat()
    except OSError as exc:
        raise RuntimeAuthorityError("tree_fingerprint") from exc
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise RuntimeAuthorityError("tree_fingerprint")
    inserted = str(package_root)
    sys.path.insert(0, inserted)
    try:
        module = importlib.import_module("adaptive_grok.util")
        origin = Path(str(module.__file__)).resolve(strict=True)
        if package_root.resolve(strict=True) not in origin.parents:
            raise RuntimeAuthorityError("tree_fingerprint")
        value = module.tree_fingerprint(root)
    except RuntimeAuthorityError:
        raise
    except Exception as exc:
        raise RuntimeAuthorityError("tree_fingerprint") from exc
    finally:
        try:
            sys.path.remove(inserted)
        except ValueError:
            pass
    return value
