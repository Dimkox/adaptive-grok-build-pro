import importlib
import importlib.util
import hashlib
import unittest
from copy import deepcopy

from adaptive_factory.contracts import ContractError


COMMON_PINS = {
    "repository_snapshot": "1" * 40,
    "model": "fixture-model@1",
    "tools_digest": "2" * 64,
    "policy_digest": "3" * 64,
    "oracle_version": "factory-semantic-oracles-v1",
    "cache_mode": "case_declared",
    "tool_version": "pump-fixture@1",
    "tool_responses_digest": "4" * 64,
    "context_digest": "5" * 64,
    "sanitizer_digest": "6" * 64,
    "prompt_digest": "7" * 64,
    "resources_digest": "8" * 64,
}


class BehaviorQualificationTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(
            importlib.util.find_spec("adaptive_factory.behavior_qualification"),
            "F24/F26 qualification harness missing",
        )
        return importlib.import_module("adaptive_factory.behavior_qualification")

    def variants(self):
        return {
            "A": {**COMMON_PINS, "representation": "native", "backend": "native"},
            "B": {**COMMON_PINS, "representation": "fpf", "backend": "native"},
            "C": {**COMMON_PINS, "representation": "fpf", "backend": "vibevm-fixture"},
        }

    @staticmethod
    def executor(mode, case, attempt):
        expected = case["expected"]
        result = {
            "status": "completed",
            "domain_result": deepcopy(expected["domain_result"]),
            "latency_ms": 10 + ord(mode),
            "cost_usd_micros": 10,
            "input_tokens": 100,
            "actual_model": COMMON_PINS["model"],
            "tool_version": "pump-fixture@1",
            "external_write_effects": 0,
            "authority_effect": "none",
            "criterion_ids": deepcopy(case["criterion_ids"]),
            "tool_responses_digest": COMMON_PINS["tool_responses_digest"],
            "context_digest": COMMON_PINS["context_digest"],
            "sanitizer_digest": COMMON_PINS["sanitizer_digest"],
            "prompt_digest": COMMON_PINS["prompt_digest"],
            "resources_digest": COMMON_PINS["resources_digest"],
            "cache_state": case["cache_state"],
            "context_bytes": {"A": 1000, "B": 800, "C": 700}[mode],
            "unique_context_bytes": {"A": 800, "B": 700, "C": 650}[mode],
            "reread_bytes": {"A": 200, "B": 100, "C": 50}[mode],
            "preparation_cost_usd_micros": {"A": 20, "B": 15, "C": 12}[mode],
            "update_cost_usd_micros": {"A": 10, "B": 8, "C": 6}[mode],
            "corrections": {"A": 2, "B": 1, "C": 0}[mode],
        }
        if case["domain"] == "pump_selector":
            result["domain_result"]["flow"] = result["domain_result"].pop("flow_m3h")
            result["domain_result"]["flow_unit"] = "m3/h"
            result["domain_result"]["head"] = result["domain_result"].pop("head_m")
            result["domain_result"]["head_unit"] = "m"
        if case["case_id"] == "F24-004":
            result["domain_result"]["flow"] = expected["domain_result"]["flow_m3h"] / 3.6
            result["domain_result"]["flow_unit"] = "l/s"
        return result

    def config(self):
        return {
            "schema_version": 1,
            "repetitions": 1,
            "max_attempts": 36,
            "max_total_latency_ms": 10_000,
            "max_total_input_tokens": 10_000,
            "max_total_cost_usd_micros": 1_000,
            "minimum_quality_micros": 1_000_000,
            "maximum_quality_regression_micros": 0,
            "declared_variable_factors": ["representation", "backend"],
        }

    def test_frozen_corpus_has_exact_four_pump_four_factory_four_cross_cases_and_baseline(self):
        module = self.module()
        suite = module.load_frozen_suite()
        baseline = module.load_immutable_baseline(suite)
        facts = suite.to_dict()
        self.assertEqual(len(facts["cases"]), 12)
        self.assertEqual([c["case_id"] for c in facts["cases"]], [f"F24-{n:03d}" for n in range(1, 13)])
        self.assertEqual([c["domain"] for c in facts["cases"]], ["pump_selector"]*4+["factory"]*4+["cross_component"]*4)
        self.assertEqual([c["oracle"] for c in facts["cases"]], [
            "pump_selection", "pump_selection", "pump_selection", "pump_selection",
            "factory_lifecycle", "factory_routing", "factory_recovery", "factory_unknown",
            "cross_rule_conflict", "cross_context", "cross_authority", "cross_handoff",
        ])
        self.assertTrue(all(c["required"] and not c["optional"] for c in facts["cases"]))
        controls = {control["control_id"] for c in facts["cases"] for control in c["negative_controls"]}
        self.assertTrue({"wrong_document","wrong_curve","unknown_to_zero","unsupported_units","illegal_transition","wrong_write_owner","duplicate_effect","silent_precedence"} <= controls)
        self.assertTrue(all(c["forbidden_outcomes"] and c["isolation"]["external_writes"] == "forbidden" for c in facts["cases"]))
        self.assertEqual(baseline.to_dict()["corpus_digest"], suite.record_digest)
        self.assertFalse(hasattr(module, "ACCEPTED_CORPUS_DIGEST"))
        mutated = suite.to_dict()
        mutated["cases"][0]["expected"]["domain_result"]["pump_model"] = "candidate-chosen-baseline"
        mutated_suite = module.FrozenQualificationSuite.from_dict(mutated)
        mutated_profile = module.make_comparator_profile("factory-f24-f26-native-v1", mutated_suite, baseline, "factory-semantic-oracles-v1")
        mutated_report = module.run_comparison(mutated_profile, self.variants(), self.config(), self.executor).to_dict()
        self.assertEqual(mutated_report["verdict"], "ready_for_external_qualification")
        self.assertEqual(mutated_report["external_qualification"]["status"], "not_run")
        self.assertNotEqual(mutated_report["corpus_digest"], suite.record_digest)
        changed_baseline = baseline.to_dict(); changed_baseline["accepted_by"] = "candidate"
        changed = module.ImmutableQualificationBaseline.from_dict(changed_baseline, suite)
        changed_profile = module.make_comparator_profile("factory-f24-f26-native-v1", suite, changed, "factory-semantic-oracles-v1")
        changed_report = module.run_comparison(changed_profile, self.variants(), self.config(), self.executor).to_dict()
        self.assertNotEqual(changed_report["baseline_digest"], baseline.record_digest)
        self.assertEqual(changed_report["external_qualification"]["status"], "not_run")

    def test_paired_a_b_c_passes_only_with_complete_common_inputs_and_budgets(self):
        module = self.module()
        result = module.run_frozen_comparison(self.variants(), self.config(), self.executor)
        report = result.to_dict()
        self.assertEqual(report["verdict"], "ready_for_external_qualification")
        self.assertEqual(report["evaluation_outcome"], "pass")
        self.assertEqual(report["external_qualification"]["status"], "not_run")
        self.assertEqual(report["case_ids"], [f"F24-{n:03d}" for n in range(1, 13)])
        self.assertEqual(len(report["attempts"]), 36)
        self.assertEqual(report["comparisons"], {"A_to_B": "pass", "B_to_C": "pass"})
        self.assertEqual(report["gates"], {
            "benefit": "pass", "budgets": "pass", "completeness": "pass", "common_conditions": "pass", "negative_controls": "pass", "quality": "pass"
        })
        self.assertEqual(report["distributions"]["A"]["latency_ms"], {"p50": 75, "p95": 75})
        self.assertEqual(report["distributions"]["A"]["input_tokens"], {"p50": 100, "p95": 100})
        self.assertEqual(report["distributions"]["A"]["cost_usd_micros"], {"p50": 10, "p95": 10})
        self.assertEqual(report["distributions"]["A"]["corrections"], {"p50": 2, "p95": 2})
        self.assertEqual(report["distributions"]["A"]["quality_regression_micros"], {"p50": 0, "p95": 0})
        self.assertLess(report["benefit_metrics"]["C"]["total_context_bytes"], report["benefit_metrics"]["B"]["total_context_bytes"])
        self.assertTrue(all(item["status"] == "killed" for item in report["negative_control_results"]))
        self.assertEqual(report["authority_effect"], "none")
        self.assertEqual(report["m8_qualifying_contribution"], 0)
        self.assertEqual(result.record_digest, module.run_frozen_comparison(self.variants(), self.config(), self.executor).record_digest)

    def test_wrong_document_wrong_curve_unknown_as_zero_and_bad_units_fail_domain_oracle(self):
        module = self.module()
        defects = {
            "F24-001": ("source_document_id", "other-project-pump-catalog"),
            "F24-002": ("curve", [[0, 1], [100, 1]]),
            "F24-003": ("head", 0),
            "F24-004": ("flow_unit", "gallons/fortnight"),
            "F24-009": ("actual_model", "drifted-model@2"),
            "F24-010": ("tool_version", "unaccepted-tool@2"),
        }
        for case_id, (field, value) in defects.items():
            def bad(mode, case, attempt, *, _case=case_id, _field=field, _value=value):
                result = self.executor(mode, case, attempt)
                if mode == "C" and case["case_id"] == _case:
                    if _field in result["domain_result"]:
                        result["domain_result"][_field] = _value
                    else:
                        result[_field] = _value
                return result
            with self.subTest(case_id=case_id):
                report = module.run_frozen_comparison(self.variants(), self.config(), bad).to_dict()
                self.assertEqual(report["verdict"], "not_qualified")
                self.assertEqual(report["evaluation_outcome"], "fail")
                failed = [a for a in report["attempts"] if a["mode"] == "C" and a["case_id"] == case_id]
                self.assertEqual(failed[0]["oracle_status"], "fail")
                self.assertEqual(report["comparisons"]["B_to_C"], "fail")

    def test_missing_attempt_unknown_cost_and_budget_exhaustion_never_pass(self):
        module = self.module()
        def incomplete(mode, case, attempt):
            result = self.executor(mode, case, attempt)
            if mode == "B" and case["case_id"] == "F24-006":
                result["status"] = "infra_failure"
            if mode == "C" and case["case_id"] == "F24-007":
                result["cost_usd_micros"] = None
            if mode == "A" and case["case_id"] == "F24-008":
                result["input_tokens"] = None
            return result
        report = module.run_frozen_comparison(self.variants(), self.config(), incomplete).to_dict()
        self.assertEqual(report["verdict"], "not_qualified")
        self.assertEqual(report["gates"]["completeness"], "blocked")
        self.assertEqual(report["gates"]["budgets"], "fail")
        self.assertIsNone(report["totals"]["cost_usd_micros"])
        self.assertIsNone(report["totals"]["input_tokens"])

        too_small = self.config()
        too_small["max_attempts"] = 35
        blocked = module.run_frozen_comparison(self.variants(), too_small, self.executor).to_dict()
        self.assertEqual(blocked["verdict"], "not_qualified")
        self.assertEqual(blocked["evaluation_outcome"], "blocked")
        self.assertEqual(blocked["gates"]["budgets"], "blocked")

        disable_cost = self.config(); disable_cost["require_complete_cost"] = False
        with self.assertRaisesRegex(ContractError, "closed_object_required"):
            module.run_frozen_comparison(self.variants(), disable_cost, self.executor)

    def test_no_strict_benefit_cannot_qualify(self):
        module = self.module()
        def no_benefit(mode, case, attempt):
            result = self.executor(mode, case, attempt)
            for field in ("context_bytes", "unique_context_bytes", "reread_bytes", "preparation_cost_usd_micros", "update_cost_usd_micros", "corrections"):
                result[field] = self.executor("A", case, attempt)[field]
            return result
        report = module.run_frozen_comparison(self.variants(), self.config(), no_benefit).to_dict()
        self.assertEqual(report["gates"]["benefit"], "fail")
        self.assertEqual(report["verdict"], "not_qualified")

        def context_only(mode, case, attempt):
            result = self.executor(mode, case, attempt)
            result["reread_bytes"] = 200
            result["unique_context_bytes"] = result["context_bytes"] - 200
            return result
        report = module.run_frozen_comparison(self.variants(), self.config(), context_only).to_dict()
        self.assertEqual(report["gates"]["benefit"], "fail")

    def test_common_pin_drift_and_missing_baseline_fail_closed(self):
        module = self.module()
        variants = self.variants()
        variants["C"]["model"] = "different-model@2"
        with self.assertRaisesRegex(ContractError, "confounded_comparison"):
            module.run_frozen_comparison(variants, self.config(), self.executor)
        with self.assertRaisesRegex(ContractError, "baseline_required"):
            module.run_frozen_comparison(self.variants(), self.config(), self.executor, baseline=None)

    def test_impact_selector_runs_behavior_changes_and_skips_only_proven_doc_typo(self):
        module = self.module()
        def change(path, before, after):
            return {"path": path, "before_digest": hashlib.sha256(before.encode()).hexdigest(),
                    "after_digest": hashlib.sha256(after.encode()).hexdigest(), "before_text": before, "after_text": after}
        typo = module.select_behavior_impact([
            change("docs/operator.md", "Operator guidf.", "Operator guide.")
        ]).to_dict()
        self.assertEqual(typo["selection"], "deterministic_only")
        self.assertEqual(typo["affected_capabilities"], [])

        behavior = module.select_behavior_impact([
            change("prompts/system.md", "old", "new"),
            change("factory/contracts/result.json", "{}", "{\"type\":\"object\"}"),
        ]).to_dict()
        self.assertEqual(behavior["selection"], "paired_required")
        self.assertEqual(behavior["case_ids"], [f"F24-{n:03d}" for n in range(1, 13)])
        self.assertEqual(behavior["affected_capabilities"], ["prompt_behavior", "tool_result_handling"])

        unknown = module.select_behavior_impact([
            change("mystery.bin", "old", "new")
        ]).to_dict()
        self.assertEqual(unknown["selection"], "paired_required")
        self.assertIn("bounded_unknown_impact", unknown["reasons"])

        runtime = module.select_behavior_impact([
            change("factory/src/adaptive_factory/runtime.py", "typoo", "typo")
        ]).to_dict()
        self.assertEqual(runtime["selection"], "paired_required")

        forged = change("docs/operator.md", "bad", "bat"); forged["after_digest"] = "f" * 64
        with self.assertRaisesRegex(ContractError, "text_digest_mismatch"):
            module.select_behavior_impact([forged])

    def test_generic_comparator_profile_is_closed_and_bb_defaults_disabled(self):
        module = self.module()
        profile = module.native_comparator_profile()
        self.assertEqual(profile.profile_id, "factory-f24-f26-native-v1")
        self.assertEqual(profile.oracle_id, "factory-semantic-oracles-v1")
        bb = module.make_comparator_profile("bb-observation-v1", profile.suite, profile.baseline, profile.oracle_id)
        local = module.run_comparison(bb, self.variants(), self.config(), self.executor).to_dict()
        self.assertEqual(local["verdict"], "ready_for_external_qualification")
        self.assertEqual(local["external_qualification"]["status"], "not_run")
        self.assertFalse(local["production_qualified"])

    def test_candidate_never_emits_pass_and_forged_authority_is_rejected(self):
        module = self.module()
        report = module.run_frozen_comparison(self.variants(), self.config(), self.executor).to_dict()
        self.assertEqual(report["verdict"], "ready_for_external_qualification")
        self.assertNotEqual(report["verdict"], "pass")
        self.assertEqual(report["authority_effect"], "none")
        with self.assertRaisesRegex(ContractError, "external_authority_out_of_process"):
            module.run_frozen_comparison(self.variants(), self.config(), self.executor,
                                         authority={"forged": True, "verdict": "pass"})
        profile = module.native_comparator_profile()
        with self.assertRaisesRegex(ContractError, "unknown_oracle_id"):
            module.make_comparator_profile("bad", profile.suite, profile.baseline, "caller-lambda")

    def test_factory_and_cross_domain_results_reject_extra_fields(self):
        module = self.module()
        def extra(mode, case, attempt):
            result = self.executor(mode, case, attempt)
            if case["case_id"] in ("F24-005", "F24-009"):
                result["domain_result"]["candidate_extra"] = "smuggle"
            return result
        report = module.run_frozen_comparison(self.variants(), self.config(), extra).to_dict()
        self.assertEqual(report["verdict"], "not_qualified")
        self.assertEqual(report["evaluation_outcome"], "fail")


if __name__ == "__main__":
    unittest.main()
