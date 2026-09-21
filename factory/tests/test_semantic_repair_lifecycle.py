import json
import traceback
import unittest
from unittest.mock import MagicMock, patch

from adaptive_factory import semantic_repair
from adaptive_factory.contracts import ContractError, canonical_digest
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


class SemanticRepairPlanRejectionTests(unittest.TestCase):
    SQL_REASONS = frozenset({
        "command_input_invalid", "repair_payload_invalid", "cycle_lineage_invalid",
        "idempotency_conflict", "subject_not_found", "verdict_mismatch",
        "execution_material_missing", "previous_proposal_mismatch",
        "child_handoff_mismatch", "lineage_mismatch", "baseline_risk_invalid",
        "directive_conflict", "child_proposal_conflict", "store_operation_rejected",
    })

    def setUp(self):
        self.root, self.finding, self.verdict = repair_fixture()
        self.repair_request = SemanticRepairRequestV1.from_dict(
            request(self.root, self.verdict)
        )
        self.result = repair_result(self.root, self.finding, self.verdict)
        self.idempotency_key = "5" * 64

    def call_store(self, response, repair_request=None):
        return ProbeCoordinatorStore([response]).request_repair(
            TASK_ID, repair_request or self.repair_request,
            idempotency_key=self.idempotency_key,
        )

    def assert_refusal(self, response, reason):
        with patch.object(
            RepairLifecycleResult, "from_dict", wraps=RepairLifecycleResult.from_dict
        ) as parser:
            with self.assertRaises(StoreError) as raised:
                self.call_store(response)
        error = raised.exception
        self.assertEqual(str(error), f"semantic repair plan rejected: {reason}")
        parser.assert_not_called()
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        self.assertNotIn("invalid_object", "".join(traceback.format_exception(error)))

    def test_plan_reader_has_a_closed_vocabulary_and_exact_single_key(self):
        self.assertTrue(hasattr(semantic_repair, "repair_plan_rejection_reason"))
        reader = semantic_repair.repair_plan_rejection_reason
        self.assertEqual(semantic_repair.REPAIR_PLAN_REJECTION_CHANNEL,
                         "repair_plan_rejection")
        self.assertEqual(semantic_repair.UNKNOWN_REPAIR_PLAN_REJECTION,
                         "planning_rejected")
        self.assertEqual(semantic_repair.REPAIR_PLAN_REJECTIONS,
                         self.SQL_REASONS | {"planning_rejected"})
        for reason in sorted(self.SQL_REASONS):
            with self.subTest(reason=reason):
                self.assertEqual(reader({"repair_plan_rejection": reason}), reason)
        for reason in ("", "untrusted database text", None, 7, False, [], {}):
            with self.subTest(reason=reason):
                self.assertEqual(reader({"repair_plan_rejection": reason}),
                                 "planning_rejected")
        for response in (
            None, 7, False, [], {}, "repair_plan_rejection",
            {"repair_child_rejection": "command_input_invalid"},
            {"repair_plan_rejection": "subject_not_found", "extra": True},
            {**result_wire(self.result), "repair_plan_rejection": "subject_not_found"},
        ):
            with self.subTest(response=response):
                self.assertIsNone(reader(response))

    def test_store_names_every_known_refusal_without_parsing_a_lifecycle(self):
        for reason in sorted(self.SQL_REASONS):
            for encoded in (False, True):
                with self.subTest(reason=reason, encoded=encoded):
                    response = {"repair_plan_rejection": reason}
                    self.assert_refusal(json.dumps(response) if encoded else response,
                                        reason)

    def test_store_bounds_unknown_reasons_without_echoing_untrusted_data(self):
        for reason in ("untrusted SQL detail", "", None, 7, False, [], {"secret": "x"}):
            with self.subTest(reason=reason):
                self.assert_refusal({"repair_plan_rejection": reason},
                                    "planning_rejected")

    def test_store_classifies_legacy_sql_null_and_json_null_as_refusals(self):
        for response in (None, "null", " \nnull\t"):
            with self.subTest(response=response):
                self.assert_refusal(response, "store_returned_null")

    def test_malformed_json_is_stored_corruption_with_decoder_cause(self):
        for response in ("{", "untrusted database text", '{"decision":}'):
            with self.subTest(response=response):
                try:
                    self.call_store(response)
                except Exception as error:
                    self.assertIsInstance(error, StoreError)
                    self.assertEqual(str(error), "stored semantic repair result is corrupt")
                    self.assertIsInstance(error.__cause__, json.JSONDecodeError)
                else:
                    self.fail("malformed wire response was accepted")

    def test_malformed_documents_and_channel_smuggling_remain_corruption(self):
        corrupt_digest = {**result_wire(self.result), "child_proposal_digest": "0" * 64}
        for response in (
            {}, [], 7, False, '"scalar"',
            {"repair_child_rejection": "command_input_invalid"},
            {"repair_plan_rejection": "subject_not_found", "extra": True},
            {**result_wire(self.result), "repair_plan_rejection": "subject_not_found"},
            corrupt_digest,
        ):
            with self.subTest(response=response):
                with self.assertRaises(StoreError) as raised:
                    self.call_store(response)
                self.assertEqual(str(raised.exception),
                                 "stored semantic repair result is corrupt")
                self.assertIsInstance(raised.exception.__cause__, ContractError)
        self.assertEqual(self.call_store(result_wire(self.result)), self.result)
        self.assertEqual(self.call_store(json.dumps(result_wire(self.result))), self.result)

    def test_valid_lifecycle_cannot_bypass_existing_request_bindings(self):
        for key, value in (
            ("subject_digest", "0" * 64), ("verdict_digest", "0" * 64),
            ("requested_cycle", 2),
        ):
            with self.subTest(key=key):
                changed = SemanticRepairRequestV1.from_dict(
                    request(self.root, self.verdict, **{key: value})
                )
                with self.assertRaisesRegex(StoreError, "^stored semantic repair result binding mismatch$"):
                    self.call_store(result_wire(self.result), changed)
        for key, value in (
            ("expected_workspace_result_digest", "0" * 64), ("expected_fence", 8),
            ("expected_head_sha", "0" * 40), ("writer_id", "other-writer"),
            ("context_digest", "0" * 64), ("expected_base_sha", "0" * 40),
            ("expected_architecture_digest", "0" * 64),
            ("expected_authority_digest", "0" * 64), ("expected_diff_digest", "0" * 64),
        ):
            with self.subTest(key=key):
                changed = SemanticRepairRequestV1.from_dict(
                    request(self.root, self.verdict, **{key: value})
                )
                with self.assertRaisesRegex(StoreError, "^stored semantic repair child binding mismatch$"):
                    self.call_store(result_wire(self.result), changed)

    def test_deadline_escalation_remains_a_bound_successful_result(self):
        command_digest = canonical_digest({
            "contract": "adaptive-factory.semantic-repair-command/v1",
            "idempotency_key": self.idempotency_key,
            "task_id": TASK_ID,
            "repair_request": self.repair_request.to_dict(),
        })
        for request_digest in (command_digest, "0" * 64):
            escalation = RepairEscalationV1.from_dict({
                "schema_version": 1, "subject_digest": self.root.digest,
                "verdict_digest": self.verdict.digest, "requested_cycle": 1,
                "reason": "deadline_exhausted", "request_digest": request_digest,
            })
            wire = {
                "decision": "needs_human", "reason": "deadline_exhausted",
                "subject_digest": self.root.digest, "verdict_digest": self.verdict.digest,
                "cycle": 1, "directive_digest": None, "directive": None,
                "child_proposal_digest": None, "child_proposal": None,
                "escalation_digest": escalation.digest, "escalation": escalation.to_dict(),
            }
            with self.subTest(matching=request_digest == command_digest):
                if request_digest == command_digest:
                    actual = self.call_store(wire)
                    self.assertEqual(actual.decision, "needs_human")
                    self.assertEqual(actual.escalation, escalation)
                else:
                    with self.assertRaisesRegex(StoreError, "^stored semantic repair escalation binding mismatch$"):
                        self.call_store(wire)

    def test_refusal_is_classified_after_the_database_transaction_exits(self):
        store = ProbeCoordinatorStore([{"repair_plan_rejection": "child_proposal_conflict"}])
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value = store.cursor
        with patch.object(store, "_connect", return_value=connection):
            with self.assertRaisesRegex(StoreError, "^semantic repair plan rejected: child_proposal_conflict$"):
                store.request_repair(TASK_ID, self.repair_request,
                                     idempotency_key=self.idempotency_key)
        connection.transaction.return_value.__exit__.assert_called_once_with(None, None, None)
        connection.__exit__.assert_called_once_with(None, None, None)

    def test_service_propagates_refusal_without_broker_or_binding_calls(self):
        store = CoordinatorStore(self.result)
        broker = ChildBroker(self.result)
        service = FactoryService(CoreStore(), semantic_store=store, repair_child_broker=broker)
        actor = Actor("semantic-coordinator", "operator", frozenset({"semantic:repair"}),
                      frozenset({REPOSITORY_ID}))
        refusal = StoreError("semantic repair plan rejected: subject_not_found")
        with patch.object(store, "request_repair", side_effect=refusal):
            with self.assertRaises(StoreError) as raised:
                service.request_semantic_repair(
                    TASK_ID, request(self.root, self.verdict), actor=actor,
                    idempotency_key=self.idempotency_key,
                )
        self.assertIs(raised.exception, refusal)
        self.assertEqual(broker.proposals, [])
        self.assertEqual(store.bindings, [])


if __name__ == "__main__":
    unittest.main()
