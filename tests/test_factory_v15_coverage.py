import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MATRIX = (
    ROOT / "engineering/changes/20260930-factory-v1-5-fast-working-release-52ad34/evidence/requirement-coverage.json"
)


class FactoryV15CoverageTests(unittest.TestCase):
    def test_every_original_and_bb_item_has_unique_honest_source_and_test_coverage(self):
        self.assertTrue(MATRIX.is_file(), "all-item requirement coverage is missing")
        data = json.loads(MATRIX.read_text())
        expected = (
            {f"F{i:02d}" for i in range(1, 27)}
            | {f"AC{i:02d}" for i in range(1, 115)}
            | {f"BB-R{i:02d}" for i in range(1, 19)}
            | {f"BB-AC{i:02d}" for i in range(1, 37)}
        )
        entries = data["items"]
        self.assertEqual(len(entries), 194)
        self.assertEqual({entry["id"] for entry in entries}, expected)
        self.assertEqual(data["authority_effect"], "none")
        statuses = {
            "implemented_tested",
            "existing_implementation_reused",
            "implemented_pending_integration",
            "external_not_run",
            "excluded_by_owner",
            "source_gap",
        }
        for entry in entries:
            with self.subTest(requirement=entry["id"]):
                self.assertIn(entry["status"], statuses)
                self.assertTrue(entry["title"])
                self.assertTrue(entry["rationale"])
                self.assertEqual(entry["acceptance_status"], "not_evaluated")
                if entry["status"] in {"implemented_tested", "existing_implementation_reused"}:
                    self.assertTrue(entry["source_paths"])
                    self.assertTrue(entry["test_evidence"])
                    for path in entry["source_paths"]:
                        self.assertTrue((ROOT / path).is_file(), path)
                    for evidence in entry["test_evidence"]:
                        self.assertTrue((ROOT / evidence["path"]).is_file(), evidence["path"])
                        self.assertTrue(evidence["command"])
                if entry["status"] == "implemented_pending_integration":
                    self.assertTrue(entry["integration_contour"])
                if entry["status"] == "external_not_run":
                    self.assertIn(entry["external_gate"], {"live_profile_qualification", "human_accepted_history"})
        self.assertEqual(
            {entry["id"] for entry in entries if entry["status"] == "excluded_by_owner"},
            {"F14", "F15", "F16", "AC31", "AC32", "AC33", "AC34", "AC37", "AC38"},
        )
