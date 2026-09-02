from datetime import datetime, timezone
import unittest

from adaptive_factory.execution_contracts import ExecutionContractError, WorkspaceResultV1
from adaptive_factory.models import Actor, ExecutionStage, LeaseGrant, RunRole
from adaptive_factory.service import AuthorizationError, FactoryService
from adaptive_factory.brokers import ProposalContext
from adaptive_factory.workspace import WorkspaceSnapshotRequest, WorkspaceSnapshotUnavailable, WorkspaceSnapshotV1
from factory.tests.test_execution_contracts import valid_packet, valid_workspace_result


NOW = datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc)
GRANT = LeaseGrant(
    "00000000-0000-0000-0000-000000000001",
    "00000000-0000-0000-0000-000000000002",
    "worker-01",
    RunRole.WRITER,
    7,
    datetime(2026, 9, 2, 0, 5, tzinfo=timezone.utc),
    "0" * 64,
)
WORKER = Actor(
    "worker-01",
    "worker",
    frozenset({"task:claim", "task:execute"}),
    frozenset({"owner/repository"}),
)


def selection():
    packet = valid_packet()
    return {
        "provider": packet["provider"],
        "capability_policy": packet["capability_policy"],
        "plan": packet["plan"],
        "workspace_handle": packet["workspace_handle"],
        "prompt_template_digest": "7" * 64,
        "role_definition_digest": "8" * 64,
        "tool_policy_digest": "9" * 64,
        "output_schema_digest": "a" * 64,
    }


class FakeExecutionStore:
    def __init__(self):
        self.calls = []
        self.finalized = {}

    def claim(self, request, actor, now, **kwargs):
        self.calls.append(("claim", request, actor, kwargs))
        return GRANT

    def get_task(self, task_id):
        from adaptive_factory.models import TaskProjection, TaskStatus
        return TaskProjection(task_id, "owner/repository", TaskStatus.LEASED, 1, "0" * 64, "0" * 64, GRANT.expires_at)

    def execution_material(self, grant):
        self.calls.append(("material", grant))
        return {
            "repository_id": "owner/repository",
            "legacy_intent_digest": "0" * 64,
            "route_id": "37b05f579320",
            "change_id": "20260901-m5-execution",
            "exact_base_sha": "1" * 40,
            "exact_head_sha": "2" * 40,
            "spec_digest": "3" * 64,
            "architecture_digest": "4" * 64,
            "governance_digest": "5" * 64,
            "policy_digest": "6" * 64,
            "acceptance_ids": ["AC-001", "AC-002"],
            "limits": valid_packet()["limits"],
            "deadline": "2026-09-02T01:00:00Z",
        }

    def start_execution(self, grant, packet, manifest, actor, **kwargs):
        self.calls.append(("start", grant, packet, manifest, actor, kwargs))
        from adaptive_factory.models import ExecutionGrant
        return ExecutionGrant(grant, packet.packet_digest, manifest.manifest_digest, manifest.workspace_handle, manifest.provider_id, ExecutionStage.PREPARED)

    def advance_execution(self, grant, packet_digest, stage, actor, **kwargs):
        self.calls.append(("advance", grant, packet_digest, stage, actor, kwargs))
        return stage

    def proposal_context(self, grant, packet_digest):
        self.calls.append(("proposal_context", grant, packet_digest))
        return ProposalContext(
            grant.task_id, grant.run_id, grant.owner, grant.fence, packet_digest,
            grant.role.value, ("patch", "report"), 65_536, 1_000_000,
            1_000_000, 1_000_000, 100_000, ("artifacts", "notes", "structured_output", "usage"),
        )

    def commit_execution_proposal(self, grant, proposal, actor, **kwargs):
        self.calls.append(("proposal", grant, proposal, actor, kwargs))
        return proposal

    def finalize_execution(self, grant, packet_digest, snapshot, actor, **kwargs):
        self.calls.append(("finalize", grant, packet_digest, snapshot, actor, kwargs))
        value = valid_workspace_result()
        value.update({
            "task_id": grant.task_id,
            "run_id": grant.run_id,
            "task_packet_digest": packet_digest,
            "exact_head_sha": snapshot.result_head_sha,
            "workspace_snapshot_digest": snapshot.workspace_snapshot_digest,
        })
        result = WorkspaceResultV1.from_facts(value)
        if kwargs.get("idempotency_key") is not None:
            self.finalized[kwargs["idempotency_key"]] = result
        return result

    def workspace_snapshot_request(self, grant, packet_digest):
        self.calls.append(("snapshot_request", grant, packet_digest))
        return WorkspaceSnapshotRequest(
            grant.task_id, grant.run_id, "owner/repository", "workspace:" + "d" * 64, "2" * 40
        )

    def workspace_result(self, task_id, workspace_result_digest):
        self.calls.append(("workspace_result", task_id, workspace_result_digest))
        return {"result": workspace_result_digest}

    def execution_finalization_replay(self, grant, packet_digest, actor, *, idempotency_key):
        self.calls.append(("finalization_replay", grant, packet_digest, actor, idempotency_key))
        return self.finalized.get(idempotency_key)


