from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
import stat
import ctypes
import errno
import fcntl
import threading
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any

MAX_MANIFEST_BYTES = 262_144
MAX_SOURCE_BYTES = 1_000_000
MAX_SOURCES = 256
MAX_DEPTH = 64
MAX_NODES = 20_000
MAX_STRING_LENGTH = 65_536
MAX_MARKDOWN_LINES = 20_000
MAX_MARKDOWN_LINE_LENGTH = 8_192
MAX_TASKS = 500
MAX_REVIEWERS = 20
MAX_COMMAND_ARGV = 32
MAX_TASK_REFERENCES = 20_000
MAX_RECEIPT_ERRORS = 100
MAX_AGENT_LENGTH = 128
MAX_TITLE_LENGTH = 256
MAX_PATH_LENGTH = 512
MAX_INTERFACE_LENGTH = 512
# Keep byte-identical to receipts.RECEIPT_KINDS (parity-tested; this module
# stays standalone-importable, so the set cannot be a shared import here).
RECEIPT_KINDS = frozenset(
    {
        "verification",
        "code_review",
        "test_review",
        "bitrix_review",
        "security_review",
        "data_review",
        "release_review",
    }
)
RUNTIME_ROUTE_KEYS = {
    "allowed_agents",
    "analysis_agents",
    "base_commit",
    "base_fingerprint",
    "change_id",
    "complexity",
    "created_at",
    "delivery_expected",
    "domains",
    "human_gates",
    "intent",
    "primary_skill",
    "quality_profiles",
    "rationale",
    "repo",
    "required_evidence",
    "review_agents",
    "risk",
    "route_id",
    "schema_version",
    "session_id",
    "status",
    "task",
    "task_domains",
    "updated_at",
    "workflow_skills",
    "write_agent",
}
_CAS_RECOVERY_SEQUENCE = itertools.count()

ROLE_MAP = {
    "spec-kit": {
        "constitution": "governance-candidate",
        "spec": "requirements-candidate",
        "plan": "architecture-candidate",
        "tasks": "task-candidate",
        "checklist": "convergence-hint",
    },
    "bmad": {
        "prd": "requirements-candidate",
        "spec": "requirements-candidate",
        "architecture": "architecture-candidate",
        "project-context": "governance-candidate",
        "epics": "task-candidate",
        "stories": "task-candidate",
        "sprint-status": "status-projection",
        "readiness": "convergence-hint",
    },
    "superpowers": {
        "spec": "requirements-candidate",
        "plan": "architecture-candidate",
        "sdd-evidence": "runtime-evidence",
    },
}
PATH_PREFIXES = {
    "spec-kit": (".specify/", "specs/"),
    "bmad": ("_bmad/", "_bmad-output/"),
    "superpowers": ("docs/superpowers/", ".superpowers/sdd/"),
}
# YAML authority syntax is rejected; Markdown emphasis that merely looks like
# an alias (italic "*word ... *" at line start) is legitimate upstream template
# text (spec-kit ships e.g. "*Example of marking unclear requirements:*" and
# "*GATE: Must pass before Phase 0 research. ...*") and must load. Anchors and
# aliases are matched only in YAML positions: document/sequence start "&name",
# mapping value ": &name", whole-value alias "*name" after ": " or "- ".
FORBIDDEN_SOURCE = re.compile(
    r"(?:^|\s)!!"
    r"|(?:^|\s)<<:"
    r"|^[ \t]*(?:-[ \t]+)?&[A-Za-z0-9_.-]+"
    r"|:[ \t]+&[A-Za-z0-9_.-]+"
    r"|^[ \t]*-[ \t]+\*[A-Za-z0-9_.-]+[ \t]*$"
    r"|:[ \t]+\*[A-Za-z0-9_.-]+[ \t]*$",
    re.M,
)
TASK_PATTERN = re.compile(r"^\s*<!--\s*AGB-TASK\s+(.+?)\s*-->\s*$")
CLAIM_PATTERN = re.compile(r"^\s*<!--\s*AGB-CLAIM\s+(.+?)\s*-->\s*$")
STATUS_PATTERN = re.compile(r"^\s*<!--\s*AGB-TASK-STATUS\s+(.+?)\s*-->\s*$")
TASK_KEYS = {
    "key",
    "title",
    "depends_on",
    "covers",
    "files",
    "interfaces",
    "red",
    "green",
    "status",
    "enrichment_required",
}
SOURCE_STATUS_VALUES = {"pending", "in_progress", "complete"}
# Conservative-superset BMAD story-status vocabulary around
# bmad-code-org/BMAD-METHOD v6.12.0 (template samples omit `ready-for-review`;
# build-spec front matter adds `in-review`): only terminal members may mark
# imported work advanced; everything else (including `blocked`) stays a
# non-terminal hint, advisory only.
BMAD_TERMINAL_STATUS = frozenset({"done", "complete", "completed", "ready-for-review", "in-review", "review"})
BMAD_NONTERMINAL_STATUS = frozenset(
    {"backlog", "draft", "ready-for-dev", "ready", "in-progress", "open", "optional", "blocked", "high-level"}
)
PLACEHOLDER = re.compile(r"(?i)(?:\bUNKNOWN\b|\bTBD\b|\bTODO\b|NEEDS CLARIFICATION|\.\.\.)")
SPEC_TASK = re.compile(r"^\s*-\s*\[([ xX])\]\s+(T[0-9]{1,6})\s+(?:(\[P\])\s+)?(?:\[US[0-9]+\]\s+)?(.+?)\s*$")
BMAD_TASK = re.compile(r"^\s*-\s*\[([ xX])\]\s+(.+?)\s*$")
CRITERION_TOKEN = re.compile(r"\b(?:AC|INV|FORBID)-[0-9]{3,6}\b")
FILE_TOKEN = re.compile(r"(?<![A-Za-z0-9_.-])([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\.[A-Za-z0-9]+)")
NATIVE_STATUS = re.compile(r"^\s*-\s*\[([ xX])\]\s+(T[0-9]{1,6})\b")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
SAFE_UNITTEST_TARGET = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*(?::[A-Za-z_][A-Za-z0-9_]*)?$")


class WorkflowArtifactError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid") -> None:
        super().__init__(message)
        self.code = code


class WorkflowSource:
    def __init__(self, identity: dict[str, Any], content: str) -> None:
        self.identity = identity
        self.content = content

    def to_dict(self) -> dict[str, Any]:
        return dict(self.identity)


class SourceBundle:
    def __init__(self, sources: tuple[WorkflowSource, ...], manifest_digest: str) -> None:
        self.sources = sources
        self.manifest_digest = manifest_digest

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "manifest_digest": self.manifest_digest,
            "sources": [source.to_dict() for source in self.sources],
        }


