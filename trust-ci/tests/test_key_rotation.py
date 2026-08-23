from __future__ import annotations

import unittest
from datetime import timedelta

from _support import digest, now, sha
from adaptive_trust_ci.models import ApprovalPayload
from adaptive_trust_ci.signing import (
    ApprovalError,
    Signer,
    TrustStore,
    sign_approval,
    verify_approval,
)


def key_record(
    signer: Signer,
    *,
    actor: str = 'dmitry',
    scopes: list[str] | None = None,
    not_before: str | None = None,
    not_after: str | None = None,
    revoked_at: str | None = None,
) -> dict:
    record = {
        'key_id': signer.key_id,
        'actor': actor,
        'scopes': scopes or ['governance'],
        'public_key_pem': signer.public_key_pem().decode('utf-8'),
    }
    for name, value in (
        ('not_before', not_before),
        ('not_after', not_after),
        ('revoked_at', revoked_at),
    ):
        if value is not None:
            record[name] = value
    return record


def approval(signer: Signer, *, issued=None):
    issued = issued or now()
    payload = ApprovalPayload.new(
        actor='dmitry',
        key_id=signer.key_id,
        repository='Dimkox/adaptive-grok-build-pro',
        pr_number=9,
        base_sha=sha('a'),
        head_sha=sha('b'),
        policy_digest=digest('c'),
        scope='governance',
        reason='reviewed',
        now=issued,
        ttl_seconds=600,
    )
    return payload, sign_approval(payload, signer)


def verify(envelope, store, *, current=None):
    return verify_approval(
        envelope,
        store,
        expected_repository='Dimkox/adaptive-grok-build-pro',
        expected_pr_number=9,
        expected_base_sha=sha('a'),
        expected_head_sha=sha('b'),
        expected_policy_digest=digest('c'),
        now=current or now() + timedelta(seconds=1),
        max_ttl_seconds=1800,
    )


class KeyRotationTests(unittest.TestCase):
    def test_schema_v1_trust_store_remains_compatible(self) -> None:
        signer = Signer.generate()
        store = TrustStore.from_dict({'schema_version': 1, 'keys': [key_record(signer)]})
        _, envelope = approval(signer)
        self.assertEqual(verify(envelope, store).key_id, signer.key_id)

    def test_schema_v2_accepts_overlapping_active_keys(self) -> None:
        old = Signer.generate()
        new = Signer.generate()
        store = TrustStore.from_dict(
            {
                'schema_version': 2,
                'keys': [
                    key_record(old, not_before=(now() - timedelta(days=1)).isoformat(), not_after=(now() + timedelta(days=1)).isoformat()),
                    key_record(new, not_before=(now() - timedelta(hours=1)).isoformat(), not_after=(now() + timedelta(days=30)).isoformat()),
                ],
            }
        )
        _, old_envelope = approval(old)
        _, new_envelope = approval(new)
        self.assertEqual(verify(old_envelope, store).key_id, old.key_id)
        self.assertEqual(verify(new_envelope, store).key_id, new.key_id)

    def test_revoked_key_cannot_authorize_new_or_unexpired_approval(self) -> None:
        signer = Signer.generate()
        store = TrustStore.from_dict(
            {
                'schema_version': 2,
                'keys': [key_record(signer, revoked_at=(now() + timedelta(seconds=2)).isoformat())],
            }
        )
        _, envelope = approval(signer)
        with self.assertRaisesRegex(ApprovalError, 'revoked'):
            verify(envelope, store, current=now() + timedelta(seconds=3))

    def test_not_yet_valid_key_is_rejected(self) -> None:
        signer = Signer.generate()
        store = TrustStore.from_dict(
            {
                'schema_version': 2,
                'keys': [key_record(signer, not_before=(now() + timedelta(hours=1)).isoformat())],
            }
        )
        _, envelope = approval(signer)
        with self.assertRaisesRegex(ApprovalError, 'not valid yet'):
            verify(envelope, store)

    def test_expired_key_is_rejected(self) -> None:
        signer = Signer.generate()
        store = TrustStore.from_dict(
            {
                'schema_version': 2,
                'keys': [key_record(signer, not_after=(now() + timedelta(seconds=2)).isoformat())],
            }
        )
        _, envelope = approval(signer)
        with self.assertRaisesRegex(ApprovalError, 'expired'):
            verify(envelope, store, current=now() + timedelta(seconds=3))

    def test_invalid_key_lifecycle_is_rejected_during_load(self) -> None:
        signer = Signer.generate()
        with self.assertRaisesRegex(ApprovalError, 'not_after must be after not_before'):
            TrustStore.from_dict(
                {
                    'schema_version': 2,
                    'keys': [
                        key_record(
                            signer,
                            not_before=now().isoformat(),
                            not_after=(now() - timedelta(seconds=1)).isoformat(),
                        )
                    ],
                }
            )


if __name__ == '__main__':
    unittest.main()
