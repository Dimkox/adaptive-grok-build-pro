import unittest

from adaptive_factory.semantic_adjudication import adjudicate
from adaptive_factory.semantic_contracts import SemanticCoverageV1, SemanticFindingV1, SemanticSubjectV1
from adaptive_factory.semantic_repair import plan_repair
from .test_semantic_contracts import coverage, finding, subject


RISK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def repair_case(**subject_changes):
    root = SemanticSubjectV1.from_dict(subject(**subject_changes))
    entries = coverage(root.digest)["entries"]
    entries[0] = {**entries[0], "status": "unproven", "evidence_refs": []}
    finding_value = SemanticFindingV1.from_dict(finding(root.digest))
    coverage_value = SemanticCoverageV1.from_dict(coverage(root.digest, entries=entries))
    verdict = adjudicate(root, (finding_value,), (coverage_value,))
    return root, finding_value, verdict


def policy_args(root, **changes):
    values = {
        "requested_cycle": 1,
        "writer_id": root.original_writer_id,
        "context_digest": "b" * 64,
        "prior_context_digests": (),
        "prior_finding_identity_digests": (),
        "expected_base_sha": root.exact_base_sha,
        "expected_architecture_digest": root.architecture_digest,
        "expected_authority_digest": root.authority_digest,
        "baseline_risk_level": root.risk_level,
        "budget_remaining_units": 1,
        "deadline_remaining_seconds": 1,
    }
    values.update(changes)
    return values


class SemanticRepairTests(unittest.TestCase):
    def test_cycles_one_through_three_keep_original_writer_and_fresh_context(self):
        root, finding_value, verdict = repair_case()
        prior_contexts = []
        for cycle, context in ((1, "b" * 64), (2, "c" * 64), (3, "d" * 64)):
            decision = plan_repair(
                root,
                verdict,
                **policy_args(
                    root,
                    requested_cycle=cycle,
                    context_digest=context,
                    prior_context_digests=tuple(prior_contexts),
                ),
            )
            self.assertEqual(decision.decision, "repair")
            self.assertEqual(decision.reason, "repair_allowed")
            self.assertEqual(decision.directive.cycle, cycle)
            self.assertEqual(decision.directive.writer_id, root.original_writer_id)
            self.assertEqual(decision.directive.context_digest, context)
            self.assertEqual(decision.directive.finding_identity_digests, (finding_value.identity_digest,))
            decision.directive.validate_for(root, verdict)
            prior_contexts.append(context)

    def test_fourth_cycle_and_cycle_zero_are_hard_needs_human(self):
        root, _, verdict = repair_case()
        for cycle in (0, 4):
            with self.subTest(cycle=cycle):
                decision = plan_repair(root, verdict, **policy_args(root, requested_cycle=cycle))
                self.assertEqual((decision.decision, decision.reason, decision.directive), ("needs_human", "repair_cycle_out_of_bounds", None))

    def test_recurrence_uses_typed_identity_when_wording_changes(self):
        root, original, _ = repair_case()
        changed_words = SemanticFindingV1.from_dict(
            finding(
                root.digest,
                finding_id="finding-2",
                message="The prose changed but the typed defect did not.",
                evidence_refs=["artifact:rephrased"],
                reproduction="Different narrative.",
            )
        )
        entries = coverage(root.digest)["entries"]
        entries[0] = {**entries[0], "status": "unproven", "evidence_refs": []}
        verdict = adjudicate(
            root,
            (changed_words,),
            (SemanticCoverageV1.from_dict(coverage(root.digest, entries=entries)),),
        )
        self.assertEqual(changed_words.identity_digest, original.identity_digest)
        decision = plan_repair(
            root,
            verdict,
            **policy_args(root, requested_cycle=2, prior_finding_identity_digests=(original.identity_digest,)),
        )
        self.assertEqual((decision.decision, decision.reason), ("needs_human", "finding_recurrence"))

    def test_risk_diff_architecture_authority_base_budget_deadline_and_writer_escalate(self):
        cases = {
            "risk_increased": ({"risk_level": "high"}, {"baseline_risk_level": "medium"}),
            "diff_limit_exceeded": ({"diff_lines": 101}, {}),
            "architecture_changed": ({}, {"expected_architecture_digest": "0" * 64}),
            "authority_changed": ({}, {"expected_authority_digest": "0" * 64}),
            "base_changed": ({}, {"expected_base_sha": "0" * 40}),
            "budget_exhausted": ({}, {"budget_remaining_units": 0}),
            "deadline_exhausted": ({}, {"deadline_remaining_seconds": 0}),
            "original_writer_mismatch": ({}, {"writer_id": "writer-2"}),
        }
        for reason, (subject_changes, argument_changes) in cases.items():
            root, _, verdict = repair_case(**subject_changes)
            with self.subTest(reason=reason):
                decision = plan_repair(root, verdict, **policy_args(root, **argument_changes))
                self.assertEqual((decision.decision, decision.reason, decision.directive), ("needs_human", reason, None))

    def test_reused_original_or_prior_context_escalates(self):
        root, _, verdict = repair_case()
        cases = (
            (root.original_writer_context_digest, ()),
            ("b" * 64, ("b" * 64,)),
        )
        for context, prior in cases:
            with self.subTest(context=context):
                decision = plan_repair(
                    root,
                    verdict,
                    **policy_args(root, context_digest=context, prior_context_digests=prior),
                )
                self.assertEqual((decision.decision, decision.reason), ("needs_human", "context_not_fresh"))

    def test_stale_verdict_and_nonrepair_decisions_do_not_create_directives(self):
        root, _, verdict = repair_case()
        mutated = SemanticSubjectV1.from_dict(subject(diff_digest="0" * 64))
        stale = plan_repair(mutated, verdict, **policy_args(mutated))
        self.assertEqual((stale.decision, stale.reason), ("needs_human", "stale_semantic_evidence"))

        passing_coverage = SemanticCoverageV1.from_dict(coverage(root.digest))
        passing = adjudicate(root, (), (passing_coverage,))
        not_repair = plan_repair(root, passing, **policy_args(root))
        self.assertEqual((not_repair.decision, not_repair.reason), ("needs_human", "verdict_not_repair"))

    def test_policy_result_is_deterministic_and_has_no_runtime_mutation_api(self):
        root, _, verdict = repair_case()
        first = plan_repair(root, verdict, **policy_args(root))
        second = plan_repair(root, verdict, **policy_args(root))
        self.assertEqual(first, second)
        self.assertFalse(hasattr(first, "apply"))
        self.assertFalse(hasattr(first, "transition"))


if __name__ == "__main__":
    unittest.main()
