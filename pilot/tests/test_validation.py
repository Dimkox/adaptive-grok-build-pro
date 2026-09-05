from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from pilot.contracts import CandidateChangeV1
from pilot.profile import exact_landing_profile
from pilot.store import PilotStore
from pilot.tests.test_contracts import HEX64_A, HEX64_B
from pilot.tests.support import issue_snapshot
from pilot.validation import (
    BubblewrapTestRunner,
    CandidateValidator,
    LandingSemanticGate,
    ProtectedFileObservation,
    TestProcessResult,
    ValidationWorkspace,
)
from pilot.workspace import PreparedWorkspace


def profile():
    return exact_landing_profile(
        codex_executable="/opt/pilot/bin/codex",
        codex_sha256=HEX64_A,
        codex_version="0.153.4",
        model_id="gpt-5.3-codex",
        python_executable="/usr/bin/python3",
        python_sha256=HEX64_B,
    )


def candidate(issue) -> CandidateChangeV1:
    paths = profile().allowed_write_paths
    return CandidateChangeV1.from_facts(
        {
            "schema_version": 1,
            "job_id": issue.job_id,
            "profile_digest": issue.profile_digest,
            "issue_snapshot_digest": issue.issue_snapshot_digest,
            "run_id": "pilot-run-1",
            "attempt": 1,
            "provider_id": "openai-codex-cli",
            "model_id": "gpt-5.3-codex",
            "writer_id": "codex-writer",
            "executable_version": "0.153.4",
            "executable_sha256": HEX64_A,
            "prompt_digest": profile().prompt_digest,
            "tool_policy_digest": profile().tool_policy_digest,
            "output_schema_digest": profile().output_schema_digest,
            "sandbox_evidence_digest": "c" * 64,
            "workspace_digest": "d" * 64,
            "base_sha": issue.base_sha,
            "base_tree": issue.base_tree,
            "candidate_sha": "e" * 40,
            "candidate_tree": "f" * 40,
            "changed_files": [
                {"path": path, "mode": "100644", "blob_sha": f"{index:x}" * 40, "sha256": f"{index:x}" * 64}
                for index, path in enumerate(paths, start=1)
            ],
            "diff_sha256": "9" * 64,
            "diff_bytes": 1024,
            "remote_removed": True,
            "object_storage_independent": True,
            "started_at": "2026-09-05T12:00:02Z",
            "completed_at": "2026-09-05T12:00:03Z",
            "outcome": "candidate",
        }
    )


def semantic_fixture(root: Path) -> None:
    script = b'{"@context":"https://schema.org","@type":"SoftwareSourceCode","version":"2.0.14"}'
    token = base64.b64encode(hashlib.sha256(script).digest()).decode("ascii")
    root_html = (
        "<html><body>Governed Agentic Software Factory — Offline Technical Preview "
        "Latest published release v2.0.14 <span>v2.0.14</span>"
        f'<script type="application/ld+json">{script.decode()}</script></body></html>'
    )
    (root / "index.html").write_text(root_html, encoding="utf-8")
    for locale in ("km", "ko", "lv", "nl", "zh-cn"):
        (root / locale).mkdir()
        (root / locale / "index.html").write_text("<html>v2.0.14</html>", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests/test_landing.py").write_text(
        "EXPECTED='2.0.14 v2.0.14 Latest published release Governed Agentic Software Factory — Offline Technical Preview'\n",
        encoding="utf-8",
    )
    (root / ".htaccess").write_text(
        "Header always set Content-Security-Policy \"default-src 'self'; script-src 'self' 'sha256-"
        + token
        + "='; style-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'\"\n",
        encoding="utf-8",
    )


class FakeValidationWorkspaces:
    def __init__(self, workspace: ValidationWorkspace, protected: ProtectedFileObservation) -> None:
        self.workspace = workspace
        self.protected = protected
        self.current_tree = workspace.candidate_tree
        self.materialize_calls = 0

    def materialize(self, writer, candidate):
        self.materialize_calls += 1
        return self.workspace

    def tree(self, workspace):
        return self.current_tree

    def protected_file(self, workspace, path):
        return self.protected


class FakeTestRunner:
    def __init__(self, result: TestProcessResult, *, mutate=None) -> None:
        self.result = result
        self.mutate = mutate
        self.calls = []

    def run(self, *, command, workspace, timeout_seconds, max_output_bytes):
        self.calls.append((command, workspace, timeout_seconds, max_output_bytes))
        if self.mutate:
            self.mutate()
        return self.result


