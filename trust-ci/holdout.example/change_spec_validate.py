from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

MAX_BYTES = 1_000_000
MAX_FILES = 100
MAX_DEPTH = 64
MAX_NODES = 20_000
MAX_STRING = 65_536
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SPEC_RE = re.compile(r"^engineering/changes/[^/]+/change-spec\.yaml$")
ID_PATTERNS = {
    "objective": re.compile(r"^OBJ-[0-9]{3,6}$"),
    "acceptance_criteria": re.compile(r"^AC-[0-9]{3,6}$"),
    "invariants": re.compile(r"^INV-[0-9]{3,6}$"),
    "forbidden_outcomes": re.compile(r"^FORBID-[0-9]{3,6}$"),
    "observability": re.compile(r"^SIG-[0-9]{3,6}$"),
}
EVIDENCE_KEYS = {"test", "receipt", "production_signal", "attestation"}
RECEIPT_KINDS = {"verification", "code_review", "test_review", "security_review", "release_review"}
TEST_RE = re.compile(r"^[A-Za-z0-9_./:-]+$")
ATTESTATION_RE = re.compile(r"^[A-Za-z0-9_.:@/-]+$")
SCOPE_RE = re.compile(r"^[a-z][a-z0-9_-]{0,127}$")
CHANGE_RE = re.compile(r"^[0-9]{8}-[A-Za-z0-9\u0400-\u04FF][A-Za-z0-9._:\u0400-\u04FF-]{2,120}$")


def fail(message: str) -> None:
    raise SystemExit(message)


def _constant(value: str) -> None:
    fail(f"non-finite JSON number: {value}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _walk(value: Any, depth: int = 0, count: list[int] | None = None) -> None:
    count = count or [0]
    count[0] += 1
    if count[0] > MAX_NODES or depth > MAX_DEPTH:
        fail("spec structural limit exceeded")
    if isinstance(value, str):
        if len(value) > MAX_STRING:
            fail("spec string limit exceeded")
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            fail("unpaired Unicode surrogate is forbidden")
    if isinstance(value, dict):
        for key, item in value.items():
            _walk(key, depth + 1, count)
            _walk(item, depth + 1, count)
    elif isinstance(value, list):
        for item in value:
            _walk(item, depth + 1, count)


def _git(root: Path, *args: str) -> bytes:
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True, timeout=30, check=False)
    if proc.returncode != 0:
        fail(f"git {' '.join(args[:2])} failed")
    return proc.stdout


def _exact_shas(root: Path, base_sha: str | None, head_sha: str | None) -> tuple[str, str]:
    base = str(base_sha or os.environ.get("TRUST_CI_BASE_SHA", "")).strip()
    head = str(head_sha or os.environ.get("TRUST_CI_HEAD_SHA", "")).strip()
    if not SHA_RE.fullmatch(base) or not SHA_RE.fullmatch(head):
        fail("exact TRUST_CI_BASE_SHA and TRUST_CI_HEAD_SHA are required")
    _git(root, "cat-file", "-e", f"{base}^{{commit}}")
    _git(root, "cat-file", "-e", f"{head}^{{commit}}")
    actual = _git(root, "rev-parse", "HEAD").decode("ascii", errors="strict").strip()
    if actual != head:
        fail("workspace HEAD does not equal TRUST_CI_HEAD_SHA")
    return base, head


def _changed_specs(root: Path, base: str, head: str) -> list[str]:
    raw = _git(root, "diff", "--name-only", "-z", base, head, "--")
    try:
        paths = [item.decode("utf-8", errors="strict") for item in raw.split(b"\0") if item]
    except UnicodeDecodeError:
        fail("changed path is not UTF-8")
    selected = sorted(path for path in paths if SPEC_RE.fullmatch(path))
    if len(selected) > MAX_FILES:
        fail("changed spec count limit exceeded")
    return selected


