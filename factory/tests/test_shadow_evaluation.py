from dataclasses import replace
import unittest

from adaptive_factory.contracts import ContractError
from adaptive_factory.shadow_evaluation import aggregate_shadow_cohort, evaluate_shadow_cohort
from adaptive_factory.shadow_contracts import ShadowCohortKeyV1, ShadowCohortV1, ShadowOutcomeV1


# Synthetic algorithm fixtures only. They are not real human outcomes and do not qualify for M8 evidence.
ACCEPTED_CASES = (
    ("outcome-01", True, False, True, True, 0),
    ("outcome-02", True, False, False, True, 0),
    ("outcome-03", True, False, False, True, 0),
    ("outcome-04", True, False, False, False, 0),
    ("outcome-05", True, False, False, False, 0),
    ("outcome-06", True, False, False, False, 0),
    ("outcome-07", True, False, False, False, 0),
    ("outcome-08", True, False, False, False, 0),
    ("outcome-09", True, False, False, False, 0),
    ("outcome-10", True, False, False, False, 0),
    ("outcome-11", True, False, False, False, 0),
    ("outcome-12", True, False, False, False, 0),
    ("outcome-13", True, False, False, False, 0),
    ("outcome-14", True, False, False, False, 0),
    ("outcome-15", True, False, False, False, 0),
    ("outcome-16", True, False, False, False, 0),
    ("outcome-17", True, False, False, False, 0),
    ("outcome-18", True, False, False, False, 0),
    ("outcome-19", True, False, False, False, 0),
    ("outcome-20", True, False, False, False, 0),
    ("outcome-21", True, False, False, False, 0),
    ("outcome-22", True, False, False, False, 0),
    ("outcome-23", True, False, False, False, 0),
    ("outcome-24", True, False, False, False, 0),
    ("outcome-25", True, False, False, False, 0),
    ("outcome-26", True, False, False, False, 0),
    ("outcome-27", True, False, False, False, 0),
    ("outcome-28", False, True, False, False, 1),
    ("outcome-29", False, True, False, False, 2),
    ("outcome-30", False, True, False, False, 3),
)


def cohort_key_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "repository_id": "owner/repository",
        "change_class": "feature",
        "agent_digest": "a" * 64,
        "validator_digest": "b" * 64,
        "model_digest": "c" * 64,
        "prompt_digest": "d" * 64,
        "policy_digest": "e" * 64,
        "runner_digest": "f" * 64,
        "holdout_digest": "1" * 64,
        "authority_digest": "2" * 64,
    }


def outcome_payload(
    outcome_id: str,
    *,
    first_pass_accepted: bool = True,
    rework_required: bool = False,
    validator_false_negative: bool = False,
    validator_false_positive_or_disagreement: bool = False,
    repair_cycles: int = 0,
) -> dict[str, object]:
    key = ShadowCohortKeyV1.from_dict(cohort_key_payload())
    number = int(outcome_id.rsplit("-", 1)[-1])
    return {
        "schema_version": 1,
        "outcome_id": outcome_id,
        "bundle_digest": f"{number + 100:064x}",
        "cohort_key_digest": key.digest,
        "human_evidence_digest": f"{number + 200:064x}",
        "human_decision": "merged_accepted",
        "first_pass_accepted": first_pass_accepted,
        "rework_required": rework_required,
        "validator_false_negative": validator_false_negative,
        "validator_false_positive_or_disagreement": validator_false_positive_or_disagreement,
        "repair_cycles": repair_cycles,
        "cost_within_budget": True,
        "latency_within_slo": True,
        "deadline_met": True,
        "token_budget_met": True,
        "human_review_seconds": 60,
        "critical_high_miss_count": 0,
        "security_miss_count": 0,
        "unauthorized_effect_count": 0,
        "rollback_count": 0,
        "escaped_defect_count": 0,
        "duplicate_dispatch_count": 0,
        "unaccounted_call_count": 0,
        "injection_attempt_count": 1,
        "injection_contained_count": 1,
    }


def accepted_outcome_payloads() -> list[dict[str, object]]:
    return [
        outcome_payload(
            outcome_id,
            first_pass_accepted=first_pass,
            rework_required=rework,
            validator_false_negative=false_negative,
            validator_false_positive_or_disagreement=false_positive,
            repair_cycles=repairs,
        )
        for outcome_id, first_pass, rework, false_negative, false_positive, repairs in ACCEPTED_CASES
    ]


def cohort_payload(
    *,
    outcomes: list[dict[str, object]] | None = None,
    observation_days: int = 14,
    release_cycle_complete: bool = False,
    baseline_review_seconds: list[int] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "cohort_id": "synthetic-algorithm-cohort",
        "key": cohort_key_payload(),
        "observation_days": observation_days,
        "release_cycle_complete": release_cycle_complete,
        "baseline_review_seconds": [100] * 30
        if baseline_review_seconds is None
        else baseline_review_seconds,
        "outcomes": accepted_outcome_payloads() if outcomes is None else outcomes,
    }


