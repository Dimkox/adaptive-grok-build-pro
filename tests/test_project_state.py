from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CURRENT_CHECK = "adaptive-trust-ci/verified@06ecf1c875bc"
CURRENT_APP_ID = 4694114
CURRENT_MAIN_SHA = "1751b5855e46782b9a1bfceb6e1ab0102cba03b0"  # v2.0.14 merge
OBSERVED_MAIN_SHA = "130ce4a42d9f9bbd1b56772d40b19ae530283205"  # 2026-09-22 observation, PR #185 source base for the v2.0.19 candidate
V2017_SOURCE_BASE = "78082a290f8b90cade88685351fbb2ba263689b9"  # PR #98 release-sync merge: the base the candidate was authored on
V2017_CHECKED_HEAD = "bbc5cdd9b8ee4dbc6927bf24244a5434f490576d"
V2017_MERGE_COMMIT = "c86b1a1989ace899a4450bde558fcd8adc00e4e2"
V2017_TREE = "5826924586f9d42b02bf9fd5d51985bd323da31e"
V2017_TAG_OBJECT = "5c6687ed97e1c365597bf27047016eb07411f28b"
V2017_ZIP_SHA256 = "770f1db5725e666be60c1f879d2768feacb15dd53e194a1f1f48632980f74616"
V2017_SIDECAR_SHA256 = "54db9f64bb7296ca657410131499ca06358f89b23171e221b04e300acf03f3c0"
V2017_PUBLISHED_AT = "2026-09-16T01:17:14Z"
V2017_MERGED_AT = "2026-09-16T01:14:19Z"
V2017_ATTESTATION_ID = "b9510589-d40c-4976-aafd-cad6fc141972"
V2018_CHECKED_HEAD = "07d1141e70884397a61eb93fd76525baf2444a0e"
V2018_MERGE_COMMIT = "e7d0f72bf834b75eb543d9424ee47c7829cc65c0"
V2018_TREE = "c78d200ee6a6a7ab1e32f2194691a8e639b9dab3"
V2018_ZIP_SHA256 = "0bc6adc9f4660e1b60be4cb4895e97f2641338b52b6a5e05ac3c7acd85e59b3a"
V2018_SIDECAR_SHA256 = "dd7e2ec5a979d70062f206f381efcb38b92da2f7bfc1129034b459e125a54216"
V2018_ATTESTATION_ID = "8172a5bc-1377-428a-aaa9-b8da462f9952"
POST_V2018_PR_HEADS = {
    111: "176c3c6331241929c5e9091c93833c04d0d010d2",
    112: "f541250196f6f08e13b6ad703d30434492fea2ff",
    113: "2d1c0208faba0ca5635e37acfd46cace6182057a",
    114: "245e565e95797032d94a310264e80ed803d95450",
    115: "55dbb6b243a6523c38ee8332153a82d0885227a6",
    116: "72d7340ef7d8df40262c3c1f5793d1cf3173571f",
    149: "c7b557d8bbee8ddf2fc539383c8452112cba6b31",
    150: "c335a33b9cffde4d8912b173803c3adec3348d06",
    151: "b4c0c5f6516e5b34a4726a59bb530dd100b31a03",
    154: "a4023258047a03e1176daa3a35695c9d9b49f8be",
    170: "1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48",
    173: "23984e55560c6d559a46445061f10331ca05bcf9",
    174: "73a8edd7678b4d605f6335569534653c6587eabc",
    184: "0d16a5370537e697657fd60c7b27d994f45bd4b2",
    185: "17489bf52ae1f6fac7923d8e3448bcae26f54163",
}

