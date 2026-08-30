from __future__ import annotations

import unittest
import base64
import threading
import uuid
from dataclasses import replace
from datetime import timedelta

from _support import digest, now, sha
from adaptive_trust_ci.models import (
    ApprovalPayload,
    JobRequest,
    PromotionExpectedBinding,
    PromotionEvent,
    PromotionPayload,
    ProtectedBranchAttestationPayload,
)
from adaptive_trust_ci.provenance import DeliveryConflict, MergedPullRequestFact, ReconciliationWatermark
from adaptive_trust_ci.signing import (
    Signer,
    sign_approval,
    sign_promotion,
    sign_protected_branch_attestation,
)
from adaptive_trust_ci.store import MemoryStore, ProvenanceMismatch, ReplayError


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
        self.signer = Signer.generate()
        self.merge_fact = MergedPullRequestFact.create(
            delivery_id="delivery-store-1",
            payload_sha256=digest("d"),
            repository_id=123,
            repository="dimkox/adaptive-grok-build-pro",
            installation_id=456,
            pr_number=701,
            head_sha=sha("e"),
            base_sha=sha("f"),
            protected_ref="refs/heads/main",
            merged_commit_sha=sha("a"),
            merged_at="2026-08-23T11:59:00Z",
            received_at=now(),
        )
        self.attestation_payload = ProtectedBranchAttestationPayload(
            schema_version=1,
            source_attestation_id="abcdefab-1234-4234-8234-abcdefabcdef",
            merge_fact_id=self.merge_fact.merge_fact_id,
            repository=self.merge_fact.repository,
            protected_ref=self.merge_fact.protected_ref,
            merged_commit_sha=self.merge_fact.merged_commit_sha,
            policy_epoch=digest("c"),
            runner_digest=digest("1"),
            holdout_digest=digest("2"),
            image_digest=digest("3"),
            artifact_sha256=digest("b"),
            result="passed",
            issued_at="2026-08-23T12:00:00Z",
            key_id=self.signer.key_id,
        )
        self.protected_evidence = sign_protected_branch_attestation(
            self.attestation_payload, self.signer
        )
        self.promotion_payload = PromotionPayload(
            schema_version=1,
            promotion_id="12345678-1234-4234-8234-123456789abc",
            nonce=base64.urlsafe_b64encode(b"n" * 32).decode("ascii").rstrip("="),
            actor="dmitry",
            key_id=self.signer.key_id,
            repository=self.attestation_payload.repository,
            merged_commit_sha=self.attestation_payload.merged_commit_sha,
            artifact_sha256=self.attestation_payload.artifact_sha256,
            target_environment="production",
            policy_epoch=self.attestation_payload.policy_epoch,
            source_attestation_id=self.attestation_payload.source_attestation_id,
            reason="Deploy the immutable reviewed artifact",
            issued_at="2026-08-23T12:00:00Z",
            expires_at="2026-08-23T12:15:00Z",
        )
        self.promotion_envelope = sign_promotion(self.promotion_payload, self.signer)
        self.expected_promotion = PromotionExpectedBinding(
            repository=self.promotion_payload.repository,
            merged_commit_sha=self.promotion_payload.merged_commit_sha,
            artifact_sha256=self.promotion_payload.artifact_sha256,
            target_environment=self.promotion_payload.target_environment,
            policy_epoch=self.promotion_payload.policy_epoch,
            source_attestation_id=self.promotion_payload.source_attestation_id,
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

    def seed_protected_evidence(self) -> None:
        self.store.activate_policy(self.promotion_payload.policy_epoch)
        self.assertTrue(self.store.record_merge_fact(self.merge_fact))
        self.assertTrue(self.store.record_protected_branch_evidence(self.protected_evidence))

    def test_merge_fact_delivery_conflict_lease_retry_and_watermark_are_durable_style(self) -> None:
        self.assertTrue(self.store.record_merge_fact(self.merge_fact))
        self.assertFalse(self.store.record_merge_fact(self.merge_fact))
        with self.assertRaises(DeliveryConflict):
            self.store.record_merge_fact(
                replace(self.merge_fact, payload_sha256=digest("e"))
            )

        claimed = self.store.claim_merge_fact("worker-1", 60, now=now())
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(claimed.fact, self.merge_fact)
        self.assertEqual(claimed.attempt, 1)
        self.store.retry_merge_fact(claimed, "github unavailable", now=now())
        self.assertIsNone(self.store.claim_merge_fact("worker-2", 60, now=now()))
        reclaimed = self.store.claim_merge_fact(
            "worker-2", 60, now=now() + timedelta(seconds=5)
        )
        self.assertIsNotNone(reclaimed)
        assert reclaimed is not None
        self.assertEqual(reclaimed.attempt, 2)
        self.store.complete_merge_fact(reclaimed, now=now())
        self.assertIsNone(self.store.claim_merge_fact("worker-3", 60, now=now()))

        first = ReconciliationWatermark("2026-08-23T12:00:00Z", 4)
        later = ReconciliationWatermark("2026-08-23T12:00:00Z", 5)
        self.store.save_reconciliation_watermark(self.merge_fact.repository, first)
        self.store.save_reconciliation_watermark(self.merge_fact.repository, later)
        self.assertEqual(
            self.store.load_reconciliation_watermark(self.merge_fact.repository), later
        )
        with self.assertRaises(ValueError):
            self.store.save_reconciliation_watermark(self.merge_fact.repository, first)

    def test_reconciliation_can_requeue_an_exhausted_merge_fact(self) -> None:
        self.store.record_merge_fact(self.merge_fact)
        queue = self.store._merge_queue[self.merge_fact.merge_fact_id]
        queue.update({"status": "dead", "attempt": 20, "last_error": "retry-exhausted:outage"})

        self.assertTrue(self.store.requeue_merge_fact(self.merge_fact.merge_fact_id, now=now()))
        reclaimed = self.store.claim_merge_fact("worker-recovery", 60, now=now())
        self.assertIsNotNone(reclaimed)
        assert reclaimed is not None
        self.assertEqual(reclaimed.attempt, 1)

    def test_protected_evidence_exact_tuple_reuses_existing_identity_and_rejects_mismatch(self) -> None:
        self.store.record_merge_fact(self.merge_fact)
        self.assertTrue(self.store.record_protected_branch_evidence(self.protected_evidence))
        replay_payload = replace(
            self.attestation_payload,
            source_attestation_id=str(uuid.uuid4()),
            issued_at="2026-08-23T12:00:01Z",
        )
        replay = sign_protected_branch_attestation(replay_payload, self.signer)
        stored = self.store.record_or_get_protected_branch_evidence(replay)
        self.assertEqual(stored, self.protected_evidence)

        mismatch = sign_protected_branch_attestation(
            replace(replay_payload, runner_digest=digest("9")), self.signer
        )
        with self.assertRaises(ReplayError):
            self.store.record_or_get_protected_branch_evidence(mismatch)

    def test_protected_evidence_acceptance_and_consumption_append_atomic_events(self) -> None:
        self.seed_protected_evidence()
        record, created = self.store.accept_promotion(
            self.promotion_envelope, "request-00000001", "correlation-1", now(),
        )
        self.assertTrue(created)
        self.assertEqual(record.promotion_id, self.promotion_payload.promotion_id)
        replay, replay_created = self.store.accept_promotion(
            self.promotion_envelope, "request-00000001", "correlation-2", now(),
        )
        self.assertFalse(replay_created)
        self.assertEqual(replay, record)
        with self.assertRaises(ReplayError):
            self.store.accept_promotion(
                self.promotion_envelope, "request-00000002", "correlation-3", now(),
            )

        operation_id = str(uuid.uuid4())
        consumption = self.store.consume_promotion(
            record.promotion_id, self.expected_promotion, operation_id, now()
        )
        self.assertEqual(consumption.operation_id, operation_id)
        with self.assertRaises(ReplayError):
            self.store.consume_promotion(
                record.promotion_id,
                self.expected_promotion,
                str(uuid.uuid4()),
                now(),
            )
        events = self.store.list_promotion_events(record.promotion_id, limit=10)
        self.assertEqual(
            [event.event_type for event in events],
            ["promotion.accepted", "promotion.consumed"],
        )

    def test_concurrent_accept_and_consume_have_exactly_one_winner(self) -> None:
        self.seed_protected_evidence()

        def concurrently(callable_):
            barrier = threading.Barrier(3)
            values = []

            def run():
                barrier.wait(timeout=5)
                try:
                    values.append(callable_())
                except BaseException as exc:
                    values.append(exc)

            threads = [threading.Thread(target=run) for _ in range(2)]
            for thread in threads:
                thread.start()
            barrier.wait(timeout=5)
            for thread in threads:
                thread.join(timeout=10)
            return values

        accepted = concurrently(
            lambda: self.store.accept_promotion(
                self.promotion_envelope, str(uuid.uuid4()), "correlation-race", now(),
            )
        )
        winners = [value for value in accepted if isinstance(value, tuple) and value[1]]
        self.assertEqual(len(winners), 1)
        self.assertEqual(sum(isinstance(value, ReplayError) for value in accepted), 1)

        consumed = concurrently(
            lambda: self.store.consume_promotion(
                self.promotion_payload.promotion_id,
                self.expected_promotion,
                str(uuid.uuid4()),
                now(),
            )
        )
        self.assertEqual(sum(not isinstance(value, BaseException) for value in consumed), 1)
        self.assertEqual(sum(isinstance(value, ReplayError) for value in consumed), 1)

    def test_exact_provenance_is_required_before_promotion_acceptance(self) -> None:
        self.store.activate_policy(self.promotion_payload.policy_epoch)
        self.store.record_merge_fact(self.merge_fact)
        with self.assertRaisesRegex(RuntimeError, "provenance"):
            self.store.accept_promotion(
                self.promotion_envelope, "request-00000001", "correlation-1", now(),
            )

    def test_acceptance_requires_an_independently_current_policy_epoch(self) -> None:
        self.seed_protected_evidence()
        try:
            self.store.activate_policy(self.promotion_payload.policy_epoch)
            self.assertEqual(
                self.store.get_active_policy_epoch(), self.promotion_payload.policy_epoch
            )
            self.store.activate_policy(digest("f"))
            with self.assertRaises(ProvenanceMismatch):
                self.store.accept_promotion(
                    self.promotion_envelope,
                    "request-00000001",
                    "correlation-1",
                    now(),
                )
        except (AttributeError, TypeError) as exc:
            self.fail(f"acceptance lacks a store-owned current-policy boundary: {exc}")
        self.assertEqual(len(self.store._promotion_idempotency), 0)
        self.assertEqual(len(self.store._promotions), 0)

    def test_rejected_promotion_audit_accepts_only_bounded_typed_rejection(self) -> None:
        event = PromotionEvent(
            schema_version=1,
            event_id=str(uuid.uuid4()),
            event_type='promotion.rejected',
            occurred_at='2026-08-23T12:00:00Z',
            promotion_id=None,
            correlation_id='correlation-rejected',
            operation_id=None,
            actor='dmitry',
            key_id=self.signer.key_id,
            repository='dimkox/adaptive-grok-build-pro',
            merged_commit_sha=sha('a'),
            artifact_sha256=digest('b'),
            target_environment='production',
            policy_epoch=digest('c'),
            outcome='rejected',
            reason_code='signature_invalid',
            details={'http_status': 401},
        )
        self.store.record_promotion_rejection(event)
        self.assertEqual(self.store._promotion_events, [event])
        with self.assertRaises(ValueError):
            self.store.record_promotion_rejection(replace(event, event_type='promotion.accepted'))


if __name__ == "__main__":
    unittest.main()
