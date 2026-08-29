from __future__ import annotations

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from _support import now, policy_data, sha
from adaptive_trust_ci.holdout import bundle_digest
from adaptive_trust_ci.models import ApprovalPayload, Checkout, CommandResult, JobRequest
from adaptive_trust_ci.policy import Policy, PolicyCatalog
from adaptive_trust_ci.runner import JobRunner
from adaptive_trust_ci.signing import Signer, sign_approval, verify_attestation
from adaptive_trust_ci.store import MemoryStore
from adaptive_trust_ci.workspace import GitWorkspace, WorkspaceMutationError


class FakeGitHub:
    def __init__(self, *, fail_success_once: bool = False) -> None:
        self.ensured = []
        self.completed = []
        self.fail_success_once = fail_success_once

    def ensure_check_run(self, repository, sha_value, **kwargs):
        self.ensured.append((repository, sha_value, kwargs))
        return 55

    def complete_check_run(self, repository, check_run_id, **kwargs):
        self.completed.append((repository, check_run_id, kwargs))
        if kwargs['conclusion'] == 'success' and self.fail_success_once:
            self.fail_success_once = False
            raise RuntimeError('GitHub unavailable')


class FakeWorkspace:
    def __init__(self, job, *, changed_files, **kwargs) -> None:
        self.kwargs = kwargs
        self.job = job
        self.changed_files = tuple(changed_files)
        self.path = Path(tempfile.mkdtemp())
        (self.path / '.git').mkdir()
        self.reset_calls = 0
        self.assert_calls = 0
        self.cleaned = False

    def checkout(self, job):
        self.assert_same(job)
        return Checkout(self.path, self.changed_files)

    def assert_same(self, job):
        if job.job_id != self.job.job_id:
            raise AssertionError('job mismatch')

    def assert_unchanged(self):
        self.assert_calls += 1
        mutated = self.path / 'production.py'
        if mutated.exists():
            raise WorkspaceMutationError(('production.py',))

    def reset(self):
        self.reset_calls += 1
        (self.path / 'production.py').unlink(missing_ok=True)

    def cleanup(self):
        self.cleaned = True
        shutil.rmtree(self.path, ignore_errors=True)


class FakeExecutor:
    def __init__(self, results, *, mutate_on=()) -> None:
        self.results = list(results)
        self.calls = []
        self.mutate_on = set(mutate_on)

    def run(self, spec, workspace, env, max_output_bytes, *, workspace_host_path, holdout_path=None, holdout_host_path=None):
        self.calls.append((spec.name, workspace, dict(env), max_output_bytes, workspace_host_path, holdout_path, holdout_host_path))
        if spec.name in self.mutate_on:
            (workspace / 'production.py').write_text('mutated\n', encoding='utf-8')
        return self.results.pop(0)


