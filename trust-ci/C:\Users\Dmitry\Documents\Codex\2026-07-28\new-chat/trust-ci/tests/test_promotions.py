from __future__ import annotations

import base64
import json
import unittest
from datetime import timedelta

from _support import digest, now, sha
from adaptive_trust_ci.models import PromotionEnvelope, PromotionPayload, ProtectedBranchAttestationPayload, canonical_json
from adaptive_trust_ci.signing import PROMOTION_VERIFICATION_ERROR, Signer, TrustStore, sign_promotion, verify_promotion


class PromotionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.signer = Signer.generate()
        self.store = TrustStore.from_dict({"schema_version": 2, "keys": [{"key_id": self.signer.key_id, "actor": "operator", "scopes": ["promotion:production"], "public_key_pem": self.signer.public_key_pem().decode()}]})
        self.payload = PromotionPayload.new(actor="operator", key_id=self.signer.key_id, repository="Dimkox/adaptive-grok-build-pro", merged_commit_sha=sha("a"), artifact_sha256=digest("b"), target_environment="production", policy_epoch=digest("c"), source_attestation_id="123e4567-e89b-12d3-a456-426614174000", reason="release exact artifact", now=now(), ttl_seconds=900)
        self.envelope = sign_promotion(self.payload, self.signer)
        self.expected = {"repository": self.payload.repository, "merged_commit_sha": self.payload.merged_commit_sha, "artifact_sha256": self.payload.artifact_sha256, "target_environment": "production", "policy_epoch": self.payload.policy_epoch, "source_attestation_id": self.payload.source_attestation_id}

    def verify(self, envelope=None, **overrides):
        values = {"now": now() + timedelta(seconds=1), "maximum_ttl_seconds": 900}
        values.update(overrides)
        return verify_promotion(envelope or self.envelope, self.store, self.expected, **values)

    def test_valid_signature_and_canonical_bytes_verify(self) -> None:
        self.assertEqual(self.verify(), self.payload)
        self.assertEqual(self.payload.canonical_bytes(), canonical_json(self.payload.to_dict()))
        self.assertEqual(json.loads(self.payload.canonical_bytes()), self.payload.to_dict())

    def test_duplicate_and_unknown_keys_are_rejected(self) -> None:
        raw = self.envelope.canonical_bytes().decode().replace('"payload":{', '"payload":{"schema_version":1,')
        with self.assertRaises(ValueError):
            PromotionEnvelope.from_json(raw)
        data = self.envelope.to_dict()
        data["payload"]["unknown"] = True
        with self.assertRaises(ValueError):
            PromotionEnvelope.from_dict(data)

    def test_every_signed_binding_tamper_has_constant_public_error(self) -> None:
        changes = {"promotion_id": "123e4567-e89b-12d3-a456-426614174001", "nonce": base64.urlsafe_b64encode(b"z" * 32).decode().rstrip("="), "actor": "other", "key_id": "0" * 16, "repository": "other/repo", "merged_commit_sha": sha("d"), "artifact_sha256": digest("d"), "target_environment": "staging", "policy_epoch": digest("d"), "source_attestation_id": "123e4567-e89b-12d3-a456-426614174001", "reason": "changed", "issued_at": "2026-08-23T12:00:01Z", "expires_at": "2026-08-23T12:15:00Z"}
        for field, value in changes.items():
            data = self.envelope.to_dict()
            data["payload"][field] = value
            with self.assertRaisesRegex(ValueError, f"^{PROMOTION_VERIFICATION_ERROR}$"):
                self.verify(PromotionEnvelope.from_dict(data))

    def test_time_future_skew_and_ttl_boundaries_are_rejected(self) -> None:
        for issued, ttl in ((now() + timedelta(seconds=61), 900), (now(), 0), (now(), 901)):
            with self.assertRaises(ValueError):
                PromotionPayload.new(actor="operator", key_id=self.signer.key_id, repository=self.payload.repository, merged_commit_sha=sha("a"), artifact_sha256=digest("b"), target_environment="production", policy_epoch=digest("c"), source_attestation_id=self.payload.source_attestation_id, reason="x", now=issued, ttl_seconds=ttl)

    def test_expected_tuple_and_production_scope_are_required(self) -> None:
        with self.assertRaisesRegex(ValueError, f"^{PROMOTION_VERIFICATION_ERROR}$"):
            self.verify(expected={**self.expected, "artifact_sha256": digest("d")})
        no_scope = TrustStore.from_dict({"schema_version": 2, "keys": [{"key_id": self.signer.key_id, "actor": "operator", "scopes": ["governance"], "public_key_pem": self.signer.public_key_pem().decode()}]})
        with self.assertRaisesRegex(ValueError, f"^{PROMOTION_VERIFICATION_ERROR}$"):
            verify_promotion(self.envelope, no_scope, self.expected, now=now(), maximum_ttl_seconds=900)

    def test_protected_branch_attestation_is_strict_and_passed(self) -> None:
        attestation = ProtectedBranchAttestationPayload(schema_version=1, source_attestation_id=self.payload.source_attestation_id, repository=self.payload.repository, protected_ref="refs/heads/main", merged_commit_sha=sha("a"), policy_epoch=digest("c"), artifact_sha256=digest("b"), status="passed", runner_digest=digest("d"), holdout_digest=digest("e"), image_digest=digest("f"), created_at="2026-08-23T12:00:00Z")
        self.assertEqual(attestation.to_dict()["status"], "passed")
        with self.assertRaises(ValueError):
            ProtectedBranchAttestationPayload.from_dict({**attestation.to_dict(), "extra": 1})


if __name__ == "__main__":
    unittest.main()
