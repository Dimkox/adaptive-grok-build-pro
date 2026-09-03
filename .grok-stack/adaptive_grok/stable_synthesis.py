from __future__ import annotations

import hashlib
import fcntl
import json
import math
import os
import re
import secrets
import stat
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

WEEK_SECONDS = 604800
MAX_ITERATIONS = 8
MAX_JOURNAL_ENTRIES = 10000
MAX_SUBJECT = 160
MAX_INTENT_BYTES = 1048576
MAX_REQUIREMENTS = 128
MAX_TASKS = 256
MAX_TASK_LINKS = 64
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")
TAG_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
JOURNAL_RECORD_FIELDS = frozenset({"recorded_at", "kind", "component_digest", "config_digest", "intent_digest", "snapshot_digest"})
JOURNAL_ENTRY_FIELDS = JOURNAL_RECORD_FIELDS | {"sequence", "prior_digest", "digest"}
STATE_ROOT_FIELDS = frozenset({"schema_version", "last_attempt_epoch", "next_due_epoch", "overall_status", "sources", "errors", "component_digest", "config_digest", "journal_digest", "snapshot_digest"})
STATE_PAYLOAD_FIELDS = STATE_ROOT_FIELDS - {"journal_digest", "snapshot_digest"}
SUCCESS_SOURCE_FIELDS = frozenset({"status", "release_tag", "tag_object_sha", "release_commit_sha", "release_changed", "head_sha", "compare_base_sha", "compare_head_sha", "merge_base_sha", "compare_status", "ahead_by", "behind_by", "available_count", "candidates", "truncated", "partial", "issue", "release_etag", "cached_release", "last_success_epoch"})
FAILURE_SOURCE_FIELDS = frozenset({"status", "error", "last_success_epoch"})
SOURCE_IDS = ("bmad_method", "spec_kit", "superpowers")
ALLOWED_REPOS = ("bmad-code-org/BMAD-METHOD", "github/spec-kit", "obra/superpowers")
PIN_AUTHORITY = {
    "bmad_method": ("bmad-code-org/BMAD-METHOD", "v6.11.0", "178414679b11a171ca1597b0ebc1723ed488fc73", "9ce3c397c9b238de96f7365da8019f6f66b059da", "BMad Code LLC (2025)"),
    "spec_kit": ("github/spec-kit", "v1.0.4", "98d9fe5010aa7d857264e19d439782e186bf641a", "cb610277fdea781fcfa83d20522c2db37c94068d", "GitHub Inc. (2025)"),
    "superpowers": ("obra/superpowers", "v6.3.0", "86babb696875227929e85420f287d6309374b93f", "b36e0829c6d0140e93cfef2ca599b1b07d4a7797", "Jesse Vincent (2025)"),
}
TERMINAL_STATES = frozenset({"ready", "blocked", "needs_human", "iteration_limit"})
TRANSITIONS = {
    "pending": frozenset({"analyzing", "blocked"}),
    "analyzing": frozenset({"repair_planned", "ready", "blocked", "needs_human"}),
    "repair_planned": frozenset({"analyzing", "ready", "blocked", "needs_human", "iteration_limit"}),
}


class SynthesisError(RuntimeError):
    pass


class TransportError(SynthesisError):
    pass


@dataclass(frozen=True)
class Upstream:
    id: str
    repository: str
    repository_url: str
    stable_tag: str
    tag_object_sha: str
    peeled_commit_sha: str
    release_url: str
    commit_url: str
    license: str
    license_holder: str
    license_url: str


@dataclass(frozen=True)
class Finding:
    id: str
    category: str
    subject: str
    detail: str


@dataclass(frozen=True)
class Repair:
    finding_id: str
    action: str
    target: str


@dataclass(frozen=True)
class SynthesisResult:
    schema_version: int
    state: str
    iterations: int
    intent_digest: str
    tasks: tuple[dict[str, Any], ...]
    findings: tuple[Finding, ...]
    repair_plan: tuple[Repair, ...]
    digest: str


@dataclass(frozen=True)
class IntentRequirement:
    id: str
    statement: str


@dataclass(frozen=True)
class PlannedTask:
    id: str
    requirement_ids: tuple[str, ...]
    state: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class HttpRequest:
    method: str
    url: str
    headers: tuple[tuple[str, str], ...]
    timeout_seconds: float = 10
    deadline_monotonic: float | None = None
    max_body_bytes: int = 1048576


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _strict_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SynthesisError("duplicate JSON key")
        result[key] = value
    return result


def strict_json(raw: bytes, max_bytes: int) -> Any:
    if len(raw) > max_bytes:
        raise SynthesisError("response body exceeds configured bound")
    try:
        text = raw.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=_strict_object_pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(SynthesisError("non-finite JSON number")),
            parse_int=_bounded_json_int,
            parse_float=_bounded_json_float,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError, OverflowError) as exc:
        raise SynthesisError("response is not strict UTF-8 JSON") from exc


def _bounded_json_int(value: str) -> int:
    if len(value) > 32:
        raise SynthesisError("JSON number is outside bounded syntax")
    parsed = int(value)
    if abs(parsed) > 9007199254740991:
        raise SynthesisError("JSON number is outside bounded syntax")
    return parsed


def _bounded_json_float(value: str) -> float:
    if len(value) > 64:
        raise SynthesisError("JSON number is outside bounded syntax")
    parsed = float(value)
    if not math.isfinite(parsed) or abs(parsed) > 9007199254740991:
        raise SynthesisError("JSON number is outside bounded syntax")
    return parsed


