import unittest

from adaptive_factory.models import Actor
from adaptive_factory.semantic_adjudication import adjudicate
from adaptive_factory.semantic_contracts import SemanticCoverageV1, SemanticFindingV1, SemanticSubjectV1
from adaptive_factory.semantic_repair import (
    RepairChildProposalV1,
    RepairChildTaskBindingV1,
    RepairEscalationV1,
    RepairLifecycleResult,
    SemanticRepairRequestV1,
    plan_repair,
)
from adaptive_factory.service import AuthorizationError, FactoryService
from adaptive_factory.store import PostgresSemanticCoordinatorStore, StoreError
from .test_semantic_contracts import coverage, finding, subject
from .test_semantic_persistence import FakeConnection, FakeCursor


TASK_ID = "00000000-0000-0000-0000-000000000001"
REPOSITORY_ID = "owner/repository"


def repair_fixture():
    root = SemanticSubjectV1.from_dict(subject())
    entries = coverage(root.digest)["entries"]
    entries[0] = {**entries[0], "status": "unproven", "evidence_refs": []}
    finding_value = SemanticFindingV1.from_dict(finding(root.digest))
    verdict = adjudicate(
        root,
        (finding_value,),
        (SemanticCoverageV1.from_dict(coverage(root.digest, entries=entries)),),
    )
    return root, finding_value, verdict


def request(root, verdict, **changes):
    value = {
        "schema_version": 1,
        "subject_digest": root.digest,
        "verdict_digest": verdict.digest,
        "requested_cycle": 1,
        "previous_child_proposal_digest": None,
        "writer_id": root.original_writer_id,
        "context_digest": "b" * 64,
        "expected_workspace_result_digest": "c" * 64,
        "expected_fence": 7,
        "expected_head_sha": root.exact_head_sha,
        "expected_base_sha": root.exact_base_sha,
        "expected_architecture_digest": root.architecture_digest,
        "expected_authority_digest": root.authority_digest,
        "expected_diff_digest": root.diff_digest,
        "expected_risk_level": root.risk_level,
    }
    value.update(changes)
    if value["requested_cycle"] >= 2 and "previous_child_proposal_digest" not in changes:
        value["previous_child_proposal_digest"] = "9" * 64
    return value


def repair_result(root, finding_value, verdict):
    policy = plan_repair(
        root,
        verdict,
        requested_cycle=1,
        writer_id=root.original_writer_id,
        context_digest="b" * 64,
        prior_context_digests=(),
        prior_finding_identity_digests=(),
        expected_base_sha=root.exact_base_sha,
        expected_architecture_digest=root.architecture_digest,
        expected_authority_digest=root.authority_digest,
        baseline_risk_level=root.risk_level,
        budget_remaining_units=100,
        deadline_remaining_seconds=60,
    )
    directive = policy.directive
    child = RepairChildProposalV1.from_dict(
        {
            "schema_version": 1,
            "subject_digest": root.digest,
            "verdict_digest": verdict.digest,
            "directive_digest": directive.digest,
            "cycle": 1,
            "previous_child_proposal_digest": None,
            "parent_task_id": TASK_ID,
            "parent_run_id": "00000000-0000-0000-0000-000000000002",
            "parent_fence": 7,
            "parent_task_packet_digest": "d" * 64,
            "parent_run_manifest_digest": "e" * 64,
            "parent_workspace_result_digest": "c" * 64,
            "parent_exact_head_sha": root.exact_head_sha,
            "writer_id": root.original_writer_id,
            "context_digest": "b" * 64,
            "exact_base_sha": root.exact_base_sha,
            "architecture_digest": root.architecture_digest,
            "authority_digest": root.authority_digest,
            "diff_digest": root.diff_digest,
            "finding_identity_digests": [finding_value.identity_digest],
            "baseline_risk_level": root.risk_level,
            "max_cost_usd_micros": 1_000,
            "max_token_units": 2_000,
            "max_output_bytes": 3_000,
            "max_events": 100,
            "infrastructure_retries_remaining": 2,
            "budget_remaining_units": 3,
            "deadline_at": "2026-09-03T00:00:00Z",
            "proposal_state": "pending_handoff",
            "requires_new_workspace_result": True,
            "requires_new_semantic_subject": True,
        }
    )
    return RepairLifecycleResult.from_dict(
        {
            "decision": "repair",
            "reason": "repair_allowed",
            "subject_digest": root.digest,
            "verdict_digest": verdict.digest,
            "cycle": 1,
            "directive_digest": directive.digest,
            "directive": directive.to_dict(),
            "child_proposal_digest": child.digest,
            "child_proposal": child.to_dict(),
            "escalation_digest": None,
            "escalation": None,
        }
    )


