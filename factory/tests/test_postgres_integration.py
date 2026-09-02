from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import os
import threading
import time
import unittest
import uuid

from fastapi.testclient import TestClient

from adaptive_factory.migrations import PostgresMigrator, discover_migrations
from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.brokers import (
    ArtifactProposal,
    NoteProposal,
    TerminalProposal,
    UsageProposal,
    proposal_idempotency_key,
)
from adaptive_factory.contracts import canonical_digest, canonical_json
from adaptive_factory.execution_contracts import WorkspaceResultV1, workspace_evidence_digest
from adaptive_factory.models import Actor, ExecutionStage, FailureClass, RunRole, TaskStatus
from adaptive_factory.protocol import CanonicalEvent
from adaptive_factory.recovery import ExecutionRecovery
from adaptive_factory.semantic_bridge import SemanticBridgeResult
from adaptive_factory.service import AuthorizationError, ExecutionContractError, FactoryService
from adaptive_factory.store import (
    BudgetError,
    FenceError,
    PostgresArtifactAttestationStore,
    PostgresFactoryStore,
    PostgresSemanticCoordinatorStore,
    StoreError,
)
from adaptive_factory.workspace import (
    ArtifactAttestationRequest,
    ArtifactAttestationUnavailable,
    ArtifactAttestationV1,
    FakeWorkspaceBroker,
    WorkspaceHandle,
    WorkspacePolicy,
    WorkspaceSnapshotV1,
)
from factory.tests.test_contracts import valid_intake
from factory.tests.test_execution_contracts import valid_packet
from factory.tests.test_execution_service import trusted_registry


DATABASE_URL = os.environ.get("FACTORY_TEST_DATABASE_URL")
NOW = datetime.now(timezone.utc).replace(microsecond=0)
OPERATOR = Actor(
    "operator",
    "operator",
    frozenset({"task:submit", "task:cancel", "factory:kill", "factory:reconcile"}),
    frozenset({"*"}),
)
WORKER = Actor(
    "worker", "worker", frozenset({"task:claim", "task:execute", "task:heartbeat", "task:release", "task:budget"}), frozenset({"*"})
)


class TrustedPostgresTestSnapshotBroker:
    def __init__(self):
        self.calls = 0

    def snapshot(self, request):
        self.calls += 1
        return WorkspaceSnapshotV1.from_facts({
            "contract_version": 1, "repository_id": request.repository_id,
            "workspace_handle": request.workspace_handle,
            "input_head_sha": request.input_head_sha, "result_head_sha": "4" * 40,
            "diff_digest": "6" * 64, "diff_lines": 12, "source": "trusted_git_broker",
        })


class TrustedPostgresTestArtifactBroker:
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


class CountingArtifactAttestationStore(PostgresArtifactAttestationStore):
    def __init__(self, database_url):
        super().__init__(database_url)
        self.calls = 0

    def record_artifact_attestation(self, attestation):
        self.calls += 1
        return super().record_artifact_attestation(attestation)