def _read(root: Path, rel: str) -> bytes:
    parts = Path(rel).parts
    if not parts or Path(rel).is_absolute() or any(part in {"", ".", ".."} for part in parts):
        fail(f"{rel}: unsafe spec path")
    descriptors: list[int] = []
    try:
        current = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        descriptors.append(current)
        for part in parts[:-1]:
            current = os.open(
                part,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=current,
            )
            descriptors.append(current)
        fd = os.open(parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=current)
        descriptors.append(fd)
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > MAX_BYTES:
            fail(f"{rel}: unsafe or oversized spec")
        chunks: list[bytes] = []
        remaining = MAX_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(fd)
        before_identity = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)
        after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        if len(data) != opened.st_size or after_identity != before_identity:
            fail(f"{rel}: spec changed while reading")
    except FileNotFoundError:
        fail(f"{rel}: changed spec was deleted")
    except OSError as exc:
        fail(f"{rel}: cannot read spec: {exc}")
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    if len(data) > MAX_BYTES:
        fail(f"{rel}: oversized spec")
    return data


def _parse(rel: str, data: bytes) -> dict[str, Any]:
    if data.startswith(b"\xef\xbb\xbf"):
        fail(f"{rel}: BOM is forbidden")
    try:
        value = json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=_pairs, parse_constant=_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        fail(f"{rel}: invalid canonical JSON: {exc}")
    if not isinstance(value, dict):
        fail(f"{rel}: spec root must be an object")
    _walk(value)
    return value


