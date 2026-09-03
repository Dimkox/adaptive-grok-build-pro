from datetime import datetime, timezone
import unittest

from adaptive_factory.adapters import AdapterConformance, AdapterRegistry, TrustedExecutionProfile
from adaptive_factory.contracts import canonical_digest
from adaptive_factory.execution_contracts import ExecutionContractError, ExecutionSelectionV1, WorkspaceResultV1
from adaptive_factory.models import Actor, ExecutionStage, FailureClass, LeaseGrant, RunRole, TaskStatus
from adaptive_factory.service import (
    AuthorizationError,
    FactoryService,
    SnapshotBrokerIntegrityError,
    SnapshotBrokerUnavailable,
)
from adaptive_factory.brokers import ProposalContext
from adaptive_factory.store import FenceError, StoreError
from adaptive_factory.workspace import (
    ArtifactAttestationUnavailable,
    ArtifactAttestationV1,
    WorkspaceSnapshotRequest,
    WorkspaceSnapshotUnavailable,
    WorkspaceSnapshotV1,
)
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


def trusted_registry(value=None, *, roles=("reader", "writer")):
    selected = ExecutionSelectionV1.from_dict(value or selection())
    provider = selected.provider
    conformance = AdapterConformance(
        provider_id=provider.provider_id,
        native_version=provider.native_version,
        distribution_digest_hint=provider.native_digest,
        capabilities=provider.capabilities,
        missing_capabilities=(),
        fixture_conformant=True,
        execution_eligible=True,
        adapter_id=provider.adapter_id,
        adapter_version=provider.adapter_version,
        adapter_digest=provider.adapter_digest,
        native_digest=provider.native_digest,
    )
    return AdapterRegistry((TrustedExecutionProfile(selected, conformance, roles),))


class FakeExecutionStore:
    def __init__(self, *, grant=GRANT, start_error=None):
        self.calls = []
        self.finalized = {}
        self.proposal_commands = {}
        self.terminal_commands = {}
        self.grant = grant
        self.start_error = start_error

    def claim(self, request, actor, now, **kwargs):
        self.calls.append(("claim", request, actor, kwargs))
        return self.grant

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
        if self.start_error is not None:
            raise self.start_error
        from adaptive_factory.models import ExecutionGrant
        return ExecutionGrant(grant, packet.packet_digest, manifest.manifest_digest, manifest.workspace_handle, manifest.provider_id, ExecutionStage.PREPARED)

    def release(self, grant, outcome, actor, now, **kwargs):
        self.calls.append(("release", grant, outcome, actor, now, kwargs))
        return TaskStatus.RETRY if outcome is FailureClass.DATABASE_UNAVAILABLE else TaskStatus.NEEDS_HUMAN

    def advance_execution(self, grant, packet_digest, stage, actor, **kwargs):
        self.calls.append(("advance", grant, packet_digest, stage, actor, kwargs))
        return stage

    def proposal_context(self, grant, packet_digest):
        self.calls.append(("proposal_context", grant, packet_digest))
        return ProposalContext(
            grant.task_id, grant.run_id, grant.owner, grant.fence, packet_digest,
            grant.role.value, "owner/repository", "workspace:" + "d" * 64,
            ("artifacts", "factory/src"), ("patch", "report"), 65_536, 1_000_000,
            1_000_000, 1_000_000, 100_000, ("artifacts", "notes", "structured_output", "usage"),
        )

    def commit_execution_proposal(self, grant, proposal, actor, **kwargs):
        self.calls.append(("proposal", grant, proposal, actor, kwargs))
        key = kwargs.get("idempotency_key")
        if key is not None:
            self.proposal_commands[key] = (kwargs["event"].to_dict(), proposal)
        return proposal

    def execution_proposal_replay(self, grant, event, actor, *, idempotency_key):
        self.calls.append(("proposal_replay", grant, event, actor, idempotency_key))
        if idempotency_key not in self.proposal_commands:
            return None
        prior_event, proposal = self.proposal_commands[idempotency_key]
        if prior_event != event.to_dict():
            raise StoreError("idempotency key reused with different command")
        return proposal

    def begin_execution_terminal_composite(
        self,
        grant,
        event,
        actor,
        *,
        proposal_key,
        finalize_key,
        idempotency_key,
        correlation_id,
    ):
        self.calls.append(
            (
                "terminal_begin",
                grant,
                event,
                actor,
                proposal_key,
                finalize_key,
                idempotency_key,
                correlation_id,
            )
        )
        marker = (event.to_dict(), proposal_key, finalize_key)
        prior = self.terminal_commands.get(idempotency_key)
        if prior is not None and prior != marker:
            raise StoreError("idempotency key reused with different command")
        self.terminal_commands[idempotency_key] = marker

    def record_fence_rejection(self):
        self.calls.append(("fence_rejection",))

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
    def snapshot(self, _request, *, timeout_seconds):
        return WorkspaceSnapshotUnavailable()


