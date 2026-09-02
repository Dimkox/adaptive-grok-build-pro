"""Synthetic opaque M9 fixtures.

Nothing in this module represents accepted evidence, a real repository, an
environment, an authority envelope, or a deployment capability.  Repeated hex
values are opaque test identities only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass

from adaptive_delivery.contracts import (
    DeliveryDecisionV1,
    DeliveryPromotionV1,
    EnvironmentObservationV1,
    ExposurePlanV1,
    SignedArtifactRefV1,
)

SYNTHETIC_EVALUATION_TIME = "2026-09-02T09:21:00Z"
SYNTHETIC_DECISION_TIME = "2026-09-02T09:22:00Z"


def _json_value(value):
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def synthetic_digest(value) -> str:
    encoded = json.dumps(
        _json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def synthetic_artifact(*, previous: bool = False, **updates) -> SignedArtifactRefV1:
    values = {
        "schema_version": 1,
        "repository_id": "synthetic/repository",
        "merged_sha": ("b" if previous else "a") * 40,
        "artifact_digest": ("f" if previous else "1") * 64,
        "sbom_digest": "2" * 64,
        "provenance_digest": "3" * 64,
        "supply_chain_manifest_digest": "4" * 64,
        "image_digest": "5" * 64,
        "authority_envelope_digest": ("e" if previous else "6") * 64,
        "authority_verifier_id": "synthetic-artifact-verifier/v1",
        "authority_verified_at": "2026-09-02T09:00:00Z",
        "authority_expires_at": "2026-09-02T12:00:00Z",
        "authority_scope": "signed_artifact_use",
    }
    values.update(updates)
    resource_names = (
        "schema_version",
        "repository_id",
        "merged_sha",
        "artifact_digest",
        "sbom_digest",
        "provenance_digest",
        "supply_chain_manifest_digest",
        "image_digest",
    )
    values["authority_resource_digest"] = synthetic_digest(
        {name: values[name] for name in resource_names}
    )
    return SignedArtifactRefV1(**values)


def synthetic_plan(**updates) -> ExposurePlanV1:
    values = {
        "schema_version": 1,
        "plan_id": "synthetic/plan",
        "environment_order": (
            "preview",
            "staging",
            "bounded_canary",
            "production",
        ),
        "preview_basis_points": (10000,),
        "staging_basis_points": (10000,),
        "canary_basis_points": (100, 500, 1000),
        "max_observation_age_seconds": 300,
        "evaluation_window_seconds": 120,
        "required_metric_families": (
            "health",
            "error",
            "latency",
            "security",
            "business",
        ),
        "health_min_basis_points": 9900,
        "error_max_basis_points": 100,
        "latency_p95_max_ms": 500,
        "security_critical_max": 0,
        "business_min_basis_points": 9500,
        "allowed_recovery_actions": (
            "halt",
            "decrease_exposure",
            "restore_previous",
        ),
    }
    values.update(updates)
    values["plan_digest"] = synthetic_digest(values)
    return ExposurePlanV1(**values)


def synthetic_promotion(
    *,
    artifact: SignedArtifactRefV1 | None = None,
    previous_artifact: SignedArtifactRefV1 | None = None,
    plan: ExposurePlanV1 | None = None,
    **updates,
) -> DeliveryPromotionV1:
    values = {
        "schema_version": 1,
        "promotion_id": "synthetic/promotion",
        "repository_id": "synthetic/repository",
        "artifact": artifact or synthetic_artifact(),
        "previous_signed_artifact": previous_artifact
        or synthetic_artifact(previous=True),
        "m8_profile_digest": "7" * 64,
        "m8_cohort_digest": "8" * 64,
        "policy_digest": "9" * 64,
        "holdout_digest": "a" * 64,
        "runner_image_digest": "b" * 64,
        "environment_set_digest": "c" * 64,
        "exposure_plan": plan or synthetic_plan(),
        "requested_at": "2026-09-02T09:15:00Z",
        "expires_at": "2026-09-02T11:00:00Z",
        "authority_envelope_digest": "d" * 64,
        "authority_verifier_id": "synthetic-promotion-verifier/v1",
        "authority_verified_at": "2026-09-02T09:10:00Z",
        "authority_expires_at": "2026-09-02T11:30:00Z",
        "authority_scope": "nonproduction_staged_delivery",
    }
    values.update(updates)
    resource_names = (
        "schema_version",
        "promotion_id",
        "repository_id",
        "artifact",
        "previous_signed_artifact",
        "m8_profile_digest",
        "m8_cohort_digest",
        "policy_digest",
        "holdout_digest",
        "runner_image_digest",
        "environment_set_digest",
        "exposure_plan",
        "requested_at",
        "expires_at",
    )
    values["authority_resource_digest"] = synthetic_digest(
        {name: values[name] for name in resource_names}
    )
    values["promotion_digest"] = synthetic_digest(values)
    return DeliveryPromotionV1(**values)


def synthetic_observation(
    promotion: DeliveryPromotionV1 | None = None,
    **updates,
) -> EnvironmentObservationV1:
    bound_promotion = promotion or synthetic_promotion()
    environment = updates.get("environment", "preview")
    default_exposure = {
        "preview": bound_promotion.exposure_plan.preview_basis_points[0],
        "staging": bound_promotion.exposure_plan.staging_basis_points[0],
        "bounded_canary": bound_promotion.exposure_plan.canary_basis_points[0],
        "production": 10000,
    }[environment]
    values = {
        "schema_version": 1,
        "observation_id": "synthetic/observation",
        "promotion_digest": bound_promotion.promotion_digest,
        "artifact_digest": bound_promotion.artifact.artifact_digest,
        "environment_set_digest": bound_promotion.environment_set_digest,
        "environment": environment,
        "exposure_basis_points": default_exposure,
        "policy_digest": bound_promotion.policy_digest,
        "captured_at": "2026-09-02T09:20:00Z",
        "window_started_at": "2026-09-02T09:18:00Z",
        "window_ended_at": "2026-09-02T09:20:00Z",
        "health_basis_points": 9990,
        "error_basis_points": 10,
        "latency_p95_ms": 125,
        "security_critical_count": 0,
        "business_basis_points": 9800,
        "sample_count": 500,
        "source_snapshot_digest": "e" * 64,
    }
    values.update(updates)
    values["observation_digest"] = synthetic_digest(values)
    return EnvironmentObservationV1(**values)


def synthetic_denied_decision(
    promotion: DeliveryPromotionV1 | None = None,
    **updates,
) -> DeliveryDecisionV1:
    bound_promotion = promotion or synthetic_promotion()
    values = {
        "schema_version": 1,
        "decision_id": "synthetic/denied-decision",
        "promotion_digest": bound_promotion.promotion_digest,
        "artifact_digest": bound_promotion.artifact.artifact_digest,
        "environment": "bounded_canary",
        "exposure_basis_points": bound_promotion.exposure_plan.canary_basis_points[1],
        "observation_set_digest": "f" * 64,
        "evaluation_time": SYNTHETIC_EVALUATION_TIME,
        "outcome": "deny",
        "reason_codes": ("health_below_minimum",),
        "next_environment": None,
        "next_exposure_basis_points": None,
    }
    values.update(updates)
    values["decision_digest"] = synthetic_digest(values)
    return DeliveryDecisionV1(**values)