def _required_object(value: Any, rel: str, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{rel}: {field} must be an object")
    return value


def _exact_object(value: Any, rel: str, field: str, keys: set[str]) -> dict[str, Any]:
    result = _required_object(value, rel, field)
    if set(result) != keys:
        fail(f"{rel}: {field} must contain exactly {sorted(keys)}")
    return result


def _text(value: Any, rel: str, field: str, *, maximum: int, pattern: re.Pattern[str] | None = None) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum or (pattern and not pattern.fullmatch(value)):
        fail(f"{rel}: invalid {field}")
    return value


def _string_array(value: Any, rel: str, field: str, *, maximum: int, item_maximum: int = 512, pattern: re.Pattern[str] | None = None) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        fail(f"{rel}: {field} must be a bounded unique array")
    for item in value:
        _text(item, rel, field, maximum=item_maximum, pattern=pattern)
    if len(value) != len(set(value)):
        fail(f"{rel}: {field} must be a bounded unique array")
    return value


def _safe_contract(value: str, rel: str) -> None:
    path = Path(value)
    unsafe_character = any(
        unicodedata.category(character) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for character in value
    )
    if unsafe_character or path.is_absolute() or not value or "\\" in value or any(part in {"", ".", ".."} for part in path.parts):
        fail(f"{rel}: unsafe contract path")


def _evidence(value: Any, rel: str, signals: set[str]) -> None:
    if not isinstance(value, dict) or len(value) != 1:
        fail(f"{rel}: evidence must have exactly one supported key")
    key, scalar = next(iter(value.items()))
    if key not in EVIDENCE_KEYS:
        fail(f"{rel}: evidence must have exactly one supported key")
    if key == "test":
        _text(scalar, rel, "test evidence", maximum=512, pattern=TEST_RE)
    elif key == "receipt":
        if not isinstance(scalar, str) or scalar not in RECEIPT_KINDS:
            fail(f"{rel}: invalid receipt evidence")
    elif key == "production_signal":
        if not isinstance(scalar, str) or not ID_PATTERNS["observability"].fullmatch(scalar) or scalar not in signals:
            fail(f"{rel}: unresolved production signal")
    else:
        _text(scalar, rel, "attestation evidence", maximum=128, pattern=ATTESTATION_RE)


def _items(spec: dict[str, Any], rel: str, field: str) -> list[dict[str, Any]]:
    value = spec.get(field)
    if not isinstance(value, list) or len(value) > 500:
        fail(f"{rel}: {field} must be a bounded array")
    if not all(isinstance(item, dict) for item in value):
        fail(f"{rel}: {field} items must be objects")
    return value


def _validate_document(rel: str, spec: dict[str, Any]) -> None:
    _walk(spec)
    required = {"schema_version", "change_id", "objective", "risk", "acceptance_criteria", "invariants", "forbidden_outcomes", "contracts", "observability", "rollback", "approvals"}
    if set(spec) != required or spec.get("schema_version") != 2:
        fail(f"{rel}: strict schema_version 2 top-level contract required")
    if not isinstance(spec.get("change_id"), str) or not CHANGE_RE.fullmatch(spec["change_id"]):
        fail(f"{rel}: invalid change_id")
    objective = _exact_object(spec["objective"], rel, "objective", {"id", "statement", "success_metric", "target"})
    if not ID_PATTERNS["objective"].fullmatch(str(objective.get("id", ""))):
        fail(f"{rel}: invalid objective ID")
    for field, maximum in (("statement", 4096), ("success_metric", 512), ("target", 512)):
        _text(objective.get(field), rel, f"objective.{field}", maximum=maximum)
    if objective.get("success_metric") == "UNKNOWN" or objective.get("target") == "UNKNOWN":
        fail(f"{rel}: UNKNOWN objective fields are forbidden at holdout gate")
    risk = _exact_object(spec["risk"], rel, "risk", {"tier", "domains"})
    if risk.get("tier") not in {"green", "yellow", "red"}:
        fail(f"{rel}: invalid risk tier")
    _string_array(risk.get("domains"), rel, "risk.domains", maximum=50, item_maximum=128)
    all_ids: set[str] = {str(objective["id"])}
    signals: set[str] = set()
    for item in _items(spec, rel, "observability"):
        if set(item) != {"id", "metric", "proves"}:
            fail(f"{rel}: invalid observability item")
        signal_id = item.get("id")
        if not isinstance(signal_id, str):
            fail(f"{rel}: invalid signal ID")
        if not ID_PATTERNS["observability"].fullmatch(signal_id) or signal_id in signals:
            fail(f"{rel}: invalid or duplicate signal ID")
        _text(item.get("metric"), rel, "observability.metric", maximum=512)
        proves = _string_array(item.get("proves"), rel, "observability.proves", maximum=500, pattern=ID_PATTERNS["objective"])
        if not proves or set(proves) != {objective["id"]}:
            fail(f"{rel}: observability.proves must resolve the objective")
        signals.add(signal_id)
    criteria = _items(spec, rel, "acceptance_criteria")
    if not criteria:
        fail(f"{rel}: at least one acceptance criterion is required")
    for field in ("acceptance_criteria", "invariants", "forbidden_outcomes"):
        for item in _items(spec, rel, field):
            if set(item) != {"id", "statement", "evidence"}:
                fail(f"{rel}: invalid {field} item")
            item_id = item.get("id")
            if not isinstance(item_id, str):
                fail(f"{rel}: invalid {field} ID")
            if not ID_PATTERNS[field].fullmatch(item_id) or item_id in all_ids:
                fail(f"{rel}: invalid or duplicate {field} ID")
            _text(item.get("statement"), rel, f"{field}.statement", maximum=4096)
            all_ids.add(item_id)
            evidence = item.get("evidence")
            if not isinstance(evidence, list) or len(evidence) > 50:
                fail(f"{rel}: invalid evidence array")
            if field == "acceptance_criteria" and not evidence:
                fail(f"{rel}: acceptance criterion {item_id} has no evidence")
            for ref in evidence:
                _evidence(ref, rel, signals)
    approvals = _exact_object(spec["approvals"], rel, "approvals", {"required_scopes"})
    scopes = _string_array(approvals.get("required_scopes"), rel, "approvals.required_scopes", maximum=50, item_maximum=128, pattern=SCOPE_RE)
    if risk.get("tier") == "red" and (not spec["forbidden_outcomes"] or not scopes):
        fail(f"{rel}: red risk requires forbidden outcomes and approval scopes")
    contracts = _exact_object(spec["contracts"], rel, "contracts", {"openapi", "json_schema", "events"})
    for name, values in contracts.items():
        for value in _string_array(values, rel, f"contracts.{name}", maximum=100):
            _safe_contract(value, rel)
    rollback = _exact_object(spec["rollback"], rel, "rollback", {"strategy", "maximum_steps"})
    if rollback.get("strategy") not in {"feature_flag", "forward_fix", "restore", "migration_reversal"}:
        fail(f"{rel}: invalid rollback strategy")
    maximum_steps = rollback.get("maximum_steps")
    if isinstance(maximum_steps, bool) or not isinstance(maximum_steps, int) or not 1 <= maximum_steps <= 20:
        fail(f"{rel}: invalid rollback maximum_steps")


def validate(root: Path, *, base_sha: str | None = None, head_sha: str | None = None) -> None:
    root = root.resolve(strict=True)
    base, head = _exact_shas(root, base_sha, head_sha)
    for rel in _changed_specs(root, base, head):
        _validate_document(rel, _parse(rel, _read(root, rel)))
