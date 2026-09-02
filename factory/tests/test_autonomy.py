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
)
from adaptive_factory.contracts import ContractError


SYNTHETIC_ALGORITHM_FIXTURES_ONLY = True
NOW = datetime(2026, 9, 2, 6, 0, tzinfo=timezone.utc)
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
        for parser, payload, code in (
            (PromotionRecommendationV1.from_dict, recommendation, "external_action_forbidden"),
            (DemotionDecisionV1.from_dict, demotion, "external_action_forbidden"),
            (PromotionRecommendationV1.from_dict, level_jump, "invalid_transition"),
            (DemotionDecisionV1.from_dict, bad_result, "invalid_demotion"),
        ):
            with self.subTest(code=code), self.assertRaisesRegex(ContractError, code):
                parser(payload)


if __name__ == "__main__":
    unittest.main()