class TrustedTestSnapshotBroker:
    def __init__(self):
        self.calls = 0
        self.timeouts = []
        self.available = True
        self.repository_id = None

    def snapshot(self, request, *, timeout_seconds):
        self.calls += 1
        self.timeouts.append(timeout_seconds)
        if not self.available:
            return WorkspaceSnapshotUnavailable()
        return WorkspaceSnapshotV1.from_facts({
            "contract_version": 1,
            "repository_id": self.repository_id or request.repository_id,
            "workspace_handle": request.workspace_handle,
            "input_head_sha": request.input_head_sha, "result_head_sha": "f" * 40,
            "diff_digest": "e" * 64, "diff_lines": 12, "source": "trusted_git_broker",
        })


class TrustedTestArtifactBroker:
    def __init__(self):
        self.calls = 0
        self.available = True

    def attest_artifact(self, request):
        self.calls += 1
        if not self.available:
            return ArtifactAttestationUnavailable()
        return ArtifactAttestationV1.from_facts({
            "contract_version": 1,
            **request.to_dict(),
            "source": "trusted_workspace_broker",
        })


class TrustedTestArtifactAttestationStore:
    def __init__(self):
        self.calls = 0

    def record_artifact_attestation(self, attestation):
        self.calls += 1
        return attestation


