from datetime import datetime, timedelta, timezone
import unittest

from adaptive_factory.recovery import (
    ExecutionRecovery,
    ExecutionRecoveryCandidate,
    ExecutionRecoveryCursor,
)
from adaptive_factory.workspace import (
    FakeWorkspaceBroker,
    WorkspaceError,
    WorkspaceHandle,
    WorkspacePolicy,
)


NOW = datetime(2026, 9, 2, 1, 0, tzinfo=timezone.utc)


def candidate(number: int) -> ExecutionRecoveryCandidate:
    return ExecutionRecoveryCandidate(
        task_id=f"00000000-0000-0000-0000-{number:012d}",
        run_id=f"10000000-0000-0000-0000-{number:012d}",
        manifest_digest=f"{number:x}" * 64,
        workspace_handle="workspace:" + f"{number:x}" * 64,
        updated_at=NOW + timedelta(seconds=number),
    )


def policy() -> WorkspacePolicy:
    return WorkspacePolicy(("factory/src",), ("read", "write"), ("LANG",), ())


class RecordingRecoveryStore:
    def __init__(self, values, calls=None):
        self.values = tuple(values)
        self.terminal = set()
        self.fail_terminal_once = set()
        self.cleanup_failures = []
        self.calls = calls if calls is not None else []

    def execution_recovery_candidates(self, *, limit, cursor):
        self.calls.append(("scan", limit, cursor))
        values = [
            value for value in self.values
            if value.run_id not in self.terminal
            and (cursor is None or value.cursor > cursor)
        ]
        return tuple(sorted(values, key=lambda value: value.cursor)[:limit])

    def terminalize_execution_orphan(self, value):
        self.calls.append(("terminalize", value.run_id))
        if value.run_id in self.fail_terminal_once:
            self.fail_terminal_once.remove(value.run_id)
            return "not_eligible"
        if value.run_id in self.terminal:
            return "already_terminal"
        self.terminal.add(value.run_id)
        return "orphaned"

    def record_execution_cleanup_success(self, value):
        self.calls.append(("cleanup_succeeded", value.run_id))

    def record_execution_cleanup_failure(self, value):
        self.calls.append(("cleanup_failed", value.run_id, "workspace_cleanup_failed"))
        self.cleanup_failures.append(value.run_id)


class FailingWorkspace:
    def __init__(self, delegate, failed_run, calls):
        self.delegate = delegate
        self.failed_run = failed_run
        self.failed = True
        self.calls = calls

    def release(self, handle):
        self.calls.append(("release", handle.run_id))
        if self.failed and handle.run_id == self.failed_run:
            raise RuntimeError("provider-secret-shaped-raw-exception")
        return self.delegate.release(handle)


class RecoveryTests(unittest.TestCase):
    def registered(self, *values):
        broker = FakeWorkspaceBroker()
        for value in values:
            broker.register(
                WorkspaceHandle(value.task_id, value.run_id, value.workspace_handle), policy()
            )
        return broker

    def test_limit_and_cursor_contract_are_closed(self):
        store = RecordingRecoveryStore(())
        recovery = ExecutionRecovery(store, FakeWorkspaceBroker())
        for invalid in (0, 101, True, "1"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                recovery.reconcile(limit=invalid)
        with self.assertRaises(ValueError):
            ExecutionRecoveryCursor(NOW.replace(tzinfo=None), candidate(1).run_id)
        with self.assertRaises(ValueError):
            ExecutionRecoveryCursor(NOW, "not-a-run-id")

    def test_cleanup_failure_continues_page_without_advancing_past_retry(self):
        first, blocked, later = candidate(1), candidate(2), candidate(3)
        calls = []
        store = RecordingRecoveryStore((later, blocked, first), calls)
        workspace = FailingWorkspace(
            self.registered(first, blocked, later), blocked.run_id, calls,
        )
        result = ExecutionRecovery(store, workspace).reconcile(limit=3)

        self.assertEqual(
            (result.candidates, result.orphaned, result.cleanup_failed, result.terminalize_failed),
            (3, 2, 1, 0),
        )
        self.assertEqual(result.cursor, first.cursor)
        self.assertEqual(store.terminal, {first.run_id, later.run_id})
        self.assertEqual(store.cleanup_failures, [blocked.run_id])
        self.assertNotIn("provider-secret", repr(result))
        for value in (first, later):
            self.assertLess(
                calls.index(("release", value.run_id)),
                calls.index(("cleanup_succeeded", value.run_id)),
            )
            self.assertLess(
                calls.index(("cleanup_succeeded", value.run_id)),
                calls.index(("terminalize", value.run_id)),
            )

        workspace.failed = False
        replay = ExecutionRecovery(store, workspace).reconcile(
            limit=3, cursor=result.cursor,
        )
        self.assertEqual((replay.candidates, replay.orphaned), (1, 1))
        self.assertEqual(replay.cursor, blocked.cursor)
        self.assertEqual(
            ExecutionRecovery(store, workspace).reconcile(limit=3, cursor=replay.cursor).candidates,
            0,
        )

    def test_terminalization_failure_retries_after_idempotent_fake_cleanup(self):
        value = candidate(4)
        store = RecordingRecoveryStore((value,))
        store.fail_terminal_once.add(value.run_id)
        workspace = self.registered(value)
        recovery = ExecutionRecovery(store, workspace)

        first = recovery.reconcile(limit=1)
        self.assertEqual((first.orphaned, first.terminalize_failed, first.cursor), (0, 1, None))
        second = recovery.reconcile(limit=1, cursor=first.cursor)
        self.assertEqual((second.orphaned, second.terminalize_failed), (1, 0))
        self.assertEqual(
            [call for call in store.calls if call[0] == "terminalize"],
            [
                ("terminalize", value.run_id),
                ("terminalize", value.run_id),
            ],
        )
        self.assertEqual(
            [call for call in store.calls if call[0] == "cleanup_succeeded"],
            [("cleanup_succeeded", value.run_id)],
        )


if __name__ == "__main__":
    unittest.main()
