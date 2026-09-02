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
from adaptive_delivery.m8_boundary import (
    PROVISIONAL_M8_PRODUCER_SHA,
    M8AutonomyProfileV1,
    M8AutonomyTupleV1,
    M8CohortEvidenceV1,
    M8DeliveryHandoffV1,
    M8PromotionRecommendationV1,
)

SYNTHETIC_EVALUATION_TIME = "2026-09-02T09:21:00Z"
SYNTHETIC_DECISION_TIME = "2026-09-02T09:22:00Z"


def _json_value(value):
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _json_value(to_dict())
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


def synthetic_domain_digest(domain: str, value) -> str:
    encoded = json.dumps(
        _json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + encoded).hexdigest()


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


def synthetic_m8_evidence(
    *,
    repository_id: str = "synthetic/repository",
    policy_digest: str = "9" * 64,
    holdout_digest: str = "a" * 64,
    runner_digest: str = "b" * 64,
    tuple_updates: dict | None = None,
    task_updates: dict | None = None,
    cohort_updates: dict | None = None,
    profile_updates: dict | None = None,
    recommendation_updates: dict | None = None,
    producer_commit_sha: str = PROVISIONAL_M8_PRODUCER_SHA,
) -> M8DeliveryHandoffV1:
    tuple_values = {
        "schema_version": 1,
        "repository_id": repository_id,
        "task_class": "low_risk_text_only",
        "m7_change_class": "feature",
        "agent_digest": "3" * 64,
        "validator_digest": "4" * 64,
        "provider_digest": "5" * 64,
        "model_digest": "6" * 64,
        "prompt_digest": "7" * 64,
        "policy_digest": policy_digest,
        "runner_digest": runner_digest,
        "holdout_digest": holdout_digest,
        "authority_digest": "8" * 64,
        "authority_ceiling": "L2",
        "expires_at": "2026-09-02T11:15:00Z",
    }
    direct_updates = tuple_updates or {}
    tuple_values.update(
        {
            key: value
            for key, value in direct_updates.items()
            if key not in {"m7_cohort_key_digest", "provider_mapping_digest"}
        }
    )
    m7_key = {
        "schema_version": 1,
        "repository_id": tuple_values["repository_id"],
        "change_class": tuple_values["m7_change_class"],
        "agent_digest": tuple_values["agent_digest"],
        "validator_digest": tuple_values["validator_digest"],
        "model_digest": tuple_values["model_digest"],
        "prompt_digest": tuple_values["prompt_digest"],
        "policy_digest": tuple_values["policy_digest"],
        "runner_digest": tuple_values["runner_digest"],
        "holdout_digest": tuple_values["holdout_digest"],
        "authority_digest": tuple_values["authority_digest"],
    }
    m7_key_digest = synthetic_domain_digest(
        "adaptive-factory.m7-shadow-cohort-key/v1", m7_key
    )
    provider_mapping = {
        "schema_version": 1,
        "cohort_key_digest": m7_key_digest,
        "validator_digest": tuple_values["validator_digest"],
        "provider_digest": tuple_values["provider_digest"],
    }
    tuple_values["m7_cohort_key_digest"] = direct_updates.get(
        "m7_cohort_key_digest", m7_key_digest
    )
    tuple_values["provider_mapping_digest"] = direct_updates.get(
        "provider_mapping_digest",
        synthetic_domain_digest(
            "adaptive-factory.m8-m7-provider-mapping/v1", provider_mapping
        ),
    )
    autonomy_tuple = M8AutonomyTupleV1(**tuple_values)
    tasks = []
    bundles = []
    outcomes = []
    for index in range(30):
        task_id = f"task-{index:03d}"
        run_id = f"run-{index:03d}"
        exact_head_sha = f"{index + 1:040x}"
        bundle_digest = f"{index + 100:064x}"
        human_receipt = f"{index + 300:064x}"
        bundle = {
            "schema_version": 1,
            "status": "synthetic_only",
            "bundle_digest": bundle_digest,
            "evidence": {
                "m4": {"task_id": task_id, "run_id": run_id},
                "m5": {"result_exact_head_sha": exact_head_sha},
            },
        }
        outcome = {
            "schema_version": 1,
            "bundle_digest": bundle_digest,
            "human_evidence_digest": human_receipt,
            "human_decision": "merged_accepted",
        }
        bundles.append(bundle)
        outcomes.append(outcome)
        task = {
            "schema_version": 1,
            "tuple_digest": autonomy_tuple.digest,
            "task_id": task_id,
            "run_id": run_id,
            "exact_head_sha": exact_head_sha,
            "observed_at": "2026-09-02T09:05:00Z",
            "m7_bundle_digest": bundle_digest,
            "m7_outcome_digest": synthetic_domain_digest(
                "adaptive-factory.m7-shadow-outcome/v1", outcome
            ),
            "audit_sampled": True,
            "audit_accepted": True,
            "human_acceptance_receipt_digest": human_receipt,
            "attestation_receipt_digest": f"{index + 400:064x}",
            "quality_score_millionths": 990_000,
            "security_failure_count": 0,
            "authorization_failure_count": 0,
            "duplicate_dispatch_count": 0,
            "cost_usd_micros": 1_000,
            "latency_ms": 100,
            "demotion_trigger_count": 0,
        }
        if index == 0:
            task.update(task_updates or {})
        tasks.append(task)
    cohort_body = {
        "schema_version": 1,
        "autonomy_tuple": autonomy_tuple.to_dict(),
        "tasks": tasks,
        "m7_handoff": {
            "schema_version": 1,
            "provider_mapping": provider_mapping,
            "bundles": bundles,
            "cohort": {
                "schema_version": 1,
                "key": m7_key,
                "outcomes": outcomes,
            },
            "aggregate": {"schema_version": 1},
            "evaluation": {"schema_version": 1},
        },
        "window_started_at": "2026-09-02T09:00:00Z",
        "window_ended_at": "2026-09-02T09:10:00Z",
        "minimum_human_acceptances": 30,
        "minimum_audit_rate_millionths": 200_000,
        "minimum_quality_score_millionths": 950_000,
        "maximum_security_failures": 0,
        "maximum_authorization_failures": 0,
        "maximum_duplicate_dispatches": 0,
        "maximum_cost_usd_micros": 10_000,
        "maximum_latency_ms": 500,
        "maximum_demotion_triggers": 0,
    }
    cohort_body.update(cohort_updates or {})
    cohort = M8CohortEvidenceV1.from_dict(cohort_body)
    profile_values = {
        "schema_version": 1,
        "tuple_digest": autonomy_tuple.digest,
        "cohort_digest": cohort.digest,
        "current_level": "L2",
        "accepted_task_count": cohort.accepted_task_count,
        "audit_sample_count": cohort.audit_sample_count,
        "audit_accepted_count": cohort.audit_accepted_count,
        "minimum_quality_score_millionths": cohort.minimum_quality_score_millionths,
        "total_security_failures": cohort.total_security_failures,
        "total_authorization_failures": cohort.total_authorization_failures,
        "total_duplicate_dispatches": cohort.total_duplicate_dispatches,
        "maximum_cost_usd_micros": cohort.maximum_cost_usd_micros,
        "p95_latency_ms": cohort.p95_latency_ms,
        "total_demotion_triggers": cohort.total_demotion_triggers,
        "expires_at": autonomy_tuple.expires_at,
        "halted": False,
    }
    profile_values.update(profile_updates or {})
    profile = M8AutonomyProfileV1(**profile_values)
    recommendation_values = {
        "schema_version": 1,
        "tuple_digest": autonomy_tuple.digest,
        "cohort_digest": cohort.digest,
        "current_level": profile.current_level,
        "recommended_level": "L2",
        "reason_code": "already_at_ceiling",
        "evaluated_at": "2026-09-02T09:14:00Z",
        "expires_at": autonomy_tuple.expires_at,
        "separate_activation_required": True,
        "external_action_authorized": False,
    }
    recommendation_values.update(recommendation_updates or {})
    recommendation = M8PromotionRecommendationV1(**recommendation_values)
    handoff_body = {
        "schema_version": 1,
        "producer_commit_sha": producer_commit_sha,
        "cohort": cohort.to_dict(),
        "profile": profile.to_dict(),
        "recommendation": recommendation.to_dict(),
    }
    return M8DeliveryHandoffV1(
        schema_version=1,
        producer_commit_sha=producer_commit_sha,
        cohort=cohort,
        profile=profile,
        recommendation=recommendation,
        handoff_digest=synthetic_domain_digest(
            "adaptive-delivery.m8-delivery-handoff/v1", handoff_body
        ),
    )


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
    values.setdefault(
        "m8_evidence",
        synthetic_m8_evidence(
            repository_id=values["repository_id"],
            policy_digest=values["policy_digest"],
            holdout_digest=values["holdout_digest"],
            runner_digest=values["runner_image_digest"],
        ),
    )
    resource_names = (
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
