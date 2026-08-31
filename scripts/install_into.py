from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

MANAGED_DIRS = (".grok", ".agents", ".grok-stack")
MANAGED_FILES = (
    "scripts/grok_architecture.py",
    "scripts/grok_governance.py",
    "scripts/grok_route.py",
    "scripts/grok_change.py",
    "scripts/grok_spec.py",
    "scripts/grok_verify.py",
    "scripts/grok_review.py",
    "scripts/grok_approve.py",
    "scripts/grok_doctor.py",
    "scripts/grok_status.py",
    "scripts/grok_deploy.py",
    "session_start.py",
    "user_prompt_submit.py",
    "pre_tool_use.py",
    "post_tool_use.py",
    "pre_compact.py",
    "subagent_start.py",
    "subagent_stop.py",
    "stop_gate.py",
    "session_end.py",
    "ruff.toml",
    "bandit.yaml",
    ".coveragerc",
    "schemas/change-spec.schema.json",
    "schemas/change-spec-v1.schema.json",
    "schemas/architecture-system.schema.json",
    "schemas/architecture-rules.schema.json",
    "schemas/governance-rule.schema.json",
    "schemas/debt-entry.schema.json",
    "schemas/canonical-example.schema.json",
    "schemas/governance-handoff-v1.schema.json",
)
SKIP_PREFIXES = (".grok-stack/runtime/",)
TARGET_OWNED_ARCHITECTURE = frozenset(
    {
        "architecture/adoption.json",
        "architecture/rules.yaml",
        "architecture/system.yaml",
    }
)
TARGET_OWNED_GOVERNANCE = frozenset(
    {
        "governance/rules/index.json",
        "governance/debt/index.json",
        "governance/canonical-examples/index.json",
    }
)
EMPTY_DIRECTORIES = (
    "engineering/changes",
    "engineering/adr",
    "engineering/runbooks",
    "engineering/reviews",
    "engineering/contracts/openapi",
    "engineering/contracts/asyncapi",
    "engineering/contracts/schemas",
)
MANAGED_START = "<!-- ADAPTIVE-GROK-PRO:START -->"
MANAGED_END = "<!-- ADAPTIVE-GROK-PRO:END -->"
LEGACY_PLAN_NOTICE = (
    "NOTICE: legacy install mode now emits a read-only plan; "
    "use --materialize-new only for an absent target."
)
MANUAL_CLEANUP_PREFIX = "manual cleanup required: installer ownership is unresolved"
MAX_SOURCE_FILE_BYTES = 16 * 1024 * 1024
MAX_TOOLCHAIN_BYTES = 1024 * 1024
MAX_MANAGED_SOURCE_ENTRIES = 20_000
MAX_MANAGED_SOURCE_DEPTH = 64
RENAME_NOREPLACE = 1
_UNSUPPORTED_RENAME_ERRNOS = frozenset(
    {
        errno.ENOSYS,
        errno.EINVAL,
        getattr(errno, "EOPNOTSUPP", errno.ENOTSUP),
        errno.ENOTSUP,
    }
)


class UnsafeInstallTarget(RuntimeError):
    pass


@dataclass(frozen=True)
class InstallEntry:
    path: str
    content: bytes
    mode: int

    @property
    def size(self) -> int:
        return len(self.content)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()

    def manifest(self) -> dict[str, object]:
        return {
            "path": self.path,
            "action": "create",
            "mode": self.mode,
            "size": self.size,
            "sha256": self.sha256,
        }


def _identity(value: os.stat_result) -> tuple[int, int, int]:
    return value.st_dev, value.st_ino, value.st_mode


def _file_identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
        value.st_mode,
    )


@dataclass
class _DirectoryBinding:
    root_fd: int
    descriptor: int
    root_identity: tuple[int, int, int]
    components: tuple[tuple[str, tuple[int, int, int]], ...]

    def close(self) -> None:
        os.close(self.descriptor)
        os.close(self.root_fd)


def _open_child_directory(
    parent: int,
    component: str,
    expected: tuple[int, int, int] | None = None,
) -> tuple[int, tuple[int, int, int]]:
    nofollow, directory = _require_descriptor_primitives()
    metadata = os.stat(component, dir_fd=parent, follow_symlinks=False)
    identity = _identity(metadata)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or expected is not None and identity != expected
    ):
        raise UnsafeInstallTarget(f"directory component is unsafe: {component}")
    child = os.open(
        component,
        os.O_RDONLY | directory | nofollow,
        dir_fd=parent,
    )
    try:
        if _identity(os.fstat(child)) != identity:
            raise UnsafeInstallTarget(f"directory component changed: {component}")
    except BaseException:
        os.close(child)
        raise
    return child, identity