def validate_workflow_source(identity: Any) -> dict[str, Any]:
    required = {"schema_version", "source_type", "source_version", "role", "path", "size", "sha256"}
    if not isinstance(identity, dict) or set(identity) != required or identity.get("schema_version") != 1:
        raise WorkflowArtifactError("workflow source has an invalid closed shape", code="source-schema")
    source_type = identity.get("source_type")
    role = identity.get("role")
    if source_type not in ROLE_MAP or role not in ROLE_MAP[source_type]:
        raise WorkflowArtifactError("workflow source type or role is invalid", code="source-schema")
    _bounded_text(identity.get("source_version"), "source_version", maximum=32)
    path = identity.get("path")
    if not isinstance(path, str) or Path(path).is_absolute():
        raise WorkflowArtifactError("workflow source path is invalid", code="source-schema")
    _relative_path(Path("/repository"), path)
    size = identity.get("size")
    if isinstance(size, bool) or not isinstance(size, int) or not 0 <= size <= MAX_SOURCE_BYTES:
        raise WorkflowArtifactError("workflow source size is invalid", code="source-schema")
    if not isinstance(identity.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", identity["sha256"]):
        raise WorkflowArtifactError("workflow source digest is invalid", code="source-schema")
    return identity


def canonical_json(value: Any) -> bytes:
    _bounded_walk(value)
    try:
        return (
            json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise WorkflowArtifactError("value is not canonical JSON", code="json") from exc


def _bounded_walk(value: Any) -> None:
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            raise WorkflowArtifactError("JSON structural limit exceeded", code="limit")
        if isinstance(current, str):
            if len(current) > MAX_STRING_LENGTH or unicodedata.normalize("NFC", current) != current:
                raise WorkflowArtifactError("JSON string is unbounded or non-NFC", code="unicode")
            try:
                current.encode("utf-8")
            except UnicodeError as exc:
                raise WorkflowArtifactError("JSON string is not UTF-8 encodable", code="unicode") from exc
        elif isinstance(current, dict):
            for key, child in current.items():
                if not isinstance(key, str):
                    raise WorkflowArtifactError("JSON object key must be a string", code="json")
                stack.append((key, depth + 1))
                stack.append((child, depth + 1))
        elif isinstance(current, list):
            stack.extend((child, depth + 1) for child in current)
        elif current is not None and not isinstance(current, (bool, int, float)):
            raise WorkflowArtifactError("unsupported JSON value", code="json")


def _strict_json(raw: bytes, *, limit: int) -> Any:
    if len(raw) > limit or raw.startswith(b"\xef\xbb\xbf"):
        raise WorkflowArtifactError("JSON byte limit or encoding preamble rejected", code="limit")
    try:
        text = raw.decode("utf-8", errors="strict")

        def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in items:
                if key in result:
                    raise WorkflowArtifactError(f"duplicate JSON key: {key}", code="duplicate")
                result[key] = value
            return result

        value = json.loads(
            text,
            object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                WorkflowArtifactError(f"non-finite JSON value: {token}", code="json")
            ),
        )
    except WorkflowArtifactError:
        raise
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise WorkflowArtifactError("invalid strict JSON", code="json") from exc
    _bounded_walk(value)
    return value


def _relative_path(root: Path, path: Path | str) -> str:
    raw = os.fspath(path)
    if not isinstance(raw, str) or "\\" in raw or CONTROL.search(raw):
        raise WorkflowArtifactError("path contains a control character or backslash", code="path")
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            candidate = candidate.relative_to(root)
        except ValueError as exc:
            raise WorkflowArtifactError("path escapes repository", code="path") from exc
    pure = PurePosixPath(candidate.as_posix())
    if not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise WorkflowArtifactError("invalid repository-relative path", code="path")
    value = pure.as_posix()
    if len(value) > MAX_PATH_LENGTH or unicodedata.normalize("NFC", value) != value:
        raise WorkflowArtifactError("path is unbounded or non-NFC", code="path")
    return value


def _bounded_text(value: Any, name: str, *, minimum: int = 1, maximum: int = MAX_STRING_LENGTH) -> str:
    if (
        not isinstance(value, str)
        or len(value) < minimum
        or len(value) > maximum
        or unicodedata.normalize("NFC", value) != value
        or CONTROL.search(value)
    ):
        raise WorkflowArtifactError(f"{name} is empty, unbounded, non-NFC, or contains controls", code="schema")
    return value


def _bounded_markdown(content: str, path: str) -> None:
    if "\x00" in content or unicodedata.normalize("NFC", content) != content:
        raise WorkflowArtifactError(f"source content is unsafe: {path}", code="content")
    lines = content.splitlines()
    if len(lines) > MAX_MARKDOWN_LINES or any(len(line) > MAX_MARKDOWN_LINE_LENGTH for line in lines):
        raise WorkflowArtifactError(f"source text limits exceeded: {path}", code="limit")


def _open_root(root: Path) -> tuple[Path, int]:
    canonical = root.resolve(strict=True)
    required = ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK")
    if any(not hasattr(os, name) for name in required) or os.open not in getattr(os, "supports_dir_fd", set()):
        raise WorkflowArtifactError("secure descriptor reads unsupported", code="platform")
    try:
        descriptor = os.open(canonical, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as exc:
        raise WorkflowArtifactError("cannot open repository root safely", code="io") from exc
    return canonical, descriptor


def _read_regular(root: Path, relative: str, *, limit: int) -> bytes:
    canonical, root_fd = _open_root(root)
    del canonical
    parts = PurePosixPath(relative).parts
    directory_fd = os.dup(root_fd)
    os.close(root_fd)
    descriptor: int | None = None
    flags_dir = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    flags_file = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
    try:
        for component in parts[:-1]:
            next_fd = os.open(component, flags_dir, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        descriptor = os.open(parts[-1], flags_file, dir_fd=directory_fd)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise WorkflowArtifactError(f"source is not a bounded regular file: {relative}", code="file")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65_536, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > limit:
                raise WorkflowArtifactError(f"source exceeds byte limit: {relative}", code="limit")
        after = os.fstat(descriptor)
        identity = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        observed = (after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        if identity != observed:
            raise WorkflowArtifactError(f"source changed while reading: {relative}", code="race")
        return b"".join(chunks)
    except WorkflowArtifactError:
        raise
    except OSError as exc:
        raise WorkflowArtifactError(f"cannot read source safely: {relative}", code="io") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory_fd)


def load_source_manifest(root: Path, manifest_path: Path) -> SourceBundle:
    canonical = root.resolve(strict=True)
    manifest_rel = _relative_path(canonical, manifest_path)
    manifest_raw = _read_regular(canonical, manifest_rel, limit=MAX_MANIFEST_BYTES)
    manifest = _strict_json(manifest_raw, limit=MAX_MANIFEST_BYTES)
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"schema_version", "sources"}
        or manifest.get("schema_version") != 1
    ):
        raise WorkflowArtifactError("manifest must be a closed schema_version 1 object", code="schema")
    entries = manifest.get("sources")
    if not isinstance(entries, list) or len(entries) > MAX_SOURCES:
        raise WorkflowArtifactError("manifest sources must be a bounded array", code="schema")
    seen: set[str] = set()
    seen_casefold: set[str] = set()
    sources: list[WorkflowSource] = []
    for entry in entries:
        required = {"source_type", "source_version", "role", "path"}
        if (
            not isinstance(entry, dict)
            or set(entry) != required
            or not all(isinstance(entry[key], str) for key in required)
        ):
            raise WorkflowArtifactError("manifest source entry is not closed", code="schema")
        source_type = entry["source_type"]
        role = entry["role"]
        source_version = _bounded_text(entry["source_version"], "source_version", maximum=32)
        _bounded_text(source_type, "source_type", maximum=32)
        _bounded_text(role, "role", maximum=32)
        if source_type not in ROLE_MAP or role not in ROLE_MAP[source_type]:
            raise WorkflowArtifactError("source type or role is not allowlisted", code="role")
        if Path(entry["path"]).is_absolute():
            raise WorkflowArtifactError("source path must be repository-relative", code="path")
        path = _relative_path(canonical, entry["path"])
        folded_path = path.casefold()
        if path in seen or folded_path in seen_casefold or not path.startswith(PATH_PREFIXES[source_type]):
            raise WorkflowArtifactError("source path is duplicate or outside framework allowlist", code="path")
        if source_type == "superpowers" and role == "sdd-evidence" and not path.startswith(".superpowers/sdd/"):
            raise WorkflowArtifactError("Superpowers runtime evidence must stay under .superpowers/sdd", code="path")
        if source_type == "superpowers" and role != "sdd-evidence" and not path.startswith("docs/superpowers/"):
            raise WorkflowArtifactError("Superpowers tracked sources must stay under docs/superpowers", code="path")
        seen.add(path)
        seen_casefold.add(folded_path)
        raw = _read_regular(canonical, path, limit=MAX_SOURCE_BYTES)
        try:
            content = raw.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise WorkflowArtifactError(f"source is not UTF-8: {path}", code="unicode") from exc
        _bounded_markdown(content, path)
        if FORBIDDEN_SOURCE.search(content):
            raise WorkflowArtifactError(
                f"source contains non-NFC or forbidden YAML authority syntax: {path}", code="content"
            )
        identity = {
            "schema_version": 1,
            "source_type": source_type,
            "source_version": source_version,
            "role": role,
            "path": path,
            "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        validate_workflow_source(identity)
        sources.append(WorkflowSource(identity, content))
    sources.sort(key=lambda item: (item.identity["source_type"], item.identity["path"], item.identity["role"]))
    normalized_manifest = {"schema_version": 1, "sources": [source.to_dict() for source in sources]}
    return SourceBundle(tuple(sources), hashlib.sha256(canonical_json(normalized_manifest)).hexdigest())


def load_runtime_authority(root: Path, kind: str) -> dict[str, Any]:
    """Read the two CLI authority pointers through the bounded descriptor loader."""
    relative = {
        "route": ".grok-stack/runtime/active-route.json",
        "change": ".grok-stack/runtime/active-change.json",
    }.get(kind)
    if relative is None:
        raise WorkflowArtifactError("runtime authority kind is invalid", code="route")
    data = _strict_json(_read_regular(root, relative, limit=MAX_MANIFEST_BYTES), limit=MAX_MANIFEST_BYTES)
    if not isinstance(data, dict):
        raise WorkflowArtifactError(f"active {kind} must be an object", code=kind)
    if kind == "route":
        required = {"route_id", "write_agent", "review_agents", "required_evidence"}
        if set(data) - RUNTIME_ROUTE_KEYS or not required.issubset(data):
            raise WorkflowArtifactError("active route has an invalid closed shape", code="route")
        if "schema_version" in data and data["schema_version"] != 1:
            raise WorkflowArtifactError("active route schema version is invalid", code="route")
        if not isinstance(data.get("route_id"), str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", data["route_id"]):
            raise WorkflowArtifactError("active route id is invalid", code="route")
        _validate_route(data)
    elif (
        set(data) != {"change_id", "path"}
        or not isinstance(data.get("change_id"), str)
        or not re.fullmatch(r"[A-Za-z0-9._:-]{3,128}", data["change_id"])
        or data.get("path") != f"engineering/changes/{data['change_id']}"
    ):
        raise WorkflowArtifactError("active change has an invalid closed shape", code="change")
    return data


def digest_without(value: dict[str, Any], field: str) -> str:
    return hashlib.sha256(canonical_json({key: item for key, item in value.items() if key != field})).hexdigest()


def adapt_sources(bundle: SourceBundle) -> list[dict[str, Any]]:
    candidates = []
    for source in bundle.sources:
        identity = source.identity
        role = str(identity["role"])
        source_type = str(identity["source_type"])
        candidate = {
            "schema_version": 1,
            "source_type": source_type,
            "role": role,
            "path": identity["path"],
            "sha256": identity["sha256"],
            "candidate_kind": ROLE_MAP[source_type][role],
            "authority": False,
            "receipt_eligible": False,
        }
        candidates.append(candidate)
    return candidates


def _load_native_spec(root: Path, change_id: str) -> dict[str, Any]:
    relative = f"engineering/changes/{change_id}/change-spec.yaml"
    data = _strict_json(_read_regular(root, relative, limit=MAX_SOURCE_BYTES), limit=MAX_SOURCE_BYTES)
    if not isinstance(data, dict) or data.get("change_id") != change_id:
        raise WorkflowArtifactError("native change specification is missing or mismatched", code="native")
    return data


def _string_list(
    value: Any,
    name: str,
    *,
    allow_empty: bool = True,
    maximum_items: int,
    maximum_length: int = 512,
) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value) or len(value) > maximum_items:
        raise WorkflowArtifactError(f"task {name} must be a bounded array", code="task")
    result = []
    for item in value:
        if (
            not isinstance(item, str)
            or not item
            or len(item) > maximum_length
            or unicodedata.normalize("NFC", item) != item
            or CONTROL.search(item)
        ):
            raise WorkflowArtifactError(f"task {name} item is invalid", code="task")
        result.append(item)
    if len({item.casefold() for item in result}) != len(result):
        raise WorkflowArtifactError(f"task {name} contains duplicates", code="task")
    return result


def _verification_command(value: Any, name: str) -> list[str]:
    command = _string_list(
        value,
        name,
        allow_empty=False,
        maximum_items=MAX_COMMAND_ARGV,
        maximum_length=512,
    )
    if any("http://" in item.casefold() or "https://" in item.casefold() for item in command):
        raise WorkflowArtifactError(f"task {name} command contains a network locator", code="command")
    if command[:3] == ["python3", "-m", "unittest"]:
        if not all(SAFE_UNITTEST_TARGET.fullmatch(item) for item in command[3:]):
            raise WorkflowArtifactError(f"task {name} unittest command is outside the allowlist", code="command")
        return command
    if command in (
        ["python3", "scripts/grok_verify.py", "--mode", "fast"],
        ["python3", "scripts/grok_verify.py", "--mode", "pr"],
    ):
        return command
    raise WorkflowArtifactError(f"task {name} is not an allowlisted read-only verification command", code="command")


def _validate_route(route: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    writer = route.get("write_agent")
    reviewers = route.get("review_agents")
    required = route.get("required_evidence")
    if not isinstance(writer, str):
        raise WorkflowArtifactError("active route has no valid writer", code="route")
    writer = _bounded_text(writer, "write_agent", maximum=MAX_AGENT_LENGTH)
    if (
        not isinstance(reviewers, list)
        or len(reviewers) > MAX_REVIEWERS
        or not all(isinstance(item, str) for item in reviewers)
    ):
        raise WorkflowArtifactError("active route reviewers are invalid", code="route")
    normalized_reviewers = [_bounded_text(item, "review_agent", maximum=MAX_AGENT_LENGTH) for item in reviewers]
    if len({item.casefold() for item in normalized_reviewers}) != len(normalized_reviewers):
        raise WorkflowArtifactError("active route reviewers collide", code="route")
    if (
        not isinstance(required, list)
        or not required
        or len(required) > len(RECEIPT_KINDS)
        or any(not isinstance(item, str) or item not in RECEIPT_KINDS for item in required)
        or len(set(required)) != len(required)
    ):
        raise WorkflowArtifactError("active route required_evidence is empty or outside the closed set", code="route")
    return writer, normalized_reviewers, list(required)


def _task_metadata(bundle: SourceBundle) -> list[tuple[WorkflowSource, dict[str, Any]]]:
    result: list[tuple[WorkflowSource, dict[str, Any]]] = []
    for source in bundle.sources:
        if ROLE_MAP[str(source.identity["source_type"])][str(source.identity["role"])] != "task-candidate":
            continue
        if len(result) > MAX_TASKS:
            raise WorkflowArtifactError("task graph exceeds the task limit", code="limit")
        annotated_keys: set[str] = set()
        for line in source.content.splitlines():
            match = TASK_PATTERN.fullmatch(line)
            if not match:
                continue
            value = _strict_json(match.group(1).encode("utf-8"), limit=65_536)
            if (
                not isinstance(value, dict)
                or set(value) - TASK_KEYS
                or not TASK_KEYS.difference({"enrichment_required"}).issubset(value)
            ):
                raise WorkflowArtifactError("AGB task metadata has unsupported or missing fields", code="task")
            annotated_keys.add(str(value["key"]))
            result.append((source, value))
        native = _native_framework_tasks(source)
        result.extend((source, value) for value in native if value["key"] not in annotated_keys)
    return result


def _generated_task(key: str, title: str, depends_on: list[str], *, checked: bool) -> dict[str, Any]:
    covers = sorted(set(CRITERION_TOKEN.findall(title)))
    parsed_files = sorted(set(FILE_TOKEN.findall(title)))
    files = parsed_files or [f"workflow/imports/{key}.md"]
    command = ["python3", "scripts/grok_verify.py", "--mode", "pr"]
    enrichment = ["green", "interfaces", "red"] + ([] if parsed_files else ["files"])
    return {
        "key": key,
        "title": title[:256],
        "depends_on": depends_on,
        "covers": covers,
        "files": files,
        "interfaces": [f"imported-task:{key}"],
        "red": command,
        "green": command,
        "status": "complete" if checked else "pending",
        "enrichment_required": sorted(enrichment),
    }


def _native_framework_tasks(source: WorkflowSource) -> list[dict[str, Any]]:
    source_type = str(source.identity["source_type"])
    role = str(source.identity["role"])
    if source_type == "spec-kit" and role == "tasks":
        result: list[dict[str, Any]] = []
        previous_phase: list[str] = []
        current_phase: list[str] = []
        saw_phase = False
        for line in source.content.splitlines():
            if re.match(r"^#{2,6}\s+Phase\b", line, re.I):
                if saw_phase:
                    previous_phase = list(current_phase)
                current_phase = []
                saw_phase = True
                continue
            match = SPEC_TASK.fullmatch(line)
            if not match:
                continue
            key = match.group(2).lower()
            parallel = bool(match.group(3))
            title = match.group(4)
            dependencies = list(previous_phase)
            if not parallel and current_phase:
                dependencies.append(current_phase[-1])
            result.append(_generated_task(key, title, sorted(set(dependencies)), checked=match.group(1).lower() == "x"))
            current_phase.append(key)
        return result
    if source_type == "bmad" and role in {"stories", "epics"}:
        result: list[dict[str, Any]] = []
        section_kind = "epic" if role == "epics" else "story"
        section = "unscoped"
        previous: str | None = None
        ordinal = 0
        for line in source.content.splitlines():
            heading = re.match(
                r"^#{1,4}\s+(Story|Epic)\s+([0-9]+(?:\.[0-9]+)*[a-z]?|[A-Za-z0-9][A-Za-z0-9.-]*)", line, re.I
            )
            if heading:
                section_kind = heading.group(1).lower()
                section = re.sub(r"[^a-z0-9]+", "-", heading.group(2).lower()).strip("-") or "unscoped"
                previous = None
                ordinal = 0
                continue
            match = BMAD_TASK.fullmatch(line)
            if not match:
                continue
            ordinal += 1
            key = f"{section_kind}-{section}-{ordinal:03d}"
            title = match.group(2)
            dependencies = [previous] if previous is not None else []
            result.append(_generated_task(key, title, dependencies, checked=match.group(1).lower() == "x"))
            previous = key
        return result
    return []


def _source_status_is_terminal(source: "WorkflowSource", lines: list[str]) -> bool:
    """First-wins status extraction for native framework story/spec documents.

    Accepts the leading ``---`` front-matter ``status:`` key (BMAD v6.12 build
    spec), the annotated ``## Status`` heading followed by its value line, and
    the upstream story-template bare line form ``Status: <value>``. Unknown
    tokens are non-terminal by design; only BMAD_TERMINAL_STATUS advances
    imported work, and never native verification.
    """
    if source.identity["source_type"] != "bmad":
        return False
    if lines and lines[0] == "---":
        for line in lines[1:]:
            if line == "---":
                break
            match = re.fullmatch(r"status:\s*['\"]?([^'\"\s#]+)['\"]?", line, re.I)
            if match:
                return match.group(1).lower().replace(" ", "-") in BMAD_TERMINAL_STATUS
    for index, line in enumerate(lines):
        if re.fullmatch(r"#{2,6}\s+Status", line, re.I):
            status = next((item for item in lines[index + 1 :] if item and not item.startswith("#")), "")
            return status.lower().replace(" ", "-") in BMAD_TERMINAL_STATUS
        match = re.fullmatch(r"Status:\s*(.+)", line, re.I)
        if match:
            return match.group(1).strip("'\"").lower().replace(" ", "-") in BMAD_TERMINAL_STATUS
    return False


def _advanced_status_hints(bundle: SourceBundle | None) -> set[str]:
    if bundle is None:
        return set()
    hints: set[str] = set()
    all_task_keys = {task["key"] for source in bundle.sources for task in _native_framework_tasks(source)}
    for source in bundle.sources:
        native = _native_framework_tasks(source)
        checked_lines = [line for line in source.content.splitlines() if re.match(r"^\s*-\s*\[[xX]\]", line)]
        if checked_lines:
            checked_titles = {BMAD_TASK.fullmatch(line).group(2) for line in checked_lines if BMAD_TASK.fullmatch(line)}
            hints.update(
                task["key"]
                for task in native
                if task["title"] in checked_titles
                or str(source.identity["source_type"]) == "spec-kit"
                and any(task["key"].upper() in line for line in checked_lines)
            )
        lines = [line.strip() for line in source.content.splitlines()]
        if source.identity["source_type"] == "bmad" and source.identity["role"] == "sprint-status":
            for line in lines:
                match = re.fullmatch(
                    r"([a-z0-9][a-z0-9-]{0,127}):\s*(done|complete|completed|ready-for-review|in-review|review)",
                    line,
                    re.I,
                )
                if not match:
                    continue
                parts = match.group(1).lower().split("-")
                numeric = [part for part in parts if part.isdigit()]
                prefix = "story-" + "-".join(numeric[:2]) + "-" if numeric else "story-" + match.group(1).lower() + "-"
                hints.update(key for key in all_task_keys if key.startswith(prefix))
        if native and _source_status_is_terminal(source, lines):
            hints.update(task["key"] for task in native)
    return hints


def _validate_repo_path(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) > MAX_PATH_LENGTH
        or "\\" in value
        or CONTROL.search(value)
        or unicodedata.normalize("NFC", value) != value
    ):
        raise WorkflowArtifactError("task file path is unsafe", code="path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise WorkflowArtifactError("task file path is unsafe", code="path")
    return pure.as_posix()


def _has_path(graph: dict[str, set[str]], start: str, target: str) -> bool:
    pending = list(graph.get(start, ()))
    seen: set[str] = set()
    while pending:
        item = pending.pop()
        if item == target:
            return True
        if item not in seen:
            seen.add(item)
            pending.extend(graph.get(item, ()))
    return False


def compile_task_graph(root: Path, change_id: str, bundle: SourceBundle, route: dict[str, Any]) -> dict[str, Any]:
    writer, reviewers, _required_evidence = _validate_route(route)
    native = _load_native_spec(root, change_id)
    required_ids = sorted(
        str(item["id"])
        for group in ("acceptance_criteria", "invariants", "forbidden_outcomes")
        for item in native.get(group, [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    )
    raw_tasks = _task_metadata(bundle)
    if len(raw_tasks) > MAX_TASKS:
        raise WorkflowArtifactError("task graph exceeds the task limit", code="limit")
    keys: set[str] = set()
    interim: list[dict[str, Any]] = []
    for source, raw in raw_tasks:
        key, title = raw["key"], raw["title"]
        if (
            not isinstance(key, str)
            or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", key)
            or key in keys
            or not isinstance(title, str)
            or not title
            or len(title) > MAX_TITLE_LENGTH
            or unicodedata.normalize("NFC", title) != title
            or CONTROL.search(title)
        ):
            raise WorkflowArtifactError("task key/title is invalid or duplicate", code="task")
        keys.add(key)
        dependencies = _string_list(raw["depends_on"], "depends_on", maximum_items=100)
        covers = _string_list(raw["covers"], "covers", maximum_items=500)
        if any(CRITERION_TOKEN.fullmatch(item) is None for item in covers):
            raise WorkflowArtifactError("task criterion id is invalid", code="coverage")
        files = [
            _validate_repo_path(item)
            for item in _string_list(raw["files"], "files", allow_empty=False, maximum_items=200)
        ]
        interfaces = _string_list(
            raw["interfaces"], "interfaces", allow_empty=False, maximum_items=100, maximum_length=MAX_INTERFACE_LENGTH
        )
        red = _verification_command(raw["red"], "red")
        green = _verification_command(raw["green"], "green")
        status_value = raw["status"]
        enrichment = _string_list(
            raw.get("enrichment_required", []), "enrichment_required", maximum_items=5, maximum_length=32
        )
        if any(item not in {"files", "interfaces", "red", "green", "covers"} for item in enrichment):
            raise WorkflowArtifactError("task enrichment marker is invalid", code="task")
        if status_value not in SOURCE_STATUS_VALUES:
            raise WorkflowArtifactError("task source status is invalid", code="task")
        stable_core = {
            "key": key,
            "title": title,
            "covers": sorted(covers),
            "files": sorted(files),
            "interfaces": sorted(interfaces),
            "enrichment_required": sorted(enrichment),
            "source_sha256": source.identity["sha256"],
        }
        task_id = "TASK-" + hashlib.sha256(canonical_json(stable_core)).hexdigest()[:12]
        interim.append(
            {
                "task_id": task_id,
                "key": key,
                "title": title,
                "depends_on_keys": dependencies,
                "covers": sorted(covers),
                "files": sorted(files),
                "interfaces": sorted(interfaces),
                "red": red,
                "green": green,
                "source_status": status_value,
                "enrichment_required": sorted(enrichment),
                "source_sha256": source.identity["sha256"],
            }
        )
    aggregate_references = sum(
        len(task["depends_on_keys"]) + len(task["covers"]) + len(task["files"]) + len(task["interfaces"])
        for task in interim
    )
    if aggregate_references > MAX_TASK_REFERENCES:
        raise WorkflowArtifactError("task graph aggregate reference limit exceeded", code="limit")
    id_by_key = {task["key"]: task["task_id"] for task in interim}
    dependencies: dict[str, set[str]] = {}
    for task in interim:
        missing = set(task.pop("depends_on_keys")) - set(id_by_key)
        if missing:
            raise WorkflowArtifactError(f"task has missing dependencies: {sorted(missing)}", code="dependency")
        task["depends_on"] = sorted(id_by_key[key] for key in raw_tasks_by_key(interim, task["key"], raw_tasks))
        dependencies[task["task_id"]] = set(task["depends_on"])
    pending = {task_id: len(values) for task_id, values in dependencies.items()}
    dependents: dict[str, set[str]] = {task_id: set() for task_id in dependencies}
    for task_id, values in dependencies.items():
        for dependency in values:
            dependents[dependency].add(task_id)
    ready = sorted(task_id for task_id, count in pending.items() if count == 0)
    order: list[str] = []
    while ready:
        task_id = ready.pop(0)
        order.append(task_id)
        for dependent in sorted(dependents[task_id]):
            pending[dependent] -= 1
            if pending[dependent] == 0:
                ready.append(dependent)
                ready.sort()
    if len(order) != len(dependencies):
        raise WorkflowArtifactError("task dependency graph contains a cycle", code="cycle")
    ancestors: dict[str, set[str]] = {}
    for task_id in order:
        ancestors[task_id] = set(dependencies[task_id])
        for dependency in dependencies[task_id]:
            ancestors[task_id].update(ancestors[dependency])
    file_owners: dict[str, list[str]] = {}
    for task in interim:
        for path in task["files"]:
            file_owners.setdefault(path.casefold(), []).append(task["task_id"])
    for owners in file_owners.values():
        for index, left in enumerate(owners):
            for right in owners[index + 1 :]:
                if left not in ancestors[right] and right not in ancestors[left]:
                    raise WorkflowArtifactError("unordered tasks declare a write conflict", code="write-conflict")
    covered = {criterion for task in interim for criterion in task["covers"]}
    unknown = covered - set(required_ids)
    missing = set(required_ids) - covered
    if unknown or missing:
        raise WorkflowArtifactError(
            f"task criterion coverage mismatch: unknown={sorted(unknown)} missing={sorted(missing)}", code="coverage"
        )
    graph: dict[str, Any] = {
        "schema_version": 1,
        "change_id": change_id,
        "source_manifest_digest": bundle.manifest_digest,
        "write_agent": writer,
        "review_agents": sorted(set(reviewers)),
        "tasks": sorted(interim, key=lambda item: item["task_id"]),
    }
    graph["graph_digest"] = digest_without(graph, "graph_digest")
    validate_task_graph(graph)
    return graph


def raw_tasks_by_key(
    interim: list[dict[str, Any]], key: str, raw_tasks: list[tuple[WorkflowSource, dict[str, Any]]]
) -> list[str]:
    del interim
    for _source, raw in raw_tasks:
        if raw["key"] == key:
            return list(raw["depends_on"])
    raise WorkflowArtifactError("task dependency source disappeared", code="task")


def validate_task_graph(graph: Any) -> dict[str, Any]:
    required = {
        "schema_version",
        "change_id",
        "source_manifest_digest",
        "write_agent",
        "review_agents",
        "tasks",
        "graph_digest",
    }
    if not isinstance(graph, dict) or set(graph) != required or graph.get("schema_version") != 1:
        raise WorkflowArtifactError("task graph has an invalid closed shape", code="graph-schema")
    _bounded_text(graph.get("change_id"), "change_id", minimum=3, maximum=128)
    _bounded_text(graph.get("write_agent"), "write_agent", maximum=MAX_AGENT_LENGTH)
    for field in ("source_manifest_digest", "graph_digest"):
        if not isinstance(graph.get(field), str) or not re.fullmatch(r"[0-9a-f]{64}", graph[field]):
            raise WorkflowArtifactError(f"task graph {field} is invalid", code="graph-schema")
    reviewers = graph.get("review_agents")
    if (
        not isinstance(reviewers, list)
        or len(reviewers) > MAX_REVIEWERS
        or any(not isinstance(item, str) for item in reviewers)
    ):
        raise WorkflowArtifactError("task graph reviewers are invalid", code="graph-schema")
    normalized_reviewers = [_bounded_text(item, "review_agent", maximum=MAX_AGENT_LENGTH) for item in reviewers]
    if len({item.casefold() for item in normalized_reviewers}) != len(normalized_reviewers):
        raise WorkflowArtifactError("task graph reviewers collide", code="graph-schema")
    tasks = graph.get("tasks")
    if not isinstance(tasks, list) or len(tasks) > MAX_TASKS:
        raise WorkflowArtifactError("task graph task limit exceeded", code="graph-schema")
    expected_task_keys = {
        "task_id",
        "key",
        "title",
        "depends_on",
        "covers",
        "files",
        "interfaces",
        "red",
        "green",
        "source_status",
        "enrichment_required",
        "source_sha256",
    }
    task_ids: set[str] = set()
    task_keys: set[str] = set()
    aggregate = 0
    for task in tasks:
        if not isinstance(task, dict) or set(task) != expected_task_keys:
            raise WorkflowArtifactError("task record has an invalid closed shape", code="graph-schema")
        task_id = task.get("task_id")
        key = task.get("key")
        if (
            not isinstance(task_id, str)
            or not re.fullmatch(r"TASK-[0-9a-f]{12}", task_id)
            or task_id in task_ids
            or not isinstance(key, str)
            or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", key)
            or key.casefold() in task_keys
        ):
            raise WorkflowArtifactError("task identity is invalid or duplicate", code="graph-schema")
        task_ids.add(task_id)
        task_keys.add(key.casefold())
        _bounded_text(task.get("title"), "task title", maximum=MAX_TITLE_LENGTH)
        dependencies = _string_list(task.get("depends_on"), "depends_on", maximum_items=100)
        covers = _string_list(task.get("covers"), "covers", maximum_items=500)
        if any(CRITERION_TOKEN.fullmatch(item) is None for item in covers):
            raise WorkflowArtifactError("task criterion id is invalid", code="graph-schema")
        files = _string_list(task.get("files"), "files", allow_empty=False, maximum_items=200)
        for path in files:
            _validate_repo_path(path)
        interfaces = _string_list(
            task.get("interfaces"),
            "interfaces",
            allow_empty=False,
            maximum_items=100,
            maximum_length=MAX_INTERFACE_LENGTH,
        )
        _verification_command(task.get("red"), "red")
        _verification_command(task.get("green"), "green")
        enrichment = _string_list(
            task.get("enrichment_required"), "enrichment_required", maximum_items=5, maximum_length=32
        )
        if any(item not in {"files", "interfaces", "red", "green", "covers"} for item in enrichment):
            raise WorkflowArtifactError("task enrichment marker is invalid", code="graph-schema")
        if task.get("source_status") not in SOURCE_STATUS_VALUES:
            raise WorkflowArtifactError("task source status is invalid", code="graph-schema")
        if not isinstance(task.get("source_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", task["source_sha256"]):
            raise WorkflowArtifactError("task source digest is invalid", code="graph-schema")
        aggregate += len(dependencies) + len(covers) + len(files) + len(interfaces)
    if aggregate > MAX_TASK_REFERENCES:
        raise WorkflowArtifactError("task graph aggregate reference limit exceeded", code="graph-schema")
    if any(dependency not in task_ids for task in tasks for dependency in task["depends_on"]):
        raise WorkflowArtifactError("task graph dependency is missing", code="graph-schema")
    return graph


def validate_convergence_report(report: Any) -> dict[str, Any]:
    required = {
        "schema_version",
        "change_id",
        "graph_digest",
        "source_manifest_digest",
        "status",
        "coverage",
        "findings",
        "report_digest",
    }
    if not isinstance(report, dict) or set(report) != required or report.get("schema_version") != 1:
        raise WorkflowArtifactError("convergence report has an invalid closed shape", code="report-schema")
    _bounded_text(report.get("change_id"), "change_id", minimum=3, maximum=128)
    for field in ("graph_digest", "source_manifest_digest", "report_digest"):
        if not isinstance(report.get(field), str) or not re.fullmatch(r"[0-9a-f]{64}", report[field]):
            raise WorkflowArtifactError(f"convergence report {field} is invalid", code="report-schema")
    if report.get("status") not in {"pass", "block"}:
        raise WorkflowArtifactError("convergence report status is invalid", code="report-schema")
    coverage = report.get("coverage")
    if not isinstance(coverage, dict) or set(coverage) != {"required", "covered", "missing"}:
        raise WorkflowArtifactError("convergence report coverage is invalid", code="report-schema")
    for field in ("required", "covered", "missing"):
        _string_list(coverage[field], f"coverage.{field}", maximum_items=2_000, maximum_length=32)
    findings = report.get("findings")
    if not isinstance(findings, list) or len(findings) > 2_000:
        raise WorkflowArtifactError("convergence report findings are invalid", code="report-schema")
    finding_keys = {"finding_id", "code", "path", "message", "disposition", "blocking"}
    finding_ids: set[str] = set()
    for finding in findings:
        if not isinstance(finding, dict) or set(finding) != finding_keys:
            raise WorkflowArtifactError("convergence finding has an invalid closed shape", code="report-schema")
        finding_id = finding.get("finding_id")
        if (
            not isinstance(finding_id, str)
            or not re.fullmatch(r"FIND-[0-9a-f]{12}", finding_id)
            or finding_id in finding_ids
        ):
            raise WorkflowArtifactError("convergence finding identity is invalid", code="report-schema")
        finding_ids.add(finding_id)
        code = _bounded_text(finding.get("code"), "finding code", maximum=64)
        if not re.fullmatch(r"[a-z0-9-]+", code):
            raise WorkflowArtifactError("convergence finding code is invalid", code="report-schema")
        _bounded_text(finding.get("path"), "finding path", maximum=MAX_PATH_LENGTH)
        _bounded_text(finding.get("message"), "finding message", maximum=2_048)
        if (
            finding.get("disposition")
            not in {
                "accept-native",
                "revise-import",
                "refresh-evidence",
                "resolve-conflict",
            }
            or finding.get("blocking") is not True
        ):
            raise WorkflowArtifactError("convergence finding disposition is invalid", code="report-schema")
    return report


def _finding(code: str, path: str, message: str, disposition: str) -> dict[str, Any]:
    core = {"code": code, "path": path, "message": message, "disposition": disposition, "blocking": True}
    return {"finding_id": "FIND-" + hashlib.sha256(canonical_json(core)).hexdigest()[:12], **core}


def _explicit_claims(bundle: SourceBundle | None) -> list[dict[str, str]]:
    if bundle is None:
        return []
    claims: list[dict[str, str]] = []
    for source in bundle.sources:
        for line in source.content.splitlines():
            match = CLAIM_PATTERN.fullmatch(line)
            if not match:
                continue
            value = _strict_json(match.group(1).encode("utf-8"), limit=65_536)
            if (
                not isinstance(value, dict)
                or set(value) != {"kind", "id", "statement"}
                or value.get("kind") not in {"objective", "criterion", "architecture"}
                or not all(isinstance(value.get(key), str) and value[key] for key in ("id", "statement"))
            ):
                raise WorkflowArtifactError("AGB claim metadata is invalid", code="claim")
            claims.append(
                {
                    "kind": value["kind"],
                    "id": value["id"],
                    "statement": value["statement"],
                    "path": str(source.identity["path"]),
                }
            )
    return sorted(claims, key=lambda item: (item["kind"], item["id"], item["path"], item["statement"]))


def _native_task_statuses(root: Path, change_id: str) -> dict[str, str]:
    relative = f"engineering/changes/{change_id}/tasks.md"
    try:
        raw = _read_regular(root, relative, limit=MAX_SOURCE_BYTES)
    except WorkflowArtifactError as exc:
        if exc.code == "io":
            return {}
        raise
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise WorkflowArtifactError("native tasks projection is not UTF-8", code="unicode") from exc
    statuses: dict[str, str] = {}
    for line in text.splitlines():
        native_match = NATIVE_STATUS.match(line)
        if native_match:
            key = native_match.group(2).lower()
            status = "complete" if native_match.group(1).lower() == "x" else "pending"
            if key in statuses and statuses[key] != status:
                raise WorkflowArtifactError("native task status is duplicated", code="status")
            statuses[key] = status
            continue
        match = STATUS_PATTERN.fullmatch(line)
        if not match:
            continue
        value = _strict_json(match.group(1).encode("utf-8"), limit=65_536)
        if (
            not isinstance(value, dict)
            or set(value) != {"key", "status"}
            or not isinstance(value.get("key"), str)
            or value.get("status") not in SOURCE_STATUS_VALUES
            or value["key"] in statuses
        ):
            raise WorkflowArtifactError("native task status metadata is invalid", code="status")
        statuses[value["key"]] = value["status"]
    return statuses


def _architecture_id(root: Path) -> str | None:
    try:
        value = _strict_json(
            _read_regular(root, "architecture/system.yaml", limit=MAX_SOURCE_BYTES), limit=MAX_SOURCE_BYTES
        )
    except WorkflowArtifactError as exc:
        if exc.code == "io":
            return None
        raise
    return (
        str(value.get("architecture_id"))
        if isinstance(value, dict) and isinstance(value.get("architecture_id"), str)
        else None
    )


def effective_task_statuses(graph: dict[str, Any], receipt_errors: list[str]) -> list[dict[str, str]]:
    """Resolve ephemeral task state without persisting receipt authority in the graph."""
    validate_task_graph(graph)
    if (
        not isinstance(receipt_errors, list)
        or len(receipt_errors) > MAX_RECEIPT_ERRORS
        or any(not isinstance(item, str) or not item or len(item) > 512 for item in receipt_errors)
    ):
        raise WorkflowArtifactError("canonical receipt validation result is invalid", code="receipt")
    receipts_current = not receipt_errors
    return [
        {
            "task_id": str(task["task_id"]),
            "source_status": str(task["source_status"]),
            "effective_status": "verified" if task["source_status"] == "complete" and receipts_current else "pending",
        }
        for task in sorted(graph["tasks"], key=lambda item: item["task_id"])
    ]


def converge(
    root: Path,
    change_id: str,
    bundle: SourceBundle | None,
    graph: dict[str, Any],
    route: dict[str, Any],
    *,
    current_fingerprint: str,
    receipt_errors: list[str],
) -> dict[str, Any]:
    _writer, _reviewers, _required_evidence = _validate_route(route)
    validate_task_graph(graph)
    if not isinstance(current_fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", current_fingerprint):
        raise WorkflowArtifactError("trusted current fingerprint is invalid", code="fingerprint")
    if (
        not isinstance(receipt_errors, list)
        or len(receipt_errors) > MAX_RECEIPT_ERRORS
        or any(not isinstance(item, str) or not item or len(item) > 512 for item in receipt_errors)
    ):
        raise WorkflowArtifactError("canonical receipt validation result is invalid", code="receipt")
    native = _load_native_spec(root, change_id)
    findings: list[dict[str, Any]] = []
    required = sorted(
        str(item["id"])
        for group in ("acceptance_criteria", "invariants", "forbidden_outcomes")
        for item in native.get(group, [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    )
    covered = sorted({str(item) for task in graph.get("tasks", []) for item in task.get("covers", [])})
    missing = sorted(set(required) - set(covered))
    if graph.get("graph_digest") != digest_without(graph, "graph_digest"):
        findings.append(
            _finding(
                "stale-graph",
                "workflow/task-graph.json",
                "stored graph digest does not match its canonical content",
                "refresh-evidence",
            )
        )
    if bundle is not None and graph.get("source_manifest_digest") != bundle.manifest_digest:
        findings.append(
            _finding(
                "stale-source",
                "workflow/manifest.json",
                "source manifest digest differs from compiled graph",
                "refresh-evidence",
            )
        )
    if graph.get("write_agent") != route.get("write_agent") or sorted(graph.get("review_agents", [])) != sorted(
        route.get("review_agents", [])
    ):
        findings.append(
            _finding(
                "route-drift", "workflow/task-graph.json", "graph ownership differs from active route", "accept-native"
            )
        )
    if missing:
        findings.append(
            _finding(
                "incomplete-coverage",
                "change-spec.yaml",
                f"native criteria lack task coverage: {missing}",
                "revise-import",
            )
        )
    native_objective = native.get("objective") if isinstance(native.get("objective"), dict) else {}
    native_criteria = {
        str(item.get("id")): str(item.get("statement"))
        for item in native.get("acceptance_criteria", [])
        if isinstance(item, dict)
    }
    architecture_id = _architecture_id(root)
    for claim in _explicit_claims(bundle):
        if (
            claim["kind"] == "objective"
            and claim["id"] == native_objective.get("id")
            and claim["statement"] != native_objective.get("statement")
        ):
            findings.append(
                _finding(
                    "goal-conflict",
                    claim["path"],
                    f"imported objective {claim['id']} contradicts native objective",
                    "accept-native",
                )
            )
        elif (
            claim["kind"] == "criterion"
            and claim["id"] in native_criteria
            and claim["statement"] != native_criteria[claim["id"]]
        ):
            findings.append(
                _finding(
                    "criterion-conflict",
                    claim["path"],
                    f"imported criterion {claim['id']} contradicts native criterion",
                    "accept-native",
                )
            )
        elif claim["kind"] == "architecture" and architecture_id is not None and claim["id"] != architecture_id:
            findings.append(
                _finding(
                    "architecture-contradiction",
                    claim["path"],
                    f"imported architecture {claim['id']} differs from native {architecture_id}",
                    "accept-native",
                )
            )
    for group in ("objective", "acceptance_criteria", "invariants", "forbidden_outcomes"):
        values = [native.get(group)] if group == "objective" else native.get(group, [])
        for item in values:
            if isinstance(item, dict) and PLACEHOLDER.search(str(item.get("statement", ""))):
                findings.append(
                    _finding(
                        "placeholder",
                        "change-spec.yaml",
                        f"native {item.get('id', group)} contains a placeholder",
                        "accept-native",
                    )
                )
    native_statuses = _native_task_statuses(root, change_id)
    effective_task_statuses(graph, receipt_errors)
    for task in graph.get("tasks", []):
        if task.get("enrichment_required"):
            findings.append(
                _finding(
                    "needs-enrichment",
                    f"workflow/tasks/{task.get('task_id', 'unknown')}",
                    f"imported task lacks native details: {task['enrichment_required']}",
                    "revise-import",
                )
            )
        if task.get("key") in native_statuses and native_statuses[task["key"]] != task.get("source_status"):
            findings.append(
                _finding(
                    "status-drift",
                    f"engineering/changes/{change_id}/tasks.md",
                    f"task {task['key']} status differs between native projection and graph",
                    "accept-native",
                )
            )
    findings.sort(key=lambda item: (item["code"], item["path"], item["finding_id"]))
    report: dict[str, Any] = {
        "schema_version": 1,
        "change_id": change_id,
        "graph_digest": graph.get("graph_digest", ""),
        "source_manifest_digest": graph.get("source_manifest_digest", ""),
        "status": "block" if findings else "pass",
        "coverage": {"required": required, "covered": covered, "missing": missing},
        "findings": findings,
    }
    report["report_digest"] = digest_without(report, "report_digest")
    validate_convergence_report(report)
    return report


def workflow_paths(root: Path, change_id: str) -> dict[str, Path]:
    if not re.fullmatch(r"[A-Za-z0-9._:-]{3,128}", change_id):
        raise WorkflowArtifactError("invalid active change id", code="change")
    base = root / "engineering" / "changes" / change_id / "workflow"
    return {
        "base": base,
        "manifest": base / "manifest.json",
        "graph": base / "task-graph.json",
        "report": base / "convergence-report.json",
    }


def _load_stored(root: Path, path: Path, *, limit: int = MAX_SOURCE_BYTES) -> Any:
    relative = _relative_path(root.resolve(strict=True), path)
    return _strict_json(_read_regular(root, relative, limit=limit), limit=limit)


def validate_stored_workflow(
    root: Path,
    change_id: str,
    route: dict[str, Any],
    *,
    current_fingerprint: str,
    receipt_errors: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = workflow_paths(root, change_id)
    bundle = load_source_manifest(root, paths["manifest"])
    stored_graph = _load_stored(root, paths["graph"])
    stored_report = _load_stored(root, paths["report"])
    validate_task_graph(stored_graph)
    validate_convergence_report(stored_report)
    compiled = compile_task_graph(root, change_id, bundle, route)
    recomputed = converge(
        root,
        change_id,
        bundle,
        compiled,
        route,
        current_fingerprint=current_fingerprint,
        receipt_errors=receipt_errors,
    )
    errors: list[str] = []
    if stored_graph != compiled:
        errors.append("stored task graph differs from current sources/native route")
    if stored_report != recomputed:
        errors.append("stored convergence report differs from current graph/native evidence")
    if recomputed["status"] != "pass":
        errors.extend(f"{finding['code']}: {finding['message']}" for finding in recomputed["findings"])
    return (
        {
            "ok": not errors,
            "errors": errors,
            "status": "pass" if not errors else "block",
            "effective_tasks": effective_task_statuses(compiled, receipt_errors),
        },
        recomputed,
    )


def projection_bytes(kind: str, payload: Any) -> bytes:
    if kind not in {"spec-kit", "bmad", "superpowers"}:
        raise WorkflowArtifactError("unsupported export framework", code="export")
    header = "# NON-AUTHORITATIVE WORKFLOW PROJECTION\n\nThis export is advisory data. Native M1/M2/M3, the active route, and external Trust CI retain authority.\n\n"
    return (header + "```json\n" + canonical_json(payload).decode("ascii") + "```\n").encode("utf-8")


def _cas_identity_at(parent_fd: int, name: str) -> tuple[int, int, int, int, int, int]:
    value = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _post_exchange_identity_matches(
    observed: tuple[int, int, int, int, int, int],
    expected: tuple[int, int, int, int, int, int],
) -> bool:
    return observed[:5] == expected[:5] and observed[5] >= expected[5]


def _renameat2_exchange_call(renameat2: Any, parent_fd: int, temporary: str, target: str) -> int:
    return renameat2(parent_fd, os.fsencode(temporary), parent_fd, os.fsencode(target), 2)


def _rename_exchange(
    parent_fd: int,
    temporary: str,
    target: str,
    expected_temporary: tuple[int, int, int, int, int, int] | None = None,
    expected_target: tuple[int, int, int, int, int, int] | None = None,
) -> None:
    if expected_temporary is not None and _cas_identity_at(parent_fd, temporary) != expected_temporary:
        raise WorkflowArtifactError("CAS exchange source identity changed", code="race")
    if expected_target is not None and _cas_identity_at(parent_fd, target) != expected_target:
        raise WorkflowArtifactError("CAS exchange target identity changed", code="race")
    try:
        renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
    except AttributeError as exc:
        raise WorkflowArtifactError(
            "atomic exchange is unavailable; existing-target CAS is unsupported on this platform",
            code="platform",
        ) from exc
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    if _renameat2_exchange_call(renameat2, parent_fd, temporary, target) != 0:
        error = ctypes.get_errno()
        if error in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP}:
            raise WorkflowArtifactError(
                "atomic exchange is unavailable; existing-target CAS is unsupported on this platform",
                code="platform",
            )
        raise OSError(error, os.strerror(error))


def _rename_noreplace(parent_fd: int, source: str, target: str, target_parent_fd: int | None = None) -> None:
    try:
        renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
    except AttributeError as exc:
        raise WorkflowArtifactError("no-clobber recovery rename is unavailable", code="platform") from exc
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    destination_fd = parent_fd if target_parent_fd is None else target_parent_fd
    if renameat2(parent_fd, os.fsencode(source), destination_fd, os.fsencode(target), 1) != 0:
        error = ctypes.get_errno()
        if error == errno.EEXIST:
            raise FileExistsError(error, os.strerror(error), target)
        if error in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP}:
            raise WorkflowArtifactError("no-clobber recovery rename is unavailable", code="platform")
        raise OSError(error, os.strerror(error))


def _acquire_cas_lock(root: Path, change_id: str, relative_target: str) -> tuple[int, int]:
    _, root_fd = _open_root(root)
    directory_fd = root_fd
    lock_fd: int | None = None
    flags_dir = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        for component in (".grok-stack", "runtime", "workflow-cas", change_id):
            try:
                os.mkdir(component, mode=0o700, dir_fd=directory_fd)
            except FileExistsError:
                pass
            next_fd = os.open(component, flags_dir, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        lock_name = hashlib.sha256(relative_target.encode("utf-8")).hexdigest() + ".lock"
        lock_fd = os.open(
            lock_name,
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
            0o600,
            dir_fd=directory_fd,
        )
        before = os.fstat(lock_fd)
        if not stat.S_ISREG(before.st_mode):
            raise WorkflowArtifactError("CAS lock is not a regular file", code="cas")
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        current = os.stat(lock_name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            current.st_dev,
            current.st_ino,
            current.st_mode,
            current.st_size,
            current.st_mtime_ns,
            current.st_ctime_ns,
        ):
            raise WorkflowArtifactError("CAS lock identity changed", code="race")
        result = (lock_fd, os.dup(directory_fd))
        lock_fd = None
        return result
    except WorkflowArtifactError:
        raise
    except OSError as exc:
        raise WorkflowArtifactError("CAS lock acquisition failed", code="io") from exc
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        os.close(directory_fd)


def cas_write(root: Path, change_id: str, relative_target: str, data: bytes, expected_digest: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
        raise WorkflowArtifactError("expected digest must be lowercase SHA-256", code="cas")
    if len(data) > MAX_SOURCE_BYTES:
        raise WorkflowArtifactError("CAS payload exceeds byte limit", code="limit")
    workflow_paths(root, change_id)
    target_path = PurePosixPath(relative_target)
    target_parts = target_path.parts
    if (
        not target_parts
        or len(target_parts) > 8
        or any(part in {"", ".", ".."} for part in target_parts)
        or len(relative_target) > 512
        or unicodedata.normalize("NFC", relative_target) != relative_target
    ):
        raise WorkflowArtifactError("invalid workflow write target", code="path")
    direct = relative_target in {"task-graph.json", "convergence-report.json"}
    projected = len(target_parts) >= 2 and target_parts[0] in {"projections", "exports"}
    if not direct and not projected:
        raise WorkflowArtifactError("workflow write target is not allowlisted", code="path")
    if direct:
        derived = _strict_json(data, limit=MAX_SOURCE_BYTES)
        if relative_target == "task-graph.json":
            validate_task_graph(derived)
        else:
            validate_convergence_report(derived)
        if canonical_json(derived) != data:
            raise WorkflowArtifactError("derived workflow artifact is not canonical JSON", code="cas")

    lock_fd, recovery_dir_fd = _acquire_cas_lock(root, change_id, relative_target)
    _, root_fd = _open_root(root)
    directory_fd = root_fd
    parent_fd: int | None = None
    descriptor: int | None = None
    recovery_token = hashlib.sha256(
        f"{relative_target}\0{os.getpid()}\0{threading.get_ident()}\0{next(_CAS_RECOVERY_SEQUENCE)}".encode()
    ).hexdigest()[:24]
    temporary = f".agb-stage-{recovery_token}"
    recovery = f".agb-recovery-{recovery_token}"
    temporary_exists = False
    temporary_identity: tuple[int, int, int, int, int, int] | None = None
    flags_dir = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    flags_file = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK

    def entry_identity(fd: int, name: str) -> tuple[int, int, int, int, int, int]:
        return _cas_identity_at(fd, name)

    def digest_target(fd: int, name: str) -> tuple[str, tuple[int, int, int, int, int, int]]:
        source_fd: int | None = None
        try:
            source_fd = os.open(name, flags_file, dir_fd=fd)
            before = os.fstat(source_fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_SOURCE_BYTES:
                raise WorkflowArtifactError("CAS target is not a bounded regular file", code="cas")
            digest = hashlib.sha256()
            remaining = MAX_SOURCE_BYTES + 1
            while remaining:
                chunk = os.read(source_fd, min(65_536, remaining))
                if not chunk:
                    break
                digest.update(chunk)
                remaining -= len(chunk)
            after = os.fstat(source_fd)
            before_identity = (
                before.st_dev,
                before.st_ino,
                before.st_mode,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            )
            after_identity = (
                after.st_dev,
                after.st_ino,
                after.st_mode,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            )
            if before.st_size > MAX_SOURCE_BYTES or before_identity != after_identity:
                raise WorkflowArtifactError("CAS target changed while reading", code="race")
            return digest.hexdigest(), after_identity
        finally:
            if source_fd is not None:
                os.close(source_fd)

    def preserve_temporary() -> str | None:
        nonlocal temporary_exists
        if not temporary_exists or parent_fd is None:
            return None
        try:
            _rename_noreplace(parent_fd, temporary, recovery, recovery_dir_fd)
        except FileNotFoundError:
            artifact = None
        except (FileExistsError, OSError, WorkflowArtifactError):
            artifact = temporary
        else:
            artifact = recovery
        temporary_exists = False
        return artifact

    try:
        for component in ("engineering", "changes", change_id, "workflow"):
            next_fd = os.open(component, flags_dir, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        for component in target_parts[:-1]:
            try:
                os.mkdir(component, mode=0o700, dir_fd=directory_fd)
            except FileExistsError:
                pass
            next_fd = os.open(component, flags_dir, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        parent_fd = directory_fd
        directory_fd = -1

        try:
            current, current_identity = digest_target(parent_fd, target_parts[-1])
        except FileNotFoundError:
            current = "0" * 64
            current_identity = None
        if current != expected_digest:
            raise WorkflowArtifactError("CAS expected digest mismatch", code="cas")

        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=parent_fd,
        )
        temporary_exists = True
        offset = 0
        while offset < len(data):
            offset += os.write(descriptor, data[offset:])
        os.fsync(descriptor)
        temporary_stat = os.fstat(descriptor)
        temporary_identity = (
            temporary_stat.st_dev,
            temporary_stat.st_ino,
            temporary_stat.st_mode,
            temporary_stat.st_size,
            temporary_stat.st_mtime_ns,
            temporary_stat.st_ctime_ns,
        )
        os.close(descriptor)
        descriptor = None
        if current_identity is None:
            try:
                os.link(
                    temporary,
                    target_parts[-1],
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                    follow_symlinks=False,
                )
            except FileExistsError as exc:
                raise WorkflowArtifactError("CAS target appeared before publication", code="race") from exc
            preserve_temporary()
        else:
            _rename_exchange(parent_fd, temporary, target_parts[-1], temporary_identity, current_identity)
            displaced_identity = None
            published_identity = None
            try:
                displaced_identity = entry_identity(parent_fd, temporary)
                published_identity = entry_identity(parent_fd, target_parts[-1])
                identities_valid = _post_exchange_identity_matches(
                    displaced_identity, current_identity
                ) and _post_exchange_identity_matches(published_identity, temporary_identity)
                displaced_digest = None
                if identities_valid:
                    displaced_digest, hashed_displaced_identity = digest_target(parent_fd, temporary)
                    identities_valid = _post_exchange_identity_matches(
                        hashed_displaced_identity, displaced_identity
                    )
                publication_valid = identities_valid and displaced_digest == expected_digest
            except (OSError, WorkflowArtifactError):
                publication_valid = False
            if not publication_valid:
                rollback_error: BaseException | None = None
                try:
                    _rename_exchange(
                        parent_fd,
                        temporary,
                        target_parts[-1],
                        displaced_identity,
                        published_identity,
                    )
                except Exception as exc:  # preserve entries even when platform rollback fails
                    rollback_error = exc
                if rollback_error is None:
                    try:
                        restored_identity = entry_identity(parent_fd, target_parts[-1])
                    except OSError:
                        restored_identity = None
                    try:
                        rollback_temp_identity = entry_identity(parent_fd, temporary)
                    except OSError:
                        rollback_temp_identity = None
                    recovery_artifact = preserve_temporary()
                    restored_changed = displaced_identity is not None and (
                        restored_identity is None
                        or not _post_exchange_identity_matches(restored_identity, displaced_identity)
                    )
                    rollback_temp_changed = published_identity is not None and (
                        rollback_temp_identity is None
                        or not _post_exchange_identity_matches(rollback_temp_identity, published_identity)
                    )
                    if restored_changed or rollback_temp_changed:
                        raise WorkflowArtifactError(
                            f"CAS rollback raced; competing entries were preserved for forward recovery at {recovery_artifact}",
                            code="race",
                        )
                    raise WorkflowArtifactError(
                        f"CAS target changed before atomic publication and was restored; recovery={recovery_artifact}",
                        code="race",
                    )
                recovery_artifact = preserve_temporary()
                raise WorkflowArtifactError(
                    f"CAS rollback failed closed with entries preserved at {recovery_artifact}: {rollback_error}",
                    code="race",
                )
            preserve_temporary()
        os.fsync(parent_fd)
    except WorkflowArtifactError:
        raise
    except OSError as exc:
        raise WorkflowArtifactError("CAS publication failed", code="io") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory_fd >= 0:
            os.close(directory_fd)
        if parent_fd is not None:
            if temporary_exists:
                preserve_temporary()
            os.close(parent_fd)
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
        os.close(recovery_dir_fd)
    return hashlib.sha256(data).hexdigest()
