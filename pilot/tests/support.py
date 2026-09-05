from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import subprocess

from pilot.contracts import CandidateChangeV1, IssueSnapshotV1


def run_git(repository: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=repository,
        env={
            "HOME": str(repository),
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C",
            "TZ": "UTC",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
        },
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise AssertionError(completed.stderr.decode("utf-8", errors="replace"))
    return completed.stdout


def make_source(root: Path) -> tuple[Path, str, str]:
    source = root / "source"
    source.mkdir(mode=0o700)
    run_git(source, "init", "--initial-branch=main")
    (source / "index.html").write_text("v2.0.12\n", encoding="utf-8")
    (source / "index.css").write_text("body{}\n", encoding="utf-8")
    run_git(source, "add", "--", "index.html", "index.css")
    run_git(
        source,
        "-c",
        "user.name=pilot",
        "-c",
        "user.email=pilot@example.invalid",
        "commit",
        "-m",
        "base",
    )
    sha = run_git(source, "rev-parse", "HEAD").decode().strip()
    tree = run_git(source, "rev-parse", "HEAD^{tree}").decode().strip()
    return source, sha, tree


def issue_snapshot(
    *,
    profile_digest: str = "a" * 64,
    base_sha: str = "b" * 40,
    base_tree: str = "c" * 40,
    body: str = "Untrusted issue body",
) -> IssueSnapshotV1:
    return IssueSnapshotV1.from_facts(
        {
            "schema_version": 1,
            "job_id": "pilot-job-1",
            "profile_digest": profile_digest,
            "repository_id": "github.com/Dimkox/ai-dark-factory-landing",
            "repository_node_id": "R_target",
            "issue_number": 1,
            "issue_node_id": "I_target_1",
            "state": "open",
            "updated_at": "2026-09-05T12:00:00Z",
            "author_login": "partner",
            "author_association": "COLLABORATOR",
            "title": "Update release presentation",
            "body": body,
            "base_ref": "refs/heads/main",
            "base_sha": base_sha,
            "base_tree": base_tree,
            "acceptance_ids": ["AC-ISSUE-001", "AC-ISSUE-002"],
            "source_adapter_digest": hashlib.sha256(b"issue-source").hexdigest(),
            "auth_principal_digest": hashlib.sha256(b"principal").hexdigest(),
            "fetched_at": "2026-09-05T12:00:01Z",
        }
    )


def utc_time(second: int = 0) -> datetime:
    return datetime(2026, 9, 5, 12, 0, second, tzinfo=timezone.utc)


def candidate_change(issue: IssueSnapshotV1) -> CandidateChangeV1:
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
            "executable_sha256": "d" * 64,
            "prompt_digest": "e" * 64,
            "tool_policy_digest": "f" * 64,
            "output_schema_digest": "1" * 64,
            "sandbox_evidence_digest": "2" * 64,
            "workspace_digest": "3" * 64,
            "base_sha": issue.base_sha,
            "base_tree": issue.base_tree,
            "candidate_sha": "4" * 40,
            "candidate_tree": "5" * 40,
            "changed_files": [
                {
                    "path": "index.html",
                    "mode": "100644",
                    "blob_sha": "6" * 40,
                    "sha256": "7" * 64,
                }
            ],
            "diff_sha256": "8" * 64,
            "diff_bytes": 128,
            "remote_removed": True,
            "object_storage_independent": True,
            "started_at": "2026-09-05T12:00:02Z",
            "completed_at": "2026-09-05T12:00:03Z",
            "outcome": "candidate",
        }
    )