def child_binding(result):
    return RepairChildTaskBindingV1.from_dict(
        {
            "schema_version": 1,
            "child_proposal_digest": result.child_proposal_digest,
            "child_task_id": "00000000-0000-0000-0000-000000000003",
            "child_intent_digest": "f" * 64,
        }
    )


class CoreStore:
    def get_task(self, task_id):
        if task_id != TASK_ID:
            raise KeyError(task_id)
        return type("Task", (), {"repository_id": REPOSITORY_ID})()


class CoordinatorStore:
    def __init__(self, result):
        self.result = result
        self.calls = []
        self.bindings = []

    def request_repair(self, task_id, repair_request, *, idempotency_key):
        self.calls.append((task_id, repair_request, idempotency_key))
        return self.result

    def bind_repair_child(self, binding):
        self.bindings.append(binding)
        return binding


class ChildBroker:
    def __init__(self, result, error=None):
        self.binding = (
            child_binding(result)
            if result.child_proposal_digest is not None
            else RepairChildTaskBindingV1.from_dict(
                {
                    "schema_version": 1,
                    "child_proposal_digest": "1" * 64,
                    "child_task_id": "00000000-0000-0000-0000-000000000003",
                    "child_intent_digest": "f" * 64,
                }
            )
        )
        self.error = error
        self.proposals = []
        self.children = {}

    def propose_repair_child(self, proposal, *, idempotency_key):
        self.proposals.append(proposal)
        if self.error is not None:
            raise self.error
        self.children.setdefault(idempotency_key, proposal)
        return self.binding


class ProbeCoordinatorStore(PostgresSemanticCoordinatorStore):
    def __init__(self, rows):
        self.cursor = FakeCursor(rows)
        self.database_url = "postgresql://semantic-repair-probe"

    def _connect(self):
        return FakeConnection(self.cursor)


def result_wire(result):
    return {
        "decision": result.decision,
        "reason": result.reason,
        "subject_digest": result.subject_digest,
        "verdict_digest": result.verdict_digest,
        "cycle": result.cycle,
        "directive_digest": result.directive_digest,
        "directive": result.directive.to_dict() if result.directive else None,
        "child_proposal_digest": result.child_proposal_digest,
        "child_proposal": (
            result.child_proposal.to_dict() if result.child_proposal else None
        ),
        "escalation_digest": result.escalation_digest,
        "escalation": result.escalation.to_dict() if result.escalation else None,
    }


