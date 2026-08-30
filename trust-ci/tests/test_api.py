from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import tempfile
import unittest
import uuid
from dataclasses import replace
from datetime import timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from _support import digest, now, policy_data, sha
from adaptive_trust_ci.api import create_app
from adaptive_trust_ci.models import (
    ApprovalPayload,
    JobRequest,
    PromotionPayload,
    ProtectedBranchAttestationPayload,
    utc_now,
)
from adaptive_trust_ci.policy import Policy
from adaptive_trust_ci.provenance import MergedPullRequestFact
from adaptive_trust_ci.settings import ApiSettings, CommonSettings, SettingsError
from adaptive_trust_ci.signing import (
    Signer,
    TrustStore,
    sign_approval,
    sign_promotion,
    sign_protected_branch_attestation,
)
from adaptive_trust_ci.store import MemoryStore


class PolicyRotatingStore(MemoryStore):
    def __init__(self, rotate_policy) -> None:
        super().__init__()
        self._rotate_policy = rotate_policy

    def ping(self) -> None:
        callback, self._rotate_policy = self._rotate_policy, None
        if callback is not None:
            callback()


class StoreEntryPolicyRotatingStore(MemoryStore):
    def __init__(self, replacement_epoch: str) -> None:
        super().__init__()
        self.replacement_epoch = replacement_epoch
        self.rotation_completed = False

    def accept_promotion(self, *args, **kwargs):
        with self._lock:
            self._active_policy_epoch = self.replacement_epoch
            self.rotation_completed = True
        return super().accept_promotion(*args, **kwargs)


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
        self.common.policy_path.write_text(json.dumps(policy_data()), encoding='utf-8')
        self.human = Signer.generate()
        self.trust_store = TrustStore.from_dict(
            {
                'schema_version': 1,
                'keys': [
                    {
                        'key_id': self.human.key_id,
                        'actor': 'dmitry',
                        'scopes': ['governance', 'database', 'promotion:production'],
                        'public_key_pem': self.human.public_key_pem().decode(),
                    }
                ],
            }
        )
        self.store = MemoryStore()
        self.store.activate_policy(self.policy.digest)
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

    def merged_webhook_body(self) -> bytes:
        return json.dumps(
            {
                'action': 'closed',
                'installation': {'id': 42},
                'repository': {
                    'id': 101,
                    'full_name': 'Dimkox/adaptive-grok-build-pro',
                },
                'pull_request': {
                    'number': 15,
                    'merged': True,
                    'merged_at': '2026-08-30T11:59:00Z',
                    'merge_commit_sha': sha('c'),
                    'head': {'sha': sha('b'), 'ref': 'feat/x'},
                    'base': {'sha': sha('a'), 'ref': 'main'},
                },
            },
            separators=(',', ':'),
        ).encode()

    def headers(self, body: bytes, *, delivery_id: str = 'delivery-1') -> dict[str, str]:
        signature = hmac.new(self.settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        return {
            'X-Hub-Signature-256': f'sha256={signature}',
            'X-GitHub-Event': 'pull_request',
            'X-GitHub-Delivery': delivery_id,
        }

    def promotion_envelope(self, *, signer=None, **changes):
        current = utc_now().astimezone(timezone.utc).replace(microsecond=0)
        selected_signer = signer or self.human
        ci_signer = Signer.generate()
        merged_sha = uuid.uuid4().hex + uuid.uuid4().hex[:8]
        fact = MergedPullRequestFact.create(
            delivery_id=f'promotion-{uuid.uuid4()}',
            payload_sha256=digest('d'),
            repository_id=101,
            repository='dimkox/adaptive-grok-build-pro',
            installation_id=42,
            pr_number=15,
            head_sha=sha('b'),
            base_sha=sha('a'),
            protected_ref='refs/heads/main',
            merged_commit_sha=merged_sha,
            merged_at=(current - timedelta(minutes=2)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            received_at=current,
        )
        self.store.record_merge_fact(fact)
        evidence_payload = ProtectedBranchAttestationPayload(
            schema_version=1,
            source_attestation_id=str(uuid.uuid4()),
            merge_fact_id=fact.merge_fact_id,
            repository=fact.repository,
            protected_ref=fact.protected_ref,
            merged_commit_sha=fact.merged_commit_sha,
            policy_epoch=self.policy.digest,
            runner_digest=digest('1'),
            holdout_digest=digest('2'),
            image_digest=digest('3'),
            artifact_sha256=digest('b'),
            result='passed',
            issued_at=(current - timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            key_id=ci_signer.key_id,
        )
        self.store.record_protected_branch_evidence(
            sign_protected_branch_attestation(evidence_payload, ci_signer)
        )
        values = {
            'schema_version': 1,
            'promotion_id': str(uuid.uuid4()),
            'nonce': __import__('base64').urlsafe_b64encode(os.urandom(32)).decode().rstrip('='),
            'actor': 'dmitry',
            'key_id': selected_signer.key_id,
            'repository': evidence_payload.repository,
            'merged_commit_sha': evidence_payload.merged_commit_sha,
            'artifact_sha256': evidence_payload.artifact_sha256,
            'target_environment': 'production',
            'policy_epoch': evidence_payload.policy_epoch,
            'source_attestation_id': evidence_payload.source_attestation_id,
            'reason': 'Deploy the reviewed immutable artifact',
            'issued_at': current.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'expires_at': (current + timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        values.update(changes)
        return sign_promotion(PromotionPayload(**values), selected_signer)

    @staticmethod
    def promotion_headers(key='request-00000001', correlation='correlation-0001'):
        return {
            'Idempotency-Key': key,
            'X-Correlation-ID': correlation,
            'Content-Type': 'application/json',
        }

    @staticmethod
    def raw_asgi_post(app, headers: list[tuple[bytes, bytes]], body: bytes):
        async def invoke():
            sent = []
            delivered = False

            async def receive():
                nonlocal delivered
                if delivered:
                    return {'type': 'http.disconnect'}
                delivered = True
                return {'type': 'http.request', 'body': body, 'more_body': False}

            async def send(message):
                sent.append(message)

            await app(
                {
                    'type': 'http',
                    'asgi': {'version': '3.0'},
                    'http_version': '1.1',
                    'method': 'POST',
                    'scheme': 'https',
                    'path': '/promotions',
                    'raw_path': b'/promotions',
                    'query_string': b'',
                    'root_path': '',
                    'headers': headers,
                    'client': ('127.0.0.1', 12345),
                    'server': ('testserver', 443),
                },
                receive,
                send,
            )
            start = next(message for message in sent if message['type'] == 'http.response.start')
            response_body = b''.join(
                message.get('body', b'')
                for message in sent
                if message['type'] == 'http.response.body'
            )
            return start['status'], json.loads(response_body)

        return asyncio.run(invoke())

    def test_promotion_exact_retry_is_retrieval_but_new_key_replay_conflicts(self) -> None:
        envelope = self.promotion_envelope().to_dict()
        first = self.client.post('/promotions', headers=self.promotion_headers(), json=envelope)
        again = self.client.post('/promotions', headers=self.promotion_headers(), json=envelope)
        conflict = self.client.post(
            '/promotions',
            headers=self.promotion_headers(key='request-00000002'),
            json=envelope,
        )
        self.assertEqual((first.status_code, again.status_code, conflict.status_code), (201, 200, 409))
        self.assertFalse(first.json()['idempotent_replay'])
        self.assertTrue(again.json()['idempotent_replay'])
        self.assertEqual(conflict.headers['content-type'], 'application/problem+json')
        self.assertEqual(conflict.json()['code'], 'promotion_replay')
        self.assertEqual(
            [event.event_type for event in self.store.list_promotion_events(first.json()['promotion_id'], limit=10)],
            ['promotion.accepted'],
        )

    def test_promotion_changed_request_under_same_key_and_nonce_reuse_conflict(self) -> None:
        first = self.promotion_envelope()
        accepted = self.client.post('/promotions', headers=self.promotion_headers(), json=first.to_dict())
        changed = self.promotion_envelope()
        key_conflict = self.client.post('/promotions', headers=self.promotion_headers(), json=changed.to_dict())
        nonce_payload = changed.payload.to_dict()
        nonce_payload['promotion_id'] = str(uuid.uuid4())
        nonce_payload['nonce'] = first.payload.nonce
        nonce_reuse = sign_promotion(PromotionPayload(**nonce_payload), self.human)
        replay = self.client.post(
            '/promotions',
            headers=self.promotion_headers(key='request-00000002'),
            json=nonce_reuse.to_dict(),
        )
        self.assertEqual(accepted.status_code, 201)
        self.assertEqual((key_conflict.status_code, key_conflict.json()['code']), (409, 'idempotency_conflict'))
        self.assertEqual((replay.status_code, replay.json()['code']), (409, 'promotion_replay'))
        self.assertEqual(len(self.store._promotions), 1)

    def test_promotion_rejects_oversize_duplicate_json_and_ambiguous_framing(self) -> None:
        envelope = self.promotion_envelope().to_dict()
        raw = json.dumps(envelope, separators=(',', ':'))
        duplicate = raw.replace('"actor":"dmitry"', '"actor":"dmitry","actor":"mallory"')
        duplicate_response = self.client.post(
            '/promotions', headers=self.promotion_headers(), content=duplicate
        )
        oversized = self.client.post(
            '/promotions', headers=self.promotion_headers(), content=b'x' * (16 * 1024 + 1)
        )
        ambiguous = self.client.post(
            '/promotions',
            headers={**self.promotion_headers(), 'Content-Length': str(len(raw)), 'Transfer-Encoding': 'chunked'},
            content=raw,
        )
        inconsistent_length = self.client.post(
            '/promotions',
            headers={**self.promotion_headers(), 'Content-Length': '1'},
            content=raw,
        )
        for response in (duplicate_response, oversized, ambiguous, inconsistent_length):
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.headers['content-type'], 'application/problem+json')
            self.assertEqual(response.json()['code'], 'malformed_envelope')

    def test_promotion_requires_bounded_idempotency_and_correlation_headers(self) -> None:
        envelope = self.promotion_envelope().to_dict()
        for headers in (
            {'X-Correlation-ID': 'correlation-0001'},
            {'Idempotency-Key': 'request-00000001'},
            self.promotion_headers(key='short'),
            self.promotion_headers(correlation='x' * 129),
        ):
            with self.subTest(headers=headers):
                response = self.client.post('/promotions', headers=headers, json=envelope)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()['code'], 'malformed_envelope')

    def test_promotion_rejects_ambiguous_singleton_headers_at_raw_asgi_boundary(self) -> None:
        body = json.dumps(
            self.promotion_envelope().to_dict(), separators=(',', ':')
        ).encode()
        baseline = [
            (b'idempotency-key', b'request-00000001'),
            (b'x-correlation-id', b'correlation-0001'),
            (b'content-type', b'application/json'),
            (b'content-length', str(len(body)).encode()),
        ]
        ambiguous = (
            baseline + [(b'idempotency-key', b'request-00000002')],
            [(b'idempotency-key', b'request-00000001,request-00000002'), *baseline[1:]],
            baseline + [(b'x-correlation-id', b'correlation-0002')],
            [baseline[0], (b'x-correlation-id', b'correlation-0001,correlation-0002'), *baseline[2:]],
            baseline + [(b'content-type', b'text/plain')],
            [*baseline[:2], (b'content-type', b'application/json,text/plain'), baseline[3]],
            baseline + [(b'content-encoding', b'identity'), (b'content-encoding', b'identity')],
            baseline + [(b'content-encoding', b'identity,gzip')],
            baseline + [(b'content-encoding', b'gzip')],
        )
        for headers in ambiguous:
            with self.subTest(headers=headers):
                status, problem = self.raw_asgi_post(self.client.app, headers, body)
                self.assertEqual((status, problem.get('code')), (400, 'malformed_envelope'))
        self.assertEqual(len(self.store._promotions), 0)

    def test_promotion_resolves_policy_after_start_and_fails_closed_on_unavailable_policy(self) -> None:
        policy_path = self.common.policy_path
        policy_path.write_text(json.dumps(policy_data()), encoding='utf-8')
        client = TestClient(
            create_app(
                self.settings,
                store=self.store,
                trust_store=self.trust_store,
            )
        )
        old_epoch = self.policy.digest
        rotated_data = policy_data()
        rotated_data['max_attempts'] += 1
        rotated_policy = Policy.from_dict(rotated_data)
        self.assertNotEqual(rotated_policy.digest, old_epoch)

        old_envelope = self.promotion_envelope().to_dict()
        policy_path.write_text(json.dumps(rotated_data), encoding='utf-8')
        self.store.activate_policy(rotated_policy.digest)
        rotated = client.post('/promotions', headers=self.promotion_headers(), json=old_envelope)
        self.assertEqual((rotated.status_code, rotated.json().get('code')), (403, 'policy_mismatch'))

        policy_path.unlink()
        removed = client.post(
            '/promotions',
            headers=self.promotion_headers(key='request-00000002'),
            json=self.promotion_envelope().to_dict(),
        )
        self.assertEqual((removed.status_code, removed.json().get('code')), (503, 'authorization_unavailable'))

        policy_path.write_text('{corrupt', encoding='utf-8')
        corrupt = client.post(
            '/promotions',
            headers=self.promotion_headers(key='request-00000003'),
            json=self.promotion_envelope().to_dict(),
        )
        self.assertEqual((corrupt.status_code, corrupt.json().get('code')), (503, 'authorization_unavailable'))
        self.assertEqual(len(self.store._promotions), 0)

    def test_promotion_detects_policy_change_between_verification_and_acceptance(self) -> None:
        policy_path = self.common.policy_path
        policy_path.write_text(json.dumps(policy_data()), encoding='utf-8')
        rotated_data = policy_data()
        rotated_data['max_attempts'] += 1
        rotating_store = PolicyRotatingStore(
            lambda: policy_path.write_text(json.dumps(rotated_data), encoding='utf-8')
        )
        rotating_store.activate_policy(self.policy.digest)
        original_store = self.store
        self.store = rotating_store
        try:
            envelope = self.promotion_envelope().to_dict()
        finally:
            self.store = original_store
        client = TestClient(
            create_app(
                self.settings,
                store=rotating_store,
                trust_store=self.trust_store,
            )
        )
        response = client.post('/promotions', headers=self.promotion_headers(), json=envelope)
        self.assertEqual((response.status_code, response.json().get('code')), (503, 'authorization_unavailable'))
        self.assertEqual(len(rotating_store._promotions), 0)

    def test_readiness_fails_when_file_and_database_policy_epochs_differ(self) -> None:
        rotated_data = policy_data()
        rotated_data['max_attempts'] += 1
        self.common.policy_path.write_text(json.dumps(rotated_data), encoding='utf-8')
        response = self.client.get('/health/ready')
        self.assertEqual(response.status_code, 503)

        unavailable_store = MemoryStore()
        unavailable = TestClient(
            create_app(
                self.settings,
                store=unavailable_store,
                trust_store=self.trust_store,
            )
        )
        self.assertEqual(unavailable.get('/health/ready').status_code, 503)

    def test_policy_promotion_ttl_cannot_be_widened_by_runtime_settings(self) -> None:
        policy_source = policy_data()
        policy_source['promotion'] = {
            'environments': ['production'],
            'max_ttl_seconds': 900,
        }
        policy = Policy.from_dict(policy_source)
        self.common.policy_path.write_text(json.dumps(policy_source), encoding='utf-8')
        store = MemoryStore()
        store.activate_policy(policy.digest)
        widened = replace(self.settings, promotion_max_ttl_seconds=3600)
        original_policy, original_store = self.policy, self.store
        self.policy, self.store = policy, store
        try:
            envelope = self.promotion_envelope(
                expires_at=(
                    utc_now().astimezone(timezone.utc).replace(microsecond=0)
                    + timedelta(minutes=30)
                ).strftime('%Y-%m-%dT%H:%M:%SZ')
            )
        finally:
            self.policy, self.store = original_policy, original_store
        client = TestClient(
            create_app(widened, store=store, policy=policy, trust_store=self.trust_store)
        )

        self.assertEqual(client.get('/health/ready').status_code, 503)
        response = client.post(
            '/promotions', headers=self.promotion_headers(), json=envelope.to_dict()
        )
        self.assertEqual(
            (response.status_code, response.json()['code']),
            (503, 'authorization_unavailable'),
        )
        self.assertEqual(len(store._promotions), 0)

    def test_runtime_environment_may_narrow_but_never_widen_policy(self) -> None:
        policy_source = policy_data()
        policy_source['promotion'] = {
            'environments': ['production', 'staging'],
            'max_ttl_seconds': 900,
        }
        policy = Policy.from_dict(policy_source)
        self.common.policy_path.write_text(json.dumps(policy_source), encoding='utf-8')
        store = MemoryStore()
        store.activate_policy(policy.digest)
        original_policy, original_store = self.policy, self.store
        self.policy, self.store = policy, store
        try:
            staging = self.promotion_envelope(target_environment='staging')
        finally:
            self.policy, self.store = original_policy, original_store
        narrowed = TestClient(
            create_app(self.settings, store=store, policy=policy, trust_store=self.trust_store)
        )
        self.assertEqual(narrowed.get('/health/ready').status_code, 200)
        denied = narrowed.post(
            '/promotions', headers=self.promotion_headers(), json=staging.to_dict()
        )
        self.assertEqual(
            (denied.status_code, denied.json()['code']), (403, 'target_forbidden')
        )

        widened_settings = replace(self.settings, promotion_environment='development')
        widened = TestClient(
            create_app(
                widened_settings,
                store=store,
                policy=policy,
                trust_store=self.trust_store,
            )
        )
        self.assertEqual(widened.get('/health/ready').status_code, 503)
        rejected = widened.post(
            '/promotions',
            headers=self.promotion_headers(key='request-00000002'),
            json=staging.to_dict(),
        )
        self.assertEqual(
            (rejected.status_code, rejected.json()['code']),
            (503, 'authorization_unavailable'),
        )
        self.assertEqual(len(store._promotions), 0)

    def test_store_entry_policy_rotation_cannot_accept_stale_file_epoch(self) -> None:
        rotating_store = StoreEntryPolicyRotatingStore(digest('f'))
        rotating_store._active_policy_epoch = self.policy.digest
        original_store = self.store
        self.store = rotating_store
        try:
            envelope = self.promotion_envelope().to_dict()
        finally:
            self.store = original_store
        client = TestClient(
            create_app(
                self.settings,
                store=rotating_store,
                policy=self.policy,
                trust_store=self.trust_store,
            )
        )
        response = client.post('/promotions', headers=self.promotion_headers(), json=envelope)
        self.assertTrue(rotating_store.rotation_completed)
        self.assertEqual((response.status_code, response.json().get('code')), (403, 'provenance_mismatch'))
        self.assertEqual(len(rotating_store._promotion_idempotency), 0)
        self.assertEqual(len(rotating_store._promotions), 0)
        self.assertFalse(any(event.event_type == 'promotion.accepted' for event in rotating_store._promotion_events))

    def test_promotion_signature_time_and_server_owned_mismatches_have_frozen_codes(self) -> None:
        valid = self.promotion_envelope()
        tampered = valid.to_dict()
        tampered['signature'] = ('A' if tampered['signature'][0] != 'A' else 'Q') + tampered['signature'][1:]
        signature = self.client.post('/promotions', headers=self.promotion_headers(), json=tampered)

        expired = self.promotion_envelope(
            issued_at='2026-08-30T00:00:00Z',
            expires_at='2026-08-30T00:01:00Z',
        )
        stale = self.client.post('/promotions', headers=self.promotion_headers(key='request-00000002'), json=expired.to_dict())

        wrong_environment = self.promotion_envelope(target_environment='staging')
        forbidden = self.client.post('/promotions', headers=self.promotion_headers(key='request-00000003'), json=wrong_environment.to_dict())

        wrong_repository = self.promotion_envelope(repository='attacker/repository')
        repository = self.client.post('/promotions', headers=self.promotion_headers(key='request-00000008'), json=wrong_repository.to_dict())

        wrong_policy = self.promotion_envelope(policy_epoch=digest('f'))
        policy = self.client.post('/promotions', headers=self.promotion_headers(key='request-00000004'), json=wrong_policy.to_dict())

        missing_evidence = self.promotion_envelope(source_attestation_id=str(uuid.uuid4()))
        provenance = self.client.post('/promotions', headers=self.promotion_headers(key='request-00000005'), json=missing_evidence.to_dict())

        wrong_artifact = self.promotion_envelope(artifact_sha256=digest('e'))
        artifact = self.client.post('/promotions', headers=self.promotion_headers(key='request-00000009'), json=wrong_artifact.to_dict())

        self.assertEqual((signature.status_code, stale.status_code, forbidden.status_code, repository.status_code, policy.status_code, provenance.status_code, artifact.status_code), (401, 422, 403, 403, 403, 403, 403))
        self.assertEqual(
            [signature.json()['code'], stale.json()['code'], forbidden.json()['code'], repository.json()['code'], policy.json()['code'], provenance.json()['code'], artifact.json()['code']],
            ['signature_invalid', 'envelope_not_current', 'target_forbidden', 'target_forbidden', 'policy_mismatch', 'provenance_mismatch', 'provenance_mismatch'],
        )
        self.assertEqual(len(self.store._promotions), 0)

    def test_unknown_and_wrong_scope_promotion_keys_share_signature_invalid_response(self) -> None:
        unknown = self.promotion_envelope(signer=Signer.generate())
        unknown_response = self.client.post(
            '/promotions', headers=self.promotion_headers(key='request-00000010'), json=unknown.to_dict()
        )
        wrong_scope_store = TrustStore.from_dict(
            {
                'schema_version': 1,
                'keys': [{
                    'key_id': self.human.key_id,
                    'actor': 'dmitry',
                    'scopes': ['governance'],
                    'public_key_pem': self.human.public_key_pem().decode(),
                }],
            }
        )
        wrong_scope_client = TestClient(
            create_app(self.settings, store=self.store, policy=self.policy, trust_store=wrong_scope_store)
        )
        scoped = self.promotion_envelope()
        scoped_response = wrong_scope_client.post(
            '/promotions', headers=self.promotion_headers(key='request-00000011'), json=scoped.to_dict()
        )
        self.assertEqual(
            [(unknown_response.status_code, unknown_response.json()['code']), (scoped_response.status_code, scoped_response.json()['code'])],
            [(401, 'signature_invalid'), (401, 'signature_invalid')],
        )

    def test_unsupported_contract_and_content_type_have_constant_problem_shape(self) -> None:
        envelope = self.promotion_envelope().to_dict()
        envelope['algorithm'] = 'RSA'
        unsupported = self.client.post('/promotions', headers=self.promotion_headers(), json=envelope)
        wrong_type = self.client.post(
            '/promotions',
            headers={**self.promotion_headers(key='request-00000012'), 'Content-Type': 'text/plain'},
            content='{}',
        )
        self.assertEqual((unsupported.status_code, unsupported.json()['code']), (400, 'unsupported_contract'))
        self.assertEqual((wrong_type.status_code, wrong_type.json()['code']), (400, 'malformed_envelope'))
        for response in (unsupported, wrong_type):
            self.assertEqual(set(response.json()), {'type', 'title', 'status', 'code', 'correlation_id'})

    def test_promotion_settings_reject_unbounded_or_noncanonical_values(self) -> None:
        for changes in (
            {'promotion_environment': 'Production'},
            {'promotion_max_ttl_seconds': 3601},
            {'promotion_rate_limit_per_minute': 0},
            {'deployer_token': 'short'},
            {'promotion_consume_rate_limit_per_minute': 0},
            {'promotion_manifest_path': self.common.policy_path},
            {
                'promotion_manifest_path': self.common.policy_path,
                'promotion_artifact_path': self.common.policy_path,
            },
            {
                'promotion_manifest_path': self.common.policy_path,
                'promotion_artifact_path': self.common.policy_path,
                'promotion_manifest_sha256': 'A' * 64,
            },
        ):
            with self.subTest(changes=changes), self.assertRaises(SettingsError):
                replace(self.settings, **changes)

    def test_promotion_kill_switch_and_bounded_rate_limit_fail_closed(self) -> None:
        envelope = self.promotion_envelope().to_dict()
        self.common.kill_switch_path.write_text('stop')
        stopped = self.client.post('/promotions', headers=self.promotion_headers(), json=envelope)
        self.assertEqual((stopped.status_code, stopped.json()['code']), (503, 'promotion_disabled'))
        self.common.kill_switch_path.unlink()

        limited_settings = replace(self.settings, promotion_rate_limit_per_minute=1)
        limited = TestClient(create_app(limited_settings, store=self.store, policy=self.policy, trust_store=self.trust_store))
        first = limited.post('/promotions', headers=self.promotion_headers(key='request-00000006'), json=envelope)
        second = limited.post('/promotions', headers=self.promotion_headers(key='request-00000007'), json=envelope)
        self.assertEqual(first.status_code, 201)
        self.assertEqual((second.status_code, second.json()['code']), (429, 'rate_limited'))

    def test_malformed_promotion_admission_is_bounded_before_durable_audit(self) -> None:
        limited_settings = replace(self.settings, promotion_rate_limit_per_minute=1)
        limited_store = MemoryStore()
        limited_store.activate_policy(self.policy.digest)
        limited = TestClient(create_app(
            limited_settings, store=limited_store, policy=self.policy,
            trust_store=self.trust_store,
        ))
        headers = self.promotion_headers(key='request-00000013')
        first = limited.post('/promotions', headers=headers, content=b'{')
        second = limited.post(
            '/promotions',
            headers=self.promotion_headers(key='request-00000014'),
            content=b'{',
        )
        self.assertEqual((first.status_code, first.json()['code']), (400, 'malformed_envelope'))
        self.assertEqual((second.status_code, second.json()['code']), (429, 'rate_limited'))
        rejected = [
            event for event in limited_store._promotion_events
            if event.event_type == 'promotion.rejected'
        ]
        self.assertEqual(len(rejected), 1)

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

    def test_merged_webhook_uses_active_store_as_durable_recorder_by_default(self) -> None:
        client = TestClient(
            create_app(
                self.settings,
                store=self.store,
                policy=self.policy,
                trust_store=self.trust_store,
                protected_ref='refs/heads/main',
            )
        )
        body = self.merged_webhook_body()
        response = client.post(
            '/webhooks/github', content=body, headers=self.headers(body, delivery_id='merge-1')
        )
        self.assertEqual(response.status_code, 200)
        claimed = self.store.claim_merge_fact('worker-1', 60, now=utc_now())
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(claimed.fact.merge_fact_id, response.json()['merge_fact_id'])

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
        response = self.client.post(
            '/webhooks/github', content=closed, headers=self.headers(closed, delivery_id='delivery-2')
        )
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
