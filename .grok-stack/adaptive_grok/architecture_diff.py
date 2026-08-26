from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
# Git is resolved once and invoked only with an argument vector and shell=False.
import subprocess  # nosec B404
import tempfile
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
)

ADOPTION_BASE_SHA = "25bfbe59ea188d9687b20a9caad19e7db3d031f8"
MAX_GIT_OUTPUT_BYTES = 20_000_000
MAX_CHANGED_PATHS = 20_000
MAX_ANALYZED_FILE_BYTES = 10_000_000
MAX_DIFF_ARTIFACT_BYTES = 50_000_000
_EXACT_SHA = re.compile(r"[0-9a-f]{40}")
_MODEL_PATHS = ("architecture/system.yaml", "architecture/rules.yaml")
_SCHEMA_PATHS = (
    "schemas/architecture-system.schema.json",
    "schemas/architecture-rules.schema.json",
)
_GIT_EXECUTABLE = shutil.which("git")


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


def _git(
    root: Path,
    arguments: list[str],
    *,
    allow_failure: bool = False,
    limit: int = MAX_GIT_OUTPUT_BYTES,
) -> bytes | None:
    if _GIT_EXECUTABLE is None:
        raise ArchitectureError("Git executable is unavailable", code="git")
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        # The executable is fixed and arguments never pass through a shell.
        process = subprocess.run(  # nosec B603
            [_GIT_EXECUTABLE, *arguments],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            check=False,
        )
        stdout_size = stdout.tell()
        stderr_size = stderr.tell()
        if stdout_size > limit or stderr_size > 65_536:
            raise ArchitectureError("bounded Git output limit exceeded", code="limit")
        stdout.seek(0)
        stderr.seek(0)
        output = stdout.read(limit + 1)
        error = stderr.read(65_537)
    if process.returncode:
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
    entry = _git(
        root,
        ["--literal-pathspecs", "ls-tree", "-z", sha, "--", path],
        allow_failure=True,
        limit=4_096 + len(os.fsencode(path)),
    )
    if not entry:
        if required:
            raise ArchitectureError(f"required Git object path is missing: {path}", code="missing")
        return None
    records = [record for record in entry.split(b"\0") if record]
    if len(records) != 1 or b"\t" not in records[0]:
        raise ArchitectureError(f"ambiguous Git tree entry for {path}", code="git")
    metadata, returned_path = records[0].split(b"\t", 1)
    fields = metadata.split()
    if returned_path != os.fsencode(path) or len(fields) != 3:
        raise ArchitectureError(f"unexpected Git tree entry for {path}", code="git")
    mode, kind, _object_id = fields
    if kind != b"blob" or mode not in {b"100644", b"100755"}:
        raise ArchitectureError(f"Git object path is not a regular file: {path}", code="io")
    spec = f"{sha}:{path}"
    size_raw = _git(root, ["cat-file", "-s", spec], allow_failure=True, limit=64)
    if size_raw is None:
        if required:
            raise ArchitectureError(f"required Git object path is missing: {path}", code="missing")
        return None
    try:
        size = int(size_raw)
    except ValueError as exc:
        raise ArchitectureError(f"invalid Git blob size for {path}", code="git") from exc
    if size > MAX_ANALYZED_FILE_BYTES:
        raise ArchitectureError(f"Git blob exceeds analysis limit: {path}", code="limit")
    value = _required_output(
        _git(root, ["show", spec], limit=MAX_ANALYZED_FILE_BYTES),
        operation=f"read blob {path}",
    )
    if len(value) != size:
        raise ArchitectureError(f"Git blob changed during object read: {path}", code="git")
    return value


def _worktree_blob(root: Path, path: str) -> bytes | None:
    parts = path.split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ArchitectureError(f"invalid worktree path: {path}", code="path")
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_follow is None:
        raise ArchitectureError("worktree analysis requires O_NOFOLLOW", code="io")
    directory = -1
    descriptor = -1
    try:
        directory = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | no_follow)
        for component in parts[:-1]:
            child = os.open(
                component,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | no_follow,
                dir_fd=directory,
            )
            os.close(directory)
            directory = child
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | no_follow,
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


def _materialized_state(root: Path, sha: str, *, adoption_base: bool = False) -> _ArchitectureState | None:
    model_values = tuple(_git_blob(root, sha, path) for path in _MODEL_PATHS)
    if model_values == (None, None):
        if adoption_base and sha == ADOPTION_BASE_SHA:
            return None
        raise ArchitectureError("architecture model is missing outside the adoption base", code="missing")
    if any(value is None for value in model_values):
        raise ArchitectureError("architecture model is partially missing", code="missing")
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
    return _ArchitectureState(snapshot=snapshot, contracts=records)


def _worktree_state(root: Path) -> _ArchitectureState:
    snapshot = load_architecture(root)
    return _ArchitectureState(snapshot=snapshot, contracts=contract_inventory(root, snapshot))


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
    repository_inventory_digest: str
    digest: str
    _base_state: _ArchitectureState | None = field(repr=False, compare=False)
    _head_state: _ArchitectureState = field(repr=False, compare=False)


