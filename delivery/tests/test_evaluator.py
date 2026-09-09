import unittest
from collections.abc import Sequence

from delivery.tests.synthetic_fixtures import (
    SYNTHETIC_EVALUATION_TIME,
    synthetic_artifact,
    synthetic_m8_evidence,
    synthetic_observation,
    synthetic_plan,
    synthetic_promotion,
)

from adaptive_delivery.contracts import ContractError
from adaptive_delivery.evaluator import evaluate_delivery


class EvaluatorTests(unittest.TestCase):
    def evaluate(self, promotion, observations, environment, exposure, at=SYNTHETIC_EVALUATION_TIME):
        return evaluate_delivery(
            promotion,
            observations,
            at,
            environment=environment,
            exposure_basis_points=exposure,
        )

    def test_opaque_m8_digest_pair_cannot_authorize_a_delivery_advance(self):
        with self.assertRaisesRegex(TypeError, "m8_profile_digest"):
            synthetic_promotion(
                m8_profile_digest="0" * 64,
                m8_cohort_digest="1" * 64,
            )

    def test_passing_stages_advance_only_one_pre_authorized_step(self):
        promotion = synthetic_promotion()
        cases = (
            ("preview", 10000, "staging", 10000),
            ("staging", 10000, "bounded_canary", 100),
            ("bounded_canary", 100, "bounded_canary", 500),
            ("bounded_canary", 500, "bounded_canary", 1000),
        )
        for environment, exposure, next_environment, next_exposure in cases:
            with self.subTest(environment=environment, exposure=exposure):
                observation = synthetic_observation(
                    promotion,
                    environment=environment,
                    exposure_basis_points=exposure,
                )
                decision = self.evaluate(
                    promotion, (observation,), environment, exposure
                )
                self.assertEqual(decision.outcome, "advance")
                self.assertEqual(decision.reason_codes, ("thresholds_passed",))
                self.assertEqual(decision.next_environment, next_environment)
                self.assertEqual(decision.next_exposure_basis_points, next_exposure)

    def test_last_canary_pass_and_production_stop_at_human_boundary(self):
        promotion = synthetic_promotion()
        for environment, exposure in (("bounded_canary", 1000), ("production", 10000)):
            with self.subTest(environment=environment):
                observation = synthetic_observation(
                    promotion,
                    environment=environment,
                    exposure_basis_points=exposure,
                )
                decision = self.evaluate(
                    promotion, (observation,), environment, exposure
                )
                self.assertEqual(decision.outcome, "needs_human")
                self.assertIn("production_requires_human", decision.reason_codes)
                self.assertIsNone(decision.next_environment)
                self.assertIsNone(decision.next_exposure_basis_points)

    def test_missing_current_snapshot_denies_as_incomplete(self):
        promotion = synthetic_promotion()
        decision = self.evaluate(promotion, (), "preview", 10000)
        self.assertEqual(decision.outcome, "deny")
        self.assertEqual(decision.reason_codes, ("observation_incomplete",))

    def test_duplicate_replay_and_contradiction_are_all_reported(self):
        promotion = synthetic_promotion()
        first = synthetic_observation(promotion)
        replay = self.evaluate(promotion, (first, first), "preview", 10000)
        self.assertEqual(
            replay.reason_codes,
            ("observation_duplicate", "observation_replay"),
        )

        conflicting = synthetic_observation(
            promotion,
            observation_id="synthetic/observation-conflict",
            health_basis_points=9800,
            source_snapshot_digest="0" * 64,
        )
        contradiction = self.evaluate(
            promotion, (first, conflicting), "preview", 10000
        )
        self.assertEqual(
            contradiction.reason_codes,
            (
                "health_below_minimum",
                "observation_contradictory",
                "observation_duplicate",
            ),
        )

    def test_binding_mismatches_are_collected_without_short_circuit(self):
        promotion = synthetic_promotion()
        observation = synthetic_observation(
            promotion,
            promotion_digest="0" * 64,
            artifact_digest="2" * 64,
            environment_set_digest="3" * 64,
            environment="staging",
            exposure_basis_points=5000,
            policy_digest="4" * 64,
        )
        decision = self.evaluate(promotion, (observation,), "preview", 10000)
        self.assertEqual(
            decision.reason_codes,
            (
                "artifact_mismatch",
                "environment_mismatch",
                "environment_set_mismatch",
                "exposure_mismatch",
                "policy_mismatch",
                "promotion_mismatch",
            ),
        )

    def test_every_promotion_resource_mutation_rotates_the_exact_binding(self):
        promotion = synthetic_promotion()
        mutations = (
            {
                "m8_evidence": synthetic_m8_evidence(
                    profile_updates={"current_level": "L1"},
                    recommendation_updates={
                        "current_level": "L1",
                        "recommended_level": "L2",
                        "reason_code": "qualified",
                    },
                )
            },
            {
                "m8_evidence": synthetic_m8_evidence(
                    tuple_updates={"provider_digest": "0" * 64}
                )
            },
            {"holdout_digest": "2" * 64},
            {"runner_image_digest": "3" * 64},
            {"environment_set_digest": "4" * 64},
            {"artifact": synthetic_artifact(sbom_digest="5" * 64)},
            {"artifact": synthetic_artifact(provenance_digest="6" * 64)},
            {
                "artifact": synthetic_artifact(
                    supply_chain_manifest_digest="7" * 64
                )
            },
            {"artifact": synthetic_artifact(image_digest="8" * 64)},
        )
        for update in mutations:
            with self.subTest(update=tuple(update)):
                alternate = synthetic_promotion(**update)
                observation = synthetic_observation(alternate)
                decision = self.evaluate(
                    promotion, (observation,), "preview", 10000
                )
                self.assertIn("promotion_mismatch", decision.reason_codes)

    def test_time_freshness_and_window_failures_are_stable(self):
        promotion = synthetic_promotion()
        stale = synthetic_observation(promotion)
        stale_decision = self.evaluate(
            promotion, (stale,), "preview", 10000, "2026-09-02T09:30:00Z"
        )
        self.assertEqual(stale_decision.reason_codes, ("observation_stale",))

        bad_window = synthetic_observation(
            promotion,
            window_started_at="2026-09-02T09:19:00Z",
        )
        future = synthetic_observation(
            promotion,
            observation_id="synthetic/future-observation",
            captured_at="2026-09-02T09:22:00Z",
            window_started_at="2026-09-02T09:20:00Z",
            window_ended_at="2026-09-02T09:22:00Z",
            source_snapshot_digest="0" * 64,
        )
        decision = self.evaluate(
            promotion, (bad_window, future), "preview", 10000
        )
        self.assertIn("observation_time_invalid", decision.reason_codes)
        self.assertIn("observation_contradictory", decision.reason_codes)

    def test_fresh_capture_cannot_hide_an_old_observation_window(self):
        promotion = synthetic_promotion()
        observation = synthetic_observation(
            promotion,
            captured_at="2026-09-02T09:24:30Z",
            window_started_at="2026-09-02T09:16:00Z",
            window_ended_at="2026-09-02T09:18:00Z",
        )
        decision = self.evaluate(
            promotion,
            (observation,),
            "preview",
            10000,
            "2026-09-02T09:25:00Z",
        )
        self.assertEqual(decision.outcome, "deny")
        self.assertEqual(decision.reason_codes, ("observation_stale",))

    def test_authority_and_promotion_validity_are_checked_at_evaluation_time(self):
        promotion = synthetic_promotion()
        observation = synthetic_observation(promotion)
        early = self.evaluate(
            promotion,
            (observation,),
            "preview",
            10000,
            "2026-09-02T09:14:59Z",
        )
        self.assertEqual(
            early.reason_codes,
            ("authority_not_yet_valid", "observation_time_invalid"),
        )

        late = self.evaluate(
            promotion,
            (observation,),
            "preview",
            10000,
            "2026-09-02T11:30:00Z",
        )
        self.assertEqual(
            late.reason_codes,
            (
                "authority_expired",
                "observation_stale",
                "promotion_expired",
            ),
        )

    def test_all_threshold_boundaries_pass_and_one_unit_beyond_denies(self):
        promotion = synthetic_promotion()
        boundary = synthetic_observation(
            promotion,
            health_basis_points=9900,
            error_basis_points=100,
            latency_p95_ms=500,
            security_critical_count=0,
            business_basis_points=9500,
        )
        self.assertEqual(
            self.evaluate(promotion, (boundary,), "preview", 10000).outcome,
            "advance",
        )
        cases = (
            ({"health_basis_points": 9899}, "health_below_minimum"),
            ({"error_basis_points": 101}, "error_above_maximum"),
            ({"latency_p95_ms": 501}, "latency_above_maximum"),
            ({"security_critical_count": 1}, "security_critical"),
            ({"business_basis_points": 9499}, "business_below_minimum"),
        )
        for update, reason in cases:
            with self.subTest(reason=reason):
                observation = synthetic_observation(promotion, **update)
                decision = self.evaluate(
                    promotion, (observation,), "preview", 10000
                )
                self.assertEqual(decision.outcome, "deny")
                self.assertEqual(decision.reason_codes, (reason,))

    def test_unplanned_exposure_denies_without_advancing(self):
        promotion = synthetic_promotion()
        observation = synthetic_observation(
            promotion,
            environment="bounded_canary",
            exposure_basis_points=750,
        )
        decision = self.evaluate(
            promotion, (observation,), "bounded_canary", 750
        )
        self.assertEqual(decision.outcome, "deny")
        self.assertEqual(decision.reason_codes, ("exposure_mismatch",))

    def test_observation_input_order_cannot_change_reasons_or_digest(self):
        promotion = synthetic_promotion()
        first = synthetic_observation(promotion)
        second = synthetic_observation(
            promotion,
            observation_id="synthetic/second-observation",
            error_basis_points=101,
            source_snapshot_digest="0" * 64,
        )
        forward = self.evaluate(promotion, (first, second), "preview", 10000)
        reverse = self.evaluate(promotion, (second, first), "preview", 10000)
        self.assertEqual(forward.reason_codes, reverse.reason_codes)
        self.assertEqual(forward.observation_set_digest, reverse.observation_set_digest)
        self.assertEqual(forward.decision_digest, reverse.decision_digest)

    def test_single_observation_call_shape_remains_compatible_with_the_plan(self):
        promotion = synthetic_promotion(plan=synthetic_plan())
        observation = synthetic_observation(promotion)
        decision = evaluate_delivery(
            promotion, observation, SYNTHETIC_EVALUATION_TIME
        )
        self.assertEqual(decision.outcome, "advance")

    def test_oversized_observation_sequence_is_rejected_before_materialization(self):
        class OversizedObservations(Sequence):
            def __init__(self):
                self.read = False

            def __len__(self):
                return 129

            def __getitem__(self, index):
                self.read = True
                raise AssertionError(f"materialized item {index}")

        observations = OversizedObservations()
        with self.assertRaisesRegex(ContractError, "128"):
            self.evaluate(
                synthetic_promotion(), observations, "preview", 10000
            )
        self.assertFalse(observations.read)

    def test_observation_generator_is_rejected_without_consumption(self):
        consumed = []

        def observations():
            consumed.append(True)
            yield synthetic_observation(synthetic_promotion())

        with self.assertRaisesRegex(ContractError, "observation sequence"):
            self.evaluate(
                synthetic_promotion(), observations(), "preview", 10000
            )
        self.assertEqual(consumed, [])

    def test_observation_sequence_reads_only_its_declared_bounded_length(self):
        promotion = synthetic_promotion()
        observation = synthetic_observation(promotion)

        class LyingObservationSequence(Sequence):
            def __init__(self):
                self.read_indexes = []

            def __len__(self):
                return 1

            def __getitem__(self, index):
                self.read_indexes.append(index)
                if index >= 3:
                    raise AssertionError("unbounded sequence materialization")
                return observation

        observations = LyingObservationSequence()
        decision = self.evaluate(
            promotion, observations, "preview", 10000
        )
        self.assertEqual(decision.outcome, "advance")
        self.assertEqual(observations.read_indexes, [0])


if __name__ == "__main__":
    unittest.main()
