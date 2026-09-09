import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace

from delivery.tests.synthetic_fixtures import (
    SYNTHETIC_EVALUATION_TIME,
    synthetic_domain_digest,
    synthetic_m8_evidence,
    synthetic_observation,
    synthetic_promotion,
)

from adaptive_delivery.contracts import ContractError
from adaptive_delivery.evaluator import evaluate_delivery
from adaptive_delivery.m8_boundary import (
    M8AutonomyProfileV1,
    M8AutonomyTupleV1,
    M8BoundaryError,
    M8CohortEvidenceV1,
    M8DeliveryHandoffV1,
    M8PromotionRecommendationV1,
)
from adaptive_factory.autonomy import (
    AutonomyProfileV1,
    AutonomyTupleV1,
    CohortEvidenceV1,
    PromotionRecommendationV1,
)


def rebuilt_handoff(source, *, cohort=None, profile=None, recommendation=None):
    values = {
        "schema_version": 1,
        "producer_commit_sha": source.producer_commit_sha,
        "cohort": cohort or source.cohort,
        "profile": profile or source.profile,
        "recommendation": recommendation or source.recommendation,
    }
    body = {
        "schema_version": values["schema_version"],
        "producer_commit_sha": values["producer_commit_sha"],
        "cohort": values["cohort"].to_dict(),
        "profile": values["profile"].to_dict(),
        "recommendation": values["recommendation"].to_dict(),
    }
    return M8DeliveryHandoffV1(
        **values,
        handoff_digest=synthetic_domain_digest(
            "adaptive-delivery.m8-delivery-handoff/v1", body
        ),
    )


