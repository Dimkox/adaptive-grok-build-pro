from dataclasses import asdict, replace
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import json
import os
import threading
import time
import unittest
import uuid

from adaptive_factory.contracts import canonical_digest
from adaptive_factory.execution_contracts import WorkspaceResultV1, workspace_evidence_digest
from adaptive_factory.brokers import BrokerError, ProposalBroker, proposal_idempotency_key
from adaptive_factory.migrations import (
    PostgresMigrator,
    RoleSafetyError,
    discover_migrations,
)
from adaptive_factory.models import Actor, ExecutionStage, FailureClass, RunRole
from adaptive_factory.service import (
    AuthorizationError,
    ClaimRequest,
    FactoryService,
    SnapshotBrokerUnavailable,
)
from adaptive_factory.store import (
    FenceError,
    IntegrityError,
    PostgresArtifactAttestationStore,
    PostgresFactoryStore,
    StoreError,
    StoreUnavailable,
)
from adaptive_factory.protocol import CanonicalEvent
from adaptive_factory.recovery import (
    ExecutionRecovery,
    ExecutionRecoveryCandidate,
    ExecutionRecoveryNotDue,
)
from adaptive_factory.workspace import (
    ArtifactAttestationV1,
    FakeWorkspaceBroker,
    WorkspaceHandle,
    WorkspacePolicy,
    WorkspaceReleaseOutcome,
    WorkspaceSnapshotUnavailable,
    WorkspaceSnapshotV1,
)
from factory.tests.test_contracts import valid_intake
from factory.tests.test_execution_contracts import valid_packet
from factory.tests.test_execution_service import trusted_registry
from factory.tests.test_postgres_integration import DATABASE_URL, NOW, OPERATOR, WORKER


class TrustedArtifactBroker:
    def attest_artifact(self, request):
        return ArtifactAttestationV1.from_facts(
            {
                "contract_version": 1,
                **request.to_dict(),
                "source": "trusted_workspace_broker",
            }
        )


class TrustedSnapshotBroker:
    def snapshot(self, request, *, timeout_seconds=5.0):
        if timeout_seconds != 5.0:
            raise AssertionError("snapshot timeout must stay bounded")
        return WorkspaceSnapshotV1.from_facts(
            {
                "contract_version": 1,
                "repository_id": request.repository_id,
                "workspace_handle": request.workspace_handle,
                "input_head_sha": request.input_head_sha,
                "result_head_sha": "f" * 40,
                "diff_digest": "e" * 64,
                "diff_lines": 1,
                "source": "trusted_git_broker",
            }
        )


class RecordingSnapshotBroker:
    def __init__(self, *, unavailable_once=False, rendezvous=1):
        self.calls = 0
        self.unavailable_once = unavailable_once
        self._lock = threading.Lock()
        self._rendezvous = (
            threading.Barrier(rendezvous) if rendezvous > 1 else None
        )

    def snapshot(self, request, *, timeout_seconds):
        if timeout_seconds != 5.0:
            raise AssertionError("snapshot timeout must stay bounded")
        with self._lock:
            self.calls += 1
            call = self.calls
        if self._rendezvous is not None:
            self._rendezvous.wait(timeout=5)
        if self.unavailable_once and call == 1:
            return WorkspaceSnapshotUnavailable()
        return WorkspaceSnapshotV1.from_facts(
            {
                "contract_version": 1,
                "repository_id": request.repository_id,
                "workspace_handle": request.workspace_handle,
                "input_head_sha": request.input_head_sha,
                "result_head_sha": "f" * 40,
                "diff_digest": "e" * 64,
                "diff_lines": 1,
                "source": "trusted_git_broker",
            }
        )


