"""Issue #50: one bad character in the architecture model must be reported once, located.

Before this contour a trailing slash in a ``repository_paths`` entry was rejected with the
same unlocated "unsafe repository-relative path" verdict as a ``../`` escape, and the only way
to see it was a full root-suite run in which every ``load_architecture()`` consumer raised its
own copy. These tests pin the two properties that replaced that behaviour:

* the defect still fails closed - the model must never load with a bad declared path, and
* one cheap preflight reports it, naming document, line, entry and reason.
"""

from __future__ import annotations

import contextlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

from adaptive_grok.architecture import (  # noqa: E402
    RULE_PATH_FIELDS,
    ArchitectureError,
    _path_shape_problem,
    load_architecture,
    preflight_architecture,
)
from adaptive_grok.doctor import run_doctor  # noqa: E402

SYSTEM_RELATIVE = "architecture/system.yaml"
RULES_RELATIVE = "architecture/rules.yaml"

# The bad entry used throughout; it is a plausible directory-style path with one extra character.
BAD_ENTRY = "factory/runtime/"


def _system(repository_paths: list) -> dict:
    return {
        "schema_version": 1,
        "architecture_id": "ARCH-PREFLIGHT-TEST",
        "trust_domains": [
            {"id": "TD-LOCAL", "kind": "local_preflight", "owner": "engineering"}
        ],
        "data_classifications": [
            {
                "id": "DATA-INTERNAL",
                "classification": "internal",
                "tenant_scoped": False,
                "contains_secret": False,
            }
        ],
        "secret_classes": [],
        "signals": [{"id": "SIG-EDGE-FAILURE", "description": "edge failure"}],
        "contracts": [],
        "nodes": [
            {
                "id": "NODE-PREFLIGHT-A",
                "type": "local_component",
                "owner": "engineering",
                "trust_domain": "TD-LOCAL",
                "data_classification": "DATA-INTERNAL",
                "secrets": [],
                "runtime": {
                    "kind": "python_process",
                    "lifecycle": "on_demand",
                    "network": "none",
                    "evidence": "source_described",
                },
                "repository_paths": repository_paths,
                "public_contracts": [],
            },
            {
                "id": "NODE-PREFLIGHT-B",
                "type": "repository",
                "owner": "engineering",
                "trust_domain": "TD-LOCAL",
                "data_classification": "DATA-INTERNAL",
                "secrets": [],
                "runtime": {
                    "kind": "none",
                    "lifecycle": "none",
                    "network": "none",
                    "evidence": "source_described",
                },
                "repository_paths": [],
                "public_contracts": [],
            },
        ],
        "edges": [
            {
                "id": "EDGE-A-B",
                "from": "NODE-PREFLIGHT-A",
                "to": "NODE-PREFLIGHT-B",
                "type": "dependency",
                "protocol": "filesystem",
                "direction": "from_to",
                "authentication": "local_os",
                "network_policy": "no_network",
                "sync_or_async": "synchronous",
                "allowed_data": ["DATA-INTERNAL"],
                "failure_behavior": {
                    "mode": "fail_closed",
                    "timeout_ms": 1000,
                    "max_retries": 0,
                    "idempotency": "not_required",
                    "correlation_id": "not_required",
                    "terminal_action": "reject",
                    "observable_signal": "SIG-EDGE-FAILURE",
                },
            }
        ],
    }


def _rules(source_prefixes: list) -> dict:
    return {
        "schema_version": 1,
        "architecture_id": "ARCH-PREFLIGHT-TEST",
        "forbidden_edges": [],
        "path_boundaries": [
            {
                "id": "RULE-PREFLIGHT-BOUNDARY",
                "source_prefixes": source_prefixes,
                "forbidden_dependency_prefixes": [],
                "severity": "error",
            }
        ],
        "contract_policies": [],
        "migration_policies": [],
        "tenant_authorization_policies": [],
        "network_policies": [],
        "change_separation_policies": [],
        "code_budgets": [],
        "background_job_policies": [],
        "secret_flow_policies": [],
        "workspace_trust_policies": [],
        "risk_escalations": [],
    }


