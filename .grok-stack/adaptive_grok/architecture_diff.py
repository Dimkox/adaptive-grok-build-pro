from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import stat
# Git is resolved once and invoked only with an argument vector and shell=False.
import subprocess  # nosec B404
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .architecture import (
    RULE_COLLECTIONS,
    ArchitectureError,
    ArchitectureSnapshot,
    ContractRecord,
    architecture_digests,
    contract_inventory,
    load_architecture,
    parse_adoption_marker,
)

ADOPTION_BASE_SHA = "25bfbe59ea188d9687b20a9caad19e7db3d031f8"
MAX_GIT_OUTPUT_BYTES = 20_000_000
MAX_CHANGED_PATHS = 20_000
MAX_ANALYZED_FILE_BYTES = 10_000_000
MAX_DIFF_ARTIFACT_BYTES = 50_000_000
MAX_LINE_STAT_LINES = 100_000
_EXACT_SHA = re.compile(r"[0-9a-f]{40}")
_ADOPTION_PATH = "architecture/adoption.json"
_MODEL_PATHS = ("architecture/system.yaml", "architecture/rules.yaml")
_SCHEMA_PATHS = (
    "schemas/architecture-system.schema.json",
    "schemas/architecture-rules.schema.json",
)
_GIT_EXECUTABLE = shutil.which("git")
_GIT_TIMEOUT_SECONDS = 30.0
_LINE_STAT_TIMEOUT_SECONDS = 2.0


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("ascii")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _path_text(value: bytes) -> str:
    if b"\0" in value:
        raise ArchitectureError("Git emitted an invalid NUL-bearing path", code="git")
    return os.fsdecode(value)


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def _run_capped(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    stdout_limit: int,
    stderr_limit: int,
    timeout: float,
    stdin_data: bytes | None = None,
) -> tuple[int, bytes, bytes]:
    """Run a process while enforcing limits before output is fully produced."""
    input_stream = tempfile.TemporaryFile() if stdin_data is not None else None
    if input_stream is not None:
        input_stream.write(stdin_data)
        input_stream.seek(0)
    process = subprocess.Popen(  # nosec B603
        command, cwd=cwd, env=env,
        stdin=input_stream if input_stream is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
        start_new_session=True,
    )
    selector: selectors.BaseSelector | None = None
    streams: dict[Any, tuple[bytearray, int]] = {}
    try:
        if process.stdout is None or process.stderr is None:  # pragma: no cover - Popen contract
            raise ArchitectureError("bounded process pipes are unavailable", code="io")
        streams = {
            process.stdout: (bytearray(), stdout_limit),
            process.stderr: (bytearray(), stderr_limit),
        }
        try:
            selector = selectors.DefaultSelector()
            for stream in streams:
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ)
        except Exception as exc:
            raise ArchitectureError(
                f"bounded process setup failed: {exc}", code="io"
            ) from exc
        deadline = time.monotonic() + timeout
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _stop_process(process)
                raise ArchitectureError("bounded process timeout exceeded", code="timeout")
            events = selector.select(remaining)
            if not events and time.monotonic() >= deadline:
                _stop_process(process)
                raise ArchitectureError("bounded process timeout exceeded", code="timeout")
            for key, _mask in events:
                stream = key.fileobj
                buffer, limit = streams[stream]
                chunk = os.read(stream.fileno(), min(65_536, limit - len(buffer) + 1))
                if not chunk:
                    selector.unregister(stream)
                    stream.close()
                    continue
                buffer.extend(chunk)
                if len(buffer) > limit:
                    _stop_process(process)
                    raise ArchitectureError("bounded process output limit exceeded", code="limit")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _stop_process(process)
            raise ArchitectureError("bounded process timeout exceeded", code="timeout")
        try:
            returncode = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            _stop_process(process)
            raise ArchitectureError("bounded process timeout exceeded", code="timeout") from exc
        return returncode, bytes(streams[process.stdout][0]), bytes(streams[process.stderr][0])
    finally:
        if selector is not None:
            selector.close()
        for stream in (process.stdout, process.stderr):
            if stream is None:
                continue
            if not stream.closed:
                stream.close()
        if process.poll() is None:
            _stop_process(process)
        if input_stream is not None:
            input_stream.close()