class ExecutionServiceTests(unittest.TestCase):
    def test_self_asserted_selection_is_rejected_without_trusted_registry(self):
        store = FakeExecutionStore()
        with self.assertRaisesRegex(ExecutionContractError, "provider_ineligible"):
            FactoryService(store).claim_execution(
                owner=WORKER.actor_id,
                role=RunRole.WRITER,
                repositories=("owner/repository",),
                lease_seconds=60,
                selection=selection(),
                actor=WORKER,
                now=NOW,
            )
        self.assertEqual(store.calls, [])

    def test_explicit_execution_claim_preserves_legacy_digest_and_persists_manifest(self):
        store = FakeExecutionStore()
        result = FactoryService(store, execution_registry=trusted_registry()).claim_execution(
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

    def test_reader_selection_cannot_request_write_capabilities(self):
        store = FakeExecutionStore()
        with self.assertRaisesRegex(ExecutionContractError, "role_capability_forbidden"):
            FactoryService(store, execution_registry=trusted_registry()).claim_execution(
                owner=WORKER.actor_id,
                role=RunRole.READER,
                repositories=("owner/repository",),
                lease_seconds=60,
                selection=selection(),
                actor=WORKER,
                now=NOW,
            )
        self.assertEqual(store.calls, [])

    def test_post_claim_start_failure_releases_capacity_with_typed_outcome(self):
        store = FakeExecutionStore(start_error=RuntimeError("packet persistence unavailable"))
        with self.assertRaisesRegex(RuntimeError, "packet persistence unavailable"):
            FactoryService(store, execution_registry=trusted_registry()).claim_execution(
                owner=WORKER.actor_id,
                role=RunRole.WRITER,
                repositories=("owner/repository",),
                lease_seconds=60,
                selection=selection(),
                actor=WORKER,
                now=NOW,
                idempotency_key="b" * 64,
                correlation_id="claim-cleanup",
            )
        self.assertEqual(tuple(item[0] for item in store.calls), ("claim", "material", "start", "release"))
        self.assertIs(store.calls[-1][2], FailureClass.DATABASE_UNAVAILABLE)

    def test_claimed_role_mismatch_fails_closed_and_releases_capacity(self):
        forged = LeaseGrant(
            GRANT.task_id, GRANT.run_id, GRANT.owner, RunRole.READER,
            GRANT.fence, GRANT.expires_at, GRANT.packet_digest,
        )
        store = FakeExecutionStore(grant=forged)
        with self.assertRaisesRegex(ExecutionContractError, "grant_identity_mismatch"):
            FactoryService(store, execution_registry=trusted_registry()).claim_execution(
                owner=WORKER.actor_id,
                role=RunRole.WRITER,
                repositories=("owner/repository",),
                lease_seconds=60,
                selection=selection(),
                actor=WORKER,
                now=NOW,
            )
        self.assertEqual(tuple(item[0] for item in store.calls), ("claim", "release"))

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
        missing_store = FakeExecutionStore()
        with self.assertRaises(SnapshotBrokerUnavailable):
            FactoryService(missing_store).finalize_execution(
                GRANT,
                packet_digest="d" * 64,
                actor=WORKER,
                idempotency_key="0" * 64,
            )
        self.assertEqual(
            tuple(item[0] for item in missing_store.calls),
            ("finalization_replay", "finalization_replay"),
        )
        store = FakeExecutionStore()
        service = FactoryService(store, snapshot_broker=UnavailableSnapshotBroker())
        with self.assertRaisesRegex(
            SnapshotBrokerUnavailable, "trusted workspace snapshot unavailable"
        ):
            service.finalize_execution(
                GRANT, packet_digest="d" * 64, actor=WORKER,
            )
        self.assertEqual(
            tuple(item[0] for item in store.calls),
            ("finalization_replay", "snapshot_request", "finalization_replay"),
        )
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
            "finalization_replay", "snapshot_request", "finalization_replay",
            "finalization_replay", "snapshot_request", "finalize",
            "finalization_replay",
        ))
        self.assertEqual(broker.calls, 1)
        with self.assertRaises(TypeError):
            service.finalize_execution(
                GRANT, packet_digest="d" * 64, snapshot=WorkspaceSnapshotUnavailable(), actor=WORKER,
            )

    def test_terminal_composite_derives_phase_keys_and_replays_without_snapshot(self):
        store = FakeExecutionStore()
        broker = TrustedTestSnapshotBroker()
        service = FactoryService(store, snapshot_broker=broker)
        outer_key = "b" * 64
        payload = {"summary": "complete"}

        first = service.commit_terminal_and_finalize(
            GRANT,
            packet_digest="d" * 64,
            sequence=1,
            event_type="run.completed",
            payload=payload,
            actor=WORKER,
            idempotency_key=outer_key,
            correlation_id="terminal-001",
        )
        replay = service.commit_terminal_and_finalize(
            GRANT,
            packet_digest="d" * 64,
            sequence=1,
            event_type="run.completed",
            payload=dict(payload),
            actor=WORKER,
            idempotency_key=outer_key,
            correlation_id="terminal-001",
        )

        proposal_key = canonical_digest(
            {
                "contract": "adaptive-factory.execution-terminal-phase/v1",
                "command": outer_key,
                "phase": "proposal",
            }
        )
        finalize_key = canonical_digest(
            {
                "contract": "adaptive-factory.execution-terminal-phase/v1",
                "command": outer_key,
                "phase": "finalize",
            }
        )
        self.assertNotEqual(proposal_key, finalize_key)
        self.assertEqual(first.proposal, replay.proposal)
        self.assertEqual(first.result, replay.result)
        self.assertEqual(broker.calls, 1)
        self.assertEqual(broker.timeouts, [5.0])
        self.assertIn(proposal_key, store.proposal_commands)
        self.assertIn(finalize_key, store.finalized)
        self.assertEqual(
            tuple(item[0] for item in store.calls),
            (
                "terminal_begin",
                "proposal_replay",
                "proposal_context",
                "proposal",
                "finalization_replay",
                "snapshot_request",
                "finalize",
                "terminal_begin",
                "proposal_replay",
                "finalization_replay",
            ),
        )

    def test_terminal_composite_records_stale_outer_marker_fence_before_broker(self):
        store = FakeExecutionStore()
        broker = TrustedTestSnapshotBroker()
        service = FactoryService(store, snapshot_broker=broker)

        def stale(*args, **kwargs):
            raise FenceError("stale execution fence")

        store.begin_execution_terminal_composite = stale
        with self.assertRaisesRegex(FenceError, "stale execution fence"):
            service.commit_terminal_and_finalize(
                GRANT,
                packet_digest="d" * 64,
                sequence=1,
                event_type="run.completed",
                payload={"summary": "complete"},
                actor=WORKER,
                idempotency_key="9" * 64,
                correlation_id="terminal-stale",
            )

        self.assertEqual(store.calls, [("fence_rejection",)])
        self.assertEqual(broker.calls, 0)

    def test_terminal_composite_resumes_after_snapshot_failure_and_conflicts_before_broker(self):
        store = FakeExecutionStore()
        broker = TrustedTestSnapshotBroker()
        broker.available = False
        service = FactoryService(store, snapshot_broker=broker)
        outer_key = "c" * 64
        arguments = {
            "packet_digest": "d" * 64,
            "sequence": 1,
            "event_type": "run.failed",
            "payload": {"failure_class": "validation", "diagnostic": "bounded"},
            "actor": WORKER,
            "idempotency_key": outer_key,
            "correlation_id": "terminal-resume",
        }

        with self.assertRaisesRegex(
            SnapshotBrokerUnavailable, "trusted workspace snapshot unavailable"
        ):
            service.commit_terminal_and_finalize(GRANT, **arguments)
        self.assertEqual((len(store.proposal_commands), len(store.finalized)), (1, 0))
        with self.assertRaisesRegex(StoreError, "different command"):
            service.commit_terminal_and_finalize(
                GRANT,
                **{
                    **arguments,
                    "payload": {
                        "failure_class": "validation",
                        "diagnostic": "changed",
                    },
                },
            )
        self.assertEqual(broker.calls, 1)

        broker.available = True
        completed = service.commit_terminal_and_finalize(GRANT, **arguments)
        replay = service.commit_terminal_and_finalize(GRANT, **arguments)
        self.assertEqual(completed, replay)
        self.assertEqual((broker.calls, len(store.proposal_commands), len(store.finalized)), (2, 1, 1))

    def test_terminal_composite_rejects_mismatched_snapshot_then_resumes_all_variants(self):
        variants = (
            ("run.completed", {"summary": "complete"}),
            (
                "run.failed",
                {"failure_class": "validation", "diagnostic": "bounded"},
            ),
            (
                "run.needs_human",
                {"reason": "review", "diagnostic": "bounded"},
            ),
        )
        for index, (event_type, payload) in enumerate(variants):
            with self.subTest(event_type=event_type):
                store = FakeExecutionStore()
                broker = TrustedTestSnapshotBroker()
                broker.repository_id = "other/repository"
                service = FactoryService(store, snapshot_broker=broker)
                arguments = {
                    "packet_digest": "d" * 64,
                    "sequence": 1,
                    "event_type": event_type,
                    "payload": payload,
                    "actor": WORKER,
                    "idempotency_key": f"{index + 1:x}" * 64,
                    "correlation_id": f"terminal-variant-{index}",
                }
                with self.assertRaisesRegex(
                    SnapshotBrokerIntegrityError,
                    "trusted workspace snapshot binding mismatch",
                ):
                    service.commit_terminal_and_finalize(GRANT, **arguments)
                self.assertEqual(len(store.finalized), 0)
                broker.repository_id = None
                completion = service.commit_terminal_and_finalize(GRANT, **arguments)
                self.assertEqual(completion.proposal.terminal_type, event_type)
                self.assertIsInstance(completion.result, WorkspaceResultV1)

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
        self.assertEqual(
            tuple(item[0] for item in store.calls),
            ("proposal_replay", "proposal_context", "proposal"),
        )
        self.assertNotIn("ghp_", repr(store.calls[-1][2]))

    def test_artifact_proposal_fails_closed_without_server_attestation(self):
        store = FakeExecutionStore()
        payload = {
            "artifact_class": "report",
            "path": "artifacts/report.json",
            "sha256": "e" * 64,
            "size_bytes": 12,
            "media_type": "application/json",
        }
        for service in (
            FactoryService(store),
            FactoryService(store, artifact_broker=TrustedTestArtifactBroker()),
        ):
            with self.assertRaisesRegex(ExecutionContractError, "artifact_attestation_unavailable"):
                service.commit_execution_proposal(
                GRANT,
                packet_digest="d" * 64,
                sequence=1,
                event_type="artifact.proposed",
                payload=payload,
                actor=WORKER,
            )
        self.assertEqual(tuple(item[0] for item in store.calls).count("proposal"), 0)

    def test_forbidden_artifact_never_reaches_trusted_broker_or_attestation_store(self):
        broker = TrustedTestArtifactBroker()
        attestation_store = TrustedTestArtifactAttestationStore()
        service = FactoryService(
            FakeExecutionStore(),
            artifact_broker=broker,
            artifact_attestation_store=attestation_store,
        )
        valid = {
            "artifact_class": "report",
            "path": "artifacts/report.json",
            "sha256": "e" * 64,
            "size_bytes": 12,
            "media_type": "application/json",
        }
        invalid = (
            {**valid, "artifact_class": "undeclared"},
            {**valid, "path": "outside/report.json"},
            {**valid, "sha256": "invalid"},
            {**valid, "size_bytes": 1_000_001},
            {**valid, "media_type": "INVALID"},
        )
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                service.commit_execution_proposal(
                    GRANT,
                    packet_digest="d" * 64,
                    sequence=1,
                    event_type="artifact.proposed",
                    payload=payload,
                    actor=WORKER,
                )
        self.assertEqual((broker.calls, attestation_store.calls), (0, 0))

    def test_trusted_artifact_attestation_is_exact_and_replay_precedes_broker(self):
        store = FakeExecutionStore()
        broker = TrustedTestArtifactBroker()
        attestation_store = TrustedTestArtifactAttestationStore()
        service = FactoryService(
            store, artifact_broker=broker,
            artifact_attestation_store=attestation_store,
        )
        payload = {
            "artifact_class": "report",
            "path": "artifacts/report.json",
            "sha256": "e" * 64,
            "size_bytes": 12,
            "media_type": "application/json",
        }
        first = service.commit_execution_proposal(
            GRANT, packet_digest="d" * 64, sequence=1,
            event_type="artifact.proposed", payload=payload, actor=WORKER,
            idempotency_key="a" * 64,
        )
        self.assertEqual((first.author_role, len(first.artifact_attestation_digest)), ("writer", 64))
        broker.available = False
        replay = service.commit_execution_proposal(
            GRANT, packet_digest="d" * 64, sequence=1,
            event_type="artifact.proposed", payload=dict(payload), actor=WORKER,
            idempotency_key="a" * 64,
        )
        self.assertEqual(replay, first)
        self.assertEqual(broker.calls, 1)
        self.assertEqual(attestation_store.calls, 1)
        before = tuple(item[0] for item in store.calls)
        changed = dict(payload, sha256="f" * 64)
        with self.assertRaisesRegex(StoreError, "different command"):
            service.commit_execution_proposal(
                GRANT, packet_digest="d" * 64, sequence=1,
                event_type="artifact.proposed", payload=changed, actor=WORKER,
                idempotency_key="a" * 64,
            )
        self.assertEqual(broker.calls, 1)
        self.assertEqual(tuple(item[0] for item in store.calls)[len(before):], ("proposal_replay",))

    def test_proposal_identity_and_payload_are_closed_before_store_commit(self):
        store = FakeExecutionStore()
        with self.assertRaisesRegex(ValueError, "payload_fields"):
            FactoryService(store).commit_execution_proposal(
                GRANT,
                packet_digest="d" * 64,
                sequence=1,
                event_type="note.proposed",
                payload={"note_type": "finding", "body": "safe", "evidence": [], "command": "push"},
                actor=WORKER,
            )
        self.assertEqual(store.calls, [])

    def test_direct_service_structured_text_is_rejected_before_replay(self):
        cases = (
            (
                "note.proposed",
                {"note_type": "finding", "body": {"reasoning": "private"}, "evidence": []},
            ),
            ("run.completed", {"summary": {"reasoning": "private"}}),
        )
        for event_type, payload in cases:
            store = FakeExecutionStore()
            with self.subTest(event_type=event_type), self.assertRaisesRegex(
                ValueError, "forbidden_content"
            ):
                FactoryService(store).commit_execution_proposal(
                    GRANT, packet_digest="d" * 64, sequence=1,
                    event_type=event_type, payload=payload, actor=WORKER,
                    idempotency_key="b" * 64,
                )
            self.assertEqual(store.calls, [])

    def test_proposal_payload_is_frozen_before_replay_boundary(self):
        payload = {"note_type": "finding", "body": "original", "evidence": []}
        store = FakeExecutionStore()
        original_replay = store.execution_proposal_replay

        def mutating_replay(*args, **kwargs):
            payload["body"] = "mutated after validation"
            return original_replay(*args, **kwargs)

        store.execution_proposal_replay = mutating_replay
        proposal = FactoryService(store).commit_execution_proposal(
            GRANT, packet_digest="d" * 64, sequence=1,
            event_type="note.proposed", payload=payload, actor=WORKER,
        )
        self.assertEqual(proposal.body, "original")

    def test_proposal_replay_still_requires_scope_kind_owner_and_repository(self):
        store = FakeExecutionStore()
        service = FactoryService(store)
        payload = {"note_type": "finding", "body": "safe", "evidence": []}
        service.commit_execution_proposal(
            GRANT, packet_digest="d" * 64, sequence=1,
            event_type="note.proposed", payload=payload, actor=WORKER,
            idempotency_key="b" * 64,
        )
        denied = (
            Actor("worker-01", "worker", frozenset(), frozenset({"owner/repository"})),
            Actor("worker-01", "operator", frozenset({"task:execute"}), frozenset({"owner/repository"})),
            Actor("other-worker", "worker", frozenset({"task:execute"}), frozenset({"owner/repository"})),
            Actor("worker-01", "worker", frozenset({"task:execute"}), frozenset({"other/repository"})),
        )
        for actor in denied:
            store.calls.clear()
            with self.subTest(actor=actor), self.assertRaises(AuthorizationError):
                service.commit_execution_proposal(
                    GRANT, packet_digest="d" * 64, sequence=1,
                    event_type="note.proposed", payload=dict(payload), actor=actor,
                    idempotency_key="b" * 64,
                )
            self.assertEqual(store.calls, [])


if __name__ == "__main__":
    unittest.main()
