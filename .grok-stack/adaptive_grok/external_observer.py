from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import stat
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator


ROOT = Path(__file__).resolve().parents[2]
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
MAX_BODY = 1_048_576
MAX_TAG_DEPTH = 4
MAX_CHECKS = 100
MAX_COMMITS = 100
MAX_STATE = 2_000_000
MAX_CALLS = 16
CHECK_CONCLUSIONS = {None, "success", "failure", "neutral", "cancelled", "skipped", "timed_out", "action_required", "stale", "startup_failure"}


class ObserverError(RuntimeError):
    pass


class TransportError(ObserverError):
    pass


@dataclass(frozen=True)
class ObserverConfig:
    repository: str
    default_branch: str
    pull_request_number: int
    expected_check_name: str
    expected_app_id: int
    freshness_seconds: int


@dataclass(frozen=True)
class Claim:
    id: str
    claim_status: str
    sha: str | None = None
    reviewed_sha: str | None = None
    digest: str | None = None
    observed_at: str | None = None


def _closed(value: dict[str, Any], required: set[str], optional: set[str], error: str) -> None:
    if set(value) != required | (set(value) & optional) or not required <= set(value):
        raise ObserverError(error)


def _sha(value: Any) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise ObserverError("invalid_response")
    return value


def parse_config(raw: object, *, allow_placeholders: bool = False) -> ObserverConfig:
    if not isinstance(raw, dict):
        raise ObserverError("invalid_config")
    required = {"schema_version", "repository", "default_branch", "pull_request_number", "expected_check_name", "expected_app_id", "freshness_seconds"}
    _closed(raw, required, set(), "invalid_config")
    if raw["schema_version"] != 1:
        raise ObserverError("invalid_config")
    repo = raw["repository"]
    branch = raw["default_branch"]
    check = raw["expected_check_name"]
    if not all(isinstance(item, str) for item in (repo, branch, check)):
        raise ObserverError("invalid_config")
    if not REPO_RE.fullmatch(repo) or not re.fullmatch(r"[A-Za-z0-9._/-]{1,100}", branch) or not 1 <= len(check) <= 200:
        raise ObserverError("invalid_config")
    if not allow_placeholders and (repo == "OWNER/REPOSITORY" or check == "CHECK_NAME"):
        raise ObserverError("invalid_config")
    pr = raw["pull_request_number"]
    app = raw["expected_app_id"]
    fresh = raw["freshness_seconds"]
    if isinstance(pr, bool) or not isinstance(pr, int) or not 1 <= pr <= 2_147_483_647:
        raise ObserverError("invalid_config")
    if isinstance(app, bool) or not isinstance(app, int) or not 1 <= app <= 2_147_483_647:
        raise ObserverError("invalid_config")
    if isinstance(fresh, bool) or not isinstance(fresh, int) or not 60 <= fresh <= 86_400:
        raise ObserverError("invalid_config")
    return ObserverConfig(repo, branch, pr, check, app, fresh)


def parse_claims(raw: object) -> tuple[Claim, ...]:
    if not isinstance(raw, dict):
        raise ObserverError("invalid_claims")
    _closed(raw, {"schema_version", "snapshot_kind", "milestones"}, {"project_state", "candidate"}, "invalid_claims")
    if raw["schema_version"] != 1 or raw["snapshot_kind"] != "historical_claims" or not isinstance(raw["milestones"], list) or len(raw["milestones"]) > 10:
        raise ObserverError("invalid_claims")
    result: list[Claim] = []
    seen: set[str] = set()
    for item in raw["milestones"]:
        if not isinstance(item, dict):
            raise ObserverError("invalid_claims")
        _closed(item, {"id", "claim_status"}, {"sha", "reviewed_sha", "digest", "observed_at"}, "invalid_claims")
        ident = item["id"]
        status_value = item["claim_status"]
        if not isinstance(ident, str) or not re.fullmatch(r"M[0-9]", ident) or ident in seen:
            raise ObserverError("invalid_claims")
        if status_value not in {"evidence_claimed", "historical_evidence_claimed"}:
            raise ObserverError("invalid_claims")
        for key in ("sha", "reviewed_sha"):
            if key in item and not SHA_RE.fullmatch(str(item[key])):
                raise ObserverError("invalid_claims")
        if "digest" in item and not re.fullmatch(r"[0-9a-f]{64}", str(item["digest"])):
            raise ObserverError("invalid_claims")
        result.append(Claim(**item))
        seen.add(ident)
    return tuple(sorted(result, key=lambda item: item.id))


