"""Issue #202: declared expectation sets must be provably satisfiable at plan time.

A controller- or analyst-authored criterion can name a *set* of expected
outcomes ("after the flip the verifier reddens exactly {key-A, key-B}"). Nothing
checked whether each declared member is achievable, so an unreachable member was
only discovered when the implementer measured reality and had to improvise a
weaker rule. These tests pin the third door: the recorder's own declaration must
either carry a per-member liveness proof or be worded as a falsifiable upper
bound, and the check fires while the specification is still a plan.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

import adaptive_grok.spec as SPEC  # noqa: E402
from adaptive_grok.spec import (  # noqa: E402
    SpecError,
    dump_canonical_spec,
    expectation_set_findings,
    load_schema,
    load_spec,
    validate_spec,
)

CHANGE_ID = "20260925-expectation-set-satisfiability-test"
LIVE_MEMBER = "css-link-count"
DEAD_MEMBER = "frozen-plan-text"
ALT_MEMBER = "generated-plan-text"
MODULE = Path(__file__).relative_to(ROOT).as_posix()
# The probes below resolve to executable mutation/observe/undo fixtures. The
# dead member intentionally has no probe because no detector path produces it.
LIVE_PROBE = {"test": f"{MODULE}::ExpectationSetProbeTests::test_liveness_probe_css_link_count"}
ALT_PROBE = {"test": f"{MODULE}::ExpectationSetProbeTests::test_liveness_probe_generated_plan_text"}
SHARED_PROBE = {
    "test": f"{MODULE}::ExpectationSetProbeTests::test_liveness_probe_css_link_count_and_generated_plan_text"
}


def spec_with(collection: str, statement: str, evidence: list[dict[str, str]]) -> dict:
    """Return a gate-valid v2 spec whose only criterion of ``collection`` is declared."""
    prefix = {"acceptance_criteria": "AC", "invariants": "INV", "forbidden_outcomes": "FORBID"}[collection]
    document = {
        "schema_version": 2,
        "change_id": CHANGE_ID,
        "objective": {
            "id": "OBJ-001",
            "statement": "Reject a declared expectation set that contains an unreachable member",
            "success_metric": "expectation_set_liveness_findings",
            "target": "dead_member_rejected_at_plan_time",
        },
        "risk": {"tier": "green", "domains": ["generic"]},
        "acceptance_criteria": [],
        "invariants": [],
        "forbidden_outcomes": [],
        "contracts": {"openapi": [], "json_schema": [], "events": []},
        "observability": [{"id": "SIG-001", "metric": "expectation_set_finding_count", "proves": ["OBJ-001"]}],
        "rollback": {"strategy": "forward_fix", "maximum_steps": 1},
        "approvals": {"required_scopes": []},
    }
    document[collection] = [{"id": f"{prefix}-001", "statement": statement, "evidence": evidence}]
    return document


def exact_statement() -> str:
    return (
        f"After the config flip the historical verifier reddens exactly {{{LIVE_MEMBER}, {DEAD_MEMBER}}}; "
        "the comparison is a literal set equality."
    )


def validate_source_fixture(statement: str, evidence: list[dict[str, str]], source: str) -> list[str]:
    """Validate one criterion against a real repository-contained test source."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        test_path = root / "tests" / "probe.py"
        test_path.parent.mkdir(parents=True)
        test_path.write_text(source, encoding="utf-8")
        package = root / "engineering" / "changes" / CHANGE_ID
        package.mkdir(parents=True)
        path = package / "change-spec.yaml"
        path.write_text(
            dump_canonical_spec(spec_with("acceptance_criteria", statement, evidence)),
            encoding="utf-8",
        )
        return validate_spec(root, path, gate=True)