class M8BoundaryTests(unittest.TestCase):
    def test_bridge_exports_the_actual_m8_producer_types(self):
        self.assertIs(M8AutonomyTupleV1, AutonomyTupleV1)
        self.assertIs(M8CohortEvidenceV1, CohortEvidenceV1)
        self.assertIs(M8AutonomyProfileV1, AutonomyProfileV1)
        self.assertIs(M8PromotionRecommendationV1, PromotionRecommendationV1)

    def test_exact_material_tuple_and_domain_digest_chain_are_present(self):
        handoff = synthetic_m8_evidence()
        tuple_value = handoff.cohort.autonomy_tuple

        self.assertEqual(tuple_value.repository_id, "synthetic/repository")
        self.assertEqual(tuple_value.task_class, "low_risk_text_only")
        for field in (
            "m7_change_class",
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
            self.assertTrue(getattr(tuple_value, field))
        self.assertEqual(handoff.profile.tuple_digest, tuple_value.digest)
        self.assertEqual(handoff.recommendation.tuple_digest, tuple_value.digest)
        self.assertEqual(handoff.profile.cohort_digest, handoff.cohort.digest)
        self.assertEqual(handoff.recommendation.cohort_digest, handoff.cohort.digest)
        self.assertEqual(handoff.profile.digest, synthetic_domain_digest(
            "adaptive-factory.m8-autonomy-profile/v1", handoff.profile.to_dict()
        ))

    def test_adapter_is_immutable_source_only_and_never_durable_authority(self):
        handoff = synthetic_m8_evidence()
        self.assertEqual(
            handoff.SOURCE_STATUS, "blocked_pending_durable_m8_lookup"
        )
        self.assertFalse(handoff.EXTERNAL_ACTION_AUTHORIZED)
        self.assertFalse(handoff.durable_acceptance_available)
        self.assertFalse(handoff.durable_currentness_available)
        with self.assertRaises(FrozenInstanceError):
            handoff.profile.current_level = "L0"

    def test_provider_mapping_validator_and_provider_each_rotate_exact_chain(self):
        baseline = synthetic_m8_evidence()
        cases = (
            {"agent_digest": "c" * 64},
            {"validator_digest": "d" * 64},
            {"provider_digest": "e" * 64},
        )
        for update in cases:
            with self.subTest(field=tuple(update)):
                changed = synthetic_m8_evidence(tuple_updates=update)
                self.assertNotEqual(
                    baseline.cohort.autonomy_tuple.digest,
                    changed.cohort.autonomy_tuple.digest,
                )
                self.assertNotEqual(baseline.cohort.digest, changed.cohort.digest)
                self.assertNotEqual(baseline.profile.digest, changed.profile.digest)
                self.assertNotEqual(baseline.handoff_digest, changed.handoff_digest)

    def test_cohort_body_cannot_swap_validator_without_rebinding_tasks(self):
        handoff = synthetic_m8_evidence()
        body = handoff.cohort.to_dict()
        body["autonomy_tuple"]["validator_digest"] = "f" * 64

        with self.assertRaisesRegex(M8BoundaryError, "tuple_mismatch"):
            M8CohortEvidenceV1.from_dict(body)

    def test_provider_mapping_cannot_diverge_from_tuple_or_m7_key(self):
        body = synthetic_m8_evidence().cohort.to_dict()
        body["m7_handoff"]["provider_mapping"]["provider_digest"] = "0" * 64

        with self.assertRaisesRegex(M8BoundaryError, "provider_mapping_digest"):
            M8CohortEvidenceV1.from_dict(body)

    def test_cohort_wire_rejects_pathological_nested_producer_body(self):
        body = synthetic_m8_evidence().to_dict()
        nested = {}
        cursor = nested
        for index in range(70):
            child = {f"n{index}": {}}
            cursor.update(child)
            cursor = child[f"n{index}"]
        body["cohort"]["m7_handoff"]["evaluation"] = nested

        with self.assertRaisesRegex(M8BoundaryError, "depth"):
            M8DeliveryHandoffV1.from_dict(body)

    def test_task_observed_at_tuple_expiry_matches_exact_m8_rejection(self):
        body = synthetic_m8_evidence().cohort.to_dict()
        expiry = body["window_ended_at"]
        body["autonomy_tuple"]["expires_at"] = expiry
        tuple_digest = synthetic_domain_digest(
            "adaptive-factory.m8-autonomy-tuple/v1", body["autonomy_tuple"]
        )
        for task in body["tasks"]:
            task["tuple_digest"] = tuple_digest
        body["tasks"][-1]["observed_at"] = expiry

        with self.assertRaisesRegex(M8BoundaryError, "task_at_or_after_tuple_expiry"):
            M8CohortEvidenceV1.from_dict(body)

    def test_fractional_m8_timestamps_normalize_to_producer_digest_bytes(self):
        source = synthetic_m8_evidence()
        raw_cohort = source.cohort.to_dict()
        canonical_cohort = deepcopy(raw_cohort)
        raw_cohort["autonomy_tuple"]["expires_at"] = "2026-09-02T11:15:00.5Z"
        canonical_cohort["autonomy_tuple"]["expires_at"] = (
            "2026-09-02T11:15:00.500000Z"
        )
        tuple_digest = synthetic_domain_digest(
            "adaptive-factory.m8-autonomy-tuple/v1",
            canonical_cohort["autonomy_tuple"],
        )
        for raw_task, canonical_task in zip(
            raw_cohort["tasks"], canonical_cohort["tasks"], strict=True
        ):
            raw_task["tuple_digest"] = tuple_digest
            canonical_task["tuple_digest"] = tuple_digest
            raw_task["observed_at"] = "2026-09-02T09:05:00.2Z"
            canonical_task["observed_at"] = "2026-09-02T09:05:00.200000Z"
        for field, raw, canonical in (
            ("window_started_at", "2026-09-02T09:00:00.1Z", "2026-09-02T09:00:00.100000Z"),
            ("window_ended_at", "2026-09-02T09:10:00.3Z", "2026-09-02T09:10:00.300000Z"),
        ):
            raw_cohort[field] = raw
            canonical_cohort[field] = canonical

        cohort = M8CohortEvidenceV1.from_dict(raw_cohort)

        self.assertEqual(cohort.to_dict(), canonical_cohort)
        self.assertEqual(
            cohort.digest,
            synthetic_domain_digest(
                "adaptive-factory.m8-cohort-evidence/v1", canonical_cohort
            ),
        )

        raw_profile = source.profile.to_dict()
        raw_profile.update(
            tuple_digest=tuple_digest,
            cohort_digest=cohort.digest,
            expires_at="2026-09-02T11:15:00.5Z",
        )
        profile = M8AutonomyProfileV1.from_dict(raw_profile)
        self.assertEqual(
            profile.to_dict()["expires_at"], "2026-09-02T11:15:00.500000Z"
        )

        raw_recommendation = source.recommendation.to_dict()
        raw_recommendation.update(
            tuple_digest=tuple_digest,
            cohort_digest=cohort.digest,
            evaluated_at="2026-09-02T09:14:00.4Z",
            expires_at="2026-09-02T11:15:00.5Z",
        )
        recommendation = M8PromotionRecommendationV1.from_dict(raw_recommendation)
        self.assertEqual(
            recommendation.to_dict()["evaluated_at"], "2026-09-02T09:14:00.400000Z"
        )
        self.assertEqual(
            recommendation.to_dict()["expires_at"], "2026-09-02T11:15:00.500000Z"
        )

    def test_profile_cohort_and_recommendation_mismatch_are_rejected(self):
        handoff = synthetic_m8_evidence()
        bad_profile = replace(handoff.profile, tuple_digest="0" * 64)
        with self.assertRaisesRegex(M8BoundaryError, "tuple_digest"):
            rebuilt_handoff(handoff, profile=bad_profile)

        bad_profile = replace(handoff.profile, cohort_digest="1" * 64)
        with self.assertRaisesRegex(M8BoundaryError, "cohort_digest"):
            rebuilt_handoff(handoff, profile=bad_profile)

        bad_recommendation = replace(
            handoff.recommendation,
            current_level="L1",
            recommended_level="L2",
            reason_code="qualified",
        )
        with self.assertRaisesRegex(M8BoundaryError, "current_level"):
            rebuilt_handoff(handoff, recommendation=bad_recommendation)

    def test_caller_cannot_forge_profile_aggregate_and_rehash_the_handoff(self):
        handoff = synthetic_m8_evidence()
        forged = replace(
            handoff.profile,
            accepted_task_count=30,
            audit_sample_count=29,
            audit_accepted_count=29,
            minimum_quality_score_millionths=1_000_000,
            total_security_failures=0,
        )

        with self.assertRaisesRegex(M8BoundaryError, "profile_aggregate"):
            rebuilt_handoff(handoff, profile=forged)

    def test_promotion_rejects_wrong_repo_policy_holdout_or_runner_binding(self):
        handoff = synthetic_m8_evidence()
        cases = (
            {"repository_id": "other/repository"},
            {"policy_digest": "0" * 64},
            {"holdout_digest": "1" * 64},
            {"runner_image_digest": "2" * 64},
        )
        for update in cases:
            with self.subTest(field=tuple(update)), self.assertRaisesRegex(
                ContractError, "m8_evidence|repository_id"
            ):
                synthetic_promotion(m8_evidence=handoff, **update)

    def test_blocked_recommendation_halted_or_demoted_profile_cannot_advance(self):
        cases = (
            (
                {
                    "current_level": "L0",
                },
                {
                    "current_level": "L0",
                    "recommended_level": "L0",
                    "reason_code": "m7_bundle_blocked",
                },
                {"m8_recommendation_ineligible"},
                None,
            ),
            (
                {"current_level": "L1"},
                {
                    "current_level": "L1",
                    "recommended_level": "L1",
                    "reason_code": "cohort_replay",
                },
                {"m8_recommendation_ineligible"},
                None,
            ),
            (
                {"current_level": "L0", "halted": True},
                {
                    "current_level": "L0",
                    "recommended_level": "L0",
                    "reason_code": "halted_profile",
                },
                {"m8_profile_ineligible", "m8_recommendation_ineligible"},
                None,
            ),
            (
                {
                    "current_level": "L0",
                    "halted": True,
                    "total_demotion_triggers": 1,
                },
                {
                    "current_level": "L0",
                    "recommended_level": "L0",
                    "reason_code": "halted_profile",
                },
                {"m8_profile_ineligible", "m8_recommendation_ineligible"},
                {"demotion_trigger_count": 1},
            ),
        )
        for profile_updates, recommendation_updates, expected, task_updates in cases:
            with self.subTest(profile=profile_updates):
                handoff = synthetic_m8_evidence(
                    task_updates=task_updates,
                    profile_updates=profile_updates,
                    recommendation_updates=recommendation_updates,
                )
                promotion = synthetic_promotion(m8_evidence=handoff)
                decision = evaluate_delivery(
                    promotion,
                    synthetic_observation(promotion),
                    SYNTHETIC_EVALUATION_TIME,
                )
                self.assertEqual(decision.outcome, "deny")
                self.assertTrue(expected.issubset(decision.reason_codes))

    def test_current_l0_or_l1_qualified_profile_stays_within_l2_ceiling(self):
        cases = (("L0", "L1"), ("L1", "L2"))
        for current, recommended in cases:
            with self.subTest(current=current):
                handoff = synthetic_m8_evidence(
                    profile_updates={"current_level": current},
                    recommendation_updates={
                        "current_level": current,
                        "recommended_level": recommended,
                        "reason_code": "qualified",
                    },
                )
                promotion = synthetic_promotion(m8_evidence=handoff)
                decision = evaluate_delivery(
                    promotion,
                    synthetic_observation(promotion),
                    SYNTHETIC_EVALUATION_TIME,
                )
                self.assertEqual(decision.outcome, "advance")
                self.assertFalse(promotion.m8_evidence.durable_currentness_available)

    def test_expired_or_not_yet_current_m8_evidence_cannot_advance(self):
        expired = synthetic_m8_evidence(
            tuple_updates={"expires_at": "2026-09-02T09:20:00Z"}
        )
        future = synthetic_m8_evidence(
            recommendation_updates={"evaluated_at": "2026-09-02T09:22:00Z"}
        )
        cases = (
            (expired, "m8_evidence_expired"),
            (future, "m8_evidence_not_current"),
        )
        for handoff, reason in cases:
            with self.subTest(reason=reason):
                promotion = synthetic_promotion(m8_evidence=handoff)
                decision = evaluate_delivery(
                    promotion,
                    synthetic_observation(promotion),
                    SYNTHETIC_EVALUATION_TIME,
                )
                self.assertEqual(decision.outcome, "deny")
                self.assertIn(reason, decision.reason_codes)

    def test_current_provisional_m8_blocked_bundles_cannot_advance(self):
        source = synthetic_m8_evidence()
        recommendation = replace(
            source.recommendation,
            recommended_level=source.recommendation.current_level,
            reason_code="m7_bundle_blocked",
        )
        handoff = rebuilt_handoff(
            source,
            recommendation=recommendation,
        )
        promotion = synthetic_promotion(m8_evidence=handoff)

        decision = evaluate_delivery(
            promotion,
            synthetic_observation(promotion),
            SYNTHETIC_EVALUATION_TIME,
        )

        self.assertEqual(decision.outcome, "deny")
        self.assertIn("m8_recommendation_ineligible", decision.reason_codes)

    def test_valid_typed_evidence_only_advances_source_conformance(self):
        promotion = synthetic_promotion()
        decision = evaluate_delivery(
            promotion,
            synthetic_observation(promotion),
            SYNTHETIC_EVALUATION_TIME,
        )
        self.assertEqual(decision.outcome, "advance")
        self.assertFalse(promotion.m8_evidence.durable_currentness_available)
        self.assertEqual(
            promotion.m8_evidence.SOURCE_STATUS,
            "blocked_pending_durable_m8_lookup",
        )


if __name__ == "__main__":
    unittest.main()