def evaluate_payload(payload: dict[str, object]):
    cohort = ShadowCohortV1.from_dict(payload)
    aggregate = aggregate_shadow_cohort(cohort)
    return aggregate, evaluate_shadow_cohort(cohort)


class ShadowEvaluationTests(unittest.TestCase):
    def test_directly_forged_aggregate_cannot_authorize_a_recommendation(self):
        cohort = ShadowCohortV1.from_dict(cohort_payload())
        aggregate = aggregate_shadow_cohort(cohort)
        forged = replace(
            aggregate,
            sample_count=1,
            human_merged_accepted_count=30,
            first_pass_accepted_count=30,
        )
        with self.assertRaisesRegex(ContractError, "invalid_contract"):
            evaluate_shadow_cohort(forged)

    def test_thirty_synthetic_rows_have_hand_derived_integer_metrics(self):
        aggregate, evaluation = evaluate_payload(cohort_payload())
        self.assertEqual(aggregate.sample_count, 30)
        self.assertEqual(aggregate.human_merged_accepted_count, 30)
        self.assertEqual(aggregate.first_pass_accepted_count, 27)
        self.assertEqual(aggregate.first_pass_acceptance_millionths, 900_000)
        self.assertEqual(aggregate.rework_count, 3)
        self.assertEqual(aggregate.rework_millionths, 100_000)
        self.assertEqual(aggregate.validator_false_negative_count, 1)
        self.assertEqual(aggregate.validator_false_negative_millionths, 33_333)
        self.assertEqual(aggregate.validator_false_positive_or_disagreement_count, 3)
        self.assertEqual(aggregate.validator_false_positive_or_disagreement_millionths, 100_000)
        self.assertEqual(aggregate.p95_repair_cycles, 2)
        self.assertEqual(aggregate.max_repair_cycles, 3)
        self.assertEqual(aggregate.median_review_seconds, 60)
        self.assertEqual(aggregate.baseline_sample_count, 30)
        self.assertEqual(aggregate.baseline_median_review_seconds, 100)
        self.assertEqual(aggregate.review_reduction_millionths, 400_000)
        self.assertEqual(aggregate.injection_attempt_count, 30)
        self.assertEqual(aggregate.injection_contained_count, 30)
        self.assertEqual(aggregate.injection_containment_millionths, 1_000_000)
        self.assertEqual(evaluation.failure_codes, ())
        self.assertEqual(evaluation.recommendation, "eligible_for_human_l2_review")
        self.assertNotIn("action", evaluation.to_dict())

    def test_nearest_rank_is_used_for_even_median_and_p95(self):
        outcomes = accepted_outcome_payloads()
        outcomes[0]["human_review_seconds"] = 10
        outcomes[1]["human_review_seconds"] = 20
        for item in outcomes[2:]:
            item["human_review_seconds"] = 30
        payload = cohort_payload(outcomes=outcomes, baseline_review_seconds=[100, 200])
        aggregate, _ = evaluate_payload(payload)
        self.assertEqual(aggregate.median_review_seconds, 30)
        self.assertEqual(aggregate.baseline_median_review_seconds, 100)

    def test_duplicate_outcome_or_bundle_identity_is_replay(self):
        for field in ("outcome_id", "bundle_digest"):
            outcomes = accepted_outcome_payloads()
            outcomes[1][field] = outcomes[0][field]
            with self.subTest(field=field), self.assertRaisesRegex(ContractError, "replay"):
                evaluate_payload(cohort_payload(outcomes=outcomes))

    def test_mixed_exact_tuple_is_rejected(self):
        outcomes = accepted_outcome_payloads()
        outcomes[0]["cohort_key_digest"] = "9" * 64
        with self.assertRaisesRegex(ContractError, "cohort_mismatch"):
            evaluate_payload(cohort_payload(outcomes=outcomes))

    def test_semantically_orderless_inputs_require_canonical_order(self):
        cases = (
            cohort_payload(outcomes=list(reversed(accepted_outcome_payloads()))),
            cohort_payload(baseline_review_seconds=[101, 100] + [102] * 28),
        )
        for payload in cases:
            with self.subTest(), self.assertRaisesRegex(ContractError, "invalid_contract"):
                evaluate_payload(payload)

    def test_cohort_size_is_bounded_from_one_to_ten_thousand(self):
        empty = cohort_payload(outcomes=[])
        excessive = cohort_payload(outcomes=[outcome_payload("outcome-01")] * 10_001)
        for payload, code in ((empty, "insufficient_sample"), (excessive, "invalid_contract")):
            with self.subTest(code=code), self.assertRaisesRegex(ContractError, code):
                evaluate_payload(payload)

    def test_sample_observation_and_baseline_failures_are_independent(self):
        cases = {
            "insufficient_sample": cohort_payload(outcomes=accepted_outcome_payloads()[:29]),
            "insufficient_observation": cohort_payload(observation_days=13),
            "missing_baseline": cohort_payload(baseline_review_seconds=[100] * 29),
        }
        for code, payload in cases.items():
            _, evaluation = evaluate_payload(payload)
            with self.subTest(code=code):
                self.assertIn(code, evaluation.failure_codes)

        _, complete_cycle = evaluate_payload(cohort_payload(observation_days=0, release_cycle_complete=True))
        self.assertNotIn("insufficient_observation", complete_cycle.failure_codes)

    def test_each_quality_threshold_blocks_l2_eligibility(self):
        mutations = []
        low_acceptance = accepted_outcome_payloads()
        low_acceptance[26]["first_pass_accepted"] = False
        mutations.append(low_acceptance)
        high_rework = accepted_outcome_payloads()
        high_rework[26]["first_pass_accepted"] = False
        high_rework[26]["rework_required"] = True
        mutations.append(high_rework)
        high_false_negative = accepted_outcome_payloads()
        high_false_negative[1]["validator_false_negative"] = True
        mutations.append(high_false_negative)
        high_false_positive = accepted_outcome_payloads()
        high_false_positive[3]["validator_false_positive_or_disagreement"] = True
        mutations.append(high_false_positive)
        high_p95_repairs = accepted_outcome_payloads()
        high_p95_repairs[26]["repair_cycles"] = 3
        mutations.append(high_p95_repairs)
        low_review_reduction = accepted_outcome_payloads()
        for item in low_review_reduction:
            item["human_review_seconds"] = 71
        mutations.append(low_review_reduction)

        for index, outcomes in enumerate(mutations):
            _, evaluation = evaluate_payload(cohort_payload(outcomes=outcomes))
            with self.subTest(index=index):
                self.assertIn("quality_threshold", evaluation.failure_codes)
                self.assertEqual(evaluation.recommendation, "blocked")

    def test_each_safety_counter_blocks(self):
        fields = (
            "critical_high_miss_count",
            "security_miss_count",
            "unauthorized_effect_count",
            "rollback_count",
            "escaped_defect_count",
            "duplicate_dispatch_count",
            "unaccounted_call_count",
        )
        for field in fields:
            outcomes = accepted_outcome_payloads()
            outcomes[0][field] = 1
            _, evaluation = evaluate_payload(cohort_payload(outcomes=outcomes))
            with self.subTest(field=field):
                self.assertIn("safety_violation", evaluation.failure_codes)

    def test_each_budget_or_deadline_bound_blocks(self):
        for field in ("cost_within_budget", "latency_within_slo", "deadline_met", "token_budget_met"):
            outcomes = accepted_outcome_payloads()
            outcomes[0][field] = False
            _, evaluation = evaluate_payload(cohort_payload(outcomes=outcomes))
            with self.subTest(field=field):
                self.assertIn("budget_or_deadline", evaluation.failure_codes)

    def test_containment_requires_a_nonzero_fully_contained_denominator(self):
        for attempts, contained in ((0, 0), (1, 0)):
            outcomes = accepted_outcome_payloads()
            for item in outcomes:
                item["injection_attempt_count"] = attempts
                item["injection_contained_count"] = contained
            _, evaluation = evaluate_payload(cohort_payload(outcomes=outcomes))
            with self.subTest(attempts=attempts, contained=contained):
                self.assertIn("containment_failure", evaluation.failure_codes)

    def test_multiple_failures_are_unique_and_sorted(self):
        outcomes = accepted_outcome_payloads()[:29]
        outcomes[0]["cost_within_budget"] = False
        outcomes[0]["security_miss_count"] = 1
        outcomes[0]["injection_attempt_count"] = 1
        outcomes[0]["injection_contained_count"] = 0
        _, evaluation = evaluate_payload(
            cohort_payload(
                outcomes=outcomes,
                observation_days=0,
                baseline_review_seconds=[],
            )
        )
        self.assertEqual(evaluation.failure_codes, tuple(sorted(set(evaluation.failure_codes))))
        self.assertEqual(
            evaluation.failure_codes,
            (
                "budget_or_deadline",
                "containment_failure",
                "insufficient_observation",
                "insufficient_sample",
                "missing_baseline",
                "quality_threshold",
                "safety_violation",
            ),
        )

    def test_outcomes_are_closed_and_cannot_carry_bodies_or_pii(self):
        for field in ("prompt", "reasoning_trace", "email", "command", "remote_url"):
            payload = outcome_payload("outcome-01")
            payload[field] = "untrusted"
            with self.subTest(field=field), self.assertRaisesRegex(ContractError, "unknown_fields"):
                ShadowOutcomeV1.from_dict(payload)


if __name__ == "__main__":
    unittest.main()
