from __future__ import annotations

import json
import os
import re
import stat
import subprocess
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
    if isinstance(value, str) and len(value) > MAX_STRING:
        fail("spec string limit exceeded")
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
    path = root.joinpath(*Path(rel).parts)
    try:
        info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(info.st_mode):
            fail(f"{rel}: spec must be a regular non-symlink file")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            opened = os.fstat(fd)
            if (info.st_dev, info.st_ino) != (opened.st_dev, opened.st_ino) or opened.st_size > MAX_BYTES:
                fail(f"{rel}: unsafe or oversized spec")
            data = os.read(fd, MAX_BYTES + 1)
        finally:
            os.close(fd)
    except FileNotFoundError:
        fail(f"{rel}: changed spec was deleted")
    except OSError as exc:
        fail(f"{rel}: cannot read spec: {exc}")
    if len(data) > MAX_BYTES:
        fail(f"{rel}: oversized spec")
    return data


def _parse(rel: str, data: bytes) -> dict[str, Any]:
    if data.startswith(b"\xef\xbb\xbf"):
        fail(f"{rel}: BOM is forbidden")
    try:
        value = json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=_pairs, parse_constant=_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"{rel}: invalid canonical JSON: {exc}")
    if not isinstance(value, dict):
        fail(f"{rel}: spec root must be an object")
    _walk(value)
    return value


def _required_object(value: Any, rel: str, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{rel}: {field} must be an object")
    return value


def _items(spec: dict[str, Any], rel: str, field: str) -> list[dict[str, Any]]:
    value = spec.get(field)
    if not isinstance(value, list) or len(value) > 500:
        fail(f"{rel}: {field} must be a bounded array")
    if not all(isinstance(item, dict) for item in value):
        fail(f"{rel}: {field} items must be objects")
    return value


def _validate_document(rel: str, spec: dict[str, Any]) -> None:
    required = {"schema_version", "change_id", "objective", "risk", "acceptance_criteria", "invariants", "forbidden_outcomes", "contracts", "observability", "rollback", "approvals"}
    if set(spec) != required or spec.get("schema_version") != 2:
        fail(f"{rel}: strict schema_version 2 top-level contract required")
    objective = _required_object(spec["objective"], rel, "objective")
    if not ID_PATTERNS["objective"].fullmatch(str(objective.get("id", ""))):
        fail(f"{rel}: invalid objective ID")
    if objective.get("success_metric") == "UNKNOWN" or objective.get("target") == "UNKNOWN":
        fail(f"{rel}: UNKNOWN objective fields are forbidden at holdout gate")
    risk = _required_object(spec["risk"], rel, "risk")
    if risk.get("tier") not in {"green", "yellow", "red"}:
        fail(f"{rel}: invalid risk tier")
    all_ids: set[str] = {str(objective["id"])}
    signals: set[str] = set()
    for item in _items(spec, rel, "observability"):
        signal_id = str(item.get("id", ""))
        if not ID_PATTERNS["observability"].fullmatch(signal_id) or signal_id in signals:
            fail(f"{rel}: invalid or duplicate signal ID")
        signals.add(signal_id)
    criteria = _items(spec, rel, "acceptance_criteria")
    if not criteria:
        fail(f"{rel}: at least one acceptance criterion is required")
    for field in ("acceptance_criteria", "invariants", "forbidden_outcomes"):
        for item in _items(spec, rel, field):
            item_id = str(item.get("id", ""))
            if not ID_PATTERNS[field].fullmatch(item_id) or item_id in all_ids:
                fail(f"{rel}: invalid or duplicate {field} ID")
            all_ids.add(item_id)
            evidence = item.get("evidence")
            if field == "acceptance_criteria" and (not isinstance(evidence, list) or not evidence):
                fail(f"{rel}: acceptance criterion {item_id} has no evidence")
            for ref in evidence or []:
                if not isinstance(ref, dict) or len(ref) != 1 or next(iter(ref)) not in EVIDENCE_KEYS:
                    fail(f"{rel}: evidence must have exactly one supported key")
                if "production_signal" in ref and ref["production_signal"] not in signals:
                    fail(f"{rel}: unresolved production signal")
    approvals = _required_object(spec["approvals"], rel, "approvals")
    if risk.get("tier") == "red" and (not spec["forbidden_outcomes"] or not approvals.get("required_scopes")):
        fail(f"{rel}: red risk requires forbidden outcomes and approval scopes")
    _required_object(spec["contracts"], rel, "contracts")
    rollback = _required_object(spec["rollback"], rel, "rollback")
    if rollback.get("strategy") not in {"feature_flag", "forward_fix", "restore", "migration_reversal"}:
        fail(f"{rel}: invalid rollback strategy")


def validate(root: Path, *, base_sha: str | None = None, head_sha: str | None = None) -> None:
    root = root.resolve(strict=True)
    base, head = _exact_shas(root, base_sha, head_sha)
    for rel in _changed_specs(root, base, head):
        _validate_document(rel, _parse(rel, _read(root, rel)))