class ExpectationSetProbeTests(unittest.TestCase):
    """Executable mutation/observe/undo fixtures referenced by exact-set specs."""

    @staticmethod
    def _observe(state: dict[str, bool]) -> set[str]:
        observed: set[str] = set()
        if state["css_changed"]:
            observed.add(LIVE_MEMBER)
        if state["generated_plan_changed"]:
            observed.add(ALT_MEMBER)
        return observed

    def test_liveness_probe_css_link_count(self) -> None:
        state = {"css_changed": False, "generated_plan_changed": False}
        SPEC.exercise_expectation_member(
            "css-link-count",
            observe=lambda: self._observe(state),
            mutate=lambda: state.__setitem__("css_changed", True),
            undo=lambda: state.__setitem__("css_changed", False),
        )
        document = spec_with("acceptance_criteria", f"The verifier reddens exactly {{{LIVE_MEMBER}}}.", [LIVE_PROBE])
        self.assertEqual(expectation_set_findings(document, root=ROOT), [])
        self.assertTrue(validate_spec(document, gate=True, root=ROOT)["ok"])

    def test_liveness_probe_generated_plan_text(self) -> None:
        state = {"css_changed": False, "generated_plan_changed": False}
        SPEC.exercise_expectation_member(
            "generated-plan-text",
            observe=lambda: self._observe(state),
            mutate=lambda: state.__setitem__("generated_plan_changed", True),
            undo=lambda: state.__setitem__("generated_plan_changed", False),
        )

    def test_liveness_probe_css_link_count_and_generated_plan_text(self) -> None:
        state = {"css_changed": False, "generated_plan_changed": False}
        SPEC.exercise_expectation_member(
            "css-link-count",
            observe=lambda: self._observe(state),
            mutate=lambda: state.__setitem__("css_changed", True),
            undo=lambda: state.__setitem__("css_changed", False),
        )
        SPEC.exercise_expectation_member(
            "generated-plan-text",
            observe=lambda: self._observe(state),
            mutate=lambda: state.__setitem__("generated_plan_changed", True),
            undo=lambda: state.__setitem__("generated_plan_changed", False),
        )