def load_upstreams(root: Path) -> tuple[Upstream, ...]:
    path = root / "engineering/stable-synthesis/stable-synthesis-upstreams.v1.json"
    raw = strict_json(_read_regular_bytes(path, 128 * 1024), 128 * 1024)
    expected_top = {"schema_version", "interval_seconds", "request_timeout_seconds", "run_timeout_seconds", "max_body_bytes", "max_candidates_per_source", "sources"}
    if not isinstance(raw, dict) or set(raw) != expected_top or raw["schema_version"] != 1:
        raise SynthesisError("upstream contract is not closed v1")
    if raw["interval_seconds"] != WEEK_SECONDS or raw["request_timeout_seconds"] != 10 or raw["run_timeout_seconds"] != 90:
        raise SynthesisError("upstream timing contract changed")
    for key, low, high in (("max_body_bytes", 1024, 1048576), ("max_candidates_per_source", 1, 100)):
        value = raw[key]
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise SynthesisError(f"{key} is outside closed bounds")
    sources = raw.get("sources")
    if not isinstance(sources, list) or len(sources) != 3:
        raise SynthesisError("exactly three sources are required")
    fields = set(Upstream.__dataclass_fields__)
    parsed: list[Upstream] = []
    for item in sources:
        if not isinstance(item, dict) or set(item) != fields or not all(isinstance(v, str) for v in item.values()):
            raise SynthesisError("source record is not closed")
        source = Upstream(**item)
        if not SHA40.fullmatch(source.tag_object_sha) or not SHA40.fullmatch(source.peeled_commit_sha):
            raise SynthesisError("pin SHA must be lowercase 40-hex")
        if source.license != "MIT" or source.repository not in ALLOWED_REPOS:
            raise SynthesisError("source authority is outside closed allowlist")
        repository, tag, tag_object, peeled, holder = PIN_AUTHORITY.get(source.id, (None,) * 5)
        expected = {
            "repository": repository,
            "repository_url": f"https://github.com/{repository}",
            "stable_tag": tag,
            "tag_object_sha": tag_object,
            "peeled_commit_sha": peeled,
            "release_url": f"https://github.com/{repository}/releases/tag/{tag}",
            "commit_url": f"https://github.com/{repository}/commit/{peeled}",
            "license": "MIT",
            "license_holder": holder,
            "license_url": f"https://github.com/{repository}/blob/{peeled}/LICENSE",
        }
        actual = asdict(source)
        actual.pop("id")
        if actual != expected:
            raise SynthesisError(f"source authority mismatch: {source.id}")
        parsed.append(source)
    if tuple(s.id for s in parsed) != SOURCE_IDS or tuple(s.repository for s in parsed) != ALLOWED_REPOS:
        raise SynthesisError("sources must be unique and canonically ordered")
    return tuple(parsed)


def _task_id(intent_digest: str, name: str) -> str:
    return "ST-" + hashlib.sha256(f"{intent_digest}:{name}".encode()).hexdigest()[:12]


def validate_dag(tasks: Iterable[dict[str, Any]]) -> None:
    materialized = list(tasks)
    ids = {task.get("id") for task in materialized}
    if len(ids) != len(materialized) or None in ids:
        raise SynthesisError("task IDs must be unique")
    visiting: set[str] = set()
    visited: set[str] = set()
    by_id = {str(t["id"]): t for t in materialized}

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise SynthesisError("task DAG contains a cycle")
        if task_id in visited:
            return
        visiting.add(task_id)
        deps = by_id[task_id].get("depends_on", [])
        if not isinstance(deps, list) or any(dep not in by_id for dep in deps):
            raise SynthesisError("task DAG has missing dependency")
        for dep in deps:
            visit(dep)
        visiting.remove(task_id)
        visited.add(task_id)

    for key in sorted(by_id):
        visit(key)


def transition(current: str, target: str) -> str:
    if target not in TRANSITIONS.get(current, frozenset()):
        raise SynthesisError(f"invalid state transition: {current}->{target}")
    return target


def analyze_traceability(requirements: Iterable[IntentRequirement], tasks: Iterable[PlannedTask]) -> tuple[Finding, ...]:
    reqs = {item.id: item for item in requirements}
    materialized = tuple(tasks)
    findings: list[Finding] = []
    referenced = {req for task in materialized for req in task.requirement_ids}
    for req_id in sorted(reqs):
        if req_id not in referenced:
            findings.append(Finding(f"F-MISSING-{req_id}", "missing", req_id, "requirement has no planned task"))
    for task in sorted(materialized, key=lambda item: item.id):
        unknown = sorted(set(task.requirement_ids) - set(reqs))
        if unknown or not task.requirement_ids:
            findings.append(Finding(f"F-UNREQUESTED-{task.id}", "unrequested", task.id, "task is not traced to requested intent"))
        if task.state == "ready" and not task.evidence:
            findings.append(Finding(f"F-CONTRADICTS-{task.id}", "contradicts", task.id, "ready task has no evidence"))
        elif task.state != "ready":
            findings.append(Finding(f"F-PARTIAL-{task.id}", "partial", task.id, "task is not terminal"))
    return tuple(sorted(findings, key=lambda item: (item.category, item.id)))


