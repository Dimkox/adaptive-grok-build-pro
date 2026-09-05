from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from pilot.workspace import ExactGitWorkspace, WorkspaceError, WorkspacePolicy
from pilot.tests.support import issue_snapshot, make_source, run_git


class ExactGitWorkspaceTests(unittest.TestCase):
    def test_private_no_local_clone_has_no_remote_and_seals_one_parent_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, base_sha, base_tree = make_source(root)
            policy = WorkspacePolicy(
                profile_digest="a" * 64,
                base_sha=base_sha,
                base_tree=base_tree,
                allowed_write_paths=("index.html",),
                max_diff_bytes=4096,
            )
            manager = ExactGitWorkspace(
                source,
                root / "private-workspaces",
                control_repository=Path(__file__).resolve().parents[2],
                policy=policy,
            )
            prepared = manager.prepare("pilot-job-1")
            (prepared.worktree / "index.html").write_text("v2.0.14\n", encoding="utf-8")

            candidate = manager.seal(
                prepared,
                issue_snapshot(
                    profile_digest=policy.profile_digest,
                    base_sha=base_sha,
                    base_tree=base_tree,
                ),
                sandbox_evidence_digest="d" * 64,
                model_id="gpt-5.3-codex",
                executable_version="0.153.4",
                executable_sha256="e" * 64,
                prompt_digest="f" * 64,
                tool_policy_digest="1" * 64,
                output_schema_digest="2" * 64,
                started_at="2026-09-05T12:00:02Z",
                completed_at="2026-09-05T12:00:03Z",
            )

            self.assertFalse((prepared.worktree / ".git").exists())
            self.assertEqual(run_git(prepared.git_dir, "remote"), b"")
            self.assertFalse((prepared.git_dir / "objects/info/alternates").exists())
            self.assertEqual(candidate.base_sha, base_sha)
            self.assertEqual(
                run_git(prepared.git_dir, "rev-list", "--parents", "-n", "1", candidate.candidate_sha).decode().split(),
                [candidate.candidate_sha, base_sha],
            )
            self.assertEqual(tuple(item.path for item in candidate.changed_files), ("index.html",))
            self.assertEqual((prepared.root.stat().st_mode & 0o777), 0o700)

    def test_disallowed_or_special_change_is_rejected_without_commit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, base_sha, base_tree = make_source(root)
            manager = ExactGitWorkspace(
                source,
                root / "private-workspaces",
                control_repository=Path(__file__).resolve().parents[2],
                policy=WorkspacePolicy("a" * 64, base_sha, base_tree, ("index.html",), 4096),
            )
            prepared = manager.prepare("pilot-job-1")
            (prepared.worktree / "not-allowed.txt").write_text("no", encoding="utf-8")
            with self.assertRaisesRegex(WorkspaceError, "changed_paths"):
                manager.seal(
                    prepared,
                    issue_snapshot(profile_digest="a" * 64, base_sha=base_sha, base_tree=base_tree),
                    sandbox_evidence_digest="d" * 64,
                    model_id="gpt-5.3-codex",
                    executable_version="0.153.4",
                    executable_sha256="e" * 64,
                    prompt_digest="f" * 64,
                    tool_policy_digest="1" * 64,
                    output_schema_digest="2" * 64,
                    started_at="2026-09-05T12:00:02Z",
                    completed_at="2026-09-05T12:00:03Z",
                )
            self.assertEqual(run_git(prepared.git_dir, "rev-parse", "HEAD").decode().strip(), base_sha)


if __name__ == "__main__":
    unittest.main()
