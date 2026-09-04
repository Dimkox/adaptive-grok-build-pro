from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import threading
import unittest

from adaptive_factory.recovery import (
    ExecutionRecovery,
    ExecutionRecoveryCandidate,
    ExecutionRecoveryClaim,
    ExecutionRecoveryCursor,
    ExecutionRecoveryNotDue,
    ExecutionRecoveryPage,
)
from adaptive_factory.models import Actor
from adaptive_factory.store import AuthorityError, PostgresFactoryStore, StoreError
from adaptive_factory.workspace import (
    FakeWorkspaceBroker,
    WorkspaceHandle,
    WorkspacePolicy,
    WorkspaceReleaseOutcome,
)


NOW = datetime(2026, 9, 2, 1, 0, tzinfo=timezone.utc)
RECOVERY_ACTOR = Actor(
    "factory-recovery", "operator", frozenset({"factory:reconcile"}), frozenset({"*"})
)


def candidate(number: int) -> ExecutionRecoveryCandidate:
    return ExecutionRecoveryCandidate(
        task_id=f"00000000-0000-0000-0000-{number:012d}",
        run_id=f"10000000-0000-0000-0000-{number:012d}",
        manifest_digest=f"{number:064x}"[-64:],
        workspace_handle="workspace:" + f"{number:064x}"[-64:],
        updated_at=NOW + timedelta(seconds=number),
    )


def policy() -> WorkspacePolicy:
    return WorkspacePolicy(("factory/src",), ("read", "write"), ("LANG",), ())


class RecordingRecoveryStore:
    def __init__(self, values, calls=None):
        self.values = tuple(values)
        self.terminal = set()
        self.cleaned = set()
        self.fail_terminal_once = set()
        self.cleanup_failures = []
        self.active_claims = {}
        self.claim_fences = {}
        self.pending_cancelled = set()
        self.not_due = set()
        self.fail_cleanup_success_once = set()
        self.calls = calls if calls is not None else []
        self.lock = threading.Lock()

    def execution_recovery_candidates(self, *, limit, cursor):
        self.calls.append(("scan", limit, cursor))
        fresh = [
            replace(value, source="fresh")
            for value in self.values
            if value.run_id not in self.cleaned
            and value.run_id not in self.terminal
            and (cursor is None or value.cursor > cursor)
        ]
        retries = [
            replace(value, source="cleanup_retry")
            for value in self.values
            if value.run_id not in self.cleaned and value.run_id in self.terminal
        ]
        fresh.sort(key=lambda value: value.cursor)
        retries.sort(key=lambda value: value.cursor)
        fresh_count = len(fresh)
        selected = []
        if fresh:
            selected.append(fresh.pop(0))
        if retries:
            selected.append(retries.pop(0))
        selected.extend(sorted(fresh + retries, key=lambda value: value.cursor))
        selected = tuple(selected[:limit])
        selected_fresh = tuple(
            value.cursor for value in selected if value.source == "fresh"
        )
        return ExecutionRecoveryPage(
            selected,
            max(selected_fresh) if selected_fresh else None,
            len(selected_fresh) == fresh_count,
        )

    def claim_execution_recovery(self, value, actor, *, timeout_seconds=5.0):
        with self.lock:
            if actor != RECOVERY_ACTOR:
                raise RuntimeError("invalid recovery actor")
            self.calls.append(("claim", value.run_id))
            if value.run_id in self.not_due:
                return ExecutionRecoveryNotDue(value)
            if value.run_id in self.fail_terminal_once:
                self.fail_terminal_once.remove(value.run_id)
                return None
            if value.run_id in self.active_claims:
                return None
            transition = "cleanup_retry"
            if value.run_id not in self.terminal:
                self.terminal.add(value.run_id)
                transition = (
                    "cancelled"
                    if value.run_id in self.pending_cancelled
                    else "orphaned"
                )
            fence = self.claim_fences.get(value.run_id, 0) + 1
            self.claim_fences[value.run_id] = fence
            claim = ExecutionRecoveryClaim(
                candidate=value,
                claim_token=f"20000000-0000-0000-0000-{fence:012d}",
                claim_fence=fence,
                claim_expires_at=NOW + timedelta(seconds=30),
                transition=transition,
                advances_discovery_cursor=(
                    transition == "orphaned"
                    and value.run_id not in self.pending_cancelled
                ),
            )
            self.active_claims[value.run_id] = claim
            return claim

    def record_execution_cleanup_success(self, claim, *, timeout_seconds=5.0):
        self.calls.append(("cleanup_succeeded", claim.candidate.run_id))
        if claim.candidate.run_id in self.fail_cleanup_success_once:
            self.fail_cleanup_success_once.remove(claim.candidate.run_id)
            raise RuntimeError("database-unavailable")
        with self.lock:
            if self.active_claims.get(claim.candidate.run_id) != claim:
                raise RuntimeError("stale-cleanup-claim")
            self.cleaned.add(claim.candidate.run_id)
            self.active_claims.pop(claim.candidate.run_id)

    def record_execution_cleanup_failure(self, claim, *, timeout_seconds=5.0):
        run_id = claim.candidate.run_id
        self.calls.append(("cleanup_failed", run_id, "workspace_cleanup_failed"))
        with self.lock:
            if self.active_claims.get(run_id) != claim:
                raise RuntimeError("stale-cleanup-claim")
            self.cleanup_failures.append(run_id)
            self.active_claims.pop(run_id)

    def expire_claim(self, run_id):
        with self.lock:
            self.active_claims.pop(run_id, None)


