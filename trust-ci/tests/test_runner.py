from __future__ import annotations

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from _support import now, policy_data, sha
from adaptive_trust_ci.models import ApprovalPayload, Checkout, CommandResult, JobRequest
from adaptive_trust_ci.policy import Policy
from adaptive_trust_ci.runner import JobRunner
from adaptive_trust_ci.signing import Signer, sign_approval, verify_attestation
from adaptive_trust_ci.store import MemoryStore


class FakeGitHub:
    def __init__(self, *, fail_success_once: bool = False) -> None:
        self.statuses = []
        self.fail_success_once = fail_success_once

    def post_status(self, repository, sha_value, **kwargs):
        self.statuses.append((repository, sha_value, kwargs))
        if kwargs["state"] == "success" and self.fail_success_once:
            self.fail_success_once = False
            raise RuntimeError("GitHub unavailable")


class FakeWorkspace:
    def __init__(self, job, *, changed_files, **kwargs) -> None:
        del kwargs
        self.job = job
        self.changed_files = tuple(changed_files)
        self.path = Path(tempfile.mkdtemp())
        (self.path / ".git").mkdir()
        self.reset_calls = 0
        self.cleaned = False

    def checkout(self, job):
        self.assert_same(job)
        return Checkout(self.path, self.changed_files)

    def assert_same(self, job):
        if job.job_id != self.job.job_id:
            raise AssertionError("job mismatch")

    def reset(self):
        self.reset_calls += 1

    def cleanup(self):
        self.cleaned = True
        shutil.rmtree(self.path, ignore_errors=True)


class FakeExecutor:
    def __init__(self, results) -> None:
        self.results = list(results)
        self.calls = []

    def run(self, spec, workspace, env, max_output_bytes):
        self.calls.append((spec.name, workspace, dict(env), max_output_bytes))
        return self.results.pop(0)


