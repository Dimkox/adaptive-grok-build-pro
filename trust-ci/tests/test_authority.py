from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from _support import now, policy_data, sha
from adaptive_trust_ci.api import create_app
from adaptive_trust_ci.holdout import bundle_digest
from adaptive_trust_ci.models import (
    ApprovalPayload, AttestationEnvelope, AttestationPayload, JobRequest,
    canonical_json, parse_datetime,
)
from adaptive_trust_ci.policy import PolicyCatalog
from adaptive_trust_ci.settings import ApiSettings, CommonSettings
from adaptive_trust_ci.signing import Signer, TrustStore, sign_approval, sign_attestation
from adaptive_trust_ci.store import MemoryStore


class AuthorityTests(unittest.TestCase):
    """All keys are ephemeral synthetic fixtures; only public bytes touch disk."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.holdout = self.root / 'holdout'
        self.holdout.mkdir()
        (self.holdout / 'validate.py').write_text('# synthetic holdout\n')
        self.data = policy_data(holdout_path=str(self.holdout), holdout_digest=bundle_digest(self.holdout))
        self.policy_path = self.root / 'policy.json'
        self.policy_path.write_text(json.dumps(self.data))
        self.catalog = PolicyCatalog.from_dict(self.data)
        self.policy = self.catalog.profiles[0]
        self.approver = Signer.generate()
        self.ci = Signer.generate()
        self.public_path = self.root / 'ci-public.pem'
        self.public_path.write_bytes(self.ci.public_key_pem())
        self.trust_data = {'schema_version': 2, 'keys': [{
            'key_id': self.approver.key_id, 'actor': 'synthetic-reviewer',
            'scopes': ['governance', 'database'],
            'public_key_pem': self.approver.public_key_pem().decode(),
        }]}
        self.trust_path = self.root / 'trust.json'
        self.trust_path.write_text(json.dumps(self.trust_data))
        self.trust = TrustStore.from_dict(self.trust_data)
        self.settings = ApiSettings(
            CommonSettings('postgresql://unused', self.policy_path, 'https://ci.example', self.root / 'STOP'),
            'synthetic-webhook', self.trust_path, 'synthetic-read',
        )
        self.headers = {'Authorization': 'Bearer synthetic-read'}
        self.store = MemoryStore()
        request = JobRequest('Dimkox/adaptive-grok-build-pro', 19, sha('a'), sha('b'), 'feature', 'main')
        self.job, _ = self.store.enqueue(request, self.policy.digest, 3, now=now())
        self.changed = ['trust-ci/src/synthetic.py']
        self.store.claim('fixture-worker', 90, now=now())
        self.store.finish(self.job.job_id, 'fixture-worker', 'passed', {'changed_files': self.changed}, now=now())
        self.attest()
        self.approve()
        self.clock = patch('adaptive_trust_ci.authority.utc_now', return_value=now())

    def approve(self, *, ttl=900, issued=None, approval_id=None, **changes):
        payload = ApprovalPayload.new(
            actor='synthetic-reviewer', key_id=self.approver.key_id,
            repository=self.job.repository, pr_number=self.job.pr_number,
            base_sha=self.job.base_sha, head_sha=self.job.head_sha,
            policy_digest=self.policy.digest, scope='governance', reason='synthetic fixture',
            now=issued or now(), ttl_seconds=ttl,
        )
        if approval_id:
            changes['approval_id'] = approval_id
        payload = dataclasses.replace(payload, **changes)
        envelope = sign_approval(payload, self.approver)
        self.store.record_approval(payload, envelope, now=now())
        return envelope

    def attest(self, **changes):
        commands = [{'name': 'holdout-bundle-integrity', 'status': 'pass', 'exit_code': 0,
                     'duration_seconds': 0.0, 'output_sha256': self.policy.holdout.digest}]
        for command in self.policy.commands + self.policy.holdout.commands:
            commands.append({'name': command.name, 'status': 'pass', 'exit_code': 0,
                'duration_seconds': 0.0, 'output_sha256': '0' * 64})
        payload = AttestationPayload(
            1, 'synthetic-attestation', self.job.job_id, self.job.repository, self.job.pr_number,
            self.job.base_sha, self.job.head_sha, self.policy.digest, 'passed', tuple(commands),
            tuple(self.changed), ('governance',), now().isoformat(), now().isoformat(), self.ci.key_id,
        )
        payload = dataclasses.replace(payload, **changes)
        self.envelope = sign_attestation(payload, self.ci)
        self.store._attestations[self.job.job_id] = self.envelope

    def client(self, **kwargs):
        return TestClient(create_app(self.settings, store=self.store, **kwargs))

    def get(self, client=None, *, job_id=None):
        with patch.dict('os.environ', {'TRUST_CI_ATTESTATION_PUBLIC_KEY_PATH': str(self.public_path)}):
            with self.clock:
                return (client or self.client()).get('/authority/' + (job_id or self.job.job_id), headers=self.headers)

    def snapshot(self, **kwargs):
        from adaptive_trust_ci.authority import current_job_authority
        with self.clock:
            return current_job_authority(
                self.store, self.job.job_id,
                current_catalog=kwargs.pop('current_catalog', lambda: PolicyCatalog.load(self.policy_path)),
                current_trust_store=kwargs.pop('current_trust_store', lambda: TrustStore.load(self.trust_path)),
                current_attestation_public_key=kwargs.pop('current_attestation_public_key', self.public_path.read_bytes),
                stopped=kwargs.pop('stopped', lambda: self.settings.common.stopped), **kwargs,
            )

    def test_authority_route_requires_existing_read_bearer(self):
        for supplied in ({}, {'Authorization': 'Bearer incorrect'}):
            with self.subTest(headers=supplied):
                response = self.client().get('/authority/' + self.job.job_id, headers=supplied)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.headers['www-authenticate'], 'Bearer')

    def test_exact_snapshot_is_public_closed_and_short_lived(self):
        response = self.get()
        self.assertEqual(response.status_code, 200, response.text)
        value = response.json()
        self.assertEqual(set(value), {'schema_version', 'repository', 'pr_number', 'base_sha', 'head_sha',
            'job_id', 'policy_digest', 'check_name', 'holdout_digest', 'required_scopes', 'approvals',
            'trust_revision', 'attestation_digest', 'observed_at', 'valid_until'})
        self.assertEqual(value['schema_version'], 1)
        self.assertEqual(value['repository'], 'Dimkox/adaptive-grok-build-pro')
        self.assertEqual(value['pr_number'], 19)
        self.assertEqual(value['base_sha'], 'a' * 40)
        self.assertEqual(value['head_sha'], 'b' * 40)
        self.assertEqual(value['job_id'], self.job.job_id)
        self.assertEqual(value['policy_digest'], self.policy.digest)
        self.assertEqual(value['check_name'], self.policy.check_name)
        self.assertEqual(value['holdout_digest'], self.policy.holdout.digest)
        self.assertEqual(value['required_scopes'], ['governance'])
        self.assertEqual(parse_datetime(value['valid_until']), now() + timedelta(seconds=60))
        self.assertEqual(value['attestation_digest'], hashlib.sha256(canonical_json(self.envelope.to_dict())).hexdigest())
        self.assertEqual(set(value['approvals'][0]), {'scope', 'envelope_digest', 'expires_at', 'key_id'})
        for private in ('signature', 'public_key_pem', 'synthetic fixture', 'synthetic-read', 'PRIVATE KEY'):
            self.assertNotIn(private, response.text)
        self.assertEqual(self.store.get_job(self.job.job_id).status, 'passed')

    def test_snapshot_conforms_to_versioned_closed_openapi_schema(self):
        validator_path = Path(__file__).resolve().parents[2] / 'tests/json_schema_subset.py'
        module_spec = importlib.util.spec_from_file_location('authority_schema_validator', validator_path)
        validator_module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(validator_module)
        contract = json.loads((Path(__file__).resolve().parents[2] /
            'engineering/contracts/openapi/trust-ci.v1.json').read_text())
        self.assertIn('/authority/{job_id}', contract['paths'])
        operation = contract['paths']['/authority/{job_id}']['get']
        self.assertEqual(operation['security'], [{'bearerAuth': []}])
        self.assertEqual(set(operation['responses']), {'200', '401', '409'})
        schema = dict(contract['components']['schemas']['CurrentAuthoritySnapshotV1'])
        schema.pop('description', None)  # Human annotation is outside the strict validation subset.
        validator = validator_module.SubsetValidator(schema)
        snapshot = self.snapshot()
        validator.validate(snapshot)
        for extra in ({**snapshot, 'merge_allowed': True}, {**snapshot, 'schema_version': 2},
                      {**snapshot, 'approvals': [{**snapshot['approvals'][0], 'signature': 'secret'}]}):
            with self.subTest(extra=extra):
                with self.assertRaises(validator_module.SchemaValidationError):
                    validator.validate(extra)

    def test_stopped_missing_and_incomplete_jobs_fail_closed(self):
        self.assertEqual(self.get(job_id='absent').status_code, 409)
        for status in ('queued', 'running', 'needs_approval', 'failed', 'cancelled', 'dead'):
            with self.subTest(status=status):
                self.store._jobs[self.job.job_id].status = status
                self.assertEqual(self.get().status_code, 409)
        self.store._jobs[self.job.job_id].status = 'passed'
        (self.root / 'STOP').touch()
        self.assertEqual(self.get().status_code, 409)

    def test_each_attestation_tuple_identity_is_bound(self):
        changes = {'repository': 'Other/repository', 'pr_number': 20, 'base_sha': sha('c'),
                   'head_sha': sha('c'), 'policy_digest': 'c' * 64, 'job_id': 'different'}
        for field, value in changes.items():
            with self.subTest(field=field):
                self.attest(**{field: value})
                self.assertEqual(self.get().status_code, 409)

    def test_invalid_attestation_signature_and_current_ci_key_fail_closed(self):
        self.store._attestations[self.job.job_id] = AttestationEnvelope(self.envelope.payload, 'AAAA')
        self.assertEqual(self.get().status_code, 409)
        self.attest()
        self.public_path.write_bytes(Signer.generate().public_key_pem())
        self.assertEqual(self.get().status_code, 409)

    def test_public_key_access_time_update_does_not_invalidate_stable_source(self):
        current = self.public_path.stat()
        os.utime(self.public_path, ns=(1_000_000_000, current.st_mtime_ns))
        response = self.get()
        self.assertEqual(response.status_code, 200, response.text)

    def test_explicit_public_provider_is_verified_without_file_fallback(self):
        self.public_path.unlink()
        client = self.client(current_attestation_public_key=self.ci.public_key_pem)
        self.assertEqual(self.get(client).status_code, 200)
        incorrect = self.client(current_attestation_public_key=Signer.generate().public_key_pem)
        self.assertEqual(self.get(incorrect).status_code, 409)

    def test_ci_public_source_rejects_oversize_fifo_and_symlink_parent(self):
        self.public_path.write_bytes(b'x' * 16385)
        self.assertEqual(self.get().status_code, 409)
        self.public_path.unlink()
        os.mkfifo(self.public_path)
        self.assertEqual(self.get().status_code, 409)
        self.public_path.unlink()
        self.public_path.write_bytes(self.ci.public_key_pem())
        link = self.root / 'linked-parent'
        link.symlink_to(self.root, target_is_directory=True)
        with patch.dict('os.environ', {'TRUST_CI_ATTESTATION_PUBLIC_KEY_PATH': str(link / 'ci-public.pem')}):
            with self.clock:
                response = self.client().get('/authority/' + self.job.job_id, headers=self.headers)
        self.assertEqual(response.status_code, 409)

    def test_unknown_signed_attestation_field_fails_closed(self):
        original = self.envelope.payload.to_dict()
        original['unknown-authority'] = True
        self.store._attestations[self.job.job_id] = AttestationEnvelope.from_dict({
            'payload': original, 'signature': self.ci.sign(original),
        })
        self.assertEqual(self.get().status_code, 409)

    def test_ci_public_source_is_required_regular_absolute_readable_and_valid(self):
        for value in ('', 'relative.pem', str(self.root / 'missing')):
            with self.subTest(path=value), patch.dict('os.environ', {'TRUST_CI_ATTESTATION_PUBLIC_KEY_PATH': value}):
                with self.clock:
                    response = self.client().get('/authority/' + self.job.job_id, headers=self.headers)
                self.assertEqual(response.status_code, 409)
        original = self.public_path.read_bytes()
        self.public_path.unlink()
        target = self.root / 'target.pem'
        target.write_bytes(original)
        self.public_path.symlink_to(target)
        self.assertEqual(self.get().status_code, 409)
        self.public_path.unlink()
        self.public_path.mkdir()
        self.assertEqual(self.get().status_code, 409)
        self.public_path.rmdir()
        self.public_path.write_text('malformed public key')
        self.assertEqual(self.get().status_code, 409)
        self.public_path.write_bytes(original)
        with patch('adaptive_trust_ci.authority.os.open', side_effect=PermissionError('synthetic denied')):
            self.assertEqual(self.get().status_code, 409)

    def test_policy_reloaded_even_when_old_startup_policy_was_injected(self):
        client = self.client(policy=self.policy, trust_store=self.trust)
        self.data['commands'][0]['name'] = 'current-policy-v2'
        self.policy_path.write_text(json.dumps(self.data))
        self.assertEqual(self.get(client).status_code, 409)

    def test_current_policy_holdout_and_trust_read_errors_fail_closed(self):
        client = self.client()
        for path in (self.policy_path, self.trust_path, self.holdout / 'validate.py'):
            with self.subTest(path=path):
                original = path.read_bytes()
                path.unlink()
                self.assertEqual(self.get(client).status_code, 409)
                path.write_bytes(original)
        (self.holdout / 'validate.py').write_text('# mutated current holdout')
        self.assertEqual(self.get(client).status_code, 409)

    def test_revoked_expired_or_removed_approval_key_fails_closed(self):
        client = self.client()
        for field in ('not_after', 'revoked_at', 'not_before'):
            with self.subTest(field=field):
                self.trust_data['keys'][0][field] = (now() + timedelta(seconds=1) if field == 'not_before' else now()).isoformat()
                self.trust_path.write_text(json.dumps(self.trust_data))
                self.assertEqual(self.get(client).status_code, 409)
                del self.trust_data['keys'][0][field]
        self.trust_data['keys'] = []
        self.trust_path.write_text(json.dumps(self.trust_data))
        self.assertEqual(self.get(client).status_code, 409)

    def test_required_approval_is_verified_and_exact_tuple_bound(self):
        self.store._approvals.clear()
        for changes in ({'base_sha': sha('c')}, {'head_sha': sha('c')}, {'pr_number': 20},
                        {'repository': 'Other/repository'}, {'policy_digest': 'c' * 64}, {'scope': 'database'}):
            with self.subTest(changes=changes):
                self.store._approvals.clear()
                self.approve(**changes)
                self.assertEqual(self.get().status_code, 409)
        self.store._approvals.clear()
        envelope = self.approve()
        self.store._approvals[envelope.payload.approval_id] = (envelope.payload, dataclasses.replace(envelope, signature='AAAA'))
        self.assertEqual(self.get().status_code, 409)

    def test_expiry_bounds_each_selected_approval_and_key_cutoff(self):
        for cutoff in ('approval', 'not_after', 'revoked_at'):
            with self.subTest(cutoff=cutoff):
                self.store._approvals.clear()
                self.approve(ttl=12 if cutoff == 'approval' else 900)
                trust_data = json.loads(json.dumps(self.trust_data))
                if cutoff != 'approval':
                    trust_data['keys'][0][cutoff] = (now() + timedelta(seconds=12)).isoformat()
                self.trust_path.write_text(json.dumps(trust_data))
                self.assertEqual(parse_datetime(self.get().json()['valid_until']), now() + timedelta(seconds=12))

    def test_expired_approval_missing_attestation_or_attested_scopes_fail_closed(self):
        self.store._approvals.clear()
        self.approve(issued=now() - timedelta(seconds=901), ttl=900)
        self.assertEqual(self.get().status_code, 409)
        self.approve()
        self.attest(approved_scopes=())
        self.assertEqual(self.get().status_code, 409)
        self.store._attestations.clear()
        self.assertEqual(self.get().status_code, 409)

    def test_duplicate_scope_chooses_longest_expiry_then_smallest_id(self):
        self.store._approvals.clear()
        self.approve(ttl=30, approval_id='00000000-0000-0000-0000-000000000001')
        self.approve(ttl=900, approval_id='00000000-0000-0000-0000-000000000003')
        expected = self.approve(ttl=900, approval_id='00000000-0000-0000-0000-000000000002')
        value = self.snapshot()
        self.assertEqual(value['approvals'][0]['envelope_digest'], hashlib.sha256(canonical_json(expected.to_dict())).hexdigest())
        self.assertEqual(parse_datetime(value['valid_until']), now() + timedelta(seconds=60))

    def test_inventory_overflow_and_malformed_changed_inventory_fail_closed(self):
        for _ in range(128):
            self.approve()
        self.assertEqual(self.get().status_code, 409)
        self.store._approvals.clear()
        self.approve()
        for changed in ([], None, ['trust-ci/src/synthetic.py'] * 2, ['../escape'], ['x'] * 10001):
            with self.subTest(changed=str(changed)[:40]):
                self.store._jobs[self.job.job_id].result['changed_files'] = changed
                self.assertEqual(self.get().status_code, 409)

    def test_missing_failed_duplicate_or_unknown_attested_command_fails_closed(self):
        original = self.envelope.payload.command_results
        for commands in (original[:1], original + (original[0],),
                         ({**original[0], 'status': 'fail'},) + original[1:],
                         original + ({'name': 'unexpected', 'status': 'pass', 'exit_code': 0},)):
            with self.subTest(commands=commands):
                self.attest(command_results=commands)
                self.assertEqual(self.get().status_code, 409)

    def test_malformed_signed_attestation_inventories_fail_closed(self):
        original = self.envelope.payload.to_dict()
        for update in ({'changed_files': self.changed * 2}, {'approved_scopes': ['governance'] * 2},
                       {'command_results': [{**original['command_results'][0], 'duration_seconds': -1}] + original['command_results'][1:]},
                       {'command_results': original['command_results'][:1] + [
                           {**original['command_results'][1], 'output_sha256': 'malformed'}] + original['command_results'][2:]}):
            with self.subTest(update=update):
                raw = {**original, **update}
                self.store._attestations[self.job.job_id] = AttestationEnvelope.from_dict({
                    'payload': raw, 'signature': self.ci.sign(raw),
                })
                self.assertEqual(self.get().status_code, 409)

    def test_every_current_source_and_job_is_rechecked_before_response(self):
        for source in ('catalog', 'trust', 'ci-key', 'holdout', 'job', 'attestation', 'signed-bytes', 'approvals', 'stopped'):
            with self.subTest(source=source):
                self.setUp()
                calls = 0
                def current_catalog():
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        if source == 'catalog':
                            self.data['commands'][0]['name'] = 'rotated'
                            self.policy_path.write_text(json.dumps(self.data))
                        elif source == 'trust':
                            self.trust_data['keys'][0]['revoked_at'] = now().isoformat()
                            self.trust_path.write_text(json.dumps(self.trust_data))
                        elif source == 'ci-key':
                            self.public_path.write_bytes(Signer.generate().public_key_pem())
                        elif source == 'holdout':
                            (self.holdout / 'validate.py').write_text('# concurrent mutation')
                        elif source == 'job':
                            self.store._jobs[self.job.job_id].base_sha = sha('c')
                        elif source == 'attestation':
                            self.store._attestations[self.job.job_id] = dataclasses.replace(self.envelope, signature='AAAA')
                        elif source == 'signed-bytes':
                            self.store._attestations[self.job.job_id] = dataclasses.replace(self.envelope,
                                _signed_payload={**self.envelope.payload.to_dict(), 'unknown-field': True})
                        elif source == 'approvals':
                            self.store._approvals.clear()
                        elif source == 'stopped':
                            (self.root / 'STOP').touch()
                    return PolicyCatalog.load(self.policy_path)
                with self.assertRaises((ValueError, RuntimeError)):
                    self.snapshot(current_catalog=current_catalog)

    def test_clock_crossing_validity_cutoff_fails_closed(self):
        self.store._approvals.clear()
        self.approve(ttl=5)
        from adaptive_trust_ci.authority import current_job_authority
        with patch('adaptive_trust_ci.authority.utc_now', side_effect=[now(), now() + timedelta(seconds=5)]):
            with self.assertRaises(ValueError):
                current_job_authority(self.store, self.job.job_id, current_catalog=lambda: self.catalog,
                    current_trust_store=lambda: self.trust, current_attestation_public_key=self.ci.public_key_pem,
                    stopped=lambda: False)


if __name__ == '__main__':
    unittest.main()