def _git_environment() -> dict[str, str]:
    if _GIT_EXECUTABLE is None:
        raise ArchitectureError("Git executable is unavailable", code="git")
    return {
        "PATH": str(Path(_GIT_EXECUTABLE).parent),
        "LANG": "C",
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
    }


def _git_command(arguments: list[str]) -> list[str]:
    if _GIT_EXECUTABLE is None:
        raise ArchitectureError("Git executable is unavailable", code="git")
    return [
        _GIT_EXECUTABLE,
        "--no-replace-objects",
        "-c",
        "core.attributesFile=/dev/null",
        "-c",
        "core.excludesFile=/dev/null",
        "-c",
        "core.ignoreCase=false",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.pager=cat",
        "-c",
        "diff.algorithm=myers",
        "-c",
        "diff.external=",
        "-c",
        "diff.renames=false",
        *arguments,
    ]


def _git(
    root: Path,
    arguments: list[str],
    *,
    allow_failure: bool = False,
    limit: int = MAX_GIT_OUTPUT_BYTES,
    stdin_data: bytes | None = None,
) -> bytes | None:
    returncode, output, error = _run_capped(
        _git_command(arguments),
        cwd=root,
        env=_git_environment(),
        stdout_limit=limit,
        stderr_limit=65_536,
        timeout=_GIT_TIMEOUT_SECONDS,
        stdin_data=stdin_data,
    )
    if returncode:
        if allow_failure:
            return None
        message = error.decode("utf-8", "replace").strip()
        raise ArchitectureError(f"Git object operation failed: {message}", code="git")
    return output


def _required_output(value: bytes | None, *, operation: str) -> bytes:
    if value is None:
        raise ArchitectureError(f"required Git output missing: {operation}", code="git")
    return value


def _required_head(value: str | None) -> str:
    if value is None:
        raise ArchitectureError("commit diff is missing exact head_sha", code="git")
    return value


def _exact_commit(root: Path, value: str, *, label: str) -> str:
    if not isinstance(value, str) or _EXACT_SHA.fullmatch(value) is None:
        raise ArchitectureError(f"{label} must be an exact 40-character commit SHA", code="git")
    kind = _git(root, ["cat-file", "-t", value], allow_failure=True, limit=64)
    if kind != b"commit\n":
        raise ArchitectureError(f"{label} is not an available commit object", code="git")
    return value


def _head_commit(root: Path) -> str:
    value = _required_output(
        _git(root, ["rev-parse", "--verify", "HEAD^{commit}"], limit=128),
        operation="resolve HEAD",
    )
    return _exact_commit(root, value.decode("ascii").strip(), label="head_sha")


def _git_blob(root: Path, sha: str, path: str, *, required: bool = False) -> bytes | None:
    value = _git_blobs(root, sha, (path,))[path]
    if value is None and required:
        raise ArchitectureError(f"required Git object path is missing: {path}", code="missing")
    return value


@dataclass(frozen=True)
class ArchitectureBaseSelection:
    route_base_sha: str
    comparison_base_sha: str
    base_kind: str
    bootstrap_baseline: bool