def _open_directory_binding(path: Path) -> _DirectoryBinding:
    nofollow, directory = _require_descriptor_primitives()
    absolute = Path(os.path.abspath(path))
    if not absolute.is_absolute():
        raise UnsafeInstallTarget("directory binding requires an absolute path")
    try:
        root_fd = os.open(os.path.sep, os.O_RDONLY | directory | nofollow)
    except OSError as exc:
        raise UnsafeInstallTarget(f"cannot bind filesystem root: {exc}") from exc
    root_identity = _identity(os.fstat(root_fd))
    current = os.dup(root_fd)
    components: list[tuple[str, tuple[int, int, int]]] = []
    try:
        for component in absolute.parts[1:]:
            child, identity = _open_child_directory(current, component)
            os.close(current)
            current = child
            components.append((component, identity))
        binding = _DirectoryBinding(
            root_fd,
            current,
            root_identity,
            tuple(components),
        )
        _check_directory_binding(binding)
        return binding
    except UnsafeInstallTarget:
        os.close(current)
        os.close(root_fd)
        raise
    except OSError as exc:
        os.close(current)
        os.close(root_fd)
        raise UnsafeInstallTarget(f"cannot bind directory ancestry: {exc}") from exc


def _check_directory_binding(binding: _DirectoryBinding) -> None:
    if _identity(os.fstat(binding.root_fd)) != binding.root_identity:
        raise UnsafeInstallTarget("filesystem root identity changed")
    current = os.dup(binding.root_fd)
    try:
        for component, expected in binding.components:
            child, _identity_value = _open_child_directory(
                current, component, expected
            )
            os.close(current)
            current = child
        if _identity(os.fstat(current)) != _identity(os.fstat(binding.descriptor)):
            raise UnsafeInstallTarget("bound directory no longer matches its ancestry")
    except UnsafeInstallTarget:
        raise
    except OSError as exc:
        raise UnsafeInstallTarget(f"cannot recheck directory ancestry: {exc}") from exc
    finally:
        os.close(current)


