from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from pilot.store import PilotStore, PilotStoreError
from pilot.tests.support import issue_snapshot


class PilotRecoveryTests(unittest.TestCase):
    def test_interrupted_invocation_is_terminal_and_cannot_start_again(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state_root = Path(raw) / "state"
            control = Path(__file__).resolve().parents[2]
            issue = issue_snapshot()
            store = PilotStore(state_root, control_repository=control)
            store.create_or_replay(issue, command_key="submit-1")
            store.mark_workspace_ready(issue.job_id, workspace_digest="3" * 64)
            store.begin_invocation(issue.job_id, command_key="codex-1")
            store.close()

            recovered = PilotStore(state_root, control_repository=control)
            job = recovered.get(issue.job_id)
            self.assertEqual((job.state, job.reason_code), ("needs_human", "model_outcome_ambiguous"))
            with self.assertRaisesRegex(PilotStoreError, "attempt_consumed"):
                recovered.begin_invocation(issue.job_id, command_key="codex-2")
            recovered.close()


if __name__ == "__main__":
    unittest.main()
