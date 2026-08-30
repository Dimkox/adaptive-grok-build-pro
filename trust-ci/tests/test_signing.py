from __future__ import annotations

import unittest
from datetime import timedelta

from _support import digest, now, sha
from adaptive_trust_ci.models import ApprovalEnvelope, ApprovalPayload, PromotionPayload, canonical_json
from adaptive_trust_ci.signing import (
    ApprovalError,
    Signer,
    TrustStore,
    sign_approval,
    sign_promotion,
    verify_approval,
)
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

    def test_promotion_signature_uses_canonical_payload_bytes(self) -> None:
        payload = PromotionPayload(
            schema_version=1,
            promotion_id="12345678-1234-4234-8234-123456789abc",
            nonce="bm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm4",
            actor="dmitry",
            key_id=self.signer.key_id,
            repository="dimkox/adaptive-grok-build-pro",
            merged_commit_sha=sha("a"),
            artifact_sha256=digest("b"),
            target_environment="production",
            policy_epoch=digest("c"),
            source_attestation_id="abcdefab-1234-4234-8234-abcdefabcdef",
            reason="Reviewed exact artifact",
            issued_at="2026-08-23T12:00:00Z",
            expires_at="2026-08-23T12:15:00Z",
        )
        envelope = sign_promotion(payload, self.signer)
        self.signer._private_key.public_key().verify(
            __import__("base64").urlsafe_b64decode(envelope.signature + "=="),
            canonical_json(payload.to_dict()),
        )


if __name__ == "__main__":
    unittest.main()