class FailingWorkspace:
    def __init__(self, delegate, failed_run, calls):
        self.delegate = delegate
        self.failed_run = failed_run
        self.failed = True
        self.calls = calls

    def release(self, handle, *, timeout_seconds):
        self.calls.append(("release", handle.run_id))
        if self.failed and handle.run_id == self.failed_run:
            raise RuntimeError("provider-secret-shaped-raw-exception")
        return self.delegate.release(handle, timeout_seconds=timeout_seconds)


class BlockingWorkspace:
    def __init__(self, delegate):
        self.delegate = delegate
        self.entered = threading.Event()
        self.resume = threading.Event()
        self.calls = 0

    def release(self, handle, *, timeout_seconds):
        self.calls += 1
        self.entered.set()
        if not self.resume.wait(timeout=2):
            raise RuntimeError("test release barrier timed out")
        return self.delegate.release(handle, timeout_seconds=timeout_seconds)


class ExpiringWorkspace:
    def __init__(self, delegate):
        self.delegate = delegate
        self.first_entered = threading.Event()
        self.resume_first = threading.Event()
        self.calls = 0
        self.outcomes = []

    def release(self, handle, *, timeout_seconds):
        self.calls += 1
        if self.calls == 1:
            self.first_entered.set()
            if not self.resume_first.wait(timeout=2):
                raise RuntimeError("test expiry barrier timed out")
        outcome = self.delegate.release(
            handle, timeout_seconds=timeout_seconds
        )
        self.outcomes.append(outcome)
        return outcome


class InvalidReleaseWorkspace:
    def __init__(self, outcome):
        self.outcome = outcome

    def release(self, _handle, *, timeout_seconds):
        return self.outcome


