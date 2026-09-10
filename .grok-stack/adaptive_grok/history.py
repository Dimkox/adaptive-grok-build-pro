"""Bounded, offline accounting of imported historical evidence; no authority effects."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_REPOSITORIES = 100
MAX_OBSERVATIONS = 20_000
MAX_REFERENCES = 100
MAX_STRING_LENGTH = 2048
MAX_INTEGER = 2**63 - 1
MAX_DEPTH = 12
MAX_NODES = 500_000

PROFILE_FIELDS = (
    "schema_version", "repository_id", "task_class", "m7_change_class",
    "m7_cohort_key_digest", "provider_mapping_digest", "agent_digest",
    "validator_digest", "provider_digest", "model_digest", "prompt_digest",
    "policy_digest", "runner_digest", "holdout_digest", "authority_digest",
    "authority_ceiling", "expires_at",
)
METRICS = ("cost_usd_micros", "latency_ms", "regression_count", "rollback_count")
ACCEPTANCE_STATES = ("unknown", "documented_validation", "explicit_human_acceptance", "rejected")
PR_FIELDS = (
    "number", "state", "base_ref", "head_sha", "merge_sha", "merged_at",
    "merged_by_account_type", "delivered_at_ref", "source_refs",
)
TASK_FIELDS = (
    "task_id", "pull_request_numbers", "acceptance", "acceptance_source_refs",
    "operator_interventions", "intervention_coverage", "intervention_source_refs",
    "session_started_at", "session_ended_at", *METRICS, "profile", "source_refs",
)
REPOSITORY_FIELDS = (
    "repository_id", "default_branch", "delivery_ref", "delivery_sha",
    "pagination_complete", "task_inventory_complete", "source_refs", "pull_requests", "tasks",
)
QUALIFICATION_GAPS = (
    "m7_bundle_missing", "m7_outcome_missing", "external_acceptance_unavailable",
    "currentness_unavailable", "audit_coverage_missing",
)


class HistoryError(ValueError):
    """Invalid snapshot; messages contain schema locations, never imported values."""


def _error(location: str, reason: str) -> None:
    raise HistoryError(f"{location}: {reason}")


def _bounded_json(data: Any) -> None:
    # Iterative traversal bounds both in-memory callers and parsed JSON. Cycles hit
    # the depth bound without depending on the interpreter's recursion limit.
    pending = [(data, 0)]
    count = 0
    while pending:
        value, depth = pending.pop()
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            _error("input", "JSON complexity limit exceeded")
        if type(value) is dict:
            if len(value) > 100:
                _error("input", "object field limit exceeded")
            for key, item in value.items():
                _string(key, "input key")
                pending.append((item, depth + 1))
        elif type(value) is list:
            if len(value) > MAX_OBSERVATIONS:
                _error("input", "list limit exceeded")
            pending.extend((item, depth + 1) for item in value)
        elif type(value) is str:
            _string(value, "input string", allow_empty=True)
        elif value is not None and type(value) not in (int, bool):
            _error("input", "expected JSON objects, arrays, strings, integers, booleans or null")


def _object(value: Any, required: tuple, location: str, optional: tuple = ()) -> dict:
    if type(value) is not dict:
        _error(location, "expected object")
    if set(value) - set(required) - set(optional):
        _error(location, "unknown field")
    if set(required) - set(value):
        _error(location, "required field missing")
    return value


def _string(value: Any, location: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str or len(value) > MAX_STRING_LENGTH:
        _error(location, "expected bounded string")
    if not allow_empty and not value.strip():
        _error(location, "expected nonempty string")
    if any(ord(character) < 32 or 127 <= ord(character) <= 159 or
           0xD800 <= ord(character) <= 0xDFFF for character in value):
        _error(location, "control characters and surrogate code points are forbidden")
    return value


def _integer(value: Any, location: str, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= MAX_INTEGER:
        _error(location, "expected bounded integer excluding booleans")
    return value


def _boolean(value: Any, location: str) -> bool:
    if type(value) is not bool:
        _error(location, "expected boolean")
    return value


def _enum(value: Any, choices: tuple, location: str) -> str:
    if type(value) is not str or value not in choices:
        _error(location, "unsupported value")
    return value


def _list(value: Any, location: str, limit: int = MAX_OBSERVATIONS) -> list:
    if type(value) is not list or len(value) > limit:
        _error(location, "expected bounded list")
    return value


def _refs(value: Any, location: str, required: bool = False) -> list[str]:
    result = sorted({_string(ref, location) for ref in _list(value, location, MAX_REFERENCES)})
    if required and not result:
        _error(location, "source reference required")
    return result


def _sha(value: Any, location: str, *, digest: bool = False) -> str:
    pattern = r"[0-9a-f]{64}" if digest else r"(?:[0-9a-f]{40}|[0-9a-f]{64})"
    if type(value) is not str or re.fullmatch(pattern, value) is None:
        _error(location, "expected lowercase hexadecimal digest")
    return value


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _timestamp(value: Any, location: str) -> str:
    if type(value) is not str or re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)", value
    ) is None:
        _error(location, "expected timezone-aware ISO timestamp")
    try:
        return _instant(value).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, OverflowError):
        _error(location, "invalid timestamp")


def _nullable(value: Any, validator, location: str) -> Any:
    return None if value is None else validator(value, location)


def _profile(value: Any, repository_id: str) -> dict:
    if value is None:
        value = {}
    _object(value, (), "task.profile", PROFILE_FIELDS)
    result = {}
    for field in PROFILE_FIELDS:
        item = value.get(field)
        if item is None:
            result[field] = None
        elif field == "schema_version":
            result[field] = _integer(item, "profile.schema_version", 1)
        elif field.endswith("_digest"):
            result[field] = _sha(item, "profile." + field, digest=True)
        elif field == "expires_at":
            result[field] = _timestamp(item, "profile.expires_at")
        else:
            result[field] = _string(item, "profile." + field)
    if result["repository_id"] is not None and result["repository_id"] != repository_id:
        _error("task.profile.repository_id", "repository binding mismatch")
    return result


def _pull_request(value: Any, captured_at: str) -> dict:
    _object(value, PR_FIELDS, "pull_request", ("delivery_kind",))
    result = {
        "number": _integer(value["number"], "pull_request.number", 1),
        "state": _enum(value["state"], ("open", "closed", "merged"), "pull_request.state"),
        "delivery_kind": _enum(value.get("delivery_kind", "unknown"),
                               ("product_change", "branch_sync", "unknown"), "pull_request.delivery_kind"),
        "source_refs": _refs(value["source_refs"], "pull_request.source_refs", True),
    }
    for field, validator in (
        ("base_ref", _string), ("head_sha", _sha), ("merge_sha", _sha),
        ("merged_at", _timestamp), ("merged_by_account_type", _string), ("delivered_at_ref", _boolean),
    ):
        result[field] = _nullable(value[field], validator, "pull_request." + field)
    if result["merged_at"] is not None:
        if result["state"] != "merged" or _instant(result["merged_at"]) > _instant(captured_at):
            _error("pull_request.merged_at", "merge timestamp inconsistent with state or capture")
    return result


def _task(value: Any, repository_id: str, captured_at: str) -> dict:
    _object(value, TASK_FIELDS, "task")
    result = {
        "task_id": _string(value["task_id"], "task.task_id"),
        "pull_request_numbers": sorted({_integer(item, "task.pull_request_numbers", 1)
                                        for item in _list(value["pull_request_numbers"], "task.pull_request_numbers")}),
        "acceptance": _enum(value["acceptance"], ACCEPTANCE_STATES, "task.acceptance"),
        "intervention_coverage": _enum(value["intervention_coverage"],
                                       ("unknown", "partial", "complete"), "task.intervention_coverage"),
        "source_refs": _refs(value["source_refs"], "task.source_refs", True),
        "profile": _profile(value["profile"], repository_id),
    }
    result["acceptance_source_refs"] = _refs(value["acceptance_source_refs"], "task.acceptance_source_refs",
                                             result["acceptance"] != "unknown")
    measured = result["intervention_coverage"] != "unknown"
    result["intervention_source_refs"] = _refs(value["intervention_source_refs"], "task.intervention_source_refs", measured)
    for field in (*METRICS, "operator_interventions"):
        result[field] = _nullable(value[field], _integer, "task." + field)
    if measured != (result["operator_interventions"] is not None):
        _error("task.operator_interventions", "count must be known exactly when coverage is measured")
    for field in ("session_started_at", "session_ended_at"):
        result[field] = _nullable(value[field], _timestamp, "task." + field)
        if result[field] is not None and _instant(result[field]) > _instant(captured_at):
            _error("task." + field, "session cannot extend beyond capture")
    start, end = result["session_started_at"], result["session_ended_at"]
    if result["intervention_coverage"] == "complete" and (start is None or end is None):
        _error("task.intervention_coverage", "complete coverage requires a bounded session")
    if start is not None and end is not None and _instant(start) > _instant(end):
        _error("task.session_ended_at", "session end precedes start")
    return result


def _deduplicate(records: list[dict], key: str, kind: str, duplicates: dict) -> list[dict]:
    unique = {}
    for record in records:
        identity = record[key]
        if identity in unique:
            if unique[identity] != record:
                _error("input", "conflicting " + kind + " observations")
            duplicates[kind] += 1
        else:
            unique[identity] = record
    return [unique[identity] for identity in sorted(unique)]


def _normalize(data: Any) -> tuple[dict, dict]:
    _bounded_json(data)
    _object(data, ("schema_version", "captured_at", "repositories"), "snapshot")
    if _integer(data["schema_version"], "snapshot.schema_version", 1) != 1:
        _error("snapshot.schema_version", "unsupported schema version")
    captured_at = _timestamp(data["captured_at"], "snapshot.captured_at")
    duplicates = {"repository": 0, "pull_request": 0, "task": 0}
    repositories = []
    observation_count = 0
    for value in _list(data["repositories"], "snapshot.repositories", MAX_REPOSITORIES):
        _object(value, REPOSITORY_FIELDS, "repository")
        repo = {field: _string(value[field], "repository." + field)
                for field in ("repository_id", "default_branch", "delivery_ref")}
        repo["delivery_sha"] = _sha(value["delivery_sha"], "repository.delivery_sha")
        for field in ("pagination_complete", "task_inventory_complete"):
            repo[field] = _boolean(value[field], "repository." + field)
        repo["source_refs"] = _refs(value["source_refs"], "repository.source_refs", True)
        prs = _list(value["pull_requests"], "repository.pull_requests")
        tasks = _list(value["tasks"], "repository.tasks")
        observation_count += len(prs) + len(tasks)
        if observation_count > MAX_OBSERVATIONS:
            _error("snapshot", "observation count limit exceeded")
        repo["pull_requests"] = _deduplicate([_pull_request(pr, captured_at) for pr in prs],
                                             "number", "pull_request", duplicates)
        repo["tasks"] = _deduplicate([_task(task, repo["repository_id"], captured_at) for task in tasks],
                                    "task_id", "task", duplicates)
        pr_ids = {pr["number"] for pr in repo["pull_requests"]}
        if any(set(task["pull_request_numbers"]) - pr_ids for task in repo["tasks"]):
            _error("task.pull_request_numbers", "linked request missing from snapshot")
        repositories.append(repo)
    return {
        "schema_version": 1,
        "captured_at": captured_at,
        "repositories": _deduplicate(repositories, "repository_id", "repository", duplicates),
    }, duplicates


def _unique_json_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _error("input", "duplicate JSON key")
        result[key] = value
    return result


def _nonfinite_number(value: str) -> None:
    _error("input", "nonfinite JSON number")


def load_history(path: str | Path) -> dict:
    """Read only the selected regular file, once; never resolve evidence references."""
    try:
        flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
        if not hasattr(os, "O_NOFOLLOW") and stat.S_ISLNK(os.lstat(path).st_mode):
            _error("input", "snapshot must be a regular file")
        descriptor = os.open(path, flags)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                _error("input", "snapshot must be a regular file")
            if metadata.st_size > MAX_INPUT_BYTES:
                _error("input", "snapshot exceeds 8 MiB limit")
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                raw = stream.read(MAX_INPUT_BYTES + 1)
        finally:
            os.close(descriptor)
    except (OSError, ValueError) as exc:
        if isinstance(exc, HistoryError):
            raise
        raise HistoryError("input: cannot read a regular snapshot file") from None
    if len(raw) > MAX_INPUT_BYTES:
        _error("input", "snapshot exceeds 8 MiB limit")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_json_object,
                          parse_constant=_nonfinite_number)
    except HistoryError:
        raise
    except (UnicodeError, ValueError, RecursionError):
        raise HistoryError("input: expected bounded UTF-8 JSON") from None
    _normalize(data)
    return data


def _digest(domain: str, value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((domain + "\0" + canonical).encode("ascii")).hexdigest()


def _interventions(tasks: list[dict]) -> dict:
    complete = [task["operator_interventions"] for task in tasks if task["intervention_coverage"] == "complete"]
    partial = [task["operator_interventions"] for task in tasks if task["intervention_coverage"] == "partial"]
    measured = complete + partial
    return {
        "complete_session_count": len(complete),
        "partial_session_count": len(partial),
        "unknown_session_count": len(tasks) - len(measured),
        "observed_lower_bound": sum(measured) if measured else None,
        "complete_session_interventions": sum(complete) if complete else None,
        "complete_session_zero_intervention_count": complete.count(0),
        "complete_session_zero_intervention_rate": complete.count(0) / len(complete) if complete else None,
    }


def _metrics(tasks: list[dict]) -> dict:
    result = {}
    for field in METRICS:
        known = [task[field] for task in tasks if task[field] is not None]
        result[field] = {
            "known_task_count": len(known), "unknown_task_count": len(tasks) - len(known),
            "observed_sum": sum(known) if known else None,
        }
    return result


def _profile_issues(profile: dict, captured_at: str) -> list[str]:
    issues = []
    for field, supported, reason in (
        ("schema_version", 1, "profile_schema_unsupported"),
        ("task_class", "low_risk_text_only", "task_class_unsupported"),
        ("authority_ceiling", "L2", "authority_ceiling_unsupported"),
    ):
        if profile[field] is not None and profile[field] != supported:
            issues.append(reason)
    if profile["expires_at"] is not None and _instant(profile["expires_at"]) <= _instant(captured_at):
        issues.append("profile_expired_at_capture")
    return sorted(issues)


def _task_report(task: dict, captured_at: str) -> dict:
    missing = sorted(field for field in PROFILE_FIELDS if task["profile"][field] is None)
    issues = _profile_issues(task["profile"], captured_at)
    gaps = set(QUALIFICATION_GAPS) | set(issues)
    if task["acceptance"] in ("unknown", "documented_validation"):
        gaps.add("acceptance_evidence_missing")
    if task["acceptance"] == "rejected":
        gaps.add("acceptance_rejected")
    if task["intervention_coverage"] != "complete":
        gaps.add("intervention_coverage_incomplete")
    if task["profile"]["task_class"] is None:
        gaps.add("task_class_unknown")
    if missing:
        gaps.add("exact_profile_missing_fields")
    if any(task[field] is None for field in METRICS):
        gaps.add("quality_cost_latency_outcomes_unknown")
    return {
        **task,
        "missing_profile_fields": missing,
        "profile_metadata_digest": None if missing else _digest("historical-profile-metadata-v1", task["profile"]),
        "profile_metadata_status": "incomplete" if missing else "complete",
        "profile_compatibility_issues": issues,
        "qualification_gaps": sorted(gaps),
    }


def _repository_report(repo: dict, captured_at: str) -> dict:
    tasks = [_task_report(task, captured_at) for task in repo["tasks"]]
    prs = repo["pull_requests"]
    acceptance = {state: sum(task["acceptance"] == state for task in tasks) for state in ACCEPTANCE_STATES}
    buckets = {}
    for task in tasks:
        digest = task["profile_metadata_digest"]
        if digest is None:
            continue
        if digest not in buckets:
            buckets[digest] = {
                "repository_id": repo["repository_id"], "profile_metadata_digest": digest,
                "profile": task["profile"], "metadata_status": "complete",
                "compatibility_issues": task["profile_compatibility_issues"],
                "task_ids": [], "observed_explicit_acceptance_count": 0,
                "floor_semantics": "imported_metadata_accounting_only",
                "m8_qualification": "not_evaluated", "authority_effect": "none",
            }
        bucket = buckets[digest]
        bucket["task_ids"].append(task["task_id"])
        bucket["observed_explicit_acceptance_count"] += task["acceptance"] == "explicit_human_acceptance"
    for bucket in buckets.values():
        bucket["remaining_to_observed_30_floor"] = max(0, 30 - bucket["observed_explicit_acceptance_count"])
    known_classes = [task["profile"]["task_class"] for task in tasks if task["profile"]["task_class"] is not None]
    complete_profile_count = sum(task["profile_metadata_digest"] is not None for task in tasks)
    linked = {number for task in tasks for number in task["pull_request_numbers"]}
    gaps = set(QUALIFICATION_GAPS)
    for task in tasks:
        gaps.update(task["qualification_gaps"])
    if len(linked) < len(prs):
        gaps.add("task_identity_missing")
    if not repo["task_inventory_complete"]:
        gaps.add("task_inventory_incomplete")
    if not repo["pagination_complete"]:
        gaps.add("pull_request_inventory_incomplete")
    return {
        **{field: repo[field] for field in REPOSITORY_FIELDS if field not in ("tasks", "pull_requests")},
        "pull_requests_observed": len(prs),
        "pull_request_total": len(prs) if repo["pagination_complete"] else None,
        "merged_prs_observed": sum(pr["state"] == "merged" for pr in prs),
        "branch_sync_prs_observed": sum(pr["delivery_kind"] == "branch_sync" for pr in prs),
        "pr_state_counts": {state: sum(pr["state"] == state for pr in prs) for state in ("open", "closed", "merged")},
        "delivery_identity_reachability": {
            "reachable": sum(pr["delivered_at_ref"] is True for pr in prs),
            "identity_not_reachable": sum(pr["delivered_at_ref"] is False for pr in prs),
            "unknown": sum(pr["delivered_at_ref"] is None for pr in prs),
        },
        "pull_requests_without_task_identity": len(prs) - len(linked),
        "pull_requests": prs,
        "tasks_observed": len(tasks), "task_total": len(tasks) if repo["task_inventory_complete"] else None,
        "acceptance_counts": acceptance,
        "explicit_acceptances_observed": acceptance["explicit_human_acceptance"],
        "accepted_task_total": acceptance["explicit_human_acceptance"]
        if repo["task_inventory_complete"] and not acceptance["unknown"] and not acceptance["documented_validation"] else None,
        "interventions": _interventions(tasks), "metrics": _metrics(tasks),
        "profile_coverage": {
            "complete_task_count": complete_profile_count,
            "incomplete_task_count": len(tasks) - complete_profile_count,
            "supported_task_class_count": known_classes.count("low_risk_text_only"),
            "unsupported_task_class_count": len(known_classes) - known_classes.count("low_risk_text_only"),
            "unknown_task_class_count": len(tasks) - len(known_classes),
        },
        "exact_profile_buckets": [buckets[key] for key in sorted(buckets)],
        "tasks": tasks, "qualification_gaps": sorted(gaps),
    }


def summarize_history(data: Any) -> dict:
    """Return deterministic accounting; imported claims never qualify or activate M8."""
    normalized, duplicates = _normalize(data)
    repositories = [_repository_report(repo, normalized["captured_at"]) for repo in normalized["repositories"]]
    gaps = set(QUALIFICATION_GAPS)
    for repo in repositories:
        gaps.update(repo["qualification_gaps"])
    pagination_complete = all(repo["pagination_complete"] for repo in repositories)
    task_inventory_complete = all(repo["task_inventory_complete"] for repo in repositories)
    return {
        "schema_version": 1, "captured_at": normalized["captured_at"],
        "normalized_input_digest": _digest("historical-evidence-snapshot-v1", normalized),
        "evidence_kind": "untrusted_imported_history", "provenance_status": "source_claims_unverified",
        "inventory_scope": "repositories_and_records_in_the_explicit_snapshot",
        "m8_qualification": "not_evaluated", "authority_effect": "none",
        "projects_observed": len(repositories),
        "pagination_complete": pagination_complete, "task_inventory_complete": task_inventory_complete,
        "inventory_complete": pagination_complete and task_inventory_complete,
        "duplicate_observations": duplicates, "repositories": repositories,
        "qualification_gaps": sorted(gaps),
    }
