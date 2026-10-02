#!/usr/bin/env python3
"""Offline Factory release lifecycle policy; runtime authority is explicitly injected.

Safety patterns adapted with owner authorization from Dimkox/liqvera at
e3df6833e8916d01f55028e63d4db1632a805a75. Upstream has no open-source license.
No Liqvera service configuration, launchers, or executable payload is included.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import secrets
import shutil
import socket
import stat
import time
from typing import Protocol
import zipfile

MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_FILES = 4096
MAX_JSON_BYTES = 1024 * 1024
MAX_BACKUP_BYTES = 1024 * 1024 * 1024
HEX = re.compile(r"[0-9a-f]{64}\Z")
MARKER = ".factory-release.json"
DIRECTORIES = ("state", "releases", "config", "data", "backups", "logs")
PHASES = {"ready", "stopped", "removed", "failed", "prepared", "starting", "healthy", "switched", "removing", "purging"}
TERMINAL = {"ready", "stopped", "removed", "failed"}
SECRET_LINE = re.compile(
    r"(?i)password|passwd|secret|token|api[_-]?key|authorization|credential|private[_ -]?key|"
    r"://[^/\s]+:[^/\s]+@|-----BEGIN|\b(?:sk|ghp|github_pat)-?[_A-Za-z0-9]{12,}"
)


class InstallerError(RuntimeError):
    """Only a closed code is exposed; underlying exceptions may contain secrets."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hex(value: object) -> str:
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise InstallerError("INVALID_DIGEST")
    return value


def _read(path: Path, maximum: int) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        with os.fdopen(descriptor, "rb") as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
                raise InstallerError("UNSAFE_FILE")
            content = handle.read(maximum + 1)
            after = os.fstat(handle.fileno())
            if len(content) > maximum or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns
            ):
                raise InstallerError("UNSAFE_FILE")
            return content
    except OSError as exc:
        raise InstallerError("UNSAFE_FILE") from exc