class SemanticRepairLifecycleTests(unittest.TestCase):
    def test_request_is_closed_and_binds_every_parent_policy_fact(self):
        root, _finding, verdict = repair_fixture()
        parsed = SemanticRepairRequestV1.from_dict(request(root, verdict))
        self.assertEqual(parsed.subject_digest, root.digest)
        self.assertEqual(parsed.expected_workspace_result_digest, "c" * 64)
        self.assertIsNone(parsed.previous_child_proposal_digest)
        with self.assertRaisesRegex(ValueError, "unknown_fields"):
            SemanticRepairRequestV1.from_dict(
                request(root, verdict, provider_command="forbidden")
            )
        with self.assertRaisesRegex(ValueError, "repair_cycle_sequence"):
            SemanticRepairRequestV1.from_dict(
                request(
                    root,
                    verdict,
                    requested_cycle=3,
                    previous_child_proposal_digest=None,
                )
            )

    def test_coordinator_persists_then_hands_only_the_exact_child_to_m5_broker(self):
        root, finding_value, verdict = repair_fixture()
        result = repair_result(root, finding_value, verdict)
        store = CoordinatorStore(result)
        broker = ChildBroker(result)
        service = FactoryService(
            CoreStore(), semantic_store=store, repair_child_broker=broker
        )
        actor = Actor(
            "semantic-coordinator",
            "operator",
            frozenset({"semantic:repair"}),
            frozenset({REPOSITORY_ID}),
        )

        actual = service.request_semantic_repair(
            TASK_ID,
            request(root, verdict),
            actor=actor,
            idempotency_key="1" * 64,
        )

        self.assertEqual(actual, result)
        self.assertEqual(len(store.calls), 1)
        self.assertIsInstance(store.calls[0][1], SemanticRepairRequestV1)
        self.assertEqual(broker.proposals, [result.child_proposal])
        self.assertEqual(broker.children, {result.child_proposal_digest: result.child_proposal})
        self.assertEqual(store.bindings, [child_binding(result)])
        child_wire = result.child_proposal.to_dict()
        for forbidden in (
            "provider",
            "workspace_handle",
            "git",
            "prompt",
            "credentials",
            "validator",
            "adjudicator",
        ):
            self.assertNotIn(forbidden, child_wire)
        self.assertTrue(child_wire["requires_new_workspace_result"])
        self.assertTrue(child_wire["requires_new_semantic_subject"])

    def test_invalid_policy_result_is_persisted_without_child_or_broker_call(self):
        root, _finding, verdict = repair_fixture()
        escalation = RepairEscalationV1.from_dict(
            {
                "schema_version": 1,
                "subject_digest": root.digest,
                "verdict_digest": verdict.digest,
                "requested_cycle": 4,
                "reason": "repair_cycle_out_of_bounds",
                "request_digest": "a" * 64,
            }
        )
        result = RepairLifecycleResult.from_dict(
            {
                "decision": "needs_human",
                "reason": "repair_cycle_out_of_bounds",
                "subject_digest": root.digest,
                "verdict_digest": verdict.digest,
                "cycle": 4,
                "directive_digest": None,
                "directive": None,
                "child_proposal_digest": None,
                "child_proposal": None,
                "escalation_digest": escalation.digest,
                "escalation": escalation.to_dict(),
            }
        )
        store = CoordinatorStore(result)
        broker = ChildBroker(result)
        service = FactoryService(
            CoreStore(), semantic_store=store, repair_child_broker=broker
        )
        actor = Actor(
            "semantic-coordinator",
            "operator",
            frozenset({"semantic:repair"}),
            frozenset({REPOSITORY_ID}),
        )
        actual = service.request_semantic_repair(
            TASK_ID,
            request(root, verdict, requested_cycle=4),
            actor=actor,
            idempotency_key="2" * 64,
        )
        self.assertEqual(actual.decision, "needs_human")
        self.assertIsNone(actual.child_proposal)
        self.assertEqual(broker.proposals, [])
        self.assertEqual(store.bindings, [])

    def test_broker_failure_leaves_exact_persisted_child_retryable(self):
        root, finding_value, verdict = repair_fixture()
        result = repair_result(root, finding_value, verdict)
        store = CoordinatorStore(result)
        broker = ChildBroker(result, RuntimeError("m5 child broker unavailable"))
        service = FactoryService(
            CoreStore(), semantic_store=store, repair_child_broker=broker
        )
        actor = Actor(
            "semantic-coordinator",
            "operator",
            frozenset({"semantic:repair"}),
            frozenset({REPOSITORY_ID}),
        )
        with self.assertRaisesRegex(RuntimeError, "broker unavailable"):
            service.request_semantic_repair(
                TASK_ID,
                request(root, verdict),
                actor=actor,
                idempotency_key="3" * 64,
            )
        broker.error = None
        replay = service.request_semantic_repair(
            TASK_ID,
            request(root, verdict),
            actor=actor,
            idempotency_key="3" * 64,
        )
        self.assertEqual(replay, result)
        self.assertEqual(broker.proposals, [result.child_proposal, result.child_proposal])
        self.assertEqual(
            broker.children, {result.child_proposal_digest: result.child_proposal}
        )
        self.assertEqual(store.bindings, [child_binding(result)])

    def test_writer_cannot_request_repair_even_with_coordinator_scope(self):
        root, finding_value, verdict = repair_fixture()
        service = FactoryService(
            CoreStore(),
            semantic_store=CoordinatorStore(repair_result(root, finding_value, verdict)),
            repair_child_broker=ChildBroker(repair_result(root, finding_value, verdict)),
        )
        writer = Actor(
            root.original_writer_id,
            "worker",
            frozenset({"semantic:repair", "task:execute"}),
            frozenset({REPOSITORY_ID}),
        )
        with self.assertRaises(AuthorizationError):
            service.request_semantic_repair(
                TASK_ID,
                request(root, verdict),
                actor=writer,
                idempotency_key="4" * 64,
            )

    def test_store_sends_one_closed_canonical_command_and_reparses_every_digest(self):
        root, finding_value, verdict = repair_fixture()
        expected = repair_result(root, finding_value, verdict)
        repair_request = SemanticRepairRequestV1.from_dict(request(root, verdict))
        store = ProbeCoordinatorStore([result_wire(expected)])
        actual = store.request_repair(
            TASK_ID, repair_request, idempotency_key="5" * 64
        )
        self.assertEqual(actual, expected)
        query, params = store.cursor.calls[-1]
        self.assertIn("semantic_plan_repair", query)
        self.assertEqual(params[0], "5" * 64)
        self.assertEqual(params[3], TASK_ID)
        self.assertNotIn(": ", params[2])

        corrupt = result_wire(expected)
        corrupt["child_proposal_digest"] = "0" * 64
        with self.assertRaises(StoreError):
            ProbeCoordinatorStore([corrupt]).request_repair(
                TASK_ID, repair_request, idempotency_key="5" * 64
            )

    def test_store_persists_only_the_closed_exact_broker_task_binding(self):
        root, finding_value, verdict = repair_fixture()
        result = repair_result(root, finding_value, verdict)
        binding = child_binding(result)
        store = ProbeCoordinatorStore([binding.to_dict()])

        self.assertEqual(store.bind_repair_child(binding), binding)
        query, params = store.cursor.calls[-1]
        self.assertIn("semantic_bind_repair_child", query)
        self.assertEqual(params[0], binding.digest)
        self.assertNotIn(": ", params[1])

        corrupt = {
            **binding.to_dict(),
            "child_task_id": "00000000-0000-0000-0000-000000000004",
        }
        with self.assertRaises(StoreError):
            ProbeCoordinatorStore([corrupt]).bind_repair_child(binding)

    def test_new_child_contract_cannot_relabel_old_result_or_verdict(self):
        root, finding_value, verdict = repair_fixture()
        result = repair_result(root, finding_value, verdict)
        child = result.child_proposal
        self.assertEqual(child.parent_workspace_result_digest, "c" * 64)
        self.assertEqual(child.parent_exact_head_sha, root.exact_head_sha)
        self.assertEqual(child.baseline_risk_level, root.risk_level)
        self.assertEqual(result.verdict_digest, verdict.digest)
        with self.assertRaisesRegex(ValueError, "requires_new_workspace_result"):
            RepairChildProposalV1.from_dict(
                {**child.to_dict(), "requires_new_workspace_result": False}
            )
        with self.assertRaisesRegex(ValueError, "requires_new_semantic_subject"):
            RepairChildProposalV1.from_dict(
                {**child.to_dict(), "requires_new_semantic_subject": False}
            )
        with self.assertRaisesRegex(ValueError, "baseline_risk_level"):
            RepairChildProposalV1.from_dict(
                {**child.to_dict(), "baseline_risk_level": "none"}
            )


if __name__ == "__main__":
    unittest.main()