def _object_digest(value: Any) -> str:
    if isinstance(value, ContractRecord):
        return value.digest
    return _digest(value)


def _change_records(
    base: _ArchitectureState | None, head: _ArchitectureState
) -> tuple[ArchitectureChange, ...]:
    def indexed(values: list[dict[str, Any]]) -> dict[str, Any]:
        return {value["id"]: value for value in values}

    base_system = base.snapshot.system if base else {}
    head_system = head.snapshot.system
    collections: list[tuple[str, dict[str, Any], dict[str, Any]]] = [
        ("node", indexed(base_system.get("nodes", [])), indexed(head_system["nodes"])),
        ("edge", indexed(base_system.get("edges", [])), indexed(head_system["edges"])),
        (
            "classification",
            indexed(base_system.get("data_classifications", [])),
            indexed(head_system["data_classifications"]),
        ),
        (
            "secret",
            indexed(base_system.get("secret_classes", [])),
            indexed(head_system["secret_classes"]),
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
    base_rules = base.snapshot.rules if base else {}
    head_rules = head.snapshot.rules
    collections.append(
        (
            "rule",
            {
                item["id"]: item
                for collection in RULE_COLLECTIONS
                for item in base_rules.get(collection, [])
            },
            {
                item["id"]: item
                for collection in RULE_COLLECTIONS
                for item in head_rules[collection]
            },
        )
    )
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
    arguments = ["diff", "--name-only", "-z", "--no-renames", base]
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


def _statuses(root: Path, base: str, head: str | None, *, worktree: bool) -> dict[str, str]:
    arguments = ["diff", "--name-status", "-z", "--no-renames", base]
    if not worktree:
        arguments.append(_required_head(head))
    raw = _required_output(_git(root, arguments), operation="read changed path status")
    fields = [item for item in raw.split(b"\0") if item]
    if len(fields) % 2:
        raise ArchitectureError("unexpected NUL-delimited Git status output", code="git")
    statuses = {
        _path_text(fields[index + 1]): {b"A": "added", b"D": "deleted", b"M": "modified"}.get(
            fields[index][:1], "unsupported"
        )
        for index in range(0, len(fields), 2)
    }
    if worktree:
        untracked = _required_output(
            _git(root, ["ls-files", "--others", "--exclude-standard", "-z"]),
            operation="list untracked status",
        )
        statuses.update({_path_text(item): "added" for item in untracked.split(b"\0") if item})
    return statuses


def _line_stats(
    root: Path, base: str, head: str | None, *, worktree: bool
) -> dict[str, tuple[int | None, int | None]]:
    arguments = ["diff", "--numstat", "-z", "--no-renames", base]
    if not worktree:
        arguments.append(_required_head(head))
    raw = _required_output(_git(root, arguments), operation="read changed line counts")
    result: dict[str, tuple[int | None, int | None]] = {}
    for record in (item for item in raw.split(b"\0") if item):
        fields = record.split(b"\t", 2)
        if len(fields) != 3:
            raise ArchitectureError("unexpected NUL-delimited Git numstat output", code="git")
        added = None if fields[0] == b"-" else int(fields[0])
        deleted = None if fields[1] == b"-" else int(fields[1])
        result[_path_text(fields[2])] = (added, deleted)
    return result


def read_diff_file(root: Path, diff: ArchitectureDiff, path: str, side: str = "head") -> bytes | None:
    repository = Path(root).resolve(strict=True)
    if side not in {"base", "head"}:
        raise ArchitectureError("diff file side must be base or head", code="invalid")
    if side == "base":
        return _git_blob(repository, diff.base_sha, path)
    if diff.head_kind == "worktree":
        return _worktree_blob(repository, path)
    return _git_blob(repository, _required_head(diff.head_sha), path)


def git_tree_paths(root: Path, sha: str, prefixes: tuple[str, ...]) -> tuple[str, ...]:
    raw = _required_output(
        _git(root, ["ls-tree", "-r", "--name-only", "-z", "--full-tree", sha]),
        operation="list Git tree paths",
    )
    paths = tuple(
        sorted(
            path
            for path in (_path_text(item) for item in raw.split(b"\0") if item)
            if any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes)
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
) -> ArchitectureDiff:
    repository = Path(root).resolve(strict=True)
    base = _exact_commit(repository, base_sha, label="base_sha")
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
    base_state = _materialized_state(repository, base, adoption_base=True)
    paths = _changed_paths(repository, base, head, worktree=worktree)
    statuses = _statuses(repository, base, head, worktree=worktree)
    line_stats = _line_stats(repository, base, head, worktree=worktree)
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
        added, deleted = line_stats.get(path, (None, None))
        if worktree and statuses.get(path) == "added" and path not in line_stats and new is not None:
            if b"\0" not in new:
                added, deleted = len(new.splitlines()), 0
        artifacts.append(
            ChangedArtifact(
                path=path,
                status=statuses.get(path, "added" if old is None else "unsupported"),
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
        repository_inventory_digest=_tree_inventory_digest(
            repository, head, worktree=worktree, artifacts=tuple(artifacts)
        ),
        digest=_digest(payload),
        _base_state=base_state,
        _head_state=head_state,
    )
