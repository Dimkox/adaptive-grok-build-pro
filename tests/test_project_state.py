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
CURRENT_MAIN_SHA = "1751b5855e46782b9a1bfceb6e1ab0102cba03b0"
RELEASE_MERGE_SHA = "8599d45f4f28285381b05a53feb3059de92eb2a8"
HISTORICAL_M4_BASE_SHA = "78ad2f679d38dc3244e716c586332417e610089c"
RELEASE_HEAD_SHA = "b5eba759c309a92f92f4d4003d025795c7f8a1f9"
RELEASE_TREE = "03e122a30fb2dbb59907f4c4c28e17f93cbf0751"
RELEASE_ZIP_SHA256 = "3d5179f589c507143f4b93a98d2518e37e470e8566a62f77b31c35743ed8240c"
CURRENT_RELEASE_HEAD_SHA = "66a7fe5c4a59b3ea7e1350b34e0a547faf5a9f57"
CURRENT_RELEASE_TREE = "618df086920c92179aa0e22a8c8d4ad30ebd9230"
CURRENT_RELEASE_ZIP_SHA256 = "b03c64e67ac757f7d84abfed407cbd0ace2771afd960c67e24684099b3cc0264"
CURRENT_RELEASE_SIDECAR_SHA256 = "1a961c35b8f12fa02579ec7888c889f0ae7ca8656b158eb731681ef8357caf3c"
CURRENT_LANDING_SHA = "699010380f4f90a0193a9c22090c35e6aded7d2c"
CURRENT_LANDING_TREE = "f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4"
PR21_HEAD_SHA = "571cad7877431ac5ab5779b53fe9f7effd6859ce"
SEO_MERGE_SHA = "8ab4e57038dec2e07f01aaa0b207813a387358f4"
M4_PRODUCT_SHA = "67dc4ddfc8043608aa7a0ef6396c7c0e158d18f4"
M4_REVIEW_SHA = "4f75558770f2f332b32b4a47fe6afa61fcc524ec"
M4_SOURCE_SHA = "460a8a01a6394cac710b4e3f9eea3d94d4beef89"
M4_INTEGRATION_SHA = "da7ec8d7d40f52663aba1ff59bf03ccf209395b0"
M4_SCANNER_REPAIR_SHA = "5a6cdfb7a129e02724c632f78c31de6406d6863a"
M4_RELEASE_STATE_BASE_SHA = "56e12b2b394436ee227c66d78b1caba8f7317c78"
M4_REPAIR_CHECKPOINT_SHA = "47b1c0ab5f27bc946cd1b2682de68b4ca3c67a95"
M4_RELEASE_STATE_BASE_FINGERPRINT = "e27caec9d2de459ef26bea49b99b93b5b7326a9c84c89b97f4ec482c237d4add"
M4_FAILED_VERIFY_SHA = "547ee628812fbf098f337a854f68edf660091ead"
M4_FAILED_VERIFY_FINGERPRINT = "f0efa89e689dbe47c701a4d301e97361ee671e299ef2f32b5295b908e182e768"
M5_PROVISIONAL_SHA = "85cd4343143915ce9342634e7fe81886b6394871"
M6_PROVISIONAL_SHA = "c6d48ffd8594b3baab1a575021452ea5dfa2a98b"
M7_PROVISIONAL_SHA = "00e0e4f9a6f50844bf9e0ffc7139d3283dda889f"
M8_PROVISIONAL_SHA = "a937ac8d200a4e143c295fabd482b19bc8cc4286"
M9_PROVISIONAL_SHA = "64b10689ce78a0464a494440f3fa981e18789687"
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
        self.assertEqual(state["product_version"], "2.0.14")
        self.assertEqual(state["latest_published_release"], "v2.0.14")
        self.assertEqual(state["observed_main_sha"], CURRENT_MAIN_SHA)
        self.assertRegex(state["observed_at"], r"^2026-09-04T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(set(state["milestones"]), MILESTONES)
        for milestone in state["milestones"].values():
            self.assertEqual(set(milestone), set(AXES))

        expected = {
            "M0": ("complete", "passed", "not_applicable", "delivered", "stale"),
            "M1": ("complete", "passed", "merged", "delivered", "success"),
            "M2": ("complete", "passed", "merged", "delivered", "success"),
            "M3": ("complete", "passed", "merged", "delivered", "success"),
            "M4": ("complete", "passed_for_release_head", "included_in_v2.0.13_delivery", "delivered", "success"),
            "M5": ("delivered_to_main", "passed_for_release_head", "included_in_v2.0.13_delivery", "delivered", "success"),
            "M6": ("delivered_to_main", "passed_for_release_head", "included_in_v2.0.13_delivery", "delivered", "success"),
            "M7": ("delivered_to_main", "passed_for_release_head", "included_in_v2.0.13_delivery", "delivered", "success"),
            "M8": ("delivered_to_main", "passed_for_release_head", "included_in_v2.0.13_delivery", "delivered", "success"),
            "M9": ("delivered_to_main", "passed_for_release_head", "included_in_v2.0.13_delivery", "delivered", "success"),
        }
        for milestone, statuses in expected.items():
            actual = self.state["milestones"][milestone]
            self.assertEqual(
                tuple(actual[axis]["status"] for axis in AXES),
                statuses,
            )
        self.assertEqual(
            self.state["delivered_milestones_on_main"],
            ["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"],
        )
        self.assertEqual(
            self.state["implemented_milestones"],
            ["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"],
        )
        repair = state["current_unreleased_change"]
        self.assertEqual(repair["route_id"], "eb3f80383d44")
        self.assertEqual(repair["branch"], "feature/l5-current-landing-source")
        self.assertEqual(repair["landing_source"]["commit"], CURRENT_LANDING_SHA)
        self.assertEqual(repair["landing_source"]["tree"], CURRENT_LANDING_TREE)
        self.assertTrue(repair["landing_source"]["read_only"])
        self.assertEqual(repair["write_paths"], ["content.css", "index.html"])
        self.assertEqual(repair["protected_source_member"], "index.css")
        self.assertEqual(repair["deploy_member_count"], 20)
        self.assertEqual(repair["focused_tests"], {"status": "passed", "count": 47})
        self.assertEqual(repair["full_verifier"], "pending")
        self.assertEqual(repair["independent_reviews"], "pending")
        self.assertFalse(repair["package_rebuild"])
        self.assertFalse(repair["external_effect"])

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
                "main_merge": RELEASE_MERGE_SHA,
            },
            "M2": {
                "implementation": "022411b05924618cfde0cb97b8c8aff4955e6013",
                "review": "022411b05924618cfde0cb97b8c8aff4955e6013",
                "stack_base": "milestone/m1-typed-intent-evidence",
                "stack_pr": 10,
                "stack_merge": "c23fd49f80c7d1c74ca3393b6079a74f251a72d8",
                "gate_head": "022411b05924618cfde0cb97b8c8aff4955e6013",
                "main_merge": RELEASE_MERGE_SHA,
            },
            "M3": {
                "implementation": "1e73ff9b91d9b711cafccad7ccccb1a992d5e84d",
                "review": "1e73ff9b91d9b711cafccad7ccccb1a992d5e84d",
                "stack_base": "milestone/m2-executable-architecture",
                "stack_pr": 11,
                "stack_merge": "67714a1f1b87effcfabe55d5ca2770d0a68d17c1",
                "gate_head": "1e73ff9b91d9b711cafccad7ccccb1a992d5e84d",
                "main_merge": RELEASE_MERGE_SHA,
            },
            "M4": {
                "implementation": M4_PRODUCT_SHA,
                "review": M4_REVIEW_SHA,
                "stack_base": "origin/main",
                "stack_pr": 22,
                "gate_head": RELEASE_HEAD_SHA,
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
            "v2.0.13",
        )
        self.assertEqual(m4["review"]["evidence_head"], M4_SOURCE_SHA)
        self.assertEqual(m4["stack_integration"]["base_commit"], HISTORICAL_M4_BASE_SHA)
        self.assertEqual(m4["stack_integration"]["source_head"], M4_SOURCE_SHA)
        self.assertEqual(
            m4["stack_integration"]["merge_parents"],
            [M4_SOURCE_SHA, HISTORICAL_M4_BASE_SHA],
        )
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
        self.assertEqual(m4["stack_integration"]["merge_commit"], RELEASE_MERGE_SHA)
        self.assertEqual(m4["external_gate"]["pull_request"], 22)
        self.assertEqual(m4["external_gate"]["head_sha"], RELEASE_HEAD_SHA)
        self.assertEqual(m4["external_gate"]["check_run_id"], 100955508827)
        self.assertEqual(
            m4["external_gate"]["attestation_id"],
            "74f1bbb2-3098-4d35-a42f-d49351d81c4a",
        )
        self.assertEqual(m4["external_gate"]["historical_source_pull_request"], 21)
        self.assertEqual(m4["external_gate"]["historical_source_head"], M4_SOURCE_SHA)

        m5 = state["milestones"]["M5"]
        self.assertEqual(m5["implementation"]["commit"], M5_PROVISIONAL_SHA)
        self.assertEqual(m5["stack_integration"]["base_commit"], M4_PRODUCT_SHA)
        self.assertEqual(m5["main_delivery"]["merge_commit"], RELEASE_MERGE_SHA)
        m6 = state["milestones"]["M6"]
        self.assertEqual(m6["implementation"]["commit"], M6_PROVISIONAL_SHA)
        self.assertEqual(m6["main_delivery"]["merge_commit"], RELEASE_MERGE_SHA)
        m7 = state["milestones"]["M7"]
        self.assertEqual(m7["implementation"]["commit"], M7_PROVISIONAL_SHA)
        m8 = state["milestones"]["M8"]
        self.assertEqual(m8["implementation"]["commit"], M8_PROVISIONAL_SHA)
        m9 = state["milestones"]["M9"]
        self.assertEqual(m9["implementation"]["commit"], M9_PROVISIONAL_SHA)
        self.assertEqual(m9["stack_integration"]["base_commit"], M8_PROVISIONAL_SHA)
        self.assertEqual(m9["main_delivery"]["pull_request"], 22)
        self.assertEqual(m9["main_delivery"]["merge_commit"], RELEASE_MERGE_SHA)

        published = state["published_release"]
        self.assertEqual(published["tag"], "v2.0.14")
        self.assertEqual(published["checked_head"], CURRENT_RELEASE_HEAD_SHA)
        self.assertEqual(published["merge_commit"], CURRENT_MAIN_SHA)
        self.assertEqual(published["tree"], CURRENT_RELEASE_TREE)
        self.assertEqual(published["artifact"]["sha256"], CURRENT_RELEASE_ZIP_SHA256)
        self.assertEqual(
            published["artifact"]["sidecar_sha256"],
            CURRENT_RELEASE_SIDECAR_SHA256,
        )
        prior = state["prior_published_releases"]
        self.assertEqual(len(prior), 1)
        self.assertEqual(prior[0]["tag"], "v2.0.13")
        self.assertEqual(prior[0]["checked_head"], RELEASE_HEAD_SHA)
        self.assertEqual(prior[0]["merge_commit"], RELEASE_MERGE_SHA)
        self.assertEqual(prior[0]["tree"], RELEASE_TREE)
        self.assertEqual(prior[0]["artifact"]["sha256"], RELEASE_ZIP_SHA256)
        self.assertEqual(
            state["local_candidate"],
            {
                "version": "2.0.14",
                "status": "published",
                "route_id": "9f67efd2575c",
                "branch": "feature/l5-multimodal-landing-factory",
                "change_package": "engineering/changes/20260904-l5-multimodal-landing-dogfood-9f67ef",
                "source_base": "b10a5c474883e30dcaf781d104cbb804f031b52f",
                "reviewed_product_head": "5f47508f3c0d52b71a3c866969cc28b6476a9d99",
                "reviewed_product_tree": "0ae72773d73a294b88a398cec9926f6fca2f5555",
                "reviewed_policy_head": "58c9caed5d2c8f9febba297430a0782438505d82",
                "reviewed_policy_tree": "975bf7a21784bf91279a684bdeb5f5394fb715a1",
                "source_gate_status": "passed_for_artifact_head",
                "review_status": "four_route_selected_reviews_passed",
                "checked_head": CURRENT_RELEASE_HEAD_SHA,
                "merge_commit": CURRENT_MAIN_SHA,
                "tree": CURRENT_RELEASE_TREE,
                "pull_request": 24,
                "artifact_status": "published_tag_bound",
                "artifact_child": {
                    "identity": "A",
                    "source_parent": "5b33a384e853ad6e1b945898f9ed5e54329dd2ad",
                    "source_parent_tree": "b4b0c5cc45469e57c7c8f5d1a4a4a31182c1dfce",
                    "commit": CURRENT_RELEASE_HEAD_SHA,
                    "tree": CURRENT_RELEASE_TREE,
                    "delta_paths": [
                        "packages/adaptive-grok-build-pro-v2.0.14.zip",
                        "packages/adaptive-grok-build-pro-v2.0.14.zip.sha256",
                    ],
                    "zip_sha256": CURRENT_RELEASE_ZIP_SHA256,
                    "sidecar_sha256": CURRENT_RELEASE_SIDECAR_SHA256,
                    "status": "published_as_v2.0.14",
                },
                "published": True,
                "published_at": "2026-09-04T16:58:48Z",
                "external_effect": True,
                "external_effect_scope": "github_repository_delivery_and_release_only",
                "operational_activation": False,
                "notes": "The L5 landing source and artifact are published as repository product v2.0.14. Provider and publisher defaults remain unavailable, with no operational provider, target mutation, hosting, indexing, deployment, M8 activation, or production authority.",
            },
        )

    def test_m4_source_implementation_is_distinct_from_verification_review_and_delivery(self) -> None:
        dimensions = self.state["active_delivery"]["m4_dimensions"]
        self.assertEqual(
            self.state["active_delivery"]["status"],
            "v2.0.14_published_repository_delivery_complete",
        )
        self.assertTrue(
            self.state["active_delivery"]["next_action"].startswith(
                "No repository-release action remains for v2.0.14"
            )
        )
        source_gate = self.state["active_delivery"]["local_source_gate"]
        self.assertEqual(source_gate["status"], "passed_for_artifact_head")
        self.assertEqual(source_gate["product_head"], "5f47508f3c0d52b71a3c866969cc28b6476a9d99")
        self.assertEqual(source_gate["policy_head"], "58c9caed5d2c8f9febba297430a0782438505d82")
        self.assertEqual(source_gate["reviews"], "four_route_selected_reviews_passed")
        self.assertEqual(source_gate["artifact_head"], CURRENT_RELEASE_HEAD_SHA)
        self.assertEqual(source_gate["artifact_tree"], CURRENT_RELEASE_TREE)
        self.assertEqual(source_gate["artifact_verification"], "passed")
        self.assertEqual(self.state["active_delivery"]["route_id"], "9f67efd2575c")
        self.assertEqual(
            self.state["active_delivery"]["branch"],
            "feature/l5-multimodal-landing-factory",
        )
        self.assertEqual(
            dimensions["implementation_source"],
            {
                "status": "delivered_to_main",
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
                    "restored_m2_and_nested_factory_architecture_budgets",
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
                "local_exact_head_verification": "passed_for_release_head",
                "independent_review": "passed_for_release_head",
                "pr_external_merge_delivery": "published",
            },
        )
        self.assertEqual(
            self.state["milestones"]["M4"]["implementation"]["source_status"],
            "delivered_to_main",
        )
        self.assertEqual(
            self.state["milestones"]["M5"]["implementation"]["status"],
            "delivered_to_main",
        )

    def test_m4_handoff_does_not_make_an_unconditional_stale_package_claim(self) -> None:
        surfaces = (
            'README.md',
            'START_HERE.md',
            'packages/README.md',
            'PROJECT_STATE.json',
            'DARK_FACTORY_ROADMAP.md',
            'engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/release.md',
            'engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/tasks.md',
        )
        forbidden = (
            'currently stale candidate package',
            'tracked stale local artifact',
            'tracked zip is a stale local artifact',
            'zip/sidecar are stale',
            'zip/sidecar were built from an earlier tree and are stale',
            'previous 2.0.13 files remain stale',
            'tracked archive still represents an earlier tree and must be rebuilt',
        )
        for relative in surfaces:
            content = (ROOT / relative).read_text(encoding='utf-8').lower()
            for claim in forbidden:
                self.assertNotIn(claim, content, (relative, claim))

    def test_delivery_schedule_is_dependency_relative_and_does_not_revive_missed_dates(self) -> None:
        schedule = self.state["active_delivery"]["schedule"]
        self.assertEqual(schedule["basis"], "dependency_relative")
        self.assertEqual(schedule["m4_local_ready_target"], "2026-09-03")
        self.assertEqual(
            schedule["t0"],
            {
                "definition": "externally accepted exact M4 SHA",
                "status": "accepted_via_pr22",
                "sha": RELEASE_HEAD_SHA,
                "accepted_at": "2026-09-04T08:31:49Z",
                "requires": [
                    "separately_authorized_pull_request",
                    "exact_sha_external_trust_ci",
                    "protected_merge_and_acceptance_record",
                ],
            },
        )
        self.assertEqual(
            schedule["sequential_acceptance_order"],
            ["M4", "M5", "M6", "M7", "M8", "M9"],
        )
        self.assertEqual(schedule["m8_calendar"]["status"], "indeterminate")
        self.assertEqual(schedule["m8_calendar"]["minimum_human_accepted_tasks"], 30)
        self.assertEqual(
            schedule["m9_entry_requires"],
            [
                "accepted_m8",
                "signed_artifact",
                "environment_evidence",
                "recovery_evidence",
            ],
        )
        self.assertEqual(
            schedule["superseded_target"],
            {
                "at": "2026-09-08T00:00:00+03:00",
                "status": "superseded_unachievable_historical_target",
                "gate_waiver": False,
            },
        )

        current_docs = [
            ROOT / "README.md",
            ROOT / "START_HERE.md",
            ROOT / "DARK_FACTORY_ROADMAP.md",
            ROOT / "engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/schedule.md",
            ROOT / "engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/brief.md",
            ROOT / "engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/release.md",
            ROOT / "engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/rollback.md",
        ]
        for path in current_docs:
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?i)(?:hard|superseding) (?:program )?deadline is \*\*2026-09-08")
        canonical_schedule = current_docs[3].read_text(encoding="utf-8")
        self.assertIn("T0", canonical_schedule)
        self.assertIn("externally accepted exact M4 SHA", canonical_schedule)
        self.assertIn("superseded and unachievable historical target", canonical_schedule)

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
        self.assertEqual(self.state["milestones"]["M4"]["main_delivery"]["status"], "delivered")
        self.assertEqual(self.state["milestones"]["M4"]["external_gate"]["status"], "success")

    def test_work_inventory_preserves_open_and_unresolved_continuation_work(self) -> None:
        inventory = self.state["work_inventory"]
        expected_open = [
            {"pull_request": 12, "branch": "fix/human-approval-cli", "base": "main", "head": "0f7f508945ccce7dc4f1bffc463247633e9e8f58", "status": "blocked_old_epoch_action_required", "observed_check_conclusion": "ACTION_REQUIRED", "unique_scope": "Lazy CLI imports and tests are absent from main.", "disposition": "Keep stale; extract the unique scope into a clean successor. No successor PR exists."},
            {"pull_request": 13, "branch": "feat/trust-ci-repository-profiles", "base": "main", "head": "f2fd8a7a00a731fbb7acb90e3c7c7881568c8d80", "status": "blocked_old_epoch_action_required", "observed_check_conclusion": "ACTION_REQUIRED", "unique_scope": "Repository-scoped Trust CI profiles are absent from main.", "disposition": "Keep stale; extract the unique scope into a clean successor. No successor PR exists."},
            {"pull_request": 15, "branch": "mvp/investor-ready", "base": "main", "head": "165d5dd90a2fc2831a3b85be2562a2bb241c8b14", "status": "blocked_current_epoch_failure", "observed_check": CURRENT_CHECK, "observed_check_conclusion": "FAILURE", "gitguardian_conclusion": "SUCCESS", "failure_cause": "not inspected or inferred", "unique_commit": "9dcdf5880b619f29c01dbe76e0f598ff1fad9f9b", "unique_scope": "Investor demo and packaging hardening are absent from main.", "disposition": "Wholesale merge is superseded; extract the unique scope into a clean successor. No successor PR exists."},
            {"pull_request": 21, "branch": "milestone/m4-durable-control-plane-accepted-m3", "base": "main", "head": PR21_HEAD_SHA, "status": "open_trust_ci_failure_gitguardian_failure", "observed_check": CURRENT_CHECK, "observed_check_conclusion": "FAILURE", "gitguardian_conclusion": "FAILURE", "failure_cause": "not inspected or inferred", "disposition": "Preserve both failure results without diagnosing or dismissing them; PR 22 is the delivered v2.0.13 path."},
        ]
        self.assertEqual(inventory["open_pull_requests"], expected_open)
        delivered = self.state["delivered_non_milestone_work"]
        self.assertEqual(len(delivered), 2)
        seo = delivered[0]
        self.assertEqual(
            {key: seo[key] for key in ("pull_request", "status", "source_head", "merge_commit")},
            {"pull_request": 19, "status": "delivered", "source_head": "ecc85d903d0394f99a139fd4e74a7cc452e386c6", "merge_commit": SEO_MERGE_SHA},
        )
        landing = delivered[1]
        self.assertEqual(
            {
                key: landing[key]
                for key in (
                    "pull_request",
                    "status",
                    "checked_head",
                    "merge_commit",
                    "tree",
                    "release",
                    "artifact_sha256",
                    "operational_activation",
                )
            },
            {
                "pull_request": 24,
                "status": "delivered",
                "checked_head": CURRENT_RELEASE_HEAD_SHA,
                "merge_commit": CURRENT_MAIN_SHA,
                "tree": CURRENT_RELEASE_TREE,
                "release": "v2.0.14",
                "artifact_sha256": CURRENT_RELEASE_ZIP_SHA256,
                "operational_activation": False,
            },
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
                ("6c578a9933b3", "integration/m5-m4-final-20260904"),
                ("e323f21f2dfc", "integration/m6-m5-final-20260904"),
                ("03b8e24f06e9", "integration/m7-m6-final-20260904"),
                ("3ec8b3357363", "repair/m8-contract-boundary-20260904"),
                ("331ca7021cc0", "integration/m9-m8-final-20260904"),
                ("9f67efd2575c", "feature/l5-multimodal-landing-factory"),
            ],
        )
        self.assertEqual(inventory["active"][0]["source_head"], M4_PRODUCT_SHA)
        self.assertEqual(inventory["active"][0]["base_head"], HISTORICAL_M4_BASE_SHA)
        self.assertEqual(inventory["active"][0]["intermediate_code_head"], M4_INTEGRATION_SHA)
        self.assertEqual(
            inventory["active"][0]["latest_committed_repair_checkpoint"],
            M4_REPAIR_CHECKPOINT_SHA,
        )
        self.assertEqual(inventory["active"][1]["head"], M5_PROVISIONAL_SHA)
        self.assertEqual(inventory["active"][2]["head"], M6_PROVISIONAL_SHA)
        self.assertEqual(inventory["active"][3]["head"], M7_PROVISIONAL_SHA)
        self.assertEqual(inventory["active"][4]["head"], M8_PROVISIONAL_SHA)
        self.assertEqual(inventory["active"][5]["head"], RELEASE_HEAD_SHA)
        self.assertEqual(inventory["active"][5]["source_checkpoint"], M9_PROVISIONAL_SHA)
        self.assertEqual(inventory["active"][5]["pull_request"], 22)
        self.assertEqual(inventory["active"][6]["status"], "published")
        self.assertEqual(inventory["active"][6]["head"], CURRENT_RELEASE_HEAD_SHA)
        self.assertEqual(inventory["active"][6]["merge_commit"], CURRENT_MAIN_SHA)
        self.assertEqual(
            inventory["active"][6]["current_candidate_identity"],
            "v2.0.14",
        )
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
