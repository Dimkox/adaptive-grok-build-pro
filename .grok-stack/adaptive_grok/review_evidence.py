from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any


MAX_REPORT_BYTES = 512 * 1024
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_CLAIMS = 200
MAX_CITATIONS_PER_CLAIM = 20
MAX_ARGV_ITEMS = 64
MAX_TEXT_CHARS = 8_192
REVIEW_KINDS = frozenset({"code_review", "test_review", "bitrix_review", "security_review", "data_review", "release_review"})
SUPPORTED_PROBE_SCHEMA = "adaptive_grok.architecture.unsupported_schema"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Z][A-Z0-9_-]{0,63}$")
_REVISION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class ReviewEvidenceError(ValueError):
    """A bounded review report or one of its evidence records is invalid."""


def _relative(value: Any, *, allow_dot: bool = False) -> str:
    if not isinstance(value, str) or not value or len(value) > 512 or "\x00" in value or "\\" in value:
        raise ReviewEvidenceError("report paths must be bounded normalized repository-relative paths")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or any(part in {"", "."} for part in path.parts):
        if allow_dot and value == ".":
            return value
        raise ReviewEvidenceError("report paths must be bounded normalized repository-relative paths")
    if path.as_posix() != value:
        raise ReviewEvidenceError("report paths must use normalized separators")
    return value