class RecoveryTests(unittest.TestCase):
    def registered(self, *values):
        broker = FakeWorkspaceBroker()
        for value in values:
            broker.register(
                WorkspaceHandle(value.task_id, value.run_id, value.workspace_handle),
                policy(),
            )
        return broker

    def test_limit_and_cursor_contract_are_closed(self):
        store = RecordingRecoveryStore(())
        recovery = ExecutionRecovery(store, FakeWorkspaceBroker(), RECOVERY_ACTOR)
        for invalid in (0, 1, 101, True, "1"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                recovery.reconcile(limit=invalid)
        with self.assertRaises(ValueError):
            ExecutionRecoveryCursor(NOW.replace(tzinfo=None), candidate(1).run_id)
        with self.assertRaises(ValueError):
            ExecutionRecoveryCursor(NOW, "not-a-run-id")
        duplicated = candidate(99)
        with self.assertRaisesRegex(ValueError, "invalid_recovery_page"):
            ExecutionRecoveryPage(
                (
                    duplicated,
                    replace(duplicated, source="cleanup_retry"),
                ),
                duplicated.cursor,
                False,
            )
        with self.assertRaisesRegex(ValueError, "invalid_recovery_page"):
            ExecutionRecoveryPage(
                (
                    duplicated,
                    replace(
                        candidate(98),
                        manifest_digest=duplicated.manifest_digest,
                    ),
                ),
                max(duplicated.cursor, candidate(98).cursor),
                False,
            )
        for repositories in (frozenset(), frozenset({"repository-a"})):
            with self.subTest(repositories=repositories), self.assertRaisesRegex(
                ValueError, "invalid_recovery_actor"
            ):
                ExecutionRecovery(
                    store,
                    FakeWorkspaceBroker(),
                    Actor(
                        "scoped-operator",
                        "operator",
                        frozenset({"factory:reconcile"}),
                        repositories,
                    ),
                )
            with self.subTest(store_repositories=repositories), self.assertRaises(
                AuthorityError
            ):
                PostgresFactoryStore(
                    "postgresql://must-not-connect.invalid/test"
                ).claim_execution_recovery(
                    candidate(1),
                    Actor(
                        "scoped-operator",
                        "operator",
                        frozenset({"factory:reconcile"}),
                        repositories,
                    ),
                )
        for invalid_timeout in (True, 0, 2.999, float("nan"), float("inf")):
            with self.subTest(timeout=invalid_timeout), self.assertRaises(StoreError):
                PostgresFactoryStore(
                    "postgresql://must-not-connect.invalid/test"
                ).claim_execution_recovery(
                    candidate(1),
                    RECOVERY_ACTOR,
                    timeout_seconds=invalid_timeout,
                )
        for database_url in (
            "host=database-a,database-b dbname=factory",
            "hostaddr=127.0.0.1,127.0.0.2 dbname=factory",
            "dbname=factory",
            "service=factory",
        ):
            invalid_store = PostgresFactoryStore(database_url)
            valid_candidate = candidate(97)
            valid_claim = ExecutionRecoveryClaim(
                valid_candidate,
                "20000000-0000-0000-0000-000000000097",
                1,
                NOW + timedelta(seconds=30),
                "orphaned",
                True,
            )
            operations = (
                lambda: invalid_store.execution_recovery_candidates(
                    limit=2, cursor=None
                ),
                lambda: invalid_store.claim_execution_recovery(
                    valid_candidate, RECOVERY_ACTOR
                ),
                lambda: invalid_store.record_execution_cleanup_success(valid_claim),
                lambda: invalid_store.record_execution_cleanup_failure(valid_claim),
            )
            for operation in operations:
                with self.subTest(
                    database_url=database_url, operation=operation
                ), self.assertRaisesRegex(StoreError, "single database host"):
                    operation()

    def test_cleanup_failure_is_durable_and_permits_discovery_wrap(self):
        first, blocked, later = candidate(1), candidate(2), candidate(3)
        calls = []
        store = RecordingRecoveryStore((later, blocked, first), calls)
        workspace = FailingWorkspace(
            self.registered(first, blocked, later), blocked.run_id, calls
        )
        result = ExecutionRecovery(store, workspace, RECOVERY_ACTOR).reconcile(limit=3)

        self.assertEqual(
            (
                result.candidates,
                result.orphaned,
                result.cleanup_failed,
                result.terminalize_failed,
            ),
            (3, 3, 1, 0),
        )
        self.assertIsNone(result.cursor)
        self.assertEqual(store.terminal, {first.run_id, blocked.run_id, later.run_id})
        self.assertEqual(store.cleanup_failures, [blocked.run_id])
        self.assertNotIn("provider-secret", repr(result))
        for value in (first, later):
            self.assertLess(
                calls.index(("claim", value.run_id)),
                calls.index(("release", value.run_id)),
            )
            self.assertLess(
                calls.index(("release", value.run_id)),
                calls.index(("cleanup_succeeded", value.run_id)),
            )
        self.assertLess(
            calls.index(("claim", blocked.run_id)),
            calls.index(("release", blocked.run_id)),
        )
        self.assertLess(
            calls.index(("release", blocked.run_id)),
            calls.index(("cleanup_failed", blocked.run_id, "workspace_cleanup_failed")),
        )

        workspace.failed = False
        replay = ExecutionRecovery(store, workspace, RECOVERY_ACTOR).reconcile(
            limit=3, cursor=result.cursor
        )
        self.assertEqual((replay.candidates, replay.orphaned), (1, 0))
        self.assertIsNone(replay.cursor)
        self.assertEqual(
            ExecutionRecovery(store, workspace, RECOVERY_ACTOR)
            .reconcile(limit=3, cursor=replay.cursor)
            .candidates,
            0,
        )

    def test_cleanup_outcome_write_failure_is_reported_as_terminalize_failure(self):
        value = candidate(76)

        class OutcomeFailingStore(RecordingRecoveryStore):
            def record_execution_cleanup_failure(
                self, claim, *, timeout_seconds=5.0
            ):
                raise RuntimeError("database-unavailable")

        store = OutcomeFailingStore((value,))
        workspace = FailingWorkspace(
            self.registered(value), value.run_id, store.calls
        )
        result = ExecutionRecovery(store, workspace, RECOVERY_ACTOR).reconcile(
            limit=2
        )

        self.assertEqual(
            (result.orphaned, result.cleanup_failed, result.terminalize_failed),
            (1, 1, 1),
        )

    def test_terminalization_failure_retries_after_idempotent_cleanup(self):
        value = candidate(4)
        store = RecordingRecoveryStore((value,))
        store.fail_terminal_once.add(value.run_id)
        workspace = self.registered(value)
        recovery = ExecutionRecovery(store, workspace, RECOVERY_ACTOR)

        first = recovery.reconcile(limit=2)
        self.assertEqual(
            (first.orphaned, first.terminalize_failed, first.cursor), (0, 1, None)
        )
        self.assertEqual(
            [call for call in store.calls if call[0] == "release"], []
        )
        second = recovery.reconcile(limit=2, cursor=first.cursor)
        self.assertEqual((second.orphaned, second.terminalize_failed), (1, 0))
        self.assertEqual(
            [call for call in store.calls if call[0] == "claim"],
            [
                ("claim", value.run_id),
                ("claim", value.run_id),
            ],
        )
        self.assertEqual(
            [call for call in store.calls if call[0] == "cleanup_succeeded"],
            [("cleanup_succeeded", value.run_id)],
        )

    def test_live_cleanup_claim_allows_only_one_broker_call_before_expiry(self):
        value = candidate(5)
        store = RecordingRecoveryStore((value,))
        workspace = BlockingWorkspace(self.registered(value))
        recovery = ExecutionRecovery(store, workspace, RECOVERY_ACTOR)

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(recovery.reconcile, limit=2)
            self.assertTrue(workspace.entered.wait(timeout=2))
            second = executor.submit(recovery.reconcile, limit=2).result(timeout=2)
            self.assertEqual((second.orphaned, second.terminalize_failed), (0, 1))
            self.assertEqual(workspace.calls, 1)
            workspace.resume.set()
            self.assertEqual(first.result(timeout=2).orphaned, 1)

        self.assertEqual(workspace.calls, 1)
        self.assertEqual(store.cleaned, {value.run_id})

    def test_expired_claim_allows_idempotent_at_least_once_release(self):
        value = candidate(8)
        store = RecordingRecoveryStore((value,))
        workspace = ExpiringWorkspace(self.registered(value))
        recovery = ExecutionRecovery(store, workspace, RECOVERY_ACTOR)

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(recovery.reconcile, limit=2)
            self.assertTrue(workspace.first_entered.wait(timeout=2))
            store.expire_claim(value.run_id)
            second = executor.submit(recovery.reconcile, limit=2).result(timeout=2)
            self.assertEqual((second.orphaned, second.cleanup_failed), (0, 0))
            workspace.resume_first.set()
            self.assertEqual(first.result(timeout=2).cleanup_failed, 1)

        self.assertEqual(workspace.calls, 2)
        self.assertEqual(
            {outcome.status for outcome in workspace.outcomes},
            {"released", "already_absent"},
        )
        self.assertEqual(store.claim_fences[value.run_id], 2)
        self.assertEqual(store.cleaned, {value.run_id})

    def test_crash_after_release_retries_absent_with_a_new_claim(self):
        value = candidate(6)
        store = RecordingRecoveryStore((value,))
        store.fail_cleanup_success_once.add(value.run_id)
        workspace = self.registered(value)
        recovery = ExecutionRecovery(store, workspace, RECOVERY_ACTOR)

        first = recovery.reconcile(limit=2)
        self.assertEqual((first.orphaned, first.cleanup_failed), (1, 1))
        self.assertNotIn(value.run_id, store.cleaned)

        store.expire_claim(value.run_id)
        second = recovery.reconcile(limit=2, cursor=value.cursor)
        self.assertEqual((second.orphaned, second.cleanup_failed), (0, 0))
        self.assertEqual(store.claim_fences[value.run_id], 2)
        self.assertEqual(store.cleaned, {value.run_id})

    def test_release_outcome_is_closed_and_provider_neutral(self):
        value = candidate(7)
        for invalid in ("released", "fake_released", object()):
            with self.subTest(invalid=invalid):
                store = RecordingRecoveryStore((value,))
                result = ExecutionRecovery(
                    store, InvalidReleaseWorkspace(invalid), RECOVERY_ACTOR
                ).reconcile(limit=2)
                self.assertEqual((result.cleanup_failed, result.orphaned), (1, 1))
                self.assertEqual(store.cleanup_failures, [value.run_id])
        for status in ("released", "already_absent"):
            with self.subTest(status=status):
                store = RecordingRecoveryStore((value,))
                result = ExecutionRecovery(
                    store,
                    InvalidReleaseWorkspace(WorkspaceReleaseOutcome(status)),
                    RECOVERY_ACTOR,
                ).reconcile(limit=2)
                self.assertEqual((result.cleanup_failed, result.orphaned), (0, 1))
                self.assertEqual(store.cleaned, {value.run_id})

        with self.assertRaisesRegex(Exception, "workspace_release_outcome"):
            WorkspaceReleaseOutcome("unknown")

    def test_cleanup_retry_older_than_discovery_cursor_never_regresses_cursor(self):
        old = candidate(2)
        newer_cursor = candidate(10).cursor
        store = RecordingRecoveryStore((old,))
        store.terminal.add(old.run_id)
        workspace = self.registered(old)

        result = ExecutionRecovery(store, workspace, RECOVERY_ACTOR).reconcile(
            limit=2, cursor=newer_cursor
        )

        self.assertEqual(result.orphaned, 0)
        self.assertIsNone(result.cursor)
        self.assertEqual(store.cleaned, {old.run_id})

    def test_pending_cancel_job_cannot_advance_past_unseen_fresh_manifest(self):
        first, middle, pending_cancel = candidate(1), candidate(5), candidate(9)

        class PagedStore(RecordingRecoveryStore):
            def __init__(self):
                super().__init__((first, middle, pending_cancel))
                self.pages = [(first, pending_cancel), (middle,)]

            def execution_recovery_candidates(self, *, limit, cursor):
                self.calls.append(("scan", limit, cursor))
                values = self.pages.pop(0) if self.pages else ()
                candidates = tuple(
                    replace(
                        value,
                        source=(
                            "cleanup_retry"
                            if value.run_id in self.pending_cancelled
                            else "fresh"
                        ),
                    )
                    for value in values
                )
                fresh = tuple(
                    value for value in candidates if value.source == "fresh"
                )
                return ExecutionRecoveryPage(
                    candidates,
                    max((value.cursor for value in fresh), default=None),
                    not bool(self.pages),
                )

        store = PagedStore()
        store.pending_cancelled.add(pending_cancel.run_id)
        workspace = self.registered(first, middle, pending_cancel)
        first_page = ExecutionRecovery(
            store, workspace, RECOVERY_ACTOR
        ).reconcile(limit=2)
        self.assertEqual(first_page.cursor, first.cursor)
        second_page = ExecutionRecovery(
            store, workspace, RECOVERY_ACTOR
        ).reconcile(limit=2, cursor=first_page.cursor)
        self.assertIsNone(second_page.cursor)

    def test_raw_pages_advance_across_healthy_rows_wrap_and_revisit_expiry(self):
        values = tuple(candidate(number) for number in range(1, 104))
        store = RecordingRecoveryStore(values)
        store.not_due.update(value.run_id for value in values)
        workspace = self.registered(values[49])
        recovery = ExecutionRecovery(store, workspace, RECOVERY_ACTOR)

        first = recovery.reconcile(limit=100)
        self.assertEqual(first.cursor, values[99].cursor)
        self.assertEqual(first.orphaned, 0)
        second = recovery.reconcile(limit=100, cursor=first.cursor)
        self.assertIsNone(second.cursor)
        self.assertEqual(second.candidates, 3)

        store.not_due.remove(values[49].run_id)
        revisited = recovery.reconcile(limit=100, cursor=second.cursor)
        self.assertEqual(revisited.orphaned, 1)
        self.assertEqual(revisited.cursor, values[99].cursor)
        self.assertIn(values[49].run_id, store.cleaned)

    def test_each_bounded_page_reserves_fresh_and_retry_lanes(self):
        fresh, retry = candidate(20), candidate(21)
        store = RecordingRecoveryStore((fresh, retry))
        store.not_due.add(fresh.run_id)
        store.terminal.add(retry.run_id)
        result = ExecutionRecovery(
            store, self.registered(retry), RECOVERY_ACTOR
        ).reconcile(limit=2)

        self.assertEqual(result.candidates, 2)
        self.assertEqual(store.cleaned, {retry.run_id})
        self.assertIn(("claim", fresh.run_id), store.calls)
        self.assertIn(("claim", retry.run_id), store.calls)

    def test_fresh_contention_stops_that_lane_but_not_retry_cleanup(self):
        blocked, later, retry = candidate(30), candidate(31), candidate(32)
        store = RecordingRecoveryStore((blocked, later, retry))
        store.fail_terminal_once.add(blocked.run_id)
        store.terminal.add(retry.run_id)
        result = ExecutionRecovery(
            store, self.registered(retry), RECOVERY_ACTOR
        ).reconcile(limit=3)

        self.assertEqual(result.terminalize_failed, 1)
        self.assertIn(("claim", retry.run_id), store.calls)
        self.assertNotIn(("claim", later.run_id), store.calls)
        self.assertIn(retry.run_id, store.cleaned)

    def test_monotonic_budget_returns_processed_prefix_and_resumes(self):
        values = tuple(candidate(number) for number in range(40, 70))

        class Clock:
            value = 0.0

            def __call__(self):
                return self.value

        clock = Clock()

        class LatencyStore(RecordingRecoveryStore):
            def execution_recovery_candidates(self, *, limit, cursor):
                clock.value += 5.0
                return super().execution_recovery_candidates(
                    limit=limit, cursor=cursor
                )

            def claim_execution_recovery(
                self, value, actor, *, timeout_seconds=5.0
            ):
                self.calls.append(("claim_timeout", timeout_seconds))
                if timeout_seconds != 3.0:
                    raise AssertionError("recovery claim was not tightly bounded")
                self.not_due.add(value.run_id)
                clock.value += 3.0
                return super().claim_execution_recovery(
                    value, actor, timeout_seconds=timeout_seconds
                )

        store = LatencyStore(values)
        recovery = ExecutionRecovery(
            store, FakeWorkspaceBroker(), RECOVERY_ACTOR, monotonic=clock
        )
        first_started = clock.value
        first = recovery.reconcile(limit=30)
        self.assertEqual((first.candidates, first.cursor), (5, values[4].cursor))
        self.assertLessEqual(clock.value - first_started, 30)
        second_started = clock.value
        second = recovery.reconcile(limit=30, cursor=first.cursor)
        self.assertEqual((second.candidates, second.cursor), (5, values[9].cursor))
        self.assertLessEqual(clock.value - second_started, 30)

    def test_broker_timeout_is_bounded_and_leaves_durable_retry(self):
        value = candidate(75)
        clock = type("Clock", (), {"value": 0.0, "__call__": lambda self: self.value})()

        class BoundedStore(RecordingRecoveryStore):
            def execution_recovery_candidates(self, *, limit, cursor):
                clock.value += 5.0
                return super().execution_recovery_candidates(
                    limit=limit, cursor=cursor
                )

            def claim_execution_recovery(
                self, candidate, actor, *, timeout_seconds=5.0
            ):
                self.calls.append(("claim_timeout", timeout_seconds))
                clock.value += 3.0
                return super().claim_execution_recovery(
                    candidate, actor, timeout_seconds=timeout_seconds
                )

            def record_execution_cleanup_failure(
                self, claim, *, timeout_seconds=5.0
            ):
                self.calls.append(("failure_timeout", timeout_seconds))
                clock.value += 3.0
                return super().record_execution_cleanup_failure(
                    claim, timeout_seconds=timeout_seconds
                )

        class TimeoutWorkspace:
            timeouts = []

            def release(self, _handle, *, timeout_seconds):
                self.timeouts.append(timeout_seconds)
                clock.value += timeout_seconds
                raise TimeoutError("bounded workspace release timeout")

        store = BoundedStore((value,))
        workspace = TimeoutWorkspace()
        result = ExecutionRecovery(
            store, workspace, RECOVERY_ACTOR, monotonic=clock
        ).reconcile(limit=2)

        self.assertEqual((result.orphaned, result.cleanup_failed), (1, 1))
        self.assertEqual(workspace.timeouts, [5.0])
        self.assertEqual(store.cleanup_failures, [value.run_id])
        self.assertIn(("claim_timeout", 3.0), store.calls)
        self.assertIn(("failure_timeout", 3.0), store.calls)
        self.assertLessEqual(clock.value, 30)


if __name__ == "__main__":
    unittest.main()