def _json(content: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise InstallerError("INVALID_JSON")
            result[key] = value
        return result

    try:
        if len(content) > MAX_JSON_BYTES:
            raise InstallerError("INVALID_JSON")
        value = json.loads(content, object_pairs_hook=unique)
        if not isinstance(value, dict):
            raise InstallerError("INVALID_JSON")
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InstallerError("INVALID_JSON") from exc


def _path(value: object) -> str:
    if (not isinstance(value, str) or len(value) > 512
            or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", value)
            or any(part in {".", ".."} for part in value.split("/"))
            or len(value.split("/")) > 32 or value == MARKER):
        raise InstallerError("UNSAFE_ARCHIVE_PATH")
    return value


def _manifest(content: bytes) -> dict:
    value = _json(content)
    if (set(value) != {"schema_version", "product_version", "profile", "data_schema", "files"}
            or value["schema_version"] != "factory-release/v1"
            or value["profile"] != "factory-python"
            or not isinstance(value["product_version"], str)
            or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", value["product_version"])
            or type(value["data_schema"]) is not int or not 0 <= value["data_schema"] <= 1000000
            or not isinstance(value["files"], list) or not 1 <= len(value["files"]) <= MAX_FILES):
        raise InstallerError("INVALID_MANIFEST")
    names = set()
    total = 0
    for item in value["files"]:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256", "mode"}:
            raise InstallerError("INVALID_MANIFEST")
        name = _path(item["path"])
        if (name in names or type(item["size"]) is not int or not 0 <= item["size"] <= MAX_FILE_BYTES
                or type(item["mode"]) is not int or item["mode"] not in {0o644, 0o755}):
            raise InstallerError("INVALID_MANIFEST")
        _hex(item["sha256"])
        names.add(name)
        total += item["size"]
    if total > MAX_TOTAL_BYTES or any(str(parent) in names for name in names for parent in PurePosixPath(name).parents):
        raise InstallerError("INVALID_MANIFEST")
    return value


@dataclass(frozen=True)
class VerifiedRelease:
    archive_sha256: str
    manifest_sha256: str
    manifest_bytes: bytes
    files: tuple[tuple[str, bytes, int], ...]

    @property
    def identity(self) -> str:
        return _digest((self.archive_sha256 + self.manifest_sha256).encode("ascii"))

    @property
    def manifest(self) -> dict:
        return _manifest(self.manifest_bytes)


def verify_release(*, archive: Path, manifest: Path, archive_sha256: str, manifest_sha256: str) -> VerifiedRelease:
    """Both SHA-256 values must come from an independent trusted channel."""
    _hex(archive_sha256)
    _hex(manifest_sha256)
    archive_bytes = _read(Path(archive), MAX_ARCHIVE_BYTES)
    manifest_bytes = _read(Path(manifest), MAX_JSON_BYTES)
    if _digest(archive_bytes) != archive_sha256 or _digest(manifest_bytes) != manifest_sha256:
        raise InstallerError("DIGEST_MISMATCH")
    inventory = {item["path"]: item for item in _manifest(manifest_bytes)["files"]}
    files = []
    seen = set()
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as handle:
            members = handle.infolist()
            if not 1 <= len(members) <= MAX_FILES or len(members) != len(inventory):
                raise InstallerError("INVENTORY_MISMATCH")
            for member in members:
                name = _path(member.filename)
                item = inventory.get(name)
                mode = member.external_attr >> 16
                if (name in seen or item is None or member.is_dir()
                        or stat.S_IFMT(mode) not in {0, stat.S_IFREG}
                        or stat.S_IMODE(mode) != item["mode"] or member.flag_bits & 1
                        or member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                        or member.file_size != item["size"] or member.file_size > MAX_FILE_BYTES):
                    raise InstallerError("UNSAFE_ARCHIVE")
                with handle.open(member) as source:
                    content = source.read(MAX_FILE_BYTES + 1)
                if len(content) != item["size"] or _digest(content) != item["sha256"]:
                    raise InstallerError("INVENTORY_MISMATCH")
                files.append((name, content, item["mode"]))
                seen.add(name)
    except (zipfile.BadZipFile, RuntimeError, ValueError, OSError, EOFError) as exc:
        raise InstallerError("INVALID_ARCHIVE") from exc
    return VerifiedRelease(archive_sha256, manifest_sha256, manifest_bytes, tuple(files))


def _safe_root(root: Path) -> Path:
    root = Path(root)
    if (not root.is_absolute() or len(root.parts) < 3 or ".." in root.parts
            or root == Path.home() or root == Path.cwd()):
        raise InstallerError("UNSAFE_ROOT")
    candidate = Path("/")
    for part in root.parts[1:]:
        candidate /= part
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in {0, os.getuid()}
                or info.st_mode & 0o022 and not (info.st_uid == 0 and info.st_mode & stat.S_ISVTX)):
            raise InstallerError("UNSAFE_ROOT")
        if candidate == root and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise InstallerError("UNSAFE_ROOT")
    return root


def _pristine_initialization(root: Path) -> bool:
    """Only an exact empty, private subset of our topology is replayable."""
    for entry in root.iterdir():
        info = entry.lstat()
        if (entry.name not in DIRECTORIES or not stat.S_ISDIR(info.st_mode)
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700):
            return False
        for child in entry.iterdir():
            metadata = child.lstat()
            if (entry.name != "state" or child.name != "lock" or not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600
                    or metadata.st_nlink != 1 or metadata.st_size != 0):
                return False
    return True


