from __future__ import annotations

import itertools
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CURRENT_CHECK = "adaptive-trust-ci/verified@06ecf1c875bc"
CURRENT_APP_ID = 4694114
CURRENT_MAIN_SHA = "8ab4e57038dec2e07f01aaa0b207813a387358f4"
MILESTONES = {f"M{number}" for number in range(10)}
AXES = ("implementation", "review", "stack_integration", "main_delivery", "external_gate")


def _section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if match is None:
        raise AssertionError(f"missing section: {heading}")
    return match.group(1)


class ProjectStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state = json.loads((ROOT / "PROJECT_STATE.json").read_text(encoding="utf-8"))

    def test_project_state_has_independent_milestone_axes_and_truthful_facts(self) -> None:
        state = self.state
        self.assertEqual(state["schema_version"], 2)
        self.assertEqual(state["observed_main_sha"], CURRENT_MAIN_SHA)
        self.assertRegex(state["observed_at"], r"^2026-09-01T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(set(state["milestones"]), MILESTONES)
        for milestone in state["milestones"].values():
            self.assertEqual(set(milestone), set(AXES))

        expected = {
            "M0": ("complete", "passed", "not_applicable", "delivered", "stale"),
            "M1": ("complete", "passed", "merged", "partial", "success"),
            "M2": ("complete", "passed", "merged", "not_delivered", "success"),
            "M3": ("complete", "passed", "merged", "not_delivered", "success"),
            "M4": ("complete", "stale", "open", "not_delivered", "failure"),
        }
        for milestone, statuses in expected.items():
            actual = self.state["milestones"][milestone]
            self.assertEqual(
                tuple(actual[axis]["status"] for axis in AXES),
                statuses,
            )
        for milestone in (f"M{number}" for number in range(5, 10)):
            actual = self.state["milestones"][milestone]
            self.assertEqual(actual["implementation"]["status"], "not_started")
            self.assertEqual(actual["review"]["status"], "not_reviewed")
            self.assertEqual(actual["main_delivery"]["status"], "not_delivered")
            self.assertEqual(actual["external_gate"]["status"], "not_run")
        self.assertEqual(self.state["delivered_milestones_on_main"], ["M0"])
        self.assertEqual(self.state["implemented_milestones"], ["M0", "M1", "M2", "M3", "M4"])

    def test_current_epoch_and_app_are_consistent_in_handoff_documents(self) -> None:
        trust = self.state["trust_ci"]
        self.assertEqual(trust["required_check"], CURRENT_CHECK)
        self.assertEqual(trust["github_app_id"], CURRENT_APP_ID)
        current_sections = (
            _section((ROOT / "README.md").read_text(encoding="utf-8"), "Current state"),
            _section((ROOT / "START_HERE.md").read_text(encoding="utf-8"), "Current project state"),
        )
        for section in current_sections:
            self.assertIn(CURRENT_CHECK, section)
            self.assertIn(str(CURRENT_APP_ID), section)
            self.assertIn(CURRENT_MAIN_SHA, section)
            self.assertNotIn("adaptive-trust-ci/verified@6737355947c2", section)

        start_here = (ROOT / "START_HERE.md").read_text(encoding="utf-8")
        self.assertIn("PR #19", start_here)
        self.assertIn("delivered", start_here)
        self.assertNotRegex(start_here, r"open PRs[^.;\n]*#19")

    def test_work_inventory_preserves_open_and_unresolved_continuation_work(self) -> None:
        inventory = self.state["work_inventory"]
        self.assertEqual(
            {item["pull_request"] for item in inventory["open_pull_requests"]},
            {12, 13, 15, 17},
        )
        seo = self.state["delivered_non_milestone_work"][0]
        self.assertEqual(seo["pull_request"], 19)
        self.assertEqual(seo["status"], "delivered")
        self.assertEqual(seo["merge_commit"], CURRENT_MAIN_SHA)
        self.assertIn("944abd96ddb3", {item["route_id"] for item in inventory["active"]})
        self.assertIn(14, {item.get("pull_request") for item in inventory["retained_unresolved"]})
        self.assertIn(1, {item.get("pull_request") for item in inventory["superseded"]})

    def test_readme_graph_is_exact_complete_k16(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        block = re.search(r"## Stack graph\n.*?```mermaid\n(.*?)```", readme, re.S)
        self.assertIsNotNone(block)
        edges = [
            tuple(sorted(edge))
            for edge in re.findall(r"^\s*(\w+)\s*---\s*(\w+)\s*$", block.group(1), re.M)
        ]
        nodes = {node for edge in edges for node in edge}
        expected = {tuple(sorted(pair)) for pair in itertools.combinations(nodes, 2)}
        self.assertEqual(len(nodes), 16)
        self.assertEqual(len(edges), 120)
        self.assertEqual(len(set(edges)), 120)
        self.assertEqual(set(edges), expected)


if __name__ == "__main__":
    unittest.main()