@unittest.skipUnless(DATABASE_URL, "FACTORY_TEST_DATABASE_URL must name a disposable database")
class PostgresFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        PostgresMigrator(DATABASE_URL).apply()
        from adaptive_factory.admin import (
            provision_artifact_attestor_login,
            provision_runtime_login,
            provision_semantic_coordinator_login,
        )
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        cls.artifact_attestor_login = f"factory_artifact_test_{os.getpid()}"
        cls.runtime_login = f"factory_runtime_test_{os.getpid()}"
        cls.semantic_coordinator_login = f"factory_semantic_test_{os.getpid()}"
        cls.artifact_attestor_password = "local-artifact-attestor-test"
        cls.runtime_password = "local-runtime-store-test"
        cls.semantic_coordinator_password = "local-semantic-coordinator-test"
        provision_runtime_login(DATABASE_URL, cls.runtime_login, cls.runtime_password)
        provision_artifact_attestor_login(
            DATABASE_URL, cls.artifact_attestor_login, cls.artifact_attestor_password,
            runtime_login="factory_service_test",
        )
        provision_semantic_coordinator_login(
            DATABASE_URL,
            cls.semantic_coordinator_login,
            cls.semantic_coordinator_password,
        )
        cls.artifact_attestor_url = make_conninfo(**{
            **conninfo_to_dict(DATABASE_URL),
            "user": cls.artifact_attestor_login,
            "password": cls.artifact_attestor_password,
        })
        cls.runtime_url = make_conninfo(**{
            **conninfo_to_dict(DATABASE_URL),
            "user": cls.runtime_login,
            "password": cls.runtime_password,
        })
        cls.semantic_coordinator_url = make_conninfo(**{
            **conninfo_to_dict(DATABASE_URL),
            "user": cls.semantic_coordinator_login,
            "password": cls.semantic_coordinator_password,
        })

    @classmethod
    def tearDownClass(cls):
        import psycopg
        from psycopg import sql

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            cursor.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM {}").format(
                sql.Identifier(cursor.fetchone()[0]), sql.Identifier(cls.runtime_login),
            ))
            cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(
                sql.Identifier(cls.artifact_attestor_login)
            ))
            cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(
                sql.Identifier(cls.semantic_coordinator_login)
            ))
            cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(
                sql.Identifier(cls.runtime_login)
            ))

    def setUp(self):
        import psycopg

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "TRUNCATE factory.semantic_recovery_records, factory.semantic_child_proposals, factory.semantic_directives, factory.semantic_verdicts, factory.semantic_coverage, factory.semantic_findings, factory.semantic_assignments, factory.semantic_metric_events, factory.semantic_command_results, factory.semantic_subjects, factory.execution_recovery_cleanup_successes, factory.execution_recovery_cleanup_failures, factory.workspace_results, factory.execution_proposals, factory.execution_artifact_attestations, factory.execution_stage_events, factory.execution_manifests, factory.execution_packets, factory.audit_log, factory.audit_heads, factory.task_events, factory.command_results, factory.metric_counters, factory.budget_reservations, factory.usage_observations, factory.capacity_allocations, factory.attempts, factory.runs, factory.lease_sequences, factory.kill_switches, factory.reconciliation_runs, factory.tasks, factory.accepted_intents, factory.intake_identities, factory.m0_authority_observations, factory.m0_bootstrap_exceptions RESTART IDENTITY"
            )
            cursor.execute("SELECT to_regclass('factory.metric_counters_pre_012_untrusted')")
            if cursor.fetchone()[0] is not None:
                cursor.execute("TRUNCATE factory.kill_switch_heads")
                cursor.execute("INSERT INTO factory.metric_counters(singleton) VALUES (true)")
            cursor.execute("UPDATE factory.capacity_counters SET active_count=0")
            cursor.execute(
                "INSERT INTO factory.m0_authority_observations(observation_id,observed_at,check_name,exact_head_sha,issuer,evidence_digest,repository_id,policy_digest) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    uuid.uuid4(),
                    NOW,
                    "adaptive-trust-ci/verified@06ecf1c875bc",
                    "3" * 40,
                    "external-trust-ci-api",
                    "7" * 64,
                    "owner/repository",
                    "06ecf1c875bc" + "9" * 52,
                ),
            )
        self.store = PostgresFactoryStore(self.runtime_url)
        self.service = FactoryService(self.store)

    def payload(self, repository="owner/repository", source=None):
        value = valid_intake()
        value["repository_id"] = repository
        value["source_id"] = source or str(uuid.uuid4())
        value["m0_authority"]["observed_at"] = NOW.isoformat()
        if repository != "owner/repository":
            import psycopg

            observed_at = NOW - timedelta(microseconds=1 + sum(repository.encode("utf-8")))
            value["m0_authority"]["observed_at"] = observed_at.isoformat()
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO factory.m0_authority_observations
                    (observation_id,observed_at,check_name,exact_head_sha,issuer,evidence_digest,repository_id,policy_digest)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (
                        uuid.uuid4(), observed_at, "adaptive-trust-ci/verified@06ecf1c875bc", "3" * 40,
                        "external-trust-ci-api", uuid.uuid4().hex * 2, repository, value["policy_digest"],
                    ),
                )
        return value

    def submit(self, repository="owner/repository", source=None):
        return self.service.intake(self.payload(repository, source), actor=OPERATOR, now=NOW)

    def test_artifact_attestation_and_exact_replay_are_persisted_and_fenced(self):
        import psycopg

        repository = "owner/m5-artifact-attestation"
        task = self.submit(repository=repository, source="m5-artifact-attestation").task
        packet = valid_packet()
        packet["provider"]["capabilities"] = ["artifacts", "notes", "structured_output"]
        selection = {
            "provider": packet["provider"],
            "capability_policy": packet["capability_policy"],
            "plan": packet["plan"],
            "workspace_handle": packet["workspace_handle"],
            "prompt_template_digest": "7" * 64,
            "role_definition_digest": "8" * 64,
            "tool_policy_digest": "9" * 64,
            "output_schema_digest": "a" * 64,
        }
        execution = FactoryService(
            self.store, execution_registry=trusted_registry(selection)
        ).claim_execution(
            owner=WORKER.actor_id, role=RunRole.WRITER,
            repositories=(repository,), lease_seconds=60,
            selection=selection, actor=WORKER, now=NOW,
        )
        broker = TrustedPostgresTestArtifactBroker()
        attestation_store = CountingArtifactAttestationStore(self.artifact_attestor_url)
        service = FactoryService(
            self.store, artifact_broker=broker,
            artifact_attestation_store=attestation_store,
        )
        payload = {
            "artifact_class": "report",
            "path": "factory/src/change.patch",
            "sha256": "b" * 64,
            "size_bytes": 12,
            "media_type": "text/plain",
        }
        api_idempotency = "artifact-replay-001"
        command_key = canonical_digest({
            "contract": "adaptive-factory.command/v1",
            "idempotency_key": api_idempotency,
        })
        artifact = service.commit_execution_proposal(
            execution.lease, packet_digest=execution.packet_digest,
            sequence=1, event_type="artifact.proposed", payload=payload,
            actor=WORKER, idempotency_key=command_key,
        )
        direct_facts = (
            execution.lease.task_id, execution.lease.run_id, execution.lease.owner,
            execution.lease.fence, execution.lease.packet_digest, execution.packet_digest,
        )
        forged_role = replace(artifact, sequence=2, author_role="reader", idempotency_key="0" * 64)
        forged_role = replace(
            forged_role, idempotency_key=proposal_idempotency_key(forged_role)
        )
        forged_attestation = replace(
            artifact, sequence=2, artifact_attestation_digest="f" * 64,
            idempotency_key="0" * 64,
        )
        forged_attestation = replace(
            forged_attestation,
            idempotency_key=proposal_idempotency_key(forged_attestation),
        )
        reused_attestation = replace(artifact, sequence=2, idempotency_key="0" * 64)
        reused_attestation = replace(
            reused_attestation,
            idempotency_key=proposal_idempotency_key(reused_attestation),
        )
        for forged in (
            dict(forged_role.__dict__), dict(forged_attestation.__dict__),
            dict(reused_attestation.__dict__),
        ):
            with self.subTest(forged=forged["author_role"] + forged["path"]):
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute("SET ROLE factory_runtime")
                    cursor.execute(
                        "SELECT factory.execution_propose(%s,%s,%s,%s,%s,%s,2,%s,'artifact',%s::jsonb)",
                        (*direct_facts, forged["idempotency_key"], psycopg.types.json.Jsonb(forged)),
                    )
                    self.assertFalse(cursor.fetchone()[0])
        for secret in (
            "OPENAI_API_KEY=fixture",
            "-----BEGIN PRIVATE KEY-----\nfixture\n-----END PRIVATE KEY-----",
        ):
            forged_note = NoteProposal(
                execution.lease.task_id, execution.lease.run_id, execution.packet_digest,
                execution.lease.fence, 2, "writer", "finding", secret, (), "0" * 64,
            )
            forged_note = replace(
                forged_note, idempotency_key=proposal_idempotency_key(forged_note)
            )
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute("SET ROLE factory_runtime")
                cursor.execute(
                    "SELECT factory.execution_propose(%s,%s,%s,%s,%s,%s,2,%s,'note',%s::jsonb)",
                    (
                        *direct_facts, forged_note.idempotency_key,
                        psycopg.types.json.Jsonb(dict(forged_note.__dict__)),
                    ),
                )
                self.assertFalse(cursor.fetchone()[0])
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                has_table_privilege('factory_runtime','factory.execution_proposals','SELECT'),
                has_function_privilege(
                  'factory_runtime',
                  'factory.execution_proposal_by_key(uuid,uuid,character)',
                  'EXECUTE'
                )"""
            )
            self.assertEqual(cursor.fetchone(), (False, True))
            cursor.execute(
                "SELECT count(*) FROM factory.execution_proposals WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone()[0], 1)
        terminal = self.service.commit_execution_proposal(
            execution.lease, packet_digest=execution.packet_digest,
            sequence=2, event_type="run.failed",
            payload={"failure_class": "validation", "diagnostic": "fixture terminal"},
            actor=WORKER, idempotency_key="c" * 64,
        )
        FactoryService(
            self.store, snapshot_broker=TrustedPostgresTestSnapshotBroker()
        ).finalize_execution(
            execution.lease, packet_digest=execution.packet_digest, actor=WORKER,
        )
        broker.available = False
        replay = service.commit_execution_proposal(
            execution.lease, packet_digest=execution.packet_digest,
            sequence=1, event_type="artifact.proposed", payload=dict(payload),
            actor=WORKER, idempotency_key=command_key,
        )
        self.assertEqual(replay, artifact)
        self.assertEqual(broker.calls, 1)
        self.assertEqual(attestation_store.calls, 1)
        event = CanonicalEvent.from_payload(
            task_id=execution.lease.task_id, run_id=execution.lease.run_id,
            packet_digest=execution.packet_digest, sequence=1,
            event_type="artifact.proposed", payload=payload,
        )
        alternate = replace(
            artifact, artifact_attestation_digest="f" * 64,
            idempotency_key="0" * 64,
        )
        alternate = replace(
            alternate, idempotency_key=proposal_idempotency_key(alternate)
        )
        direct_replay = self.store.commit_execution_proposal(
            execution.lease, alternate, WORKER, event=event,
            idempotency_key=command_key,
        )
        self.assertEqual(direct_replay, artifact)
        wrong_event = CanonicalEvent.from_payload(
            task_id=execution.lease.task_id, run_id=execution.lease.run_id,
            packet_digest=execution.packet_digest, sequence=1,
            event_type="note.proposed",
            payload={"note_type": "finding", "body": "safe", "evidence": []},
        )
        with self.assertRaisesRegex(StoreError, "does not match command"):
            self.store.commit_execution_proposal(
                execution.lease, artifact, WORKER, event=wrong_event,
            )
        with self.assertRaisesRegex(StoreError, "different command"):
            service.commit_execution_proposal(
                execution.lease, packet_digest=execution.packet_digest,
                sequence=1, event_type="artifact.proposed",
                payload={**payload, "sha256": "d" * 64}, actor=WORKER,
            idempotency_key=command_key,
            )
        with self.assertRaises(FenceError):
            service.commit_execution_proposal(
                execution.lease, packet_digest=execution.packet_digest,
                sequence=3, event_type="artifact.proposed", payload=payload,
                actor=WORKER, idempotency_key="e" * 64,
            )
        self.assertEqual(broker.calls, 1)
        self.assertEqual(attestation_store.calls, 1)
        self.assertEqual(
            self.store.metrics()[
                "factory_execution_protocol_and_proposal_outcomes_total"
            ]["artifact"],
            1,
        )

        grant_payload = {
            "task_id": execution.lease.task_id, "run_id": execution.lease.run_id,
            "owner": execution.lease.owner, "role": execution.lease.role.value,
            "fence": execution.lease.fence,
            "expires_at": execution.lease.expires_at.isoformat().replace("+00:00", "Z"),
            "packet_digest": execution.lease.packet_digest,
        }
        unauthorized = Actor(
            "worker", "worker", frozenset({"task:execute"}), frozenset({"other/repository"})
        )
        api = TestClient(create_app(
            service, Authenticator({"api-worker": WORKER, "api-unauthorized": unauthorized})
        ))
        api_payload = {
            "grant": grant_payload, "packet_digest": execution.packet_digest, "sequence": 1,
            **payload,
        }
        api_headers = {
            "Authorization": "Bearer api-worker", "Idempotency-Key": api_idempotency,
            "X-Correlation-ID": "artifact-replay-correlation",
        }
        first_api_replay = api.post(
            "/v1/execution/artifacts", headers=api_headers, json=api_payload
        )
        second_api_replay = api.post(
            "/v1/execution/artifacts", headers=api_headers, json=api_payload
        )
        self.assertEqual(first_api_replay.status_code, 200, first_api_replay.text)
        self.assertEqual(second_api_replay.status_code, 200, second_api_replay.text)
        self.assertEqual(second_api_replay.content, first_api_replay.content)
        changed_response = api.post(
            "/v1/execution/artifacts", headers=api_headers,
            json={**api_payload, "sha256": "d" * 64},
        )
        self.assertEqual(changed_response.status_code, 409, changed_response.text)
        unauthorized_response = api.post(
            "/v1/execution/artifacts",
            headers={**api_headers, "Authorization": "Bearer api-unauthorized"},
            json=api_payload,
        )
        self.assertEqual(unauthorized_response.status_code, 403, unauthorized_response.text)
        self.assertEqual(broker.calls, 1)

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT body->>'author_role',body->>'artifact_attestation_digest',
                trim(idempotency_key),
                (SELECT result FROM factory.command_results WHERE idempotency_key=%s),
                (SELECT trim(request_digest) FROM factory.command_results WHERE idempotency_key=%s),
                (SELECT count(*) FROM factory.execution_proposals WHERE run_id=%s)
                FROM factory.execution_proposals
                WHERE run_id=%s AND proposal_kind='artifact'""",
                (command_key, command_key, execution.lease.run_id, execution.lease.run_id),
            )
            author_role, attestation_digest, persisted_key, command_result, request_digest, count = cursor.fetchone()
        self.assertEqual((author_role, len(attestation_digest), persisted_key, count), ("writer", 64, artifact.idempotency_key, 2))
        self.assertEqual(command_result, {
            "proposal_kind": "artifact", "sequence": 1,
            "proposal_idempotency_key": artifact.idempotency_key,
        })
        self.assertEqual(
            request_digest,
            canonical_digest(self.store._execution_proposal_command(execution.lease, event)),
        )

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """UPDATE factory.execution_proposals SET body=to_jsonb(body::text)
                WHERE run_id=%s AND proposal_kind='artifact'""",
                (execution.lease.run_id,),
            )
        with self.assertRaisesRegex(StoreError, "persisted execution proposal is corrupt"):
            service.commit_execution_proposal(
                execution.lease, packet_digest=execution.packet_digest,
                sequence=1, event_type="artifact.proposed", payload=dict(payload),
                actor=WORKER, idempotency_key=command_key,
            )

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """UPDATE factory.execution_proposals SET body=(body#>>'{}')::jsonb
                WHERE run_id=%s AND proposal_kind='artifact'""",
                (execution.lease.run_id,),
            )

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.command_results SET result=jsonb_set(result,'{sequence}','true'::jsonb) WHERE idempotency_key=%s",
                (command_key,),
            )
        with self.assertRaisesRegex(StoreError, "persisted execution proposal command is corrupt"):
            service.commit_execution_proposal(
                execution.lease, packet_digest=execution.packet_digest,
                sequence=1, event_type="artifact.proposed", payload=dict(payload),
                actor=WORKER, idempotency_key=command_key,
            )

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """UPDATE factory.command_results SET result=%s::jsonb
                WHERE idempotency_key=%s""",
                (
                    psycopg.types.json.Jsonb({
                        "proposal_kind": "artifact", "sequence": 1,
                        "proposal_idempotency_key": terminal.idempotency_key,
                    }),
                    command_key,
                ),
            )
        with self.assertRaisesRegex(StoreError, "persisted execution proposal is corrupt"):
            service.commit_execution_proposal(
                execution.lease, packet_digest=execution.packet_digest,
                sequence=1, event_type="artifact.proposed", payload=dict(payload),
                actor=WORKER, idempotency_key=command_key,
            )

    def test_runtime_cannot_forge_self_consistent_artifact_attestation(self):
        import psycopg

        repository = "owner/m5-runtime-forged-attestation"
        task = self.submit(repository=repository, source="m5-runtime-forged-attestation").task
        packet = valid_packet()
        packet["provider"]["capabilities"] = ["artifacts", "notes", "structured_output"]
        selection = {
            "provider": packet["provider"], "capability_policy": packet["capability_policy"],
            "plan": packet["plan"], "workspace_handle": packet["workspace_handle"],
            "prompt_template_digest": "7" * 64, "role_definition_digest": "8" * 64,
            "tool_policy_digest": "9" * 64, "output_schema_digest": "a" * 64,
        }
        execution = FactoryService(
            self.store, execution_registry=trusted_registry(selection)
        ).claim_execution(
            owner=WORKER.actor_id, role=RunRole.WRITER, repositories=(repository,),
            lease_seconds=60, selection=selection, actor=WORKER, now=NOW,
        )
        facts = {
            "contract_version": 1, "task_id": execution.lease.task_id,
            "run_id": execution.lease.run_id, "repository_id": repository,
            "packet_digest": execution.packet_digest,
            "workspace_handle": packet["workspace_handle"],
            "producer_sequence": 1, "fence": execution.lease.fence,
            "author_role": "writer", "artifact_class": "report",
            "path": "factory/src/forged.patch", "sha256": "b" * 64,
            "size_bytes": 12, "media_type": "text/plain",
            "source": "trusted_workspace_broker",
        }
        attestation = ArtifactAttestationV1.from_facts(facts)
        proposal = ArtifactProposal(
            execution.lease.task_id, execution.lease.run_id, execution.packet_digest,
            execution.lease.fence, 1, "writer", "report", facts["path"], facts["sha256"],
            facts["size_bytes"], facts["media_type"],
            attestation.artifact_attestation_digest, "0" * 64,
        )
        proposal = replace(proposal, idempotency_key=proposal_idempotency_key(proposal))
        forbidden_note = NoteProposal(
            execution.lease.task_id, execution.lease.run_id, execution.packet_digest,
            execution.lease.fence, 1, "writer", "model_analysis", "safe finding", (), "0" * 64,
        )
        forbidden_note = replace(
            forbidden_note, idempotency_key=proposal_idempotency_key(forbidden_note)
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("SET ROLE factory_runtime")
            cursor.execute(
                "SELECT factory.execution_propose(%s,%s,%s,%s,%s,%s,1,%s,'artifact',%s::jsonb)",
                (
                    execution.lease.task_id, execution.lease.run_id, execution.lease.owner,
                    execution.lease.fence, execution.lease.packet_digest,
                    execution.packet_digest, proposal.idempotency_key,
                    psycopg.types.json.Jsonb(dict(proposal.__dict__)),
                ),
            )
            self.assertFalse(cursor.fetchone()[0])
            cursor.execute(
                "SELECT factory.execution_propose(%s,%s,%s,%s,%s,%s,1,%s,'note',%s::jsonb)",
                (
                    execution.lease.task_id, execution.lease.run_id, execution.lease.owner,
                    execution.lease.fence, execution.lease.packet_digest,
                    execution.packet_digest, forbidden_note.idempotency_key,
                    psycopg.types.json.Jsonb(dict(forbidden_note.__dict__)),
                ),
            )
            self.assertFalse(cursor.fetchone()[0])
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM factory.execution_proposals WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_direct_note_evidence_is_closed_bounded_and_path_safe(self):
        import psycopg

        repository = "owner/m5-direct-note-evidence"
        task = self.submit(repository=repository, source="m5-direct-note-evidence").task
        packet = valid_packet()
        packet["provider"]["capabilities"] = ["notes", "structured_output"]
        selection = {
            "provider": packet["provider"], "capability_policy": packet["capability_policy"],
            "plan": packet["plan"], "workspace_handle": packet["workspace_handle"],
            "prompt_template_digest": "7" * 64, "role_definition_digest": "8" * 64,
            "tool_policy_digest": "9" * 64, "output_schema_digest": "a" * 64,
        }
        execution = FactoryService(
            self.store, execution_registry=trusted_registry(selection)
        ).claim_execution(
            owner=WORKER.actor_id, role=RunRole.WRITER, repositories=(repository,),
            lease_seconds=60, selection=selection, actor=WORKER, now=NOW,
        )
        direct_facts = (
            execution.lease.task_id, execution.lease.run_id, execution.lease.owner,
            execution.lease.fence, execution.lease.packet_digest, execution.packet_digest,
        )

        def proposal(note_type="finding", evidence=()):
            value = NoteProposal(
                execution.lease.task_id, execution.lease.run_id, execution.packet_digest,
                execution.lease.fence, 1, "writer", note_type, "bounded finding",
                tuple(evidence), "0" * 64,
            )
            return replace(value, idempotency_key=proposal_idempotency_key(value))

        exact_1024 = "factory/src/" + "x" * (1024 - len("factory/src/"))
        exact_1025 = exact_1024 + "x"
        self.assertEqual((len(exact_1024.encode()), len(exact_1025.encode())), (1024, 1025))
        rejected = (
            proposal("x"), proposal("late"), proposal("private_thoughts"),
            proposal(evidence=("",)),
            proposal(evidence=("factory/src/../outside",)),
            proposal(evidence=("factory/src/.git/config",)),
            proposal(evidence=(exact_1025,)),
        )
        with self.store._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            for invalid in rejected:
                cursor.execute(
                    "SELECT factory.execution_propose(%s,%s,%s,%s,%s,%s,1,%s,'note',%s::jsonb)",
                    (*direct_facts, invalid.idempotency_key,
                     psycopg.types.json.Jsonb(dict(invalid.__dict__))),
                )
                self.assertFalse(cursor.fetchone()[0], invalid)
            accepted = proposal(evidence=(exact_1024,))
            cursor.execute(
                "SELECT factory.execution_propose(%s,%s,%s,%s,%s,%s,1,%s,'note',%s::jsonb)",
                (*direct_facts, accepted.idempotency_key,
                 psycopg.types.json.Jsonb(dict(accepted.__dict__))),
            )
            self.assertTrue(cursor.fetchone()[0])
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM factory.execution_proposals WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone()[0], 1)

    def test_artifact_attestation_sequence_reservation_serializes_both_interleavings(self):
        import psycopg

        def claim(label):
            repository = f"owner/{label}"
            task = self.submit(repository=repository, source=label).task
            packet = valid_packet()
            packet["provider"]["capabilities"] = ["artifacts", "notes", "structured_output", "usage"]
            selection = {
                "provider": packet["provider"],
                "capability_policy": packet["capability_policy"],
                "plan": packet["plan"], "workspace_handle": packet["workspace_handle"],
                "prompt_template_digest": "7" * 64, "role_definition_digest": "8" * 64,
                "tool_policy_digest": "9" * 64, "output_schema_digest": "a" * 64,
            }
            execution = FactoryService(
                self.store, execution_registry=trusted_registry(selection)
            ).claim_execution(
                owner=WORKER.actor_id, role=RunRole.WRITER, repositories=(repository,),
                lease_seconds=60, selection=selection, actor=WORKER, now=NOW,
            )
            return task, packet, execution, repository

        def attestation(packet, execution, repository):
            return ArtifactAttestationV1.from_facts({
                "contract_version": 1, "task_id": execution.lease.task_id,
                "run_id": execution.lease.run_id, "repository_id": repository,
                "packet_digest": execution.packet_digest,
                "workspace_handle": packet["workspace_handle"],
                "producer_sequence": 1, "fence": execution.lease.fence,
                "author_role": "writer", "artifact_class": "report",
                "path": "factory/src/result.patch", "sha256": "b" * 64,
                "size_bytes": 12, "media_type": "text/plain",
                "source": "trusted_workspace_broker",
            })

        def note(execution):
            value = NoteProposal(
                execution.lease.task_id, execution.lease.run_id, execution.packet_digest,
                execution.lease.fence, 1, "writer", "finding", "competing note", (), "0" * 64,
            )
            return replace(value, idempotency_key=proposal_idempotency_key(value))

        def execute_propose(store, execution, proposal, kind):
            with store._connect() as connection, connection.transaction(), connection.cursor() as cursor:
                cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
                cursor.execute(
                    "SELECT factory.execution_propose(%s,%s,%s,%s,%s,%s,1,%s,%s,%s::jsonb)",
                    (
                        execution.lease.task_id, execution.lease.run_id, execution.lease.owner,
                        execution.lease.fence, execution.lease.packet_digest,
                        execution.packet_digest, proposal.idempotency_key, kind,
                        psycopg.types.json.Jsonb(dict(proposal.__dict__)),
                    ),
                )
                return cursor.fetchone()[0]

        def wait_for_lock(application_name):
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline:
                with psycopg.connect(DATABASE_URL) as observer, observer.cursor() as cursor:
                    cursor.execute(
                        """SELECT count(*) FROM pg_stat_activity
                        WHERE datname=current_database() AND application_name=%s
                          AND state='active' AND wait_event_type='Lock'""",
                        (application_name,),
                    )
                    if cursor.fetchone()[0] == 1:
                        return
                time.sleep(0.02)
            self.fail(f"{application_name} did not block on the execution authority lock")

        task, packet, execution, repository = claim("m5-proposal-first-reservation")
        proposal_first = note(execution)
        runtime = self.store._connect()
        proposal_first_pool = ThreadPoolExecutor(max_workers=1)
        try:
            with runtime.cursor() as cursor:
                cursor.execute(
                    "SELECT factory.execution_propose(%s,%s,%s,%s,%s,%s,1,%s,'note',%s::jsonb)",
                    (
                        execution.lease.task_id, execution.lease.run_id, execution.lease.owner,
                        execution.lease.fence, execution.lease.packet_digest,
                        execution.packet_digest, proposal_first.idempotency_key,
                        psycopg.types.json.Jsonb(dict(proposal_first.__dict__)),
                    ),
                )
                self.assertTrue(cursor.fetchone()[0])
            recorder_url = psycopg.conninfo.make_conninfo(
                self.artifact_attestor_url, application_name="m5_attestor_after_proposal",
            )
            recorder = PostgresArtifactAttestationStore(recorder_url)
            future = proposal_first_pool.submit(
                recorder.record_artifact_attestation,
                attestation(packet, execution, repository),
            )
            wait_for_lock("m5_attestor_after_proposal")
            runtime.commit()
            rejected = future.result(timeout=10)
            self.assertIsInstance(rejected, ArtifactAttestationUnavailable)
        finally:
            runtime.rollback()
            runtime.close()
            proposal_first_pool.shutdown(wait=True, cancel_futures=True)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM factory.execution_artifact_attestations WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone()[0], 0)
        self.service.cancel(
            task.task_id, reason="bounded proposal-first cleanup",
            idempotency_key="1" * 64, actor=OPERATOR, now=NOW,
        )

        task, packet, execution, repository = claim("m5-attestation-first-reservation")
        reserved = attestation(packet, execution, repository)
        attestor = PostgresArtifactAttestationStore(self.artifact_attestor_url)._connect()
        attestation_first_pool = ThreadPoolExecutor(max_workers=1)
        try:
            with attestor.cursor() as cursor:
                cursor.execute(
                    "SELECT factory.execution_record_artifact_attestation(%s::jsonb)",
                    (psycopg.types.json.Jsonb(reserved.to_dict()),),
                )
                self.assertEqual(
                    cursor.fetchone()[0]["artifact_attestation_digest"],
                    reserved.artifact_attestation_digest,
                )
            competing_store = PostgresFactoryStore(psycopg.conninfo.make_conninfo(
                self.runtime_url, application_name="m5_note_after_attestation",
            ))
            future = attestation_first_pool.submit(
                execute_propose, competing_store, execution, note(execution), "note",
            )
            wait_for_lock("m5_note_after_attestation")
            attestor.commit()
            self.assertFalse(future.result(timeout=10))
        finally:
            attestor.rollback()
            attestor.close()
            attestation_first_pool.shutdown(wait=True, cancel_futures=True)

        usage = UsageProposal(
            execution.lease.task_id, execution.lease.run_id, execution.packet_digest,
            execution.lease.fence, 1, "writer", "reserved-sequence-call", "d" * 64,
            1, 1, 0, 1, 1, "0" * 64,
        )
        usage = replace(usage, idempotency_key=proposal_idempotency_key(usage))
        terminal = TerminalProposal(
            execution.lease.task_id, execution.lease.run_id, execution.packet_digest,
            execution.lease.fence, 1, "writer", "run.completed", "bounded complete",
            None, None, None, "0" * 64,
        )
        terminal = replace(terminal, idempotency_key=proposal_idempotency_key(terminal))
        self.assertFalse(execute_propose(self.store, execution, usage, "usage"))
        self.assertFalse(execute_propose(self.store, execution, terminal, "terminal"))

        artifact = ArtifactProposal(
            execution.lease.task_id, execution.lease.run_id, execution.packet_digest,
            execution.lease.fence, 1, "writer", "report", reserved.path, reserved.sha256,
            reserved.size_bytes, reserved.media_type,
            reserved.artifact_attestation_digest, "0" * 64,
        )
        artifact = replace(artifact, idempotency_key=proposal_idempotency_key(artifact))
        self.assertTrue(execute_propose(self.store, execution, artifact, "artifact"))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT a.consumed_at,p.proposal_kind,
                (SELECT count(*) FROM factory.execution_artifact_attestations WHERE run_id=a.run_id),
                (SELECT count(*) FROM factory.execution_proposals WHERE run_id=a.run_id)
                FROM factory.execution_artifact_attestations a
                JOIN factory.execution_proposals p USING (run_id,producer_sequence)
                WHERE a.run_id=%s""",
                (execution.lease.run_id,),
            )
            consumed_at, proposal_kind, attestation_count, proposal_count = cursor.fetchone()
            self.assertEqual((proposal_kind, attestation_count, proposal_count), ("artifact", 1, 1))
        self.assertTrue(execute_propose(self.store, execution, artifact, "artifact"))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT consumed_at,
                (SELECT count(*) FROM factory.execution_artifact_attestations WHERE run_id=a.run_id),
                (SELECT count(*) FROM factory.execution_proposals WHERE run_id=a.run_id)
                FROM factory.execution_artifact_attestations a WHERE run_id=%s""",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone(), (consumed_at, 1, 1))
        self.service.cancel(
            task.task_id, reason="bounded attestation-first cleanup",
            idempotency_key="2" * 64, actor=OPERATOR, now=NOW,
        )

    def test_execution_capabilities_reject_repeatable_read_snapshots(self):
        import psycopg

        def claim(label):
            repository = f"owner/{label}"
            task = self.submit(repository=repository, source=label).task
            packet = valid_packet()
            packet["provider"]["capabilities"] = ["artifacts", "notes", "structured_output"]
            selection = {
                "provider": packet["provider"],
                "capability_policy": packet["capability_policy"],
                "plan": packet["plan"], "workspace_handle": packet["workspace_handle"],
                "prompt_template_digest": "7" * 64, "role_definition_digest": "8" * 64,
                "tool_policy_digest": "9" * 64, "output_schema_digest": "a" * 64,
            }
            execution = FactoryService(
                self.store, execution_registry=trusted_registry(selection)
            ).claim_execution(
                owner=WORKER.actor_id, role=RunRole.WRITER, repositories=(repository,),
                lease_seconds=60, selection=selection, actor=WORKER, now=NOW,
            )
            return task, packet, execution, repository

        task, _packet, execution, _repository = claim("m5-rr-proposal")
        note = NoteProposal(
            execution.lease.task_id, execution.lease.run_id, execution.packet_digest,
            execution.lease.fence, 1, "writer", "finding", "bounded", (), "0" * 64,
        )
        note = replace(note, idempotency_key=proposal_idempotency_key(note))
        with self.store._connect() as connection:
            connection.commit()
            with connection.transaction(), connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                cursor.execute(
                    "SELECT factory.execution_propose(%s,%s,%s,%s,%s,%s,1,%s,'note',%s::jsonb)",
                    (
                        execution.lease.task_id, execution.lease.run_id, execution.lease.owner,
                        execution.lease.fence, execution.lease.packet_digest,
                        execution.packet_digest, note.idempotency_key,
                        psycopg.types.json.Jsonb(dict(note.__dict__)),
                    ),
                )
                self.assertFalse(cursor.fetchone()[0])
        self.service.cancel(
            task.task_id, reason="bounded RR proposal cleanup",
            idempotency_key="3" * 64, actor=OPERATOR, now=NOW,
        )

        task, packet, execution, repository = claim("m5-rr-attestation")
        reserved = ArtifactAttestationV1.from_facts({
            "contract_version": 1, "task_id": execution.lease.task_id,
            "run_id": execution.lease.run_id, "repository_id": repository,
            "packet_digest": execution.packet_digest,
            "workspace_handle": packet["workspace_handle"],
            "producer_sequence": 1, "fence": execution.lease.fence,
            "author_role": "writer", "artifact_class": "report",
            "path": "factory/src/result.patch", "sha256": "b" * 64,
            "size_bytes": 12, "media_type": "text/plain",
            "source": "trusted_workspace_broker",
        })
        with PostgresArtifactAttestationStore(self.artifact_attestor_url)._connect() as connection:
            connection.commit()
            with connection.transaction(), connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                cursor.execute(
                    "SELECT factory.execution_record_artifact_attestation(%s::jsonb)",
                    (psycopg.types.json.Jsonb(reserved.to_dict()),),
                )
                self.assertIsNone(cursor.fetchone()[0])
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                (SELECT count(*) FROM factory.execution_proposals WHERE run_id=%s),
                (SELECT count(*) FROM factory.execution_artifact_attestations WHERE run_id=%s)""",
                (execution.lease.run_id, execution.lease.run_id),
            )
            self.assertEqual(cursor.fetchone(), (0, 0))
        self.service.cancel(
            task.task_id, reason="bounded RR attestation cleanup",
            idempotency_key="4" * 64, actor=OPERATOR, now=NOW,
        )

    def test_artifact_recorder_rejects_out_of_order_terminal_and_event_limit_without_poisoning(self):
        import psycopg

        def claim(label: str, max_events: int):
            intake = self.payload(source=label)
            intake["limits"]["max_events"] = max_events
            task = self.service.intake(intake, actor=OPERATOR, now=NOW).task
            packet = valid_packet()
            packet["provider"]["capabilities"] = ["artifacts", "notes", "structured_output"]
            selection = {
                "provider": packet["provider"],
                "capability_policy": packet["capability_policy"],
                "plan": packet["plan"],
                "workspace_handle": packet["workspace_handle"],
                "prompt_template_digest": "7" * 64,
                "role_definition_digest": "8" * 64,
                "tool_policy_digest": "9" * 64,
                "output_schema_digest": "a" * 64,
            }
            execution = FactoryService(
                self.store, execution_registry=trusted_registry(selection)
            ).claim_execution(
                owner=WORKER.actor_id, role=RunRole.WRITER,
                repositories=("owner/repository",), lease_seconds=60,
                selection=selection, actor=WORKER, now=NOW,
            )
            broker = TrustedPostgresTestArtifactBroker()
            recorder = PostgresArtifactAttestationStore(self.artifact_attestor_url)
            return task, packet, execution, broker, recorder, FactoryService(
                self.store, artifact_broker=broker,
                artifact_attestation_store=recorder,
            )

        artifact = {
            "artifact_class": "report", "path": "factory/src/result.patch",
            "sha256": "b" * 64, "size_bytes": 12, "media_type": "text/plain",
        }

        task, packet, execution, _, _, service = claim("attestation-out-of-order", 4)
        with self.assertRaises((ExecutionContractError, FenceError)):
            service.commit_execution_proposal(
                execution.lease, packet_digest=execution.packet_digest, sequence=2,
                event_type="artifact.proposed", payload=artifact, actor=WORKER,
            )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM factory.execution_artifact_attestations WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone()[0], 0)
        service.commit_execution_proposal(
            execution.lease, packet_digest=execution.packet_digest, sequence=1,
            event_type="artifact.proposed", payload=artifact, actor=WORKER,
        )
        self.service.cancel(
            task.task_id, reason="bounded test cleanup", idempotency_key="1" * 64,
            actor=OPERATOR, now=NOW,
        )

        task, packet, execution, _, _, service = claim("attestation-unsafe-path", 4)
        exact_1024 = "factory/src/" + "x" * (1024 - len("factory/src/"))
        exact_1025 = exact_1024 + "x"
        self.assertEqual(
            (len(exact_1024.encode()), len(exact_1025.encode())), (1024, 1025),
        )
        for unsafe_path in (
            "factory/src/password=hunter2", "factory/src/ghp_secret",
            "factory/src/../outside", "factory/src/.git/config",
            exact_1025,
        ):
            with self.subTest(unsafe_path=unsafe_path), self.assertRaises(ExecutionContractError):
                service.commit_execution_proposal(
                    execution.lease, packet_digest=execution.packet_digest, sequence=1,
                    event_type="artifact.proposed", payload={**artifact, "path": unsafe_path},
                    actor=WORKER,
                )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM factory.execution_artifact_attestations WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone()[0], 0)
            raw = {
                "contract_version": 1,
                "task_id": execution.lease.task_id,
                "run_id": execution.lease.run_id,
                "repository_id": "owner/repository",
                "packet_digest": execution.packet_digest,
                "workspace_handle": packet["workspace_handle"],
                "producer_sequence": 1,
                "fence": execution.lease.fence,
                "author_role": "writer",
                "artifact_class": artifact["artifact_class"],
                "path": "factory/src/result.patch",
                "sha256": artifact["sha256"],
                "size_bytes": artifact["size_bytes"],
                "media_type": artifact["media_type"],
                "source": "trusted_workspace_broker",
            }
            cursor.execute("SET ROLE factory_artifact_attestor")
            for unsafe_path in (
                "factory/src/ghp_secret",
                "factory/src/../outside",
                "factory/src/.git/config",
                exact_1025,
            ):
                direct = {**raw, "path": unsafe_path}
                direct["artifact_attestation_digest"] = canonical_digest({
                    "contract": "adaptive-factory.artifact-attestation/v1", **direct,
                })
                cursor.execute(
                    "SELECT factory.execution_record_artifact_attestation(%s::jsonb)",
                    (psycopg.types.json.Jsonb(direct),),
                )
                self.assertIsNone(cursor.fetchone()[0])
                cursor.execute("RESET ROLE")
                cursor.execute(
                    "SELECT count(*) FROM factory.execution_artifact_attestations WHERE run_id=%s",
                    (execution.lease.run_id,),
                )
                self.assertEqual(cursor.fetchone()[0], 0)
                cursor.execute("SET ROLE factory_artifact_attestor")
            exact = {**raw, "path": exact_1024}
            exact["artifact_attestation_digest"] = canonical_digest({
                "contract": "adaptive-factory.artifact-attestation/v1", **exact,
            })
            cursor.execute(
                "SELECT factory.execution_record_artifact_attestation(%s::jsonb)",
                (psycopg.types.json.Jsonb(exact),),
            )
            self.assertEqual(
                cursor.fetchone()[0]["artifact_attestation_digest"],
                exact["artifact_attestation_digest"],
            )
            cursor.execute("RESET ROLE")
            cursor.execute(
                "SELECT count(*) FROM factory.execution_artifact_attestations WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone()[0], 1)
        service.commit_execution_proposal(
            execution.lease, packet_digest=execution.packet_digest, sequence=1,
            event_type="artifact.proposed", payload={**artifact, "path": exact_1024},
            actor=WORKER,
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT count(*),bool_and(consumed_at IS NOT NULL)
                FROM factory.execution_artifact_attestations WHERE run_id=%s""",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone(), (1, True))
        self.service.cancel(
            task.task_id, reason="bounded test cleanup", idempotency_key="4" * 64,
            actor=OPERATOR, now=NOW,
        )

        task, packet, execution, _, _, service = claim("attestation-event-limit", 2)
        for sequence, note_type in ((1, "finding"), (2, "conclusion")):
            service.commit_execution_proposal(
                execution.lease, packet_digest=execution.packet_digest, sequence=sequence,
                event_type="note.proposed",
                payload={"note_type": note_type, "body": "bounded", "evidence": []},
                actor=WORKER,
            )
        with self.assertRaises((ExecutionContractError, FenceError)):
            service.commit_execution_proposal(
                execution.lease, packet_digest=execution.packet_digest, sequence=3,
                event_type="artifact.proposed", payload=artifact, actor=WORKER,
            )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM factory.execution_artifact_attestations WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone()[0], 0)
        self.service.cancel(
            task.task_id, reason="bounded test cleanup", idempotency_key="2" * 64,
            actor=OPERATOR, now=NOW,
        )

        task, packet, execution, broker, recorder, service = claim("attestation-terminal", 4)
        service.commit_execution_proposal(
            execution.lease, packet_digest=execution.packet_digest, sequence=1,
            event_type="run.failed",
            payload={"failure_class": "validation", "diagnostic": "bounded"},
            actor=WORKER,
        )
        request = ArtifactAttestationRequest.from_facts({
            "task_id": execution.lease.task_id, "run_id": execution.lease.run_id,
            "repository_id": "owner/repository", "packet_digest": execution.packet_digest,
            "workspace_handle": packet["workspace_handle"], "producer_sequence": 2,
            "fence": execution.lease.fence, "author_role": "writer",
            "artifact_class": artifact["artifact_class"], "path": artifact["path"],
            "sha256": artifact["sha256"], "size_bytes": artifact["size_bytes"],
            "media_type": artifact["media_type"],
        })
        observed = broker.attest_artifact(request)
        self.assertIsInstance(
            recorder.record_artifact_attestation(observed), ArtifactAttestationUnavailable
        )
        with self.assertRaises(FenceError):
            service.commit_execution_proposal(
                execution.lease, packet_digest=execution.packet_digest, sequence=2,
                event_type="artifact.proposed", payload=artifact, actor=WORKER,
            )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM factory.execution_artifact_attestations WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone()[0], 0)
        self.service.cancel(
            task.task_id, reason="bounded test cleanup", idempotency_key="3" * 64,
            actor=OPERATOR, now=NOW,
        )

    def test_semantic_subject_publish_is_exact_replay_safe_and_role_isolated(self):
        import psycopg

        task = self.submit(source="m6-semantic-subject").task
        packet = valid_packet()
        packet["provider"]["capabilities"] = ["structured_output", "usage"]
        selection = {
            "provider": packet["provider"],
            "capability_policy": packet["capability_policy"],
            "plan": packet["plan"],
            "workspace_handle": packet["workspace_handle"],
            "prompt_template_digest": "7" * 64,
            "role_definition_digest": "8" * 64,
            "tool_policy_digest": "9" * 64,
            "output_schema_digest": "a" * 64,
        }
        execution = FactoryService(
            self.store, execution_registry=trusted_registry(selection)
        ).claim_execution(
            owner=WORKER.actor_id,
            role=RunRole.WRITER,
            repositories=(task.repository_id,),
            lease_seconds=60,
            selection=selection,
            actor=WORKER,
            now=datetime.now(timezone.utc),
            idempotency_key="1" * 64,
        )
        self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="usage.reported",
            payload={
                "provider_call_id": "semantic-fixture-call",
                "price_table_digest": "d" * 64,
                "input_tokens": 10,
                "output_tokens": 5,
                "reasoning_tokens": 0,
                "cost_usd_micros": 25,
                "output_bytes": 20,
            },
            actor=WORKER,
            idempotency_key="2" * 64,
        )
        self.service.observe_usage(
            execution.lease,
            provider_call_id="semantic-fixture-call",
            price_table_digest="d" * 64,
            cost_usd_micros=25,
            token_units=15,
            output_bytes=20,
            actor=WORKER,
            idempotency_key="3" * 64,
        )
        self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=2,
            event_type="run.completed",
            payload={"summary": "semantic fixture complete"},
            actor=WORKER,
            idempotency_key="4" * 64,
        )
        for index, stage in enumerate(
            (ExecutionStage.RUNNING, ExecutionStage.COLLECTING), start=5
        ):
            self.service.advance_execution(
                execution.lease,
                packet_digest=execution.packet_digest,
                stage=stage,
                actor=WORKER,
                idempotency_key=str(index) * 64,
            )
        result = FactoryService(
            self.store, snapshot_broker=TrustedPostgresTestSnapshotBroker()
        ).finalize_execution(
            execution.lease,
            packet_digest=execution.packet_digest,
            actor=WORKER,
            idempotency_key="7" * 64,
        )

        semantic_store = PostgresSemanticCoordinatorStore(
            self.semantic_coordinator_url
        )
        actor = Actor(
            "semantic-coordinator",
            "operator",
            frozenset({"semantic:publish", "semantic:read"}),
            frozenset({task.repository_id}),
        )
        semantic_service = FactoryService(
            self.store, semantic_store=semantic_store
        )
        inputs = {
            "schema_version": 1,
            "workspace_result_digest": result.workspace_result_digest,
            "requirements": [
                {"kind": "acceptance_criterion", "requirement_id": "AC-001"},
                {"kind": "acceptance_criterion", "requirement_id": "AC-002"},
                {"kind": "invariant", "requirement_id": "INV-001"},
            ],
            "holdout_evidence_digest": "b" * 64,
            "review_evidence_digest": "c" * 64,
            "original_writer_context_digest": "d" * 64,
            "risk_level": "high",
            "diff_limit": 100,
        }
        key = "8" * 64
        published = semantic_service.publish_semantic_subject(
            task.task_id,
            result.workspace_result_digest,
            inputs,
            actor=actor,
            idempotency_key=key,
        )
        replay = semantic_service.publish_semantic_subject(
            task.task_id,
            result.workspace_result_digest,
            dict(inputs),
            actor=actor,
            idempotency_key=key,
        )
        self.assertEqual(replay, published)
        self.assertEqual(
            semantic_service.get_semantic_subject(
                task.task_id, published.subject.digest, actor=actor
            ),
            published,
        )

        changed_inputs = {**inputs, "holdout_evidence_digest": "e" * 64}
        with self.assertRaisesRegex(StoreError, "publication rejected"):
            semantic_service.publish_semantic_subject(
                task.task_id,
                result.workspace_result_digest,
                changed_inputs,
                actor=actor,
                idempotency_key=key,
            )
        material = semantic_store.execution_material(
            task.task_id, result.workspace_result_digest
        )
        substituted_binding = replace(
            published.binding, exact_head_sha="5" * 40
        )
        substituted_subject = replace(
            published.subject,
            exact_head_sha="5" * 40,
            deterministic_evidence_digest=substituted_binding.digest,
        )
        substituted = SemanticBridgeResult(
            substituted_binding,
            published.validation_inputs,
            substituted_subject,
        )
        with self.assertRaisesRegex(StoreError, "publication rejected"):
            semantic_store.publish_subject(
                material, substituted, idempotency_key="9" * 64
            )

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                (SELECT count(*) FROM factory.semantic_subjects),
                (SELECT count(*) FROM factory.semantic_command_results),
                has_table_privilege('factory_runtime','factory.semantic_subjects','INSERT'),
                has_table_privilege('factory_semantic_coordinator','factory.semantic_subjects','INSERT'),
                has_table_privilege('factory_semantic_validator','factory.semantic_subjects','INSERT'),
                has_table_privilege('factory_semantic_adjudicator','factory.semantic_subjects','INSERT')"""
            )
            self.assertEqual(cursor.fetchone(), (1, 1, False, False, False, False))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            with self.assertRaisesRegex(psycopg.Error, "append-only"):
                cursor.execute(
                    "UPDATE factory.semantic_subjects SET owner_id='forged' WHERE subject_digest=%s",
                    (published.subject.digest,),
                )
        with semantic_store._connect() as connection, connection.cursor() as cursor:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                cursor.execute(
                    "INSERT INTO factory.semantic_metric_events(metric_name,label) VALUES ('semantic_subject_lifecycle','published')"
                )

    def test_execution_lifecycle_persists_new_digest_stages_and_redacted_proposal(self):
        task = self.submit(source="m5-execution-lifecycle").task
        packet = valid_packet()
        packet["provider"]["capabilities"] = ["artifacts", "cancellation", "notes", "structured_output", "usage"]
        selection = {
            "provider": packet["provider"],
            "capability_policy": packet["capability_policy"],
            "plan": packet["plan"],
            "workspace_handle": packet["workspace_handle"],
            "prompt_template_digest": "7" * 64,
            "role_definition_digest": "8" * 64,
            "tool_policy_digest": "9" * 64,
            "output_schema_digest": "a" * 64,
        }
        execution = FactoryService(self.store, execution_registry=trusted_registry(selection)).claim_execution(
            owner=WORKER.actor_id, role=RunRole.WRITER, repositories=(task.repository_id,),
            lease_seconds=60, selection=selection, actor=WORKER, now=NOW,
            idempotency_key="b" * 64, correlation_id="m5-execution-claim",
        )
        self.assertNotEqual(execution.packet_digest, execution.lease.packet_digest)
        self.assertEqual(execution.stage, ExecutionStage.PREPARED)
        note = self.service.commit_execution_proposal(
            execution.lease, packet_digest=execution.packet_digest, sequence=1,
            event_type="note.proposed",
            payload={"note_type": "finding", "body": "token ghp_abcdefghijk", "evidence": ["factory/src"]},
            actor=WORKER, idempotency_key="c" * 64, correlation_id="m5-execution-note",
        )
        replay = self.service.commit_execution_proposal(
            execution.lease, packet_digest=execution.packet_digest, sequence=1,
            event_type="note.proposed",
            payload={"note_type": "finding", "body": "token ghp_abcdefghijk", "evidence": ["factory/src"]},
            actor=WORKER, idempotency_key="c" * 64, correlation_id="m5-execution-note",
        )
        self.assertEqual((note.body, replay.body), ("token [REDACTED]", "token [REDACTED]"))
        self.service.commit_execution_proposal(
            execution.lease, packet_digest=execution.packet_digest, sequence=2,
            event_type="usage.reported",
            payload={
                "provider_call_id": "fixture-call", "price_table_digest": "d" * 64,
                "input_tokens": 10, "output_tokens": 5, "reasoning_tokens": 0,
                "cost_usd_micros": 25, "output_bytes": 20,
            },
            actor=WORKER, idempotency_key="d" * 64, correlation_id="m5-execution-usage",
        )
        self.service.observe_usage(
            execution.lease, provider_call_id="fixture-call", price_table_digest="d" * 64,
            cost_usd_micros=25, token_units=15, output_bytes=20, actor=WORKER,
            idempotency_key="e" * 64, correlation_id="m5-authoritative-usage",
        )
        self.service.commit_execution_proposal(
            execution.lease, packet_digest=execution.packet_digest, sequence=3,
            event_type="run.completed", payload={"summary": "fixture complete"},
            actor=WORKER, idempotency_key="f" * 64, correlation_id="m5-terminal",
        )
        for forged_outcome in ("completed", FailureClass.VALIDATION):
            with self.subTest(forged_outcome=forged_outcome), self.assertRaises(FenceError):
                self.service.release(
                    execution.lease, outcome=forged_outcome, actor=WORKER, now=NOW,
                )
        self.assertEqual(self.store.get_task(task.task_id).status, TaskStatus.LEASED)
        for index, stage in enumerate((ExecutionStage.RUNNING, ExecutionStage.COLLECTING), start=4):
            self.service.advance_execution(
                execution.lease, packet_digest=execution.packet_digest, stage=stage,
                actor=WORKER, idempotency_key=str(index) * 64, correlation_id="m5-stage",
            )
        snapshot_broker = TrustedPostgresTestSnapshotBroker()
        finalizer = FactoryService(self.store, snapshot_broker=snapshot_broker)
        import psycopg
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.tasks SET accounting_blocked=true WHERE task_id=%s",
                (task.task_id,),
            )
        with self.assertRaises(FenceError):
            finalizer.finalize_execution(
                execution.lease, packet_digest=execution.packet_digest, actor=WORKER,
            )
        self.assertEqual(snapshot_broker.calls, 0)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.tasks SET accounting_blocked=false WHERE task_id=%s",
                (task.task_id,),
            )
        result = finalizer.finalize_execution(
            execution.lease, packet_digest=execution.packet_digest,
            actor=WORKER, idempotency_key="7" * 64, correlation_id="m5-finalize",
        )
        result_replay = finalizer.finalize_execution(
            execution.lease, packet_digest=execution.packet_digest,
            actor=WORKER, idempotency_key="7" * 64, correlation_id="m5-finalize",
        )
        self.assertEqual(result.workspace_result_digest, result_replay.workspace_result_digest)
        self.assertEqual(snapshot_broker.calls, 1)
        self.assertEqual((result.exact_head_sha, result.terminal_stage), ("4" * 40, "completed"))
        self.assertEqual(
            (result.m4_status, result.failure_class, result.failure_reason),
            ("ready_for_human", None, None),
        )
        self.assertEqual(self.store.get_task(task.task_id).status, TaskStatus.READY_FOR_HUMAN)
        with self.assertRaises(FenceError):
            self.service.commit_execution_proposal(
                execution.lease, packet_digest=execution.packet_digest, sequence=2,
                event_type="note.proposed",
                payload={"note_type": "finding", "body": "late", "evidence": []}, actor=WORKER,
            )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                (SELECT count(*) FROM factory.execution_packets WHERE run_id=%s),
                (SELECT count(*) FROM factory.execution_stage_events e JOIN factory.execution_manifests m USING(manifest_digest) WHERE m.run_id=%s),
                (SELECT count(*) FROM factory.execution_proposals WHERE run_id=%s),
                (SELECT count(*) FROM factory.workspace_results WHERE run_id=%s),
                (SELECT body->>'body' FROM factory.execution_proposals WHERE run_id=%s AND proposal_kind='note')""",
                (execution.lease.run_id,) * 5,
            )
            self.assertEqual(cursor.fetchone(), (1, 4, 3, 1, "token [REDACTED]"))
        with self.assertRaises(FenceError):
            self.service.release(execution.lease, outcome="completed", actor=WORKER, now=NOW)
        reader = Actor("m6-reader", "operator", frozenset({"task:read"}), frozenset({task.repository_id}))
        bundle = self.service.get_workspace_result(
            task.task_id, result.workspace_result_digest, actor=reader,
        )
        self.assertEqual(bundle["result"].workspace_result_digest, result.workspace_result_digest)
        self.assertEqual((bundle["snapshot"].diff_digest, bundle["snapshot"].diff_lines), ("6" * 64, 12))
        self.assertEqual(bundle["packet"].provider.profile_digest, bundle["packet"].provider.profile_digest)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.workspace_results SET exact_head_sha=%s WHERE run_id=%s",
                ("5" * 40, execution.lease.run_id),
            )
        with self.assertRaises(StoreError):
            self.store.workspace_result(task.task_id, result.workspace_result_digest)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.workspace_results SET exact_head_sha=%s WHERE run_id=%s",
                (result.exact_head_sha, execution.lease.run_id),
            )
            cursor.execute(
                "UPDATE factory.workspace_results SET workspace_result_digest=%s WHERE run_id=%s",
                ("f" * 64, execution.lease.run_id),
            )
        with self.assertRaises(StoreError):
            self.store.workspace_result(task.task_id, "f" * 64)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.workspace_results SET workspace_result_digest=%s WHERE run_id=%s",
                (result.workspace_result_digest, execution.lease.run_id),
            )
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE factory.execution_proposals SET proposal_kind='note' WHERE run_id=%s AND proposal_kind='terminal'",
                    (execution.lease.run_id,),
                )
        other_repository = "owner/m5-cross-run-integrity"
        other_task = self.submit(
            repository=other_repository, source="m5-cross-run-integrity"
        ).task
        other_execution = FactoryService(
            self.store, execution_registry=trusted_registry(selection)
        ).claim_execution(
            owner=WORKER.actor_id, role=RunRole.WRITER,
            repositories=(other_repository,), lease_seconds=60,
            selection=selection, actor=WORKER, now=NOW,
        )
        other_terminal = self.service.commit_execution_proposal(
            other_execution.lease, packet_digest=other_execution.packet_digest,
            sequence=1, event_type="run.failed",
            payload={"failure_class": "validation", "diagnostic": "other run"},
            actor=WORKER,
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT trim(manifest_digest) FROM factory.execution_manifests WHERE run_id=%s",
                (other_execution.lease.run_id,),
            )
            other_manifest_digest = cursor.fetchone()[0]
        substitutions = (
            ("run_manifest_digest", other_manifest_digest),
            ("terminal_proposal_digest", other_terminal.idempotency_key),
        )
        for column, value in substitutions:
            with self.subTest(cross_run_column=column), self.assertRaises(
                psycopg.errors.ForeignKeyViolation
            ):
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        f"UPDATE factory.workspace_results SET {column}=%s WHERE run_id=%s",
                        (value, execution.lease.run_id),
                    )
        wrong_repo = Actor("other-reader", "operator", frozenset({"task:read"}), frozenset({"other/repository"}))
        with self.assertRaises(AuthorizationError):
            self.service.get_workspace_result(task.task_id, result.workspace_result_digest, actor=wrong_repo)

    def test_terminal_result_atomically_derives_m4_failure_disposition(self):
        cases = (
            ("retry", "run.failed", {"failure_class": "database_unavailable", "diagnostic": "temporary outage"}, 1, None, TaskStatus.RETRY),
            ("reserved", "run.failed", {"failure_class": "database_unavailable", "diagnostic": "reservation open"}, 1, "reservation", TaskStatus.NEEDS_HUMAN),
            ("events", "run.failed", {"failure_class": "database_unavailable", "diagnostic": "event budget full"}, 1, "event_limit", TaskStatus.NEEDS_HUMAN),
            ("nonretryable", "run.failed", {"failure_class": "validation", "diagnostic": "invalid output"}, 1, None, TaskStatus.NEEDS_HUMAN),
            ("exhausted", "run.failed", {"failure_class": "database_unavailable", "diagnostic": "third outage"}, 3, None, TaskStatus.DEAD),
            ("human", "run.needs_human", {"reason": "policy decision", "diagnostic": "operator required"}, 1, None, TaskStatus.NEEDS_HUMAN),
        )
        for source, terminal_type, payload, attempt_no, setup, expected_status in cases:
            with self.subTest(source=source):
                repository = f"owner/m5-terminal-{source}"
                task = self.submit(repository=repository, source=f"m5-terminal-{source}").task
                packet = valid_packet()
                packet["provider"]["capabilities"] = ["structured_output"]
                selection = {
                    "provider": packet["provider"],
                    "capability_policy": packet["capability_policy"],
                    "plan": packet["plan"],
                    "workspace_handle": packet["workspace_handle"],
                    "prompt_template_digest": "7" * 64,
                    "role_definition_digest": "8" * 64,
                    "tool_policy_digest": "9" * 64,
                    "output_schema_digest": "a" * 64,
                }
                execution = FactoryService(
                    self.store, execution_registry=trusted_registry(selection)
                ).claim_execution(
                    owner=WORKER.actor_id,
                    role=RunRole.WRITER,
                    repositories=(task.repository_id,),
                    lease_seconds=60,
                    selection=selection,
                    actor=WORKER,
                    now=NOW,
                )
                if attempt_no != 1:
                    import psycopg
                    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                        cursor.execute(
                            "UPDATE factory.attempts SET attempt_no=%s WHERE run_id=%s",
                            (attempt_no, execution.lease.run_id),
                        )
                if setup == "reservation":
                    self.service.reserve_budget(
                        execution.lease,
                        cost_usd_micros=0,
                        token_units=0,
                        wall_seconds=1,
                        reason_digest="b" * 64,
                        idempotency_key="c" * 64,
                        actor=WORKER,
                    )
                elif setup == "event_limit":
                    import psycopg
                    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                        cursor.execute(
                            """UPDATE factory.tasks SET event_limit=(
                              SELECT count(*) FROM factory.task_events
                              WHERE task_id=%s AND NOT mandatory_cleanup
                            ) WHERE task_id=%s""",
                            (task.task_id, task.task_id),
                        )
                self.service.commit_execution_proposal(
                    execution.lease,
                    packet_digest=execution.packet_digest,
                    sequence=1,
                    event_type=terminal_type,
                    payload=payload,
                    actor=WORKER,
                )
                result = FactoryService(
                    self.store, snapshot_broker=TrustedPostgresTestSnapshotBroker()
                ).finalize_execution(
                    execution.lease,
                    packet_digest=execution.packet_digest,
                    actor=WORKER,
                )
                self.assertEqual(result.m4_status, expected_status.value)
                self.assertEqual(self.store.get_task(task.task_id).status, expected_status)
                expected_failure = payload.get("failure_class")
                expected_reason = payload.get("diagnostic") if expected_failure else payload.get("reason")
                self.assertEqual((result.failure_class, result.failure_reason), (expected_failure, expected_reason))
                import psycopg
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT released_at IS NOT NULL FROM factory.runs WHERE run_id=%s",
                        (execution.lease.run_id,),
                    )
                    self.assertTrue(cursor.fetchone()[0])
                    if setup == "reservation":
                        cursor.execute(
                            "SELECT accounting_blocked FROM factory.tasks WHERE task_id=%s",
                            (task.task_id,),
                        )
                        self.assertTrue(cursor.fetchone()[0])

    def test_finalize_db_hash_parity_and_forged_result_rolls_back(self):
        import hashlib
        import psycopg

        canonical = {"failure": "quoted \"snowman ☃\""}
        domain = "adaptive-factory.workspace-notes/v1"
        evidence = ["a" * 64, "b" * 64]
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT trim(factory.execution_contract_hash(NULL,%s)),trim(factory.execution_contract_hash(%s,%s))",
                (canonical_json(canonical).decode(), domain, canonical_json(evidence).decode()),
            )
            plain, separated = cursor.fetchone()
        self.assertEqual(plain, canonical_digest(canonical))
        self.assertEqual(
            separated,
            hashlib.sha256(domain.encode() + b"\0" + canonical_json(evidence)).hexdigest(),
        )

        repository = "owner/m5-forged-finalize"
        task = self.submit(repository=repository, source="m5-forged-finalize").task
        packet = valid_packet()
        packet["provider"]["capabilities"] = ["structured_output"]
        selection = {
            "provider": packet["provider"], "capability_policy": packet["capability_policy"],
            "plan": packet["plan"], "workspace_handle": packet["workspace_handle"],
            "prompt_template_digest": "7" * 64, "role_definition_digest": "8" * 64,
            "tool_policy_digest": "9" * 64, "output_schema_digest": "a" * 64,
        }
        execution = FactoryService(
            self.store, execution_registry=trusted_registry(selection)
        ).claim_execution(
            owner=WORKER.actor_id, role=RunRole.WRITER, repositories=(repository,),
            lease_seconds=60, selection=selection, actor=WORKER, now=NOW,
        )
        terminal = self.service.commit_execution_proposal(
            execution.lease, packet_digest=execution.packet_digest, sequence=1,
            event_type="run.failed",
            payload={"failure_class": "validation", "diagnostic": "quoted \"snowman ☃\""},
            actor=WORKER,
        )
        request = self.store.workspace_snapshot_request(execution.lease, execution.packet_digest)
        snapshot = TrustedPostgresTestSnapshotBroker().snapshot(request)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT trim(manifest_digest) FROM factory.execution_manifests WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            manifest_digest = cursor.fetchone()[0]
        result = WorkspaceResultV1.from_facts({
            "contract_version": 1, "task_id": execution.lease.task_id,
            "run_id": execution.lease.run_id, "task_packet_digest": execution.packet_digest,
            "run_manifest_digest": manifest_digest, "exact_head_sha": snapshot.result_head_sha,
            "workspace_snapshot_digest": snapshot.workspace_snapshot_digest,
            "terminal_stage": "failed", "terminal_proposal_digest": terminal.idempotency_key,
            "artifact_manifest_digest": workspace_evidence_digest("artifacts", []),
            "note_manifest_digest": workspace_evidence_digest("notes", []),
            "usage_evidence_digest": workspace_evidence_digest("usage", []),
            "diagnostics_digest": workspace_evidence_digest("diagnostics", []),
            "m4_status": "needs_human", "failure_class": "validation",
            "failure_reason": "quoted \"snowman ☃\"",
        })
        forged = result.to_dict()
        forged["artifact_manifest_digest"] = "f" * 64
        forged["workspace_result_digest"] = "e" * 64
        unknown_snapshot = snapshot.to_dict()
        unknown_snapshot.pop("contract_version")
        unknown_snapshot["unknown"] = 1
        missing_result = result.to_dict()
        missing_result.pop("m4_status")
        null_result = result.to_dict()
        null_result["workspace_result_digest"] = None
        fractional_snapshot = snapshot.to_dict()
        fractional_snapshot["diff_lines"] = 1.5
        direct_cases = (
            (snapshot.to_dict(), forged, forged["workspace_result_digest"]),
            (unknown_snapshot, result.to_dict(), result.workspace_result_digest),
            (snapshot.to_dict(), missing_result, result.workspace_result_digest),
            (snapshot.to_dict(), null_result, result.workspace_result_digest),
            (fractional_snapshot, result.to_dict(), result.workspace_result_digest),
            (None, result.to_dict(), result.workspace_result_digest),
            (snapshot.to_dict(), None, result.workspace_result_digest),
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("SET ROLE factory_runtime")
            for direct_snapshot, direct_result, direct_digest in direct_cases:
                cursor.execute(
                    "SELECT factory.execution_finalize_commit(%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)",
                    (
                        execution.lease.task_id, execution.lease.run_id, execution.lease.owner,
                        execution.lease.fence, execution.lease.packet_digest, execution.packet_digest,
                        direct_digest, psycopg.types.json.Jsonb(direct_snapshot),
                        psycopg.types.json.Jsonb(direct_result),
                    ),
                )
                self.assertFalse(cursor.fetchone()[0])
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT t.state,r.released_at IS NULL,a.released_at IS NULL,
                at.finished_at IS NULL,(SELECT count(*) FROM factory.workspace_results WHERE run_id=r.run_id)
                FROM factory.tasks t JOIN factory.runs r ON r.run_id=t.current_run_id
                JOIN factory.capacity_allocations a ON a.run_id=r.run_id
                JOIN factory.attempts at ON at.run_id=r.run_id WHERE t.task_id=%s""",
                (task.task_id,),
            )
            self.assertEqual(cursor.fetchone(), ("leased", True, True, True, 0))
            cursor.execute(
                """SELECT
                (SELECT count(*) FROM factory.task_events WHERE task_id=%s),
                (SELECT count(*) FROM factory.audit_log WHERE task_id=%s),
                (SELECT count(*) FROM factory.execution_stage_events e
                  JOIN factory.execution_manifests m USING(manifest_digest) WHERE m.run_id=%s)""",
                (task.task_id, task.task_id, execution.lease.run_id),
            )
            before_counts = cursor.fetchone()
        from unittest.mock import patch
        with patch.object(self.store, "_audit", side_effect=RuntimeError("injected audit failure")):
            with self.assertRaisesRegex(RuntimeError, "injected audit failure"):
                FactoryService(
                    self.store, snapshot_broker=TrustedPostgresTestSnapshotBroker()
                ).finalize_execution(
                    execution.lease, packet_digest=execution.packet_digest, actor=WORKER,
                )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT t.state,r.released_at IS NULL,a.released_at IS NULL,
                at.finished_at IS NULL,m.terminal_at IS NULL,
                (SELECT count(*) FROM factory.workspace_results WHERE run_id=r.run_id),
                (SELECT count(*) FROM factory.task_events WHERE task_id=t.task_id),
                (SELECT count(*) FROM factory.audit_log WHERE task_id=t.task_id),
                (SELECT count(*) FROM factory.execution_stage_events e WHERE e.manifest_digest=m.manifest_digest)
                FROM factory.tasks t JOIN factory.runs r ON r.run_id=t.current_run_id
                JOIN factory.capacity_allocations a ON a.run_id=r.run_id
                JOIN factory.attempts at ON at.run_id=r.run_id
                JOIN factory.execution_manifests m ON m.run_id=r.run_id WHERE t.task_id=%s""",
                (task.task_id,),
            )
            rolled_back = cursor.fetchone()
        self.assertEqual(rolled_back[:6], ("leased", True, True, True, True, 0))
        self.assertEqual(rolled_back[6:], before_counts)
        successful = FactoryService(
            self.store, snapshot_broker=TrustedPostgresTestSnapshotBroker()
        ).finalize_execution(
            execution.lease, packet_digest=execution.packet_digest, actor=WORKER,
        )
        self.assertEqual(successful.workspace_result_digest, result.workspace_result_digest)
        expected_release_key = canonical_digest({
            "action": "execution_finalize", "fence": execution.lease.fence,
            "run_id": execution.lease.run_id, "target": "needs_human",
        })
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT t.current_run_id IS NULL,a.released_at IS NOT NULL,
                (SELECT count(*) FROM factory.workspace_results WHERE run_id=%s),
                at.failure_digest,
                (SELECT trim(idempotency_key) FROM factory.task_events
                  WHERE task_id=t.task_id AND action='released' ORDER BY event_sequence DESC LIMIT 1),
                (SELECT action FROM factory.audit_log
                  WHERE task_id=t.task_id ORDER BY audit_id DESC LIMIT 1)
                FROM factory.tasks t JOIN factory.capacity_allocations a ON a.task_id=t.task_id
                JOIN factory.attempts at ON at.task_id=t.task_id
                WHERE t.task_id=%s""",
                (execution.lease.run_id, task.task_id),
            )
            final_state = cursor.fetchone()
        self.assertEqual(
            final_state,
            (
                True, True, 1, canonical_digest({"failure": "validation"}),
                expected_release_key, "execution_finalize",
            ),
        )

    def test_finalize_and_cancel_share_capacity_then_task_lock_order(self):
        repository = "owner/m5-finalize-cancel-race"
        task = self.submit(repository=repository, source="m5-finalize-cancel-race").task
        packet = valid_packet()
        packet["provider"]["capabilities"] = ["structured_output"]
        selection = {
            "provider": packet["provider"], "capability_policy": packet["capability_policy"],
            "plan": packet["plan"], "workspace_handle": packet["workspace_handle"],
            "prompt_template_digest": "7" * 64, "role_definition_digest": "8" * 64,
            "tool_policy_digest": "9" * 64, "output_schema_digest": "a" * 64,
        }
        execution = FactoryService(
            self.store, execution_registry=trusted_registry(selection)
        ).claim_execution(
            owner=WORKER.actor_id, role=RunRole.WRITER, repositories=(repository,),
            lease_seconds=60, selection=selection, actor=WORKER, now=NOW,
        )
        self.service.commit_execution_proposal(
            execution.lease, packet_digest=execution.packet_digest, sequence=1,
            event_type="run.failed",
            payload={"failure_class": "validation", "diagnostic": "race"}, actor=WORKER,
        )
        import psycopg

        cancel_store = PostgresFactoryStore(
            psycopg.conninfo.make_conninfo(self.runtime_url, application_name="m5_cancel_waiter")
        )
        finalize_store = PostgresFactoryStore(
            psycopg.conninfo.make_conninfo(self.runtime_url, application_name="m5_finalize_waiter")
        )
        cancel_service = FactoryService(cancel_store)
        finalizer = FactoryService(
            finalize_store, snapshot_broker=TrustedPostgresTestSnapshotBroker()
        )

        def wait_until_capacity_blocked(application_name):
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline:
                with psycopg.connect(DATABASE_URL) as observer, observer.cursor() as cursor:
                    cursor.execute(
                        """SELECT count(*) FROM pg_stat_activity
                        WHERE datname=current_database() AND application_name=%s
                          AND state='active' AND wait_event_type='Lock'""",
                        (application_name,),
                    )
                    if cursor.fetchone()[0] == 1:
                        return
                time.sleep(0.02)
            self.fail(f"{application_name} did not block on the capacity lock")

        blocker = psycopg.connect(DATABASE_URL, application_name="m5_capacity_blocker")
        try:
            with blocker.cursor() as cursor:
                cursor.execute(
                    "SELECT scope_key FROM factory.capacity_counters "
                    "WHERE scope_key='global:writer' FOR UPDATE"
                )
            with ThreadPoolExecutor(max_workers=2) as pool:
                cancel_future = pool.submit(
                    cancel_service.cancel, task.task_id, reason="operator race",
                    idempotency_key="d" * 64, actor=OPERATOR, now=NOW,
                )
                wait_until_capacity_blocked("m5_cancel_waiter")
                finalize_future = pool.submit(
                    finalizer.finalize_execution, execution.lease,
                    packet_digest=execution.packet_digest, actor=WORKER,
                )
                wait_until_capacity_blocked("m5_finalize_waiter")
                blocker.rollback()
                cancelled = cancel_future.result(timeout=10)
                with self.assertRaises(FenceError):
                    finalize_future.result(timeout=10)
        finally:
            blocker.rollback()
            blocker.close()
        self.assertEqual(cancelled.status, TaskStatus.CANCELLED)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT t.current_run_id IS NULL,a.released_at IS NOT NULL,
                (SELECT count(*) FROM factory.workspace_results WHERE run_id=%s)
                FROM factory.tasks t JOIN factory.capacity_allocations a ON a.task_id=t.task_id
                WHERE t.task_id=%s""",
                (execution.lease.run_id, task.task_id),
            )
            current_cleared, allocation_released, result_count = cursor.fetchone()
        self.assertEqual((current_cleared, allocation_released, result_count), (True, True, 0))

    def test_forged_grant_role_is_rejected_by_authoritative_run_lock(self):
        task = self.submit(source="m5-forged-grant-role").task
        grant = self.service.claim(
            owner=WORKER.actor_id,
            role=RunRole.WRITER,
            repositories=(task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        forged = type(grant)(
            grant.task_id,
            grant.run_id,
            grant.owner,
            RunRole.READER,
            grant.fence,
            grant.expires_at,
            grant.packet_digest,
        )
        with self.assertRaises(FenceError):
            self.service.heartbeat(forged, actor=WORKER, now=NOW)

    def test_execution_proposals_are_consecutive_bounded_and_terminal(self):
        def claim_execution(source, max_events):
            intake = self.payload(source=source)
            intake["limits"]["max_events"] = max_events
            task = self.service.intake(intake, actor=OPERATOR, now=NOW).task
            packet = valid_packet()
            packet["provider"]["capabilities"] = ["notes", "structured_output", "usage"]
            selection = {
                "provider": packet["provider"],
                "capability_policy": packet["capability_policy"],
                "plan": packet["plan"],
                "workspace_handle": packet["workspace_handle"],
                "prompt_template_digest": "7" * 64,
                "role_definition_digest": "8" * 64,
                "tool_policy_digest": "9" * 64,
                "output_schema_digest": "a" * 64,
            }
            execution = FactoryService(
                self.store, execution_registry=trusted_registry(selection)
            ).claim_execution(
                owner=WORKER.actor_id,
                role=RunRole.WRITER,
                repositories=(task.repository_id,),
                lease_seconds=60,
                selection=selection,
                actor=WORKER,
                now=NOW,
            )
            return execution

        bounded = claim_execution("m5-proposal-limit", 2)
        for sequence in (1, 2):
            self.service.commit_execution_proposal(
                bounded.lease,
                packet_digest=bounded.packet_digest,
                sequence=sequence,
                event_type="note.proposed",
                payload={"note_type": "finding", "body": f"note-{sequence}", "evidence": []},
                actor=WORKER,
            )
        with self.assertRaises(FenceError):
            self.service.commit_execution_proposal(
                bounded.lease,
                packet_digest=bounded.packet_digest,
                sequence=3,
                event_type="note.proposed",
                payload={"note_type": "finding", "body": "over-limit", "evidence": []},
                actor=WORKER,
            )
        self.service.cancel(
            bounded.lease.task_id,
            reason="proposal limit test cleanup",
            idempotency_key="f" * 64,
            actor=OPERATOR,
            now=NOW,
        )

        execution = claim_execution("m5-proposal-order", 3)
        note = self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="note.proposed",
            payload={"note_type": "finding", "body": "first", "evidence": []},
            actor=WORKER,
        )
        with self.assertRaises(FenceError):
            self.service.commit_execution_proposal(
                execution.lease,
                packet_digest=execution.packet_digest,
                sequence=3,
                event_type="usage.reported",
                payload={
                    "provider_call_id": "gap-call",
                    "price_table_digest": "d" * 64,
                    "input_tokens": 1,
                    "output_tokens": 1,
                    "reasoning_tokens": 0,
                    "cost_usd_micros": 1,
                    "output_bytes": 1,
                },
                actor=WORKER,
            )
        self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=2,
            event_type="usage.reported",
            payload={
                "provider_call_id": "ordered-call",
                "price_table_digest": "d" * 64,
                "input_tokens": 1,
                "output_tokens": 1,
                "reasoning_tokens": 0,
                "cost_usd_micros": 1,
                "output_bytes": 1,
            },
            actor=WORKER,
        )
        terminal_key = "e" * 64
        terminal = self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=3,
            event_type="run.completed",
            payload={"summary": "complete"},
            actor=WORKER,
            idempotency_key=terminal_key,
        )
        replay = self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=3,
            event_type="run.completed",
            payload={"summary": "complete"},
            actor=WORKER,
            idempotency_key=terminal_key,
        )
        self.assertEqual(replay.idempotency_key, terminal.idempotency_key)
        import psycopg
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT idempotency_key,body FROM factory.execution_proposals WHERE run_id=%s AND producer_sequence=3",
                (execution.lease.run_id,),
            )
            persisted_key, persisted_body = cursor.fetchone()
            direct_facts = (
                execution.lease.task_id,
                execution.lease.run_id,
                execution.lease.owner,
                execution.lease.fence,
                execution.lease.packet_digest,
                execution.packet_digest,
            )
            cursor.execute(
                "SELECT factory.execution_propose(%s,%s,%s,%s,%s,%s,3,%s,'terminal',%s::jsonb)",
                (*direct_facts, persisted_key, psycopg.types.json.Jsonb(persisted_body)),
            )
            self.assertTrue(cursor.fetchone()[0])
            cursor.execute(
                "SELECT factory.execution_propose(%s,%s,%s,%s,%s,%s,3,%s,'terminal',%s::jsonb)",
                (*direct_facts, "0" * 64, psycopg.types.json.Jsonb(persisted_body)),
            )
            self.assertFalse(cursor.fetchone()[0])
            cursor.execute(
                "SELECT factory.execution_propose(%s,%s,%s,%s,%s,%s,2,%s,'terminal',%s::jsonb)",
                (*direct_facts, persisted_key, psycopg.types.json.Jsonb(persisted_body)),
            )
            self.assertFalse(cursor.fetchone()[0])
        with self.assertRaises(FenceError):
            self.service.commit_execution_proposal(
                execution.lease,
                packet_digest=execution.packet_digest,
                sequence=4,
                event_type="note.proposed",
                payload={"note_type": "finding", "body": "late", "evidence": []},
                actor=WORKER,
            )

        self.service.observe_usage(
            execution.lease,
            provider_call_id="ordered-call",
            price_table_digest="d" * 64,
            cost_usd_micros=1,
            token_units=2,
            output_bytes=1,
            actor=WORKER,
        )
        for stage in (ExecutionStage.RUNNING, ExecutionStage.COLLECTING):
            self.service.advance_execution(
                execution.lease,
                packet_digest=execution.packet_digest,
                stage=stage,
                actor=WORKER,
            )
        finalizer = FactoryService(
            self.store, snapshot_broker=TrustedPostgresTestSnapshotBroker()
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            finalize_future = pool.submit(
                finalizer.finalize_execution,
                execution.lease,
                packet_digest=execution.packet_digest,
                actor=WORKER,
            )
            late_future = pool.submit(
                self.service.commit_execution_proposal,
                execution.lease,
                packet_digest=execution.packet_digest,
                sequence=4,
                event_type="note.proposed",
                payload={"note_type": "finding", "body": "concurrent-late", "evidence": []},
                actor=WORKER,
            )
            result = finalize_future.result(timeout=10)
            with self.assertRaises(FenceError):
                late_future.result(timeout=10)
        self.assertEqual(
            result.note_manifest_digest,
            workspace_evidence_digest("notes", [note.idempotency_key]),
        )

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT producer_sequence,proposal_kind FROM factory.execution_proposals WHERE run_id=%s ORDER BY producer_sequence",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchall(), [(1, "note"), (2, "usage"), (3, "terminal")])
            cursor.execute(
                "SELECT count(*) FROM factory.execution_proposals WHERE run_id=%s",
                (bounded.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone()[0], 2)

    def authority_payload(self, kind: str, source: str, suffix: int):
        import psycopg

        payload = self.payload(source=source)
        if kind == "observation":
            observed_at = NOW - timedelta(seconds=suffix)
            payload["m0_authority"]["observed_at"] = observed_at.isoformat()
            identity = uuid.uuid4()
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO factory.m0_authority_observations
                    (observation_id,observed_at,check_name,exact_head_sha,issuer,evidence_digest,repository_id,policy_digest)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        identity, observed_at, payload["m0_authority"]["check_name"],
                        payload["m0_authority"]["exact_head_sha"], "external-trust-ci-api",
                        uuid.uuid4().hex * 2, payload["repository_id"], payload["policy_digest"],
                    ),
                )
            return payload, "m0_authority_observations", "observation_id", identity
        expires_at = NOW + timedelta(minutes=10)
        identity = f"bootstrap-{suffix}"
        payload["m0_authority"] = {
            "bootstrap_exception": identity,
            "issuer": "repository-owner",
            "scope": "task:intake",
            "expires_at": expires_at.isoformat(),
        }
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO factory.m0_bootstrap_exceptions
                (exception_id,issuer,scope,expires_at,approval_digest,repository_id,policy_digest,action)
                VALUES (%s,'repository-owner','task:intake',%s,%s,%s,%s,'task:intake')""",
                (identity, expires_at, uuid.uuid4().hex * 2, payload["repository_id"], payload["policy_digest"]),
            )
        return payload, "m0_bootstrap_exceptions", "exception_id", identity

    def assert_mandatory_cleanup(self, task_id: str, run_id: str, action: str):
        import psycopg

        audit_action = {"released": "release", "cancelled": "cancel"}[action]
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                (SELECT count(*) FROM factory.task_events WHERE task_id=%s AND action=%s AND mandatory_cleanup),
                (SELECT count(*) FROM factory.audit_log WHERE task_id=%s AND action=%s),
                (SELECT count(*) FROM factory.capacity_allocations WHERE run_id=%s AND released_at IS NULL),
                (SELECT active_count FROM factory.capacity_counters WHERE scope_key='global:reader'),
                (SELECT active_count FROM factory.capacity_counters WHERE scope_key='repository:owner/repository:reader')""",
                (task_id, action, task_id, audit_action, run_id),
            )
            self.assertEqual(cursor.fetchone(), (1, 1, 0, 0, 0))

    def test_duplicate_and_changed_intake_are_atomic_and_immutable(self):
        payload = self.payload(source="same-source")
        first = self.service.intake(payload, actor=OPERATOR, now=NOW)
        duplicate = self.service.intake(payload, actor=OPERATOR, now=NOW)
        changed = self.payload(source="same-source")
        changed["source_digest"] = "8" * 64
        replacement = self.service.intake(changed, actor=OPERATOR, now=NOW)
        self.assertTrue(first.created)
        self.assertFalse(duplicate.created)
        self.assertEqual(first.task.task_id, duplicate.task.task_id)
        self.assertNotEqual(first.task.task_id, replacement.task.task_id)
        self.assertEqual(self.store.get_task(first.task.task_id).status, TaskStatus.SUPERSEDED)

    def test_changed_frozen_head_authority_and_limits_supersede_exact_replay(self):
        import psycopg

        source = "full-frozen-intent"
        original = self.payload(source=source)
        first = self.service.intake(original, actor=OPERATOR, now=NOW)
        self.assertFalse(self.service.intake(original, actor=OPERATOR, now=NOW).created)
        changed_limits = self.payload(source=source)
        changed_limits["limits"]["max_events"] -= 1
        second = self.service.intake(changed_limits, actor=OPERATOR, now=NOW)
        self.assertNotEqual(first.task.task_id, second.task.task_id)
        changed_head = self.payload(source=source)
        for handoff in (changed_head["architecture"], changed_head["governance"]):
            handoff["exact_head_sha"] = "4" * 40
        changed_head["m0_authority"]["exact_head_sha"] = "4" * 40
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO factory.m0_authority_observations
                (observation_id,observed_at,check_name,exact_head_sha,issuer,evidence_digest,repository_id,policy_digest)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    uuid.uuid4(), NOW, changed_head["m0_authority"]["check_name"], "4" * 40,
                    "external-trust-ci-api", "8" * 64, changed_head["repository_id"], changed_head["policy_digest"],
                ),
            )
        third = self.service.intake(changed_head, actor=OPERATOR, now=NOW)
        self.assertNotEqual(second.task.task_id, third.task.task_id)
        self.assertEqual(self.store.get_task(second.task.task_id).status, TaskStatus.SUPERSEDED)

    def test_m0_authority_is_repository_policy_action_and_transaction_bound(self):
        import psycopg

        cross_repository = self.payload(source="cross-authority")
        cross_repository["repository_id"] = "other/repository"
        with self.assertRaises(StoreError):
            self.service.intake(cross_repository, actor=OPERATOR, now=NOW)

        wrong_policy = self.payload(source="wrong-policy")
        wrong_policy["policy_digest"] = "abcdefabcdef" + "1" * 52
        wrong_policy["m0_authority"]["check_name"] = "adaptive-trust-ci/verified@abcdefabcdef"
        with self.assertRaises(StoreError):
            self.service.intake(wrong_policy, actor=OPERATOR, now=NOW)

        exception_expires_at = NOW + timedelta(minutes=10)
        exception_payload = self.payload(source="wrong-exception-scope")
        exception_payload["m0_authority"] = {
            "bootstrap_exception": "local-bootstrap",
            "issuer": "repository-owner",
            "scope": "task:intake",
            "expires_at": exception_expires_at.isoformat(),
        }
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO factory.m0_bootstrap_exceptions
                (exception_id,issuer,scope,expires_at,approval_digest,repository_id,policy_digest,action)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'task:intake')""",
                (
                    "local-bootstrap", "repository-owner", "task:intake", exception_expires_at,
                    "5" * 64, exception_payload["repository_id"], exception_payload["policy_digest"],
                ),
            )
        accepted = self.service.intake(exception_payload, actor=OPERATOR, now=NOW)
        self.assertTrue(accepted.created)
        wrong_scope = self.payload(source="wrong-exception-scope-2")
        wrong_scope["m0_authority"] = {**exception_payload["m0_authority"], "scope": "task:read"}
        with self.assertRaises(StoreError):
            self.service.intake(wrong_scope, actor=OPERATOR, now=NOW)

        race_payload = self.payload(source="revocation-race")
        identity = f"{race_payload['repository_id']}\x1f{race_payload['source_type']}\x1f{race_payload['source_id']}"
        blocker = psycopg.connect(DATABASE_URL)
        blocker.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", (identity,))
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.service.intake, race_payload, actor=OPERATOR, now=NOW)
            with psycopg.connect(DATABASE_URL) as revoker:
                revoker.execute(
                    "UPDATE factory.m0_authority_observations SET revoked_at=clock_timestamp() WHERE repository_id=%s",
                    (race_payload["repository_id"],),
                )
            blocker.execute("SELECT pg_advisory_unlock(hashtextextended(%s,0))", (identity,))
            blocker.close()
            with self.assertRaises(StoreError):
                future.result(timeout=5)

    def test_m0_revocation_before_validation_rejects_observation_and_exception(self):
        import psycopg
        from psycopg import sql

        for offset, kind in enumerate(("observation", "exception"), start=20):
            with self.subTest(kind=kind):
                payload, table, key_column, identity = self.authority_payload(
                    kind, f"revoked-before-{kind}", offset
                )
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        sql.SQL("UPDATE factory.{} SET revoked_at=clock_timestamp() WHERE {}=%s").format(
                            sql.Identifier(table), sql.Identifier(key_column)
                        ),
                        (identity,),
                    )
                with self.assertRaises(StoreError):
                    self.service.intake(payload, actor=OPERATOR, now=NOW)
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT count(*) FROM factory.tasks WHERE source_id=%s", (payload["source_id"],)
                    )
                    self.assertEqual(cursor.fetchone()[0], 0)

    def test_m0_revocation_after_validation_waits_for_intake_commit(self):
        import psycopg
        from psycopg import sql

        class PausingStore(PostgresFactoryStore):
            def __init__(self, database_url):
                super().__init__(database_url)
                self.validated = threading.Event()
                self.resume = threading.Event()

            def _verify_m0_authority(self, cursor, intake):
                valid = super()._verify_m0_authority(cursor, intake)
                self.validated.set()
                if not self.resume.wait(timeout=5):
                    raise RuntimeError("authority validation barrier timed out")
                return valid

        for offset, kind in enumerate(("observation", "exception"), start=30):
            with self.subTest(kind=kind):
                payload, table, key_column, identity = self.authority_payload(
                    kind, f"revoked-after-{kind}", offset
                )
                store = PausingStore(self.runtime_url)
                service = FactoryService(store)

                def intake_then_commit():
                    result = service.intake(payload, actor=OPERATOR, now=NOW)
                    return result, time.monotonic()

                def revoke_then_commit():
                    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                        cursor.execute(
                            sql.SQL("UPDATE factory.{} SET revoked_at=clock_timestamp() WHERE {}=%s").format(
                                sql.Identifier(table), sql.Identifier(key_column)
                            ),
                            (identity,),
                        )
                    return time.monotonic()

                with ThreadPoolExecutor(max_workers=2) as pool:
                    intake_future = pool.submit(intake_then_commit)
                    self.assertTrue(store.validated.wait(timeout=5))
                    revoke_future = pool.submit(revoke_then_commit)
                    revocation_blocked = False
                    try:
                        revoke_future.result(timeout=0.25)
                    except FutureTimeout:
                        revocation_blocked = True
                    finally:
                        store.resume.set()
                    accepted, intake_committed_at = intake_future.result(timeout=5)
                    revoked_at = revoke_future.result(timeout=5)
                self.assertTrue(revocation_blocked)
                self.assertTrue(accepted.created)
                self.assertLessEqual(intake_committed_at, revoked_at)
                later = {**payload, "source_id": f"later-{kind}"}
                with self.assertRaises(StoreError):
                    self.service.intake(later, actor=OPERATOR, now=NOW)

    def test_cancel_and_supersede_release_leases_capacity_once(self):
        import psycopg

        for role, source in ((RunRole.READER, "cancel-reader"), (RunRole.WRITER, "supersede-writer")):
            task = self.submit(source=source).task
            grant = self.service.claim(
                owner="ignored-caller-owner",
                role=role,
                repositories=(task.repository_id,),
                lease_seconds=60,
                actor=WORKER,
                now=NOW,
            )
            self.assertEqual(grant.owner, WORKER.actor_id)
            if role is RunRole.READER:
                first = self.service.cancel(
                    task.task_id, reason="operator", idempotency_key="1" * 64, actor=OPERATOR, now=NOW
                )
                second = self.service.cancel(
                    task.task_id, reason="operator", idempotency_key="1" * 64, actor=OPERATOR, now=NOW
                )
                self.assertEqual(first.status, TaskStatus.CANCELLED)
                self.assertEqual(second.status, TaskStatus.CANCELLED)
            else:
                replacement = self.payload(source=source)
                replacement["source_digest"] = "8" * 64
                self.service.intake(replacement, actor=OPERATOR, now=NOW)
                self.assertEqual(self.store.get_task(task.task_id).status, TaskStatus.SUPERSEDED)
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    "SELECT r.released_at IS NOT NULL,a.released_at IS NOT NULL FROM factory.runs r JOIN factory.capacity_allocations a USING(run_id) WHERE r.run_id=%s",
                    (grant.run_id,),
                )
                self.assertEqual(cursor.fetchone(), (True, True))
                cursor.execute("SELECT active_count FROM factory.capacity_counters WHERE scope_key=%s", (f"global:{role.value}",))
                self.assertEqual(cursor.fetchone()[0], 0)
            result = self.service.reconcile(actor=OPERATOR, now=NOW)
            self.assertEqual(result.repaired, 0)

    def test_reservations_are_bounded_replay_safe_and_settled_by_usage(self):
        import psycopg

        task = self.submit(source="accounting-invariant").task
        grant = self.service.claim(
            owner="ignored",
            role=RunRole.READER,
            repositories=(task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        reservation = self.service.reserve_budget(
            grant,
            cost_usd_micros=25_000_000,
            token_units=2_000_000,
            wall_seconds=14_400,
            reason_digest="a" * 64,
            idempotency_key="b" * 64,
            actor=WORKER,
        )
        duplicate = self.service.reserve_budget(
            grant,
            cost_usd_micros=25_000_000,
            token_units=2_000_000,
            wall_seconds=14_400,
            reason_digest="a" * 64,
            idempotency_key="b" * 64,
            actor=WORKER,
        )
        self.assertEqual(duplicate, reservation)
        with self.assertRaises(BudgetError):
            self.service.reserve_budget(
                grant,
                cost_usd_micros=0,
                token_units=0,
                wall_seconds=1,
                reason_digest="c" * 64,
                idempotency_key="d" * 64,
                actor=WORKER,
            )
        self.service.observe_usage(
            grant,
            provider_call_id="provider-call",
            price_table_digest="2" * 64,
            cost_usd_micros=25_000_000,
            token_units=2_000_000,
            output_bytes=1,
            actor=WORKER,
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT cost_reserved_micros,cost_observed_micros,tokens_reserved,tokens_observed,wall_reserved_seconds FROM factory.tasks WHERE task_id=%s",
                (task.task_id,),
            )
            self.assertEqual(cursor.fetchone(), (0, 25_000_000, 0, 2_000_000, 0))
            cursor.execute("SELECT released_at IS NOT NULL FROM factory.budget_reservations WHERE reservation_id=%s", (reservation,))
            self.assertTrue(cursor.fetchone()[0])

    def test_completion_requires_unblocked_settled_accounting(self):
        task = self.submit(source="completion-accounting").task
        grant = self.service.claim(
            owner="ignored",
            role=RunRole.READER,
            repositories=(task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        with self.assertRaises(BudgetError):
            self.service.release(grant, outcome="completed", actor=WORKER, now=NOW)
        self.service.reserve_budget(
            grant,
            cost_usd_micros=0,
            token_units=0,
            wall_seconds=1,
            reason_digest="a" * 64,
            idempotency_key="b" * 64,
            actor=WORKER,
        )
        with self.assertRaises(BudgetError):
            self.service.release(grant, outcome="completed", actor=WORKER, now=NOW)
        self.service.observe_usage(
            grant,
            provider_call_id="settled",
            price_table_digest="2" * 64,
            cost_usd_micros=0,
            token_units=0,
            output_bytes=0,
            actor=WORKER,
        )
        self.assertEqual(self.service.release(grant, outcome="completed", actor=WORKER, now=NOW), TaskStatus.READY_FOR_HUMAN)

    def test_api_mutations_replay_exact_results_and_reject_changed_commands(self):
        from fastapi.testclient import TestClient

        task = self.submit(source="api-idempotency").task
        token = "worker-" + "api-" + "credential"
        client = TestClient(create_app(self.service, Authenticator({token: WORKER})))
        headers = {
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "command-replay-001",
            "X-Correlation-ID": "correlation-replay-001",
        }
        payload = {"role": "reader", "repositories": [task.repository_id], "lease_seconds": 60}
        first = client.post("/v1/claims", headers=headers, json=payload)
        duplicate = client.post("/v1/claims", headers=headers, json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(first.json(), duplicate.json())
        changed = client.post("/v1/claims", headers=headers, json={**payload, "lease_seconds": 61})
        self.assertEqual(changed.status_code, 409)
        grant = first.json()["grant"]
        accounting_headers = {**headers, "Idempotency-Key": "accounting-command-001"}
        reserved = client.post(
            "/v1/budget-reservations",
            headers=accounting_headers,
            json={"grant": grant, "cost_usd_micros": 0, "token_units": 0, "wall_seconds": 1, "reason_digest": "a" * 64},
        )
        self.assertEqual(reserved.status_code, 200)
        usage = client.post(
            "/v1/usage-observations",
            headers={**headers, "Idempotency-Key": "usage-command-001"},
            json={"grant": grant, "provider_call_id": "api-call", "price_table_digest": "2" * 64, "cost_usd_micros": 0, "token_units": 0, "output_bytes": 0},
        )
        self.assertEqual(usage.status_code, 200)
        proposal_headers = {**headers, "Idempotency-Key": "proposal-command-001"}
        proposed = client.post("/v1/proposals", headers=proposal_headers, json={"grant": grant, "outcome": "completed"})
        proposed_replay = client.post("/v1/proposals", headers=proposal_headers, json={"grant": grant, "outcome": "completed"})
        self.assertEqual((proposed.status_code, proposed_replay.status_code), (200, 200))
        self.assertEqual(proposed.json(), proposed_replay.json())

        operator_token = "operator-" + "api-" + "credential"
        operator_client = TestClient(create_app(self.service, Authenticator({operator_token: OPERATOR})))
        operator_headers = {
            "Authorization": f"Bearer {operator_token}",
            "Idempotency-Key": "2d42f0ba-5244-4b04-8494-1abcecda988d",
            "X-Correlation-ID": "kill-correlation-001",
        }
        killed = operator_client.post(
            "/v1/kill-switches",
            headers=operator_headers,
            json={"scope_key": "global", "enabled": True, "reason": "stop"},
        )
        replay = operator_client.post(
            "/v1/kill-switches",
            headers=operator_headers,
            json={"scope_key": "global", "enabled": True, "reason": "stop"},
        )
        conflict = operator_client.post(
            "/v1/kill-switches",
            headers=operator_headers,
            json={"scope_key": "global", "enabled": False, "reason": "stop"},
        )
        self.assertEqual((killed.status_code, replay.status_code, conflict.status_code), (200, 200, 409))
        self.assertEqual(killed.json(), replay.json())

    def test_empty_claim_is_replayed_after_work_arrives(self):
        from fastapi.testclient import TestClient
        import psycopg

        token = "worker-" + "empty-claim-" + "credential"
        client = TestClient(create_app(self.service, Authenticator({token: WORKER})))
        headers = {
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "empty-claim-command-001",
            "X-Correlation-ID": "empty-claim-correlation-001",
        }
        payload = {"role": "reader", "repositories": ["owner/repository"], "lease_seconds": 60}
        first = client.post("/v1/claims", headers=headers, json=payload)
        self.assertEqual(first.json(), {"grant": None})
        self.submit(source="arrived-after-empty-claim")
        replay = client.post("/v1/claims", headers=headers, json=payload)
        conflict = client.post("/v1/claims", headers=headers, json={**payload, "lease_seconds": 61})
        self.assertEqual(replay.json(), first.json())
        self.assertEqual(conflict.status_code, 409)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT correlation_id,result FROM factory.command_results WHERE action='claim'"
            )
            self.assertEqual(cursor.fetchone(), ("empty-claim-correlation-001", {"grant": None}))

    def test_accounting_commands_replay_before_stale_fence_and_preserve_correlation(self):
        from fastapi.testclient import TestClient
        import psycopg

        task = self.submit(source="accounting-command-replay").task
        grant = self.service.claim(
            owner="ignored", role=RunRole.READER, repositories=(task.repository_id,),
            lease_seconds=60, actor=WORKER, now=NOW,
        )
        token = "worker-" + "accounting-" + "credential"
        client = TestClient(create_app(self.service, Authenticator({token: WORKER})))
        grant_body = {
            "task_id": grant.task_id, "run_id": grant.run_id, "owner": grant.owner,
            "role": grant.role.value, "fence": grant.fence,
            "expires_at": grant.expires_at.isoformat().replace("+00:00", "Z"),
            "packet_digest": grant.packet_digest,
        }
        reserve_headers = {
            "Authorization": f"Bearer {token}", "Idempotency-Key": "reservation-command-001",
            "X-Correlation-ID": "reservation-correlation-001",
        }
        reserve_body = {
            "grant": grant_body, "cost_usd_micros": 0, "token_units": 0,
            "wall_seconds": 1, "reason_digest": "a" * 64,
        }
        reserved = client.post("/v1/budget-reservations", headers=reserve_headers, json=reserve_body)
        self.assertEqual(reserved.status_code, 200)

        usage_task = self.submit(source="usage-command-replay").task
        usage_grant = self.service.claim(
            owner="ignored", role=RunRole.READER, repositories=(usage_task.repository_id,),
            lease_seconds=60, actor=WORKER, now=NOW,
        )
        usage_grant_body = {
            "task_id": usage_grant.task_id, "run_id": usage_grant.run_id, "owner": usage_grant.owner,
            "role": usage_grant.role.value, "fence": usage_grant.fence,
            "expires_at": usage_grant.expires_at.isoformat().replace("+00:00", "Z"),
            "packet_digest": usage_grant.packet_digest,
        }
        usage_headers = {
            "Authorization": f"Bearer {token}", "Idempotency-Key": "usage-command-001",
            "X-Correlation-ID": "usage-correlation-001",
        }
        usage_body = {
            "grant": usage_grant_body, "provider_call_id": "provider-call-one",
            "price_table_digest": "2" * 64, "cost_usd_micros": 0,
            "token_units": 0, "output_bytes": 0,
        }
        usage = client.post("/v1/usage-observations", headers=usage_headers, json=usage_body)
        replay = client.post("/v1/usage-observations", headers=usage_headers, json=usage_body)
        changed = client.post(
            "/v1/usage-observations", headers=usage_headers,
            json={**usage_body, "provider_call_id": "provider-call-two"},
        )
        self.assertEqual((usage.status_code, replay.status_code, changed.status_code), (200, 200, 409))
        self.assertEqual(usage.json(), replay.json())
        self.service.release(grant, outcome=FailureClass.WORKER_LOST, actor=WORKER, now=NOW)
        stale_replay = client.post("/v1/budget-reservations", headers=reserve_headers, json=reserve_body)
        self.assertEqual(stale_replay.status_code, 200)
        self.assertEqual(stale_replay.json(), reserved.json())
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT action,correlation_id FROM factory.command_results WHERE action IN ('reserve_budget','observe_usage') ORDER BY action"
            )
            self.assertEqual(
                cursor.fetchall(),
                [("observe_usage", "usage-correlation-001"), ("reserve_budget", "reservation-correlation-001")],
            )

    def test_two_workers_get_one_task_and_late_fence_is_rejected(self):
        self.submit()

        def claim(index):
            return self.service.claim(
                owner=f"worker-{index}",
                role=RunRole.READER,
                repositories=("owner/repository",),
                lease_seconds=30,
                actor=WORKER,
                now=NOW,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            grants = list(pool.map(claim, range(2)))
        live = [grant for grant in grants if grant]
        self.assertEqual(len(live), 1)
        old = live[0]
        import psycopg

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",
                (old.run_id,),
            )
        self.service.reconcile(actor=OPERATOR, now=NOW)
        new = self.service.claim(
            owner="worker-new",
            role=RunRole.READER,
            repositories=("owner/repository",),
            lease_seconds=30,
            actor=WORKER,
            now=NOW,
        )
        self.assertGreater(new.fence, old.fence)
        with self.assertRaises(FenceError):
            self.service.heartbeat(old, actor=WORKER, now=NOW)

    def test_reconcile_isolates_orphan_and_repairs_valid_expired_lease(self):
        import psycopg

        first = self.submit(source="orphan-expired").task
        second = self.submit(source="valid-expired").task
        grants = [
            self.service.claim(owner="ignored", role=RunRole.READER, repositories=(first.repository_id,), lease_seconds=60, actor=WORKER, now=NOW),
            self.service.claim(owner="ignored", role=RunRole.READER, repositories=(second.repository_id,), lease_seconds=60, actor=WORKER, now=NOW),
        ]
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=ANY(%s)", ([grant.run_id for grant in grants],))
            cursor.execute("UPDATE factory.tasks SET state='cancelled',current_run_id=NULL,current_fence=NULL,terminal_at=clock_timestamp() WHERE task_id=%s", (first.task_id,))
        result = self.service.reconcile(actor=OPERATOR, now=NOW)
        replay = self.service.reconcile(actor=OPERATOR, now=NOW)
        self.assertEqual((result.candidates, result.repaired, replay.repaired), (2, 2, 0))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM factory.capacity_allocations WHERE released_at IS NULL")
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute("SELECT active_count FROM factory.capacity_counters WHERE scope_key='global:reader'")
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_reader_and_writer_capacity_is_enforced(self):
        for index in range(21):
            self.submit(repository="repo/a" if index < 11 else "repo/b")
        readers = []
        for index in range(30):
            grant = self.service.claim(
                owner=f"reader-{index}",
                role=RunRole.READER,
                repositories=("repo/a", "repo/b"),
                lease_seconds=60,
                actor=WORKER,
                now=NOW,
            )
            if grant:
                readers.append(grant)
        self.assertEqual(len(readers), 20)
        self.assertEqual(sum(self.store.get_task(grant.task_id).repository_id == "repo/a" for grant in readers), 10)
        self.assertIsNone(
            self.service.claim(
                owner="reader-21", role=RunRole.READER, repositories=("repo/a", "repo/b"),
                lease_seconds=60, actor=WORKER, now=NOW,
            )
        )
        for index, grant in enumerate(readers):
            self.service.observe_usage(
                grant,
                provider_call_id=f"capacity-{index}",
                price_table_digest="2" * 64,
                cost_usd_micros=0,
                token_units=0,
                output_bytes=0,
                actor=WORKER,
            )
            self.service.release(grant, outcome="completed", actor=WORKER, now=NOW)
        for index in range(2):
            self.submit(repository="repo/w", source=f"writer-{index}")
        first = self.service.claim(
            owner="writer-1", role=RunRole.WRITER, repositories=("repo/w",), lease_seconds=60, actor=WORKER, now=NOW
        )
        second = self.service.claim(
            owner="writer-2", role=RunRole.WRITER, repositories=("repo/w",), lease_seconds=60, actor=WORKER, now=NOW
        )
        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_retry_budget_kill_and_reconcile_fail_closed(self):
        task = self.submit().task
        for attempt in range(1, 4):
            grant = self.service.claim(
                owner=f"worker-{attempt}",
                role=RunRole.READER,
                repositories=(task.repository_id,),
                lease_seconds=30,
                actor=WORKER,
                now=NOW,
            )
            self.service.release(grant, outcome=FailureClass.WORKER_LOST, actor=WORKER, now=NOW)
        self.assertEqual(self.store.get_task(task.task_id).status, TaskStatus.DEAD)

        task = self.submit(source="budget").task
        grant = self.service.claim(
            owner="budget-worker",
            role=RunRole.READER,
            repositories=(task.repository_id,),
            lease_seconds=30,
            actor=WORKER,
            now=NOW,
        )
        self.service.reserve_budget(
            grant,
            cost_usd_micros=25_000_000,
            token_units=2_000_000,
            wall_seconds=30,
            reason_digest="a" * 64,
            idempotency_key="b" * 64,
            actor=WORKER,
        )
        with self.assertRaises(BudgetError):
            self.service.reserve_budget(
                grant,
                cost_usd_micros=1,
                token_units=0,
                wall_seconds=0,
                reason_digest="c" * 64,
                idempotency_key="d" * 64,
                actor=WORKER,
            )

        usage_task = self.submit(source="missing-accounting").task
        usage_grant = self.service.claim(
            owner="usage-worker",
            role=RunRole.READER,
            repositories=(usage_task.repository_id,),
            lease_seconds=30,
            actor=WORKER,
            now=NOW,
        )
        with self.assertRaises(BudgetError):
            self.service.observe_usage(
                usage_grant,
                provider_call_id="provider-call-1",
                price_table_digest=None,
                cost_usd_micros=1,
                token_units=1,
                output_bytes=1,
                actor=WORKER,
            )
        with self.assertRaises(BudgetError):
            self.service.reserve_budget(
                usage_grant,
                cost_usd_micros=0,
                token_units=0,
                wall_seconds=0,
                reason_digest="f" * 64,
                idempotency_key="1" * 64,
                actor=WORKER,
            )

        output_payload = self.payload(source="output-budget")
        output_payload["limits"]["max_output_bytes"] = 1
        output_task = self.service.intake(output_payload, actor=OPERATOR, now=NOW).task
        output_grant = self.service.claim(
            owner="output-worker",
            role=RunRole.READER,
            repositories=(output_task.repository_id,),
            lease_seconds=30,
            actor=WORKER,
            now=NOW,
        )
        first_usage = self.service.observe_usage(
            output_grant,
            provider_call_id="output-1",
            price_table_digest="2" * 64,
            cost_usd_micros=0,
            token_units=0,
            output_bytes=1,
            actor=WORKER,
        )
        duplicate_usage = self.service.observe_usage(
            output_grant,
            provider_call_id="output-1",
            price_table_digest="2" * 64,
            cost_usd_micros=0,
            token_units=0,
            output_bytes=1,
            actor=WORKER,
        )
        self.assertTrue(first_usage.created)
        self.assertFalse(duplicate_usage.created)
        self.assertEqual(first_usage.observation_id, duplicate_usage.observation_id)
        with self.assertRaises(StoreError):
            self.service.observe_usage(
                output_grant,
                provider_call_id="output-1",
                price_table_digest="2" * 64,
                cost_usd_micros=1,
                token_units=0,
                output_bytes=1,
                actor=WORKER,
            )
        with self.assertRaises(BudgetError):
            self.service.observe_usage(
                output_grant,
                provider_call_id="output-2",
                price_table_digest="2" * 64,
                cost_usd_micros=0,
                token_units=0,
                output_bytes=1,
                actor=WORKER,
            )

        self.service.set_kill(
            scope_key="global", enabled=True, reason="operator-stop", idempotency_key="e" * 64, actor=OPERATOR, now=NOW
        )
        self.submit(source="killed")
        self.assertIsNone(
            self.service.claim(
                owner="blocked",
                role=RunRole.READER,
                repositories=("owner/repository",),
                lease_seconds=30,
                actor=WORKER,
                now=NOW,
            )
        )

    def test_execution_recovery_is_fenced_idempotent_and_artifact_blind(self):
        import psycopg

        repository = "owner/m5-recovery"
        task = self.submit(repository=repository, source="m5-recovery").task
        packet = valid_packet()
        packet["provider"]["capabilities"] = sorted(
            {*packet["provider"]["capabilities"], "artifacts"}
        )
        selection = {
            "provider": packet["provider"],
            "capability_policy": packet["capability_policy"],
            "plan": packet["plan"],
            "workspace_handle": packet["workspace_handle"],
            "prompt_template_digest": "7" * 64,
            "role_definition_digest": "8" * 64,
            "tool_policy_digest": "9" * 64,
            "output_schema_digest": "a" * 64,
        }
        execution_service = FactoryService(
            self.store, execution_registry=trusted_registry(selection),
        )
        execution = execution_service.claim_execution(
            owner=WORKER.actor_id, role=RunRole.WRITER, repositories=(repository,),
            lease_seconds=60, selection=selection, actor=WORKER, now=NOW,
        )
        workspace = FakeWorkspaceBroker()
        handle = WorkspaceHandle(
            execution.lease.task_id, execution.lease.run_id, execution.workspace_handle,
        )
        workspace.register(
            handle,
            WorkspacePolicy(("factory/src",), ("read", "write"), ("LANG",), ()),
        )
        attestation = TrustedPostgresTestArtifactBroker().attest_artifact(
            ArtifactAttestationRequest.from_facts({
                "task_id": execution.lease.task_id,
                "run_id": execution.lease.run_id,
                "repository_id": repository,
                "packet_digest": execution.packet_digest,
                "workspace_handle": execution.workspace_handle,
                "producer_sequence": 1,
                "fence": execution.lease.fence,
                "author_role": "writer",
                "artifact_class": "report",
                "path": "factory/src/recovery-evidence.patch",
                "sha256": "b" * 64,
                "size_bytes": 12,
                "media_type": "text/plain",
            })
        )
        recorded = PostgresArtifactAttestationStore(
            self.artifact_attestor_url,
        ).record_artifact_attestation(attestation)
        self.assertEqual(recorded, attestation)
        self.assertEqual(self.store.execution_recovery_candidates(limit=100, cursor=None), ())
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE factory.capacity_allocations SET released_at=clock_timestamp() WHERE run_id=%s",
                    (execution.lease.run_id,),
                )
                cursor.execute(
                    "SELECT count(*) FROM factory.execution_recovery_candidates(100,NULL,NULL)"
                )
                self.assertEqual(cursor.fetchone()[0], 0)
                cursor.execute(
                    "UPDATE factory.capacity_allocations SET released_at=NULL WHERE run_id=%s",
                    (execution.lease.run_id,),
                )
                cursor.execute(
                    "UPDATE factory.runs SET released_at=clock_timestamp() WHERE run_id=%s",
                    (execution.lease.run_id,),
                )
                cursor.execute(
                    "SELECT count(*) FROM factory.execution_recovery_candidates(100,NULL,NULL)"
                )
                self.assertEqual(cursor.fetchone()[0], 0)
                cursor.execute(
                    "UPDATE factory.capacity_allocations SET released_at=clock_timestamp() WHERE run_id=%s",
                    (execution.lease.run_id,),
                )
                cursor.execute(
                    "SELECT count(*) FROM factory.execution_recovery_candidates(100,NULL,NULL)"
                )
                self.assertEqual(cursor.fetchone()[0], 1)
            connection.rollback()
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        self.assertEqual(self.service.reconcile(actor=OPERATOR, now=NOW).repaired, 1)
        candidates = self.store.execution_recovery_candidates(limit=100, cursor=None)
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(
            (candidate.task_id, candidate.run_id, candidate.manifest_digest),
            (task.task_id, execution.lease.run_id, execution.manifest_digest),
        )

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT to_jsonb(t),to_jsonb(r),to_jsonb(a),to_jsonb(at),
                (SELECT count(*) FROM factory.execution_artifact_attestations),
                (SELECT count(*) FROM factory.execution_proposals WHERE run_id=r.run_id),
                (SELECT count(*) FROM factory.workspace_results WHERE run_id=r.run_id)
                FROM factory.tasks t JOIN factory.runs r ON r.task_id=t.task_id
                JOIN factory.capacity_allocations a ON a.run_id=r.run_id
                JOIN factory.attempts at ON at.run_id=r.run_id
                WHERE r.run_id=%s""",
                (execution.lease.run_id,),
            )
            immutable_before = cursor.fetchone()
            cursor.execute(
                "SELECT to_jsonb(a) FROM factory.execution_artifact_attestations a WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            attestation_before = cursor.fetchone()[0]
        self.store.record_execution_cleanup_failure(candidate)
        self.store.record_execution_cleanup_failure(candidate)
        result = ExecutionRecovery(self.store, workspace).reconcile(limit=100)
        replay = ExecutionRecovery(self.store, workspace).reconcile(limit=100)
        self.assertEqual(
            (result.candidates, result.orphaned, result.cursor, replay.candidates),
            (1, 1, candidate.cursor, 0),
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT to_jsonb(t),to_jsonb(r),to_jsonb(a),to_jsonb(at),
                (SELECT count(*) FROM factory.execution_artifact_attestations),
                (SELECT count(*) FROM factory.execution_proposals WHERE run_id=r.run_id),
                (SELECT count(*) FROM factory.workspace_results WHERE run_id=r.run_id)
                FROM factory.tasks t JOIN factory.runs r ON r.task_id=t.task_id
                JOIN factory.capacity_allocations a ON a.run_id=r.run_id
                JOIN factory.attempts at ON at.run_id=r.run_id
                WHERE r.run_id=%s""",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone(), immutable_before)
            cursor.execute(
                "SELECT to_jsonb(a) FROM factory.execution_artifact_attestations a WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone()[0], attestation_before)
            cursor.execute(
                """SELECT m.stage,m.terminal_at IS NOT NULL,
                count(e.stage_event_id),count(e.stage_event_id) FILTER (WHERE e.stage='orphaned')
                FROM factory.execution_manifests m
                JOIN factory.execution_stage_events e USING(manifest_digest)
                WHERE m.run_id=%s GROUP BY m.stage,m.terminal_at""",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone(), ("orphaned", True, 2, 1))
            cursor.execute(
                "SELECT count(*),min(failure_code),max(failure_code) FROM factory.execution_recovery_cleanup_failures"
            )
            self.assertEqual(cursor.fetchone(), (1, "workspace_cleanup_failed", "workspace_cleanup_failed"))
            cursor.execute(
                """SELECT
                (SELECT count(*) FROM factory.execution_recovery_cleanup_successes),
                execution_claimed,execution_stage_transitions,execution_orphaned,
                execution_workspace_released,execution_cleanup_failed
                FROM factory.metric_counters WHERE singleton"""
            )
            self.assertEqual(cursor.fetchone(), (1, 1, 2, 1, 1, 1))
        with self.assertRaises(FenceError):
            self.service.commit_execution_proposal(
                execution.lease, packet_digest=execution.packet_digest, sequence=1,
                event_type="note.proposed",
                payload={"note_type": "finding", "body": "late", "evidence": []},
                actor=WORKER,
            )
        replacement = execution_service.claim_execution(
            owner=WORKER.actor_id, role=RunRole.WRITER, repositories=(repository,),
            lease_seconds=60, selection=selection, actor=WORKER, now=NOW,
        )
        self.assertGreater(replacement.lease.fence, execution.lease.fence)

    def test_execution_recovery_capabilities_and_metrics_are_fixed(self):
        import psycopg

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                has_function_privilege('factory_runtime','factory.execution_recovery_candidates(integer,timestamptz,uuid)','EXECUTE'),
                has_function_privilege('factory_runtime','factory.execution_orphan_terminalize(uuid,char)','EXECUTE'),
                has_function_privilege('factory_runtime','factory.execution_recovery_cleanup_failed(uuid,char)','EXECUTE'),
                has_function_privilege('factory_runtime','factory.execution_recovery_cleanup_succeeded(uuid,char)','EXECUTE'),
                has_function_privilege('public','factory.execution_orphan_terminalize(uuid,char)','EXECUTE'),
                has_function_privilege('factory_artifact_attestor','factory.execution_orphan_terminalize(uuid,char)','EXECUTE'),
                has_table_privilege('factory_runtime','factory.execution_recovery_cleanup_failures','SELECT'),
                has_table_privilege('factory_runtime','factory.execution_manifests','UPDATE')"""
            )
            self.assertEqual(
                cursor.fetchone(),
                (True, True, True, True, False, False, False, False),
            )
            cursor.execute(
                "SELECT lower(pg_get_functiondef('factory.execution_orphan_terminalize(uuid,char)'::regprocedure))"
            )
            terminalizer = cursor.fetchone()[0]
            cursor.execute(
                """SELECT string_agg(lower(pg_get_functiondef(p.oid)),E'\\n' ORDER BY p.proname)
                FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                WHERE n.nspname='factory' AND p.proname IN (
                  'execution_recovery_candidates','execution_orphan_terminalize',
                  'execution_recovery_cleanup_failed','execution_recovery_cleanup_succeeded')"""
            )
            all_recovery_functions = cursor.fetchone()[0]
            self.assertNotIn("execution_artifact_attestations", all_recovery_functions)
        for forbidden in (
            "execution_proposals", "workspace_results", "execution_artifact_attestations",
            "update factory.tasks", "update factory.runs", "update factory.attempts",
            "update factory.capacity_allocations",
        ):
            self.assertNotIn(forbidden, terminalizer)
        metrics = self.store.metrics()
        self.assertEqual(
            tuple(metrics),
            (
                "factory_intake_and_rejection_outcomes_total",
                "factory_lease_reclaim_and_fence_rejection_total",
                "factory_capacity_budget_kill_and_reconcile_outcomes_total",
                "factory_execution_claim_and_stage_outcomes_total",
                "factory_execution_protocol_and_proposal_outcomes_total",
                "factory_execution_orphan_and_cleanup_outcomes_total",
            ),
        )
        self.assertEqual(
            set(metrics["factory_execution_claim_and_stage_outcomes_total"]),
            {"claimed", "stage_transitions"},
        )
        self.assertEqual(
            set(metrics["factory_execution_protocol_and_proposal_outcomes_total"]),
            {"note", "artifact", "usage", "terminal"},
        )
        self.assertEqual(
            set(metrics["factory_execution_orphan_and_cleanup_outcomes_total"]),
            {"orphaned", "workspace_released", "cleanup_failed"},
        )

    def test_execution_recovery_keysets_and_terminalizes_concurrently_once(self):
        import psycopg

        def released_candidate(label):
            repository = f"owner/{label}"
            task = self.submit(repository=repository, source=label).task
            packet = valid_packet()
            selection = {
                "provider": packet["provider"],
                "capability_policy": packet["capability_policy"],
                "plan": packet["plan"],
                "workspace_handle": packet["workspace_handle"],
                "prompt_template_digest": "7" * 64,
                "role_definition_digest": "8" * 64,
                "tool_policy_digest": "9" * 64,
                "output_schema_digest": "a" * 64,
            }
            execution = FactoryService(
                self.store, execution_registry=trusted_registry(selection),
            ).claim_execution(
                owner=WORKER.actor_id, role=RunRole.WRITER, repositories=(repository,),
                lease_seconds=60, selection=selection, actor=WORKER, now=NOW,
            )
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",
                    (execution.lease.run_id,),
                )
            self.assertEqual(self.service.reconcile(actor=OPERATOR, now=NOW).repaired, 1)
            return execution

        first = released_candidate("m5-keyset-first")
        second = released_candidate("m5-keyset-second")
        all_candidates = self.store.execution_recovery_candidates(limit=100, cursor=None)
        self.assertEqual(
            {item.run_id for item in all_candidates},
            {first.lease.run_id, second.lease.run_id},
        )
        self.assertEqual(
            tuple(item.cursor for item in all_candidates),
            tuple(sorted(item.cursor for item in all_candidates)),
        )
        page_one = self.store.execution_recovery_candidates(limit=1, cursor=None)
        page_two = self.store.execution_recovery_candidates(limit=1, cursor=page_one[0].cursor)
        self.assertEqual(page_one + page_two, all_candidates)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("SET LOCAL enable_seqscan=off")
            cursor.execute(
                """EXPLAIN (FORMAT JSON) SELECT m.task_id,m.run_id,m.manifest_digest,
                m.workspace_handle,m.updated_at FROM factory.execution_manifests m
                JOIN factory.runs r ON r.run_id=m.run_id AND r.task_id=m.task_id
                JOIN factory.capacity_allocations a ON a.run_id=m.run_id AND a.task_id=m.task_id
                WHERE m.terminal_at IS NULL AND r.released_at IS NOT NULL
                  AND a.released_at IS NOT NULL ORDER BY m.updated_at,m.run_id LIMIT 100"""
            )
            self.assertIn("execution_manifests_recovery", str(cursor.fetchone()[0]))

        first_candidate, second_candidate = all_candidates
        self.store.record_execution_cleanup_success(first_candidate)
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = sorted(pool.map(
                lambda _index: self.store.terminalize_execution_orphan(first_candidate),
                range(2),
            ))
        self.assertEqual(outcomes, ["already_terminal", "orphaned"])
        # A terminalizer racing ahead cannot erase the independently observed cleanup.
        self.assertEqual(
            self.store.terminalize_execution_orphan(second_candidate), "orphaned",
        )
        self.store.record_execution_cleanup_success(second_candidate)
        self.store.record_execution_cleanup_success(second_candidate)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                (SELECT count(*) FROM factory.execution_stage_events e
                  JOIN factory.execution_manifests m USING(manifest_digest)
                  WHERE m.run_id=%s AND e.stage='orphaned'),
                (SELECT count(*) FROM factory.execution_recovery_cleanup_successes),
                (SELECT execution_orphaned FROM factory.metric_counters WHERE singleton),
                (SELECT execution_workspace_released FROM factory.metric_counters WHERE singleton)""",
                (first_candidate.run_id,),
            )
            self.assertEqual(cursor.fetchone(), (1, 2, 2, 2))

    def test_release_metrics_inventory_tracks_durable_operations_and_rejections(self):
        import psycopg
        from fastapi.testclient import TestClient

        self.submit(source="metrics-queued")
        dead = self.submit(source="metrics-dead").task
        for attempt in range(3):
            grant = self.service.claim(
                owner=f"metrics-dead-{attempt}", role=RunRole.READER,
                repositories=(dead.repository_id,), lease_seconds=30, actor=WORKER, now=NOW,
            )
            self.service.release(grant, outcome=FailureClass.WORKER_LOST, actor=WORKER, now=NOW)

        reserved = self.submit(source="metrics-reserved").task
        reserved_grant = self.service.claim(
            owner="metrics-reserved", role=RunRole.READER, repositories=(reserved.repository_id,),
            lease_seconds=30, actor=WORKER, now=NOW,
        )
        self.service.reserve_budget(
            reserved_grant, cost_usd_micros=7, token_units=11, wall_seconds=13,
            reason_digest="a" * 64, idempotency_key="b" * 64, actor=WORKER,
        )

        observed = self.submit(source="metrics-observed").task
        observed_grant = self.service.claim(
            owner="metrics-observed", role=RunRole.READER, repositories=(observed.repository_id,),
            lease_seconds=30, actor=WORKER, now=NOW,
        )
        self.service.observe_usage(
            observed_grant, provider_call_id="metrics-call", price_table_digest="c" * 64,
            cost_usd_micros=5, token_units=6, output_bytes=7, actor=WORKER,
        )

        repair = self.submit(source="metrics-repair").task
        repair_grant = self.service.claim(
            owner="metrics-repair", role=RunRole.READER, repositories=(repair.repository_id,),
            lease_seconds=30, actor=WORKER, now=NOW,
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",
                (repair_grant.run_id,),
            )
        self.assertEqual(self.service.reconcile(actor=OPERATOR, now=NOW).repaired, 1)
        with self.assertRaises(FenceError):
            self.service.heartbeat(repair_grant, actor=WORKER, now=NOW)
        self.service.set_kill(
            scope_key="global", enabled=True, reason="metrics-stop",
            idempotency_key="d" * 64, actor=OPERATOR, now=NOW,
        )

        token = "metrics-" + "local-" + "operator-credential"
        authenticator = Authenticator({token: OPERATOR})
        client = TestClient(create_app(self.service, authenticator))
        self.assertEqual(client.get("/metrics").status_code, 401)
        response = client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)
        metrics = response.json()
        self.assertEqual(
            set(metrics),
            {
                "factory_intake_and_rejection_outcomes_total",
                "factory_lease_reclaim_and_fence_rejection_total",
                "factory_capacity_budget_kill_and_reconcile_outcomes_total",
                "factory_execution_claim_and_stage_outcomes_total",
                "factory_execution_protocol_and_proposal_outcomes_total",
                "factory_execution_orphan_and_cleanup_outcomes_total",
            },
        )
        intake = metrics["factory_intake_and_rejection_outcomes_total"]
        leases = metrics["factory_lease_reclaim_and_fence_rejection_total"]
        operations = metrics["factory_capacity_budget_kill_and_reconcile_outcomes_total"]
        self.assertEqual(
            set(metrics["factory_execution_claim_and_stage_outcomes_total"]),
            {"claimed", "stage_transitions"},
        )
        self.assertEqual(
            set(metrics["factory_execution_protocol_and_proposal_outcomes_total"]),
            {"note", "artifact", "usage", "terminal"},
        )
        self.assertEqual(
            set(metrics["factory_execution_orphan_and_cleanup_outcomes_total"]),
            {"orphaned", "workspace_released", "cleanup_failed"},
        )
        self.assertEqual(set(intake), {"accepted", "superseded", "queued", "retry", "dead", "transition_events"})
        self.assertEqual(set(leases), {"live_leases", "reclaimed", "fence_rejected"})
        self.assertEqual(
            set(operations),
            {
                "active_capacity", "cost_reserved_micros", "cost_observed_micros",
                "tokens_reserved", "tokens_observed", "wall_reserved_seconds",
                "output_observed_bytes", "accounting_blocked", "active_kills",
                "reconciliation_runs", "reconciliation_candidates", "repaired", "auth_rejected",
            },
        )
        self.assertEqual(
            (intake["accepted"], intake["queued"], intake["retry"], intake["dead"]),
            (5, 1, 1, 1),
        )
        self.assertGreaterEqual(intake["transition_events"], 15)
        self.assertEqual((leases["live_leases"], leases["reclaimed"], leases["fence_rejected"]), (2, 1, 1))
        self.assertEqual(
            (
                operations["active_capacity"], operations["cost_reserved_micros"],
                operations["cost_observed_micros"], operations["tokens_reserved"],
                operations["tokens_observed"], operations["wall_reserved_seconds"],
                operations["output_observed_bytes"], operations["active_kills"],
                operations["reconciliation_runs"], operations["reconciliation_candidates"],
                operations["repaired"], operations["auth_rejected"],
            ),
            (2, 7, 5, 11, 6, 13, 7, 1, 1, 1, 1, 1),
        )
        self.assertNotIn(token, response.text)
        self.assertNotIn("metrics-queued", response.text)
        self.assertLessEqual(len(response.content), 2048)

    def test_metric_counter_runtime_is_capability_only_monotonic_and_saturating(self):
        import psycopg

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                has_table_privilege('factory_runtime','factory.metric_counters','SELECT'),
                has_table_privilege('factory_runtime','factory.metric_counters','INSERT'),
                has_table_privilege('factory_runtime','factory.metric_counters','UPDATE'),
                has_table_privilege('factory_runtime','factory.metric_counters','DELETE'),
                has_table_privilege('factory_runtime','factory.metric_counters_pre_012_untrusted','SELECT'),
                has_function_privilege('factory_runtime','factory.increment_fence_rejected()','EXECUTE'),
                has_function_privilege('factory_runtime','factory.read_metrics_snapshot()','EXECUTE'),
                has_function_privilege('public','factory.increment_fence_rejected()','EXECUTE'),
                has_function_privilege('factory_runtime','factory.metrics_task_delta()','EXECUTE')"""
            )
            self.assertEqual(cursor.fetchone(), (False, False, False, False, False, True, True, False, False))

        forbidden = (
            "INSERT INTO factory.metric_counters(singleton,fence_rejected) VALUES (false,99)",
            "UPDATE factory.metric_counters SET fence_rejected=0",
            "DELETE FROM factory.metric_counters",
            "SELECT * FROM factory.metric_counters",
            "INSERT INTO factory.metric_counters_pre_012_untrusted(metric_name,outcome,value) VALUES ('forged','unknown',99)",
            "SELECT * FROM factory.metric_counters_pre_012_untrusted",
        )
        for statement in forbidden:
            with self.subTest(statement=statement), psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL ROLE factory_runtime")
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        cursor.execute(statement)

        def increment(_index):
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute("SET LOCAL ROLE factory_runtime")
                cursor.execute("SELECT factory.increment_fence_rejected()")
                return cursor.fetchone()[0]

        with ThreadPoolExecutor(max_workers=8) as pool:
            values = tuple(pool.map(increment, range(8)))
        self.assertEqual((len(set(values)), min(values), max(values)), (8, 1, 8))
        self.assertEqual(
            self.store.metrics()["factory_lease_reclaim_and_fence_rejection_total"]["fence_rejected"], 8
        )

        maximum = 9_223_372_036_854_775_807
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE factory.metric_counters SET fence_rejected=%s", (maximum - 1,))
        self.assertEqual((increment(0), increment(1)), (maximum, maximum))

    def test_metrics_snapshot_is_atomic_constant_row_and_timed(self):
        import psycopg
        from fastapi.testclient import TestClient
        from unittest import mock

        task = self.submit(source="metrics-snapshot-race").task
        grant = self.service.claim(
            owner="metrics-snapshot-race", role=RunRole.READER,
            repositories=(task.repository_id,), lease_seconds=60, actor=WORKER, now=NOW,
        )
        observed = threading.Event()
        proceed = threading.Event()
        statements = []
        real_connection = self.store._connect()

        class ProbeCursor:
            def __init__(self, inner):
                self.inner = inner

            def __enter__(self):
                self.inner.__enter__()
                return self

            def __exit__(self, *args):
                return self.inner.__exit__(*args)

            def __getattr__(self, name):
                return getattr(self.inner, name)

            def execute(self, statement, parameters=None):
                text = str(statement).lower()
                statements.append(text)
                result = self.inner.execute(statement, parameters)
                if (
                    "from factory.runs" in text and "filter (where state='leased'" in text
                ) or "read_metrics_snapshot" in text:
                    if not observed.is_set():
                        observed.set()
                        if not proceed.wait(2):
                            raise RuntimeError("metrics snapshot test barrier timed out")
                return result

        class ProbeConnection:
            def __enter__(self):
                real_connection.__enter__()
                return self

            def __exit__(self, *args):
                return real_connection.__exit__(*args)

            def cursor(self):
                return ProbeCursor(real_connection.cursor())

        with mock.patch.object(self.store, "_connect", return_value=ProbeConnection()):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self.store.metrics)
                self.assertTrue(observed.wait(2), statements)
                other = FactoryService(PostgresFactoryStore(self.runtime_url))
                other.release(grant, outcome=FailureClass.WORKER_LOST, actor=WORKER, now=NOW)
                proceed.set()
                metrics = future.result(timeout=2)
        leases = metrics["factory_lease_reclaim_and_fence_rejection_total"]["live_leases"]
        capacity = metrics["factory_capacity_budget_kill_and_reconcile_outcomes_total"]["active_capacity"]
        self.assertIn((leases, capacity), {(1, 1), (0, 0)})
        self.assertIn("set local statement_timeout='5s'", statements)
        self.assertIn("set local lock_timeout='500ms'", statements)
        data_statements = [item for item in statements if item.startswith("select")]
        self.assertEqual(len(data_statements), 1)
        self.assertIn("read_metrics_snapshot", data_statements[0])

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("EXPLAIN (ANALYZE,FORMAT JSON) SELECT * FROM factory.metric_counters WHERE singleton")
            plan = cursor.fetchone()[0][0]["Plan"]
            self.assertEqual((plan["Relation Name"], plan["Actual Rows"]), ("metric_counters", 1))

        blocker = psycopg.connect(DATABASE_URL)
        blocker.execute("LOCK TABLE factory.metric_counters IN ACCESS EXCLUSIVE MODE")
        token = "metrics-" + "timeout-" + "credential"
        client = TestClient(
            create_app(self.service, Authenticator({token: OPERATOR})), raise_server_exceptions=False
        )
        started = time.monotonic()
        unavailable = client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
        elapsed = time.monotonic() - started
        blocker.rollback()
        blocker.close()
        self.assertEqual(unavailable.status_code, 503)
        self.assertLess(elapsed, 2)

    def test_locked_metric_counter_never_delays_or_masks_stale_fence_409(self):
        import psycopg
        from fastapi.testclient import TestClient

        task = self.submit(source="metrics-locked-fence").task
        grant = self.service.claim(
            owner="worker", role=RunRole.READER, repositories=(task.repository_id,),
            lease_seconds=60, actor=WORKER, now=NOW,
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.capacity_allocations SET released_at=clock_timestamp() WHERE run_id=%s",
                (grant.run_id,),
            )
            cursor.execute("SELECT to_regclass('factory.metric_counters_pre_012_untrusted')")
            migrated = cursor.fetchone()[0] is not None
            if not migrated:
                cursor.execute(
                    """INSERT INTO factory.metric_counters(metric_name,outcome,value)
                    VALUES ('factory_lease_reclaim_and_fence_rejection_total','fence_rejected',0)
                    ON CONFLICT(metric_name,outcome) DO UPDATE SET value=0"""
                )
        locker = psycopg.connect(DATABASE_URL)
        if migrated:
            locker.execute("SELECT fence_rejected FROM factory.metric_counters WHERE singleton FOR UPDATE")
        else:
            locker.execute(
                """SELECT value FROM factory.metric_counters
                WHERE metric_name='factory_lease_reclaim_and_fence_rejection_total'
                  AND outcome='fence_rejected' FOR UPDATE"""
            )
        token = "metrics-" + "locked-fence-" + "credential"
        client = TestClient(create_app(self.service, Authenticator({token: WORKER})))
        body = {
            "task_id": grant.task_id, "run_id": grant.run_id, "owner": grant.owner,
            "role": grant.role.value, "fence": grant.fence,
            "expires_at": grant.expires_at.isoformat().replace("+00:00", "Z"),
            "packet_digest": grant.packet_digest,
        }

        def request(command):
            return client.post(
                "/v1/heartbeats",
                headers={
                    "Authorization": f"Bearer {token}", "Idempotency-Key": command,
                    "X-Correlation-ID": command,
                },
                json=body,
            )

        timed_out = False
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(request, "locked-fence-command")
            try:
                response = future.result(timeout=1)
            except FutureTimeout:
                timed_out = True
                locker.rollback()
                response = future.result(timeout=2)
            finally:
                if not timed_out:
                    locker.rollback()
        locker.close()
        self.assertFalse(timed_out, "metric row lock delayed the authoritative stale-fence response")
        self.assertEqual((response.status_code, response.json()), (409, {"error": "conflict", "code": "stale_fence"}))
        self.assertEqual(
            self.store.metrics()["factory_lease_reclaim_and_fence_rejection_total"]["fence_rejected"], 0
        )
        after_unlock = request("unlocked-fence-command")
        self.assertEqual((after_unlock.status_code, after_unlock.json()), (409, {"error": "conflict", "code": "stale_fence"}))
        self.assertEqual(
            self.store.metrics()["factory_lease_reclaim_and_fence_rejection_total"]["fence_rejected"], 1
        )

    def test_event_repair_and_database_deadline_limits_fail_closed(self):
        import psycopg

        event_payload = self.payload(source="event-limit")
        event_payload["limits"]["max_events"] = 2
        event_task = self.service.intake(event_payload, actor=OPERATOR, now=NOW).task
        event_grant = self.service.claim(
            owner="event-worker", role=RunRole.READER, repositories=(event_task.repository_id,),
            lease_seconds=60, actor=WORKER, now=NOW,
        )
        release_key = "1" * 64
        released = self.service.release(
            event_grant, outcome=FailureClass.WORKER_LOST, actor=WORKER, now=NOW,
            idempotency_key=release_key, correlation_id="event-budget-release",
        )
        replay = self.service.release(
            event_grant, outcome=FailureClass.WORKER_LOST, actor=WORKER, now=NOW,
            idempotency_key=release_key, correlation_id="event-budget-release",
        )
        self.assertEqual((released, replay), (TaskStatus.NEEDS_HUMAN, TaskStatus.NEEDS_HUMAN))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT state,current_run_id,(SELECT count(*) FROM factory.task_events WHERE task_id=t.task_id) FROM factory.tasks t WHERE task_id=%s",
                (event_task.task_id,),
            )
            self.assertEqual(cursor.fetchone(), ("needs_human", None, 3))
        self.assert_mandatory_cleanup(event_task.task_id, event_grant.run_id, "released")

        repair_payload = self.payload(source="repair-limit")
        repair_payload["limits"]["semantic_repairs"] = 1
        repair_task = self.service.intake(repair_payload, actor=OPERATOR, now=NOW).task
        for expected in (TaskStatus.RETRY, TaskStatus.NEEDS_HUMAN):
            grant = self.service.claim(
                owner="repair-worker", role=RunRole.READER, repositories=(repair_task.repository_id,),
                lease_seconds=60, actor=WORKER, now=NOW,
            )
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",
                    (grant.run_id,),
                )
            self.assertEqual(self.service.reconcile(actor=OPERATOR, now=NOW).repaired, 1)
            self.assertEqual(self.store.get_task(repair_task.task_id).status, expected)
        self.assertEqual(self.service.reconcile(actor=OPERATOR, now=NOW).repaired, 0)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT repair_count,repair_limit FROM factory.tasks WHERE task_id=%s", (repair_task.task_id,))
            self.assertEqual(cursor.fetchone(), (1, 1))

        expired_task = self.submit(source="deadline-before-claim").task
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE factory.tasks SET deadline_at=clock_timestamp()-interval '1 second' WHERE task_id=%s", (expired_task.task_id,))
        self.assertIsNone(self.service.claim(
            owner="late-worker", role=RunRole.READER, repositories=(expired_task.repository_id,),
            lease_seconds=60, actor=WORKER, now=NOW,
        ))
        live_task = self.submit(source="deadline-before-mutation").task
        live_grant = self.service.claim(
            owner="late-worker", role=RunRole.READER, repositories=(live_task.repository_id,),
            lease_seconds=60, actor=WORKER, now=NOW,
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE factory.tasks SET deadline_at=clock_timestamp()-interval '1 second' WHERE task_id=%s", (live_task.task_id,))
        with self.assertRaises(FenceError):
            self.service.heartbeat(live_grant, actor=WORKER, now=NOW)

    def test_exhausted_event_budget_allows_reconcile_and_cancel_cleanup_once(self):
        import psycopg

        reconcile_payload = self.payload(source="event-limit-reconcile")
        reconcile_payload["limits"]["max_events"] = 2
        reconcile_task = self.service.intake(reconcile_payload, actor=OPERATOR, now=NOW).task
        reconcile_grant = self.service.claim(
            owner="event-reconcile-worker", role=RunRole.READER,
            repositories=(reconcile_task.repository_id,), lease_seconds=60, actor=WORKER, now=NOW,
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",
                (reconcile_grant.run_id,),
            )
        first = self.service.reconcile(actor=OPERATOR, now=NOW)
        second = self.service.reconcile(actor=OPERATOR, now=NOW)
        self.assertEqual((first.repaired, second.repaired), (1, 0))
        self.assert_mandatory_cleanup(reconcile_task.task_id, reconcile_grant.run_id, "released")

        cancel_payload = self.payload(source="event-limit-cancel")
        cancel_payload["limits"]["max_events"] = 2
        cancel_task = self.service.intake(cancel_payload, actor=OPERATOR, now=NOW).task
        cancel_grant = self.service.claim(
            owner="event-cancel-worker", role=RunRole.READER,
            repositories=(cancel_task.repository_id,), lease_seconds=60, actor=WORKER, now=NOW,
        )
        cancel_key = "2" * 64
        first_cancel = self.service.cancel(
            cancel_task.task_id, reason="event-budget-cleanup", idempotency_key=cancel_key,
            actor=OPERATOR, now=NOW,
        )
        second_cancel = self.service.cancel(
            cancel_task.task_id, reason="event-budget-cleanup", idempotency_key=cancel_key,
            actor=OPERATOR, now=NOW,
        )
        self.assertEqual((first_cancel.status, second_cancel.status), (TaskStatus.CANCELLED, TaskStatus.CANCELLED))
        self.assert_mandatory_cleanup(cancel_task.task_id, cancel_grant.run_id, "cancelled")

    def test_prior_attempt_reservation_forces_accounting_recovery_not_retry(self):
        import psycopg

        task = self.submit(source="cross-attempt-reservation").task
        grant = self.service.claim(
            owner="reservation-worker", role=RunRole.READER, repositories=(task.repository_id,),
            lease_seconds=60, actor=WORKER, now=NOW,
        )
        self.service.reserve_budget(
            grant, cost_usd_micros=25_000_000, token_units=2_000_000, wall_seconds=14_400,
            reason_digest="a" * 64, idempotency_key="b" * 64, actor=WORKER,
        )
        status = self.service.release(grant, outcome=FailureClass.WORKER_LOST, actor=WORKER, now=NOW)
        self.assertEqual(status, TaskStatus.NEEDS_HUMAN)
        self.assertIsNone(self.service.claim(
            owner="retry-worker", role=RunRole.READER, repositories=(task.repository_id,),
            lease_seconds=60, actor=WORKER, now=NOW,
        ))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT state,accounting_blocked,cost_reserved_micros,tokens_reserved,wall_reserved_seconds,
                (SELECT count(*) FROM factory.budget_reservations WHERE task_id=t.task_id AND released_at IS NULL)
                FROM factory.tasks t WHERE task_id=%s""",
                (task.task_id,),
            )
            self.assertEqual(cursor.fetchone(), ("needs_human", True, 25_000_000, 2_000_000, 14_400, 1))

    def test_schema_008_upgrade_quarantines_legacy_reservation_before_claim(self):
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        database_name = f"factory_upgrade_{uuid.uuid4().hex[:12]}"
        connection_parameters = conninfo_to_dict(DATABASE_URL)
        upgrade_url = make_conninfo(**{**connection_parameters, "dbname": database_name})
        with psycopg.connect(DATABASE_URL, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
        try:
            migrations = discover_migrations()
            task_id, intent_id, run_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
            blocked_task_id, blocked_intent_id = uuid.uuid4(), uuid.uuid4()
            ready_task_id, ready_intent_id = uuid.uuid4(), uuid.uuid4()
            ready_new_task_id, ready_new_intent_id = uuid.uuid4(), uuid.uuid4()
            ready_failed_run_id, ready_completed_run_id = uuid.uuid4(), uuid.uuid4()
            with psycopg.connect(upgrade_url) as connection, connection.cursor() as cursor:
                cursor.execute("CREATE SCHEMA factory")
                cursor.execute(
                    """CREATE TABLE factory.schema_migrations (
                    version integer PRIMARY KEY, name text UNIQUE NOT NULL,
                    sha256 char(64) NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())"""
                )
                for migration in migrations[:8]:
                    cursor.execute(migration.sql)
                    cursor.execute(
                        "INSERT INTO factory.schema_migrations(version,name,sha256) VALUES (%s,%s,%s)",
                        (migration.version, migration.name, migration.sha256),
                    )
                cursor.execute(
                    "INSERT INTO factory.intake_identities(repository_id,source_type,source_id) VALUES ('owner/repository','manual','legacy-reservation')"
                )
                cursor.execute(
                    """INSERT INTO factory.accepted_intents
                    (intent_id,intent_digest,idempotency_key,repository_id,source_type,source_id,source_digest,
                     exact_base_sha,spec_digest,architecture_digest,governance_digest,policy_digest,body)
                    VALUES (%s,%s,%s,'owner/repository','manual','legacy-reservation',%s,%s,%s,%s,%s,%s,'{}')""",
                    (intent_id, "1" * 64, "2" * 64, "3" * 64, "4" * 40, "5" * 64, "6" * 64, "7" * 64, "8" * 64),
                )
                cursor.execute(
                    """INSERT INTO factory.tasks
                    (task_id,intent_id,repository_id,source_type,source_id,state,generation,packet_digest,
                     deadline_at,cost_limit_micros,token_limit,output_limit_bytes,event_limit,
                     cost_reserved_micros,tokens_reserved,accounting_blocked,repair_limit,repair_count,
                     wall_limit_seconds,wall_reserved_seconds)
                    VALUES (%s,%s,'owner/repository','manual','legacy-reservation','retry',1,%s,
                     now()+interval '1 hour',25000000,2000000,10000000,100,25000000,2000000,false,3,0,14400,14400)""",
                    (task_id, intent_id, "1" * 64),
                )
                cursor.execute(
                    """INSERT INTO factory.runs
                    (run_id,task_id,owner_id,role,packet_digest,fence,state,lease_expires_at,deadline_at,released_at)
                    VALUES (%s,%s,'legacy-worker','reader',%s,1,'failed',now()-interval '1 minute',now()+interval '1 hour',now())""",
                    (run_id, task_id, "1" * 64),
                )
                cursor.execute(
                    """INSERT INTO factory.attempts
                    (attempt_id,task_id,run_id,attempt_no,failure_class,failure_code,failure_digest,finished_at)
                    VALUES (%s,%s,%s,1,'worker_lost','worker_lost',%s,now())""",
                    (uuid.uuid4(), task_id, run_id, "9" * 64),
                )
                cursor.execute(
                    """INSERT INTO factory.budget_reservations
                    (reservation_id,task_id,run_id,idempotency_key,cost_usd_micros,token_units,wall_seconds,reason_digest)
                    VALUES (%s,%s,%s,%s,25000000,2000000,14400,%s)""",
                    (uuid.uuid4(), task_id, run_id, "a" * 64, "b" * 64),
                )
                cursor.execute(
                    """INSERT INTO factory.intake_identities(repository_id,source_type,source_id)
                    VALUES ('owner/repository','manual','legacy-blocked-zero'),
                           ('owner/repository','manual','legacy-ready-reservation')"""
                )
                for legacy_intent_id, source in (
                    (blocked_intent_id, "legacy-blocked-zero"),
                    (ready_intent_id, "legacy-ready-reservation"),
                    (ready_new_intent_id, "legacy-ready-reservation"),
                ):
                    cursor.execute(
                        """INSERT INTO factory.accepted_intents
                        (intent_id,intent_digest,idempotency_key,repository_id,source_type,source_id,source_digest,
                         exact_base_sha,spec_digest,architecture_digest,governance_digest,policy_digest,body)
                        VALUES (%s,%s,%s,'owner/repository','manual',%s,%s,%s,%s,%s,%s,%s,'{}')""",
                        (
                            legacy_intent_id, uuid.uuid4().hex * 2, uuid.uuid4().hex * 2, source,
                            uuid.uuid4().hex * 2, uuid.uuid4().hex + uuid.uuid4().hex[:8],
                            uuid.uuid4().hex * 2, uuid.uuid4().hex * 2,
                            uuid.uuid4().hex * 2, uuid.uuid4().hex * 2,
                        ),
                    )
                cursor.execute(
                    """INSERT INTO factory.tasks
                    (task_id,intent_id,repository_id,source_type,source_id,state,generation,packet_digest,
                     deadline_at,cost_limit_micros,token_limit,output_limit_bytes,event_limit,
                     accounting_blocked,repair_limit,repair_count,wall_limit_seconds)
                    VALUES (%s,%s,'owner/repository','manual','legacy-blocked-zero','retry',1,%s,
                     now()+interval '1 hour',25000000,2000000,10000000,100,true,3,0,14400)""",
                    (blocked_task_id, blocked_intent_id, uuid.uuid4().hex * 2),
                )
                cursor.execute(
                    """INSERT INTO factory.tasks
                    (task_id,intent_id,repository_id,source_type,source_id,state,generation,packet_digest,
                     deadline_at,cost_limit_micros,token_limit,output_limit_bytes,event_limit,
                     cost_reserved_micros,tokens_reserved,accounting_blocked,repair_limit,repair_count,
                     wall_limit_seconds,wall_reserved_seconds,terminal_at)
                    VALUES (%s,%s,'owner/repository','manual','legacy-ready-reservation','ready_for_human',1,%s,
                     now()+interval '1 hour',25000000,2000000,10000000,100,500,600,false,3,0,14400,700,now())""",
                    (ready_task_id, ready_intent_id, uuid.uuid4().hex * 2),
                )
                cursor.execute(
                    """INSERT INTO factory.tasks
                    (task_id,intent_id,repository_id,source_type,source_id,state,generation,packet_digest,
                     deadline_at,cost_limit_micros,token_limit,output_limit_bytes,event_limit,
                     accounting_blocked,repair_limit,repair_count,wall_limit_seconds)
                    VALUES (%s,%s,'owner/repository','manual','legacy-ready-reservation','queued',2,%s,
                     now()+interval '1 hour',25000000,2000000,10000000,100,false,3,0,14400)""",
                    (ready_new_task_id, ready_new_intent_id, uuid.uuid4().hex * 2),
                )
                for legacy_run_id, fence, state in (
                    (ready_failed_run_id, 1, "failed"),
                    (ready_completed_run_id, 2, "completed"),
                ):
                    cursor.execute(
                        """INSERT INTO factory.runs
                        (run_id,task_id,owner_id,role,packet_digest,fence,state,lease_expires_at,deadline_at,released_at)
                        SELECT %s,task_id,'legacy-worker','reader',packet_digest,%s,%s,
                          now()-interval '1 minute',deadline_at,now() FROM factory.tasks WHERE task_id=%s""",
                        (legacy_run_id, fence, state, ready_task_id),
                    )
                cursor.execute(
                    """INSERT INTO factory.attempts
                    (attempt_id,task_id,run_id,attempt_no,failure_class,failure_code,failure_digest,finished_at)
                    VALUES (%s,%s,%s,1,'worker_lost','worker_lost',%s,now()),
                           (%s,%s,%s,2,NULL,NULL,NULL,now())""",
                    (
                        uuid.uuid4(), ready_task_id, ready_failed_run_id, uuid.uuid4().hex * 2,
                        uuid.uuid4(), ready_task_id, ready_completed_run_id,
                    ),
                )
                cursor.execute(
                    """INSERT INTO factory.budget_reservations
                    (reservation_id,task_id,run_id,idempotency_key,cost_usd_micros,token_units,wall_seconds,reason_digest)
                    VALUES (%s,%s,%s,%s,500,600,700,%s)""",
                    (
                        uuid.uuid4(), ready_task_id, ready_failed_run_id,
                        uuid.uuid4().hex * 2, uuid.uuid4().hex * 2,
                    ),
                )
                cursor.execute(
                    """INSERT INTO factory.usage_observations
                    (observation_id,task_id,run_id,provider_call_id,price_table_digest,cost_usd_micros,
                     token_units,output_bytes)
                    VALUES (%s,%s,%s,'legacy-completed-call',%s,1,1,1)""",
                    (uuid.uuid4(), ready_task_id, ready_completed_run_id, uuid.uuid4().hex * 2),
                )
                cursor.execute(
                    """INSERT INTO factory.metric_counters(metric_name,outcome,value) VALUES
                    ('factory_lease_reclaim_and_fence_rejection_total','fence_rejected',999),
                    ('forged-untrusted-key','unknown',777)"""
                )

            applied = PostgresMigrator(upgrade_url).apply()
            from psycopg.conninfo import conninfo_to_dict, make_conninfo
            upgraded_runtime_url = make_conninfo(**{
                **conninfo_to_dict(upgrade_url), "user": self.runtime_login,
                "password": self.runtime_password,
            })
            upgraded_store = PostgresFactoryStore(upgraded_runtime_url)
            upgraded_service = FactoryService(upgraded_store)
            readiness = upgraded_store.readiness()
            self.assertEqual(
                (
                    [migration.version for migration in applied],
                    readiness["status"], readiness["schema_version"], readiness["accounting_consistent"],
                    upgraded_store.get_task(str(task_id)).status,
                    upgraded_store.get_task(str(blocked_task_id)).status,
                    upgraded_store.get_task(str(ready_task_id)).status,
                    upgraded_store.get_task(str(ready_new_task_id)).status,
                ),
                (
                    [9, 10, 11, 12, 13, 14], "ready", 14, True,
                    TaskStatus.NEEDS_HUMAN, TaskStatus.NEEDS_HUMAN, TaskStatus.SUPERSEDED,
                    TaskStatus.QUEUED,
                ),
            )
            metrics = upgraded_store.metrics()
            self.assertEqual(
                (
                    metrics["factory_intake_and_rejection_outcomes_total"]["accepted"],
                    metrics["factory_intake_and_rejection_outcomes_total"]["superseded"],
                    metrics["factory_intake_and_rejection_outcomes_total"]["queued"],
                    metrics["factory_lease_reclaim_and_fence_rejection_total"]["fence_rejected"],
                    metrics["factory_capacity_budget_kill_and_reconcile_outcomes_total"]["cost_reserved_micros"],
                    metrics["factory_capacity_budget_kill_and_reconcile_outcomes_total"]["output_observed_bytes"],
                    metrics["factory_capacity_budget_kill_and_reconcile_outcomes_total"]["accounting_blocked"],
                ),
                (4, 1, 1, 0, 25_000_500, 1, 3),
            )
            with psycopg.connect(upgrade_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    "SELECT metric_name,outcome,value FROM factory.metric_counters_pre_012_untrusted ORDER BY metric_name"
                )
                self.assertEqual(
                    cursor.fetchall(),
                    [
                        ("factory_lease_reclaim_and_fence_rejection_total", "fence_rejected", 999),
                        ("forged-untrusted-key", "unknown", 777),
                    ],
                )
            current_grant = upgraded_service.claim(
                owner="legacy-retry-worker", role=RunRole.READER, repositories=("owner/repository",),
                lease_seconds=60, actor=WORKER, now=NOW,
            )
            self.assertIsNotNone(current_grant)
            self.assertEqual(current_grant.task_id, str(ready_new_task_id))
            self.assertEqual(upgraded_store.get_task(current_grant.task_id).generation, 2)
            with psycopg.connect(upgrade_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT accounting_blocked,cost_reserved_micros,tokens_reserved,wall_reserved_seconds,
                    (SELECT count(*) FROM factory.budget_reservations WHERE task_id=t.task_id AND released_at IS NULL)
                    FROM factory.tasks t WHERE task_id=%s""",
                    (task_id,),
                )
                self.assertEqual(cursor.fetchone(), (True, 25_000_000, 2_000_000, 14_400, 1))
                cursor.execute(
                    """SELECT task_id,accounting_blocked,cost_reserved_micros,tokens_reserved,
                    wall_reserved_seconds,
                    (SELECT count(*) FROM factory.budget_reservations b
                     WHERE b.task_id=t.task_id AND b.released_at IS NULL)
                    FROM factory.tasks t WHERE task_id=ANY(%s) ORDER BY task_id""",
                    ([blocked_task_id, ready_task_id],),
                )
                expected = {
                    blocked_task_id: (True, 0, 0, 0, 0),
                    ready_task_id: (True, 500, 600, 700, 1),
                }
                self.assertEqual(
                    {row[0]: tuple(row[1:]) for row in cursor.fetchall()}, expected
                )
                cursor.execute(
                    "UPDATE factory.tasks SET state='retry',accounting_blocked=false WHERE task_id=%s",
                    (task_id,),
                )
            self.assertEqual(
                (upgraded_store.readiness()["status"], upgraded_store.readiness()["accounting_consistent"]),
                ("not_ready", False),
            )
            self.assertIsNone(
                upgraded_service.claim(
                    owner="legacy-guard-worker", role=RunRole.READER, repositories=("owner/repository",),
                    lease_seconds=60, actor=WORKER, now=NOW,
                )
            )
            with psycopg.connect(upgrade_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE factory.tasks SET state='needs_human',accounting_blocked=true WHERE task_id=%s",
                    (task_id,),
                )
                cursor.execute(
                    "UPDATE factory.tasks SET state='ready_for_human',accounting_blocked=false WHERE task_id=%s",
                    (ready_task_id,),
                )
            self.assertEqual(
                (upgraded_store.readiness()["status"], upgraded_store.readiness()["accounting_consistent"]),
                ("not_ready", False),
            )
            with psycopg.connect(upgrade_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE factory.tasks SET state='superseded',accounting_blocked=true WHERE task_id=%s",
                    (ready_task_id,),
                )
            self.assertEqual(upgraded_store.readiness()["status"], "ready")
            with psycopg.connect(upgrade_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE factory.tasks SET accounting_blocked=false WHERE task_id=%s",
                    (ready_task_id,),
                )
            self.assertEqual(
                (upgraded_store.readiness()["status"], upgraded_store.readiness()["accounting_consistent"]),
                ("not_ready", False),
            )
            with psycopg.connect(upgrade_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE factory.tasks SET accounting_blocked=true WHERE task_id=%s",
                    (ready_task_id,),
                )
            self.assertEqual(upgraded_store.readiness()["status"], "ready")
            self.assertEqual(PostgresMigrator(upgrade_url).apply(), ())
        finally:
            with psycopg.connect(DATABASE_URL, autocommit=True) as admin:
                admin.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s AND pid<>pg_backend_pid()",
                    (database_name,),
                )
                admin.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name)))

    def test_repository_kill_is_isolated_and_reconcile_page_timeout_are_bounded(self):
        import psycopg

        repo_a = self.submit(repository="repo/a", source="killed-a").task
        repo_b = self.submit(repository="repo/b", source="live-b").task
        self.service.set_kill(
            scope_key="repository:repo/a", enabled=True, reason="repo-stop", idempotency_key="9" * 64,
            actor=OPERATOR, now=NOW,
        )
        self.assertIsNone(self.service.claim(
            owner="repo-worker", role=RunRole.READER, repositories=(repo_a.repository_id,),
            lease_seconds=60, actor=WORKER, now=NOW,
        ))
        repo_b_grant = self.service.claim(
            owner="repo-worker", role=RunRole.READER, repositories=(repo_b.repository_id,),
            lease_seconds=60, actor=WORKER, now=NOW,
        )
        self.assertEqual(repo_b_grant.task_id, repo_b.task_id)
        self.service.cancel(
            repo_b.task_id, reason="isolation-proved", idempotency_key="8" * 64, actor=OPERATOR, now=NOW
        )

        seeded = [self.submit(source=f"bounded-reconcile-{index}").task for index in range(101)]
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            # A valid capacity snapshot has at most 21 candidates. Remove only the
            # disposable check to exercise the defensive page bound above that invariant.
            cursor.execute("ALTER TABLE factory.capacity_counters DROP CONSTRAINT capacity_counters_check")
            cursor.execute(
                """INSERT INTO factory.runs(run_id,task_id,owner_id,role,packet_digest,fence,state,lease_expires_at,deadline_at)
                SELECT gen_random_uuid(),task_id,'expired-worker','reader',packet_digest,1,'leased',
                  clock_timestamp()-interval '1 second',deadline_at FROM factory.tasks WHERE task_id=ANY(%s)
                RETURNING run_id,task_id""",
                ([task.task_id for task in seeded],),
            )
            runs = cursor.fetchall()
            cursor.executemany(
                "INSERT INTO factory.attempts(attempt_id,task_id,run_id,attempt_no) VALUES (gen_random_uuid(),%s,%s,1)",
                [(task_id, run_id) for run_id, task_id in runs],
            )
            cursor.executemany(
                "INSERT INTO factory.capacity_allocations(allocation_id,run_id,task_id,repository_id,role) VALUES (gen_random_uuid(),%s,%s,'owner/repository','reader')",
                [(run_id, task_id) for run_id, task_id in runs],
            )
            cursor.executemany(
                "UPDATE factory.tasks SET state='leased',current_run_id=%s,current_fence=1 WHERE task_id=%s",
                runs,
            )
            cursor.execute("UPDATE factory.capacity_counters SET active_count=101 WHERE scope_key IN ('global:reader','repository:owner/repository:reader')")
            cursor.execute(
                """CREATE FUNCTION factory.assert_reconcile_timeout() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN IF current_setting('statement_timeout') <> '5s' THEN RAISE EXCEPTION 'unbounded reconciliation'; END IF; RETURN NEW; END $$"""
            )
            cursor.execute(
                "CREATE TRIGGER assert_reconcile_timeout BEFORE INSERT ON factory.reconciliation_runs FOR EACH ROW EXECUTE FUNCTION factory.assert_reconcile_timeout()"
            )
        first = self.service.reconcile(
            actor=OPERATOR, now=NOW, limit=100, idempotency_key="7" * 64, correlation_id="bounded-page-1"
        )
        replay = self.service.reconcile(
            actor=OPERATOR, now=NOW, limit=100, idempotency_key="7" * 64, correlation_id="bounded-page-1"
        )
        second = self.service.reconcile(actor=OPERATOR, now=NOW, limit=100, cursor=first.cursor)
        self.assertEqual((first.candidates, first.repaired, replay, second.candidates, second.repaired), (100, 100, first, 1, 1))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("DROP TRIGGER assert_reconcile_timeout ON factory.reconciliation_runs")
            cursor.execute("DROP FUNCTION factory.assert_reconcile_timeout()")
            cursor.execute("SELECT count(*) FROM factory.runs WHERE released_at IS NULL AND lease_expires_at<=clock_timestamp()")
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute(
                "ALTER TABLE factory.capacity_counters ADD CONSTRAINT capacity_counters_check CHECK(active_count BETWEEN 0 AND ceiling)"
            )

    def test_reconcile_and_cancel_share_capacity_then_task_lock_order(self):
        import psycopg

        task = self.submit(source="lock-order").task
        grant = self.service.claim(
            owner="lock-worker", role=RunRole.READER, repositories=(task.repository_id,),
            lease_seconds=60, actor=WORKER, now=NOW,
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (grant.run_id,))
        blocker = psycopg.connect(DATABASE_URL)
        blocker.execute("SELECT factory.capacity_lock_run(%s)", (grant.run_id,))
        errors = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            cancel = pool.submit(
                self.service.cancel, task.task_id, reason="operator", idempotency_key="6" * 64,
                actor=OPERATOR, now=NOW,
            )
            time.sleep(0.1)
            reconcile = pool.submit(self.service.reconcile, actor=OPERATOR, now=NOW)
            time.sleep(0.1)
            blocker.commit()
            blocker.close()
            for future in (cancel, reconcile):
                try:
                    future.result(timeout=5)
                except Exception as exc:
                    errors.append(exc)
        self.assertEqual(errors, [])
        self.assertEqual(self.store.get_task(task.task_id).status, TaskStatus.CANCELLED)

    def test_representative_hot_queries_use_task_scoped_indexes(self):
        import psycopg

        task = self.submit(source="index-plans").task
        other_task = self.submit(source="index-plans-other-history").task
        grant = self.service.claim(
            owner="plan-worker", role=RunRole.READER, repositories=(task.repository_id,),
            lease_seconds=60, actor=WORKER, now=NOW,
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO factory.audit_log
                (task_id,run_id,previous_digest,current_digest,actor_id,action,resource,reason,correlation_id,metadata,digest_version)
                VALUES (%s,%s,%s,%s,'plan','plan','task','plan','plan','{}'::jsonb,2)""",
                [
                    (task.task_id, grant.run_id, f"{index:064x}", f"{index + 1:064x}")
                    for index in range(1, 501)
                ],
            )
            cursor.executemany(
                """INSERT INTO factory.audit_log
                (task_id,previous_digest,current_digest,actor_id,action,resource,reason,correlation_id,metadata,digest_version)
                VALUES (%s,%s,%s,'plan','plan','task','plan','plan','{}'::jsonb,2)""",
                [
                    (other_task.task_id, f"{10_000 + index:064x}", f"{20_000 + index:064x}")
                    for index in range(5_000)
                ],
            )
            cursor.executemany(
                """INSERT INTO factory.usage_observations
                (observation_id,task_id,run_id,provider_call_id,price_table_digest,cost_usd_micros,token_units,output_bytes)
                VALUES (gen_random_uuid(),%s,%s,%s,%s,0,0,0)""",
                [(task.task_id, grant.run_id, f"plan-{index}", "2" * 64) for index in range(500)],
            )
            cursor.executemany(
                """INSERT INTO factory.budget_reservations
                (reservation_id,task_id,run_id,idempotency_key,cost_usd_micros,token_units,wall_seconds,reason_digest)
                VALUES (gen_random_uuid(),%s,%s,%s,0,0,0,%s)""",
                [(task.task_id, grant.run_id, f"{1000 + index:064x}", "3" * 64) for index in range(500)],
            )
            cursor.execute("ANALYZE factory.tasks; ANALYZE factory.runs; ANALYZE factory.audit_log; ANALYZE factory.usage_observations; ANALYZE factory.budget_reservations")
            cursor.execute("SET LOCAL enable_seqscan=off")
            statements = {
                "claim": ("SELECT task_id FROM factory.tasks WHERE state IN ('queued','retry') ORDER BY created_at,task_id LIMIT 1", ()),
                "audit": ("SELECT * FROM factory.audit_log WHERE task_id=%s ORDER BY audit_id LIMIT 100001", (task.task_id,)),
                "usage": ("SELECT sum(output_bytes) FROM factory.usage_observations WHERE task_id=%s", (task.task_id,)),
                "reservation": ("SELECT sum(cost_usd_micros) FROM factory.budget_reservations WHERE task_id=%s AND run_id=%s AND released_at IS NULL", (task.task_id, grant.run_id)),
                "reconcile": ("SELECT task_id FROM factory.runs WHERE released_at IS NULL AND lease_expires_at<=clock_timestamp() ORDER BY task_id LIMIT 100", ()),
            }
            expected = {
                "claim": {"tasks_claim_queue"},
                "audit": {"audit_log_task_order"},
                "usage": {"usage_observations_task_run"},
                "reservation": {"budget_reservations_task_run_active"},
                "reconcile": {"runs_reconcile_keyset", "runs_expired_reconcile"},
            }
            for name, (statement, params) in statements.items():
                cursor.execute("EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) " + statement, params)
                plan = cursor.fetchone()[0][0]["Plan"]
                indexes = set()
                pending = [plan]
                while pending:
                    node = pending.pop()
                    if node.get("Index Name"):
                        indexes.add(node["Index Name"])
                    pending.extend(node.get("Plans", []))
                self.assertTrue(indexes & expected[name], (name, indexes, plan))

    def test_shipped_local_bootstrap_provisions_effective_runtime_login(self):
        import psycopg
        from adaptive_factory.admin import BootstrapError, bootstrap_local, provision_runtime_login

        login = "factory_service_test"
        attestor_login = "factory_artifact_service_test"
        unsafe_login = "factory_unsafe_dual_test"
        mismatch_login = "factory_mismatch_test"
        from psycopg import sql

        def cleanup_bootstrap_roles():
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                for role in (login, attestor_login, unsafe_login, mismatch_login):
                    cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))

        self.addCleanup(cleanup_bootstrap_roles)
        password = "-".join(("local", "runtime", "bootstrap", "test"))
        attestor_password = "-".join(("local", "artifact", "attestor", "test"))
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        runtime_url = make_conninfo(**{**conninfo_to_dict(DATABASE_URL), "user": login, "password": password})
        attestor_url = make_conninfo(**{
            **conninfo_to_dict(DATABASE_URL), "user": attestor_login,
            "password": attestor_password,
        })
        with self.assertRaisesRegex(BootstrapError, "runtime readiness validation failed"):
            bootstrap_local(
                DATABASE_URL, mismatch_login, "local-runtime-mismatch-test",
                self.runtime_url,
            )
        result = bootstrap_local(
            DATABASE_URL, login, password, runtime_url,
            attestor_login, attestor_password, attestor_url,
        )
        self.assertEqual(result["database_role"], "factory_runtime")
        self.assertEqual(result["artifact_attestor_database_role"], "factory_artifact_attestor")
        self.assertEqual(result["schema_version"], 14)
        with psycopg.connect(runtime_url) as connection, connection.cursor() as cursor:
            cursor.execute("SET ROLE factory_runtime")
            cursor.execute("SELECT session_user,current_user")
            self.assertEqual(cursor.fetchone(), (login, "factory_runtime"))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "CREATE ROLE factory_unsafe_dual_test LOGIN NOINHERIT PASSWORD 'local-unsafe-dual-test'"
            )
            cursor.execute("GRANT factory_artifact_attestor TO factory_unsafe_dual_test")
        with self.assertRaisesRegex(BootstrapError, "unsafe role membership"):
            provision_runtime_login(
                DATABASE_URL, unsafe_login, "local-unsafe-dual-test"
            )
    def test_store_and_migration_reject_owner_or_transitively_privileged_capability_roles(self):
        import psycopg
        from psycopg import sql

        with self.assertRaisesRegex(StoreError, "runtime login is not least privilege"):
            PostgresFactoryStore(DATABASE_URL).readiness()
        with self.assertRaisesRegex(StoreError, "artifact attestor login is not least privilege"):
            PostgresArtifactAttestationStore(DATABASE_URL).readiness()

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            database_name = cursor.fetchone()[0]
            cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(database_name), sql.Identifier(self.runtime_login),
            ))
        self.assertEqual(self.store.readiness()["status"], "ready")
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(sql.SQL(
                "GRANT CONNECT ON DATABASE {} TO {} WITH GRANT OPTION"
            ).format(sql.Identifier(database_name), sql.Identifier(self.runtime_login)))
        try:
            with self.assertRaisesRegex(StoreError, "direct database authority"):
                self.store.readiness()
        finally:
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(sql.SQL(
                    "REVOKE GRANT OPTION FOR CONNECT ON DATABASE {} FROM {}"
                ).format(sql.Identifier(database_name), sql.Identifier(self.runtime_login)))
        self.assertEqual(self.store.readiness()["status"], "ready")

        hostile_runtime = PostgresFactoryStore(psycopg.conninfo.make_conninfo(
            self.runtime_url, options="-csearch_path=public,pg_catalog",
        ))
        with hostile_runtime._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('search_path')")
            self.assertEqual(cursor.fetchone()[0], "pg_catalog, factory")
        hostile_attestor = PostgresArtifactAttestationStore(psycopg.conninfo.make_conninfo(
            self.artifact_attestor_url, options="-csearch_path=public,pg_catalog",
        ))
        with hostile_attestor._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_setting('search_path'),current_setting('lock_timeout'),"
                "current_setting('statement_timeout')"
            )
            self.assertEqual(cursor.fetchone(), ("pg_catalog, factory", "5s", "5s"))

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(sql.SQL("GRANT SELECT (task_id) ON factory.tasks TO {}").format(
                sql.Identifier(self.runtime_login),
            ))
        try:
            with self.assertRaisesRegex(StoreError, "direct database authority"):
                self.store.readiness()
        finally:
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(sql.SQL("REVOKE SELECT (task_id) ON factory.tasks FROM {}").format(
                    sql.Identifier(self.runtime_login),
                ))
                cursor.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM {}").format(
                    sql.Identifier(database_name), sql.Identifier(self.runtime_login),
                ))

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("GRANT pg_read_all_data TO factory_runtime")
        try:
            with self.assertRaisesRegex(StoreError, "runtime capability role is not isolated"):
                self.store.readiness()
        finally:
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute("REVOKE pg_read_all_data FROM factory_runtime")

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("GRANT pg_read_all_data TO factory_artifact_attestor")
        try:
            with self.assertRaisesRegex(StoreError, "artifact attestor capability role is not isolated"):
                PostgresArtifactAttestationStore(self.artifact_attestor_url).readiness()
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                with self.assertRaisesRegex(Exception, "unsafe capability role"):
                    execution_migration = next(
                        item for item in discover_migrations() if item.version == 13
                    )
                    cursor.execute(execution_migration.sql)
        finally:
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute("REVOKE pg_read_all_data FROM factory_artifact_attestor")

    def test_roles_are_isolated_and_audit_is_append_only_and_verifiable(self):
        task = self.submit(source="audit-role-check").task
        self.assertTrue(self.store.verify_audit_chain(task.task_id))
        self.assertEqual(self.store.readiness()["database_role"], "factory_runtime")
        import psycopg

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS trust_ci; REVOKE ALL ON SCHEMA trust_ci FROM PUBLIC")
            cursor.execute(
                "SELECT rolname,rolcanlogin,rolsuper,rolcreaterole FROM pg_roles WHERE rolname=ANY(%s) ORDER BY rolname",
                (["factory_artifact_attestor", "factory_audit_reader", "factory_migrator", "factory_runtime"],),
            )
            roles = cursor.fetchall()
            self.assertEqual(
                [row[0] for row in roles],
                ["factory_artifact_attestor", "factory_audit_reader", "factory_migrator", "factory_runtime"],
            )
            self.assertTrue(all(row[1:] == (False, False, False) for row in roles))
            cursor.execute(
                """SELECT
                has_function_privilege('factory_runtime','factory.execution_record_artifact_attestation(jsonb)','EXECUTE'),
                has_function_privilege('factory_artifact_attestor','factory.execution_record_artifact_attestation(jsonb)','EXECUTE'),
                has_table_privilege('factory_runtime','factory.execution_artifact_attestations','SELECT'),
                has_table_privilege('factory_artifact_attestor','factory.execution_artifact_attestations','SELECT'),
                has_table_privilege('factory_runtime','factory.execution_artifact_attestations','UPDATE'),
                has_table_privilege('factory_artifact_attestor','factory.execution_artifact_attestations','UPDATE'),
                has_function_privilege('factory_artifact_attestor',
                  'factory.execution_propose(uuid,uuid,text,bigint,character,character,bigint,character,text,jsonb)',
                  'EXECUTE'),
                pg_has_role('factory_runtime','factory_artifact_attestor','MEMBER'),
                pg_has_role('factory_artifact_attestor','factory_runtime','MEMBER')"""
            )
            self.assertEqual(
                cursor.fetchone(),
                (False, True, False, False, False, False, False, False, False),
            )
            cursor.execute(
                "SELECT has_schema_privilege('factory_runtime','trust_ci','USAGE'), has_table_privilege('factory_runtime','factory.audit_log','UPDATE'), has_table_privilege('factory_runtime','factory.audit_log','DELETE')"
            )
            self.assertEqual(cursor.fetchone(), (False, False, False))
            cursor.execute(
                "SELECT has_table_privilege('factory_runtime','factory.audit_log','INSERT'), has_table_privilege('factory_audit_reader','factory.audit_log','SELECT')"
            )
            self.assertEqual(cursor.fetchone(), (True, True))
            cursor.execute(
                "SELECT has_table_privilege('factory_runtime','factory.capacity_counters','INSERT'), has_column_privilege('factory_runtime','factory.capacity_counters','ceiling','UPDATE'), has_column_privilege('factory_runtime','factory.capacity_counters','active_count','UPDATE'), has_table_privilege('factory_runtime','factory.intake_identities','UPDATE'), has_column_privilege('factory_runtime','factory.capacity_allocations','released_at','UPDATE')"
            )
            self.assertEqual(cursor.fetchone(), (False, False, False, False, False))
        forbidden = (
            ("UPDATE factory.accepted_intents SET body='{}'::jsonb",),
            ("UPDATE factory.task_events SET actor_id='tampered'",),
            ("UPDATE factory.audit_log SET actor_id='tampered'",),
            ("DELETE FROM factory.accepted_intents",),
            ("UPDATE factory.capacity_counters SET ceiling=999 WHERE scope_key='global:reader'",),
            ("UPDATE factory.capacity_counters SET active_count=0 WHERE scope_key='global:reader'",),
            ("INSERT INTO factory.capacity_counters(scope_key,active_count,ceiling) VALUES ('repository:forged/repo:reader',0,999)",),
            ("UPDATE factory.capacity_allocations SET released_at=clock_timestamp()",),
            ("UPDATE factory.capacity_allocations SET released_at=NULL",),
            ("UPDATE factory.intake_identities SET source_id='tampered'",),
            ("UPDATE factory.workspace_results SET body='{}'::jsonb",),
            ("DELETE FROM factory.workspace_results",),
        )
        for (statement,) in forbidden:
            with self.subTest(statement=statement), psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL ROLE factory_runtime")
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        cursor.execute(statement)
        lifecycle_task = self.submit(source="capacity-function-lifecycle").task
        lifecycle_grant = self.service.claim(
            owner="ignored", role=RunRole.READER, repositories=(lifecycle_task.repository_id,),
            lease_seconds=60, actor=WORKER, now=NOW,
        )
        self.assertIsNotNone(lifecycle_grant)
        self.service.observe_usage(
            lifecycle_grant, provider_call_id="capacity-lifecycle", price_table_digest="2" * 64,
            cost_usd_micros=0, token_units=0, output_bytes=0, actor=WORKER,
        )
        self.service.release(lifecycle_grant, outcome="completed", actor=WORKER, now=NOW)
        self.assertEqual(self.store.readiness()["status"], "ready")

    def test_audit_chain_binds_task_run_and_correlation_identity(self):
        import psycopg

        for field in ("task_id", "run_id", "correlation_id"):
            with self.subTest(field=field):
                task = self.submit(source=f"audit-semantic-{field}").task
                grant = self.service.claim(
                    owner="ignored", role=RunRole.READER, repositories=(task.repository_id,),
                    lease_seconds=60, actor=WORKER, now=NOW,
                )
                self.assertTrue(self.store.verify_audit_chain(task.task_id))
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    if field == "task_id":
                        other = self.submit(source=f"audit-other-{field}").task
                        cursor.execute(
                            "UPDATE factory.audit_log SET task_id=%s WHERE task_id=%s AND action='intake'",
                            (other.task_id, task.task_id),
                        )
                    elif field == "run_id":
                        cursor.execute(
                            "UPDATE factory.audit_log SET run_id=%s WHERE task_id=%s AND action='intake'",
                            (grant.run_id, task.task_id),
                        )
                    else:
                        cursor.execute(
                            "UPDATE factory.audit_log SET correlation_id='tampered' WHERE task_id=%s AND action='intake'",
                            (task.task_id,),
                        )
                self.assertFalse(self.store.verify_audit_chain(task.task_id))

    def test_hidden_allocation_invalidates_fence_and_reconciliation_fails_closed(self):
        import psycopg

        task = self.submit(source="hidden-allocation").task
        grant = self.service.claim(
            owner="ignored", role=RunRole.READER, repositories=(task.repository_id,),
            lease_seconds=60, actor=WORKER, now=NOW,
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.capacity_allocations SET released_at=clock_timestamp() WHERE run_id=%s",
                (grant.run_id,),
            )
        with self.assertRaises(FenceError):
            self.service.heartbeat(grant, actor=WORKER, now=NOW)
        with self.assertRaises(FenceError):
            self.service.release(grant, outcome=FailureClass.WORKER_LOST, actor=WORKER, now=NOW)
        with self.assertRaises(FenceError):
            self.service.reserve_budget(
                grant, cost_usd_micros=0, token_units=0, wall_seconds=1,
                reason_digest="a" * 64, idempotency_key="b" * 64, actor=WORKER,
            )
        with self.assertRaises(FenceError):
            self.service.observe_usage(
                grant, provider_call_id="hidden-allocation", price_table_digest="2" * 64,
                cost_usd_micros=0, token_units=0, output_bytes=0, actor=WORKER,
            )
        self.assertEqual(self.store.readiness()["status"], "not_ready")
        with self.assertRaisesRegex(StoreError, "capacity counters do not match live allocations"):
            self.service.reconcile(actor=OPERATOR, now=NOW)

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.capacity_allocations SET released_at=NULL WHERE run_id=%s",
                (grant.run_id,),
            )
        self.service.observe_usage(
            grant, provider_call_id="restored-allocation", price_table_digest="2" * 64,
            cost_usd_micros=0, token_units=0, output_bytes=0, actor=WORKER,
        )
        self.assertEqual(
            self.service.release(grant, outcome="completed", actor=WORKER, now=NOW),
            TaskStatus.READY_FOR_HUMAN,
        )
        self.assertEqual(self.store.readiness()["status"], "ready")


if __name__ == "__main__":
    unittest.main()
