from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
import unittest
import uuid

from adaptive_factory.migrations import PostgresMigrator
from adaptive_factory.models import Actor, FailureClass, RunRole, TaskStatus
from adaptive_factory.service import FactoryService
from adaptive_factory.store import BudgetError, FenceError, PostgresFactoryStore
from factory.tests.test_contracts import valid_intake


DATABASE_URL = os.environ.get("FACTORY_TEST_DATABASE_URL")
NOW = datetime.now(timezone.utc).replace(microsecond=0)
OPERATOR = Actor("operator", "operator", frozenset({"task:submit", "task:cancel", "factory:kill", "factory:reconcile"}), frozenset({"*"}))
WORKER = Actor("worker", "worker", frozenset({"task:claim", "task:heartbeat", "task:release", "task:budget"}), frozenset({"*"}))


@unittest.skipUnless(DATABASE_URL, "FACTORY_TEST_DATABASE_URL must name a disposable database")
class PostgresFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        PostgresMigrator(DATABASE_URL).apply()

    def setUp(self):
        import psycopg
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("TRUNCATE factory.audit_log, factory.audit_heads, factory.task_events, factory.budget_reservations, factory.usage_observations, factory.capacity_allocations, factory.attempts, factory.runs, factory.lease_sequences, factory.kill_switches, factory.reconciliation_runs, factory.tasks, factory.accepted_intents, factory.intake_identities RESTART IDENTITY")
            cursor.execute("UPDATE factory.capacity_counters SET active_count=0")
        self.store = PostgresFactoryStore(DATABASE_URL)
        self.service = FactoryService(self.store)

    def payload(self, repository="owner/repository", source=None):
        value = valid_intake()
        value["repository_id"] = repository
        value["source_id"] = source or str(uuid.uuid4())
        value["m0_authority"]["observed_at"] = NOW.isoformat()
        return value

    def submit(self, repository="owner/repository", source=None):
        return self.service.intake(self.payload(repository, source), actor=OPERATOR, now=NOW)

    def test_duplicate_and_changed_intake_are_atomic_and_immutable(self):
        payload = self.payload(source="same-source")
        first = self.service.intake(payload, actor=OPERATOR, now=NOW)
        duplicate = self.service.intake(payload, actor=OPERATOR, now=NOW)
        changed = self.payload(source="same-source"); changed["source_digest"] = "8" * 64
        replacement = self.service.intake(changed, actor=OPERATOR, now=NOW)
        self.assertTrue(first.created); self.assertFalse(duplicate.created)
        self.assertEqual(first.task.task_id, duplicate.task.task_id)
        self.assertNotEqual(first.task.task_id, replacement.task.task_id)
        self.assertEqual(self.store.get_task(first.task.task_id).status, TaskStatus.SUPERSEDED)

    def test_two_workers_get_one_task_and_late_fence_is_rejected(self):
        self.submit()
        def claim(index):
            return self.service.claim(owner=f"worker-{index}", role=RunRole.READER, repositories=("owner/repository",), lease_seconds=30, actor=WORKER, now=NOW)
        with ThreadPoolExecutor(max_workers=2) as pool:
            grants = list(pool.map(claim, range(2)))
        live = [grant for grant in grants if grant]
        self.assertEqual(len(live), 1)
        old = live[0]
        import psycopg
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (old.run_id,))
        self.service.reconcile(actor=OPERATOR, now=NOW)
        new = self.service.claim(owner="worker-new", role=RunRole.READER, repositories=("owner/repository",), lease_seconds=30, actor=WORKER, now=NOW)
        self.assertGreater(new.fence, old.fence)
        with self.assertRaises(FenceError):
            self.service.heartbeat(old, actor=WORKER, now=NOW)

    def test_reader_and_writer_capacity_is_enforced(self):
        for index in range(21): self.submit(repository="repo/a" if index < 11 else "repo/b")
        readers = []
        for index in range(30):
            grant = self.service.claim(owner=f"reader-{index}", role=RunRole.READER, repositories=("repo/a", "repo/b"), lease_seconds=60, actor=WORKER, now=NOW)
            if grant: readers.append(grant)
        self.assertEqual(len(readers), 20)
        self.assertEqual(sum(self.store.get_task(grant.task_id).repository_id == "repo/a" for grant in readers), 10)
        for grant in readers: self.service.release(grant, outcome="completed", actor=WORKER, now=NOW)
        for index in range(2): self.submit(repository="repo/w", source=f"writer-{index}")
        first = self.service.claim(owner="writer-1", role=RunRole.WRITER, repositories=("repo/w",), lease_seconds=60, actor=WORKER, now=NOW)
        second = self.service.claim(owner="writer-2", role=RunRole.WRITER, repositories=("repo/w",), lease_seconds=60, actor=WORKER, now=NOW)
        self.assertIsNotNone(first); self.assertIsNone(second)

    def test_retry_budget_kill_and_reconcile_fail_closed(self):
        task = self.submit().task
        for attempt in range(1, 4):
            grant = self.service.claim(owner=f"worker-{attempt}", role=RunRole.READER, repositories=(task.repository_id,), lease_seconds=30, actor=WORKER, now=NOW)
            self.service.release(grant, outcome=FailureClass.WORKER_LOST, actor=WORKER, now=NOW)
        self.assertEqual(self.store.get_task(task.task_id).status, TaskStatus.DEAD)

        task = self.submit(source="budget").task
        grant = self.service.claim(owner="budget-worker", role=RunRole.READER, repositories=(task.repository_id,), lease_seconds=30, actor=WORKER, now=NOW)
        self.service.reserve_budget(grant, cost_usd_micros=25_000_000, token_units=2_000_000, wall_seconds=30, reason_digest="a" * 64, idempotency_key="b" * 64, actor=WORKER)
        with self.assertRaises(BudgetError):
            self.service.reserve_budget(grant, cost_usd_micros=1, token_units=0, wall_seconds=0, reason_digest="c" * 64, idempotency_key="d" * 64, actor=WORKER)

        self.service.set_kill(scope_key="global", enabled=True, reason="operator-stop", idempotency_key="e" * 64, actor=OPERATOR, now=NOW)
        self.submit(source="killed")
        self.assertIsNone(self.service.claim(owner="blocked", role=RunRole.READER, repositories=("owner/repository",), lease_seconds=30, actor=WORKER, now=NOW))


if __name__ == "__main__":
    unittest.main()