class UnavailableSnapshotBroker:
    def snapshot(self, _request):
        return WorkspaceSnapshotUnavailable()


class TrustedTestSnapshotBroker:
    def __init__(self):
        self.calls = 0

    def snapshot(self, request):
        self.calls += 1
        return WorkspaceSnapshotV1.from_facts({
            "contract_version": 1, "repository_id": request.repository_id,
            "workspace_handle": request.workspace_handle,
            "input_head_sha": request.input_head_sha, "result_head_sha": "f" * 40,
            "diff_digest": "e" * 64, "diff_lines": 12, "source": "trusted_git_broker",
        })


class ExecutionServiceTests(unittest.TestCase):
    def test_explicit_execution_claim_preserves_legacy_digest_and_persists_manifest(self):
        store = FakeExecutionStore()
        result = FactoryService(store).claim_execution(
            owner=WORKER.actor_id,
            role=RunRole.WRITER,
            repositories=("owner/repository",),
            lease_seconds=60,
            selection=selection(),
            actor=WORKER,
            now=NOW,
            idempotency_key="b" * 64,
            correlation_id="correlation-001",
        )
        self.assertEqual(result.lease.packet_digest, "0" * 64)
        self.assertNotEqual(result.packet_digest, result.lease.packet_digest)
        self.assertEqual(result.provider_id, "codex")
        self.assertEqual(result.stage, ExecutionStage.PREPARED)
        self.assertEqual(tuple(item[0] for item in store.calls), ("claim", "material", "start"))

    def test_invalid_or_ineligible_selection_fails_before_m4_claim(self):
        store = FakeExecutionStore()
        invalid = selection()
        invalid["provider"]["eligible"] = False
        with self.assertRaisesRegex(ExecutionContractError, "provider_ineligible"):
            FactoryService(store).claim_execution(
                owner=WORKER.actor_id, role=RunRole.WRITER, repositories=("owner/repository",),
                lease_seconds=60, selection=invalid, actor=WORKER, now=NOW,
            )
        self.assertEqual(store.calls, [])

    def test_execution_requires_worker_scope_and_repository_authority(self):
        service = FactoryService(FakeExecutionStore())
        for actor in (
            Actor("worker-01", "worker", frozenset({"task:claim"}), frozenset({"owner/repository"})),
            Actor("operator", "operator", frozenset({"task:claim", "task:execute"}), frozenset({"owner/repository"})),
            Actor("worker-01", "worker", frozenset({"task:claim", "task:execute"}), frozenset({"other/repository"})),
        ):
            with self.subTest(actor=actor), self.assertRaises(AuthorizationError):
                service.claim_execution(owner=actor.actor_id, role=RunRole.WRITER, repositories=("owner/repository",), lease_seconds=60, selection=selection(), actor=actor, now=NOW)

    def test_stage_advance_binds_legacy_grant_and_new_packet_digest(self):
        store = FakeExecutionStore()
        service = FactoryService(store)
        result = service.advance_execution(
            GRANT,
            packet_digest="d" * 64,
            stage=ExecutionStage.RUNNING,
            actor=WORKER,
            idempotency_key="e" * 64,
            correlation_id="correlation-002",
        )
        self.assertEqual(result, ExecutionStage.RUNNING)
        self.assertEqual(store.calls[-1][2], "d" * 64)

    def test_generic_stage_advance_cannot_terminalize_without_workspace_result(self):
        service = FactoryService(FakeExecutionStore())
        for stage in (
            ExecutionStage.COMPLETED, ExecutionStage.FAILED, ExecutionStage.NEEDS_HUMAN,
            ExecutionStage.CANCELLED, ExecutionStage.ORPHANED,
        ):
            with self.subTest(stage=stage), self.assertRaisesRegex(ExecutionContractError, "terminal_requires_finalize"):
                service.advance_execution(GRANT, packet_digest="d" * 64, stage=stage, actor=WORKER)

    def test_finalize_requires_trusted_snapshot_and_returns_factual_result(self):
        store = FakeExecutionStore()
        service = FactoryService(store, snapshot_broker=UnavailableSnapshotBroker())
        with self.assertRaisesRegex(ExecutionContractError, "workspace_snapshot_unavailable"):
            service.finalize_execution(
                GRANT, packet_digest="d" * 64, actor=WORKER,
            )
        self.assertEqual(tuple(item[0] for item in store.calls), ("finalization_replay", "snapshot_request"))
        broker = TrustedTestSnapshotBroker()
        service = FactoryService(store, snapshot_broker=broker)
        result = service.finalize_execution(
            GRANT, packet_digest="d" * 64, actor=WORKER,
            idempotency_key="f" * 64, correlation_id="finalize-001",
        )
        replay = service.finalize_execution(
            GRANT, packet_digest="d" * 64, actor=WORKER,
            idempotency_key="f" * 64, correlation_id="finalize-001",
        )
        self.assertEqual(result.exact_head_sha, "f" * 40)
        self.assertEqual(replay.workspace_result_digest, result.workspace_result_digest)
        self.assertEqual(tuple(item[0] for item in store.calls), (
            "finalization_replay", "snapshot_request", "finalization_replay", "snapshot_request", "finalize",
            "finalization_replay",
        ))
        self.assertEqual(broker.calls, 1)
        with self.assertRaises(TypeError):
            service.finalize_execution(
                GRANT, packet_digest="d" * 64, snapshot=WorkspaceSnapshotUnavailable(), actor=WORKER,
            )

    def test_workspace_result_query_requires_read_scope_and_repository(self):
        service = FactoryService(FakeExecutionStore())
        denied = (
            Actor("worker-01", "worker", frozenset(), frozenset({"owner/repository"})),
            Actor("reader", "operator", frozenset({"task:read"}), frozenset({"other/repository"})),
        )
        for actor in denied:
            with self.subTest(actor=actor), self.assertRaises(AuthorizationError):
                service.get_workspace_result(GRANT.task_id, "f" * 64, actor=actor)
        reader = Actor("reader", "operator", frozenset({"task:read"}), frozenset({"owner/repository"}))
        self.assertEqual(
            service.get_workspace_result(GRANT.task_id, "f" * 64, actor=reader),
            {"result": "f" * 64},
        )

    def test_proposal_is_validated_redacted_and_committed_under_live_grant(self):
        store = FakeExecutionStore()
        proposal = FactoryService(store).commit_execution_proposal(
            GRANT,
            packet_digest="d" * 64,
            sequence=3,
            event_type="note.proposed",
            payload={"note_type": "finding", "body": "token ghp_abcdefghijk", "evidence": ["factory/src"]},
            actor=WORKER,
            correlation_id="correlation-003",
        )
        self.assertEqual(proposal.body, "token [REDACTED]")
        self.assertEqual(tuple(item[0] for item in store.calls), ("proposal_context", "proposal"))
        self.assertNotIn("ghp_", repr(store.calls[-1]))

    def test_proposal_identity_and_payload_are_closed_before_store_commit(self):
        store = FakeExecutionStore()
        with self.assertRaisesRegex(ValueError, "note_fields"):
            FactoryService(store).commit_execution_proposal(
                GRANT,
                packet_digest="d" * 64,
                sequence=1,
                event_type="note.proposed",
                payload={"note_type": "finding", "body": "safe", "evidence": [], "command": "push"},
                actor=WORKER,
            )
        self.assertEqual(tuple(item[0] for item in store.calls), ("proposal_context",))


if __name__ == "__main__":
    unittest.main()
