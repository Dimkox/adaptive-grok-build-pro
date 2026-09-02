"""Synthetic algorithm fixtures only; never factual M7 or M8 evidence."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import unittest

from adaptive_factory.autonomy import (
    AutonomyProfileV1,
    AutonomyTupleV1,
    CohortEvidenceV1,
    CohortTaskEvidenceV1,
    DemotionDecisionV1,
    PromotionRecommendationV1,
    demote_profile,
    evaluate_autonomy,
)
from adaptive_factory.contracts import ContractError


SYNTHETIC_ALGORITHM_FIXTURES_ONLY = True
NOW = datetime(2026, 9, 4, 0, 0, tzinfo=timezone.utc)
TUPLE_DIGEST = "421c8e27291f81ff447c1bbaab497c4b709098a30addbd103fb8ecc64045b112"


def valid_tuple_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "repository_id": "owner/repository",
        "task_class": "low_risk_text_only",
        "m4_product_sha": "4" * 40,
        "m5_product_sha": "5" * 40,
        "m6_product_sha": "6" * 40,
        "m7_product_sha": "7" * 40,
        "m7_exact_head_sha": "8" * 40,
        "agent_digest": "a" * 64,
        "provider_digest": "b" * 64,
        "model_digest": "c" * 64,
        "prompt_digest": "d" * 64,
        "policy_digest": "e" * 64,
        "runner_image_digest": "f" * 64,
        "holdout_digest": "0" * 64,
        "authority_observation_digest": "1" * 64,
        "authority_ceiling": "L2",
        "expires_at": "2026-09-07T18:00:00Z",
    }


def valid_task_payload(index: int = 0) -> dict[str, object]:
    return {
        "schema_version": 1,
        "tuple_digest": TUPLE_DIGEST,
        "task_id": f"task-{index:03d}",
        "run_id": f"run-{index:03d}",
        "exact_head_sha": f"{index + 10:040x}",
        "observed_at": "2026-09-02T06:00:00Z",
        "eligible": True,
        "human_accepted": True,
        "audit_sampled": index == 0,
        "audit_accepted": index == 0,
        "human_acceptance_receipt_digest": f"{index + 20:064x}",
        "attestation_receipt_digest": f"{index + 30:064x}",
        "quality_score_millionths": 990_000,
        "security_failure_count": 0,
        "authorization_failure_count": 0,
        "duplicate_dispatch_count": 0,
        "cost_usd_micros": 100_000,
        "latency_ms": 1_000,
        "demotion_trigger_count": 0,
    }


def valid_cohort_payload(task_count: int = 2) -> dict[str, object]:
    return {
        "schema_version": 1,
        "autonomy_tuple": valid_tuple_payload(),
        "tasks": [valid_task_payload(index) for index in range(task_count)],
        "factual_m7_restack_observed": True,
        "factual_m7_receipt_digest": "9" * 64,
        "window_started_at": "2026-09-02T00:00:00Z",
        "window_ended_at": "2026-09-03T00:00:00Z",
        "minimum_human_acceptances": 30,
        "minimum_audit_rate_millionths": 200_000,
        "minimum_quality_score_millionths": 950_000,
        "maximum_security_failures": 0,
        "maximum_authorization_failures": 0,
        "maximum_duplicate_dispatches": 0,
        "maximum_cost_usd_micros": 200_000,
        "maximum_latency_ms": 2_000,
        "maximum_demotion_triggers": 0,
    }


def valid_profile_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "tuple_digest": TUPLE_DIGEST,
        "cohort_digest": "2" * 64,
        "current_level": "L0",
        "accepted_task_count": 30,
        "audit_sample_count": 6,
        "audit_accepted_count": 6,
        "minimum_quality_score_millionths": 990_000,
        "total_security_failures": 0,
        "total_authorization_failures": 0,
        "total_duplicate_dispatches": 0,
        "maximum_cost_usd_micros": 100_000,
        "p95_latency_ms": 1_000,
        "total_demotion_triggers": 0,
        "expires_at": "2026-09-07T18:00:00Z",
        "halted": False,
    }


def valid_recommendation_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "tuple_digest": TUPLE_DIGEST,
        "cohort_digest": "2" * 64,
        "current_level": "L0",
        "recommended_level": "L1",
        "reason_code": "qualified",
        "evaluated_at": "2026-09-02T06:00:00Z",
        "expires_at": "2026-09-07T18:00:00Z",
        "separate_activation_required": True,
        "external_action_authorized": False,
    }


def valid_demotion_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "profile_digest": "3" * 64,
        "tuple_digest": TUPLE_DIGEST,
        "trigger": "security_failure",
        "prior_level": "L1",
        "resulting_level": "L0",
        "effective_at": "2026-09-02T06:00:00Z",
        "halt": True,
        "external_action_authorized": False,
    }


def qualifying_cohort_payload() -> dict[str, object]:
    """Synthetic exact-boundary cohort; never evidence of a human decision."""
    payload = valid_cohort_payload(task_count=30)
    tasks = payload["tasks"]
    assert isinstance(tasks, list)
    for index, task in enumerate(tasks):
        assert isinstance(task, dict)
        task["observed_at"] = (
            "2026-09-02T06:00:00Z" if index < 15 else "2026-09-03T06:00:00Z"
        )
        sampled = index in {0, 1, 2, 15, 16, 17}
        task["audit_sampled"] = sampled
        task["audit_accepted"] = sampled
    payload["window_ended_at"] = "2026-09-04T00:00:00Z"
    return payload


def cohort_with_tuple_payload(tuple_payload: dict[str, object]) -> dict[str, object]:
    payload = qualifying_cohort_payload()
    autonomy_tuple = AutonomyTupleV1.from_dict(tuple_payload)
    payload["autonomy_tuple"] = tuple_payload
    tasks = payload["tasks"]
    assert isinstance(tasks, list)
    for task in tasks:
        assert isinstance(task, dict)
        task["tuple_digest"] = autonomy_tuple.digest
    return payload


class AutonomyContractTests(unittest.TestCase):
    def test_synthetic_boundary_data_is_explicitly_not_factual_evidence(self):
        self.assertIs(SYNTHETIC_ALGORITHM_FIXTURES_ONLY, True)

    def test_tuple_is_closed_frozen_canonical_and_exactly_bound(self):
        autonomy_tuple = AutonomyTupleV1.from_dict(valid_tuple_payload())
        self.assertEqual(autonomy_tuple.to_dict(), valid_tuple_payload())
        self.assertEqual(autonomy_tuple.digest, TUPLE_DIGEST)
        self.assertEqual(AutonomyTupleV1.from_dict(autonomy_tuple.to_dict()), autonomy_tuple)
        with self.assertRaises(FrozenInstanceError):
            autonomy_tuple.task_class = "other"

    def test_all_six_v1_records_reject_unknown_missing_and_wrong_version(self):
        cases = (
            (AutonomyTupleV1, valid_tuple_payload()),
            (CohortTaskEvidenceV1, valid_task_payload()),
            (CohortEvidenceV1, valid_cohort_payload()),
            (AutonomyProfileV1, valid_profile_payload()),
            (PromotionRecommendationV1, valid_recommendation_payload()),
            (DemotionDecisionV1, valid_demotion_payload()),
        )
        for contract, original in cases:
            unknown = deepcopy(original)
            unknown["push"] = True
            missing = deepcopy(original)
            missing.pop(next(iter(missing)))
            version = deepcopy(original)
            version["schema_version"] = 2
            for mutation, code in (
                (unknown, "unknown_fields"),
                (missing, "missing_fields"),
                (version, "unsupported_version"),
            ):
                with self.subTest(contract=contract.__name__, code=code), self.assertRaisesRegex(
                    ContractError, code
                ):
                    contract.from_dict(mutation)

    def test_only_low_risk_text_and_l0_through_l2_are_representable(self):
        wrong_class = valid_tuple_payload()
        wrong_class["task_class"] = "code_change"
        wrong_ceiling = valid_tuple_payload()
        wrong_ceiling["authority_ceiling"] = "L3"
        wrong_profile = valid_profile_payload()
        wrong_profile["current_level"] = "L4"
        for parser, payload, code in (
            (AutonomyTupleV1.from_dict, wrong_class, "unsupported_task_class"),
            (AutonomyTupleV1.from_dict, wrong_ceiling, "unsupported_level"),
            (AutonomyProfileV1.from_dict, wrong_profile, "unsupported_level"),
        ):
            with self.subTest(code=code), self.assertRaisesRegex(ContractError, code):
                    parser(payload)


class AutonomyEvaluationTests(unittest.TestCase):
    """Synthetic boundary cases only; these never assert a factual cohort exists."""

    def test_exact_thresholds_recommend_one_level_and_compute_integer_metrics(self):
        payload = qualifying_cohort_payload()
        tasks = payload["tasks"]
        assert isinstance(tasks, list)
        for index, task in enumerate(tasks):
            assert isinstance(task, dict)
            task["quality_score_millionths"] = 950_000
            task["cost_usd_micros"] = 200_000
            task["latency_ms"] = index + 1
        payload["maximum_latency_ms"] = 30
        cohort = CohortEvidenceV1.from_dict(payload)

        profile, recommendation = evaluate_autonomy(cohort, None, NOW)

        self.assertEqual(
            {
                "current_level": profile.current_level,
                "accepted_task_count": profile.accepted_task_count,
                "audit_sample_count": profile.audit_sample_count,
                "audit_accepted_count": profile.audit_accepted_count,
                "minimum_quality_score_millionths": profile.minimum_quality_score_millionths,
                "total_security_failures": profile.total_security_failures,
                "total_authorization_failures": profile.total_authorization_failures,
                "total_duplicate_dispatches": profile.total_duplicate_dispatches,
                "maximum_cost_usd_micros": profile.maximum_cost_usd_micros,
                "p95_latency_ms": profile.p95_latency_ms,
                "total_demotion_triggers": profile.total_demotion_triggers,
                "halted": profile.halted,
            },
            {
                "current_level": "L0",
                "accepted_task_count": 30,
                "audit_sample_count": 6,
                "audit_accepted_count": 6,
                "minimum_quality_score_millionths": 950_000,
                "total_security_failures": 0,
                "total_authorization_failures": 0,
                "total_duplicate_dispatches": 0,
                "maximum_cost_usd_micros": 200_000,
                "p95_latency_ms": 29,
                "total_demotion_triggers": 0,
                "halted": False,
            },
        )
        self.assertEqual(profile.tuple_digest, TUPLE_DIGEST)
        self.assertEqual(profile.cohort_digest, cohort.digest)
        self.assertEqual(
            (
                recommendation.current_level,
                recommendation.recommended_level,
                recommendation.reason_code,
                recommendation.separate_activation_required,
                recommendation.external_action_authorized,
            ),
            ("L0", "L1", "qualified", True, False),
        )

    def test_each_closed_gate_holds_the_current_level_with_a_fixed_reason(self):
        cases = []

        factual = qualifying_cohort_payload()
        factual["factual_m7_restack_observed"] = False
        cases.append(("factual_m7_missing", factual))

        acceptances = qualifying_cohort_payload()
        acceptances["tasks"] = acceptances["tasks"][:-1]
        cases.append(("insufficient_acceptances", acceptances))

        ineligible = qualifying_cohort_payload()
        ineligible["tasks"][29]["eligible"] = False
        cases.append(("ineligible_task", ineligible))

        not_accepted = qualifying_cohort_payload()
        not_accepted["tasks"][29]["human_accepted"] = False
        cases.append(("human_acceptance_missing", not_accepted))

        audit_rate = qualifying_cohort_payload()
        audit_rate["tasks"][17]["audit_sampled"] = False
        audit_rate["tasks"][17]["audit_accepted"] = False
        cases.append(("audit_rate_insufficient", audit_rate))

        audit_day = qualifying_cohort_payload()
        for task in audit_day["tasks"]:
            if task["observed_at"] == "2026-09-03T06:00:00Z":
                task["audit_sampled"] = False
                task["audit_accepted"] = False
        for index in (3, 4, 5):
            audit_day["tasks"][index]["audit_sampled"] = True
            audit_day["tasks"][index]["audit_accepted"] = True
        cases.append(("audit_day_gap", audit_day))

        audit_rejected = qualifying_cohort_payload()
        audit_rejected["tasks"][0]["audit_accepted"] = False
        cases.append(("audit_rejected", audit_rejected))

        quality = qualifying_cohort_payload()
        quality["tasks"][29]["quality_score_millionths"] = 949_999
        cases.append(("quality_below_threshold", quality))

        security = qualifying_cohort_payload()
        security["tasks"][29]["security_failure_count"] = 1
        cases.append(("security_failure", security))

        authorization = qualifying_cohort_payload()
        authorization["tasks"][29]["authorization_failure_count"] = 1
        cases.append(("authorization_failure", authorization))

        duplicate = qualifying_cohort_payload()
        duplicate["tasks"][29]["duplicate_dispatch_count"] = 1
        cases.append(("duplicate_dispatch", duplicate))

        cost = qualifying_cohort_payload()
        cost["tasks"][29]["cost_usd_micros"] = 200_001
        cases.append(("cost_above_threshold", cost))

        latency = qualifying_cohort_payload()
        latency["tasks"][28]["latency_ms"] = 2_001
        latency["tasks"][29]["latency_ms"] = 2_001
        cases.append(("latency_above_threshold", latency))

        demotion = qualifying_cohort_payload()
        demotion["tasks"][29]["demotion_trigger_count"] = 1
        cases.append(("demotion_fact_present", demotion))

        for reason, payload in cases:
            with self.subTest(reason=reason):
                cohort = CohortEvidenceV1.from_dict(payload)
                _, recommendation = evaluate_autonomy(cohort, None, NOW)
                self.assertEqual(
                    (
                        recommendation.current_level,
                        recommendation.recommended_level,
                        recommendation.reason_code,
                    ),
                    ("L0", "L0", reason),
                )

    def test_profile_reuse_is_exact_gradual_replay_safe_and_l2_capped(self):
        first = CohortEvidenceV1.from_dict(qualifying_cohort_payload())
        l0_profile, _ = evaluate_autonomy(first, None, NOW)
        l1_payload = l0_profile.to_dict()
        l1_payload["current_level"] = "L1"
        l1_profile = AutonomyProfileV1.from_dict(l1_payload)

        _, replay = evaluate_autonomy(first, l1_profile, NOW)
        self.assertEqual((replay.recommended_level, replay.reason_code), ("L1", "cohort_replay"))

        second_payload = qualifying_cohort_payload()
        second_payload["tasks"][29]["attestation_receipt_digest"] = "a" * 64
        second = CohortEvidenceV1.from_dict(second_payload)
        l1_current, promote_l2 = evaluate_autonomy(second, l1_profile, NOW)
        self.assertEqual(l1_current.current_level, "L1")
        self.assertEqual((promote_l2.recommended_level, promote_l2.reason_code), ("L2", "qualified"))

        l2_payload = l1_current.to_dict()
        l2_payload["current_level"] = "L2"
        l2_profile = AutonomyProfileV1.from_dict(l2_payload)
        third_payload = qualifying_cohort_payload()
        third_payload["tasks"][29]["attestation_receipt_digest"] = "b" * 64
        third = CohortEvidenceV1.from_dict(third_payload)
        _, ceiling = evaluate_autonomy(third, l2_profile, NOW)
        self.assertEqual((ceiling.recommended_level, ceiling.reason_code), ("L2", "already_at_ceiling"))

    def test_tuple_expiry_halted_state_and_mutation_fail_closed(self):
        expired_tuple = valid_tuple_payload()
        expired_tuple["expires_at"] = "2026-09-04T00:00:00Z"
        expired = CohortEvidenceV1.from_dict(cohort_with_tuple_payload(expired_tuple))
        expired_profile, expired_recommendation = evaluate_autonomy(expired, None, NOW)
        self.assertEqual(expired_profile.current_level, "L0")
        self.assertEqual(
            (
                expired_recommendation.current_level,
                expired_recommendation.recommended_level,
                expired_recommendation.reason_code,
            ),
            ("L0", "L0", "tuple_expired"),
        )

        cohort = CohortEvidenceV1.from_dict(qualifying_cohort_payload())
        profile, _ = evaluate_autonomy(cohort, None, NOW)
        halted_payload = profile.to_dict()
        halted_payload["halted"] = True
        halted = AutonomyProfileV1.from_dict(halted_payload)
        _, halted_recommendation = evaluate_autonomy(cohort, halted, NOW)
        self.assertEqual(halted_recommendation.reason_code, "halted_profile")

        mutated_tuple = valid_tuple_payload()
        mutated_tuple["model_digest"] = "1" * 64
        mutated = CohortEvidenceV1.from_dict(cohort_with_tuple_payload(mutated_tuple))
        with self.assertRaisesRegex(ContractError, "tuple_mismatch"):
            evaluate_autonomy(mutated, profile, NOW)

    def test_evaluator_accepts_only_frozen_records_and_aware_time(self):
        cohort = CohortEvidenceV1.from_dict(qualifying_cohort_payload())
        with self.assertRaisesRegex(ContractError, "invalid_contract"):
            evaluate_autonomy(cohort.to_dict(), None, NOW)
        with self.assertRaisesRegex(ContractError, "invalid_time"):
            evaluate_autonomy(cohort, None, datetime(2026, 9, 2, 6, 0))

    def test_open_window_fails_closed(self):
        cohort = CohortEvidenceV1.from_dict(qualifying_cohort_payload())
        with self.assertRaisesRegex(ContractError, "cohort_window_open"):
            evaluate_autonomy(
                cohort,
                None,
                datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc),
            )

    def test_window_after_tuple_expiry_fails_closed(self):
        past_expiry_tuple = valid_tuple_payload()
        past_expiry_tuple["expires_at"] = "2026-09-03T12:00:00Z"
        with self.assertRaisesRegex(ContractError, "cohort_after_tuple_expiry"):
            CohortEvidenceV1.from_dict(cohort_with_tuple_payload(past_expiry_tuple))

    def test_task_at_tuple_expiry_fails_closed(self):
        task_at_expiry = qualifying_cohort_payload()
        expiring_tuple = valid_tuple_payload()
        expiring_tuple["expires_at"] = "2026-09-04T00:00:00Z"
        expiring = AutonomyTupleV1.from_dict(expiring_tuple)
        task_at_expiry["autonomy_tuple"] = expiring_tuple
        for task in task_at_expiry["tasks"]:
            task["tuple_digest"] = expiring.digest
        task_at_expiry["tasks"][29]["observed_at"] = "2026-09-04T00:00:00Z"
        with self.assertRaisesRegex(ContractError, "task_at_or_after_tuple_expiry"):
            CohortEvidenceV1.from_dict(task_at_expiry)


class AutonomyContractBoundaryTests(unittest.TestCase):
    def test_identifiers_times_metrics_and_receipts_are_bounded(self):
        cases = []
        long_id = valid_task_payload()
        long_id["task_id"] = "x" * 129
        cases.append((long_id, "invalid_identifier"))
        bad_time = valid_task_payload()
        bad_time["observed_at"] = "not-a-time"
        cases.append((bad_time, "invalid_time"))
        bad_receipt = valid_task_payload()
        bad_receipt["attestation_receipt_digest"] = "secret-value"
        cases.append((bad_receipt, "invalid_digest"))
        quality = valid_task_payload()
        quality["quality_score_millionths"] = 1_000_001
        cases.append((quality, "invalid_integer"))
        cost = valid_task_payload()
        cost["cost_usd_micros"] = 1_000_000_000_001
        cases.append((cost, "invalid_integer"))
        latency = valid_task_payload()
        latency["latency_ms"] = 604_800_001
        cases.append((latency, "invalid_integer"))
        for payload, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(ContractError, code):
                CohortTaskEvidenceV1.from_dict(payload)

    def test_cohort_is_ordered_distinct_single_tuple_and_deeply_frozen(self):
        cohort = CohortEvidenceV1.from_dict(valid_cohort_payload())
        self.assertEqual([task.task_id for task in cohort.tasks], ["task-000", "task-001"])
        with self.assertRaises(TypeError):
            cohort.tasks[0] = cohort.tasks[1]

        duplicate = valid_cohort_payload()
        duplicate["tasks"][1]["run_id"] = duplicate["tasks"][0]["run_id"]
        mixed = valid_cohort_payload()
        mixed["tasks"][1]["tuple_digest"] = "f" * 64
        unordered = valid_cohort_payload()
        unordered["tasks"].reverse()
        for payload, code in (
            (duplicate, "duplicate_identity"),
            (mixed, "tuple_mismatch"),
            (unordered, "invalid_order"),
        ):
            with self.subTest(code=code), self.assertRaisesRegex(ContractError, code):
                CohortEvidenceV1.from_dict(payload)

    def test_recommendation_and_demotion_can_never_authorize_external_action(self):
        recommendation = valid_recommendation_payload()
        recommendation["external_action_authorized"] = True
        demotion = valid_demotion_payload()
        demotion["external_action_authorized"] = True
        level_jump = valid_recommendation_payload()
        level_jump["recommended_level"] = "L2"
        bad_result = valid_demotion_payload()
        bad_result["resulting_level"] = "L1"
        nonqualified_advance = valid_recommendation_payload()
        nonqualified_advance["reason_code"] = "security_failure"
        for parser, payload, code in (
            (PromotionRecommendationV1.from_dict, recommendation, "external_action_forbidden"),
            (DemotionDecisionV1.from_dict, demotion, "external_action_forbidden"),
            (PromotionRecommendationV1.from_dict, level_jump, "invalid_transition"),
            (
                PromotionRecommendationV1.from_dict,
                nonqualified_advance,
                "invalid_transition",
            ),
            (DemotionDecisionV1.from_dict, bad_result, "invalid_demotion"),
        ):
            with self.subTest(code=code), self.assertRaisesRegex(ContractError, code):
                parser(payload)


class AutonomyDemotionTests(unittest.TestCase):
    """Synthetic trigger facts only; no case is a production incident record."""

    def setUp(self):
        cohort = CohortEvidenceV1.from_dict(qualifying_cohort_payload())
        l0_profile, _ = evaluate_autonomy(cohort, None, NOW)
        profile_payload = l0_profile.to_dict()
        profile_payload["current_level"] = "L2"
        self.profile = AutonomyProfileV1.from_dict(profile_payload)

    def test_every_closed_trigger_atomically_returns_one_l0_halted_pair(self):
        triggers = (
            "security_failure",
            "authorization_failure",
            "incorrect_merge",
            "rollback",
            "escaped_defect",
            "invalid_attestation",
            "policy_bypass",
            "unexplained_regression",
        )
        for trigger in triggers:
            with self.subTest(trigger=trigger):
                updated, decision = demote_profile(self.profile, frozenset({trigger}), NOW)
                self.assertEqual(
                    (
                        updated.current_level,
                        updated.halted,
                        updated.total_demotion_triggers,
                        updated.tuple_digest,
                        updated.cohort_digest,
                    ),
                    (
                        "L0",
                        True,
                        1,
                        self.profile.tuple_digest,
                        self.profile.cohort_digest,
                    ),
                )
                self.assertEqual(
                    (
                        decision.profile_digest,
                        decision.tuple_digest,
                        decision.trigger,
                        decision.prior_level,
                        decision.resulting_level,
                        decision.halt,
                        decision.external_action_authorized,
                    ),
                    (
                        self.profile.digest,
                        self.profile.tuple_digest,
                        trigger,
                        "L2",
                        "L0",
                        True,
                        False,
                    ),
                )
                self.assertEqual(self.profile.current_level, "L2")
                self.assertIs(self.profile.halted, False)

    def test_trigger_set_uses_fixed_priority_and_counter_is_bounded(self):
        updated, decision = demote_profile(
            self.profile,
            frozenset({"policy_bypass", "rollback", "security_failure"}),
            NOW,
        )
        self.assertEqual(decision.trigger, "security_failure")
        self.assertEqual(updated.total_demotion_triggers, 3)

        saturated_payload = self.profile.to_dict()
        saturated_payload["total_demotion_triggers"] = 1_000_000
        saturated = AutonomyProfileV1.from_dict(saturated_payload)
        bounded, _ = demote_profile(saturated, frozenset({"rollback"}), NOW)
        self.assertEqual(bounded.total_demotion_triggers, 1_000_000)

    def test_demotion_rejects_non_factual_shapes_unknown_reasons_and_naive_time(self):
        cases = (
            (self.profile.to_dict(), frozenset({"rollback"}), NOW, "invalid_contract"),
            (self.profile, frozenset(), NOW, "invalid_demotion_trigger"),
            (self.profile, frozenset({"other"}), NOW, "invalid_demotion_trigger"),
            (self.profile, ["rollback"], NOW, "invalid_contract"),
            (
                self.profile,
                frozenset({"rollback"}),
                datetime(2026, 9, 2, 6, 0),
                "invalid_time",
            ),
        )
        for profile, triggers, observed_at, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(ContractError, code):
                demote_profile(profile, triggers, observed_at)

    def test_halted_result_cannot_produce_a_new_promotion_recommendation(self):
        halted, _ = demote_profile(self.profile, frozenset({"escaped_defect"}), NOW)
        next_payload = qualifying_cohort_payload()
        next_payload["tasks"][29]["attestation_receipt_digest"] = "c" * 64
        next_cohort = CohortEvidenceV1.from_dict(next_payload)

        current, recommendation = evaluate_autonomy(next_cohort, halted, NOW)

        self.assertEqual((current.current_level, current.halted), ("L0", True))
        self.assertEqual(
            (recommendation.recommended_level, recommendation.reason_code),
            ("L0", "halted_profile"),
        )


if __name__ == "__main__":
    unittest.main()
