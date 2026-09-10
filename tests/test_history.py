from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

from adaptive_grok.history import HistoryError, load_history, summarize_history


def snapshot() -> dict:
    return {
        "schema_version": 1,
        "captured_at": "2026-09-10T12:00:00Z",
        "repositories": [{
            "repository_id": "synthetic/project",
            "default_branch": "main",
            "delivery_ref": "delivery",
            "delivery_sha": "1" * 40,
            "pagination_complete": True,
            "task_inventory_complete": False,
            "source_refs": ["synthetic:inventory"],
            "pull_requests": [],
            "tasks": [],
        }],
    }


def pull_request(number: int = 1, **overrides) -> dict:
    return {
        "number": number,
        "state": "merged",
        "base_ref": "delivery",
        "head_sha": "2" * 40,
        "merge_sha": "3" * 40,
        "merged_at": "2026-09-09T12:00:00Z",
        "merged_by_account_type": "User",
        "delivered_at_ref": True,
        "source_refs": ["synthetic:pull-request"],
        **overrides,
    }


def task(task_id: str = "task-a", **overrides) -> dict:
    return {
        "task_id": task_id,
        "pull_request_numbers": [],
        "acceptance": "unknown",
        "acceptance_source_refs": [],
        "operator_interventions": None,
        "intervention_coverage": "unknown",
        "intervention_source_refs": [],
        "session_started_at": None,
        "session_ended_at": None,
        "cost_usd_micros": None,
        "latency_ms": None,
        "regression_count": None,
        "rollback_count": None,
        "profile": None,
        "source_refs": ["synthetic:task"],
        **overrides,
    }


def profile(**overrides) -> dict:
    return {
        "schema_version": 1,
        "repository_id": "synthetic/project",
        "task_class": "low_risk_text_only",
        "m7_change_class": "text_change",
        **{field: "a" * 64 for field in (
            "m7_cohort_key_digest", "provider_mapping_digest", "agent_digest",
            "validator_digest", "provider_digest", "model_digest", "prompt_digest",
            "policy_digest", "runner_digest", "holdout_digest", "authority_digest",
        )},
        "authority_ceiling": "L2",
        "expires_at": "2026-12-01T00:00:00Z",
        **overrides,
    }