class ExpectationSetTests(unittest.TestCase):
    def test_baseline_spec_without_a_declared_set_is_valid(self) -> None:
        document = spec_with("acceptance_criteria", "The verifier reports the cutover state once.", [LIVE_PROBE])
        self.assertTrue(validate_spec(document, gate=True)["ok"])
        self.assertEqual(expectation_set_findings(document), [])

    def test_dead_member_of_an_exact_set_is_rejected_and_named(self) -> None:
        """Primary evidence: the unreachable member is refused with a precise finding."""
        document = spec_with("acceptance_criteria", exact_statement(), [LIVE_PROBE])
        findings = expectation_set_findings(document, root=ROOT)
        self.assertEqual(len(findings), 1, findings)
        finding = findings[0]
        self.assertIn("AC-001", finding)
        self.assertIn(repr(DEAD_MEMBER), finding)
        self.assertNotIn(repr(LIVE_MEMBER), finding)
        self.assertIn("executable mutation/undo probe", finding)
        self.assertIn("upper bound", finding)
        with self.assertRaises(SpecError) as raised:
            validate_spec(document, gate=True, root=ROOT)
        self.assertEqual(raised.exception.code, "incomplete")
        self.assertIn(repr(DEAD_MEMBER), str(raised.exception))

    def test_the_obligation_holds_while_the_spec_is_only_a_draft(self) -> None:
        document = spec_with("acceptance_criteria", exact_statement(), [LIVE_PROBE])
        with self.assertRaises(SpecError) as raised:
            validate_spec(document, gate=False, root=ROOT)
        self.assertIn(repr(DEAD_MEMBER), str(raised.exception))

    def test_every_member_with_a_probe_is_accepted(self) -> None:
        statement = f"Reds exactly {{{LIVE_MEMBER}, {ALT_MEMBER}}}."
        document = spec_with("acceptance_criteria", statement, [LIVE_PROBE, ALT_PROBE])
        self.assertEqual(expectation_set_findings(document, root=ROOT), [])
        self.assertTrue(validate_spec(document, gate=True, root=ROOT)["ok"])

    def test_one_probe_may_cover_several_members(self) -> None:
        statement = f"Reds exactly {{{LIVE_MEMBER}, {ALT_MEMBER}}}."
        self.assertEqual(
            expectation_set_findings(spec_with("acceptance_criteria", statement, [SHARED_PROBE]), root=ROOT),
            [],
        )
        self.assertEqual(len(expectation_set_findings(spec_with("acceptance_criteria", statement, []))), 2)

    def test_nonexistent_selector_cannot_prove_a_member(self) -> None:
        statement = f"Reds exactly {{{LIVE_MEMBER}}}."
        evidence = [{"test": "tests/probe.py::Probe::test_css_link_count"}]
        errors = validate_source_fixture(
            statement,
            evidence,
            "import unittest\n\nclass Probe(unittest.TestCase):\n    def test_another_selector(self):\n        pass\n",
        )
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("executable mutation/undo probe", errors[0])

    def test_selector_without_the_probe_helper_cannot_prove_a_member(self) -> None:
        statement = f"Reds exactly {{{LIVE_MEMBER}}}."
        evidence = [{"test": "tests/probe.py::Probe::test_css_link_count"}]
        errors = validate_source_fixture(
            statement,
            evidence,
            "import unittest\n\nclass Probe(unittest.TestCase):\n    def test_css_link_count(self):\n        pass\n",
        )
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("executable mutation/undo probe", errors[0])

    def test_probe_helper_must_name_the_same_literal_member(self) -> None:
        statement = f"Reds exactly {{{LIVE_MEMBER}}}."
        evidence = [{"test": "tests/probe.py::Probe::test_css_link_count"}]
        source = """\
import unittest
from adaptive_grok.spec import exercise_expectation_member

class Probe(unittest.TestCase):
    def test_css_link_count(self):
        exercise_expectation_member(
            "another-member", observe=lambda: set(), mutate=lambda: None, undo=lambda: None
        )
"""
        errors = validate_source_fixture(statement, evidence, source)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("executable mutation/undo probe", errors[0])

    def test_local_pass_only_helper_lookalike_cannot_prove_a_member(self) -> None:
        statement = f"Reds exactly {{{LIVE_MEMBER}}}."
        evidence = [{"test": "tests/probe.py::Probe::test_css_link_count"}]
        source = f"""\
import unittest

def exercise_expectation_member(*args, **kwargs):
    pass

class Probe(unittest.TestCase):
    def test_css_link_count(self):
        exercise_expectation_member(
            "{LIVE_MEMBER}", observe=lambda: set(), mutate=lambda: None, undo=lambda: None
        )
"""
        errors = validate_source_fixture(statement, evidence, source)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("executable mutation/undo probe", errors[0])

    def test_trusted_helper_import_cannot_be_shadowed_by_a_lookalike(self) -> None:
        statement = f"Reds exactly {{{LIVE_MEMBER}}}."
        evidence = [{"test": "tests/probe.py::Probe::test_css_link_count"}]
        source = f"""\
import unittest
from adaptive_grok.spec import exercise_expectation_member

def pass_only(*args, **kwargs):
    pass

exercise_expectation_member = pass_only

class Probe(unittest.TestCase):
    def test_css_link_count(self):
        exercise_expectation_member(
            "{LIVE_MEMBER}", observe=lambda: set(), mutate=lambda: None, undo=lambda: None
        )
"""
        errors = validate_source_fixture(statement, evidence, source)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("executable mutation/undo probe", errors[0])

    def test_helper_rebound_in_if_try_or_by_attribute_is_not_a_probe(self) -> None:
        """A lookalike assigned in if/try, or onto the module attribute, is not the helper."""
        statement = f"Reds exactly {{{LIVE_MEMBER}}}."
        evidence = [{"test": "tests/probe.py::Probe::test_css_link_count"}]
        call = f"""\
        exercise_expectation_member(
            "{LIVE_MEMBER}", observe=lambda: set(), mutate=lambda: None, undo=lambda: None
        )
"""
        attribute_call = f"""\
        spec.exercise_expectation_member(
            "{LIVE_MEMBER}", observe=lambda: set(), mutate=lambda: None, undo=lambda: None
        )
"""
        cases = {
            "if": f"""\
import unittest
from adaptive_grok.spec import exercise_expectation_member

def pass_only(*args, **kwargs):
    pass

if True:
    exercise_expectation_member = pass_only

class Probe(unittest.TestCase):
    def test_css_link_count(self):
{call}""",
            "try": f"""\
import unittest
from adaptive_grok.spec import exercise_expectation_member

def pass_only(*args, **kwargs):
    pass

try:
    exercise_expectation_member = pass_only
except Exception:
    pass

class Probe(unittest.TestCase):
    def test_css_link_count(self):
{call}""",
            "attribute": f"""\
import unittest
import adaptive_grok.spec as spec

def pass_only(*args, **kwargs):
    pass

spec.exercise_expectation_member = pass_only

class Probe(unittest.TestCase):
    def test_css_link_count(self):
{attribute_call}""",
            "attribute-in-method": f"""\
import unittest
import adaptive_grok.spec as spec

def pass_only(*args, **kwargs):
    pass

class Probe(unittest.TestCase):
    def test_css_link_count(self):
        spec.exercise_expectation_member = pass_only
{attribute_call}""",
        }
        for name, source in cases.items():
            with self.subTest(name=name):
                errors = validate_source_fixture(statement, evidence, source)
                self.assertEqual(len(errors), 1, errors)
                self.assertIn("executable mutation/undo probe", errors[0])

    def test_unexecuted_helper_call_is_not_a_probe(self) -> None:
        """Return, an unawaited async test, skip, and expectedFailure do not run the proof."""
        statement = f"Reds exactly {{{LIVE_MEMBER}}}."
        evidence = [{"test": "tests/probe.py::Probe::test_css_link_count"}]
        call = f"""\
        exercise_expectation_member(
            "{LIVE_MEMBER}", observe=lambda: set(), mutate=lambda: None, undo=lambda: None
        )
"""
        cases = {
            "after-return": f"""\
    def test_css_link_count(self):
        return
{call}""",
            "async": f"""\
    async def test_css_link_count(self):
{call}""",
            "skip": f"""\
    @unittest.skip("dead member")
    def test_css_link_count(self):
{call}""",
            "expected-failure": f"""\
    @unittest.expectedFailure
    def test_css_link_count(self):
{call}""",
        }
        for name, method in cases.items():
            with self.subTest(name=name):
                source = (
                    "import unittest\n"
                    "from adaptive_grok.spec import exercise_expectation_member\n\n"
                    "class Probe(unittest.TestCase):\n"
                    f"{method}"
                )
                errors = validate_source_fixture(statement, evidence, source)
                self.assertEqual(len(errors), 1, errors)
                self.assertIn("executable mutation/undo probe", errors[0])

    def test_exact_member_requires_observe_mutate_undo_callables(self) -> None:
        """AC-002: keyword-only observe/mutate/undo must be present and callable."""
        statement = f"Reds exactly {{{LIVE_MEMBER}}}."
        evidence = [{"test": "tests/probe.py::Probe::test_css_link_count"}]
        cases = {
            "positional": f"""\
        exercise_expectation_member(
            "{LIVE_MEMBER}", lambda: set(), lambda: None, lambda: None
        )
""",
            "constants": f"""\
        exercise_expectation_member(
            "{LIVE_MEMBER}", observe=1, mutate=2, undo=3
        )
""",
            "missing": f"""\
        exercise_expectation_member("{LIVE_MEMBER}")
""",
            "partial": f"""\
        exercise_expectation_member(
            "{LIVE_MEMBER}", observe=lambda: set(), mutate=lambda: None
        )
""",
        }
        for name, call in cases.items():
            with self.subTest(name=name):
                source = (
                    "import unittest\n"
                    "from adaptive_grok.spec import exercise_expectation_member\n\n"
                    "class Probe(unittest.TestCase):\n"
                    "    def test_css_link_count(self):\n"
                    f"{call}"
                )
                errors = validate_source_fixture(statement, evidence, source)
                self.assertEqual(len(errors), 1, errors)
                self.assertIn("executable mutation/undo probe", errors[0])

    def test_helper_call_hidden_in_an_uncalled_nested_function_is_not_a_probe(self) -> None:
        statement = f"Reds exactly {{{LIVE_MEMBER}}}."
        evidence = [{"test": "tests/probe.py::Probe::test_css_link_count"}]
        source = f"""\
import unittest
from adaptive_grok.spec import exercise_expectation_member

class Probe(unittest.TestCase):
    def test_css_link_count(self):
        def never_called():
            exercise_expectation_member(
                "{LIVE_MEMBER}", observe=lambda: set(), mutate=lambda: None, undo=lambda: None
            )
        pass
"""
        errors = validate_source_fixture(statement, evidence, source)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("executable mutation/undo probe", errors[0])

    def test_local_testcase_lookalike_is_not_an_executable_selector(self) -> None:
        statement = f"Reds exactly {{{LIVE_MEMBER}}}."
        evidence = [{"test": "tests/probe.py::Probe::test_css_link_count"}]
        source = f"""\
from adaptive_grok.spec import exercise_expectation_member

class TestCase:
    pass

class Probe(TestCase):
    def test_css_link_count(self):
        exercise_expectation_member(
            "{LIVE_MEMBER}", observe=lambda: set(), mutate=lambda: None, undo=lambda: None
        )
"""
        errors = validate_source_fixture(statement, evidence, source)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("executable mutation/undo probe", errors[0])

    def test_member_name_cannot_be_assembled_across_test_entries(self) -> None:
        statement = "Reds exactly {alpha-agents}."
        evidence = [
            {"test": "tests/test_change_spec.py::alpha"},
            {"test": ".agents/skills/adaptive-delivery/SKILL.md::agents"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "change-spec.yaml"
            path.write_text(
                dump_canonical_spec(spec_with("acceptance_criteria", statement, evidence)),
                encoding="utf-8",
            )
            errors = validate_spec(ROOT, path, gate=True)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("alpha-agents", errors[0])

    def test_short_members_in_an_exact_multi_member_set_are_not_placeholders(self) -> None:
        document = spec_with("acceptance_criteria", "Reds exactly {A, B}.", [{"receipt": "verification"}])
        findings = expectation_set_findings(document)
        self.assertEqual(len(findings), 2, findings)
        self.assertIn("'A'", findings[0])
        self.assertIn("'B'", findings[1])

    def test_exactness_cue_does_not_cross_a_sentence_boundary(self) -> None:
        statement = (
            "The retry count is exactly 2. "
            f"The contextual pair {{{LIVE_MEMBER}, {DEAD_MEMBER}}} is documented elsewhere."
        )
        document = spec_with("acceptance_criteria", statement, [{"receipt": "verification"}])
        self.assertEqual(expectation_set_findings(document), [])

    def test_plural_allowed_deviations_is_an_upper_bound_cue(self) -> None:
        statement = f"Observed allowed deviations are {{{LIVE_MEMBER}, {DEAD_MEMBER}}}."
        findings = expectation_set_findings(
            spec_with("acceptance_criteria", statement, [{"receipt": "verification"}])
        )
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("without asserting non-emptiness", findings[0])

    def test_probe_helper_executes_absent_present_restored_contract(self) -> None:
        helper = getattr(SPEC, "exercise_expectation_member", None)
        self.assertIsNotNone(helper, "the executable liveness helper is missing")
        state = {"active": False}

        def observe() -> set[str]:
            return {LIVE_MEMBER} if state["active"] else set()

        helper(
            LIVE_MEMBER,
            observe=observe,
            mutate=lambda: state.__setitem__("active", True),
            undo=lambda: state.__setitem__("active", False),
        )
        self.assertFalse(state["active"])

        with self.assertRaises(AssertionError):
            helper(LIVE_MEMBER, observe=lambda: set(), mutate=lambda: None, undo=lambda: None)

        state["active"] = True
        with self.assertRaises(AssertionError):
            helper(LIVE_MEMBER, observe=observe, mutate=lambda: None, undo=lambda: None)

        state["active"] = False
        with self.assertRaises(AssertionError):
            helper(
                LIVE_MEMBER,
                observe=observe,
                mutate=lambda: state.__setitem__("active", True),
                undo=lambda: None,
            )

    def test_non_test_evidence_never_proves_liveness(self) -> None:
        statement = f"Reds exactly {{{LIVE_MEMBER}}}."
        for evidence in (
            {"attestation": f"liveness:{LIVE_MEMBER}"},
            {"receipt": "verification"},
            {"production_signal": "SIG-001"},
        ):
            with self.subTest(evidence=evidence):
                findings = expectation_set_findings(spec_with("acceptance_criteria", statement, [evidence]))
                self.assertEqual(len(findings), 1, findings)
                self.assertIn(repr(LIVE_MEMBER), findings[0])

    def test_evidence_naming_another_member_is_not_a_proof(self) -> None:
        document = spec_with("acceptance_criteria", f"Reds exactly {{{DEAD_MEMBER}}}.", [LIVE_PROBE])
        findings = expectation_set_findings(document, root=ROOT)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn(repr(DEAD_MEMBER), findings[0])

    def test_invariants_and_forbidden_outcomes_are_covered(self) -> None:
        statement = f"Track B keys are exactly {{{LIVE_MEMBER}, {DEAD_MEMBER}}}."
        for collection, prefix in (("invariants", "INV"), ("forbidden_outcomes", "FORBID")):
            with self.subTest(collection=collection):
                findings = expectation_set_findings(spec_with(collection, statement, [LIVE_PROBE]), root=ROOT)
                self.assertEqual(len(findings), 1, findings)
                self.assertIn(f"{prefix}-001", findings[0])
                self.assertIn(repr(DEAD_MEMBER), findings[0])

    def test_upper_bound_without_non_emptiness_can_never_fail(self) -> None:
        statement = f"Observed reds are a subset of {{{LIVE_MEMBER}, {DEAD_MEMBER}}}."
        document = spec_with("acceptance_criteria", statement, [LIVE_PROBE])
        findings = expectation_set_findings(document, root=ROOT)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("AC-001", findings[0])
        self.assertIn("without asserting non-emptiness", findings[0])
        with self.assertRaises(SpecError):
            validate_spec(document, gate=True)

    def test_upper_bound_with_non_emptiness_is_accepted(self) -> None:
        statement = f"Observed reds are a non-empty subset of {{{LIVE_MEMBER}, {DEAD_MEMBER}}}."
        document = spec_with("acceptance_criteria", statement, [LIVE_PROBE])
        self.assertEqual(expectation_set_findings(document), [])
        self.assertTrue(validate_spec(document, gate=True)["ok"])

    def test_declaration_without_a_quantifier_imposes_no_obligation(self) -> None:
        statement = f"The pair {{{LIVE_MEMBER}, {DEAD_MEMBER}}} is documented in the brief."
        document = spec_with("acceptance_criteria", statement, [{"receipt": "verification"}])
        self.assertEqual(expectation_set_findings(document), [])

    def test_placeholders_counts_and_code_are_not_expectation_sets(self) -> None:
        for statement in (
            "The rollout flips exactly {0, 1} flags.",
            "The header is exactly {TITLE} and nothing more.",
            "The record is exactly {\"a\": 1} and the row is {X}.",
            "Nothing may redden: the expected set is exactly {}.",
            "The diff changes exactly index.html and content.css.",
        ):
            with self.subTest(statement=statement):
                findings = expectation_set_findings(
                    spec_with("acceptance_criteria", statement, [{"receipt": "verification"}])
                )
                self.assertEqual(findings, [], statement)

    def test_malformed_criteria_are_skipped_not_crashed(self) -> None:
        document = spec_with("acceptance_criteria", exact_statement(), [LIVE_PROBE])
        document["acceptance_criteria"].append("not-a-mapping")
        document["invariants"] = [{"id": "INV-001", "statement": None, "evidence": None}]
        document["forbidden_outcomes"] = [{"id": "FORBID-001", "statement": f"Reds exactly {{{LIVE_MEMBER}}}", "evidence": [{"test": 7}]}]
        findings = expectation_set_findings(document, root=ROOT)
        self.assertEqual(len(findings), 2, findings)
        self.assertIn("AC-001", findings[0])
        self.assertIn("FORBID-001", findings[1])

    def test_path_api_reports_the_finding_against_the_spec_file(self) -> None:
        document = spec_with("acceptance_criteria", exact_statement(), [LIVE_PROBE])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "engineering" / "changes" / CHANGE_ID
            package.mkdir(parents=True)
            (root / "tests").mkdir()
            (root / "tests" / "test_spec_expectation_sets.py").write_text(
                f"""\
import unittest
from adaptive_grok.spec import exercise_expectation_member

class ExpectationSetProbeTests(unittest.TestCase):
    def test_liveness_probe_css_link_count(self):
        state = {{"active": False}}
        exercise_expectation_member(
            "{LIVE_MEMBER}",
            observe=lambda: {{"{LIVE_MEMBER}"}} if state["active"] else set(),
            mutate=lambda: state.__setitem__("active", True),
            undo=lambda: state.__setitem__("active", False),
        )

    def test_liveness_probe_generated_plan_text(self):
        state = {{"active": False}}
        exercise_expectation_member(
            "{ALT_MEMBER}",
            observe=lambda: {{"{ALT_MEMBER}"}} if state["active"] else set(),
            mutate=lambda: state.__setitem__("active", True),
            undo=lambda: state.__setitem__("active", False),
        )
""",
                encoding="utf-8",
            )
            path = package / "change-spec.yaml"
            path.write_text(dump_canonical_spec(document), encoding="utf-8")
            errors = validate_spec(root, path, gate=True)
            self.assertEqual(len(errors), 1, errors)
            self.assertIn(str(path), errors[0])
            self.assertIn(repr(DEAD_MEMBER), errors[0])
            repaired = copy.deepcopy(document)
            repaired["acceptance_criteria"][0]["statement"] = (
                f"The verifier reddens exactly {{{LIVE_MEMBER}, {ALT_MEMBER}}}."
            )
            repaired["acceptance_criteria"][0]["evidence"] = [LIVE_PROBE, ALT_PROBE]
            path.write_text(dump_canonical_spec(repaired), encoding="utf-8")
            self.assertEqual(validate_spec(root, path, gate=True), [])
            self.assertEqual(load_spec(path, allow_legacy=False)["change_id"], CHANGE_ID)

    def test_baseline_and_current_validator_errors_match_for_every_baseline_package(self) -> None:
        """AC-005: compare full errors using the committed route base validator."""
        package = ROOT / "engineering" / "changes" / "20260925-reject-unsatisfiable-expectation-set-members-in-113055"
        route = json.loads((package / "route.json").read_text(encoding="utf-8"))
        base = route["base_commit"]
        source = subprocess.run(
            ["git", "show", f"{base}:.grok-stack/adaptive_grok/spec.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=True,
        ).stdout
        baseline = types.ModuleType("issue202_baseline_spec")
        baseline.__file__ = str(ROOT / ".grok-stack" / "adaptive_grok" / "spec.py")
        exec(compile(source, f"{base}:spec.py", "exec"), baseline.__dict__)  # noqa: S102  # nosec B102
        inventory = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", base, "--", "engineering/changes"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=True,
        ).stdout.splitlines()
        paths = [ROOT / rel for rel in inventory if rel.endswith("/change-spec.yaml")]
        self.assertGreater(len(paths), 90, "expected the committed baseline package inventory")
        for path in paths:
            with self.subTest(package=path.parent.name):
                self.assertEqual(
                    validate_spec(ROOT, path, gate=True),
                    baseline.validate_spec(ROOT, path, gate=True),
                )

    def test_criterion_shape_stays_inside_the_deployed_holdout_contract(self) -> None:
        """The obligation must not need a new spec field: the holdout freezes keys."""
        schema = load_schema()
        criterion_keys = set(schema["$defs"]["criterion"]["properties"])
        holdout = (ROOT / "trust-ci" / "holdout.example" / "change_spec_validate.py").read_text(encoding="utf-8")
        pinned = re.search(r'if set\(item\) != (\{[^{}]*"statement"[^{}]*\}):', holdout)
        self.assertIsNotNone(pinned, "the holdout no longer pins the criterion key set")
        holdout_keys = set(re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"', pinned.group(1)))
        self.assertEqual(criterion_keys, holdout_keys)


if __name__ == "__main__":
    unittest.main()
