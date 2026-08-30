from __future__ import annotations

import unittest
import uuid
from datetime import timedelta
from types import SimpleNamespace

from _support import digest, now, sha
from adaptive_trust_ci.metrics import collect_metrics, render_prometheus
from adaptive_trust_ci.models import JobRequest, PromotionEvent
from adaptive_trust_ci.provenance import MergedPullRequestFact, ReconciliationWatermark
from adaptive_trust_ci.store import MemoryStore


class MetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = MemoryStore()

    def request(self, pr_number: int, head: str) -> JobRequest:
        return JobRequest(
            repository='Dimkox/adaptive-grok-build-pro',
            pr_number=pr_number,
            base_sha=sha('a'),
            head_sha=sha(head),
            head_ref=f'feat/{pr_number}',
            base_ref='main',
        )

    def test_collects_low_cardinality_queue_and_terminal_metrics(self) -> None:
        queued, _ = self.store.enqueue(self.request(1, 'b'), digest('c'), 3, now=now())
        passed, _ = self.store.enqueue(self.request(2, 'd'), digest('c'), 3, now=now() + timedelta(seconds=10))
        claimed = self.store.claim('worker-1', 60, now=now() + timedelta(seconds=11))
        assert claimed is not None
        self.assertEqual(claimed.job_id, queued.job_id)
        self.store.mark_running(claimed.job_id, 'worker-1', now=now() + timedelta(seconds=12))
        self.store.finish(
            claimed.job_id,
            'worker-1',
            'passed',
            {},
            now=now() + timedelta(seconds=13),
        )
        snapshot = collect_metrics(
            self.store,
            now=now() + timedelta(seconds=30),
            stopped=False,
            policy_digest=digest('c'),
            check_name='adaptive-trust-ci/verified@cccccccccccc',
        )
        self.assertEqual(snapshot.job_counts['passed'], 1)
        self.assertEqual(snapshot.job_counts['queued'], 1)
        self.assertEqual(snapshot.expired_leases, 0)
        self.assertGreaterEqual(snapshot.oldest_queued_age_seconds, 20)
        text = render_prometheus(snapshot)
        self.assertIn('adaptive_trust_ci_jobs{status="passed"} 1', text)
        self.assertIn('adaptive_trust_ci_jobs{status="queued"} 1', text)
        self.assertIn('adaptive_trust_ci_kill_switch 0', text)
        self.assertIn('adaptive_trust_ci_policy_info{check_name="adaptive-trust-ci/verified@cccccccccccc",policy_epoch="cccccccccccc"} 1', text)
        self.assertNotIn('Dimkox', text)
        self.assertNotIn(passed.head_sha, text)
        self.assertNotIn(passed.job_id, text)

    def test_expired_lease_and_kill_switch_are_visible(self) -> None:
        self.store.enqueue(self.request(3, 'e'), digest('c'), 3, now=now())
        claimed = self.store.claim('worker-1', 5, now=now())
        assert claimed is not None
        snapshot = collect_metrics(
            self.store,
            now=now() + timedelta(seconds=6),
            stopped=True,
            policy_digest=digest('d'),
            check_name='adaptive-trust-ci/verified@dddddddddddd',
        )
        self.assertEqual(snapshot.expired_leases, 1)
        self.assertTrue(snapshot.stopped)
        text = render_prometheus(snapshot)
        self.assertIn('adaptive_trust_ci_expired_leases 1', text)
        self.assertIn('adaptive_trust_ci_kill_switch 1', text)

    def test_prometheus_renderer_escapes_label_values(self) -> None:
        snapshot = collect_metrics(
            self.store,
            now=now(),
            stopped=False,
            policy_digest=digest('a'),
            check_name='check"name\\line\nnext',
        )
        text = render_prometheus(snapshot)
        self.assertIn('check\\"name\\\\line\\nnext', text)

    def test_durable_promotion_consume_and_dependency_aggregates_are_bounded(self) -> None:
        promotion_one = str(uuid.uuid4())
        promotion_two = str(uuid.uuid4())
        operation = str(uuid.uuid4())

        def event(event_type, occurred_at, promotion_id, outcome, reason, operation_id=None):
            return PromotionEvent(
                schema_version=1,
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                occurred_at=occurred_at,
                promotion_id=promotion_id,
                correlation_id='metrics-correlation',
                operation_id=operation_id,
                actor='fixture',
                key_id='fixture-key',
                repository='dimkox/adaptive-grok-build-pro',
                merged_commit_sha=sha('a'),
                artifact_sha256=digest('b'),
                target_environment='production',
                policy_epoch=digest('c'),
                outcome=outcome,
                reason_code=reason,
                details={},
            )

        with self.store._lock:
            self.store._promotion_events.extend(
                (
                    event('promotion.accepted', '2026-08-23T11:55:00Z', promotion_one, 'accepted', 'accepted'),
                    event('promotion.accepted', '2026-08-23T11:56:00Z', promotion_two, 'accepted', 'accepted'),
                    event('promotion.consumed', '2026-08-23T11:58:00Z', promotion_two, 'consumed', 'consumed', operation),
                    event('promotion.rejected', '2026-08-23T11:59:00Z', None, 'rejected', 'authorization_unavailable'),
                )
            )
        snapshot = collect_metrics(
            self.store,
            now=now(),
            stopped=False,
            policy_digest=digest('c'),
            check_name='adaptive-trust-ci/verified@cccccccccccc',
        )
        self.assertEqual(snapshot.promotion_outcomes['accepted'], 2)
        self.assertEqual(snapshot.promotion_outcomes['rejected'], 1)
        self.assertEqual(snapshot.promotion_outcomes['consumed'], 1)
        self.assertEqual(snapshot.promotion_reasons['authorization_unavailable'], 1)
        self.assertEqual(snapshot.accepted_unconsumed, 1)
        self.assertEqual(snapshot.consumed_without_terminal, 1)
        self.assertEqual(snapshot.consumed_without_terminal_oldest_age_seconds, 120)
        text = render_prometheus(snapshot)
        self.assertIn('adaptive_trust_ci_promotion_decisions_total{outcome="accepted"} 2', text)
        self.assertIn('adaptive_trust_ci_promotion_reasons_total{reason="authorization_unavailable"} 1', text)
        self.assertIn('adaptive_trust_ci_promotions_accepted_unconsumed 1', text)
        self.assertIn('adaptive_trust_ci_consumed_without_terminal 1', text)
        for forbidden in (promotion_one, promotion_two, operation, sha('a'), digest('b')):
            self.assertNotIn(forbidden, text)

    def test_merge_reconciliation_protected_and_expired_metrics_are_durable_and_bounded(self) -> None:
        def fact(received_at, suffix):
            return MergedPullRequestFact.create(
                delivery_id=f'metrics-delivery-{suffix}',
                payload_sha256=digest(suffix),
                repository_id=101,
                repository='dimkox/adaptive-grok-build-pro',
                installation_id=42,
                pr_number=int(suffix, 16) + 1,
                head_sha=sha('a'),
                base_sha=sha('b'),
                protected_ref='refs/heads/main',
                merged_commit_sha=sha('c'),
                merged_at=(received_at - timedelta(seconds=10)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                received_at=received_at,
            )

        pending = fact(now() - timedelta(seconds=120), '1')
        passed = fact(now() - timedelta(seconds=90), '2')
        failed = fact(now() - timedelta(seconds=60), '3')
        for item in (pending, passed, failed):
            self.store.record_merge_fact(item)
        self.store.save_reconciliation_watermark(
            pending.repository,
            ReconciliationWatermark(
                updated_at=(now() - timedelta(seconds=75)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                pr_number=4,
            ),
        )
        expired_id = str(uuid.uuid4())
        with self.store._lock:
            self.store._merge_queue[passed.merge_fact_id]['status'] = 'completed'
            self.store._merge_queue[failed.merge_fact_id]['status'] = 'dead'
            self.store._protected_evidence[str(uuid.uuid4())] = SimpleNamespace()
            self.store._promotions[expired_id] = SimpleNamespace(
                accepted_at=now() - timedelta(minutes=10),
                envelope=SimpleNamespace(
                    payload=SimpleNamespace(
                        issued_at=(now() - timedelta(minutes=11)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                        expires_at=(now() - timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    )
                ),
            )

        snapshot = collect_metrics(
            self.store,
            now=now(),
            stopped=False,
            policy_digest=digest('c'),
            check_name='adaptive-trust-ci/verified@cccccccccccc',
        )

        self.assertEqual(getattr(snapshot, 'merge_facts_pending', None), 1)
        self.assertEqual(getattr(snapshot, 'merge_fact_oldest_pending_age_seconds', None), 120)
        self.assertEqual(getattr(snapshot, 'reconciliation_lag_seconds', None), 75)
        self.assertEqual(
            getattr(snapshot, 'protected_branch_validation_outcomes', None),
            {'passed': 1, 'failed': 1},
        )
        self.assertEqual(getattr(snapshot, 'expired_promotions', None), 1)
        rendered = render_prometheus(snapshot)
        self.assertIn('adaptive_trust_ci_merge_facts_pending 1', rendered)
        self.assertIn('adaptive_trust_ci_merge_fact_oldest_pending_age_seconds 120', rendered)
        self.assertIn('adaptive_trust_ci_reconciliation_lag_seconds 75', rendered)
        self.assertIn('adaptive_trust_ci_protected_branch_validations_total{outcome="passed"} 1', rendered)
        self.assertIn('adaptive_trust_ci_protected_branch_validations_total{outcome="failed"} 1', rendered)
        self.assertIn('adaptive_trust_ci_promotions_expired 1', rendered)
        for forbidden in (pending.merge_fact_id, pending.repository, expired_id):
            self.assertNotIn(forbidden, rendered)


if __name__ == '__main__':
    unittest.main()
