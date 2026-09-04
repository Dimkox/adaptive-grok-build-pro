from copy import deepcopy
import itertools
import unittest

from adaptive_factory.contracts import ContractError
from adaptive_factory.semantic_adjudication import adjudicate
from adaptive_factory.semantic_contracts import SemanticCoverageV1, SemanticFindingV1, SemanticSubjectV1
from .test_semantic_contracts import coverage, finding, subject, validator


def parsed_subject(**changes):
    return SemanticSubjectV1.from_dict(subject(**changes))


def parsed_finding(root, **changes):
    return SemanticFindingV1.from_dict(finding(root.digest, **changes))


def parsed_coverage(root, **changes):
    return SemanticCoverageV1.from_dict(coverage(root.digest, **changes))


class SemanticAdjudicationTests(unittest.TestCase):
    def test_exact_evidenced_coverage_passes_without_state_authority(self):
        root = parsed_subject()
        verdict = adjudicate(root, (), (parsed_coverage(root),))
        self.assertEqual(verdict.decision, "pass")
        self.assertEqual(verdict.decision_source, "deterministic_adjudicator")
        self.assertEqual(verdict.residual_risk, "none")
        self.assertFalse(hasattr(verdict, "task_state"))
        self.assertFalse(hasattr(verdict, "transition"))

    def test_repairable_finding_and_unproven_coverage_request_repair(self):
        root = parsed_subject()
        entries = coverage(root.digest)["entries"]
        entries[0] = {**entries[0], "status": "unproven", "evidence_refs": []}
        verdict = adjudicate(root, (parsed_finding(root),), (parsed_coverage(root, entries=entries),))
        self.assertEqual(verdict.decision, "repair")
        self.assertEqual(verdict.residual_risk, "medium")

    def test_needs_human_precedes_repair_for_sensitive_or_unrepairable_findings(self):
        root = parsed_subject()
        for changes in (
            {"repairable": False},
            {"category": "security_boundary"},
            {"category": "authority_violation"},
            {"category": "contradiction"},
        ):
            with self.subTest(changes=changes):
                verdict = adjudicate(root, (parsed_finding(root, **changes),), (parsed_coverage(root),))
                self.assertEqual(verdict.decision, "needs_human")

    def test_duplicates_correlations_contradictions_and_unsupported_passes_are_exposed(self):
        root = parsed_subject()
        first = parsed_finding(root)
        duplicate = parsed_finding(
            root,
            finding_id="finding-2",
            message="Paraphrased same issue.",
            evidence_refs=["artifact:second"],
            validator=validator(validator_id="validator-2", context_digest="b" * 64),
        )
        correlated = parsed_finding(
            root,
            finding_id="finding-3",
            category="test_gap",
            rule_id="rule-test-gap",
            validator=validator(validator_id="validator-3", context_digest="c" * 64),
        )
        second_entries = deepcopy(coverage(root.digest)["entries"])
        second_entries[0] = {**second_entries[0], "status": "contradicted"}
        reports = (
            parsed_coverage(root),
            parsed_coverage(
                root,
                validator=validator(validator_id="validator-4", context_digest="4" * 64),
                entries=second_entries,
            ),
        )
        verdict = adjudicate(root, (first, duplicate, correlated), reports)
        key = "acceptance_criterion:AC-001"
        self.assertEqual(verdict.duplicate_identity_digests, (first.identity_digest,))
        self.assertEqual(verdict.correlated_requirement_keys, (key,))
        self.assertEqual(verdict.contradicted_requirement_keys, (key,))
        self.assertEqual(verdict.unsupported_pass_requirement_keys, (key,))
        self.assertEqual(verdict.decision, "needs_human")

    def test_adjudication_is_deterministic_under_input_permutations(self):
        root = parsed_subject()
        findings = (
            parsed_finding(root),
            parsed_finding(root, finding_id="finding-2", category="test_gap", rule_id="rule-test-gap"),
        )
        reports = (
            parsed_coverage(root),
            parsed_coverage(root, validator=validator(validator_id="validator-2", context_digest="b" * 64)),
        )
        digests = {
            adjudicate(root, finding_order, coverage_order).digest
            for finding_order in itertools.permutations(findings)
            for coverage_order in itertools.permutations(reports)
        }
        self.assertEqual(len(digests), 1)

    def test_empty_proven_evidence_is_an_unsupported_pass(self):
        root = parsed_subject()
        entries = coverage(root.digest)["entries"]
        entries[0] = {**entries[0], "evidence_refs": []}
        verdict = adjudicate(root, (), (parsed_coverage(root, entries=entries),))
        self.assertEqual(verdict.unsupported_pass_requirement_keys, ("acceptance_criterion:AC-001",))
        self.assertEqual(verdict.decision, "needs_human")

    def test_provider_decision_cannot_enter_adjudication_contract(self):
        root = parsed_subject()
        payload = coverage(root.digest)
        payload["decision"] = "pass"
        with self.assertRaisesRegex(ContractError, "unknown_fields"):
            SemanticCoverageV1.from_dict(payload)
        with self.assertRaises(TypeError):
            adjudicate(root, (), (parsed_coverage(root),), provider_decision="pass")

    def test_every_relevant_subject_mutation_invalidates_prior_evidence(self):
        original = parsed_subject()
        old_finding = parsed_finding(original)
        old_coverage = parsed_coverage(original)
        mutations = {
            "requirements": [
                {"kind": "acceptance_criterion", "requirement_id": "AC-002"},
                {"kind": "invariant", "requirement_id": "INV-001"},
            ],
            "exact_base_sha": "a" * 40,
            "exact_head_sha": "b" * 40,
            "spec_digest": "a" * 64,
            "architecture_digest": "b" * 64,
            "authority_digest": "c" * 64,
            "diff_digest": "d" * 64,
            "deterministic_evidence_digest": "e" * 64,
            "holdout_evidence_digest": "f" * 64,
            "review_evidence_digest": "0" * 64,
            "original_writer_id": "writer-2",
            "original_writer_context_digest": "b" * 64,
            "risk_level": "high",
            "diff_lines": 21,
            "diff_limit": 99,
        }
        for field, value in mutations.items():
            with self.subTest(field=field), self.assertRaisesRegex(ContractError, "stale_semantic_evidence"):
                adjudicate(parsed_subject(**{field: value}), (old_finding,), (old_coverage,))

    def test_coverage_is_required_and_validator_separation_is_rechecked(self):
        root = parsed_subject()
        with self.assertRaisesRegex(ContractError, "semantic_coverage_missing"):
            adjudicate(root, (), ())
        bad = parsed_coverage(root, validator=validator(validator_id="writer-1"))
        with self.assertRaisesRegex(ContractError, "validator_is_original_writer"):
            adjudicate(root, (), (bad,))


if __name__ == "__main__":
    unittest.main()
