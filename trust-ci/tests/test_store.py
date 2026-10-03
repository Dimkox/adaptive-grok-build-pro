from __future__ import annotations

import unittest
import dataclasses
from datetime import timedelta
from unittest.mock import MagicMock, patch

from _support import digest, now, sha
from adaptive_trust_ci.models import ApprovalPayload, JobRequest
from adaptive_trust_ci.signing import Signer, sign_approval
from adaptive_trust_ci.store import MemoryStore, PostgresStore


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = MemoryStore()
        self.request = JobRequest(
            repository="Dimkox/adaptive-grok-build-pro",
            pr_number=7,
            base_sha=sha("a"),
            head_sha=sha("b"),
            head_ref="feat/test",
            base_ref="main",
        )

    def enqueue(self, request=None, *, max_attempts=3):
        return self.store.enqueue(request or self.request, digest("c"), max_attempts, now=now())

    def test_enqueue_is_idempotent_for_same_sha_and_policy(self) -> None:
        first, created_first = self.enqueue()
        second, created_second = self.enqueue()
        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.job_id, second.job_id)

    def test_new_head_cancels_old_active_job(self) -> None:
        first, _ = self.enqueue()
        changed = JobRequest(
            repository=self.request.repository,
            pr_number=self.request.pr_number,
            base_sha=self.request.base_sha,
            head_sha=sha("d"),
            head_ref=self.request.head_ref,
            base_ref=self.request.base_ref,
        )
        second, _ = self.enqueue(changed)
        self.assertEqual(self.store.get_job(first.job_id).status, "cancelled")
        self.assertEqual(second.status, "queued")

    def test_claim_uses_a_lease_and_increments_attempt(self) -> None:
        job, _ = self.enqueue()
        claimed = self.store.claim("worker-1", 60, now=now())
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(claimed.job_id, job.job_id)
        self.assertEqual(claimed.status, "leased")
        self.assertEqual(claimed.attempts, 1)
        self.assertEqual(claimed.lease_owner, "worker-1")

    def test_live_lease_cannot_be_claimed_twice(self) -> None:
        self.enqueue()
        self.store.claim("worker-1", 60, now=now())
        self.assertIsNone(self.store.claim("worker-2", 60, now=now() + timedelta(seconds=30)))

    def test_expired_lease_is_reclaimed(self) -> None:
        self.enqueue()
        first = self.store.claim("worker-1", 10, now=now())
        assert first is not None
        second = self.store.claim("worker-2", 10, now=now() + timedelta(seconds=11))
        assert second is not None
        self.assertEqual(second.job_id, first.job_id)
        self.assertEqual(second.attempts, 2)
        self.assertEqual(second.lease_owner, "worker-2")

    def test_expired_lease_at_attempt_limit_becomes_dead(self) -> None:
        job, _ = self.enqueue(max_attempts=1)
        self.store.claim("worker-1", 10, now=now())
        self.assertIsNone(self.store.claim("worker-2", 10, now=now() + timedelta(seconds=11)))
        self.assertEqual(self.store.get_job(job.job_id).status, "dead")

    def test_heartbeat_extends_only_owned_lease(self) -> None:
        job, _ = self.enqueue()
        self.store.claim("worker-1", 10, now=now())
        heartbeat = self.store.heartbeat(job.job_id, "worker-1", 30, now=now() + timedelta(seconds=5))
        self.assertEqual(heartbeat.lease_expires_at, now() + timedelta(seconds=35))
        with self.assertRaisesRegex(RuntimeError, "own"):
            self.store.heartbeat(job.job_id, "worker-2", 30, now=now() + timedelta(seconds=6))

    def test_retry_requeues_until_attempt_limit(self) -> None:
        job, _ = self.enqueue(max_attempts=2)
        self.store.claim("worker-1", 60, now=now())
        first = self.store.retry(job.job_id, "worker-1", "network", now=now() + timedelta(seconds=1))
        self.assertEqual(first.status, "queued")
        self.store.claim("worker-1", 60, now=now() + timedelta(seconds=2))
        second = self.store.retry(job.job_id, "worker-1", "network", now=now() + timedelta(seconds=3))
        self.assertEqual(second.status, "dead")

    def test_closed_pull_request_cancels_active_jobs(self) -> None:
        job, _ = self.enqueue()
        count = self.store.cancel_pr(job.repository, job.pr_number, now=now())
        self.assertEqual(count, 1)
        self.assertEqual(self.store.get_job(job.job_id).failure_code, "pull-request-closed")

    def test_approval_lookup_is_bound_to_all_exact_fields(self) -> None:
        signer = Signer.generate()
        payload = ApprovalPayload.new(
            actor="human",
            key_id=signer.key_id,
            repository=self.request.repository,
            pr_number=self.request.pr_number,
            base_sha=self.request.base_sha,
            head_sha=self.request.head_sha,
            policy_digest=digest("c"),
            scope="governance",
            reason="approved",
            now=now(),
        )
        self.store.record_approval(payload, sign_approval(payload, signer), now=now())
        self.assertTrue(
            self.store.has_valid_approval(
                payload.repository,
                payload.pr_number,
                payload.base_sha,
                payload.head_sha,
                payload.policy_digest,
                payload.scope,
                now() + timedelta(seconds=1),
            )
        )
        self.assertFalse(
            self.store.has_valid_approval(
                payload.repository,
                payload.pr_number,
                sha("d"),
                payload.head_sha,
                payload.policy_digest,
                payload.scope,
                now() + timedelta(seconds=1),
            )
        )

    def test_approval_requeues_waiting_exact_sha(self) -> None:
        job, _ = self.enqueue()
        claimed = self.store.claim("worker-1", 60, now=now())
        assert claimed is not None
        self.store.finish(
            job.job_id,
            "worker-1",
            "needs_approval",
            {"missing_scopes": ["governance"]},
            failure_code="approval-required",
            now=now() + timedelta(seconds=1),
        )
        count = self.store.requeue_for_approval(job.repository, job.head_sha, now=now() + timedelta(seconds=2))
        self.assertEqual(count, 1)
        self.assertEqual(self.store.get_job(job.job_id).status, "queued")

    def test_bounded_approval_inventory_is_available(self) -> None:
        self.assertTrue(callable(getattr(self.store, 'list_matching_approvals', None)))

    def approval(self, **changes):
        signer = Signer.generate()
        payload = ApprovalPayload.new(actor='synthetic', key_id=signer.key_id,
            repository=self.request.repository, pr_number=self.request.pr_number,
            base_sha=self.request.base_sha, head_sha=self.request.head_sha,
            policy_digest=digest('c'), scope='governance', reason='synthetic', now=now())
        payload = dataclasses.replace(payload, **changes)
        envelope = sign_approval(payload, signer)
        self.store.record_approval(payload, envelope, now=now())
        return envelope

    def inventory(self, *, store=None, limit=128):
        return (store or self.store).list_matching_approvals(self.request.repository,
            self.request.pr_number, self.request.base_sha, self.request.head_sha,
            digest('c'), now=now(), limit=limit)

    def test_inventory_filters_exact_tuple_and_approval_time(self):
        expected = self.approval()
        for changes in ({'repository': 'Other/repository'}, {'pr_number': 8}, {'base_sha': sha('d')},
                        {'head_sha': sha('d')}, {'policy_digest': digest('d')},
                        {'issued_at': (now() + timedelta(seconds=1)).isoformat()},
                        {'issued_at': (now() - timedelta(seconds=1)).isoformat(), 'expires_at': now().isoformat()}):
            self.approval(**changes)
        result = self.inventory(limit=1)
        self.assertEqual(result, [expected])
        self.assertIsNot(result[0], expected)

    def test_inventory_orders_expiry_descending_then_approval_id_ascending(self):
        short = self.approval(expires_at=(now() + timedelta(seconds=5)).isoformat())
        later = self.approval(approval_id='00000000-0000-0000-0000-000000000003')
        earlier = self.approval(approval_id='00000000-0000-0000-0000-000000000002')
        self.assertEqual(self.inventory(), [earlier, later, short])

    def test_memory_overflow_stops_acquisition_at_limit_plus_one(self):
        envelope = self.approval()
        class ObservedRows(dict):
            acquired = 0
            def values(rows):
                for _ in range(1000):
                    rows.acquired += 1
                    yield envelope.payload, envelope
        rows = ObservedRows()
        self.store._approvals = rows
        with self.assertRaisesRegex(RuntimeError, 'bound'):
            self.inventory(limit=2)
        self.assertEqual(rows.acquired, 3)

    def test_inventory_rejects_unbounded_limits_before_acquisition(self):
        for limit in (0, -1, 129, True, '1', None):
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError):
                    self.inventory(limit=limit)
                with patch.object(PostgresStore, '_connect', side_effect=AssertionError('must not acquire')):
                    with self.assertRaises(ValueError):
                        self.inventory(store=PostgresStore('postgresql://unused'), limit=limit)

    def test_postgres_query_is_timed_bounded_and_exact(self):
        envelope = self.approval()
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [{'payload': envelope.payload.to_dict(), 'signature': envelope.signature}]
        with patch.object(PostgresStore, '_connect', return_value=connection):
            self.assertEqual(self.inventory(store=PostgresStore('postgresql://unused'), limit=7), [envelope])
        calls = cursor.execute.call_args_list
        self.assertEqual(calls[0].args, ("SET LOCAL statement_timeout = '4000ms'",))
        sql, params = calls[1].args
        self.assertEqual(params, (self.request.repository, 7, sha('a'), sha('b'), digest('c'), now(), now(), 8))
        for predicate in ('repository = %s', 'pr_number = %s', 'base_sha = %s', 'head_sha = %s',
                          'policy_digest = %s', 'issued_at <= %s', 'expires_at > %s'):
            self.assertIn(predicate, sql)
        self.assertIn('ORDER BY expires_at DESC, approval_id ASC', sql)
        self.assertIn('LIMIT %s', sql)
        cursor.fetchall.return_value *= 8
        with patch.object(PostgresStore, '_connect', return_value=connection):
            with self.assertRaisesRegex(RuntimeError, 'bound'):
                self.inventory(store=PostgresStore('postgresql://unused'), limit=7)


if __name__ == "__main__":
    unittest.main()
