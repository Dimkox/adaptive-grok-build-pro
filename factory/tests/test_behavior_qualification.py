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
    "cache_mode": "cold",
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
        }
        if case["case_id"] == "PS-002":
            result["flow"] = expected["flow_m3h"] / 3.6
            result["flow_unit"] = "l/s"
        if case["case_id"] == "PS-003":
            result["head"] = expected["head_m"] / 0.3048
            result["head_unit"] = "ft"
        return result

    def config(self):
        return {
            "schema_version": 1,
            "repetitions": 1,
            "max_attempts": 36,
            "max_total_latency_ms": 10_000,
            "max_total_input_tokens": 10_000,
            "max_total_cost_usd_micros": 1_000,
            "require_complete_cost": True,
            "minimum_quality_micros": 1_000_000,
            "maximum_quality_regression_micros": 0,
            "declared_variable_factors": ["representation", "backend"],
        }

    def test_frozen_corpus_has_exact_twelve_stable_pump_cases_and_baseline(self):
        module = self.module()
        suite = module.load_frozen_suite()
        baseline = module.load_immutable_baseline(suite)
        facts = suite.to_dict()
        self.assertEqual(len(facts["cases"]), 12)
        self.assertEqual([c["case_id"] for c in facts["cases"]], [f"PS-{n:03d}" for n in range(1, 13)])
        self.assertTrue(all(c["required"] and c["oracle"] == "pump-selector-oracle-v1" for c in facts["cases"]))
        self.assertIn("wrong_document", {tag for c in facts["cases"] for tag in c["negative_controls"]})
        self.assertIn("wrong_curve", {tag for c in facts["cases"] for tag in c["negative_controls"]})
        self.assertIn("unknown_not_zero", {tag for c in facts["cases"] for tag in c["negative_controls"]})
        self.assertIn("unit_conversion", {tag for c in facts["cases"] for tag in c["negative_controls"]})
        self.assertEqual(baseline.to_dict()["corpus_digest"], suite.record_digest)
        mutated = suite.to_dict()
        mutated["cases"][0]["expected"]["pump_model"] = "candidate-chosen-baseline"
        with self.assertRaisesRegex(ContractError, "corpus_digest_mismatch"):
            module.FrozenQualificationSuite.from_dict(mutated)

    def test_paired_a_b_c_passes_only_with_complete_common_inputs_and_budgets(self):
        module = self.module()
        result = module.run_frozen_comparison(self.variants(), self.config(), self.executor)
        report = result.to_dict()
        self.assertEqual(report["verdict"], "pass")
        self.assertEqual(report["case_ids"], [f"PS-{n:03d}" for n in range(1, 13)])
        self.assertEqual(len(report["attempts"]), 36)
        self.assertEqual(report["comparisons"], {"A_to_B": "pass", "B_to_C": "pass"})
        self.assertEqual(report["gates"], {
            "budgets": "pass", "completeness": "pass", "common_conditions": "pass", "quality": "pass"
        })
        self.assertEqual(report["authority_effect"], "none")
        self.assertEqual(report["m8_qualifying_contribution"], 0)
        self.assertEqual(result.record_digest, module.run_frozen_comparison(self.variants(), self.config(), self.executor).record_digest)

    def test_wrong_document_wrong_curve_unknown_as_zero_and_bad_units_fail_domain_oracle(self):
        module = self.module()
        defects = {
            "PS-004": ("source_document_id", "other-project-pump-catalog"),
            "PS-005": ("curve", [[0, 1], [100, 1]]),
            "PS-008": ("head", 0),
            "PS-002": ("flow_unit", "gallons/fortnight"),
            "PS-001": ("actual_model", "drifted-model@2"),
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
            if mode == "B" and case["case_id"] == "PS-006":
                result["status"] = "infra_failure"
            if mode == "C" and case["case_id"] == "PS-007":
                result["cost_usd_micros"] = None
            return result
        report = module.run_frozen_comparison(self.variants(), self.config(), incomplete).to_dict()
        self.assertEqual(report["verdict"], "blocked")
        self.assertEqual(report["gates"]["completeness"], "blocked")
        self.assertEqual(report["gates"]["budgets"], "blocked")
        self.assertIsNone(report["totals"]["cost_usd_micros"])
        self.assertEqual(report["totals"]["input_tokens"], 3_600)

        too_small = self.config()
        too_small["max_attempts"] = 35
        blocked = module.run_frozen_comparison(self.variants(), too_small, self.executor).to_dict()
        self.assertEqual(blocked["verdict"], "blocked")
        self.assertEqual(blocked["gates"]["budgets"], "blocked")

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
             "classification": "non_executable_typo"}
        ]).to_dict()
        self.assertEqual(typo["selection"], "deterministic_only")
        self.assertEqual(typo["affected_capabilities"], [])

        behavior = module.select_behavior_impact([
            {"path": "prompts/system.md", "before_digest": "4" * 64, "after_digest": "5" * 64,
             "classification": "prompt"},
            {"path": "factory/contracts/result.json", "before_digest": "6" * 64, "after_digest": "7" * 64,
             "classification": "result_policy"},
        ]).to_dict()
        self.assertEqual(behavior["selection"], "paired_required")
        self.assertEqual(behavior["case_ids"], [f"PS-{n:03d}" for n in range(1, 13)])
        self.assertEqual(behavior["affected_capabilities"], ["prompt_behavior", "tool_result_handling"])

        unknown = module.select_behavior_impact([
            {"path": "mystery.bin", "before_digest": "8" * 64, "after_digest": "9" * 64,
             "classification": "unknown"}
        ]).to_dict()
        self.assertEqual(unknown["selection"], "paired_required")
        self.assertIn("bounded_unknown_impact", unknown["reasons"])


if __name__ == "__main__":
    unittest.main()