def synthesize(intent: dict[str, Any], *, iterations: int = 1) -> SynthesisResult:
    if not isinstance(intent, dict) or not intent or iterations < 1 or iterations > MAX_ITERATIONS:
        raise SynthesisError("intent and iteration bound are required")
    try:
        intent_bytes = canonical_bytes(intent)
    except (TypeError, ValueError) as exc:
        raise SynthesisError("intent is invalid") from exc
    if len(intent_bytes) > MAX_INTENT_BYTES:
        raise SynthesisError("intent is too large")
    intent_digest = hashlib.sha256(intent_bytes).hexdigest()
    raw_requirements = intent.get("requirements")
    if raw_requirements is None:
        raw_requirements = [{"id": "INTENT", "statement": str(intent.get("intent", "local synthesis"))}]
    if (
        not isinstance(raw_requirements, list)
        or not raw_requirements
        or len(raw_requirements) > MAX_REQUIREMENTS
        or any(
            not isinstance(item, dict)
            or set(item) != {"id", "statement"}
            or not isinstance(item["id"], str)
            or not re.fullmatch(r"[A-Z][A-Z0-9_-]{0,31}", item["id"])
            or not isinstance(item["statement"], str)
            or not 1 <= len(item["statement"]) <= 512
            for item in raw_requirements
        )
    ):
        raise SynthesisError("requirements are not closed typed records")
    requirements = tuple(IntentRequirement(item["id"], item["statement"]) for item in raw_requirements)
    if len({item.id for item in requirements}) != len(requirements):
        raise SynthesisError("requirement IDs must be unique")
    raw_tasks = intent.get("tasks")
    if raw_tasks is None:
        names = ("pins-contract", "static-analysis", "monitor-review", "readiness")
        raw_tasks = [
            {
                "id": _task_id(intent_digest, name),
                "name": name,
                "state": "pending",
                "depends_on": [] if index == 0 else [_task_id(intent_digest, names[index - 1])],
                "requirement_ids": [requirements[min(index, len(requirements) - 1)].id],
                "evidence": [],
            }
            for index, name in enumerate(names)
        ]
    if not isinstance(raw_tasks, list) or not raw_tasks or len(raw_tasks) > MAX_TASKS:
        raise SynthesisError("tasks are not closed typed records")
    tasks: list[dict[str, Any]] = []
    planned: list[PlannedTask] = []
    for item in raw_tasks:
        if not isinstance(item, dict) or set(item) != {"id", "name", "state", "depends_on", "requirement_ids", "evidence"}:
            raise SynthesisError("tasks are not closed typed records")
        if (
            not all(isinstance(item[key], str) for key in ("id", "name", "state"))
            or re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,63}", item["id"]) is None
            or not 1 <= len(item["name"]) <= 128
        ):
            raise SynthesisError("task identity is invalid")
        if item["state"] not in {"pending", "analyzing", "repair_planned", "ready", "blocked", "needs_human", "iteration_limit"}:
            raise SynthesisError("task state is invalid")
        if (
            not isinstance(item["depends_on"], list)
            or len(item["depends_on"]) > MAX_TASK_LINKS
            or not all(isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,63}", value) for value in item["depends_on"])
        ):
            raise SynthesisError("task dependencies are invalid")
        if (
            not isinstance(item["requirement_ids"], list)
            or len(item["requirement_ids"]) > MAX_TASK_LINKS
            or not all(isinstance(value, str) and re.fullmatch(r"[A-Z][A-Z0-9_-]{0,31}", value) for value in item["requirement_ids"])
        ):
            raise SynthesisError("task traceability is invalid")
        if (
            not isinstance(item["evidence"], list)
            or len(item["evidence"]) > MAX_TASK_LINKS
            or not all(isinstance(value, str) and 1 <= len(value) <= 256 for value in item["evidence"])
        ):
            raise SynthesisError("task evidence is invalid")
        normalized = {key: item[key] for key in ("id", "name", "state", "depends_on", "requirement_ids", "evidence")}
        normalized["depends_on"] = sorted(set(normalized["depends_on"]))
        normalized["requirement_ids"] = sorted(set(normalized["requirement_ids"]))
        normalized["evidence"] = sorted(set(normalized["evidence"]))
        tasks.append(normalized)
        planned.append(PlannedTask(item["id"], tuple(normalized["requirement_ids"]), item["state"], tuple(normalized["evidence"])))
    tasks.sort(key=lambda item: item["id"])
    validate_dag(tasks)
    findings: list[Finding] = list(analyze_traceability(requirements, planned))
    for key in sorted(intent):
        if intent[key] in (None, "", [], {}):
            findings.append(Finding("F-" + hashlib.sha256(f"missing:{key}".encode()).hexdigest()[:12], "missing", key, "required intent field is empty"))
    categories = {finding.category for finding in findings}
    if not findings and all(task["state"] == "ready" for task in tasks):
        state = "ready"
    elif categories and categories <= {"partial"}:
        state = "needs_human"
    else:
        state = "blocked"
    repairs = tuple(Repair(f.id, "supply_reviewed_value", f.subject) for f in findings)
    performed_iterations = 1
    payload = {"schema_version": 1, "state": state, "iterations": performed_iterations, "intent_digest": intent_digest, "tasks": tasks, "findings": [asdict(x) for x in findings], "repair_plan": [asdict(x) for x in repairs]}
    return SynthesisResult(1, state, performed_iterations, intent_digest, tuple(tasks), tuple(findings), repairs, digest(payload))


def snapshot(value: Any) -> dict[str, Any]:
    body = canonical_bytes(value)
    return {"schema_version": 1, "digest": hashlib.sha256(body).hexdigest(), "content": json.loads(body)}


def verify_snapshot(value: dict[str, Any]) -> None:
    if set(value) != {"schema_version", "digest", "content"} or value.get("schema_version") != 1 or digest(value.get("content")) != value.get("digest"):
        raise SynthesisError("snapshot digest mismatch")


def _directory_fd(path: Path) -> int:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise SynthesisError("runtime path is unsafe") from exc
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise SynthesisError("runtime path is unsafe")
    return descriptor


def _read_regular_bytes(path: Path, max_bytes: int) -> bytes:
    parent = _directory_fd(path.parent)
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent)
    except OSError as exc:
        os.close(parent)
        raise SynthesisError("runtime file is unsafe") from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
            raise SynthesisError("runtime file is unsafe")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65536, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise SynthesisError("runtime file is unsafe")
        return b"".join(chunks)
    finally:
        os.close(descriptor)
        os.close(parent)


def _atomic_write_safe(path: Path, text: str) -> None:
    parent = _directory_fd(path.parent)
    temporary = f".{path.name}.{secrets.token_hex(8)}"
    descriptor: int | None = None
    try:
        try:
            current = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            current = None
        if current is not None and not stat.S_ISREG(current.st_mode):
            raise SynthesisError("runtime target is unsafe")
        descriptor = os.open(
            temporary,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=parent,
        )
        payload = text.encode("utf-8")
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent)
        os.fsync(parent)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=parent)
        except FileNotFoundError:
            pass
        os.close(parent)


def _runtime_fd(root: Path, *, snapshots: bool = False) -> int:
    resolved = root.resolve(strict=True)
    current = os.open(resolved, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        components = [".grok-stack", "runtime", "stable-synthesis"]
        if snapshots:
            components.append("snapshots")
        for component in components:
            try:
                following = os.open(
                    component,
                    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=current,
                )
            except FileNotFoundError:
                os.mkdir(component, 0o700, dir_fd=current)
                os.fsync(current)
                following = os.open(
                    component,
                    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=current,
                )
            os.close(current)
            current = following
        return current
    except OSError as exc:
        os.close(current)
        raise SynthesisError("runtime path is unsafe") from exc
    except BaseException:
        os.close(current)
        raise


def _runtime_read(root: Path, name: str, max_bytes: int, *, snapshots: bool = False) -> bytes:
    parent = _runtime_fd(root, snapshots=snapshots)
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent)
    except OSError as exc:
        os.close(parent)
        raise SynthesisError("runtime file is unsafe") from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
            raise SynthesisError("runtime file is unsafe")
        payload = bytearray()
        while len(payload) <= max_bytes:
            chunk = os.read(descriptor, min(65536, max_bytes + 1 - len(payload)))
            if not chunk:
                return bytes(payload)
            payload.extend(chunk)
        raise SynthesisError("runtime file is unsafe")
    finally:
        os.close(descriptor)
        os.close(parent)


