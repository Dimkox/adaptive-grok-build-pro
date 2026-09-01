from __future__ import annotations

import copy
import itertools
import json
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CURRENT_CHECK = "adaptive-trust-ci/verified@06ecf1c875bc"
CURRENT_APP_ID = 4694114
CURRENT_MAIN_SHA = "8ab4e57038dec2e07f01aaa0b207813a387358f4"
MILESTONES = {f"M{number}" for number in range(10)}
AXES = ("implementation", "review", "stack_integration", "main_delivery", "external_gate")
CANONICAL_GRAPH_NODES = {
    "Route", "Skills", "Agents", "Hooks", "Policy", "Verify", "Packages", "Contract",
    "Decisions", "Mistakes", "TrustAPI", "TrustWorker", "Postgres", "Runner", "Holdout",
    "GitHubApp",
}


def _section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if match is None:
        raise AssertionError(f"missing section: {heading}")
    return match.group(1)


def _assert_readme_graph(test: unittest.TestCase, readme: str) -> None:
    block = re.search(r"## Stack graph\n.*?```mermaid\n(.*?)```", readme, re.S)
    test.assertIsNotNone(block)
    edges = [
        tuple(sorted(edge))
        for edge in re.findall(r"^\s*(\w+)\s*---\s*(\w+)\s*$", block.group(1), re.M)
    ]
    nodes = {node for edge in edges for node in edge}
    role_table = re.search(r"\| Node \| Role \|\n\| --- \| --- \|\n(.*?)(?=\n\n)", readme, re.S)
    test.assertIsNotNone(role_table)
    role_nodes = set(re.findall(r"^\| (\w+) \|", role_table.group(1), re.M))
    expected = {tuple(sorted(pair)) for pair in itertools.combinations(CANONICAL_GRAPH_NODES, 2)}
    test.assertEqual(role_nodes, CANONICAL_GRAPH_NODES)
    test.assertEqual(nodes, role_nodes)
    test.assertEqual(len(edges), 120)
    test.assertEqual(len(set(edges)), 120)
    test.assertEqual(set(edges), expected)


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

        exact_milestone_facts = {
            "M0": {
                "implementation": "9590db4db14838ab534958aaa0842f5523f043ae",
                "review": "9590db4db14838ab534958aaa0842f5523f043ae",
                "main_merge": "069fe8226addb8a1922dde3db4e753434baa3a3d",
            },
            "M1": {
                "implementation": "022411b05924618cfde0cb97b8c8aff4955e6013",
                "review": "022411b05924618cfde0cb97b8c8aff4955e6013",
                "stack_base": "milestone/m1-typed-intent-evidence",
                "stack_pr": 10,
                "stack_merge": "c23fd49f80c7d1c74ca3393b6079a74f251a72d8",
                "gate_head": "022411b05924618cfde0cb97b8c8aff4955e6013",
            },
            "M2": {
                "implementation": "022411b05924618cfde0cb97b8c8aff4955e6013",
                "review": "022411b05924618cfde0cb97b8c8aff4955e6013",
                "stack_base": "milestone/m1-typed-intent-evidence",
                "stack_pr": 10,
                "stack_merge": "c23fd49f80c7d1c74ca3393b6079a74f251a72d8",
                "gate_head": "022411b05924618cfde0cb97b8c8aff4955e6013",
            },
            "M3": {
                "implementation": "1e73ff9b91d9b711cafccad7ccccb1a992d5e84d",
                "review": "1e73ff9b91d9b711cafccad7ccccb1a992d5e84d",
                "stack_base": "milestone/m2-executable-architecture",
                "stack_pr": 11,
                "stack_merge": "67714a1f1b87effcfabe55d5ca2770d0a68d17c1",
                "gate_head": "1e73ff9b91d9b711cafccad7ccccb1a992d5e84d",
            },
            "M4": {
                "implementation": "cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06",
                "review": "f82134de35e531a8b3bbf235ad480254ba40f1fe",
                "stack_base": "milestone/m2-executable-architecture",
                "stack_pr": 17,
                "gate_head": "8e6504168462bbabad359fec3d23838c87f5ba22",
            },
        }
        for milestone, exact in exact_milestone_facts.items():
            actual = state["milestones"][milestone]
            self.assertEqual(actual["implementation"]["commit"], exact["implementation"])
            self.assertEqual(actual["review"]["commit"], exact["review"])
            if "stack_base" in exact:
                self.assertEqual(actual["stack_integration"]["base_branch"], exact["stack_base"])
                self.assertEqual(actual["stack_integration"]["pull_request"], exact["stack_pr"])
            if "stack_merge" in exact:
                self.assertEqual(actual["stack_integration"]["merge_commit"], exact["stack_merge"])
            if "main_merge" in exact:
                self.assertEqual(actual["main_delivery"]["merge_commit"], exact["main_merge"])
            if "gate_head" in exact:
                self.assertEqual(actual["external_gate"]["head_sha"], exact["gate_head"])

    def test_m2_m3_commits_have_stack_ancestry_but_are_absent_from_main(self) -> None:
        milestones = self.state["milestones"]
        relationships = (
            (milestones["M2"]["implementation"]["commit"], milestones["M2"]["stack_integration"]["merge_commit"], True),
            (milestones["M2"]["implementation"]["commit"], milestones["M3"]["stack_integration"]["merge_commit"], True),
            (milestones["M3"]["implementation"]["commit"], milestones["M3"]["stack_integration"]["merge_commit"], True),
            (milestones["M2"]["stack_integration"]["merge_commit"], CURRENT_MAIN_SHA, False),
            (milestones["M3"]["stack_integration"]["merge_commit"], CURRENT_MAIN_SHA, False),
        )
        for ancestor, descendant, expected in relationships:
            for commit in (ancestor, descendant):
                exists = subprocess.run(
                    ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
                    cwd=ROOT,
                    check=False,
                    capture_output=True,
                )
                self.assertEqual(exists.returncode, 0, f"missing commit object {commit}")
            result = subprocess.run(
                ["git", "merge-base", "--is-ancestor", ancestor, descendant],
                cwd=ROOT,
                check=False,
                capture_output=True,
            )
            self.assertEqual(result.returncode == 0, expected, f"unexpected ancestry {ancestor} -> {descendant}")

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
        expected_open = [
            {"pull_request": 12, "branch": "fix/human-approval-cli", "base": "main", "head": "0f7f508945ccce7dc4f1bffc463247633e9e8f58", "status": "blocked_old_epoch_action_required", "disposition": "Retain; rebase and obtain fresh governance approval/current-epoch check."},
            {"pull_request": 13, "branch": "feat/trust-ci-repository-profiles", "base": "main", "head": "f2fd8a7a00a731fbb7acb90e3c7c7881568c8d80", "status": "blocked_old_epoch_action_required", "disposition": "Retain; restack after PR 12 and obtain fresh approval/check."},
            {"pull_request": 15, "branch": "mvp/investor-ready", "base": "main", "head": "165d5dd90a2fc2831a3b85be2562a2bb241c8b14", "status": "blocked_current_epoch_failure", "disposition": "Do not merge wholesale; replay the unique investor demo and packaging slice."},
            {"pull_request": 17, "branch": "milestone/m4-durable-control-plane-accepted-m3", "base": "milestone/m2-executable-architecture", "head": "8e6504168462bbabad359fec3d23838c87f5ba22", "status": "open_current_epoch_and_gitguardian_failure", "disposition": "Preserve as failed evidence; create and deliver a clean successor."},
        ]
        self.assertEqual(inventory["open_pull_requests"], expected_open)
        seo = self.state["delivered_non_milestone_work"][0]
        self.assertEqual(
            {key: seo[key] for key in ("pull_request", "status", "source_head", "merge_commit")},
            {"pull_request": 19, "status": "delivered", "source_head": "ecc85d903d0394f99a139fd4e74a7cc452e386c6", "merge_commit": CURRENT_MAIN_SHA},
        )
        self.assertEqual(
            inventory["retained_unresolved"],
            [
                {"pull_request": 14, "local_head": "cb2fe7ce637c464179e20b5b37aae334e56c1838", "purpose": "Unique closed production-promotion work requiring explicit re-evaluation."},
                {"branch": "feature/workflow-artifact-adapters", "local_head": "dccaeec2a6b79c73663765f5909243e468e4b070", "purpose": "Local-only work requiring comparison before cleanup."},
                {"branch": "origin/milestone/a-plus-autopilot", "head": "90a5da294ec06e9fbbf8ea97d1c27c64484b9069", "purpose": "Design-only reference; not M8 implementation."},
            ],
        )
        self.assertEqual(
            [(item["route_id"], item["branch"]) for item in inventory["active"]],
            [
                ("944abd96ddb3", "chore/reconcile-milestone-state"),
                ("944abd96ddb3", "origin/milestone/m2-executable-architecture"),
                ("944abd96ddb3", "milestone/m4-durable-control-plane-accepted-m3"),
            ],
        )
        self.assertIn(1, {item.get("pull_request") for item in inventory["superseded"]})

    def test_adversarial_pr17_base_head_and_status_are_rejected(self) -> None:
        original = self.state
        mutated = copy.deepcopy(original)
        pr17 = next(item for item in mutated["work_inventory"]["open_pull_requests"] if item["pull_request"] == 17)
        pr17.update(base="main", head="0" * 40, status="success")
        self.state = mutated
        try:
            with self.assertRaises(AssertionError):
                self.test_work_inventory_preserves_open_and_unresolved_continuation_work()
        finally:
            self.state = original

    def test_adversarial_m2_m3_commits_are_rejected(self) -> None:
        original = self.state
        mutated = copy.deepcopy(original)
        mutated["milestones"]["M2"]["implementation"]["commit"] = "0" * 40
        mutated["milestones"]["M3"]["stack_integration"]["merge_commit"] = "f" * 40
        self.state = mutated
        try:
            with self.assertRaises(AssertionError):
                self.test_project_state_has_independent_milestone_axes_and_truthful_facts()
        finally:
            self.state = original

    def test_adversarial_m2_m3_ancestry_is_rejected(self) -> None:
        original = self.state
        mutated = copy.deepcopy(original)
        mutated["milestones"]["M2"]["implementation"]["commit"] = CURRENT_MAIN_SHA
        mutated["milestones"]["M3"]["implementation"]["commit"] = CURRENT_MAIN_SHA
        self.state = mutated
        try:
            with self.assertRaises(AssertionError):
                self.test_m2_m3_commits_have_stack_ancestry_but_are_absent_from_main()
        finally:
            self.state = original

    def test_readme_graph_is_exact_complete_k16(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        _assert_readme_graph(self, readme)

    def test_adversarial_graph_node_identity_mutation_is_rejected(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        graph = re.search(r"```mermaid\n(.*?)```", readme, re.S)
        self.assertIsNotNone(graph)
        mutant = readme[: graph.start(1)] + graph.group(1).replace("GitHubApp", "FakeApp") + readme[graph.end(1) :]
        with self.assertRaises(AssertionError):
            _assert_readme_graph(self, mutant)


if __name__ == "__main__":
    unittest.main()
