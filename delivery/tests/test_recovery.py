import unittest

from delivery.tests.synthetic_fixtures import (
    SYNTHETIC_DECISION_TIME,
    synthetic_artifact,
    synthetic_denied_decision,
    synthetic_plan,
    synthetic_promotion,
)

from adaptive_delivery.recovery import RecoverySelectionError, choose_recovery


class RecoveryTests(unittest.TestCase):
    def test_halt_is_the_least_authority_plan_action(self):
        promotion = synthetic_promotion()
        failed = synthetic_denied_decision(promotion)
        recovery = choose_recovery(promotion, failed, SYNTHETIC_DECISION_TIME)
        self.assertEqual(recovery.action, "halt")
        self.assertIsNone(recovery.target_exposure_basis_points)
        self.assertIsNone(recovery.restore_artifact_digest)
        self.assertEqual(
            recovery.reason_codes,
            ("health_below_minimum", "recovery_halt"),
        )

    def test_decrease_selects_only_the_immediately_earlier_same_stage_step(self):
        plan = synthetic_plan(allowed_recovery_actions=("decrease_exposure",))
        promotion = synthetic_promotion(plan=plan)
        failed = synthetic_denied_decision(
            promotion,
            environment="bounded_canary",
            exposure_basis_points=500,
        )
        recovery = choose_recovery(promotion, failed, SYNTHETIC_DECISION_TIME)
        self.assertEqual(recovery.action, "decrease_exposure")
        self.assertEqual(recovery.environment, "bounded_canary")
        self.assertEqual(recovery.current_exposure_basis_points, 500)
        self.assertEqual(recovery.target_exposure_basis_points, 100)
        self.assertIsNone(recovery.restore_artifact_digest)

    def test_decrease_cannot_increase_reverse_stage_or_invent_a_step(self):
        plan = synthetic_plan(allowed_recovery_actions=("decrease_exposure",))
        promotion = synthetic_promotion(plan=plan)
        cases = (
            synthetic_denied_decision(
                promotion,
                environment="bounded_canary",
                exposure_basis_points=100,
            ),
            synthetic_denied_decision(
                promotion,
                environment="bounded_canary",
                exposure_basis_points=750,
            ),
            synthetic_denied_decision(
                promotion,
                environment="production",
                exposure_basis_points=10000,
                outcome="needs_human",
                reason_codes=("production_requires_human",),
            ),
        )
        for failed in cases:
            with self.subTest(
                environment=failed.environment,
                exposure=failed.exposure_basis_points,
            ), self.assertRaises(RecoverySelectionError):
                choose_recovery(promotion, failed, SYNTHETIC_DECISION_TIME)

    def test_restore_names_only_the_exact_bound_previous_artifact(self):
        plan = synthetic_plan(allowed_recovery_actions=("restore_previous",))
        promotion = synthetic_promotion(plan=plan)
        failed = synthetic_denied_decision(promotion)
        recovery = choose_recovery(promotion, failed, SYNTHETIC_DECISION_TIME)
        self.assertEqual(recovery.action, "restore_previous")
        self.assertEqual(
            recovery.restore_artifact_digest,
            promotion.previous_signed_artifact.artifact_digest,
        )
        self.assertNotEqual(
            recovery.restore_artifact_digest,
            promotion.artifact.artifact_digest,
        )

    def test_selector_rejects_non_denial_and_every_changed_binding(self):
        promotion = synthetic_promotion()
        cases = (
            synthetic_denied_decision(
                promotion,
                outcome="needs_human",
                reason_codes=("production_requires_human",),
                environment="bounded_canary",
                exposure_basis_points=1000,
            ),
            synthetic_denied_decision(promotion, promotion_digest="0" * 64),
            synthetic_denied_decision(promotion, artifact_digest="2" * 64),
            synthetic_denied_decision(promotion, exposure_basis_points=750),
        )
        for failed in cases:
            with self.subTest(
                decision=failed.decision_digest
            ), self.assertRaises(RecoverySelectionError):
                choose_recovery(promotion, failed, SYNTHETIC_DECISION_TIME)

    def test_expired_promotion_or_current_artifact_cannot_authorize_recovery(self):
        expired_current = synthetic_artifact(
            authority_expires_at="2026-09-02T09:21:30Z"
        )
        artifact_expired = synthetic_promotion(artifact=expired_current)
        cases = (
            (synthetic_promotion(), "2026-09-02T11:00:00Z"),
            (artifact_expired, SYNTHETIC_DECISION_TIME),
        )
        for promotion, decision_time in cases:
            with self.subTest(decision_time=decision_time):
                failed = synthetic_denied_decision(promotion)
                with self.assertRaisesRegex(RecoverySelectionError, "validity"):
                    choose_recovery(promotion, failed, decision_time)

    def test_expired_previous_artifact_cannot_be_selected_for_restore(self):
        expired_previous = synthetic_artifact(
            previous=True,
            authority_expires_at="2026-09-02T09:21:30Z",
        )
        plan = synthetic_plan(allowed_recovery_actions=("restore_previous",))
        promotion = synthetic_promotion(
            previous_artifact=expired_previous,
            plan=plan,
        )
        failed = synthetic_denied_decision(promotion)
        with self.assertRaisesRegex(RecoverySelectionError, "previous artifact"):
            choose_recovery(promotion, failed, SYNTHETIC_DECISION_TIME)

    def test_decision_time_cannot_precede_the_failed_evaluation(self):
        promotion = synthetic_promotion()
        failed = synthetic_denied_decision(promotion)
        with self.assertRaisesRegex(RecoverySelectionError, "decision_time"):
            choose_recovery(
                promotion,
                failed,
                "2026-09-02T09:20:59Z",
            )

    def test_same_inputs_produce_the_same_recovery_identity(self):
        promotion = synthetic_promotion()
        failed = synthetic_denied_decision(promotion)
        first = choose_recovery(promotion, failed, SYNTHETIC_DECISION_TIME)
        second = choose_recovery(promotion, failed, SYNTHETIC_DECISION_TIME)
        self.assertEqual(first.recovery_id, second.recovery_id)
        self.assertEqual(first.recovery_digest, second.recovery_digest)


if __name__ == "__main__":
    unittest.main()
