from copy import deepcopy
from datetime import datetime, timezone, timedelta
import importlib
import unittest

from adaptive_factory.contracts import ContractError
from adaptive_factory.models import Actor, LeaseGrant, RunRole
from adaptive_factory.decision_contracts import DecisionRecordV1
from factory.tests.test_decision_contracts import decision_facts
from factory.tests.test_bb_contracts import bb_profile


def binding_facts():
    seed = decision_facts()
    return dict(
        schema_version=1,
        repository_id=seed["repository_id"],
        task_id=seed["task_id"],
        run_id=seed["run_id"],
        attempt_id=seed["attempt_id"],
        fence=1,
        contract_digest="a" * 64,
        policy_digest="b" * 64,
        context_digest=seed["context_digest"],
        profile_digest=seed["profile_digest"],
        base_sha=seed["base_sha"],
        candidate_sha=seed["head_sha"],
        branch="work/task-1",
        workspace="worktrees/task-1",
        environment_id="sandbox-1",
        host_id="host-1",
        project_id="project-1",
        thread_id="thread-1",
        workflow_id="workflow-1",
        provider="fixture",
        model="fixture-v1",
        reasoning="none",
        permission="isolated",
        revision=1,
        lease_deadline="2026-09-30T12:00:30Z",
        snapshots={"workflow": "c" * 64, "schema": "d" * 64, "environment": "e" * 64},
        children=[],
        exported_evidence_digest=None,
    )


class Journal:
    def __init__(self):
        self.records = {}
        self.reservations = []
        self.usages = []
        self.bindings = {}

    def claim_bb_binding(self, binding, grant, actor):
        fresh = binding.record_digest not in self.bindings
        self.bindings[binding.record_digest] = binding.to_dict()
        return fresh

    def verify_bb_binding(self, binding, grant, actor):
        if self.bindings.get(binding.record_digest) != binding.to_dict():
            raise ContractError("mapping_missing")
        return self.bindings[binding.record_digest]

    def begin_bb_operation(self, grant, record, actor):
        data = record.to_dict()
        key = data["decision_id"]
        if key in self.records:
            if self.records[key].record_digest != record.record_digest:
                raise ContractError("conflict")
            return False
        self.records[key] = record
        return True

    def append_decision(self, grant, record, actor):
        return self.begin_bb_operation(grant, record, actor)

    def bb_operation_records(self, grant, actor, operation_key):
        return [
            record
            for record in self.records.values()
            if any(f["name"] == "operation_key" and f["value"] == operation_key for f in record.to_dict()["facts"])
        ]

    def reserve_budget(self, *args, **kwargs):
        self.reservations.append(args)
        return "reservation-1"

    def observe_usage(self, *args, **kwargs):
        self.usages.append(args)

    def observe_bb_usage(self, grant, record, actor, decision):
        self.usages.append(record)
        return self.begin_bb_operation(grant, decision, actor)

    def begin_bb_workflow_operation(self, grant, record, actor, limits):
        if (
            record.to_dict()["decision_id"] not in self.records
            and sum(r.to_dict()["reason_code"] == "bb_intent" for r in self.records.values())
            >= limits["max_physical_attempts"]
        ):
            raise ContractError("workflow_exhausted")
        return self.begin_bb_operation(grant, record, actor)


class Transport:
    synthetic = True

    def __init__(self):
        self.calls = []
        self.unknown = False

    def capabilities(self):
        return {
            "submit",
            "status",
            "events",
            "pause",
            "resume",
            "stop",
            "reconcile",
            "artifacts",
            "usage",
            "pre_model_interception",
        }

    def command(self, operation, binding, payload, *, timeout_seconds):
        self.calls.append(operation)
        if self.unknown:
            raise TimeoutError()
        return dict(acknowledged=True, effect_outcome="unknown", stop_outcome="unknown", evidence_digest=None)

    def reconcile(self, binding, operation_id, *, timeout_seconds):
        self.calls.append("reconcile")
        return dict(acknowledged=True, effect_outcome="observed", stop_outcome="unknown", evidence_digest="f" * 64)

    def read(self, operation, binding, *, timeout_seconds):
        return self.read_result


