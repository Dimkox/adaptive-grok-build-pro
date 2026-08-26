from __future__ import annotations

import json
import unittest
from datetime import timedelta
from pathlib import Path

from _support import digest, now, sha
from adaptive_trust_ci.models import ApprovalEnvelope, ApprovalPayload, AttestationEnvelope, AttestationPayload
from adaptive_trust_ci.signing import ApprovalError, Signer, TrustStore, sign_approval, sign_attestation, verify_approval, verify_attestation
from adaptive_trust_ci.store import MemoryStore, ReplayError


class SigningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.signer = Signer.generate()
        self.store = TrustStore.from_dict(
            {
                "schema_version": 1,
                "keys": [
                    {
                        "key_id": self.signer.key_id,
                        "actor": "dmitry",
                        "scopes": ["governance", "database"],
                        "public_key_pem": self.signer.public_key_pem().decode(),
                    }
                ],
            }
        )
        self.payload = ApprovalPayload.new(
            actor="dmitry",
            key_id=self.signer.key_id,
            repository="Dimkox/adaptive-grok-build-pro",
            pr_number=42,
            base_sha=sha("a"),
            head_sha=sha("b"),
            policy_digest=digest("c"),
            scope="governance",
            reason="reviewed exact governance diff",
            now=now(),
            ttl_seconds=900,
        )
        self.envelope = sign_approval(self.payload, self.signer)

    def verify(self, envelope=None, **overrides):
        values = {
            "expected_repository": self.payload.repository,
            "expected_pr_number": self.payload.pr_number,
            "expected_base_sha": self.payload.base_sha,
            "expected_head_sha": self.payload.head_sha,
            "expected_policy_digest": self.payload.policy_digest,
            "now": now() + timedelta(seconds=1),
            "max_ttl_seconds": 1800,
        }
        values.update(overrides)
        return verify_approval(envelope or self.envelope, self.store, **values)

    def test_valid_signature_verifies(self) -> None:
        self.assertEqual(self.verify().approval_id, self.payload.approval_id)

    def test_payload_tampering_breaks_signature(self) -> None:
        data = self.envelope.to_dict()
        data["payload"]["reason"] = "changed after signature"
        with self.assertRaisesRegex(ApprovalError, "signature"):
            self.verify(ApprovalEnvelope.from_dict(data))

    def test_wrong_head_sha_is_rejected(self) -> None:
        with self.assertRaisesRegex(ApprovalError, "head SHA"):
            self.verify(expected_head_sha=sha("d"))

    def test_wrong_base_sha_is_rejected(self) -> None:
        with self.assertRaisesRegex(ApprovalError, "base SHA"):
            self.verify(expected_base_sha=sha("d"))

    def test_wrong_policy_digest_is_rejected(self) -> None:
        with self.assertRaisesRegex(ApprovalError, "policy digest"):
            self.verify(expected_policy_digest=digest("d"))

    def test_expired_approval_is_rejected(self) -> None:
        with self.assertRaisesRegex(ApprovalError, "expired"):
            self.verify(now=now() + timedelta(seconds=901))

    def test_excessive_ttl_is_rejected(self) -> None:
        with self.assertRaisesRegex(ApprovalError, "TTL"):
            self.verify(max_ttl_seconds=100)

    def test_scope_not_authorized_for_key_is_rejected(self) -> None:
        payload = ApprovalPayload.new(
            actor="dmitry",
            key_id=self.signer.key_id,
            repository=self.payload.repository,
            pr_number=42,
            base_sha=sha("a"),
            head_sha=sha("b"),
            policy_digest=digest("c"),
            scope="production",
            reason="not allowed",
            now=now(),
        )
        with self.assertRaisesRegex(ApprovalError, "scope"):
            self.verify(sign_approval(payload, self.signer))

    def test_actor_must_match_trusted_identity(self) -> None:
        payload = ApprovalPayload.new(
            actor="agent",
            key_id=self.signer.key_id,
            repository=self.payload.repository,
            pr_number=42,
            base_sha=sha("a"),
            head_sha=sha("b"),
            policy_digest=digest("c"),
            scope="governance",
            reason="wrong actor",
            now=now(),
        )
        with self.assertRaisesRegex(ApprovalError, "actor"):
            self.verify(sign_approval(payload, self.signer))

    def test_store_rejects_approval_replay(self) -> None:
        memory = MemoryStore()
        memory.record_approval(self.payload, self.envelope, now=now())
        with self.assertRaises(ReplayError):
            memory.record_approval(self.payload, self.envelope, now=now())

    def test_pre_m1_attestation_signature_and_store_replay_remain_valid(self) -> None:
        legacy = {
            'schema_version': 1, 'attestation_id': 'legacy-attestation', 'job_id': 'job-1',
            'repository': 'Dimkox/adaptive-grok-build-pro', 'pr_number': 42,
            'base_sha': sha('a'), 'head_sha': sha('b'), 'policy_digest': digest('c'),
            'status': 'passed', 'command_results': [], 'changed_files': ['docs/x.md'],
            'approved_scopes': [], 'started_at': now().isoformat(), 'completed_at': now().isoformat(),
            'key_id': self.signer.key_id,
        }
        envelope = AttestationEnvelope.from_dict({'payload': legacy, 'signature': self.signer.sign(legacy)})
        verified = verify_attestation(envelope, self.signer.public_key_pem())
        self.assertIsNone(verified.spec_digest)
        memory = MemoryStore()
        memory.record_attestation('job-1', envelope)
        stored = memory.get_attestation('job-1')
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(verify_attestation(stored, self.signer.public_key_pem()).attestation_id, 'legacy-attestation')
        self.assertNotIn('spec_digest', stored.to_dict()['payload'])

    def test_committed_pre_m1_golden_verifies_and_replays_without_rewriting(self) -> None:
        fixture = json.loads((Path(__file__).parent / 'fixtures/pre-m1-attestation.json').read_text(encoding='utf-8'))
        envelope = AttestationEnvelope.from_dict(fixture['envelope'])
        verified = verify_attestation(envelope, fixture['public_key_pem'].encode())
        self.assertEqual(verified.attestation_id, 'pre-m1-golden-attestation')
        self.assertIsNone(verified.spec_digest)
        memory = MemoryStore()
        memory.record_attestation(verified.job_id, envelope)
        stored = memory.get_attestation(verified.job_id)
        assert stored is not None
        self.assertEqual(stored.to_dict(), fixture['envelope'])
        self.assertEqual(verify_attestation(stored, fixture['public_key_pem'].encode()).job_id, verified.job_id)

    def test_attestation_coverage_is_strict_and_bounded(self) -> None:
        legacy = {
            'schema_version': 1, 'attestation_id': 'new-attestation', 'job_id': 'job-1',
            'repository': 'Dimkox/adaptive-grok-build-pro', 'pr_number': 42,
            'base_sha': sha('a'), 'head_sha': sha('b'), 'policy_digest': digest('c'),
            'status': 'passed', 'command_results': [], 'changed_files': [], 'approved_scopes': [],
            'started_at': now().isoformat(), 'completed_at': now().isoformat(), 'key_id': self.signer.key_id,
            'spec_digest': digest('d'),
            'criterion_coverage': {'spec_count': 1, 'criterion_total': 2, 'criterion_mapped': 1, 'unmapped_ids': ['AC-002']},
        }
        payload = AttestationPayload.from_dict(legacy)
        self.assertEqual(payload.criterion_coverage['unmapped_ids'], ['AC-002'])
        legacy['criterion_coverage']['extra'] = 1
        with self.assertRaises(ValueError):
            AttestationPayload.from_dict(legacy)

    def test_signed_spec_metadata_detects_digest_and_coverage_tampering(self) -> None:
        data = {
            'schema_version': 1, 'attestation_id': 'new-attestation', 'job_id': 'job-1',
            'repository': 'Dimkox/adaptive-grok-build-pro', 'pr_number': 42,
            'base_sha': sha('a'), 'head_sha': sha('b'), 'policy_digest': digest('c'),
            'status': 'passed', 'command_results': [], 'changed_files': [], 'approved_scopes': [],
            'started_at': now().isoformat(), 'completed_at': now().isoformat(), 'key_id': self.signer.key_id,
            'spec_digest': digest('d'),
            'criterion_coverage': {'spec_count': 1, 'criterion_total': 1, 'criterion_mapped': 1, 'unmapped_ids': []},
        }
        envelope = sign_attestation(AttestationPayload.from_dict(data), self.signer)
        self.assertEqual(verify_attestation(envelope, self.signer.public_key_pem()).spec_digest, digest('d'))
        for mutate in (
            lambda payload: payload.update(spec_digest=digest('e')),
            lambda payload: payload['criterion_coverage'].update(criterion_mapped=0, unmapped_ids=['AC-001']),
        ):
            tampered = envelope.to_dict()
            mutate(tampered['payload'])
            with self.assertRaisesRegex(ApprovalError, 'signature'):
                verify_attestation(AttestationEnvelope.from_dict(tampered), self.signer.public_key_pem())


if __name__ == "__main__":
    unittest.main()