def select_architecture_comparison_base(
    root: Path,
    route: dict[str, Any] | None,
) -> ArchitectureBaseSelection:
    candidate = (route or {}).get("base_commit")
    route_base = _exact_commit(
        root,
        candidate if isinstance(candidate, str) else _head_commit(root),
        label="architecture_route_base_sha",
    )
    marker_present = _git_blob(root, route_base, _ADOPTION_PATH) is not None
    model_present = tuple(
        _git_blob(root, route_base, path) is not None for path in _MODEL_PATHS
    )
    if model_present not in {(False, False), (True, True)}:
        raise ArchitectureError(
            "route-base architecture model is partially missing",
            code="missing",
        )
    if marker_present and model_present == (False, False):
        raise ArchitectureError(
            "route-base adopted architecture model is missing",
            code="missing",
        )
    if model_present == (True, True):
        marker_value = _git_blob(root, route_base, _ADOPTION_PATH, required=True)
        parse_adoption_marker(
            _required_output(marker_value, operation="read route-base adoption marker")
        )
    if model_present == (True, True):
        comparison_base = route_base
        base_kind = "route_model"
        bootstrap_baseline = False
    else:
        bootstrap_baseline = True
        try:
            comparison_base = _exact_commit(
                root,
                ADOPTION_BASE_SHA,
                label="architecture_base_sha",
            )
            base_kind = "frozen_adoption"
        except ArchitectureError:
            comparison_base = route_base
            base_kind = "route_pre_adoption"
    return ArchitectureBaseSelection(
        route_base_sha=route_base,
        comparison_base_sha=comparison_base,
        base_kind=base_kind,
        bootstrap_baseline=bootstrap_baseline,
    )


def _worktree_blob(root: Path, path: str) -> bytes | None:
    parts = path.split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ArchitectureError(f"invalid worktree path: {path}", code="path")
    no_follow = getattr(os, "O_NOFOLLOW", None)
    directory_flag = getattr(os, "O_DIRECTORY", None)
    nonblock = getattr(os, "O_NONBLOCK", None)
    if (
        not isinstance(no_follow, int)
        or no_follow == 0
        or not isinstance(directory_flag, int)
        or directory_flag == 0
        or not isinstance(nonblock, int)
        or os.open not in getattr(os, "supports_dir_fd", set())
    ):
        raise ArchitectureError("worktree analysis requires O_NOFOLLOW", code="io")
    directory = -1
    descriptor = -1
    try:
        directory = os.open(root, os.O_RDONLY | directory_flag | no_follow)
        for component in parts[:-1]:
            child = os.open(
                component,
                os.O_RDONLY | directory_flag | no_follow,
                dir_fd=directory,
            )
            os.close(directory)
            directory = child
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | nonblock | no_follow,
            dir_fd=directory,
        )
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ArchitectureError(f"worktree path is not a regular file: {path}", code="io")
        if before.st_size > MAX_ANALYZED_FILE_BYTES:
            raise ArchitectureError(f"worktree file exceeds analysis limit: {path}", code="limit")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 64 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        value = b"".join(chunks)
        after = os.fstat(descriptor)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ArchitectureError(f"worktree file read failed: {path}: {exc}", code="io") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if directory >= 0:
            os.close(directory)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise ArchitectureError(f"worktree file changed during analysis: {path}", code="io")
    if len(value) != before.st_size:
        raise ArchitectureError(f"worktree file was truncated during analysis: {path}", code="io")
    return value


@dataclass(frozen=True)
class _ArchitectureState:
    snapshot: ArchitectureSnapshot
    contracts: tuple[ContractRecord, ...]
    adoption_state: str
    adoption_digest: str