def _read_confined(root: Path, relative: str, limit: int, *, allow_dot: bool = False) -> bytes:
    relative = _relative(relative, allow_dot=allow_dot)
    canonical = root.resolve(strict=True)
    if relative == ".":
        return b""
    parts = PurePosixPath(relative).parts
    flags_dir = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    flags_file = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
    if not hasattr(os, "O_NOFOLLOW") or os.open not in getattr(os, "supports_dir_fd", set()):
        raise ReviewEvidenceError("descriptor-safe repository reads are unavailable")
    directory_fd: int | None = None
    file_fd: int | None = None
    try:
        directory_fd = os.open(canonical, flags_dir)
        for component in parts[:-1]:
            next_fd = os.open(component, flags_dir, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(parts[-1], flags_file, dir_fd=directory_fd)
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ReviewEvidenceError("evidence target must be a bounded regular file")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(file_fd, min(65_536, limit + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                raise ReviewEvidenceError("evidence target exceeds the byte limit")
            chunks.append(chunk)
        after = os.fstat(file_fd)
        def identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
            return (value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns, value.st_ctime_ns)

        if identity(before) != identity(after):
            raise ReviewEvidenceError("evidence target changed while being read")
        return b"".join(chunks)
    except ReviewEvidenceError:
        raise
    except OSError as exc:
        raise ReviewEvidenceError(f"cannot safely read repository evidence path {relative!r}: {exc.strerror or exc}") from exc
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory_fd is not None:
            os.close(directory_fd)


def _check_confined_directory(root: Path, relative: str, claim_id: str) -> None:
    relative = _relative(relative, allow_dot=True)
    if relative == ".":
        return
    canonical = root.resolve(strict=True)
    flags_dir = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(canonical, flags_dir)
        for component in PurePosixPath(relative).parts:
            next_descriptor = os.open(component, flags_dir, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
    except OSError as exc:
        raise ReviewEvidenceError(f"execution claim {claim_id} cwd is not a confined directory") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ReviewEvidenceError("review report contains a duplicate JSON key")
        result[key] = value
    return result


def _load_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(ReviewEvidenceError(f"invalid JSON value {token}")),
        )
    except ReviewEvidenceError:
        raise
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ReviewEvidenceError(f"{label} is not valid bounded UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ReviewEvidenceError(f"{label} must be a JSON object")
    return value


def _text(value: Any, field: str, *, optional: bool = False) -> str:
    if optional and value == "":
        return ""
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT_CHARS or "\x00" in value:
        raise ReviewEvidenceError(f"{field} must be non-empty bounded text")
    return value


def _validate_citation(root: Path, citation: Any) -> None:
    if not isinstance(citation, dict) or set(citation) != {"path", "start_line", "end_line", "span_sha256"}:
        raise ReviewEvidenceError("source citation must contain exactly path, start_line, end_line, and span_sha256")
    relative = _relative(citation["path"])
    start, end = citation["start_line"], citation["end_line"]
    if isinstance(start, bool) or not isinstance(start, int) or isinstance(end, bool) or not isinstance(end, int) or start < 1 or end < start or end - start > 500:
        raise ReviewEvidenceError(f"source citation {relative!r} has an invalid line span")
    digest = citation["span_sha256"]
    if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
        raise ReviewEvidenceError(f"source citation {relative!r} has an invalid span digest")
    raw = _read_confined(root, relative, MAX_SOURCE_BYTES)
    try:
        raw.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise ReviewEvidenceError(f"source citation {relative!r} is not UTF-8 text") from exc
    lines = raw.splitlines(keepends=True)
    if end > len(lines):
        raise ReviewEvidenceError(f"source citation {relative!r} line span exceeds current file")
    span = b"".join(lines[start - 1:end])
    if hashlib.sha256(span).hexdigest() != digest:
        raise ReviewEvidenceError(f"source citation {relative!r} span digest does not match current file")


def _validate_claims(root: Path, claims: Any) -> tuple[dict[str, Any], set[str]]:
    if not isinstance(claims, list) or not claims or len(claims) > MAX_CLAIMS:
        raise ReviewEvidenceError("claims must be a non-empty bounded array")
    ids: set[str] = set()
    basis_refs: dict[str, list[str]] = {}
    counts = {"source_citation": 0, "execution": 0, "inference": 0}
    for claim in claims:
        if not isinstance(claim, dict):
            raise ReviewEvidenceError("each claim must be a JSON object")
        claim_id, kind = claim.get("id"), claim.get("type")
        if not isinstance(claim_id, str) or not _ID.fullmatch(claim_id) or claim_id in ids:
            raise ReviewEvidenceError("claim IDs must be unique bounded stable IDs")
        ids.add(claim_id)
        _text(claim.get("statement"), f"claim {claim_id} statement")
        if kind == "source_citation":
            if set(claim) != {"id", "type", "statement", "citations"}:
                raise ReviewEvidenceError(f"source claim {claim_id} has unsupported fields")
            citations = claim["citations"]
            if not isinstance(citations, list) or not citations or len(citations) > MAX_CITATIONS_PER_CLAIM:
                raise ReviewEvidenceError(f"source claim {claim_id} requires bounded citations")
            for citation in citations:
                _validate_citation(root, citation)
            counts[kind] += len(citations)
        elif kind == "execution":
            if set(claim) != {"id", "type", "statement", "command"}:
                raise ReviewEvidenceError(f"execution claim {claim_id} has unsupported fields")
            command = claim["command"]
            if not isinstance(command, dict) or set(command) not in (
                {"argv", "cwd", "exit_code", "stdout_excerpt", "stderr_excerpt", "provenance"},
                {"argv", "cwd", "exit_code", "stdout_excerpt", "stderr_excerpt", "provenance", "probe"},
            ):
                raise ReviewEvidenceError(f"execution claim {claim_id} command record has an invalid shape")
            argv = command.get("argv")
            if not isinstance(argv, list) or not argv or len(argv) > MAX_ARGV_ITEMS:
                raise ReviewEvidenceError(f"execution claim {claim_id} argv must be a bounded argument array")
            for argument in argv:
                _text(argument, f"execution claim {claim_id} argv item")
            cwd = _relative(command.get("cwd"), allow_dot=True)
            _check_confined_directory(root, cwd, claim_id)
            exit_code = command.get("exit_code")
            if isinstance(exit_code, bool) or not isinstance(exit_code, int) or not -255 <= exit_code <= 255:
                raise ReviewEvidenceError(f"execution claim {claim_id} exit_code must be an integer")
            for field in ("stdout_excerpt", "stderr_excerpt"):
                value = command.get(field)
                if not isinstance(value, str) or len(value) > MAX_TEXT_CHARS or "\x00" in value:
                    raise ReviewEvidenceError(f"execution claim {claim_id} {field} must be bounded text")
            if command.get("provenance") != "self_reported_unverified":
                raise ReviewEvidenceError(f"execution claim {claim_id} provenance must be self_reported_unverified")
            if "probe" in command:
                probe = command["probe"]
                if not isinstance(probe, dict) or set(probe) != {"schema_id", "schema_version", "input"}:
                    raise ReviewEvidenceError(f"execution claim {claim_id} probe record has an invalid shape")
                if probe["schema_id"] != SUPPORTED_PROBE_SCHEMA:
                    raise ReviewEvidenceError(f"execution claim {claim_id} probe.schema_id is unsupported")
                if isinstance(probe["schema_version"], bool) or not isinstance(probe["schema_version"], int) or probe["schema_version"] != 1:
                    raise ReviewEvidenceError(f"execution claim {claim_id} probe.schema_version must be 1")
                if not isinstance(probe["input"], dict) or set(probe["input"]) != {"schema"} or not isinstance(probe["input"]["schema"], dict):
                    raise ReviewEvidenceError(f"execution claim {claim_id} probe.input must be an object containing object field 'schema'")
                try:
                    encoded = json.dumps(probe["input"], ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
                except (TypeError, ValueError, UnicodeError) as exc:
                    raise ReviewEvidenceError(f"execution claim {claim_id} probe.input is not bounded JSON data") from exc
                if len(encoded) > MAX_TEXT_CHARS:
                    raise ReviewEvidenceError(f"execution claim {claim_id} probe.input exceeds the byte limit")
            counts[kind] += 1
        elif kind == "inference":
            if set(claim) != {"id", "type", "statement", "basis_claim_ids"}:
                raise ReviewEvidenceError(f"inference claim {claim_id} has unsupported fields")
            basis = claim["basis_claim_ids"]
            if not isinstance(basis, list) or len(basis) > MAX_CLAIMS or not all(isinstance(item, str) and _ID.fullmatch(item) for item in basis):
                raise ReviewEvidenceError(f"inference claim {claim_id} basis_claim_ids must be a bounded ID array")
            basis_refs[claim_id] = basis
            counts[kind] += 1
        else:
            raise ReviewEvidenceError(f"claim {claim_id} has unsupported type")
    for claim_id, basis in basis_refs.items():
        if claim_id in basis or any(item not in ids for item in basis):
            raise ReviewEvidenceError(f"inference claim {claim_id} references an unknown or self claim")
    return {
        "claim_count": len(claims),
        "source_citation_count": counts["source_citation"],
        "execution_claim_count": counts["execution"],
        "inference_count": counts["inference"],
        "execution_provenance": "self_reported_unverified" if counts["execution"] else None,
    }, ids


def _claim_evidence(claim: dict[str, Any]) -> Any:
    kind = claim.get("type")
    if kind == "source_citation":
        return claim.get("citations")
    if kind == "execution":
        return claim.get("command")
    if kind == "inference":
        return claim.get("basis_claim_ids")
    return None


def _canonical_value(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _validate_revision(
    root: Path,
    value: Any,
    report_path: str,
    report_kind: str,
    report_status: str,
    claims: list[dict[str, Any]],
) -> None:
    required = {"revision_id", "previous_report", "previous_digest", "changed_claim_ids", "fresh_evidence_claim_ids", "changed_report_fields"}
    if not isinstance(value, dict) or set(value) != required:
        raise ReviewEvidenceError("revision must contain the exact versioned revision fields")
    revision_id = value["revision_id"]
    if not isinstance(revision_id, str) or not _REVISION_ID.fullmatch(revision_id):
        raise ReviewEvidenceError("revision_id must be a bounded stable ID")
    changed, fresh, changed_fields = value["changed_claim_ids"], value["fresh_evidence_claim_ids"], value["changed_report_fields"]
    for field_name, field_value in (("changed_claim_ids", changed), ("fresh_evidence_claim_ids", fresh)):
        if not isinstance(field_value, list) or len(field_value) > MAX_CLAIMS or any(not isinstance(item, str) or not _ID.fullmatch(item) for item in field_value) or len(set(field_value)) != len(field_value):
            raise ReviewEvidenceError(f"{field_name} must be a bounded unique stable-ID array")
    if not isinstance(changed_fields, list) or any(not isinstance(item, str) for item in changed_fields) or len(set(changed_fields)) != len(changed_fields) or any(item != "status" for item in changed_fields):
        raise ReviewEvidenceError("changed_report_fields may only contain the unique field 'status'")
    claims_by_id = {claim["id"]: claim for claim in claims}
    previous, previous_digest = value["previous_report"], value["previous_digest"]
    if previous is None:
        if previous_digest is not None or changed or fresh or changed_fields:
            raise ReviewEvidenceError("first revision cannot name a predecessor or changed claims")
        return
    previous = _relative(previous)
    if previous == report_path or not isinstance(previous_digest, str) or not _DIGEST.fullmatch(previous_digest):
        raise ReviewEvidenceError("revision predecessor path or digest is invalid")
    raw = _read_confined(root, previous, MAX_REPORT_BYTES)
    if hashlib.sha256(raw).hexdigest() != previous_digest:
        raise ReviewEvidenceError("revision predecessor digest does not match its report")
    predecessor = _load_json(raw, "revision predecessor")
    predecessor_status = predecessor.get("status")
    if (
        isinstance(predecessor.get("schema_version"), bool)
        or predecessor.get("schema_version") != 1
        or predecessor.get("review_kind") != report_kind
        or not isinstance(predecessor_status, str)
        or predecessor_status not in {"pass", "fail"}
    ):
        raise ReviewEvidenceError("revision predecessor has incompatible report kind or version")
    prior_revision = predecessor.get("revision")
    if not isinstance(prior_revision, dict) or prior_revision.get("revision_id") == revision_id:
        raise ReviewEvidenceError("revision ID must differ from its predecessor")
    prior_claims = predecessor.get("claims")
    if not isinstance(prior_claims, list) or len(prior_claims) > MAX_CLAIMS or any(not isinstance(item, dict) or not isinstance(item.get("id"), str) or not _ID.fullmatch(item["id"]) for item in prior_claims):
        raise ReviewEvidenceError("revision predecessor claims are malformed")
    prior_by_id = {item["id"]: item for item in prior_claims}
    if len(prior_by_id) != len(prior_claims):
        raise ReviewEvidenceError("revision predecessor contains duplicate claim IDs")
    removed_ids = set(prior_by_id) - set(claims_by_id)
    if removed_ids:
        removed = ", ".join(sorted(removed_ids))
        raise ReviewEvidenceError(f"claims cannot be removed from a linked revision ({removed}); retain the ID and replace it with an explicit inference claim")
    derived_changes = {
        claim_id for claim_id, current_claim in claims_by_id.items()
        if claim_id not in prior_by_id or _canonical_value(prior_by_id[claim_id]) != _canonical_value(current_claim)
    }
    if changed != sorted(derived_changes):
        raise ReviewEvidenceError("changed_claim_ids must exactly match the derived claim changes")
    if fresh != sorted(derived_changes):
        raise ReviewEvidenceError("fresh_evidence_claim_ids must exactly match the changed claim IDs")
    status_changed = predecessor_status != report_status
    expected_changed_fields = ["status"] if status_changed else []
    if changed_fields != expected_changed_fields:
        raise ReviewEvidenceError("changed_report_fields must exactly match the derived report changes")
    if status_changed and not derived_changes:
        raise ReviewEvidenceError("status transition requires fresh changed claims")
    for claim_id in derived_changes:
        current_claim = claims_by_id[claim_id]
        evidence = _claim_evidence(current_claim)
        if evidence in (None, [], {}):
            raise ReviewEvidenceError(f"changed claim {claim_id} has no fresh evidence payload")
        old = prior_by_id.get(claim_id)
        if old is not None and _canonical_value(_claim_evidence(old)) == _canonical_value(evidence):
            raise ReviewEvidenceError(f"changed claim {claim_id} repeats its predecessor evidence")


def validate_review_report(root: Path, report: str, *, expected_kind: str | None = None, expected_status: str | None = None) -> dict[str, Any]:
    """Validate a bounded v1 JSON review report against the current worktree.

    Execution records are structural, self-reported assertions. This validator
    never executes commands or authenticates their author or output.
    """
    relative = _relative(report)
    raw = _read_confined(root, relative, MAX_REPORT_BYTES)
    data = _load_json(raw, "review report")
    if set(data) != {"schema_version", "review_kind", "status", "revision", "claims"} or isinstance(data.get("schema_version"), bool) or data.get("schema_version") != 1:
        raise ReviewEvidenceError("review report must match the exact v1 structured shape")
    kind = data.get("review_kind")
    if not isinstance(kind, str) or kind not in REVIEW_KINDS or (expected_kind is not None and kind != expected_kind):
        raise ReviewEvidenceError("review report kind does not match the requested receipt")
    status = data.get("status")
    if not isinstance(status, str) or status not in {"pass", "fail"} or (expected_status is not None and status != expected_status):
        raise ReviewEvidenceError("review report status does not match the requested receipt")
    claims = data.get("claims")
    summary, _claim_ids = _validate_claims(root, claims)
    _validate_revision(root, data.get("revision"), relative, kind, status, claims)
    return {
        "report_path": relative,
        "report_digest": hashlib.sha256(raw).hexdigest(),
        "summary": summary,
    }
