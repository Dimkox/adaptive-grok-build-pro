from __future__ import annotations

import hashlib
import copy
import json
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from _support import digest, now, policy_data, sha
from adaptive_trust_ci.holdout import bundle_digest
from adaptive_trust_ci.models import ApprovalPayload, Checkout, CommandResult, JobRequest
from adaptive_trust_ci.policy import Policy
from adaptive_trust_ci.provenance import CorroboratedMerge, ProtectedBranchJobRequest
from adaptive_trust_ci.runner import JobRunner
from adaptive_trust_ci.signing import Signer, sign_approval, verify_attestation, verify_protected_branch_attestation
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
        self.policy_source = policy_data(holdout_path=str(self.holdout), holdout_digest=self.holdout_digest)
        self.policy = Policy.from_dict(self.policy_source)
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

    def build_runner(self, *, changed_files=(), results=None, github=None, mutate_on=(), supply_chain_verifier=None):
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
            holdout_host_path=Path('/host/trust-ci-holdout'),
            now_fn=now,
            workspace_factory=workspace_factory,
            protected_workspace_factory=workspace_factory,
            executor_factory=lambda _sandbox: executor,
            protected_ref='refs/heads/main',
            github_app_id=123,
            supply_chain_verifier=supply_chain_verifier or (lambda _root: True),
        )
        return runner, executor, workspaces, tokens

    def protected_request(self, artifact: Path):
        merge = CorroboratedMerge(
            merge_fact_id=str(uuid.uuid4()),
            repository='dimkox/adaptive-grok-build-pro',
            pr_number=9,
            head_sha=sha('b'),
            base_sha=sha('a'),
            protected_ref='refs/heads/main',
            merged_commit_sha=sha('c'),
            merged_at='2026-08-30T11:59:00Z',
            corroborated_at='2026-08-30T12:00:00Z',
            required_check_name=self.policy.check_name,
            required_check_app_id=123,
            branch_protection_verified_at='2026-08-30T12:00:00Z',
        )
        return ProtectedBranchJobRequest(
            job_id=str(uuid.uuid4()),
            merge=merge,
            policy_epoch=self.policy.digest,
            supply_chain_dir=str(artifact.parent),
            artifact_path=str(artifact),
            started_at=now(),
        )

    def supply_chain_artifact(self) -> tuple[Path, bytes]:
        bundle = Path(self.temp.name) / 'supply-chain'
        bundle.mkdir(exist_ok=True)
        artifact = bundle / 'artifact.zip'
        artifact.write_bytes(b'immutable artifact')
        policy_path = bundle / 'policy.json'
        policy_path.write_text(json.dumps(self.policy_source, sort_keys=True), encoding='utf-8')
        artifacts = bundle / 'artifacts.sha256'
        artifacts.write_text(f'{hashlib.sha256(artifact.read_bytes()).hexdigest()}  {artifact.name}\n', encoding='utf-8')
        manifest = {
            'schema_version': 1,
            'git_head': sha('c'),
            'policy_file': policy_path.name,
            'policy_sha256': hashlib.sha256(policy_path.read_bytes()).hexdigest(),
            'artifacts_file': artifacts.name,
            'artifacts_sha256': hashlib.sha256(artifacts.read_bytes()).hexdigest(),
            'images': {
                'api': 'registry.example/api@sha256:' + digest('a'),
                'worker': 'registry.example/worker@sha256:' + digest('b'),
                'runner': self.policy.sandbox.image,
            },
        }
        manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode() + b'\n'
        (bundle / 'supply-chain.manifest.json').write_bytes(manifest_bytes)
        (bundle / 'supply-chain.manifest.json.sig').write_text('external-signature\n', encoding='utf-8')
        return artifact, manifest_bytes

    def test_protected_branch_run_binds_exact_merge_and_verified_artifact(self) -> None:
        artifact, manifest_bytes = self.supply_chain_artifact()
        github = FakeGitHub()
        runner, executor, workspaces, _ = self.build_runner(github=github)
        request = self.protected_request(artifact)

        envelope = runner.run_protected_branch(request)

        payload = verify_protected_branch_attestation(envelope, self.signer.public_key_pem())
        self.assertEqual(payload.merge_fact_id, request.merge.merge_fact_id)
        self.assertEqual(payload.merged_commit_sha, request.merge.merged_commit_sha)
        self.assertEqual(payload.protected_ref, request.merge.protected_ref)
        self.assertEqual(payload.policy_epoch, self.policy.digest)
        self.assertEqual(payload.holdout_digest, self.holdout_digest)
        self.assertEqual(payload.artifact_sha256, hashlib.sha256(artifact.read_bytes()).hexdigest())
        self.assertEqual(payload.runner_digest, hashlib.sha256(manifest_bytes).hexdigest())
        self.assertEqual(payload.image_digest, self.policy.sandbox.image.rsplit('sha256:', 1)[1])
        self.assertEqual(payload.result, 'passed')
        self.assertEqual(github.ensured[0][1], request.merge.merged_commit_sha)
        self.assertFalse(any(call[2]['conclusion'] == 'success' for call in github.completed))
        runner.publish_protected_success(envelope)
        self.assertEqual(github.completed[-1][2]['conclusion'], 'success')
        self.assertEqual([call[0] for call in executor.calls], ['external-holdout', 'unit', 'compile'])
        self.assertTrue(workspaces[0].cleaned)

    def test_protected_branch_run_rejects_artifact_substitution_before_checkout(self) -> None:
        artifact, _manifest = self.supply_chain_artifact()
        runner, executor, workspaces, _ = self.build_runner()
        request = self.protected_request(artifact)
        artifact.write_bytes(b'substituted artifact')

        with self.assertRaisesRegex(RuntimeError, 'artifact digest'):
            runner.run_protected_branch(request)
        self.assertEqual(executor.calls, [])
        self.assertEqual(workspaces, [])

    def test_protected_branch_run_requires_external_manifest_signature_verification(self) -> None:
        artifact, _manifest = self.supply_chain_artifact()
        runner, executor, workspaces, _ = self.build_runner(supply_chain_verifier=lambda _root: False)
        with self.assertRaisesRegex(RuntimeError, 'supply-chain signature'):
            runner.run_protected_branch(self.protected_request(artifact))
        self.assertEqual(executor.calls, [])
        self.assertEqual(workspaces, [])

    def test_protected_branch_run_rejects_unallowed_repository_or_wrong_protected_ref(self) -> None:
        artifact, _manifest = self.supply_chain_artifact()
        runner, executor, workspaces, _ = self.build_runner()
        request = self.protected_request(artifact)
        for repository, protected_ref in (
            ('attacker/repository', 'refs/heads/main'),
            ('dimkox/adaptive-grok-build-pro', 'refs/heads/release'),
        ):
            with self.subTest(repository=repository, protected_ref=protected_ref):
                changed_merge = request.merge.__class__(
                    **{**request.merge.__dict__, 'repository': repository, 'protected_ref': protected_ref}
                )
                changed_request = request.__class__(**{**request.__dict__, 'merge': changed_merge})
                with self.assertRaisesRegex(RuntimeError, 'repository|protected ref'):
                    runner.run_protected_branch(changed_request)
        self.assertEqual(executor.calls, [])
        self.assertEqual(workspaces, [])

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

    def test_empty_approval_rules_preserve_all_automatic_controls(self) -> None:
        source = copy.deepcopy(self.policy_source)
        source['approval_rules'] = []
        source['promotion'] = {
            'environments': ['production'],
            'max_ttl_seconds': 900,
        }
        self.policy = Policy.from_dict(source)
        self.job.policy_digest = self.policy.digest
        runner, executor, workspaces, _ = self.build_runner(
            changed_files=['trust-ci/src/adaptive_trust_ci/api.py']
        )
        outcome = runner.process(self.job, 'worker-1')
        self.assertEqual(outcome.status, 'passed')
        self.assertEqual(
            [call[0] for call in executor.calls],
            ['external-holdout', 'unit', 'compile'],
        )
        self.assertGreaterEqual(workspaces[0].assert_calls, 3)
        envelope = self.store.get_attestation(self.job.job_id)
        self.assertIsNotNone(envelope)
        assert envelope is not None
        verified = verify_attestation(envelope, self.signer.public_key_pem())
        self.assertEqual(verified.status, 'passed')
        self.assertEqual(verified.approved_scopes, ())

    def test_empty_approval_rules_do_not_soften_terminal_command_failure(self) -> None:
        source = copy.deepcopy(self.policy_source)
        source['approval_rules'] = []
        source['promotion'] = {
            'environments': ['production'],
            'max_ttl_seconds': 900,
        }
        self.policy = Policy.from_dict(source)
        self.job.policy_digest = self.policy.digest
        github = FakeGitHub()
        runner, executor, _, _ = self.build_runner(
            changed_files=['trust-ci/src/adaptive_trust_ci/api.py'],
            results=[result('external-holdout'), result('unit', 'fail'), result('compile')],
            github=github,
        )
        outcome = runner.process(self.job, 'worker-1')
        self.assertEqual(outcome.status, 'failed')
        self.assertEqual([call[0] for call in executor.calls], ['external-holdout', 'unit'])
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