def _canonical(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


class _ModelFixture(unittest.TestCase):
    """Writes a minimal schema-valid project so that every expected line number is known."""

    def _project(self, system_paths: list, rules_prefixes: list) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "architecture").mkdir()
        (root / "schemas").mkdir()
        for name in ("architecture-system.schema.json", "architecture-rules.schema.json"):
            (root / "schemas" / name).write_bytes((ROOT / "schemas" / name).read_bytes())
        (root / SYSTEM_RELATIVE).write_text(_canonical(_system(system_paths)), encoding="utf-8")
        (root / RULES_RELATIVE).write_text(_canonical(_rules(rules_prefixes)), encoding="utf-8")
        return root

    def _line_of(self, root: Path, document: str, value: str, *, after: str) -> int:
        """Independent oracle: first line holding ``value`` after the anchor entry's id line."""
        lines = (root / document).read_text(encoding="utf-8").splitlines()
        anchors = {f'"id": "{after}",', f'"id": "{after}"'}
        anchor = next(index for index, line in enumerate(lines) if line.strip() in anchors)
        literal = json.dumps(value, ensure_ascii=False)
        candidates = {literal, f"{literal},"}
        for index in range(anchor, len(lines)):
            if lines[index].strip() in candidates:
                return index + 1
        raise AssertionError(f"{value!r} not found after {after!r} in {document}")


class TrailingSeparatorTests(_ModelFixture):
    def test_valid_model_preflights_clean_and_loads(self) -> None:
        """Contradictory control: the same check must stay silent on a good model."""
        root = self._project(["governance"], ["governance"])
        self.assertEqual(preflight_architecture(root), ())
        snapshot = load_architecture(root)
        self.assertEqual(snapshot.system["architecture_id"], "ARCH-PREFLIGHT-TEST")

    def test_trailing_separator_is_rejected_not_silently_normalized(self) -> None:
        """The one-character defect must still fail closed after the diagnosis change."""
        root = self._project([BAD_ENTRY], ["governance"])
        with self.assertRaises(ArchitectureError) as caught:
            load_architecture(root)
        self.assertEqual(caught.exception.code, "path")

    def test_trailing_separator_yields_one_located_preflight_finding(self) -> None:
        root = self._project([BAD_ENTRY], ["governance"])
        findings = preflight_architecture(root)
        self.assertEqual(len(findings), 1, [item.message for item in findings])
        finding = findings[0]
        self.assertEqual(finding.code, "path")
        self.assertEqual(finding.path, SYSTEM_RELATIVE)
        expected_line = self._line_of(
            root, SYSTEM_RELATIVE, BAD_ENTRY, after="NODE-PREFLIGHT-A"
        )
        self.assertIn(f"{SYSTEM_RELATIVE}:{expected_line}", finding.message)
        self.assertIn("NODE-PREFLIGHT-A", finding.message)
        self.assertIn(repr(BAD_ENTRY), finding.message)
        self.assertIn("trailing separator", finding.message)

    def test_loader_error_carries_the_same_location(self) -> None:
        root = self._project([BAD_ENTRY], ["governance"])
        expected_line = self._line_of(root, SYSTEM_RELATIVE, BAD_ENTRY, after="NODE-PREFLIGHT-A")
        with self.assertRaises(ArchitectureError) as caught:
            load_architecture(root)
        error = caught.exception
        self.assertEqual(error.document, SYSTEM_RELATIVE)
        self.assertEqual(error.line, expected_line)
        self.assertIn(f"{SYSTEM_RELATIVE}:{expected_line}", str(error))

    def test_repeated_bad_entry_reports_every_occurrence_count(self) -> None:
        root = self._project([BAD_ENTRY, "governance/sub"], ["governance"])
        system_path = root / SYSTEM_RELATIVE
        document = json.loads(system_path.read_text(encoding="utf-8"))
        document["nodes"][1]["repository_paths"] = [BAD_ENTRY]
        system_path.write_text(_canonical(document), encoding="utf-8")
        findings = preflight_architecture(root)
        self.assertEqual(len(findings), 1, [item.message for item in findings])
        self.assertIn("(2 occurrences)", findings[0].message)


class ShapeReasonTests(_ModelFixture):
    CASES = (
        (BAD_ENTRY, "trailing separator"),
        ("../escape", "'.' or '..' segment"),
        ("/etc/passwd", "is absolute"),
        ("a//b", "empty segment"),
        ("./relative", "'.' or '..' segment"),
        ("windows\\path", "backslash separator"),
    )

    def test_each_shape_defect_gets_its_own_reason(self) -> None:
        for value, reason in self.CASES:
            with self.subTest(value=value):
                root = self._project([value], ["governance"])
                findings = preflight_architecture(root)
                self.assertEqual(len(findings), 1, [item.message for item in findings])
                message = findings[0].message
                self.assertIn(reason, message)
                self.assertIn(SYSTEM_RELATIVE, message)
                for other_value, other_reason in self.CASES:
                    if other_reason != reason and other_value != value:
                        self.assertNotIn(other_reason, message, f"{value!r} vs {other_value!r}")

    def test_valid_path_shape_is_accepted(self) -> None:
        root = self._project(["factory/src/adaptive_factory"], ["governance"])
        self.assertEqual(preflight_architecture(root), ())

    def test_empty_entry_still_yields_exactly_one_finding(self) -> None:
        root = self._project([""], ["governance"])
        findings = preflight_architecture(root)
        self.assertEqual(len(findings), 1, [item.message for item in findings])
        self.assertIn(SYSTEM_RELATIVE, findings[0].message)

    def test_non_string_entry_yields_one_finding_without_locating_a_line(self) -> None:
        root = self._project(["governance"], ["governance"])
        system_path = root / SYSTEM_RELATIVE
        document = json.loads(system_path.read_text(encoding="utf-8"))
        document["nodes"][0]["repository_paths"] = [42]
        system_path.write_text(_canonical(document), encoding="utf-8")
        findings = preflight_architecture(root)
        self.assertEqual(len(findings), 1, [item.message for item in findings])
        self.assertIn(SYSTEM_RELATIVE, findings[0].message)


