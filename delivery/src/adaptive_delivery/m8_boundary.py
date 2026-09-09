"""M9 bridge to the integrated M8 earned-autonomy producer contracts.

M8 remains the sole owner of its tuple, cohort, profile, and recommendation.
This module reparses those records, recomputes their identity and aggregate
bindings, and adds only a source-pinned delivery handoff envelope.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
from typing import Any, ClassVar

from adaptive_factory.autonomy import (
    AutonomyProfileV1,
    AutonomyTupleV1,
    CohortEvidenceV1,
    PromotionRecommendationV1,
)
from adaptive_factory.contracts import ContractError as M8BoundaryError


PROVISIONAL_M8_PRODUCER_SHA = "f53275d5ed84022200419b399c799a995ed91a45"
M8AutonomyTupleV1 = AutonomyTupleV1
M8CohortEvidenceV1 = CohortEvidenceV1
M8AutonomyProfileV1 = AutonomyProfileV1
M8PromotionRecommendationV1 = PromotionRecommendationV1

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_MAX_WIRE_BYTES = 4 * 1024 * 1024
_MAX_WIRE_NODES = 500_000
_MAX_WIRE_DEPTH = 64


def _fail(field: str, detail: str) -> None:
    raise M8BoundaryError("invalid_contract", f"{field}: {detail}")


def _validate_json_bounds(value: object) -> None:
    stack = [(value, 0)]
    nodes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_WIRE_NODES or depth > _MAX_WIRE_DEPTH:
            _fail("canonical_body", "exceeds wire depth or node bounds")
        if isinstance(item, Mapping):
            if any(not isinstance(key, str) for key in item):
                _fail("canonical_body", "mapping keys must be strings")
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, (list, tuple)):
            stack.extend((child, depth + 1) for child in item)
        elif item is not None and type(item) not in (str, bool, int):
            _fail("canonical_body", "contains a non-JSON value")


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
        raise M8BoundaryError("invalid_contract", "canonical_body") from exc
    if len(encoded) > _MAX_WIRE_BYTES:
        _fail("canonical_body", "exceeds bounded wire size")
    return encoded


def _domain_digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + _canonical_bytes(value)).hexdigest()


def _cohort_aggregates(cohort: CohortEvidenceV1) -> dict[str, int]:
    tasks = cohort.tasks
    outcomes = {outcome.digest: outcome for outcome in cohort.m7_handoff.cohort.outcomes}
    linked = tuple(outcomes[task.m7_outcome_digest] for task in tasks)
    latencies = tuple(sorted(task.latency_ms for task in tasks))
    p95_rank = (95 * len(latencies) + 99) // 100
    return {
        "accepted_task_count": sum(
            outcome.human_decision == "merged_accepted" for outcome in linked
        ),
        "audit_sample_count": sum(task.audit_sampled for task in tasks),
        "audit_accepted_count": sum(task.audit_accepted for task in tasks),
        "minimum_quality_score_millionths": min(
            task.quality_score_millionths for task in tasks
        ),
        "total_security_failures": sum(task.security_failure_count for task in tasks),
        "total_authorization_failures": sum(
            task.authorization_failure_count for task in tasks
        ),
        "total_duplicate_dispatches": sum(
            task.duplicate_dispatch_count for task in tasks
        ),
        "maximum_cost_usd_micros": max(task.cost_usd_micros for task in tasks),
        "p95_latency_ms": latencies[p95_rank - 1],
        "total_demotion_triggers": sum(task.demotion_trigger_count for task in tasks),
    }


@dataclass(frozen=True, slots=True)
class M8DeliveryHandoffV1:
    schema_version: int
    producer_commit_sha: str
    cohort: CohortEvidenceV1
    profile: AutonomyProfileV1
    recommendation: PromotionRecommendationV1
    handoff_digest: str

    DOMAIN: ClassVar[str] = "adaptive-delivery.m8-delivery-handoff/v1"
    SOURCE_STATUS: ClassVar[str] = "blocked_pending_durable_m8_lookup"
    EXTERNAL_ACTION_AUTHORIZED: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            _fail("m8_handoff.schema_version", "must equal 1")
        if (
            not isinstance(self.producer_commit_sha, str)
            or not _HEX40.fullmatch(self.producer_commit_sha)
            or self.producer_commit_sha != PROVISIONAL_M8_PRODUCER_SHA
        ):
            _fail("m8_handoff.producer_commit_sha", "is not the pinned M8 producer")
        if type(self.cohort) is not CohortEvidenceV1:
            _fail("m8_handoff.cohort", "must be actual M8 cohort evidence")
        if type(self.profile) is not AutonomyProfileV1:
            _fail("m8_handoff.profile", "must be actual M8 profile evidence")
        if type(self.recommendation) is not PromotionRecommendationV1:
            _fail("m8_handoff.recommendation", "must be actual M8 recommendation")

        reparsed_cohort = CohortEvidenceV1.from_dict(self.cohort.to_dict())
        reparsed_profile = AutonomyProfileV1.from_dict(self.profile.to_dict())
        reparsed_recommendation = PromotionRecommendationV1.from_dict(
            self.recommendation.to_dict()
        )
        if (
            reparsed_cohort != self.cohort
            or reparsed_profile != self.profile
            or reparsed_recommendation != self.recommendation
        ):
            _fail("m8_handoff", "producer reconstruction differs")

        tuple_digest = self.cohort.autonomy_tuple.digest
        if (
            self.profile.tuple_digest != tuple_digest
            or self.recommendation.tuple_digest != tuple_digest
        ):
            _fail("m8_handoff.tuple_digest", "tuple equality chain is broken")
        if (
            self.profile.cohort_digest != self.cohort.digest
            or self.recommendation.cohort_digest != self.cohort.digest
        ):
            _fail("m8_handoff.cohort_digest", "cohort equality chain is broken")
        if self.recommendation.current_level != self.profile.current_level:
            _fail("m8_handoff.current_level", "profile and recommendation differ")
        if not (
            self.cohort.autonomy_tuple.expires_at
            == self.profile.expires_at
            == self.recommendation.expires_at
        ):
            _fail("m8_handoff.expires_at", "producer expiries differ")
        for name, expected in _cohort_aggregates(self.cohort).items():
            if getattr(self.profile, name) != expected:
                _fail("m8_handoff.profile_aggregate", f"{name} does not match cohort")
        if (
            self.cohort.m7_handoff.external_acceptance_available
            or self.cohort.m7_handoff.currentness_available
        ):
            _fail("m8_handoff", "durable upstream authority is not locally available")
        if not isinstance(self.handoff_digest, str) or not _HEX64.fullmatch(
            self.handoff_digest
        ):
            _fail("m8_handoff.handoff_digest", "must be lowercase 64-hex")
        if self.handoff_digest != self.expected_digest:
            _fail("m8_handoff.handoff_digest", "does not bind the handoff")

    @classmethod
    def from_dict(cls, data: object) -> "M8DeliveryHandoffV1":
        _validate_json_bounds(data)
        if not isinstance(data, Mapping) or set(data) != {
            "schema_version",
            "producer_commit_sha",
            "cohort",
            "profile",
            "recommendation",
            "handoff_digest",
        }:
            _fail("m8_handoff", "has missing or unknown fields")
        return cls(
            schema_version=data["schema_version"],
            producer_commit_sha=data["producer_commit_sha"],
            cohort=CohortEvidenceV1.from_dict(data["cohort"]),
            profile=AutonomyProfileV1.from_dict(data["profile"]),
            recommendation=PromotionRecommendationV1.from_dict(data["recommendation"]),
            handoff_digest=data["handoff_digest"],
        )

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
    def durable_acceptance_available(self) -> bool:
        return False

    @property
    def durable_currentness_available(self) -> bool:
        return False


def m8_gate_reasons(handoff: M8DeliveryHandoffV1, at: datetime) -> tuple[str, ...]:
    """Project a typed M8 record into M9's deterministic fail-closed reasons."""

    if type(handoff) is not M8DeliveryHandoffV1:
        _fail("m8_handoff", "must be the exact bridge type")
    if not isinstance(at, datetime) or at.tzinfo is None:
        _fail("m8_evaluation_time", "must be timezone-aware")
    profile = handoff.profile
    recommendation = handoff.recommendation
    reasons: set[str] = set()
    if at < recommendation.evaluated_at:
        reasons.add("m8_evidence_not_current")
    if at >= handoff.cohort.autonomy_tuple.expires_at:
        reasons.add("m8_evidence_expired")
    if (
        profile.halted
        or profile.total_demotion_triggers != 0
        or profile.accepted_task_count < 30
        or profile.accepted_task_count != len(handoff.cohort.tasks)
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
    if not eligible_recommendation:
        reasons.add("m8_recommendation_ineligible")
    return tuple(sorted(reasons))
