from __future__ import annotations

import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import test_api
from adaptive_trust_ci.api import create_app
from adaptive_trust_ci.store import MemoryStore


class FailingAuditStore(MemoryStore):
    def record_promotion_rejection(self, event):
        raise RuntimeError('audit database unavailable')


class OutageStore(MemoryStore):
    def ping(self) -> None:
        raise RuntimeError('database unavailable')


class PromotionObservabilityTests(test_api.ApiTests):
    def test_frozen_openapi_declares_runtime_route_limits_and_problem_contract(self) -> None:
        root = Path(__file__).resolve().parents[2]
        contract = json.loads(
            (root / 'engineering/contracts/openapi/trust-ci-promotions-v1.yaml').read_text()
        )
        operation = contract['paths']['/promotions']['post']
        self.assertEqual(contract['openapi'], '3.1.0')
        self.assertEqual(operation['x-max-body-bytes'], 16384)
        self.assertEqual(
            [parameter['name'] for parameter in operation['parameters']],
            ['Idempotency-Key', 'X-Correlation-ID'],
        )
        self.assertEqual(
            set(contract['components']['schemas']['Problem']['properties']['code']['enum']),
            {
                'malformed_envelope', 'unsupported_contract', 'signature_invalid',
                'target_forbidden', 'policy_mismatch', 'provenance_mismatch',
                'idempotency_conflict', 'promotion_replay', 'envelope_not_current',
                'rate_limited', 'authorization_unavailable', 'promotion_disabled',
                'consume_malformed', 'deployer_unauthorized', 'consume_forbidden',
                'promotion_consumed', 'consume_rate_limited', 'consume_unavailable',
                'consumption_not_found',
                'terminal_malformed', 'terminal_conflict',
            },
        )

    def test_rejected_audit_is_bounded_typed_and_excludes_sensitive_request_data(self) -> None:
        envelope = self.promotion_envelope().to_dict()
        envelope['signature'] = ('A' if envelope['signature'][0] != 'A' else 'Q') + envelope['signature'][1:]
        response = self.client.post('/promotions', headers=self.promotion_headers(), json=envelope)
        self.assertEqual(response.status_code, 401)
        rejected = [event for event in self.store._promotion_events if event.event_type == 'promotion.rejected']
        self.assertEqual(len(rejected), 1)
        event = rejected[0]
        self.assertEqual(event.reason_code, 'signature_invalid')
        serialized = str(event.to_dict())
        self.assertNotIn(envelope['signature'], serialized)
        self.assertNotIn(envelope['payload']['reason'], serialized)
        self.assertNotIn('Authorization', serialized)
        metrics = self.client.get('/metrics', headers=self.read_headers)
        self.assertIn('adaptive_trust_ci_promotion_requests_total{outcome="signature_invalid"} 1', metrics.text)
        self.assertNotIn(envelope['payload']['promotion_id'], metrics.text)

    def test_audit_failure_and_database_outage_create_zero_authority(self) -> None:
        envelope = self.promotion_envelope().to_dict()
        envelope['signature'] = ('A' if envelope['signature'][0] != 'A' else 'Q') + envelope['signature'][1:]
        audit_store = FailingAuditStore()
        audit_client = TestClient(create_app(self.settings, store=audit_store, policy=self.policy, trust_store=self.trust_store))
        audit_failure = audit_client.post('/promotions', headers=self.promotion_headers(), json=envelope)
        self.assertEqual((audit_failure.status_code, audit_failure.json()['code']), (503, 'authorization_unavailable'))
        self.assertEqual(len(audit_store._promotions), 0)
        self.assertEqual(audit_client.app.state.promotion_audit_failures, 1)

        outage_store = OutageStore()
        outage_client = TestClient(create_app(self.settings, store=outage_store, policy=self.policy, trust_store=self.trust_store))
        outage = outage_client.post('/promotions', headers=self.promotion_headers(), json=self.promotion_envelope().to_dict())
        self.assertEqual((outage.status_code, outage.json()['code']), (503, 'authorization_unavailable'))
        self.assertEqual(len(outage_store._promotions), 0)


if __name__ == '__main__':
    unittest.main()