def _runtime_write(root: Path, name: str, text: str, *, snapshots: bool = False) -> None:
    parent = _runtime_fd(root, snapshots=snapshots)
    temporary = f".{name}.{secrets.token_hex(8)}"
    descriptor: int | None = None
    try:
        try:
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            current = None
        if current is not None and not stat.S_ISREG(current.st_mode):
            raise SynthesisError("runtime target is unsafe")
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=parent)
        payload = text.encode("utf-8")
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
        os.fsync(parent)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=parent)
        except FileNotFoundError:
            pass
        os.close(parent)


@contextmanager
def _control_lock(root: Path, timeout: float = 5.0):
    parent = _runtime_fd(root)
    deadline = time.monotonic() + timeout
    try:
        descriptor = os.open(".control.lock", os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=parent)
    except OSError as exc:
        os.close(parent)
        raise SynthesisError("monitor lock is unsafe") from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise SynthesisError("monitor lock is unsafe")
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("stable synthesis is busy")
                time.sleep(0.05)
        yield
    finally:
        os.close(descriptor)
        os.close(parent)


class Journal:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.path = self.root / ".grok-stack/runtime/stable-synthesis/journal.jsonl"

    def read(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        parent = _runtime_fd(self.root)
        try:
            descriptor = os.open("journal.jsonl", os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent)
        except FileNotFoundError:
            os.close(parent)
            return []
        except OSError as exc:
            os.close(parent)
            raise SynthesisError("journal path is unsafe") from exc
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise SynthesisError("journal path is unsafe")
            with os.fdopen(descriptor, "r", encoding="utf-8", errors="strict") as handle:
                descriptor = -1
                for _ in range(MAX_JOURNAL_ENTRIES + 1):
                    line = handle.readline(128 * 1024 + 1)
                    if not line:
                        break
                    if len(line.encode("utf-8")) > 128 * 1024:
                        raise SynthesisError("journal line bound exceeded")
                    entries.append(strict_json(line.encode(), 128 * 1024))
        except (OSError, UnicodeError) as exc:
            raise SynthesisError("journal path is unsafe") from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            os.close(parent)
        if len(entries) > MAX_JOURNAL_ENTRIES:
            raise SynthesisError("journal replay bound exceeded")
        prior = "0" * 64
        for sequence, entry in enumerate(entries, 1):
            _validate_journal_entry(entry)
            recorded = dict(entry)
            actual = recorded.pop("digest", None)
            if entry.get("sequence") != sequence or entry.get("prior_digest") != prior or digest(recorded) != actual:
                raise SynthesisError("journal chain is corrupt")
            prior = str(actual)
        return entries

    def append(self, record: dict[str, Any], expected_prior: str) -> dict[str, Any]:
        with _control_lock(self.root):
            return self._append_unlocked(record, expected_prior)

    def _append_unlocked(self, record: dict[str, Any], expected_prior: str) -> dict[str, Any]:
        if set(record) != JOURNAL_RECORD_FIELDS:
            raise SynthesisError("journal record is not closed v1")
        provisional = {"sequence": 1, "prior_digest": "0" * 64, **record, "digest": "0" * 64}
        _validate_journal_entry(provisional, validate_digest=False)
        entries = self.read()
        prior = entries[-1]["digest"] if entries else "0" * 64
        if prior != expected_prior or len(entries) >= MAX_JOURNAL_ENTRIES:
            raise SynthesisError("journal compare-and-swap failed")
        item = {"sequence": len(entries) + 1, "prior_digest": prior, **record}
        item["digest"] = digest(item)
        text = "".join(json.dumps(x, sort_keys=True, separators=(",", ":")) + "\n" for x in [*entries, item])
        _runtime_write(self.root, "journal.jsonl", text)
        return item


def _validate_journal_entry(entry: Any, *, validate_digest: bool = True) -> None:
    if not isinstance(entry, dict) or set(entry) != JOURNAL_ENTRY_FIELDS:
        raise SynthesisError("journal entry is not closed v1")
    if isinstance(entry["sequence"], bool) or not isinstance(entry["sequence"], int) or entry["sequence"] < 1:
        raise SynthesisError("journal sequence is invalid")
    recorded_at = entry["recorded_at"]
    if (
        isinstance(recorded_at, bool)
        or not isinstance(recorded_at, (int, float))
        or recorded_at < 0
        or recorded_at > 9007199254740991
        or not math.isfinite(recorded_at)
    ):
        raise SynthesisError("journal timestamp is invalid")
    if not isinstance(entry["kind"], str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", entry["kind"]):
        raise SynthesisError("journal kind is invalid")
    for field in ("component_digest", "config_digest", "intent_digest", "snapshot_digest", "prior_digest"):
        if not isinstance(entry[field], str) or not SHA64.fullmatch(entry[field]):
            raise SynthesisError(f"journal {field} is invalid")
    if validate_digest and (not isinstance(entry["digest"], str) or not SHA64.fullmatch(entry["digest"])):
        raise SynthesisError("journal digest is invalid")


def write_snapshot(root: Path, value: Any) -> Path:
    item = snapshot(value)
    directory = _state_dir(root) / "snapshots"
    descriptor = _runtime_fd(root, snapshots=True)
    os.close(descriptor)
    path = directory / f"{item['digest']}.json"
    parent = _runtime_fd(root, snapshots=True)
    try:
        try:
            existing = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None and not stat.S_ISREG(existing.st_mode):
            raise SynthesisError("snapshot target is unsafe")
    finally:
        os.close(parent)
    if existing is not None:
        verify_snapshot(strict_json(_runtime_read(root, path.name, 1048576, snapshots=True), 1048576))
    else:
        _runtime_write(root, path.name, json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", snapshots=True)
    return path


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


class GitHubTransport:
    def __init__(self) -> None:
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.method != "GET":
            raise TransportError("only GET is supported")
        self._validate_request(request)
        deadline = request.deadline_monotonic
        if deadline is not None and time.monotonic() >= deadline:
            raise TransportError("run_timeout")
        req = urllib.request.Request(request.url, method="GET", headers=dict(request.headers))
        try:
            remaining = request.timeout_seconds if deadline is None else min(request.timeout_seconds, deadline - time.monotonic())
            if remaining <= 0:
                raise TransportError("run_timeout")
            with self._opener.open(req, timeout=remaining) as response:
                return HttpResponse(response.status, dict(response.headers.items()), self._read_body(response, request))
        except urllib.error.HTTPError as exc:
            return HttpResponse(exc.code, dict(exc.headers.items()), self._read_body(exc, request))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TransportError("GitHub request failed") from exc

    @staticmethod
    def _validate_request(request: HttpRequest) -> None:
        if not isinstance(request.url, str) or len(request.url) > 512 or len(request.headers) > 4:
            raise TransportError("request_target_forbidden")
        if any(
            not isinstance(name, str)
            or not isinstance(value, str)
            or len(name) > 128
            or len(value) > 512
            or any(unicodedata.category(char).startswith("C") for char in name + value)
            for name, value in request.headers
        ):
            raise TransportError("request_headers_forbidden")
        parsed = urllib.parse.urlsplit(request.url)
        if parsed.scheme != "https" or parsed.netloc != "api.github.com" or parsed.fragment:
            raise TransportError("request_target_forbidden")
        prefix = next((f"/repos/{repo}" for repo in ALLOWED_REPOS if parsed.path.startswith(f"/repos/{repo}/")), None)
        if prefix is None:
            raise TransportError("request_target_forbidden")
        suffix = parsed.path[len(prefix):]
        simple = suffix in {"/releases/latest", "/commits/main"}
        tag_ref = suffix.startswith("/git/ref/tags/") and TAG_TOKEN.fullmatch(urllib.parse.unquote(suffix.removeprefix("/git/ref/tags/"))) is not None
        tag_object = suffix.startswith("/git/tags/") and SHA40.fullmatch(suffix.removeprefix("/git/tags/")) is not None
        compare = re.fullmatch(r"/compare/[0-9a-f]{40}\.\.\.[0-9a-f]{40}", suffix) is not None
        try:
            query = urllib.parse.parse_qs(parsed.query, strict_parsing=True) if parsed.query else {}
        except ValueError as exc:
            raise TransportError("request_target_forbidden") from exc
        if not (simple or tag_ref or tag_object or compare):
            raise TransportError("request_target_forbidden")
        if compare:
            try:
                valid_query = set(query) == {"per_page", "page"} and query["page"] == ["1"] and len(query["per_page"]) == 1 and 1 <= int(query["per_page"][0]) <= 100
            except (KeyError, TypeError, ValueError):
                valid_query = False
            if not valid_query:
                raise TransportError("request_target_forbidden")
        elif query:
            raise TransportError("request_target_forbidden")
        names = {name.lower() for name, _value in request.headers}
        if names - {"accept", "x-github-api-version", "user-agent", "if-none-match"} or names & {"authorization", "cookie", "proxy-authorization"}:
            raise TransportError("request_headers_forbidden")

    @staticmethod
    def _read_body(response: Any, request: HttpRequest) -> bytes:
        chunks: list[bytes] = []
        total = 0
        while True:
            if request.deadline_monotonic is not None and time.monotonic() >= request.deadline_monotonic:
                raise TransportError("run_timeout")
            if request.deadline_monotonic is not None:
                remaining = request.deadline_monotonic - time.monotonic()
                socket = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
                if socket is not None:
                    try:
                        socket.settimeout(max(0.001, min(request.timeout_seconds, remaining)))
                    except OSError as exc:
                        raise TransportError("transport_timeout_failed") from exc
            chunk = response.read(min(65536, request.max_body_bytes + 1 - total))
            if request.deadline_monotonic is not None and time.monotonic() >= request.deadline_monotonic:
                raise TransportError("run_timeout")
            if not chunk:
                return b"".join(chunks)
            if not isinstance(chunk, bytes):
                raise TransportError("transport_body_invalid")
            chunks.append(chunk)
            total += len(chunk)
            if total > request.max_body_bytes:
                raise TransportError("body_limit")


def _state_dir(root: Path) -> Path:
    target = root.resolve(strict=True) / ".grok-stack/runtime/stable-synthesis"
    descriptor = _runtime_fd(root)
    os.close(descriptor)
    return target


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise SynthesisError("durability target is not a directory")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sanitize_subject(value: Any) -> str:
    if not isinstance(value, str):
        raise SynthesisError("candidate subject must be a string")
    clean = " ".join("".join(" " if unicodedata.category(char).startswith("C") else char for char in value).split())
    return clean[:MAX_SUBJECT]


def _bounded_etag(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 256 or any(unicodedata.category(char).startswith("C") for char in value):
        raise SynthesisError("ETag is outside bounded syntax")
    return value


def _epoch(value: Any, *, nullable: bool = False) -> bool:
    return (nullable and value is None) or (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and 0 <= value <= 9007199254740991
    )


def _validate_candidate(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"sha", "subject"}
        and isinstance(value["sha"], str)
        and SHA40.fullmatch(value["sha"]) is not None
        and isinstance(value["subject"], str)
        and len(value["subject"]) <= MAX_SUBJECT
        and not any(unicodedata.category(char).startswith("C") for char in value["subject"])
    )


def _validate_source_state(value: Any, max_candidates: int) -> None:
    if not isinstance(value, dict):
        raise SynthesisError("monitor state is invalid")
    if set(value) == FAILURE_SOURCE_FIELDS:
        if (
            value["status"] not in {"unknown", "stale"}
            or value["error"] not in {"transport", "rate_limited", "observation_invalid", "run_timeout"}
            or not _epoch(value["last_success_epoch"], nullable=True)
        ):
            raise SynthesisError("monitor state is invalid")
        return
    if set(value) != SUCCESS_SOURCE_FIELDS:
        raise SynthesisError("monitor state is invalid")
    if value["status"] not in {"converged", "review_required"}:
        raise SynthesisError("monitor state is invalid")
    if not isinstance(value["release_tag"], str) or TAG_TOKEN.fullmatch(value["release_tag"]) is None:
        raise SynthesisError("monitor state is invalid")
    for field in ("tag_object_sha", "release_commit_sha", "head_sha"):
        if not isinstance(value[field], str) or SHA40.fullmatch(value[field]) is None:
            raise SynthesisError("monitor state is invalid")
    for field in ("compare_base_sha", "compare_head_sha", "merge_base_sha"):
        item = value[field]
        if item is not None and (not isinstance(item, str) or SHA40.fullmatch(item) is None):
            raise SynthesisError("monitor state is invalid")
    if value["compare_status"] not in {None, "ahead", "behind", "diverged", "identical"}:
        raise SynthesisError("monitor state is invalid")
    if value["issue"] not in {None, "tag_object_mismatch", "compare_inconsistent", "compare_diverged"}:
        raise SynthesisError("monitor state is invalid")
    for field in ("ahead_by", "behind_by", "available_count"):
        if isinstance(value[field], bool) or not isinstance(value[field], int) or not 0 <= value[field] <= 1000000000:
            raise SynthesisError("monitor state is invalid")
    if not all(type(value[field]) is bool for field in ("release_changed", "truncated", "partial")):
        raise SynthesisError("monitor state is invalid")
    candidates = value["candidates"]
    if not isinstance(candidates, list) or len(candidates) > max_candidates or not all(_validate_candidate(item) for item in candidates):
        raise SynthesisError("monitor state is invalid")
    if len({item["sha"] for item in candidates}) != len(candidates):
        raise SynthesisError("monitor state is invalid")
    expected_status = "review_required" if value["issue"] or value["release_changed"] or value["available_count"] else "converged"
    if (
        value["status"] != expected_status
        or value["truncated"] != (value["available_count"] > len(candidates))
        or value["partial"] != (value["issue"] is not None or len(candidates) < min(value["available_count"], max_candidates))
    ):
        raise SynthesisError("monitor state is invalid")
    if _bounded_etag(value["release_etag"]) != value["release_etag"] or not _epoch(value["last_success_epoch"]):
        raise SynthesisError("monitor state is invalid")
    cached = value["cached_release"]
    if not isinstance(cached, dict) or set(cached) != {"tag_name", "draft", "prerelease"} or cached != {"tag_name": value["release_tag"], "draft": False, "prerelease": False}:
        raise SynthesisError("monitor state is invalid")


def _validate_state(value: Any, max_candidates: int, *, projection: bool = False) -> dict[str, Any]:
    expected = STATE_PAYLOAD_FIELDS if projection else STATE_ROOT_FIELDS
    if not isinstance(value, dict) or set(value) != expected or value.get("schema_version") != 1:
        raise SynthesisError("monitor state is invalid")
    if not _epoch(value["last_attempt_epoch"]) or not _epoch(value["next_due_epoch"]):
        raise SynthesisError("monitor state is invalid")
    if value["next_due_epoch"] != value["last_attempt_epoch"] + WEEK_SECONDS:
        raise SynthesisError("monitor state is invalid")
    if value["overall_status"] not in {"converged", "review_required", "degraded", "unavailable"}:
        raise SynthesisError("monitor state is invalid")
    if not isinstance(value["sources"], dict) or tuple(sorted(value["sources"])) != SOURCE_IDS:
        raise SynthesisError("monitor state is invalid")
    for source in value["sources"].values():
        _validate_source_state(source, max_candidates)
    statuses = {source["status"] for source in value["sources"].values()}
    if statuses == {"converged"}:
        expected_overall = "converged"
    elif statuses <= {"unknown"}:
        expected_overall = "unavailable"
    elif "unknown" in statuses or "stale" in statuses or any(source.get("partial") for source in value["sources"].values()):
        expected_overall = "degraded"
    else:
        expected_overall = "review_required"
    if value["overall_status"] != expected_overall:
        raise SynthesisError("monitor state is invalid")
    errors = value["errors"]
    if not isinstance(errors, list) or len(errors) > 3:
        raise SynthesisError("monitor state is invalid")
    for error in errors:
        if not isinstance(error, dict) or set(error) != {"source", "code"} or error["source"] not in SOURCE_IDS or error["code"] not in {"transport", "rate_limited", "observation_invalid", "run_timeout"}:
            raise SynthesisError("monitor state is invalid")
    for field in ("component_digest", "config_digest"):
        if not isinstance(value[field], str) or SHA64.fullmatch(value[field]) is None:
            raise SynthesisError("monitor state is invalid")
    if not projection:
        for field in ("journal_digest", "snapshot_digest"):
            if not isinstance(value[field], str) or SHA64.fullmatch(value[field]) is None:
                raise SynthesisError("monitor state is invalid")
    return value


def _error_code(exc: Exception) -> str:
    message = str(exc)
    if message == "rate_limited":
        return "rate_limited"
    if message == "run_timeout":
        return "run_timeout"
    if isinstance(exc, TransportError):
        return "transport"
    return "observation_invalid"


def _write_state(root: Path, state: dict[str, Any]) -> None:
    _runtime_write(root, "state.json", json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


class Monitor:
    def __init__(self, root: Path, transport: Callable[[HttpRequest], HttpResponse] | None = None) -> None:
        self.root = root.resolve()
        self.transport = transport or GitHubTransport()
        load_upstreams(self.root)
        config_path = self.root / "engineering/stable-synthesis/stable-synthesis-upstreams.v1.json"
        self.config = strict_json(_read_regular_bytes(config_path, 128 * 1024), 128 * 1024)
        self.config_digest = digest(self.config)
        self.component_digest = hashlib.sha256(_read_regular_bytes(Path(__file__), 1048576)).hexdigest()
        self.state_path = self.root / ".grok-stack/runtime/stable-synthesis/state.json"

    def _read_state(self) -> dict[str, Any] | None:
        parent = _runtime_fd(self.root)
        try:
            try:
                os.stat("state.json", dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                return None
        finally:
            os.close(parent)
        try:
            return _validate_state(
                strict_json(_runtime_read(self.root, "state.json", 1048576), 1048576),
                int(self.config["max_candidates_per_source"]),
            )
        except (SynthesisError, OSError, UnicodeError, TypeError, ValueError) as exc:
            raise SynthesisError("monitor state is invalid") from exc

    def _load_state(self, *, reconcile: bool = False) -> dict[str, Any]:
        state = self._read_state()
        if not reconcile:
            return state or {}
        entries = Journal(self.root).read()
        monitor_entries = [entry for entry in entries if entry["kind"] == "monitor"]
        if not monitor_entries:
            if state is not None:
                raise SynthesisError("monitor state is invalid")
            return {}
        tail = monitor_entries[-1]
        try:
            snap = strict_json(
                _runtime_read(self.root, f"{tail['snapshot_digest']}.json", 1048576, snapshots=True),
                1048576,
            )
            verify_snapshot(snap)
            payload = _validate_state(snap["content"], int(self.config["max_candidates_per_source"]), projection=True)
            if digest(payload) != tail["snapshot_digest"]:
                raise SynthesisError("snapshot projection mismatch")
        except (SynthesisError, OSError, UnicodeError, TypeError, ValueError) as exc:
            raise SynthesisError("monitor recovery evidence is invalid") from exc
        repaired = {**payload, "journal_digest": tail["digest"], "snapshot_digest": tail["snapshot_digest"]}
        if state == repaired:
            return state
        _write_state(self.root, repaired)
        return repaired

    @staticmethod
    def _status_from_state(state: dict[str, Any], timestamp: float) -> dict[str, Any]:
        last = state.get("last_attempt_epoch")
        due = 0 if last is None else last + WEEK_SECONDS
        return {"status": "due" if timestamp >= due else "not_due", "next_due_epoch": due, "last_attempt_epoch": last, "overall_status": state.get("overall_status", "unavailable")}

    def status(self, now: float | None = None) -> dict[str, Any]:
        timestamp = time.time() if now is None else now
        if not _epoch(timestamp):
            raise SynthesisError("monitor time is invalid")
        with _control_lock(self.root):
            return self._status_from_state(self._load_state(reconcile=True), timestamp)

    @staticmethod
    def _url(repository: str, suffix: str) -> str:
        if repository not in ALLOWED_REPOS or not suffix.startswith("/"):
            raise SynthesisError("request is outside allowlist")
        return f"https://api.github.com/repos/{repository}{suffix}"

    def _get(self, repository: str, suffix: str, etag: str | None = None, *, deadline: float | None = None) -> tuple[Any, str | None]:
        headers = [("Accept", "application/vnd.github+json"), ("X-GitHub-Api-Version", "2022-11-28"), ("User-Agent", "adaptive-grok-stable-synthesis/1")]
        if etag:
            headers.append(("If-None-Match", etag))
        remaining = 10 if deadline is None else deadline - time.monotonic()
        if remaining <= 0:
            raise TransportError("run_timeout")
        request = HttpRequest(
            "GET",
            self._url(repository, suffix),
            tuple(headers),
            max(0.001, min(10.0, remaining)),
            deadline,
            int(self.config["max_body_bytes"]),
        )
        response = self.transport(request)
        if deadline is not None and time.monotonic() >= deadline:
            raise TransportError("run_timeout")
        response_headers = {str(key).lower(): str(value) for key, value in response.headers.items()}
        if response.status in (301, 302, 303, 307, 308):
            raise TransportError("redirects are forbidden")
        if response.status in (403, 429):
            raise TransportError("rate_limited")
        if response.status == 304:
            return None, _bounded_etag(response_headers.get("etag") or etag)
        if response.status != 200:
            raise TransportError(f"GitHub status {response.status}")
        content_type = response_headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type not in {"application/json", "application/vnd.github+json"}:
            raise TransportError("unexpected content type")
        return strict_json(response.body, int(self.config["max_body_bytes"])), _bounded_etag(response_headers.get("etag"))

    def _observe(self, source: Upstream, previous: dict[str, Any], deadline: float) -> dict[str, Any]:
        if time.monotonic() > deadline:
            raise TransportError("run_timeout")
        release, release_etag = self._get(source.repository, "/releases/latest", previous.get("release_etag"), deadline=deadline)
        if release is None:
            release = previous.get("cached_release")
            if not isinstance(release, dict):
                raise TransportError("304_without_cache")
        if not isinstance(release, dict) or release.get("draft") is not False or release.get("prerelease") is not False or not isinstance(release.get("tag_name"), str):
            raise SynthesisError("latest release is not a qualifying stable release")
        tag = release["tag_name"]
        if not TAG_TOKEN.fullmatch(tag):
            raise SynthesisError("release tag is outside bounded token syntax")
        release = {"tag_name": tag, "draft": False, "prerelease": False}
        encoded = urllib.parse.quote(tag, safe="")
        ref, _ = self._get(source.repository, f"/git/ref/tags/{encoded}", deadline=deadline)
        if not isinstance(ref, dict) or not isinstance(ref.get("object"), dict) or ref.get("ref") != f"refs/tags/{tag}":
            raise SynthesisError("tag ref shape invalid")
        obj = ref["object"]
        root_tag_sha = obj.get("sha")
        if not isinstance(root_tag_sha, str) or SHA40.fullmatch(root_tag_sha) is None:
            raise SynthesisError("tag ref shape invalid")
        issue: str | None = "tag_object_mismatch" if tag == source.stable_tag and root_tag_sha != source.tag_object_sha else None
        seen: set[str] = set()
        for _ in range(4):
            kind, sha = obj.get("type"), obj.get("sha")
            if not isinstance(sha, str) or not SHA40.fullmatch(sha) or sha in seen:
                raise SynthesisError("invalid or cyclic tag object")
            seen.add(sha)
            if kind == "commit":
                stable_sha = sha
                break
            if kind != "tag":
                raise SynthesisError("tag does not terminate at a commit")
            tag_doc, _ = self._get(source.repository, f"/git/tags/{sha}", deadline=deadline)
            if not isinstance(tag_doc, dict) or tag_doc.get("sha") != sha or not isinstance(tag_doc.get("object"), dict):
                raise SynthesisError("annotated tag shape invalid")
            obj = tag_doc["object"]
        else:
            raise SynthesisError("annotated tag depth exceeded")
        head, _ = self._get(source.repository, "/commits/main", deadline=deadline)
        head_sha = head.get("sha") if isinstance(head, dict) else None
        if not isinstance(head_sha, str) or not SHA40.fullmatch(head_sha):
            raise SynthesisError("main head SHA invalid")
        per_page = int(self.config["max_candidates_per_source"])
        compare, _ = self._get(source.repository, f"/compare/{source.peeled_commit_sha}...{head_sha}?per_page={per_page}&page=1", deadline=deadline)
        if not isinstance(compare, dict):
            raise SynthesisError("compare response invalid")
        compare_status = compare.get("status")
        counts = (compare.get("ahead_by"), compare.get("behind_by"), compare.get("total_commits"))
        base_sha = compare.get("base_commit", {}).get("sha") if isinstance(compare.get("base_commit"), dict) else None
        merge_base_sha = compare.get("merge_base_commit", {}).get("sha") if isinstance(compare.get("merge_base_commit"), dict) else None
        compare_head_sha = compare.get("head_commit", {}).get("sha") if isinstance(compare.get("head_commit"), dict) else None
        commits = compare.get("commits")
        topology_valid = (
            compare_status in {"ahead", "behind", "diverged", "identical"}
            and all(not isinstance(value, bool) and isinstance(value, int) and 0 <= value <= 1000000000 for value in counts)
            and base_sha == source.peeled_commit_sha
            and isinstance(merge_base_sha, str)
            and SHA40.fullmatch(merge_base_sha) is not None
            and compare_head_sha == head_sha
            and isinstance(commits, list)
            and len(commits) <= per_page
        )
        if not topology_valid:
            issue = issue or "compare_inconsistent"
            commits = []
            counts = (0, 0, 0)
            compare_status = None
            base_sha = None
            merge_base_sha = None
            compare_head_sha = None
        ahead_by, behind_by, available = counts
        if issue is None and (
            available != ahead_by
            or len(commits) != min(available, per_page)
            or (compare_status == "ahead" and available == 0)
            or (compare_status == "identical" and (ahead_by != 0 or behind_by != 0 or merge_base_sha != source.peeled_commit_sha))
            or (compare_status == "ahead" and (behind_by != 0 or merge_base_sha != source.peeled_commit_sha))
        ):
            issue = issue or "compare_inconsistent"
        elif issue is None and compare_status in {"behind", "diverged"}:
            issue = issue or "compare_diverged"
        candidates = []
        for commit in commits:
            sha = commit.get("sha") if isinstance(commit, dict) else None
            message = commit.get("commit", {}).get("message") if isinstance(commit, dict) and isinstance(commit.get("commit"), dict) else None
            if not isinstance(sha, str) or not SHA40.fullmatch(sha):
                issue = issue or "compare_inconsistent"
                candidates = []
                break
            candidates.append({"sha": sha, "subject": _sanitize_subject(message.splitlines()[0] if isinstance(message, str) else "")})
        if len({item["sha"] for item in candidates}) != len(candidates):
            issue = issue or "compare_inconsistent"
            candidates = []
        if issue is None and available and available <= per_page and candidates[-1]["sha"] != head_sha:
            issue = "compare_inconsistent"
        changed_release = tag != source.stable_tag or stable_sha != source.peeled_commit_sha
        return self._observation(
            source,
            release,
            release_etag,
            tag_object_sha=root_tag_sha,
            release_commit_sha=stable_sha,
            head_sha=head_sha,
            compare_base_sha=base_sha,
            compare_head_sha=compare_head_sha,
            merge_base_sha=merge_base_sha,
            compare_status=compare_status,
            ahead_by=ahead_by,
            behind_by=behind_by,
            available_count=available,
            candidates=candidates,
            release_changed=changed_release,
            issue=issue,
            max_candidates=per_page,
        )

    @staticmethod
    def _observation(
        source: Upstream,
        release: dict[str, Any],
        release_etag: str | None,
        *,
        tag_object_sha: str | None,
        release_commit_sha: str | None,
        head_sha: str | None = None,
        compare_base_sha: str | None = None,
        compare_head_sha: str | None = None,
        merge_base_sha: str | None = None,
        compare_status: str | None = None,
        ahead_by: int = 0,
        behind_by: int = 0,
        available_count: int = 0,
        candidates: list[dict[str, str]] | None = None,
        release_changed: bool = True,
        issue: str | None = None,
        max_candidates: int = 20,
    ) -> dict[str, Any]:
        bounded = [] if candidates is None else candidates
        partial = issue is not None or len(bounded) < min(available_count, max_candidates)
        return {
            "status": "review_required" if issue or release_changed or available_count else "converged",
            "release_tag": release["tag_name"],
            "tag_object_sha": tag_object_sha,
            "release_commit_sha": release_commit_sha,
            "release_changed": release_changed,
            "head_sha": head_sha,
            "compare_base_sha": compare_base_sha,
            "compare_head_sha": compare_head_sha,
            "merge_base_sha": merge_base_sha,
            "compare_status": compare_status,
            "ahead_by": ahead_by,
            "behind_by": behind_by,
            "available_count": available_count,
            "candidates": bounded,
            "truncated": available_count > len(bounded),
            "partial": partial,
            "issue": issue,
            "release_etag": release_etag,
            "cached_release": release,
        }

    def check(self, now: float | None = None, *, force: bool = False) -> dict[str, Any]:
        timestamp = time.time() if now is None else now
        if not _epoch(timestamp):
            raise SynthesisError("monitor time is invalid")
        try:
            with _control_lock(self.root, timeout=0.0):
                previous_state = self._load_state(reconcile=True)
                current = self._status_from_state(previous_state, timestamp)
                if not force and current["status"] != "due":
                    return {**current, "performed": False}
                deadline = time.monotonic() + int(self.config["run_timeout_seconds"])
                observations: dict[str, Any] = {}
                errors: list[dict[str, str]] = []
                previous_sources = previous_state.get("sources", {}) if isinstance(previous_state.get("sources"), dict) else {}
                for source in load_upstreams(self.root):
                    try:
                        observations[source.id] = self._observe(source, previous_sources.get(source.id, {}), deadline)
                    except (SynthesisError, TransportError, KeyError, TypeError) as exc:
                        had_success = isinstance(previous_sources.get(source.id), dict) and previous_sources[source.id].get("last_success_epoch") is not None
                        code = _error_code(exc)
                        observations[source.id] = {"status": "stale" if had_success else "unknown", "error": code, "last_success_epoch": previous_sources.get(source.id, {}).get("last_success_epoch") if isinstance(previous_sources.get(source.id), dict) else None}
                        errors.append({"source": source.id, "code": code})
                    else:
                        observations[source.id]["last_success_epoch"] = timestamp
                statuses = {item["status"] for item in observations.values()}
                if statuses == {"converged"}:
                    overall = "converged"
                elif statuses <= {"unknown"}:
                    overall = "unavailable"
                elif "unknown" in statuses or "stale" in statuses or any(item.get("partial") for item in observations.values()):
                    overall = "degraded"
                else:
                    overall = "review_required"
                payload = {"schema_version": 1, "last_attempt_epoch": timestamp, "next_due_epoch": timestamp + WEEK_SECONDS, "overall_status": overall, "sources": dict(sorted(observations.items())), "errors": errors[:3], "component_digest": self.component_digest, "config_digest": self.config_digest}
                _validate_state(payload, int(self.config["max_candidates_per_source"]), projection=True)
                snap_path = write_snapshot(self.root, payload)
                journal = Journal(self.root)
                entries = journal.read()
                prior = entries[-1]["digest"] if entries else "0" * 64
                entry = journal._append_unlocked({"recorded_at": timestamp, "kind": "monitor", "component_digest": self.component_digest, "config_digest": self.config_digest, "intent_digest": digest(self.config), "snapshot_digest": snap_path.stem}, prior)
                state = {**payload, "journal_digest": entry["digest"], "snapshot_digest": snap_path.stem}
                _write_state(self.root, state)
                return {**state, "performed": True}
        except TimeoutError:
            return {"performed": False, "status": "busy", "overall_status": "degraded"}
