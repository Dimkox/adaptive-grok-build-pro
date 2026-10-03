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
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

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
MODULE = Path(__file__).relative_to(ROOT).as_posix()
# The two probes below are the liveness proofs the rule demands: each declared
# member is named by the test evidence of the criterion that declares it.
LIVE_PROBE = {"test": f"{MODULE}::ExpectationSetProbeTests::test_liveness_probe_css_link_count"}
DEAD_PROBE = {"test": f"{MODULE}::ExpectationSetProbeTests::test_liveness_probe_frozen_plan_text"}


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


class ExpectationSetProbeTests(unittest.TestCase):
    """Per-member liveness fixtures referenced as evidence by the tests below."""

    def test_liveness_probe_css_link_count(self) -> None:
        document = spec_with("acceptance_criteria", f"The verifier reddens exactly {{{LIVE_MEMBER}}}.", [LIVE_PROBE])
        self.assertEqual(expectation_set_findings(document), [])
        self.assertTrue(validate_spec(document, gate=True)["ok"])

    def test_liveness_probe_frozen_plan_text(self) -> None:
        document = spec_with("acceptance_criteria", f"The verifier reddens exactly {{{DEAD_MEMBER}}}.", [DEAD_PROBE])
        self.assertEqual(expectation_set_findings(document), [])
        self.assertTrue(validate_spec(document, gate=True)["ok"])


class ExpectationSetTests(unittest.TestCase):
    def test_baseline_spec_without_a_declared_set_is_valid(self) -> None:
        document = spec_with("acceptance_criteria", "The verifier reports the cutover state once.", [LIVE_PROBE])
        self.assertTrue(validate_spec(document, gate=True)["ok"])
        self.assertEqual(expectation_set_findings(document), [])

    def test_dead_member_of_an_exact_set_is_rejected_and_named(self) -> None:
        """Primary evidence: the unreachable member is refused with a precise finding."""
        document = spec_with("acceptance_criteria", exact_statement(), [LIVE_PROBE])
        findings = expectation_set_findings(document)
        self.assertEqual(len(findings), 1, findings)
        finding = findings[0]
        self.assertIn("AC-001", finding)
        self.assertIn(repr(DEAD_MEMBER), finding)
        self.assertNotIn(repr(LIVE_MEMBER), finding)
        self.assertIn("liveness proof", finding)
        self.assertIn("upper bound", finding)
        with self.assertRaises(SpecError) as raised:
            validate_spec(document, gate=True)
        self.assertEqual(raised.exception.code, "incomplete")
        self.assertIn(repr(DEAD_MEMBER), str(raised.exception))

    def test_the_obligation_holds_while_the_spec_is_only_a_draft(self) -> None:
        document = spec_with("acceptance_criteria", exact_statement(), [LIVE_PROBE])
        with self.assertRaises(SpecError) as raised:
            validate_spec(document, gate=False)
        self.assertIn(repr(DEAD_MEMBER), str(raised.exception))

    def test_every_member_with_a_probe_is_accepted(self) -> None:
        document = spec_with("acceptance_criteria", exact_statement(), [LIVE_PROBE, DEAD_PROBE])
        self.assertEqual(expectation_set_findings(document), [])
        self.assertTrue(validate_spec(document, gate=True)["ok"])

    def test_dashed_member_is_named_by_an_underscored_probe(self) -> None:
        """Separator and case differences must not hide an otherwise real probe."""
        statement = f"Reds exactly {{{LIVE_MEMBER}, {DEAD_MEMBER}}}."
        document = spec_with(
            "acceptance_criteria",
            statement,
            [
                {"test": "tests/test_liveness_CSS_LINK_count.py"},
                {"test": "tests/test-liveness.frozen.plan.text.py"},
            ],
        )
        self.assertEqual(expectation_set_findings(document), [])

    def test_one_probe_may_cover_several_members(self) -> None:
        statement = f"Reds exactly {{{LIVE_MEMBER}, {DEAD_MEMBER}}}."
        shared = {"test": f"{MODULE}::ExpectationSetProbeTests::test_liveness_probe_css_link_count_and_frozen_plan_text"}
        self.assertEqual(expectation_set_findings(spec_with("acceptance_criteria", statement, [shared])), [])
        self.assertEqual(len(expectation_set_findings(spec_with("acceptance_criteria", statement, []))), 2)

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
        findings = expectation_set_findings(document)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn(repr(DEAD_MEMBER), findings[0])

    def test_invariants_and_forbidden_outcomes_are_covered(self) -> None:
        statement = f"Track B keys are exactly {{{LIVE_MEMBER}, {DEAD_MEMBER}}}."
        for collection, prefix in (("invariants", "INV"), ("forbidden_outcomes", "FORBID")):
            with self.subTest(collection=collection):
                findings = expectation_set_findings(spec_with(collection, statement, [LIVE_PROBE]))
                self.assertEqual(len(findings), 1, findings)
                self.assertIn(f"{prefix}-001", findings[0])
                self.assertIn(repr(DEAD_MEMBER), findings[0])

    def test_upper_bound_without_non_emptiness_can_never_fail(self) -> None:
        statement = f"Observed reds are a subset of {{{LIVE_MEMBER}, {DEAD_MEMBER}}}."
        document = spec_with("acceptance_criteria", statement, [LIVE_PROBE])
        findings = expectation_set_findings(document)
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
        findings = expectation_set_findings(document)
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
            (root / "tests" / "test_spec_expectation_sets.py").write_text("# evidence fixture\n", encoding="utf-8")
            path = package / "change-spec.yaml"
            path.write_text(dump_canonical_spec(document), encoding="utf-8")
            errors = validate_spec(root, path, gate=True)
            self.assertEqual(len(errors), 1, errors)
            self.assertIn(str(path), errors[0])
            self.assertIn(repr(DEAD_MEMBER), errors[0])
            repaired = copy.deepcopy(document)
            repaired["acceptance_criteria"][0]["evidence"] = [LIVE_PROBE, DEAD_PROBE]
            path.write_text(dump_canonical_spec(repaired), encoding="utf-8")
            self.assertEqual(validate_spec(root, path, gate=True), [])
            self.assertEqual(load_spec(path, allow_legacy=False)["change_id"], CHANGE_ID)

    def test_no_existing_package_declares_an_unsatisfiable_set(self) -> None:
        """The new obligation is additive: no historical package gains a finding."""
        checked = 0
        for path in sorted((ROOT / "engineering" / "changes").glob("*/change-spec.yaml")):
            try:
                document = load_spec(path, allow_legacy=True)
            except SpecError:
                continue
            if not isinstance(document, dict) or document.get("schema_version") != 2:
                continue
            with self.subTest(package=path.parent.name):
                self.assertEqual(expectation_set_findings(document), [])
            checked += 1
        self.assertGreater(checked, 80, "expected the historical packages to be readable")

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