class HistoryTests(unittest.TestCase):
    def test_merged_request_does_not_invent_task_acceptance(self) -> None:
        data = snapshot()
        data["repositories"][0]["pull_requests"] = [pull_request()]
        report = summarize_history(data)
        repo = report["repositories"][0]
        self.assertEqual(repo["merged_prs_observed"], 1)
        self.assertEqual(repo["tasks_observed"], 0)
        self.assertIsNone(repo["accepted_task_total"])
        self.assertIsNone(repo["task_total"])
        self.assertIsNone(repo["interventions"]["observed_lower_bound"])
        self.assertEqual(report["m8_qualification"], "not_evaluated")
        self.assertEqual(report["authority_effect"], "none")

    def test_user_merge_actor_does_not_measure_operator_interventions(self) -> None:
        data = snapshot()
        data["repositories"][0]["pull_requests"] = [pull_request()]
        data["repositories"][0]["tasks"] = [task(pull_request_numbers=[1])]
        interventions = summarize_history(data)["repositories"][0]["interventions"]
        self.assertEqual(interventions["unknown_session_count"], 1)
        self.assertIsNone(interventions["observed_lower_bound"])
        self.assertIsNone(interventions["complete_session_zero_intervention_rate"])

    def test_identical_request_replay_counts_once(self) -> None:
        data = snapshot()
        data["repositories"][0]["pull_requests"] = [pull_request(), pull_request()]
        report = summarize_history(data)
        self.assertEqual(report["repositories"][0]["merged_prs_observed"], 1)
        self.assertEqual(report["duplicate_observations"]["pull_request"], 1)

    def test_conflicting_request_replay_is_rejected(self) -> None:
        data = snapshot()
        data["repositories"][0]["pull_requests"] = [
            pull_request(), pull_request(delivered_at_ref=False),
        ]
        with self.assertRaisesRegex(HistoryError, "conflicting.*pull_request"):
            summarize_history(data)

    def test_incomplete_pr_pagination_keeps_total_unknown(self) -> None:
        data = snapshot()
        data["repositories"][0]["pagination_complete"] = False
        data["repositories"][0]["pull_requests"] = [pull_request()]
        report = summarize_history(data)
        repo = report["repositories"][0]
        self.assertFalse(report["pagination_complete"])
        self.assertEqual(repo["pull_requests_observed"], 1)
        self.assertIsNone(repo["pull_request_total"])

    def test_empty_complete_task_inventory_has_known_zero_total(self) -> None:
        data = snapshot()
        data["repositories"][0]["task_inventory_complete"] = True
        repo = summarize_history(data)["repositories"][0]
        self.assertEqual(repo["task_total"], 0)
        self.assertEqual(repo["accepted_task_total"], 0)

    def test_equivalent_ordering_is_deterministic_and_does_not_mutate_input(self) -> None:
        data = snapshot()
        repo = data["repositories"][0]
        repo["pull_requests"] = [pull_request(2), pull_request(1)]
        repo["source_refs"] = ["synthetic:b", "synthetic:a", "synthetic:a"]
        before = copy.deepcopy(data)
        first = summarize_history(data)
        self.assertEqual(data, before)
        repo["pull_requests"].reverse()
        repo["source_refs"] = ["synthetic:a", "synthetic:b"]
        self.assertEqual(summarize_history(data), first)

    def test_loader_rejects_duplicate_json_keys_and_nonfinite_numbers(self) -> None:
        for raw in ('{"schema_version": 1, "schema_version": 1}', '{"x": NaN}'):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "snapshot.json"
                path.write_text(raw)
                with self.assertRaises(HistoryError):
                    load_history(path)

    def test_many_to_many_task_links_and_branch_sync_are_independent(self) -> None:
        data = snapshot()
        repo = data["repositories"][0]
        repo["pull_requests"] = [
            pull_request(1), pull_request(2), pull_request(3, delivery_kind="branch_sync"),
        ]
        repo["tasks"] = [task("one", pull_request_numbers=[1, 2]), task("two", pull_request_numbers=[2])]
        report = summarize_history(data)["repositories"][0]
        self.assertEqual(report["merged_prs_observed"], 3)
        self.assertEqual(report["branch_sync_prs_observed"], 1)
        self.assertEqual(report["tasks_observed"], 2)
        self.assertEqual(report["pull_requests_without_task_identity"], 1)
        self.assertEqual(report["acceptance_counts"]["unknown"], 2)

    def test_open_request_can_be_reachable_and_false_is_not_absent_code(self) -> None:
        data = snapshot()
        data["repositories"][0]["pull_requests"] = [
            pull_request(1, state="open", merged_at=None, merge_sha=None),
            pull_request(2, delivered_at_ref=False),
            pull_request(3, delivered_at_ref=None),
        ]
        report = summarize_history(data)["repositories"][0]
        self.assertEqual(report["delivery_identity_reachability"], {
            "reachable": 1, "identity_not_reachable": 1, "unknown": 1,
        })

    def test_metrics_keep_unknown_denominators_and_measured_zero(self) -> None:
        data = snapshot()
        data["repositories"][0]["tasks"] = [task("one"), task("two", cost_usd_micros=0)]
        metrics = summarize_history(data)["repositories"][0]["metrics"]
        self.assertEqual(metrics["cost_usd_micros"], {
            "known_task_count": 1, "unknown_task_count": 1, "observed_sum": 0,
        })
        self.assertIsNone(metrics["latency_ms"]["observed_sum"])

    def test_partial_interventions_are_lower_bound_only(self) -> None:
        data = snapshot()
        data["repositories"][0]["tasks"] = [task(
            operator_interventions=0, intervention_coverage="partial",
            intervention_source_refs=["synthetic:partial-events"],
        )]
        result = summarize_history(data)["repositories"][0]["interventions"]
        self.assertEqual(result["observed_lower_bound"], 0)
        self.assertEqual(result["partial_session_count"], 1)
        self.assertEqual(result["complete_session_count"], 0)
        self.assertIsNone(result["complete_session_zero_intervention_rate"])

    def test_complete_session_rate_has_explicit_measured_denominator(self) -> None:
        data = snapshot()
        complete = dict(
            intervention_coverage="complete", intervention_source_refs=["synthetic:full-log"],
            session_started_at="2026-09-09T10:00:00Z", session_ended_at="2026-09-09T11:00:00Z",
        )
        data["repositories"][0]["tasks"] = [
            task("zero", operator_interventions=0, **complete),
            task("two", operator_interventions=2, **complete),
            task("partial", operator_interventions=3, intervention_coverage="partial",
                 intervention_source_refs=["synthetic:partial-log"]),
            task("unknown"),
        ]
        result = summarize_history(data)["repositories"][0]["interventions"]
        self.assertEqual(result["complete_session_count"], 2)
        self.assertEqual(result["complete_session_interventions"], 2)
        self.assertEqual(result["observed_lower_bound"], 5)
        self.assertEqual(result["complete_session_zero_intervention_count"], 1)
        self.assertEqual(result["complete_session_zero_intervention_rate"], 0.5)

    def test_incomplete_inventory_never_claims_accepted_full_history_total(self) -> None:
        data = snapshot()
        data["repositories"][0]["tasks"] = [task(
            acceptance="explicit_human_acceptance", acceptance_source_refs=["synthetic:acceptance"],
        )]
        repo = summarize_history(data)["repositories"][0]
        self.assertEqual(repo["explicit_acceptances_observed"], 1)
        self.assertIsNone(repo["accepted_task_total"])
        data["repositories"][0]["task_inventory_complete"] = True
        self.assertEqual(summarize_history(data)["repositories"][0]["accepted_task_total"], 1)

    def test_unknown_acceptance_keeps_total_unknown_even_with_complete_task_inventory(self) -> None:
        data = snapshot()
        data["repositories"][0]["task_inventory_complete"] = True
        data["repositories"][0]["tasks"] = [task()]
        repo = summarize_history(data)["repositories"][0]
        self.assertEqual(repo["task_total"], 1)
        self.assertIsNone(repo["accepted_task_total"])

    def test_incomplete_profiles_do_not_form_wildcard_bucket(self) -> None:
        data = snapshot()
        data["repositories"][0]["tasks"] = [
            task("one", profile={"task_class": "low_risk_text_only"}),
            task("two", profile={"task_class": "low_risk_text_only"}),
        ]
        result = summarize_history(data)["repositories"][0]
        self.assertEqual(result["exact_profile_buckets"], [])
        self.assertEqual(result["profile_coverage"]["incomplete_task_count"], 2)
        self.assertIn("prompt_digest", result["tasks"][0]["missing_profile_fields"])

    def test_changed_exact_profiles_and_repositories_never_pool(self) -> None:
        data = snapshot()
        repo = data["repositories"][0]
        repo["tasks"] = [task("one", profile=profile()), task("two", profile=profile(prompt_digest="b" * 64))]
        other = copy.deepcopy(repo)
        other["repository_id"] = "synthetic/other"
        other["tasks"] = [task("one", profile=profile(repository_id="synthetic/other"))]
        data["repositories"].append(other)
        report = summarize_history(data)
        buckets = [bucket for result in report["repositories"] for bucket in result["exact_profile_buckets"]]
        self.assertEqual(len(buckets), 3)
        self.assertEqual(len({bucket["profile_metadata_digest"] for bucket in buckets}), 3)

    def test_unsupported_and_expired_metadata_remains_observed_with_diagnostics(self) -> None:
        data = snapshot()
        data["repositories"][0]["tasks"] = [task(
            profile=profile(task_class="code_change", schema_version=2, authority_ceiling="L5",
                            expires_at="2026-01-01T00:00:00Z"),
        )]
        result = summarize_history(data)["repositories"][0]
        self.assertEqual(result["tasks_observed"], 1)
        self.assertEqual(result["profile_coverage"]["unsupported_task_class_count"], 1)
        bucket = result["exact_profile_buckets"][0]
        self.assertEqual(bucket["metadata_status"], "complete")
        self.assertEqual(bucket["compatibility_issues"], [
            "authority_ceiling_unsupported", "profile_expired_at_capture",
            "profile_schema_unsupported", "task_class_unsupported",
        ])
        self.assertEqual(bucket["m8_qualification"], "not_evaluated")

    def test_thirty_synthetic_claims_are_accounting_only(self) -> None:
        data = snapshot()
        data["repositories"][0]["tasks"] = [task(
            str(number), profile=profile(), acceptance="explicit_human_acceptance",
            acceptance_source_refs=["synthetic:acceptance"],
        ) for number in range(30)]
        result = summarize_history(data)
        bucket = result["repositories"][0]["exact_profile_buckets"][0]
        self.assertEqual(bucket["observed_explicit_acceptance_count"], 30)
        self.assertEqual(bucket["remaining_to_observed_30_floor"], 0)
        self.assertEqual(bucket["authority_effect"], "none")
        self.assertEqual(result["authority_effect"], "none")
        self.assertEqual(result["m8_qualification"], "not_evaluated")
        self.assertIn("external_acceptance_unavailable", result["qualification_gaps"])

    def test_task_and_repository_duplicates_and_conflicts(self) -> None:
        data = snapshot()
        data["repositories"][0]["tasks"] = [task(), task()]
        data["repositories"].append(copy.deepcopy(data["repositories"][0]))
        result = summarize_history(data)
        self.assertEqual(result["projects_observed"], 1)
        self.assertEqual(result["repositories"][0]["tasks_observed"], 1)
        self.assertEqual(result["duplicate_observations"], {"repository": 1, "pull_request": 0, "task": 2})
        data["repositories"][1]["delivery_ref"] = "other"
        with self.assertRaisesRegex(HistoryError, "conflicting.*repository"):
            summarize_history(data)
        data = snapshot()
        data["repositories"][0]["tasks"] = [task(), task(cost_usd_micros=1)]
        with self.assertRaisesRegex(HistoryError, "conflicting.*task"):
            summarize_history(data)

    def test_duplicate_links_references_and_sparse_null_profiles_normalize(self) -> None:
        data = snapshot()
        data["repositories"][0]["pull_requests"] = [pull_request()]
        data["repositories"][0]["tasks"] = [task(pull_request_numbers=[1, 1], profile={})]
        first = summarize_history(data)
        data["repositories"][0]["tasks"][0]["pull_request_numbers"] = [1]
        data["repositories"][0]["tasks"][0]["profile"] = None
        self.assertEqual(first, summarize_history(data))

    def test_mutated_snapshot_changes_normalized_digest(self) -> None:
        data = snapshot()
        first = summarize_history(data)["normalized_input_digest"]
        data["repositories"][0]["delivery_sha"] = "4" * 40
        self.assertNotEqual(first, summarize_history(data)["normalized_input_digest"])

    def test_invalid_pr_and_task_primitives_fail_closed(self) -> None:
        cases = [
            ("pr", "number", True), ("pr", "number", 0), ("pr", "state", "accepted"),
            ("pr", "head_sha", "A" * 40), ("pr", "delivered_at_ref", 1),
            ("pr", "merged_at", "2026-09-01"), ("pr", "source_refs", []),
            ("task", "cost_usd_micros", True), ("task", "latency_ms", -1),
            ("task", "rollback_count", 0.0), ("task", "regression_count", 2**63),
            ("task", "acceptance", "accepted"), ("task", "pull_request_numbers", [99]),
            ("task", "operator_interventions", 0), ("task", "task_id", "bad\nvalue"),
            ("task", "profile", {"repository_id": "synthetic/elsewhere"}),
            ("task", "profile", {"provider_digest": "short"}),
            ("task", "profile", {"schema_version": True}),
        ]
        for kind, field, value in cases:
            with self.subTest(kind=kind, field=field, value=value):
                data = snapshot()
                repo = data["repositories"][0]
                repo["pull_requests"] = [pull_request()]
                repo["tasks"] = [task()]
                repo["pull_requests" if kind == "pr" else "tasks"][0][field] = value
                with self.assertRaises(HistoryError):
                    summarize_history(data)

    def test_missing_unknown_and_wrong_container_fields_fail_closed(self) -> None:
        for kind in ("extra", "missing", "boolean_version", "container", "string", "surrogate"):
            with self.subTest(kind=kind):
                data = snapshot()
                if kind == "extra":
                    data["run_command"] = "untrusted"
                elif kind == "missing":
                    del data["repositories"][0]["task_inventory_complete"]
                elif kind == "boolean_version":
                    data["schema_version"] = True
                elif kind == "container":
                    data["repositories"] = {}
                elif kind == "surrogate":
                    data["repositories"][0]["source_refs"] = ["\ud800"]
                else:
                    data["repositories"][0]["source_refs"] = ["x" * 2049]
                with self.assertRaises(HistoryError):
                    summarize_history(data)

    def test_measured_sessions_require_sources_and_bounded_windows(self) -> None:
        cases = [
            dict(acceptance="documented_validation"),
            dict(intervention_coverage="partial", operator_interventions=1),
            dict(intervention_coverage="complete", operator_interventions=0,
                 intervention_source_refs=["synthetic:log"]),
            dict(intervention_coverage="complete", operator_interventions=0,
                 intervention_source_refs=["synthetic:log"], session_started_at="2026-09-09T12:00:00Z",
                 session_ended_at="2026-09-09T11:00:00Z"),
            dict(intervention_coverage="complete", operator_interventions=0,
                 intervention_source_refs=["synthetic:log"], session_started_at="2026-09-09T12:00:00Z",
                 session_ended_at="2026-09-11T12:00:00Z"),
        ]
        for values in cases:
            with self.subTest(values=values):
                data = snapshot()
                data["repositories"][0]["tasks"] = [task(**values)]
                with self.assertRaises(HistoryError):
                    summarize_history(data)

    def test_loader_regular_file_limits_encoding_and_depth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "snapshot.json"
            path.write_text(json.dumps(snapshot()))
            self.assertEqual(summarize_history(load_history(path)), summarize_history(snapshot()))
            for raw in (b"\xff", b"[" * 2000 + b"]" * 2000, b" " * (8 * 1024 * 1024 + 1)):
                path.write_bytes(raw)
                with self.assertRaises(HistoryError):
                    load_history(path)
            path.write_text(json.dumps(snapshot()))
            link = root / "link.json"
            link.symlink_to(path)
            fifo = root / "fifo"
            os.mkfifo(fifo)
            for target in (root, link, fifo, root / "absent"):
                with self.subTest(target=target.name), self.assertRaises(HistoryError):
                    load_history(target)

    @unittest.skipUnless(Path("/proc/self/fd").is_dir(), "requires Linux descriptor inventory")
    def test_rejected_directory_does_not_leak_descriptors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            before = len(os.listdir("/proc/self/fd"))
            for _ in range(3):
                with self.assertRaises(HistoryError):
                    load_history(tmp)
            self.assertEqual(len(os.listdir("/proc/self/fd")), before)

    def test_malformed_timezone_offsets_are_rejected(self) -> None:
        data = snapshot()
        data["captured_at"] = "2026-09-10T12:00:00+00:99"
        with self.assertRaises(HistoryError):
            summarize_history(data)

    def test_inventory_and_reference_limits_and_cyclic_input_are_bounded(self) -> None:
        for kind in ("repositories", "observations", "references", "cycle"):
            with self.subTest(kind=kind):
                data = snapshot()
                repo = data["repositories"][0]
                if kind == "repositories":
                    data["repositories"] = [repo] * 101
                elif kind == "observations":
                    repo["pull_requests"] = [pull_request()] * 20_001
                elif kind == "references":
                    repo["source_refs"] = ["synthetic:ref"] * 101
                else:
                    repo["tasks"].append(data)
                with self.assertRaises(HistoryError):
                    summarize_history(data)

    def test_source_references_remain_opaque_data(self) -> None:
        data = snapshot()
        refs = ["https://invalid.example/no-fetch", "synthetic:$(do-not-execute)", "../do-not-read"]
        data["repositories"][0]["source_refs"] = refs
        report = summarize_history(data)
        self.assertEqual(report["repositories"][0]["source_refs"], sorted(refs))

    def test_cli_reports_json_and_safe_bounded_errors_from_unrelated_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"
            path.write_text(json.dumps(snapshot()))
            command = [sys.executable, str(ROOT / "scripts/grok_history.py"), str(path)]
            result = subprocess.run(command, cwd=tmp, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), summarize_history(snapshot()))
            self.assertEqual(result.stderr, "")
            path.write_text('{"private-marker-do-not-echo": "invalid"}')
            result = subprocess.run(command, cwd=tmp, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("private-marker-do-not-echo", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertLess(len(result.stderr), 300)


if __name__ == "__main__":
    unittest.main()
