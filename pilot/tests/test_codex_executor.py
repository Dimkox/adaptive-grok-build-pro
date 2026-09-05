from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from pilot.codex_executor import (
    CodexExecutionError,
    CodexExecutor,
    ProcessResult,
    SandboxProof,
)
from pilot.contracts import CandidateChangeV1, canonical_json
from pilot.profile import CODEX_OUTPUT_SCHEMA, exact_landing_profile
from pilot.store import PilotStore
from pilot.tests.support import issue_snapshot
from pilot.workspace import PreparedWorkspace


class FakeProbe:
    def __init__(self, proof: SandboxProof) -> None:
        self.proof = proof
        self.calls = 0

    def prove(self, workspace: PreparedWorkspace) -> SandboxProof:
        self.calls += 1
        return self.proof


class FakeRunner:
    def __init__(self, result: ProcessResult) -> None:
        self.result = result
        self.calls: list[dict] = []

    def run(self, **invocation) -> ProcessResult:
        self.calls.append(invocation)
        return self.result


class FakeWorkspaceManager:
    def __init__(self) -> None:
        self.candidate = None
        self.calls = 0

    def seal(self, workspace, issue, **facts):
        self.calls += 1
        self.asserted = (workspace, issue, facts)
        self.candidate = CandidateChangeV1.from_facts(
            {
                "schema_version": 1,
                "job_id": issue.job_id,
                "profile_digest": issue.profile_digest,
                "issue_snapshot_digest": issue.issue_snapshot_digest,
                "run_id": f"{issue.job_id}-run-1",
                "attempt": 1,
                "provider_id": "openai-codex-cli",
                "writer_id": "codex-writer",
                "sandbox_evidence_digest": facts["sandbox_evidence_digest"],
                "workspace_digest": workspace.workspace_digest,
                "base_sha": issue.base_sha,
                "base_tree": issue.base_tree,
                "candidate_sha": "4" * 40,
                "candidate_tree": "5" * 40,
                "changed_files": [{"path": "index.html", "mode": "100644", "blob_sha": "6" * 40, "sha256": "7" * 64}],
                "diff_sha256": "8" * 64,
                "diff_bytes": 128,
                "remote_removed": True,
                "object_storage_independent": True,
                "outcome": "candidate",
                **facts,
            }
        )
        return self.candidate


