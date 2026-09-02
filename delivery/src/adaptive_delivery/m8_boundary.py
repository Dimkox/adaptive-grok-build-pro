"""Temporary digest-compatible M8 wire boundary for the provisional M9 branch.

This adapter deliberately implements only the M8 values consumed by M9 and
recomputes their relevant equality/aggregate chain.  It is not a replacement
for the producer's complete M7 semantic validation.  Direct M8 imports must
replace this module when M9 is factually restacked onto M8.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import UTC, datetime
from typing import Any, ClassVar

PROVISIONAL_M8_PRODUCER_SHA = "2cee9b93c161b6c76f4fee877e6d19eacee5a271"

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$", re.ASCII)
_UTC_TIMESTAMP = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?Z$",
    re.ASCII,
)
_LEVELS = ("L0", "L1", "L2")
_RECOMMENDATION_REASONS = frozenset(
    {
        "qualified",
        "already_at_ceiling",
        "cohort_replay",
        "m7_bundle_blocked",
        "m7_acceptance_missing",
        "m7_currentness_missing",
        "tuple_expired",
        "insufficient_acceptances",
        "human_acceptance_missing",
        "audit_rate_insufficient",
        "audit_day_gap",
        "audit_rejected",
        "quality_below_threshold",
        "security_failure",
        "authorization_failure",
        "duplicate_dispatch",
        "cost_above_threshold",
        "latency_above_threshold",
        "demotion_fact_present",
        "halted_profile",
    }
)
_COHORT_FIELDS = frozenset(
    {
        "schema_version",
        "autonomy_tuple",
        "tasks",
        "m7_handoff",
        "window_started_at",
        "window_ended_at",
        "minimum_human_acceptances",
        "minimum_audit_rate_millionths",
        "minimum_quality_score_millionths",
        "maximum_security_failures",
        "maximum_authorization_failures",
        "maximum_duplicate_dispatches",
        "maximum_cost_usd_micros",
        "maximum_latency_ms",
        "maximum_demotion_triggers",
    }
)
_TASK_FIELDS = frozenset(
    {
        "schema_version",
        "tuple_digest",
        "task_id",
        "run_id",
        "exact_head_sha",
        "observed_at",
        "m7_bundle_digest",
        "m7_outcome_digest",
        "audit_sampled",
        "audit_accepted",
        "human_acceptance_receipt_digest",
        "attestation_receipt_digest",
        "quality_score_millionths",
        "security_failure_count",
        "authorization_failure_count",
        "duplicate_dispatch_count",
        "cost_usd_micros",
        "latency_ms",
        "demotion_trigger_count",
    }
)
_M7_HANDOFF_FIELDS = frozenset(
    {"schema_version", "provider_mapping", "bundles", "cohort", "aggregate", "evaluation"}
)
_MAX_COUNT = 1_000_000
_MAX_COST_USD_MICROS = 1_000_000_000_000
_MAX_LATENCY_MS = 604_800_000
_MAX_WIRE_BYTES = 4 * 1024 * 1024
_MAX_WIRE_NODES = 500_000
_MAX_WIRE_DEPTH = 64


class M8BoundaryError(ValueError):
    """The provisional wire value is not digest-compatible with the M8 boundary."""

    def __init__(self, field: str, detail: str = "") -> None:
        super().__init__(f"{field}: {detail}" if detail else field)
        self.field = field
        self.detail = detail


def _canonical_bytes(value: object) -> bytes:
    _validate_json_bounds(value)
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (RecursionError, TypeError, ValueError, UnicodeError) as exc:
        raise M8BoundaryError("canonical_body", "must be canonical JSON data") from exc
    if len(encoded) > _MAX_WIRE_BYTES:
        raise M8BoundaryError("canonical_body", "exceeds the bounded wire size")
    return encoded


def _validate_json_bounds(value: object) -> None:
    stack = [(value, 0)]
    nodes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_WIRE_NODES or depth > _MAX_WIRE_DEPTH:
            raise M8BoundaryError("canonical_body", "exceeds wire depth or node bounds")
        if isinstance(item, Mapping):
            if any(not isinstance(key, str) for key in item):
                raise M8BoundaryError("canonical_body", "mapping keys must be strings")
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, (list, tuple)):
            stack.extend((child, depth + 1) for child in item)
        elif item is not None and type(item) not in (str, bool, int):
            raise M8BoundaryError("canonical_body", "contains a non-JSON value")


def _snapshot(value: Mapping[str, Any]) -> bytes:
    return _canonical_bytes(value)


def _restore(value: bytes) -> dict[str, Any]:
    restored = json.loads(value)
    if not isinstance(restored, dict):
        raise M8BoundaryError("canonical_body", "must restore one object")
    return restored


def _domain_digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + _canonical_bytes(value)).hexdigest()


def _closed(data: object, expected: frozenset[str], field: str) -> Mapping[str, Any]:
    if not isinstance(data, Mapping) or any(not isinstance(key, str) for key in data):
        raise M8BoundaryError(field, "must be an object with string keys")
    if set(data) != expected:
        raise M8BoundaryError(field, "has missing or unknown fields")
    return data


def _version(value: object, field: str) -> None:
    if type(value) is not int or value != 1:
        raise M8BoundaryError(field, "schema_version must equal 1")


def _identifier(value: object, field: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise M8BoundaryError(field, "must be a bounded ASCII identifier")


def _hex(value: object, field: str, pattern: re.Pattern[str] = _HEX64) -> None:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise M8BoundaryError(field, "must be lowercase hexadecimal")


def _integer(value: object, field: str, minimum: int, maximum: int) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise M8BoundaryError(field, f"must be an integer from {minimum} through {maximum}")


def _boolean(value: object, field: str) -> None:
    if type(value) is not bool:
        raise M8BoundaryError(field, "must be boolean")


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not _UTC_TIMESTAMP.fullmatch(value):
        raise M8BoundaryError(field, "must be a canonical UTC RFC3339 timestamp")
    try:
        return datetime.fromisoformat(value).astimezone(UTC)
    except ValueError as exc:
        raise M8BoundaryError(field, "must be a valid UTC timestamp") from exc


def _canonical_timestamp(value: object, field: str) -> str:
    return _timestamp(value, field).isoformat().replace("+00:00", "Z")


def _record_dict(record: object) -> dict[str, object]:
    return {field.name: getattr(record, field.name) for field in fields(record)}


class _M8Value:
    DOMAIN: ClassVar[str]

    def to_dict(self) -> dict[str, object]:
        return _record_dict(self)

    @property
    def digest(self) -> str:
        return _domain_digest(self.DOMAIN, self.to_dict())


@dataclass(frozen=True, slots=True)
class M8AutonomyTupleV1(_M8Value):
    schema_version: int
    repository_id: str
    task_class: str
    m7_change_class: str
    m7_cohort_key_digest: str
    provider_mapping_digest: str
    agent_digest: str
    validator_digest: str
    provider_digest: str
    model_digest: str
    prompt_digest: str
    policy_digest: str
    runner_digest: str
    holdout_digest: str
    authority_digest: str
    authority_ceiling: str
    expires_at: str

    DOMAIN: ClassVar[str] = "adaptive-factory.m8-autonomy-tuple/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "autonomy_tuple")
        _identifier(self.repository_id, "repository_id")
        if self.task_class != "low_risk_text_only":
            raise M8BoundaryError("task_class", "must equal low_risk_text_only")
        _identifier(self.m7_change_class, "m7_change_class")
        for name in (
            "m7_cohort_key_digest",
            "provider_mapping_digest",
            "agent_digest",
            "validator_digest",
            "provider_digest",
            "model_digest",
            "prompt_digest",
            "policy_digest",
            "runner_digest",
            "holdout_digest",
            "authority_digest",
        ):
            _hex(getattr(self, name), name)
        if self.authority_ceiling != "L2":
            raise M8BoundaryError("authority_ceiling", "must equal L2")
        object.__setattr__(
            self,
            "expires_at",
            _canonical_timestamp(self.expires_at, "tuple.expires_at"),
        )

    @classmethod
    def from_dict(cls, data: object) -> M8AutonomyTupleV1:
        body = _closed(data, frozenset(field.name for field in fields(cls)), "autonomy_tuple")
        return cls(**body)


@dataclass(frozen=True, slots=True, init=False)
class M8CohortEvidenceV1:
    """Immutable complete M8 cohort body with exact producer-domain digest.

    Nested M7 semantics are intentionally not reimplemented here.  The full
    canonical body is retained and bound; direct M8 imports replace this
    temporary adapter after the factual restack.
    """

    schema_version: int
    autonomy_tuple: M8AutonomyTupleV1
    task_count: int
    accepted_task_count: int
    audit_sample_count: int
    audit_accepted_count: int
    minimum_quality_score_millionths: int
    total_security_failures: int
    total_authorization_failures: int
    total_duplicate_dispatches: int
    maximum_cost_usd_micros: int
    p95_latency_ms: int
    total_demotion_triggers: int
    upstream_blocked: bool
    window_started_at: str
    window_ended_at: str
    _body: bytes

    DOMAIN: ClassVar[str] = "adaptive-factory.m8-cohort-evidence/v1"

    @classmethod
    def from_dict(cls, data: object) -> M8CohortEvidenceV1:
        _validate_json_bounds(data)
        body = _closed(data, _COHORT_FIELDS, "cohort")
        _version(body["schema_version"], "cohort")
        autonomy_tuple = M8AutonomyTupleV1.from_dict(body["autonomy_tuple"])
        tasks = body["tasks"]
        if not isinstance(tasks, list) or not 1 <= len(tasks) <= 10_000:
            raise M8BoundaryError("cohort.tasks", "must contain 1 through 10000 tasks")
        parsed_tasks = tuple(
            _validate_task(item, autonomy_tuple, index) for index, item in enumerate(tasks)
        )
        task_ids = tuple(item["task_id"] for item in parsed_tasks)
        if task_ids != tuple(sorted(task_ids)) or len(set(task_ids)) != len(task_ids):
            raise M8BoundaryError("cohort.tasks", "task_id values must be sorted and unique")
        for name in ("run_id", "exact_head_sha", "m7_bundle_digest", "m7_outcome_digest"):
            values = tuple(item[name] for item in parsed_tasks)
            if len(set(values)) != len(values):
                raise M8BoundaryError(f"cohort.tasks.{name}", "must be unique")

        handoff = _closed(body["m7_handoff"], _M7_HANDOFF_FIELDS, "cohort.m7_handoff")
        _version(handoff["schema_version"], "cohort.m7_handoff")
        for name in ("provider_mapping", "cohort", "aggregate", "evaluation"):
            if not isinstance(handoff[name], Mapping):
                raise M8BoundaryError(f"cohort.m7_handoff.{name}", "must be an object")
        if not isinstance(handoff["bundles"], list) or not handoff["bundles"]:
            raise M8BoundaryError("cohort.m7_handoff.bundles", "must be a non-empty list")
        _validate_tuple_m7_bindings(autonomy_tuple, handoff)
        accepted_task_count, upstream_blocked = _validate_m7_links(
            parsed_tasks, handoff
        )

        started = _timestamp(body["window_started_at"], "cohort.window_started_at")
        ended = _timestamp(body["window_ended_at"], "cohort.window_ended_at")
        tuple_expiry = _timestamp(autonomy_tuple.expires_at, "tuple.expires_at")
        if started >= ended or ended > tuple_expiry:
            raise M8BoundaryError("cohort.window", "must be ordered within tuple expiry")
        for index, item in enumerate(parsed_tasks):
            observed = _timestamp(item["observed_at"], f"cohort.tasks[{index}].observed_at")
            if observed >= tuple_expiry:
                raise M8BoundaryError(
                    "cohort.tasks.observed_at", "task_at_or_after_tuple_expiry"
                )
            if not started <= observed <= ended:
                raise M8BoundaryError("cohort.tasks.observed_at", "must be inside cohort window")

        _integer(body["minimum_human_acceptances"], "minimum_human_acceptances", 30, 10_000)
        _integer(
            body["minimum_audit_rate_millionths"],
            "minimum_audit_rate_millionths",
            200_000,
            1_000_000,
        )
        _integer(
            body["minimum_quality_score_millionths"],
            "minimum_quality_score_millionths",
            0,
            1_000_000,
        )
        for name in (
            "maximum_security_failures",
            "maximum_authorization_failures",
            "maximum_duplicate_dispatches",
            "maximum_demotion_triggers",
        ):
            if body[name] != 0:
                raise M8BoundaryError(name, "must equal zero")
        _integer(
            body["maximum_cost_usd_micros"],
            "maximum_cost_usd_micros",
            0,
            _MAX_COST_USD_MICROS,
        )
        _integer(body["maximum_latency_ms"], "maximum_latency_ms", 0, _MAX_LATENCY_MS)

        instance = object.__new__(cls)
        object.__setattr__(instance, "schema_version", 1)
        object.__setattr__(instance, "autonomy_tuple", autonomy_tuple)
        object.__setattr__(instance, "task_count", len(tasks))
        object.__setattr__(instance, "accepted_task_count", accepted_task_count)
        object.__setattr__(
            instance,
            "audit_sample_count",
            sum(bool(item["audit_sampled"]) for item in parsed_tasks),
        )
        object.__setattr__(
            instance,
            "audit_accepted_count",
            sum(bool(item["audit_accepted"]) for item in parsed_tasks),
        )
        object.__setattr__(
            instance,
            "minimum_quality_score_millionths",
            min(int(item["quality_score_millionths"]) for item in parsed_tasks),
        )
        object.__setattr__(
            instance,
            "total_security_failures",
            _bounded_sum(parsed_tasks, "security_failure_count"),
        )
        object.__setattr__(
            instance,
            "total_authorization_failures",
            _bounded_sum(parsed_tasks, "authorization_failure_count"),
        )
        object.__setattr__(
            instance,
            "total_duplicate_dispatches",
            _bounded_sum(parsed_tasks, "duplicate_dispatch_count"),
        )
        object.__setattr__(
            instance,
            "maximum_cost_usd_micros",
            max(int(item["cost_usd_micros"]) for item in parsed_tasks),
        )
        object.__setattr__(
            instance,
            "p95_latency_ms",
            _nearest_rank_p95(tuple(int(item["latency_ms"]) for item in parsed_tasks)),
        )
        object.__setattr__(
            instance,
            "total_demotion_triggers",
            _bounded_sum(parsed_tasks, "demotion_trigger_count"),
        )
        object.__setattr__(instance, "upstream_blocked", upstream_blocked)
        canonical_body = dict(body)
        canonical_body["autonomy_tuple"] = autonomy_tuple.to_dict()
        canonical_body["tasks"] = [dict(item) for item in parsed_tasks]
        canonical_body["window_started_at"] = _canonical_timestamp(
            body["window_started_at"], "cohort.window_started_at"
        )
        canonical_body["window_ended_at"] = _canonical_timestamp(
            body["window_ended_at"], "cohort.window_ended_at"
        )
        object.__setattr__(instance, "window_started_at", canonical_body["window_started_at"])
        object.__setattr__(instance, "window_ended_at", canonical_body["window_ended_at"])
        object.__setattr__(instance, "_body", _snapshot(canonical_body))
        return instance

    def to_dict(self) -> dict[str, Any]:
        return _restore(self._body)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.DOMAIN.encode("ascii") + b"\x00" + self._body).hexdigest()


def _validate_task(
    data: object, autonomy_tuple: M8AutonomyTupleV1, index: int
) -> Mapping[str, Any]:
    body = _closed(data, _TASK_FIELDS, f"cohort.tasks[{index}]")
    _version(body["schema_version"], f"cohort.tasks[{index}]")
    _hex(body["tuple_digest"], f"cohort.tasks[{index}].tuple_digest")
    if body["tuple_digest"] != autonomy_tuple.digest:
        raise M8BoundaryError("cohort.tasks.tuple_digest", "does not match autonomy tuple")
    for name in ("task_id", "run_id"):
        _identifier(body[name], f"cohort.tasks[{index}].{name}")
    _hex(body["exact_head_sha"], f"cohort.tasks[{index}].exact_head_sha", _HEX40)
    observed_at = _canonical_timestamp(
        body["observed_at"], f"cohort.tasks[{index}].observed_at"
    )
    for name in (
        "m7_bundle_digest",
        "m7_outcome_digest",
        "human_acceptance_receipt_digest",
        "attestation_receipt_digest",
    ):
        _hex(body[name], f"cohort.tasks[{index}].{name}")
    for name in ("audit_sampled", "audit_accepted"):
        _boolean(body[name], f"cohort.tasks[{index}].{name}")
    if body["audit_accepted"] and not body["audit_sampled"]:
        raise M8BoundaryError("cohort.tasks.audit_accepted", "requires audit_sampled")
    _integer(
        body["quality_score_millionths"],
        f"cohort.tasks[{index}].quality_score_millionths",
        0,
        1_000_000,
    )
    for name in (
        "security_failure_count",
        "authorization_failure_count",
        "duplicate_dispatch_count",
        "demotion_trigger_count",
    ):
        _integer(body[name], f"cohort.tasks[{index}].{name}", 0, _MAX_COUNT)
    _integer(
        body["cost_usd_micros"],
        f"cohort.tasks[{index}].cost_usd_micros",
        0,
        _MAX_COST_USD_MICROS,
    )
    _integer(body["latency_ms"], f"cohort.tasks[{index}].latency_ms", 0, _MAX_LATENCY_MS)
    normalized = dict(body)
    normalized["observed_at"] = observed_at
    return normalized


def _bounded_sum(tasks: tuple[Mapping[str, Any], ...], field: str) -> int:
    return min(sum(int(item[field]) for item in tasks), _MAX_COUNT)


def _nearest_rank_p95(values: tuple[int, ...]) -> int:
    ordered = sorted(values)
    rank = (95 * len(ordered) + 99) // 100
    return ordered[rank - 1]


def _validate_m7_links(
    tasks: tuple[Mapping[str, Any], ...], handoff: Mapping[str, Any]
) -> tuple[int, bool]:
    bundles = handoff["bundles"]
    m7_cohort = handoff["cohort"]
    if not isinstance(bundles, list) or any(not isinstance(item, Mapping) for item in bundles):
        raise M8BoundaryError("cohort.m7_handoff.bundles", "must contain objects")
    if not isinstance(m7_cohort, Mapping) or not isinstance(m7_cohort.get("outcomes"), list):
        raise M8BoundaryError("cohort.m7_handoff.cohort.outcomes", "must be a list")
    outcomes = m7_cohort["outcomes"]
    if any(not isinstance(item, Mapping) for item in outcomes):
        raise M8BoundaryError("cohort.m7_handoff.cohort.outcomes", "must contain objects")
    if len(tasks) != len(bundles) or len(tasks) != len(outcomes):
        raise M8BoundaryError("cohort.m7_handoff", "task, bundle and outcome counts differ")

    bundles_by_digest: dict[str, Mapping[str, Any]] = {}
    for item in bundles:
        digest = item.get("bundle_digest")
        _hex(digest, "cohort.m7_handoff.bundle_digest")
        if digest in bundles_by_digest:
            raise M8BoundaryError("cohort.m7_handoff.bundle_digest", "must be unique")
        bundles_by_digest[digest] = item
    outcomes_by_digest: dict[str, Mapping[str, Any]] = {}
    for item in outcomes:
        digest = _domain_digest("adaptive-factory.m7-shadow-outcome/v1", item)
        if digest in outcomes_by_digest:
            raise M8BoundaryError("cohort.m7_handoff.outcome_digest", "must be unique")
        outcomes_by_digest[digest] = item

    accepted = 0
    for task in tasks:
        try:
            bundle = bundles_by_digest[str(task["m7_bundle_digest"])]
            outcome = outcomes_by_digest[str(task["m7_outcome_digest"])]
        except KeyError as exc:
            raise M8BoundaryError("cohort.m7_handoff", "task link is absent") from exc
        if outcome.get("bundle_digest") != bundle.get("bundle_digest"):
            raise M8BoundaryError("cohort.m7_handoff", "outcome bundle link differs")
        evidence = bundle.get("evidence")
        if not isinstance(evidence, Mapping):
            raise M8BoundaryError("cohort.m7_handoff.bundle.evidence", "must be an object")
        m4 = evidence.get("m4")
        m5 = evidence.get("m5")
        if not isinstance(m4, Mapping) or not isinstance(m5, Mapping):
            raise M8BoundaryError("cohort.m7_handoff.bundle.evidence", "must carry m4 and m5")
        if (task["task_id"], task["run_id"], task["exact_head_sha"]) != (
            m4.get("task_id"),
            m4.get("run_id"),
            m5.get("result_exact_head_sha"),
        ):
            raise M8BoundaryError("cohort.m7_handoff", "task identity link differs")
        if task["human_acceptance_receipt_digest"] != outcome.get("human_evidence_digest"):
            raise M8BoundaryError("cohort.m7_handoff", "human receipt link differs")
        accepted += outcome.get("human_decision") == "merged_accepted"
    return accepted, any(
        item.get("status") == "blocked_pending_durable_lookup" for item in bundles
    )


def _validate_tuple_m7_bindings(
    autonomy_tuple: M8AutonomyTupleV1, handoff: Mapping[str, Any]
) -> None:
    mapping = handoff["provider_mapping"]
    m7_cohort = handoff["cohort"]
    if not isinstance(mapping, Mapping) or not isinstance(m7_cohort, Mapping):
        raise M8BoundaryError("cohort.m7_handoff", "mapping and cohort must be objects")
    key = m7_cohort.get("key")
    if not isinstance(key, Mapping):
        raise M8BoundaryError("cohort.m7_handoff.cohort.key", "must be an object")
    mapping_digest = _domain_digest(
        "adaptive-factory.m8-m7-provider-mapping/v1", mapping
    )
    key_digest = _domain_digest("adaptive-factory.m7-shadow-cohort-key/v1", key)
    expected = {
        "repository_id": key.get("repository_id"),
        "m7_change_class": key.get("change_class"),
        "m7_cohort_key_digest": key_digest,
        "provider_mapping_digest": mapping_digest,
        "agent_digest": key.get("agent_digest"),
        "validator_digest": key.get("validator_digest"),
        "provider_digest": mapping.get("provider_digest"),
        "model_digest": key.get("model_digest"),
        "prompt_digest": key.get("prompt_digest"),
        "policy_digest": key.get("policy_digest"),
        "runner_digest": key.get("runner_digest"),
        "holdout_digest": key.get("holdout_digest"),
        "authority_digest": key.get("authority_digest"),
    }
    if mapping.get("cohort_key_digest") != key_digest:
        raise M8BoundaryError("cohort.m7_handoff.provider_mapping", "cohort key differs")
    if mapping.get("validator_digest") != key.get("validator_digest"):
        raise M8BoundaryError("cohort.m7_handoff.provider_mapping", "validator differs")
    for name, value in expected.items():
        if getattr(autonomy_tuple, name) != value:
            raise M8BoundaryError("cohort.autonomy_tuple", f"{name} differs from M7")


@dataclass(frozen=True, slots=True)
class M8AutonomyProfileV1(_M8Value):
    schema_version: int
    tuple_digest: str
    cohort_digest: str
    current_level: str
    accepted_task_count: int
    audit_sample_count: int
    audit_accepted_count: int
    minimum_quality_score_millionths: int
    total_security_failures: int
    total_authorization_failures: int
    total_duplicate_dispatches: int
    maximum_cost_usd_micros: int
    p95_latency_ms: int
    total_demotion_triggers: int
    expires_at: str
    halted: bool

    DOMAIN: ClassVar[str] = "adaptive-factory.m8-autonomy-profile/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "profile")
        _hex(self.tuple_digest, "profile.tuple_digest")
        _hex(self.cohort_digest, "profile.cohort_digest")
        if self.current_level not in _LEVELS:
            raise M8BoundaryError("profile.current_level", "must be L0, L1 or L2")
        for name in (
            "accepted_task_count",
            "audit_sample_count",
            "audit_accepted_count",
            "total_security_failures",
            "total_authorization_failures",
            "total_duplicate_dispatches",
            "total_demotion_triggers",
        ):
            _integer(getattr(self, name), f"profile.{name}", 0, _MAX_COUNT)
        if self.audit_accepted_count > self.audit_sample_count:
            raise M8BoundaryError("profile.audit_accepted_count", "cannot exceed sampled count")
        _integer(
            self.minimum_quality_score_millionths,
            "profile.minimum_quality_score_millionths",
            0,
            1_000_000,
        )
        _integer(
            self.maximum_cost_usd_micros,
            "profile.maximum_cost_usd_micros",
            0,
            _MAX_COST_USD_MICROS,
        )
        _integer(self.p95_latency_ms, "profile.p95_latency_ms", 0, _MAX_LATENCY_MS)
        object.__setattr__(
            self,
            "expires_at",
            _canonical_timestamp(self.expires_at, "profile.expires_at"),
        )
        _boolean(self.halted, "profile.halted")
        if self.halted and self.current_level != "L0":
            raise M8BoundaryError("profile.halted", "halted profile must be L0")

    @classmethod
    def from_dict(cls, data: object) -> M8AutonomyProfileV1:
        body = _closed(data, frozenset(field.name for field in fields(cls)), "profile")
        return cls(**body)


@dataclass(frozen=True, slots=True)
class M8PromotionRecommendationV1(_M8Value):
    schema_version: int
    tuple_digest: str
    cohort_digest: str
    current_level: str
    recommended_level: str
    reason_code: str
    evaluated_at: str
    expires_at: str
    separate_activation_required: bool
    external_action_authorized: bool

    DOMAIN: ClassVar[str] = "adaptive-factory.m8-promotion-recommendation/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "recommendation")
        _hex(self.tuple_digest, "recommendation.tuple_digest")
        _hex(self.cohort_digest, "recommendation.cohort_digest")
        if self.current_level not in _LEVELS or self.recommended_level not in _LEVELS:
            raise M8BoundaryError("recommendation.level", "must be L0, L1 or L2")
        current = _LEVELS.index(self.current_level)
        recommended = _LEVELS.index(self.recommended_level)
        if recommended not in (current, current + 1):
            raise M8BoundaryError("recommendation.level", "must hold or advance one level")
        if self.reason_code not in _RECOMMENDATION_REASONS:
            raise M8BoundaryError("recommendation.reason_code", "is not an M8 reason")
        if (recommended == current + 1) != (self.reason_code == "qualified"):
            raise M8BoundaryError("recommendation.reason_code", "does not match transition")
        evaluated = _timestamp(self.evaluated_at, "recommendation.evaluated_at")
        expires = _timestamp(self.expires_at, "recommendation.expires_at")
        if self.reason_code == "tuple_expired":
            if evaluated < expires or self.current_level != "L0" or self.recommended_level != "L0":
                raise M8BoundaryError("recommendation.expires_at", "invalid expired result")
        elif evaluated >= expires:
            raise M8BoundaryError("recommendation.expires_at", "must follow evaluation")
        if self.separate_activation_required is not True:
            raise M8BoundaryError("recommendation.separate_activation_required", "must be true")
        if self.external_action_authorized is not False:
            raise M8BoundaryError("recommendation.external_action_authorized", "must be false")
        object.__setattr__(
            self,
            "evaluated_at",
            evaluated.isoformat().replace("+00:00", "Z"),
        )
        object.__setattr__(
            self,
            "expires_at",
            expires.isoformat().replace("+00:00", "Z"),
        )

    @classmethod
    def from_dict(cls, data: object) -> M8PromotionRecommendationV1:
        body = _closed(data, frozenset(field.name for field in fields(cls)), "recommendation")
        return cls(**body)


@dataclass(frozen=True, slots=True)
class M8DeliveryHandoffV1:
    schema_version: int
    producer_commit_sha: str
    cohort: M8CohortEvidenceV1
    profile: M8AutonomyProfileV1
    recommendation: M8PromotionRecommendationV1
    handoff_digest: str

    DOMAIN: ClassVar[str] = "adaptive-delivery.m8-delivery-handoff/v1"
    SOURCE_STATUS: ClassVar[str] = "blocked_pending_durable_m8_lookup"
    EXTERNAL_ACTION_AUTHORIZED: ClassVar[bool] = False

    def __post_init__(self) -> None:
        _version(self.schema_version, "m8_handoff")
        _hex(self.producer_commit_sha, "m8_handoff.producer_commit_sha", _HEX40)
        if self.producer_commit_sha != PROVISIONAL_M8_PRODUCER_SHA:
            raise M8BoundaryError("m8_handoff.producer_commit_sha", "is not the pinned producer")
        if type(self.cohort) is not M8CohortEvidenceV1:
            raise M8BoundaryError("m8_handoff.cohort", "must be typed cohort evidence")
        if type(self.profile) is not M8AutonomyProfileV1:
            raise M8BoundaryError("m8_handoff.profile", "must be typed profile evidence")
        if type(self.recommendation) is not M8PromotionRecommendationV1:
            raise M8BoundaryError(
                "m8_handoff.recommendation", "must be typed recommendation evidence"
            )
        tuple_digest = self.cohort.autonomy_tuple.digest
        if self.profile.tuple_digest != tuple_digest or self.recommendation.tuple_digest != tuple_digest:
            raise M8BoundaryError("m8_handoff.tuple_digest", "tuple equality chain is broken")
        if (
            self.profile.cohort_digest != self.cohort.digest
            or self.recommendation.cohort_digest != self.cohort.digest
        ):
            raise M8BoundaryError("m8_handoff.cohort_digest", "cohort equality chain is broken")
        if self.recommendation.current_level != self.profile.current_level:
            raise M8BoundaryError("m8_handoff.current_level", "profile and recommendation differ")
        if not (
            self.cohort.autonomy_tuple.expires_at
            == self.profile.expires_at
            == self.recommendation.expires_at
        ):
            raise M8BoundaryError("m8_handoff.expires_at", "producer expiries differ")
        aggregate_bindings = {
            "accepted_task_count": self.cohort.accepted_task_count,
            "audit_sample_count": self.cohort.audit_sample_count,
            "audit_accepted_count": self.cohort.audit_accepted_count,
            "minimum_quality_score_millionths": (
                self.cohort.minimum_quality_score_millionths
            ),
            "total_security_failures": self.cohort.total_security_failures,
            "total_authorization_failures": self.cohort.total_authorization_failures,
            "total_duplicate_dispatches": self.cohort.total_duplicate_dispatches,
            "maximum_cost_usd_micros": self.cohort.maximum_cost_usd_micros,
            "p95_latency_ms": self.cohort.p95_latency_ms,
            "total_demotion_triggers": self.cohort.total_demotion_triggers,
        }
        for name, expected in aggregate_bindings.items():
            if getattr(self.profile, name) != expected:
                raise M8BoundaryError(
                    "m8_handoff.profile_aggregate", f"{name} does not match cohort tasks"
                )
        _hex(self.handoff_digest, "m8_handoff.handoff_digest")
        if self.handoff_digest != self.expected_digest:
            raise M8BoundaryError("m8_handoff.handoff_digest", "does not bind the handoff")

    @property
    def expected_digest(self) -> str:
        return _domain_digest(self.DOMAIN, self.to_dict(include_digest=False))

    def to_dict(self, *, include_digest: bool = True) -> dict[str, object]:
        body: dict[str, object] = {
            "schema_version": self.schema_version,
            "producer_commit_sha": self.producer_commit_sha,
            "cohort": self.cohort.to_dict(),
            "profile": self.profile.to_dict(),
            "recommendation": self.recommendation.to_dict(),
        }
        if include_digest:
            body["handoff_digest"] = self.handoff_digest
        return body

    @property
    def durable_currentness_available(self) -> bool:
        """The provisional source-only adapter is never operational authority."""

        return False


def m8_gate_reasons(handoff: M8DeliveryHandoffV1, at: datetime) -> tuple[str, ...]:
    """Return stable reasons that keep a non-current M8 profile from M9."""

    tuple_value = handoff.cohort.autonomy_tuple
    profile = handoff.profile
    recommendation = handoff.recommendation
    expiries = tuple(
        _timestamp(value, "m8.expires_at")
        for value in (tuple_value.expires_at, profile.expires_at, recommendation.expires_at)
    )
    reasons: set[str] = set()
    if at < _timestamp(recommendation.evaluated_at, "recommendation.evaluated_at"):
        reasons.add("m8_evidence_not_current")
    if any(at >= expiry for expiry in expiries):
        reasons.add("m8_evidence_expired")
    if (
        profile.halted
        or profile.total_demotion_triggers != 0
        or profile.accepted_task_count < 30
        or profile.accepted_task_count != handoff.cohort.task_count
        or profile.audit_accepted_count != profile.audit_sample_count
        or profile.total_security_failures != 0
        or profile.total_authorization_failures != 0
        or profile.total_duplicate_dispatches != 0
    ):
        reasons.add("m8_profile_ineligible")
    eligible_recommendation = recommendation.reason_code == "qualified" or (
        recommendation.reason_code == "already_at_ceiling"
        and recommendation.current_level == "L2"
        and recommendation.recommended_level == "L2"
    )
    if handoff.cohort.upstream_blocked:
        eligible_recommendation = False
    if not eligible_recommendation:
        reasons.add("m8_recommendation_ineligible")
    return tuple(sorted(reasons))
