from datetime import datetime, timezone
from types import MappingProxyType
import unittest

from adaptive_factory.api import _json
from adaptive_factory.models import (
    FactoryAttemptV1,
    FactoryEventV1,
    FactoryRunV1,
    FactoryTaskV1,
    RunRole,
    RunStatus,
    TaskProjection,
    TaskStatus,
)


NOW = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)


class ImmutableSnapshotTests(unittest.TestCase):
    def test_task_projection_is_a_compatibility_alias_for_versioned_task_snapshot(self):
        self.assertIs(TaskProjection, FactoryTaskV1)
        task = FactoryTaskV1(
            "00000000-0000-0000-0000-000000000001",
            "owner/repository",
            TaskStatus.QUEUED,
            1,
            "a" * 64,
            "b" * 64,
            NOW,
        )
        with self.assertRaisesRegex(Exception, "cannot assign"):
            task.status = TaskStatus.LEASED

    def test_run_and_attempt_snapshots_are_frozen_and_typed(self):
        run = FactoryRunV1(
            run_id="00000000-0000-0000-0000-000000000002",
            task_id="00000000-0000-0000-0000-000000000001",
            owner="worker-1",
            role=RunRole.WRITER,
            packet_digest="b" * 64,
            fence=2,
            status=RunStatus.LEASED,
            lease_expires_at=NOW,
            deadline_at=NOW,
            created_at=NOW,
            released_at=None,
        )
        attempt = FactoryAttemptV1(
            attempt_id="00000000-0000-0000-0000-000000000003",
            task_id=run.task_id,
            run_id=run.run_id,
            attempt_no=2,
            failure_class=None,
            failure_code=None,
            failure_digest=None,
            created_at=NOW,
            finished_at=None,
        )
        self.assertEqual(run.status, RunStatus.LEASED)
        self.assertEqual(attempt.attempt_no, 2)
        with self.assertRaisesRegex(Exception, "cannot assign"):
            run.fence = 3
        with self.assertRaisesRegex(Exception, "cannot assign"):
            attempt.attempt_no = 3

    def test_event_metadata_is_deeply_frozen_but_json_serializable(self):
        source = {
            "from_state": "leased",
            "target": "analyzing",
            "nested": {"labels": ["one", {"name": "two"}]},
        }
        event = FactoryEventV1(
            event_id="00000000-0000-0000-0000-000000000004",
            task_id="00000000-0000-0000-0000-000000000001",
            event_sequence=4,
            idempotency_key="c" * 64,
            actor_id="worker-1",
            action="phase_transitioned",
            metadata=source,
            mandatory_cleanup=False,
            created_at=NOW,
        )
        source["nested"]["labels"].append("late")
        self.assertIsInstance(event.metadata, MappingProxyType)
        self.assertIsInstance(event.metadata["nested"], MappingProxyType)
        self.assertEqual(event.metadata["nested"]["labels"], ("one", MappingProxyType({"name": "two"})))
        with self.assertRaisesRegex(Exception, "cannot assign"):
            event.action = "changed"
        with self.assertRaises(TypeError):
            event.metadata["target"] = "implementing"
        with self.assertRaises(TypeError):
            event.metadata["nested"]["labels"][1]["name"] = "changed"
        self.assertEqual(
            _json(event)["metadata"],
            {
                "from_state": "leased",
                "target": "analyzing",
                "nested": {"labels": ["one", {"name": "two"}]},
            },
        )


if __name__ == "__main__":
    unittest.main()
