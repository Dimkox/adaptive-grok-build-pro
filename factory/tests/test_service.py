from datetime import datetime, timezone
import unittest

from adaptive_factory.models import Actor, RunRole
from adaptive_factory.service import AuthorizationError, FactoryService
from factory.tests.test_contracts import valid_intake


NOW = datetime(2026, 8, 31, 20, 0, tzinfo=timezone.utc)


class RecordingStore:
    def __init__(self):
        self.calls = []

    def intake(self, intake, actor, now):
        self.calls.append(("intake", intake, actor, now))
        return {"task_id": "task-1", "created": True}

    def claim(self, request, actor, now):
        self.calls.append(("claim", request, actor, now))
        return None


class ServiceTests(unittest.TestCase):
    def test_submit_requires_scope_and_repository_authorization(self):
        store = RecordingStore(); service = FactoryService(store)
        denied = Actor("caller", "client", frozenset(), frozenset({"owner/repository"}))
        cross_repo = Actor("caller", "client", frozenset({"task:submit"}), frozenset({"other/repository"}))
        for actor in (denied, cross_repo):
            with self.assertRaises(AuthorizationError):
                service.intake(valid_intake(), actor=actor, now=NOW)
        self.assertEqual(store.calls, [])

    def test_valid_submit_parses_before_store_boundary(self):
        store = RecordingStore(); service = FactoryService(store)
        actor = Actor("caller", "client", frozenset({"task:submit"}), frozenset({"owner/repository"}))
        result = service.intake(valid_intake(), actor=actor, now=NOW)
        self.assertTrue(result["created"])
        self.assertEqual(store.calls[0][1].repository_id, "owner/repository")

    def test_claim_rejects_unbounded_lease_and_missing_worker_scope(self):
        store = RecordingStore(); service = FactoryService(store)
        actor = Actor("worker", "worker", frozenset({"task:claim"}), frozenset({"owner/repository"}))
        with self.assertRaisesRegex(ValueError, "lease_seconds"):
            service.claim(owner="worker", role=RunRole.READER, repositories=("owner/repository",), lease_seconds=301, actor=actor, now=NOW)
        denied = Actor("worker", "worker", frozenset(), frozenset({"owner/repository"}))
        with self.assertRaises(AuthorizationError):
            service.claim(owner="worker", role=RunRole.READER, repositories=("owner/repository",), lease_seconds=60, actor=denied, now=NOW)
        self.assertEqual(store.calls, [])


if __name__ == "__main__":
    unittest.main()
