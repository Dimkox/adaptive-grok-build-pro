from __future__ import annotations

import copy
import itertools
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CURRENT_CHECK = "adaptive-trust-ci/verified@06ecf1c875bc"
CURRENT_APP_ID = 4694114
CURRENT_MAIN_SHA = "78ad2f679d38dc3244e716c586332417e610089c"
SEO_MERGE_SHA = "8ab4e57038dec2e07f01aaa0b207813a387358f4"
M4_PRODUCT_SHA = "9727bc30c82bb44a86db0ef5b62e507b5527207a"
M4_FINAL_TREE = "5feb9a74eda6c54cd37539a2c5dda378a5e27853"
M4_FINAL_ARTIFACT_SHA256 = "57e6e00a6c5281fda33e1317d955dd5ca0e1a6f9467e60daa256a8919b408bcc"
M4_SOURCE_SHA = "3b1f9a54a964d91f34cee2628374b17e7a42edeb"
M4_FAILED_EXTERNAL_SHA = "571cad7877431ac5ab5779b53fe9f7effd6859ce"
M4_HISTORICAL_SOURCE_SHA = "460a8a01a6394cac710b4e3f9eea3d94d4beef89"
M4_INTEGRATION_SHA = "da7ec8d7d40f52663aba1ff59bf03ccf209395b0"
M4_SCANNER_REPAIR_SHA = "5a6cdfb7a129e02724c632f78c31de6406d6863a"
M4_RELEASE_STATE_BASE_SHA = "56e12b2b394436ee227c66d78b1caba8f7317c78"
M4_RELEASE_STATE_BASE_FINGERPRINT = "e27caec9d2de459ef26bea49b99b93b5b7326a9c84c89b97f4ec482c237d4add"
M4_FAILED_VERIFY_SHA = "547ee628812fbf098f337a854f68edf660091ead"
M4_FAILED_VERIFY_FINGERPRINT = "f0efa89e689dbe47c701a4d301e97361ee671e299ef2f32b5295b908e182e768"
M5_ENROLLMENT_SHA = "27b0ae619cacf0d9ddeed15c60212800ff6009ca"
M5_ENROLLMENT_TREE = "1a4e3f87da8a12e173a81e66b53f5fc21cb241c6"
M5_RUNTIME_CHECKPOINT = "3940267ac5754ad07a047894102015d33eb759b1"
M5_RUNTIME_TREE = "4646582a7c5ff6f08ee7e8462687da400459b08d"
M6_PROVISIONAL_SHA = "2d2360cd6f2a19ad3328d468073a52927691b112"
M6_PROVISIONAL_TREE = "5ee89e86b7e8f03ff78c644713e449b0fb9064d8"
M7_PROVISIONAL_SHA = "4df2516fa3a137fa730d08733fb9e338768232fb"
M7_PROVISIONAL_TREE = "8dbe6e4436998e9a4dbc3e2fe9ec694bf71ba7c2"
M8_STARTING_SHA = "46a6c8eba6b5bd8e4654f3041e52061cdd1a15d6"
M8_PROVISIONAL_SHA = "2cee9b93c161b6c76f4fee877e6d19eacee5a271"
M8_PROVISIONAL_TREE = "e88baebf8297007474e8c65d2314fea7e7226faa"
M9_DESIGN_SHA = "055051e26e26bf08fa85376523ba6632afcca747"
M9_PROVISIONAL_SHA = "6b42ba6d6c1ab02fe5c1c7a2ecfd762014a4d420"
M9_PROVISIONAL_TREE = "48213591aa3c8e8dc0ce4137438b081bbc83988b"
MILESTONES = {f"M{number}" for number in range(10)}
AXES = ("implementation", "review", "stack_integration", "main_delivery", "external_gate")
CANONICAL_GRAPH_NODES = {
    "Route", "Skills", "Agents", "Hooks", "Policy", "Verify", "Packages", "Contract",
    "Decisions", "Mistakes", "TrustAPI", "TrustWorker", "Postgres", "Runner", "Holdout",
    "GitHubApp", "Factory", "M5Execution", "M6Semantic", "M7Shadow", "M8Autonomy",
    "M9Delivery",
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
    test.assertEqual(len(edges), 231)
    test.assertEqual(len(set(edges)), 231)
    test.assertEqual(set(edges), expected)


class ProjectStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state = json.loads((ROOT / "PROJECT_STATE.json").read_text(encoding="utf-8"))

    def test_project_state_has_independent_milestone_axes_and_truthful_facts(self) -> None:
        state = self.state
        self.assertEqual(state["schema_version"], 2)
        self.assertEqual(state["product_version"], "2.0.13")
        self.assertEqual(state["latest_published_release"], "v2.0.12")
        self.assertEqual(state["observed_main_sha"], CURRENT_MAIN_SHA)
        self.assertRegex(state["observed_at"], r"^2026-09-03T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(set(state["milestones"]), MILESTONES)
        for milestone in state["milestones"].values():
            self.assertEqual(set(milestone), set(AXES))

        expected = {
            "M0": ("complete", "passed", "not_applicable", "delivered", "stale"),
            "M1": ("complete", "passed", "merged", "partial", "success"),
            "M2": ("complete", "passed", "merged", "not_delivered", "success"),
            "M3": ("complete", "passed", "merged", "not_delivered", "success"),
            "M4": ("local_hotfix_candidate", "refresh_pending_after_hotfix", "local_hotfix_rebuilt_after_external_failure", "not_delivered", "not_run_current_candidate"),
            "M5": ("provisional_successor_05_restart_proof_passed", "successor_05_exact_head_review_pending", "bounded_stacked_successors_in_progress", "not_delivered", "not_run"),
            "M6": ("provisional_repair_lifecycle_source", "not_started_exact_head", "blocked_on_m5_acceptance", "not_delivered", "not_run"),
            "M7": ("provisional_shadow_bundle_source", "not_started_exact_head", "blocked_on_m6_acceptance", "not_delivered", "not_run"),
            "M8": ("provisional_typed_m7_wire_source", "not_started_exact_head", "blocked_on_m7_acceptance", "not_delivered", "not_run"),
            "M9": ("provisional_tasks1_4_source", "not_started_exact_head", "blocked_on_m8_acceptance", "not_delivered", "not_run"),
        }
        for milestone, statuses in expected.items():
            actual = self.state["milestones"][milestone]
            self.assertEqual(
                tuple(actual[axis]["status"] for axis in AXES),
                statuses,
            )
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
                "implementation": M4_PRODUCT_SHA,
                "review": M4_PRODUCT_SHA,
                "stack_base": "origin/main",
                "stack_pr": 21,
                "gate_head": None,
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

        m4 = state["milestones"]["M4"]
        self.assertEqual(m4["implementation"]["source_evidence_head"], M4_SOURCE_SHA)
        self.assertEqual(m4["implementation"]["tree"], M4_FINAL_TREE)
        self.assertEqual(m4["implementation"]["artifact_sha256"], M4_FINAL_ARTIFACT_SHA256)
        self.assertEqual(m4["implementation"]["integration_baseline"], M4_INTEGRATION_SHA)
        self.assertEqual(
            m4["implementation"]["latest_committed_repair_checkpoint"],
            M4_PRODUCT_SHA,
        )
        self.assertEqual(m4["review"]["evidence_head"], M4_FAILED_EXTERNAL_SHA)
        self.assertEqual(m4["stack_integration"]["base_commit"], CURRENT_MAIN_SHA)
        self.assertEqual(m4["stack_integration"]["source_head"], M4_SOURCE_SHA)
        self.assertEqual(
            m4["stack_integration"]["latest_committed_repair_checkpoint"],
            M4_PRODUCT_SHA,
        )
        self.assertEqual(
            m4["stack_integration"]["local_hotfix_verification"],
            {
                "status": "passed",
                "head_sha": M4_PRODUCT_SHA,
                "checks": "14/14 local verifier plus 537/537 root unittest and focused different-owner/package checks",
                "tree_fingerprint": "b0a230f6ddc14a643ef9944dfa1fc707a05b84ea2b57ee48f9c10e9f2da160d4",
                "created_at": "2026-09-03T08:08:55Z",
                "notes": "Local evidence binds 9727bc3 only; docs/package changes make it historical, and the App-owned check has not run on this SHA.",
            },
        )
        self.assertIsNone(m4["stack_integration"]["merge_commit"])
        self.assertEqual(m4["external_gate"]["source_pull_request"], 21)
        self.assertEqual(m4["external_gate"]["observed_failed_head"], M4_FAILED_EXTERNAL_SHA)
        self.assertEqual(m4["external_gate"]["observed_failed_check"], "root-unittest")

        m5 = state["milestones"]["M5"]
        self.assertEqual(m5["implementation"]["commit"], M5_RUNTIME_CHECKPOINT)
        self.assertEqual(m5["implementation"]["tree"], M5_RUNTIME_TREE)
        self.assertEqual(m5["implementation"]["frozen_predecessor"], M5_ENROLLMENT_SHA)
        self.assertEqual(m5["stack_integration"]["base_commit"], M5_ENROLLMENT_SHA)
        self.assertEqual(
            state["active_delivery"]["m5_dimensions"]["local_verification"]["runtime_disposable_postgresql_17"],
            "273 tests run: 272 passed and 1 expected fresh-cluster test skipped in 221.516 seconds; two actual restarts and the M5 recovery probe passed",
        )
        self.assertIn(
            "m5_inert_systemd_installer_and_configuration_parity",
            state["active_delivery"]["m5_dimensions"]["blocked_final_gates"],
        )
        self.assertIn("immediate predecessor", m5["stack_integration"]["notes"])
        self.assertIsNone(m5["main_delivery"]["merge_commit"])
        m6 = state["milestones"]["M6"]
        self.assertEqual(m6["implementation"]["commit"], M6_PROVISIONAL_SHA)
        self.assertEqual(m6["implementation"]["tree"], M6_PROVISIONAL_TREE)
        self.assertEqual(m6["implementation"]["required_first_migration"], "018")
        self.assertEqual(
            m6["implementation"]["local_evidence"],
            {
                "status": "historical_component_checks_only",
                "notes": "Earlier Task-2/Task-3 and repair-lifecycle checks exist, but no exact-2d2360c final verifier or complete review receipt is claimed.",
            },
        )
        self.assertIsNone(m6["main_delivery"]["merge_commit"])
        m7 = state["milestones"]["M7"]
        self.assertEqual(m7["implementation"]["commit"], M7_PROVISIONAL_SHA)
        self.assertEqual(m7["implementation"]["tree"], M7_PROVISIONAL_TREE)
        self.assertEqual(
            m7["implementation"]["local_evidence"],
            {
                "focused": "30/30 passed",
                "factory": "100 tests run: 70 passed and 30 expected PostgreSQL skips",
                "receipt": "prior PR preflight interrupted; no exact-head receipt",
            },
        )
        m8 = state["milestones"]["M8"]
        self.assertEqual(m8["implementation"]["starting_head"], M8_STARTING_SHA)
        self.assertEqual(m8["implementation"]["commit"], M8_PROVISIONAL_SHA)
        self.assertEqual(m8["implementation"]["tree"], M8_PROVISIONAL_TREE)
        self.assertEqual(
            m8["implementation"]["local_evidence"],
            {
                "status": "historical_pre_correction_counts_only",
                "notes": "The older 5499c58 test totals do not bind current 2cee9b9 and no final exact-head receipt exists.",
            },
        )
        m9 = state["milestones"]["M9"]
        self.assertEqual(m9["implementation"]["prior_design_head"], M9_DESIGN_SHA)
        self.assertEqual(m9["implementation"]["commit"], M9_PROVISIONAL_SHA)
        self.assertEqual(m9["implementation"]["tree"], M9_PROVISIONAL_TREE)

    def test_m4_source_implementation_is_distinct_from_verification_review_and_delivery(self) -> None:
        dimensions = self.state["active_delivery"]["m4_dimensions"]
        self.assertIn("successor-05", self.state["active_delivery"]["next_action"])
        self.assertIn("fresh external exact-head Trust CI", self.state["active_delivery"]["next_action"])
        self.assertEqual(
            dimensions["implementation_source"],
            {
                "status": "local_hotfix_candidate_unpublished",
                "head_sha": M4_PRODUCT_SHA,
                "source_sha": M4_SOURCE_SHA,
                "tree_sha": M4_FINAL_TREE,
                "artifact_sha256": M4_FINAL_ARTIFACT_SHA256,
                "components": [
                    "typed_intake_and_task_state",
                    "postgresql_migrations_001_013",
                    "leases_fences_capacity_and_retry",
                    "budgets_kills_audit_and_reconciliation",
                    "authenticated_uds_api_cli_and_admin",
                    "disposable_postgresql_and_restart_tests",
                    "tracked_2_0_13_candidate_package",
                ],
            },
        )
        self.assertEqual(
            {
                name: dimensions[name]["status"]
                for name in (
                    "local_exact_head_verification",
                    "independent_review",
                    "pr_external_merge_delivery",
                )
            },
            {
                "local_exact_head_verification": "hotfix_tests_passed_local_only",
                "independent_review": "refresh_pending_after_hotfix",
                "pr_external_merge_delivery": "not_delivered",
            },
        )
        self.assertEqual(dimensions["pr_external_merge_delivery"]["pull_request"], 21)
        self.assertFalse(dimensions["pr_external_merge_delivery"]["contains_current_candidate"])
        self.assertEqual(dimensions["pr_external_merge_delivery"]["external_exact_head_check"], "failed_root_unittest")
        self.assertEqual(dimensions["pr_external_merge_delivery"]["gitguardian_check"], "failure_uninspected")
        m5 = self.state["active_delivery"]["m5_dimensions"]
        self.assertEqual(m5["current_slice"]["implementation_checkpoint"], M5_RUNTIME_CHECKPOINT)
        self.assertEqual(m5["current_slice"]["implementation_tree"], M5_RUNTIME_TREE)
        self.assertEqual(m5["current_slice"]["predecessor_head"], M5_ENROLLMENT_SHA)
        self.assertEqual(m5["current_slice"]["package_status"], "not_created_for_source_slice")
        self.assertEqual(m5["local_verification"]["successor_04_exact_fitness"], "passed_on_8a7be8a_to_27b0ae6")
        self.assertEqual(
            self.state["milestones"]["M4"]["implementation"]["source_status"],
            "source_fix_and_package_rebuilt_local_only",
        )
        self.assertEqual(
            self.state["milestones"]["M5"]["implementation"]["status"],
            "provisional_successor_05_restart_proof_passed",
        )

    def test_local_git_objects_corrobate_durable_stack_proof_when_available(self) -> None:
        milestones = self.state["milestones"]
        integrations = (milestones["M2"]["stack_integration"], milestones["M3"]["stack_integration"])
        required_objects = {
            CURRENT_MAIN_SHA,
            *(integration["merge_commit"] for integration in integrations),
            *(parent for integration in integrations for parent in integration["merge_parents"]),
        }
        objects_available = all(
            subprocess.run(
                ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
                cwd=ROOT,
                check=False,
                capture_output=True,
            ).returncode
            == 0
            for commit in required_objects
        )
        if not objects_available:
            return

        for integration in integrations:
            parents = subprocess.run(
                ["git", "show", "-s", "--format=%P", integration["merge_commit"]],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip().split()
            self.assertEqual(parents, integration["merge_parents"])
            result = subprocess.run(
                ["git", "merge-base", "--is-ancestor", integration["merge_commit"], CURRENT_MAIN_SHA],
                cwd=ROOT,
                check=False,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 1, f"stack merge unexpectedly reached main: {integration['merge_commit']}")

    def test_provisional_m5_m9_git_heads_and_trees_are_correlated_when_available(self) -> None:
        facts = (
            (M5_RUNTIME_CHECKPOINT, M5_RUNTIME_TREE, "milestone/m5-successor-05-runtime-recovery", True),
            (M6_PROVISIONAL_SHA, M6_PROVISIONAL_TREE, "milestone/m6-successor-02-repair-lifecycle", False),
            (M7_PROVISIONAL_SHA, M7_PROVISIONAL_TREE, "milestone/m7-shadow-handoff-provisional-m4", False),
            (M8_PROVISIONAL_SHA, M8_PROVISIONAL_TREE, "milestone/m8-earned-autonomy-provisional-m4", False),
            (M9_PROVISIONAL_SHA, M9_PROVISIONAL_TREE, "milestone/m9-staged-recovery-provisional-m4", False),
        )
        declared = {
            item["branch"]: item["head"]
            for item in self.state["work_inventory"]["active"]
            if item["branch"].startswith("milestone/m")
        }
        self.assertEqual(
            {branch: commit for commit, _tree, branch, _may_be_ancestor in facts},
            {branch: declared[branch] for _commit, _tree, branch, _may_be_ancestor in facts},
        )
        self.assertEqual(
            subprocess.run(
                ["git", "cat-file", "-e", f"{M5_ENROLLMENT_SHA}^{{commit}}"],
                cwd=ROOT,
                check=False,
                capture_output=True,
            ).returncode,
            0,
        )
        for commit, tree, branch, may_be_ancestor in facts:
            with self.subTest(branch=branch):
                ref = f"refs/heads/{branch}"
                self.assertEqual(
                    subprocess.run(
                        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
                        cwd=ROOT,
                        check=False,
                        capture_output=True,
                    ).returncode,
                    0,
                )
                self.assertEqual(
                    subprocess.run(
                        ["git", "show-ref", "--verify", "--quiet", ref],
                        cwd=ROOT,
                        check=False,
                        capture_output=True,
                    ).returncode,
                    0,
                )
                actual_tree = subprocess.run(
                    ["git", "show", "-s", "--format=%T", commit],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
                self.assertEqual(actual_tree, tree)
                if may_be_ancestor:
                    self.assertEqual(
                        subprocess.run(
                            ["git", "merge-base", "--is-ancestor", M5_ENROLLMENT_SHA, commit],
                            cwd=ROOT,
                            check=False,
                            capture_output=True,
                        ).returncode,
                        0,
                    )
                    returncode = subprocess.run(
                        ["git", "merge-base", "--is-ancestor", commit, ref],
                        cwd=ROOT,
                        check=False,
                        capture_output=True,
                    ).returncode
                    self.assertEqual(returncode, 0)
                else:
                    actual_head = subprocess.run(
                        ["git", "rev-parse", ref],
                        cwd=ROOT,
                        check=True,
                        capture_output=True,
                        text=True,
                    ).stdout.strip()
                    self.assertEqual(actual_head, commit)

    def test_current_status_surfaces_bind_checkpoint_and_pending_review_scope(self) -> None:
        central_paths = (
            "README.md",
            "START_HERE.md",
            "DARK_FACTORY_ROADMAP.md",
            "PROJECT_STATE.json",
        )
        central_text = {
            relative: (ROOT / relative).read_text(encoding="utf-8")
            for relative in central_paths
        }
        stale_current_patterns = (
            r"(?im)^Current M7\b[^\n]*c8b450f494b3d44b580556c6a612b21a3a780368",
            r"Current status: clean provisional source `c8b450f494b3d44b580556c6a612b21a3a780368`",
            r"Current status: clean provisional Task-1 head `000301796ac19c518ede110b97b9de09dc077cbd`",
            r"with coherent runtime checkpoint `5073fc05013d1d40c99f22d48db5dd3d4d8c4b87`",
            r"has Task-3 source at `f3b2c0d07116686b27feab4b60166e8a7402d672`",
            r"now has clean provisional contracts, a pure evaluator and demotion behavior at head `5499c582d403c6955324b935cbb8799b38257f5f`",
        )
        stale_checkpoint_by_milestone = {
            "M5": ("5073fc05013d1d40c99f22d48db5dd3d4d8c4b87",),
            "M6": ("f3b2c0d07116686b27feab4b60166e8a7402d672",),
            "M7": ("c8b450f494b3d44b580556c6a612b21a3a780368",),
            "M8": ("5499c582d403c6955324b935cbb8799b38257f5f",),
            "M9": ("000301796ac19c518ede110b97b9de09dc077cbd",),
        }
        current_identity = re.compile(
            r"(?i)\bcurrent(?:[ \t]+[a-z0-9_-]+){0,3}[ \t]+"
            r"(?:head|checkpoint|source|status|commit|sha)\b"
        )
        unbound_review_pass = (
            r"(?i)\b(?:independent(?:ly)?(?:[ \t]+[a-z0-9_/-]+){0,8}[ \t]+)?"
            r"review(?:s|ed)?\b[ \t,:;-]*(?:(?:has|have|is|are|was|were|and)[ \t]+){0,2}"
            r"(?:pass(?:ed)?|green)\b"
        )

        def assert_no_unbound_review_pass(relative: str, text: str) -> None:
            for line in text.splitlines():
                if re.search(r"(?i)\b(?:M5|successor[- ]?0?5|3940267|two[- ]restart)\b", line):
                    self.assertNotRegex(
                        line,
                        unbound_review_pass,
                        f"{relative} claims an exact-head review pass without repository evidence",
                    )

        def assert_no_stale_current_identity(relative: str, text: str) -> None:
            for line in text.splitlines():
                for milestone, stale_checkpoints in stale_checkpoint_by_milestone.items():
                    if not re.search(rf"(?i)\b{milestone}\b", line) or not current_identity.search(line):
                        continue
                    for stale in stale_checkpoints:
                        self.assertNotIn(
                            stale,
                            line,
                            f"{relative} presents stale {milestone} checkpoint as current",
                        )

        def assert_current_status(text_by_path: dict[str, str]) -> None:
            for relative, text in text_by_path.items():
                for current in ("3940267", "2d2360c", "4df2516", "2cee9b9", "6b42ba6"):
                    self.assertIn(current, text, f"{relative} omits current checkpoint {current}")
                self.assertNotRegex(
                    text,
                    r"actual two-restart M5 probe (?:remains|is) (?:open|pending|legacy)",
                    f"{relative} revives the completed restart-proof task",
                )
                for pattern in stale_current_patterns:
                    self.assertNotRegex(text, pattern, f"{relative} revives stale current status")
                assert_no_stale_current_identity(relative, text)
                assert_no_unbound_review_pass(relative, text)

        assert_current_status(central_text)
        adversarial = dict(central_text)
        adversarial["README.md"] += (
            "\nCurrent M7 source is c8b450f494b3d44b580556c6a612b21a3a780368.\n"
        )
        with self.assertRaises(AssertionError):
            assert_current_status(adversarial)
        adversarial_current_heads = dict(central_text)
        adversarial_current_heads["README.md"] += (
            "\nM5 current head is 5073fc05013d1d40c99f22d48db5dd3d4d8c4b87.\n"
            "M7 current head is c8b450f494b3d44b580556c6a612b21a3a780368.\n"
        )
        with self.assertRaises(AssertionError):
            assert_current_status(adversarial_current_heads)
        adversarial_review = dict(central_text)
        adversarial_review["README.md"] += (
            "\nSuccessor 05 3940267 exact-head review PASSED after the two-restart proof.\n"
        )
        with self.assertRaises(AssertionError):
            assert_current_status(adversarial_review)
        adversarial_independent_review = dict(central_text)
        adversarial_independent_review["README.md"] += (
            "\nSuccessor 05 exact head 3940267: independent test and security review PASSED.\n"
        )
        with self.assertRaises(AssertionError):
            assert_current_status(adversarial_independent_review)

        m5_paths = (
            "factory/README.md",
            "packages/README.md",
            "docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md",
            "docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md",
            "engineering/changes/20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/brief.md",
            "engineering/changes/20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/architecture.md",
            "engineering/changes/20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/release.md",
            "engineering/changes/20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/schedule.md",
            "engineering/changes/20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/tasks.md",
            "engineering/changes/20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/test-plan.md",
            "engineering/changes/20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/evidence/README.md",
        )
        for relative in m5_paths:
            with self.subTest(path=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("3940267", text)
                assert_no_stale_current_identity(relative, text)
                assert_no_unbound_review_pass(relative, text)

        m5_review = self.state["milestones"]["M5"]["review"]
        self.assertEqual(m5_review["evidence"], [])
        self.assertIsNone(m5_review["commit"])
        self.assertNotRegex(m5_review["status"], r"pass|reviewed")
        self.assertIn("pending", m5_review["status"])
        self.assertFalse((ROOT / "factory/systemd").exists())
        self.assertFalse((ROOT / "factory/tests/test_systemd_units.py").exists())
        plan = (ROOT / "docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md").read_text(encoding="utf-8")
        design = (ROOT / "docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md").read_text(encoding="utf-8")
        self.assertIn("planned successor 06", plan)
        self.assertIn("planned successor-06", design)

    def test_m2_m3_stack_merge_parent_proof_is_self_contained(self) -> None:
        milestones = self.state["milestones"]
        self.assertEqual(
            {
                milestone["stack_integration"]["merge_commit"]: milestone["stack_integration"].get("merge_parents")
                for milestone in (milestones["M2"], milestones["M3"])
            },
            {
                "c23fd49f80c7d1c74ca3393b6079a74f251a72d8": [
                    "0a4dd0a867c876f99a8fe3580c9f0d47c90e3105",
                    "022411b05924618cfde0cb97b8c8aff4955e6013",
                ],
                "67714a1f1b87effcfabe55d5ca2770d0a68d17c1": [
                    "022411b05924618cfde0cb97b8c8aff4955e6013",
                    "1e73ff9b91d9b711cafccad7ccccb1a992d5e84d",
                ],
            },
        )
        self.assertEqual(milestones["M1"]["stack_integration"], {
            **milestones["M2"]["stack_integration"],
            "notes": "The complete M1 source was accepted as part of the combined M1/M2 stack.",
        })
        self.assertEqual(
            milestones["M2"]["stack_integration"]["merge_parents"][1],
            milestones["M2"]["implementation"]["commit"],
        )
        self.assertEqual(
            milestones["M3"]["stack_integration"]["merge_parents"],
            [
                milestones["M2"]["implementation"]["commit"],
                milestones["M3"]["implementation"]["commit"],
            ],
        )

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

    def test_m4_roadmap_matches_typed_state_machine_and_local_scope(self) -> None:
        factory_src = str(ROOT / "factory" / "src")
        if factory_src not in sys.path:
            sys.path.insert(0, factory_src)
        from adaptive_factory.models import TaskStatus

        roadmap = (ROOT / "DARK_FACTORY_ROADMAP.md").read_text(encoding="utf-8")
        m4 = re.search(r"^# M4 —.*?\n(.*?)(?=^---\n\n# M5 —)", roadmap, re.M | re.S)
        self.assertIsNotNone(m4)
        m4_text = m4.group(1)

        state_section = _section(m4_text, "Factory task state machine")
        blocks = re.findall(r"```text\n(.*?)```", state_section, re.S)
        self.assertEqual(len(blocks), 2)
        primary = re.findall(r"[a-z][a-z0-9_]*", blocks[0])
        exceptional = re.findall(r"[a-z][a-z0-9_]*", blocks[1])
        expected_primary = [
            TaskStatus.INBOX,
            TaskStatus.TRIAGED,
            TaskStatus.WAITING_DESIGN_APPROVAL,
            TaskStatus.QUEUED,
            TaskStatus.LEASED,
            TaskStatus.ANALYZING,
            TaskStatus.IMPLEMENTING,
            TaskStatus.VERIFYING,
            TaskStatus.REVIEWING,
            TaskStatus.READY_FOR_HUMAN,
        ]
        expected_exceptional = {
            TaskStatus.RETRY,
            TaskStatus.NEEDS_HUMAN,
            TaskStatus.DEAD,
            TaskStatus.CANCELLED,
            TaskStatus.SUPERSEDED,
        }
        self.assertEqual(primary, [status.value for status in expected_primary])
        self.assertEqual(set(exceptional), {status.value for status in expected_exceptional})
        self.assertEqual(set(primary) | set(exceptional), {status.value for status in TaskStatus})
        self.assertTrue({"waiting_approval", "pr_open", "ready", "merged"}.isdisjoint(primary + exceptional))

        checked_items = "\n".join(
            line for line in _section(m4_text, "Work items").splitlines() if line.startswith("- [x]")
        )
        self.assertNotRegex(checked_items, r"GitHub|open factory PR|PR age")
        self.assertIn("authenticated manual API/CLI intake", checked_items)
        self.assertIn("PostgreSQL `FOR UPDATE SKIP LOCKED` leases", checked_items)
        self.assertEqual(self.state["milestones"]["M4"]["main_delivery"]["status"], "not_delivered")
        self.assertEqual(self.state["milestones"]["M4"]["external_gate"]["status"], "not_run_current_candidate")

    def test_work_inventory_preserves_open_and_unresolved_continuation_work(self) -> None:
        inventory = self.state["work_inventory"]
        expected_open = [
            {"pull_request": 12, "branch": "fix/human-approval-cli", "base": "main", "head": "0f7f508945ccce7dc4f1bffc463247633e9e8f58", "status": "blocked_old_epoch_action_required", "observed_check_conclusion": "ACTION_REQUIRED", "unique_scope": "Command-local lazy Trust CI CLI imports and their missing regression test are absent from main.", "disposition": "Keep stale; extract the unique scope into a clean successor. No successor PR exists."},
            {"pull_request": 13, "branch": "feat/trust-ci-repository-profiles", "base": "main", "head": "f2fd8a7a00a731fbb7acb90e3c7c7881568c8d80", "status": "blocked_old_epoch_action_required", "observed_check_conclusion": "ACTION_REQUIRED", "unique_scope": "PolicyCatalog repository-policy binding plus fail-closed profile/holdout validation and tests are absent from main.", "disposition": "Keep stale; extract the unique scope into a clean successor. No successor PR exists."},
            {"pull_request": 15, "branch": "mvp/investor-ready", "base": "main", "head": "165d5dd90a2fc2831a3b85be2562a2bb241c8b14", "status": "blocked_current_epoch_failure", "observed_check": CURRENT_CHECK, "observed_check_conclusion": "FAILURE", "gitguardian_conclusion": "SUCCESS", "failure_cause": "not inspected or inferred", "unique_commit": "9dcdf5880b619f29c01dbe76e0f598ff1fad9f9b", "unique_scope": "The investor demo is absent from main; its packaging-stage hardening is superseded by the stronger current M4 package tests.", "disposition": "Wholesale merge is superseded; extract only the investor-demo scope into a clean successor. No successor PR exists."},
            {"pull_request": 21, "branch": "milestone/m4-durable-control-plane-accepted-m3", "base": "main", "head": M4_FAILED_EXTERNAL_SHA, "status": "open_trust_ci_failed_root_unittest", "observed_check": CURRENT_CHECK, "observed_check_conclusion": "FAILURE", "failed_check": "root-unittest", "gitguardian_conclusion": "FAILURE", "gitguardian_finding": "not inspected or inferred", "disposition": "The local 9727bc3 hotfix is not on the PR and will be superseded by a documentation/package-parity descendant. Preserve the failed exact-head results; verify and review the final descendant before any separately authorized PR update and new App-owned exact-head check."},
        ]
        self.assertEqual(inventory["open_pull_requests"], expected_open)
        seo = self.state["delivered_non_milestone_work"][0]
        self.assertEqual(
            {key: seo[key] for key in ("pull_request", "status", "source_head", "merge_commit")},
            {"pull_request": 19, "status": "delivered", "source_head": "ecc85d903d0394f99a139fd4e74a7cc452e386c6", "merge_commit": SEO_MERGE_SHA},
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
                ("b7f288f1e81e", "integration/m4-main-20260902"),
                ("37b05f579320", "milestone/m5-successor-04-contract-enrollment"),
                ("37b05f579320", "milestone/m5-successor-05-runtime-recovery"),
                ("82aac86a3bf9", "milestone/m6-successor-02-repair-lifecycle"),
                ("e5911c3f8721", "milestone/m7-shadow-handoff-provisional-m4"),
                ("670ffe5522e0", "milestone/m8-earned-autonomy-provisional-m4"),
                ("e376373492fe", "milestone/m9-staged-recovery-provisional-m4"),
            ],
        )
        self.assertEqual(inventory["active"][0]["head"], M4_PRODUCT_SHA)
        self.assertEqual(inventory["active"][0]["tree"], M4_FINAL_TREE)
        self.assertEqual(inventory["active"][0]["artifact_sha256"], M4_FINAL_ARTIFACT_SHA256)
        self.assertEqual(inventory["active"][0]["source_head"], M4_SOURCE_SHA)
        self.assertEqual(inventory["active"][1]["head"], M5_ENROLLMENT_SHA)
        self.assertEqual(inventory["active"][1]["tree"], M5_ENROLLMENT_TREE)
        self.assertEqual(inventory["active"][2]["head"], M5_RUNTIME_CHECKPOINT)
        self.assertEqual(inventory["active"][2]["tree"], M5_RUNTIME_TREE)
        self.assertEqual(inventory["active"][2]["worktree"], "product_checkpoint_committed_with_documentation_rebind")
        self.assertEqual(inventory["active"][3]["head"], M6_PROVISIONAL_SHA)
        self.assertEqual(inventory["active"][3]["tree"], M6_PROVISIONAL_TREE)
        self.assertEqual(inventory["active"][4]["head"], M7_PROVISIONAL_SHA)
        self.assertEqual(inventory["active"][4]["tree"], M7_PROVISIONAL_TREE)
        self.assertEqual(inventory["active"][5]["starting_head"], M8_STARTING_SHA)
        self.assertEqual(inventory["active"][5]["head"], M8_PROVISIONAL_SHA)
        self.assertEqual(inventory["active"][5]["tree"], M8_PROVISIONAL_TREE)
        self.assertEqual(inventory["active"][6]["prior_design_head"], M9_DESIGN_SHA)
        self.assertEqual(inventory["active"][6]["head"], M9_PROVISIONAL_SHA)
        self.assertEqual(inventory["active"][6]["tree"], M9_PROVISIONAL_TREE)
        self.assertIn(1, {item.get("pull_request") for item in inventory["superseded"]})
        self.assertIn(
            {
                "pull_request": 17,
                "branch": "milestone/m4-durable-control-plane-accepted-m3",
                "base": "milestone/m2-executable-architecture",
                "head": M4_HISTORICAL_SOURCE_SHA,
                "status": "closed_duplicate",
                "closed_at": "2026-09-02T10:08:38Z",
                "duplicate_of": 21,
                "reason": "Closed because it exactly duplicated open PR 21 at the same head; it provides no separate delivery authority.",
            },
            inventory["superseded"],
        )

    def test_adversarial_pr21_base_head_and_status_are_rejected(self) -> None:
        original = self.state
        mutated = copy.deepcopy(original)
        pr21 = next(item for item in mutated["work_inventory"]["open_pull_requests"] if item["pull_request"] == 21)
        pr21.update(base="milestone/m2-executable-architecture", head="0" * 40, status="success")
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
        mutated["milestones"]["M2"]["stack_integration"]["merge_parents"] = [CURRENT_MAIN_SHA, "0" * 40]
        mutated["milestones"]["M3"]["stack_integration"]["merge_parents"] = ["f" * 40, CURRENT_MAIN_SHA]
        self.state = mutated
        try:
            with self.assertRaises(AssertionError):
                self.test_m2_m3_stack_merge_parent_proof_is_self_contained()
        finally:
            self.state = original

    def test_readme_graph_is_exact_complete_k22(self) -> None:
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
