from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from adaptive_factory.landing_contracts import LandingEvaluationV1, landing_digest
from adaptive_factory.landing_coordinator import (
    LANDING_WRITER_ID,
    MAX_LANDING_ATTEMPTS,
    LandingCoordinator,
)
from adaptive_factory.landing_evaluation import DeterministicLandingEvaluator
from adaptive_factory.landing_renderer import (
    DeterministicLandingRenderer,
    ExactGitLandingWorkspace,
)
from factory.tests.test_landing_renderer import landing_spec, sealed_target


START = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)


class TickClock:
    def __init__(self):
        self.value = START

    def __call__(self):
        current = self.value
        self.value += timedelta(seconds=1)
        return current


class ScriptedEvaluator:
    evaluator_id = "hidden-landing-evaluator"
    identity_digest = landing_digest(
        "evaluator-identity", {"evaluator_id": evaluator_id, "version": "1.0.0"}
    )
    policy_digest = "8" * 64
    rubric_digest = "9" * 64

    def __init__(self, decisions):
        self.decisions = tuple(decisions)
        self.calls = 0

    def evaluate(self, attempt, spec, candidate):
        del spec
        decision, reasons = self.decisions[self.calls]
        self.calls += 1
        return LandingEvaluationV1.from_facts(
            {
                "schema_version": 1,
                "attempt_digest": attempt.attempt_digest,
                "candidate_head_sha": candidate.candidate_sha,
                "evaluator_id": self.evaluator_id,
                "context_digest": landing_digest(
                    "evaluator-context",
                    {
                        "attempt_digest": attempt.attempt_digest,
                        "candidate_tree": candidate.candidate_tree,
                    },
                ),
                "policy_digest": self.policy_digest,
                "rubric_digest": self.rubric_digest,
                "decision": decision,
                "reason_codes": list(reasons),
                "requirement_digests": [],
                "finding_digests": [],
                "created_at": "2026-09-04T12:30:00Z",
            }
        )


def coordinator(target, scratch, evaluator, observed):
    return LandingCoordinator(
        ExactGitLandingWorkspace(
            target,
            scratch_root=Path(scratch),
            workspace_observer=observed.append,
        ),
        DeterministicLandingRenderer(),
        evaluator,
        clock=TickClock(),
    )


class LandingCoordinatorTests(unittest.TestCase):
    def test_independent_evaluator_selects_one_sealed_candidate_without_mutable_best_state(self):
        observed = []
        with sealed_target() as (target, _sha, _tree), tempfile.TemporaryDirectory() as scratch:
            result = coordinator(
                target,
                scratch,
                DeterministicLandingEvaluator(clock=TickClock()),
                observed,
            ).run(landing_spec(), profile_digest="7" * 64)

        self.assertEqual(result.disposition, "candidate_ready")
        self.assertIsNotNone(result.candidate)
        self.assertEqual(len(result.attempts), 1)
        self.assertEqual(len(result.evaluations), 1)
        attempt = result.attempts[0]
        evaluation = result.evaluations[0]
        self.assertNotEqual(evaluation.evaluator_id, LANDING_WRITER_ID)
        self.assertEqual(evaluation.attempt_digest, attempt.attempt_digest)
        self.assertEqual(evaluation.candidate_head_sha, result.candidate.candidate_sha)
        self.assertEqual(evaluation.decision, "pass")
        self.assertFalse(hasattr(result, "best_candidate"))
        self.assertTrue(all(not path.exists() for path in observed))
        with self.assertRaises(FrozenInstanceError):
            result.disposition = "needs_human"

    def test_evaluator_rejects_tampered_generated_cta(self):
        observed = []
        spec = landing_spec()
        evaluator = DeterministicLandingEvaluator(clock=TickClock())
        with sealed_target() as (target, _sha, _tree), tempfile.TemporaryDirectory() as scratch:
            result = coordinator(target, scratch, evaluator, observed).run(
                spec, profile_digest="7" * 64
            )
        candidate = result.candidate
        self.assertIsNotNone(candidate)
        tampered = replace(
            candidate,
            index_html=candidate.index_html.replace(
                b'class="l5-action" href="/roadmap.html"',
                b'class="l5-action" href="/\\\\attacker.example/collect"',
                1,
            ),
        )

        evaluation = evaluator.evaluate(result.attempts[-1], spec, tampered)

        self.assertEqual("needs_human", evaluation.decision)
        self.assertIn("active_content", evaluation.reason_codes)

    def test_three_repairs_stop_needs_human_with_fresh_base_and_exact_prior_chain(self):
        observed = []
        evaluator = ScriptedEvaluator(
            (
                ("repair", ("copy_density",)),
                ("repair", ("missing_required_section",)),
                ("repair", ("copy_density",)),
            )
        )
        with sealed_target() as (target, _sha, _tree), tempfile.TemporaryDirectory() as scratch:
            result = coordinator(target, scratch, evaluator, observed).run(
                landing_spec(), profile_digest="7" * 64
            )

        self.assertEqual(MAX_LANDING_ATTEMPTS, 3)
        self.assertEqual(result.disposition, "needs_human")
        self.assertIsNone(result.candidate)
        self.assertEqual([item.ordinal for item in result.attempts], [1, 2, 3])
        self.assertEqual(
            [item.prior_attempt_digest for item in result.attempts],
            [None, result.attempts[0].attempt_digest, result.attempts[1].attempt_digest],
        )
        self.assertEqual(len(observed), 3)
        self.assertEqual(len(set(observed)), 3)
        self.assertTrue(all(not path.exists() for path in observed))
        self.assertEqual(len({item.exact_base_sha for item in result.attempts}), 1)
        self.assertEqual(len({item.exact_head_sha for item in result.attempts}), 3)

    def test_repeated_repair_reason_fails_closed_without_a_third_attempt(self):
        observed = []
        evaluator = ScriptedEvaluator(
            (
                ("repair", ("copy_density",)),
                ("repair", ("copy_density",)),
            )
        )
        with sealed_target() as (target, _sha, _tree), tempfile.TemporaryDirectory() as scratch:
            result = coordinator(target, scratch, evaluator, observed).run(
                landing_spec(), profile_digest="7" * 64
            )
        self.assertEqual(result.disposition, "needs_human")
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(len(result.evaluations), 2)
        self.assertEqual(len(observed), 2)

    def test_unknown_repair_code_and_writer_evaluator_identity_fail_closed(self):
        cases = (
            ScriptedEvaluator((("repair", ("untrusted_instruction",)),)),
            ScriptedEvaluator((("pass", ()),)),
        )
        cases[1].evaluator_id = LANDING_WRITER_ID
        for evaluator in cases:
            observed = []
            with self.subTest(evaluator_id=evaluator.evaluator_id), sealed_target() as (
                target,
                _sha,
                _tree,
            ), tempfile.TemporaryDirectory() as scratch:
                result = coordinator(target, scratch, evaluator, observed).run(
                    landing_spec(), profile_digest="7" * 64
                )
            self.assertEqual(result.disposition, "needs_human")
            self.assertIsNone(result.candidate)
            self.assertEqual(len(result.attempts), 1)


if __name__ == "__main__":
    unittest.main()