class _SourceTree:
    def __init__(self, source: Path) -> None:
        self.binding = _open_directory_binding(source)
        try:
            self.managed_roots = {
                relative: self._snapshot_directory(relative)
                for relative in MANAGED_DIRS
            }
        except BaseException:
            self.binding.close()
            raise

    def close(self) -> None:
        self.binding.close()

    def __enter__(self) -> _SourceTree:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _snapshot_directory(
        self,
        relative: str,
    ) -> tuple[tuple[str, tuple[int, int, int]], ...] | None:
        parts = _path_parts(relative)
        current = os.dup(self.binding.descriptor)
        components: list[tuple[str, tuple[int, int, int]]] = []
        try:
            for component in parts:
                try:
                    child, identity = _open_child_directory(current, component)
                except FileNotFoundError:
                    return None
                os.close(current)
                current = child
                components.append((component, identity))
            return tuple(components)
        except UnsafeInstallTarget:
            raise
        except OSError as exc:
            raise UnsafeInstallTarget(
                f"cannot bind managed source root {relative}: {exc}"
            ) from exc
        finally:
            os.close(current)

    def _open_managed_directory(
        self,
        relative: str,
        expected: tuple[tuple[str, tuple[int, int, int]], ...] | None,
    ) -> int | None:
        parts = _path_parts(relative)
        current = os.dup(self.binding.descriptor)
        try:
            for index, component in enumerate(parts):
                try:
                    expected_identity = (
                        expected[index][1]
                        if expected is not None and index < len(expected)
                        else None
                    )
                    child, _identity_value = _open_child_directory(
                        current, component, expected_identity
                    )
                except FileNotFoundError:
                    if expected is None:
                        os.close(current)
                        return None
                    raise UnsafeInstallTarget(
                        f"managed source root disappeared: {relative}"
                    )
                os.close(current)
                current = child
            if expected is None:
                raise UnsafeInstallTarget(
                    f"managed source root appeared after binding: {relative}"
                )
            return current
        except UnsafeInstallTarget:
            os.close(current)
            raise
        except OSError as exc:
            os.close(current)
            raise UnsafeInstallTarget(
                f"cannot open managed source root {relative}: {exc}"
            ) from exc

    def _walk_managed_directory(
        self,
        descriptor: int,
        prefix: str,
        *,
        depth: int,
        entries_seen: list[int],
        inventory: list[tuple[str, tuple[int, int, int, int, int, int]]],
    ) -> None:
        if depth > MAX_MANAGED_SOURCE_DEPTH:
            raise UnsafeInstallTarget("managed source directory depth limit exceeded")
        bound_identity = _identity(os.fstat(descriptor))
        try:
            names = sorted(os.listdir(descriptor), key=lambda name: name.encode("utf-8"))
        except OSError as exc:
            raise UnsafeInstallTarget(
                f"cannot enumerate managed source directory {prefix}: {exc}"
            ) from exc
        entries_seen[0] += len(names)
        if entries_seen[0] > MAX_MANAGED_SOURCE_ENTRIES:
            raise UnsafeInstallTarget("managed source entry limit exceeded")
        for name in names:
            relative = f"{prefix}/{name}"
            _path_parts(relative)
            try:
                metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            except OSError as exc:
                raise UnsafeInstallTarget(
                    f"managed source changed during enumeration: {relative}"
                ) from exc
            if stat.S_ISDIR(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode):
                if name == "__pycache__":
                    continue
                child, _identity_value = _open_child_directory(
                    descriptor, name, _identity(metadata)
                )
                try:
                    self._walk_managed_directory(
                        child,
                        relative,
                        depth=depth + 1,
                        entries_seen=entries_seen,
                        inventory=inventory,
                    )
                    current = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                    if _identity(current) != _identity(metadata):
                        raise UnsafeInstallTarget(
                            f"managed source directory changed after enumeration: {relative}"
                        )
                finally:
                    os.close(child)
                continue
            if any(
                relative.startswith(skip) and not relative.endswith(".gitkeep")
                for skip in SKIP_PREFIXES
            ):
                continue
            if relative.endswith(".pyc"):
                continue
            if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
                raise UnsafeInstallTarget(
                    f"managed source is not a regular file: {relative}"
                )
            inventory.append((relative, _file_identity(metadata)))
        if _identity(os.fstat(descriptor)) != bound_identity:
            raise UnsafeInstallTarget(
                f"managed source directory identity changed: {prefix}"
            )

    def inventory(
        self,
    ) -> tuple[tuple[str, tuple[int, int, int, int, int, int] | None], ...]:
        _check_directory_binding(self.binding)
        inventory: list[
            tuple[str, tuple[int, int, int, int, int, int] | None]
        ] = []
        entries_seen = [0]
        for relative in MANAGED_DIRS:
            expected = self.managed_roots.get(relative)
            descriptor = self._open_managed_directory(relative, expected)
            if descriptor is None:
                continue
            try:
                self._walk_managed_directory(
                    descriptor,
                    relative,
                    depth=1,
                    entries_seen=entries_seen,
                    inventory=inventory,
                )
            finally:
                os.close(descriptor)
            current = self._snapshot_directory(relative)
            if current != expected:
                raise UnsafeInstallTarget(
                    f"managed source root changed after enumeration: {relative}"
                )
        inventory.extend((relative, None) for relative in MANAGED_FILES)
        _check_directory_binding(self.binding)
        return tuple(sorted(inventory, key=lambda item: item[0].encode("utf-8")))

    def read(
        self,
        relative: str,
        limit: int,
        expected_identity: tuple[int, int, int, int, int, int] | None = None,
    ) -> tuple[bytes, int]:
        _check_directory_binding(self.binding)
        nofollow, _directory = _require_descriptor_primitives()
        parts = _path_parts(relative)
        parent = os.dup(self.binding.descriptor)
        try:
            for component in parts[:-1]:
                child, _identity_value = _open_child_directory(parent, component)
                os.close(parent)
                parent = child
            before = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode):
                raise UnsafeInstallTarget(
                    f"managed source is not a regular file: {relative}"
                )
            if expected_identity is not None and _file_identity(before) != expected_identity:
                raise UnsafeInstallTarget(
                    f"managed source changed after inventory: {relative}"
                )
            descriptor = os.open(
                parts[-1],
                os.O_RDONLY | nofollow,
                dir_fd=parent,
            )
            try:
                opened = os.fstat(descriptor)
                if _file_identity(opened) != _file_identity(before):
                    raise UnsafeInstallTarget(
                        f"managed source changed while opening: {relative}"
                    )
                content = _read_limit_plus_one(descriptor, limit)
                after = os.fstat(descriptor)
            finally:
                os.close(descriptor)
            if (
                _file_identity(after) != _file_identity(opened)
                or len(content) != opened.st_size
            ):
                raise UnsafeInstallTarget(
                    f"managed source changed while reading: {relative}"
                )
            _check_directory_binding(self.binding)
            return content, stat.S_IMODE(opened.st_mode)
        except UnsafeInstallTarget:
            raise
        except OSError as exc:
            raise UnsafeInstallTarget(f"cannot read managed source {relative}: {exc}") from exc
        finally:
            os.close(parent)