@unittest.skipUnless(
    DATABASE_URL, "FACTORY_TEST_DATABASE_URL must name a disposable database"
)
class ExecutionPersistencePostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        PostgresMigrator(DATABASE_URL).apply()
        from adaptive_factory.admin import (
            provision_artifact_attestor_login,
            provision_runtime_login,
        )
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        cls.runtime_login = f"factory_exec_runtime_{os.getpid()}"
        cls.attestor_login = f"factory_exec_attestor_{os.getpid()}"
        cls.runtime_password = "local-" + "execution-runtime-password"
        cls.attestor_password = "local-" + "execution-attestor-password"
        provision_runtime_login(DATABASE_URL, cls.runtime_login, cls.runtime_password)
        provision_artifact_attestor_login(
            DATABASE_URL,
            cls.attestor_login,
            cls.attestor_password,
            runtime_login=cls.runtime_login,
        )
        values = conninfo_to_dict(DATABASE_URL)
        cls.runtime_url = make_conninfo(
            **{**values, "user": cls.runtime_login, "password": cls.runtime_password}
        )
        cls.attestor_url = make_conninfo(
            **{
                **values,
                "user": cls.attestor_login,
                "password": cls.attestor_password,
            }
        )

    @classmethod
    def tearDownClass(cls):
        import psycopg
        from psycopg import sql

        with psycopg.connect(DATABASE_URL) as connection:
            for login in (cls.attestor_login, cls.runtime_login):
                connection.execute(
                    sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(login))
                )

    @classmethod
    def runtime_store(cls, database_url: str | None = None):
        if database_url is None:
            return PostgresFactoryStore(cls.runtime_url)
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        return PostgresFactoryStore(
            make_conninfo(
                **{
                    **conninfo_to_dict(database_url),
                    "user": cls.runtime_login,
                    "password": cls.runtime_password,
                }
            )
        )

    def attestor_store(self):
        return PostgresArtifactAttestationStore(self.attestor_url)

    @classmethod
    def migrate(cls, database_url: str):
        return PostgresMigrator(database_url).apply(
            expected_runtime_login=cls.runtime_login,
            expected_artifact_attestor_login=cls.attestor_login,
        )

    def setUp(self):
        import psycopg

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "TRUNCATE factory.semantic_recovery_records, "
                "factory.semantic_escalations, factory.semantic_child_task_bindings, "
                "factory.semantic_child_proposals, factory.semantic_directives, "
                "factory.semantic_verdicts, factory.semantic_coverage, "
                "factory.semantic_findings, factory.semantic_assignments, "
                "factory.semantic_metric_events, factory.semantic_command_results, "
                "factory.semantic_subjects, factory.execution_recovery_outcomes, "
                "factory.execution_recovery_claims, factory.execution_recovery_jobs, "
                "factory.workspace_results, "
                "factory.execution_artifact_attestations, "
                "factory.execution_proposals, "
                "factory.execution_stage_events, factory.execution_manifests, "
                "factory.execution_packets, factory.audit_log, factory.audit_heads, "
                "factory.task_events, factory.command_results, factory.metric_counters, "
                "factory.budget_reservations, factory.usage_observations, "
                "factory.capacity_allocations, factory.attempts, factory.runs, "
                "factory.lease_sequences, factory.kill_switches, "
                "factory.reconciliation_runs, factory.tasks, factory.accepted_intents, "
                "factory.intake_identities, factory.m0_authority_observations, "
                "factory.m0_bootstrap_exceptions RESTART IDENTITY"
            )
            cursor.execute("SELECT to_regclass('factory.metric_counters_pre_012_untrusted')")
            if cursor.fetchone()[0] is not None:
                cursor.execute("TRUNCATE factory.kill_switch_heads")
                cursor.execute("INSERT INTO factory.metric_counters(singleton) VALUES (true)")
            cursor.execute("UPDATE factory.capacity_counters SET active_count=0")
            cursor.execute(
                "UPDATE factory.execution_metric_counters SET "
                "execution_claimed=0,stage_prepared=0,stage_running=0,stage_collecting=0,"
                "stage_completed=0,stage_failed=0,stage_needs_human=0,stage_cancelled=0,"
                "stage_orphaned=0,proposal_note=0,proposal_artifact=0,proposal_usage=0,"
                "proposal_terminal=0,recovery_claimed=0,recovery_orphaned=0,"
                "recovery_cancelled=0,cleanup_succeeded=0,cleanup_failed=0"
            )
            cursor.execute(
                """INSERT INTO factory.m0_authority_observations
                (observation_id,observed_at,check_name,exact_head_sha,issuer,
                 evidence_digest,repository_id,policy_digest)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
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
        self.store = self.runtime_store()
        self.service = FactoryService(self.store)

    def create_schema14_database(self, suffix: str) -> tuple[str, str]:
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        database = f"factory_slice03_{suffix}_{uuid.uuid4().hex[:8]}"
        connection_values = conninfo_to_dict(DATABASE_URL)
        admin_url = make_conninfo(**{**connection_values, "dbname": "postgres"})
        with psycopg.connect(admin_url, autocommit=True) as connection:
            connection.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database))
            )
        database_url = make_conninfo(**{**connection_values, "dbname": database})
        migrations = tuple(PostgresMigrator(DATABASE_URL).status())
        self.assertEqual(len(migrations), 18)
        from adaptive_factory.migrations import discover_migrations

        packaged = discover_migrations()
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA factory")
            cursor.execute(
                """CREATE TABLE factory.schema_migrations (
                version integer PRIMARY KEY,name text UNIQUE NOT NULL,
                sha256 char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
                applied_at timestamptz NOT NULL DEFAULT now())"""
            )
            for migration in packaged[:14]:
                cursor.execute(migration.sql)
                cursor.execute(
                    "INSERT INTO factory.schema_migrations(version,name,sha256) "
                    "VALUES (%s,%s,%s)",
                    (migration.version, migration.name, migration.sha256),
                )
        return database_url, admin_url

    @staticmethod
    def drop_disposable_database(database_url: str, admin_url: str) -> None:
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict

        database = conninfo_to_dict(database_url)["dbname"]
        with psycopg.connect(admin_url, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                    sql.Identifier(database)
                )
            )

    def populate_schema14_execution(
        self,
        database_url: str,
        *,
        proposal_kind: str = "note",
    ):
        import psycopg

        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO factory.m0_authority_observations
                (observation_id,observed_at,check_name,exact_head_sha,issuer,
                 evidence_digest,repository_id,policy_digest)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
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
        store = self.runtime_store(database_url)
        service = FactoryService(store)
        payload = valid_intake()
        payload["source_id"] = f"schema14-{uuid.uuid4()}"
        payload["m0_authority"]["observed_at"] = NOW.isoformat()
        task = service.intake(payload, actor=OPERATOR, now=NOW).task
        capabilities = {
            "note": ["notes", "structured_output"],
            "terminal": ["notes", "structured_output"],
            "artifact": ["artifacts", "structured_output"],
        }[proposal_kind]
        selection = self.selection(capabilities=capabilities)
        execution = FactoryService(
            store, execution_registry=trusted_registry(selection)
        ).claim_execution(
            owner=WORKER.actor_id,
            role=RunRole.WRITER,
            repositories=(task.repository_id,),
            lease_seconds=60,
            selection=selection,
            actor=WORKER,
            now=NOW,
        )
        context = store.proposal_context(execution.lease, execution.packet_digest)
        event = CanonicalEvent.from_payload(
            task_id=execution.lease.task_id,
            run_id=execution.lease.run_id,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type={
                "note": "note.proposed",
                "terminal": "run.needs_human",
                "artifact": "artifact.proposed",
            }[proposal_kind],
            payload={
                "note": {"note_type": "finding", "body": "upgrade", "evidence": []},
                "terminal": {"reason": "upgrade", "diagnostic": "legacy row"},
                "artifact": {
                    "artifact_class": "patch",
                    "path": "factory/src/upgrade.patch",
                    "sha256": "e" * 64,
                    "size_bytes": 8,
                    "media_type": "text/plain",
                },
            }[proposal_kind],
        )
        proposal = ProposalBroker().accept(
            event,
            context,
            owner=execution.lease.owner,
            fence=execution.lease.fence,
            artifact_attestation_digest=(
                "d" * 64 if proposal_kind == "artifact" else None
            ),
        )
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE factory_runtime")
            cursor.execute(
                """SELECT factory.execution_propose(
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
                (
                    execution.lease.task_id,
                    execution.lease.run_id,
                    execution.lease.owner,
                    execution.lease.fence,
                    execution.lease.packet_digest,
                    execution.packet_digest,
                    event.sequence,
                    proposal.idempotency_key,
                    proposal_kind,
                    json.dumps(asdict(proposal), sort_keys=True, separators=(",", ":")),
                ),
            )
            self.assertTrue(cursor.fetchone()[0])
        return task, execution, proposal, store

    @staticmethod
    def insert_schema14_legacy_result(
        cursor,
        task,
        execution,
        terminal,
        legacy_body,
    ) -> None:
        cursor.execute(
            "SELECT trim(manifest_digest) FROM factory.execution_manifests "
            "WHERE run_id=%s",
            (execution.lease.run_id,),
        )
        manifest_digest = cursor.fetchone()[0]
        cursor.execute(
            """INSERT INTO factory.workspace_results(
            workspace_result_digest,task_id,run_id,task_packet_digest,
            run_manifest_digest,exact_head_sha,workspace_snapshot_digest,
            terminal_stage,terminal_proposal_digest,artifact_manifest_digest,
            note_manifest_digest,usage_evidence_digest,diagnostics_digest,
            workspace_snapshot,body)
            VALUES (%s,%s,%s,%s,%s,%s,%s,'needs_human',%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)""",
            (
                "1" * 64,
                task.task_id,
                execution.lease.run_id,
                execution.packet_digest,
                manifest_digest,
                "2" * 40,
                "3" * 64,
                terminal.idempotency_key,
                "4" * 64,
                "5" * 64,
                "6" * 64,
                "7" * 64,
                json.dumps({"legacy": "snapshot"}),
                json.dumps(legacy_body),
            ),
        )

    @staticmethod
    def replaced_execution_function_metadata(cursor):
        names = (
            "execution_start",
            "execution_advance",
            "execution_propose",
            "execution_proposal_context",
            "execution_result_for_run",
            "execution_result_by_digest",
            "execution_finalize_context",
            "execution_finalize_commit",
        )
        cursor.execute(
            """SELECT p.proname||'('||pg_get_function_identity_arguments(p.oid)||')',
            p.oid::bigint,p.prosecdef,p.proconfig,
            has_function_privilege('factory_runtime',p.oid,'EXECUTE'),
            has_function_privilege('factory_artifact_attestor',p.oid,'EXECUTE'),
            EXISTS (
              SELECT 1
              FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) acl
              WHERE acl.grantee=0 AND acl.privilege_type='EXECUTE'
            )
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname='factory' AND p.proname=ANY(%s) ORDER BY 1""",
            (list(names),),
        )
        return {row[0]: row[1:] for row in cursor.fetchall()}

    def submit(self, source: str):
        payload = valid_intake()
        payload["request_id"] = (
            "request-" + canonical_digest({"execution_source": source})[:24]
        )
        payload["source_id"] = source
        payload["m0_authority"]["observed_at"] = NOW.isoformat()
        return self.service.intake(payload, actor=OPERATOR, now=NOW).task

    @staticmethod
    def selection(*, capabilities: list[str]):
        packet = valid_packet()
        packet["provider"]["capabilities"] = sorted(capabilities)
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

    def claim_execution(self, source: str, *, capabilities: list[str]):
        task = self.submit(source)
        selection = self.selection(capabilities=capabilities)
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
        self.assertIsNotNone(execution)
        return task, execution

    @staticmethod
    def proposal_body(execution, sequence, event_type, inner):
        envelope = {
            "contract": "adaptive-factory.execution-proposal/v1",
            "task_id": execution.lease.task_id,
            "run_id": execution.lease.run_id,
            "packet_digest": execution.packet_digest,
            "fence": execution.lease.fence,
            "author_role": execution.lease.role.value,
            "sequence": sequence,
            "event_type": event_type,
            "body": inner,
        }
        key = canonical_digest(envelope)
        return {
            "task_id": execution.lease.task_id,
            "run_id": execution.lease.run_id,
            "packet_digest": execution.packet_digest,
            "fence": execution.lease.fence,
            "sequence": sequence,
            "author_role": execution.lease.role.value,
            **inner,
            "idempotency_key": key,
        }, key

    @staticmethod
    def direct_propose(cursor, execution, sequence, kind, body, key):
        cursor.execute("SET LOCAL ROLE factory_runtime")
        cursor.execute(
            """SELECT factory.execution_propose(
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
            (
                execution.lease.task_id,
                execution.lease.run_id,
                execution.lease.owner,
                execution.lease.fence,
                execution.lease.packet_digest,
                execution.packet_digest,
                sequence,
                key,
                kind,
                json.dumps(body, sort_keys=True, separators=(",", ":")),
            ),
        )
        return cursor.fetchone()[0]

    @staticmethod
    def artifact_attestation(execution, sequence, values):
        return ArtifactAttestationV1.from_facts(
            {
                "contract_version": 1,
                "task_id": execution.lease.task_id,
                "run_id": execution.lease.run_id,
                "repository_id": "owner/repository",
                "packet_digest": execution.packet_digest,
                "workspace_handle": execution.workspace_handle,
                "producer_sequence": sequence,
                "fence": execution.lease.fence,
                "author_role": execution.lease.role.value,
                **values,
                "source": "trusted_workspace_broker",
            }
        )

    def test_runtime_cannot_persist_noncanonical_packet_or_manifest(self):
        import psycopg

        task = self.submit("direct-noncanonical-start")
        grant = self.service.claim(
            owner=WORKER.actor_id,
            role=RunRole.WRITER,
            repositories=(task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        self.assertIsNotNone(grant)
        malformed_packet = {
            "role": "reader",
            "limits": {"max_events": 100},
            "unknown": "runtime asserted fact",
        }
        malformed_manifest = {
            "stage": "prepared",
            "deadline": (NOW + timedelta(minutes=1)).isoformat(),
            "unknown": True,
        }
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE factory_runtime")
            cursor.execute(
                """SELECT factory.execution_start(
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)""",
                (
                    grant.task_id,
                    grant.run_id,
                    grant.owner,
                    grant.fence,
                    grant.packet_digest,
                    "b" * 64,
                    "c" * 64,
                    "workspace:" + "d" * 64,
                    "codex",
                    json.dumps(malformed_packet, sort_keys=True, separators=(",", ":")),
                    json.dumps(malformed_manifest, sort_keys=True, separators=(",", ":")),
                ),
            )
            self.assertFalse(cursor.fetchone()[0])

    def test_canonical_start_preserves_six_digit_fractional_deadline(self):
        import psycopg

        task = self.submit("fractional-deadline-start")
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """UPDATE factory.tasks
                SET deadline_at=date_trunc('second',clock_timestamp())+interval '60.12 seconds'
                WHERE task_id=%s
                RETURNING to_char(deadline_at AT TIME ZONE 'UTC','YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"')""",
                (task.task_id,),
            )
            self.assertRegex(cursor.fetchone()[0], r"\.120000Z$")
        execution = FactoryService(
            self.store,
            execution_registry=trusted_registry(
                self.selection(capabilities=["notes", "structured_output"])
            ),
        ).claim_execution(
            owner=WORKER.actor_id,
            role=RunRole.WRITER,
            repositories=(task.repository_id,),
            lease_seconds=60,
            selection=self.selection(capabilities=["notes", "structured_output"]),
            actor=WORKER,
            now=NOW,
        )
        self.assertIsNotNone(execution)

    def test_runtime_cannot_persist_open_or_cross_bound_proposal_body(self):
        import psycopg

        _task, execution = self.claim_execution(
            "direct-open-proposal", capabilities=["notes", "structured_output"]
        )
        body = {
            "task_id": execution.lease.task_id,
            "run_id": execution.lease.run_id,
            "packet_digest": execution.packet_digest,
            "fence": execution.lease.fence,
            "sequence": 1,
            "author_role": "writer",
            "note_type": "finding",
            "body": "bounded",
            "evidence": [],
            "idempotency_key": "1" * 64,
            "unknown": "runtime asserted fact",
        }
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE factory_runtime")
            cursor.execute(
                """SELECT factory.execution_propose(
                %s,%s,%s,%s,%s,%s,%s,%s,'note',%s::jsonb)""",
                (
                    execution.lease.task_id,
                    execution.lease.run_id,
                    execution.lease.owner,
                    execution.lease.fence,
                    execution.lease.packet_digest,
                    execution.packet_digest,
                    1,
                    "1" * 64,
                    json.dumps(body, sort_keys=True, separators=(",", ":")),
                ),
            )
            self.assertFalse(cursor.fetchone()[0])

    def test_direct_runtime_accepts_only_exact_closed_replayable_four_kind_sequence(self):
        import psycopg

        _task, execution = self.claim_execution(
            "direct-four-kind-proposals",
            capabilities=["artifacts", "notes", "structured_output", "usage"],
        )
        artifact_values = {
            "artifact_class": "patch",
            "path": "factory/src/result.patch",
            "sha256": "e" * 64,
            "size_bytes": 12,
            "media_type": "text/x-diff",
        }
        attestation = self.artifact_attestation(execution, 2, artifact_values)
        proposals = (
            (
                1,
                "note",
                "note.proposed",
                {"note_type": "finding", "body": "bounded", "evidence": ["factory/src"]},
            ),
            (
                2,
                "artifact",
                "artifact.proposed",
                {
                    **artifact_values,
                    "author_role": "writer",
                    "artifact_attestation_digest": attestation.artifact_attestation_digest,
                },
            ),
            (
                3,
                "usage",
                "usage.reported",
                {
                    "author_role": "writer",
                    "provider_call_id": "provider-call-1",
                    "price_table_digest": "f" * 64,
                    "input_tokens": 2,
                    "output_tokens": 3,
                    "reasoning_tokens": 5,
                    "cost_usd_micros": 7,
                    "output_bytes": 11,
                },
            ),
            (
                4,
                "terminal",
                "run.completed",
                {
                    "author_role": "writer",
                    "terminal_type": "run.completed",
                    "summary": "complete",
                    "failure_class": None,
                    "reason": None,
                    "diagnostic": None,
                },
            ),
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            for sequence, kind, event_type, inner in proposals:
                if kind == "artifact":
                    self.assertEqual(
                        self.attestor_store().record_artifact_attestation(
                            attestation
                        ),
                        attestation,
                    )
                body, key = self.proposal_body(execution, sequence, event_type, inner)
                forged = dict(body, unknown="runtime asserted fact")
                with self.subTest(kind=kind, boundary="open"):
                    self.assertFalse(
                        self.direct_propose(cursor, execution, sequence, kind, forged, key)
                    )
                wrong_role_inner = {**inner, "author_role": "reader"}
                if kind == "note":
                    wrong_role_body = {**body, "author_role": "reader"}
                    wrong_role_envelope = {
                        "contract": "adaptive-factory.execution-proposal/v1",
                        "task_id": execution.lease.task_id,
                        "run_id": execution.lease.run_id,
                        "packet_digest": execution.packet_digest,
                        "fence": execution.lease.fence,
                        "author_role": "reader",
                        "sequence": sequence,
                        "event_type": event_type,
                        "body": inner,
                    }
                    wrong_role_key = canonical_digest(wrong_role_envelope)
                    wrong_role_body["idempotency_key"] = wrong_role_key
                else:
                    wrong_role_body, wrong_role_key = self.proposal_body(
                        execution, sequence, event_type, wrong_role_inner
                    )
                    wrong_role_body["author_role"] = "reader"
                    wrong_role_envelope = {
                        "contract": "adaptive-factory.execution-proposal/v1",
                        "task_id": execution.lease.task_id,
                        "run_id": execution.lease.run_id,
                        "packet_digest": execution.packet_digest,
                        "fence": execution.lease.fence,
                        "author_role": "reader",
                        "sequence": sequence,
                        "event_type": event_type,
                        "body": wrong_role_inner,
                    }
                    wrong_role_key = canonical_digest(wrong_role_envelope)
                    wrong_role_body["idempotency_key"] = wrong_role_key
                with self.subTest(kind=kind, boundary="role"):
                    self.assertFalse(
                        self.direct_propose(
                            cursor,
                            execution,
                            sequence,
                            kind,
                            wrong_role_body,
                            wrong_role_key,
                        )
                    )
                with self.subTest(kind=kind, boundary="positive"):
                    self.assertTrue(
                        self.direct_propose(cursor, execution, sequence, kind, body, key)
                    )
                    self.assertTrue(
                        self.direct_propose(cursor, execution, sequence, kind, body, key)
                    )
                collision = dict(body, idempotency_key="0" * 64)
                self.assertFalse(
                    self.direct_propose(
                        cursor, execution, sequence, kind, collision, "0" * 64
                    )
                )
                connection.commit()
            after_terminal, after_key = self.proposal_body(
                execution,
                5,
                "note.proposed",
                {"note_type": "finding", "body": "late", "evidence": []},
            )
            self.assertFalse(
                self.direct_propose(cursor, execution, 5, "note", after_terminal, after_key)
            )

    def test_direct_runtime_enforces_capabilities_and_per_kind_limits(self):
        import psycopg

        _task, execution = self.claim_execution(
            "direct-proposal-policy", capabilities=["cancellation"]
        )
        cases = (
            (
                "note",
                "note.proposed",
                {"note_type": "finding", "body": "bounded", "evidence": []},
            ),
            (
                "artifact",
                "artifact.proposed",
                {
                    "author_role": "writer",
                    "artifact_class": "patch",
                    "path": "factory/src/result.patch",
                    "sha256": "e" * 64,
                    "size_bytes": 12,
                    "media_type": "text/x-diff",
                    "artifact_attestation_digest": "f" * 64,
                },
            ),
            (
                "usage",
                "usage.reported",
                {
                    "author_role": "writer",
                    "provider_call_id": "provider-call-1",
                    "price_table_digest": "f" * 64,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "reasoning_tokens": 0,
                    "cost_usd_micros": 0,
                    "output_bytes": 0,
                },
            ),
            (
                "terminal",
                "run.completed",
                {
                    "author_role": "writer",
                    "terminal_type": "run.completed",
                    "summary": "complete",
                    "failure_class": None,
                    "reason": None,
                    "diagnostic": None,
                },
            ),
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            for kind, event_type, inner in cases:
                body, key = self.proposal_body(execution, 1, event_type, inner)
                with self.subTest(kind=kind):
                    self.assertFalse(
                        self.direct_propose(cursor, execution, 1, kind, body, key)
                    )

    def test_terminal_failure_reason_bound_matches_python_and_sql(self):
        import psycopg

        _task, execution = self.claim_execution(
            "terminal-reason-bound", capabilities=["structured_output"]
        )
        cases = (
            (
                "run.failed",
                {"failure_class": "protocol", "diagnostic": "x" * 4097},
                {
                    "author_role": "writer",
                    "terminal_type": "run.failed",
                    "summary": "protocol: " + "x" * 4097,
                    "failure_class": "protocol",
                    "reason": None,
                    "diagnostic": "x" * 4097,
                },
            ),
            (
                "run.needs_human",
                {"reason": "x" * 4097, "diagnostic": "bounded"},
                {
                    "author_role": "writer",
                    "terminal_type": "run.needs_human",
                    "summary": "x" * 4097 + ": bounded",
                    "failure_class": None,
                    "reason": "x" * 4097,
                    "diagnostic": "bounded",
                },
            ),
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            for event_type, payload, inner in cases:
                body, key = self.proposal_body(
                    execution, 1, event_type, inner
                )
                with self.subTest(event_type=event_type, boundary="sql"):
                    self.assertFalse(
                        self.direct_propose(
                            cursor, execution, 1, "terminal", body, key
                        )
                    )
                connection.rollback()
                with self.subTest(event_type=event_type, boundary="python"), \
                        self.assertRaisesRegex(BrokerError, "terminal_too_large"):
                    self.service.commit_execution_proposal(
                        execution.lease,
                        packet_digest=execution.packet_digest,
                        sequence=1,
                        event_type=event_type,
                        payload=payload,
                        actor=WORKER,
                    )
        valid = self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="run.needs_human",
            payload={"reason": "review", "diagnostic": "bounded"},
            actor=WORKER,
        )
        result = FactoryService(
            self.store, snapshot_broker=TrustedSnapshotBroker()
        ).finalize_execution(
            execution.lease,
            packet_digest=execution.packet_digest,
            actor=WORKER,
        )
        self.assertEqual(result.terminal_proposal_digest, valid.idempotency_key)
        self.assertEqual(result.failure_reason, "review")

    def test_result_carried_terminal_text_is_nfc_without_c0_controls(self):
        import psycopg

        _task, execution = self.claim_execution(
            "terminal-result-text-canonical", capabilities=["structured_output"]
        )
        cases = (
            (
                "run.failed",
                {"failure_class": "protocol", "diagnostic": "line1\nline2"},
                "protocol",
                None,
                "line1\nline2",
            ),
            (
                "run.failed",
                {"failure_class": "protocol", "diagnostic": "e\u0301"},
                "protocol",
                None,
                "e\u0301",
            ),
            (
                "run.needs_human",
                {"reason": "line1\nline2", "diagnostic": "bounded"},
                None,
                "line1\nline2",
                "bounded",
            ),
            (
                "run.needs_human",
                {"reason": "e\u0301", "diagnostic": "bounded"},
                None,
                "e\u0301",
                "bounded",
            ),
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            for event_type, payload, failure_class, reason, diagnostic in cases:
                inner = {
                    "author_role": "writer",
                    "terminal_type": event_type,
                    "summary": (
                        f"{failure_class}: {diagnostic}"
                        if failure_class is not None
                        else f"{reason}: {diagnostic}"
                    ),
                    "failure_class": failure_class,
                    "reason": reason,
                    "diagnostic": diagnostic,
                }
                body, key = self.proposal_body(execution, 1, event_type, inner)
                with self.subTest(event_type=event_type, payload=payload, boundary="sql"):
                    self.assertFalse(
                        self.direct_propose(
                            cursor, execution, 1, "terminal", body, key
                        )
                    )
                connection.rollback()
                with self.subTest(event_type=event_type, payload=payload, boundary="python"), \
                        self.assertRaisesRegex(BrokerError, "terminal_text"):
                    self.service.commit_execution_proposal(
                        execution.lease,
                        packet_digest=execution.packet_digest,
                        sequence=1,
                        event_type=event_type,
                        payload=payload,
                        actor=WORKER,
                    )
        valid = self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="run.failed",
            payload={"failure_class": "protocol", "diagnostic": "canonical"},
            actor=WORKER,
        )
        result = FactoryService(
            self.store, snapshot_broker=TrustedSnapshotBroker()
        ).finalize_execution(
            execution.lease,
            packet_digest=execution.packet_digest,
            actor=WORKER,
        )
        self.assertEqual(result.terminal_proposal_digest, valid.idempotency_key)
        self.assertEqual(result.failure_reason, "canonical")

    def test_direct_runtime_rejects_terminal_text_empty_at_python_sql_boundary(self):
        import psycopg

        _task, execution = self.claim_execution(
            "direct-empty-terminal", capabilities=["structured_output"]
        )
        cases = (
            (
                "run.completed",
                {
                    "author_role": "writer",
                    "terminal_type": "run.completed",
                    "summary": "",
                    "failure_class": None,
                    "reason": None,
                    "diagnostic": None,
                },
            ),
            (
                "run.failed",
                {
                    "author_role": "writer",
                    "terminal_type": "run.failed",
                    "summary": "protocol: ",
                    "failure_class": "protocol",
                    "reason": None,
                    "diagnostic": "",
                },
            ),
            (
                "run.needs_human",
                {
                    "author_role": "writer",
                    "terminal_type": "run.needs_human",
                    "summary": ": bounded",
                    "failure_class": None,
                    "reason": "",
                    "diagnostic": "bounded",
                },
            ),
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            for event_type, inner in cases:
                body, key = self.proposal_body(execution, 1, event_type, inner)
                with self.subTest(event_type=event_type):
                    self.assertFalse(
                        self.direct_propose(
                            cursor, execution, 1, "terminal", body, key
                        )
                    )

    def test_service_terminal_redaction_remains_sql_canonical(self):
        _task, execution = self.claim_execution(
            "terminal-redaction-parity", capabilities=["structured_output"]
        )
        proposal = self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="run.needs_human",
            payload={
                "reason": "Authorization=fixture-secret",
                "diagnostic": "bounded detail",
            },
            actor=WORKER,
            idempotency_key="e" * 64,
        )
        self.assertEqual(
            proposal.summary, f"{proposal.reason}: {proposal.diagnostic}"
        )
        self.assertNotIn("fixture-secret", proposal.summary)

    def test_maximum_ascii_and_multibyte_notes_fit_closed_proposal_envelope(self):
        _task, execution = self.claim_execution(
            "proposal-envelope-boundary", capabilities=["notes"]
        )
        values = ("x" * 65_536, "é" * 32_768)
        for sequence, body in enumerate(values, 1):
            proposal = self.service.commit_execution_proposal(
                execution.lease,
                packet_digest=execution.packet_digest,
                sequence=sequence,
                event_type="note.proposed",
                payload={"note_type": "finding", "body": body, "evidence": []},
                actor=WORKER,
                idempotency_key=format(sequence + 4, "x") * 64,
            )
            self.assertEqual(proposal.body, body)

    def test_runtime_and_attestor_effective_roles_are_mutually_isolated(self):
        import psycopg

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE factory_runtime")
            cursor.execute(
                """SELECT current_user,
                has_function_privilege(
                  current_user,'factory.execution_record_artifact_attestation(jsonb)','EXECUTE'),
                has_table_privilege(
                  current_user,'factory.execution_artifact_attestations','SELECT'),
                has_table_privilege(
                  current_user,'factory.execution_artifact_attestations','INSERT'),
                has_function_privilege(
                  current_user,
                  'factory.execution_propose(uuid,uuid,text,bigint,character,character,bigint,character,text,jsonb)',
                  'EXECUTE')"""
            )
            self.assertEqual(
                cursor.fetchone(), ("factory_runtime", False, False, False, True)
            )
            cursor.execute("RESET ROLE")
            cursor.execute("SET LOCAL ROLE factory_artifact_attestor")
            cursor.execute(
                """SELECT current_user,
                has_function_privilege(
                  current_user,'factory.execution_record_artifact_attestation(jsonb)','EXECUTE'),
                has_function_privilege(
                  current_user,
                  'factory.execution_propose(uuid,uuid,text,bigint,character,character,bigint,character,text,jsonb)',
                  'EXECUTE'),
                has_function_privilege(
                  current_user,
                  'factory.execution_proposal_context(uuid,uuid,text,bigint,character,character)',
                  'EXECUTE'),
                has_table_privilege(
                  current_user,'factory.execution_artifact_attestations','SELECT'),
                has_table_privilege(
                  current_user,'factory.execution_artifact_attestations','INSERT')"""
            )
            self.assertEqual(
                cursor.fetchone(),
                ("factory_artifact_attestor", True, False, False, False, False),
            )

    def test_capability_roles_reject_a_second_inbound_login_member(self):
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        extra_login = f"factory_exec_extra_{os.getpid()}"
        with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
            connection.execute(
                sql.SQL("CREATE ROLE {} LOGIN NOINHERIT PASSWORD {}").format(
                    sql.Identifier(extra_login),
                    sql.Literal("local-extra-capability-password"),
                )
            )
        try:
            for role, readiness in (
                ("factory_runtime", self.runtime_store().readiness),
                (
                    "factory_artifact_attestor",
                    self.attestor_store().readiness,
                ),
            ):
                with self.subTest(role=role), psycopg.connect(
                    DATABASE_URL, autocommit=True
                ) as connection:
                    connection.execute(
                        sql.SQL("GRANT {} TO {}").format(
                            sql.Identifier(role), sql.Identifier(extra_login)
                        )
                    )
                try:
                    extra_url = make_conninfo(
                        **{
                            **conninfo_to_dict(DATABASE_URL),
                            "user": extra_login,
                            "password": "local-extra-capability-password",
                        }
                    )
                    attacker_readiness = (
                        PostgresFactoryStore(extra_url).readiness
                        if role == "factory_runtime"
                        else PostgresArtifactAttestationStore(extra_url).readiness
                    )
                    for rejected in (readiness, attacker_readiness):
                        with self.assertRaisesRegex(
                            StoreError, "capability role is not isolated"
                        ):
                            rejected()
                finally:
                    with psycopg.connect(
                        DATABASE_URL, autocommit=True
                    ) as connection:
                        connection.execute(
                            sql.SQL("REVOKE {} FROM {}").format(
                                sql.Identifier(role), sql.Identifier(extra_login)
                            )
                        )
                self.assertEqual(
                    readiness()["database_role"], role
                )
            with psycopg.connect(
                DATABASE_URL
            ) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT
                    (SELECT count(*) FROM factory.command_results),
                    (SELECT count(*) FROM factory.execution_artifact_attestations),
                    (SELECT count(*) FROM factory.execution_recovery_jobs)"""
                )
                self.assertEqual(cursor.fetchone(), (0, 0, 0))
        finally:
            with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
                connection.execute(
                    sql.SQL("DROP ROLE IF EXISTS {}").format(
                        sql.Identifier(extra_login)
                    )
                )

    def test_existing_attestor_role_cannot_gain_login_or_membership(self):
        import psycopg
        from psycopg import sql

        parent = "factory_slice03_unsafe_parent"
        with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
            connection.execute("ALTER ROLE factory_artifact_attestor LOGIN")
        try:
            with self.assertRaises(RoleSafetyError):
                self.migrate(DATABASE_URL)
        finally:
            with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
                connection.execute("ALTER ROLE factory_artifact_attestor NOLOGIN")

        with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE ROLE {}").format(sql.Identifier(parent)))
            connection.execute(
                sql.SQL("GRANT {} TO factory_artifact_attestor").format(
                    sql.Identifier(parent)
                )
            )
        try:
            with self.assertRaises(RoleSafetyError):
                self.migrate(DATABASE_URL)
        finally:
            with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
                connection.execute(
                    sql.SQL("REVOKE {} FROM factory_artifact_attestor").format(
                        sql.Identifier(parent)
                    )
                )
                connection.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(parent)))

    def test_separate_runtime_and_attestor_logins_survive_upgrade_and_attest(self):
        from adaptive_factory.admin import bootstrap_local

        readiness = bootstrap_local(
            DATABASE_URL,
            self.runtime_login,
            self.runtime_password,
            self.runtime_url,
            artifact_attestor_login=self.attestor_login,
            artifact_attestor_password=self.attestor_password,
            artifact_attestor_url=self.attestor_url,
        )
        self.assertEqual(readiness["database_role"], "factory_runtime")
        self.assertEqual(readiness["schema_version"], 18)
        self.assertEqual(
            readiness["artifact_attestor_database_role"],
            "factory_artifact_attestor",
        )
        attestor_store = self.attestor_store()
        self.assertEqual(
            attestor_store.readiness(),
            {
                "session_user": self.attestor_login,
                "database_role": "factory_artifact_attestor",
            },
        )
        _task, execution = self.claim_execution(
            "dedicated-attestor-login", capabilities=["artifacts"]
        )
        values = {
            "artifact_class": "patch",
            "path": "factory/src/result.patch",
            "sha256": "e" * 64,
            "size_bytes": 12,
            "media_type": "text/x-diff",
        }
        attestation = self.artifact_attestation(execution, 1, values)
        self.assertEqual(
            attestor_store.record_artifact_attestation(attestation), attestation
        )

    def test_bootstrap_rejects_partial_attestor_configuration_before_provisioning(self):
        import psycopg
        from adaptive_factory.admin import BootstrapError, bootstrap_local
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        runtime_login = "factory_partial_runtime"
        attestor_login = "factory_partial_attestor"
        runtime_url = make_conninfo(
            **{
                **conninfo_to_dict(DATABASE_URL),
                "user": runtime_login,
                "password": "local-partial-runtime-password",
            }
        )
        with self.assertRaisesRegex(
            BootstrapError, "complete artifact attestor configuration"
        ):
            bootstrap_local(
                DATABASE_URL,
                runtime_login,
                "local-partial-runtime-password",
                runtime_url,
                artifact_attestor_login=attestor_login,
            )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT rolname FROM pg_roles WHERE rolname=ANY(%s)",
                ([runtime_login, attestor_login],),
            )
            self.assertEqual(cursor.fetchall(), [])

    def test_attestor_proposal_probes_use_bounded_partial_and_sequence_indexes(self):
        import psycopg

        def index_names(plan):
            names = set()
            if isinstance(plan, dict):
                if "Index Name" in plan:
                    names.add(plan["Index Name"])
                for value in plan.values():
                    names.update(index_names(value))
            elif isinstance(plan, list):
                for value in plan:
                    names.update(index_names(value))
            return names

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_get_functiondef('factory.execution_record_artifact_attestation(jsonb)'::regprocedure)"
            )
            definition = cursor.fetchone()[0].lower()
            self.assertNotIn("count(*) from factory.execution_proposals", definition)
            self.assertNotIn("bool_or(", definition)
            self.assertIn("order by producer_sequence desc", definition)
            self.assertIn("limit 1", definition)
            cursor.execute("SET LOCAL enable_seqscan=off")
            cursor.execute(
                "EXPLAIN (FORMAT JSON) SELECT 1 FROM factory.execution_proposals "
                "WHERE run_id=%s AND proposal_kind='terminal'",
                (uuid.uuid4(),),
            )
            terminal_plan = cursor.fetchone()[0]
            cursor.execute(
                "EXPLAIN (FORMAT JSON) SELECT producer_sequence "
                "FROM factory.execution_proposals WHERE run_id=%s "
                "ORDER BY producer_sequence DESC LIMIT 1",
                (uuid.uuid4(),),
            )
            sequence_plan = cursor.fetchone()[0]
        self.assertIn("execution_proposals_one_terminal", index_names(terminal_plan))
        self.assertIn(
            "execution_proposals_run_id_producer_sequence_key",
            index_names(sequence_plan),
        )

    def test_direct_claim_rejects_actor_owner_mismatch_before_connect_or_mutation(self):
        import psycopg

        task = self.submit("claim-actor-owner-boundary")
        request = ClaimRequest(
            "different-worker", RunRole.WRITER, (task.repository_id,), 60
        )
        calls = []
        original_connect = self.store._connect

        def forbidden_connect():
            calls.append("connect")
            raise AssertionError("claim connected before validating worker owner")

        self.store._connect = forbidden_connect
        try:
            with self.assertRaisesRegex(StoreError, "claim owner must match worker actor"):
                self.store.claim(
                    request,
                    WORKER,
                    NOW,
                    idempotency_key="f" * 64,
                )
        finally:
            self.store._connect = original_connect
        self.assertEqual(calls, [])
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT state,current_run_id,current_fence FROM factory.tasks WHERE task_id=%s",
                (task.task_id,),
            )
            self.assertEqual(cursor.fetchone(), ("queued", None, None))
            cursor.execute("SELECT count(*) FROM factory.runs WHERE task_id=%s", (task.task_id,))
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute(
                "SELECT count(*) FROM factory.command_results WHERE idempotency_key=%s",
                ("f" * 64,),
            )
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_attestor_invalid_uuid_and_bigint_are_bounded_rejections(self):
        import psycopg

        request = {
            "contract_version": 1,
            "task_id": "00000000-0000-0000-0000-000000000001",
            "run_id": "00000000-0000-0000-0000-000000000002",
            "repository_id": "owner/repository",
            "packet_digest": "a" * 64,
            "workspace_handle": "workspace:" + "b" * 64,
            "producer_sequence": 1,
            "fence": 1,
            "author_role": "writer",
            "artifact_class": "patch",
            "path": "factory/src/result.patch",
            "sha256": "c" * 64,
            "size_bytes": 1,
            "media_type": "text/plain",
            "source": "trusted_workspace_broker",
            "artifact_attestation_digest": "d" * 64,
        }
        cases = (
            {**request, "task_id": "00000000-0000-0000-0000-00000000000-"},
            {**request, "fence": 9_999_999_999_999_999_999},
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE factory_artifact_attestor")
            for invalid in cases:
                with self.subTest(invalid=invalid):
                    cursor.execute(
                        "SELECT factory.execution_record_artifact_attestation(%s::jsonb)",
                        (json.dumps(invalid, sort_keys=True, separators=(",", ":")),),
                    )
                    self.assertIsNone(cursor.fetchone()[0])
            cursor.execute("RESET ROLE")
            cursor.execute("SELECT count(*) FROM factory.execution_artifact_attestations")
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_schema14_populated_execution_upgrades_forward_to_canonical_finalize(self):
        import psycopg

        database_url, admin_url = self.create_schema14_database("upgrade")
        try:
            task, execution, note, store = self.populate_schema14_execution(
                database_url, proposal_kind="note"
            )
            with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                before_functions = self.replaced_execution_function_metadata(cursor)
            applied = self.migrate(database_url)
            self.assertEqual(
                [(item.version, item.name) for item in applied],
                [
                    (15, "015_execution_canonical_persistence.sql"),
                    (16, "016_contract_execution_canonical_persistence.sql"),
                    (17, "017_execution_recovery_topology.sql"),
                    (18, "018_semantic_validation_bridge.sql"),
                ],
            )
            with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT max(version),
                    (SELECT count(*) FROM factory.execution_packets),
                    (SELECT count(*) FROM factory.execution_manifests),
                    (SELECT count(*) FROM factory.execution_proposals),
                    to_regprocedure('factory.execution_record_artifact_attestation(jsonb)')
                      IS NOT NULL,
                    (SELECT count(*) FROM factory.execution_metric_counters),
                    (SELECT execution_claimed=0 AND stage_prepared=0
                       AND proposal_note=0 AND recovery_claimed=0
                     FROM factory.execution_metric_counters WHERE singleton)
                    FROM factory.schema_migrations"""
                )
                self.assertEqual(
                    cursor.fetchone(), (18, 1, 1, 1, True, 1, True)
                )
                self.assertEqual(
                    self.replaced_execution_function_metadata(cursor),
                    before_functions,
                )
                for metadata in before_functions.values():
                    _oid, security_definer, config, runtime, attestor, public = metadata
                    self.assertTrue(security_definer)
                    self.assertEqual(config, ["search_path=pg_catalog, factory"])
                    self.assertTrue(runtime)
                    self.assertFalse(attestor)
                    self.assertFalse(public)
                cursor.execute(
                    """SELECT conname FROM pg_constraint
                    WHERE conrelid='factory.workspace_results'::regclass
                      AND conname=ANY(%s) ORDER BY conname""",
                    (
                        [
                            "workspace_results_run_manifest_digest_fkey",
                            "workspace_results_run_id_terminal_proposal_digest_fkey",
                            "workspace_results_run_manifest_digest_run_id_fkey",
                            "workspace_results_terminal_proposal_fkey",
                        ],
                    ),
                )
                self.assertEqual(
                    [row[0] for row in cursor.fetchall()],
                    [
                        "workspace_results_run_id_terminal_proposal_digest_fkey",
                        "workspace_results_run_manifest_digest_fkey",
                        "workspace_results_run_manifest_digest_run_id_fkey",
                        "workspace_results_terminal_proposal_fkey",
                    ],
                )
                cursor.execute(
                    """SELECT conname FROM pg_constraint
                    WHERE conname=ANY(%s) ORDER BY conname""",
                    (
                        [
                            "execution_proposals_body_check",
                            "execution_proposals_canonical_body_check",
                            "workspace_results_workspace_snapshot_digest_key",
                        ],
                    ),
                )
                self.assertEqual(
                    [row[0] for row in cursor.fetchall()],
                    ["execution_proposals_canonical_body_check"],
                )
            self.assertEqual(self.migrate(database_url), ())
            service = FactoryService(store)
            terminal = service.commit_execution_proposal(
                execution.lease,
                packet_digest=execution.packet_digest,
                sequence=2,
                event_type="run.needs_human",
                payload={"reason": "upgrade", "diagnostic": "canonical finalize"},
                actor=WORKER,
            )
            result = FactoryService(
                store, snapshot_broker=TrustedSnapshotBroker()
            ).finalize_execution(
                execution.lease,
                packet_digest=execution.packet_digest,
                actor=WORKER,
            )
            self.assertEqual(result.terminal_proposal_digest, terminal.idempotency_key)
            self.assertEqual(result.note_manifest_digest, workspace_evidence_digest(
                "notes", [note.idempotency_key]
            ))
            self.assertEqual(store.get_task(task.task_id).status.value, "needs_human")
            with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT proposal_terminal,stage_needs_human
                    FROM factory.execution_metric_counters WHERE singleton"""
                )
                self.assertEqual(cursor.fetchone(), (1, 1))
        finally:
            self.drop_disposable_database(database_url, admin_url)

    def test_schema14_upgrade_rejects_rogue_inbound_capability_member_atomically(self):
        import psycopg
        from psycopg import sql

        database_url, admin_url = self.create_schema14_database(
            "rogue_inbound_member"
        )
        rogue_login = f"factory_upgrade_rogue_{os.getpid()}"
        try:
            _task, _execution, _note, _store = self.populate_schema14_execution(
                database_url, proposal_kind="note"
            )
            with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
                connection.execute(
                    sql.SQL("CREATE ROLE {} LOGIN NOINHERIT PASSWORD {}").format(
                        sql.Identifier(rogue_login),
                        sql.Literal("local-upgrade-rogue-password"),
                    )
                )
                connection.execute(
                    sql.SQL("GRANT factory_runtime TO {}").format(
                        sql.Identifier(rogue_login)
                    )
                )
            try:
                with self.assertRaisesRegex(
                    RoleSafetyError, "role membership boundary is unsafe"
                ):
                    self.migrate(database_url)
                with psycopg.connect(
                    database_url
                ) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        """SELECT max(version),
                        to_regclass('factory.execution_recovery_jobs'),
                        (SELECT count(*) FROM factory.execution_packets),
                        (SELECT count(*) FROM factory.execution_manifests),
                        (SELECT count(*) FROM factory.execution_proposals)
                        FROM factory.schema_migrations"""
                    )
                    self.assertEqual(cursor.fetchone(), (14, None, 1, 1, 1))
            finally:
                with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
                    connection.execute(
                        sql.SQL("REVOKE factory_runtime FROM {}").format(
                            sql.Identifier(rogue_login)
                        )
                    )
                    connection.execute(
                        sql.SQL("DROP ROLE IF EXISTS {}").format(
                            sql.Identifier(rogue_login)
                        )
                    )
            self.assertEqual(
                [item.version for item in self.migrate(database_url)],
                [15, 16, 17],
            )
        finally:
            with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
                connection.execute(
                    sql.SQL("DROP ROLE IF EXISTS {}").format(
                        sql.Identifier(rogue_login)
                    )
                )
            self.drop_disposable_database(database_url, admin_url)

    def test_populated_schema16_to_17_is_atomic_zero_epoch_and_forward_only(self):
        import psycopg

        database_url, admin_url = self.create_schema14_database("schema16_recovery")
        try:
            _task, _execution, _note, _store = self.populate_schema14_execution(
                database_url, proposal_kind="note"
            )
            packaged = discover_migrations()
            with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                for migration in packaged[14:16]:
                    cursor.execute(migration.sql)
                    cursor.execute(
                        "INSERT INTO factory.schema_migrations(version,name,sha256) "
                        "VALUES (%s,%s,%s)",
                        (migration.version, migration.name, migration.sha256),
                    )
                cursor.execute(
                    "CREATE TABLE factory.execution_metric_counters "
                    "(singleton boolean PRIMARY KEY)"
                )
            with self.assertRaises(psycopg.errors.DuplicateTable):
                self.migrate(database_url)
            with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT max(version),
                    to_regclass('factory.execution_recovery_jobs'),
                    to_regclass('factory.execution_recovery_claims'),
                    to_regclass('factory.execution_recovery_outcomes'),
                    to_regclass('factory.execution_metric_counters') IS NOT NULL,
                    (SELECT count(*) FROM factory.execution_packets),
                    (SELECT count(*) FROM factory.execution_manifests),
                    (SELECT count(*) FROM factory.execution_proposals)
                    FROM factory.schema_migrations"""
                )
                self.assertEqual(
                    cursor.fetchone(), (16, None, None, None, True, 1, 1, 1)
                )
                cursor.execute("DROP TABLE factory.execution_metric_counters")
            applied = self.migrate(database_url)
            self.assertEqual(
                [(item.version, item.name) for item in applied],
                [
                    (17, "017_execution_recovery_topology.sql"),
                    (18, "018_semantic_validation_bridge.sql"),
                ],
            )
            with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT max(version),
                    (SELECT count(*) FROM factory.execution_packets),
                    (SELECT count(*) FROM factory.execution_manifests),
                    (SELECT count(*) FROM factory.execution_proposals),
                    (SELECT count(*) FROM factory.execution_metric_counters),
                    (SELECT execution_claimed=0 AND stage_prepared=0
                       AND proposal_note=0 AND recovery_claimed=0
                     FROM factory.execution_metric_counters WHERE singleton)
                    FROM factory.schema_migrations"""
                )
                self.assertEqual(cursor.fetchone(), (18, 1, 1, 1, 1, True))
        finally:
            self.drop_disposable_database(database_url, admin_url)

    def test_schema14_expand_overlay_preserves_constraints_until_contract_phase(self):
        import psycopg

        database_url, admin_url = self.create_schema14_database("expand_contract")
        try:
            canonical = discover_migrations()[14]
            self.assertEqual(canonical.name, "015_execution_canonical_persistence.sql")
            with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                cursor.execute(canonical.sql)
                cursor.execute(
                    """SELECT conname,pg_get_constraintdef(oid)
                    FROM pg_constraint
                    WHERE (conrelid='factory.execution_proposals'::regclass
                         AND conname IN (
                           'execution_proposals_body_check',
                           'execution_proposals_canonical_body_check'))
                       OR (conrelid='factory.workspace_results'::regclass
                         AND conname='workspace_results_workspace_snapshot_digest_key')"""
                )
                constraints = dict(cursor.fetchall())
                self.assertIn("65536", constraints["execution_proposals_body_check"])
                self.assertIn(
                    "1048576", constraints["execution_proposals_canonical_body_check"]
                )
                self.assertIn(
                    "workspace_results_workspace_snapshot_digest_key", constraints
                )
        finally:
            self.drop_disposable_database(database_url, admin_url)

    def test_schema15_rejects_legacy_finalized_rows_before_any_ddl_or_release(self):
        import psycopg

        database_url, admin_url = self.create_schema14_database("legacy_result")
        try:
            task, execution, terminal, _store = self.populate_schema14_execution(
                database_url, proposal_kind="terminal"
            )
            legacy_body = {"legacy": True}
            with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                self.insert_schema14_legacy_result(
                    cursor, task, execution, terminal, legacy_body
                )
            with self.assertRaisesRegex(
                psycopg.Error, "refuses legacy finalized workspace rows"
            ):
                self.migrate(database_url)
            with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT max(version),
                    (SELECT body FROM factory.workspace_results WHERE run_id=%s),
                    to_regprocedure('factory.execution_object_has_exact_keys(jsonb,text[])'),
                    EXISTS(SELECT 1 FROM information_schema.columns
                      WHERE table_schema='factory' AND table_name='workspace_results'
                        AND column_name='m4_status'),
                    t.state,r.released_at IS NULL,a.released_at IS NULL,
                    m.terminal_at IS NULL
                    FROM factory.schema_migrations versions
                    CROSS JOIN factory.tasks t
                    JOIN factory.runs r ON r.run_id=t.current_run_id
                    JOIN factory.capacity_allocations a ON a.run_id=r.run_id
                    JOIN factory.execution_manifests m ON m.run_id=r.run_id
                    WHERE t.task_id=%s GROUP BY t.state,r.released_at,a.released_at,
                      m.terminal_at""",
                    (execution.lease.run_id, task.task_id),
                )
                self.assertEqual(
                    cursor.fetchone(),
                    (14, legacy_body, None, False, "leased", True, True, True),
                )
        finally:
            self.drop_disposable_database(database_url, admin_url)

    def test_schema14_terminal_without_result_upgrades_and_finalizes_canonically(self):
        import psycopg

        database_url, admin_url = self.create_schema14_database("terminal_window")
        try:
            task, execution, terminal, store = self.populate_schema14_execution(
                database_url, proposal_kind="terminal"
            )
            applied = self.migrate(database_url)
            self.assertEqual(
                [(item.version, item.name) for item in applied],
                [
                    (15, "015_execution_canonical_persistence.sql"),
                    (16, "016_contract_execution_canonical_persistence.sql"),
                    (17, "017_execution_recovery_topology.sql"),
                    (18, "018_semantic_validation_bridge.sql"),
                ],
            )
            result = FactoryService(
                store, snapshot_broker=TrustedSnapshotBroker()
            ).finalize_execution(
                execution.lease,
                packet_digest=execution.packet_digest,
                actor=WORKER,
            )
            self.assertEqual(result.terminal_proposal_digest, terminal.idempotency_key)
            self.assertEqual(result.terminal_stage, "needs_human")
            self.assertEqual(result.m4_status, "needs_human")
            self.assertEqual(store.get_task(task.task_id).status.value, "needs_human")
            with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT max(version),
                    (SELECT count(*) FROM factory.workspace_results),
                    (SELECT bool_and(
                      body->>'workspace_result_digest'=trim(workspace_result_digest)
                      AND body->>'terminal_proposal_digest'=trim(terminal_proposal_digest)
                      AND body->>'m4_status'=m4_status)
                      FROM factory.workspace_results)
                    FROM factory.schema_migrations"""
                )
                self.assertEqual(cursor.fetchone(), (18, 1, True))
        finally:
            self.drop_disposable_database(database_url, admin_url)

    def test_schema14_contract_phase_failure_rolls_back_the_expand_overlay(self):
        import psycopg

        database_url, admin_url = self.create_schema14_database("contract_rollback")
        try:
            with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """ALTER TABLE factory.execution_proposals
                    RENAME CONSTRAINT execution_proposals_body_check
                    TO execution_proposals_body_check_fixture"""
                )
            with self.assertRaises(psycopg.Error):
                self.migrate(database_url)
            with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT max(version),
                    to_regclass('factory.execution_artifact_attestations'),
                    to_regprocedure('factory.execution_object_has_exact_keys(jsonb,text[])'),
                    EXISTS(SELECT 1 FROM information_schema.columns
                      WHERE table_schema='factory' AND table_name='workspace_results'
                        AND column_name='m4_status'),
                    EXISTS(SELECT 1 FROM pg_constraint
                      WHERE conrelid='factory.execution_proposals'::regclass
                        AND conname='execution_proposals_body_check_fixture')
                    FROM factory.schema_migrations"""
                )
                self.assertEqual(cursor.fetchone(), (14, None, None, False, True))
        finally:
            self.drop_disposable_database(database_url, admin_url)

    def test_schema15_rejects_unattested_schema14_artifact_without_residue(self):
        import psycopg

        database_url, admin_url = self.create_schema14_database("legacy_artifact")
        try:
            _task, execution, artifact, _store = self.populate_schema14_execution(
                database_url, proposal_kind="artifact"
            )
            with self.assertRaisesRegex(
                psycopg.Error, "refuses unattested legacy artifact proposals"
            ):
                self.migrate(database_url)
            with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT max(version),
                    (SELECT proposal_kind FROM factory.execution_proposals
                      WHERE run_id=%s AND idempotency_key=%s),
                    to_regclass('factory.execution_artifact_attestations'),
                    to_regprocedure('factory.execution_object_has_exact_keys(jsonb,text[])'),
                    EXISTS(SELECT 1 FROM information_schema.columns
                      WHERE table_schema='factory' AND table_name='workspace_results'
                        AND column_name='m4_status')
                    FROM factory.schema_migrations""",
                    (execution.lease.run_id, artifact.idempotency_key),
                )
                self.assertEqual(cursor.fetchone(), (14, "artifact", None, None, False))
        finally:
            self.drop_disposable_database(database_url, admin_url)

    def test_schema15_lock_gate_serializes_old_finalize_before_fresh_snapshot(self):
        import psycopg

        database_url, admin_url = self.create_schema14_database("legacy_race")
        try:
            task, execution, terminal, _store = self.populate_schema14_execution(
                database_url, proposal_kind="terminal"
            )
            migration = next(
                item for item in discover_migrations() if item.version == 15
            )
            self.assertEqual(migration.name, "015_execution_canonical_persistence.sql")
            legacy_body = {"legacy": "concurrent"}
            with psycopg.connect(database_url) as legacy_connection:
                with legacy_connection.cursor() as legacy_cursor:
                    self.insert_schema14_legacy_result(
                        legacy_cursor, task, execution, terminal, legacy_body
                    )

                def apply_with_short_lock_timeout():
                    with psycopg.connect(database_url) as connection:
                        with connection.transaction(), connection.cursor() as cursor:
                            cursor.execute("SET LOCAL lock_timeout='250ms'")
                            cursor.execute(migration.sql)

                with ThreadPoolExecutor(max_workers=1) as executor:
                    attempt = executor.submit(apply_with_short_lock_timeout)
                    with self.assertRaisesRegex(psycopg.Error, "lock timeout"):
                        attempt.result(timeout=2)
                with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        """SELECT max(version),
                        to_regprocedure('factory.execution_object_has_exact_keys(jsonb,text[])'),
                        EXISTS(SELECT 1 FROM information_schema.columns
                          WHERE table_schema='factory' AND table_name='workspace_results'
                            AND column_name='m4_status')
                        FROM factory.schema_migrations"""
                    )
                    self.assertEqual(cursor.fetchone(), (14, None, False))
                legacy_connection.commit()
            with self.assertRaisesRegex(
                psycopg.Error, "refuses legacy finalized workspace rows"
            ):
                self.migrate(database_url)
            with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                cursor.execute(
                    "SELECT max(version),(SELECT body FROM factory.workspace_results) "
                    "FROM factory.schema_migrations"
                )
                self.assertEqual(cursor.fetchone(), (14, legacy_body))
        finally:
            self.drop_disposable_database(database_url, admin_url)

    def test_finalize_atomically_derives_m4_failure_and_cross_binds_result_bundle(self):
        import psycopg

        task, execution = self.claim_execution(
            "finalize-derived-m4", capabilities=["structured_output"]
        )
        terminal = self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="run.failed",
            payload={"failure_class": "validation", "diagnostic": "invalid output"},
            actor=WORKER,
            idempotency_key="1" * 64,
        )
        result = FactoryService(
            self.store, snapshot_broker=TrustedSnapshotBroker()
        ).finalize_execution(
            execution.lease,
            packet_digest=execution.packet_digest,
            actor=WORKER,
            idempotency_key="2" * 64,
        )
        self.assertEqual(
            (
                result.terminal_stage,
                result.terminal_proposal_digest,
                result.m4_status,
                result.failure_class,
                result.failure_reason,
            ),
            (
                "failed",
                terminal.idempotency_key,
                "needs_human",
                "validation",
                "invalid output",
            ),
        )
        self.assertEqual(self.store.get_task(task.task_id).status.value, "needs_human")
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT r.released_at IS NOT NULL,a.released_at IS NOT NULL,
                w.body,w.m4_status,w.failure_class,w.failure_reason,
                trim(w.terminal_proposal_digest),w.terminal_proposal_kind
                FROM factory.runs r JOIN factory.capacity_allocations a USING(run_id)
                JOIN factory.workspace_results w USING(run_id) WHERE r.run_id=%s""",
                (execution.lease.run_id,),
            )
            released, capacity_released, body, status, failure, reason, digest, kind = (
                cursor.fetchone()
            )
            self.assertEqual(
                (released, capacity_released, status, failure, reason, digest, kind),
                (
                    True,
                    True,
                    "needs_human",
                    "validation",
                    "invalid output",
                    terminal.idempotency_key,
                    "terminal",
                ),
            )
            self.assertEqual(body, result.to_dict())
            cursor.execute(
                "UPDATE factory.workspace_results SET exact_head_sha=%s WHERE run_id=%s",
                ("0" * 40, execution.lease.run_id),
            )
        with self.assertRaises(StoreError):
            self.store.workspace_result(task.task_id, result.workspace_result_digest)

    def test_terminal_composite_persists_and_replays_all_outcomes_with_one_finalization(self):
        import psycopg

        variants = (
            (
                "completed",
                "run.completed",
                {"summary": "complete"},
                "ready_for_human",
                "completed",
                None,
                None,
            ),
            (
                "failed",
                "run.failed",
                {"failure_class": "validation", "diagnostic": "invalid output"},
                "needs_human",
                "failed",
                "validation",
                "invalid output",
            ),
            (
                "needs_human",
                "run.needs_human",
                {"reason": "review required", "diagnostic": "bounded detail"},
                "needs_human",
                "failed",
                None,
                "review required",
            ),
        )
        for index, (
            terminal_stage,
            event_type,
            payload,
            m4_status,
            run_state,
            failure_class,
            failure_reason,
        ) in enumerate(variants):
            with self.subTest(event_type=event_type):
                task, execution = self.claim_execution(
                    f"terminal-composite-{index}",
                    capabilities=(
                        ["structured_output", "usage"]
                        if terminal_stage == "completed"
                        else ["structured_output"]
                    ),
                )
                if terminal_stage == "completed":
                    usage_payload = {
                        "provider_call_id": f"terminal-composite-call-{index}",
                        "price_table_digest": "d" * 64,
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "reasoning_tokens": 0,
                        "cost_usd_micros": 25,
                        "output_bytes": 20,
                    }
                    self.service.commit_execution_proposal(
                        execution.lease,
                        packet_digest=execution.packet_digest,
                        sequence=1,
                        event_type="usage.reported",
                        payload=usage_payload,
                        actor=WORKER,
                        idempotency_key=canonical_digest(
                            {"terminal-composite-usage-proposal": index}
                        ),
                    )
                    self.service.observe_usage(
                        execution.lease,
                        provider_call_id=usage_payload["provider_call_id"],
                        price_table_digest=usage_payload["price_table_digest"],
                        cost_usd_micros=usage_payload["cost_usd_micros"],
                        token_units=(
                            usage_payload["input_tokens"]
                            + usage_payload["output_tokens"]
                            + usage_payload["reasoning_tokens"]
                        ),
                        output_bytes=usage_payload["output_bytes"],
                        actor=WORKER,
                        idempotency_key=canonical_digest(
                            {"terminal-composite-usage": index}
                        ),
                    )
                    self.service.advance_execution(
                        execution.lease,
                        packet_digest=execution.packet_digest,
                        stage=ExecutionStage.RUNNING,
                        actor=WORKER,
                        idempotency_key=canonical_digest(
                            {"terminal-composite-stage": index, "stage": "running"}
                        ),
                    )
                    self.service.advance_execution(
                        execution.lease,
                        packet_digest=execution.packet_digest,
                        stage=ExecutionStage.COLLECTING,
                        actor=WORKER,
                        idempotency_key=canonical_digest(
                            {"terminal-composite-stage": index, "stage": "collecting"}
                        ),
                    )
                outer_key = canonical_digest({"terminal-composite": index})
                broker = RecordingSnapshotBroker(
                    unavailable_once=terminal_stage == "failed",
                    rendezvous=2 if terminal_stage == "completed" else 1,
                )
                service = FactoryService(self.store, snapshot_broker=broker)
                arguments = {
                    "packet_digest": execution.packet_digest,
                    "sequence": 2 if terminal_stage == "completed" else 1,
                    "event_type": event_type,
                    "payload": payload,
                    "actor": WORKER,
                    "idempotency_key": outer_key,
                    "correlation_id": f"terminal-composite-{index}",
                }
                if terminal_stage == "completed":
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        futures = (
                            executor.submit(
                                service.commit_terminal_and_finalize,
                                execution.lease,
                                **arguments,
                            ),
                            executor.submit(
                                service.commit_terminal_and_finalize,
                                execution.lease,
                                **arguments,
                            ),
                        )
                        completions = tuple(
                            future.result(timeout=10) for future in futures
                        )
                    self.assertEqual(completions[0], completions[1])
                    completion = completions[0]
                    expected_broker_calls = 2
                else:
                    if terminal_stage == "failed":
                        with self.assertRaises(SnapshotBrokerUnavailable):
                            service.commit_terminal_and_finalize(
                                execution.lease, **arguments
                            )
                        with psycopg.connect(
                            DATABASE_URL
                        ) as connection, connection.cursor() as cursor:
                            cursor.execute(
                                "SELECT count(*) FROM factory.execution_proposals "
                                "WHERE run_id=%s AND proposal_kind='terminal'",
                                (execution.lease.run_id,),
                            )
                            self.assertEqual(cursor.fetchone()[0], 1)
                            cursor.execute(
                                "SELECT count(*) FROM factory.workspace_results WHERE run_id=%s",
                                (execution.lease.run_id,),
                            )
                            self.assertEqual(cursor.fetchone()[0], 0)
                        calls = broker.calls
                        with self.assertRaises(StoreError):
                            service.commit_terminal_and_finalize(
                                replace(
                                    execution.lease,
                                    fence=execution.lease.fence + 1,
                                ),
                                **arguments,
                            )
                        foreign = Actor(
                            "foreign-worker",
                            "worker",
                            WORKER.scopes,
                            WORKER.repositories,
                        )
                        with self.assertRaises(AuthorizationError):
                            service.commit_terminal_and_finalize(
                                execution.lease,
                                **{**arguments, "actor": foreign},
                            )
                        self.assertEqual(broker.calls, calls)
                    completion = service.commit_terminal_and_finalize(
                        execution.lease, **arguments
                    )
                    expected_broker_calls = 2 if terminal_stage == "failed" else 1
                replay = service.commit_terminal_and_finalize(
                    execution.lease, **arguments
                )
                self.assertEqual(replay, completion)
                self.assertEqual(broker.calls, expected_broker_calls)
                self.assertEqual(
                    (
                        completion.proposal.terminal_type,
                        completion.result.terminal_stage,
                        completion.result.m4_status,
                        completion.result.failure_class,
                        completion.result.failure_reason,
                    ),
                    (
                        event_type,
                        terminal_stage,
                        m4_status,
                        failure_class,
                        failure_reason,
                    ),
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
                with psycopg.connect(
                    DATABASE_URL
                ) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        """SELECT task.state,run.state,run.released_at IS NOT NULL,
                        allocation.released_at IS NOT NULL,manifest.stage,
                        result.terminal_stage,result.m4_status,result.failure_class,
                        result.failure_reason,
                        (SELECT count(*) FROM factory.execution_proposals proposal
                         WHERE proposal.run_id=run.run_id AND proposal.proposal_kind='terminal'),
                        (SELECT count(*) FROM factory.workspace_results workspace
                         WHERE workspace.run_id=run.run_id),
                        (SELECT count(*) FROM factory.execution_stage_events event
                         WHERE event.manifest_digest=manifest.manifest_digest
                           AND event.stage=%s),
                        (SELECT count(*) FROM factory.task_events event
                         WHERE event.task_id=task.task_id AND event.action='released'),
                        (SELECT count(*) FROM factory.audit_log audit
                         WHERE audit.run_id=run.run_id
                           AND audit.action='execution_finalize')
                        FROM factory.tasks task
                        JOIN factory.runs run ON run.task_id=task.task_id
                        JOIN factory.capacity_allocations allocation
                          ON allocation.run_id=run.run_id
                        JOIN factory.execution_manifests manifest
                          ON manifest.run_id=run.run_id
                        JOIN factory.workspace_results result ON result.run_id=run.run_id
                        WHERE task.task_id=%s""",
                        (terminal_stage, task.task_id),
                    )
                    self.assertEqual(
                        cursor.fetchone(),
                        (
                            m4_status,
                            run_state,
                            True,
                            True,
                            terminal_stage,
                            terminal_stage,
                            m4_status,
                            failure_class,
                            failure_reason,
                            1,
                            1,
                            1,
                            1,
                            1,
                        ),
                    )
                    cursor.execute(
                        "SELECT idempotency_key,action FROM factory.command_results "
                        "WHERE idempotency_key=ANY(%s) ORDER BY idempotency_key",
                        ([outer_key, proposal_key, finalize_key],),
                    )
                    self.assertEqual(
                        {row[0].strip(): row[1] for row in cursor.fetchall()},
                        {
                            outer_key: "execution_terminal_composite",
                            proposal_key: "execution_propose",
                            finalize_key: "execution_finalize",
                        },
                    )

    def test_terminal_outer_command_key_blocks_cross_route_reuse_and_corrupt_marker(self):
        import psycopg

        task, execution = self.claim_execution(
            "terminal-outer-note-first", capabilities=["notes", "structured_output"]
        )
        outer_key = canonical_digest({"terminal-outer-key": "note-first"})
        self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="note.proposed",
            payload={"note_type": "finding", "body": "safe", "evidence": []},
            actor=WORKER,
            idempotency_key=outer_key,
        )
        broker = RecordingSnapshotBroker()
        service = FactoryService(self.store, snapshot_broker=broker)
        with self.assertRaises(StoreError):
            service.commit_terminal_and_finalize(
                execution.lease,
                packet_digest=execution.packet_digest,
                sequence=2,
                event_type="run.completed",
                payload={"summary": "complete"},
                actor=WORKER,
                idempotency_key=outer_key,
            )
        self.assertEqual(broker.calls, 0)
        self.service.cancel(
            task.task_id,
            reason="release note-first collision fixture",
            idempotency_key=canonical_digest(
                {"terminal-outer-key": "note-first-cleanup"}
            ),
            actor=OPERATOR,
            now=NOW,
        )

        _task, execution = self.claim_execution(
            "terminal-outer-terminal-first", capabilities=["notes", "structured_output"]
        )
        outer_key = canonical_digest({"terminal-outer-key": "terminal-first"})
        unavailable = RecordingSnapshotBroker(unavailable_once=True)
        service = FactoryService(self.store, snapshot_broker=unavailable)
        terminal_arguments = {
            "packet_digest": execution.packet_digest,
            "sequence": 1,
            "event_type": "run.failed",
            "payload": {"failure_class": "validation", "diagnostic": "invalid"},
            "actor": WORKER,
            "idempotency_key": outer_key,
        }
        with self.assertRaises(SnapshotBrokerUnavailable):
            service.commit_terminal_and_finalize(execution.lease, **terminal_arguments)
        with self.assertRaises(StoreError):
            self.service.commit_execution_proposal(
                execution.lease,
                packet_digest=execution.packet_digest,
                sequence=2,
                event_type="note.proposed",
                payload={"note_type": "finding", "body": "late", "evidence": []},
                actor=WORKER,
                idempotency_key=outer_key,
            )
        self.assertEqual(unavailable.calls, 1)
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.command_results SET result='{}'::jsonb "
                "WHERE idempotency_key=%s",
                (outer_key,),
            )
        with self.assertRaises(IntegrityError):
            service.commit_terminal_and_finalize(execution.lease, **terminal_arguments)
        self.assertEqual(unavailable.calls, 1)

    def test_terminal_outer_marker_stale_fence_is_counted_before_any_mutation(self):
        import psycopg

        task, execution = self.claim_execution(
            "terminal-outer-stale-fence", capabilities=["structured_output"]
        )
        broker = RecordingSnapshotBroker()
        service = FactoryService(self.store, snapshot_broker=broker)
        outer_key = canonical_digest({"terminal-outer-key": "stale-fence"})
        with psycopg.connect(DATABASE_URL) as connection:
            before_fence = connection.execute(
                "SELECT fence_rejected FROM factory.metric_counters"
            ).fetchone()[0]
        try:
            with self.assertRaises(FenceError):
                service.commit_terminal_and_finalize(
                    replace(
                        execution.lease,
                        fence=execution.lease.fence + 1,
                    ),
                    packet_digest=execution.packet_digest,
                    sequence=1,
                    event_type="run.completed",
                    payload={"summary": "complete"},
                    actor=WORKER,
                    idempotency_key=outer_key,
                    correlation_id="terminal-outer-stale-fence",
                )
            with psycopg.connect(
                DATABASE_URL
            ) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT fence_rejected,
                    (SELECT count(*) FROM factory.command_results
                     WHERE idempotency_key=%s),
                    (SELECT count(*) FROM factory.execution_proposals WHERE run_id=%s),
                    (SELECT count(*) FROM factory.workspace_results WHERE run_id=%s)
                    FROM factory.metric_counters""",
                    (outer_key, execution.lease.run_id, execution.lease.run_id),
                )
                self.assertEqual(
                    cursor.fetchone(), (before_fence + 1, 0, 0, 0)
                )
            self.assertEqual(broker.calls, 0)
        finally:
            self.service.cancel(
                task.task_id,
                reason="release stale-fence fixture",
                idempotency_key=canonical_digest(
                    {"terminal-outer-key": "stale-fence-cleanup"}
                ),
                actor=OPERATOR,
                now=NOW,
            )

    def test_direct_forged_finalize_and_injected_audit_failure_roll_back_everything(self):
        import psycopg
        from unittest.mock import patch

        task, execution = self.claim_execution(
            "forged-finalize-rollback", capabilities=["structured_output"]
        )
        terminal = self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="run.failed",
            payload={"failure_class": "validation", "diagnostic": "invalid output"},
            actor=WORKER,
        )
        snapshot = TrustedSnapshotBroker().snapshot(
            self.store.workspace_snapshot_request(
                execution.lease, execution.packet_digest
            )
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT trim(manifest_digest) FROM factory.execution_manifests "
                "WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            manifest_digest = cursor.fetchone()[0]
        result = WorkspaceResultV1.from_facts(
            {
                "contract_version": 1,
                "task_id": execution.lease.task_id,
                "run_id": execution.lease.run_id,
                "task_packet_digest": execution.packet_digest,
                "run_manifest_digest": manifest_digest,
                "exact_head_sha": snapshot.result_head_sha,
                "workspace_snapshot_digest": snapshot.workspace_snapshot_digest,
                "terminal_stage": "failed",
                "terminal_proposal_digest": terminal.idempotency_key,
                "artifact_manifest_digest": workspace_evidence_digest("artifacts", []),
                "note_manifest_digest": workspace_evidence_digest("notes", []),
                "usage_evidence_digest": workspace_evidence_digest("usage", []),
                "diagnostics_digest": workspace_evidence_digest("diagnostics", []),
                "m4_status": "needs_human",
                "failure_class": "validation",
                "failure_reason": "invalid output",
            }
        )
        forged_result = result.to_dict()
        forged_result["artifact_manifest_digest"] = "f" * 64
        forged_result["workspace_result_digest"] = "e" * 64
        unknown_snapshot = snapshot.to_dict()
        unknown_snapshot["unknown"] = 1
        missing_result = result.to_dict()
        missing_result.pop("m4_status")
        null_result = result.to_dict()
        null_result["workspace_result_digest"] = None
        fractional_snapshot = snapshot.to_dict()
        fractional_snapshot["diff_lines"] = 1.5
        direct_cases = (
            (snapshot.to_dict(), forged_result, forged_result["workspace_result_digest"]),
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
                    "SELECT factory.execution_finalize_commit("
                    "%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)",
                    (
                        execution.lease.task_id,
                        execution.lease.run_id,
                        execution.lease.owner,
                        execution.lease.fence,
                        execution.lease.packet_digest,
                        execution.packet_digest,
                        direct_digest,
                        psycopg.types.json.Jsonb(direct_snapshot),
                        psycopg.types.json.Jsonb(direct_result),
                    ),
                )
                self.assertFalse(cursor.fetchone()[0])
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT t.state,r.released_at IS NULL,a.released_at IS NULL,
                at.finished_at IS NULL,m.terminal_at IS NULL,
                (SELECT count(*) FROM factory.workspace_results WHERE run_id=r.run_id),
                (SELECT count(*) FROM factory.task_events WHERE task_id=t.task_id),
                (SELECT count(*) FROM factory.audit_log WHERE task_id=t.task_id),
                (SELECT count(*) FROM factory.execution_stage_events e
                  WHERE e.manifest_digest=m.manifest_digest)
                FROM factory.tasks t JOIN factory.runs r ON r.run_id=t.current_run_id
                JOIN factory.capacity_allocations a ON a.run_id=r.run_id
                JOIN factory.attempts at ON at.run_id=r.run_id
                JOIN factory.execution_manifests m ON m.run_id=r.run_id
                WHERE t.task_id=%s""",
                (task.task_id,),
            )
            before = cursor.fetchone()
        self.assertEqual(before[:6], ("leased", True, True, True, True, 0))

        finalizer = FactoryService(self.store, snapshot_broker=TrustedSnapshotBroker())
        with patch.object(
            self.store, "_audit", side_effect=RuntimeError("injected audit failure")
        ):
            with self.assertRaisesRegex(RuntimeError, "injected audit failure"):
                finalizer.finalize_execution(
                    execution.lease,
                    packet_digest=execution.packet_digest,
                    actor=WORKER,
                )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT t.state,r.released_at IS NULL,a.released_at IS NULL,
                at.finished_at IS NULL,m.terminal_at IS NULL,
                (SELECT count(*) FROM factory.workspace_results WHERE run_id=r.run_id),
                (SELECT count(*) FROM factory.task_events WHERE task_id=t.task_id),
                (SELECT count(*) FROM factory.audit_log WHERE task_id=t.task_id),
                (SELECT count(*) FROM factory.execution_stage_events e
                  WHERE e.manifest_digest=m.manifest_digest)
                FROM factory.tasks t JOIN factory.runs r ON r.run_id=t.current_run_id
                JOIN factory.capacity_allocations a ON a.run_id=r.run_id
                JOIN factory.attempts at ON at.run_id=r.run_id
                JOIN factory.execution_manifests m ON m.run_id=r.run_id
                WHERE t.task_id=%s""",
                (task.task_id,),
            )
            self.assertEqual(cursor.fetchone(), before)

        successful = finalizer.finalize_execution(
            execution.lease,
            packet_digest=execution.packet_digest,
            actor=WORKER,
        )
        self.assertEqual(successful.workspace_result_digest, result.workspace_result_digest)
        self.assertEqual(self.store.get_task(task.task_id).status.value, "needs_human")
        self.assertEqual(
            canonical_digest({"failure": "validation"}),
            self._attempt_failure_digest(execution.lease.run_id),
        )

    @staticmethod
    def _attempt_failure_digest(run_id: str) -> str | None:
        import psycopg

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT trim(failure_digest) FROM factory.attempts WHERE run_id=%s",
                (run_id,),
            )
            return cursor.fetchone()[0]

    def test_completed_finalize_requires_exact_authoritative_usage_pair(self):
        import psycopg

        task, execution = self.claim_execution(
            "finalize-usage-binding", capabilities=["structured_output", "usage"]
        )
        self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="usage.reported",
            payload={
                "provider_call_id": "provider-call-1",
                "price_table_digest": "f" * 64,
                "input_tokens": 2,
                "output_tokens": 3,
                "reasoning_tokens": 5,
                "cost_usd_micros": 7,
                "output_bytes": 11,
            },
            actor=WORKER,
        )
        self.service.observe_usage(
            execution.lease,
            provider_call_id="provider-call-1",
            price_table_digest="f" * 64,
            cost_usd_micros=7,
            token_units=10,
            output_bytes=11,
            actor=WORKER,
        )
        self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=2,
            event_type="run.completed",
            payload={"summary": "complete"},
            actor=WORKER,
        )
        for stage in ("running", "collecting"):
            self.service.advance_execution(
                execution.lease,
                packet_digest=execution.packet_digest,
                stage=ExecutionStage(stage),
                actor=WORKER,
            )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.usage_observations SET output_bytes=12 WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        finalizer = FactoryService(self.store, snapshot_broker=TrustedSnapshotBroker())
        with self.assertRaises(StoreError):
            finalizer.finalize_execution(
                execution.lease, packet_digest=execution.packet_digest, actor=WORKER
            )
        self.assertEqual(self.store.get_task(task.task_id).status.value, "leased")
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.usage_observations SET output_bytes=11 WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        result = finalizer.finalize_execution(
            execution.lease, packet_digest=execution.packet_digest, actor=WORKER
        )
        self.assertEqual(result.m4_status, "ready_for_human")
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT trim(idempotency_key) FROM factory.execution_proposals "
                "WHERE run_id=%s AND proposal_kind='usage'",
                (execution.lease.run_id,),
            )
            usage_digest = cursor.fetchone()[0]
        self.assertEqual(
            result.usage_evidence_digest,
            workspace_evidence_digest("usage", [usage_digest]),
        )

    def test_finalize_requires_exact_consumed_artifact_attestation(self):
        import psycopg

        task, execution = self.claim_execution(
            "finalize-artifact-binding",
            capabilities=["artifacts", "structured_output"],
        )
        service = FactoryService(
            self.store,
            artifact_broker=TrustedArtifactBroker(),
            artifact_attestation_store=self.attestor_store(),
        )
        artifact = service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="artifact.proposed",
            payload={
                "artifact_class": "patch",
                "path": "factory/src/result.patch",
                "sha256": "e" * 64,
                "size_bytes": 12,
                "media_type": "text/x-diff",
            },
            actor=WORKER,
        )
        service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=2,
            event_type="run.needs_human",
            payload={"reason": "review", "diagnostic": "artifact ready"},
            actor=WORKER,
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.execution_artifact_attestations SET path=%s "
                "WHERE run_id=%s",
                ("factory/src/other.patch", execution.lease.run_id),
            )
        finalizer = FactoryService(self.store, snapshot_broker=TrustedSnapshotBroker())
        with self.assertRaises(StoreError):
            finalizer.finalize_execution(
                execution.lease,
                packet_digest=execution.packet_digest,
                actor=WORKER,
            )
        self.assertEqual(self.store.get_task(task.task_id).status.value, "leased")
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM factory.workspace_results WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute(
                "UPDATE factory.execution_artifact_attestations SET path=%s "
                "WHERE run_id=%s",
                ("factory/src/result.patch", execution.lease.run_id),
            )
        result = finalizer.finalize_execution(
            execution.lease,
            packet_digest=execution.packet_digest,
            actor=WORKER,
        )
        self.assertEqual(result.m4_status, "needs_human")
        self.assertEqual(
            result.artifact_manifest_digest,
            workspace_evidence_digest("artifacts", [artifact.idempotency_key]),
        )

    def test_needs_human_finalize_preserves_reservation_as_accounting_blocked(self):
        import psycopg

        task, execution = self.claim_execution(
            "finalize-needs-human-reservation", capabilities=["structured_output"]
        )
        reservation_id = self.service.reserve_budget(
            execution.lease,
            cost_usd_micros=11,
            token_units=13,
            wall_seconds=17,
            reason_digest="a" * 64,
            idempotency_key="b" * 64,
            actor=WORKER,
        )
        self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="run.needs_human",
            payload={
                "reason": "operator review",
                "diagnostic": "reservation needs reconciliation",
            },
            actor=WORKER,
        )
        result = FactoryService(
            self.store, snapshot_broker=TrustedSnapshotBroker()
        ).finalize_execution(
            execution.lease,
            packet_digest=execution.packet_digest,
            actor=WORKER,
        )
        self.assertEqual(result.m4_status, "needs_human")
        self.assertIsNone(
            self.service.claim(
                owner=WORKER.actor_id,
                role=RunRole.WRITER,
                repositories=(task.repository_id,),
                lease_seconds=60,
                actor=WORKER,
                now=NOW,
            )
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT t.state,t.accounting_blocked,t.cost_reserved_micros,
                t.tokens_reserved,t.wall_reserved_seconds,t.current_run_id,t.current_fence,
                r.released_at IS NOT NULL,a.released_at IS NOT NULL,
                reservation.released_at IS NULL
                FROM factory.tasks t JOIN factory.runs r ON r.task_id=t.task_id
                JOIN factory.capacity_allocations a ON a.run_id=r.run_id
                JOIN factory.budget_reservations reservation ON reservation.run_id=r.run_id
                WHERE t.task_id=%s AND reservation.reservation_id=%s""",
                (task.task_id, reservation_id),
            )
            self.assertEqual(
                cursor.fetchone(),
                (
                    "needs_human",
                    True,
                    11,
                    13,
                    17,
                    None,
                    None,
                    True,
                    True,
                    True,
                ),
            )

    def test_retryable_finalize_uses_persisted_zero_one_two_retry_limits(self):
        import psycopg

        for retry_limit, expected_statuses in (
            (0, ("dead",)),
            (1, ("retry", "dead")),
            (2, ("retry", "retry", "dead")),
        ):
            with self.subTest(infrastructure_retries=retry_limit):
                payload = valid_intake()
                payload["request_id"] = f"request-finalize-retries-{retry_limit}"
                payload["source_id"] = f"finalize-retries-{retry_limit}"
                payload["m0_authority"]["observed_at"] = NOW.isoformat()
                payload["limits"]["infrastructure_retries"] = retry_limit
                task = self.service.intake(payload, actor=OPERATOR, now=NOW).task
                selection = self.selection(capabilities=["structured_output"])
                execution_service = FactoryService(
                    self.store, execution_registry=trusted_registry(selection)
                )
                finalizer = FactoryService(
                    self.store, snapshot_broker=TrustedSnapshotBroker()
                )
                run_ids = []
                for attempt_no, expected_status in enumerate(expected_statuses, 1):
                    execution = execution_service.claim_execution(
                        owner=WORKER.actor_id,
                        role=RunRole.WRITER,
                        repositories=(task.repository_id,),
                        lease_seconds=60,
                        selection=selection,
                        actor=WORKER,
                        now=NOW,
                        idempotency_key=f"{retry_limit}{attempt_no}" * 32,
                    )
                    self.assertIsNotNone(execution)
                    run_ids.append(execution.lease.run_id)
                    self.service.commit_execution_proposal(
                        execution.lease,
                        packet_digest=execution.packet_digest,
                        sequence=1,
                        event_type="run.failed",
                        payload={
                            "failure_class": "database_unavailable",
                            "diagnostic": f"attempt {attempt_no}",
                        },
                        actor=WORKER,
                    )
                    result = finalizer.finalize_execution(
                        execution.lease,
                        packet_digest=execution.packet_digest,
                        actor=WORKER,
                    )
                    self.assertEqual(result.m4_status, expected_status)
                    self.assertEqual(
                        result.failure_class, "database_unavailable"
                    )
                    self.assertEqual(
                        self.store.get_task(task.task_id).status.value,
                        expected_status,
                    )
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        """SELECT count(*),bool_and(at.attempt_no BETWEEN 1 AND %s),
                        bool_and(at.failure_class='database_unavailable'),
                        bool_and(at.finished_at IS NOT NULL),
                        bool_and(r.released_at IS NOT NULL),
                        bool_and(a.released_at IS NOT NULL)
                        FROM factory.attempts at JOIN factory.runs r USING(run_id)
                        JOIN factory.capacity_allocations a USING(run_id)
                        WHERE at.task_id=%s""",
                        (len(expected_statuses), task.task_id),
                    )
                    self.assertEqual(
                        cursor.fetchone(),
                        (len(expected_statuses), True, True, True, True, True),
                    )
                    cursor.execute(
                        """SELECT current_run_id,current_fence,infrastructure_retries,
                        (SELECT count(*) FROM factory.workspace_results w
                          WHERE w.task_id=t.task_id)
                        FROM factory.tasks t WHERE task_id=%s""",
                        (task.task_id,),
                    )
                    self.assertEqual(
                        cursor.fetchone(),
                        (None, None, retry_limit, len(run_ids)),
                    )

    def test_failed_finalize_forces_accounting_recovery_for_block_or_residual_counters(self):
        import psycopg

        cases = (
            (0, True, 0, 0, 0),
            (0, False, 1, 0, 0),
            (1, False, 0, 1, 0),
            (2, False, 0, 0, 1),
        )
        for case_no, (
            retry_limit,
            blocked,
            reserved_cost,
            reserved_tokens,
            reserved_wall,
        ) in enumerate(cases, 1):
            with self.subTest(
                infrastructure_retries=retry_limit,
                blocked=blocked,
                reserved=(reserved_cost, reserved_tokens, reserved_wall),
            ):
                payload = valid_intake()
                payload["request_id"] = f"request-finalize-accounting-{case_no}"
                payload["source_id"] = f"finalize-accounting-recovery-{case_no}"
                payload["m0_authority"]["observed_at"] = NOW.isoformat()
                payload["limits"]["infrastructure_retries"] = retry_limit
                task = self.service.intake(payload, actor=OPERATOR, now=NOW).task
                selection = self.selection(capabilities=["structured_output"])
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
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        """UPDATE factory.tasks SET accounting_blocked=%s,
                        cost_reserved_micros=%s,tokens_reserved=%s,wall_reserved_seconds=%s
                        WHERE task_id=%s""",
                        (
                            blocked,
                            reserved_cost,
                            reserved_tokens,
                            reserved_wall,
                            task.task_id,
                        ),
                    )
                self.service.commit_execution_proposal(
                    execution.lease,
                    packet_digest=execution.packet_digest,
                    sequence=1,
                    event_type="run.failed",
                    payload={
                        "failure_class": "database_unavailable",
                        "diagnostic": "residual accounting",
                    },
                    actor=WORKER,
                )
                result = FactoryService(
                    self.store, snapshot_broker=TrustedSnapshotBroker()
                ).finalize_execution(
                    execution.lease,
                    packet_digest=execution.packet_digest,
                    actor=WORKER,
                )
                self.assertEqual(result.m4_status, "needs_human")
                self.assertIsNone(
                    self.service.claim(
                        owner=WORKER.actor_id,
                        role=RunRole.WRITER,
                        repositories=(task.repository_id,),
                        lease_seconds=60,
                        actor=WORKER,
                        now=NOW,
                    )
                )
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        """SELECT t.state,t.accounting_blocked,t.cost_reserved_micros,
                        t.tokens_reserved,t.wall_reserved_seconds,t.current_run_id,
                        r.released_at IS NOT NULL,a.released_at IS NOT NULL,
                        (SELECT count(*) FROM factory.budget_reservations reservation
                          WHERE reservation.task_id=t.task_id
                            AND reservation.released_at IS NULL)
                        FROM factory.tasks t JOIN factory.runs r ON r.task_id=t.task_id
                        JOIN factory.capacity_allocations a ON a.run_id=r.run_id
                        WHERE t.task_id=%s""",
                        (task.task_id,),
                    )
                    self.assertEqual(
                        cursor.fetchone(),
                        (
                            "needs_human",
                            True,
                            reserved_cost,
                            reserved_tokens,
                            reserved_wall,
                            None,
                            True,
                            True,
                            0,
                        ),
                    )

    def test_legacy_release_residual_accounting_cannot_create_unclaimable_retry(self):
        import psycopg

        task = self.submit("legacy-release-residual-accounting")
        grant = self.service.claim(
            owner=WORKER.actor_id,
            role=RunRole.WRITER,
            repositories=(task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.tasks SET tokens_reserved=1 WHERE task_id=%s",
                (task.task_id,),
            )
        self.assertEqual(
            self.service.release(
                grant,
                outcome="worker_lost",
                actor=WORKER,
                now=NOW,
            ).value,
            "needs_human",
        )
        self.assertIsNone(
            self.service.claim(
                owner=WORKER.actor_id,
                role=RunRole.WRITER,
                repositories=(task.repository_id,),
                lease_seconds=60,
                actor=WORKER,
                now=NOW,
            )
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT state,accounting_blocked,tokens_reserved,current_run_id,
                (SELECT count(*) FROM factory.budget_reservations reservation
                  WHERE reservation.task_id=t.task_id AND reservation.released_at IS NULL)
                FROM factory.tasks t WHERE task_id=%s""",
                (task.task_id,),
            )
            self.assertEqual(cursor.fetchone(), ("needs_human", True, 1, None, 0))

    def test_supported_usage_overflow_cannot_finalize_an_unclaimable_retry(self):
        import psycopg

        task, execution = self.claim_execution(
            "finalize-supported-accounting-overflow",
            capabilities=["structured_output"],
        )
        self.service.reserve_budget(
            execution.lease,
            cost_usd_micros=1,
            token_units=1,
            wall_seconds=1,
            reason_digest="a" * 64,
            idempotency_key="b" * 64,
            actor=WORKER,
        )
        with self.assertRaisesRegex(StoreError, "accounting blocked"):
            self.service.observe_usage(
                execution.lease,
                provider_call_id="overflow-call",
                price_table_digest="c" * 64,
                cost_usd_micros=25_000_001,
                token_units=0,
                output_bytes=0,
                actor=WORKER,
                idempotency_key="d" * 64,
            )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT accounting_blocked,cost_reserved_micros,tokens_reserved,
                wall_reserved_seconds,
                (SELECT count(*) FROM factory.budget_reservations reservation
                  WHERE reservation.task_id=t.task_id AND reservation.released_at IS NULL)
                FROM factory.tasks t WHERE task_id=%s""",
                (task.task_id,),
            )
            self.assertEqual(cursor.fetchone(), (True, 0, 0, 0, 0))
        self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="run.failed",
            payload={
                "failure_class": "database_unavailable",
                "diagnostic": "after accounting overflow",
            },
            actor=WORKER,
        )
        result = FactoryService(
            self.store, snapshot_broker=TrustedSnapshotBroker()
        ).finalize_execution(
            execution.lease,
            packet_digest=execution.packet_digest,
            actor=WORKER,
        )
        self.assertEqual(result.m4_status, "needs_human")
        self.assertEqual(self.store.get_task(task.task_id).status.value, "needs_human")
        self.assertIsNone(
            self.service.claim(
                owner=WORKER.actor_id,
                role=RunRole.WRITER,
                repositories=(task.repository_id,),
                lease_seconds=60,
                actor=WORKER,
                now=NOW,
            )
        )

    def test_normal_service_path_persists_all_four_closed_proposals(self):
        _task, execution = self.claim_execution(
            "service-four-kind-proposals",
            capabilities=["artifacts", "notes", "structured_output", "usage"],
        )
        service = FactoryService(
            self.store,
            artifact_broker=TrustedArtifactBroker(),
            artifact_attestation_store=self.attestor_store(),
        )
        payloads = (
            (1, "note.proposed", {"note_type": "finding", "body": "bounded", "evidence": []}),
            (
                2,
                "artifact.proposed",
                {
                    "artifact_class": "patch",
                    "path": "factory/src/result.patch",
                    "sha256": "e" * 64,
                    "size_bytes": 12,
                    "media_type": "text/x-diff",
                },
            ),
            (
                3,
                "usage.reported",
                {
                    "provider_call_id": "provider-call-1",
                    "price_table_digest": "f" * 64,
                    "input_tokens": 2,
                    "output_tokens": 3,
                    "reasoning_tokens": 5,
                    "cost_usd_micros": 7,
                    "output_bytes": 11,
                },
            ),
            (4, "run.completed", {"summary": "complete"}),
        )
        proposals = []
        for sequence, event_type, payload in payloads:
            proposals.append(
                service.commit_execution_proposal(
                    execution.lease,
                    packet_digest=execution.packet_digest,
                    sequence=sequence,
                    event_type=event_type,
                    payload=payload,
                    actor=WORKER,
                    idempotency_key=str(sequence) * 64,
                )
            )
        replay = service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=4,
            event_type="run.completed",
            payload={"summary": "complete"},
            actor=WORKER,
            idempotency_key="4" * 64,
        )
        self.assertEqual(replay, proposals[-1])
        self.assertEqual(
            [type(proposal).__name__ for proposal in proposals],
            ["NoteProposal", "ArtifactProposal", "UsageProposal", "TerminalProposal"],
        )

    def test_direct_store_cannot_diverge_any_event_payload_from_persisted_proposal(self):
        import psycopg

        _task, execution = self.claim_execution(
            "direct-store-semantic-binding",
            capabilities=["artifacts", "notes", "structured_output", "usage"],
        )
        artifact_values = {
            "artifact_class": "patch",
            "path": "factory/src/result.patch",
            "sha256": "e" * 64,
            "size_bytes": 12,
            "media_type": "text/x-diff",
        }
        cases = (
            (
                "note.proposed",
                {"note_type": "finding", "body": "honest", "evidence": []},
                {"body": "forged"},
            ),
            ("artifact.proposed", artifact_values, {"path": "factory/src/forged.patch"}),
            (
                "usage.reported",
                {
                    "provider_call_id": "provider-call-1",
                    "price_table_digest": "f" * 64,
                    "input_tokens": 2,
                    "output_tokens": 3,
                    "reasoning_tokens": 5,
                    "cost_usd_micros": 7,
                    "output_bytes": 11,
                },
                {"output_bytes": 12},
            ),
            ("run.completed", {"summary": "honest"}, {"summary": "forged"}),
        )
        forged_command_keys = []
        for sequence, (event_type, payload, forged_fields) in enumerate(cases, 1):
            event = CanonicalEvent.from_payload(
                task_id=execution.lease.task_id,
                run_id=execution.lease.run_id,
                packet_digest=execution.packet_digest,
                sequence=sequence,
                event_type=event_type,
                payload=payload,
            )
            context = self.store.proposal_context(
                execution.lease, execution.packet_digest
            )
            attestation_digest = None
            if event_type == "artifact.proposed":
                attestation = self.artifact_attestation(
                    execution, sequence, artifact_values
                )
                self.attestor_store().record_artifact_attestation(attestation)
                attestation_digest = attestation.artifact_attestation_digest
            honest = ProposalBroker().accept(
                event,
                context,
                owner=execution.lease.owner,
                fence=execution.lease.fence,
                artifact_attestation_digest=attestation_digest,
            )
            forged = replace(honest, **forged_fields, idempotency_key="0" * 64)
            forged = replace(forged, idempotency_key=proposal_idempotency_key(forged))
            forged_command_key = format(sequence + 9, "x") * 64
            forged_command_keys.append(forged_command_key)
            with self.subTest(event_type=event_type), self.assertRaises(StoreError):
                self.store.commit_execution_proposal(
                    execution.lease,
                    forged,
                    WORKER,
                    event=event,
                    idempotency_key=forged_command_key,
                )
            self.store.commit_execution_proposal(
                execution.lease,
                honest,
                WORKER,
                event=event,
                idempotency_key=format(sequence, "x") * 64,
            )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM factory.execution_proposals WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone()[0], 4)
            cursor.execute(
                """SELECT count(*) FROM factory.command_results
                WHERE action='execution_propose' AND idempotency_key=ANY(%s)""",
                (forged_command_keys,),
            )
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_exact_proposal_replay_survives_finalize_but_changed_or_new_commands_do_not(self):
        _task, execution = self.claim_execution(
            "proposal-replay-live-authority", capabilities=["structured_output"]
        )
        event = CanonicalEvent.from_payload(
            task_id=execution.lease.task_id,
            run_id=execution.lease.run_id,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="run.needs_human",
            payload={"reason": "review", "diagnostic": "bounded"},
        )
        proposal = self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type=event.event_type,
            payload=dict(event.payload),
            actor=WORKER,
            idempotency_key="b" * 64,
        )
        self.assertEqual(
            self.store.execution_proposal_replay(
                execution.lease, event, WORKER, idempotency_key="b" * 64
            ),
            proposal,
        )
        FactoryService(
            self.store, snapshot_broker=TrustedSnapshotBroker()
        ).finalize_execution(
            execution.lease,
            packet_digest=execution.packet_digest,
            actor=WORKER,
            idempotency_key="c" * 64,
        )
        self.assertEqual(
            self.store.execution_proposal_replay(
                execution.lease, event, WORKER, idempotency_key="b" * 64
            ),
            proposal,
        )
        changed = CanonicalEvent.from_payload(
            task_id=execution.lease.task_id,
            run_id=execution.lease.run_id,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="run.needs_human",
            payload={"reason": "changed", "diagnostic": "bounded"},
        )
        with self.assertRaisesRegex(StoreError, "idempotency key reused"):
            self.store.execution_proposal_replay(
                execution.lease, changed, WORKER, idempotency_key="b" * 64
            )
        with self.assertRaises(FenceError):
            self.store.execution_proposal_replay(
                execution.lease, event, WORKER, idempotency_key="e" * 64
            )

    def test_concurrent_exact_artifact_replays_after_winner_finalizes_without_side_effects(self):
        _task, execution = self.claim_execution(
            "proposal-replay-finalize-barrier",
            capabilities=["artifacts", "structured_output"],
        )
        payload = {
            "artifact_class": "patch",
            "path": "factory/src/race.patch",
            "sha256": "e" * 64,
            "size_bytes": 12,
            "media_type": "text/x-diff",
        }
        replay_checked = threading.Event()
        resume = threading.Event()
        racing_store = self.runtime_store()
        original_replay = racing_store.execution_proposal_replay
        replay_calls = []

        def pausing_replay(*args, **kwargs):
            result = original_replay(*args, **kwargs)
            replay_calls.append(result)
            if len(replay_calls) == 1:
                self.assertIsNone(result)
                replay_checked.set()
                if not resume.wait(timeout=5):
                    raise AssertionError("proposal replay barrier timed out")
            return result

        racing_store.execution_proposal_replay = pausing_replay

        class ForbiddenArtifactBroker:
            calls = 0

            def attest_artifact(self, _request):
                self.calls += 1
                raise AssertionError("exact replay called artifact broker")

        class ForbiddenAttestationStore:
            calls = 0

            def record_artifact_attestation(self, _attestation):
                self.calls += 1
                raise AssertionError("exact replay persisted another attestation")

        loser_broker = ForbiddenArtifactBroker()
        loser_attestor = ForbiddenAttestationStore()
        loser = FactoryService(
            racing_store,
            artifact_broker=loser_broker,
            artifact_attestation_store=loser_attestor,
        )
        winner_store = self.runtime_store()
        winner = FactoryService(
            winner_store,
            artifact_broker=TrustedArtifactBroker(),
            artifact_attestation_store=self.attestor_store(),
        )

        def losing_request():
            return loser.commit_execution_proposal(
                execution.lease,
                packet_digest=execution.packet_digest,
                sequence=1,
                event_type="artifact.proposed",
                payload=payload,
                actor=WORKER,
                idempotency_key="a" * 64,
            )

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(losing_request)
            self.assertTrue(replay_checked.wait(timeout=5))
            try:
                artifact = winner.commit_execution_proposal(
                    execution.lease,
                    packet_digest=execution.packet_digest,
                    sequence=1,
                    event_type="artifact.proposed",
                    payload=payload,
                    actor=WORKER,
                    idempotency_key="a" * 64,
                )
                winner.commit_execution_proposal(
                    execution.lease,
                    packet_digest=execution.packet_digest,
                    sequence=2,
                    event_type="run.needs_human",
                    payload={"reason": "review", "diagnostic": "artifact race"},
                    actor=WORKER,
                    idempotency_key="b" * 64,
                )
                FactoryService(
                    winner_store, snapshot_broker=TrustedSnapshotBroker()
                ).finalize_execution(
                    execution.lease,
                    packet_digest=execution.packet_digest,
                    actor=WORKER,
                    idempotency_key="c" * 64,
                )
            finally:
                resume.set()
            self.assertEqual(future.result(timeout=5), artifact)
        self.assertEqual((loser_broker.calls, loser_attestor.calls), (0, 0))
        self.assertEqual(len(replay_calls), 2)
        self.assertEqual(replay_calls[-1], artifact)

    def test_concurrent_artifact_read_verification_is_deterministic_and_persists_once(self):
        _task, execution = self.claim_execution(
            "artifact-read-verification-barrier",
            capabilities=["artifacts", "structured_output"],
        )
        payload = {
            "artifact_class": "patch",
            "path": "factory/src/deterministic.patch",
            "sha256": "d" * 64,
            "size_bytes": 18,
            "media_type": "text/x-diff",
        }
        loser_in_broker = threading.Event()
        resume = threading.Event()

        class PausingDeterministicArtifactBroker:
            def __init__(self):
                self.calls = []
                self._lock = threading.Lock()

            def attest_artifact(self, request):
                with self._lock:
                    self.calls.append(request.request_digest)
                    call_number = len(self.calls)
                if call_number == 1:
                    loser_in_broker.set()
                    if not resume.wait(timeout=5):
                        raise AssertionError("artifact broker barrier timed out")
                return ArtifactAttestationV1.from_facts(
                    {
                        "contract_version": 1,
                        **request.to_dict(),
                        "source": "trusted_workspace_broker",
                    }
                )

        broker = PausingDeterministicArtifactBroker()
        loser = FactoryService(
            self.runtime_store(),
            artifact_broker=broker,
            artifact_attestation_store=self.attestor_store(),
        )
        winner_store = self.runtime_store()
        winner = FactoryService(
            winner_store,
            artifact_broker=broker,
            artifact_attestation_store=self.attestor_store(),
        )

        def losing_request():
            return loser.commit_execution_proposal(
                execution.lease,
                packet_digest=execution.packet_digest,
                sequence=1,
                event_type="artifact.proposed",
                payload=payload,
                actor=WORKER,
                idempotency_key="1" * 64,
            )

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(losing_request)
            self.assertTrue(loser_in_broker.wait(timeout=5))
            try:
                artifact = winner.commit_execution_proposal(
                    execution.lease,
                    packet_digest=execution.packet_digest,
                    sequence=1,
                    event_type="artifact.proposed",
                    payload=payload,
                    actor=WORKER,
                    idempotency_key="1" * 64,
                )
                winner.commit_execution_proposal(
                    execution.lease,
                    packet_digest=execution.packet_digest,
                    sequence=2,
                    event_type="run.needs_human",
                    payload={"reason": "review", "diagnostic": "deterministic read"},
                    actor=WORKER,
                    idempotency_key="2" * 64,
                )
                FactoryService(
                    winner_store, snapshot_broker=TrustedSnapshotBroker()
                ).finalize_execution(
                    execution.lease,
                    packet_digest=execution.packet_digest,
                    actor=WORKER,
                    idempotency_key="3" * 64,
                )
            finally:
                resume.set()
            self.assertEqual(future.result(timeout=5), artifact)

        self.assertEqual(len(broker.calls), 2)
        self.assertEqual(len(set(broker.calls)), 1)
        import psycopg

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                (SELECT count(*) FROM factory.execution_artifact_attestations
                  WHERE run_id=%s),
                (SELECT count(*) FROM factory.execution_proposals
                  WHERE run_id=%s AND proposal_kind='artifact'),
                (SELECT count(*) FROM factory.command_results
                  WHERE idempotency_key=%s AND action='execution_propose')""",
                (execution.lease.run_id, execution.lease.run_id, "1" * 64),
            )
            self.assertEqual(cursor.fetchone(), (1, 1, 1))

    def test_proposal_replay_binds_actor_before_connect_and_exact_replay_survives_expiry(self):
        import psycopg

        _task, execution = self.claim_execution(
            "proposal-replay-expired-authority", capabilities=["notes"]
        )
        payload = {"note_type": "finding", "body": "bounded", "evidence": []}
        event = CanonicalEvent.from_payload(
            task_id=execution.lease.task_id,
            run_id=execution.lease.run_id,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="note.proposed",
            payload=payload,
        )
        proposal = self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type=event.event_type,
            payload=payload,
            actor=WORKER,
            idempotency_key="d" * 64,
        )
        original_connect = self.store._connect
        calls = []

        def forbidden_connect(**_kwargs):
            calls.append("connect")
            raise AssertionError("actor/grant binding connected")

        self.store._connect = forbidden_connect
        try:
            with self.assertRaisesRegex(StoreError, "bound worker actor"):
                self.store.execution_proposal_replay(
                    execution.lease,
                    event,
                    replace(WORKER, kind="operator"),
                    idempotency_key="d" * 64,
                )
            with self.assertRaisesRegex(StoreError, "bound worker actor"):
                self.store.commit_execution_proposal(
                    execution.lease,
                    proposal,
                    replace(WORKER, kind="operator"),
                    event=event,
                    idempotency_key="d" * 64,
                )
        finally:
            self.store._connect = original_connect
        self.assertEqual(calls, [])
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' "
                "WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        self.assertEqual(
            self.store.execution_proposal_replay(
                execution.lease, event, WORKER, idempotency_key="d" * 64
            ),
            proposal,
        )

    def test_corrupt_persisted_packet_limit_is_internal_integrity_not_fence(self):
        import psycopg

        _task, execution = self.claim_execution(
            "proposal-corrupt-packet-limit", capabilities=["notes"]
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT fence_rejected FROM factory.metric_counters")
            before_fence = cursor.fetchone()[0]
            cursor.execute(
                """UPDATE factory.execution_packets
                SET body=jsonb_set(body,'{limits,max_events}','\"not-a-number\"'::jsonb)
                WHERE run_id=%s""",
                (execution.lease.run_id,),
            )
        with self.assertRaisesRegex(IntegrityError, "database integrity violation"):
            self.service.commit_execution_proposal(
                execution.lease,
                packet_digest=execution.packet_digest,
                sequence=1,
                event_type="note.proposed",
                payload={"note_type": "finding", "body": "bounded", "evidence": []},
                actor=WORKER,
                idempotency_key="f" * 64,
            )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT fence_rejected,
                (SELECT count(*) FROM factory.execution_proposals WHERE run_id=%s),
                (SELECT count(*) FROM factory.command_results WHERE idempotency_key=%s)
                FROM factory.metric_counters""",
                (execution.lease.run_id, "f" * 64),
            )
            self.assertEqual(cursor.fetchone(), (before_fence, 0, 0))


    def test_recovery_claim_atomically_orphans_expired_execution_and_denies_late_work(self):
        import psycopg

        task, execution = self.claim_execution(
            "recovery-atomic-expired", capabilities=["notes", "structured_output"]
        )
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' "
                "WHERE run_id=%s",
                (execution.lease.run_id,),
            )

        import psycopg

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SET LOCAL transaction_timeout='3s'; "
                "SET LOCAL statement_timeout='5s'; SET LOCAL lock_timeout='500ms'"
            )
            cursor.execute(
                "SELECT factory.execution_recovery_candidates(%s,%s,%s)",
                (10, None, None),
            )
            page = cursor.fetchone()[0]
            candidates = page["candidates"]
            self.assertEqual(len(candidates), 1)
            self.assertEqual(
                tuple(
                    candidates[0][name].strip()
                    for name in (
                        "task_id",
                        "run_id",
                        "manifest_digest",
                        "workspace_handle",
                    )
                ),
                (
                    task.task_id,
                    execution.lease.run_id,
                    execution.manifest_digest,
                    execution.workspace_handle,
                ),
            )
            cursor.execute(
                "SELECT factory.execution_recovery_claim(%s,%s,%s,%s,%s,%s)",
                (
                    task.task_id,
                    execution.lease.run_id,
                    execution.manifest_digest,
                    execution.workspace_handle,
                    candidates[0]["updated_at"],
                    30,
                ),
            )
            self.assertIsNone(cursor.fetchone()[0])

        candidate = ExecutionRecoveryCandidate(
            task.task_id,
            execution.lease.run_id,
            execution.manifest_digest,
            execution.workspace_handle,
            datetime.fromisoformat(
                candidates[0]["updated_at"].replace("Z", "+00:00")
            ),
        )
        claim = self.store.claim_execution_recovery(candidate, OPERATOR)
        self.assertIsNotNone(claim)
        self.assertEqual(claim.transition, "orphaned")
        self.assertEqual(claim.claim_fence, 1)
        self.assertEqual(claim.candidate, candidate)
        self.assertIsNone(self.store.claim_execution_recovery(candidate, OPERATOR))

        with self.store._transaction() as cursor:
            cursor.execute(
                "SELECT factory.execution_advance(%s,%s,%s,%s,%s,%s,%s)",
                (
                    task.task_id,
                    execution.lease.run_id,
                    execution.lease.owner,
                    execution.lease.fence,
                    execution.lease.packet_digest,
                    execution.packet_digest,
                    "running",
                ),
            )
            self.assertFalse(cursor.fetchone()[0])
            cursor.execute(
                "SELECT factory.execution_finalize_context(%s,%s,%s,%s,%s,%s)",
                (
                    task.task_id,
                    execution.lease.run_id,
                    execution.lease.owner,
                    execution.lease.fence,
                    execution.lease.packet_digest,
                    execution.packet_digest,
                ),
            )
            self.assertIsNone(cursor.fetchone()[0])

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT t.state,t.current_run_id,t.current_fence,t.repair_count,
                r.state,r.released_at IS NOT NULL,
                a.released_at IS NOT NULL,m.stage,m.terminal_at IS NOT NULL,
                (SELECT count(*) FROM factory.execution_stage_events e
                 WHERE e.manifest_digest=m.manifest_digest AND e.stage='orphaned'),
                (SELECT count(*) FROM factory.execution_recovery_jobs j
                 WHERE j.run_id=r.run_id AND j.status='claimed'),
                (SELECT count(*) FROM factory.execution_proposals p WHERE p.run_id=r.run_id),
                (SELECT count(*) FROM factory.workspace_results w WHERE w.run_id=r.run_id)
                FROM factory.tasks t
                JOIN factory.runs r ON r.task_id=t.task_id
                JOIN factory.capacity_allocations a ON a.run_id=r.run_id
                JOIN factory.execution_manifests m ON m.run_id=r.run_id
                WHERE t.task_id=%s""",
                (task.task_id,),
            )
            row = cursor.fetchone()
            self.assertEqual(row[:4], ("retry", None, None, 1))
            self.assertEqual(row[4], "expired")
            self.assertEqual(row[5:], (True, True, "orphaned", True, 1, 1, 0, 0))
            cursor.execute(
                """SELECT attempt.failure_class,attempt.failure_code,
                attempt.failure_digest IS NOT NULL,attempt.finished_at IS NOT NULL,
                (SELECT count(*) FROM factory.task_events event
                 WHERE event.task_id=attempt.task_id AND event.action='released'),
                (SELECT count(*) FROM factory.audit_log audit
                 WHERE audit.task_id=attempt.task_id AND audit.run_id=attempt.run_id
                   AND audit.action='release' AND audit.reason='retry')
                FROM factory.attempts attempt WHERE attempt.run_id=%s""",
                (execution.lease.run_id,),
            )
            self.assertEqual(
                cursor.fetchone(), ("worker_lost", "worker_lost", True, True, 1, 1)
            )
            cursor.execute(
                "SELECT active_count FROM factory.capacity_counters "
                "WHERE scope_key='global:writer'"
            )
            self.assertEqual(cursor.fetchone()[0], 0)
        self.assertTrue(self.store.verify_audit_chain(task.task_id))

    def test_cancel_projects_execution_before_cleanup_and_first_claim_is_cancelled(self):
        task, execution = self.claim_execution(
            "recovery-cancelled", capabilities=["notes", "structured_output"]
        )
        cancelled = self.service.cancel(
            task.task_id,
            reason="operator cancellation",
            idempotency_key="8" * 64,
            actor=OPERATOR,
            now=NOW,
        )
        self.assertEqual(cancelled.status.value, "cancelled")
        candidates = self.store.execution_recovery_candidates(
            limit=10, cursor=None
        ).candidates
        self.assertEqual(len(candidates), 1)
        claim = self.store.claim_execution_recovery(candidates[0], OPERATOR)
        self.assertIsNotNone(claim)
        self.assertEqual(claim.transition, "cancelled")
        self.assertFalse(claim.advances_discovery_cursor)
        import psycopg

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT manifest.stage,manifest.terminal_at IS NOT NULL,
                job.terminal_stage,job.status,job.attempt_count,
                (SELECT count(*) FROM factory.execution_proposals proposal
                 WHERE proposal.run_id=job.run_id),
                (SELECT count(*) FROM factory.workspace_results result
                 WHERE result.run_id=job.run_id)
                FROM factory.execution_manifests manifest
                JOIN factory.execution_recovery_jobs job
                  ON job.manifest_digest=manifest.manifest_digest
                WHERE manifest.run_id=%s""",
                (execution.lease.run_id,),
            )
            self.assertEqual(
                cursor.fetchone(),
                ("cancelled", True, "cancelled", "claimed", 1, 0, 0),
            )

    def test_supersede_projection_is_atomic_then_queues_exact_cleanup(self):
        import psycopg

        task, execution = self.claim_execution(
            "recovery-superseded", capabilities=["notes", "structured_output"]
        )
        replacement = valid_intake()
        replacement["request_id"] = "request-recovery-superseded-replacement"
        replacement["source_id"] = "recovery-superseded"
        replacement["source_digest"] = "8" * 64
        replacement["m0_authority"]["observed_at"] = NOW.isoformat()
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                """CREATE FUNCTION factory.test_supersede_recovery_failure()
                RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
                  RAISE EXCEPTION 'injected supersede recovery failure';
                END $$"""
            )
            connection.execute(
                """CREATE TRIGGER test_supersede_recovery_failure
                BEFORE INSERT ON factory.execution_recovery_jobs
                FOR EACH ROW EXECUTE FUNCTION factory.test_supersede_recovery_failure()"""
            )
        try:
            with self.assertRaisesRegex(Exception, "injected supersede recovery failure"):
                self.service.intake(replacement, actor=OPERATOR, now=NOW)
        finally:
            with psycopg.connect(DATABASE_URL) as connection:
                connection.execute(
                    "DROP TRIGGER test_supersede_recovery_failure "
                    "ON factory.execution_recovery_jobs"
                )
                connection.execute(
                    "DROP FUNCTION factory.test_supersede_recovery_failure()"
                )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT task.state,run.state,run.released_at IS NULL,
                allocation.released_at IS NULL,manifest.stage,
                manifest.terminal_at IS NULL,
                (SELECT count(*) FROM factory.execution_recovery_jobs),
                (SELECT count(*) FROM factory.tasks candidate
                 WHERE candidate.repository_id=task.repository_id
                   AND candidate.source_type=task.source_type
                   AND candidate.source_id=task.source_id)
                FROM factory.tasks task JOIN factory.runs run ON run.task_id=task.task_id
                JOIN factory.capacity_allocations allocation ON allocation.run_id=run.run_id
                JOIN factory.execution_manifests manifest ON manifest.run_id=run.run_id
                WHERE task.task_id=%s""",
                (task.task_id,),
            )
            self.assertEqual(
                cursor.fetchone(),
                ("leased", "leased", True, True, "prepared", True, 0, 1),
            )

        created = self.service.intake(replacement, actor=OPERATOR, now=NOW)
        self.assertTrue(created.created)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT old.state,new.state,run.state,
                run.released_at IS NOT NULL,allocation.released_at IS NOT NULL,
                manifest.stage,manifest.terminal_at IS NOT NULL,
                job.terminal_stage,job.status,
                (SELECT count(*) FROM factory.execution_proposals proposal
                 WHERE proposal.run_id=run.run_id),
                (SELECT count(*) FROM factory.workspace_results result
                 WHERE result.run_id=run.run_id)
                FROM factory.tasks old JOIN factory.runs run ON run.task_id=old.task_id
                JOIN factory.capacity_allocations allocation ON allocation.run_id=run.run_id
                JOIN factory.execution_manifests manifest ON manifest.run_id=run.run_id
                JOIN factory.execution_recovery_jobs job ON job.run_id=run.run_id
                JOIN factory.tasks new ON new.task_id=%s WHERE old.task_id=%s""",
                (created.task.task_id, task.task_id),
            )
            self.assertEqual(
                cursor.fetchone(),
                (
                    "superseded",
                    "queued",
                    "released",
                    True,
                    True,
                    "cancelled",
                    True,
                    "cancelled",
                    "pending",
                    0,
                    0,
                ),
            )

    def test_recovery_candidate_hints_cannot_redirect_authoritative_cleanup(self):
        import psycopg

        task, execution = self.claim_execution(
            "recovery-forged-hints", capabilities=["notes", "structured_output"]
        )
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' "
                "WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        candidate = next(
            value
            for value in self.store.execution_recovery_candidates(
                limit=10, cursor=None
            ).candidates
            if value.run_id == execution.lease.run_id
        )
        forged_values = (
            replace(candidate, task_id=str(uuid.uuid4())),
            replace(candidate, run_id=str(uuid.uuid4())),
            replace(candidate, manifest_digest="f" * 64),
            replace(candidate, workspace_handle="workspace:" + "0" * 64),
            replace(candidate, updated_at=candidate.updated_at + timedelta(seconds=1)),
        )
        for forged in forged_values:
            with self.subTest(forged=forged):
                self.assertIsNone(
                    self.store.claim_execution_recovery(forged, OPERATOR)
                )
        with self.assertRaises(IntegrityError):
            self.store.claim_execution_recovery(
                replace(candidate, source="cleanup_retry"), OPERATOR
            )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT task.state,run.state,run.released_at IS NULL,
                allocation.released_at IS NULL,manifest.terminal_at IS NULL,
                (SELECT count(*) FROM factory.execution_recovery_jobs)
                FROM factory.tasks task JOIN factory.runs run ON run.task_id=task.task_id
                JOIN factory.capacity_allocations allocation ON allocation.run_id=run.run_id
                JOIN factory.execution_manifests manifest ON manifest.run_id=run.run_id
                WHERE task.task_id=%s""",
                (task.task_id,),
            )
            self.assertEqual(
                cursor.fetchone(), ("leased", "leased", True, True, True, 0)
            )

    def test_cleanup_outcomes_require_the_complete_authoritative_claim(self):
        import psycopg

        _task, execution = self.claim_execution(
            "recovery-forged-outcome", capabilities=["notes", "structured_output"]
        )
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.runs SET "
                "lease_expires_at=clock_timestamp()-interval '1 second' "
                "WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        candidate = next(
            value
            for value in self.store.execution_recovery_candidates(
                limit=10, cursor=None
            ).candidates
            if value.run_id == execution.lease.run_id
        )
        claim = self.store.claim_execution_recovery(candidate, OPERATOR)
        self.assertIsNotNone(claim)
        forged_claims = (
            replace(claim, candidate=replace(candidate, task_id=str(uuid.uuid4()))),
            replace(claim, candidate=replace(candidate, run_id=str(uuid.uuid4()))),
            replace(
                claim,
                candidate=replace(candidate, manifest_digest="f" * 64),
            ),
            replace(
                claim,
                candidate=replace(
                    candidate, workspace_handle="workspace:" + "0" * 64
                ),
            ),
            replace(
                claim,
                candidate=replace(
                    candidate,
                    updated_at=candidate.updated_at + timedelta(seconds=1),
                ),
            ),
            replace(
                claim,
                candidate=replace(candidate, source="cleanup_retry"),
            ),
            replace(claim, transition="cleanup_retry"),
            replace(claim, advances_discovery_cursor=False),
        )
        for forged in forged_claims:
            for recorder in (
                self.store.record_execution_cleanup_success,
                self.store.record_execution_cleanup_failure,
            ):
                with self.subTest(
                    forged=forged, recorder=recorder.__name__
                ), self.assertRaises(FenceError):
                    recorder(forged)
        self.store.record_execution_cleanup_failure(claim)
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.execution_recovery_jobs SET "
                "next_claim_at=clock_timestamp()-interval '1 second' "
                "WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        retry_candidate = next(
            value
            for value in self.store.execution_recovery_candidates(
                limit=10, cursor=None
            ).candidates
            if value.run_id == execution.lease.run_id
        )
        with self.assertRaises(IntegrityError):
            self.store.claim_execution_recovery(
                replace(retry_candidate, source="fresh"), OPERATOR
            )
        retry_claim = self.store.claim_execution_recovery(retry_candidate, OPERATOR)
        self.assertIsNotNone(retry_claim)
        forged_retry = replace(
            retry_claim,
            candidate=replace(retry_candidate, source="fresh"),
        )
        for recorder in (
            self.store.record_execution_cleanup_success,
            self.store.record_execution_cleanup_failure,
        ):
            with self.subTest(
                retry_recorder=recorder.__name__
            ), self.assertRaises(FenceError):
                recorder(forged_retry)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT job.status,job.claim_fence,job.attempt_count,
                (SELECT array_agg(outcome.claim_fence ORDER BY outcome.claim_fence)
                 FROM factory.execution_recovery_outcomes outcome
                 WHERE outcome.run_id=job.run_id),
                metrics.cleanup_succeeded,metrics.cleanup_failed
                FROM factory.execution_recovery_jobs job
                CROSS JOIN factory.execution_metric_counters metrics
                WHERE job.run_id=%s""",
                (execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone(), ("claimed", 2, 2, [1], 0, 1))

    def test_recovery_job_insert_failure_rolls_back_canonical_release_atomically(self):
        import psycopg

        task, execution = self.claim_execution(
            "recovery-rollback", capabilities=["notes", "structured_output"]
        )
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' "
                "WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            connection.execute(
                """CREATE FUNCTION factory.test_recovery_job_failure() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN
                  RAISE EXCEPTION 'injected recovery job failure';
                END $$"""
            )
            connection.execute(
                """CREATE TRIGGER test_recovery_job_failure
                BEFORE INSERT ON factory.execution_recovery_jobs
                FOR EACH ROW EXECUTE FUNCTION factory.test_recovery_job_failure()"""
            )
        candidate = next(
            value
            for value in self.store.execution_recovery_candidates(
                limit=10, cursor=None
            ).candidates
            if value.run_id == execution.lease.run_id
        )
        try:
            with self.assertRaisesRegex(Exception, "injected recovery job failure"):
                self.store.claim_execution_recovery(candidate, OPERATOR)
        finally:
            with psycopg.connect(DATABASE_URL) as connection:
                connection.execute(
                    "DROP TRIGGER test_recovery_job_failure ON factory.execution_recovery_jobs"
                )
                connection.execute("DROP FUNCTION factory.test_recovery_job_failure()")
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT task.state,task.current_run_id=run.run_id,
                task.current_fence=run.fence,task.repair_count,
                run.state,run.released_at IS NULL,allocation.released_at IS NULL,
                attempt.finished_at IS NULL,manifest.stage,manifest.terminal_at IS NULL,
                (SELECT count(*) FROM factory.execution_recovery_jobs),
                (SELECT count(*) FROM factory.task_events event
                 WHERE event.task_id=task.task_id AND event.action='released'),
                (SELECT count(*) FROM factory.audit_log audit
                 WHERE audit.task_id=task.task_id AND audit.action='release'),
                metrics.recovery_claimed,metrics.recovery_orphaned,
                metrics.stage_orphaned
                FROM factory.tasks task JOIN factory.runs run ON run.task_id=task.task_id
                JOIN factory.capacity_allocations allocation ON allocation.run_id=run.run_id
                JOIN factory.attempts attempt ON attempt.run_id=run.run_id
                JOIN factory.execution_manifests manifest ON manifest.run_id=run.run_id
                CROSS JOIN factory.execution_metric_counters metrics
                WHERE task.task_id=%s""",
                (task.task_id,),
            )
            self.assertEqual(
                cursor.fetchone(),
                (
                    "leased",
                    True,
                    True,
                    0,
                    "leased",
                    True,
                    True,
                    True,
                    "prepared",
                    True,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                ),
            )

    def test_recovery_failure_history_survives_reclaim_and_success(self):
        import psycopg

        _task, execution = self.claim_execution(
            "recovery-history", capabilities=["notes", "structured_output"]
        )
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' "
                "WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        candidate = next(
            value
            for value in self.store.execution_recovery_candidates(
                limit=10, cursor=None
            ).candidates
            if value.run_id == execution.lease.run_id
        )
        first = self.store.claim_execution_recovery(candidate, OPERATOR)
        self.assertIsNotNone(first)
        self.store.record_execution_cleanup_failure(first)
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.execution_recovery_jobs "
                "SET next_claim_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        restarted_store = self.runtime_store()
        retry_candidate = next(
            value
            for value in restarted_store.execution_recovery_candidates(
                limit=10, cursor=None
            ).candidates
            if value.run_id == execution.lease.run_id
        )
        second = restarted_store.claim_execution_recovery(retry_candidate, OPERATOR)
        self.assertIsNotNone(second)
        self.assertEqual(second.transition, "cleanup_retry")
        self.assertEqual(second.claim_fence, 2)
        self.assertFalse(second.advances_discovery_cursor)
        with self.assertRaises(FenceError):
            restarted_store.record_execution_cleanup_success(first)
        restarted_store.record_execution_cleanup_success(second)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT status,attempt_count,failure_count,last_failure_code,
                last_failed_at IS NOT NULL,completed_at IS NOT NULL
                FROM factory.execution_recovery_jobs WHERE run_id=%s""",
                (execution.lease.run_id,),
            )
            self.assertEqual(
                cursor.fetchone(),
                ("succeeded", 2, 1, "workspace_cleanup_failed", True, True),
            )
            cursor.execute(
                """SELECT claim.claim_fence,claim.transition,outcome.outcome,
                outcome.failure_code
                FROM factory.execution_recovery_claims claim
                JOIN factory.execution_recovery_outcomes outcome
                  USING(run_id,claim_fence)
                WHERE claim.run_id=%s ORDER BY claim.claim_fence""",
                (execution.lease.run_id,),
            )
            self.assertEqual(
                cursor.fetchall(),
                [
                    (1, "orphaned", "failed", "workspace_cleanup_failed"),
                    (2, "cleanup_retry", "succeeded", None),
                ],
            )
            cursor.execute(
                """SELECT recovery_claimed,recovery_orphaned,cleanup_failed,
                cleanup_succeeded FROM factory.execution_metric_counters"""
            )
            self.assertEqual(cursor.fetchone(), (2, 1, 1, 1))
        self.assertFalse(
            any(
                value.run_id == execution.lease.run_id
                for value in restarted_store.execution_recovery_candidates(
                    limit=10, cursor=None
                ).candidates
            )
        )

    def test_expired_cleanup_claim_is_at_least_once_but_durably_fenced(self):
        import psycopg

        _task, execution = self.claim_execution(
            "recovery-claim-ttl", capabilities=["notes", "structured_output"]
        )
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' "
                "WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        candidate = next(
            value
            for value in self.store.execution_recovery_candidates(
                limit=10, cursor=None
            ).candidates
            if value.run_id == execution.lease.run_id
        )
        first = self.store.claim_execution_recovery(candidate, OPERATOR)
        self.assertIsNotNone(first)
        delegate = FakeWorkspaceBroker()
        handle = WorkspaceHandle(
            candidate.task_id, candidate.run_id, candidate.workspace_handle
        )
        delegate.register(
            handle,
            WorkspacePolicy(("factory/src",), ("read", "write"), ("LANG",), ()),
        )
        entered = threading.Event()
        resume = threading.Event()

        class DelayedFirstBroker:
            def __init__(self):
                self.calls = 0
                self.lock = threading.Lock()

            def release(self, target, *, timeout_seconds):
                with self.lock:
                    self.calls += 1
                    call = self.calls
                if call == 1:
                    entered.set()
                    if not resume.wait(timeout=3):
                        raise RuntimeError("cleanup overlap barrier timed out")
                return delegate.release(target, timeout_seconds=timeout_seconds)

        broker = DelayedFirstBroker()

        with ThreadPoolExecutor(max_workers=2) as executor:
            older = executor.submit(
                broker.release, handle, timeout_seconds=5
            )
            self.assertTrue(entered.wait(timeout=3))
            with psycopg.connect(DATABASE_URL) as connection:
                connection.execute(
                    "UPDATE factory.execution_recovery_jobs SET "
                    "claim_expires_at=clock_timestamp()-interval '1 second',"
                    "next_claim_at=clock_timestamp()-interval '1 second' "
                    "WHERE run_id=%s",
                    (execution.lease.run_id,),
                )
            retry = next(
                value
                for value in self.store.execution_recovery_candidates(
                    limit=10, cursor=None
                ).candidates
                if value.run_id == execution.lease.run_id
            )
            second = self.store.claim_execution_recovery(retry, OPERATOR)
            self.assertIsNotNone(second)
            self.assertEqual(second.claim_fence, 2)
            newer_outcome = broker.release(handle, timeout_seconds=5)
            resume.set()
            older_outcome = older.result(timeout=3)
        self.assertEqual(newer_outcome, WorkspaceReleaseOutcome("released"))
        self.assertEqual(
            older_outcome, WorkspaceReleaseOutcome("already_absent")
        )
        self.store.record_execution_cleanup_success(second)
        with self.assertRaises(FenceError):
            self.store.record_execution_cleanup_success(first)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT job.status,job.claim_fence,job.attempt_count,
                (SELECT array_agg(claim.claim_fence ORDER BY claim.claim_fence)
                 FROM factory.execution_recovery_claims claim
                 WHERE claim.run_id=job.run_id),
                (SELECT array_agg(outcome.claim_fence ORDER BY outcome.claim_fence)
                 FROM factory.execution_recovery_outcomes outcome
                 WHERE outcome.run_id=job.run_id),
                (SELECT count(*) FROM factory.execution_recovery_outcomes outcome
                 WHERE outcome.run_id=job.run_id AND outcome.outcome='succeeded')
                FROM factory.execution_recovery_jobs job WHERE job.run_id=%s""",
                (execution.lease.run_id,),
            )
            self.assertEqual(
                cursor.fetchone(), ("succeeded", 2, 2, [1, 2], [2], 1)
            )

    def test_recovery_page_is_work_conserving_and_fair_in_both_directions(self):
        import psycopg

        retry_runs = []
        for index in range(10):
            task, execution = self.claim_execution(
                f"recovery-page-retry-{index}",
                capabilities=["notes", "structured_output"],
            )
            self.service.cancel(
                task.task_id,
                reason="page fixture",
                idempotency_key=f"{index + 1:064x}",
                actor=OPERATOR,
                now=NOW,
            )
            retry_runs.append(execution.lease.run_id)
        fresh_runs = []
        for index in range(10):
            _task, execution = self.claim_execution(
                f"recovery-page-fresh-{index}",
                capabilities=["notes", "structured_output"],
            )
            self.service.release(
                execution.lease,
                outcome=FailureClass.WORKER_LOST,
                actor=WORKER,
                now=NOW,
            )
            fresh_runs.append(execution.lease.run_id)

        balanced = self.store.execution_recovery_candidates(limit=10, cursor=None)
        self.assertEqual(len(balanced.candidates), 10)
        self.assertEqual(
            [value.source for value in balanced.candidates[:2]],
            ["fresh", "cleanup_retry"],
        )
        self.assertEqual(
            {source: sum(value.source == source for value in balanced.candidates)
             for source in ("fresh", "cleanup_retry")},
            {"fresh": 5, "cleanup_retry": 5},
        )
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                """UPDATE factory.execution_recovery_jobs SET status='succeeded',
                next_claim_at=NULL,completed_at=clock_timestamp()
                WHERE run_id=ANY(%s) AND run_id<>%s""",
                (retry_runs, retry_runs[0]),
            )
        retry_short = self.store.execution_recovery_candidates(limit=10, cursor=None)
        self.assertEqual(len(retry_short.candidates), 10)
        self.assertEqual(
            sum(value.source == "cleanup_retry" for value in retry_short.candidates),
            1,
        )
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                """UPDATE factory.execution_recovery_jobs SET status='pending',
                next_claim_at=clock_timestamp(),completed_at=NULL
                WHERE run_id=ANY(%s)""",
                (retry_runs,),
            )
            connection.execute(
                """UPDATE factory.execution_manifests SET stage='cancelled',
                terminal_at=clock_timestamp(),updated_at=clock_timestamp()
                WHERE run_id=ANY(%s) AND run_id<>%s""",
                (fresh_runs, fresh_runs[0]),
            )
        fresh_short = self.store.execution_recovery_candidates(limit=10, cursor=None)
        self.assertEqual(len(fresh_short.candidates), 10)
        self.assertEqual(
            sum(value.source == "fresh" for value in fresh_short.candidates), 1
        )

    def test_recovery_raw_page_caps_at_100_then_empty_page_wraps(self):
        runs = []
        for index in range(101):
            _task, execution = self.claim_execution(
                f"recovery-raw-page-{index}",
                capabilities=["notes", "structured_output"],
            )
            self.service.release(
                execution.lease,
                outcome=FailureClass.WORKER_LOST,
                actor=WORKER,
                now=NOW,
            )
            runs.append(execution.lease.run_id)
        first = self.store.execution_recovery_candidates(limit=100, cursor=None)
        self.assertEqual((len(first.candidates), first.exhausted), (100, False))
        self.assertEqual(
            {value.source for value in first.candidates}, {"fresh"}
        )
        second = self.store.execution_recovery_candidates(
            limit=100, cursor=first.scanned_through
        )
        self.assertEqual((len(second.candidates), second.exhausted), (1, True))
        self.assertEqual(
            {value.run_id for value in first.candidates + second.candidates},
            set(runs),
        )
        empty = self.store.execution_recovery_candidates(
            limit=100, cursor=second.scanned_through
        )
        self.assertEqual((empty.candidates, empty.scanned_through, empty.exhausted),
                         ((), None, True))
        wrapped = self.store.execution_recovery_candidates(limit=100, cursor=None)
        self.assertEqual(
            {value.run_id for value in wrapped.candidates},
            {value.run_id for value in first.candidates},
        )

    def test_recovery_cursor_advances_over_healthy_prefix_then_revisits_expiry(self):
        import psycopg

        executions = []
        selection = self.selection(capabilities=["cancellation"])
        selection["capability_policy"]["allowed_tools"] = ["read_file"]
        selection["capability_policy"]["artifact_classes"] = ["report"]
        execution_service = FactoryService(
            self.store, execution_registry=trusted_registry(selection)
        )
        for index in range(3):
            task = self.submit(f"recovery-healthy-prefix-{index}")
            execution = execution_service.claim_execution(
                owner=WORKER.actor_id,
                role=RunRole.READER,
                repositories=(task.repository_id,),
                lease_seconds=60,
                selection=selection,
                actor=WORKER,
                now=NOW,
            )
            self.assertIsNotNone(execution)
            executions.append(execution)
        stale = executions[-1]
        self.service.release(
            stale.lease,
            outcome=FailureClass.WORKER_LOST,
            actor=WORKER,
            now=NOW,
        )
        broker = FakeWorkspaceBroker()
        for execution in (stale, executions[0]):
            broker.register(
                WorkspaceHandle(
                    execution.lease.task_id,
                    execution.lease.run_id,
                    execution.workspace_handle,
                ),
                WorkspacePolicy(
                    ("factory/src",), ("read", "write"), ("LANG",), ()
                ),
            )
        recovery = ExecutionRecovery(self.runtime_store(), broker, OPERATOR)
        first = recovery.reconcile(limit=2)
        self.assertEqual(
            (first.candidates, first.orphaned, first.terminalize_failed),
            (2, 0, 0),
        )
        self.assertIsNotNone(first.cursor)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT count(*) FILTER (WHERE manifest.stage='prepared'
                  AND manifest.terminal_at IS NULL),
                (SELECT count(*) FROM factory.execution_recovery_jobs)
                FROM factory.execution_manifests manifest
                WHERE manifest.run_id=ANY(%s)""",
                ([value.lease.run_id for value in executions[:2]],),
            )
            self.assertEqual(cursor.fetchone(), (2, 0))
        second = recovery.reconcile(limit=2, cursor=first.cursor)
        self.assertEqual((second.candidates, second.orphaned), (1, 1))
        self.assertIsNone(second.cursor)
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.runs SET "
                "lease_expires_at=clock_timestamp()-interval '1 second' "
                "WHERE run_id=%s",
                (executions[0].lease.run_id,),
            )
        revisited = recovery.reconcile(limit=2, cursor=second.cursor)
        self.assertEqual((revisited.candidates, revisited.orphaned), (2, 1))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT manifest.run_id,manifest.stage,
                EXISTS(SELECT 1 FROM factory.execution_recovery_jobs job
                  WHERE job.run_id=manifest.run_id)
                FROM factory.execution_manifests manifest
                WHERE manifest.run_id=ANY(%s) ORDER BY manifest.run_id""",
                ([value.lease.run_id for value in executions],),
            )
            stages = {str(run_id): (stage, has_job)
                      for run_id, stage, has_job in cursor.fetchall()}
            self.assertEqual(
                stages[executions[0].lease.run_id], ("orphaned", True)
            )
            self.assertEqual(
                stages[executions[1].lease.run_id], ("prepared", False)
            )
            self.assertEqual(stages[stale.lease.run_id], ("orphaned", True))

    def test_recovery_uses_db_deadline_and_m4_retry_limits_zero_one_two(self):
        import psycopg

        for retry_limit in (0, 1, 2):
            with self.subTest(retry_limit=retry_limit):
                payload = valid_intake()
                payload["request_id"] = f"request-recovery-retry-{retry_limit}"
                payload["source_id"] = f"recovery-retry-limit-{retry_limit}"
                payload["m0_authority"]["observed_at"] = NOW.isoformat()
                payload["limits"]["infrastructure_retries"] = retry_limit
                task = self.service.intake(payload, actor=OPERATOR, now=NOW).task
                selection = self.selection(
                    capabilities=["notes", "structured_output"]
                )
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
                self.assertIsNotNone(execution)
                with psycopg.connect(DATABASE_URL) as connection:
                    connection.execute(
                        "UPDATE factory.tasks SET deadline_at=clock_timestamp()-interval '1 second' "
                        "WHERE task_id=%s",
                        (task.task_id,),
                    )
                    connection.execute(
                        "UPDATE factory.runs SET lease_expires_at=clock_timestamp()+interval '30 seconds' "
                        "WHERE run_id=%s",
                        (execution.lease.run_id,),
                    )
                candidate = next(
                    value
                    for value in self.store.execution_recovery_candidates(
                        limit=10, cursor=None
                    ).candidates
                    if value.run_id == execution.lease.run_id
                )
                claim = self.store.claim_execution_recovery(candidate, OPERATOR)
                self.assertIsNotNone(claim)
                self.store.record_execution_cleanup_success(claim)
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        """SELECT task.state,task.repair_count,run.state,
                        attempt.failure_class,attempt.failure_code
                        FROM factory.tasks task
                        JOIN factory.runs run ON run.task_id=task.task_id
                        JOIN factory.attempts attempt ON attempt.run_id=run.run_id
                        WHERE task.task_id=%s""",
                        (task.task_id,),
                    )
                    expected_state = "dead" if retry_limit == 0 else "retry"
                    self.assertEqual(
                        cursor.fetchone(),
                        (
                            expected_state,
                            1,
                            "expired",
                            "worker_lost",
                            "worker_lost",
                        ),
                    )

    def test_historical_expiry_stays_orphaned_when_new_run_is_cancelled(self):
        import psycopg

        task, first = self.claim_execution(
            "recovery-two-runs", capabilities=["notes", "structured_output"]
        )
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' "
                "WHERE run_id=%s",
                (first.lease.run_id,),
            )
        reconciled = self.store.reconcile(OPERATOR, NOW, 10, None)
        self.assertEqual(reconciled.repaired, 1)
        selection = self.selection(capabilities=["notes", "structured_output"])
        second = FactoryService(
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
        self.assertIsNotNone(second)
        self.service.cancel(
            task.task_id,
            reason="cancel second run",
            idempotency_key="9" * 64,
            actor=OPERATOR,
            now=NOW,
        )
        candidates = self.store.execution_recovery_candidates(
            limit=10, cursor=None
        ).candidates
        self.assertEqual({value.run_id for value in candidates}, {
            first.lease.run_id,
            second.lease.run_id,
        })
        claims = {
            value.run_id: self.store.claim_execution_recovery(value, OPERATOR)
            for value in candidates
        }
        self.assertEqual(claims[first.lease.run_id].transition, "orphaned")
        self.assertEqual(claims[second.lease.run_id].transition, "cancelled")
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT manifest.run_id,manifest.stage,
                count(event.stage_event_id) FILTER (
                  WHERE event.stage IN ('orphaned','cancelled')),
                count(DISTINCT job.run_id)
                FROM factory.execution_manifests manifest
                JOIN factory.execution_stage_events event
                  ON event.manifest_digest=manifest.manifest_digest
                JOIN factory.execution_recovery_jobs job ON job.run_id=manifest.run_id
                WHERE manifest.run_id=ANY(%s)
                GROUP BY manifest.run_id,manifest.stage ORDER BY manifest.run_id""",
                ([first.lease.run_id, second.lease.run_id],),
            )
            rows = cursor.fetchall()
            self.assertEqual({row[1] for row in rows}, {"orphaned", "cancelled"})
            self.assertTrue(all(row[2:] == (1, 1) for row in rows))

    def test_accounting_blocked_recovery_is_never_requeued(self):
        import psycopg

        task, execution = self.claim_execution(
            "recovery-accounting-blocked",
            capabilities=["notes", "structured_output"],
        )
        self.store.reserve_budget(
            execution.lease,
            1,
            1,
            1,
            "a" * 64,
            "b" * 64,
            WORKER,
        )
        with self.assertRaises(Exception):
            self.store.observe_usage(
                execution.lease,
                "provider-overrun",
                "c" * 64,
                25_000_001,
                1,
                0,
                WORKER,
            )
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' "
                "WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        candidate = next(
            value
            for value in self.store.execution_recovery_candidates(
                limit=10, cursor=None
            ).candidates
            if value.run_id == execution.lease.run_id
        )
        claim = self.store.claim_execution_recovery(candidate, OPERATOR)
        self.assertIsNotNone(claim)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT state,accounting_blocked,current_run_id,current_fence,
                cost_reserved_micros,tokens_reserved,wall_reserved_seconds
                FROM factory.tasks WHERE task_id=%s""",
                (task.task_id,),
            )
            self.assertEqual(
                cursor.fetchone(),
                ("needs_human", True, None, None, 0, 0, 0),
            )
        self.assertIsNone(
            self.service.claim(
                owner=WORKER.actor_id,
                role=RunRole.WRITER,
                repositories=(task.repository_id,),
                lease_seconds=60,
                actor=WORKER,
                now=NOW,
            )
        )

    def test_two_reconcilers_create_one_terminal_stage_and_cleanup_claim(self):
        import psycopg

        task, execution = self.claim_execution(
            "recovery-concurrent", capabilities=["notes", "structured_output"]
        )
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' "
                "WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        candidate = next(
            value
            for value in self.store.execution_recovery_candidates(
                limit=10, cursor=None
            ).candidates
            if value.run_id == execution.lease.run_id
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(
                executor.map(
                    lambda _index: self.runtime_store().claim_execution_recovery(
                        candidate, OPERATOR
                    ),
                    range(2),
                )
            )
        self.assertEqual(sum(value is not None for value in results), 1)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                (SELECT count(*) FROM factory.execution_stage_events event
                 WHERE event.manifest_digest=%s AND event.stage='orphaned'),
                (SELECT count(*) FROM factory.execution_recovery_jobs job
                 WHERE job.run_id=%s),
                (SELECT count(*) FROM factory.execution_recovery_claims claim
                 WHERE claim.run_id=%s),
                (SELECT count(*) FROM factory.task_events event
                 WHERE event.task_id=%s AND event.action='released'),
                (SELECT count(*) FROM factory.audit_log audit
                 WHERE audit.task_id=%s AND audit.action='release')""",
                (
                    execution.manifest_digest,
                    execution.lease.run_id,
                    execution.lease.run_id,
                    task.task_id,
                    task.task_id,
                ),
            )
            self.assertEqual(cursor.fetchone(), (1, 1, 1, 1, 1))

    def test_heartbeat_winner_revalidation_prevents_recovery_mutation(self):
        import psycopg

        task, execution = self.claim_execution(
            "recovery-heartbeat-race", capabilities=["notes", "structured_output"]
        )
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()+interval '500 milliseconds' "
                "WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        locked = threading.Event()
        resume = threading.Event()

        def heartbeat_winner():
            with self.runtime_store()._transaction() as cursor:
                cursor.execute(
                    """SELECT run.run_id FROM factory.tasks task
                    JOIN factory.runs run ON run.run_id=task.current_run_id
                    WHERE task.task_id=%s AND run.run_id=%s
                      AND run.lease_expires_at>clock_timestamp()
                    FOR UPDATE OF task,run""",
                    (task.task_id, execution.lease.run_id),
                )
                self.assertIsNotNone(cursor.fetchone())
                locked.set()
                self.assertTrue(resume.wait(timeout=3))
                cursor.execute(
                    "UPDATE factory.runs SET lease_expires_at=clock_timestamp()+interval '30 seconds' "
                    "WHERE run_id=%s",
                    (execution.lease.run_id,),
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            heartbeat = executor.submit(heartbeat_winner)
            self.assertTrue(locked.wait(timeout=3))
            time.sleep(0.7)
            candidate = next(
                value
                for value in self.store.execution_recovery_candidates(
                    limit=10, cursor=None
                ).candidates
                if value.run_id == execution.lease.run_id
            )
            recovery = executor.submit(
                self.runtime_store().claim_execution_recovery,
                candidate,
                OPERATOR,
            )
            time.sleep(0.1)
            resume.set()
            heartbeat.result(timeout=3)
            self.assertIsInstance(
                recovery.result(timeout=3), ExecutionRecoveryNotDue
            )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT task.state,run.state,run.released_at IS NULL,
                run.lease_expires_at>clock_timestamp(),allocation.released_at IS NULL,
                manifest.stage,manifest.terminal_at IS NULL,
                (SELECT count(*) FROM factory.execution_recovery_jobs),
                (SELECT count(*) FROM factory.task_events event
                 WHERE event.task_id=task.task_id AND event.action='released'),
                (SELECT count(*) FROM factory.audit_log audit
                 WHERE audit.task_id=task.task_id AND audit.action='release')
                FROM factory.tasks task JOIN factory.runs run ON run.task_id=task.task_id
                JOIN factory.capacity_allocations allocation ON allocation.run_id=run.run_id
                JOIN factory.execution_manifests manifest ON manifest.run_id=run.run_id
                WHERE task.task_id=%s""",
                (task.task_id,),
            )
            self.assertEqual(
                cursor.fetchone(),
                ("leased", "leased", True, True, True, "prepared", True, 0, 0, 0),
            )

    def test_recovery_contention_stops_fresh_cursor_but_cleanup_lane_continues(self):
        import psycopg

        retry_task, retry_execution = self.claim_execution(
            "recovery-contention-retry",
            capabilities=["notes", "structured_output"],
        )
        self.service.cancel(
            retry_task.task_id,
            reason="contention retry fixture",
            idempotency_key="d" * 64,
            actor=OPERATOR,
            now=NOW,
        )
        blocked_task, blocked_execution = self.claim_execution(
            "recovery-contention-fresh",
            capabilities=["notes", "structured_output"],
        )
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.runs SET "
                "lease_expires_at=clock_timestamp()-interval '1 second' "
                "WHERE run_id=%s",
                (blocked_execution.lease.run_id,),
            )
        page = self.store.execution_recovery_candidates(limit=2, cursor=None)
        blocked_candidate = next(
            value
            for value in page.candidates
            if value.run_id == blocked_execution.lease.run_id
        )
        retry_candidate = next(
            value
            for value in page.candidates
            if value.run_id == retry_execution.lease.run_id
        )
        broker = FakeWorkspaceBroker()
        broker.register(
            WorkspaceHandle(
                retry_candidate.task_id,
                retry_candidate.run_id,
                retry_candidate.workspace_handle,
            ),
            WorkspacePolicy(("factory/src",), ("read", "write"), ("LANG",), ()),
        )
        with psycopg.connect(DATABASE_URL) as blocker:
            blocker.execute(
                "SELECT task_id FROM factory.tasks WHERE task_id=%s FOR UPDATE",
                (blocked_task.task_id,),
            )
            started = time.monotonic()
            with self.assertRaises(StoreUnavailable):
                self.runtime_store().claim_execution_recovery(
                    blocked_candidate,
                    OPERATOR,
                    timeout_seconds=3.0,
                )
            self.assertLess(time.monotonic() - started, 3.0)
            result = ExecutionRecovery(
                self.runtime_store(), broker, OPERATOR
            ).reconcile(limit=2)
            self.assertEqual(
                (
                    result.candidates,
                    result.terminalize_failed,
                    result.cancelled,
                    result.cursor,
                ),
                (2, 1, 1, None),
            )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT task.state,run.state,allocation.released_at IS NULL,
                manifest.stage,manifest.terminal_at IS NULL,
                (SELECT count(*) FROM factory.execution_recovery_jobs job
                 WHERE job.run_id=run.run_id)
                FROM factory.tasks task
                JOIN factory.runs run ON run.run_id=task.current_run_id
                JOIN factory.capacity_allocations allocation ON allocation.run_id=run.run_id
                JOIN factory.execution_manifests manifest ON manifest.run_id=run.run_id
                WHERE task.task_id=%s""",
                (blocked_task.task_id,),
            )
            self.assertEqual(
                cursor.fetchone(),
                ("leased", "leased", True, "prepared", True, 0),
            )
            cursor.execute(
                "SELECT status,attempt_count FROM factory.execution_recovery_jobs "
                "WHERE run_id=%s",
                (retry_execution.lease.run_id,),
            )
            self.assertEqual(cursor.fetchone(), ("succeeded", 1))

    def test_cancel_and_fresh_recovery_race_is_bounded_and_single_terminal(self):
        import psycopg

        task, execution = self.claim_execution(
            "recovery-cancel-race", capabilities=["notes", "structured_output"]
        )
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.runs SET "
                "lease_expires_at=clock_timestamp()-interval '1 second' "
                "WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        candidate = next(
            value
            for value in self.store.execution_recovery_candidates(
                limit=2, cursor=None
            ).candidates
            if value.run_id == execution.lease.run_id
        )
        advisory_key = 707_017
        with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
            connection.execute(
                """CREATE FUNCTION factory.test_cancel_recovery_barrier()
                RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
                  IF NEW.stage='cancelled' THEN
                    PERFORM pg_advisory_xact_lock(707017);
                  END IF;
                  RETURN NEW;
                END $$"""
            )
            connection.execute(
                """CREATE TRIGGER test_cancel_recovery_barrier
                BEFORE UPDATE ON factory.execution_manifests
                FOR EACH ROW EXECUTE FUNCTION factory.test_cancel_recovery_barrier()"""
            )
        blocker = psycopg.connect(DATABASE_URL, autocommit=True)
        blocker.execute("SELECT pg_advisory_lock(%s)", (advisory_key,))
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                cancelled = executor.submit(
                    self.service.cancel,
                    task.task_id,
                    reason="cancel wins bounded recovery race",
                    idempotency_key="c" * 64,
                    actor=OPERATOR,
                    now=NOW,
                )
                waiting = False
                for _attempt in range(200):
                    with psycopg.connect(
                        DATABASE_URL
                    ) as observer, observer.cursor() as cursor:
                        cursor.execute(
                            "SELECT EXISTS(SELECT 1 FROM pg_locks "
                            "WHERE locktype='advisory' AND NOT granted)"
                        )
                        waiting = cursor.fetchone()[0]
                    if waiting:
                        break
                    time.sleep(0.01)
                self.assertTrue(waiting, "cancel did not reach recovery barrier")
                started = time.monotonic()
                recovery = executor.submit(
                    self.runtime_store().claim_execution_recovery,
                    candidate,
                    OPERATOR,
                    timeout_seconds=3.0,
                )
                time.sleep(0.1)
                blocker.execute("SELECT pg_advisory_unlock(%s)", (advisory_key,))
                projection = cancelled.result(timeout=3)
                race_result = recovery.result(timeout=3)
                self.assertIsNone(race_result)
                self.assertLess(time.monotonic() - started, 3.0)
                self.assertEqual(projection.status.value, "cancelled")
        finally:
            try:
                blocker.execute("SELECT pg_advisory_unlock(%s)", (advisory_key,))
            finally:
                blocker.close()
            with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
                connection.execute(
                    "DROP TRIGGER IF EXISTS test_cancel_recovery_barrier "
                    "ON factory.execution_manifests"
                )
                connection.execute(
                    "DROP FUNCTION IF EXISTS factory.test_cancel_recovery_barrier()"
                )
        replay = self.service.cancel(
            task.task_id,
            reason="cancel wins bounded recovery race",
            idempotency_key="c" * 64,
            actor=OPERATOR,
            now=NOW,
        )
        self.assertEqual(replay.status.value, "cancelled")
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT task.state,run.state,run.released_at IS NOT NULL,
                allocation.released_at IS NOT NULL,manifest.stage,
                manifest.terminal_at IS NOT NULL,
                (SELECT count(*) FROM factory.execution_stage_events event
                 WHERE event.manifest_digest=manifest.manifest_digest
                   AND event.stage='cancelled'),
                (SELECT count(*) FROM factory.execution_recovery_jobs job
                 WHERE job.run_id=run.run_id),
                (SELECT count(*) FROM factory.execution_proposals proposal
                 WHERE proposal.run_id=run.run_id),
                (SELECT count(*) FROM factory.workspace_results result
                 WHERE result.run_id=run.run_id)
                FROM factory.tasks task JOIN factory.runs run ON run.task_id=task.task_id
                JOIN factory.capacity_allocations allocation ON allocation.run_id=run.run_id
                JOIN factory.execution_manifests manifest ON manifest.run_id=run.run_id
                WHERE task.task_id=%s""",
                (task.task_id,),
            )
            self.assertEqual(
                cursor.fetchone(),
                ("cancelled", "released", True, True, "cancelled", True, 1, 1, 0, 0),
            )

    def test_recovery_definers_reject_unbounded_runtime_sessions(self):
        import psycopg

        calls = (
            "SELECT factory.execution_recovery_candidates(2,NULL,NULL)",
            "SELECT factory.execution_recovery_context(NULL::uuid,NULL::uuid,"
            "NULL::char(64),NULL::text,NULL::timestamptz)",
            "SELECT factory.execution_recovery_claim(NULL::uuid,NULL::uuid,"
            "NULL::char(64),NULL::text,NULL::timestamptz,NULL::integer)",
            "SELECT factory.execution_recovery_cancel_task(NULL::uuid)",
            "SELECT factory.execution_recovery_cleanup_succeeded("
            "NULL::uuid,NULL::uuid,NULL::char(64),NULL::text,NULL::timestamptz,"
            "NULL::text,NULL::uuid,NULL::bigint,NULL::text,NULL::boolean)",
            "SELECT factory.execution_recovery_cleanup_failed("
            "NULL::uuid,NULL::uuid,NULL::char(64),NULL::text,NULL::timestamptz,"
            "NULL::text,NULL::uuid,NULL::bigint,NULL::text,NULL::boolean)",
            "SELECT factory.read_combined_metrics_snapshot()",
        )
        for statement_timeout, lock_timeout, transaction_timeout in (
            ("0", "500ms", "3s"),
            ("6s", "500ms", "3s"),
            ("5s", "0", "3s"),
            ("5s", "501ms", "3s"),
            ("5s", "500ms", "0"),
            ("5s", "500ms", "4s"),
        ):
            with self.subTest(
                statement_timeout=statement_timeout,
                lock_timeout=lock_timeout,
                transaction_timeout=transaction_timeout,
            ), psycopg.connect(self.runtime_url, autocommit=True) as connection:
                connection.execute("SET ROLE factory_runtime")
                connection.execute(f"SET statement_timeout='{statement_timeout}'")
                connection.execute(f"SET lock_timeout='{lock_timeout}'")
                connection.execute(f"SET transaction_timeout='{transaction_timeout}'")
                for statement in calls:
                    with self.subTest(statement=statement), self.assertRaisesRegex(
                        psycopg.errors.RaiseException, "bounded"
                    ):
                        connection.execute(statement)
        with psycopg.connect(self.runtime_url, autocommit=True) as connection:
            connection.execute("SET ROLE factory_runtime")
            connection.execute("SET statement_timeout='5s'")
            connection.execute("SET lock_timeout='500ms'")
            connection.execute("SET transaction_timeout='3s'")
            self.assertIsInstance(connection.execute(calls[0]).fetchone()[0], dict)
            self.assertIsNone(connection.execute(calls[1]).fetchone()[0])
            self.assertIsNone(connection.execute(calls[2]).fetchone()[0])
            self.assertEqual(connection.execute(calls[3]).fetchone()[0], "not_eligible")
            self.assertFalse(connection.execute(calls[4]).fetchone()[0])
            self.assertFalse(connection.execute(calls[5]).fetchone()[0])
            self.assertIsInstance(connection.execute(calls[6]).fetchone()[0], dict)
        started = time.monotonic()
        with self.assertRaises(StoreUnavailable):
            with self.runtime_store()._transaction(
                connect_timeout=2,
                lock_timeout="500ms",
                statement_timeout="900ms",
                transaction_timeout="1s",
            ) as cursor:
                cursor.execute("SELECT pg_sleep(0.6)")
                cursor.execute("SELECT pg_sleep(0.6)")
        self.assertLess(time.monotonic() - started, 3.0)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                (SELECT count(*) FROM factory.execution_recovery_jobs),
                (SELECT count(*) FROM factory.execution_recovery_claims),
                (SELECT count(*) FROM factory.execution_recovery_outcomes)"""
            )
            self.assertEqual(cursor.fetchone(), (0, 0, 0))

    def test_execution_metrics_are_fixed_bounded_atomic_and_least_privilege(self):
        import psycopg

        initial = self.store.metrics()
        self.assertEqual(
            set(initial),
            {
                "factory_intake_and_rejection_outcomes_total",
                "factory_lease_reclaim_and_fence_rejection_total",
                "factory_capacity_budget_kill_and_reconcile_outcomes_total",
                "factory_execution_claim_and_stage_outcomes_total",
                "factory_execution_protocol_and_proposal_outcomes_total",
                "factory_execution_orphan_and_cleanup_outcomes_total",
            },
        )
        self.assertEqual(
            initial["factory_execution_claim_and_stage_outcomes_total"],
            {
                "claimed": 0,
                "prepared": 0,
                "running": 0,
                "collecting": 0,
                "completed": 0,
                "failed": 0,
                "needs_human": 0,
                "cancelled": 0,
                "orphaned": 0,
            },
        )
        _task, execution = self.claim_execution(
            "execution-metrics", capabilities=["notes", "structured_output"]
        )
        updated = self.store.metrics()
        self.assertEqual(
            (
                updated["factory_execution_claim_and_stage_outcomes_total"]["claimed"],
                updated["factory_execution_claim_and_stage_outcomes_total"]["prepared"],
            ),
            (1, 1),
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT function.provolatile,function.prosecdef,function.proconfig,
                has_function_privilege(
                  'factory_runtime','factory.read_combined_metrics_snapshot()','EXECUTE'),
                has_function_privilege(
                  'factory_artifact_attestor',
                  'factory.read_combined_metrics_snapshot()','EXECUTE'),
                EXISTS(
                  SELECT 1 FROM aclexplode(
                    COALESCE(function.proacl,acldefault('f',function.proowner))) acl
                  WHERE acl.grantee=0 AND acl.privilege_type='EXECUTE')
                FROM pg_proc function
                WHERE function.oid='factory.read_combined_metrics_snapshot()'::regprocedure"""
            )
            self.assertEqual(
                cursor.fetchone(),
                ("s", True, ["search_path=pg_catalog, factory"], True, False, False),
            )
            cursor.execute(
                """SELECT column_name FROM information_schema.columns
                WHERE table_schema='factory'
                  AND table_name='execution_metric_counters'
                ORDER BY ordinal_position"""
            )
            columns = [row[0] for row in cursor.fetchall()]
            self.assertEqual(len(columns), 19)
            self.assertEqual(columns[0], "singleton")
            cursor.execute(
                """SELECT
                has_table_privilege(
                  'factory_runtime','factory.execution_metric_counters',
                  'SELECT,INSERT,UPDATE,DELETE'),
                has_table_privilege(
                  'factory_runtime','factory.execution_recovery_jobs',
                  'SELECT,INSERT,UPDATE,DELETE'),
                has_table_privilege(
                  'factory_artifact_attestor','factory.execution_recovery_claims',
                  'SELECT,INSERT,UPDATE,DELETE')"""
            )
            self.assertEqual(cursor.fetchone(), (False, False, False))
            capability_names = (
                "execution_recovery_candidates",
                "execution_recovery_context",
                "execution_recovery_claim",
                "execution_recovery_cancel_task",
                "execution_recovery_cleanup_succeeded",
                "execution_recovery_cleanup_failed",
                "read_combined_metrics_snapshot",
                "execution_recovery_require_bounds",
                "execution_metric_increment",
                "execution_metric_row_delta",
            )
            cursor.execute(
                """SELECT function.proname,
                has_function_privilege('factory_runtime',function.oid,'EXECUTE'),
                has_function_privilege(
                  'factory_artifact_attestor',function.oid,'EXECUTE'),
                EXISTS(SELECT 1 FROM aclexplode(COALESCE(
                  function.proacl,acldefault('f',function.proowner))) acl
                  WHERE acl.grantee=0 AND acl.privilege_type='EXECUTE')
                FROM pg_proc function JOIN pg_namespace namespace
                  ON namespace.oid=function.pronamespace
                WHERE namespace.nspname='factory' AND function.proname=ANY(%s)
                ORDER BY function.proname""",
                (list(capability_names),),
            )
            function_acl = {
                name: (runtime, attestor, public)
                for name, runtime, attestor, public in cursor.fetchall()
            }
            self.assertEqual(set(function_acl), set(capability_names))
            for name in capability_names[:7]:
                self.assertEqual(function_acl[name], (True, False, False))
            for name in capability_names[7:]:
                self.assertEqual(function_acl[name], (False, False, False))
            cursor.execute(
                """SELECT relation.relname,
                has_table_privilege('factory_runtime',relation.oid,
                  'SELECT,INSERT,UPDATE,DELETE'),
                has_table_privilege('factory_artifact_attestor',relation.oid,
                  'SELECT,INSERT,UPDATE,DELETE'),
                EXISTS(SELECT 1 FROM aclexplode(COALESCE(
                  relation.relacl,acldefault('r',relation.relowner))) acl
                  WHERE acl.grantee=0 AND acl.privilege_type=ANY(
                    ARRAY['SELECT','INSERT','UPDATE','DELETE']))
                FROM pg_class relation JOIN pg_namespace namespace
                  ON namespace.oid=relation.relnamespace
                WHERE namespace.nspname='factory' AND relation.relname=ANY(%s)
                ORDER BY relation.relname""",
                (
                    [
                        "execution_recovery_jobs",
                        "execution_recovery_claims",
                        "execution_recovery_outcomes",
                        "execution_metric_counters",
                    ],
                ),
            )
            self.assertEqual(
                cursor.fetchall(),
                [
                    ("execution_metric_counters", False, False, False),
                    ("execution_recovery_claims", False, False, False),
                    ("execution_recovery_jobs", False, False, False),
                    ("execution_recovery_outcomes", False, False, False),
                ],
            )
            cursor.execute(
                "SET LOCAL plan_cache_mode=force_generic_plan; "
                "SET LOCAL enable_seqscan=off; SET LOCAL enable_bitmapscan=off"
            )
            cursor.execute(
                """PREPARE recovery_retry_plan(timestamptz,integer) AS
                SELECT job.run_id FROM factory.execution_recovery_jobs job
                WHERE job.status<>'succeeded' AND job.next_claim_at<=$1
                  AND (job.status<>'claimed' OR job.claim_expires_at<=$1)
                ORDER BY job.next_claim_at,job.updated_at,job.run_id LIMIT $2"""
            )
            cursor.execute(
                "EXPLAIN (FORMAT TEXT) EXECUTE recovery_retry_plan("
                "'2026-09-02T00:00:00Z'::timestamptz,50)"
            )
            retry_plan = "\n".join(row[0] for row in cursor.fetchall()).lower()
            self.assertIn("execution_recovery_jobs_claimable", retry_plan)
            self.assertIn("index cond", retry_plan)
            self.assertIn("next_claim_at", retry_plan)
            cursor.execute(
                """PREPARE recovery_fresh_start(integer) AS
                SELECT manifest.run_id FROM factory.execution_manifests manifest
                WHERE manifest.terminal_at IS NULL AND NOT EXISTS(
                  SELECT 1 FROM factory.execution_recovery_jobs job
                  WHERE job.run_id=manifest.run_id)
                ORDER BY manifest.updated_at,manifest.run_id LIMIT $1"""
            )
            cursor.execute(
                "EXPLAIN (FORMAT TEXT) EXECUTE recovery_fresh_start(50)"
            )
            fresh_start_plan = "\n".join(
                row[0] for row in cursor.fetchall()
            ).lower()
            self.assertIn("execution_manifests_recovery", fresh_start_plan)
            cursor.execute(
                """PREPARE recovery_fresh_after(timestamptz,uuid,integer) AS
                SELECT manifest.run_id FROM factory.execution_manifests manifest
                WHERE manifest.terminal_at IS NULL
                  AND (manifest.updated_at,manifest.run_id)>($1,$2)
                  AND NOT EXISTS(
                    SELECT 1 FROM factory.execution_recovery_jobs job
                    WHERE job.run_id=manifest.run_id)
                ORDER BY manifest.updated_at,manifest.run_id LIMIT $3"""
            )
            cursor.execute(
                "EXPLAIN (FORMAT TEXT) EXECUTE recovery_fresh_after("
                "'2026-09-02T00:00:00Z'::timestamptz,"
                "'00000000-0000-0000-0000-000000000000'::uuid,50)"
            )
            fresh_after_plan = "\n".join(
                row[0] for row in cursor.fetchall()
            ).lower()
            self.assertIn("execution_manifests_recovery", fresh_after_plan)
            self.assertIn("index cond", fresh_after_plan)
            self.assertIn("updated_at", fresh_after_plan)
            self.assertIn("run_id", fresh_after_plan)
        with psycopg.connect(self.runtime_url, autocommit=True) as connection:
            connection.execute("SET ROLE factory_runtime")
            with self.assertRaisesRegex(Exception, "bounded combined metrics"):
                connection.execute("SELECT factory.read_combined_metrics_snapshot()")
        self.assertEqual(execution.stage.value, "prepared")


