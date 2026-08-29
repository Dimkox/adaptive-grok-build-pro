from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from _support import now, policy_data, sha
from adaptive_trust_ci.api import create_app
from adaptive_trust_ci.models import ApprovalPayload, JobRequest, utc_now
from adaptive_trust_ci.policy import Policy, PolicyCatalog
from adaptive_trust_ci.settings import ApiSettings, CommonSettings
from adaptive_trust_ci.signing import Signer, TrustStore, sign_approval
from adaptive_trust_ci.store import MemoryStore


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.common = CommonSettings(
            database_url='postgresql://unused',
            policy_path=base / 'policy.json',
            public_base_url='https://ci.example.com',
            kill_switch_path=base / 'STOP',
        )
        self.settings = ApiSettings(
            common=self.common,
            webhook_secret='wh-secret',
            trust_store_path=base / 'trust-store.json',
            read_token='read-token',
        )
        self.policy = Policy.from_dict(policy_data())
        self.human = Signer.generate()
        self.trust_store = TrustStore.from_dict(
            {
                'schema_version': 1,
                'keys': [
                    {
                        'key_id': self.human.key_id,
                        'actor': 'dmitry',
                        'scopes': ['governance', 'database'],
                        'public_key_pem': self.human.public_key_pem().decode(),
                    }
                ],
            }
        )
        self.store = MemoryStore()
        self.client = TestClient(
            create_app(
                self.settings,
                store=self.store,
                policy=self.policy,
                trust_store=self.trust_store,
            )
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    @property
    def read_headers(self) -> dict[str, str]:
        return {'Authorization': 'Bearer read-token'}

    def webhook_body(self, action='opened', *, repository='Dimkox/adaptive-grok-build-pro') -> bytes:
        return json.dumps(
            {
                'action': action,
                'repository': {'full_name': repository},
                'pull_request': {
                    'number': 15,
                    'draft': False,
                    'head': {'sha': sha('b'), 'ref': 'feat/x'},
                    'base': {'sha': sha('a'), 'ref': 'main'},
                },
            }
        ).encode()

    def headers(self, body: bytes) -> dict[str, str]:
        signature = hmac.new(self.settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        return {'X-Hub-Signature-256': f'sha256={signature}', 'X-GitHub-Event': 'pull_request'}

    def catalog(self, *, changed=False) -> PolicyCatalog:
        common = policy_data()
        common.pop('allowed_repositories')
        common.pop('commands')
        common.pop('holdout')
        data = {
            **common,
            'repository_profiles': [
                {
                    'repository': 'Dimkox/adaptive-grok-build-pro',
                    'commands': policy_data()['commands'],
                    'holdout': {**policy_data(holdout_digest='a' * 64)['holdout'], 'host_path': '/srv/holdouts/adaptive-grok-build-pro'},
                },
                {
                    'repository': 'Dimkox/ii-tonya-platform',
                    'commands': [
                        {'name': 'platform-unit', 'argv': ['pytest', '-q'], 'timeout_seconds': 120, 'required': True},
                    ],
                    'holdout': {**policy_data(holdout_digest='b' * 64)['holdout'], 'host_path': '/srv/holdouts/ii-tonya-platform'},
                },
            ],
        }
        if changed:
            data['repository_profiles'][0]['commands'][0]['name'] = 'unit-v2'
        return PolicyCatalog.from_dict(data)

    def test_health_reports_policy_digest_and_worker_publisher(self) -> None:
        response = self.client.get('/health/ready')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['policy_digest'], self.policy.digest)
        self.assertEqual(response.json()['status_publisher'], 'worker-github-app')

    def test_signed_webhook_only_enqueues_for_worker_publisher(self) -> None:
        body = self.webhook_body()
        response = self.client.post('/webhooks/github', content=body, headers=self.headers(body))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['created'])
        self.assertEqual(response.json()['status_publisher'], 'worker-github-app')
        self.assertEqual(self.store.get_job(response.json()['job_id']).status, 'queued')

    def test_duplicate_webhook_reuses_idempotent_job(self) -> None:
        body = self.webhook_body()
        first = self.client.post('/webhooks/github', content=body, headers=self.headers(body))
        second = self.client.post('/webhooks/github', content=body, headers=self.headers(body))
        self.assertEqual(first.json()['job_id'], second.json()['job_id'])
        self.assertFalse(second.json()['created'])

    def test_invalid_webhook_signature_is_rejected(self) -> None:
        body = self.webhook_body()
        response = self.client.post(
            '/webhooks/github',
            content=body,
            headers={'X-Hub-Signature-256': 'sha256=' + '0' * 64, 'X-GitHub-Event': 'pull_request'},
        )
        self.assertEqual(response.status_code, 401)

    def test_disallowed_repository_is_rejected(self) -> None:
        body = self.webhook_body(repository='attacker/repo')
        response = self.client.post('/webhooks/github', content=body, headers=self.headers(body))
        self.assertEqual(response.status_code, 403)

    def test_catalog_webhook_binds_selected_repository_digest(self) -> None:
        catalog = self.catalog()
        store = MemoryStore()
        client = TestClient(create_app(self.settings, store=store, policy=catalog, trust_store=self.trust_store))
        for repository in ('Dimkox/adaptive-grok-build-pro', 'Dimkox/ii-tonya-platform'):
            body = self.webhook_body(repository=repository)
            response = client.post('/webhooks/github', content=body, headers=self.headers(body))
            self.assertEqual(response.status_code, 200)
            job = store.get_job(response.json()['job_id'])
            self.assertEqual(job.policy_digest, catalog.resolve_repository(job.repository).digest)

    def test_catalog_case_variant_is_rejected_and_health_is_low_cardinality(self) -> None:
        catalog = self.catalog()
        store = MemoryStore()
        client = TestClient(create_app(self.settings, store=store, policy=catalog, trust_store=self.trust_store))
        body = self.webhook_body(repository='dimkox/ii-tonya-platform')
        self.assertEqual(client.post('/webhooks/github', content=body, headers=self.headers(body)).status_code, 403)
        health = client.get('/health/ready')
        self.assertEqual(health.status_code, 200)
        payload = health.json()
        self.assertEqual(payload['catalog_digest'], catalog.digest)
        self.assertEqual(payload['policy_mode'], 'catalog')
        self.assertEqual(payload['profile_count'], 2)
        self.assertNotIn('Dimkox/ii-tonya-platform', health.text)

    def test_unknown_and_case_variant_closed_events_cannot_cancel_configured_jobs(self) -> None:
        opened = self.webhook_body()
        self.client.post('/webhooks/github', content=opened, headers=self.headers(opened))
        for repository in ('attacker/repo', 'dimkox/adaptive-grok-build-pro'):
            closed = self.webhook_body('closed', repository=repository)
            response = self.client.post('/webhooks/github', content=closed, headers=self.headers(closed))
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.store.get_job_for_sha('Dimkox/adaptive-grok-build-pro', sha('b')).status, 'queued')

    def test_catalog_approval_fails_closed_when_bound_profile_is_removed(self) -> None:
        catalog = self.catalog()
        store = MemoryStore()
        first_client = TestClient(create_app(self.settings, store=store, policy=catalog, trust_store=self.trust_store))
        body = self.webhook_body(repository='Dimkox/adaptive-grok-build-pro')
        job = store.get_job(first_client.post('/webhooks/github', content=body, headers=self.headers(body)).json()['job_id'])
        assert job is not None
        claimed = store.claim('worker', catalog.lease_seconds, now=now())
        assert claimed is not None
        store.finish(job.job_id, 'worker', 'needs_approval', {'missing_scopes': ['governance']}, failure_code='approval-required', now=now())
        payload = ApprovalPayload.new(
            actor='dmitry', key_id=self.human.key_id, repository=job.repository,
            pr_number=job.pr_number, base_sha=job.base_sha, head_sha=job.head_sha,
            policy_digest=job.policy_digest, scope='governance', reason='reviewed', now=utc_now(),
        )
        changed_client = TestClient(create_app(self.settings, store=store, policy=self.catalog(changed=True), trust_store=self.trust_store))
        response = changed_client.post('/approvals', json=sign_approval(payload, self.human).to_dict())
        self.assertEqual(response.status_code, 409)
        self.assertEqual(store.get_job(job.job_id).status, 'needs_approval')

    def test_kill_switch_blocks_new_jobs_without_needing_github_credentials(self) -> None:
        self.common.kill_switch_path.write_text('stop')
        body = self.webhook_body()
        response = self.client.post('/webhooks/github', content=body, headers=self.headers(body))
        self.assertEqual(response.status_code, 503)
        self.assertIsNone(self.store.get_job_for_sha('Dimkox/adaptive-grok-build-pro', sha('b')))

    def test_closed_pull_request_cancels_active_job(self) -> None:
        opened = self.webhook_body()
        self.client.post('/webhooks/github', content=opened, headers=self.headers(opened))
        closed = self.webhook_body('closed')
        response = self.client.post('/webhooks/github', content=closed, headers=self.headers(closed))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['cancelled_jobs'], 1)

    def test_signed_approval_requeues_matching_waiting_job(self) -> None:
        request = JobRequest(
            repository='Dimkox/adaptive-grok-build-pro',
            pr_number=15,
            base_sha=sha('a'),
            head_sha=sha('b'),
            head_ref='feat/x',
            base_ref='main',
        )
        job, _ = self.store.enqueue(request, self.policy.digest, self.policy.max_attempts, now=now())
        claimed = self.store.claim('worker', self.policy.lease_seconds, now=now())
        assert claimed is not None
        self.store.finish(
            job.job_id,
            'worker',
            'needs_approval',
            {'missing_scopes': ['governance']},
            failure_code='approval-required',
            now=now(),
        )
        payload = ApprovalPayload.new(
            actor='dmitry',
            key_id=self.human.key_id,
            repository=job.repository,
            pr_number=job.pr_number,
            base_sha=job.base_sha,
            head_sha=job.head_sha,
            policy_digest=job.policy_digest,
            scope='governance',
            reason='reviewed exact SHA',
            now=utc_now(),
        )
        response = self.client.post('/approvals', json=sign_approval(payload, self.human).to_dict())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['requeued_jobs'], 1)
        self.assertEqual(response.json()['status_publisher'], 'worker-github-app')
        self.assertEqual(self.store.get_job(job.job_id).status, 'queued')

    def test_tampered_approval_is_rejected(self) -> None:
        request = JobRequest(
            repository='Dimkox/adaptive-grok-build-pro',
            pr_number=15,
            base_sha=sha('a'),
            head_sha=sha('b'),
            head_ref='feat/x',
            base_ref='main',
        )
        job, _ = self.store.enqueue(request, self.policy.digest, self.policy.max_attempts, now=now())
        payload = ApprovalPayload.new(
            actor='dmitry',
            key_id=self.human.key_id,
            repository=job.repository,
            pr_number=job.pr_number,
            base_sha=job.base_sha,
            head_sha=job.head_sha,
            policy_digest=job.policy_digest,
            scope='governance',
            reason='reviewed',
            now=now(),
        )
        envelope = sign_approval(payload, self.human).to_dict()
        envelope['payload']['reason'] = 'tampered'
        response = self.client.post('/approvals', json=envelope)
        self.assertEqual(response.status_code, 403)

    def test_server_trust_store_revocation_is_reloaded_without_api_restart(self) -> None:
        issued = utc_now()
        trust_data = {
            'schema_version': 2,
            'keys': [
                {
                    'key_id': self.human.key_id,
                    'actor': 'dmitry',
                    'scopes': ['governance'],
                    'not_before': (issued - timedelta(days=1)).isoformat(),
                    'not_after': (issued + timedelta(days=1)).isoformat(),
                    'revoked_at': None,
                    'public_key_pem': self.human.public_key_pem().decode(),
                }
            ],
        }
        self.settings.trust_store_path.write_text(json.dumps(trust_data), encoding='utf-8')
        dynamic_store = MemoryStore()
        client = TestClient(
            create_app(
                self.settings,
                store=dynamic_store,
                policy=self.policy,
                trust_store=None,
            )
        )
        request = JobRequest(
            repository='Dimkox/adaptive-grok-build-pro',
            pr_number=15,
            base_sha=sha('a'),
            head_sha=sha('b'),
            head_ref='feat/x',
            base_ref='main',
        )
        job, _ = dynamic_store.enqueue(request, self.policy.digest, self.policy.max_attempts, now=issued)
        payload = ApprovalPayload.new(
            actor='dmitry',
            key_id=self.human.key_id,
            repository=job.repository,
            pr_number=job.pr_number,
            base_sha=job.base_sha,
            head_sha=job.head_sha,
            policy_digest=job.policy_digest,
            scope='governance',
            reason='reviewed',
            now=issued,
        )
        envelope = sign_approval(payload, self.human).to_dict()
        trust_data['keys'][0]['revoked_at'] = (utc_now() - timedelta(seconds=1)).isoformat()
        self.settings.trust_store_path.write_text(json.dumps(trust_data), encoding='utf-8')
        response = client.post('/approvals', json=envelope)
        self.assertEqual(response.status_code, 403)
        self.assertIn('revoked', response.text)

    def test_job_and_attestation_reads_require_bearer_token(self) -> None:
        request = JobRequest(
            repository='Dimkox/adaptive-grok-build-pro',
            pr_number=15,
            base_sha=sha('a'),
            head_sha=sha('b'),
            head_ref='feat/x',
            base_ref='main',
        )
        job, _ = self.store.enqueue(request, self.policy.digest, self.policy.max_attempts, now=now())
        self.assertEqual(self.client.get(f'/jobs/{job.job_id}').status_code, 401)
        self.assertEqual(self.client.get(f'/jobs/{job.job_id}', headers={'Authorization': 'Bearer wrong'}).status_code, 401)
        self.assertEqual(self.client.get(f'/jobs/{job.job_id}', headers=self.read_headers).status_code, 200)
        self.assertEqual(self.client.get(f'/attestations/{job.job_id}').status_code, 401)
        self.assertEqual(self.client.get(f'/attestations/{job.job_id}', headers=self.read_headers).status_code, 404)

    def test_authorized_job_endpoint_does_not_return_command_output(self) -> None:
        request = JobRequest(
            repository='Dimkox/adaptive-grok-build-pro',
            pr_number=15,
            base_sha=sha('a'),
            head_sha=sha('b'),
            head_ref='feat/x',
            base_ref='main',
        )
        job, _ = self.store.enqueue(request, self.policy.digest, self.policy.max_attempts, now=now())
        claimed = self.store.claim('worker', self.policy.lease_seconds, now=now())
        assert claimed is not None
        self.store.finish(
            job.job_id,
            'worker',
            'failed',
            {'commands': [{'name': 'unit', 'status': 'fail', 'stdout_tail': 'secret output'}]},
            now=now(),
        )
        response = self.client.get(f'/jobs/{job.job_id}', headers=self.read_headers)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('stdout_tail', response.text)
        self.assertNotIn('secret output', response.text)

    def test_metrics_require_bearer_and_expose_no_high_cardinality_data(self) -> None:
        body = self.webhook_body()
        queued = self.client.post('/webhooks/github', content=body, headers=self.headers(body)).json()
        self.assertEqual(self.client.get('/metrics').status_code, 401)
        response = self.client.get('/metrics', headers=self.read_headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers['content-type'].startswith('text/plain'))
        self.assertIn('adaptive_trust_ci_jobs{status="queued"} 1', response.text)
        self.assertIn(self.policy.check_name, response.text)
        self.assertNotIn('Dimkox', response.text)
        self.assertNotIn(sha('b'), response.text)
        self.assertNotIn(queued['job_id'], response.text)

    def test_metrics_reflect_kill_switch(self) -> None:
        self.common.kill_switch_path.write_text('stop')
        response = self.client.get('/metrics', headers=self.read_headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn('adaptive_trust_ci_kill_switch 1', response.text)


if __name__ == '__main__':
    unittest.main()