def result(name: str, status: str = "pass") -> CommandResult:
    exit_code = 0 if status == "pass" else 1
    return CommandResult(
        name=name,
        status=status,
        exit_code=exit_code,
        duration_seconds=0.1,
        stdout_tail="ok" if status == "pass" else "",
        stderr_tail="" if status == "pass" else "failed",
        output_sha256=hashlib.sha256(f"{name}:{status}".encode()).hexdigest(),
    )


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = Policy.from_dict(policy_data())
        self.store = MemoryStore()
        self.signer = Signer.generate()
        request = JobRequest(
            repository="Dimkox/adaptive-grok-build-pro",
            pr_number=9,
            base_sha=sha("a"),
            head_sha=sha("b"),
            head_ref="feat/test",
            base_ref="main",
        )
        job, _ = self.store.enqueue(request, self.policy.digest, self.policy.max_attempts, now=now())
        self.job = self.store.claim("worker-1", self.policy.lease_seconds, now=now())
        assert self.job is not None
        self.assertEqual(self.job.job_id, job.job_id)

    def build_runner(self, *, changed_files=(), results=None, github=None):
        executor = FakeExecutor(results or [result("unit"), result("compile")])
        workspaces = []

        def workspace_factory(job, **kwargs):
            workspace = FakeWorkspace(job, changed_files=changed_files, **kwargs)
            workspaces.append(workspace)
            return workspace

        runner = JobRunner(
            store=self.store,
            policy=self.policy,
            github=github or FakeGitHub(),
            signer=self.signer,
            github_token="token",
            public_base_url="https://ci.example.com",
            workspace_root=Path(tempfile.gettempdir()),
            now_fn=now,
            workspace_factory=workspace_factory,
            executor_factory=lambda _sandbox: executor,
        )
        return runner, executor, workspaces

    def test_passing_job_publishes_success_and_signed_attestation(self) -> None:
        github = FakeGitHub()
        runner, executor, workspaces = self.build_runner(changed_files=["docs/x.md"], github=github)
        outcome = runner.process(self.job, "worker-1")
        self.assertEqual(outcome.status, "passed")
        self.assertEqual([call[0] for call in executor.calls], ["unit", "compile"])
        self.assertEqual([item[2]["state"] for item in github.statuses], ["pending", "success"])
        envelope = self.store.get_attestation(self.job.job_id)
        self.assertIsNotNone(envelope)
        assert envelope is not None
        payload = verify_attestation(envelope, self.signer.public_key_pem())
        self.assertEqual(payload.head_sha, self.job.head_sha)
        self.assertEqual(payload.policy_digest, self.policy.digest)
        self.assertTrue(workspaces[0].cleaned)

    def test_protected_path_waits_for_signed_approval(self) -> None:
        runner, executor, _ = self.build_runner(changed_files=["trust-ci/src/x.py"])
        outcome = runner.process(self.job, "worker-1")
        self.assertEqual(outcome.status, "needs_approval")
        self.assertEqual(executor.calls, [])
        self.assertEqual(outcome.details["missing_scopes"], ["governance"])

    def test_valid_exact_approval_allows_execution(self) -> None:
        human = Signer.generate()
        payload = ApprovalPayload.new(
            actor="human",
            key_id=human.key_id,
            repository=self.job.repository,
            pr_number=self.job.pr_number,
            base_sha=self.job.base_sha,
            head_sha=self.job.head_sha,
            policy_digest=self.job.policy_digest,
            scope="governance",
            reason="reviewed",
            now=now(),
        )
        self.store.record_approval(payload, sign_approval(payload, human), now=now())
        runner, executor, _ = self.build_runner(changed_files=["trust-ci/src/x.py"])
        outcome = runner.process(self.job, "worker-1")
        self.assertEqual(outcome.status, "passed")
        self.assertEqual(len(executor.calls), 2)

    def test_first_failed_command_stops_pipeline(self) -> None:
        github = FakeGitHub()
        runner, executor, _ = self.build_runner(
            changed_files=["docs/x.md"],
            results=[result("unit", "fail"), result("compile")],
            github=github,
        )
        outcome = runner.process(self.job, "worker-1")
        self.assertEqual(outcome.status, "failed")
        self.assertEqual(len(executor.calls), 1)
        self.assertEqual(github.statuses[-1][2]["state"], "failure")

    def test_signed_attestation_is_replayed_after_status_publication_failure(self) -> None:
        first_github = FakeGitHub(fail_success_once=True)
        runner, executor, _ = self.build_runner(changed_files=["docs/x.md"], github=first_github)
        with self.assertRaisesRegex(RuntimeError, "GitHub unavailable"):
            runner.process(self.job, "worker-1")
        self.assertIsNotNone(self.store.get_attestation(self.job.job_id))
        self.store.retry(self.job.job_id, "worker-1", "GitHub unavailable", now=now())
        reclaimed = self.store.claim("worker-2", self.policy.lease_seconds, now=now())
        assert reclaimed is not None
        second_github = FakeGitHub()
        replay_runner, replay_executor, _ = self.build_runner(
            changed_files=["should-not-checkout"],
            results=[],
            github=second_github,
        )
        outcome = replay_runner.process(reclaimed, "worker-2")
        self.assertEqual(outcome.status, "passed")
        self.assertEqual(replay_executor.calls, [])
        self.assertEqual(second_github.statuses[-1][2]["state"], "success")
        self.assertIn("replayed", second_github.statuses[-1][2]["description"])

    def test_policy_digest_mismatch_fails_without_checkout(self) -> None:
        self.job.policy_digest = "d" * 64
        github = FakeGitHub()
        runner, executor, workspaces = self.build_runner(github=github)
        outcome = runner.process(self.job, "worker-1")
        self.assertEqual(outcome.status, "failed")
        self.assertEqual(executor.calls, [])
        self.assertEqual(workspaces, [])
        self.assertEqual(github.statuses[-1][2]["state"], "failure")


if __name__ == "__main__":
    unittest.main()
