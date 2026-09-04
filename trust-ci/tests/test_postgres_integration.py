from __future__ import annotations

import json
import os
import threading
import unittest
from datetime import timedelta
from pathlib import Path

from _support import digest, now, sha
from adaptive_trust_ci.migrations import PostgresMigrator
from adaptive_trust_ci.models import ApprovalPayload, AttestationEnvelope, AttestationPayload, JobRequest
from adaptive_trust_ci.signing import Signer, sign_approval, sign_attestation, verify_attestation
from adaptive_trust_ci.store import PostgresStore, ReplayError


DATABASE_URL = os.environ.get('TRUST_CI_TEST_DATABASE_URL', '').strip()


@unittest.skipUnless(DATABASE_URL, 'TRUST_CI_TEST_DATABASE_URL is not configured')
class PostgresIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.store = PostgresStore(DATABASE_URL)
        cls.migrator = PostgresMigrator(DATABASE_URL)
        cls.migrator.apply()

    def setUp(self) -> None:
        with self.store._connect() as connection:
            connection.execute(
                'TRUNCATE trust_ci_events, trust_ci_attestations, trust_ci_approvals, '
                'trust_ci_job_attempts, trust_ci_jobs RESTART IDENTITY CASCADE'
            )
            connection.commit()

    def request(self, *, head='b') -> JobRequest:
        return JobRequest(
            repository='Dimkox/adaptive-grok-build-pro',
            pr_number=701,
            base_sha=sha('a'),
            head_sha=sha(head),
            head_ref='feat/postgres-test',
            base_ref='main',
        )

    def enqueue(self, *, max_attempts=3):
        return self.store.enqueue(self.request(), digest('c'), max_attempts, now=now())

    def test_migration_registry_is_current_and_idempotent(self) -> None:
        first = self.migrator.status()
        self.assertEqual(first.pending, ())
        self.assertGreaterEqual(len(first.applied), 2)
        second = self.migrator.apply()
        self.assertEqual(second.pending, ())
        self.assertEqual(
            [(item.version, item.sha256) for item in first.applied],
            [(item.version, item.sha256) for item in second.applied],
        )
        with self.store._connect() as connection:
            rows = connection.execute(
                'SELECT version, name, sha256 FROM trust_ci_schema_migrations ORDER BY version'
            ).fetchall()
            connection.rollback()
        self.assertEqual(len(rows), len(first.applied))

    def test_two_concurrent_workers_cannot_claim_same_live_job(self) -> None:
        job, _ = self.enqueue()
        barrier = threading.Barrier(3)
        claimed = []
        errors = []

        def claim(worker_id: str) -> None:
            try:
                barrier.wait(timeout=10)
                claimed.append(self.store.claim(worker_id, 60, now=now()))
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=claim, args=(f'worker-{number}',)) for number in (1, 2)]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=10)
        for thread in threads:
            thread.join(timeout=20)
        self.assertEqual(errors, [])
        winners = [item for item in claimed if item is not None]
        self.assertEqual(len(winners), 1)
        self.assertEqual(winners[0].job_id, job.job_id)
        self.assertEqual(self.store.get_job(job.job_id).attempts, 1)

    def test_expired_database_lease_is_reclaimed_by_another_worker(self) -> None:
        job, _ = self.enqueue()
        first = self.store.claim('worker-1', 60, now=now())
        assert first is not None
        with self.store._connect() as connection:
            connection.execute(
                "UPDATE trust_ci_jobs SET lease_expires_at = now() - interval '1 second' WHERE job_id = %s",
                (job.job_id,),
            )
            connection.commit()
        second = self.store.claim('worker-2', 60, now=now() + timedelta(minutes=1))
        assert second is not None
        self.assertEqual(second.job_id, job.job_id)
        self.assertEqual(second.lease_owner, 'worker-2')
        self.assertEqual(second.attempts, 2)

    def test_heartbeat_requires_current_lease_owner(self) -> None:
        job, _ = self.enqueue()
        self.store.claim('worker-1', 60, now=now())
        heartbeat = self.store.heartbeat(job.job_id, 'worker-1', 120, now=now() + timedelta(seconds=1))
        self.assertEqual(heartbeat.lease_owner, 'worker-1')
        with self.assertRaisesRegex(RuntimeError, 'own'):
            self.store.heartbeat(job.job_id, 'worker-2', 120, now=now() + timedelta(seconds=2))

    def test_expired_lease_at_attempt_limit_becomes_dead(self) -> None:
        job, _ = self.enqueue(max_attempts=1)
        self.store.claim('worker-1', 60, now=now())
        with self.store._connect() as connection:
            connection.execute(
                "UPDATE trust_ci_jobs SET lease_expires_at = now() - interval '1 second' WHERE job_id = %s",
                (job.job_id,),
            )
            connection.commit()
        self.assertIsNone(self.store.claim('worker-2', 60, now=now() + timedelta(minutes=1)))
        dead = self.store.get_job(job.job_id)
        self.assertEqual(dead.status, 'dead')
        self.assertEqual(dead.failure_code, 'attempts-exhausted-after-worker-loss')

    def test_duplicate_webhook_identity_returns_same_job(self) -> None:
        first, created = self.enqueue()
        second, duplicate = self.enqueue()
        self.assertTrue(created)
        self.assertFalse(duplicate)
        self.assertEqual(first.job_id, second.job_id)

    def test_approval_nonce_replay_is_rejected_by_database_constraint(self) -> None:
        signer = Signer.generate()
        payload = ApprovalPayload.new(
            actor='dmitry',
            key_id=signer.key_id,
            repository='Dimkox/adaptive-grok-build-pro',
            pr_number=701,
            base_sha=sha('a'),
            head_sha=sha('b'),
            policy_digest=digest('c'),
            scope='governance',
            reason='reviewed exact SHA',
            now=now(),
        )
        envelope = sign_approval(payload, signer)
        self.store.record_approval(payload, envelope, now=now())
        with self.assertRaises(ReplayError):
            self.store.record_approval(payload, envelope, now=now())

    def test_signed_attestation_survives_new_store_instance(self) -> None:
        job, _ = self.enqueue()
        signer = Signer.generate()
        payload = AttestationPayload(
            schema_version=1,
            attestation_id='00000000-0000-0000-0000-000000000701',
            job_id=job.job_id,
            repository=job.repository,
            pr_number=job.pr_number,
            base_sha=job.base_sha,
            head_sha=job.head_sha,
            policy_digest=job.policy_digest,
            status='passed',
            command_results=({'name': 'unit', 'status': 'pass', 'exit_code': 0, 'output_sha256': digest('d')},),
            changed_files=('docs/x.md',),
            approved_scopes=(),
            started_at=now().isoformat(),
            completed_at=(now() + timedelta(seconds=2)).isoformat(),
            key_id=signer.key_id,
        )
        envelope = sign_attestation(payload, signer)
        self.store.record_attestation(job.job_id, envelope)
        reconnected = PostgresStore(DATABASE_URL)
        stored = reconnected.get_attestation(job.job_id)
        self.assertIsNotNone(stored)
        assert stored is not None
        verified = verify_attestation(stored, signer.public_key_pem())
        self.assertEqual(verified.job_id, job.job_id)
        self.assertEqual(verified.head_sha, job.head_sha)

    def test_committed_pre_m1_golden_round_trips_exactly_through_postgres(self) -> None:
        fixture = json.loads((Path(__file__).parent / 'fixtures/pre-m1-attestation-postgres.json').read_text(encoding='utf-8'))
        envelope = AttestationEnvelope.from_dict(fixture['envelope'])
        payload = verify_attestation(envelope, fixture['public_key_pem'].encode())
        request = JobRequest(
            repository=payload.repository,
            pr_number=payload.pr_number,
            base_sha=payload.base_sha,
            head_sha=payload.head_sha,
            head_ref='feat/pre-m1-postgres',
            base_ref='main',
        )
        job, _ = self.store.enqueue(request, payload.policy_digest, 3, now=now())
        with self.store._connect() as connection:
            connection.execute(
                'UPDATE trust_ci_jobs SET job_id = %s WHERE job_id = %s',
                (payload.job_id, job.job_id),
            )
            connection.commit()
        self.store.record_attestation(payload.job_id, envelope)
        stored = PostgresStore(DATABASE_URL).get_attestation(payload.job_id)
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored.to_dict(), fixture['envelope'])
        verified = verify_attestation(stored, fixture['public_key_pem'].encode())
        self.assertEqual(verified.job_id, payload.job_id)
        self.assertIsNone(verified.spec_digest)

    def test_signed_typed_metadata_round_trips_through_postgres(self) -> None:
        job, _ = self.enqueue()
        signer = Signer.generate()
        payload = AttestationPayload(
            schema_version=1,
            attestation_id='00000000-0000-0000-0000-000000000702',
            job_id=job.job_id,
            repository=job.repository,
            pr_number=job.pr_number,
            base_sha=job.base_sha,
            head_sha=job.head_sha,
            policy_digest=job.policy_digest,
            status='failed',
            command_results=({'name': 'typed-spec-metadata', 'status': 'fail', 'exit_code': 96, 'output_sha256': digest('e')},),
            changed_files=('engineering/changes/20260826-alpha/change-spec.yaml',),
            approved_scopes=(),
            started_at=now().isoformat(),
            completed_at=(now() + timedelta(seconds=2)).isoformat(),
            key_id=signer.key_id,
            spec_digest=digest('f'),
            criterion_coverage={
                'spec_count': 2,
                'criterion_total': 2,
                'criterion_mapped': 1,
                'unmapped_ids': ['engineering/changes/20260826-alpha/change-spec.yaml#AC-001'],
            },
        )
        envelope = sign_attestation(payload, signer)
        self.store.record_attestation(job.job_id, envelope)
        stored = PostgresStore(DATABASE_URL).get_attestation(job.job_id)
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored.to_dict(), envelope.to_dict())
        verified = verify_attestation(stored, signer.public_key_pem())
        self.assertEqual(verified.spec_digest, digest('f'))
        self.assertEqual(verified.criterion_coverage, payload.criterion_coverage)


if __name__ == '__main__':
    unittest.main()