class CodexExecutorTests(unittest.TestCase):
    def test_exact_argv_starts_once_and_persists_the_sealed_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            binary = root / "codex"
            binary.write_bytes(b"fake pinned codex")
            binary.chmod(0o755)
            output_schema = root / "output-schema.json"
            output_schema.write_bytes(canonical_json(CODEX_OUTPUT_SCHEMA))
            profile = exact_landing_profile(
                codex_executable=str(binary),
                codex_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                codex_version="0.153.4",
                model_id="gpt-5.3-codex",
                python_executable="/usr/bin/python3",
                python_sha256="b" * 64,
            )
            issue = issue_snapshot(
                profile_digest=profile.profile_digest,
                base_sha=profile.base_sha,
                base_tree=profile.base_tree,
                body="untrusted $(git push --force) body",
            )
            workspace_digest = "3" * 64
            state = PilotStore(root / "state", control_repository=Path(__file__).resolve().parents[2])
            state.create_or_replay(issue, command_key="submit-1")
            state.mark_workspace_ready(issue.job_id, workspace_digest=workspace_digest)
            workspace = PreparedWorkspace(
                root=root / "workspace",
                worktree=root / "workspace/app",
                git_dir=root / "workspace/control.git",
                base_sha=issue.base_sha,
                base_tree=issue.base_tree,
                workspace_digest=workspace_digest,
                object_storage_independent=True,
                remote_removed=True,
            )
            workspace.worktree.mkdir(parents=True)
            workspace.git_dir.mkdir()
            proof = SandboxProof.passed(
                profile_digest=profile.profile_digest,
                workspace_digest=workspace.workspace_digest,
                launcher_digest="c" * 64,
                observed_at="2026-09-05T12:00:02Z",
            )
            runner = FakeRunner(
                ProcessResult(
                    returncode=0,
                    stdout=b'{"type":"turn.completed"}\n',
                    stderr=b"",
                    started_at="2026-09-05T12:00:02Z",
                    completed_at="2026-09-05T12:00:03Z",
                )
            )
            workspaces = FakeWorkspaceManager()
            executor = CodexExecutor(
                profile,
                state,
                workspaces,
                probe=FakeProbe(proof),
                runner=runner,
                output_schema_path=output_schema,
            )

            result = executor.run(issue, workspace, command_key="codex-1")

            self.assertEqual(state.get(issue.job_id).candidate, result)
            self.assertEqual(result.executable_sha256, profile.codex_sha256)
            self.assertEqual(result.prompt_digest, profile.prompt_digest)
            self.assertEqual(result.tool_policy_digest, profile.tool_policy_digest)
            self.assertEqual(result.output_schema_digest, profile.output_schema_digest)
            self.assertEqual(len(runner.calls), 1)
            invocation = runner.calls[0]
            argv = invocation["argv"]
            self.assertEqual(argv[0], str(binary))
            self.assertLess(argv.index("-a"), argv.index("exec"))
            self.assertIn("workspace-write", argv)
            self.assertIn("--ignore-user-config", argv)
            self.assertNotIn(issue.body, "\x00".join(argv))
            self.assertIn(issue.body, invocation["stdin"].decode("utf-8"))
            self.assertEqual(invocation["environment"].get("GIT_TERMINAL_PROMPT"), "0")
            self.assertFalse(any("GITHUB" in key for key in invocation["environment"]))
            with self.assertRaises(CodexExecutionError):
                executor.run(issue, workspace, command_key="codex-2")
            self.assertEqual(len(runner.calls), 1)
            state.close()

    def test_failed_sandbox_proof_starts_zero_processes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            binary = root / "codex"
            binary.write_bytes(b"fake pinned codex")
            binary.chmod(0o755)
            output_schema = root / "output-schema.json"
            output_schema.write_bytes(canonical_json(CODEX_OUTPUT_SCHEMA))
            profile = exact_landing_profile(
                codex_executable=str(binary),
                codex_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                codex_version="0.153.4",
                model_id="gpt-5.3-codex",
                python_executable="/usr/bin/python3",
                python_sha256="b" * 64,
            )
            issue = issue_snapshot(profile_digest=profile.profile_digest, base_sha=profile.base_sha, base_tree=profile.base_tree)
            state = PilotStore(root / "state", control_repository=Path(__file__).resolve().parents[2])
            state.create_or_replay(issue, command_key="submit-1")
            state.mark_workspace_ready(issue.job_id, workspace_digest="3" * 64)
            workspace = PreparedWorkspace(root / "w", root / "w/app", root / "w/git", issue.base_sha, issue.base_tree, "3" * 64, True, True)
            failed = SandboxProof.failed(
                profile_digest=profile.profile_digest,
                workspace_digest=workspace.workspace_digest,
                launcher_digest="c" * 64,
                reason_code="network_denial_unproven",
                observed_at="2026-09-05T12:00:02Z",
            )
            runner = FakeRunner(ProcessResult(0, b"", b"", "2026-09-05T12:00:02Z", "2026-09-05T12:00:03Z"))
            executor = CodexExecutor(profile, state, FakeWorkspaceManager(), probe=FakeProbe(failed), runner=runner, output_schema_path=output_schema)
            with self.assertRaisesRegex(CodexExecutionError, "sandbox_unavailable"):
                executor.run(issue, workspace, command_key="codex-1")
            self.assertEqual(runner.calls, [])
            self.assertEqual(state.get(issue.job_id).state, "needs_human")
            state.close()


if __name__ == "__main__":
    unittest.main()
