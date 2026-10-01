from copy import deepcopy
import importlib
import importlib.util
import unittest
from datetime import datetime, timezone

from adaptive_factory.contracts import ContractError
from adaptive_factory.migrations import discover_migrations
from adaptive_factory.models import Actor, LeaseGrant, RunRole, TaskProjection, TaskStatus
from adaptive_factory.service import FactoryService
from adaptive_factory.store import PostgresFactoryStore


def decision_facts():
    return dict(
        schema_version=1,
        decision_id="decision-1",
        repository_id="owner/project",
        task_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        attempt_id="attempt-1",
        fence=1,
        observed_at="2026-09-30T12:00:00Z",
        decision_kind="state",
        rule_id="RULE-1",
        rule_version="1",
        facts=[
            dict(name="from_state", value="leased"),
            dict(name="target", value="analyzing"),
        ],
        outcome="observed",
        reason_code="phase_started",
        base_sha="1" * 40,
        head_sha="2" * 40,
        context_digest="3" * 64,
        spec_digest="4" * 64,
        profile_digest="5" * 64,
        evidence_refs=["evidence/report.json"],
        constraints=["scope_bound"],
        next_step="verify",
        supersedes=None,
    )


class DecisionContractTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(
            importlib.util.find_spec("adaptive_factory.decision_contracts"),
            "decision contract missing",
        )
        return importlib.import_module("adaptive_factory.decision_contracts")

    def test_strict_factual_record_and_supersession_identity(self):
        module = self.module()
        facts = decision_facts()
        record = module.DecisionRecordV1.from_dict(facts)
        self.assertEqual(record.to_dict()["next_step"], "verify")
        self.assertEqual(
            record.record_digest,
            module.DecisionRecordV1.from_dict(deepcopy(facts)).record_digest,
        )
        for key, value in [
            ("outcome", "success"),
            ("fence", True),
            ("head_sha", "bad"),
            ("supersedes", "decision-1"),
        ]:
            changed = deepcopy(facts)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ContractError):
                module.DecisionRecordV1.from_dict(changed)
        facts["facts"][0]["value"] = "password=synthetic-secret"
        with self.assertRaises(ContractError):
            module.DecisionRecordV1.from_dict(facts)

    def test_cost_completeness_requires_declared_usage_coverage(self):
        module = self.module()
        entry = dict(
            usage_id="call-1",
            source="provider",
            currency="USD",
            pricing_version="p1",
            amount_usd_micros=120,
            status="actual",
        )
        self.assertFalse(module.summarize_cost([entry])["complete"])
        self.assertFalse(module.summarize_cost([entry], expected_usage_ids=["call-1", "call-2"])["complete"])
        self.assertTrue(module.summarize_cost([entry], expected_usage_ids=["call-1"])["complete"])

    def test_parallel_timing_uses_union_not_sum_and_never_invents_acceptance(self):
        module = self.module()
        intervals = [
            dict(
                phase="analysis",
                start="2026-09-30T12:00:00Z",
                end="2026-09-30T12:00:10Z",
            ),
            dict(
                phase="execution",
                start="2026-09-30T12:00:05Z",
                end="2026-09-30T12:00:15Z",
            ),
        ]
        summary = module.summarize_timing("2026-09-30T12:00:00Z", "2026-09-30T12:00:20Z", intervals)
        self.assertEqual(
            summary,
            dict(
                age_seconds=20,
                accepted_seconds=None,
                observed_wall_seconds=15,
                resource_seconds=20,
                human_seconds=None,
            ),
        )

    def test_append_only_migration_and_transactional_store_seam_exist(self):
        self.module()
        versions = {migration.version for migration in discover_migrations()}
        self.assertIn(23, versions, "additive decision migration missing")
        self.assertTrue(
            hasattr(PostgresFactoryStore, "append_decision"),
            "durable decision consumer missing",
        )

    def test_service_forwards_decision_to_atomic_phase_transition(self):
        now = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
        decision = object()

        class Store:
            forwarded = None

            def get_task(self, task_id):
                return TaskProjection(
                    task_id, "owner/project", TaskStatus.LEASED, 1, "a" * 64, "b" * 64, now
                )

            def transition_phase(self, grant, target, actor, observed_at, **kwargs):
                self.forwarded = kwargs["decision_record"]
                return target

        store = Store()
        worker = Actor(
            "worker-1",
            "worker",
            frozenset({"task:release"}),
            frozenset({"owner/project"}),
        )
        grant = LeaseGrant(
            "task-1", "run-1", worker.actor_id, RunRole.READER, 1, now, "b" * 64
        )
        self.assertEqual(
            FactoryService(store).transition_phase(
                grant,
                target=TaskStatus.ANALYZING,
                actor=worker,
                now=now,
                decision_record=decision,
            ),
            TaskStatus.ANALYZING,
        )
        self.assertIs(store.forwarded, decision)