def _read_limit_plus_one(descriptor: int, limit: int) -> bytes:
    if limit < 0:
        raise UnsafeInstallTarget("managed source byte limit is invalid")
    chunks: list[bytes] = []
    remaining = limit + 1
    while remaining:
        chunk = os.read(descriptor, min(65_536, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    content = b"".join(chunks)
    if len(content) > limit:
        raise UnsafeInstallTarget("managed source exceeds its byte limit")
    return content


def _path_parts(relative: str) -> tuple[str, ...]:
    if not isinstance(relative, str) or not relative or "\\" in relative or "\x00" in relative:
        raise UnsafeInstallTarget(f"unsafe managed path: {relative!r}")
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise UnsafeInstallTarget(f"unsafe managed path: {relative!r}")
    normalized = path.as_posix()
    if normalized != relative:
        raise UnsafeInstallTarget(f"non-canonical managed path: {relative!r}")
    return path.parts


def iter_source_files(source: Path) -> list[tuple[str, Path]]:
    with _SourceTree(source) as tree:
        return [(relative, source / relative) for relative, _identity in tree.inventory()]


def managed_agents_text(source: Path) -> str:
    with _SourceTree(source) as tree:
        content, _mode = tree.read("AGENTS.md", MAX_SOURCE_FILE_BYTES)
    try:
        core = content.decode("utf-8").rstrip()
    except UnicodeError as exc:
        raise UnsafeInstallTarget("managed AGENTS.md is not UTF-8") from exc
    return f"{MANAGED_START}\n{core}\n{MANAGED_END}\n"


def _source_entry(
    relative: str,
    tree: _SourceTree,
    expected_identity: tuple[int, int, int, int, int, int] | None = None,
) -> InstallEntry:
    _path_parts(relative)
    if relative in TARGET_OWNED_ARCHITECTURE:
        raise UnsafeInstallTarget(f"target-owned architecture cannot be managed: {relative}")
    if relative in TARGET_OWNED_GOVERNANCE:
        raise UnsafeInstallTarget(f"target-owned governance cannot be managed: {relative}")
    content, mode = tree.read(relative, MAX_SOURCE_FILE_BYTES, expected_identity)
    return InstallEntry(relative, content, mode)


def build_payload(
    source: Path,
    *,
    profile_kind: str = "generic",
) -> tuple[InstallEntry, ...]:
    if profile_kind not in {"generic", "bitrix"}:
        raise UnsafeInstallTarget(f"unsupported explicit profile kind: {profile_kind}")
    with _SourceTree(source) as tree:
        entries = [
            _source_entry(relative, tree, expected_identity)
            for relative, expected_identity in tree.inventory()
        ]
        agents_content, _agents_mode = tree.read(
            "AGENTS.md",
            MAX_SOURCE_FILE_BYTES,
        )
        try:
            agents_core = agents_content.decode("utf-8").rstrip()
        except UnicodeError as exc:
            raise UnsafeInstallTarget("managed AGENTS.md is not UTF-8") from exc
        entries.append(
            InstallEntry(
                "AGENTS.md",
                f"{MANAGED_START}\n{agents_core}\n{MANAGED_END}\n".encode("utf-8"),
                0o644,
            )
        )
        if profile_kind == "bitrix":
            content, mode = tree.read(
                "docs/bitrix-local-AGENTS.md",
                MAX_SOURCE_FILE_BYTES,
            )
            entries.append(InstallEntry("local/AGENTS.md", content, mode))
    entries.sort(key=lambda entry: entry.path.encode("utf-8"))
    seen: set[str] = set()
    for entry in entries:
        if entry.path in seen:
            raise UnsafeInstallTarget(f"duplicate managed path: {entry.path}")
        seen.add(entry.path)
    for path in seen:
        parts = _path_parts(path)
        for length in range(1, len(parts)):
            if PurePosixPath(*parts[:length]).as_posix() in seen:
                raise UnsafeInstallTarget(f"managed file/directory collision: {path}")
    return tuple(entries)


def _dependency_advice(
    source: Path,
    *,
    include_dependencies: bool,
    include_optional: bool,
) -> list[dict[str, object]]:
    if not include_dependencies:
        return []
    with _SourceTree(source) as tree:
        content, _mode = tree.read(
            ".grok-stack/config/toolchain.json",
            MAX_TOOLCHAIN_BYTES,
        )
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise UnsafeInstallTarget(f"toolchain advisory source is invalid: {exc}") from exc
    tools = data.get("tools") if isinstance(data, dict) else None
    if not isinstance(tools, list):
        raise UnsafeInstallTarget("toolchain advisory source has no tools list")
    advice: list[dict[str, object]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            raise UnsafeInstallTarget("toolchain advisory entry is invalid")
        required = tool.get("required") is True
        if not required and not include_optional:
            continue
        installs = tool.get("install")
        command = installs.get("generic") if isinstance(installs, dict) else None
        tool_id = tool.get("id")
        if not isinstance(tool_id, str) or not tool_id:
            raise UnsafeInstallTarget("toolchain advisory id is invalid")
        advice.append(
            {
                "id": tool_id,
                "required": required,
                "profile": tool.get("profile") if isinstance(tool.get("profile"), str) else None,
                "command": command if isinstance(command, str) else None,
                "advisory_only": True,
            }
        )
    return sorted(advice, key=lambda item: str(item["id"]).encode("utf-8"))


def _target_state(target: Path) -> str:
    absolute = Path(os.path.abspath(target))
    if not absolute.name:
        return "unsafe"
    try:
        parent = _open_directory_binding(absolute.parent)
    except UnsafeInstallTarget:
        return "unsafe"
    try:
        try:
            metadata = os.stat(
                absolute.name,
                dir_fd=parent.descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return "absent"
        except OSError:
            return "unsafe"
        if stat.S_ISDIR(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode):
            return "directory"
        return "unsafe"
    finally:
        parent.close()


def _make_plan(
    source: Path,
    target: Path,
    *,
    include_dependencies: bool,
    include_optional: bool,
    payload: tuple[InstallEntry, ...] | None = None,
) -> dict[str, object]:
    selected_payload = payload if payload is not None else build_payload(source)
    return {
        "version": 1,
        "target_state": _target_state(target),
        "entries": [entry.manifest() for entry in selected_payload],
        "dependency_advice": _dependency_advice(
            source,
            include_dependencies=include_dependencies,
            include_optional=include_optional,
        ),
    }


def plan_install(source: Path, target: Path) -> dict[str, object]:
    return _make_plan(
        source,
        target,
        include_dependencies=True,
        include_optional=False,
    )


def _require_descriptor_primitives() -> tuple[int, int]:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if not nofollow or not directory:
        raise UnsafeInstallTarget("safe no-follow directory operations are unavailable")
    return nofollow, directory


def _renameat2() -> Any:
    library = ctypes.CDLL(None, use_errno=True)
    try:
        function = library.renameat2
    except AttributeError as exc:
        raise UnsafeInstallTarget("renameat2(RENAME_NOREPLACE) is unavailable") from exc
    function.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    function.restype = ctypes.c_int
    return function


def _rename_noreplace(parent_fd: int, stage_name: str, target_name: str) -> None:
    function = _renameat2()
    result = function(
        parent_fd,
        os.fsencode(stage_name),
        parent_fd,
        os.fsencode(target_name),
        RENAME_NOREPLACE,
    )
    if result == 0:
        return
    error = ctypes.get_errno()
    if error in {errno.EEXIST, errno.ENOTEMPTY}:
        raise UnsafeInstallTarget("installation target appeared before publication")
    if error in _UNSUPPORTED_RENAME_ERRNOS:
        raise UnsafeInstallTarget("renameat2(RENAME_NOREPLACE) is unsupported")
    raise OSError(error, os.strerror(error))


def _write_all(descriptor: int, content: bytes) -> None:
    remaining = memoryview(content)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("installer write made no progress")
        remaining = remaining[written:]


def _read_all(descriptor: int, expected_size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = expected_size
    while remaining:
        chunk = os.read(descriptor, min(65_536, remaining))
        if not chunk:
            raise UnsafeInstallTarget("staged file was truncated")
        chunks.append(chunk)
        remaining -= len(chunk)
    if os.read(descriptor, 1):
        raise UnsafeInstallTarget("staged file grew during verification")
    return b"".join(chunks)


def _stat_absent(parent_fd: int, name: str) -> None:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise UnsafeInstallTarget("materialization requires an absent target")


@dataclass
class _ParentBinding:
    directory: _DirectoryBinding
    target_name: str

    @property
    def descriptor(self) -> int:
        return self.directory.descriptor

    def close(self) -> None:
        self.directory.close()


def _open_parent(target: Path) -> _ParentBinding:
    absolute = Path(os.path.abspath(target))
    target_name = absolute.name
    if target_name in {"", ".", ".."}:
        raise UnsafeInstallTarget("installation target must name a child path")
    directory = _open_directory_binding(absolute.parent)
    try:
        _stat_absent(directory.descriptor, target_name)
        _check_directory_binding(directory)
    except BaseException:
        directory.close()
        raise
    return _ParentBinding(directory, target_name)


def _check_parent(parent: _ParentBinding) -> None:
    _check_directory_binding(parent.directory)


def _allocate_stage(parent_fd: int) -> tuple[str, int, tuple[int, int, int]]:
    nofollow, directory = _require_descriptor_primitives()
    for _attempt in range(32):
        name = f".adaptive-install-{uuid.uuid4().hex}"
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent_fd)
        except FileExistsError:
            continue
        stage_identity: tuple[int, int, int] | None = None
        descriptor = -1
        try:
            descriptor = os.open(
                name,
                os.O_RDONLY | directory | nofollow,
                dir_fd=parent_fd,
            )
            try:
                metadata = os.fstat(descriptor)
            except BaseException as failure:
                try:
                    metadata = os.fstat(descriptor)
                except BaseException as retry_failure:
                    raise UnsafeInstallTarget(
                        f"{MANUAL_CLEANUP_PREFIX}: stage {name}"
                    ) from retry_failure
                stage_identity = _identity(metadata)
                raise failure
            stage_identity = _identity(metadata)
            if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
                raise UnsafeInstallTarget("installer stage is not a real directory")
            return name, descriptor, stage_identity
        except BaseException as failure:
            if descriptor >= 0:
                os.close(descriptor)
            if stage_identity is None:
                if isinstance(failure, UnsafeInstallTarget) and str(failure).startswith(
                    MANUAL_CLEANUP_PREFIX
                ):
                    raise
                raise UnsafeInstallTarget(
                    f"{MANUAL_CLEANUP_PREFIX}: stage {name}"
                ) from failure
            try:
                current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                if _identity(current) != stage_identity or not stat.S_ISDIR(
                    current.st_mode
                ):
                    raise UnsafeInstallTarget(
                        f"{MANUAL_CLEANUP_PREFIX}: stage {name}"
                    )
                os.rmdir(name, dir_fd=parent_fd)
            except BaseException as cleanup_failure:
                if isinstance(
                    cleanup_failure, UnsafeInstallTarget
                ) and str(cleanup_failure).startswith(MANUAL_CLEANUP_PREFIX):
                    raise cleanup_failure from failure
                raise UnsafeInstallTarget(
                    f"{MANUAL_CLEANUP_PREFIX}: stage {name}; {cleanup_failure}"
                ) from failure
            raise
    raise UnsafeInstallTarget("cannot allocate an installer-owned sibling stage")


def _directory_paths(payload: tuple[InstallEntry, ...]) -> list[str]:
    paths: set[str] = set()
    for relative in EMPTY_DIRECTORIES:
        parts = _path_parts(relative)
        for length in range(1, len(parts) + 1):
            paths.add(PurePosixPath(*parts[:length]).as_posix())
    for entry in payload:
        parts = _path_parts(entry.path)
        for length in range(1, len(parts)):
            paths.add(PurePosixPath(*parts[:length]).as_posix())
    return sorted(paths, key=lambda path: (len(_path_parts(path)), path.encode("utf-8")))


def _create_stage(
    stage_fd: int,
    stage_identity: tuple[int, int, int],
    payload: tuple[InstallEntry, ...],
    directory_fds: dict[str, int],
    directory_identities: dict[str, tuple[int, int, int]],
    file_identities: dict[str, tuple[int, int, int]],
    created_directories: set[str],
    created_files: set[str],
) -> None:
    nofollow, directory = _require_descriptor_primitives()
    directory_fds[""] = stage_fd
    directory_identities[""] = stage_identity
    for relative in _directory_paths(payload):
        parts = _path_parts(relative)
        parent_name = PurePosixPath(*parts[:-1]).as_posix() if len(parts) > 1 else ""
        parent_fd = directory_fds[parent_name]
        os.mkdir(parts[-1], mode=0o755, dir_fd=parent_fd)
        created_directories.add(relative)
        descriptor = -1
        retained = False
        try:
            descriptor = os.open(
                parts[-1],
                os.O_RDONLY | directory | nofollow,
                dir_fd=parent_fd,
            )
            try:
                opened = os.fstat(descriptor)
            except BaseException as failure:
                try:
                    opened = os.fstat(descriptor)
                except BaseException as retry_failure:
                    raise UnsafeInstallTarget(
                        f"{MANUAL_CLEANUP_PREFIX}: directory {relative}"
                    ) from retry_failure
                if not stat.S_ISDIR(opened.st_mode):
                    raise UnsafeInstallTarget(
                        f"staged directory is unsafe: {relative}"
                    )
                directory_fds[relative] = descriptor
                retained = True
                directory_identities[relative] = _identity(opened)
                raise failure
            if not stat.S_ISDIR(opened.st_mode):
                raise UnsafeInstallTarget(f"staged directory is unsafe: {relative}")
            directory_fds[relative] = descriptor
            retained = True
            directory_identities[relative] = _identity(opened)
            os.fchmod(descriptor, 0o755)  # nosec B103
            after = os.fstat(descriptor)
            if (after.st_dev, after.st_ino) != (opened.st_dev, opened.st_ino):
                raise UnsafeInstallTarget(f"staged directory changed: {relative}")
            directory_identities[relative] = _identity(after)
        except BaseException as failure:
            if descriptor < 0:
                raise UnsafeInstallTarget(
                    f"{MANUAL_CLEANUP_PREFIX}: directory {relative}"
                ) from failure
            if not retained:
                os.close(descriptor)
            raise
    for entry in payload:
        parts = _path_parts(entry.path)
        parent_name = PurePosixPath(*parts[:-1]).as_posix() if len(parts) > 1 else ""
        parent_fd = directory_fds[parent_name]
        descriptor = os.open(
            parts[-1],
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
            entry.mode,
            dir_fd=parent_fd,
        )
        created_files.add(entry.path)
        try:
            try:
                metadata = os.fstat(descriptor)
            except BaseException:
                # The exclusive create already transferred ownership of this name.
                # Bind its identity before closing so cleanup never guesses.
                file_identities[entry.path] = _identity(os.fstat(descriptor))
                raise
            if not stat.S_ISREG(metadata.st_mode):
                raise UnsafeInstallTarget(f"staged file is unsafe: {entry.path}")
            file_identities[entry.path] = _identity(metadata)
            os.fchmod(descriptor, entry.mode)
            file_identities[entry.path] = _identity(os.fstat(descriptor))
            _write_all(descriptor, entry.content)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _verify_stage(
    directory_fds: dict[str, int],
    directory_identities: dict[str, tuple[int, int, int]],
    file_identities: dict[str, tuple[int, int, int]],
    payload: tuple[InstallEntry, ...],
) -> None:
    nofollow, _directory = _require_descriptor_primitives()
    expected_children: dict[str, set[str]] = {name: set() for name in directory_fds}
    for relative in directory_fds:
        if not relative:
            continue
        parts = _path_parts(relative)
        parent_name = PurePosixPath(*parts[:-1]).as_posix() if len(parts) > 1 else ""
        expected_children[parent_name].add(parts[-1])
    for entry in payload:
        parts = _path_parts(entry.path)
        parent_name = PurePosixPath(*parts[:-1]).as_posix() if len(parts) > 1 else ""
        expected_children[parent_name].add(parts[-1])
        parent_fd = directory_fds[parent_name]
        metadata = os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
        if (
            _identity(metadata) != file_identities[entry.path]
            or not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != entry.mode
            or metadata.st_size != entry.size
        ):
            raise UnsafeInstallTarget(f"staged manifest mismatch: {entry.path}")
        descriptor = os.open(parts[-1], os.O_RDONLY | nofollow, dir_fd=parent_fd)
        try:
            opened = os.fstat(descriptor)
            content = _read_all(descriptor, entry.size)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        if (
            _identity(opened) != file_identities[entry.path]
            or _identity(after) != _identity(opened)
            or hashlib.sha256(content).hexdigest() != entry.sha256
        ):
            raise UnsafeInstallTarget(f"staged content mismatch: {entry.path}")
    for relative, descriptor in directory_fds.items():
        if _identity(os.fstat(descriptor)) != directory_identities[relative]:
            raise UnsafeInstallTarget(f"staged directory changed: {relative or '.'}")
        if set(os.listdir(descriptor)) != expected_children[relative]:
            raise UnsafeInstallTarget(f"staged inventory mismatch: {relative or '.'}")


def _check_stage(
    parent_fd: int,
    stage_name: str,
    stage_fd: int,
    stage_identity: tuple[int, int, int],
) -> None:
    metadata = os.stat(stage_name, dir_fd=parent_fd, follow_symlinks=False)
    if (
        _identity(metadata) != stage_identity
        or _identity(os.fstat(stage_fd)) != stage_identity
        or not stat.S_ISDIR(metadata.st_mode)
    ):
        raise UnsafeInstallTarget("installer stage identity changed")


def _cleanup_stage(
    parent_fd: int,
    stage_name: str,
    stage_fd: int,
    stage_identity: tuple[int, int, int],
    directory_fds: dict[str, int],
    directory_identities: dict[str, tuple[int, int, int]],
    file_identities: dict[str, tuple[int, int, int]],
    created_directories: set[str],
    created_files: set[str],
) -> None:
    _check_stage(parent_fd, stage_name, stage_fd, stage_identity)
    for relative in sorted(
        created_files,
        key=lambda path: path.encode("utf-8"),
        reverse=True,
    ):
        parts = _path_parts(relative)
        parent_name = PurePosixPath(*parts[:-1]).as_posix() if len(parts) > 1 else ""
        parent = directory_fds[parent_name]
        expected = file_identities.get(relative)
        if expected is None:
            raise UnsafeInstallTarget(
                f"{MANUAL_CLEANUP_PREFIX}: file {relative}"
            )
        metadata = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
        if _identity(metadata) != expected or not stat.S_ISREG(metadata.st_mode):
            raise UnsafeInstallTarget(f"staged file changed before cleanup: {relative}")
        os.unlink(parts[-1], dir_fd=parent)
    nested = sorted(
        created_directories,
        key=lambda path: (len(_path_parts(path)), path.encode("utf-8")),
        reverse=True,
    )
    for relative in nested:
        parts = _path_parts(relative)
        parent_name = PurePosixPath(*parts[:-1]).as_posix() if len(parts) > 1 else ""
        parent = directory_fds[parent_name]
        descriptor = directory_fds.pop(relative, None)
        if descriptor is not None:
            os.close(descriptor)
        expected = directory_identities.get(relative)
        if expected is None:
            raise UnsafeInstallTarget(
                f"{MANUAL_CLEANUP_PREFIX}: directory {relative}"
            )
        metadata = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
        if (
            _identity(metadata) != expected
            or not stat.S_ISDIR(metadata.st_mode)
        ):
            raise UnsafeInstallTarget(f"staged directory changed before cleanup: {relative}")
        os.rmdir(parts[-1], dir_fd=parent)
    metadata = os.stat(stage_name, dir_fd=parent_fd, follow_symlinks=False)
    if _identity(metadata) != stage_identity or not stat.S_ISDIR(metadata.st_mode):
        raise UnsafeInstallTarget("installer stage changed before final cleanup")
    os.close(stage_fd)
    directory_fds.pop("", None)
    os.rmdir(stage_name, dir_fd=parent_fd)


def _close_directories(directory_fds: dict[str, int]) -> None:
    seen: set[int] = set()
    for descriptor in directory_fds.values():
        if descriptor not in seen:
            seen.add(descriptor)
            try:
                os.close(descriptor)
            except OSError:
                pass
    directory_fds.clear()


def _materialize_new(
    source: Path,
    target: Path,
    *,
    include_dependencies: bool,
    include_optional: bool,
) -> dict[str, object]:
    payload = build_payload(source)
    plan = _make_plan(
        source,
        target,
        include_dependencies=include_dependencies,
        include_optional=include_optional,
        payload=payload,
    )
    if plan["target_state"] != "absent":
        raise UnsafeInstallTarget("materialization requires an absent target")
    _renameat2()
    parent = _open_parent(target)
    parent_fd = parent.descriptor
    stage_name = ""
    stage_fd = -1
    stage_identity = (0, 0, 0)
    directory_fds: dict[str, int] = {}
    directory_identities: dict[str, tuple[int, int, int]] = {}
    file_identities: dict[str, tuple[int, int, int]] = {}
    created_directories: set[str] = set()
    created_files: set[str] = set()
    published = False
    try:
        stage_name, stage_fd, stage_identity = _allocate_stage(parent_fd)
        _create_stage(
            stage_fd,
            stage_identity,
            payload,
            directory_fds,
            directory_identities,
            file_identities,
            created_directories,
            created_files,
        )
        _verify_stage(directory_fds, directory_identities, file_identities, payload)
        for relative in sorted(
            directory_fds,
            key=lambda path: (len(_path_parts(path)) if path else 0, path.encode("utf-8")),
            reverse=True,
        ):
            os.fsync(directory_fds[relative])
        _check_parent(parent)
        os.fsync(parent_fd)
        _check_stage(parent_fd, stage_name, stage_fd, stage_identity)
        _stat_absent(parent_fd, parent.target_name)
        _rename_noreplace(parent_fd, stage_name, parent.target_name)
        published = True
        os.fsync(parent_fd)
        return plan
    except BaseException as failure:
        if stage_name and not published:
            try:
                _cleanup_stage(
                    parent_fd,
                    stage_name,
                    stage_fd,
                    stage_identity,
                    directory_fds,
                    directory_identities,
                    file_identities,
                    created_directories,
                    created_files,
                )
            except BaseException as cleanup_failure:
                raise UnsafeInstallTarget(
                    f"installer stage cleanup failed safely: {cleanup_failure}"
                ) from failure
        raise
    finally:
        _close_directories(directory_fds)
        parent.close()


def materialize_new(source: Path, target: Path) -> dict[str, object]:
    return _materialize_new(
        source,
        target,
        include_dependencies=True,
        include_optional=False,
    )


def install(
    source: Path,
    target: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
    with_ci: bool = False,
    install_deps: bool = True,
    all_deps: bool = False,
    runner: Any = None,
) -> dict[str, object]:
    del dry_run, runner
    if with_ci:
        raise SystemExit(
            "GitHub Actions is forbidden. Use local `make verify` / "
            "`python3 scripts/grok_verify.py --mode pr`."
        )
    if force:
        raise SystemExit(
            "--force is no longer supported; existing repositories are read-only. "
            "Use the plan in a reviewed source-change workflow."
        )
    plan = _make_plan(
        source,
        target,
        include_dependencies=install_deps,
        include_optional=all_deps,
    )
    print(LEGACY_PLAN_NOTICE)
    print(json.dumps(plan, sort_keys=True, indent=2))
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Plan a read-only Adaptive Grok installation or atomically materialize "
            "a new absent target."
        )
    )
    parser.add_argument("target")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--plan", action="store_true", help="Emit a read-only install plan.")
    modes.add_argument(
        "--materialize-new",
        action="store_true",
        help="Atomically publish a complete installation to an absent target.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Removed: existing repository mutation is not supported.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Alias for planning.")
    parser.add_argument(
        "--with-ci",
        action="store_true",
        help="Forbidden. Never GitHub Actions; use local verification.",
    )
    dependencies = parser.add_mutually_exclusive_group()
    dependencies.add_argument(
        "--no-deps",
        action="store_true",
        help="Omit dependency advisory commands from the plan.",
    )
    dependencies.add_argument(
        "--all-deps",
        action="store_true",
        help="Include optional dependency commands as advice only.",
    )
    args = parser.parse_args()
    if args.with_ci:
        parser.error("GitHub Actions is forbidden")
    if args.force:
        parser.error(
            "--force is no longer supported; existing repositories are read-only"
        )
    if args.materialize_new and args.dry_run:
        parser.error("--dry-run is planning and cannot be combined with --materialize-new")
    target = Path(args.target)
    if args.materialize_new:
        result = _materialize_new(
            ROOT,
            target,
            include_dependencies=not args.no_deps,
            include_optional=args.all_deps,
        )
    else:
        result = _make_plan(
            ROOT,
            target,
            include_dependencies=not args.no_deps,
            include_optional=args.all_deps,
        )
        if not args.plan:
            print(LEGACY_PLAN_NOTICE)
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
