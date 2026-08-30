from __future__ import annotations

import base64
import asyncio
import hashlib
import json
import tempfile
import unittest
import uuid
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from _support import digest, now, policy_data, sha
from adaptive_trust_ci.api import create_app
from adaptive_trust_ci.models import PromotionPayload, ProtectedBranchAttestationPayload, utc_now
from adaptive_trust_ci.policy import Policy
from adaptive_trust_ci.provenance import MergedPullRequestFact
from adaptive_trust_ci.settings import ApiSettings, CommonSettings
from adaptive_trust_ci.signing import Signer, TrustStore, sign_promotion, sign_protected_branch_attestation
from adaptive_trust_ci.store import MemoryStore


class ConsumeFailingStore(MemoryStore):
    def consume_promotion(self, *args, **kwargs):
        raise ConnectionError('database lost')


class PromotionEndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.common = CommonSettings(
            database_url='postgresql://unused',
            policy_path=base / 'policy.json',
            public_base_url='https://ci.example.com',
            kill_switch_path=base / 'STOP',
        )
        self.policy_source = policy_data()
        self.policy = Policy.from_dict(self.policy_source)
        self.common.policy_path.write_text(json.dumps(self.policy_source), encoding='utf-8')
        self.artifact = base / 'artifact.zip'
        self.artifact.write_bytes(b'exact deployable bytes')
        self.artifact_digest = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        policy_copy = base / 'bundle-policy.json'
        policy_copy.write_text(json.dumps(self.policy_source, sort_keys=True), encoding='utf-8')
        artifacts = base / 'artifacts.sha256'
        artifacts.write_text(
            f'{self.artifact_digest}  {self.artifact.name}\n', encoding='utf-8'
        )
        self.manifest = base / 'supply-chain.manifest.json'
        self.manifest.write_text(
            json.dumps(
                {
                    'schema_version': 1,
                    'created_at': '2026-08-30T00:00:00+00:00',
                    'git_head': sha('a'),
                    'policy_file': policy_copy.name,
                    'policy_sha256': hashlib.sha256(policy_copy.read_bytes()).hexdigest(),
                    'artifacts_file': artifacts.name,
                    'artifacts_sha256': hashlib.sha256(artifacts.read_bytes()).hexdigest(),
                    'images': {
                        'api': 'registry.example/api@sha256:' + digest('1'),
                        'worker': 'registry.example/worker@sha256:' + digest('2'),
                        'runner': self.policy.sandbox.image,
                    },
                    'sbom_directory': 'sbom',
                    'scan_directory': 'scan',
                },
                sort_keys=True,
                separators=(',', ':'),
            )
            + '\n',
            encoding='utf-8',
        )
        self.settings = ApiSettings(
            common=self.common,
            webhook_secret='wh-secret',
            trust_store_path=base / 'trust-store.json',
            read_token='read-token',
            deployer_token='dedicated-' + 'deployer-token',
            promotion_manifest_path=self.manifest,
            promotion_artifact_path=self.artifact,
            promotion_manifest_sha256=hashlib.sha256(self.manifest.read_bytes()).hexdigest(),
            promotion_consume_rate_limit_per_minute=10,
        )
        self.human = Signer.generate()
        self.trust_store = TrustStore.from_dict(
            {
                'schema_version': 1,
                'keys': [
                    {
                        'key_id': self.human.key_id,
                        'actor': 'dmitry',
                        'scopes': ['promotion:production'],
                        'public_key_pem': self.human.public_key_pem().decode(),
                    }
                ],
            }
        )
        self.store = MemoryStore()
        self.store.activate_policy(self.policy.digest)
        self.envelope = self._envelope()
        self.client = TestClient(
            create_app(
                self.settings,
                store=self.store,
                policy=self.policy,
                trust_store=self.trust_store,
            )
        )
        accepted = self.client.post(
            '/promotions',
            headers={
                'Idempotency-Key': 'request-e2e-000001',
                'X-Correlation-ID': 'correlation-accept',
            },
            json=self.envelope.to_dict(),
        )
        self.assertEqual(accepted.status_code, 201, accepted.text)
        payload = self.envelope.payload
        self.consume_body = {
            'repository': payload.repository,
            'merged_commit_sha': payload.merged_commit_sha,
            'artifact_sha256': payload.artifact_sha256,
            'target_environment': payload.target_environment,
            'policy_epoch': payload.policy_epoch,
            'source_attestation_id': payload.source_attestation_id,
            'operation_id': str(uuid.uuid4()),
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _envelope(self):
        current = utc_now().replace(microsecond=0)
        fact = MergedPullRequestFact.create(
            delivery_id='delivery-e2e-1',
            payload_sha256=digest('d'),
            repository_id=123,
            repository='dimkox/adaptive-grok-build-pro',
            installation_id=456,
            pr_number=701,
            head_sha=sha('e'),
            base_sha=sha('f'),
            protected_ref='refs/heads/main',
            merged_commit_sha=sha('a'),
            merged_at='2026-08-23T11:59:00Z',
            received_at=now(),
        )
        attestation = ProtectedBranchAttestationPayload(
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
            artifact_sha256=self.artifact_digest,
            result='passed',
            issued_at=current.strftime('%Y-%m-%dT%H:%M:%SZ'),
            key_id=self.human.key_id,
        )
        self.store.record_merge_fact(fact)
        self.store.record_protected_branch_evidence(
            sign_protected_branch_attestation(attestation, self.human)
        )
        return sign_promotion(
            PromotionPayload(
                schema_version=1,
                promotion_id=str(uuid.uuid4()),
                nonce=base64.urlsafe_b64encode(b'z' * 32).decode().rstrip('='),
                actor='dmitry',
                key_id=self.human.key_id,
                repository=fact.repository,
                merged_commit_sha=fact.merged_commit_sha,
                artifact_sha256=self.artifact_digest,
                target_environment='production',
                policy_epoch=self.policy.digest,
                source_attestation_id=attestation.source_attestation_id,
                reason='Deploy exact artifact',
                issued_at=(current - timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                expires_at=(current + timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            ),
            self.human,
        )

    @property
    def consume_headers(self) -> dict[str, str]:
        return {
            'Authorization': 'Bearer dedicated-deployer-token',
            'X-Correlation-ID': 'correlation-consume',
        }

    @staticmethod
    def raw_consume(
        app, path: str, headers: list[tuple[bytes, bytes]], body: bytes
    ) -> tuple[int, dict]:
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
                    'path': path,
                    'raw_path': path.encode(),
                    'query_string': b'',
                    'root_path': '',
                    'headers': headers,
                    'client': ('127.0.0.1', 12345),
                    'server': ('testserver', 443),
                },
                receive,
                send,
            )
            start = next(item for item in sent if item['type'] == 'http.response.start')
            raw = b''.join(
                item.get('body', b'')
                for item in sent
                if item['type'] == 'http.response.body'
            )
            return start['status'], json.loads(raw)

        return asyncio.run(invoke())

    def test_authenticated_consume_precedes_the_only_explicit_external_effect(self) -> None:
        response = self.client.post(
            f'/promotions/{self.envelope.payload.promotion_id}/consume',
            headers=self.consume_headers,
            json=self.consume_body,
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['operation_id'], self.consume_body['operation_id'])

        retry = self.client.post(
            f'/promotions/{self.envelope.payload.promotion_id}/consume',
            headers=self.consume_headers,
            json=self.consume_body,
        )
        self.assertEqual((retry.status_code, retry.json()['code']), (409, 'promotion_consumed'))
        self.assertEqual(len(self.store._promotion_consumptions), 1)
        self.assertEqual(
            [event.event_type for event in self.store.list_promotion_events(
                self.envelope.payload.promotion_id, limit=10
            )],
            ['promotion.accepted', 'promotion.consumed'],
        )

    def test_deployer_records_one_terminal_outcome_after_exact_consumption(self) -> None:
        promotion_id = self.envelope.payload.promotion_id
        self.client.post(
            f'/promotions/{promotion_id}/consume', headers=self.consume_headers,
            json=self.consume_body,
        )
        path = f'/promotions/{promotion_id}/consume/{self.consume_body["operation_id"]}/terminal'
        completed = self.client.post(
            path, headers=self.consume_headers,
            json={
                'event_type': 'deployment.completed', 'reason_code': 'completed',
                'details': {'deployment_id': 'local-drill-1'},
            },
        )
        self.assertEqual(completed.status_code, 201)
        self.assertEqual(completed.json()['event_type'], 'deployment.completed')
        duplicate = self.client.post(
            path, headers=self.consume_headers,
            json={'event_type': 'deployment.failed', 'reason_code': 'failed', 'details': {}},
        )
        self.assertEqual((duplicate.status_code, duplicate.json()['code']), (409, 'terminal_conflict'))

    def test_lost_response_reconciles_only_the_exact_committed_operation(self) -> None:
        path = f'/promotions/{self.envelope.payload.promotion_id}/consume'
        committed = self.client.post(
            path, headers=self.consume_headers, json=self.consume_body
        )
        self.assertEqual(committed.status_code, 200, committed.text)
        lookup = self.client.get(
            f'{path}/{self.consume_body["operation_id"]}',
            headers={
                'Authorization': 'Bearer dedicated-deployer-token',
                'X-Correlation-ID': 'correlation-reconcile',
            },
        )
        self.assertEqual(lookup.status_code, 200, lookup.text)
        lookup_body = lookup.json()
        self.assertTrue(lookup_body['reconciled'])
        self.assertEqual(lookup_body['operation_id'], self.consume_body['operation_id'])
        contract = json.loads(
            (
                Path(__file__).resolve().parents[2]
                / 'engineering/contracts/openapi/trust-ci-promotions-v1.yaml'
            ).read_text(encoding='utf-8')
        )
        consumption_schema = contract['components']['schemas'][
            'PromotionConsumptionRepresentation'
        ]
        self.assertTrue(set(consumption_schema['required']) <= set(lookup_body))
        self.assertTrue(
            set(lookup_body) <= set(consumption_schema['properties']),
            'runtime reconciliation response must have no schema-unknown properties',
        )
        acceptance_schema = contract['components']['schemas'][
            'PromotionRepresentation'
        ]
        self.assertNotIn('reconciled', acceptance_schema['properties'])
        missing_operation = str(uuid.uuid4())
        generic_conflict = self.client.post(
            path,
            headers=self.consume_headers,
            json={**self.consume_body, 'operation_id': missing_operation},
        )
        self.assertEqual(
            (generic_conflict.status_code, generic_conflict.json()['code']),
            (409, 'promotion_consumed'),
        )
        self.assertNotIn('operation_id', generic_conflict.json())
        missing = self.client.get(
            f'{path}/{missing_operation}',
            headers={
                'Authorization': 'Bearer dedicated-deployer-token',
                'X-Correlation-ID': 'correlation-reconcile-missing',
            },
        )
        self.assertEqual(
            (missing.status_code, missing.json()['code']),
            (404, 'consumption_not_found'),
        )
        self.assertNotIn('operation_id', missing.json())
        self.assertEqual(len(self.store._promotion_consumptions), 1)
        self.assertEqual(
            [event.event_type for event in self.store.list_promotion_events(
                self.envelope.payload.promotion_id, limit=10
            )],
            ['promotion.accepted', 'promotion.consumed'],
        )

    def test_auth_mismatch_kill_switch_and_database_loss_create_zero_effects(self) -> None:
        effects: list[str] = []
        for authorization in (None, 'Bearer wrong-token'):
            headers = {'X-Correlation-ID': 'correlation-auth'}
            if authorization is not None:
                headers['Authorization'] = authorization
            response = self.client.post(
                f'/promotions/{self.envelope.payload.promotion_id}/consume',
                headers=headers,
                json=self.consume_body,
            )
            self.assertEqual((response.status_code, response.json()['code']), (401, 'deployer_unauthorized'))
        self.common.kill_switch_path.write_text('stop', encoding='utf-8')
        stopped = self.client.post(
            f'/promotions/{self.envelope.payload.promotion_id}/consume',
            headers=self.consume_headers,
            json=self.consume_body,
        )
        self.assertEqual((stopped.status_code, stopped.json()['code']), (503, 'promotion_disabled'))
        self.common.kill_switch_path.unlink()
        failed_client = TestClient(
            create_app(
                self.settings,
                store=ConsumeFailingStore(),
                policy=self.policy,
                trust_store=self.trust_store,
            )
        )
        unavailable = failed_client.post(
            f'/promotions/{self.envelope.payload.promotion_id}/consume',
            headers=self.consume_headers,
            json=self.consume_body,
        )
        self.assertEqual(
            (unavailable.status_code, unavailable.json()['code']),
            (503, 'consume_unavailable'),
        )
        self.assertEqual(effects, [])

    def test_strict_headers_body_and_exact_tuple_are_required(self) -> None:
        path = f'/promotions/{self.envelope.payload.promotion_id}/consume'
        duplicate_auth = self.client.post(
            path,
            headers=[
                ('Authorization', 'Bearer dedicated-deployer-token'),
                ('Authorization', 'Bearer dedicated-deployer-token'),
                ('X-Correlation-ID', 'correlation-duplicate'),
                ('Content-Type', 'application/json'),
            ],
            content=json.dumps(self.consume_body),
        )
        self.assertEqual((duplicate_auth.status_code, duplicate_auth.json()['code']), (400, 'consume_malformed'))
        duplicate_body = json.dumps(self.consume_body)[:-1] + ',"operation_id":"' + str(uuid.uuid4()) + '"}'
        duplicate_json = self.client.post(
            path,
            headers={**self.consume_headers, 'Content-Type': 'application/json'},
            content=duplicate_body,
        )
        self.assertEqual((duplicate_json.status_code, duplicate_json.json()['code']), (400, 'consume_malformed'))
        mismatch = self.client.post(
            path,
            headers=self.consume_headers,
            json={**self.consume_body, 'artifact_sha256': digest('f')},
        )
        self.assertEqual((mismatch.status_code, mismatch.json()['code']), (403, 'consume_forbidden'))

    def test_raw_asgi_consume_framing_and_schema_matrix(self) -> None:
        path = f'/promotions/{self.envelope.payload.promotion_id}/consume'
        client = TestClient(create_app(
            replace(self.settings, promotion_consume_rate_limit_per_minute=100),
            store=self.store,
            policy=self.policy,
            trust_store=self.trust_store,
        ))
        valid = json.dumps(self.consume_body, separators=(',', ':')).encode()
        baseline = [
            (b'authorization', b'Bearer dedicated-deployer-token'),
            (b'x-correlation-id', b'correlation-raw'),
            (b'content-type', b'application/json'),
            (b'content-length', str(len(valid)).encode()),
        ]
        edge = valid + (b' ' * (4096 - len(valid)))
        edge_headers = [*baseline[:-1], (b'content-length', b'4096')]
        status, _ = self.raw_consume(client.app, path, edge_headers, edge)
        self.assertEqual(status, 200)
        invalid_cases = [
            ([*baseline[:-1], (b'content-length', b'4097')], edge + b' '),
            ([*baseline[:-1], (b'content-length', b'0')], b''),
            ([*baseline[:-1], (b'content-length', str(len(valid) + 1).encode())], valid),
            ([*baseline, (b'transfer-encoding', b'chunked')], valid),
            ([*baseline, (b'content-length', str(len(valid)).encode())], valid),
            ([*baseline[:-1], (b'transfer-encoding', b'chunked'), (b'transfer-encoding', b'chunked')], valid),
            ([*baseline[:-1], (b'transfer-encoding', b'gzip')], valid),
            ([*baseline, (b'authorization', b'Bearer dedicated-deployer-token')], valid),
            ([(b'authorization', b'Bearer dedicated-deployer-token,Bearer dedicated-deployer-token'), *baseline[1:]], valid),
            ([*baseline, (b'x-correlation-id', b'other')], valid),
            ([baseline[0], (b'x-correlation-id', b'a,b'), *baseline[2:]], valid),
            ([*baseline, (b'content-type', b'application/json')], valid),
            ([*baseline[:2], (b'content-type', b'application/json,text/plain'), baseline[3]], valid),
            ([*baseline, (b'content-encoding', b'gzip')], valid),
            ([*baseline, (b'content-encoding', b'identity'), (b'content-encoding', b'identity')], valid),
            ([*baseline, (b'content-encoding', b'identity,gzip')], valid),
            ([baseline[0], baseline[1], baseline[3]], valid),
            (baseline, b'{}'),
            (baseline, b'[]'),
            (baseline, json.dumps({**self.consume_body, 'unknown': True}).encode()),
            (baseline, json.dumps({key: value for key, value in self.consume_body.items() if key != 'repository'}).encode()),
            (baseline, json.dumps({**self.consume_body, 'operation_id': 'not-a-uuid'}).encode()),
            (baseline, json.dumps({**self.consume_body, 'repository': '../escape'}).encode()),
            (baseline, json.dumps({**self.consume_body, 'merged_commit_sha': 'a' * 39}).encode()),
            (baseline, json.dumps({**self.consume_body, 'artifact_sha256': 'A' * 64}).encode()),
            (baseline, json.dumps({**self.consume_body, 'target_environment': 'Production'}).encode()),
            (baseline, json.dumps({**self.consume_body, 'policy_epoch': 'f' * 63}).encode()),
            (baseline, json.dumps({**self.consume_body, 'source_attestation_id': 'not-a-uuid'}).encode()),
        ]
        for headers, body in invalid_cases:
            adjusted = [
                (name, str(len(body)).encode()) if name == b'content-length' else (name, value)
                for name, value in headers
            ]
            # Preserve intentionally inconsistent and oversized length probes.
            if headers is invalid_cases[0][0] or headers is invalid_cases[2][0]:
                adjusted = headers
            with self.subTest(headers=headers, body=body[:80]):
                status, problem = self.raw_consume(client.app, path, adjusted, body)
                self.assertEqual((status, problem['code']), (400, 'consume_malformed'))
        self.assertEqual(len(self.store._promotion_consumptions), 1)
        self.assertEqual(
            [event.event_type for event in self.store.list_promotion_events(
                self.envelope.payload.promotion_id, limit=10
            )],
            ['promotion.accepted', 'promotion.consumed'],
        )
        invalid_path_status, invalid_path_problem = self.raw_consume(
            client.app,
            '/promotions/00000000-0000-7000-8000-000000000000/consume',
            baseline,
            valid,
        )
        self.assertEqual(
            (invalid_path_status, invalid_path_problem['code']),
            (400, 'consume_malformed'),
        )

    def test_consume_rate_limit_is_bounded(self) -> None:
        limited = replace(self.settings, promotion_consume_rate_limit_per_minute=1)
        client = TestClient(
            create_app(
                limited,
                store=self.store,
                policy=self.policy,
                trust_store=self.trust_store,
            )
        )
        first = client.post(
            f'/promotions/{self.envelope.payload.promotion_id}/consume',
            headers=self.consume_headers,
            json={**self.consume_body, 'artifact_sha256': digest('f')},
        )
        second = client.post(
            f'/promotions/{self.envelope.payload.promotion_id}/consume',
            headers=self.consume_headers,
            json=self.consume_body,
        )
        self.assertEqual(first.status_code, 403)
        self.assertEqual((second.status_code, second.json()['code']), (429, 'consume_rate_limited'))

    def test_consume_rejects_uuid_versions_outside_one_through_five(self) -> None:
        invalid_ids = (
            '00000000-0000-0000-0000-000000000000',
            '00000000-0000-6000-8000-000000000000',
            '00000000-0000-7000-8000-000000000000',
            '00000000-0000-8000-8000-000000000000',
        )
        accepted_events = len(self.store.list_promotion_events(
            self.envelope.payload.promotion_id, limit=10
        ))
        for invalid in invalid_ids:
            response = self.client.post(
                f'/promotions/{self.envelope.payload.promotion_id}/consume',
                headers=self.consume_headers,
                json={**self.consume_body, 'operation_id': invalid},
            )
            self.assertEqual(
                (response.status_code, response.json()['code']),
                (400, 'consume_malformed'),
            )
        self.assertEqual(len(self.store._promotion_consumptions), 0)
        self.assertEqual(
            len(self.store.list_promotion_events(self.envelope.payload.promotion_id, limit=10)),
            accepted_events,
        )

    def test_openapi_freezes_internal_consume_auth_body_and_errors(self) -> None:
        contract = json.loads(
            (
                Path(__file__).resolve().parents[2]
                / 'engineering/contracts/openapi/trust-ci-promotions-v1.yaml'
            ).read_text(encoding='utf-8')
        )
        operation = contract['paths']['/promotions/{promotion_id}/consume']['post']
        self.assertEqual(operation['x-max-body-bytes'], 4096)
        self.assertEqual(operation['security'], [{'deployerBearer': []}])
        required = operation['requestBody']['content']['application/json']['schema']['required']
        self.assertEqual(
            set(required),
            {
                'repository',
                'merged_commit_sha',
                'artifact_sha256',
                'target_environment',
                'policy_epoch',
                'source_attestation_id',
                'operation_id',
            },
        )
        codes = contract['components']['schemas']['Problem']['properties']['code']['enum']
        for code in (
            'consume_malformed',
            'deployer_unauthorized',
            'consume_forbidden',
            'promotion_consumed',
            'consume_rate_limited',
            'consume_unavailable',
        ):
            self.assertIn(code, codes)
        reconciliation = contract['paths'][
            '/promotions/{promotion_id}/consume/{operation_id}'
        ]['get']
        self.assertEqual(reconciliation['security'], [{'deployerBearer': []}])
        self.assertIn('404', reconciliation['responses'])
        self.assertIn('consumption_not_found', codes)


if __name__ == '__main__':
    unittest.main()