def _claim_context(raw: object) -> tuple[tuple[Claim, ...], dict[str, Any] | None, dict[str, Any] | None]:
    claims = parse_claims(raw)
    assert isinstance(raw, dict)
    project = raw.get("project_state")
    candidate = raw.get("candidate")
    if project is not None:
        if not isinstance(project, dict):
            raise ObserverError("invalid_claims")
        _closed(project, {"observed_main_sha", "observed_at"}, set(), "invalid_claims")
        if not SHA_RE.fullmatch(str(project["observed_main_sha"])) or not isinstance(project["observed_at"], str) or len(project["observed_at"]) > 40:
            raise ObserverError("invalid_claims")
    if candidate is not None:
        if not isinstance(candidate, dict):
            raise ObserverError("invalid_claims")
        _closed(candidate, {"implementation_sha", "reviewed_sha", "evidence_digest", "observed_at", "referenced_pr"}, set(), "invalid_claims")
        if not SHA_RE.fullmatch(str(candidate["implementation_sha"])) or not SHA_RE.fullmatch(str(candidate["reviewed_sha"])) or not re.fullmatch(r"[0-9a-f]{64}", str(candidate["evidence_digest"])):
            raise ObserverError("invalid_claims")
        if not isinstance(candidate["observed_at"], str) or len(candidate["observed_at"]) > 40 or not isinstance(candidate["referenced_pr"], dict):
            raise ObserverError("invalid_claims")
        reference = candidate["referenced_pr"]
        _closed(reference, {"number", "state", "base_ref", "head_sha"}, set(), "invalid_claims")
        if isinstance(reference["number"], bool) or not isinstance(reference["number"], int) or reference["state"] not in {"open", "closed"} or not isinstance(reference["base_ref"], str) or not SHA_RE.fullmatch(str(reference["head_sha"])):
            raise ObserverError("invalid_claims")
    return claims, project, candidate


def _epoch(value: object) -> int:
    if not isinstance(value, str) or len(value) > 40 or not value.endswith("Z"):
        raise ObserverError("invalid_claims")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ObserverError("invalid_claims") from exc
    if parsed.tzinfo != timezone.utc:
        raise ObserverError("invalid_claims")
    return int(parsed.timestamp())


def _reject_constant(_value: str) -> None:
    raise ValueError("invalid_json")


def _bounded_int(value: str) -> int:
    parsed = int(value)
    if not -(2**63) <= parsed <= 2**63 - 1:
        raise ValueError("invalid_json")
    return parsed


def strict_json(data: bytes) -> object:
    if len(data) > MAX_BODY:
        raise TransportError("oversize")
    try:
        text = data.decode("utf-8", errors="strict")
        def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in items:
                if key in result:
                    raise ValueError("duplicate_key")
                result[key] = value
            return result
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=_reject_constant, parse_float=_reject_constant, parse_int=_bounded_int)
        _validate_json_shape(value)
        return value
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, OverflowError) as exc:
        raise TransportError("invalid_json") from exc


def _validate_json_shape(value: object, depth: int = 0) -> None:
    if depth > 16:
        raise ValueError("invalid_json")
    if isinstance(value, str):
        if len(value) > 4096:
            raise ValueError("invalid_json")
    elif isinstance(value, list):
        if len(value) > 1000:
            raise ValueError("invalid_json")
        for item in value:
            _validate_json_shape(item, depth + 1)
    elif isinstance(value, dict):
        if len(value) > 200:
            raise ValueError("invalid_json")
        for key, item in value.items():
            if len(key) > 128:
                raise ValueError("invalid_json")
            _validate_json_shape(item, depth + 1)


def canonical_bytes(value: object) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ObserverError("invalid_projection") from exc


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise TransportError("redirect_forbidden")


