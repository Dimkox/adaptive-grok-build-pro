import importlib
import importlib.util
import unittest
from copy import deepcopy

from adaptive_factory.contracts import ContractError


COMMON_PINS = {
    "repository_snapshot": "1" * 40,
    "model": "fixture-model@1",
    "tools_digest": "2" * 64,
    "policy_digest": "3" * 64,
    "oracle_version": "pump-selector-oracle-v1",
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
            "decision": expected["decision"],
            "source_document_id": expected["source_document_id"],
            "pump_model": expected["pump_model"],
            "flow": expected["flow_m3h"],
            "flow_unit": "m3/h",
            "head": expected["head_m"],
            "head_unit": "m",
            "curve": deepcopy(expected["curve"]),
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
        if case["case_id"] == "F24-004":
            result["flow"] = expected["flow_m3h"] / 3.6
            result["flow_unit"] = "l/s"
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
            "benefit_metric": "total_context_bytes",
        }

    def test_frozen_corpus_has_exact_four_pump_four_factory_four_cross_cases_and_baseline(self):
        module = self.module()
        suite = module.load_frozen_suite()
        baseline = module.load_immutable_baseline(suite)
        facts = suite.to_dict()
        self.assertEqual(len(facts["cases"]), 12)
        self.assertEqual([c["case_id"] for c in facts["cases"]], [f"F24-{n:03d}" for n in range(1, 13)])
        self.assertEqual([c["domain"] for c in facts["cases"]], ["pump_selector"]*4+["factory"]*4+["cross_component"]*4)
        self.assertTrue(all(c["required"] and not c["optional"] and c["oracle"] == "pump-selector-oracle-v1" for c in facts["cases"]))
        controls = {control["control_id"] for c in facts["cases"] for control in c["negative_controls"]}
        self.assertTrue({"wrong_document","wrong_curve","unknown_to_zero","unsupported_units","unknown_tokens"} <= controls)
        self.assertTrue(all(c["forbidden_outcomes"] and c["isolation"]["external_writes"] == "forbidden" for c in facts["cases"]))
        self.assertEqual(baseline.to_dict()["corpus_digest"], suite.record_digest)
        self.assertEqual(module.ACCEPTED_CORPUS_DIGEST, "384c86fa02b5e570c353f0423eac956119c45142699e0d9a2dab3114f11d9f1b")
        self.assertEqual(module.ACCEPTED_BASELINE_DIGEST, "de100d45be16ed381b2a8e8aa2ad2e111dff56c144df59d0a8f65bd2a13622b4")
        with self.assertRaisesRegex(ContractError, "corpus_digest_mismatch"):
            module.load_frozen_suite(accepted_digest="0" * 64)
        mutated = suite.to_dict()
        mutated["cases"][0]["expected"]["pump_model"] = "candidate-chosen-baseline"
        with self.assertRaisesRegex(ContractError, "corpus_digest_mismatch"):
            module.FrozenQualificationSuite.from_dict(mutated)
        changed_baseline = baseline.to_dict(); changed_baseline["accepted_by"] = "candidate"
        with self.assertRaisesRegex(ContractError, "baseline_digest_mismatch"):
            module.ImmutableQualificationBaseline.from_dict(changed_baseline, suite)

    def test_paired_a_b_c_passes_only_with_complete_common_inputs_and_budgets(self):
        module = self.module()
        result = module.run_frozen_comparison(self.variants(), self.config(), self.executor)
        report = result.to_dict()
        self.assertEqual(report["verdict"], "pass")
        self.assertEqual(report["case_ids"], [f"F24-{n:03d}" for n in range(1, 13)])
        self.assertEqual(len(report["attempts"]), 36)
        self.assertEqual(report["comparisons"], {"A_to_B": "pass", "B_to_C": "pass"})
        self.assertEqual(report["gates"], {
            "benefit": "pass", "budgets": "pass", "completeness": "pass", "common_conditions": "pass", "negative_controls": "pass", "quality": "pass"
        })
        self.assertEqual(report["distributions"]["A"]["latency_ms"], {"p50": 75, "p95": 75})
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
                    result[_field] = _value
                return result
            with self.subTest(case_id=case_id):
                report = module.run_frozen_comparison(self.variants(), self.config(), bad).to_dict()
                self.assertEqual(report["verdict"], "fail")
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
        self.assertEqual(report["verdict"], "fail")
        self.assertEqual(report["gates"]["completeness"], "blocked")
        self.assertEqual(report["gates"]["budgets"], "fail")
        self.assertIsNone(report["totals"]["cost_usd_micros"])
        self.assertIsNone(report["totals"]["input_tokens"])

        too_small = self.config()
        too_small["max_attempts"] = 35
        blocked = module.run_frozen_comparison(self.variants(), too_small, self.executor).to_dict()
        self.assertEqual(blocked["verdict"], "blocked")
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
        self.assertEqual(report["verdict"], "fail")

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
        typo = module.select_behavior_impact([
            {"path": "docs/operator.md", "before_digest": "4" * 64, "after_digest": "5" * 64,
             "before_text": "Operator guidf.", "after_text": "Operator guide."}
        ]).to_dict()
        self.assertEqual(typo["selection"], "deterministic_only")
        self.assertEqual(typo["affected_capabilities"], [])

        behavior = module.select_behavior_impact([
            {"path": "prompts/system.md", "before_digest": "4" * 64, "after_digest": "5" * 64,
             "before_text": "old", "after_text": "new"},
            {"path": "factory/contracts/result.json", "before_digest": "6" * 64, "after_digest": "7" * 64,
             "before_text": "{}", "after_text": "{\"type\":\"object\"}"},
        ]).to_dict()
        self.assertEqual(behavior["selection"], "paired_required")
        self.assertEqual(behavior["case_ids"], [f"F24-{n:03d}" for n in range(1, 13)])
        self.assertEqual(behavior["affected_capabilities"], ["prompt_behavior", "tool_result_handling"])

        unknown = module.select_behavior_impact([
            {"path": "mystery.bin", "before_digest": "8" * 64, "after_digest": "9" * 64,
             "before_text": "old", "after_text": "new"}
        ]).to_dict()
        self.assertEqual(unknown["selection"], "paired_required")
        self.assertIn("bounded_unknown_impact", unknown["reasons"])

        runtime = module.select_behavior_impact([
            {"path": "factory/src/adaptive_factory/runtime.py", "before_digest": "a" * 64, "after_digest": "b" * 64,
             "before_text": "typoo", "after_text": "typo"}
        ]).to_dict()
        self.assertEqual(runtime["selection"], "paired_required")


if __name__ == "__main__":
    unittest.main()
