"""Pure deterministic evaluation for an exact M9 promotion snapshot."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import fields
from datetime import UTC, datetime

from .contracts import (
    ENVIRONMENT_ORDER,
    ContractError,
    DeliveryDecisionV1,
    DeliveryPromotionV1,
    EnvironmentObservationV1,
    SignedArtifactRefV1,
    canonical_digest,
)
from .m8_boundary import m8_gate_reasons

_MAX_OBSERVATIONS = 128


def _parse_time(value: str, field: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except (TypeError, ValueError) as exc:
        raise ContractError(field, "must be UTC RFC3339 whole seconds ending in Z") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ContractError(field, "must be UTC RFC3339 whole seconds ending in Z")
    return parsed


def _record_payload(record: object, digest_field: str) -> dict[str, object]:
    return {
        field.name: getattr(record, field.name)
        for field in fields(record)
        if field.name != digest_field
    }


def _artifact_resource(artifact: SignedArtifactRefV1) -> dict[str, object]:
    names = (
        "schema_version",
        "repository_id",
        "merged_sha",
        "artifact_digest",
        "sbom_digest",
        "provenance_digest",
        "supply_chain_manifest_digest",
        "image_digest",
    )
    return {name: getattr(artifact, name) for name in names}


def _promotion_resource(promotion: DeliveryPromotionV1) -> dict[str, object]:
    names = (
        "schema_version",
        "promotion_id",
        "repository_id",
        "artifact",
        "previous_signed_artifact",
        "m8_evidence",
        "policy_digest",
        "holdout_digest",
        "runner_image_digest",
        "environment_set_digest",
        "exposure_plan",
        "requested_at",
        "expires_at",
    )
    return {name: getattr(promotion, name) for name in names}


def _authority_reasons(
    promotion: DeliveryPromotionV1, evaluation_time: datetime
) -> list[str]:
    reasons: list[str] = []
    authorities = (promotion, promotion.artifact, promotion.previous_signed_artifact)
    if any(
        evaluation_time < _parse_time(item.authority_verified_at, "authority_verified_at")
        for item in authorities
    ) or evaluation_time < _parse_time(promotion.requested_at, "requested_at"):
        reasons.append("authority_not_yet_valid")
    if any(
        evaluation_time >= _parse_time(item.authority_expires_at, "authority_expires_at")
        for item in authorities
    ):
        reasons.append("authority_expired")
    if evaluation_time >= _parse_time(promotion.expires_at, "expires_at"):
        reasons.append("promotion_expired")
    reasons.extend(m8_gate_reasons(promotion.m8_evidence, evaluation_time))

    if (
        promotion.authority_scope != "nonproduction_staged_delivery"
        or promotion.artifact.authority_scope != "signed_artifact_use"
        or promotion.previous_signed_artifact.authority_scope != "signed_artifact_use"
    ):
        reasons.append("authority_scope_mismatch")
    resource_pairs = (
        (
            promotion.authority_resource_digest,
            canonical_digest(_promotion_resource(promotion)),
        ),
        (
            promotion.artifact.authority_resource_digest,
            canonical_digest(_artifact_resource(promotion.artifact)),
        ),
        (
            promotion.previous_signed_artifact.authority_resource_digest,
            canonical_digest(_artifact_resource(promotion.previous_signed_artifact)),
        ),
    )
    if any(supplied != expected for supplied, expected in resource_pairs):
        reasons.append("authority_resource_mismatch")
    if promotion.promotion_digest != canonical_digest(
        _record_payload(promotion, "promotion_digest")
    ):
        reasons.append("promotion_mismatch")
    return reasons


def _normalize_observations(
    observation_set: EnvironmentObservationV1 | Sequence[EnvironmentObservationV1],
) -> tuple[EnvironmentObservationV1, ...]:
    if isinstance(observation_set, EnvironmentObservationV1):
        return (observation_set,)
    if isinstance(observation_set, (str, bytes)) or not isinstance(
        observation_set, Sequence
    ):
        raise ContractError(
            "observation_set", "must be one observation or an immutable observation sequence"
        )
    count = len(observation_set)
    if count > _MAX_OBSERVATIONS:
        raise ContractError(
            "observation_set", f"cannot exceed {_MAX_OBSERVATIONS} observations"
        )
    observations = tuple(observation_set[index] for index in range(count))
    if len(observations) > _MAX_OBSERVATIONS:
        raise ContractError(
            "observation_set", f"cannot exceed {_MAX_OBSERVATIONS} observations"
        )
    if any(not isinstance(item, EnvironmentObservationV1) for item in observations):
        raise ContractError("observation_set", "contains a non-observation value")
    return observations


def _target_state(
    promotion: DeliveryPromotionV1,
    observations: tuple[EnvironmentObservationV1, ...],
    environment: str | None,
    exposure_basis_points: int | None,
) -> tuple[str, int]:
    if environment is None and exposure_basis_points is None and len(observations) == 1:
        return observations[0].environment, observations[0].exposure_basis_points
    if environment not in ENVIRONMENT_ORDER:
        raise ContractError("environment", "must name the exact current environment")
    if type(exposure_basis_points) is not int or not 0 <= exposure_basis_points <= 10000:
        raise ContractError(
            "exposure_basis_points", "must name the exact current integer exposure"
        )
    return environment, exposure_basis_points


def _planned_exposures(promotion: DeliveryPromotionV1, environment: str) -> tuple[int, ...]:
    plan = promotion.exposure_plan
    if environment == "preview":
        return plan.preview_basis_points
    if environment == "staging":
        return plan.staging_basis_points
    if environment == "bounded_canary":
        return plan.canary_basis_points
    return (10000,)


def _binding_reasons(
    promotion: DeliveryPromotionV1,
    observations: tuple[EnvironmentObservationV1, ...],
    environment: str,
    exposure_basis_points: int,
) -> list[str]:
    reasons: list[str] = []
    if exposure_basis_points not in _planned_exposures(promotion, environment):
        reasons.append("exposure_mismatch")
    checks = (
        (
            "promotion_mismatch",
            lambda item: item.promotion_digest != promotion.promotion_digest,
        ),
        (
            "artifact_mismatch",
            lambda item: item.artifact_digest != promotion.artifact.artifact_digest,
        ),
        (
            "environment_set_mismatch",
            lambda item: item.environment_set_digest
            != promotion.environment_set_digest,
        ),
        ("environment_mismatch", lambda item: item.environment != environment),
        (
            "exposure_mismatch",
            lambda item: item.exposure_basis_points != exposure_basis_points,
        ),
        ("policy_mismatch", lambda item: item.policy_digest != promotion.policy_digest),
    )
    for reason, predicate in checks:
        if any(predicate(item) for item in observations):
            reasons.append(reason)
    return reasons


def _cardinality_reasons(
    observations: tuple[EnvironmentObservationV1, ...],
) -> list[str]:
    if not observations:
        return ["observation_incomplete"]
    reasons: list[str] = []
    if len(observations) > 1:
        reasons.append("observation_duplicate")
    observation_ids = tuple(item.observation_id for item in observations)
    observation_digests = tuple(item.observation_digest for item in observations)
    if len(set(observation_ids)) != len(observation_ids) or len(
        set(observation_digests)
    ) != len(observation_digests):
        reasons.append("observation_replay")

    contexts: dict[tuple[object, ...], set[str]] = {}
    for item in observations:
        context = (
            item.promotion_digest,
            item.artifact_digest,
            item.environment_set_digest,
            item.environment,
            item.exposure_basis_points,
            item.policy_digest,
        )
        contexts.setdefault(context, set()).add(item.observation_digest)
        if item.observation_digest != canonical_digest(
            _record_payload(item, "observation_digest")
        ):
            reasons.append("observation_contradictory")
    if any(len(digests) > 1 for digests in contexts.values()):
        reasons.append("observation_contradictory")
    return reasons


def _time_reasons(
    promotion: DeliveryPromotionV1,
    observations: tuple[EnvironmentObservationV1, ...],
    evaluation_time: datetime,
) -> list[str]:
    reasons: list[str] = []
    requested_at = _parse_time(promotion.requested_at, "requested_at")
    expires_at = _parse_time(promotion.expires_at, "expires_at")
    for item in observations:
        captured_at = _parse_time(item.captured_at, "captured_at")
        window_started_at = _parse_time(item.window_started_at, "window_started_at")
        window_ended_at = _parse_time(item.window_ended_at, "window_ended_at")
        window_seconds = int((window_ended_at - window_started_at).total_seconds())
        if (
            captured_at > evaluation_time
            or window_ended_at > evaluation_time
            or window_started_at < requested_at
            or window_ended_at >= expires_at
            or window_seconds != promotion.exposure_plan.evaluation_window_seconds
        ):
            reasons.append("observation_time_invalid")
        capture_age_seconds = (evaluation_time - captured_at).total_seconds()
        window_age_seconds = (evaluation_time - window_ended_at).total_seconds()
        if (
            max(capture_age_seconds, window_age_seconds)
            > promotion.exposure_plan.max_observation_age_seconds
        ):
            reasons.append("observation_stale")
    return reasons


def _threshold_reasons(
    promotion: DeliveryPromotionV1,
    observations: tuple[EnvironmentObservationV1, ...],
) -> list[str]:
    plan = promotion.exposure_plan
    checks = (
        (
            "health_below_minimum",
            lambda item: item.health_basis_points < plan.health_min_basis_points,
        ),
        (
            "error_above_maximum",
            lambda item: item.error_basis_points > plan.error_max_basis_points,
        ),
        (
            "latency_above_maximum",
            lambda item: item.latency_p95_ms > plan.latency_p95_max_ms,
        ),
        (
            "security_critical",
            lambda item: item.security_critical_count > plan.security_critical_max,
        ),
        (
            "business_below_minimum",
            lambda item: item.business_basis_points < plan.business_min_basis_points,
        ),
    )
    return [
        reason
        for reason, predicate in checks
        if any(predicate(item) for item in observations)
    ]


def _next_state(
    promotion: DeliveryPromotionV1,
    environment: str,
    exposure_basis_points: int,
) -> tuple[str, int] | None:
    if environment == "production":
        return None
    exposures = _planned_exposures(promotion, environment)
    if exposure_basis_points not in exposures:
        return None
    index = exposures.index(exposure_basis_points)
    if index + 1 < len(exposures):
        return environment, exposures[index + 1]
    environment_index = ENVIRONMENT_ORDER.index(environment)
    next_environment = ENVIRONMENT_ORDER[environment_index + 1]
    if next_environment == "production":
        return None
    return next_environment, _planned_exposures(promotion, next_environment)[0]


def _observation_set_digest(
    observations: tuple[EnvironmentObservationV1, ...],
) -> str:
    return canonical_digest(tuple(sorted(item.observation_digest for item in observations)))


def evaluate_delivery(
    promotion: DeliveryPromotionV1,
    observation_set: EnvironmentObservationV1 | Sequence[EnvironmentObservationV1],
    evaluation_time: str,
    *,
    environment: str | None = None,
    exposure_basis_points: int | None = None,
) -> DeliveryDecisionV1:
    """Evaluate one complete current snapshot without performing any side effect."""

    if not isinstance(promotion, DeliveryPromotionV1):
        raise ContractError("promotion", "must be DeliveryPromotionV1")
    observations = _normalize_observations(observation_set)
    current_environment, current_exposure = _target_state(
        promotion, observations, environment, exposure_basis_points
    )
    evaluated_at = _parse_time(evaluation_time, "evaluation_time")

    # The order is part of the fail-closed contract.  Every check runs and the
    # externally visible closed reasons are then sorted and deduplicated.
    reasons = _authority_reasons(promotion, evaluated_at)
    reasons.extend(
        _binding_reasons(
            promotion,
            observations,
            current_environment,
            current_exposure,
        )
    )
    reasons.extend(_cardinality_reasons(observations))
    reasons.extend(_time_reasons(promotion, observations, evaluated_at))
    reasons.extend(_threshold_reasons(promotion, observations))
    failure_reasons = tuple(sorted(set(reasons)))

    next_state = _next_state(promotion, current_environment, current_exposure)
    if current_environment == "production":
        outcome = "needs_human"
        reasons = tuple(sorted(set(failure_reasons + ("production_requires_human",))))
        next_state = None
    elif failure_reasons:
        outcome = "deny"
        reasons = failure_reasons
        next_state = None
    elif next_state is None:
        outcome = "needs_human"
        reasons = ("production_requires_human", "thresholds_passed")
    else:
        outcome = "advance"
        reasons = ("thresholds_passed",)

    observation_digest = _observation_set_digest(observations)
    identity = {
        "promotion_digest": promotion.promotion_digest,
        "artifact_digest": promotion.artifact.artifact_digest,
        "environment": current_environment,
        "exposure_basis_points": current_exposure,
        "observation_set_digest": observation_digest,
        "evaluation_time": evaluation_time,
        "outcome": outcome,
        "reason_codes": reasons,
        "next_state": next_state,
    }
    values = {
        "schema_version": 1,
        "decision_id": f"decision/{canonical_digest(identity)[:32]}",
        "promotion_digest": promotion.promotion_digest,
        "artifact_digest": promotion.artifact.artifact_digest,
        "environment": current_environment,
        "exposure_basis_points": current_exposure,
        "observation_set_digest": observation_digest,
        "evaluation_time": evaluation_time,
        "outcome": outcome,
        "reason_codes": reasons,
        "next_environment": next_state[0] if next_state is not None else None,
        "next_exposure_basis_points": next_state[1] if next_state is not None else None,
    }
    values["decision_digest"] = canonical_digest(values)
    return DeliveryDecisionV1(**values)