class GitHubTransport:
    def __init__(self, repository: str, opener: Callable[..., Any] | None = None, *, clock: Callable[[], float] = time.monotonic) -> None:
        if not REPO_RE.fullmatch(repository):
            raise TransportError("invalid_repository")
        self.repository = repository
        self.clock = clock
        self.started = clock()
        if opener is None:
            client = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
            self.opener = client.open
        else:
            self.opener = opener

    def get(self, path: str) -> object:
        return self.request("GET", f"https://api.github.com{path}")

    def request(self, method: str, url: str) -> object:
        parsed = urllib.parse.urlsplit(url)
        prefix = f"/repos/{self.repository}/"
        suffix = parsed.path[len(prefix):] if parsed.path.startswith(prefix) else ""
        allowed = (
            re.fullmatch(r"commits/[A-Za-z0-9._/-]{1,100}", suffix)
            or re.fullmatch(r"commits/[0-9a-f]{40}/check-runs", suffix)
            or re.fullmatch(r"pulls/[1-9][0-9]{0,9}", suffix)
            or suffix == "releases/latest"
            or re.fullmatch(r"git/ref/tags/[A-Za-z0-9._%+-]{1,384}", suffix)
            or re.fullmatch(r"git/tags/[0-9a-f]{40}", suffix)
            or re.fullmatch(r"compare/[0-9a-f]{40}\.\.\.[0-9a-f]{40}", suffix)
        )
        query_ok = (not parsed.query) or (suffix.endswith("/check-runs") and parsed.query == "per_page=100") or (suffix.startswith("compare/") and parsed.query == "per_page=100&page=1")
        if method != "GET" or parsed.scheme != "https" or parsed.netloc != "api.github.com" or not allowed or not query_ok or parsed.fragment:
            raise TransportError("forbidden_request")
        if self.clock() - self.started >= 90:
            raise TransportError("deadline")
        request = urllib.request.Request(url, method="GET", headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "adaptive-external-observer/1"})
        remaining = min(10.0, 90.0 - (self.clock() - self.started))
        try:
            response = self.opener(request, timeout=remaining)
            try:
                status_code = getattr(response, "status", 200)
                if status_code in {301, 302, 303, 307, 308}:
                    raise TransportError("redirect_forbidden")
                if status_code in {403, 429}:
                    raise TransportError("rate_limited")
                if status_code != 200:
                    raise TransportError("github_unavailable")
                content_type = str(getattr(response, "headers", {}).get("Content-Type", "")).split(";", 1)[0].strip().lower()
                if content_type not in {"application/json", "application/vnd.github+json"}:
                    raise TransportError("invalid_content_type")
                chunks: list[bytes] = []
                size = 0
                while True:
                    if self.clock() - self.started >= 90:
                        raise TransportError("deadline")
                    chunk = response.read(min(65536, MAX_BODY + 1 - size))
                    if not isinstance(chunk, bytes):
                        raise TransportError("invalid_body")
                    if self.clock() - self.started >= 90:
                        raise TransportError("deadline")
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_BODY:
                        raise TransportError("oversize")
                    chunks.append(chunk)
                return strict_json(b"".join(chunks))
            finally:
                close = getattr(response, "close", None)
                if callable(close):
                    close()
        except TransportError:
            raise
        except urllib.error.HTTPError as exc:
            raise TransportError("rate_limited" if exc.code in {403, 429} else "github_unavailable") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TransportError("timeout") from exc


