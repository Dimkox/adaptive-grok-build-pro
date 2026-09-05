from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pilot.store import PilotStore, PilotStoreError
from pilot.tests.support import candidate_change, issue_snapshot, utc_time


class PilotStoreTests(unittest.TestCase):
    def test_replay_is_exact_and_candidate_survives_close_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state_root = root / "state"
            issue = issue_snapshot()
            store = PilotStore(
                state_root,
                control_repository=Path(__file__).resolve().parents[2],
                clock=lambda: utc_time(4),
            )
            job, created = store.create_or_replay(issue, command_key="submit-1")
            replay, replay_created = store.create_or_replay(issue, command_key="submit-1")
            self.assertTrue(created)
            self.assertFalse(replay_created)
            self.assertEqual(job, replay)
            job = store.mark_workspace_ready(issue.job_id, workspace_digest="3" * 64)
            job = store.begin_invocation(issue.job_id, command_key="codex-1")
            candidate = candidate_change(issue)
            job = store.store_candidate(issue.job_id, candidate)
            self.assertEqual(job.state, "candidate_sealed")
            store.close()

            reopened = PilotStore(
                state_root,
                control_repository=Path(__file__).resolve().parents[2],
                clock=lambda: utc_time(5),
            )
            self.assertEqual(reopened.get(issue.job_id).candidate, candidate)
            self.assertEqual(state_root.stat().st_mode & 0o777, 0o700)
            self.assertEqual(reopened.database_path.stat().st_mode & 0o777, 0o600)
            reopened.close()

    def test_conflicting_replay_and_tampered_record_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state_root = root / "state"
            issue = issue_snapshot()
            store = PilotStore(state_root, control_repository=Path(__file__).resolve().parents[2])
            store.create_or_replay(issue, command_key="submit-1")
            with self.assertRaisesRegex(PilotStoreError, "command_conflict"):
                store.create_or_replay(
                    issue_snapshot(body="different"), command_key="submit-1"
                )
            store.close()

            connection = sqlite3.connect(state_root / "pilot.sqlite3")
            connection.execute(
                "UPDATE jobs SET snapshot_json = ? WHERE job_id = ?",
                (b"{}", issue.job_id),
            )
            connection.commit()
            connection.close()
            reopened = PilotStore(state_root, control_repository=Path(__file__).resolve().parents[2])
            with self.assertRaises(PilotStoreError):
                reopened.get(issue.job_id)
            reopened.close()


if __name__ == "__main__":
    unittest.main()
