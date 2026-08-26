from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from _support import now, policy_data, sha
from adaptive_trust_ci.holdout import bundle_digest
from adaptive_trust_ci.models import ApprovalPayload, AttestationEnvelope, AttestationPayload, Checkout, CommandResult, JobRequest
from adaptive_trust_ci.policy import Policy
from adaptive_trust_ci.runner import JobRunner, SpecMetadataError, extract_spec_metadata
from adaptive_trust_ci.signing import Signer, sign_approval, sign_attestation, verify_attestation
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
    def __init__(self, job, *, changed_files, workspace_files=None, **kwargs) -> None:
        self.kwargs = kwargs
        self.job = job
        self.changed_files = tuple(changed_files)
        self.path = Path(tempfile.mkdtemp())
        (self.path / '.git').mkdir()
        for rel, content in (workspace_files or {}).items():
            target = self.path / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8')
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

    def build_runner(self, *, changed_files=(), workspace_files=None, results=None, github=None, mutate_on=()):
        executor = FakeExecutor(
            results or [result('external-holdout'), result('unit'), result('compile')],
            mutate_on=mutate_on,
        )
        workspaces = []
        tokens = []

        def workspace_factory(job, **kwargs):
            workspace = FakeWorkspace(job, changed_files=changed_files, workspace_files=workspace_files, **kwargs)
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
            executor_factory=lambda _sandbox: executor,
        )
        return runner, executor, workspaces, tokens

    def test_git_workspace_matches_runner_integrity_contract(self):
        self.assertTrue(hasattr(GitWorkspace, 'assert_unchanged'))

    def test_spec_metadata_is_deterministic_data_only(self) -> None:
        checkout = Path(self.temp.name) / 'metadata'
        first = checkout / 'engineering/changes/20260826-a/change-spec.yaml'
        second = checkout / 'engineering/changes/20260826-b/change-spec.yaml'
        first.parent.mkdir(parents=True)
        second.parent.mkdir(parents=True)
        first.write_text(json.dumps({'schema_version': 2, 'acceptance_criteria': [{'id': 'AC-002', 'statement': 'two', 'evidence': []}, {'id': 'AC-001', 'statement': 'one', 'evidence': [{'receipt': 'verification'}]}]}), encoding='utf-8')
        second.write_text(json.dumps({'schema_version': 2, 'acceptance_criteria': [{'id': 'AC-003', 'statement': 'three', 'evidence': [{'test': 'tests/x.py'}]}]}), encoding='utf-8')
        paths = (second.relative_to(checkout).as_posix(), first.relative_to(checkout).as_posix())
        digest_value, coverage = extract_spec_metadata(checkout, paths)
        reverse_digest, reverse_coverage = extract_spec_metadata(checkout, tuple(reversed(paths)))
        self.assertEqual(digest_value, reverse_digest)
        self.assertEqual(coverage, reverse_coverage)
        self.assertEqual(coverage['spec_count'], 2)
        self.assertEqual(coverage['criterion_total'], 3)
        self.assertEqual(
            coverage['unmapped_ids'],
            ['engineering/changes/20260826-a/change-spec.yaml#AC-002'],
        )

    def test_spec_metadata_rejects_malformed_evidence_and_json(self) -> None:
        checkout = Path(self.temp.name) / 'metadata-invalid'
        path = checkout / 'engineering/changes/20260826-a/change-spec.yaml'
        path.parent.mkdir(parents=True)
        rel = path.relative_to(checkout).as_posix()
        for document in (
            {'schema_version': 2, 'acceptance_criteria': [{'id': 'AC-001', 'evidence': [{'test': None}]}]},
            {'schema_version': 2, 'acceptance_criteria': [{'id': 'AC-001', 'evidence': [{'receipt': 'bogus'}]}]},
            {'schema_version': 2, 'acceptance_criteria': [{'id': 'AC-001', 'evidence': [{'production_signal': 'SIG-999'}]}], 'observability': []},
            {'schema_version': 2, 'acceptance_criteria': [{'id': 'AC-001', 'statement': '', 'evidence': [{'receipt': 'verification'}]}]},
            {
                'schema_version': 2,
                'objective': {'id': 'OBJ-001'},
                'acceptance_criteria': [{'id': 'AC-001', 'statement': 'x', 'evidence': [{'production_signal': 'SIG-001'}]}],
                'observability': [{'id': 'SIG-001', 'metric': 'x', 'proves': []}],
            },
        ):
            with self.subTest(document=document):
                path.write_text(json.dumps(document), encoding='utf-8')
                with self.assertRaises(SpecMetadataError):
                    extract_spec_metadata(checkout, (rel,))
        path.write_text('{bad json', encoding='utf-8')
        with self.assertRaises(SpecMetadataError):
            extract_spec_metadata(checkout, (rel,))

    def test_criterion_ids_are_spec_local_and_coverage_is_path_qualified(self) -> None:
        checkout = Path(self.temp.name) / 'metadata-duplicate'
        paths = []
        for name, evidence in (('a', []), ('b', [{'receipt': 'verification'}])):
            path = checkout / f'engineering/changes/20260826-{name}/change-spec.yaml'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'schema_version': 2, 'acceptance_criteria': [{'id': 'AC-001', 'statement': 'local', 'evidence': evidence}]}), encoding='utf-8')
            paths.append(path.relative_to(checkout).as_posix())
        digest_value, coverage = extract_spec_metadata(checkout, tuple(reversed(paths)))
        reverse_digest, reverse_coverage = extract_spec_metadata(checkout, tuple(paths))
        self.assertEqual(digest_value, reverse_digest)
        self.assertEqual(coverage, reverse_coverage)
        self.assertEqual(coverage['spec_count'], 2)
        self.assertEqual(coverage['criterion_total'], 2)
        self.assertEqual(coverage['criterion_mapped'], 1)
        self.assertEqual(coverage['unmapped_ids'], [f'{paths[0]}#AC-001'])

    def test_malformed_spec_error_retains_exact_raw_provenance_digest(self) -> None:
        checkout = Path(self.temp.name) / 'metadata-provenance'
        path = checkout / 'engineering/changes/20260826-a/change-spec.yaml'
        path.parent.mkdir(parents=True)
        raw = b'{bad json'
        path.write_bytes(raw)
        rel = path.relative_to(checkout).as_posix()
        entries = [{'path': rel, 'raw_digest': hashlib.sha256(raw).hexdigest(), 'semantic_digest': None}]
        expected = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with self.assertRaises(SpecMetadataError) as raised:
            extract_spec_metadata(checkout, (rel,))
        self.assertEqual(raised.exception.spec_digest, expected)

    def test_spec_metadata_rejects_symlink(self) -> None:
        checkout = Path(self.temp.name) / 'metadata-symlink'
        outside = checkout / 'outside'
        outside.parent.mkdir(parents=True)
        outside.write_text('{}', encoding='utf-8')
        path = checkout / 'engineering/changes/20260826-a/change-spec.yaml'
        path.parent.mkdir(parents=True)
        path.symlink_to(outside)
        with self.assertRaises(SpecMetadataError):
            extract_spec_metadata(checkout, (path.relative_to(checkout).as_posix(),))

    def test_spec_metadata_rejects_ancestor_symlink(self) -> None:
        checkout = Path(self.temp.name) / 'metadata-ancestor-symlink'
        outside = Path(self.temp.name) / 'metadata-outside'
        path = outside / 'changes/20260826-a/change-spec.yaml'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'schema_version': 2, 'acceptance_criteria': []}), encoding='utf-8')
        checkout.mkdir()
        (checkout / 'engineering').symlink_to(outside)
        with self.assertRaises(SpecMetadataError):
            extract_spec_metadata(checkout, ('engineering/changes/20260826-a/change-spec.yaml',))

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

    def test_real_git_paths_preserve_scope_and_signed_spec_provenance(self) -> None:
        workspace = GitWorkspace(
            self.job,
            github_token='token',
            checkout_depth=1,
            base_directory=Path(self.temp.name) / 'real-workspace',
        )
        try:
            subprocess.run(['git', 'init', '-q'], cwd=workspace.path, check=True)
            subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=workspace.path, check=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=workspace.path, check=True)
            (workspace.path / 'README.md').write_text('base\n', encoding='utf-8')
            subprocess.run(['git', 'add', '.'], cwd=workspace.path, check=True)
            subprocess.run(['git', 'commit', '-qm', 'base'], cwd=workspace.path, check=True)
            base = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=workspace.path, text=True).strip()

            protected = (
                'trust-ci/файл.txt',
                'trust-ci/line\nbreak.txt',
                'trust-ci/tab\tname.txt',
                'trust-ci/back\\slash.txt',
            )
            spec_paths = tuple(
                f'engineering/changes/20260826-{name}/change-spec.yaml'
                for name in ('юникод', 'line\nbreak', 'tab\tname', 'back\\slash')
            )
            document = json.dumps({
                'schema_version': 2,
                'acceptance_criteria': [
                    {'id': 'AC-001', 'statement': 'exact path', 'evidence': [{'receipt': 'verification'}]},
                ],
            })
            for rel in protected:
                target = workspace.path / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('protected\n', encoding='utf-8')
            for rel in spec_paths:
                target = workspace.path / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(document, encoding='utf-8')
            subprocess.run(['git', 'add', '.'], cwd=workspace.path, check=True)
            subprocess.run(['git', 'commit', '-qm', 'unusual paths'], cwd=workspace.path, check=True)
            head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=workspace.path, text=True).strip()

            changed = workspace._changed_files(base, head)
            self.assertEqual(changed, tuple(sorted((*protected, *spec_paths))))
            with self.assertRaisesRegex(RuntimeError, 'exact base/head SHA'):
                workspace._changed_files('a' * 40, head)
            for rel in protected:
                self.assertEqual(self.policy.required_scopes((rel,)), {'governance'})
            digest_value, coverage = extract_spec_metadata(workspace.path, changed)
            self.assertEqual(coverage, {'spec_count': 4, 'criterion_total': 4, 'criterion_mapped': 4, 'unmapped_ids': []})
            payload = AttestationPayload(
                schema_version=1,
                attestation_id='real-path-attestation',
                job_id=self.job.job_id,
                repository=self.job.repository,
                pr_number=self.job.pr_number,
                base_sha=base,
                head_sha=head,
                policy_digest=self.job.policy_digest,
                status='passed',
                command_results=(),
                changed_files=changed,
                approved_scopes=('governance',),
                started_at=now().isoformat(),
                completed_at=now().isoformat(),
                key_id=self.signer.key_id,
                spec_digest=digest_value,
                criterion_coverage=coverage,
            )
            verified = verify_attestation(sign_attestation(payload, self.signer), self.signer.public_key_pem())
            self.assertEqual(verified.changed_files, changed)
            self.assertEqual(verified.spec_digest, digest_value)

            invalid_path = os.fsencode(workspace.path) + b'/trust-ci/invalid-\xff.txt'
            descriptor = os.open(invalid_path, os.O_WRONLY | os.O_CREAT, 0o600)
            os.write(descriptor, b'invalid utf-8 path\n')
            os.close(descriptor)
            subprocess.run(['git', 'add', '.'], cwd=workspace.path, check=True)
            subprocess.run(['git', 'commit', '-qm', 'invalid utf8 path'], cwd=workspace.path, check=True)
            invalid_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=workspace.path, text=True).strip()
            with self.assertRaisesRegex(RuntimeError, 'strict UTF-8'):
                workspace._changed_files(head, invalid_head)
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

    def test_valid_spec_metadata_is_in_signed_attestation(self) -> None:
        rel = 'engineering/changes/20260826-a/change-spec.yaml'
        document = {'schema_version': 2, 'acceptance_criteria': [{'id': 'AC-001', 'statement': 'signed', 'evidence': [{'receipt': 'verification'}]}]}
        runner, executor, _, _ = self.build_runner(changed_files=[rel], workspace_files={rel: json.dumps(document)})
        outcome = runner.process(self.job, 'worker-1')
        self.assertEqual(outcome.status, 'passed')
        self.assertEqual(len(executor.calls), 3)
        envelope = self.store.get_attestation(self.job.job_id)
        assert envelope is not None
        payload = verify_attestation(envelope, self.signer.public_key_pem())
        self.assertIsNotNone(payload.spec_digest)
        self.assertEqual(payload.criterion_coverage['criterion_mapped'], 1)

    def test_malformed_spec_produces_signed_failure_without_commands(self) -> None:
        rel = 'engineering/changes/20260826-a/change-spec.yaml'
        malformed = '{bad json'
        runner, executor, _, _ = self.build_runner(changed_files=[rel], workspace_files={rel: malformed})
        outcome = runner.process(self.job, 'worker-1')
        self.assertEqual(outcome.status, 'failed')
        self.assertEqual(executor.calls, [])
        envelope = self.store.get_attestation(self.job.job_id)
        assert envelope is not None
        payload = verify_attestation(envelope, self.signer.public_key_pem())
        self.assertEqual(payload.status, 'failed')
        entries = [{'path': rel, 'raw_digest': hashlib.sha256(malformed.encode()).hexdigest(), 'semantic_digest': None}]
        expected = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(payload.spec_digest, expected)
        self.assertEqual(payload.criterion_coverage, {'spec_count': 0, 'criterion_total': 0, 'criterion_mapped': 0, 'unmapped_ids': []})
        self.assertEqual(payload.command_results[-1]['name'], 'typed-spec-metadata')

    def test_unpaired_surrogate_produces_signed_failure_with_raw_provenance(self) -> None:
        rel = 'engineering/changes/20260826-surrogate/change-spec.yaml'
        document = {
            'schema_version': 2,
            'acceptance_criteria': [
                {'id': 'AC-001', 'statement': 'bad\ud800value', 'evidence': [{'receipt': 'verification'}]},
            ],
        }
        raw = json.dumps(document)
        runner, executor, _, _ = self.build_runner(changed_files=[rel], workspace_files={rel: raw})
        outcome = runner.process(self.job, 'worker-1')
        self.assertEqual(outcome.status, 'failed')
        self.assertEqual(executor.calls, [])
        envelope = self.store.get_attestation(self.job.job_id)
        assert envelope is not None
        payload = verify_attestation(envelope, self.signer.public_key_pem())
        entries = [{'path': rel, 'raw_digest': hashlib.sha256(raw.encode()).hexdigest(), 'semantic_digest': None}]
        expected = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(payload.spec_digest, expected)
        self.assertEqual(payload.criterion_coverage, {'spec_count': 0, 'criterion_total': 0, 'criterion_mapped': 0, 'unmapped_ids': []})
        self.assertEqual(payload.command_results[-1]['name'], 'typed-spec-metadata')

    def test_duplicate_local_ids_across_specs_produce_passing_signed_metadata(self) -> None:
        paths = [f'engineering/changes/20260826-{name}/change-spec.yaml' for name in ('alpha', 'bravo')]
        document = json.dumps({'schema_version': 2, 'acceptance_criteria': [{'id': 'AC-001', 'statement': 'local', 'evidence': [{'receipt': 'verification'}]}]})
        runner, executor, _, _ = self.build_runner(
            changed_files=list(reversed(paths)),
            workspace_files={path: document for path in paths},
        )
        outcome = runner.process(self.job, 'worker-1')
        self.assertEqual(outcome.status, 'passed')
        self.assertEqual(len(executor.calls), 3)
        envelope = self.store.get_attestation(self.job.job_id)
        assert envelope is not None
        payload = verify_attestation(envelope, self.signer.public_key_pem())
        self.assertEqual(payload.criterion_coverage, {'spec_count': 2, 'criterion_total': 2, 'criterion_mapped': 2, 'unmapped_ids': []})

    def test_aggregate_coverage_limit_produces_signed_failure_not_constructor_error(self) -> None:
        paths = [f'engineering/changes/20260826-{name}/change-spec.yaml' for name in ('alpha', 'bravo')]
        documents = {}
        for path, count in zip(paths, (251, 250), strict=True):
            documents[path] = json.dumps({
                'schema_version': 2,
                'acceptance_criteria': [
                    {'id': f'AC-{index:03d}', 'statement': 'bounded', 'evidence': []}
                    for index in range(1, count + 1)
                ],
            })
        runner, executor, _, _ = self.build_runner(changed_files=paths, workspace_files=documents)
        outcome = runner.process(self.job, 'worker-1')
        self.assertEqual(outcome.status, 'failed')
        self.assertEqual(executor.calls, [])
        envelope = self.store.get_attestation(self.job.job_id)
        assert envelope is not None
        payload = verify_attestation(envelope, self.signer.public_key_pem())
        self.assertIsNotNone(payload.spec_digest)
        self.assertEqual(payload.criterion_coverage, {'spec_count': 0, 'criterion_total': 0, 'criterion_mapped': 0, 'unmapped_ids': []})
        self.assertIn('aggregate unmapped criterion limit exceeded', outcome.details['commands'][-1]['stderr_tail'])

    def test_committed_pre_m1_golden_replays_through_job_runner_without_workspace(self) -> None:
        fixture = json.loads((Path(__file__).parent / 'fixtures/pre-m1-attestation-postgres.json').read_text(encoding='utf-8'))
        envelope = AttestationEnvelope.from_dict(fixture['envelope'])
        payload = envelope.payload
        store = MemoryStore()
        request = JobRequest(
            repository=payload.repository,
            pr_number=payload.pr_number,
            base_sha=payload.base_sha,
            head_sha=payload.head_sha,
            head_ref='feat/pre-m1',
            base_ref='main',
        )
        job, _ = store.enqueue(request, payload.policy_digest, self.policy.max_attempts, now=now())
        with store._lock:
            stored_job = store._jobs.pop(job.job_id)
            stored_job.job_id = payload.job_id
            store._jobs[payload.job_id] = stored_job
            store._idempotency[stored_job.idempotency_key] = payload.job_id
        claimed = store.claim('golden-worker', self.policy.lease_seconds, now=now())
        assert claimed is not None
        store.record_attestation(payload.job_id, envelope)

        class PublicVerifier:
            def public_key_pem(self):
                return fixture['public_key_pem'].encode()

        github = FakeGitHub()
        runner = JobRunner(
            store=store,
            policy=replace(self.policy, digest=payload.policy_digest),
            github=github,
            signer=PublicVerifier(),
            github_token_provider=lambda: self.fail('replay requested a token'),
            public_base_url='https://ci.example.com',
            workspace_root=Path(tempfile.gettempdir()),
            workspace_host_root=Path('/host/trust-ci-workspaces'),
            holdout_host_path=Path('/host/trust-ci-holdout'),
            now_fn=now,
            workspace_factory=lambda *_args, **_kwargs: self.fail('replay created a workspace'),
        )
        outcome = runner.process(claimed, 'golden-worker')
        self.assertEqual(outcome.status, 'passed')
        self.assertTrue(outcome.details['replayed'])
        self.assertEqual(store.get_attestation(payload.job_id).to_dict(), fixture['envelope'])
        self.assertEqual(github.completed[-1][2]['conclusion'], 'success')

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
        rel = 'engineering/changes/20260826-replay/change-spec.yaml'
        document = {'schema_version': 2, 'acceptance_criteria': [{'id': 'AC-001', 'statement': 'replay', 'evidence': [{'receipt': 'verification'}]}]}
        runner, _, _, _ = self.build_runner(
            changed_files=[rel],
            workspace_files={rel: json.dumps(document)},
            github=first_github,
        )
        with self.assertRaisesRegex(RuntimeError, 'GitHub unavailable'):
            runner.process(self.job, 'worker-1')
        stored = self.store.get_attestation(self.job.job_id)
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertIsNotNone(verify_attestation(stored, self.signer.public_key_pem()).spec_digest)
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