def result(name: str, status: str = 'pass') -> CommandResult:
    exit_code = 0 if status == 'pass' else 1
    return CommandResult(
        name=name,
        status=status,
        exit_code=exit_code,
        duration_seconds=0.1,
        stdout_tail='ok' if status == 'pass' else '',
        stderr_tail='' if status == 'pass' else 'failed',
        output_sha256=hashlib.sha256(f'{name}:{status}'.encode()).hexdigest(),
    )


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.holdout = Path(self.temp.name) / 'holdout'
        self.holdout.mkdir()
        (self.holdout / 'validate.py').write_text('print("ok")\n', encoding='utf-8')
        self.holdout_digest = bundle_digest(self.holdout)
        self.policy = Policy.from_dict(
            policy_data(holdout_path=str(self.holdout), holdout_digest=self.holdout_digest)
        )
        self.store = MemoryStore()
        self.signer = Signer.generate()
        request = JobRequest(
            repository='Dimkox/adaptive-grok-build-pro',
            pr_number=9,
            base_sha=sha('a'),
            head_sha=sha('b'),
            head_ref='feat/test',
            base_ref='main',
        )
        job, _ = self.store.enqueue(request, self.policy.digest, self.policy.max_attempts, now=now())
        self.job = self.store.claim('worker-1', self.policy.lease_seconds, now=now())
        assert self.job is not None
        self.assertEqual(self.job.job_id, job.job_id)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def build_runner(self, *, changed_files=(), results=None, github=None, mutate_on=(), holdout_host_path=None):
        executor = FakeExecutor(
            results or [result('external-holdout'), result('unit'), result('compile')],
            mutate_on=mutate_on,
        )
        workspaces = []
        tokens = []

        def workspace_factory(job, **kwargs):
            workspace = FakeWorkspace(job, changed_files=changed_files, **kwargs)
            workspaces.append(workspace)
            return workspace

        def token_provider():
            tokens.append('called')
            return 'installation-token'

        runner = JobRunner(
            store=self.store,
            policy=self.policy,
            github=github or FakeGitHub(),
            signer=self.signer,
            github_token_provider=token_provider,
            public_base_url='https://ci.example.com',
            workspace_root=Path(tempfile.gettempdir()),
            workspace_host_root=Path('/host/trust-ci-workspaces'),
            holdout_host_path=holdout_host_path or Path('/host/trust-ci-holdout'),
            now_fn=now,
            workspace_factory=workspace_factory,
            executor_factory=lambda _sandbox: executor,
        )
        return runner, executor, workspaces, tokens

    def test_git_workspace_matches_runner_integrity_contract(self):
        self.assertTrue(hasattr(GitWorkspace, 'assert_unchanged'))

    def test_git_workspace_allows_rootless_daemon_traversal(self):
        base = Path(self.temp.name) / 'workspaces'
        workspace = GitWorkspace(
            self.job,
            github_token='token',
            checkout_depth=1,
            base_directory=base,
        )
        try:
            self.assertEqual(workspace.path.stat().st_mode & 0o777, 0o755)
        finally:
            workspace.cleanup()

    def test_passing_job_uses_epoch_check_runs_holdout_and_signed_attestation(self) -> None:
        github = FakeGitHub()
        runner, executor, workspaces, tokens = self.build_runner(changed_files=['docs/x.md'], github=github)
        outcome = runner.process(self.job, 'worker-1')
        self.assertEqual(outcome.status, 'passed')
        self.assertEqual([call[0] for call in executor.calls], ['external-holdout', 'unit', 'compile'])
        self.assertTrue(str(executor.calls[0][4]).startswith('/host/trust-ci-workspaces/'))
        self.assertEqual(executor.calls[0][5], self.holdout)
        self.assertEqual(executor.calls[0][6], Path('/host/trust-ci-holdout'))
        self.assertIsNone(executor.calls[-1][5])
        self.assertIsNone(executor.calls[-1][6])
        self.assertEqual(github.ensured[0][2]['name'], self.policy.check_name)
        self.assertEqual(github.ensured[0][2]['external_id'], self.job.job_id)
        self.assertEqual(github.completed[-1][1], 55)
        self.assertEqual(github.completed[-1][2]['conclusion'], 'success')
        self.assertEqual(tokens, ['called'])
        self.assertEqual(workspaces[0].kwargs['github_token'], 'installation-token')
        self.assertGreaterEqual(workspaces[0].assert_calls, 3)
        envelope = self.store.get_attestation(self.job.job_id)
        self.assertIsNotNone(envelope)
        assert envelope is not None
        payload = verify_attestation(envelope, self.signer.public_key_pem())
        self.assertEqual(payload.head_sha, self.job.head_sha)
        self.assertEqual(payload.policy_digest, self.policy.digest)
        self.assertEqual(payload.command_results[0]['name'], 'holdout-bundle-integrity')
        self.assertEqual(payload.command_results[0]['output_sha256'], self.holdout_digest)
        self.assertTrue(workspaces[0].cleaned)

    def test_catalog_profiles_reach_executor_with_isolated_commands_mounts_and_attestations(self) -> None:
        second_holdout = Path(self.temp.name) / 'second-holdout'
        second_holdout.mkdir()
        (second_holdout / 'validate.py').write_text('print("second")\n', encoding='utf-8')
        common = policy_data()
        common.pop('allowed_repositories')
        common.pop('commands')
        common.pop('holdout')
        catalog = PolicyCatalog.from_dict({
            **common,
            'repository_profiles': [
                {'repository': 'Dimkox/adaptive-grok-build-pro', 'commands': policy_data()['commands'],
                 'holdout': {**policy_data(holdout_path=str(self.holdout), holdout_digest=self.holdout_digest)['holdout'],
                             'host_path': '/host/holdouts/a'}},
                {'repository': 'Dimkox/ii-tonya-platform',
                 'commands': [{'name': 'platform-unit', 'argv': ['pytest'], 'timeout_seconds': 120, 'required': True}],
                 'holdout': {**policy_data(holdout_path=str(second_holdout), holdout_digest=bundle_digest(second_holdout))['holdout'],
                             'host_path': '/host/holdouts/b'}},
            ],
        })
        observations = []
        for index, repository in enumerate(('Dimkox/adaptive-grok-build-pro', 'Dimkox/ii-tonya-platform')):
            policy = catalog.resolve_repository(repository)
            request = JobRequest(repository, 20 + index, sha('c'), sha(str(index + 3)), 'feat/catalog', 'main')
            job, _ = self.store.enqueue(request, policy.digest, policy.max_attempts, now=now())
            claimed = self.store.claim(f'worker-{index}', policy.lease_seconds, now=now())
            assert claimed is not None
            self.policy = policy
            github = FakeGitHub()
            runner, executor, _, _ = self.build_runner(
                changed_files=['docs/x.md'], github=github, holdout_host_path=policy.holdout.host_path,
            )
            outcome = runner.process(claimed, f'worker-{index}')
            self.assertEqual(outcome.status, 'passed')
            observations.append((policy, job, executor, github))
        first, second = observations
        self.assertEqual([call[0] for call in first[2].calls], ['external-holdout', 'unit', 'compile'])
        self.assertEqual([call[0] for call in second[2].calls], ['external-holdout', 'platform-unit'])
        self.assertEqual(first[2].calls[0][5], self.holdout)
        self.assertEqual(second[2].calls[0][5], second_holdout)
        self.assertEqual(first[2].calls[0][6], Path('/host/holdouts/a'))
        self.assertEqual(second[2].calls[0][6], Path('/host/holdouts/b'))
        for policy, job, _, github in observations:
            self.assertEqual(github.ensured[0][2]['name'], policy.check_name)
            payload = verify_attestation(self.store.get_attestation(job.job_id), self.signer.public_key_pem())
            self.assertEqual(payload.policy_digest, policy.digest)

    def test_protected_path_waits_for_signed_approval_and_completes_action_required(self) -> None:
        github = FakeGitHub()
        runner, executor, _, _ = self.build_runner(changed_files=['trust-ci/src/x.py'], github=github)
        outcome = runner.process(self.job, 'worker-1')
        self.assertEqual(outcome.status, 'needs_approval')
        self.assertEqual(executor.calls, [])
        self.assertEqual(outcome.details['missing_scopes'], ['governance'])
        self.assertEqual(github.completed[-1][2]['conclusion'], 'action_required')

    def test_valid_exact_approval_allows_execution(self) -> None:
        human = Signer.generate()
        payload = ApprovalPayload.new(
            actor='human',
            key_id=human.key_id,
            repository=self.job.repository,
            pr_number=self.job.pr_number,
            base_sha=self.job.base_sha,
            head_sha=self.job.head_sha,
            policy_digest=self.job.policy_digest,
            scope='governance',
            reason='reviewed',
            now=now(),
        )
        self.store.record_approval(payload, sign_approval(payload, human), now=now())
        runner, executor, _, _ = self.build_runner(changed_files=['trust-ci/src/x.py'])
        outcome = runner.process(self.job, 'worker-1')
        self.assertEqual(outcome.status, 'passed')
        self.assertEqual(len(executor.calls), 3)

    def test_first_failed_command_stops_pipeline_and_completes_failure(self) -> None:
        github = FakeGitHub()
        runner, executor, _, _ = self.build_runner(
            changed_files=['docs/x.md'],
            results=[result('external-holdout', 'fail'), result('unit'), result('compile')],
            github=github,
        )
        outcome = runner.process(self.job, 'worker-1')
        self.assertEqual(outcome.status, 'failed')
        self.assertEqual(len(executor.calls), 1)
        self.assertEqual(github.completed[-1][2]['conclusion'], 'failure')

    def test_successful_command_that_mutates_checkout_fails_pipeline(self) -> None:
        runner, executor, _, _ = self.build_runner(
            changed_files=['docs/x.md'],
            mutate_on=['external-holdout'],
        )
        outcome = runner.process(self.job, 'worker-1')
        self.assertEqual(outcome.status, 'failed')
        self.assertEqual([call[0] for call in executor.calls], ['external-holdout'])
        names = [item['name'] for item in outcome.details['commands']]
        self.assertIn('external-holdout:source-integrity', names)
        self.assertIn('production.py', str(outcome.details['commands']))

    def test_holdout_digest_mismatch_fails_without_checkout_or_commands(self) -> None:
        (self.holdout / 'validate.py').write_text('print("tampered")\n', encoding='utf-8')
        github = FakeGitHub()
        runner, executor, workspaces, tokens = self.build_runner(changed_files=['docs/x.md'], github=github)
        outcome = runner.process(self.job, 'worker-1')
        self.assertEqual(outcome.status, 'failed')
        self.assertEqual(executor.calls, [])
        self.assertEqual(workspaces, [])
        self.assertEqual(tokens, [])
        self.assertEqual(github.completed[-1][2]['conclusion'], 'failure')

    def test_signed_attestation_is_replayed_after_check_publication_failure(self) -> None:
        first_github = FakeGitHub(fail_success_once=True)
        runner, _, _, _ = self.build_runner(changed_files=['docs/x.md'], github=first_github)
        with self.assertRaisesRegex(RuntimeError, 'GitHub unavailable'):
            runner.process(self.job, 'worker-1')
        self.assertIsNotNone(self.store.get_attestation(self.job.job_id))
        self.store.retry(self.job.job_id, 'worker-1', 'GitHub unavailable', now=now())
        reclaimed = self.store.claim('worker-2', self.policy.lease_seconds, now=now())
        assert reclaimed is not None
        second_github = FakeGitHub()
        replay_runner, replay_executor, workspaces, tokens = self.build_runner(
            changed_files=['should-not-checkout'],
            results=[],
            github=second_github,
        )
        outcome = replay_runner.process(reclaimed, 'worker-2')
        self.assertEqual(outcome.status, 'passed')
        self.assertEqual(replay_executor.calls, [])
        self.assertEqual(workspaces, [])
        self.assertEqual(tokens, [])
        self.assertEqual(second_github.completed[-1][2]['conclusion'], 'success')
        self.assertIn('replayed', second_github.completed[-1][2]['summary'])

    def test_policy_digest_mismatch_fails_without_checkout(self) -> None:
        self.job.policy_digest = 'd' * 64
        github = FakeGitHub()
        runner, executor, workspaces, tokens = self.build_runner(github=github)
        outcome = runner.process(self.job, 'worker-1')
        self.assertEqual(outcome.status, 'failed')
        self.assertEqual(executor.calls, [])
        self.assertEqual(workspaces, [])
        self.assertEqual(tokens, [])
        self.assertEqual(github.completed[-1][2]['conclusion'], 'failure')

    def test_dead_job_publication_is_app_owned_epoch_check(self) -> None:
        github = FakeGitHub()
        runner, _, _, _ = self.build_runner(github=github)
        runner.publish_dead_job(self.job, 'network unavailable')
        self.assertEqual(github.ensured[-1][2]['name'], self.policy.check_name)
        self.assertEqual(github.completed[-1][2]['conclusion'], 'failure')
        self.assertIn('network unavailable', github.completed[-1][2]['summary'])


if __name__ == '__main__':
    unittest.main()