class RulesDocumentLocationTests(_ModelFixture):
    def test_rule_path_defect_names_the_rules_document(self) -> None:
        root = self._project(["governance"], [BAD_ENTRY])
        findings = preflight_architecture(root)
        self.assertEqual(len(findings), 1, [item.message for item in findings])
        finding = findings[0]
        self.assertEqual(finding.path, RULES_RELATIVE)
        expected_line = self._line_of(
            root, RULES_RELATIVE, BAD_ENTRY, after="RULE-PREFLIGHT-BOUNDARY"
        )
        self.assertIn(f"{RULES_RELATIVE}:{expected_line}", finding.message)
        self.assertIn("RULE-PREFLIGHT-BOUNDARY", finding.message)


class PreflightRobustnessTests(unittest.TestCase):
    def test_missing_model_is_a_finding_and_never_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            findings = preflight_architecture(Path(tmp))
        self.assertEqual(len(findings), 1)
        self.assertIn(SYSTEM_RELATIVE, findings[0].message)

    def test_live_project_model_preflights_clean(self) -> None:
        self.assertEqual(preflight_architecture(ROOT), ())

    def test_live_project_declares_no_badly_shaped_path(self) -> None:
        """Inventory guard: re-derived from the shipped documents, never from a frozen count."""
        system = json.loads((ROOT / SYSTEM_RELATIVE).read_text(encoding="utf-8"))
        rules = json.loads((ROOT / RULES_RELATIVE).read_text(encoding="utf-8"))
        declared = [
            path for node in system["nodes"] for path in node["repository_paths"]
        ] + [contract["path"] for contract in system["contracts"]]
        for collection, entries in rules.items():
            if not isinstance(entries, list):
                continue
            for rule in entries:
                for field in RULE_PATH_FIELDS & set(rule):
                    declared.extend(rule[field])
        self.assertTrue(declared, "shipped model declares no paths at all")
        self.assertEqual(
            sorted({value for value in declared if _path_shape_problem(value)}),
            [],
        )


class DoctorPreflightGateTests(_ModelFixture):
    def _harness_copy(self) -> Path:
        from tests._support import project_copy

        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        root = stack.enter_context(project_copy())
        (root / "architecture").mkdir()
        (root / "schemas").mkdir()
        for relative in (SYSTEM_RELATIVE, RULES_RELATIVE):
            (root / relative).write_bytes((ROOT / relative).read_bytes())
        for name in ("architecture-system.schema.json", "architecture-rules.schema.json"):
            (root / "schemas" / name).write_bytes((ROOT / "schemas" / name).read_bytes())
        return root

    def _model_item(self, root: Path):
        items = [item for item in run_doctor(root) if item.name == "architecture-model"]
        self.assertEqual(len(items), 1)
        return items[0]

    def test_doctor_passes_the_shipped_model(self) -> None:
        item = self._model_item(self._harness_copy())
        self.assertEqual(item.status, "pass", item.message)

    def test_doctor_reports_one_located_failure_for_a_bad_trailing_slash(self) -> None:
        root = self._harness_copy()
        system_path = root / SYSTEM_RELATIVE
        document = json.loads(system_path.read_text(encoding="utf-8"))
        declared = next((node for node in document["nodes"] if node["repository_paths"]), None)
        self.assertIsNotNone(declared, "shipped model declares no repository paths at all")
        declared["repository_paths"] = list(declared["repository_paths"]) + [BAD_ENTRY]
        mutated = _canonical(document)
        system_path.write_text(mutated, encoding="utf-8")
        literal = json.dumps(BAD_ENTRY, ensure_ascii=False)
        expected_line = next(
            number
            for number, line in enumerate(mutated.splitlines(), start=1)
            if line.strip() in {literal, f"{literal},"}
        )
        item = self._model_item(root)
        self.assertEqual(item.status, "fail")
        self.assertIn(f"{SYSTEM_RELATIVE}:{expected_line}", item.message)
        self.assertIn("trailing separator", item.message)


if __name__ == "__main__":
    unittest.main()