def preflight(root: Path, *, platform_name: str | None = None, minimum_free_bytes: int = MAX_TOTAL_BYTES,
              minimum_memory_bytes: int = 128 * 1024 * 1024, ports: tuple[int, ...] = ()) -> dict:
    """Read-only host checks. No package manager, privilege escalation, or daemon calls."""
    root = _safe_root(root)
    if (platform_name or platform.system()) != "Linux" or not hasattr(os, "O_NOFOLLOW"):
        raise InstallerError("UNSUPPORTED_HOST")
    if root.exists() and any(root.iterdir()):
        if (root / "state").exists():
            _safe_root(root / "state")
        if (root / "state/install.json").exists():
            state = _json(_read(root / "state/install.json", MAX_JSON_BYTES))
            if state.get("schema_version") != "factory-install/v1" or state.get("root") != str(root):
                raise InstallerError("UNSAFE_INSTALLATION")
        elif not _pristine_initialization(root):
            raise InstallerError("RECONCILIATION_REQUIRED")
    ancestor = root
    while not ancestor.exists():
        ancestor = ancestor.parent
    if (type(minimum_free_bytes) is not int or minimum_free_bytes < 0
            or shutil.disk_usage(ancestor).free < minimum_free_bytes):
        raise InstallerError("DISK_REQUIRED")
    if (type(minimum_memory_bytes) is not int or minimum_memory_bytes < 0
            or os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") < minimum_memory_bytes):
        raise InstallerError("MEMORY_REQUIRED")
    if len(ports) > 16:
        raise InstallerError("INVALID_PORT")
    for port in ports:
        if type(port) is not int or not 1 <= port <= 65535:
            raise InstallerError("INVALID_PORT")
        try:
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise InstallerError("PORT_UNAVAILABLE") from exc
    return {"schema_version": "factory-preflight/v1", "root": str(root), "platform": "Linux", "ready": True}


class RuntimeAdapter(Protocol):
    """Trusted operator adapter: honor time/byte limits; isolate candidate from prior.

    preflight/status/health/logs are read-only. Never migrate data in start/stop.
    The adapter owns service authorization, finite waits, and per-release isolation.
    """

    def preflight(self, profile: str, timeout: int) -> bool: ...
    def start(self, release: Path, timeout: int) -> None: ...
    def stop(self, release: Path, timeout: int) -> None: ...
    def health(self, release: Path, timeout: int) -> bool: ...
    def status(self, release: Path, timeout: int) -> bool: ...
    def logs(self, release: Path, lines: int, maximum_bytes: int, timeout: int) -> str: ...


class UnavailableRuntimeAdapter:
    """Concrete fail-closed default: no implicit daemon or service authority."""

    def preflight(self, profile: str, timeout: int) -> bool:
        raise InstallerError("ADAPTER_REQUIRED")

    def start(self, release: Path, timeout: int) -> None:
        raise InstallerError("ADAPTER_REQUIRED")

    def stop(self, release: Path, timeout: int) -> None:
        raise InstallerError("ADAPTER_REQUIRED")

    def health(self, release: Path, timeout: int) -> bool:
        raise InstallerError("ADAPTER_REQUIRED")

    def status(self, release: Path, timeout: int) -> None:
        return None

    def logs(self, release: Path, lines: int, maximum_bytes: int, timeout: int) -> str:
        raise InstallerError("ADAPTER_REQUIRED")


@dataclass(frozen=True)
class TransitionEvidence:
    root: str
    prior: str
    candidate: str
    data_schema: int
    backup: Path
    backup_sha256: str


def _validate_transition(value: dict, *, completed: bool = False) -> None:
    required = {"id", "candidate", "prior", "kind", "backup", "schema_prior", "schema_candidate",
                "compatibility", "runtime_preflight", "health"}
    if completed:
        required.add("completed_generation")
    if (not isinstance(value, dict) or set(value) != required
            or not isinstance(value["id"], str) or not re.fullmatch(r"[0-9a-f]{32}", value["id"])
            or value["kind"] not in {"install", "update", "reverse", "restart"}
            or type(value["schema_candidate"]) is not int or not 0 <= value["schema_candidate"] <= 1000000
            or value["schema_prior"] is not None and (type(value["schema_prior"]) is not int
                                                       or not 0 <= value["schema_prior"] <= 1000000)
            or value["runtime_preflight"] is not True or type(value["health"]) is not bool):
        raise InstallerError("INVALID_STATE")
    _hex(value["candidate"])
    if value["prior"] is not None:
        _hex(value["prior"])
    expected = "new-empty-installation" if value["schema_prior"] is None else "same-schema"
    if (value["compatibility"] != expected or expected == "same-schema"
            and value["schema_prior"] != value["schema_candidate"]):
        raise InstallerError("INVALID_STATE")
    backup = value["backup"]
    if backup is not None:
        if (not isinstance(backup, dict) or set(backup) != {"path", "sha256"}
                or not isinstance(backup["path"], str) or len(backup["path"]) > 512
                or not backup["path"].startswith("backups/") or ".." in Path(backup["path"]).parts):
            raise InstallerError("INVALID_STATE")
        _hex(backup["sha256"])
    if value["kind"] in {"update", "reverse"} and backup is None:
        raise InstallerError("INVALID_STATE")
    if completed and (value["health"] is not True or type(value["completed_generation"]) is not int
                      or value["completed_generation"] < 1):
        raise InstallerError("INVALID_STATE")


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(".write-" + secrets.token_hex(16))
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


class SetupManager:
    def __init__(self, root: Path, adapter: RuntimeAdapter | None = None):
        self.root = _safe_root(root)
        self.adapter = adapter if adapter is not None else UnavailableRuntimeAdapter()

    def _runtime(self, method: str, *args, **kwargs):
        started = time.monotonic()
        try:
            result = getattr(self.adapter, method)(*args, timeout=30, **kwargs)
        except InstallerError as exc:
            if exc.code == "ADAPTER_REQUIRED":
                raise
            raise InstallerError("RUNTIME_FAILED") from exc
        except Exception as exc:
            raise InstallerError("RUNTIME_FAILED") from exc
        if time.monotonic() - started > 30:
            raise InstallerError("RUNTIME_TIMEOUT")
        return result

    def _tree(self) -> list[tuple[str, int, int, int, int]]:
        """Inspect metadata only, including data/config; never acquire secret contents."""
        result = []
        for directory in DIRECTORIES:
            base = self.root / directory
            if not base.exists() and not base.is_symlink():
                continue
            stack = [base]
            while stack:
                entry = stack.pop()
                info = entry.lstat()
                if (info.st_uid != os.getuid() or stat.S_ISLNK(info.st_mode)
                        or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode))
                        or stat.S_ISREG(info.st_mode) and info.st_nlink != 1
                        or info.st_mode & 0o002):
                    raise InstallerError("UNSAFE_INSTALLATION")
                result.append((str(entry.relative_to(self.root)), info.st_ino,
                               info.st_size, info.st_mtime_ns, info.st_mode))
                if len(result) > 20000 or len(entry.relative_to(self.root).parts) > 40:
                    raise InstallerError("INSTALLATION_LIMIT")
                if stat.S_ISDIR(info.st_mode):
                    stack.extend(entry.iterdir())
        return sorted(result)

    def _state(self) -> dict:
        _safe_root(self.root)
        self._tree()
        path = self.root / "state/install.json"
        value = _json(_read(path, MAX_JSON_BYTES))
        value.setdefault("last_transition", None)  # Existing v1 state remains readable.
        if (set(value) != {"schema_version", "root", "generation", "phase", "current", "previous",
                           "data_schema", "operation", "last_transition"}
                or value["schema_version"] != "factory-install/v1" or value["root"] != str(self.root)
                or type(value["generation"]) is not int or value["generation"] < 0
                or not isinstance(value["phase"], str) or value["phase"] not in PHASES
                or value["data_schema"] is not None and (type(value["data_schema"]) is not int
                                                          or not 0 <= value["data_schema"] <= 1000000)):
            raise InstallerError("INVALID_STATE")
        for key in ("current", "previous"):
            if value[key] is not None:
                _hex(value[key])
        operation = value["operation"]
        if operation is not None:
            if (not isinstance(operation, dict)
                    or not isinstance(operation.get("id"), str) or not re.fullmatch(r"[0-9a-f]{32}", operation["id"])):
                raise InstallerError("INVALID_STATE")
            if set(operation) != {"id", "candidate", "prior"}:
                _validate_transition(operation)
            _hex(operation["candidate"])
            if operation["prior"] is not None:
                _hex(operation["prior"])
        if value["last_transition"] is not None:
            _validate_transition(value["last_transition"], completed=True)
        actual = self._pointer()
        if value["phase"] in TERMINAL and actual != value["current"]:
            raise InstallerError("RECONCILIATION_REQUIRED")
        return value

    def _pointer(self) -> str | None:
        path = self.root / "current"
        try:
            target = os.readlink(path)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise InstallerError("UNSAFE_POINTER") from exc
        if not re.fullmatch(r"releases/[0-9a-f]{64}", target):
            raise InstallerError("UNSAFE_POINTER")
        return target.split("/")[1]

    def _save(self, state: dict, phase: str, **fields) -> None:
        state.update(fields, phase=phase, generation=state["generation"] + 1)
        _atomic_json(self.root / "state/install.json", state)

    @contextmanager
    def _lock(self, *, create=False, recover_initial=False):
        _safe_root(self.root)
        if not self.root.exists():
            if not create or not self.root.parent.exists():
                raise InstallerError("INSTALLATION_ABSENT")
            self.root.mkdir(mode=0o700)
            _sync_directory(self.root.parent)
        initial = not (self.root / "state/install.json").exists()
        if initial:
            if not (create or recover_initial) or not _pristine_initialization(self.root):
                raise InstallerError("RECONCILIATION_REQUIRED")
            (self.root / "state").mkdir(mode=0o700, exist_ok=True)
        self._tree()
        descriptor = os.open(self.root / "state/lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise InstallerError("INSTALLATION_LOCKED") from exc
            if initial:
                # Recheck after acquiring the durable lock; no data/unknown bytes are adopted.
                if not _pristine_initialization(self.root):
                    raise InstallerError("RECONCILIATION_REQUIRED")
                for directory in DIRECTORIES:
                    (self.root / directory).mkdir(mode=0o700, exist_ok=True)
                _atomic_json(self.root / "state/install.json", {
                    "schema_version": "factory-install/v1", "root": str(self.root), "generation": 0,
                    "phase": "stopped", "current": None, "previous": None, "data_schema": None,
                    "operation": None, "last_transition": None,
                })
                _sync_directory(self.root)
            state = self._state()
            yield state
        finally:
            os.close(descriptor)

    def _idle(self, state: dict) -> None:
        if state["phase"] not in TERMINAL:
            raise InstallerError("RECONCILIATION_REQUIRED")

    def _release(self, identity: str) -> tuple[Path, dict]:
        _hex(identity)
        path = self.root / "releases" / identity
        self._tree()
        marker = _json(_read(path / MARKER, MAX_JSON_BYTES))
        if set(marker) != {"archive_sha256", "manifest_sha256", "manifest"}:
            raise InstallerError("INVALID_RELEASE")
        archive_sha = _hex(marker["archive_sha256"])
        manifest_sha = _hex(marker["manifest_sha256"])
        if not isinstance(marker["manifest"], str):
            raise InstallerError("INVALID_RELEASE")
        content = marker["manifest"].encode()
        manifest = _manifest(content)
        if _digest(content) != manifest_sha or _digest((archive_sha + manifest_sha).encode()) != identity:
            raise InstallerError("INVALID_RELEASE")
        expected = {item["path"]: item for item in manifest["files"]}
        expected_directories = {str(parent) for name in expected for parent in PurePosixPath(name).parents
                                if str(parent) != "."}
        if stat.S_IMODE(path.stat().st_mode) != 0o555 or stat.S_IMODE((path / MARKER).stat().st_mode) != 0o444:
            raise InstallerError("INVALID_RELEASE")
        actual = set()
        actual_directories = set()
        for entry in path.rglob("*"):
            name = str(entry.relative_to(path))
            if entry.is_dir():
                if stat.S_IMODE(entry.stat().st_mode) != 0o555:
                    raise InstallerError("INVALID_RELEASE")
                actual_directories.add(name)
            elif name != MARKER:
                item = expected.get(name)
                if item is None or stat.S_IMODE(entry.stat().st_mode) != item["mode"] & ~0o222:
                    raise InstallerError("INVALID_RELEASE")
                content = _read(entry, MAX_FILE_BYTES)
                if len(content) != item["size"] or _digest(content) != item["sha256"]:
                    raise InstallerError("INVALID_RELEASE")
                actual.add(name)
        if actual != set(expected) or actual_directories != expected_directories:
            raise InstallerError("INVALID_RELEASE")
        return path, manifest

    def _stage(self, release: VerifiedRelease) -> Path:
        path = self.root / "releases" / release.identity
        if path.exists():
            self._release(release.identity)
            return path
        temporary = self.root / "releases" / (".stage-" + secrets.token_hex(16))
        temporary.mkdir(mode=0o700)
        # Stage from the captured verified bytes; archive is never reopened or extractall'd.
        for name, content, mode in release.files:
            entry = temporary / name
            entry.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            descriptor = os.open(entry, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode & ~0o222)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        _atomic_json(temporary / MARKER, {"archive_sha256": release.archive_sha256,
                                         "manifest_sha256": release.manifest_sha256,
                                         "manifest": release.manifest_bytes.decode()})
        (temporary / MARKER).chmod(0o444)
        for directory in sorted((entry for entry in temporary.rglob("*") if entry.is_dir()), reverse=True):
            directory.chmod(0o555)
            _sync_directory(directory)
        temporary.chmod(0o555)
        _sync_directory(temporary)
        os.rename(temporary, path)
        _sync_directory(path.parent)
        self._release(release.identity)
        return path

    def _switch(self, identity: str) -> None:
        temporary = self.root / (".current-" + secrets.token_hex(16))
        temporary.symlink_to("releases/" + _hex(identity))
        os.replace(temporary, self.root / "current")
        _sync_directory(self.root)

    def _evidence(self, state: dict, identity: str, manifest: dict, evidence: TransitionEvidence | None) -> dict:
        if (not isinstance(evidence, TransitionEvidence) or evidence.root != str(self.root)
                or evidence.prior != state["current"] or evidence.candidate != identity
                or type(evidence.data_schema) is not int or evidence.data_schema != state["data_schema"]
                or manifest["data_schema"] != state["data_schema"]):
            raise InstallerError("BACKUP_COMPATIBILITY_REQUIRED")
        backup = Path(evidence.backup)
        if not backup.is_absolute() or ".." in backup.parts or not backup.is_relative_to(self.root / "backups"):
            raise InstallerError("BACKUP_COMPATIBILITY_REQUIRED")
        self._tree()
        _hex(evidence.backup_sha256)
        if _digest(_read(backup, MAX_BACKUP_BYTES)) != evidence.backup_sha256:
            raise InstallerError("BACKUP_COMPATIBILITY_REQUIRED")
        relative = str(backup.relative_to(self.root))
        if len(relative) > 512:
            raise InstallerError("BACKUP_COMPATIBILITY_REQUIRED")
        return {"path": relative, "sha256": evidence.backup_sha256}

    def _operation(self, state: dict, identity: str, manifest: dict, kind: str, backup: dict | None = None) -> dict:
        value = {"id": secrets.token_hex(16), "candidate": identity, "prior": state["current"], "kind": kind,
                 "backup": backup, "schema_prior": state["data_schema"], "schema_candidate": manifest["data_schema"],
                 "compatibility": "new-empty-installation" if state["data_schema"] is None else "same-schema",
                 "runtime_preflight": True, "health": False}
        _validate_transition(value)
        return value

    def _last_success(self, state: dict, operation: dict) -> dict | None:
        if operation["candidate"] == operation["prior"]:
            return state["last_transition"]
        value = dict(operation, health=True, completed_generation=state["generation"] + 1)
        _validate_transition(value, completed=True)
        return value

    def _activate(self, state: dict, identity: str, path: Path, manifest: dict,
                  *, kind: str = "restart", backup: dict | None = None) -> str:
        prior = state["current"]
        previous = state["previous"] if prior == identity else prior
        operation = state["operation"] if state["phase"] == "prepared" else self._operation(
            state, identity, manifest, kind, backup)
        self._save(state, "starting", operation=operation)
        try:
            self._runtime("start", path)
            if self._runtime("health", path) is not True:
                raise InstallerError("HEALTH_FAILED")
            operation["health"] = True
            self._save(state, "healthy", operation=operation)
            self._switch(identity)
            self._save(state, "switched", current=identity, previous=previous, data_schema=manifest["data_schema"])
        except Exception:
            # An already-switched pointer is ambiguous until explicit reconciliation.
            if self._pointer() == prior:
                try:
                    self._runtime("stop", path)
                except InstallerError:
                    raise InstallerError("RECONCILIATION_REQUIRED") from None
                self._save(state, "failed", current=prior)
            raise
        if prior is not None and prior != identity:
            prior_path, _ = self._release(prior)
            self._runtime("stop", prior_path)
        self._save(state, "ready", operation=None, last_transition=self._last_success(state, operation))
        return identity

    def install(self, **artifact) -> str:
        release = verify_release(**artifact)
        preflight(self.root)
        if self._runtime("preflight", release.manifest["profile"]) is not True:
            raise InstallerError("RUNTIME_UNAVAILABLE")
        with self._lock(create=True) as state:
            self._idle(state)
            if state["current"] == release.identity:
                self._release(release.identity)
                return release.identity
            if state["current"] is not None or state["data_schema"] is not None:
                raise InstallerError("UPDATE_REQUIRED")
            self._save(state, "prepared", operation=self._operation(state, release.identity, release.manifest, "install"))
            path = self._stage(release)
            return self._activate(state, release.identity, path, release.manifest)

    def update(self, *, evidence: TransitionEvidence | None = None, **artifact) -> str:
        release = verify_release(**artifact)
        preflight(self.root)
        if self._runtime("preflight", release.manifest["profile"]) is not True:
            raise InstallerError("RUNTIME_UNAVAILABLE")
        with self._lock() as state:
            self._idle(state)
            if state["current"] == release.identity:
                self._release(release.identity)
                return release.identity
            backup = self._evidence(state, release.identity, release.manifest, evidence)
            self._save(state, "prepared", operation=self._operation(state, release.identity, release.manifest, "update", backup))
            return self._activate(state, release.identity, self._stage(release), release.manifest)

    def reverse(self, identity: str, *, evidence: TransitionEvidence | None = None) -> str:
        preflight(self.root)
        with self._lock() as state:
            self._idle(state)
            path, manifest = self._release(identity)
            backup = self._evidence(state, identity, manifest, evidence)
            if self._runtime("preflight", manifest["profile"]) is not True:
                raise InstallerError("RUNTIME_UNAVAILABLE")
            return self._activate(state, identity, path, manifest, kind="reverse", backup=backup)

    def status(self) -> dict:
        if not self.root.exists():
            return {"schema_version": "factory-status/v1", "root": str(self.root), "phase": "absent", "current": None}
        state = self._state()
        running = None
        if (state["current"] is not None and state["phase"] not in {"purging", "removing"}
                and not isinstance(self.adapter, UnavailableRuntimeAdapter)):
            running = self._runtime("status", self._release(state["current"])[0])
            if type(running) is not bool:
                raise InstallerError("RUNTIME_FAILED")
        return dict(state, schema_version="factory-status/v1", running=running)

    def start(self) -> None:
        preflight(self.root)
        with self._lock() as state:
            self._idle(state)
            if state["current"] is None:
                raise InstallerError("INSTALLATION_ABSENT")
            path, manifest = self._release(state["current"])
            if self._runtime("preflight", manifest["profile"]) is not True:
                raise InstallerError("RUNTIME_UNAVAILABLE")
            if self._runtime("status", path) is True and self._runtime("health", path) is True:
                return
            self._activate(state, state["current"], path, manifest)

    def stop(self) -> None:
        with self._lock() as state:
            self._idle(state)
            if state["current"] is None:
                return
            path, _ = self._release(state["current"])
            if self._runtime("status", path) is True:
                self._runtime("stop", path)
            if state["phase"] != "stopped":
                self._save(state, "stopped", operation=None)

    def logs(self, *, lines: int = 100, maximum_bytes: int = 65536) -> str:
        if type(lines) is not int or not 1 <= lines <= 1000 or type(maximum_bytes) is not int or not 1 <= maximum_bytes <= 65536:
            raise InstallerError("INVALID_LOG_LIMIT")
        state = self._state()
        if state["current"] is None:
            return ""
        path, _ = self._release(state["current"])
        text = self._runtime("logs", path, lines=lines, maximum_bytes=maximum_bytes)
        if not isinstance(text, str):
            raise InstallerError("RUNTIME_FAILED")
        # Redact before truncation so a partial secret never escapes at the byte boundary.
        bounded = text[:65536]
        bounded = re.sub(r"-----BEGIN[^\n]*-----.*?(?:-----END[^\n]*-----|\Z)", "[REDACTED]",
                         bounded, flags=re.DOTALL)
        result = "\n".join("[REDACTED]" if SECRET_LINE.search(line)
                           or any(not char.isprintable() and char != "\t" for char in line) else line
                           for line in bounded.split("\n")[-lines:])
        return result.encode()[:maximum_bytes].decode("utf-8", "ignore")

    def _purge_token(self, state: dict) -> str:
        inventory = [item for item in self._tree() if item[0].split("/")[0] != "state"]
        binding = {"root": str(self.root), "generation": state["generation"], "current": state["current"],
                   "root_identity": [self.root.stat().st_dev, self.root.stat().st_ino],
                   "targets": ["releases", "config", "data", "backups", "logs"], "inventory": inventory}
        return "purge-" + _digest(json.dumps(binding, sort_keys=True).encode())

    def purge_token(self) -> str:
        return self._purge_token(self._state())

    def remove(self, *, purge: bool = False, token: str | None = None) -> None:
        with self._lock() as state:
            self._idle(state)
            if purge and (not isinstance(token, str) or not secrets.compare_digest(token, self._purge_token(state))):
                raise InstallerError("PURGE_CONFIRMATION_REQUIRED")
            if state["phase"] == "removed" and not purge:
                return
            self._save(state, "removing", operation=None)
            if state["current"] is not None:
                path, _ = self._release(state["current"])
                self._runtime("stop", path)
                (self.root / "current").unlink()
                _sync_directory(self.root)
            if purge:
                self._save(state, "purging")
                for directory in ("releases", "config", "data", "backups", "logs"):
                    target = self.root / directory
                    if target.exists():
                        # Only the validated, exact target-bound private tree is writable for removal.
                        for entry in target.rglob("*"):
                            if entry.is_dir():
                                entry.chmod(0o700)
                        target.chmod(0o700)
                        shutil.rmtree(target)
                _sync_directory(self.root)
            if state["phase"] != "removed" or purge:
                self._save(state, "removed", current=None, previous=None, operation=None,
                           data_schema=None if purge else state["data_schema"])

    def reconcile(self) -> None:
        with self._lock(recover_initial=True) as state:
            if state["phase"] in TERMINAL:
                return
            if state["phase"] == "purging":
                raise InstallerError("RECOVERY_REQUIRED")
            if state["phase"] == "removing":
                current = self._pointer()
                if current not in {None, state["current"]}:
                    raise InstallerError("RECOVERY_REQUIRED")
                if state["current"] is not None:
                    self._runtime("stop", self._release(state["current"])[0])
                if current is not None:
                    (self.root / "current").unlink()
                    _sync_directory(self.root)
                self._save(state, "removed", current=None, previous=None, operation=None)
                return
            operation = state["operation"]
            if operation is None:
                raise InstallerError("RECONCILIATION_REQUIRED")
            current = self._pointer()
            candidate, prior = operation["candidate"], operation["prior"]
            if current == candidate and state["phase"] in {"healthy", "switched", "starting"}:
                if current != prior and set(operation) == {"id", "candidate", "prior"}:
                    raise InstallerError("RECOVERY_REQUIRED")
                path, manifest = self._release(candidate)
                if self._runtime("health", path) is not True:
                    raise InstallerError("RECOVERY_REQUIRED")
                if prior is not None and prior != candidate:
                    self._runtime("stop", self._release(prior)[0])
                previous = state["previous"] if prior == candidate else prior
                self._save(state, "ready", current=candidate, previous=previous,
                           data_schema=manifest["data_schema"], operation=None,
                           last_transition=self._last_success(state, operation))
            elif current == prior:
                path = self.root / "releases" / candidate
                if path.exists():
                    self._runtime("stop", self._release(candidate)[0])
                self._save(state, "failed", current=prior, operation=None)
            else:
                raise InstallerError("RECOVERY_REQUIRED")


def main(argv: list[str] | None = None, *, adapter: RuntimeAdapter | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify", "preflight", "install", "update", "reverse", "status", "logs",
                                            "start", "stop", "remove", "purge-token", "reconcile"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--archive-sha256")
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--release")
    parser.add_argument("--lines", type=int, default=100)
    parser.add_argument("--maximum-bytes", type=int, default=65536)
    parser.add_argument("--purge", action="store_true")
    parser.add_argument("--token")
    args = parser.parse_args(argv)
    try:
        manager = SetupManager(args.root, adapter)
        artifact = {key: getattr(args, key) for key in ("archive", "manifest", "archive_sha256", "manifest_sha256")}
        if args.command in {"verify", "install", "update"} and any(value is None for value in artifact.values()):
            raise InstallerError("ARTIFACT_ARGUMENTS_REQUIRED")
        if args.command == "verify":
            result = {"release": verify_release(**artifact).identity}
        elif args.command == "preflight":
            result = preflight(args.root)
        elif args.command in {"install", "update"}:
            result = {"release": getattr(manager, args.command)(**artifact)}
        elif args.command == "reverse":
            if args.release is None:
                raise InstallerError("RELEASE_REQUIRED")
            result = {"release": manager.reverse(args.release)}
        elif args.command == "logs":
            result = {"logs": manager.logs(lines=args.lines, maximum_bytes=args.maximum_bytes)}
        elif args.command == "purge-token":
            result = {"token": manager.purge_token()}
        elif args.command == "remove":
            manager.remove(purge=args.purge, token=args.token)
            result = manager.status()
        elif args.command == "status":
            result = manager.status()
        else:
            getattr(manager, args.command)()
            result = manager.status()
        print(json.dumps(result, sort_keys=True))
        return 0
    except (InstallerError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"schema_version": "factory-error/v1",
                          "error": exc.code if isinstance(exc, InstallerError) else "OPERATION_FAILED"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
