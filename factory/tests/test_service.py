from datetime import datetime, timezone
import unittest

from adaptive_factory.models import Actor, FailureClass, LeaseGrant, RunRole, TaskProjection, TaskStatus
from adaptive_factory.contracts import ContractError
from adaptive_factory.service import AuthorizationError, FactoryService
from factory.tests.test_contracts import valid_intake


NOW = datetime(2026, 8, 31, 20, 0, tzinfo=timezone.utc)


class RecordingStore:
    def __init__(self):
        self.calls = []

    def intake(self, intake, actor, now):
        if intake.m0_authority.bootstrap_exception is not None:
            raise AuthorizationError("transactional authority lookup rejected")
        self.calls.append(("intake", intake, actor, now))
        return {"task_id": "task-1", "created": True}

    def claim(self, request, actor, now, **_kwargs):
        self.calls.append(("claim", request, actor, now))
        return None

    def get_task(self, task_id):
        return TaskProjection(task_id, "owner/repository", TaskStatus.QUEUED, 1, "a" * 64, "b" * 64, NOW)

    def list_tasks(self, **kwargs):
        self.calls.append(("list", kwargs))
        return (self.get_task("task-1"),)

    def release(self, grant, outcome, actor, now, **_kwargs):
        self.calls.append(("release", outcome))
        return TaskStatus.RETRY

    def reconcile(self, *args, **kwargs):
        self.calls.append(("reconcile", args, kwargs))
        return "reconciled"

    def metrics(self):
        self.calls.append(("metrics",))
        return {}


class ServiceTests(unittest.TestCase):
    def test_submit_requires_scope_and_repository_authorization(self):
        store = RecordingStore()
        service = FactoryService(store)
        denied = Actor("caller", "client", frozenset(), frozenset({"owner/repository"}))
        cross_repo = Actor("caller", "client", frozenset({"task:submit"}), frozenset({"other/repository"}))
        for actor in (denied, cross_repo):
            with self.assertRaises(AuthorizationError):
                service.intake(valid_intake(), actor=actor, now=NOW)
        self.assertEqual(store.calls, [])

    def test_valid_submit_parses_before_store_boundary(self):
        store = RecordingStore()
        service = FactoryService(store)
        actor = Actor("caller", "client", frozenset({"task:submit"}), frozenset({"owner/repository"}))
        result = service.intake(valid_intake(), actor=actor, now=NOW)
        self.assertTrue(result["created"])
        self.assertEqual(store.calls[0][1].repository_id, "owner/repository")

    def test_submit_rejects_caller_asserted_or_unpersisted_m0_authority(self):
        store = RecordingStore()
        service = FactoryService(store)
        actor = Actor("caller", "client", frozenset({"task:submit"}), frozenset({"owner/repository"}))
        payload = valid_intake()
        payload["m0_authority"]["check_name"] = "caller-asserted-not-trust-ci"
        with self.assertRaises(ContractError):
            service.intake(payload, actor=actor, now=NOW)
        payload = valid_intake()
        payload["m0_authority"] = {
            "bootstrap_exception": "fabricated",
            "issuer": "untrusted-caller",
            "scope": "anything",
            "expires_at": "2026-09-01T20:00:00+00:00",
        }
        with self.assertRaises(AuthorizationError):
            service.intake(payload, actor=actor, now=NOW)
        self.assertEqual(store.calls, [])

    def test_global_reconcile_and_metrics_require_wildcard_repository_authority(self):
        store = RecordingStore()
        service = FactoryService(store)
        scoped = Actor(
            "operator", "operator", frozenset({"factory:reconcile"}), frozenset({"owner/repository"})
        )
        with self.assertRaises(AuthorizationError):
            service.reconcile(actor=scoped, now=NOW)
        with self.assertRaises(AuthorizationError):
            service.metrics(actor=scoped)
        self.assertEqual(store.calls, [])

    def test_claim_rejects_unbounded_lease_and_missing_worker_scope(self):
        store = RecordingStore()
        service = FactoryService(store)
        actor = Actor("worker", "worker", frozenset({"task:claim"}), frozenset({"owner/repository"}))
        with self.assertRaisesRegex(ValueError, "lease_seconds"):
            service.claim(
                owner="worker",
                role=RunRole.READER,
                repositories=("owner/repository",),
                lease_seconds=301,
                actor=actor,
                now=NOW,
            )
        denied = Actor("worker", "worker", frozenset(), frozenset({"owner/repository"}))
        with self.assertRaises(AuthorizationError):
            service.claim(
                owner="worker",
                role=RunRole.READER,
                repositories=("owner/repository",),
                lease_seconds=60,
                actor=denied,
                now=NOW,
            )
        self.assertEqual(store.calls, [])

    def test_worker_and_kill_mutations_enforce_actor_and_repository_boundary(self):
        store = RecordingStore()
        service = FactoryService(store)
        worker = Actor(
            "worker-B",
            "worker",
            frozenset({"task:claim", "task:heartbeat", "task:release", "task:budget"}),
            frozenset({"other/repository"}),
        )
        grant = LeaseGrant("task-1", "run-1", "worker-A", RunRole.READER, 1, NOW, "b" * 64)
        with self.assertRaises(AuthorizationError):
            service.heartbeat(grant, actor=worker, now=NOW)
        with self.assertRaises(AuthorizationError):
            service.release(grant, outcome="completed", actor=worker, now=NOW)
        operator = Actor("operator", "operator", frozenset({"factory:kill"}), frozenset({"owner/repository"}))
        with self.assertRaises(AuthorizationError):
            service.set_kill(
                scope_key="repository:other/repository",
                enabled=True,
                reason="stop",
                idempotency_key="a" * 64,
                actor=operator,
                now=NOW,
            )
        with self.assertRaises(AuthorizationError):
            service.set_kill(
                scope_key="global",
                enabled=True,
                reason="stop",
                idempotency_key="a" * 64,
                actor=operator,
                now=NOW,
            )

    def test_read_list_and_release_stay_typed_and_authorized(self):
        store = RecordingStore()
        service = FactoryService(store)
        reader = Actor("reader", "client", frozenset({"task:read", "task:list"}), frozenset({"owner/repository"}))
        self.assertEqual(service.get_task("task-1", actor=reader).task_id, "task-1")
        self.assertEqual(
            len(service.list_tasks(repository_id="owner/repository", limit=10, cursor=None, actor=reader)), 1
        )
        worker = Actor("worker", "worker", frozenset({"task:release"}), frozenset({"owner/repository"}))
        grant = LeaseGrant("task-1", "run-1", "worker", RunRole.READER, 1, NOW, "b" * 64)
        service.release(grant, outcome="worker_lost", actor=worker, now=NOW)
        self.assertEqual(store.calls[-1], ("release", FailureClass.WORKER_LOST))
        with self.assertRaises(ValueError):
            service.release(grant, outcome="provider_says_retry", actor=worker, now=NOW)


if __name__ == "__main__":
    unittest.main()
