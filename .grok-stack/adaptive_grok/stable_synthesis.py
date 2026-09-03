from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from .state import runtime_lock
from .util import atomic_write_text, git_head, load_json, runtime_dir, tree_fingerprint

WEEK_SECONDS = 604800
MAX_ITERATIONS = 8
MAX_JOURNAL_ENTRIES = 10000
MAX_SUBJECT = 160
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SOURCE_IDS = ("bmad_method", "spec_kit", "superpowers")
ALLOWED_REPOS = ("bmad-code-org/BMAD-METHOD", "github/spec-kit", "obra/superpowers")
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
    timeout_seconds: int = 10


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
            raise SynthesisError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(raw: bytes, max_bytes: int) -> Any:
    if len(raw) > max_bytes:
        raise SynthesisError("response body exceeds configured bound")
    try:
        text = raw.decode("utf-8", errors="strict")
        return json.loads(text, object_pairs_hook=_strict_object_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SynthesisError("response is not strict UTF-8 JSON") from exc


def load_upstreams(root: Path) -> tuple[Upstream, ...]:
    path = root / "engineering/contracts/schemas/stable-synthesis-upstreams.v1.json"
    raw = strict_json(path.read_bytes(), 128 * 1024)
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
        elif task.state in {"analyzing", "repair_planned"}:
            findings.append(Finding(f"F-PARTIAL-{task.id}", "partial", task.id, "task is not terminal"))
    return tuple(sorted(findings, key=lambda item: (item.category, item.id)))


def synthesize(intent: dict[str, Any], *, iterations: int = 1) -> SynthesisResult:
    if not isinstance(intent, dict) or not intent or iterations < 1 or iterations > MAX_ITERATIONS:
        raise SynthesisError("intent and iteration bound are required")
    intent_digest = digest(intent)
    names = ("pins-contract", "static-analysis", "monitor-review", "readiness")
    tasks = []
    for index, name in enumerate(names):
        tasks.append({"id": _task_id(intent_digest, name), "name": name, "state": "pending", "depends_on": [] if index == 0 else [_task_id(intent_digest, names[index - 1])]})
    validate_dag(tasks)
    findings: list[Finding] = []
    for key in sorted(intent):
        if intent[key] in (None, "", [], {}):
            findings.append(Finding("F-" + hashlib.sha256(f"missing:{key}".encode()).hexdigest()[:12], "missing", key, "required intent field is empty"))
    state = "ready" if not findings else "blocked"
    repairs = tuple(Repair(f.id, "supply_reviewed_value", f.subject) for f in findings)
    payload = {"schema_version": 1, "state": state, "iterations": iterations, "intent_digest": intent_digest, "tasks": tasks, "findings": [asdict(x) for x in findings], "repair_plan": [asdict(x) for x in repairs]}
    return SynthesisResult(1, state, iterations, intent_digest, tuple(tasks), tuple(findings), repairs, digest(payload))


def snapshot(value: Any) -> dict[str, Any]:
    body = canonical_bytes(value)
    return {"schema_version": 1, "digest": hashlib.sha256(body).hexdigest(), "content": json.loads(body)}


def verify_snapshot(value: dict[str, Any]) -> None:
    if set(value) != {"schema_version", "digest", "content"} or value.get("schema_version") != 1 or digest(value.get("content")) != value.get("digest"):
        raise SynthesisError("snapshot digest mismatch")


class Journal:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / ".grok-stack/runtime/stable-synthesis/journal.jsonl"

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        if self.path.is_symlink() or not self.path.is_file():
            raise SynthesisError("journal path is not a regular file")
        entries: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            entries.append(strict_json(line.encode(), 128 * 1024))
        if len(entries) > MAX_JOURNAL_ENTRIES:
            raise SynthesisError("journal replay bound exceeded")
        prior = "0" * 64
        for sequence, entry in enumerate(entries, 1):
            recorded = dict(entry)
            actual = recorded.pop("digest", None)
            if entry.get("sequence") != sequence or entry.get("prior_digest") != prior or digest(recorded) != actual:
                raise SynthesisError("journal chain is corrupt")
            prior = str(actual)
        return entries

    def append(self, record: dict[str, Any], expected_prior: str) -> dict[str, Any]:
        with runtime_lock(self.root, "stable-synthesis-journal", timeout=0.0):
            _state_dir(self.root)
            return self._append_unlocked(record, expected_prior)

    def _append_unlocked(self, record: dict[str, Any], expected_prior: str) -> dict[str, Any]:
        entries = self.read()
        prior = entries[-1]["digest"] if entries else "0" * 64
        if prior != expected_prior or len(entries) >= MAX_JOURNAL_ENTRIES:
            raise SynthesisError("journal compare-and-swap failed")
        item = {"sequence": len(entries) + 1, "prior_digest": prior, **record}
        item["digest"] = digest(item)
        text = "".join(json.dumps(x, sort_keys=True, separators=(",", ":")) + "\n" for x in [*entries, item])
        atomic_write_text(self.path, text)
        return item


def write_snapshot(root: Path, value: Any) -> Path:
    item = snapshot(value)
    directory = _state_dir(root) / "snapshots"
    directory.mkdir(mode=0o700, exist_ok=True)
    path = directory / f"{item['digest']}.json"
    if path.exists():
        verify_snapshot(strict_json(path.read_bytes(), 1048576))
    else:
        atomic_write_text(path, json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
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
        req = urllib.request.Request(request.url, method="GET", headers=dict(request.headers))
        try:
            with self._opener.open(req, timeout=request.timeout_seconds) as response:
                return HttpResponse(response.status, dict(response.headers.items()), response.read(1048577))
        except urllib.error.HTTPError as exc:
            return HttpResponse(exc.code, dict(exc.headers.items()), exc.read(1048577))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TransportError("GitHub request failed") from exc


def _state_dir(root: Path) -> Path:
    base = runtime_dir(root)
    if base.is_symlink():
        raise SynthesisError("runtime directory must not be a symlink")
    target = base / "stable-synthesis"
    if target.exists() and (target.is_symlink() or not target.is_dir()):
        raise SynthesisError("stable synthesis state path is unsafe")
    target.mkdir(mode=0o700, exist_ok=True)
    return target


def _sanitize_subject(value: Any) -> str:
    if not isinstance(value, str):
        raise SynthesisError("candidate subject must be a string")
    clean = " ".join(value.replace("\x00", " ").split())
    return clean[:MAX_SUBJECT]


class Monitor:
    def __init__(self, root: Path, transport: Callable[[HttpRequest], HttpResponse] | None = None) -> None:
        self.root = root.resolve()
        self.transport = transport or GitHubTransport()
        self.config = load_json(self.root / "engineering/contracts/schemas/stable-synthesis-upstreams.v1.json", {})
        self.state_path = self.root / ".grok-stack/runtime/stable-synthesis/state.json"

    def _load_state(self) -> dict[str, Any]:
        state = load_json(self.state_path, {})
        return state if isinstance(state, dict) and state.get("schema_version") in (None, 1) else {}

    def status(self, now: float | None = None) -> dict[str, Any]:
        timestamp = time.time() if now is None else now
        state = self._load_state()
        last = state.get("last_attempt_epoch")
        due = 0 if not isinstance(last, (int, float)) else last + WEEK_SECONDS
        return {"status": "due" if timestamp >= due else "not_due", "next_due_epoch": due, "last_attempt_epoch": last, "overall_status": state.get("overall_status", "unavailable")}

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
        request = HttpRequest("GET", self._url(repository, suffix), tuple(headers), max(1, min(10, int(remaining + 0.999))))
        response = self.transport(request)
        if response.status in (301, 302, 303, 307, 308):
            raise TransportError("redirects are forbidden")
        if response.status in (403, 429):
            raise TransportError("rate_limited")
        if response.status == 304:
            return None, response.headers.get("ETag") or etag
        if response.status != 200:
            raise TransportError(f"GitHub status {response.status}")
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type not in {"application/json", "application/vnd.github+json"}:
            raise TransportError("unexpected content type")
        return strict_json(response.body, int(self.config["max_body_bytes"])), response.headers.get("ETag")

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
        encoded = urllib.parse.quote(tag, safe="")
        ref, _ = self._get(source.repository, f"/git/ref/tags/{encoded}", deadline=deadline)
        if not isinstance(ref, dict) or not isinstance(ref.get("object"), dict):
            raise SynthesisError("tag ref shape invalid")
        obj = ref["object"]
        kind, sha = obj.get("type"), obj.get("sha")
        if not isinstance(sha, str) or not SHA40.fullmatch(sha):
            raise SynthesisError("invalid tag object")
        if kind == "commit":
            stable_sha = sha
        elif kind == "tag":
            tag_doc, _ = self._get(source.repository, f"/git/tags/{sha}", deadline=deadline)
            if not isinstance(tag_doc, dict) or not isinstance(tag_doc.get("object"), dict):
                raise SynthesisError("annotated tag shape invalid")
            terminal = tag_doc["object"]
            stable_sha = terminal.get("sha")
            if terminal.get("type") != "commit" or not isinstance(stable_sha, str) or not SHA40.fullmatch(stable_sha):
                raise SynthesisError("annotated tag does not terminate at a commit")
        else:
            raise SynthesisError("tag does not terminate at a commit")
        head, _ = self._get(source.repository, "/commits/main", deadline=deadline)
        head_sha = head.get("sha") if isinstance(head, dict) else None
        if not isinstance(head_sha, str) or not SHA40.fullmatch(head_sha):
            raise SynthesisError("main head SHA invalid")
        per_page = int(self.config["max_candidates_per_source"])
        compare, _ = self._get(source.repository, f"/compare/{source.peeled_commit_sha}...{head_sha}?per_page={per_page}&page=1", deadline=deadline)
        if not isinstance(compare, dict) or not isinstance(compare.get("total_commits"), int) or isinstance(compare["total_commits"], bool) or compare["total_commits"] < 0 or not isinstance(compare.get("commits"), list):
            raise SynthesisError("compare response invalid")
        candidates = []
        for commit in compare["commits"][:per_page]:
            sha = commit.get("sha") if isinstance(commit, dict) else None
            message = commit.get("commit", {}).get("message") if isinstance(commit, dict) and isinstance(commit.get("commit"), dict) else None
            if not isinstance(sha, str) or not SHA40.fullmatch(sha):
                raise SynthesisError("candidate SHA invalid")
            candidates.append({"sha": sha, "subject": _sanitize_subject(message.splitlines()[0] if isinstance(message, str) else "")})
        changed_release = tag != source.stable_tag or stable_sha != source.peeled_commit_sha
        available = compare["total_commits"]
        return {"status": "review_required" if changed_release or available else "converged", "release_tag": tag, "release_commit_sha": stable_sha, "release_changed": changed_release, "head_sha": head_sha, "available_count": available, "candidates": candidates, "truncated": available > len(candidates), "partial": len(compare["commits"]) < min(available, per_page), "release_etag": release_etag, "cached_release": release}

    def check(self, now: float | None = None, *, force: bool = False) -> dict[str, Any]:
        timestamp = time.time() if now is None else now
        try:
            with runtime_lock(self.root, "stable-synthesis", timeout=0.0):
                _state_dir(self.root)
                previous_state = self._load_state()
                current = self.status(timestamp)
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
                        observations[source.id] = {"status": "stale" if had_success else "unknown", "error": str(exc)[:160], "last_success_epoch": previous_sources.get(source.id, {}).get("last_success_epoch") if isinstance(previous_sources.get(source.id), dict) else None}
                        errors.append({"source": source.id, "code": type(exc).__name__})
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
                state = {"schema_version": 1, "last_attempt_epoch": timestamp, "next_due_epoch": timestamp + WEEK_SECONDS, "overall_status": overall, "sources": dict(sorted(observations.items())), "errors": errors[:3], "head_sha": git_head(self.root), "tree_fingerprint": tree_fingerprint(self.root)}
                snap_path = write_snapshot(self.root, state)
                journal = Journal(self.root)
                entries = journal.read()
                prior = entries[-1]["digest"] if entries else "0" * 64
                journal._append_unlocked({"recorded_at": timestamp, "kind": "monitor", "head_sha": state["head_sha"], "tree_fingerprint": state["tree_fingerprint"], "intent_digest": digest(self.config), "snapshot_digest": snap_path.stem}, prior)
                atomic_write_text(self.state_path, json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
                return {**state, "performed": True}
        except TimeoutError:
            return {"performed": False, "status": "busy", "overall_status": "degraded"}
