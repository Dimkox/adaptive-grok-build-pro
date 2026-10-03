"""Architecture input refusal must precede expensive consumers and locate the defect."""
from __future__ import annotations

import json
import os
import signal
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_architecture_model import ARCH, DIAGRAMS, ROOT, _rules, _system
from adaptive_grok.doctor import run_doctor
from adaptive_grok.state import set_active_route
from adaptive_grok.verification import verify
from adaptive_grok import verification as verifier
from adaptive_grok.python_test_runner import RunCancelled

SYSTEM = "architecture/system.yaml"
RULES = "architecture/rules.yaml"
BAD = "factory/runtime/"


def _canonical(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


class ArchitectureInputTests(unittest.TestCase):
    def _project(self) -> Path:
        directory = tempfile.TemporaryDirectory(prefix="architecture-inputs-")
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / "architecture").mkdir()
        (root / "schemas").mkdir()
        for name in ("architecture-system.schema.json", "architecture-rules.schema.json"):
            (root / "schemas" / name).write_bytes((ROOT / "schemas" / name).read_bytes())
        self._write(root, SYSTEM, _system())
        self._write(root, RULES, _rules())
        return root

    @staticmethod
    def _write(root: Path, relative: str, value: dict) -> str:
        text = _canonical(value)
        (root / relative).write_text(text, encoding="utf-8")
        return text

    def _findings(self, root: Path):
        preflight = getattr(ARCH, "preflight_architecture", None)
        self.assertTrue(callable(preflight), "bounded architecture input preflight is missing")
        return preflight(root)

    def _bad_path(self, root: Path, value=BAD, *, lookalike: bool = False) -> tuple[int, int]:
        model = _system()
        if lookalike:
            model["signals"][0]["description"] = "legal\u2028text\u0085still-one-line"
            model["edges"][0]["failure_behavior"]["terminal_action"] = "reject\u2028bounded"
        model["nodes"][0]["repository_paths"] = [value]
        text = self._write(root, SYSTEM, model)
        literal = json.dumps(value, ensure_ascii=False)
        lines = text.split("\n")
        index = next(i for i, line in enumerate(lines) if line.strip() == literal)
        return index + 1, lines[index].index(literal) + 1

    def test_valid_model_keeps_digests_and_generated_views(self) -> None:
        root = self._project()
        before = ARCH.load_architecture(root)
        digests = ARCH.architecture_digests(before)
        views = DIAGRAMS.render_diagrams(before)
        self.assertEqual(self._findings(root), ())
        after = ARCH.load_architecture(root)
        self.assertEqual(ARCH.architecture_digests(after), digests)
        self.assertEqual(DIAGRAMS.render_diagrams(after), views)
        self.assertEqual(self._findings(ROOT), ())

    def test_loader_reports_exact_structural_path_location(self) -> None:
        root = self._project()
        line, column = self._bad_path(root)
        with self.assertRaises(ARCH.ArchitectureError) as caught:
            ARCH.load_architecture(root)
        error = caught.exception
        self.assertEqual(getattr(error, "document", None), SYSTEM)
        self.assertEqual(getattr(error, "line", None), line)
        self.assertEqual(getattr(error, "column", None), column)
        self.assertIn(f"{SYSTEM}:{line}:{column}", str(error))
        self.assertIn("trailing separator", str(error))

    def test_unicode_line_lookalikes_do_not_shift_coordinates(self) -> None:
        root = self._project()
        line, column = self._bad_path(root, lookalike=True)
        finding, = self._findings(root)
        self.assertIn(f"{SYSTEM}:{line}:{column}", finding.message)
        text = (root / SYSTEM).read_text(encoding="utf-8")
        naive = next(i + 1 for i, row in enumerate(text.splitlines()) if row.strip() == json.dumps(BAD))
        self.assertGreater(naive, line, "fixture must expose physical-newline miscounting")

    def test_path_shapes_fail_closed_with_specific_location(self) -> None:
        cases = [("../escape", "segment"), ("./relative", "segment"),
                 ("/absolute", "absolute"), ("a//b", "empty segment"),
                 ("a\\b", "backslash"), ("", "empty"), (42, "string"),
                 ("cafe\u0301", "NFC"), ("a\u2028b", "control")]
        for value, reason in cases:
            with self.subTest(value=value):
                root = self._project()
                line, column = self._bad_path(root, value)
                finding, = self._findings(root)
                self.assertIn(f"{SYSTEM}:{line}:{column}", finding.message)
                self.assertIn(reason, finding.message)

    def test_duplicate_literal_is_located_in_failing_rule(self) -> None:
        root = self._project()
        rules = _rules()
        rules["migration_policies"] = [{"id": "RULE-EARLIER", "immutable_history": True,
            "path_prefixes": [BAD], "required_phases": ["contract", "expand", "migrate"], "severity": "error"}]
        rules["path_boundaries"] = [{"id": "RULE-FAIL", "source_prefixes": [BAD],
            "forbidden_dependency_prefixes": [], "severity": "error"}]
        text = self._write(root, RULES, rules)
        rows = text.split("\n")
        anchor = next(i for i, row in enumerate(rows) if '"id": "RULE-FAIL"' in row)
        index = next(i for i in range(anchor, len(rows)) if rows[i].strip() == json.dumps(BAD))
        finding, = self._findings(root)
        self.assertIn(f"{RULES}:{index + 1}:{rows[index].index(chr(34)) + 1}", finding.message)
        self.assertIn("RULE-FAIL", finding.message)

    def test_missing_and_symlink_inputs_report_actual_document(self) -> None:
        for relative in (SYSTEM, RULES, "schemas/architecture-system.schema.json", "schemas/architecture-rules.schema.json"):
            for symlink in (False, True):
                with self.subTest(relative=relative, symlink=symlink):
                    root = self._project()
                    path = root / relative
                    if symlink:
                        saved = root / "saved-input.json"
                        path.rename(saved)
                        path.symlink_to(saved)
                    else:
                        path.unlink()
                    finding, = self._findings(root)
                    self.assertEqual(finding.code, "io")
                    self.assertEqual(finding.path, relative)

    def test_malformed_json_and_yaml_name_exact_syntax_position(self) -> None:
        for text, line, column in [("{\n  \"nodes\": ]\n}\n", 2, 12), ("schema_version: 1\n", 1, 1)]:
            with self.subTest(text=text):
                root = self._project()
                (root / SYSTEM).write_text(text, encoding="utf-8")
                finding, = self._findings(root)
                self.assertEqual(finding.path, SYSTEM)
                self.assertIn(f"{SYSTEM}:{line}:{column}", finding.message)

    def test_duplicate_json_key_reports_second_key_position(self) -> None:
        root = self._project()
        (root / SYSTEM).write_text('{\n  "nodes": [],\n  "nodes": []\n}\n', encoding="utf-8")
        finding, = self._findings(root)
        self.assertIn(f"{SYSTEM}:3:3", finding.message)

    def test_nested_duplicate_coordinate_matches_the_object_decoder_refused(self) -> None:
        root = self._project()
        text = '{\n  "bad": 1,\n  "bad": 2,\n  "nested": {\n    "bad": 1,\n    "bad": 2\n  }\n}\n'
        (root / SYSTEM).write_text(text, encoding="utf-8")
        finding, = self._findings(root)
        self.assertIn(f"{SYSTEM}:6:5", finding.message)

    def test_model_and_document_bounds_are_refusals(self) -> None:
        for kind in ("bytes", "nodes", "depth"):
            with self.subTest(kind=kind):
                root = self._project()
                if kind == "bytes":
                    text = " " * (ARCH.MAX_DOCUMENT_BYTES + 1)
                elif kind == "depth":
                    text = '{"nested": ' + "[" * (ARCH.MAX_DEPTH + 1) + "0" + "]" * (ARCH.MAX_DEPTH + 1) + "}\n"
                else:
                    model = _system()
                    model["nodes"] *= ARCH.MAX_MODEL_NODES
                    text = _canonical(model)
                (root / SYSTEM).write_text(text, encoding="utf-8")
                finding, = self._findings(root)
                self.assertEqual(finding.path, SYSTEM)
                self.assertIn(finding.code, {"limit", "schema"})

    def test_raw_document_alias_shape_is_rejected_before_path_normalization(self) -> None:
        root = self._project()
        for raw in ("./architecture/system.yaml", "architecture//system.yaml", "architecture/../architecture/system.yaml"):
            with self.subTest(raw=raw), self.assertRaises(ARCH.ArchitectureError):
                ARCH.load_architecture(root, system_path=raw)

    def test_duplicate_contract_paths_and_hardlink_aliases_are_refused(self) -> None:
        for hardlink in (False, True):
            with self.subTest(hardlink=hardlink):
                root = self._project()
                model = _system()
                record = {"id": "CONTRACT-A", "kind": "json_schema", "path": "a.json", "version": "1",
                          "role": "consumer", "compatibility": "consumer_accepts_old"}
                model["contracts"] = [record, {**record, "id": "CONTRACT-B", "path": "b.json" if hardlink else "a.json"}]
                self._write(root, SYSTEM, model)
                (root / "a.json").write_text("{}\n", encoding="utf-8")
                if hardlink:
                    os.link(root / "a.json", root / "b.json")
                finding, = self._findings(root)
                self.assertIn("duplicate" if not hardlink else "alias", finding.message)

    def test_referenced_contract_cannot_alias_an_authority_input(self) -> None:
        root = self._project()
        model = _system()
        model["contracts"] = [{"id": "CONTRACT-A", "kind": "json_schema", "path": "system-copy.json", "version": "1",
                               "role": "consumer", "compatibility": "consumer_accepts_old"}]
        self._write(root, SYSTEM, model)
        os.link(root / SYSTEM, root / "system-copy.json")
        findings = self._findings(root)
        self.assertEqual(len(findings), 1)
        self.assertIn("filesystem alias", findings[0].message)

    def test_missing_symlink_and_unloadable_referenced_files_are_refused(self) -> None:
        for kind in ("missing", "symlink", "malformed"):
            with self.subTest(kind=kind):
                root = self._project()
                model = _system()
                model["contracts"] = [{"id": "CONTRACT-A", "kind": "json_schema", "path": "contract.json", "version": "1",
                                       "role": "consumer", "compatibility": "consumer_accepts_old"}]
                self._write(root, SYSTEM, model)
                if kind == "symlink":
                    (root / "outside.json").write_text("{}\n", encoding="utf-8")
                    (root / "contract.json").symlink_to(root / "outside.json")
                elif kind == "malformed":
                    (root / "contract.json").write_text("{\n", encoding="utf-8")
                finding, = self._findings(root)
                self.assertEqual(finding.path, "contract.json")

    def test_doctor_distinguishes_skipped_from_missing_schema(self) -> None:
        root = self._project()
        (root / "schemas/architecture-rules.schema.json").unlink()
        item, = [item for item in run_doctor(root) if item.name == "architecture-model"]
        self.assertEqual(item.status, "fail")
        self.assertIn("schemas/architecture-rules.schema.json", item.message)
        (root / SYSTEM).unlink()
        (root / RULES).unlink()
        item, = [item for item in run_doctor(root) if item.name == "architecture-model"]
        self.assertEqual(item.status, "info")
        self.assertIn("skipped", item.message)

    def test_refused_inputs_with_active_route_return_report_without_binding_receipt(self) -> None:
        root = self._project()
        self._bad_path(root)
        set_active_route(root, {"route_id": "input-refusal", "quality_profiles": ["base"], "delivery_expected": False})
        report = verify(root, mode="fast", record=True)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["architecture"]["receipt_status"], "not_recorded")
        check, = [item for item in report["checks"] if item["name"] == "architecture-inputs"]
        self.assertTrue(any(item.get("code") == "receipt-not-recorded" for item in check["details"]))
        self.assertFalse((root / ".grok-stack/runtime/receipts/input-refusal/verification.json").exists())

    def test_refusal_followed_by_cancellation_never_rebinds_receipt(self) -> None:
        root = self._project()
        self._bad_path(root)
        set_active_route(root, {"route_id": "input-refusal", "quality_profiles": ["base"], "delivery_expected": False})
        with patch.object(verifier, "_workflow_artifacts_check", side_effect=RunCancelled(signal.SIGTERM)), \
             patch.object(verifier, "_record_verification_receipt") as publish:
            with self.assertRaises(verifier.VerificationCancelled) as caught:
                verify(root, mode="fast", record=True)
        publish.assert_not_called()
        report = caught.exception.report
        self.assertEqual(report["evidence_status"], "not_recorded")
        self.assertEqual(report["terminal_state"], "cancelled")
        self.assertEqual(report["architecture"]["receipt_status"], "not_recorded")
        self.assertEqual(caught.exception.code, 143)
        checks = {item["name"]: item for item in report["checks"]}
        self.assertEqual(checks["architecture-inputs"]["status"], "fail")
        self.assertEqual(checks["verification-interrupted"]["status"], "cancelled")

    def test_verifier_discloses_skip_and_blocks_root_discovery_on_refusal(self) -> None:
        root = self._project()
        self._bad_path(root)
        tests = root / "tests"
        tests.mkdir()
        marker = root / "root-discovery-ran"
        (tests / "test_would_run.py").write_text(
            "from pathlib import Path\nimport unittest\nclass WouldRun(unittest.TestCase):\n"
            "    def test_marker(self):\n"
            f"        Path({str(marker)!r}).write_text('ran')\n", encoding="utf-8")
        report = verify(root, mode="fast", record=False)
        checks = {item["name"]: item for item in report["checks"]}
        self.assertFalse(marker.exists(), "root discovery started after an input refusal")
        self.assertEqual(checks["architecture-inputs"]["status"], "fail")
        self.assertEqual(checks["architecture"]["status"], "fail")
        self.assertEqual(checks["python-unittest"]["status"], "skip")
        (root / SYSTEM).unlink()
        (root / RULES).unlink()
        report = verify(root, mode="fast", record=False)
        checks = {item["name"]: item for item in report["checks"]}
        self.assertEqual(checks["architecture-inputs"]["status"], "skip")


if __name__ == "__main__":
    unittest.main()