FRESH_CLUSTER_DATABASE_URL = os.environ.get("FACTORY_FRESH_CLUSTER_DATABASE_URL")


@unittest.skipUnless(
    FRESH_CLUSTER_DATABASE_URL,
    "FACTORY_FRESH_CLUSTER_DATABASE_URL must name an empty disposable PG17 cluster",
)
class FreshClusterArtifactAttestorMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg

        migrations = discover_migrations()
        if len(migrations) != 18:
            raise AssertionError("fresh-cluster test requires migrations 001..018")
        with psycopg.connect(FRESH_CLUSTER_DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT to_regnamespace('factory'),to_regrole('factory_artifact_attestor')")
                if cursor.fetchone() != (None, None):
                    raise AssertionError("fresh-cluster database and capability role must be absent")
                cursor.execute("CREATE SCHEMA factory")
                cursor.execute(
                    """CREATE TABLE factory.schema_migrations (
                    version integer PRIMARY KEY,name text UNIQUE NOT NULL,
                    sha256 char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
                    applied_at timestamptz NOT NULL DEFAULT now())"""
                )
                for migration in migrations[:14]:
                    cursor.execute(migration.sql)
                    cursor.execute(
                        "INSERT INTO factory.schema_migrations(version,name,sha256) "
                        "VALUES (%s,%s,%s)",
                        (migration.version, migration.name, migration.sha256),
                    )

    def assert_schema14_without_015_residue(self):
        import psycopg

        with psycopg.connect(FRESH_CLUSTER_DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT max(version),
                    to_regclass('factory.execution_artifact_attestations'),
                    to_regprocedure('factory.execution_object_has_exact_keys(jsonb,text[])'),
                    EXISTS(SELECT 1 FROM information_schema.columns
                      WHERE table_schema='factory' AND table_name='workspace_results'
                        AND column_name='m4_status')
                    FROM factory.schema_migrations"""
                )
                self.assertEqual(cursor.fetchone(), (14, None, None, False))

    def test_unsafe_role_or_membership_rolls_back_then_absent_role_is_created_least_privilege(self):
        import psycopg

        with psycopg.connect(FRESH_CLUSTER_DATABASE_URL, autocommit=True) as connection:
            connection.execute(
                "CREATE ROLE factory_artifact_attestor NOLOGIN NOINHERIT"
            )
            connection.execute(
                "GRANT factory_runtime TO factory_artifact_attestor WITH INHERIT FALSE, SET TRUE"
            )
        with self.assertRaisesRegex(RoleSafetyError, "role membership boundary is unsafe"):
            PostgresMigrator(FRESH_CLUSTER_DATABASE_URL).apply()
        self.assert_schema14_without_015_residue()
        with psycopg.connect(FRESH_CLUSTER_DATABASE_URL, autocommit=True) as connection:
            connection.execute("REVOKE factory_runtime FROM factory_artifact_attestor")
            connection.execute("DROP ROLE factory_artifact_attestor")
            connection.execute("CREATE ROLE factory_artifact_attestor LOGIN NOINHERIT")
        with self.assertRaisesRegex(RoleSafetyError, "group role has unsafe attributes"):
            PostgresMigrator(FRESH_CLUSTER_DATABASE_URL).apply()
        self.assert_schema14_without_015_residue()
        with psycopg.connect(FRESH_CLUSTER_DATABASE_URL, autocommit=True) as connection:
            connection.execute("DROP ROLE factory_artifact_attestor")

        applied = PostgresMigrator(FRESH_CLUSTER_DATABASE_URL).apply()
        self.assertEqual(
            [(item.version, item.name) for item in applied],
            [
                (15, "015_execution_canonical_persistence.sql"),
                (16, "016_contract_execution_canonical_persistence.sql"),
                (17, "017_execution_recovery_topology.sql"),
                (18, "018_semantic_validation_bridge.sql"),
            ],
        )
        self.assertEqual(PostgresMigrator(FRESH_CLUSTER_DATABASE_URL).apply(), ())
        with psycopg.connect(FRESH_CLUSTER_DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT rolcanlogin,rolinherit,rolsuper,rolcreaterole,rolcreatedb,
                    rolreplication,rolbypassrls,rolconfig
                    FROM pg_roles WHERE rolname='factory_artifact_attestor'"""
                )
                self.assertEqual(
                    cursor.fetchone(),
                    (False, False, False, False, False, False, False, None),
                )
                cursor.execute(
                    """SELECT count(*) FROM pg_auth_members membership
                    JOIN pg_roles parent ON parent.oid=membership.roleid
                    JOIN pg_roles member ON member.oid=membership.member
                    WHERE parent.rolname='factory_artifact_attestor'
                       OR member.rolname='factory_artifact_attestor'"""
                )
                self.assertEqual(cursor.fetchone()[0], 0)
                cursor.execute(
                    """SELECT
                    has_schema_privilege('factory_artifact_attestor','factory','USAGE'),
                    has_function_privilege(
                      'factory_artifact_attestor',
                      'factory.execution_record_artifact_attestation(jsonb)','EXECUTE'),
                    has_function_privilege(
                      'factory_runtime',
                      'factory.execution_record_artifact_attestation(jsonb)','EXECUTE'),
                    has_function_privilege(
                      'factory_artifact_attestor',
                      'factory.execution_start(uuid,uuid,text,bigint,char,char,char,text,text,jsonb,jsonb)',
                      'EXECUTE'),
                    has_table_privilege(
                      'factory_artifact_attestor',
                      'factory.execution_artifact_attestations','SELECT,INSERT,UPDATE,DELETE'),
                    has_table_privilege(
                      'factory_runtime',
                      'factory.execution_artifact_attestations','SELECT,INSERT,UPDATE,DELETE')"""
                )
                self.assertEqual(cursor.fetchone(), (True, True, False, False, False, False))
                cursor.execute(
                    """SELECT COALESCE(array_agg(COALESCE(role.rolname,'PUBLIC')
                      ORDER BY COALESCE(role.rolname,'PUBLIC')),ARRAY[]::name[])
                    FROM pg_proc function
                    CROSS JOIN LATERAL aclexplode(
                      COALESCE(function.proacl,acldefault('f',function.proowner))
                    ) acl
                    LEFT JOIN pg_roles role ON role.oid=acl.grantee
                    WHERE function.oid=
                      'factory.execution_record_artifact_attestation(jsonb)'::regprocedure
                      AND acl.privilege_type='EXECUTE'"""
                )
                self.assertEqual(
                    set(cursor.fetchone()[0]),
                    {connection.info.user, "factory_artifact_attestor"},
                )
                cursor.execute("SELECT max(version) FROM factory.schema_migrations")
                self.assertEqual(cursor.fetchone()[0], 18)


if __name__ == "__main__":
    unittest.main()