class ValidationTests(unittest.TestCase):
    def test_semantic_gate_proves_exact_versions_labels_csp_and_protected_css(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            semantic_fixture(root)
            issue = issue_snapshot(profile_digest=profile().profile_digest, base_sha=profile().base_sha, base_tree=profile().base_tree)
            decision = LandingSemanticGate(profile()).evaluate(
                root,
                candidate(issue),
                ProtectedFileObservation(profile().protected_index_css_blob, profile().protected_index_css_sha256),
                issue.acceptance_ids,
            )
            self.assertEqual(decision.decision, "pass")
            self.assertEqual(decision.reason_codes, ())

            (root / "nl/index.html").write_text("<html>v2.0.12</html>", encoding="utf-8")
            rejected = LandingSemanticGate(profile()).evaluate(
                root,
                candidate(issue),
                ProtectedFileObservation(profile().protected_index_css_blob, profile().protected_index_css_sha256),
                issue.acceptance_ids,
            )
            self.assertEqual(rejected.decision, "rejected")
            self.assertIn("semantic_non_pass", rejected.reason_codes)

    def test_fixed_test_and_semantic_pass_persist_one_exact_validation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            semantic_fixture(root)
            configured = profile()
            issue = issue_snapshot(profile_digest=configured.profile_digest, base_sha=configured.base_sha, base_tree=configured.base_tree)
            sealed = candidate(issue)
            store = PilotStore(root / "state", control_repository=Path(__file__).resolve().parents[2])
            store.create_or_replay(issue, command_key="submit-1")
            store.mark_workspace_ready(issue.job_id, workspace_digest=sealed.workspace_digest)
            store.begin_invocation(issue.job_id, command_key="codex-1")
            store.store_candidate(issue.job_id, sealed)
            validation_workspace = ValidationWorkspace(root / "validation", root, root / "validation.git", sealed.candidate_sha, sealed.candidate_tree, "1" * 64)
            workspaces = FakeValidationWorkspaces(
                validation_workspace,
                ProtectedFileObservation(configured.protected_index_css_blob, configured.protected_index_css_sha256),
            )
            runner = FakeTestRunner(TestProcessResult("completed", 0, b"OK\n", b"", 42, "2026-09-05T12:00:04Z"))
            validator = CandidateValidator(configured, store, workspaces, runner=runner, gate=LandingSemanticGate(configured))
            result = validator.validate(
                sealed,
                PreparedWorkspace(root / "writer", root / "writer/app", root / "writer.git", issue.base_sha, issue.base_tree, sealed.workspace_digest, True, True),
                command_key="validate-1",
            )
            self.assertEqual(result.decision, "pass")
            self.assertEqual(store.get(issue.job_id).state, "gate_passed")
            self.assertEqual(runner.calls[0][0], configured.test_argv)
            self.assertEqual(result.writer_id, sealed.writer_id)
            self.assertNotEqual(result.writer_id, result.evaluator_id)
            store.close()

    def test_tree_mutation_is_terminal_even_when_test_exit_is_zero(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            semantic_fixture(root)
            configured = profile()
            issue = issue_snapshot(profile_digest=configured.profile_digest, base_sha=configured.base_sha, base_tree=configured.base_tree)
            sealed = candidate(issue)
            store = PilotStore(root / "state", control_repository=Path(__file__).resolve().parents[2])
            store.create_or_replay(issue, command_key="submit-1")
            store.mark_workspace_ready(issue.job_id, workspace_digest=sealed.workspace_digest)
            store.begin_invocation(issue.job_id, command_key="codex-1")
            store.store_candidate(issue.job_id, sealed)
            validation_workspace = ValidationWorkspace(root / "validation", root, root / "validation.git", sealed.candidate_sha, sealed.candidate_tree, "1" * 64)
            workspaces = FakeValidationWorkspaces(validation_workspace, ProtectedFileObservation(configured.protected_index_css_blob, configured.protected_index_css_sha256))
            runner = FakeTestRunner(
                TestProcessResult("completed", 0, b"OK\n", b"", 42, "2026-09-05T12:00:04Z"),
                mutate=lambda: setattr(workspaces, "current_tree", "0" * 40),
            )
            result = CandidateValidator(configured, store, workspaces, runner=runner, gate=LandingSemanticGate(configured)).validate(
                sealed,
                PreparedWorkspace(root / "writer", root / "writer/app", root / "writer.git", issue.base_sha, issue.base_tree, sealed.workspace_digest, True, True),
                command_key="validate-1",
            )
            self.assertEqual(result.decision, "rejected")
            self.assertIn("test_mutation", result.reason_codes)
            self.assertEqual(store.get(issue.job_id).state, "needs_human")
            store.close()

    def test_bwrap_argv_has_minimal_read_only_source_and_no_network(self) -> None:
        configured = profile()
        workspace = ValidationWorkspace(Path("/private/job"), Path("/private/job/app"), Path("/private/job/git"), "e" * 40, "f" * 40, "1" * 64)
        argv, environment = BubblewrapTestRunner(configured).invocation(configured.test_argv, workspace)
        self.assertIn("--unshare-all", argv)
        self.assertIn("--ro-bind", argv)
        self.assertIn("/workspace", argv)
        self.assertNotIn(str(workspace.git_dir), argv)
        self.assertEqual(argv[-len(configured.test_argv):], configured.test_argv)
        self.assertFalse(any(key.startswith(("GH_", "GITHUB_", "CODEX_")) for key in environment))


if __name__ == "__main__":
    unittest.main()