def _materialized_state(
    root: Path,
    sha: str,
    *,
    adoption_base: bool = False,
    bootstrap_baseline: bool = False,
) -> _ArchitectureState | None:
    model_values = tuple(_git_blob(root, sha, path) for path in _MODEL_PATHS)
    marker_value = _git_blob(root, sha, _ADOPTION_PATH)
    if model_values == (None, None):
        if marker_value is not None:
            raise ArchitectureError(
                "architecture adoption marker exists without the model", code="missing"
            )
        if (adoption_base and sha == ADOPTION_BASE_SHA) or bootstrap_baseline:
            return None
        raise ArchitectureError("architecture model is missing outside the adoption base", code="missing")
    if any(value is None for value in model_values):
        raise ArchitectureError("architecture model is partially missing", code="missing")
    if marker_value is None:
        raise ArchitectureError("architecture adoption marker is missing", code="missing")
    adoption = parse_adoption_marker(marker_value)
    schema_values = tuple(_git_blob(root, sha, path, required=True) for path in _SCHEMA_PATHS)
    with tempfile.TemporaryDirectory(prefix="adaptive-architecture-object-") as directory:
        materialized = Path(directory)
        for path, value in zip((*_MODEL_PATHS, *_SCHEMA_PATHS), (*model_values, *schema_values)):
            target = materialized / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(_required_output(value, operation=f"materialize {path}"))
        snapshot = load_architecture(materialized)
        for contract in snapshot.system["contracts"]:
            value = _git_blob(root, sha, contract["path"], required=True)
            target = materialized / contract["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(_required_output(value, operation=f"materialize {contract['path']}"))
        records = contract_inventory(materialized, snapshot)
    if adoption["architecture_id"] != snapshot.system["architecture_id"]:
        raise ArchitectureError(
            "architecture adoption marker id does not match the model", code="schema"
        )
    return _ArchitectureState(
        snapshot=snapshot,
        contracts=records,
        adoption_state="adopted",
        adoption_digest=adoption["digest"],
    )


def _worktree_state(root: Path) -> _ArchitectureState:
    snapshot = load_architecture(root)
    marker_value = _worktree_blob(root, _ADOPTION_PATH)
    if marker_value is None:
        raise ArchitectureError("architecture adoption marker is missing", code="missing")
    adoption = parse_adoption_marker(marker_value)
    if adoption["architecture_id"] != snapshot.system["architecture_id"]:
        raise ArchitectureError(
            "architecture adoption marker id does not match the model", code="schema"
        )
    return _ArchitectureState(
        snapshot=snapshot,
        contracts=contract_inventory(root, snapshot),
        adoption_state="adopted",
        adoption_digest=adoption["digest"],
    )


@dataclass(frozen=True)
class ArchitectureChange:
    kind: str
    id: str
    change: str
    before_digest: str | None
    after_digest: str | None


@dataclass(frozen=True)
class ChangedArtifact:
    path: str
    status: str
    added_lines: int | None
    deleted_lines: int | None
    base_size: int
    head_size: int
    base_digest: str | None
    head_digest: str | None


@dataclass(frozen=True)
class ArchitectureDiff:
    base_sha: str
    head_sha: str | None
    head_kind: str
    baseline_introduced: bool
    changed_paths: tuple[str, ...]
    changes: tuple[ArchitectureChange, ...]
    artifacts: tuple[ChangedArtifact, ...]
    base_architecture_digest: str | None
    head_architecture_digest: str
    base_adoption_state: str
    head_adoption_state: str
    base_adoption_digest: str | None
    head_adoption_digest: str
    repository_inventory_digest: str
    digest: str
    _base_state: _ArchitectureState | None = field(repr=False, compare=False)
    _head_state: _ArchitectureState = field(repr=False, compare=False)


def _object_digest(value: Any) -> str:
    if isinstance(value, ContractRecord):
        projected = {key: getattr(value, key) for key in ("id", "kind", "path", "version", "role", "compatibility")}
        projected["document_digest"] = value.digest
        return _digest(projected)
    return _digest(value)


def _change_records(
    base: _ArchitectureState | None, head: _ArchitectureState
) -> tuple[ArchitectureChange, ...]:
    def indexed(values: list[dict[str, Any]]) -> dict[str, Any]:
        return {value["id"]: value for value in values}

    def indexed_rules(rules: dict[str, Any]) -> dict[str, Any]:
        return {item["id"]: item for collection in RULE_COLLECTIONS for item in rules.get(collection, [])}

    base_system = base.snapshot.system if base else {}
    head_system = head.snapshot.system
    collections: list[tuple[str, dict[str, Any], dict[str, Any]]] = [
        (
            "system",
            {"ARCHITECTURE": {key: base_system[key] for key in ("schema_version", "architecture_id")}}
            if base else {},
            {"ARCHITECTURE": {key: head_system[key] for key in ("schema_version", "architecture_id")}},
        ),
        (
            "runtime",
            {item["id"]: item["runtime"] for item in base_system.get("nodes", [])},
            {item["id"]: item["runtime"] for item in head_system["nodes"]},
        ),
        (
            "contract",
            {item.id: item for item in (base.contracts if base else ())},
            {item.id: item for item in head.contracts},
        ),
    ]
    for kind, key in (
        ("trust_domain", "trust_domains"), ("signal", "signals"), ("node", "nodes"),
        ("edge", "edges"), ("classification", "data_classifications"),
        ("secret", "secret_classes"),
    ):
        collections.append((kind, indexed(base_system.get(key, [])), indexed(head_system[key])))
    base_rules = base.snapshot.rules if base else {}
    head_rules = head.snapshot.rules
    collections.extend((
        (
            "rules",
            {"ARCHITECTURE": {key: base_rules[key] for key in ("schema_version", "architecture_id")}}
            if base else {},
            {"ARCHITECTURE": {key: head_rules[key] for key in ("schema_version", "architecture_id")}},
        ),
        ("rule", indexed_rules(base_rules), indexed_rules(head_rules)),
    ))
    changes: list[ArchitectureChange] = []
    for kind, before, after in collections:
        for identity in set(before) | set(after):
            old = before.get(identity)
            new = after.get(identity)
            if old is None:
                change = "added"
            elif new is None:
                change = "removed"
            elif _object_digest(old) != _object_digest(new):
                change = "changed"
            else:
                continue
            changes.append(
                ArchitectureChange(
                    kind=kind,
                    id=identity,
                    change=change,
                    before_digest=None if old is None else _object_digest(old),
                    after_digest=None if new is None else _object_digest(new),
                )
            )
    return tuple(sorted(changes, key=lambda item: (item.kind, item.id, item.change)))


def _changed_paths(root: Path, base: str, head: str | None, *, worktree: bool) -> tuple[str, ...]:
    arguments = [
        "diff", "--name-only", "-z", "--no-renames", "--no-ext-diff", "--no-textconv", base
    ]
    if not worktree:
        arguments.append(_required_head(head))
    raw = _required_output(_git(root, arguments), operation="list changed paths")
    values = [_path_text(item) for item in raw.split(b"\0") if item]
    if worktree:
        untracked = _required_output(
            _git(root, ["ls-files", "--others", "--exclude-standard", "-z"]),
            operation="list untracked paths",
        )
        values.extend(_path_text(item) for item in untracked.split(b"\0") if item)
    unique = tuple(sorted(set(values)))
    if len(unique) > MAX_CHANGED_PATHS:
        raise ArchitectureError("changed path limit exceeded", code="limit")
    return unique


def _line_stats(old: bytes | None, new: bytes | None) -> tuple[int | None, int | None]:
    before = old or b""
    after = new or b""
    if len(before) > MAX_ANALYZED_FILE_BYTES or len(after) > MAX_ANALYZED_FILE_BYTES:
        raise ArchitectureError("line-stat byte limit exceeded", code="limit")
    if b"\0" in before or b"\0" in after:
        return None, None
    try:
        before_lines = before.decode("utf-8").splitlines()
        after_lines = after.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return None, None
    if len(before_lines) > MAX_LINE_STAT_LINES or len(after_lines) > MAX_LINE_STAT_LINES:
        raise ArchitectureError("line-stat line limit exceeded", code="limit")
    with tempfile.TemporaryDirectory(prefix="adaptive-line-stat-") as directory:
        root = Path(directory)
        (root / "before").write_bytes(before)
        (root / "after").write_bytes(after)
        returncode, output, error = _run_capped(
            _git_command(
                [
                    "diff",
                    "--no-index",
                    "--numstat",
                    "--no-renames",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--",
                    "before",
                    "after",
                ]
            ),
            cwd=root,
            env=_git_environment(),
            stdout_limit=4_096,
            stderr_limit=65_536,
            timeout=_LINE_STAT_TIMEOUT_SECONDS,
        )
    if returncode not in {0, 1}:
        message = error.decode("utf-8", "replace").strip()
        raise ArchitectureError(f"exact line-stat operation failed: {message}", code="git")
    if returncode == 0:
        if output:
            raise ArchitectureError("unchanged line-stat operation emitted output", code="git")
        return 0, 0
    records = output.rstrip(b"\n").split(b"\n")
    if len(records) != 1:
        raise ArchitectureError("unexpected exact line-stat output", code="git")
    fields = records[0].split(b"\t", 2)
    if len(fields) != 3 or fields[0] == b"-" or fields[1] == b"-":
        raise ArchitectureError("exact text line-stat output is unavailable", code="git")
    try:
        return int(fields[0]), int(fields[1])
    except ValueError as exc:
        raise ArchitectureError("invalid exact line-stat counts", code="git") from exc


def read_diff_file(root: Path, diff: ArchitectureDiff, path: str, side: str = "head") -> bytes | None:
    repository = Path(root).resolve(strict=True)
    if side not in {"base", "head"}:
        raise ArchitectureError("diff file side must be base or head", code="invalid")
    if side == "base":
        return _git_blob(repository, diff.base_sha, path)
    if diff.head_kind == "worktree":
        return _worktree_blob(repository, path)
    return _git_blob(repository, _required_head(diff.head_sha), path)


def _git_blobs(root: Path, sha: str, paths: tuple[str, ...]) -> dict[str, bytes | None]:
    requested = tuple(sorted(set(paths)))
    if len(requested) > MAX_CHANGED_PATHS:
        raise ArchitectureError("diff file batch path limit exceeded", code="limit")
    if not requested:
        return {}
    encoded = tuple(os.fsencode(path) for path in requested)
    if any(b"\0" in path for path in encoded) or sum(map(len, encoded)) > 65_536:
        raise ArchitectureError("diff file batch path input limit exceeded", code="limit")
    raw = _required_output(
        _git(
            root,
            ["--literal-pathspecs", "ls-tree", "-lr", "-z", "--full-tree", sha, "--", *requested],
            limit=min(MAX_GIT_OUTPUT_BYTES, 4_096 + sum(map(len, encoded))),
        ),
        operation="read Git batch tree metadata",
    )
    entries: dict[str, tuple[bytes, int]] = {}
    for record in (item for item in raw.split(b"\0") if item):
        if b"\t" not in record:
            raise ArchitectureError("invalid Git batch tree metadata", code="git")
        metadata, returned_path = record.split(b"\t", 1)
        fields = metadata.split()
        path = _path_text(returned_path)
        if path not in requested or len(fields) != 4 or path in entries:
            raise ArchitectureError(f"unexpected Git tree entry for {path}", code="git")
        mode, kind, object_id, size_raw = fields
        if kind != b"blob" or mode not in {b"100644", b"100755"}:
            raise ArchitectureError(f"Git object path is not a regular file: {path}", code="io")
        if _EXACT_SHA.fullmatch(object_id.decode("ascii", "replace")) is None:
            raise ArchitectureError(f"invalid Git blob identity for {path}", code="git")
        try:
            size = int(size_raw)
        except ValueError as exc:
            raise ArchitectureError(f"invalid Git blob size for {path}", code="git") from exc
        if size > MAX_ANALYZED_FILE_BYTES:
            raise ArchitectureError(f"Git blob exceeds analysis limit: {path}", code="limit")
        entries[path] = object_id, size
    present = tuple(path for path in requested if path in entries)
    total = sum(entries[path][1] for path in present)
    if total > MAX_GIT_OUTPUT_BYTES:
        raise ArchitectureError("Git blob batch exceeds analysis limit", code="limit")
    if not present:
        return {path: None for path in requested}
    specs = b"".join(sha.encode("ascii") + b":" + os.fsencode(path) + b"\0" for path in present)
    output = _required_output(
        _git(
            root,
            ["cat-file", "-Z", "--batch=%(objectname) %(objecttype) %(objectsize)"],
            limit=total + 128 * len(present),
            stdin_data=specs,
        ),
        operation="read Git blob batch",
    )
    values: dict[str, bytes | None] = {path: None for path in requested}
    cursor = 0
    for path in present:
        end = output.find(b"\0", cursor)
        if end < 0:
            raise ArchitectureError(f"truncated Git blob batch header for {path}", code="git")
        fields = output[cursor:end].split()
        object_id, size = entries[path]
        if fields != [object_id, b"blob", str(size).encode("ascii")]:
            raise ArchitectureError(f"unexpected Git blob batch header for {path}", code="git")
        start = end + 1
        finish = start + size
        if finish >= len(output) or output[finish:finish + 1] != b"\0":
            raise ArchitectureError(f"truncated Git blob batch content for {path}", code="git")
        values[path] = output[start:finish]
        cursor = finish + 1
    if cursor != len(output):
        raise ArchitectureError("unexpected trailing Git blob batch output", code="git")
    return values


def read_diff_files(
    root: Path, diff: ArchitectureDiff, paths: tuple[str, ...], side: str = "head"
) -> dict[str, bytes | None]:
    """Read a bounded exact set of paths, batching immutable Git blob content."""
    repository = Path(root).resolve(strict=True)
    if side not in {"base", "head"}:
        raise ArchitectureError("diff file side must be base or head", code="invalid")
    requested = tuple(sorted(set(paths)))
    if side == "head" and diff.head_kind == "worktree":
        return {path: _worktree_blob(repository, path) for path in requested}
    sha = diff.base_sha if side == "base" else _required_head(diff.head_sha)
    return _git_blobs(repository, sha, requested)


def git_tree_paths(root: Path, sha: str, prefixes: tuple[str, ...]) -> tuple[str, ...]:
    raw = _required_output(
        _git(root, ["ls-tree", "-r", "--name-only", "-z", "--full-tree", sha]),
        operation="list Git tree paths",
    )
    paths = tuple(
        sorted(
            path
            for path in (_path_text(item) for item in raw.split(b"\0") if item)
            if any(not prefix or path == prefix or path.startswith(prefix + "/") for prefix in prefixes)
        )
    )
    if len(paths) > MAX_CHANGED_PATHS:
        raise ArchitectureError("Git tree path limit exceeded", code="limit")
    return paths


def _tree_inventory_digest(
    root: Path,
    sha: str | None,
    *,
    worktree: bool,
    artifacts: tuple[ChangedArtifact, ...] = (),
) -> str:
    if worktree:
        raw = _required_output(
            _git(root, ["ls-files", "-s", "-z"]), operation="read worktree index"
        )
        untracked = _required_output(
            _git(root, ["ls-files", "--others", "--exclude-standard", "-z"]),
            operation="read worktree untracked inventory",
        )
        return _digest(
            {
                "tracked_index": os.fsdecode(raw),
                "untracked": os.fsdecode(untracked),
                "worktree_changes": [
                    {
                        "path": item.path,
                        "status": item.status,
                        "head_digest": item.head_digest,
                        "head_size": item.head_size,
                    }
                    for item in artifacts
                ],
            }
        )
    exact_sha = _required_head(sha)
    raw = _required_output(
        _git(root, ["ls-tree", "-r", "-z", "--full-tree", exact_sha]),
        operation="read Git tree inventory",
    )
    return _digest(os.fsdecode(raw))


def diff_architecture(
    root: Path | str,
    *,
    base_sha: str,
    head_sha: str | None = None,
    worktree: bool = False,
    _trusted_base_selection: ArchitectureBaseSelection | None = None,
) -> ArchitectureDiff:
    repository = Path(root).resolve(strict=True)
    base = _exact_commit(repository, base_sha, label="base_sha")
    bootstrap_baseline = False
    if _trusted_base_selection is not None:
        verified_selection = select_architecture_comparison_base(
            repository,
            {"base_commit": _trusted_base_selection.route_base_sha},
        )
        if verified_selection != _trusted_base_selection:
            raise ArchitectureError("architecture base selection is stale", code="git")
        if base != _trusted_base_selection.comparison_base_sha:
            raise ArchitectureError(
                "architecture base selection does not match base_sha",
                code="git",
            )
        bootstrap_baseline = _trusted_base_selection.bootstrap_baseline
    if worktree:
        if head_sha is not None:
            raise ArchitectureError("worktree diff cannot also name head_sha", code="git")
        head = None
        head_state = _worktree_state(repository)
        head_kind = "worktree"
    else:
        head = _head_commit(repository) if head_sha is None else _exact_commit(
            repository, head_sha, label="head_sha"
        )
        head_state = _materialized_state(repository, head)
        if head_state is None:
            raise ArchitectureError("head architecture model is missing", code="missing")
        head_kind = "commit"
    base_state = _materialized_state(
        repository,
        base,
        adoption_base=True,
        bootstrap_baseline=bootstrap_baseline,
    )
    paths = _changed_paths(repository, base, head, worktree=worktree)
    artifacts: list[ChangedArtifact] = []
    artifact_bytes = 0
    for path in paths:
        old = _git_blob(repository, base, path)
        new = (
            _worktree_blob(repository, path)
            if worktree
            else _git_blob(repository, _required_head(head), path)
        )
        artifact_bytes += len(old or b"") + len(new or b"")
        if artifact_bytes > MAX_DIFF_ARTIFACT_BYTES:
            raise ArchitectureError("aggregate changed artifact byte limit exceeded", code="limit")
        status = "added" if old is None and new is not None else (
            "deleted" if old is not None and new is None else "modified"
        )
        added, deleted = _line_stats(old, new)
        artifacts.append(
            ChangedArtifact(
                path=path,
                status=status,
                added_lines=added,
                deleted_lines=deleted,
                base_size=len(old or b""),
                head_size=len(new or b""),
                base_digest=None if old is None else hashlib.sha256(old).hexdigest(),
                head_digest=None if new is None else hashlib.sha256(new).hexdigest(),
            )
        )
    changes = _change_records(base_state, head_state)
    base_digest = None if base_state is None else architecture_digests(base_state.snapshot)[
        "architecture_digest"
    ]
    head_digest = architecture_digests(head_state.snapshot)["architecture_digest"]
    payload = {
        "contract": "adaptive-grok.architecture-diff",
        "contract_version": 1,
        "base_sha": base,
        "head_sha": head,
        "head_kind": head_kind,
        "baseline_introduced": base_state is None,
        "base_architecture_digest": base_digest,
        "head_architecture_digest": head_digest,
        "base_adoption_state": "bootstrap_absent" if base_state is None else base_state.adoption_state,
        "head_adoption_state": head_state.adoption_state,
        "base_adoption_digest": None if base_state is None else base_state.adoption_digest,
        "head_adoption_digest": head_state.adoption_digest,
        "changed_paths": paths,
        "changes": [
            {
                "kind": item.kind,
                "id": item.id,
                "change": item.change,
                "before_digest": item.before_digest,
                "after_digest": item.after_digest,
            }
            for item in changes
        ],
    }
    return ArchitectureDiff(
        base_sha=base,
        head_sha=head,
        head_kind=head_kind,
        baseline_introduced=base_state is None,
        changed_paths=paths,
        changes=changes,
        artifacts=tuple(artifacts),
        base_architecture_digest=base_digest,
        head_architecture_digest=head_digest,
        base_adoption_state="bootstrap_absent" if base_state is None else base_state.adoption_state,
        head_adoption_state=head_state.adoption_state,
        base_adoption_digest=None if base_state is None else base_state.adoption_digest,
        head_adoption_digest=head_state.adoption_digest,
        repository_inventory_digest=_tree_inventory_digest(
            repository, head, worktree=worktree, artifacts=tuple(artifacts)
        ),
        digest=_digest(payload),
        _base_state=base_state,
        _head_state=head_state,
    )