V2016_CHECKED_HEAD = "2b1517986b9b5b83a95b1286baac161074c58175"
V2016_MERGE_COMMIT = "969c4f65f54ef9230f3f94587e228098d1c2ecb9"
V2016_TREE = "2c24c33873c972822354218addf983b8166fa40a"
V2016_ZIP_SHA256 = "71f63a1089f4009cc65ed0afb5b755418fa5a8bf1dd4ce2aebae2f1b8cc746d7"
V2016_SIDECAR_SHA256 = "14e3753aadf21f29119fdc059d4c65791833144d8de1ece0b7d83adf1b254fb8"
V2016_SOURCE_BASE = "1a8c89170349fcc2597be0a1665b0e0a31d124e0"
V2015_CHECKED_HEAD = "9fcc9d943c74260c02a920a59490143f91cb38b2"
V2015_MERGE_COMMIT = "fd51dcfed6b33f4a8707c0db602328146df17cc9"
V2015_TREE = "f01e9b0d1f80fb6731c68079540fd98e5c1f64ac"
V2015_ZIP_SHA256 = "1f0f64557fd258df7e533f674bb4e7c55d4a1a51454d48bcfecfa5487d08e9d7"
V2015_SIDECAR_SHA256 = "8f3ed4b8eb96f7984eb38b0c988bd8a8cee8cdc789bca52527084b78fd791c6d"
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
        self.assertEqual(state["product_version"], "2.0.19")
        self.assertEqual(state["latest_published_release"], "v2.0.18")
        self.assertEqual(state["observed_main_sha"], OBSERVED_MAIN_SHA)
        self.assertRegex(state["observed_at"], r"^2026-09-22T\d{2}:\d{2}:\d{2}Z$")
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
        repair = state["delivered_change_history"]["design_partner_pilot"]["record"]
        self.assertEqual(repair["route_id"], "0ce2d62a018e")
        self.assertEqual(repair["branch"], "feature/design-partner-pilot")
        self.assertEqual(repair["source_base"], "6f3b6ed2853b7a6f78804888cffca578d4dc9448")
        self.assertEqual(repair["stage"], "local_pr_candidate")
        self.assertEqual(repair["landing_source"]["commit"], CURRENT_LANDING_SHA)
        self.assertEqual(repair["landing_source"]["tree"], CURRENT_LANDING_TREE)
        self.assertTrue(repair["landing_source"]["read_only"])
        self.assertEqual(repair["issue_number"], 1)
        self.assertEqual(
            repair["write_paths"],
            [".htaccess", "index.html", "km/index.html", "ko/index.html", "lv/index.html", "nl/index.html", "tests/test_landing.py", "zh-cn/index.html"],
        )
        self.assertEqual(repair["protected_source_member"], "index.css")
        self.assertEqual(repair["execution"]["default"], "unavailable")
        self.assertEqual(
            repair["execution"]["cli_phases"],
            ["prepare", "publish-branch", "publish-proposal", "status"],
        )
        self.assertEqual(repair["execution"]["provider_mode"], "app_server_chatgpt")
        self.assertEqual(repair["execution"]["model"], "gpt-6-astra")
        self.assertEqual(repair["execution"]["max_codex_starts"], 1)
        self.assertFalse(repair["execution"]["automatic_retry"])
        self.assertEqual(repair["local_store"]["engine"], "stdlib_sqlite")
        self.assertEqual(repair["local_store"]["startup_recovery_limit"], 100)
        self.assertEqual(repair["local_store"]["status_access"], "read_only_query_only")
        self.assertEqual(repair["publication"]["branch_push"], "exact_resource_non_force_only")
        self.assertEqual(repair["publication"]["proposal"], "exact_resource_draft_only")
        self.assertEqual(
            repair["publication"]["runtime_grant_binding"],
            "current_origin_route_change_head_tree_fingerprint",
        )
        self.assertIsNone(repair["publication"]["landing_trust_ci_profile"])
        self.assertEqual(
            repair["package_rebuild"],
            "source_parent_R_then_zip_sidecar_only_child_A",
        )
        self.assertFalse(repair["external_effect"])
        self.assertEqual(
            repair["focused_tests"],
            {
                "status": "task6_affected_tests_passed_before_source_freeze",
                "contracts_architecture": 5,
                "issue_store_workspace_codex_recovery": 9,
                "validation": 4,
                "authority_publication": 4,
                "coordinator_cli": 3,
                "task6_app_server": 4,
                "task6_cli": 3,
                "task6_coordinator_recovery": 2,
                "task6_live_phases": 4,
                "task6_pinned_github": 2,
                "task6_runtime_authority": 2,
                "task6_store": 3,
                "task6_workspace": 3,
            },
        )
        self.assertEqual(
            repair["full_verifier"],
            "original_2405b013_failed_one_postgres_method_then_targeted_recovery_passed_unchanged_tree",
        )
        self.assertEqual(
            repair["independent_reviews"],
            "original_fail_reports_preserved_existing_three_reviewers_recheck_final_repaired_artifact",
        )
        self.assertEqual(repair["execution"]["command_permissions"], "pilot_confined")
        self.assertEqual(repair["observed_target_drift"]["status"], "blocked_before_model_attempt")
        self.assertFalse(repair["execution"]["live_model_invoked"])

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
        self.assertEqual(published["tag"], "v2.0.18")
        self.assertEqual(published["pull_request"], 108)
        self.assertEqual(published["checked_head"], V2018_CHECKED_HEAD)
        self.assertEqual(published["merge_commit"], V2018_MERGE_COMMIT)
        self.assertEqual(published["tree"], V2018_TREE)
        self.assertEqual(published["artifact"]["sha256"], V2018_ZIP_SHA256)
        self.assertEqual(
            published["artifact"]["sidecar_sha256"],
            V2018_SIDECAR_SHA256,
        )
        self.assertEqual(published["trust_ci"]["check_run_id"], 104809218211)
        self.assertEqual(published["tag_object"], "31d3171f651ea77e29de58d4affc58d008f1c7a5")
        self.assertEqual(published["published_at"], "2026-09-16T13:52:24Z")
        self.assertEqual(published["merged_at"], "2026-09-16T13:51:26Z")
        self.assertEqual(published["gitguardian"]["conclusion"], "SUCCESS")
        self.assertEqual(published["gitguardian"]["check_run_id"], 104809206290)
        self.assertEqual(
            published["trust_ci"]["attestation_id"],
            V2018_ATTESTATION_ID,
        )
        self.assertEqual(published["gitguardian"]["conclusion"], "SUCCESS")
        prior = state["prior_published_releases"]
        self.assertEqual(len(prior), 5)
        self.assertEqual(prior[0]["tag"], "v2.0.17")
        self.assertEqual(prior[0]["checked_head"], V2017_CHECKED_HEAD)
        self.assertEqual(prior[0]["merge_commit"], V2017_MERGE_COMMIT)
        self.assertEqual(prior[0]["tree"], V2017_TREE)
        self.assertEqual(prior[0]["artifact"]["sha256"], V2017_ZIP_SHA256)
        self.assertEqual(prior[0]["artifact"]["sidecar_sha256"], V2017_SIDECAR_SHA256)
        self.assertEqual(prior[0]["tag_object"], V2017_TAG_OBJECT)
        self.assertEqual(prior[0]["trust_ci"]["attestation_id"], V2017_ATTESTATION_ID)
        self.assertEqual(prior[0]["published_at"], V2017_PUBLISHED_AT)
        self.assertEqual(prior[0]["merged_at"], V2017_MERGED_AT)
        self.assertEqual(prior[0]["pull_request"], 99)
        self.assertEqual(prior[1]["tag"], "v2.0.16")
        self.assertEqual(prior[1]["checked_head"], V2016_CHECKED_HEAD)
        self.assertEqual(prior[1]["merge_commit"], V2016_MERGE_COMMIT)
        self.assertEqual(prior[1]["tree"], V2016_TREE)
        self.assertEqual(prior[1]["artifact"]["sha256"], V2016_ZIP_SHA256)
        self.assertEqual(prior[2]["tag"], "v2.0.15")
        self.assertEqual(prior[2]["checked_head"], V2015_CHECKED_HEAD)
        self.assertEqual(prior[2]["merge_commit"], V2015_MERGE_COMMIT)
        self.assertEqual(prior[2]["tree"], V2015_TREE)
        self.assertEqual(prior[2]["artifact"]["sha256"], V2015_ZIP_SHA256)
        self.assertEqual(prior[3]["tag"], "v2.0.14")
        self.assertEqual(prior[3]["checked_head"], CURRENT_RELEASE_HEAD_SHA)
        self.assertEqual(prior[3]["merge_commit"], CURRENT_MAIN_SHA)
        self.assertEqual(prior[3]["tree"], CURRENT_RELEASE_TREE)
        self.assertEqual(prior[3]["artifact"]["sha256"], CURRENT_RELEASE_ZIP_SHA256)
        self.assertEqual(prior[4]["tag"], "v2.0.13")
        self.assertEqual(prior[4]["checked_head"], RELEASE_HEAD_SHA)
        self.assertEqual(prior[4]["merge_commit"], RELEASE_MERGE_SHA)
        self.assertEqual(prior[4]["tree"], RELEASE_TREE)
        self.assertEqual(prior[4]["artifact"]["sha256"], RELEASE_ZIP_SHA256)
        local = state["local_candidate"]
        self.assertEqual(local["version"], "2.0.19")
        self.assertEqual(local["status"], "pending_release")
        self.assertEqual(local["route_id"], "4317e673390b")
        self.assertEqual(local["branch"], "release/v2.0.19-factory-bugfixes")
        self.assertIsNone(local["pull_request"])
        self.assertEqual(
            local["change_package"],
            "engineering/changes/20260923-release-v2-0-19-with-fail-closed-factory-issue-f-4317e6",
        )
        self.assertEqual(local["artifact_status"], "pending_unpublished_artifact_child")
        self.assertFalse(local["published"])
        self.assertIsNone(local["published_at"])
        self.assertFalse(local["external_effect"])
        self.assertIsNone(local["external_effect_scope"])
        self.assertFalse(local["operational_activation"])
        self.assertIsNone(local["artifact_child"]["zip_sha256"])
        self.assertIsNone(local["artifact_child"]["sidecar_sha256"])
        for key in ("reviewed_product_head", "reviewed_product_tree", "checked_head", "merge_commit", "tree"):
            self.assertIsNone(local[key], f"pending candidate must not name {key}")
        for key in ("source_parent", "source_parent_tree", "commit", "tree"):
            self.assertIsNone(local["artifact_child"][key], f"pending artifact child must not name {key}")
        self.assertEqual(local["source_base"], OBSERVED_MAIN_SHA)
        self.assertEqual(local["artifact_child"]["status"], "not_built")
        self.assertEqual(
            local["artifact_child"]["delta_paths"],
            [
                "packages/adaptive-grok-build-pro-v2.0.19.zip",
                "packages/adaptive-grok-build-pro-v2.0.19.zip.sha256",
            ],
        )
        self.assertEqual(local["artifact_child"]["identity"], "A")
        self.assertTrue(local["artifact_child"]["requirement"])
        self.assertEqual(
            state["current_unreleased_change"]["change_id"],
            "20260923-release-v2-0-19-with-fail-closed-factory-issue-f-4317e6",
        )

    def test_post_publication_landing_and_archived_candidate_are_recorded(self) -> None:
        landing = self.state["delivered_change_history"]["post_v2_0_17_landing"]
        self.assertEqual(landing["status"], "landed_in_v2_0_18_release")
        rows = landing["pull_requests"]
        self.assertEqual(
            {row["pull_request"] for row in rows},
            {101, 102, 105, 106},
        )
        for row in rows:
            self.assertRegex(row["head"], r"^(?:[0-9a-f]{8}|[0-9a-f]{40})$")
            self.assertRegex(row["merge_commit"], r"^[0-9a-f]{40}$")
            self.assertRegex(row["merged_at"], r"^2026-09-16T\d{2}:\d{2}:\d{2}Z$")
            self.assertGreater(row["check_run_id"], 104_600_000_000)
            self.assertTrue(row["purpose"])
        next_landing = self.state["delivered_change_history"]["post_v2_0_18_landing"]
        self.assertEqual(next_landing["status"], "landed_in_v2_0_19_candidate")
        self.assertEqual(
            {row["pull_request"] for row in next_landing["pull_requests"]},
            {111, 112, 113, 114, 115, 116, 149, 150, 151, 154, 170, 173, 174, 184, 185},
        )
        for row in next_landing["pull_requests"]:
            self.assertEqual(row["head"], POST_V2018_PR_HEADS[row["pull_request"]])
            self.assertRegex(row["head"], r"^[0-9a-f]{40}$")
            self.assertRegex(row["merge_commit"], r"^[0-9a-f]{40}$")
            self.assertRegex(row["merged_at"], r"^2026-09-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertGreater(row["check_run_id"], 104_800_000_000)
            self.assertTrue(row["purpose"])
        archived = self.state["delivered_change_history"][
            "v2_0_17_release_preparation"
        ]["published_local_candidate"]
        self.assertEqual(archived["version"], "2.0.17")
        self.assertEqual(archived["status"], "published")
        self.assertTrue(archived["published"])
        self.assertEqual(archived["merge_commit"], V2017_MERGE_COMMIT)
        self.assertEqual(archived["checked_head"], V2017_CHECKED_HEAD)
        self.assertEqual(archived["artifact_child"]["zip_sha256"], V2017_ZIP_SHA256)
        self.assertEqual(
            archived["artifact_child"]["sidecar_sha256"], V2017_SIDECAR_SHA256
        )

    def test_m4_source_implementation_is_distinct_from_verification_review_and_delivery(self) -> None:
        dimensions = self.state["active_delivery"]["m4_dimensions"]
        current = self.state["current_unreleased_change"]
        delivery = self.state["active_delivery"]
        for key in ("route_id", "branch", "change_package", "next_action"):
            self.assertEqual(delivery[key], current[key])
        self.assertEqual(current["source_base"], OBSERVED_MAIN_SHA)
        self.assertEqual(current["status"], "release_sync_authored")
        self.assertEqual(
            current["identity"],
            "v2.0.19 release candidate with bounded local guards related to #35/#39 and owned fail-closed fixes for #73/#167; #48 remains separated under FIT-TRUST-CI-SEPARATION",
        )
        self.assertEqual(current["route_id"], "4317e673390b")
        self.assertEqual(current["target_version"], "2.0.19")
        self.assertEqual(delivery["status"], "release_sync_pending")
        self.assertIsNone(delivery["local_source_gate"]["artifact_head"])
        self.assertIsNone(delivery["repository_delivery"]["checked_head"])
        self.assertIsNone(delivery["repository_delivery"]["pull_request"])
        self.assertIsNone(delivery["package_handoff"]["tag_target"])
        historical = self.state["delivered_change_history"]["l5_offline_v2_0_14"]
        source_gate = historical["local_source_gate"]
        self.assertEqual(source_gate["status"], "passed_for_artifact_head")
        self.assertEqual(source_gate["product_head"], "5f47508f3c0d52b71a3c866969cc28b6476a9d99")
        self.assertEqual(source_gate["policy_head"], "58c9caed5d2c8f9febba297430a0782438505d82")
        self.assertEqual(source_gate["reviews"], "four_route_selected_reviews_passed")
        self.assertEqual(source_gate["artifact_head"], CURRENT_RELEASE_HEAD_SHA)
        self.assertEqual(source_gate["artifact_tree"], CURRENT_RELEASE_TREE)
        self.assertEqual(source_gate["artifact_verification"], "passed")
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

    def test_retained_33_entry_records_the_delivered_retake(self) -> None:
        # Adversarial arm for the flipped entry: the #33 line may stay in the historical
        # list only while it states the re-take was delivered by #113 with its exact merge
        # SHA and keeps parallelism conditional on an importable pytest+xdist install.
        entry = next(
            item
            for item in self.state["work_inventory"]["retained_unresolved"]
            if item.get("pull_request") == 33
        )
        self.assertEqual(entry["status"], "retaken_and_delivered")
        self.assertIn("PR #113", entry["resolution"])
        self.assertIn("35cbbe0f857bdb03dec4eb0ecff542a148b84658", entry["resolution"])
        self.assertIn("conditional on an importable pytest+xdist", entry["resolution"])
        # The historical observation itself must survive untouched.
        self.assertEqual(entry["head"], "6d72d4c859dded241b55e90ae9514ad428a7eb1b")
        self.assertEqual(entry["observed_check_conclusion"], "FAILURE")
        self.assertEqual(entry["closed_at"], "2026-09-16T07:21:05Z")
        if subprocess.run(
            ["git", "cat-file", "-e", "35cbbe0f857bdb03dec4eb0ecff542a148b84658^{commit}"],
            cwd=ROOT, check=False, capture_output=True,
        ).returncode:
            return  # object not fetched here; the internal pins above still stand
        subject = subprocess.run(
            ["git", "show", "-s", "--format=%s", "35cbbe0f857bdb03dec4eb0ecff542a148b84658"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout
        self.assertIn("(retakes #33) (#113)", subject)

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
            self.assertIn(self.state["observed_main_sha"], section)
            self.assertNotIn("adaptive-trust-ci/verified@6737355947c2", section)

        start_here = (ROOT / "START_HERE.md").read_text(encoding="utf-8")
        self.assertIn("PR #19", start_here)
        self.assertIn("delivered", start_here)
        self.assertNotRegex(start_here, r"open PRs[^.;\n]*#19")

    def test_runtime_observations_are_source_bound_without_promoting_qualification(self) -> None:
        state = self.state
        evidence = json.loads((ROOT / state["runtime_observations"]["evidence"]).read_text())
        runtime = state["runtime_observations"]
        # Runtime evidence is intentionally historical and remains bound to the
        # immutable published release while the current source observation advances.
        self.assertEqual(state["published_release"]["merge_commit"], evidence["source_base"])
        for role, source in (("primary", evidence["qwen_historical_acceptance"]),
                             ("secondary", evidence["grok"])):
            service = runtime["services"][role]
            with self.subTest(role=role):
                expected_sha = source.get("merged_and_installed_sha", source.get("merged_commit"))
                expected_result = source.get("socket_acceptance", source.get("smoke"))
                self.assertEqual(service["installed_sha"], expected_sha)
                self.assertEqual(service["acceptance"]["artifact_digest"], expected_result["artifact_digest"])
                self.assertEqual(service["acceptance"]["state"], "artifact_ready")
                self.assertIsNone(service["acceptance"]["live_url"])
                self.assertIn("Id=" + service["unit"] + "\nActiveState=active\nUnitFileState=enabled",
                              evidence["service_observation"])
                self.assertTrue(service["live_enabled"])
        from adaptive_factory.landing_http import HttpLandingProfile
        for service in runtime["services"].values():
            profile = HttpLandingProfile.for_provider(service["selected_profile"])
            self.assertEqual(service["model"], profile.model_id)
        primary = runtime["services"]["primary"]
        self.assertEqual(Path(primary["control_repository"]).parent.name, primary["installed_sha"])
        self.assertEqual(state["l5_production_preparation"]["selected_profile"], primary["selected_profile"])
        from adaptive_factory.settings import FactorySettings
        self.assertFalse(FactorySettings.landing_live_enabled)
        template = json.loads((ROOT / runtime["source_defaults"]["template"]).read_text())
        self.assertFalse(template["live_enabled"])
        self.assertFalse(runtime["source_defaults"]["live_enabled"])
        for key in ("external_maintainer_accepted_pilot", "m8_qualifying_cohort", "m8_activation",
                    "m9_general_operational_qualification", "factory_site_publication",
                    "complete_pilot_cost_and_human_intervention_accounting"):
            self.assertFalse(state["operational_qualification"][key])
        # A pending candidate must never be presented as the published release:
        # the product identity leads, the published tag lags by exactly that bump.
        self.assertEqual(state["latest_published_release"], state["published_release"]["tag"])
        self.assertEqual(state["local_candidate"]["version"], state["product_version"])
        self.assertFalse(state["local_candidate"]["published"])
        self.assertFalse(state["local_candidate"]["operational_activation"])
        self.assertNotEqual("v" + state["product_version"], state["published_release"]["tag"])
        self.assertEqual(state["observed_main_sha"], OBSERVED_MAIN_SHA)

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
        self.assertEqual(inventory["open_pull_requests"], [])
        self.assertNotIn(12, {item["pull_request"] for item in inventory["open_pull_requests"]})
        self.assertEqual(inventory["delivered_since_historical_inventory"][0]["pull_request"], 12)
        self.assertEqual(inventory["delivered_since_historical_inventory"][0]["status"], "delivered")
        self.assertEqual(inventory["active"], [])
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
        # GENERATED: mirrors PROJECT_STATE.work_inventory.retained_unresolved verbatim;
        # regenerate from the JSON (json.dumps fields) whenever either side changes.
        self.assertEqual(
            inventory["retained_unresolved"],
            [
                {"branch": "perf/parallel-python-tests", "closed_at": "2026-09-16T07:21:05Z", "failure_cause": "head 6d72d4c8\u2026: mandatory root-unittest exited 1 with `Ran 642 tests in 443.587s` and `FAILED (failures=7, skipped=1)`; all seven failures are inside this pull request's own tests/test_python_test_runner.py. One reports \"Trust CI tests failed: pytest missing; install .grok-stack/config/python-test-requirements.txt with this Python\" (the workers=2 trust-CLI case); the remaining six assert `'fail' != 'pass'`, including the unittest-path case test_unittest_filename_pattern_is_preserved. The record does not state the runtime's package inventory, so no wider claim is made than that message. Historical observation for that head; refresh base/head and re-derive eligibility before any delivery claim.", "head": "6d72d4c859dded241b55e90ae9514ad428a7eb1b", "observed_check": "adaptive-trust-ci/verified@06ecf1c875bc", "observed_check_conclusion": "FAILURE", "pull_request": 33, "purpose": "Closed without merging on 2026-09-16 by maintainer decision, with the diagnosis and the re-take path recorded on the pull request: the runner must select its engine from what the interpreter actually provides, and its unittest-branch tests must be satisfiable without an importable pytest. The branch and its 1540-insertion head are kept untouched and undeleted; parallel local verification remains an open goal, not a delivered one.", "status": "retaken_and_delivered", "unique_scope": "Parallel local Python verification", "resolution": "Retaken and delivered by PR #113 (squash merge 35cbbe0f857bdb03dec4eb0ecff542a148b84658, 2026-09-16): python_test_runner selects its engine from what the interpreter provides (capability probe before execution; unimportable xdist degrades to one disclosed sequential unittest pass), and the suite passes on a pytest-free interpreter - proven locally and by the App-owned exact-head check on head 2d1c0208. The perf/parallel-python-tests branch and its head 6d72d4c8\u2026 stay retained untouched as the diagnosis exhibit; the failure_cause text above remains a historical observation of that head. True parallelism remains conditional on an importable pytest+xdist install: on such interpreters the runner uses xdist, elsewhere it discloses the serial degrade."},
                {"pull_request": 15, "branch": "mvp/investor-ready", "head": "165d5dd90a2fc2831a3b85be2562a2bb241c8b14", "status": "closed_unmerged", "closed_at": "2026-09-15T20:02:30Z", "observed_check": "adaptive-trust-ci/verified@06ecf1c875bc", "observed_check_conclusion": "FAILURE", "unique_scope": "Unique investor demo and packaging hardening", "purpose": "Closed without merging on 2026-09-15T20:02:30Z; its displayed failure conclusion is historical evidence, and any reuse needs a fresh scoped extraction rather than a reopen.", "failure_cause": "head 165d5dd9…: mandatory root-unittest exited 1 with `Ran 480 tests in 244.175s` and `FAILED (failures=1, errors=5)`. The record first shows git refusing the job's own checkout — \"fatal: detected dubious ownership in repository at '/workspace/.git'\" followed by \"fatal: Could not read from remote repository.\" — and the consequences are `ArchitectureError: base_sha is not an available commit object` from adaptive_grok/architecture_diff.py `_exact_commit` (three architecture bootstrap tests) and `RuntimeError: architecture binding requires an exact Git HEAD` (two receipt tests), with the single failure being `AssertionError: 2 != 0` in the architecture CLI bootstrap case. Historical observation; the pull request was closed without merging, so no current eligibility applies."},
                {"pull_request": 14, "local_head": "cb2fe7ce637c464179e20b5b37aae334e56c1838", "purpose": "Unique closed production-promotion work requiring explicit re-evaluation."},
                {"branch": "feature/workflow-artifact-adapters", "local_head": "dccaeec2a6b79c73663765f5909243e468e4b070", "purpose": "Superseded by the port on feature/third-party-components-sync, delivered by PR #93 as 280cbff12df2578da3c671d4daa8b5492f26a7fc. The branch and its worktree hold the only untouched copy of the never-committed original epic, so they were retained until the v2.0.17 release record referenced the #93 lineage; that condition is now met (published v2.0.17, predecessors naming 280cbff), and removal is a separate explicitly approved cleanup step, not an automatic consequence of this release."},
                {"branch": "origin/milestone/a-plus-autopilot", "head": "90a5da294ec06e9fbbf8ea97d1c27c64484b9069", "purpose": "Design-only reference; not M8 implementation."},
            ],
        )
        self.assertEqual(
            [(item["route_id"], item["branch"]) for item in inventory["historical_integrations"]],
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
        self.assertEqual(inventory["historical_integrations"][0]["source_head"], M4_PRODUCT_SHA)
        self.assertEqual(inventory["historical_integrations"][0]["base_head"], HISTORICAL_M4_BASE_SHA)
        self.assertEqual(inventory["historical_integrations"][0]["intermediate_code_head"], M4_INTEGRATION_SHA)
        self.assertEqual(
            inventory["historical_integrations"][0]["latest_committed_repair_checkpoint"],
            M4_REPAIR_CHECKPOINT_SHA,
        )
        self.assertEqual(inventory["historical_integrations"][1]["head"], M5_PROVISIONAL_SHA)
        self.assertEqual(inventory["historical_integrations"][2]["head"], M6_PROVISIONAL_SHA)
        self.assertEqual(inventory["historical_integrations"][3]["head"], M7_PROVISIONAL_SHA)
        self.assertEqual(inventory["historical_integrations"][4]["head"], M8_PROVISIONAL_SHA)
        self.assertEqual(inventory["historical_integrations"][5]["head"], RELEASE_HEAD_SHA)
        self.assertEqual(inventory["historical_integrations"][5]["source_checkpoint"], M9_PROVISIONAL_SHA)
        self.assertEqual(inventory["historical_integrations"][5]["pull_request"], 22)
        self.assertEqual(inventory["historical_integrations"][6]["status"], "published")
        self.assertEqual(inventory["historical_integrations"][6]["head"], CURRENT_RELEASE_HEAD_SHA)
        self.assertEqual(inventory["historical_integrations"][6]["merge_commit"], CURRENT_MAIN_SHA)
        self.assertEqual(
            inventory["historical_integrations"][6]["current_candidate_identity"],
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
        self.assertIn(
            {
                "pull_request": 21,
                "branch": "milestone/m4-durable-control-plane-accepted-m3",
                "base": "main",
                "head": PR21_HEAD_SHA,
                "status": "closed_superseded",
                "closed_at": "2026-09-05T12:07:24Z",
                "observed_check": CURRENT_CHECK,
                "observed_check_conclusion": "FAILURE",
                "gitguardian_conclusion": "FAILURE",
                "failure_cause": "the branch's final head 571cad78… (the pull request was later marked superseded): mandatory root-unittest exited 1 with `Ran 535 tests in 379.425s` and `FAILED (errors=1, skipped=1)`. The lone error is in tests/test_manifest_package.py's test_shipped_zip_exactly_matches_filtered_tracked_head, where the test's own git helper raised subprocess.CalledProcessError for `['git', '--no-replace-objects', '-C', '/workspace', 'rev-parse', '--verify', 'HEAD^{commit}']` with exit status 128; the same record shows the job checking out 571cad78…, so no further mechanism is claimed. An earlier head 460a8a01… passed all six mandatory commands, so the error is attributed to that job, not to the branch content. Historical observation.",
                "disposition": "Closed as stale after PR 22 delivered M1-M9 in v2.0.13 and PR 24 delivered additive L5 in v2.0.14; preserved failure conclusions are historical evidence, not current delivery blockers.",
            },
            inventory["superseded"],
        )

    def test_adversarial_pr21_base_head_and_status_are_rejected(self) -> None:
        original = self.state
        mutated = copy.deepcopy(original)
        pr21 = next(
            item
            for item in mutated["work_inventory"]["superseded"]
            if item.get("pull_request") == 21
        )
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


if __name__ == "__main__":
    unittest.main()
