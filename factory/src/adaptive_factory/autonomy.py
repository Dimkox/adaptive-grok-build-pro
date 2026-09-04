from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime, timezone
import hashlib
from typing import Any, ClassVar, Mapping

from .contracts import ContractError, HEX40, HEX64, _closed, _hex, _id, _time, canonical_json
from .m7_autonomy_bridge import M7AutonomyBridgeV1


MAX_COHORT_TASKS = 10_000
MAX_COUNT = 1_000_000
MAX_COST_USD_MICROS = 1_000_000_000_000
MAX_LATENCY_MS = 604_800_000
LEVELS = ("L0", "L1", "L2")
RECOMMENDATION_REASONS = frozenset(
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
DEMOTION_TRIGGERS = (
    "security_failure",
    "authorization_failure",
    "incorrect_merge",
    "rollback",
    "escaped_defect",
    "invalid_attestation",
    "policy_bypass",
    "unexplained_regression",
)


def _object(data: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(data, Mapping) or any(not isinstance(key, str) for key in data):
        raise ContractError("invalid_contract", name)
    return data


def _field_names(contract: type[Any]) -> set[str]:
    return {field.name for field in fields(contract)}


def _version(value: Any, name: str) -> int:
    if type(value) is not int or value != 1:
        raise ContractError("unsupported_version", name)
    return 1


def _identifier(value: Any, name: str) -> str:
    try:
        return _id(value, name)
    except (ContractError, UnicodeEncodeError) as exc:
        raise ContractError("invalid_identifier", name) from exc


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ContractError("invalid_integer", name)
    return value


def _boolean(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ContractError("invalid_boolean", name)
    return value


def _timestamp(value: Any, name: str) -> datetime:
    return _time(value, name)


def _timestamp_dict(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _level(value: Any, name: str) -> str:
    if value not in LEVELS:
        raise ContractError("unsupported_level", name)
    return value


def _domain_digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + canonical_json(value)).hexdigest()


class _AutonomyValue:
    DOMAIN: ClassVar[str]

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    @property
    def digest(self) -> str:
        return _domain_digest(self.DOMAIN, self.to_dict())


@dataclass(frozen=True)
class AutonomyTupleV1(_AutonomyValue):
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
    expires_at: datetime

    DOMAIN: ClassVar[str] = "adaptive-factory.m8-autonomy-tuple/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "autonomy_tuple")
        _identifier(self.repository_id, "repository_id")
        if self.task_class != "low_risk_text_only":
            raise ContractError("unsupported_task_class")
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
            _hex(getattr(self, name), name, HEX64)
        if self.authority_ceiling != "L2":
            raise ContractError("unsupported_level", "authority_ceiling")
        if not isinstance(self.expires_at, datetime) or self.expires_at.tzinfo is None:
            raise ContractError("invalid_time", "expires_at")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AutonomyTupleV1":
        data = _object(data, "autonomy_tuple")
        _closed(data, _field_names(cls))
        if data["task_class"] != "low_risk_text_only":
            raise ContractError("unsupported_task_class")
        if data["authority_ceiling"] != "L2":
            raise ContractError("unsupported_level", "authority_ceiling")
        return cls(
            _version(data["schema_version"], "autonomy_tuple"),
            _identifier(data["repository_id"], "repository_id"),
            data["task_class"],
            _identifier(data["m7_change_class"], "m7_change_class"),
            _hex(data["m7_cohort_key_digest"], "m7_cohort_key_digest", HEX64),
            _hex(data["provider_mapping_digest"], "provider_mapping_digest", HEX64),
            _hex(data["agent_digest"], "agent_digest", HEX64),
            _hex(data["validator_digest"], "validator_digest", HEX64),
            _hex(data["provider_digest"], "provider_digest", HEX64),
            _hex(data["model_digest"], "model_digest", HEX64),
            _hex(data["prompt_digest"], "prompt_digest", HEX64),
            _hex(data["policy_digest"], "policy_digest", HEX64),
            _hex(data["runner_digest"], "runner_digest", HEX64),
            _hex(data["holdout_digest"], "holdout_digest", HEX64),
            _hex(data["authority_digest"], "authority_digest", HEX64),
            data["authority_ceiling"],
            _timestamp(data["expires_at"], "expires_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "repository_id": self.repository_id,
            "task_class": self.task_class,
            "m7_change_class": self.m7_change_class,
            "m7_cohort_key_digest": self.m7_cohort_key_digest,
            "provider_mapping_digest": self.provider_mapping_digest,
            "agent_digest": self.agent_digest,
            "validator_digest": self.validator_digest,
            "provider_digest": self.provider_digest,
            "model_digest": self.model_digest,
            "prompt_digest": self.prompt_digest,
            "policy_digest": self.policy_digest,
            "runner_digest": self.runner_digest,
            "holdout_digest": self.holdout_digest,
            "authority_digest": self.authority_digest,
            "authority_ceiling": self.authority_ceiling,
            "expires_at": _timestamp_dict(self.expires_at),
        }


@dataclass(frozen=True)
class CohortTaskEvidenceV1(_AutonomyValue):
    schema_version: int
    tuple_digest: str
    task_id: str
    run_id: str
    exact_head_sha: str
    observed_at: datetime
    m7_bundle_digest: str
    m7_outcome_digest: str
    audit_sampled: bool
    audit_accepted: bool
    human_acceptance_receipt_digest: str
    attestation_receipt_digest: str
    quality_score_millionths: int
    security_failure_count: int
    authorization_failure_count: int
    duplicate_dispatch_count: int
    cost_usd_micros: int
    latency_ms: int
    demotion_trigger_count: int

    DOMAIN: ClassVar[str] = "adaptive-factory.m8-cohort-task-evidence/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "cohort_task_evidence")
        _hex(self.tuple_digest, "tuple_digest", HEX64)
        _identifier(self.task_id, "task_id")
        _identifier(self.run_id, "run_id")
        _hex(self.exact_head_sha, "exact_head_sha", HEX40)
        if not isinstance(self.observed_at, datetime) or self.observed_at.tzinfo is None:
            raise ContractError("invalid_time", "observed_at")
        for name in ("m7_bundle_digest", "m7_outcome_digest"):
            _hex(getattr(self, name), name, HEX64)
        for name in ("audit_sampled", "audit_accepted"):
            _boolean(getattr(self, name), name)
        if self.audit_accepted and not self.audit_sampled:
            raise ContractError("invalid_audit_state")
        _hex(
            self.human_acceptance_receipt_digest,
            "human_acceptance_receipt_digest",
            HEX64,
        )
        _hex(self.attestation_receipt_digest, "attestation_receipt_digest", HEX64)
        _integer(self.quality_score_millionths, "quality_score_millionths", 0, 1_000_000)
        for name in (
            "security_failure_count",
            "authorization_failure_count",
            "duplicate_dispatch_count",
            "demotion_trigger_count",
        ):
            _integer(getattr(self, name), name, 0, MAX_COUNT)
        _integer(self.cost_usd_micros, "cost_usd_micros", 0, MAX_COST_USD_MICROS)
        _integer(self.latency_ms, "latency_ms", 0, MAX_LATENCY_MS)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CohortTaskEvidenceV1":
        data = _object(data, "cohort_task_evidence")
        _closed(data, _field_names(cls))
        return cls(
            _version(data["schema_version"], "cohort_task_evidence"),
            _hex(data["tuple_digest"], "tuple_digest", HEX64),
            _identifier(data["task_id"], "task_id"),
            _identifier(data["run_id"], "run_id"),
            _hex(data["exact_head_sha"], "exact_head_sha", HEX40),
            _timestamp(data["observed_at"], "observed_at"),
            _hex(data["m7_bundle_digest"], "m7_bundle_digest", HEX64),
            _hex(data["m7_outcome_digest"], "m7_outcome_digest", HEX64),
            _boolean(data["audit_sampled"], "audit_sampled"),
            _boolean(data["audit_accepted"], "audit_accepted"),
            _hex(
                data["human_acceptance_receipt_digest"],
                "human_acceptance_receipt_digest",
                HEX64,
            ),
            _hex(data["attestation_receipt_digest"], "attestation_receipt_digest", HEX64),
            _integer(data["quality_score_millionths"], "quality_score_millionths", 0, 1_000_000),
            _integer(data["security_failure_count"], "security_failure_count", 0, MAX_COUNT),
            _integer(
                data["authorization_failure_count"],
                "authorization_failure_count",
                0,
                MAX_COUNT,
            ),
            _integer(data["duplicate_dispatch_count"], "duplicate_dispatch_count", 0, MAX_COUNT),
            _integer(data["cost_usd_micros"], "cost_usd_micros", 0, MAX_COST_USD_MICROS),
            _integer(data["latency_ms"], "latency_ms", 0, MAX_LATENCY_MS),
            _integer(data["demotion_trigger_count"], "demotion_trigger_count", 0, MAX_COUNT),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tuple_digest": self.tuple_digest,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "exact_head_sha": self.exact_head_sha,
            "observed_at": _timestamp_dict(self.observed_at),
            "m7_bundle_digest": self.m7_bundle_digest,
            "m7_outcome_digest": self.m7_outcome_digest,
            "audit_sampled": self.audit_sampled,
            "audit_accepted": self.audit_accepted,
            "human_acceptance_receipt_digest": self.human_acceptance_receipt_digest,
            "attestation_receipt_digest": self.attestation_receipt_digest,
            "quality_score_millionths": self.quality_score_millionths,
            "security_failure_count": self.security_failure_count,
            "authorization_failure_count": self.authorization_failure_count,
            "duplicate_dispatch_count": self.duplicate_dispatch_count,
            "cost_usd_micros": self.cost_usd_micros,
            "latency_ms": self.latency_ms,
            "demotion_trigger_count": self.demotion_trigger_count,
        }


@dataclass(frozen=True)
class CohortEvidenceV1(_AutonomyValue):
    schema_version: int
    autonomy_tuple: AutonomyTupleV1
    tasks: tuple[CohortTaskEvidenceV1, ...]
    m7_handoff: M7AutonomyBridgeV1
    window_started_at: datetime
    window_ended_at: datetime
    minimum_human_acceptances: int
    minimum_audit_rate_millionths: int
    minimum_quality_score_millionths: int
    maximum_security_failures: int
    maximum_authorization_failures: int
    maximum_duplicate_dispatches: int
    maximum_cost_usd_micros: int
    maximum_latency_ms: int
    maximum_demotion_triggers: int

    DOMAIN: ClassVar[str] = "adaptive-factory.m8-cohort-evidence/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "cohort_evidence")
        if not isinstance(self.autonomy_tuple, AutonomyTupleV1):
            raise ContractError("invalid_contract", "autonomy_tuple")
        if not isinstance(self.tasks, tuple) or not 1 <= len(self.tasks) <= MAX_COHORT_TASKS:
            raise ContractError("invalid_contract", "tasks")
        if any(not isinstance(task, CohortTaskEvidenceV1) for task in self.tasks):
            raise ContractError("invalid_contract", "tasks")
        task_ids = tuple(task.task_id for task in self.tasks)
        if task_ids != tuple(sorted(task_ids)):
            raise ContractError("invalid_order", "tasks")
        for name in ("task_id", "run_id", "exact_head_sha"):
            identities = tuple(getattr(task, name) for task in self.tasks)
            if len(set(identities)) != len(identities):
                raise ContractError("duplicate_identity", name)
        if any(task.tuple_digest != self.autonomy_tuple.digest for task in self.tasks):
            raise ContractError("tuple_mismatch")
        if not isinstance(self.m7_handoff, M7AutonomyBridgeV1):
            raise ContractError("invalid_contract", "m7_handoff")
        cohort = self.m7_handoff.cohort
        cohort_key = cohort.key
        provider_mapping = self.m7_handoff.provider_mapping
        tuple_bindings = {
            "repository_id": cohort_key.repository_id,
            "m7_change_class": cohort_key.change_class,
            "m7_cohort_key_digest": cohort_key.digest,
            "provider_mapping_digest": provider_mapping.digest,
            "agent_digest": cohort_key.agent_digest,
            "validator_digest": cohort_key.validator_digest,
            "provider_digest": provider_mapping.provider_digest,
            "model_digest": cohort_key.model_digest,
            "prompt_digest": cohort_key.prompt_digest,
            "policy_digest": cohort_key.policy_digest,
            "runner_digest": cohort_key.runner_digest,
            "holdout_digest": cohort_key.holdout_digest,
            "authority_digest": cohort_key.authority_digest,
        }
        for name, expected in tuple_bindings.items():
            if getattr(self.autonomy_tuple, name) != expected:
                raise ContractError("tuple_mismatch", name)
        if len(self.tasks) != len(cohort.outcomes):
            raise ContractError("m7_outcome_mismatch", "task_count")
        if len({task.m7_bundle_digest for task in self.tasks}) != len(self.tasks):
            raise ContractError("duplicate_identity", "m7_bundle_digest")
        if len({task.m7_outcome_digest for task in self.tasks}) != len(self.tasks):
            raise ContractError("duplicate_identity", "m7_outcome_digest")
        bundles_by_digest = {
            item.bundle_digest: item for item in self.m7_handoff.bundles
        }
        outcomes_by_digest = {
            item.digest: item for item in self.m7_handoff.cohort.outcomes
        }
        for task in self.tasks:
            try:
                bundle = bundles_by_digest[task.m7_bundle_digest]
                outcome = outcomes_by_digest[task.m7_outcome_digest]
            except KeyError as exc:
                raise ContractError("m7_outcome_mismatch", "task_link") from exc
            if outcome.bundle_digest != bundle.bundle_digest:
                raise ContractError("m7_outcome_mismatch", "bundle_digest")
            if (task.task_id, task.run_id, task.exact_head_sha) != (
                bundle.evidence.m4.task_id,
                bundle.evidence.m4.run_id,
                bundle.evidence.m5.result_exact_head_sha,
            ):
                raise ContractError("m7_outcome_mismatch", "task_identity")
            if task.human_acceptance_receipt_digest != outcome.human_evidence_digest:
                raise ContractError("m7_outcome_mismatch", "human_receipt")
        if (
            not isinstance(self.window_started_at, datetime)
            or self.window_started_at.tzinfo is None
            or not isinstance(self.window_ended_at, datetime)
            or self.window_ended_at.tzinfo is None
            or self.window_started_at >= self.window_ended_at
        ):
            raise ContractError("invalid_time", "cohort_window")
        if self.window_ended_at > self.autonomy_tuple.expires_at:
            raise ContractError("invalid_time", "cohort_after_tuple_expiry")
        if any(
            task.observed_at >= self.autonomy_tuple.expires_at
            for task in self.tasks
        ):
            raise ContractError("invalid_time", "task_at_or_after_tuple_expiry")
        if any(
            not self.window_started_at <= task.observed_at <= self.window_ended_at
            for task in self.tasks
        ):
            raise ContractError("invalid_time", "task_outside_window")
        _integer(
            self.minimum_human_acceptances,
            "minimum_human_acceptances",
            30,
            MAX_COHORT_TASKS,
        )
        _integer(
            self.minimum_audit_rate_millionths,
            "minimum_audit_rate_millionths",
            200_000,
            1_000_000,
        )
        _integer(
            self.minimum_quality_score_millionths,
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
            if getattr(self, name) != 0:
                raise ContractError("zero_tolerance_required", name)
        _integer(self.maximum_cost_usd_micros, "maximum_cost_usd_micros", 0, MAX_COST_USD_MICROS)
        _integer(self.maximum_latency_ms, "maximum_latency_ms", 0, MAX_LATENCY_MS)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CohortEvidenceV1":
        data = _object(data, "cohort_evidence")
        _closed(data, _field_names(cls))
        tasks = data["tasks"]
        if not isinstance(tasks, list):
            raise ContractError("invalid_contract", "tasks")
        if not 1 <= len(tasks) <= MAX_COHORT_TASKS:
            raise ContractError("invalid_contract", "tasks")
        return cls(
            _version(data["schema_version"], "cohort_evidence"),
            AutonomyTupleV1.from_dict(data["autonomy_tuple"]),
            tuple(CohortTaskEvidenceV1.from_dict(task) for task in tasks),
            M7AutonomyBridgeV1.from_dict(data["m7_handoff"]),
            _timestamp(data["window_started_at"], "window_started_at"),
            _timestamp(data["window_ended_at"], "window_ended_at"),
            _integer(data["minimum_human_acceptances"], "minimum_human_acceptances", 30, MAX_COHORT_TASKS),
            _integer(
                data["minimum_audit_rate_millionths"],
                "minimum_audit_rate_millionths",
                200_000,
                1_000_000,
            ),
            _integer(
                data["minimum_quality_score_millionths"],
                "minimum_quality_score_millionths",
                0,
                1_000_000,
            ),
            _integer(data["maximum_security_failures"], "maximum_security_failures", 0, 0),
            _integer(
                data["maximum_authorization_failures"],
                "maximum_authorization_failures",
                0,
                0,
            ),
            _integer(data["maximum_duplicate_dispatches"], "maximum_duplicate_dispatches", 0, 0),
            _integer(data["maximum_cost_usd_micros"], "maximum_cost_usd_micros", 0, MAX_COST_USD_MICROS),
            _integer(data["maximum_latency_ms"], "maximum_latency_ms", 0, MAX_LATENCY_MS),
            _integer(data["maximum_demotion_triggers"], "maximum_demotion_triggers", 0, 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "autonomy_tuple": self.autonomy_tuple.to_dict(),
            "tasks": [task.to_dict() for task in self.tasks],
            "m7_handoff": self.m7_handoff.to_dict(),
            "window_started_at": _timestamp_dict(self.window_started_at),
            "window_ended_at": _timestamp_dict(self.window_ended_at),
            "minimum_human_acceptances": self.minimum_human_acceptances,
            "minimum_audit_rate_millionths": self.minimum_audit_rate_millionths,
            "minimum_quality_score_millionths": self.minimum_quality_score_millionths,
            "maximum_security_failures": self.maximum_security_failures,
            "maximum_authorization_failures": self.maximum_authorization_failures,
            "maximum_duplicate_dispatches": self.maximum_duplicate_dispatches,
            "maximum_cost_usd_micros": self.maximum_cost_usd_micros,
            "maximum_latency_ms": self.maximum_latency_ms,
            "maximum_demotion_triggers": self.maximum_demotion_triggers,
        }


@dataclass(frozen=True)
class AutonomyProfileV1(_AutonomyValue):
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
    expires_at: datetime
    halted: bool

    DOMAIN: ClassVar[str] = "adaptive-factory.m8-autonomy-profile/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "autonomy_profile")
        _hex(self.tuple_digest, "tuple_digest", HEX64)
        _hex(self.cohort_digest, "cohort_digest", HEX64)
        _level(self.current_level, "current_level")
        for name in (
            "accepted_task_count",
            "audit_sample_count",
            "audit_accepted_count",
            "total_security_failures",
            "total_authorization_failures",
            "total_duplicate_dispatches",
            "total_demotion_triggers",
        ):
            _integer(getattr(self, name), name, 0, MAX_COUNT)
        if self.audit_accepted_count > self.audit_sample_count:
            raise ContractError("invalid_audit_state")
        _integer(
            self.minimum_quality_score_millionths,
            "minimum_quality_score_millionths",
            0,
            1_000_000,
        )
        _integer(self.maximum_cost_usd_micros, "maximum_cost_usd_micros", 0, MAX_COST_USD_MICROS)
        _integer(self.p95_latency_ms, "p95_latency_ms", 0, MAX_LATENCY_MS)
        if not isinstance(self.expires_at, datetime) or self.expires_at.tzinfo is None:
            raise ContractError("invalid_time", "expires_at")
        _boolean(self.halted, "halted")
        if self.halted and self.current_level != "L0":
            raise ContractError("invalid_halted_profile")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AutonomyProfileV1":
        data = _object(data, "autonomy_profile")
        _closed(data, _field_names(cls))
        return cls(
            _version(data["schema_version"], "autonomy_profile"),
            _hex(data["tuple_digest"], "tuple_digest", HEX64),
            _hex(data["cohort_digest"], "cohort_digest", HEX64),
            _level(data["current_level"], "current_level"),
            _integer(data["accepted_task_count"], "accepted_task_count", 0, MAX_COUNT),
            _integer(data["audit_sample_count"], "audit_sample_count", 0, MAX_COUNT),
            _integer(data["audit_accepted_count"], "audit_accepted_count", 0, MAX_COUNT),
            _integer(
                data["minimum_quality_score_millionths"],
                "minimum_quality_score_millionths",
                0,
                1_000_000,
            ),
            _integer(data["total_security_failures"], "total_security_failures", 0, MAX_COUNT),
            _integer(
                data["total_authorization_failures"],
                "total_authorization_failures",
                0,
                MAX_COUNT,
            ),
            _integer(data["total_duplicate_dispatches"], "total_duplicate_dispatches", 0, MAX_COUNT),
            _integer(data["maximum_cost_usd_micros"], "maximum_cost_usd_micros", 0, MAX_COST_USD_MICROS),
            _integer(data["p95_latency_ms"], "p95_latency_ms", 0, MAX_LATENCY_MS),
            _integer(data["total_demotion_triggers"], "total_demotion_triggers", 0, MAX_COUNT),
            _timestamp(data["expires_at"], "expires_at"),
            _boolean(data["halted"], "halted"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tuple_digest": self.tuple_digest,
            "cohort_digest": self.cohort_digest,
            "current_level": self.current_level,
            "accepted_task_count": self.accepted_task_count,
            "audit_sample_count": self.audit_sample_count,
            "audit_accepted_count": self.audit_accepted_count,
            "minimum_quality_score_millionths": self.minimum_quality_score_millionths,
            "total_security_failures": self.total_security_failures,
            "total_authorization_failures": self.total_authorization_failures,
            "total_duplicate_dispatches": self.total_duplicate_dispatches,
            "maximum_cost_usd_micros": self.maximum_cost_usd_micros,
            "p95_latency_ms": self.p95_latency_ms,
            "total_demotion_triggers": self.total_demotion_triggers,
            "expires_at": _timestamp_dict(self.expires_at),
            "halted": self.halted,
        }


@dataclass(frozen=True)
class PromotionRecommendationV1(_AutonomyValue):
    schema_version: int
    tuple_digest: str
    cohort_digest: str
    current_level: str
    recommended_level: str
    reason_code: str
    evaluated_at: datetime
    expires_at: datetime
    separate_activation_required: bool
    external_action_authorized: bool

    DOMAIN: ClassVar[str] = "adaptive-factory.m8-promotion-recommendation/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "promotion_recommendation")
        _hex(self.tuple_digest, "tuple_digest", HEX64)
        _hex(self.cohort_digest, "cohort_digest", HEX64)
        current = _level(self.current_level, "current_level")
        recommended = _level(self.recommended_level, "recommended_level")
        if LEVELS.index(recommended) not in (LEVELS.index(current), LEVELS.index(current) + 1):
            raise ContractError("invalid_transition")
        if self.reason_code not in RECOMMENDATION_REASONS:
            raise ContractError("invalid_reason")
        advances = LEVELS.index(recommended) == LEVELS.index(current) + 1
        if advances != (self.reason_code == "qualified"):
            raise ContractError("invalid_transition")
        if not isinstance(self.evaluated_at, datetime) or self.evaluated_at.tzinfo is None:
            raise ContractError("invalid_time", "evaluated_at")
        if not isinstance(self.expires_at, datetime) or self.expires_at.tzinfo is None:
            raise ContractError("invalid_time", "expires_at")
        expired_result = self.reason_code == "tuple_expired"
        if expired_result and (
            self.evaluated_at < self.expires_at
            or current != "L0"
            or recommended != "L0"
        ):
            raise ContractError("invalid_expired_recommendation")
        if not expired_result and self.evaluated_at >= self.expires_at:
            raise ContractError("invalid_time", "recommendation_expiry")
        if self.separate_activation_required is not True:
            raise ContractError("separate_activation_required")
        if self.external_action_authorized is not False:
            raise ContractError("external_action_forbidden")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PromotionRecommendationV1":
        data = _object(data, "promotion_recommendation")
        _closed(data, _field_names(cls))
        return cls(
            _version(data["schema_version"], "promotion_recommendation"),
            _hex(data["tuple_digest"], "tuple_digest", HEX64),
            _hex(data["cohort_digest"], "cohort_digest", HEX64),
            _level(data["current_level"], "current_level"),
            _level(data["recommended_level"], "recommended_level"),
            data["reason_code"],
            _timestamp(data["evaluated_at"], "evaluated_at"),
            _timestamp(data["expires_at"], "expires_at"),
            _boolean(data["separate_activation_required"], "separate_activation_required"),
            _boolean(data["external_action_authorized"], "external_action_authorized"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tuple_digest": self.tuple_digest,
            "cohort_digest": self.cohort_digest,
            "current_level": self.current_level,
            "recommended_level": self.recommended_level,
            "reason_code": self.reason_code,
            "evaluated_at": _timestamp_dict(self.evaluated_at),
            "expires_at": _timestamp_dict(self.expires_at),
            "separate_activation_required": self.separate_activation_required,
            "external_action_authorized": self.external_action_authorized,
        }


def _aware_time(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ContractError("invalid_time", name)
    return value


def _bounded_sum(values: tuple[int, ...]) -> int:
    return min(sum(values), MAX_COUNT)


def _nearest_rank_p95(values: tuple[int, ...]) -> int:
    ordered = sorted(values)
    rank = (95 * len(ordered) + 99) // 100
    return ordered[rank - 1]


def _cohort_profile(
    cohort: CohortEvidenceV1,
    current_level: str,
    halted: bool,
) -> AutonomyProfileV1:
    tasks = cohort.tasks
    outcomes_by_digest = {
        outcome.digest: outcome for outcome in cohort.m7_handoff.cohort.outcomes
    }
    outcomes = tuple(outcomes_by_digest[task.m7_outcome_digest] for task in tasks)
    return AutonomyProfileV1(
        schema_version=1,
        tuple_digest=cohort.autonomy_tuple.digest,
        cohort_digest=cohort.digest,
        current_level=current_level,
        accepted_task_count=sum(
            outcome.human_decision == "merged_accepted" for outcome in outcomes
        ),
        audit_sample_count=sum(task.audit_sampled for task in tasks),
        audit_accepted_count=sum(task.audit_accepted for task in tasks),
        minimum_quality_score_millionths=min(
            task.quality_score_millionths for task in tasks
        ),
        total_security_failures=_bounded_sum(
            tuple(task.security_failure_count for task in tasks)
        ),
        total_authorization_failures=_bounded_sum(
            tuple(task.authorization_failure_count for task in tasks)
        ),
        total_duplicate_dispatches=_bounded_sum(
            tuple(task.duplicate_dispatch_count for task in tasks)
        ),
        maximum_cost_usd_micros=max(task.cost_usd_micros for task in tasks),
        p95_latency_ms=_nearest_rank_p95(tuple(task.latency_ms for task in tasks)),
        total_demotion_triggers=_bounded_sum(
            tuple(task.demotion_trigger_count for task in tasks)
        ),
        expires_at=cohort.autonomy_tuple.expires_at,
        halted=halted,
    )


def _cohort_gate_reason(
    cohort: CohortEvidenceV1,
    profile: AutonomyProfileV1,
) -> str | None:
    tasks = cohort.tasks
    outcomes_by_digest = {
        outcome.digest: outcome for outcome in cohort.m7_handoff.cohort.outcomes
    }
    if any(
        outcomes_by_digest[task.m7_outcome_digest].human_decision != "merged_accepted"
        for task in tasks
    ):
        return "human_acceptance_missing"
    if profile.accepted_task_count < cohort.minimum_human_acceptances:
        return "insufficient_acceptances"
    if (
        profile.audit_sample_count * 1_000_000
        < len(tasks) * cohort.minimum_audit_rate_millionths
    ):
        return "audit_rate_insufficient"
    represented_days = {task.observed_at.astimezone(timezone.utc).date() for task in tasks}
    sampled_days = {
        task.observed_at.astimezone(timezone.utc).date()
        for task in tasks
        if task.audit_sampled
    }
    if not represented_days.issubset(sampled_days):
        return "audit_day_gap"
    if profile.audit_accepted_count != profile.audit_sample_count:
        return "audit_rejected"
    if profile.minimum_quality_score_millionths < cohort.minimum_quality_score_millionths:
        return "quality_below_threshold"
    if profile.total_security_failures > cohort.maximum_security_failures:
        return "security_failure"
    if profile.total_authorization_failures > cohort.maximum_authorization_failures:
        return "authorization_failure"
    if profile.total_duplicate_dispatches > cohort.maximum_duplicate_dispatches:
        return "duplicate_dispatch"
    if profile.maximum_cost_usd_micros > cohort.maximum_cost_usd_micros:
        return "cost_above_threshold"
    if profile.p95_latency_ms > cohort.maximum_latency_ms:
        return "latency_above_threshold"
    if profile.total_demotion_triggers > cohort.maximum_demotion_triggers:
        return "demotion_fact_present"
    if any(
        bundle.status == "blocked_pending_durable_lookup"
        for bundle in cohort.m7_handoff.bundles
    ):
        return "m7_bundle_blocked"
    if not cohort.m7_handoff.external_acceptance_available:
        return "m7_acceptance_missing"
    if not cohort.m7_handoff.currentness_available:
        return "m7_currentness_missing"
    return None


def evaluate_autonomy(
    cohort: CohortEvidenceV1,
    existing_profile: AutonomyProfileV1 | None,
    evaluated_at: datetime,
) -> tuple[AutonomyProfileV1, PromotionRecommendationV1]:
    """Compute a recommendation-only profile snapshot from closed factual shapes."""
    if not isinstance(cohort, CohortEvidenceV1):
        raise ContractError("invalid_contract", "cohort")
    evaluated_at = _aware_time(evaluated_at, "evaluated_at")
    if evaluated_at < cohort.window_ended_at:
        raise ContractError("invalid_time", "cohort_window_open")
    tuple_digest = cohort.autonomy_tuple.digest
    if existing_profile is not None and not isinstance(existing_profile, AutonomyProfileV1):
        raise ContractError("invalid_contract", "existing_profile")
    if existing_profile is not None:
        if existing_profile.tuple_digest != tuple_digest:
            raise ContractError("tuple_mismatch", "existing_profile")
        if existing_profile.expires_at != cohort.autonomy_tuple.expires_at:
            raise ContractError("profile_expiry_mismatch")

    expired = evaluated_at >= cohort.autonomy_tuple.expires_at
    current_level = "L0" if expired or existing_profile is None else existing_profile.current_level
    halted = bool(existing_profile and existing_profile.halted and not expired)
    profile = _cohort_profile(cohort, current_level, halted)

    if expired:
        reason = "tuple_expired"
    elif halted:
        reason = "halted_profile"
    elif existing_profile is not None and existing_profile.cohort_digest == cohort.digest:
        reason = "cohort_replay"
    else:
        reason = _cohort_gate_reason(cohort, profile)

    if reason is None and current_level == cohort.autonomy_tuple.authority_ceiling:
        reason = "already_at_ceiling"
    if reason is None:
        reason = "qualified"
        recommended_level = LEVELS[LEVELS.index(current_level) + 1]
    else:
        recommended_level = current_level

    recommendation = PromotionRecommendationV1(
        schema_version=1,
        tuple_digest=tuple_digest,
        cohort_digest=cohort.digest,
        current_level=current_level,
        recommended_level=recommended_level,
        reason_code=reason,
        evaluated_at=evaluated_at,
        expires_at=cohort.autonomy_tuple.expires_at,
        separate_activation_required=True,
        external_action_authorized=False,
    )
    return profile, recommendation


@dataclass(frozen=True)
class DemotionDecisionV1(_AutonomyValue):
    schema_version: int
    profile_digest: str
    tuple_digest: str
    trigger: str
    prior_level: str
    resulting_level: str
    effective_at: datetime
    halt: bool
    external_action_authorized: bool

    DOMAIN: ClassVar[str] = "adaptive-factory.m8-demotion-decision/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "demotion_decision")
        _hex(self.profile_digest, "profile_digest", HEX64)
        _hex(self.tuple_digest, "tuple_digest", HEX64)
        if self.trigger not in DEMOTION_TRIGGERS:
            raise ContractError("invalid_demotion_trigger")
        _level(self.prior_level, "prior_level")
        if self.resulting_level != "L0":
            raise ContractError("invalid_demotion")
        if not isinstance(self.effective_at, datetime) or self.effective_at.tzinfo is None:
            raise ContractError("invalid_time", "effective_at")
        if self.halt is not True:
            raise ContractError("invalid_demotion")
        if self.external_action_authorized is not False:
            raise ContractError("external_action_forbidden")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DemotionDecisionV1":
        data = _object(data, "demotion_decision")
        _closed(data, _field_names(cls))
        return cls(
            _version(data["schema_version"], "demotion_decision"),
            _hex(data["profile_digest"], "profile_digest", HEX64),
            _hex(data["tuple_digest"], "tuple_digest", HEX64),
            data["trigger"],
            _level(data["prior_level"], "prior_level"),
            data["resulting_level"],
            _timestamp(data["effective_at"], "effective_at"),
            _boolean(data["halt"], "halt"),
            _boolean(data["external_action_authorized"], "external_action_authorized"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "profile_digest": self.profile_digest,
            "tuple_digest": self.tuple_digest,
            "trigger": self.trigger,
            "prior_level": self.prior_level,
            "resulting_level": self.resulting_level,
            "effective_at": _timestamp_dict(self.effective_at),
            "halt": self.halt,
            "external_action_authorized": self.external_action_authorized,
        }


def demote_profile(
    profile: AutonomyProfileV1,
    trigger_facts: frozenset[str],
    observed_at: datetime,
) -> tuple[AutonomyProfileV1, DemotionDecisionV1]:
    """Return one immutable L0/halted profile and its highest-priority reason."""
    if not isinstance(profile, AutonomyProfileV1):
        raise ContractError("invalid_contract", "profile")
    if not isinstance(trigger_facts, frozenset):
        raise ContractError("invalid_contract", "trigger_facts")
    if not trigger_facts or not trigger_facts.issubset(DEMOTION_TRIGGERS):
        raise ContractError("invalid_demotion_trigger")
    observed_at = _aware_time(observed_at, "observed_at")
    selected_trigger = next(
        trigger for trigger in DEMOTION_TRIGGERS if trigger in trigger_facts
    )
    updated_profile = replace(
        profile,
        current_level="L0",
        total_demotion_triggers=min(
            MAX_COUNT,
            profile.total_demotion_triggers + len(trigger_facts),
        ),
        halted=True,
    )
    decision = DemotionDecisionV1(
        schema_version=1,
        profile_digest=profile.digest,
        tuple_digest=profile.tuple_digest,
        trigger=selected_trigger,
        prior_level=profile.current_level,
        resulting_level="L0",
        effective_at=observed_at,
        halt=True,
        external_action_authorized=False,
    )
    return updated_profile, decision