class BBAdapterTests(unittest.TestCase):
    def setup_adapter(self, **options):
        module = importlib.import_module("adaptive_factory.bb_adapter")
        data = binding_facts()
        binding = module.BBExecutionBindingV1.from_dict(data)
        grant = LeaseGrant(
            data["task_id"],
            data["run_id"],
            "writer",
            RunRole.WRITER,
            1,
            datetime(2026, 9, 30, 12, 0, 30, tzinfo=timezone.utc),
            "9" * 64,
        )
        actor = Actor("writer", "worker", frozenset({"task:release", "task:budget"}), frozenset({"owner/project"}))
        journal = Journal()
        transport = Transport()
        adapter = module.BBAdapter(journal, transport, bb_profile(), synthetic=True)
        return adapter, binding, grant, actor, journal, transport

    def test_durable_intent_precedes_submit_and_duplicate_does_not_pay_twice(self):
        adapter, binding, grant, actor, journal, transport = self.setup_adapter()
        now = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
        result = adapter.submit(
            binding,
            grant,
            actor,
            DecisionRecordV1.from_dict(decision_facts()),
            operation_id="op-1",
            cost_usd_micros=100,
            token_units=10,
            now=now,
        )
        self.assertEqual(result.to_dict()["effect_outcome"], "unknown")
        adapter.submit(
            binding,
            grant,
            actor,
            DecisionRecordV1.from_dict(decision_facts()),
            operation_id="op-1",
            cost_usd_micros=100,
            token_units=10,
            now=now,
        )
        self.assertEqual(transport.calls, ["submit"])
        self.assertEqual(len(journal.reservations), 1)
        self.assertEqual(journal.bindings[binding.record_digest], binding.to_dict())
        self.assertTrue(any(record.to_dict()["reason_code"] == "bb_intent" for record in journal.records.values()))
        with self.assertRaises(ContractError):
            adapter.submit(
                binding,
                grant,
                actor,
                DecisionRecordV1.from_dict(decision_facts()),
                operation_id="op-1",
                cost_usd_micros=101,
                token_units=10,
                now=now,
            )

    def test_uncertain_effect_requires_reconciliation_without_submit_or_failover(self):
        adapter, binding, grant, actor, journal, transport = self.setup_adapter()
        transport.unknown = True
        now = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
        seed = DecisionRecordV1.from_dict(decision_facts())
        result = adapter.submit(
            binding, grant, actor, seed, operation_id="op-1", cost_usd_micros=100, token_units=10, now=now
        )
        self.assertEqual(result.to_dict()["effect_outcome"], "unknown")
        adapter.submit(binding, grant, actor, seed, operation_id="op-1", cost_usd_micros=100, token_units=10, now=now)
        self.assertEqual(transport.calls, ["submit"])
        observed = adapter.reconcile(binding, grant, actor, seed, operation_id="op-1", now=now)
        self.assertEqual(observed.to_dict()["effect_outcome"], "observed")
        self.assertEqual(transport.calls, ["submit", "reconcile"])
        replay = adapter.submit(
            binding, grant, actor, seed, operation_id="op-1", cost_usd_micros=100, token_units=10, now=now
        )
        self.assertEqual(replay.to_dict()["effect_outcome"], "observed")
        self.assertEqual(adapter.disable([result])["safe_native_operations"], [])

    def test_fence_lease_identity_and_unsupported_are_checked_before_transport(self):
        adapter, binding, grant, actor, journal, transport = self.setup_adapter()
        seed = DecisionRecordV1.from_dict(decision_facts())
        with self.assertRaises(ContractError):
            adapter.submit(
                binding, grant, actor, seed, operation_id="op-1", cost_usd_micros=1, token_units=1, now=grant.expires_at
            )
        wrong = Actor("other", "worker", actor.scopes, actor.repositories)
        with self.assertRaises(ContractError):
            adapter.stop(
                binding, grant, wrong, seed, operation_id="stop-1", now=datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
            )
        self.assertEqual(transport.calls, [])
        adapter.synthetic = False
        self.assertEqual(adapter.capabilities()["backend"], "native")
        with self.assertRaises(ContractError):
            adapter.submit(
                binding,
                grant,
                actor,
                seed,
                operation_id="op-1",
                cost_usd_micros=1,
                token_units=1,
                now=datetime(2026, 9, 30, 12, tzinfo=timezone.utc),
            )

    def test_event_conflict_resume_snapshot_and_evidence_retention(self):
        adapter, binding, grant, actor, journal, transport = self.setup_adapter()
        seed = DecisionRecordV1.from_dict(decision_facts())
        now = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
        event = dict(
            schema_version=1,
            event_id="event-1",
            source="fixture",
            occurred_at="2026-09-30T12:00:00Z",
            received_at="2026-09-30T12:00:01Z",
            binding_digest=binding.record_digest,
            type="heartbeat",
            payload_digest="1" * 64,
        )
        self.assertTrue(adapter.ingest_event(binding, grant, actor, seed, event, now=now))
        self.assertFalse(adapter.ingest_event(binding, grant, actor, seed, event, now=now))
        event["payload_digest"] = "2" * 64
        with self.assertRaises(ContractError):
            adapter.ingest_event(binding, grant, actor, seed, event, now=now)
        changed = deepcopy(binding.to_dict())
        changed["snapshots"]["workflow"] = "2" * 64
        module = importlib.import_module("adaptive_factory.bb_adapter")
        with self.assertRaises(ContractError):
            adapter.validate_resume(
                binding,
                module.BBExecutionBindingV1.from_dict(changed),
                actual_artifacts={},
                expected_artifacts={},
                access_allowed=True,
            )
        with self.assertRaises(ContractError):
            adapter.cleanup_allowed(binding, stop_outcome="observed")

    def test_control_stop_never_requires_paid_budget_and_supervisor_quarantines_expired_lease(self):
        adapter, binding, grant, actor, journal, transport = self.setup_adapter()
        seed = DecisionRecordV1.from_dict(decision_facts())
        adapter.stop(
            binding, grant, actor, seed, operation_id="stop-1", now=datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
        )
        self.assertEqual(journal.reservations, [])
        state = adapter.supervise(binding, grant, now=grant.expires_at)
        self.assertEqual(state["state"], "quarantined")
        self.assertFalse(state["new_calls_allowed"])

    def test_observation_artifacts_and_usage_are_bound_and_never_self_accept(self):
        adapter, binding, grant, actor, journal, transport = self.setup_adapter()
        seed = DecisionRecordV1.from_dict(decision_facts())
        now = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
        transport.read_result = dict(
            binding_digest=binding.record_digest,
            revision=1,
            observed_at="2026-09-30T12:00:00Z",
            state="completed",
            workers=["attempt-1"],
        )
        state = adapter.status(binding, grant, actor, seed, now=now)
        self.assertEqual(state["acceptance"], "awaiting_independent_review")
        transport.read_result["binding_digest"] = "f" * 64
        with self.assertRaises(ContractError):
            adapter.status(binding, grant, actor, seed, now=now)
        import hashlib

        artifact = dict(
            path="reports/check.txt", content="passed", sha256=hashlib.sha256(b"passed").hexdigest(), size_bytes=6
        )
        transport.read_result = dict(binding_digest=binding.record_digest, artifacts=[artifact])
        exported = adapter.artifacts(binding, grant, actor, seed, now=now)
        self.assertEqual(exported[0]["sha256"], artifact["sha256"])
        transport.read_result["artifacts"][0]["path"] = "../escape"
        with self.assertRaises(ContractError):
            adapter.artifacts(binding, grant, actor, seed, now=now)

    def test_accounting_preserves_nulls_and_provider_counter_subsets(self):
        module = importlib.import_module("adaptive_factory.bb_adapter")
        usage = dict(
            schema_version=1,
            provider_request_id="request-1",
            provider="fixture",
            model="fixture-v1",
            binding_digest="1" * 64,
            input_tokens=100,
            output_tokens=20,
            reasoning_tokens=10,
            cached_input_tokens=50,
            cache_write_tokens=None,
            missing_reason="not_reported",
            provider_cost_usd_micros=None,
            calculated_cost_usd_micros=120,
            confirmed_cost_usd_micros=None,
            price_table_digest="2" * 64,
            usage_source="provider",
            cost_status="estimated",
            reasoning_in_output=True,
            cache_in_input=True,
        )
        observation = module.BBUsageObservationV1.from_dict(usage)
        self.assertEqual(observation.token_units, 120)
        self.assertIsNone(observation.to_dict()["cache_write_tokens"])
        self.assertIsNone(observation.to_dict()["confirmed_cost_usd_micros"])
        usage["cached_input_tokens"] = 101
        with self.assertRaises(ContractError):
            module.BBUsageObservationV1.from_dict(usage)

    def test_late_usage_has_factual_record_in_same_factory_ledger_not_new_paid_action(self):
        adapter, binding, grant, actor, journal, transport = self.setup_adapter()
        seed = DecisionRecordV1.from_dict(decision_facts())
        usage = dict(
            schema_version=1,
            provider_request_id="request-1",
            provider="fixture",
            model="fixture-v1",
            binding_digest=binding.record_digest,
            input_tokens=100,
            output_tokens=20,
            reasoning_tokens=10,
            cached_input_tokens=50,
            cache_write_tokens=None,
            missing_reason="not_reported",
            provider_cost_usd_micros=None,
            calculated_cost_usd_micros=120,
            confirmed_cost_usd_micros=None,
            price_table_digest="2" * 64,
            usage_source="provider",
            cost_status="estimated",
            reasoning_in_output=True,
            cache_in_input=True,
        )
        journal.claim_bb_binding(binding, grant, actor)
        adapter.ingest_usage(binding, grant, actor, seed, usage, now=grant.expires_at + timedelta(seconds=1))
        self.assertEqual(transport.calls, [])
        self.assertEqual(len(journal.usages), 1)
        record = next(iter(journal.records.values())).to_dict()
        facts = {f["name"]: f["value"] for f in record["facts"]}
        self.assertIsNone(facts["cache_write_tokens"])
        self.assertIsNone(facts["confirmed_cost_usd_micros"])

    def test_workflow_attempt_limits_are_claimed_durably_not_reset_by_recreation(self):
        from adaptive_factory.bb_profiles import BBWorkflowSnapshotV1

        workflow = BBWorkflowSnapshotV1.from_dict(
            dict(
                schema_version=1,
                workflow_id="flow-1",
                script_digest="1" * 64,
                schema_digest="2" * 64,
                provider_profile_digest="5" * 64,
                steps=["implement", "test", "review"],
                max_agents=1,
                max_depth=1,
                max_physical_attempts=1,
                max_notifications=1,
                retry_owner="factory",
                max_cost_usd_micros=100,
                wall_seconds=60,
                orchestra_enabled=False,
                orchestra_plugin_digest=None,
            )
        )
        adapter, binding, grant, actor, journal, transport = self.setup_adapter()
        data = binding.to_dict()
        data["snapshots"]["workflow"] = workflow.record_digest
        module = importlib.import_module("adaptive_factory.bb_adapter")
        binding = module.BBExecutionBindingV1.from_dict(data)
        seed = DecisionRecordV1.from_dict(decision_facts())
        now = datetime(2026, 9, 30, 12, tzinfo=timezone.utc)
        from dataclasses import replace

        with self.assertRaisesRegex(ContractError, "bb_implement_requires_writer"):
            adapter.submit_workflow(
                workflow,
                "implement",
                binding,
                replace(grant, role=RunRole.READER),
                actor,
                seed,
                operation_id="reader-implement",
                cost_usd_micros=50,
                token_units=10,
                now=now,
            )
        adapter.submit_workflow(
            workflow,
            "implement",
            binding,
            grant,
            actor,
            seed,
            operation_id="call-1",
            cost_usd_micros=50,
            token_units=10,
            now=now,
        )
        with self.assertRaises(ContractError):
            adapter.submit_workflow(
                workflow,
                "test",
                binding,
                grant,
                actor,
                seed,
                operation_id="call-2",
                cost_usd_micros=50,
                token_units=10,
                now=now,
            )
        self.assertEqual(transport.calls, ["submit"])