def _read_json(path: Path, *, missing: object = None) -> object:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return missing
    except OSError as exc:
        raise ObserverError("invalid_state") from exc
    try:
        mode = os.fstat(fd).st_mode
        if not stat.S_ISREG(mode):
            raise ObserverError("invalid_state")
        chunks: list[bytes] = []
        remaining = MAX_STATE + 1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > MAX_STATE:
            raise ObserverError("invalid_state")
        return strict_json(data)
    except TransportError as exc:
        raise ObserverError("invalid_state") from exc
    finally:
        os.close(fd)


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ObserverError("unsafe_state")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(canonical_bytes(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except OSError as exc:
        raise ObserverError("state_write_failed") from exc
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _safe_runtime(root: Path) -> Path:
    current = root
    for name in (".grok-stack", "runtime", "external-observer"):
        current = current / name
        try:
            mode = os.lstat(current).st_mode
            if not stat.S_ISDIR(mode):
                raise ObserverError("unsafe_state")
        except FileNotFoundError:
            try:
                os.mkdir(current, 0o700)
            except FileExistsError as exc:
                raise ObserverError("unsafe_state") from exc
    return current


def _validate_cached_status(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ObserverError("invalid_state")
    try:
        return validate_status(value)
    except ObserverError as exc:
        raise ObserverError("invalid_state") from exc


def validate_status(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ObserverError("invalid_projection")
    required = {"schema_version", "kind", "generated_at_epoch", "observation_epoch", "subject_digest", "snapshot_age_seconds", "main_sha", "current_delivery_pr", "pr_state", "pr_head_sha", "reviewed_sha", "trust_ci_check_name", "trust_ci_app_id", "trust_ci_sha", "trust_ci_status", "trust_ci_conclusion", "trust_ci_verdict", "trust_ci_failed_step", "release_sha", "evidence_freshness", "overall", "freshness", "implemented", "reviewed", "project_state", "reference", "check_verified", "delivered", "released", "attestation", "check_reference", "findings", "milestones", "observation", "digest"}
    if frozenset(value) not in {frozenset(required), frozenset(required | {"error"})} or value.get("schema_version") != 1 or value.get("kind") != "PUBLIC_STATUS.v1":
        raise ObserverError("invalid_projection")
    for key in ("generated_at_epoch", "observation_epoch", "snapshot_age_seconds"):
        if isinstance(value.get(key), bool) or not isinstance(value.get(key), int) or not 0 <= value[key] <= 2_147_483_647:
            raise ObserverError("invalid_projection")
    if not re.fullmatch(r"[0-9a-f]{64}", str(value.get("subject_digest"))):
        raise ObserverError("invalid_projection")
    for key in ("main_sha", "pr_head_sha", "reviewed_sha", "trust_ci_sha", "release_sha"):
        if value.get(key) is not None and not SHA_RE.fullmatch(str(value[key])):
            raise ObserverError("invalid_projection")
    if value.get("current_delivery_pr") is not None and (isinstance(value["current_delivery_pr"], bool) or not isinstance(value["current_delivery_pr"], int) or value["current_delivery_pr"] < 1):
        raise ObserverError("invalid_projection")
    if value.get("trust_ci_verdict") not in {"PASS", "FAIL", "PENDING", "UNKNOWN"} or value.get("evidence_freshness") not in {"FRESH", "STALE"} or value.get("trust_ci_status") not in {"queued", "in_progress", "completed", "UNKNOWN"} or value.get("trust_ci_conclusion") not in CHECK_CONCLUSIONS or not isinstance(value.get("trust_ci_check_name"), str) or not 1 <= len(value["trust_ci_check_name"]) <= 200:
        raise ObserverError("invalid_projection")
    if value.get("trust_ci_app_id") is not None and (isinstance(value["trust_ci_app_id"], bool) or not isinstance(value["trust_ci_app_id"], int) or value["trust_ci_app_id"] < 1):
        raise ObserverError("invalid_projection")
    enum_fields = {
        "overall": {"FRESH", "STALE", "UNAVAILABLE"}, "freshness": {"FRESH", "INCOHERENT", "STALE", "UNKNOWN"},
        "implemented": {"EVIDENCE_CLAIMED", "STALE", "UNKNOWN"}, "reviewed": {"EVIDENCE_CLAIMED", "STALE", "UNKNOWN"},
        "project_state": {"CLAIM_MATCH", "STALE_SNAPSHOT"}, "reference": {"CLAIM_MATCH", "STALE_REFERENCE"},
        "check_verified": {"VERIFIED", "UNKNOWN"}, "delivered": {"DELIVERED", "UNKNOWN"},
        "released": {"RELEASE_CURRENT", "RELEASE_BEHIND", "UNKNOWN"}, "attestation": {"ATTESTATION_UNOBSERVABLE"},
        "check_reference": {"REFERENCED_NOT_VERIFIED", "NONE"}, "pr_state": {"open", "closed", "UNKNOWN"},
    }
    if any(value.get(key) not in allowed for key, allowed in enum_fields.items()) or value.get("trust_ci_failed_step") not in {None, "root-unittest"}:
        raise ObserverError("invalid_projection")
    if not isinstance(value.get("findings"), list) or len(value["findings"]) > 12 or not isinstance(value.get("milestones"), list) or len(value["milestones"]) > 10 or not isinstance(value.get("observation"), dict):
        raise ObserverError("invalid_projection")
    finding_codes = {"snapshot_incoherent", "project_state_stale", "reference_stale", "check_unverified", "delivery_unproven", "release_unproven", "rate_limited", "timeout", "deadline", "github_unavailable", "observation_invalid"}
    if len(set(value["findings"])) != len(value["findings"]) or any(item not in finding_codes for item in value["findings"]):
        raise ObserverError("invalid_projection")
    milestone_keys = {"id", "claim_status", "implemented", "reviewed", "delivery", "trust", "release", "freshness", "claimed_sha", "claimed_reviewed_sha", "evidence_digest"}
    for item in value["milestones"]:
        if not isinstance(item, dict) or set(item) != milestone_keys or not re.fullmatch(r"M[0-9]", str(item.get("id"))) or item.get("claim_status") not in {"evidence_claimed", "historical_evidence_claimed"}:
            raise ObserverError("invalid_projection")
        for key in ("claimed_sha", "claimed_reviewed_sha"):
            if item.get(key) is not None and not SHA_RE.fullmatch(str(item[key])):
                raise ObserverError("invalid_projection")
        if item.get("evidence_digest") is not None and not re.fullmatch(r"[0-9a-f]{64}", str(item["evidence_digest"])):
            raise ObserverError("invalid_projection")
    observation = value["observation"]
    if observation:
        observation_keys = {"subject_digest", "freshness_seconds", "opening_main", "closing_main", "opening_pr", "closing_pr", "check", "delivery_valid", "release_commit", "release_behind"}
        if set(observation) != observation_keys or not isinstance(observation.get("check"), dict) or set(observation["check"]) != {"name", "app_id", "status", "conclusion", "verdict", "sha", "referenced", "failed_step"}:
            raise ObserverError("invalid_projection")
        check_row = observation["check"]
        if check_row.get("verdict") not in {"PASS", "FAIL", "PENDING", "UNKNOWN"} or check_row.get("status") not in {"queued", "in_progress", "completed", "UNKNOWN"} or check_row.get("conclusion") not in CHECK_CONCLUSIONS or not isinstance(check_row.get("referenced"), bool):
            raise ObserverError("invalid_projection")
        pr_keys = {"number", "state", "draft", "merged", "base_ref", "base_sha", "head_sha", "merge_commit_sha"}
        for pr_row in (observation.get("opening_pr"), observation.get("closing_pr")):
            if not isinstance(pr_row, dict) or set(pr_row) != pr_keys or pr_row.get("state") not in {"open", "closed"} or not isinstance(pr_row.get("draft"), bool) or not isinstance(pr_row.get("merged"), bool):
                raise ObserverError("invalid_projection")
    unsigned = dict(value)
    digest = unsigned.pop("digest", None)
    if not isinstance(digest, str) or hashlib.sha256(canonical_bytes(unsigned)).hexdigest() != digest:
        raise ObserverError("invalid_projection")
    return value


@contextlib.contextmanager
def _lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    except OSError as exc:
        raise ObserverError("observer_busy") from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ObserverError("observer_busy")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ObserverError("observer_busy") from exc
        yield
    finally:
        os.close(fd)


def _dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ObserverError("invalid_response")
    return value


def _pr_identity(value: object, expected_number: int) -> dict[str, Any]:
    row = _dict(value)
    base = _dict(row.get("base"))
    head = _dict(row.get("head"))
    number = row.get("number")
    state_value = row.get("state")
    draft = row.get("draft")
    merged = row.get("merged")
    base_ref = base.get("ref")
    if number != expected_number or state_value not in {"open", "closed"} or not isinstance(draft, bool) or not isinstance(merged, bool) or not isinstance(base_ref, str) or not 1 <= len(base_ref) <= 100:
        raise ObserverError("invalid_response")
    merge = row.get("merge_commit_sha")
    if merge is not None:
        merge = _sha(merge)
    return {"number": number, "state": state_value, "draft": draft, "merged": merged, "base_ref": base_ref, "base_sha": _sha(base.get("sha")), "head_sha": _sha(head.get("sha")), "merge_commit_sha": merge}


def _check_identity(value: object, expected_name: str, expected_app: int, head: str) -> dict[str, Any]:
    document = _dict(value)
    rows = document.get("check_runs")
    total = document.get("total_count")
    if isinstance(total, bool) or not isinstance(total, int) or total < 0 or not isinstance(rows, list) or len(rows) > MAX_CHECKS or total != len(rows):
        raise ObserverError("invalid_response")
    matching = [row for row in rows if isinstance(row, dict) and row.get("name") == expected_name]
    if len(matching) != 1:
        return {"name": expected_name, "app_id": None, "status": "UNKNOWN", "conclusion": None, "verdict": "UNKNOWN", "sha": None, "referenced": False, "failed_step": None}
    row = matching[0]
    app = _dict(row.get("app"))
    app_id = app.get("id")
    row_head = _sha(row.get("head_sha"))
    status_value = row.get("status")
    conclusion = row.get("conclusion")
    if isinstance(app_id, bool) or not isinstance(app_id, int) or app_id < 1 or app_id != expected_app or row_head != head or status_value not in {"queued", "in_progress", "completed"} or conclusion not in CHECK_CONCLUSIONS:
        return {"name": expected_name, "app_id": app_id if isinstance(app_id, int) and not isinstance(app_id, bool) else None, "status": status_value if status_value in {"queued", "in_progress", "completed"} else "UNKNOWN", "conclusion": conclusion if conclusion in CHECK_CONCLUSIONS else None, "verdict": "UNKNOWN", "sha": row_head, "referenced": bool(row.get("details_url")), "failed_step": None}
    verdict = "PASS" if status_value == "completed" and conclusion == "success" else ("FAIL" if status_value == "completed" and conclusion not in {None, "neutral", "skipped"} else "PENDING")
    output = row.get("output")
    recognized = None
    if verdict == "FAIL" and isinstance(output, dict):
        bounded = " ".join(str(output.get(key, ""))[:200] for key in ("title", "summary")).lower()
        if "root-unittest" in bounded:
            recognized = "root-unittest"
    return {"name": expected_name, "app_id": expected_app, "status": status_value, "conclusion": conclusion, "verdict": verdict, "sha": row_head, "referenced": bool(row.get("details_url")), "failed_step": recognized}


def _compare(value: object, base: str, head: str) -> bool:
    row = _dict(value)
    status_value = row.get("status")
    ahead = row.get("ahead_by")
    behind = row.get("behind_by")
    commits = row.get("commits")
    if status_value not in {"identical", "ahead", "behind", "diverged"} or isinstance(ahead, bool) or not isinstance(ahead, int) or isinstance(behind, bool) or not isinstance(behind, int):
        return False
    if ahead < 0 or behind < 0 or not isinstance(commits, list) or len(commits) > MAX_COMMITS:
        return False
    try:
        base_seen = _sha(_dict(row.get("base_commit"))["sha"])
        merge_base = _sha(_dict(row.get("merge_base_commit"))["sha"])
        candidates = [_sha(_dict(item)["sha"]) for item in commits]
    except (KeyError, ObserverError):
        return False
    if base_seen != base or merge_base != base:
        return False
    if status_value == "identical":
        return ahead == 0 and behind == 0 and base == head and not candidates
    return status_value == "ahead" and ahead > 0 and behind == 0 and candidates and candidates[-1] == head


def _resolve_tag(transport: Any, repo: str, tag: str) -> str:
    if not isinstance(tag, str) or not re.fullmatch(r"[A-Za-z0-9._+-]{1,128}", tag):
        raise ObserverError("invalid_release")
    ref = _dict(transport.get(f"/repos/{repo}/git/ref/tags/{urllib.parse.quote(tag, safe='')}"))
    if ref.get("ref") != f"refs/tags/{tag}":
        raise ObserverError("invalid_release")
    obj = _dict(ref.get("object"))
    visited: set[str] = set()
    for _ in range(MAX_TAG_DEPTH):
        sha = _sha(obj.get("sha"))
        kind = obj.get("type")
        if kind == "commit":
            return sha
        if kind != "tag" or sha in visited:
            raise ObserverError("invalid_release")
        visited.add(sha)
        document = _dict(transport.get(f"/repos/{repo}/git/tags/{sha}"))
        if _sha(document.get("sha")) != sha:
            raise ObserverError("invalid_release")
        obj = _dict(document.get("object"))
    raise ObserverError("invalid_release")


def project_status(observation: dict[str, Any], claims_raw: object, *, now: int) -> dict[str, Any]:
    claims, project, candidate = _claim_context(claims_raw)
    live_pr = observation.get("opening_pr") if isinstance(observation.get("opening_pr"), dict) else {}
    project_fresh = project is not None and 0 <= now - _epoch(project.get("observed_at")) <= observation.get("freshness_seconds", 0)
    candidate_fresh = candidate is not None and 0 <= now - _epoch(candidate.get("observed_at")) <= observation.get("freshness_seconds", 0)
    project_match = project_fresh and project.get("observed_main_sha") == observation.get("opening_main")
    referenced = candidate.get("referenced_pr") if candidate else None
    reference_match = candidate_fresh and isinstance(referenced, dict) and observation.get("opening_pr") == observation.get("closing_pr") and referenced == {"number": live_pr.get("number"), "state": live_pr.get("state"), "base_ref": live_pr.get("base_ref"), "head_sha": live_pr.get("head_sha")}
    head = live_pr.get("head_sha")
    implementation = "EVIDENCE_CLAIMED" if candidate_fresh and candidate.get("implementation_sha") == head else ("STALE" if candidate else "UNKNOWN")
    reviewed = "EVIDENCE_CLAIMED" if candidate_fresh and candidate.get("reviewed_sha") == head else ("STALE" if candidate else "UNKNOWN")
    remote_coherent = observation.get("opening_main") == observation.get("closing_main") and observation.get("opening_pr") == observation.get("closing_pr")
    coherent = remote_coherent and project_match and reference_match and implementation != "STALE" and reviewed != "STALE"
    check_identity = observation.get("check") if isinstance(observation.get("check"), dict) else {}
    trust_verdict = check_identity.get("verdict", "UNKNOWN")
    check = "VERIFIED" if trust_verdict == "PASS" else "UNKNOWN"
    delivered = "DELIVERED" if remote_coherent and observation.get("delivery_valid") else "UNKNOWN"
    released = "RELEASE_CURRENT" if remote_coherent and observation.get("release_commit") == observation.get("opening_main") else ("RELEASE_BEHIND" if remote_coherent and observation.get("release_behind") else "UNKNOWN")
    findings = []
    for condition, code in ((not coherent, "snapshot_incoherent"), (not project_match, "project_state_stale"), (not reference_match, "reference_stale"), (check != "VERIFIED", "check_unverified"), (delivered != "DELIVERED", "delivery_unproven"), (released == "UNKNOWN", "release_unproven")):
        if condition:
            findings.append(code)
    result = {
        "schema_version": 1,
        "kind": "PUBLIC_STATUS.v1",
        "generated_at_epoch": now,
        "observation_epoch": now,
        "subject_digest": observation.get("subject_digest", "0" * 64),
        "snapshot_age_seconds": 0,
        "main_sha": observation.get("opening_main"),
        "current_delivery_pr": live_pr.get("number"),
        "pr_state": live_pr.get("state"),
        "pr_head_sha": head,
        "reviewed_sha": candidate.get("reviewed_sha") if candidate else None,
        "trust_ci_check_name": check_identity.get("name", "UNKNOWN"),
        "trust_ci_app_id": check_identity.get("app_id"),
        "trust_ci_sha": check_identity.get("sha"),
        "trust_ci_status": check_identity.get("status", "UNKNOWN"),
        "trust_ci_conclusion": check_identity.get("conclusion"),
        "trust_ci_verdict": trust_verdict,
        "trust_ci_failed_step": check_identity.get("failed_step"),
        "release_sha": observation.get("release_commit"),
        "evidence_freshness": "FRESH" if candidate_fresh else "STALE",
        "overall": "FRESH" if coherent else "STALE",
        "freshness": "FRESH" if coherent else "INCOHERENT",
        "implemented": implementation,
        "reviewed": reviewed,
        "project_state": "CLAIM_MATCH" if project_match else "STALE_SNAPSHOT",
        "reference": "CLAIM_MATCH" if reference_match else "STALE_REFERENCE",
        "check_verified": check,
        "delivered": delivered,
        "released": released,
        "attestation": "ATTESTATION_UNOBSERVABLE",
        "check_reference": "REFERENCED_NOT_VERIFIED" if check_identity.get("referenced") else "NONE",
        "findings": findings,
        "milestones": [{"id": item.id, "claim_status": item.claim_status, "implemented": "EVIDENCE_CLAIMED" if item.sha else "UNKNOWN", "reviewed": "EVIDENCE_CLAIMED" if item.reviewed_sha else "UNKNOWN", "delivery": "UNKNOWN", "trust": "UNKNOWN", "release": "UNKNOWN", "freshness": "HISTORICAL", "claimed_sha": item.sha, "claimed_reviewed_sha": item.reviewed_sha, "evidence_digest": item.digest} for item in claims],
        "observation": observation,
    }
    unsigned = canonical_bytes(result)
    result["digest"] = hashlib.sha256(unsigned).hexdigest()
    return validate_status(result)


def render_text(status_value: dict[str, Any]) -> str:
    status_value = validate_status(status_value)
    fields = ("overall", "freshness", "implemented", "reviewed", "check_verified", "delivered", "released", "attestation")
    return "PUBLIC_STATUS.v1\n" + "\n".join(f"{key}: {status_value[key]}" for key in fields) + f"\ndigest: {status_value['digest']}\n"


def load_document(path: Path, *, error: str) -> object:
    try:
        value = _read_json(path)
    except ObserverError as exc:
        raise ObserverError(error) from exc
    if value is None:
        raise ObserverError(error)
    return value


def load_status(root: Path) -> dict[str, Any]:
    value = _read_json(_safe_runtime(root) / "state.json")
    if not isinstance(value, dict) or value.get("schema_version") != 1 or not isinstance(value.get("status"), dict):
        raise ObserverError("invalid_state")
    return _validate_cached_status(value["status"])


class ExternalObserver:
    def __init__(self, root: Path, config_raw: object, claims_raw: object, transport: Any) -> None:
        self.root = root
        self.config = parse_config(config_raw)
        self.claims = claims_raw
        self.transport = transport
        self.runtime = root / ".grok-stack/runtime/external-observer"
        self.calls = 0

    def get(self, path: str) -> object:
        self.calls += 1
        if self.calls > MAX_CALLS:
            raise ObserverError("call_limit")
        return self.transport.get(path)

    def _observe(self) -> dict[str, Any]:
        cfg = self.config
        repo = cfg.repository
        prefix = f"/repos/{repo}"
        main_open = _sha(_dict(self.get(f"{prefix}/commits/{cfg.default_branch}")).get("sha"))
        pr_identity = _pr_identity(self.get(f"{prefix}/pulls/{cfg.pull_request_number}"), cfg.pull_request_number)
        head = pr_identity["head_sha"]
        check_identity = _check_identity(self.get(f"{prefix}/commits/{head}/check-runs?per_page=100"), cfg.expected_check_name, cfg.expected_app_id, head)
        release = _dict(self.get(f"{prefix}/releases/latest"))
        if release.get("draft") is not False or release.get("prerelease") is not False:
            raise ObserverError("invalid_release")
        release_commit = _resolve_tag(self, repo, release.get("tag_name"))
        release_compare = self.get(f"{prefix}/compare/{release_commit}...{main_open}?per_page=100&page=1")
        release_behind = _compare(release_compare, release_commit, main_open)
        merge = pr_identity.get("merge_commit_sha")
        delivery_valid = False
        if pr_identity["number"] == cfg.pull_request_number and pr_identity["state"] == "closed" and pr_identity["merged"] is True and pr_identity["draft"] is False and pr_identity["base_ref"] == cfg.default_branch and pr_identity["base_sha"] == main_open and isinstance(merge, str) and SHA_RE.fullmatch(merge):
            delivery_valid = _compare(self.get(f"{prefix}/compare/{merge}...{main_open}?per_page=100&page=1"), merge, main_open)
        main_close = _sha(_dict(self.get(f"{prefix}/commits/{cfg.default_branch}")).get("sha"))
        pr_close = _pr_identity(self.get(f"{prefix}/pulls/{cfg.pull_request_number}"), cfg.pull_request_number)
        subject = {"repository": repo, "default_branch": cfg.default_branch, "pull_request_number": cfg.pull_request_number, "expected_check_name": cfg.expected_check_name, "expected_app_id": cfg.expected_app_id}
        return {"subject_digest": hashlib.sha256(canonical_bytes(subject)).hexdigest(), "freshness_seconds": cfg.freshness_seconds, "opening_main": main_open, "closing_main": main_close, "opening_pr": pr_identity, "closing_pr": pr_close, "check": check_identity, "delivery_valid": delivery_valid, "release_commit": release_commit, "release_behind": release_behind}

    def check(self, *, now: int) -> dict[str, Any]:
        self.runtime = _safe_runtime(self.root)
        state_path = self.runtime / "state.json"
        with _lock(self.runtime / ".observer.lock"):
            prior = _read_json(state_path)
            if prior is not None:
                if not isinstance(prior, dict) or set(prior) != {"schema_version", "status"} or prior.get("schema_version") != 1:
                    raise ObserverError("invalid_state")
                _validate_cached_status(prior.get("status"))
            try:
                self.calls = 0
                observation = self._observe()
                status_value = project_status(observation, self.claims, now=now)
                _atomic_json(state_path, {"schema_version": 1, "status": status_value})
                return status_value
            except (ObserverError, TransportError) as exc:
                code = str(exc) if str(exc) in {"rate_limited", "timeout", "deadline", "github_unavailable"} else "observation_invalid"
                if prior is None:
                    empty = {"schema_version": 1, "kind": "PUBLIC_STATUS.v1", "generated_at_epoch": now, "observation_epoch": now, "subject_digest": "0" * 64, "snapshot_age_seconds": 0, "main_sha": None, "current_delivery_pr": None, "pr_state": "UNKNOWN", "pr_head_sha": None, "reviewed_sha": None, "trust_ci_check_name": self.config.expected_check_name, "trust_ci_app_id": None, "trust_ci_sha": None, "trust_ci_status": "UNKNOWN", "trust_ci_conclusion": None, "trust_ci_verdict": "UNKNOWN", "trust_ci_failed_step": None, "release_sha": None, "evidence_freshness": "STALE", "overall": "UNAVAILABLE", "freshness": "UNKNOWN", "implemented": "UNKNOWN", "reviewed": "UNKNOWN", "project_state": "STALE_SNAPSHOT", "reference": "STALE_REFERENCE", "check_verified": "UNKNOWN", "delivered": "UNKNOWN", "released": "UNKNOWN", "attestation": "ATTESTATION_UNOBSERVABLE", "check_reference": "NONE", "findings": [code], "milestones": [], "observation": {}, "error": code}
                    empty["digest"] = hashlib.sha256(canonical_bytes(empty)).hexdigest()
                    validate_status(empty)
                    _atomic_json(state_path, {"schema_version": 1, "status": empty})
                    return empty
                stale = dict(prior["status"])
                if stale["overall"] == "UNAVAILABLE":
                    stale.update({"snapshot_age_seconds": max(0, now - stale["observation_epoch"]), "generated_at_epoch": now, "error": code})
                else:
                    stale.update({"snapshot_age_seconds": max(0, now - stale["observation_epoch"]), "generated_at_epoch": now, "overall": "STALE", "freshness": "STALE", "error": code})
                stale["findings"] = list(dict.fromkeys([*stale["findings"], code]))[-12:]
                stale.pop("digest", None)
                stale["digest"] = hashlib.sha256(canonical_bytes(stale)).hexdigest()
                validate_status(stale)
                _atomic_json(state_path, {"schema_version": 1, "status": stale})
                return stale
