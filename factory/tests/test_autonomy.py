"""Synthetic actual-M7 bridge and M8 algorithm fixtures; never factual evidence."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timezone
import hashlib
import json
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
from adaptive_factory.m7_autonomy_bridge import M7AutonomyBridgeV1
from adaptive_factory.shadow_evaluation import aggregate_shadow_cohort, evaluate_shadow_cohort


SYNTHETIC_ALGORITHM_FIXTURES_ONLY = True
NOW = datetime(2026, 9, 4, 0, 0, tzinfo=timezone.utc)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _domain_digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + _canonical(value)).hexdigest()


def m7_key_payload() -> dict[str, object]:
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


def m7_bundle_payload(index: int) -> dict[str, object]:
    task_id = f"task-{index:03d}"
    run_id = f"run-{index:03d}"
    input_head = f"{index + 100:040x}"
    result_head = f"{index + 200:040x}"
    legacy = f"{index + 300:064x}"
    packet = f"{index + 400:064x}"
    subject = f"{index + 500:064x}"
    verdict = {
        "schema_version": 1,
        "subject_digest": subject,
        "decision": "pass",
        "decision_source": "deterministic_adjudicator",
        "finding_identity_digests": [],
        "duplicate_identity_digests": [],
        "correlated_requirement_keys": [],
        "contradicted_requirement_keys": [],
        "unsupported_pass_requirement_keys": [],
        "residual_risk": "none",
    }
    binding_digest = f"{index + 600:064x}"
    validation_inputs_digest = f"{index + 700:064x}"
    envelope = {
        "contract": "adaptive-factory.semantic-subject-envelope/v1",
        "binding_digest": binding_digest,
        "validation_inputs_digest": validation_inputs_digest,
        "subject_digest": subject,
    }
    m4 = {
        "schema_version": 1,
        "task_id": task_id,
        "run_id": run_id,
        "owner": f"worker-{index:03d}",
        "role": "writer",
        "fence": index + 1,
        "intent_digest": legacy,
        "lease_packet_digest": legacy,
    }
    m5 = {
        "schema_version": 1,
        "task_id": task_id,
        "run_id": run_id,
        "owner": f"worker-{index:03d}",
        "role": "writer",
        "fence": index + 1,
        "repository_id": "owner/repository",
        "legacy_intent_digest": legacy,
        "task_packet_digest": packet,
        "run_manifest_digest": f"{index + 800:064x}",
        "workspace_snapshot_digest": f"{index + 900:064x}",
        "workspace_result_digest": f"{index + 1000:064x}",
        "authority_exact_head_sha": input_head,
        "snapshot_input_head_sha": input_head,
        "snapshot_result_head_sha": result_head,
        "result_exact_head_sha": result_head,
    }
    m6 = {
        "schema_version": 1,
        "task_id": task_id,
        "run_id": run_id,
        "owner": f"worker-{index:03d}",
        "role": "writer",
        "fence": index + 1,
        "repository_id": "owner/repository",
        "legacy_intent_digest": legacy,
        "task_packet_digest": packet,
        "run_manifest_digest": m5["run_manifest_digest"],
        "workspace_snapshot_digest": m5["workspace_snapshot_digest"],
        "workspace_result_digest": m5["workspace_result_digest"],
        "binding_input_head_sha": input_head,
        "binding_exact_head_sha": result_head,
        "subject_exact_head_sha": result_head,
        "envelope_digest": _digest(envelope),
        "binding_digest": binding_digest,
        "validation_inputs_digest": validation_inputs_digest,
        "subject_digest": subject,
        "evidence_set_digest": f"{index + 1100:064x}",
        "verdict_digest": _digest(verdict),
        "verdict": verdict,
    }
    evidence = {"schema_version": 1, "m4": m4, "m5": m5, "m6": m6}
    evidence_digest = _domain_digest(
        "adaptive-factory.m7-shadow-task-evidence/v1", evidence
    )
    operator = {
        "schema_version": 1,
        "subject_digest": evidence_digest,
        "external_capability": "absent",
        "recommended_action": "human_review",
        "instructions": [
            "human_decides_merge",
            "inspect_local_bundle",
            "obtain_human_review",
            "verify_exact_sha_trust_ci",
        ],
    }
    unsigned = {
        "schema_version": 1,
        "status": "blocked_pending_durable_lookup",
        "evidence": evidence,
        "operator_handoff": operator,
    }
    return {
        **unsigned,
        "bundle_digest": _domain_digest(
            "adaptive-factory.m7-ready-for-pr-bundle/v1", unsigned
        ),
    }


def m7_outcome_payload(index: int, bundle_digest: str, key_digest: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "outcome_id": f"outcome-{index:03d}",
        "bundle_digest": bundle_digest,
        "cohort_key_digest": key_digest,
        "human_evidence_digest": f"{index + 1200:064x}",
        "human_decision": "merged_accepted",
        "first_pass_accepted": True,
        "rework_required": False,
        "validator_false_negative": False,
        "validator_false_positive_or_disagreement": False,
        "repair_cycles": 0,
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


def _reclose_handoff(payload: dict[str, object]) -> None:
    # Derived M7 bodies are deliberately absent from the envelope. The bridge
    # reparses the actual cohort and recomputes both values itself.
    assert "aggregate" not in payload
    assert "evaluation" not in payload


def valid_handoff_payload(task_count: int = 30) -> dict[str, object]:
    key = m7_key_payload()
    key_digest = _domain_digest("adaptive-factory.m7-shadow-cohort-key/v1", key)
    bundles = [m7_bundle_payload(index) for index in range(task_count)]
    outcomes = [
        m7_outcome_payload(index, str(bundle["bundle_digest"]), key_digest)
        for index, bundle in enumerate(bundles)
    ]
    cohort = {
        "schema_version": 1,
        "cohort_id": "synthetic-m8-wire-cohort",
        "key": key,
        "observation_days": 14,
        "release_cycle_complete": False,
        "baseline_review_seconds": [100] * max(30, task_count),
        "outcomes": outcomes,
    }
    payload: dict[str, object] = {
        "schema_version": 1,
        "provider_mapping": {
            "schema_version": 1,
            "cohort_key_digest": key_digest,
            "validator_digest": key["validator_digest"],
            "provider_digest": "3" * 64,
        },
        "bundles": sorted(bundles, key=lambda item: str(item["bundle_digest"])),
        "cohort": cohort,
    }
    _reclose_handoff(payload)
    return payload


def valid_tuple_payload(handoff: dict[str, object] | None = None) -> dict[str, object]:
    handoff = valid_handoff_payload() if handoff is None else handoff
    cohort = handoff["cohort"]
    mapping = handoff["provider_mapping"]
    assert isinstance(cohort, dict) and isinstance(mapping, dict)
    key = cohort["key"]
    assert isinstance(key, dict)
    return {
        "schema_version": 1,
        "repository_id": key["repository_id"],
        "task_class": "low_risk_text_only",
        "m7_change_class": key["change_class"],
        "m7_cohort_key_digest": _domain_digest(
            "adaptive-factory.m7-shadow-cohort-key/v1", key
        ),
        "provider_mapping_digest": _domain_digest(
            "adaptive-factory.m8-m7-provider-mapping/v1", mapping
        ),
        "agent_digest": key["agent_digest"],
        "validator_digest": key["validator_digest"],
        "provider_digest": mapping["provider_digest"],
        "model_digest": key["model_digest"],
        "prompt_digest": key["prompt_digest"],
        "policy_digest": key["policy_digest"],
        "runner_digest": key["runner_digest"],
        "holdout_digest": key["holdout_digest"],
        "authority_digest": key["authority_digest"],
        "authority_ceiling": "L2",
        "expires_at": "2026-09-07T18:00:00Z",
    }


def valid_cohort_payload(task_count: int = 30) -> dict[str, object]:
    handoff = valid_handoff_payload(task_count)
    tuple_payload = valid_tuple_payload(handoff)
    tuple_digest = _domain_digest("adaptive-factory.m8-autonomy-tuple/v1", tuple_payload)
    cohort = handoff["cohort"]
    bundles = handoff["bundles"]
    assert isinstance(cohort, dict) and isinstance(bundles, list)
    outcomes = cohort["outcomes"]
    assert isinstance(outcomes, list)
    bundle_by_digest = {str(bundle["bundle_digest"]): bundle for bundle in bundles}
    tasks = []
    for index, outcome in enumerate(outcomes):
        assert isinstance(outcome, dict)
        bundle = bundle_by_digest[str(outcome["bundle_digest"])]
        evidence = bundle["evidence"]
        assert isinstance(evidence, dict)
        m4 = evidence["m4"]
        m5 = evidence["m5"]
        assert isinstance(m4, dict) and isinstance(m5, dict)
        tasks.append(
            {
                "schema_version": 1,
                "tuple_digest": tuple_digest,
                "task_id": m4["task_id"],
                "run_id": m4["run_id"],
                "exact_head_sha": m5["result_exact_head_sha"],
                "observed_at": "2026-09-02T06:00:00Z"
                if index < 15
                else "2026-09-03T06:00:00Z",
                "m7_bundle_digest": bundle["bundle_digest"],
                "m7_outcome_digest": _domain_digest(
                    "adaptive-factory.m7-shadow-outcome/v1", outcome
                ),
                "audit_sampled": index in {0, 1, 2, 15, 16, 17},
                "audit_accepted": index in {0, 1, 2, 15, 16, 17},
                "human_acceptance_receipt_digest": outcome["human_evidence_digest"],
                "attestation_receipt_digest": f"{index + 1400:064x}",
                "quality_score_millionths": 990_000,
                "security_failure_count": 0,
                "authorization_failure_count": 0,
                "duplicate_dispatch_count": 0,
                "cost_usd_micros": 100_000,
                "latency_ms": 1_000,
                "demotion_trigger_count": 0,
            }
        )
    return {
        "schema_version": 1,
        "autonomy_tuple": tuple_payload,
        "tasks": tasks,
        "m7_handoff": handoff,
        "window_started_at": "2026-09-02T00:00:00Z",
        "window_ended_at": "2026-09-04T00:00:00Z",
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


def valid_profile_payload(tuple_digest: str, cohort_digest: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "tuple_digest": tuple_digest,
        "cohort_digest": cohort_digest,
        "current_level": "L1",
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


class M7BridgeContractTests(unittest.TestCase):
    def test_full_handoff_recomputes_all_bodies_and_has_no_caller_acceptance_flag(self):
        payload = valid_handoff_payload()
        handoff = M7AutonomyBridgeV1.from_dict(payload)

        self.assertEqual(handoff.to_dict(), payload)
        self.assertEqual(len(handoff.bundles), 30)
        self.assertFalse(handoff.external_acceptance_available)
        self.assertFalse(handoff.currentness_available)
        self.assertEqual(handoff.aggregate, aggregate_shadow_cohort(handoff.cohort))
        self.assertEqual(handoff.evaluation, evaluate_shadow_cohort(handoff.cohort))
        self.assertNotIn("acceptance_status", handoff.to_dict())
        self.assertNotIn("currentness_status", handoff.to_dict())

    def test_bundle_legacy_packet_and_input_result_identities_are_separately_bound(self):
        handoff = M7AutonomyBridgeV1.from_dict(valid_handoff_payload(1))
        bundle = handoff.bundles[0].to_dict()
        m4 = bundle["evidence"]["m4"]
        m5 = bundle["evidence"]["m5"]
        m6 = bundle["evidence"]["m6"]
        self.assertEqual(m4["intent_digest"], m5["legacy_intent_digest"])
        self.assertNotEqual(m4["intent_digest"], m5["task_packet_digest"])
        self.assertEqual(m5["authority_exact_head_sha"], m6["binding_input_head_sha"])
        self.assertEqual(m5["result_exact_head_sha"], m6["subject_exact_head_sha"])

    def test_outcome_bundle_mismatch_fails_after_all_digests_are_reclosed(self):
        payload = valid_handoff_payload()
        cohort = payload["cohort"]
        assert isinstance(cohort, dict)
        outcomes = cohort["outcomes"]
        assert isinstance(outcomes, list) and isinstance(outcomes[0], dict)
        outcomes[0]["bundle_digest"] = "9" * 64
        _reclose_handoff(payload)

        with self.assertRaisesRegex(ContractError, "m7_outcome_mismatch"):
            M7AutonomyBridgeV1.from_dict(payload)

    def test_validator_swap_and_provider_map_mismatch_do_not_collapse(self):
        validator_swap = valid_handoff_payload()
        cohort = validator_swap["cohort"]
        assert isinstance(cohort, dict) and isinstance(cohort["key"], dict)
        cohort["key"]["validator_digest"] = "8" * 64
        key_digest = _domain_digest(
            "adaptive-factory.m7-shadow-cohort-key/v1", cohort["key"]
        )
        outcomes = cohort["outcomes"]
        assert isinstance(outcomes, list)
        for outcome in outcomes:
            assert isinstance(outcome, dict)
            outcome["cohort_key_digest"] = key_digest
        _reclose_handoff(validator_swap)

        provider_mismatch = valid_handoff_payload()
        mapping = provider_mismatch["provider_mapping"]
        assert isinstance(mapping, dict)
        mapping["cohort_key_digest"] = "7" * 64

        collapsed = valid_handoff_payload()
        collapsed_mapping = collapsed["provider_mapping"]
        assert isinstance(collapsed_mapping, dict)
        collapsed_mapping["provider_digest"] = collapsed_mapping["validator_digest"]

        for payload in (validator_swap, provider_mismatch, collapsed):
            with self.subTest(), self.assertRaisesRegex(
                ContractError, "provider_mapping_mismatch"
            ):
                M7AutonomyBridgeV1.from_dict(payload)

    def test_caller_cannot_supply_derived_or_authority_status_fields(self):
        for field in (
            "aggregate",
            "evaluation",
            "eligible",
            "acceptance_status",
            "currentness_status",
        ):
            payload = valid_handoff_payload()
            payload[field] = {}
            with self.subTest(field=field), self.assertRaisesRegex(
                ContractError, "unknown_fields"
            ):
                M7AutonomyBridgeV1.from_dict(payload)

    def test_direct_wrapper_construction_cannot_bypass_wire_recomputation(self):
        valid = M7AutonomyBridgeV1.from_dict(valid_handoff_payload())
        # Simulate an object that bypassed the producer constructor; ordinary
        # dataclass replacement is already rejected by the canonical M7 type.
        forged_bundle = object.__new__(type(valid.bundles[0]))
        for field in fields(type(valid.bundles[0])):
            object.__setattr__(
                forged_bundle, field.name, getattr(valid.bundles[0], field.name)
            )
        object.__setattr__(forged_bundle, "status", "ready")
        bundles = tuple(
            sorted((forged_bundle, *valid.bundles[1:]), key=lambda item: item.bundle_digest)
        )

        with self.assertRaisesRegex(ContractError, "invalid_bundle_status"):
            M7AutonomyBridgeV1(
                schema_version=1,
                provider_mapping=valid.provider_mapping,
                bundles=bundles,
                cohort=valid.cohort,
            )


class AutonomyContractTests(unittest.TestCase):
    def test_synthetic_data_is_explicitly_not_factual_evidence(self):
        self.assertIs(SYNTHETIC_ALGORITHM_FIXTURES_ONLY, True)

    def test_tuple_binds_validator_and_explicit_provider_mapping(self):
        payload = valid_tuple_payload()
        autonomy_tuple = AutonomyTupleV1.from_dict(payload)
        self.assertEqual(autonomy_tuple.to_dict(), payload)
        self.assertIn("validator_digest", {field.name for field in fields(AutonomyTupleV1)})
        self.assertIn("provider_mapping_digest", {field.name for field in fields(AutonomyTupleV1)})
        with self.assertRaises(FrozenInstanceError):
            autonomy_tuple.provider_digest = "0" * 64

        swapped = deepcopy(payload)
        swapped["validator_digest"] = "8" * 64
        self.assertNotEqual(
            AutonomyTupleV1.from_dict(swapped).digest,
            autonomy_tuple.digest,
        )

    def test_old_synthetic_authority_fields_are_unknown(self):
        cohort = valid_cohort_payload()
        cohort["factual_m7_restack_observed"] = True
        tasks = cohort["tasks"]
        assert isinstance(tasks, list) and isinstance(tasks[0], dict)
        tasks[0]["eligible"] = True
        old_tuple = valid_tuple_payload()
        old_tuple["m7_product_sha"] = "7" * 40
        for parser, payload in (
            (CohortEvidenceV1.from_dict, cohort),
            (AutonomyTupleV1.from_dict, old_tuple),
        ):
            with self.subTest(), self.assertRaisesRegex(ContractError, "unknown_fields"):
                parser(payload)

    def test_arbitrary_receipt_and_stale_task_identity_are_rejected(self):
        receipt = valid_cohort_payload()
        receipt_tasks = receipt["tasks"]
        assert isinstance(receipt_tasks, list) and isinstance(receipt_tasks[0], dict)
        receipt_tasks[0]["human_acceptance_receipt_digest"] = "9" * 64
        stale = valid_cohort_payload()
        stale_tasks = stale["tasks"]
        assert isinstance(stale_tasks, list) and isinstance(stale_tasks[0], dict)
        stale_tasks[0]["exact_head_sha"] = "9" * 40
        for payload in (receipt, stale):
            with self.subTest(), self.assertRaisesRegex(
                ContractError, "m7_outcome_mismatch"
            ):
                CohortEvidenceV1.from_dict(payload)

    def test_nonaccepted_outcome_is_derived_not_overridden_by_task(self):
        payload = valid_cohort_payload()
        handoff = payload["m7_handoff"]
        tasks = payload["tasks"]
        assert isinstance(handoff, dict) and isinstance(tasks, list)
        cohort = handoff["cohort"]
        assert isinstance(cohort, dict) and isinstance(cohort["outcomes"], list)
        outcome = cohort["outcomes"][0]
        assert isinstance(outcome, dict) and isinstance(tasks[0], dict)
        outcome["human_decision"] = "not_merged"
        outcome["first_pass_accepted"] = False
        tasks[0]["m7_outcome_digest"] = _domain_digest(
            "adaptive-factory.m7-shadow-outcome/v1", outcome
        )
        _reclose_handoff(handoff)
        parsed = CohortEvidenceV1.from_dict(payload)

        profile, recommendation = evaluate_autonomy(parsed, None, NOW)

        self.assertEqual(profile.accepted_task_count, 29)
        self.assertEqual(recommendation.reason_code, "human_acceptance_missing")


class AutonomyEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.cohort = CohortEvidenceV1.from_dict(valid_cohort_payload())

    def test_closed_m7_bundle_blocks_forged_thirty_row_qualification(self):
        profile, recommendation = evaluate_autonomy(self.cohort, None, NOW)

        self.assertEqual(profile.accepted_task_count, 30)
        self.assertEqual(profile.audit_sample_count, 6)
        self.assertEqual(
            (recommendation.current_level, recommendation.recommended_level),
            ("L0", "L0"),
        )
        self.assertEqual(recommendation.reason_code, "m7_bundle_blocked")
        self.assertFalse(recommendation.external_action_authorized)

    def test_existing_l2_profile_never_advances_or_authorizes(self):
        profile_payload = valid_profile_payload(
            self.cohort.autonomy_tuple.digest, self.cohort.digest
        )
        profile_payload["current_level"] = "L2"
        profile_payload["cohort_digest"] = "9" * 64
        profile = AutonomyProfileV1.from_dict(profile_payload)

        _, recommendation = evaluate_autonomy(self.cohort, profile, NOW)

        self.assertEqual(recommendation.recommended_level, "L2")
        self.assertEqual(recommendation.reason_code, "m7_bundle_blocked")
        self.assertFalse(recommendation.external_action_authorized)

    def test_tuple_mutation_and_replay_are_exact(self):
        profile = AutonomyProfileV1.from_dict(
            valid_profile_payload(self.cohort.autonomy_tuple.digest, self.cohort.digest)
        )
        _, replay = evaluate_autonomy(self.cohort, profile, NOW)
        self.assertEqual(replay.reason_code, "cohort_replay")

        mutated_payload = valid_cohort_payload()
        tuple_payload = mutated_payload["autonomy_tuple"]
        tasks = mutated_payload["tasks"]
        assert isinstance(tuple_payload, dict) and isinstance(tasks, list)
        tuple_payload["model_digest"] = "8" * 64
        mutated_digest = _domain_digest(
            "adaptive-factory.m8-autonomy-tuple/v1", tuple_payload
        )
        for task in tasks:
            assert isinstance(task, dict)
            task["tuple_digest"] = mutated_digest
        with self.assertRaisesRegex(ContractError, "tuple_mismatch"):
            CohortEvidenceV1.from_dict(mutated_payload)

    def test_expiry_and_open_window_fail_closed(self):
        with self.assertRaisesRegex(ContractError, "cohort_window_open"):
            evaluate_autonomy(
                self.cohort,
                None,
                datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc),
            )
        expired_payload = valid_cohort_payload()
        tuple_payload = expired_payload["autonomy_tuple"]
        tasks = expired_payload["tasks"]
        assert isinstance(tuple_payload, dict) and isinstance(tasks, list)
        tuple_payload["expires_at"] = "2026-09-04T00:00:00Z"
        tuple_digest = _domain_digest(
            "adaptive-factory.m8-autonomy-tuple/v1", tuple_payload
        )
        for task in tasks:
            assert isinstance(task, dict)
            task["tuple_digest"] = tuple_digest
        expired = CohortEvidenceV1.from_dict(expired_payload)
        _, recommendation = evaluate_autonomy(expired, None, NOW)
        self.assertEqual(recommendation.reason_code, "tuple_expired")


class AutonomyRegressionBoundaryTests(unittest.TestCase):
    def test_exact_threshold_metrics_remain_integer_and_m7_blocked(self):
        payload = valid_cohort_payload()
        tasks = payload["tasks"]
        assert isinstance(tasks, list)
        for index, task in enumerate(tasks):
            assert isinstance(task, dict)
            task["quality_score_millionths"] = 950_000
            task["cost_usd_micros"] = 200_000
            task["latency_ms"] = index + 1
        payload["maximum_latency_ms"] = 30

        profile, recommendation = evaluate_autonomy(
            CohortEvidenceV1.from_dict(payload), None, NOW
        )

        self.assertEqual(profile.accepted_task_count, 30)
        self.assertEqual((profile.audit_sample_count, profile.audit_accepted_count), (6, 6))
        self.assertEqual(profile.minimum_quality_score_millionths, 950_000)
        self.assertEqual(profile.maximum_cost_usd_micros, 200_000)
        self.assertEqual(profile.p95_latency_ms, 29)
        self.assertEqual(recommendation.reason_code, "m7_bundle_blocked")

    def test_each_reachable_gate_reason_remains_independently_observable(self):
        cases: list[tuple[str, dict[str, object]]] = []
        cases.append(("insufficient_acceptances", valid_cohort_payload(29)))

        human = valid_cohort_payload()
        handoff = human["m7_handoff"]
        tasks = human["tasks"]
        assert isinstance(handoff, dict) and isinstance(tasks, list)
        cohort = handoff["cohort"]
        assert isinstance(cohort, dict) and isinstance(cohort["outcomes"], list)
        outcome = cohort["outcomes"][0]
        assert isinstance(outcome, dict) and isinstance(tasks[0], dict)
        outcome["human_decision"] = "not_merged"
        outcome["first_pass_accepted"] = False
        tasks[0]["m7_outcome_digest"] = _domain_digest(
            "adaptive-factory.m7-shadow-outcome/v1", outcome
        )
        _reclose_handoff(handoff)
        cases.append(("human_acceptance_missing", human))

        audit_rate = valid_cohort_payload()
        assert isinstance(audit_rate["tasks"], list)
        audit_rate["tasks"][17]["audit_sampled"] = False
        audit_rate["tasks"][17]["audit_accepted"] = False
        cases.append(("audit_rate_insufficient", audit_rate))

        audit_day = valid_cohort_payload()
        assert isinstance(audit_day["tasks"], list)
        for index in (15, 16, 17):
            audit_day["tasks"][index]["audit_sampled"] = False
            audit_day["tasks"][index]["audit_accepted"] = False
        for index in (3, 4, 5):
            audit_day["tasks"][index]["audit_sampled"] = True
            audit_day["tasks"][index]["audit_accepted"] = True
        cases.append(("audit_day_gap", audit_day))

        audit_rejected = valid_cohort_payload()
        assert isinstance(audit_rejected["tasks"], list)
        audit_rejected["tasks"][0]["audit_accepted"] = False
        cases.append(("audit_rejected", audit_rejected))

        mutations = (
            ("quality_below_threshold", "quality_score_millionths", 949_999),
            ("security_failure", "security_failure_count", 1),
            ("authorization_failure", "authorization_failure_count", 1),
            ("duplicate_dispatch", "duplicate_dispatch_count", 1),
            ("cost_above_threshold", "cost_usd_micros", 200_001),
            ("demotion_fact_present", "demotion_trigger_count", 1),
        )
        for reason, field, value in mutations:
            payload = valid_cohort_payload()
            assert isinstance(payload["tasks"], list)
            payload["tasks"][29][field] = value
            cases.append((reason, payload))

        latency = valid_cohort_payload()
        assert isinstance(latency["tasks"], list)
        latency["tasks"][28]["latency_ms"] = 2_001
        latency["tasks"][29]["latency_ms"] = 2_001
        cases.append(("latency_above_threshold", latency))

        for reason, payload in cases:
            with self.subTest(reason=reason):
                _, recommendation = evaluate_autonomy(
                    CohortEvidenceV1.from_dict(payload), None, NOW
                )
                self.assertEqual(recommendation.reason_code, reason)
                self.assertEqual(recommendation.recommended_level, "L0")

    def test_task_bounds_times_receipts_and_metrics_fail_closed(self):
        task_payload = valid_cohort_payload()["tasks"][0]
        assert isinstance(task_payload, dict)
        cases = []
        for field, value, code in (
            ("task_id", "x" * 129, "invalid_identifier"),
            ("observed_at", "not-a-time", "invalid_time"),
            ("attestation_receipt_digest", "secret-value", "invalid_digest"),
            ("quality_score_millionths", 1_000_001, "invalid_integer"),
            ("cost_usd_micros", 1_000_000_000_001, "invalid_integer"),
            ("latency_ms", 604_800_001, "invalid_integer"),
        ):
            mutation = deepcopy(task_payload)
            mutation[field] = value
            cases.append((mutation, code))
        for payload, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(ContractError, code):
                CohortTaskEvidenceV1.from_dict(payload)

    def test_cohort_order_distinctness_and_deep_immutability_are_preserved(self):
        cohort = CohortEvidenceV1.from_dict(valid_cohort_payload())
        with self.assertRaises(TypeError):
            cohort.tasks[0] = cohort.tasks[1]
        detached = cohort.m7_handoff.to_dict()
        detached["bundles"].clear()
        self.assertEqual(len(cohort.m7_handoff.bundles), 30)

        duplicate = valid_cohort_payload()
        assert isinstance(duplicate["tasks"], list)
        duplicate["tasks"][1]["run_id"] = duplicate["tasks"][0]["run_id"]
        unordered = valid_cohort_payload()
        assert isinstance(unordered["tasks"], list)
        unordered["tasks"].reverse()
        duplicate_link = valid_cohort_payload()
        assert isinstance(duplicate_link["tasks"], list)
        duplicate_link["tasks"][1]["m7_outcome_digest"] = duplicate_link["tasks"][0][
            "m7_outcome_digest"
        ]
        for payload, code in (
            (duplicate, "duplicate_identity"),
            (unordered, "invalid_order"),
            (duplicate_link, "duplicate_identity"),
        ):
            with self.subTest(code=code), self.assertRaisesRegex(ContractError, code):
                CohortEvidenceV1.from_dict(payload)

    def test_evaluator_requires_frozen_records_and_aware_time(self):
        cohort = CohortEvidenceV1.from_dict(valid_cohort_payload())
        with self.assertRaisesRegex(ContractError, "invalid_contract"):
            evaluate_autonomy(cohort.to_dict(), None, NOW)
        with self.assertRaisesRegex(ContractError, "invalid_time"):
            evaluate_autonomy(cohort, None, datetime(2026, 9, 4, 0, 0))

    def test_task_at_expiry_fails_before_evaluation(self):
        payload = valid_cohort_payload()
        tuple_payload = payload["autonomy_tuple"]
        tasks = payload["tasks"]
        assert isinstance(tuple_payload, dict) and isinstance(tasks, list)
        tuple_payload["expires_at"] = "2026-09-04T00:00:00Z"
        tasks[29]["observed_at"] = "2026-09-04T00:00:00Z"
        tuple_digest = _domain_digest(
            "adaptive-factory.m8-autonomy-tuple/v1", tuple_payload
        )
        for task in tasks:
            assert isinstance(task, dict)
            task["tuple_digest"] = tuple_digest
        with self.assertRaisesRegex(ContractError, "task_at_or_after_tuple_expiry"):
            CohortEvidenceV1.from_dict(payload)

    def test_halted_profile_cannot_recommend_promotion(self):
        cohort = CohortEvidenceV1.from_dict(valid_cohort_payload())
        payload = valid_profile_payload(cohort.autonomy_tuple.digest, "9" * 64)
        payload["current_level"] = "L0"
        payload["halted"] = True
        halted = AutonomyProfileV1.from_dict(payload)

        current, recommendation = evaluate_autonomy(cohort, halted, NOW)

        self.assertEqual((current.current_level, current.halted), ("L0", True))
        self.assertEqual(recommendation.reason_code, "halted_profile")
        self.assertEqual(recommendation.recommended_level, "L0")


class AutonomyDemotionTests(unittest.TestCase):
    def setUp(self):
        cohort = CohortEvidenceV1.from_dict(valid_cohort_payload())
        self.profile = AutonomyProfileV1.from_dict(
            valid_profile_payload(cohort.autonomy_tuple.digest, cohort.digest)
        )

    def test_every_trigger_atomically_returns_l0_halted_without_action(self):
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
                self.assertEqual((updated.current_level, updated.halted), ("L0", True))
                self.assertEqual(decision.trigger, trigger)
                self.assertFalse(decision.external_action_authorized)

    def test_trigger_priority_is_fixed_and_inputs_fail_closed(self):
        updated, decision = demote_profile(
            self.profile,
            frozenset({"policy_bypass", "rollback", "security_failure"}),
            NOW,
        )
        self.assertEqual(decision.trigger, "security_failure")
        self.assertEqual(updated.total_demotion_triggers, 3)
        for triggers in (frozenset(), frozenset({"other"}), ["rollback"]):
            with self.subTest(triggers=triggers), self.assertRaises(ContractError):
                demote_profile(self.profile, triggers, NOW)


class ClosedM8RecordTests(unittest.TestCase):
    def test_all_m8_records_reject_unknown_missing_and_wrong_version(self):
        cohort = CohortEvidenceV1.from_dict(valid_cohort_payload())
        profile = valid_profile_payload(cohort.autonomy_tuple.digest, cohort.digest)
        recommendation = {
            "schema_version": 1,
            "tuple_digest": cohort.autonomy_tuple.digest,
            "cohort_digest": cohort.digest,
            "current_level": "L0",
            "recommended_level": "L0",
            "reason_code": "m7_bundle_blocked",
            "evaluated_at": "2026-09-04T00:00:00Z",
            "expires_at": "2026-09-07T18:00:00Z",
            "separate_activation_required": True,
            "external_action_authorized": False,
        }
        demotion = {
            "schema_version": 1,
            "profile_digest": "3" * 64,
            "tuple_digest": cohort.autonomy_tuple.digest,
            "trigger": "security_failure",
            "prior_level": "L1",
            "resulting_level": "L0",
            "effective_at": "2026-09-04T00:00:00Z",
            "halt": True,
            "external_action_authorized": False,
        }
        cases = (
            (AutonomyTupleV1, valid_tuple_payload()),
            (CohortTaskEvidenceV1, valid_cohort_payload()["tasks"][0]),
            (CohortEvidenceV1, valid_cohort_payload()),
            (AutonomyProfileV1, profile),
            (PromotionRecommendationV1, recommendation),
            (DemotionDecisionV1, demotion),
        )
        for contract, original in cases:
            assert isinstance(original, dict)
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

    def test_external_action_and_levels_are_closed(self):
        cohort = CohortEvidenceV1.from_dict(valid_cohort_payload())
        _, recommendation = evaluate_autonomy(cohort, None, NOW)
        payload = recommendation.to_dict()
        payload["external_action_authorized"] = True
        with self.assertRaisesRegex(ContractError, "external_action_forbidden"):
            PromotionRecommendationV1.from_dict(payload)
        tuple_payload = valid_tuple_payload()
        tuple_payload["authority_ceiling"] = "L3"
        with self.assertRaisesRegex(ContractError, "unsupported_level"):
            AutonomyTupleV1.from_dict(tuple_payload)


if __name__ == "__main__":
    unittest.main()
