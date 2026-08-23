from __future__ import annotations

import unittest
from datetime import timedelta

from _support import digest, now, sha
from adaptive_trust_ci.metrics import collect_metrics, render_prometheus
from adaptive_trust_ci.models import JobRequest
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


if __name__ == '__main__':
    unittest.main()
