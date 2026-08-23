from __future__ import annotations

import os
import threading
import unittest
from datetime import timedelta
from importlib.resources import files

from _support import digest, now, sha
from adaptive_trust_ci.models import ApprovalPayload, JobRequest
from adaptive_trust_ci.signing import Signer, sign_approval
from adaptive_trust_ci.store import PostgresStore, ReplayError


DATABASE_URL = os.environ.get('TRUST_CI_TEST_DATABASE_URL', '').strip()


@unittest.skipUnless(DATABASE_URL, 'TRUST_CI_TEST_DATABASE_URL is not configured')
class PostgresIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.store = PostgresStore(DATABASE_URL)
        sql = files('adaptive_trust_ci.resources').joinpath('001_schema.sql').read_text(encoding='utf-8')
        cls.store.migrate(sql)

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

    def test_migration_is_idempotent(self) -> None:
        sql = files('adaptive_trust_ci.resources').joinpath('001_schema.sql').read_text(encoding='utf-8')
        self.store.migrate(sql)
        self.store.ping()

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


if __name__ == '__main__':
    unittest.main()
