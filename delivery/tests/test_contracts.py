import hashlib
import json
import unittest
from dataclasses import FrozenInstanceError, asdict, fields

from delivery.tests.synthetic_fixtures import synthetic_m8_evidence

from adaptive_delivery.contracts import (
    ContractError,
    DeliveryDecisionV1,
    DeliveryEvidenceV1,
    DeliveryPromotionV1,
    EnvironmentObservationV1,
    ExposurePlanV1,
    RecoveryDecisionV1,
    SignedArtifactRefV1,
    canonical_digest,
)

HEX = {
    name: character * 64
    for name, character in zip(
        (
            "artifact",
            "sbom",
            "provenance",
            "manifest",
            "image",
            "envelope",
            "profile",
            "cohort",
            "policy",
            "holdout",
            "runner",
            "environment_set",
            "observation_set",
            "previous_evidence",
            "delivery_decision",
            "recovery_decision",
            "source_snapshot",
            "failed_decision",
        ),
        "123456789abcdefabc",
        strict=True,
    )
}


def _json_value(value):
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _json_value(to_dict())
    if hasattr(value, "__dataclass_fields__"):
        return {key: _json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _digest(value):
    encoded = json.dumps(
        _json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def artifact_fields(**updates):
    values = {
        "schema_version": 1,
        "repository_id": "owner/repository",
        "merged_sha": "a" * 40,
        "artifact_digest": HEX["artifact"],
        "sbom_digest": HEX["sbom"],
        "provenance_digest": HEX["provenance"],
        "supply_chain_manifest_digest": HEX["manifest"],
        "image_digest": HEX["image"],
        "authority_envelope_digest": HEX["envelope"],
        "authority_verifier_id": "trust-verifier/v1",
        "authority_verified_at": "2026-09-02T09:00:00Z",
        "authority_expires_at": "2026-09-02T12:00:00Z",
        "authority_scope": "signed_artifact_use",
    }
    resource = {
        key: values[key]
        for key in (
            "schema_version",
            "repository_id",
            "merged_sha",
            "artifact_digest",
            "sbom_digest",
            "provenance_digest",
            "supply_chain_manifest_digest",
            "image_digest",
        )
    }
    values["authority_resource_digest"] = _digest(resource)
    values.update(updates)
    return values


def plan_fields(**updates):
    values = {
        "schema_version": 1,
        "plan_id": "plan/m9-preview-staging-canary",
        "environment_order": ("preview", "staging", "bounded_canary", "production"),
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
    resource = {key: value for key, value in values.items() if key != "plan_digest"}
    values.setdefault("plan_digest", _digest(resource))
    return values


def promotion_fields(**updates):
    artifact = SignedArtifactRefV1(**artifact_fields())
    previous_values = artifact_fields(
        merged_sha="b" * 40,
        artifact_digest="f" * 64,
        authority_envelope_digest="e" * 64,
    )
    previous_resource = {
        key: previous_values[key]
        for key in (
            "schema_version",
            "repository_id",
            "merged_sha",
            "artifact_digest",
            "sbom_digest",
            "provenance_digest",
            "supply_chain_manifest_digest",
            "image_digest",
        )
    }
    previous_values["authority_resource_digest"] = _digest(previous_resource)
    values = {
        "schema_version": 1,
        "promotion_id": "promotion/m9-001",
        "repository_id": "owner/repository",
        "artifact": artifact,
        "previous_signed_artifact": SignedArtifactRefV1(**previous_values),
        "m8_evidence": synthetic_m8_evidence(
            repository_id="owner/repository",
            policy_digest=HEX["policy"],
            holdout_digest=HEX["holdout"],
            runner_digest=HEX["runner"],
        ),
        "policy_digest": HEX["policy"],
        "holdout_digest": HEX["holdout"],
        "runner_image_digest": HEX["runner"],
        "environment_set_digest": HEX["environment_set"],
        "exposure_plan": ExposurePlanV1(**plan_fields()),
        "requested_at": "2026-09-02T09:15:00Z",
        "expires_at": "2026-09-02T11:00:00Z",
        "authority_envelope_digest": "d" * 64,
        "authority_verifier_id": "promotion-verifier/v1",
        "authority_verified_at": "2026-09-02T09:10:00Z",
        "authority_expires_at": "2026-09-02T11:30:00Z",
        "authority_scope": "nonproduction_staged_delivery",
    }
    values.update(updates)
    authority_resource = {
        key: values[key]
        for key in (
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
    }
    values.setdefault("authority_resource_digest", _digest(authority_resource))
    promotion_resource = dict(values)
    values.setdefault("promotion_digest", _digest(promotion_resource))
    return values


def observation_fields(**updates):
    promotion = DeliveryPromotionV1(**promotion_fields())
    values = {
        "schema_version": 1,
        "observation_id": "observation/preview-001",
        "promotion_digest": promotion.promotion_digest,
        "artifact_digest": promotion.artifact.artifact_digest,
        "environment_set_digest": promotion.environment_set_digest,
        "environment": "preview",
        "exposure_basis_points": 10000,
        "policy_digest": promotion.policy_digest,
        "captured_at": "2026-09-02T09:20:00Z",
        "window_started_at": "2026-09-02T09:18:00Z",
        "window_ended_at": "2026-09-02T09:20:00Z",
        "health_basis_points": 9990,
        "error_basis_points": 10,
        "latency_p95_ms": 125,
        "security_critical_count": 0,
        "business_basis_points": 9800,
        "sample_count": 500,
        "source_snapshot_digest": HEX["source_snapshot"],
    }
    values.update(updates)
    values.setdefault("observation_digest", _digest(values))
    return values


def decision_fields(**updates):
    promotion = DeliveryPromotionV1(**promotion_fields())
    values = {
        "schema_version": 1,
        "decision_id": "decision/preview-001",
        "promotion_digest": promotion.promotion_digest,
        "artifact_digest": promotion.artifact.artifact_digest,
        "environment": "preview",
        "exposure_basis_points": 10000,
        "observation_set_digest": HEX["observation_set"],
        "evaluation_time": "2026-09-02T09:21:00Z",
        "outcome": "advance",
        "reason_codes": ("thresholds_passed",),
        "next_environment": "staging",
        "next_exposure_basis_points": 10000,
    }
    values.update(updates)
    values.setdefault("decision_digest", _digest(values))
    return values


def recovery_fields(**updates):
    promotion = DeliveryPromotionV1(**promotion_fields())
    values = {
        "schema_version": 1,
        "recovery_id": "recovery/preview-001",
        "promotion_digest": promotion.promotion_digest,
        "failed_decision_digest": HEX["failed_decision"],
        "environment": "preview",
        "current_exposure_basis_points": 10000,
        "action": "halt",
        "target_exposure_basis_points": None,
        "restore_artifact_digest": None,
        "reason_codes": ("recovery_halt",),
        "decision_time": "2026-09-02T09:22:00Z",
    }
    values.update(updates)
    values.setdefault("recovery_digest", _digest(values))
    return values


def evidence_fields(**updates):
    promotion = DeliveryPromotionV1(**promotion_fields())
    values = {
        "schema_version": 1,
        "evidence_id": "evidence/preview-001",
        "sequence": 1,
        "promotion_digest": promotion.promotion_digest,
        "previous_evidence_digest": None,
        "artifact_digest": promotion.artifact.artifact_digest,
        "environment": "preview",
        "exposure_basis_points": 10000,
        "observation_set_digest": HEX["observation_set"],
        "delivery_decision_digest": HEX["delivery_decision"],
        "recovery_decision_digest": None,
        "dry_run_effect": "entered_stage",
        "recorded_at": "2026-09-02T09:23:00Z",
        "reason_codes": ("thresholds_passed",),
    }
    values.update(updates)
    values.setdefault("evidence_digest", _digest(values))
    return values


class ContractTests(unittest.TestCase):
    def test_canonical_digest_is_stable_and_uses_canonical_json(self):
        expected = "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
        self.assertEqual(canonical_digest({"b": 2, "a": 1}), expected)
        self.assertEqual(canonical_digest({"a": 1, "b": 2}), expected)

    def test_canonical_digest_never_calls_an_unknown_to_dict_method(self):
        class MaliciousValue:
            called = False

            def to_dict(self):
                self.called = True
                return {"forged": "canonical body"}

        value = MaliciousValue()
        with self.assertRaisesRegex(ContractError, "not canonical JSON"):
            canonical_digest(value)
        self.assertFalse(value.called)

    def test_all_seven_v1_records_have_exact_closed_frozen_shapes(self):
        records = (
            SignedArtifactRefV1(**artifact_fields()),
            ExposurePlanV1(**plan_fields()),
            DeliveryPromotionV1(**promotion_fields()),
            EnvironmentObservationV1(**observation_fields()),
            DeliveryDecisionV1(**decision_fields()),
            RecoveryDecisionV1(**recovery_fields()),
            DeliveryEvidenceV1(**evidence_fields()),
        )
        for record in records:
            with self.subTest(record=type(record).__name__):
                with self.assertRaises(FrozenInstanceError):
                    record.schema_version = 2
                with self.assertRaises(TypeError):
                    type(record)(**asdict(record), unknown_field="forbidden")
                self.assertNotIn("__dict__", dir(record))

    def test_exact_field_names_are_frozen_for_every_v1_record(self):
        expected = {
            SignedArtifactRefV1: tuple(artifact_fields()),
            ExposurePlanV1: tuple(plan_fields()),
            DeliveryPromotionV1: tuple(promotion_fields()),
            EnvironmentObservationV1: tuple(observation_fields()),
            DeliveryDecisionV1: tuple(decision_fields()),
            RecoveryDecisionV1: tuple(recovery_fields()),
            DeliveryEvidenceV1: tuple(evidence_fields()),
        }
        for record_type, names in expected.items():
            with self.subTest(record=record_type.__name__):
                self.assertEqual(tuple(field.name for field in fields(record_type)), names)

    def test_signed_artifact_rejects_unbound_authority_resource(self):
        with self.assertRaisesRegex(ContractError, "authority_resource_digest"):
            SignedArtifactRefV1(**artifact_fields(authority_resource_digest="0" * 64))

    def test_signed_artifact_rejects_bad_version_identity_time_and_scope(self):
        cases = (
            ({"schema_version": 2}, "schema_version"),
            ({"repository_id": "contains space"}, "repository_id"),
            ({"merged_sha": "A" * 40}, "merged_sha"),
            ({"artifact_digest": "not-a-digest"}, "artifact_digest"),
            ({"authority_verified_at": "2026-09-02T09:00:00+00:00"}, "authority_verified_at"),
            ({"authority_scope": "deploy_production"}, "authority_scope"),
        )
        for update, error in cases:
            with self.subTest(update=update), self.assertRaisesRegex(ContractError, error):
                SignedArtifactRefV1(**artifact_fields(**update))

    def test_exposure_plan_is_bounded_ordered_and_digest_bound(self):
        valid = ExposurePlanV1(**plan_fields())
        self.assertEqual(valid.canary_basis_points, (100, 500, 1000))
        cases = (
            ({"environment_order": ("preview", "bounded_canary", "staging", "production")}, "environment_order"),
            ({"preview_basis_points": (5000, 1000)}, "preview_basis_points"),
            ({"canary_basis_points": (100, 100)}, "canary_basis_points"),
            ({"canary_basis_points": tuple(range(1, 18))}, "canary_basis_points"),
            ({"canary_basis_points": (10000,)}, "canary_basis_points"),
            ({"max_observation_age_seconds": 3601}, "max_observation_age_seconds"),
            ({"required_metric_families": ("health",)}, "required_metric_families"),
            ({"security_critical_max": 1}, "security_critical_max"),
            ({"allowed_recovery_actions": ("halt", "deploy")}, "allowed_recovery_actions"),
            ({"plan_digest": "0" * 64}, "plan_digest"),
        )
        for update, error in cases:
            with self.subTest(update=update), self.assertRaisesRegex(ContractError, error):
                ExposurePlanV1(**plan_fields(**update))

    def test_promotion_binds_repository_artifacts_authority_and_complete_digest(self):
        promotion = DeliveryPromotionV1(**promotion_fields())
        self.assertNotEqual(
            promotion.artifact.artifact_digest,
            promotion.previous_signed_artifact.artifact_digest,
        )
        cases = (
            ({"repository_id": "other/repository"}, "repository_id"),
            ({"previous_signed_artifact": promotion.artifact}, "previous_signed_artifact"),
            ({"authority_scope": "signed_artifact_use"}, "authority_scope"),
            ({"authority_resource_digest": "0" * 64}, "authority_resource_digest"),
            ({"promotion_digest": "0" * 64}, "promotion_digest"),
            ({"expires_at": "2026-09-02T09:14:59Z"}, "expires_at"),
        )
        for update, error in cases:
            with self.subTest(update=update), self.assertRaisesRegex(ContractError, error):
                DeliveryPromotionV1(**promotion_fields(**update))

    def test_observation_rejects_bad_window_ranges_and_digest(self):
        self.assertEqual(EnvironmentObservationV1(**observation_fields()).sample_count, 500)
        cases = (
            ({"environment": "production-wide"}, "environment"),
            ({"exposure_basis_points": 10001}, "exposure_basis_points"),
            ({"window_started_at": "2026-09-02T09:21:00Z"}, "window_started_at"),
            ({"health_basis_points": -1}, "health_basis_points"),
            ({"latency_p95_ms": 0}, "latency_p95_ms"),
            ({"security_critical_count": -1}, "security_critical_count"),
            ({"sample_count": 0}, "sample_count"),
            ({"observation_digest": "0" * 64}, "observation_digest"),
        )
        for update, error in cases:
            with self.subTest(update=update), self.assertRaisesRegex(ContractError, error):
                EnvironmentObservationV1(**observation_fields(**update))

    def test_decision_has_closed_outcome_reasons_and_human_production_boundary(self):
        self.assertEqual(DeliveryDecisionV1(**decision_fields()).outcome, "advance")
        cases = (
            ({"outcome": "deploy"}, "outcome"),
            ({"reason_codes": ("thresholds_passed", "thresholds_passed")}, "reason_codes"),
            ({"reason_codes": ("free form",)}, "reason_codes"),
            ({"reason_codes": (None,)}, "reason_codes"),
            ({"outcome": "deny", "next_environment": "staging", "next_exposure_basis_points": 10000}, "next_environment"),
            ({"environment": "production", "outcome": "advance"}, "production"),
            ({"decision_digest": "0" * 64}, "decision_digest"),
        )
        for update, error in cases:
            with self.subTest(update=update), self.assertRaisesRegex(ContractError, error):
                DeliveryDecisionV1(**decision_fields(**update))

    def test_recovery_action_shapes_can_only_narrow(self):
        self.assertEqual(RecoveryDecisionV1(**recovery_fields()).action, "halt")
        valid_decrease = recovery_fields(
            action="decrease_exposure",
            target_exposure_basis_points=5000,
            reason_codes=("recovery_decrease",),
        )
        valid_decrease["recovery_digest"] = _digest(
            {key: value for key, value in valid_decrease.items() if key != "recovery_digest"}
        )
        self.assertEqual(
            RecoveryDecisionV1(**valid_decrease).target_exposure_basis_points, 5000
        )
        cases = (
            ({"action": "advance"}, "action"),
            ({"action": "halt", "target_exposure_basis_points": 1}, "target_exposure_basis_points"),
            ({"action": "decrease_exposure", "target_exposure_basis_points": 10000}, "target_exposure_basis_points"),
            ({"action": "restore_previous", "restore_artifact_digest": None}, "restore_artifact_digest"),
            ({"recovery_digest": "0" * 64}, "recovery_digest"),
        )
        for update, error in cases:
            with self.subTest(update=update), self.assertRaisesRegex(ContractError, error):
                RecoveryDecisionV1(**recovery_fields(**update))

    def test_evidence_is_bounded_digest_chained_and_dry_run_only(self):
        self.assertEqual(DeliveryEvidenceV1(**evidence_fields()).sequence, 1)
        second = evidence_fields(
            evidence_id="evidence/preview-002",
            sequence=2,
            previous_evidence_digest=HEX["previous_evidence"],
        )
        second["evidence_digest"] = _digest(
            {key: value for key, value in second.items() if key != "evidence_digest"}
        )
        self.assertEqual(DeliveryEvidenceV1(**second).sequence, 2)
        cases = (
            ({"sequence": 0}, "sequence"),
            ({"sequence": 129}, "sequence"),
            ({"sequence": 1, "previous_evidence_digest": HEX["previous_evidence"]}, "previous_evidence_digest"),
            ({"sequence": 2, "previous_evidence_digest": None}, "previous_evidence_digest"),
            ({"dry_run_effect": "deployed"}, "dry_run_effect"),
            ({"evidence_digest": "0" * 64}, "evidence_digest"),
        )
        for update, error in cases:
            with self.subTest(update=update), self.assertRaisesRegex(ContractError, error):
                DeliveryEvidenceV1(**evidence_fields(**update))


if __name__ == "__main__":
    unittest.main()
