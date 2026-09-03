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
M4_PRODUCT_SHA = "4f75558770f2f332b32b4a47fe6afa61fcc524ec"
M4_SOURCE_SHA = "460a8a01a6394cac710b4e3f9eea3d94d4beef89"
M4_INTEGRATION_SHA = "da7ec8d7d40f52663aba1ff59bf03ccf209395b0"
M4_SCANNER_REPAIR_SHA = "5a6cdfb7a129e02724c632f78c31de6406d6863a"
M4_RELEASE_STATE_BASE_SHA = "56e12b2b394436ee227c66d78b1caba8f7317c78"
M4_REPAIR_CHECKPOINT_SHA = "9da561aad818db73c0601e6d20f8c208f905fb07"
M4_RELEASE_STATE_BASE_FINGERPRINT = "e27caec9d2de459ef26bea49b99b93b5b7326a9c84c89b97f4ec482c237d4add"
M4_FAILED_VERIFY_SHA = "547ee628812fbf098f337a854f68edf660091ead"
M4_FAILED_VERIFY_FINGERPRINT = "f0efa89e689dbe47c701a4d301e97361ee671e299ef2f32b5295b908e182e768"
M5_PROVISIONAL_SHA = "141e51e75b2bb337fa3bb1544639c6c46c287309"
M6_TASK1_SHA = "3def83eb915ca68e66379269526ffa64822a1104"
M6_TASK2_SHA = "a8ca0f3afffbd9ef5584825252f9a669a324d2a5"
M6_PROVISIONAL_SHA = "f3b2c0d07116686b27feab4b60166e8a7402d672"
M7_PROVISIONAL_SHA = "c8b450f494b3d44b580556c6a612b21a3a780368"
M8_STARTING_SHA = "46a6c8eba6b5bd8e4654f3041e52061cdd1a15d6"
M8_PROVISIONAL_SHA = "5735e762b8d7571887f6fa4ac9cf10cd1fad1954"
M9_DESIGN_SHA = "055051e26e26bf08fa85376523ba6632afcca747"
M9_PROVISIONAL_SHA = "000301796ac19c518ede110b97b9de09dc077cbd"
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
        self.assertRegex(state["observed_at"], r"^2026-09-02T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(set(state["milestones"]), MILESTONES)
        for milestone in state["milestones"].values():
            self.assertEqual(set(milestone), set(AXES))

        expected = {
            "M0": ("complete", "passed", "not_applicable", "delivered", "stale"),
            "M1": ("complete", "passed", "merged", "partial", "success"),
            "M2": ("complete", "passed", "merged", "not_delivered", "success"),
            "M3": ("complete", "passed", "merged", "not_delivered", "success"),
            "M4": ("complete", "pending_refresh", "local_integrated_candidate", "not_delivered", "not_run"),
            "M5": ("provisional_source_complete", "pending_final", "blocked_on_m4_acceptance", "not_delivered", "blocked"),
            "M6": ("provisional_task3_source", "not_started", "blocked_on_m5_acceptance", "not_delivered", "not_run"),
            "M7": ("provisional_algorithm_source", "not_started", "blocked_on_m6_acceptance", "not_delivered", "not_run"),
            "M8": ("provisional_task1_source", "not_started", "blocked_on_m7_acceptance", "not_delivered", "not_run"),
            "M9": ("provisional_task1_source", "not_started", "blocked_on_m8_acceptance", "not_delivered", "not_run"),
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
                "stack_pr": None,
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
        self.assertEqual(m4["implementation"]["integration_baseline"], M4_INTEGRATION_SHA)
        self.assertEqual(
            m4["implementation"]["latest_committed_repair_checkpoint"],
            M4_REPAIR_CHECKPOINT_SHA,
        )
        self.assertEqual(
            m4["implementation"]["current_candidate_identity"],
            "repository tree containing this PROJECT_STATE.json",
        )
        self.assertEqual(m4["review"]["evidence_head"], M4_SOURCE_SHA)
        self.assertEqual(m4["stack_integration"]["base_commit"], CURRENT_MAIN_SHA)
        self.assertEqual(m4["stack_integration"]["source_head"], M4_SOURCE_SHA)
        self.assertEqual(m4["stack_integration"]["merge_parents"], [M4_SOURCE_SHA, CURRENT_MAIN_SHA])
        self.assertEqual(m4["stack_integration"]["intermediate_code_head"], M4_INTEGRATION_SHA)
        self.assertEqual(
            m4["stack_integration"]["latest_committed_repair_checkpoint"],
            M4_REPAIR_CHECKPOINT_SHA,
        )
        self.assertEqual(
            m4["stack_integration"]["intermediate_local_verification"],
            {
                "status": "passed",
                "head_sha": M4_INTEGRATION_SHA,
                "checks_passed": 14,
                "checks_total": 14,
                "changed_files": 469,
                "notes": "Historical exact-code-head preflight only; subsequent repair commits and this migration/docs tree require a final rerun before completion.",
            },
        )
        self.assertEqual(
            m4["stack_integration"]["repair_local_verification"],
            {
                "status": "failed",
                "head_sha": M4_FAILED_VERIFY_SHA,
                "tree_fingerprint": M4_FAILED_VERIFY_FINGERPRINT,
                "checks_passed": 13,
                "checks_total": 14,
                "failed_check": "secret-scan",
                "created_at": "2026-09-02T10:08:32Z",
                "repair_head": M4_SCANNER_REPAIR_SHA,
                "notes": "The sole generic-secret finding was repaired in synthetic test fixtures and superseded by the passing release-state verification at 56e12b2.",
            },
        )
        self.assertEqual(
            m4["stack_integration"]["release_state_local_verification"],
            {
                "status": "passed",
                "head_sha": M4_RELEASE_STATE_BASE_SHA,
                "tree_fingerprint": M4_RELEASE_STATE_BASE_FINGERPRINT,
                "checks_passed": 14,
                "checks_total": 14,
                "created_at": "2026-09-02T10:51:29Z",
                "notes": "Exact baseline receipt only; the current follow-up changes source and package bytes, so the receipt does not transfer.",
            },
        )
        self.assertIsNone(m4["stack_integration"]["merge_commit"])
        self.assertEqual(m4["external_gate"]["source_pull_request"], 21)
        self.assertEqual(m4["external_gate"]["source_head"], M4_SOURCE_SHA)
        self.assertEqual(m4["external_gate"]["source_trust_ci_status"], "success")
        self.assertEqual(m4["external_gate"]["source_gitguardian_status"], "failure_metadata_only")

        m5 = state["milestones"]["M5"]
        self.assertEqual(m5["implementation"]["commit"], M5_PROVISIONAL_SHA)
        self.assertEqual(m5["stack_integration"]["base_commit"], "94fc5ad878e6b15df6418303caada49a3b93bf4c")
        self.assertIsNone(m5["main_delivery"]["merge_commit"])
        m6 = state["milestones"]["M6"]
        self.assertEqual(m6["implementation"]["commit"], M6_PROVISIONAL_SHA)
        self.assertEqual(m6["implementation"]["task1_head"], M6_TASK1_SHA)
        self.assertEqual(m6["implementation"]["task2_head"], M6_TASK2_SHA)
        self.assertEqual(
            m6["implementation"]["local_evidence"],
            {
                "task2": {"tests_passed": 209, "tests_total": 209, "actual_restart": "passed"},
                "task3": {
                    "focused_passed": 67,
                    "focused_total": 67,
                    "legacy_passed": 40,
                    "legacy_total": 40,
                    "postgresql17_passed": 1,
                    "postgresql17_total": 1,
                    "architecture_checks": "passed",
                },
            },
        )
        self.assertIsNone(m6["main_delivery"]["merge_commit"])
        m7 = state["milestones"]["M7"]
        self.assertEqual(m7["implementation"]["commit"], M7_PROVISIONAL_SHA)
        m8 = state["milestones"]["M8"]
        self.assertEqual(m8["implementation"]["starting_head"], M8_STARTING_SHA)
        self.assertEqual(m8["implementation"]["commit"], M8_PROVISIONAL_SHA)
        m9 = state["milestones"]["M9"]
        self.assertEqual(m9["implementation"]["prior_design_head"], M9_DESIGN_SHA)
        self.assertEqual(m9["implementation"]["commit"], M9_PROVISIONAL_SHA)

    def test_m4_source_implementation_is_distinct_from_verification_review_and_delivery(self) -> None:
        dimensions = self.state["active_delivery"]["m4_dimensions"]
        self.assertTrue(
            self.state["active_delivery"]["next_action"].startswith(
                "Run local exact-head verification and all route-selected reviews"
            )
        )
        self.assertEqual(
            dimensions["implementation_source"],
            {
                "status": "implemented_local_candidate",
                "components": [
                    "typed_intake_and_task_state",
                    "postgresql_migrations_001_013",
                    "leases_fences_capacity_and_retry",
                    "budgets_kills_audit_and_reconciliation",
                    "semantic_work_identity_and_command_replay",
                    "bounded_immutable_lifecycle_history_and_fenced_phases",
                    "sole_checked_closed_inline_17_operation_http_contract",
                    "authenticated_uds_api_cli_and_admin",
                    "disposable_postgresql_and_restart_tests",
                    "rebuilt_tracked_2_0_13_candidate_from_preceding_clean_source_head",
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
                "local_exact_head_verification": "receipt_required_for_current_exact_head",
                "independent_review": "rereview_required_for_current_exact_head",
                "pr_external_merge_delivery": "not_delivered",
            },
        )
        self.assertEqual(
            self.state["milestones"]["M4"]["implementation"]["source_status"],
            "implemented_local_candidate",
        )
        self.assertEqual(
            self.state["milestones"]["M5"]["implementation"]["status"],
            "provisional_source_complete",
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
        self.assertEqual(self.state["milestones"]["M4"]["external_gate"]["status"], "not_run")

    def test_work_inventory_preserves_open_and_unresolved_continuation_work(self) -> None:
        inventory = self.state["work_inventory"]
        expected_open = [
            {"pull_request": 12, "branch": "fix/human-approval-cli", "base": "main", "head": "0f7f508945ccce7dc4f1bffc463247633e9e8f58", "status": "blocked_old_epoch_action_required", "observed_check_conclusion": "ACTION_REQUIRED", "unique_scope": "Lazy CLI imports and tests are absent from main.", "disposition": "Keep stale; extract the unique scope into a clean successor. No successor PR exists."},
            {"pull_request": 13, "branch": "feat/trust-ci-repository-profiles", "base": "main", "head": "f2fd8a7a00a731fbb7acb90e3c7c7881568c8d80", "status": "blocked_old_epoch_action_required", "observed_check_conclusion": "ACTION_REQUIRED", "unique_scope": "Repository-scoped Trust CI profiles are absent from main.", "disposition": "Keep stale; extract the unique scope into a clean successor. No successor PR exists."},
            {"pull_request": 15, "branch": "mvp/investor-ready", "base": "main", "head": "165d5dd90a2fc2831a3b85be2562a2bb241c8b14", "status": "blocked_current_epoch_failure", "observed_check": CURRENT_CHECK, "observed_check_conclusion": "FAILURE", "gitguardian_conclusion": "SUCCESS", "failure_cause": "not inspected or inferred", "unique_commit": "9dcdf5880b619f29c01dbe76e0f598ff1fad9f9b", "unique_scope": "Investor demo and packaging hardening are absent from main.", "disposition": "Wholesale merge is superseded; extract the unique scope into a clean successor. No successor PR exists."},
            {"pull_request": 21, "branch": "milestone/m4-durable-control-plane-accepted-m3", "base": "main", "head": M4_SOURCE_SHA, "status": "open_trust_ci_success_gitguardian_failure", "disposition": "Preserve check metadata without inspecting or dismissing the finding; the new current-main merge tree requires fresh verification and exact-head checks."},
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
                ("37b05f579320", "milestone/m5-isolated-execution-provisional-m4"),
                ("82aac86a3bf9", "milestone/m6-semantic-validation-provisional-m4"),
                ("e5911c3f8721", "milestone/m7-shadow-handoff-provisional-m4"),
                ("670ffe5522e0", "milestone/m8-earned-autonomy-provisional-m4"),
                ("e376373492fe", "milestone/m9-staged-recovery-provisional-m4"),
            ],
        )
        self.assertEqual(inventory["active"][0]["source_head"], M4_SOURCE_SHA)
        self.assertEqual(inventory["active"][0]["base_head"], CURRENT_MAIN_SHA)
        self.assertEqual(inventory["active"][0]["intermediate_code_head"], M4_INTEGRATION_SHA)
        self.assertEqual(
            inventory["active"][0]["latest_committed_repair_checkpoint"],
            M4_REPAIR_CHECKPOINT_SHA,
        )
        self.assertEqual(inventory["active"][1]["head"], M5_PROVISIONAL_SHA)
        self.assertEqual(inventory["active"][2]["task1_head"], M6_TASK1_SHA)
        self.assertEqual(inventory["active"][2]["task2_head"], M6_TASK2_SHA)
        self.assertEqual(inventory["active"][2]["head"], M6_PROVISIONAL_SHA)
        self.assertEqual(inventory["active"][3]["head"], M7_PROVISIONAL_SHA)
        self.assertEqual(inventory["active"][4]["starting_head"], M8_STARTING_SHA)
        self.assertEqual(inventory["active"][4]["head"], M8_PROVISIONAL_SHA)
        self.assertEqual(inventory["active"][5]["prior_design_head"], M9_DESIGN_SHA)
        self.assertEqual(inventory["active"][5]["head"], M9_PROVISIONAL_SHA)
        self.assertIn(1, {item.get("pull_request") for item in inventory["superseded"]})
        self.assertIn(
            {
                "pull_request": 17,
                "branch": "milestone/m4-durable-control-plane-accepted-m3",
                "base": "milestone/m2-executable-architecture",
                "head": M4_SOURCE_SHA,
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
