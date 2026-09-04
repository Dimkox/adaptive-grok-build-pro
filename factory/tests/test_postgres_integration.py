from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import fields, replace
from datetime import datetime, timedelta, timezone
from functools import partial
import json
import os
import threading
import time
import unittest
from unittest import mock
import uuid

from adaptive_factory.migrations import PostgresMigrator, discover_migrations
from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.contracts import TaskIntakeV1, canonical_digest, canonical_json
from adaptive_factory.models import Actor, ExecutionStage, FailureClass, LeaseGrant, RunRole, TaskStatus
from adaptive_factory.semantic_adjudication import adjudicate
from adaptive_factory.semantic_bridge import SemanticBridgeResult
from adaptive_factory.semantic_contracts import (
    SemanticCoverageV1,
    SemanticFindingV1,
    ValidatorIdentityV1,
)
from adaptive_factory.semantic_repair import (
    RepairChildTaskBindingV1,
    SemanticRepairRequestV1,
)
from adaptive_factory.service import (
    REPAIR_CHILD_BROKER_ACTOR_ID,
    REPAIR_CHILD_BROKER_ACTOR_KIND,
    AuthorizationError,
    ClaimRequest,
    FactoryService,
)
from adaptive_factory.state import TransitionDecision
from adaptive_factory.store import (
    BudgetError,
    FenceError,
    PostgresFactoryStore,
    PostgresSemanticAdjudicatorStore,
    PostgresSemanticCoordinatorStore,
    PostgresSemanticValidatorStore,
    StoreError,
    StoreUnavailable,
)
from adaptive_factory.workspace import WorkspaceSnapshotV1
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
REPAIR_CHILD_BROKER = Actor(
    REPAIR_CHILD_BROKER_ACTOR_ID,
    REPAIR_CHILD_BROKER_ACTOR_KIND,
    frozenset({"task:submit", "task:cancel"}),
    frozenset({"*"}),
)
WORKER = Actor(
    "worker", "worker", frozenset({"task:claim", "task:execute", "task:heartbeat", "task:release", "task:budget"}), frozenset({"*"})
)
SECOND_WORKER = Actor(
    "worker-2",
    "worker",
    frozenset(
        {"task:claim", "task:execute", "task:heartbeat", "task:release", "task:budget"}
    ),
    frozenset({"*"}),
)
READER = Actor(
    "reader", "client", frozenset({"task:read"}), frozenset({"owner/repository"})
)


class TrustedPostgresTestSnapshotBroker:
    def __init__(self, result_head_sha="4" * 40):
        self.calls = 0
        self.result_head_sha = result_head_sha

    def snapshot(self, request, *, timeout_seconds=5.0):
        if timeout_seconds != 5.0:
            raise AssertionError("snapshot timeout must stay bounded")
        self.calls += 1
        return WorkspaceSnapshotV1.from_facts({
            "contract_version": 1, "repository_id": request.repository_id,
            "workspace_handle": request.workspace_handle,
            "input_head_sha": request.input_head_sha,
            "result_head_sha": self.result_head_sha,
            "diff_digest": "6" * 64, "diff_lines": 12, "source": "trusted_git_broker",
        })


@unittest.skipUnless(DATABASE_URL, "FACTORY_TEST_DATABASE_URL must name a disposable database")
class PostgresFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        PostgresMigrator(DATABASE_URL).apply()
        from adaptive_factory.admin import (
            provision_runtime_login,
            provision_semantic_adjudicator_login,
            provision_semantic_coordinator_login,
            provision_semantic_validator_login,
        )
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        cls.runtime_login = f"factory_base_runtime_{os.getpid()}"
        cls.semantic_coordinator_login = f"factory_semantic_{os.getpid()}"
        cls.semantic_validator_login = f"factory_validator_{os.getpid()}"
        cls.semantic_adjudicator_login = f"factory_adjudicator_{os.getpid()}"
        cls.runtime_password = "local-" + "base-runtime-store-password"
        cls.semantic_coordinator_password = "local-" + "semantic-coordinator-test"
        cls.semantic_validator_password = "local-" + "semantic-validator-test"
        cls.semantic_adjudicator_password = "local-" + "semantic-adjudicator-test"
        provision_runtime_login(DATABASE_URL, cls.runtime_login, cls.runtime_password)
        provision_semantic_coordinator_login(
            DATABASE_URL,
            cls.semantic_coordinator_login,
            cls.semantic_coordinator_password,
        )
        provision_semantic_validator_login(
            DATABASE_URL,
            cls.semantic_validator_login,
            cls.semantic_validator_password,
        )
        provision_semantic_adjudicator_login(
            DATABASE_URL,
            cls.semantic_adjudicator_login,
            cls.semantic_adjudicator_password,
        )
        cls.runtime_url = make_conninfo(
            **{
                **conninfo_to_dict(DATABASE_URL),
                "user": cls.runtime_login,
                "password": cls.runtime_password,
            }
        )
        cls.semantic_coordinator_url = make_conninfo(
            **{
                **conninfo_to_dict(DATABASE_URL),
                "user": cls.semantic_coordinator_login,
                "password": cls.semantic_coordinator_password,
            }
        )
        cls.semantic_validator_url = make_conninfo(
            **{
                **conninfo_to_dict(DATABASE_URL),
                "user": cls.semantic_validator_login,
                "password": cls.semantic_validator_password,
            }
        )
        cls.semantic_adjudicator_url = make_conninfo(
            **{
                **conninfo_to_dict(DATABASE_URL),
                "user": cls.semantic_adjudicator_login,
                "password": cls.semantic_adjudicator_password,
            }
        )

    @classmethod
    def tearDownClass(cls):
        import psycopg
        from psycopg import sql

        with psycopg.connect(DATABASE_URL) as connection:
            for role in (
                cls.semantic_adjudicator_login,
                cls.semantic_validator_login,
                cls.semantic_coordinator_login,
                cls.runtime_login,
            ):
                connection.execute(
                    sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role))
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

    @classmethod
    def migrate(cls, database_url: str):
        return PostgresMigrator(database_url).apply(
            expected_runtime_login=cls.runtime_login
        )

    def setUp(self):
        import psycopg

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "TRUNCATE factory.semantic_recovery_records, factory.semantic_escalations, factory.semantic_child_task_bindings, factory.semantic_child_proposals, factory.semantic_directives, factory.semantic_verdicts, factory.semantic_coverage, factory.semantic_findings, factory.semantic_assignments, factory.semantic_metric_events, factory.semantic_command_results, factory.semantic_subjects, factory.execution_recovery_outcomes, factory.execution_recovery_claims, factory.execution_recovery_jobs, factory.workspace_results, factory.execution_artifact_attestations, factory.execution_proposals, factory.execution_stage_events, factory.execution_manifests, factory.execution_packets, factory.audit_log, factory.audit_heads, factory.task_events, factory.command_results, factory.metric_counters, factory.budget_reservations, factory.usage_observations, factory.capacity_allocations, factory.attempts, factory.runs, factory.lease_sequences, factory.kill_switches, factory.reconciliation_runs, factory.tasks, factory.accepted_intents, factory.intake_identities, factory.m0_authority_observations, factory.m0_bootstrap_exceptions RESTART IDENTITY"
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
        self.store = self.runtime_store()
        self.service = FactoryService(self.store)

    def payload(self, repository="owner/repository", source=None):
        value = valid_intake()
        value["request_id"] = f"request-{uuid.uuid4()}"
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

    def advance_to_phase(self, grant, target: TaskStatus) -> None:
        ordered = (
            TaskStatus.ANALYZING,
            TaskStatus.IMPLEMENTING,
            TaskStatus.VERIFYING,
            TaskStatus.REVIEWING,
        )
        for phase in ordered[: ordered.index(target) + 1]:
            self.service.transition_phase(
                grant,
                target=phase,
                actor=WORKER,
                now=NOW,
                idempotency_key=canonical_digest(
                    {"test": "advance", "run_id": grant.run_id, "target": phase.value}
                ),
                correlation_id=f"advance-{phase.value}",
            )

    def _assert_claim_terminal_race_releases_capacity(self, action: str) -> None:
        import psycopg

        class PausingCloseStore(PostgresFactoryStore):
            def __init__(self, database_url):
                super().__init__(database_url)
                self.close_snapshot_complete = threading.Event()
                self.resume_terminal = threading.Event()
                self._pause_once = True

            def _close_active_lease(self, cursor, task_id):
                super()._close_active_lease(cursor, task_id)
                if self._pause_once:
                    self._pause_once = False
                    self.close_snapshot_complete.set()
                    if not self.resume_terminal.wait(timeout=5):
                        raise RuntimeError("terminal transition barrier timed out")

        for index, role in enumerate((RunRole.READER, RunRole.WRITER), start=1):
            with self.subTest(action=action, role=role.value):
                source = f"{action}-claim-race-{role.value}"
                repository = f"race/{action}/{role.value}"
                task = self.submit(repository=repository, source=source).task
                pausing_store = PausingCloseStore(self.runtime_url)
                pausing_service = FactoryService(pausing_store)
                command_key = f"{index if action == 'cancel' else index + 2}" * 64

                with ThreadPoolExecutor(max_workers=2) as pool:
                    if action == "cancel":
                        terminal_future = pool.submit(
                            pausing_service.cancel,
                            task.task_id,
                            reason="operator-race",
                            idempotency_key=command_key,
                            actor=OPERATOR,
                            now=NOW,
                        )
                    else:
                        replacement = self.payload(repository=repository, source=source)
                        replacement["source_digest"] = f"{index + 7}" * 64
                        terminal_future = pool.submit(
                            pausing_service.intake, replacement, actor=OPERATOR, now=NOW
                        )
                    self.assertTrue(pausing_store.close_snapshot_complete.wait(timeout=5))
                    claim_future = pool.submit(
                        self.service.claim,
                        owner="ignored-race-owner",
                        role=role,
                        repositories=(task.repository_id,),
                        lease_seconds=60,
                        actor=WORKER,
                        now=NOW,
                    )
                    try:
                        grant = claim_future.result(timeout=5)
                    finally:
                        pausing_store.resume_terminal.set()
                    terminal_future.result(timeout=5)

                self.assertIsNotNone(grant)
                expected = TaskStatus.CANCELLED if action == "cancel" else TaskStatus.SUPERSEDED
                self.assertEqual(self.store.get_task(task.task_id).status, expected)
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT current_run_id,current_fence FROM factory.tasks WHERE task_id=%s",
                        (task.task_id,),
                    )
                    self.assertEqual(cursor.fetchone(), (None, None))
                    cursor.execute(
                        "SELECT count(*) FROM factory.runs WHERE task_id=%s AND released_at IS NULL",
                        (task.task_id,),
                    )
                    self.assertEqual(cursor.fetchone()[0], 0)
                    cursor.execute(
                        "SELECT count(*) FROM factory.capacity_allocations WHERE task_id=%s AND released_at IS NULL",
                        (task.task_id,),
                    )
                    self.assertEqual(cursor.fetchone()[0], 0)
                    scopes = [f"global:{role.value}"]
                    if role is RunRole.READER:
                        scopes.append(f"repository:{task.repository_id}:reader")
                    cursor.execute(
                        "SELECT scope_key,active_count FROM factory.capacity_counters WHERE scope_key=ANY(%s)",
                        (scopes,),
                    )
                    self.assertEqual(dict(cursor.fetchall()), {scope: 0 for scope in scopes})
                self.assertTrue(self.store.readiness()["capacity_consistent"])

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
        for index, stage in enumerate((ExecutionStage.RUNNING, ExecutionStage.COLLECTING), start=4):
            self.service.advance_execution(
                execution.lease, packet_digest=execution.packet_digest, stage=stage,
                actor=WORKER, idempotency_key=str(index) * 64, correlation_id="m5-stage",
            )
        snapshot_broker = TrustedPostgresTestSnapshotBroker()
        finalizer = FactoryService(self.store, snapshot_broker=snapshot_broker)
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
        with self.assertRaises(FenceError):
            self.service.commit_execution_proposal(
                execution.lease, packet_digest=execution.packet_digest, sequence=2,
                event_type="note.proposed",
                payload={"note_type": "finding", "body": "late", "evidence": []}, actor=WORKER,
            )
        import psycopg
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
        self.assertEqual(result.m4_status, TaskStatus.READY_FOR_HUMAN.value)
        self.assertEqual(self.store.get_task(task.task_id).status, TaskStatus.READY_FOR_HUMAN)
        with self.assertRaises(FenceError):
            self.service.release(execution.lease, outcome="completed", actor=WORKER, now=NOW)
        reader = Actor("m6-reader", "operator", frozenset({"task:read"}), frozenset({task.repository_id}))
        bundle = self.service.get_workspace_result(
            task.task_id, result.workspace_result_digest, actor=reader,
        )
        self.assertEqual(bundle["result"].workspace_result_digest, result.workspace_result_digest)
        self.assertEqual((bundle["snapshot"].diff_digest, bundle["snapshot"].diff_lines), ("6" * 64, 12))
        self.assertEqual(bundle["packet"].provider.profile_digest, bundle["packet"].provider.profile_digest)
        wrong_repo = Actor("other-reader", "operator", frozenset({"task:read"}), frozenset({"other/repository"}))
        with self.assertRaises(AuthorizationError):
            self.service.get_workspace_result(task.task_id, result.workspace_result_digest, actor=wrong_repo)

    def test_execution_propose_runtime_boundary_is_monotonic_fenced_and_bounded(self):
        import psycopg

        def start(source: str, *, max_events: int = 1_000):
            payload = self.payload(source=source)
            payload["limits"]["max_events"] = max_events
            task = self.service.intake(payload, actor=OPERATOR, now=NOW).task
            packet = valid_packet()
            packet["provider"]["capabilities"] = [
                "artifacts",
                "cancellation",
                "notes",
                "structured_output",
                "usage",
            ]
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
                idempotency_key=uuid.uuid4().hex * 2,
                correlation_id=source,
            )
            self.assertIsNotNone(execution)
            return task, execution

        def propose(
            execution,
            sequence: int,
            idempotency_key: str,
            kind: str,
            body: dict,
            *,
            owner: str | None = None,
        ) -> bool:
            body = {
                "task_id": execution.lease.task_id,
                "run_id": execution.lease.run_id,
                "packet_digest": execution.packet_digest,
                "fence": execution.lease.fence,
                "sequence": sequence,
                "author_role": execution.lease.role.value,
                **body,
                "idempotency_key": idempotency_key,
            }
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute("SET LOCAL ROLE factory_runtime")
                cursor.execute(
                    "SELECT factory.execution_propose(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
                    (
                        execution.lease.task_id,
                        execution.lease.run_id,
                        owner or execution.lease.owner,
                        execution.lease.fence,
                        execution.lease.packet_digest,
                        execution.packet_digest,
                        sequence,
                        idempotency_key,
                        kind,
                        json.dumps(body, sort_keys=True, separators=(",", ":")),
                    ),
                )
                return bool(cursor.fetchone()[0])

        def proposal_key(execution, sequence: int, kind: str, body: dict) -> str:
            event_type = (
                body["terminal_type"]
                if kind == "terminal"
                else {
                    "note": "note.proposed",
                    "artifact": "artifact.proposed",
                    "usage": "usage.reported",
                }[kind]
            )
            semantic = dict(body)
            if kind == "note":
                semantic.pop("author_role", None)
            return canonical_digest(
                {
                    "contract": "adaptive-factory.execution-proposal/v1",
                    "task_id": execution.lease.task_id,
                    "run_id": execution.lease.run_id,
                    "packet_digest": execution.packet_digest,
                    "fence": execution.lease.fence,
                    "author_role": execution.lease.role.value,
                    "sequence": sequence,
                    "event_type": event_type,
                    "body": semantic,
                }
            )

        task, execution = start("execution-propose-monotonic")
        note = {
            "author_role": "writer",
            "note_type": "finding",
            "body": "bounded",
            "evidence": [],
        }
        terminal = {
            "author_role": "writer",
            "terminal_type": "run.failed",
            "failure_class": "validation",
            "reason": None,
            "diagnostic": "bounded",
            "summary": "validation: bounded",
        }
        first_key = proposal_key(execution, 1, "note", note)
        terminal_key = proposal_key(execution, 2, "terminal", terminal)

        self.assertFalse(
            propose(execution, 1, "6" * 64, "note", note, owner="forged-worker")
        )
        self.assertFalse(
            propose(
                execution,
                1,
                "c" * 64,
                "note",
                {**note, "author_role": "reader"},
            )
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT deadline_at FROM factory.tasks WHERE task_id=%s",
                (task.task_id,),
            )
            deadline = cursor.fetchone()[0]
            cursor.execute(
                "UPDATE factory.tasks SET deadline_at=clock_timestamp()-interval '1 second' WHERE task_id=%s",
                (task.task_id,),
            )
        self.assertFalse(propose(execution, 1, "7" * 64, "note", note))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.tasks SET deadline_at=%s WHERE task_id=%s",
                (deadline, task.task_id),
            )
            cursor.execute(
                "UPDATE factory.tasks SET state='queued' WHERE task_id=%s",
                (task.task_id,),
            )
        self.assertFalse(propose(execution, 1, "8" * 64, "note", note))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.tasks SET state='leased' WHERE task_id=%s",
                (task.task_id,),
            )
            cursor.execute(
                "UPDATE factory.runs SET state='failed' WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        self.assertFalse(propose(execution, 1, "9" * 64, "note", note))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.runs SET state='leased' WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            cursor.execute(
                "UPDATE factory.runs SET role='reader' WHERE run_id=%s",
                (execution.lease.run_id,),
            )
        self.assertFalse(propose(execution, 1, "d" * 64, "note", note))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.runs SET role='writer' WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            cursor.execute(
                "UPDATE factory.tasks SET packet_digest=%s WHERE task_id=%s",
                ("e" * 64, task.task_id),
            )
        self.assertFalse(propose(execution, 1, "a" * 64, "note", note))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.tasks SET packet_digest=%s WHERE task_id=%s",
                (execution.lease.packet_digest, task.task_id),
            )

        self.assertFalse(propose(execution, 2, first_key, "note", note))
        self.assertTrue(propose(execution, 1, first_key, "note", note))
        self.assertFalse(propose(execution, 3, "3" * 64, "note", note))
        self.assertTrue(propose(execution, 1, first_key, "note", note))
        self.assertFalse(propose(execution, 1, "4" * 64, "note", note))
        self.assertFalse(propose(execution, 2, first_key, "note", note))
        self.assertTrue(propose(execution, 2, terminal_key, "terminal", terminal))
        self.assertTrue(propose(execution, 2, terminal_key, "terminal", terminal))
        self.assertFalse(propose(execution, 3, "5" * 64, "note", note))
        self.service.cancel(
            task.task_id,
            reason="bounded-test-cleanup",
            idempotency_key="b" * 64,
            actor=OPERATOR,
            now=NOW,
        )

        max_events = 8
        _bounded_task, bounded = start(
            "execution-propose-max-events", max_events=max_events
        )
        for sequence in range(1, max_events + 1):
            bounded_note = {**note, "body": f"event-{sequence}"}
            self.assertTrue(
                propose(
                    bounded,
                    sequence,
                    proposal_key(bounded, sequence, "note", bounded_note),
                    "note",
                    bounded_note,
                )
            )
        over_limit_note = {**note, "body": "over-limit"}
        self.assertFalse(
            propose(
                bounded,
                max_events + 1,
                proposal_key(
                    bounded, max_events + 1, "note", over_limit_note
                ),
                "note",
                over_limit_note,
            )
        )

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
        self.assertTrue(duplicate.created)
        self.assertEqual(first, duplicate)
        self.assertEqual(first.task.task_id, duplicate.task.task_id)
        self.assertNotEqual(first.task.task_id, replacement.task.task_id)
        self.assertEqual(self.store.get_task(first.task.task_id).status, TaskStatus.SUPERSEDED)

    def test_run_attempt_and_event_history_pages_are_stable_bounded_and_authorized(self):
        task = self.submit(source="history-pages").task
        grants = []
        for _ in range(3):
            grant = self.service.claim(
                owner=WORKER.actor_id,
                role=RunRole.READER,
                repositories=(task.repository_id,),
                lease_seconds=60,
                actor=WORKER,
                now=NOW,
            )
            self.assertIsNotNone(grant)
            grants.append(grant)
            self.service.release(
                grant,
                outcome=FailureClass.WORKER_LOST,
                actor=WORKER,
                now=NOW,
            )

        pages = []
        cursor = None
        while True:
            page = self.service.list_task_runs(
                task.task_id, limit=1, cursor=cursor, actor=READER
            )
            pages.append(page)
            if page.cursor is None:
                break
            cursor = page.cursor
        items = [page.items[0] for page in pages]
        self.assertEqual([item.run.fence for item in items], [1, 2, 3])
        self.assertEqual([item.attempt.attempt_no for item in items], [1, 2, 3])
        self.assertEqual(
            [(item.run.run_id, item.attempt.run_id) for item in items],
            [(grant.run_id, grant.run_id) for grant in grants],
        )
        self.assertEqual([page.cursor is None for page in pages], [False, False, True])

        first_events = self.service.list_task_events(
            task.task_id, limit=2, cursor=None, actor=READER
        )
        self.assertEqual(
            [event.event_sequence for event in first_events.items],
            [1, 2],
        )
        self.assertIsNotNone(first_events.cursor)
        seen = list(first_events.items)
        cursor_sequence = first_events.cursor
        while cursor_sequence is not None:
            page = self.service.list_task_events(
                task.task_id, limit=2, cursor=cursor_sequence, actor=READER
            )
            seen.extend(page.items)
            cursor_sequence = page.cursor
        self.assertEqual(
            [event.event_sequence for event in seen],
            list(range(1, len(seen) + 1)),
        )
        self.assertEqual(len({event.event_id for event in seen}), len(seen))

        denied = Actor(
            "cross-reader",
            "client",
            frozenset({"task:read"}),
            frozenset({"other/repository"}),
        )
        with self.assertRaises(AuthorizationError):
            self.service.list_task_runs(task.task_id, limit=1, cursor=None, actor=denied)
        with self.assertRaises(AuthorizationError):
            self.service.list_task_events(task.task_id, limit=1, cursor=None, actor=denied)

    def test_phase_transition_is_concurrent_replay_safe_fenced_and_audited(self):
        import psycopg

        task = self.submit(source="phase-concurrent-replay").task
        grant = self.service.claim(
            owner=WORKER.actor_id,
            role=RunRole.READER,
            repositories=(task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        wrong_role_key = "0" * 64
        with self.assertRaises(FenceError):
            self.service.transition_phase(
                replace(grant, role=RunRole.WRITER),
                target=TaskStatus.ANALYZING,
                actor=WORKER,
                now=NOW,
                idempotency_key=wrong_role_key,
            )
        key = "a" * 64
        call = partial(
            self.service.transition_phase,
            grant,
            target=TaskStatus.ANALYZING,
            actor=WORKER,
            now=NOW,
            idempotency_key=key,
            correlation_id="phase-replay-correlation",
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = tuple(pool.map(lambda _index: call(), range(2)))
        self.assertEqual(results, (TaskStatus.ANALYZING, TaskStatus.ANALYZING))

        replay = self.service.transition_phase(
            grant,
            target=TaskStatus.ANALYZING,
            actor=WORKER,
            now=NOW,
            idempotency_key=key,
            correlation_id="phase-replay-correlation",
        )
        self.assertEqual(replay, TaskStatus.ANALYZING)
        self.assertEqual(
            tuple(field.name for field in fields(LeaseGrant)),
            (
                "task_id",
                "run_id",
                "owner",
                "role",
                "fence",
                "expires_at",
                "packet_digest",
            ),
        )
        with self.assertRaises(StoreError):
            self.service.transition_phase(
                replace(grant, packet_digest="c" * 64),
                target=TaskStatus.ANALYZING,
                actor=WORKER,
                now=NOW,
                idempotency_key=key,
                correlation_id="phase-replay-correlation",
            )
        with self.assertRaises(StoreError):
            self.service.transition_phase(
                grant,
                target=TaskStatus.IMPLEMENTING,
                actor=WORKER,
                now=NOW,
                idempotency_key=key,
                correlation_id="phase-replay-correlation",
            )
        skip_key = "b" * 64
        with self.assertRaises(StoreError):
            self.service.transition_phase(
                grant,
                target=TaskStatus.VERIFYING,
                actor=WORKER,
                now=NOW,
                idempotency_key=skip_key,
                correlation_id="phase-skip-correlation",
            )

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT t.state,r.state,a.released_at IS NULL,
                (SELECT count(*) FROM factory.task_events
                  WHERE task_id=t.task_id AND action='phase_transitioned'),
                (SELECT count(*) FROM factory.audit_log
                  WHERE task_id=t.task_id AND action='phase_transition'),
                (SELECT count(*) FROM factory.command_results
                  WHERE idempotency_key=%s),
                (SELECT count(*) FROM factory.command_results
                  WHERE idempotency_key=%s),
                (SELECT count(*) FROM factory.command_results
                  WHERE idempotency_key=%s)
                FROM factory.tasks t JOIN factory.runs r ON r.run_id=t.current_run_id
                JOIN factory.capacity_allocations a ON a.run_id=r.run_id
                WHERE t.task_id=%s""",
                (key, skip_key, wrong_role_key, task.task_id),
            )
            self.assertEqual(
                cursor.fetchone(),
                ("analyzing", "leased", True, 1, 1, 1, 0, 0),
            )
            cursor.execute(
                """SELECT e.metadata,a.metadata,a.correlation_id
                FROM factory.task_events e JOIN factory.audit_log a
                  ON a.task_id=e.task_id AND a.action='phase_transition'
                WHERE e.task_id=%s AND e.action='phase_transitioned'""",
                (task.task_id,),
            )
            event_metadata, audit_metadata, correlation = cursor.fetchone()
            expected = {
                "from_state": "leased",
                "target": "analyzing",
                "operation": "phase",
                "run_id": grant.run_id,
                "fence": grant.fence,
            }
            self.assertEqual(event_metadata, expected)
            self.assertEqual(audit_metadata, expected)
            self.assertEqual(correlation, "phase-replay-correlation")

        heartbeat = self.service.heartbeat(
            grant,
            actor=WORKER,
            now=NOW,
            idempotency_key="c" * 64,
        )
        self.assertEqual(
            tuple(field.name for field in fields(heartbeat)),
            tuple(field.name for field in fields(LeaseGrant)),
        )
        self.assertEqual(
            self.service.release(
                grant,
                outcome=FailureClass.WORKER_LOST,
                actor=WORKER,
                now=NOW,
            ),
            TaskStatus.RETRY,
        )
        stale_key = "d" * 64
        with self.assertRaises(FenceError):
            self.service.transition_phase(
                grant,
                target=TaskStatus.IMPLEMENTING,
                actor=WORKER,
                now=NOW,
                idempotency_key=stale_key,
            )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                (SELECT count(*) FROM factory.task_events
                  WHERE task_id=%s AND action='phase_transitioned'),
                (SELECT count(*) FROM factory.audit_log
                  WHERE task_id=%s AND action='phase_transition'),
                (SELECT count(*) FROM factory.command_results
                  WHERE idempotency_key=%s)""",
                (task.task_id, task.task_id, stale_key),
            )
            self.assertEqual(cursor.fetchone(), (1, 1, 0))

    def test_phase_transition_rolls_back_when_post_mutation_evidence_fails(self):
        import psycopg

        class FailingPhaseAuditStore(PostgresFactoryStore):
            def _audit(self, cursor, task_id, actor, action, resource, reason, correlation_id, metadata=None, run_id=None):
                if action == "phase_transition":
                    raise StoreError("injected post-mutation audit failure")
                return super()._audit(
                    cursor,
                    task_id,
                    actor,
                    action,
                    resource,
                    reason,
                    correlation_id,
                    metadata,
                    run_id,
                )

        task = self.submit(source="phase-post-mutation-rollback").task
        grant = self.service.claim(
            owner=WORKER.actor_id,
            role=RunRole.READER,
            repositories=(task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        key = "e" * 64
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT transition_events FROM factory.metric_counters"
            )
            transition_events_before = cursor.fetchone()[0]

        failing_service = FactoryService(FailingPhaseAuditStore(self.runtime_url))
        with self.assertRaisesRegex(StoreError, "post-mutation"):
            failing_service.transition_phase(
                grant,
                target=TaskStatus.ANALYZING,
                actor=WORKER,
                now=NOW,
                idempotency_key=key,
                correlation_id="phase-rollback-correlation",
            )

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT t.state,r.state,r.released_at IS NULL,a.released_at IS NULL,
                (SELECT count(*) FROM factory.task_events
                  WHERE task_id=t.task_id AND action='phase_transitioned'),
                (SELECT count(*) FROM factory.audit_log
                  WHERE task_id=t.task_id AND action='phase_transition'),
                (SELECT count(*) FROM factory.command_results
                  WHERE idempotency_key=%s),
                (SELECT transition_events FROM factory.metric_counters)
                FROM factory.tasks t JOIN factory.runs r ON r.run_id=t.current_run_id
                JOIN factory.capacity_allocations a ON a.run_id=r.run_id
                WHERE t.task_id=%s""",
                (key, task.task_id),
            )
            self.assertEqual(
                cursor.fetchone(),
                (
                    "leased",
                    "leased",
                    True,
                    True,
                    0,
                    0,
                    0,
                    transition_events_before,
                ),
            )

    def test_phase_sequence_and_completed_release_edges_are_exact(self):
        import psycopg

        reviewed = self.submit(source="phase-reviewed-completion").task
        reviewed_grant = self.service.claim(
            owner=WORKER.actor_id,
            role=RunRole.READER,
            repositories=(reviewed.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        self.advance_to_phase(reviewed_grant, TaskStatus.REVIEWING)
        self.service.observe_usage(
            reviewed_grant,
            provider_call_id="phase-reviewed-usage",
            price_table_digest="2" * 64,
            cost_usd_micros=0,
            token_units=0,
            output_bytes=0,
            actor=WORKER,
        )
        self.assertEqual(
            self.service.release(
                reviewed_grant, outcome="completed", actor=WORKER, now=NOW
            ),
            TaskStatus.READY_FOR_HUMAN,
        )

        compatible = self.submit(source="phase-leased-compatibility").task
        compatible_grant = self.service.claim(
            owner=WORKER.actor_id,
            role=RunRole.READER,
            repositories=(compatible.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        self.service.observe_usage(
            compatible_grant,
            provider_call_id="phase-compatible-usage",
            price_table_digest="2" * 64,
            cost_usd_micros=0,
            token_units=0,
            output_bytes=0,
            actor=WORKER,
        )
        self.assertEqual(
            self.service.release(
                compatible_grant, outcome="completed", actor=WORKER, now=NOW
            ),
            TaskStatus.READY_FOR_HUMAN,
        )

        for phase in (
            TaskStatus.ANALYZING,
            TaskStatus.IMPLEMENTING,
            TaskStatus.VERIFYING,
        ):
            with self.subTest(phase=phase.value):
                repository = f"phase/completion-denied/{phase.value}"
                task = self.submit(
                    repository=repository,
                    source=f"phase-completion-denied-{phase.value}",
                ).task
                grant = self.service.claim(
                    owner=WORKER.actor_id,
                    role=RunRole.READER,
                    repositories=(task.repository_id,),
                    lease_seconds=60,
                    actor=WORKER,
                    now=NOW,
                )
                self.advance_to_phase(grant, phase)
                self.service.observe_usage(
                    grant,
                    provider_call_id=f"phase-denied-{phase.value}",
                    price_table_digest="2" * 64,
                    cost_usd_micros=0,
                    token_units=0,
                    output_bytes=0,
                    actor=WORKER,
                )
                key = canonical_digest(
                    {"test": "completed-denied", "phase": phase.value}
                )
                with self.assertRaises(StoreError):
                    self.service.release(
                        grant,
                        outcome="completed",
                        actor=WORKER,
                        now=NOW,
                        idempotency_key=key,
                    )
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        """SELECT t.state,r.state,r.released_at IS NULL,
                        a.released_at IS NULL,at.finished_at IS NULL,
                        (SELECT count(*) FROM factory.command_results WHERE idempotency_key=%s)
                        FROM factory.tasks t JOIN factory.runs r ON r.run_id=t.current_run_id
                        JOIN factory.capacity_allocations a ON a.run_id=r.run_id
                        JOIN factory.attempts at ON at.run_id=r.run_id
                        WHERE t.task_id=%s""",
                        (key, task.task_id),
                    )
                    self.assertEqual(
                        cursor.fetchone(),
                        (phase.value, "leased", True, True, True, 0),
                    )
                self.service.release(
                    grant,
                    outcome=FailureClass.WORKER_LOST,
                    actor=WORKER,
                    now=NOW,
                )

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT action,metadata FROM factory.task_events
                WHERE task_id=%s AND action IN ('claimed','phase_transitioned','released')
                ORDER BY event_sequence""",
                (reviewed.task_id,),
            )
            events = cursor.fetchall()
            self.assertEqual(len(events), 6)
            for _action, metadata in events:
                self.assertEqual(
                    set(("from_state", "target", "operation")) - set(metadata),
                    set(),
                )

    def test_every_active_phase_accepts_lease_operations_and_reconciliation(self):
        import psycopg

        active = (
            TaskStatus.LEASED,
            TaskStatus.ANALYZING,
            TaskStatus.IMPLEMENTING,
            TaskStatus.VERIFYING,
            TaskStatus.REVIEWING,
        )
        for phase in active:
            with self.subTest(phase=phase.value):
                repository = f"active/operations/{phase.value}"
                task = self.submit(
                    repository=repository,
                    source=f"active-operations-{phase.value}",
                ).task
                grant = self.service.claim(
                    owner=WORKER.actor_id,
                    role=RunRole.READER,
                    repositories=(task.repository_id,),
                    lease_seconds=60,
                    actor=WORKER,
                    now=NOW,
                )
                if phase is not TaskStatus.LEASED:
                    self.advance_to_phase(grant, phase)
                self.service.heartbeat(
                    grant,
                    actor=WORKER,
                    now=NOW,
                    idempotency_key=canonical_digest(
                        {"test": "heartbeat-phase", "phase": phase.value}
                    ),
                )
                self.service.reserve_budget(
                    grant,
                    cost_usd_micros=0,
                    token_units=0,
                    wall_seconds=1,
                    reason_digest="3" * 64,
                    idempotency_key=canonical_digest(
                        {"test": "reserve-phase", "phase": phase.value}
                    ),
                    actor=WORKER,
                )
                self.service.observe_usage(
                    grant,
                    provider_call_id=f"usage-{phase.value}",
                    price_table_digest="2" * 64,
                    cost_usd_micros=0,
                    token_units=0,
                    output_bytes=0,
                    actor=WORKER,
                    idempotency_key=canonical_digest(
                        {"test": "usage-phase", "phase": phase.value}
                    ),
                )
                self.assertEqual(
                    self.service.release(
                        grant,
                        outcome=FailureClass.WORKER_LOST,
                        actor=WORKER,
                        now=NOW,
                    ),
                    TaskStatus.RETRY,
                )

        reconcile_grants = []
        for phase in active:
            repository = f"active/reconcile/{phase.value}"
            task = self.submit(
                repository=repository,
                source=f"active-reconcile-{phase.value}",
            ).task
            grant = self.service.claim(
                owner=WORKER.actor_id,
                role=RunRole.READER,
                repositories=(task.repository_id,),
                lease_seconds=60,
                actor=WORKER,
                now=NOW,
            )
            if phase is not TaskStatus.LEASED:
                self.advance_to_phase(grant, phase)
            reconcile_grants.append((phase, task, grant))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """UPDATE factory.runs
                SET lease_expires_at=clock_timestamp()-interval '1 second'
                WHERE run_id=ANY(%s)""",
                ([grant.run_id for _phase, _task, grant in reconcile_grants],),
            )
        result = self.service.reconcile(actor=OPERATOR, now=NOW)
        self.assertEqual(result.repaired, len(active))
        for _phase, task, grant in reconcile_grants:
            self.assertEqual(self.store.get_task(task.task_id).status, TaskStatus.RETRY)
            with self.assertRaises(FenceError):
                self.service.heartbeat(grant, actor=WORKER, now=NOW)

    def test_transition_policy_denials_roll_back_all_mutation_classes(self):
        import psycopg

        denied = TransitionDecision("forbidden", "injected policy denial")

        claim_task = self.submit(
            repository="policy/denial/claim", source="policy-denial-claim"
        ).task
        claim_key = "1" * 64
        with mock.patch("adaptive_factory.store.authorize_transition", return_value=denied):
            with self.assertRaises(StoreError):
                self.service.claim(
                    owner=WORKER.actor_id,
                    role=RunRole.READER,
                    repositories=(claim_task.repository_id,),
                    lease_seconds=60,
                    actor=WORKER,
                    now=NOW,
                    idempotency_key=claim_key,
                )

        release_task = self.submit(
            repository="policy/denial/release", source="policy-denial-release"
        ).task
        release_grant = self.service.claim(
            owner=WORKER.actor_id,
            role=RunRole.READER,
            repositories=(release_task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        release_key = "2" * 64
        with mock.patch("adaptive_factory.store.authorize_transition", return_value=denied):
            with self.assertRaises(StoreError):
                self.service.release(
                    release_grant,
                    outcome=FailureClass.WORKER_LOST,
                    actor=WORKER,
                    now=NOW,
                    idempotency_key=release_key,
                )

        cancel_task = self.submit(
            repository="policy/denial/cancel", source="policy-denial-cancel"
        ).task
        cancel_grant = self.service.claim(
            owner=WORKER.actor_id,
            role=RunRole.READER,
            repositories=(cancel_task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        cancel_key = "3" * 64
        with mock.patch("adaptive_factory.store.authorize_transition", return_value=denied):
            with self.assertRaises(StoreError):
                self.service.cancel(
                    cancel_task.task_id,
                    reason="injected",
                    idempotency_key=cancel_key,
                    actor=OPERATOR,
                    now=NOW,
                )

        superseded = self.submit(
            repository="policy/denial/supersede",
            source="policy-denial-supersede",
        ).task
        replacement = self.payload(
            repository="policy/denial/supersede",
            source="policy-denial-supersede",
        )
        replacement["source_digest"] = "8" * 64
        with mock.patch("adaptive_factory.store.authorize_transition", return_value=denied):
            with self.assertRaises(StoreError):
                self.service.intake(replacement, actor=OPERATOR, now=NOW)

        reconcile_task = self.submit(
            repository="policy/denial/reconcile", source="policy-denial-reconcile"
        ).task
        reconcile_grant = self.service.claim(
            owner=WORKER.actor_id,
            role=RunRole.READER,
            repositories=(reconcile_task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        deadline_task = self.submit(
            repository="policy/denial/deadline", source="policy-denial-deadline"
        ).task
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """UPDATE factory.runs
                SET lease_expires_at=clock_timestamp()-interval '1 second'
                WHERE run_id=%s""",
                (reconcile_grant.run_id,),
            )
            cursor.execute(
                """UPDATE factory.tasks
                SET deadline_at=clock_timestamp()-interval '1 second'
                WHERE task_id=%s""",
                (deadline_task.task_id,),
            )
        with mock.patch("adaptive_factory.store.authorize_transition", return_value=denied):
            with self.assertRaises(StoreError):
                self.service.reconcile(actor=OPERATOR, now=NOW)

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT state,current_run_id FROM factory.tasks
                WHERE task_id=ANY(%s) ORDER BY task_id""",
                ([claim_task.task_id, release_task.task_id, cancel_task.task_id],),
            )
            by_task = {}
            cursor.execute(
                """SELECT task_id,state,current_run_id FROM factory.tasks
                WHERE task_id=ANY(%s)""",
                ([
                    claim_task.task_id,
                    release_task.task_id,
                    cancel_task.task_id,
                    superseded.task_id,
                    reconcile_task.task_id,
                    deadline_task.task_id,
                ],),
            )
            by_task = {str(row[0]): row[1:] for row in cursor.fetchall()}
            self.assertEqual(by_task[claim_task.task_id], ("queued", None))
            for task, grant in (
                (release_task, release_grant),
                (cancel_task, cancel_grant),
                (reconcile_task, reconcile_grant),
            ):
                self.assertEqual(by_task[task.task_id], ("leased", uuid.UUID(grant.run_id)))
            self.assertEqual(by_task[superseded.task_id], ("queued", None))
            self.assertEqual(by_task[deadline_task.task_id], ("queued", None))
            cursor.execute(
                """SELECT count(*) FROM factory.tasks
                WHERE source_id='policy-denial-supersede'"""
            )
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute(
                """SELECT count(*) FROM factory.command_results
                WHERE idempotency_key=ANY(%s)""",
                ([claim_key, release_key, cancel_key],),
            )
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute("SELECT count(*) FROM factory.reconciliation_runs")
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_retry_exhaustion_policy_denial_rolls_back_terminalization(self):
        import psycopg

        task = self.submit(
            repository="policy/denial/retry-exhausted",
            source="policy-denial-retry-exhausted",
        ).task
        run_id = str(uuid.uuid4())
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.tasks SET infrastructure_retries=0 WHERE task_id=%s",
                (task.task_id,),
            )
            cursor.execute(
                """INSERT INTO factory.runs
                (run_id,task_id,owner_id,role,packet_digest,fence,state,
                 lease_expires_at,deadline_at,released_at)
                SELECT %s,task_id,'prior-worker','reader',packet_digest,1,'failed',
                  clock_timestamp()-interval '1 minute',deadline_at,clock_timestamp()
                FROM factory.tasks WHERE task_id=%s""",
                (run_id, task.task_id),
            )
            cursor.execute(
                """INSERT INTO factory.attempts
                (attempt_id,task_id,run_id,attempt_no,failure_class,failure_code,
                 failure_digest,finished_at)
                VALUES (%s,%s,%s,1,'worker_lost','worker_lost',%s,clock_timestamp())""",
                (uuid.uuid4(), task.task_id, run_id, "f" * 64),
            )

        denied = TransitionDecision("forbidden", "injected retry-exhaustion denial")
        key = "9" * 64
        with mock.patch("adaptive_factory.store.authorize_transition", return_value=denied):
            with self.assertRaises(StoreError):
                self.service.claim(
                    owner=WORKER.actor_id,
                    role=RunRole.READER,
                    repositories=(task.repository_id,),
                    lease_seconds=60,
                    actor=WORKER,
                    now=NOW,
                    idempotency_key=key,
                )

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT state,terminal_at IS NULL,
                (SELECT count(*) FROM factory.lease_sequences WHERE task_id=t.task_id),
                (SELECT count(*) FROM factory.task_events
                  WHERE task_id=t.task_id AND action='retry_exhausted'),
                (SELECT count(*) FROM factory.audit_log
                  WHERE task_id=t.task_id AND reason='retry_exhausted'),
                (SELECT count(*) FROM factory.command_results WHERE idempotency_key=%s)
                FROM factory.tasks t WHERE task_id=%s""",
                (key, task.task_id),
            )
            self.assertEqual(cursor.fetchone(), ("queued", True, 0, 0, 0, 0))

    def test_run_history_cursor_is_task_bound_and_cardinality_fails_closed(self):
        import psycopg

        first = self.submit(source="history-cursor-first").task
        first_grant = self.service.claim(
            owner=WORKER.actor_id,
            role=RunRole.READER,
            repositories=(first.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        second = self.submit(source="history-cursor-second").task
        second_grant = self.service.claim(
            owner=WORKER.actor_id,
            role=RunRole.READER,
            repositories=(second.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        for invalid in (str(uuid.uuid4()), second_grant.run_id):
            with self.subTest(cursor=invalid):
                with self.assertRaisesRegex(ValueError, "invalid run cursor"):
                    self.service.list_task_runs(
                        first.task_id, limit=1, cursor=invalid, actor=READER
                    )

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO factory.attempts
                (attempt_id,task_id,run_id,attempt_no)
                VALUES (%s,%s,%s,2)""",
                (uuid.uuid4(), first.task_id, first_grant.run_id),
            )
        with self.assertRaises(StoreUnavailable):
            self.service.list_task_runs(first.task_id, limit=100, cursor=None, actor=READER)

    def test_run_history_orders_by_fence_not_uuid(self):
        import psycopg

        task = self.submit(source="history-fence-order").task
        run_ids = (
            "ffffffff-ffff-4fff-8fff-ffffffffffff",
            "11111111-1111-4111-8111-111111111111",
            "88888888-8888-4888-8888-888888888888",
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            for fence, run_id in enumerate(run_ids, start=1):
                cursor.execute(
                    """INSERT INTO factory.runs
                    (run_id,task_id,owner_id,role,packet_digest,fence,state,
                     lease_expires_at,deadline_at,released_at)
                    VALUES (%s,%s,'history-reader','reader',%s,%s,'completed',
                      clock_timestamp(),clock_timestamp(),clock_timestamp())""",
                    (run_id, task.task_id, task.packet_digest, fence),
                )
                cursor.execute(
                    """INSERT INTO factory.attempts
                    (attempt_id,task_id,run_id,attempt_no,finished_at)
                    VALUES (%s,%s,%s,%s,clock_timestamp())""",
                    (uuid.uuid4(), task.task_id, run_id, fence),
                )
        page = self.service.list_task_runs(
            task.task_id, limit=100, cursor=None, actor=READER
        )
        self.assertEqual(tuple(item.run.run_id for item in page.items), run_ids)
        self.assertIsNone(page.cursor)

    def test_run_history_missing_attempt_fails_closed(self):
        import psycopg

        task = self.submit(source="history-missing-attempt").task
        run_id = uuid.uuid4()
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO factory.runs
                (run_id,task_id,owner_id,role,packet_digest,fence,state,
                 lease_expires_at,deadline_at,released_at)
                VALUES (%s,%s,'orphan-reader','reader',%s,1,'released',
                  clock_timestamp(),clock_timestamp(),clock_timestamp())""",
                (run_id, task.task_id, task.packet_digest),
            )
        with self.assertRaises(StoreUnavailable):
            self.service.list_task_runs(task.task_id, limit=100, cursor=None, actor=READER)

    def test_history_store_rejects_boolean_bounds_and_cursors(self):
        task = self.submit(source="history-bool-bounds").task
        for read in (
            lambda: self.store.list_task_runs(
                task.task_id, limit=True, cursor_run_id=None
            ),
            lambda: self.store.list_task_runs(
                task.task_id, limit=1, cursor_run_id=True
            ),
            lambda: self.store.list_task_events(
                task.task_id, limit=True, cursor_sequence=None
            ),
            lambda: self.store.list_task_events(
                task.task_id, limit=1, cursor_sequence=True
            ),
        ):
            with self.assertRaises(ValueError):
                read()

    def test_history_http_boundary_is_authorized_typed_and_redacted(self):
        from fastapi.testclient import TestClient

        task = self.submit(source="history-http").task
        grant = self.service.claim(
            owner=WORKER.actor_id,
            role=RunRole.READER,
            repositories=(task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        other = self.submit(source="history-http-other").task
        other_grant = self.service.claim(
            owner=WORKER.actor_id,
            role=RunRole.READER,
            repositories=(other.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        token = "history-" + "reader-" + "token"
        client = TestClient(create_app(self.service, Authenticator({token: READER})))
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Correlation-ID": "history-http-correlation",
        }
        runs = client.get(f"/v1/tasks/{task.task_id}/runs", headers=headers)
        events = client.get(f"/v1/tasks/{task.task_id}/events", headers=headers)
        self.assertEqual(runs.status_code, 200)
        self.assertEqual(runs.json()["items"][0]["run"]["run_id"], grant.run_id)
        self.assertEqual(runs.json()["items"][0]["attempt"]["attempt_no"], 1)
        self.assertEqual(events.status_code, 200)
        self.assertEqual(events.headers["X-Correlation-ID"], "history-http-correlation")

        cross_cursor = client.get(
            f"/v1/tasks/{task.task_id}/runs",
            headers=headers,
            params={"cursor": other_grant.run_id},
        )
        unknown_cursor = client.get(
            f"/v1/tasks/{task.task_id}/runs",
            headers=headers,
            params={"cursor": str(uuid.uuid4())},
        )
        for response in (cross_cursor, unknown_cursor):
            self.assertEqual(response.status_code, 422)
            self.assertNotIn(other.task_id, response.text)
            self.assertNotIn(other_grant.run_id, response.text)
        missing = client.get(
            f"/v1/tasks/{uuid.uuid4()}/events",
            headers=headers,
        )
        self.assertEqual(missing.status_code, 404)

    def test_history_projection_corruption_in_lookahead_fails_closed(self):
        import psycopg

        task = self.submit(source="history-lookahead-corruption").task
        first = self.service.claim(
            owner=WORKER.actor_id,
            role=RunRole.READER,
            repositories=(task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        second_run_id = uuid.uuid4()
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO factory.runs
                (run_id,task_id,owner_id,role,packet_digest,fence,state,
                 lease_expires_at,deadline_at,released_at)
                VALUES (%s,%s,'corrupt-reader','reader',%s,2,'failed',
                  clock_timestamp(),clock_timestamp(),clock_timestamp())""",
                (second_run_id, task.task_id, task.packet_digest),
            )
            cursor.execute(
                """INSERT INTO factory.attempts
                (attempt_id,task_id,run_id,attempt_no,failure_class)
                VALUES (%s,%s,%s,2,'worker_lost')""",
                (uuid.uuid4(), task.task_id, second_run_id),
            )
            cursor.execute(
                """INSERT INTO factory.task_events
                (event_id,task_id,event_sequence,idempotency_key,actor_id,action,metadata)
                VALUES (%s,%s,3,%s,'corrupt-reader','corrupt',%s::jsonb)""",
                (uuid.uuid4(), task.task_id, uuid.uuid4().hex * 2, "[]"),
            )

        with self.assertRaises(StoreUnavailable):
            self.service.list_task_runs(task.task_id, limit=1, cursor=None, actor=READER)
        with self.assertRaises(StoreUnavailable):
            self.service.list_task_events(task.task_id, limit=2, cursor=None, actor=READER)
        self.assertEqual(first.fence, 1)

    def test_intake_separates_semantic_work_identity_from_command_replay(self):
        import psycopg

        source = "semantic-work-identity"
        original = self.payload(source=source)
        original_contract = TaskIntakeV1.from_dict(original, now=NOW)
        first = self.service.intake(original, actor=OPERATOR, now=NOW)

        refreshed = self.payload(source=source)
        refreshed["request_id"] = "semantic-request-002"
        refreshed_at = NOW - timedelta(seconds=1)
        refreshed["m0_authority"]["observed_at"] = refreshed_at.isoformat()
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO factory.m0_authority_observations
                (observation_id,observed_at,check_name,exact_head_sha,issuer,evidence_digest,
                repository_id,policy_digest)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    uuid.uuid4(),
                    refreshed_at,
                    refreshed["m0_authority"]["check_name"],
                    refreshed["m0_authority"]["exact_head_sha"],
                    "external-trust-ci-api",
                    uuid.uuid4().hex * 2,
                    refreshed["repository_id"],
                    refreshed["policy_digest"],
                ),
            )

        duplicate = self.service.intake(refreshed, actor=OPERATOR, now=NOW)
        replay = self.service.intake(refreshed, actor=OPERATOR, now=NOW)
        self.assertTrue(first.created)
        self.assertFalse(duplicate.created)
        self.assertFalse(replay.created)
        self.assertEqual(first.task.task_id, duplicate.task.task_id)
        self.assertEqual(first.task.intent_digest, duplicate.task.intent_digest)
        self.assertEqual(first.task.packet_digest, first.task.intent_digest)

        conflicting = self.payload(source=source)
        conflicting["request_id"] = refreshed["request_id"]
        conflicting["m0_authority"] = dict(refreshed["m0_authority"])
        conflicting["source_digest"] = "8" * 64
        with self.assertRaisesRegex(StoreError, "idempotency key reused with different command"):
            self.service.intake(conflicting, actor=OPERATOR, now=NOW)

        expected_command_keys = {
            canonical_digest(
                {
                    "contract": "adaptive-factory.intake-command/v1",
                    "request_id": request_id,
                }
            )
            for request_id in (original["request_id"], refreshed["request_id"])
        }
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT i.intent_digest,i.idempotency_key,i.body,t.packet_digest,t.generation
                FROM factory.accepted_intents i JOIN factory.tasks t ON t.intent_id=i.intent_id
                WHERE i.repository_id=%s AND i.source_type=%s AND i.source_id=%s""",
                (original["repository_id"], original["source_type"], source),
            )
            stored = cursor.fetchone()
            self.assertIsNotNone(stored)
            self.assertEqual(stored[0].strip(), first.task.intent_digest)
            self.assertEqual(stored[1].strip(), canonical_digest({
                "contract": "adaptive-factory.work-identity/v1",
                "work": {
                    key: value
                    for key, value in original.items()
                    if key not in {"request_id", "m0_authority"}
                },
            }))
            self.assertEqual(stored[2], original_contract.to_dict())
            self.assertEqual(stored[3].strip(), first.task.intent_digest)
            self.assertEqual(stored[4], 1)
            cursor.execute(
                """SELECT idempotency_key,action,result->>'task_id',result->>'created'
                FROM factory.command_results WHERE idempotency_key=ANY(%s)
                ORDER BY idempotency_key""",
                (list(expected_command_keys),),
            )
            commands = cursor.fetchall()
            self.assertEqual({row[0].strip() for row in commands}, expected_command_keys)
            self.assertEqual({row[1] for row in commands}, {"intake"})
            self.assertEqual({row[2] for row in commands}, {first.task.task_id})
            self.assertEqual({row[3] for row in commands}, {"true", "false"})

    def test_http_intake_deduplicates_fresh_proof_and_conflicts_on_command_reuse(self):
        import psycopg
        from fastapi.testclient import TestClient

        token = "-".join(("semantic", "operator", "credential"))
        client = TestClient(create_app(self.service, Authenticator({token: OPERATOR})))
        source = "semantic-http-identity"
        original = self.payload(source=source)
        original["request_id"] = "semantic-http-001"

        def headers(request_id: str, correlation_id: str):
            return {
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": request_id,
                "X-Correlation-ID": correlation_id,
            }

        accepted = client.post(
            "/v1/tasks",
            json=original,
            headers=headers(original["request_id"], "semantic-correlation-001"),
        )
        self.assertEqual(accepted.status_code, 201)
        first = accepted.json()
        self.assertTrue(first["created"])

        refreshed = self.payload(source=source)
        refreshed["request_id"] = "semantic-http-002"
        refreshed_at = NOW - timedelta(seconds=2)
        refreshed["m0_authority"]["observed_at"] = refreshed_at.isoformat()
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO factory.m0_authority_observations
                (observation_id,observed_at,check_name,exact_head_sha,issuer,evidence_digest,
                repository_id,policy_digest)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    uuid.uuid4(),
                    refreshed_at,
                    refreshed["m0_authority"]["check_name"],
                    refreshed["m0_authority"]["exact_head_sha"],
                    "external-trust-ci-api",
                    uuid.uuid4().hex * 2,
                    refreshed["repository_id"],
                    refreshed["policy_digest"],
                ),
            )
        duplicate_headers = headers(refreshed["request_id"], "semantic-correlation-002")
        duplicate = client.post("/v1/tasks", json=refreshed, headers=duplicate_headers)
        replay = client.post("/v1/tasks", json=refreshed, headers=duplicate_headers)
        for response in (duplicate, replay):
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()["created"])
            self.assertEqual(response.json()["task"]["task_id"], first["task"]["task_id"])
            self.assertEqual(
                response.headers["X-Correlation-ID"],
                "semantic-correlation-002",
            )

        conflicting = {**refreshed, "source_digest": "8" * 64}
        conflict = client.post("/v1/tasks", json=conflicting, headers=duplicate_headers)
        self.assertEqual(
            (conflict.status_code, conflict.json()),
            (
                409,
                {
                    "error": "conflict",
                    "code": "store_conflict",
                    "detail": "stored command conflicts with request",
                },
            ),
        )
        self.assertEqual(
            conflict.headers["X-Correlation-ID"], "semantic-correlation-002"
        )

        replacement = self.payload(source=source)
        replacement["request_id"] = "semantic-http-003"
        replacement["m0_authority"] = dict(refreshed["m0_authority"])
        replacement["source_digest"] = "8" * 64
        replacement_headers = headers(
            replacement["request_id"],
            "semantic-correlation-003",
        )
        created = client.post("/v1/tasks", json=replacement, headers=replacement_headers)
        created_replay = client.post(
            "/v1/tasks",
            json=replacement,
            headers=replacement_headers,
        )
        self.assertEqual((created.status_code, created_replay.status_code), (201, 201))
        self.assertEqual(created.json(), created_replay.json())
        self.assertNotEqual(created.json()["task"]["task_id"], first["task"]["task_id"])

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT state,count(*) FROM factory.tasks
                WHERE repository_id=%s AND source_type=%s AND source_id=%s
                GROUP BY state ORDER BY state""",
                (original["repository_id"], original["source_type"], source),
            )
            self.assertEqual(dict(cursor.fetchall()), {"queued": 1, "superseded": 1})
            cursor.execute(
                "SELECT correlation_id FROM factory.command_results WHERE action='intake'"
            )
            self.assertEqual(
                {row[0] for row in cursor.fetchall()},
                {
                    "semantic-correlation-001",
                    "semantic-correlation-002",
                    "semantic-correlation-003",
                },
            )
            cursor.execute(
                "SELECT action,correlation_id FROM factory.audit_log ORDER BY audit_id"
            )
            self.assertEqual(
                cursor.fetchall(),
                [
                    ("intake", "semantic-correlation-001"),
                    ("superseded", "semantic-correlation-003"),
                    ("intake", "semantic-correlation-003"),
                ],
            )

    def test_changed_frozen_head_authority_and_limits_supersede_exact_replay(self):
        import psycopg

        source = "full-frozen-intent"
        original = self.payload(source=source)
        first = self.service.intake(original, actor=OPERATOR, now=NOW)
        self.assertEqual(
            self.service.intake(original, actor=OPERATOR, now=NOW),
            first,
        )
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
                later = {
                    **payload,
                    "request_id": f"{payload['request_id']}-later",
                    "source_id": f"later-{kind}",
                }
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

    def test_cancel_and_supersede_quarantine_unresolved_accounting_for_both_roles(self):
        import psycopg

        expected_reserved_cost = 0
        expected_reserved_tokens = 0
        expected_reserved_wall = 0
        expected_blocked = 0
        cases = [
            (action, role, with_reservation)
            for action in ("cancel", "supersede")
            for role in (RunRole.READER, RunRole.WRITER)
            for with_reservation in (False, True)
        ]
        for index, (action, role, with_reservation) in enumerate(cases, start=1):
            with self.subTest(action=action, role=role.value, with_reservation=with_reservation):
                source = f"terminal-accounting-{action}-{role.value}-{with_reservation}"
                repository = f"terminal/accounting/{action}/{role.value}/{with_reservation}"
                task = self.submit(repository=repository, source=source).task
                grant = self.service.claim(
                    owner="ignored-terminal-owner",
                    role=role,
                    repositories=(repository,),
                    lease_seconds=60,
                    actor=WORKER,
                    now=NOW,
                )
                cost = 100 + index
                tokens = 200 + index
                wall = 10 + index
                if with_reservation:
                    self.service.reserve_budget(
                        grant,
                        cost_usd_micros=cost,
                        token_units=tokens,
                        wall_seconds=wall,
                        reason_digest="a" * 64,
                        idempotency_key=f"{index:064x}",
                        actor=WORKER,
                    )
                    expected_reserved_cost += cost
                    expected_reserved_tokens += tokens
                    expected_reserved_wall += wall
                    expected_blocked += 1

                if action == "cancel":
                    command_key = f"{index + 100:064x}"
                    first = self.service.cancel(
                        task.task_id,
                        reason="operator-accounting-terminal",
                        idempotency_key=command_key,
                        actor=OPERATOR,
                        now=NOW,
                    )
                    replay = self.service.cancel(
                        task.task_id,
                        reason="operator-accounting-terminal",
                        idempotency_key=command_key,
                        actor=OPERATOR,
                        now=NOW,
                    )
                    self.assertEqual((first.status, replay.status), (TaskStatus.CANCELLED, TaskStatus.CANCELLED))
                    terminal_state = "cancelled"
                    event_action = "cancelled"
                    audit_action = "cancel"
                else:
                    replacement = self.payload(repository=repository, source=source)
                    replacement["source_digest"] = "e" * 64
                    first = self.service.intake(replacement, actor=OPERATOR, now=NOW)
                    replay = self.service.intake(replacement, actor=OPERATOR, now=NOW)
                    self.assertTrue(first.created)
                    self.assertEqual(replay, first)
                    terminal_state = "superseded"
                    event_action = "superseded"
                    audit_action = "superseded"

                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        """SELECT state,accounting_blocked,cost_reserved_micros,tokens_reserved,
                        wall_reserved_seconds,current_run_id,current_fence,
                        (SELECT count(*) FROM factory.budget_reservations b
                          WHERE b.task_id=t.task_id AND b.released_at IS NULL),
                        (SELECT metadata FROM factory.task_events e
                          WHERE e.task_id=t.task_id AND e.action=%s ORDER BY event_sequence DESC LIMIT 1),
                        (SELECT metadata FROM factory.audit_log a
                          WHERE a.task_id=t.task_id AND a.action=%s ORDER BY audit_id DESC LIMIT 1)
                        FROM factory.tasks t WHERE task_id=%s""",
                        (event_action, audit_action, task.task_id),
                    )
                    row = cursor.fetchone()
                    self.assertEqual(
                        row[:8],
                        (
                            terminal_state,
                            with_reservation,
                            cost if with_reservation else 0,
                            tokens if with_reservation else 0,
                            wall if with_reservation else 0,
                            None,
                            None,
                            1 if with_reservation else 0,
                        ),
                    )
                    self.assertEqual(row[8]["accounting_quarantined"], with_reservation)
                    self.assertEqual(row[9]["accounting_quarantined"], with_reservation)
                    cursor.execute(
                        "SELECT count(*) FROM factory.capacity_allocations WHERE run_id=%s AND released_at IS NULL",
                        (grant.run_id,),
                    )
                    self.assertEqual(cursor.fetchone()[0], 0)
                self.assertTrue(self.store.verify_audit_chain(task.task_id))

        readiness = self.store.readiness()
        self.assertEqual(
            (readiness["status"], readiness["capacity_consistent"], readiness["accounting_consistent"]),
            ("ready", True, True),
        )
        metrics = self.store.metrics()["factory_capacity_budget_kill_and_reconcile_outcomes_total"]
        self.assertEqual(metrics["active_capacity"], 0)
        self.assertEqual(metrics["cost_reserved_micros"], expected_reserved_cost)
        self.assertEqual(metrics["tokens_reserved"], expected_reserved_tokens)
        self.assertEqual(metrics["wall_reserved_seconds"], expected_reserved_wall)
        self.assertEqual(metrics["accounting_blocked"], expected_blocked)

    def test_terminal_accounting_requires_an_explicit_quarantine_marker_for_readiness(self):
        import psycopg

        for state in ("cancelled", "dead", "needs_human"):
            with self.subTest(state=state):
                task = self.submit(source=f"readiness-terminal-accounting-{state}").task
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        """UPDATE factory.tasks SET state=%s,cost_reserved_micros=1,
                        accounting_blocked=false,current_run_id=NULL,current_fence=NULL
                        WHERE task_id=%s""",
                        (state, task.task_id),
                    )
                readiness = self.store.readiness()
                self.assertEqual((readiness["status"], readiness["accounting_consistent"]), ("not_ready", False))
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE factory.tasks SET accounting_blocked=true WHERE task_id=%s",
                        (task.task_id,),
                    )
                readiness = self.store.readiness()
                self.assertEqual((readiness["status"], readiness["accounting_consistent"]), ("ready", True))

    def test_reservation_and_terminalization_race_is_quarantined_or_fenced(self):
        import psycopg

        class PausingReserveStore(PostgresFactoryStore):
            def __init__(self, database_url):
                super().__init__(database_url)
                self.reservation_written = threading.Event()
                self.resume_reservation = threading.Event()
                self._pause_once = True

            def _record_command(self, cursor, key, actor, action, digest, correlation, result):
                super()._record_command(cursor, key, actor, action, digest, correlation, result)
                if action == "reserve_budget" and self._pause_once:
                    self._pause_once = False
                    self.reservation_written.set()
                    if not self.resume_reservation.wait(timeout=5):
                        raise RuntimeError("reservation barrier timed out")

        reservation_first = self.submit(
            repository="terminal/race/reservation-first",
            source="reservation-first",
        ).task
        reservation_first_grant = self.service.claim(
            owner="reservation-race-worker",
            role=RunRole.READER,
            repositories=(reservation_first.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        pausing_reserve_store = PausingReserveStore(self.runtime_url)
        pausing_reserve_service = FactoryService(pausing_reserve_store)
        with ThreadPoolExecutor(max_workers=2) as pool:
            reservation_future = pool.submit(
                pausing_reserve_service.reserve_budget,
                reservation_first_grant,
                cost_usd_micros=101,
                token_units=202,
                wall_seconds=11,
                reason_digest="a" * 64,
                idempotency_key="1" * 64,
                actor=WORKER,
            )
            self.assertTrue(pausing_reserve_store.reservation_written.wait(timeout=5))
            terminal_future = pool.submit(
                self.service.cancel,
                reservation_first.task_id,
                reason="reservation-race",
                idempotency_key="2" * 64,
                actor=OPERATOR,
                now=NOW,
            )
            try:
                with self.assertRaises(FutureTimeout):
                    terminal_future.result(timeout=0.2)
            finally:
                pausing_reserve_store.resume_reservation.set()
            reservation_future.result(timeout=5)
            self.assertEqual(terminal_future.result(timeout=5).status, TaskStatus.CANCELLED)

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT state,accounting_blocked,cost_reserved_micros,
                (SELECT count(*) FROM factory.budget_reservations b
                  WHERE b.task_id=t.task_id AND b.released_at IS NULL)
                FROM factory.tasks t WHERE task_id=%s""",
                (reservation_first.task_id,),
            )
            self.assertEqual(cursor.fetchone(), ("cancelled", True, 101, 1))

        class PausingTerminalStore(PostgresFactoryStore):
            def __init__(self, database_url):
                super().__init__(database_url)
                self.lease_closed = threading.Event()
                self.resume_terminal = threading.Event()
                self._pause_once = True

            def _close_active_lease(self, cursor, task_id):
                super()._close_active_lease(cursor, task_id)
                if self._pause_once:
                    self._pause_once = False
                    self.lease_closed.set()
                    if not self.resume_terminal.wait(timeout=5):
                        raise RuntimeError("terminal barrier timed out")

        terminal_first = self.submit(
            repository="terminal/race/terminal-first",
            source="terminal-first",
        ).task
        terminal_first_grant = self.service.claim(
            owner="reservation-race-worker",
            role=RunRole.READER,
            repositories=(terminal_first.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        pausing_terminal_store = PausingTerminalStore(self.runtime_url)
        pausing_terminal_service = FactoryService(pausing_terminal_store)
        with ThreadPoolExecutor(max_workers=2) as pool:
            terminal_future = pool.submit(
                pausing_terminal_service.cancel,
                terminal_first.task_id,
                reason="terminal-race",
                idempotency_key="3" * 64,
                actor=OPERATOR,
                now=NOW,
            )
            self.assertTrue(pausing_terminal_store.lease_closed.wait(timeout=5))
            reservation_future = pool.submit(
                self.service.reserve_budget,
                terminal_first_grant,
                cost_usd_micros=101,
                token_units=202,
                wall_seconds=11,
                reason_digest="a" * 64,
                idempotency_key="4" * 64,
                actor=WORKER,
            )
            try:
                with self.assertRaises(FutureTimeout):
                    reservation_future.result(timeout=0.2)
            finally:
                pausing_terminal_store.resume_terminal.set()
            self.assertEqual(terminal_future.result(timeout=5).status, TaskStatus.CANCELLED)
            with self.assertRaises(FenceError):
                reservation_future.result(timeout=5)

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT state,accounting_blocked,cost_reserved_micros,
                (SELECT count(*) FROM factory.budget_reservations b
                  WHERE b.task_id=t.task_id AND b.released_at IS NULL)
                FROM factory.tasks t WHERE task_id=%s""",
                (terminal_first.task_id,),
            )
            self.assertEqual(cursor.fetchone(), ("cancelled", False, 0, 0))
        self.assertTrue(self.store.readiness()["accounting_consistent"])

    def test_cancel_racing_claim_releases_reader_and_writer_capacity(self):
        self._assert_claim_terminal_race_releases_capacity("cancel")

    def test_supersede_racing_claim_releases_reader_and_writer_capacity(self):
        self._assert_claim_terminal_race_releases_capacity("supersede")

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

    def test_accepted_infrastructure_retry_limits_are_exact_on_release(self):
        for infrastructure_retries in range(3):
            with self.subTest(infrastructure_retries=infrastructure_retries):
                repository = f"retry/release-{infrastructure_retries}"
                payload = self.payload(
                    repository=repository,
                    source=f"release-limit-{infrastructure_retries}",
                )
                payload["limits"]["infrastructure_retries"] = infrastructure_retries
                self.service.intake(payload, actor=OPERATOR, now=NOW)
                for attempt_no in range(1, infrastructure_retries + 2):
                    grant = self.service.claim(
                        owner=f"release-limit-{infrastructure_retries}-{attempt_no}",
                        role=RunRole.READER,
                        repositories=(repository,),
                        lease_seconds=30,
                        actor=WORKER,
                        now=NOW,
                    )
                    self.assertIsNotNone(grant)
                    status = self.service.release(
                        grant, outcome=FailureClass.WORKER_LOST, actor=WORKER, now=NOW
                    )
                    expected = (
                        TaskStatus.RETRY
                        if attempt_no <= infrastructure_retries
                        else TaskStatus.DEAD
                    )
                    self.assertEqual(status, expected)
                self.assertIsNone(
                    self.service.claim(
                        owner=f"release-limit-{infrastructure_retries}-exhausted",
                        role=RunRole.READER,
                        repositories=(repository,),
                        lease_seconds=30,
                        actor=WORKER,
                        now=NOW,
                    )
                )

    def test_infrastructure_retry_limit_is_persisted_with_frozen_intent(self):
        import psycopg

        source = "persisted-retry-limit"
        first_payload = self.payload(source=source)
        first_payload["limits"]["infrastructure_retries"] = 1
        first = self.service.intake(first_payload, actor=OPERATOR, now=NOW).task
        replacement_payload = self.payload(source=source)
        replacement_payload["limits"]["infrastructure_retries"] = 0
        replacement = self.service.intake(replacement_payload, actor=OPERATOR, now=NOW).task
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT t.task_id,t.infrastructure_retries,
                (i.body #>> '{limits,infrastructure_retries}')::integer,
                t.packet_digest,i.intent_digest,t.state
                FROM factory.tasks t JOIN factory.accepted_intents i ON i.intent_id=t.intent_id
                WHERE t.task_id=ANY(%s) ORDER BY t.generation""",
                ([first.task_id, replacement.task_id],),
            )
            rows = cursor.fetchall()
        self.assertEqual(
            [
                (str(row[0]), row[1], row[2], row[3].strip(), row[4].strip(), row[5])
                for row in rows
            ],
            [
                (
                    first.task_id,
                    1,
                    1,
                    first.packet_digest,
                    first.intent_digest,
                    TaskStatus.SUPERSEDED.value,
                ),
                (
                    replacement.task_id,
                    0,
                    0,
                    replacement.packet_digest,
                    replacement.intent_digest,
                    TaskStatus.QUEUED.value,
                ),
            ],
        )

    def test_accepted_infrastructure_retry_limits_are_exact_on_reconciliation(self):
        import psycopg

        for infrastructure_retries in range(3):
            with self.subTest(infrastructure_retries=infrastructure_retries):
                repository = f"retry/reconcile-{infrastructure_retries}"
                payload = self.payload(
                    repository=repository,
                    source=f"reconcile-limit-{infrastructure_retries}",
                )
                payload["limits"]["infrastructure_retries"] = infrastructure_retries
                task = self.service.intake(payload, actor=OPERATOR, now=NOW).task
                for attempt_no in range(1, infrastructure_retries + 2):
                    grant = self.service.claim(
                        owner=f"reconcile-limit-{infrastructure_retries}-{attempt_no}",
                        role=RunRole.READER,
                        repositories=(repository,),
                        lease_seconds=30,
                        actor=WORKER,
                        now=NOW,
                    )
                    self.assertIsNotNone(grant)
                    with psycopg.connect(DATABASE_URL) as connection:
                        connection.execute(
                            "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",
                            (grant.run_id,),
                        )
                    result = self.service.reconcile(actor=OPERATOR, now=NOW)
                    self.assertEqual((result.candidates, result.repaired), (1, 1))
                    expected = (
                        TaskStatus.RETRY
                        if attempt_no <= infrastructure_retries
                        else TaskStatus.DEAD
                    )
                    self.assertEqual(self.store.get_task(task.task_id).status, expected)
                self.assertEqual(
                    self.service.reconcile(actor=OPERATOR, now=NOW).repaired,
                    0,
                )

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
        execution_stages = metrics["factory_execution_claim_and_stage_outcomes_total"]
        execution_protocol = metrics[
            "factory_execution_protocol_and_proposal_outcomes_total"
        ]
        execution_recovery = metrics[
            "factory_execution_orphan_and_cleanup_outcomes_total"
        ]
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
            set(execution_stages),
            {
                "claimed", "prepared", "running", "collecting", "completed",
                "failed", "needs_human", "cancelled", "orphaned",
            },
        )
        self.assertEqual(
            set(execution_protocol), {"note", "artifact", "usage", "terminal"}
        )
        self.assertEqual(
            set(execution_recovery),
            {"claimed", "orphaned", "cancelled", "workspace_released", "cleanup_failed"},
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
                ) or "read_combined_metrics_snapshot" in text:
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
                other = FactoryService(self.runtime_store())
                other.release(grant, outcome=FailureClass.WORKER_LOST, actor=WORKER, now=NOW)
                proceed.set()
                metrics = future.result(timeout=2)
        leases = metrics["factory_lease_reclaim_and_fence_rejection_total"]["live_leases"]
        capacity = metrics["factory_capacity_budget_kill_and_reconcile_outcomes_total"]["active_capacity"]
        self.assertIn((leases, capacity), {(1, 1), (0, 0)})
        self.assertIn("set local statement_timeout='5s'", statements)
        self.assertIn("set local lock_timeout='500ms'", statements)
        self.assertIn("set local transaction_timeout='3s'", statements)
        data_statements = [item for item in statements if item.startswith("select")]
        self.assertEqual(len(data_statements), 1)
        self.assertIn("read_combined_metrics_snapshot", data_statements[0])

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
        stale_fence_error = {
            "error": "conflict",
            "code": "stale_fence",
            "detail": "lease fence is stale",
        }
        self.assertEqual((response.status_code, response.json()), (409, stale_fence_error))
        self.assertEqual(
            self.store.metrics()["factory_lease_reclaim_and_fence_rejection_total"]["fence_rejected"], 0
        )
        after_unlock = request("unlocked-fence-command")
        self.assertEqual(
            (after_unlock.status_code, after_unlock.json()),
            (409, stale_fence_error),
        )
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

    def test_reconcile_terminalizes_deadline_expired_leases_without_starving_the_page(self):
        import psycopg

        settled_task = self.submit(source="deadline-reconcile-settled").task
        unsettled_task = self.submit(source="deadline-reconcile-unsettled").task
        settled_grant = self.service.claim(
            owner="deadline-worker",
            role=RunRole.READER,
            repositories=(settled_task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        unsettled_grant = self.service.claim(
            owner="deadline-worker",
            role=RunRole.READER,
            repositories=(unsettled_task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        self.service.reserve_budget(
            unsettled_grant,
            cost_usd_micros=101,
            token_units=202,
            wall_seconds=11,
            reason_digest="a" * 64,
            idempotency_key="b" * 64,
            actor=WORKER,
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second'
                WHERE run_id=ANY(%s)""",
                ([settled_grant.run_id, unsettled_grant.run_id],),
            )
            cursor.execute(
                """UPDATE factory.tasks SET deadline_at=clock_timestamp()-interval '1 second'
                WHERE task_id=ANY(%s)""",
                ([settled_task.task_id, unsettled_task.task_id],),
            )
            cursor.execute(
                "UPDATE factory.tasks SET repair_count=repair_limit WHERE task_id=%s",
                (settled_task.task_id,),
            )

        first = self.service.reconcile(actor=OPERATOR, now=NOW)
        replay = self.service.reconcile(actor=OPERATOR, now=NOW)
        self.assertEqual((first.candidates, first.repaired, replay.repaired), (2, 2, 0))
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT task_id,state,accounting_blocked,current_run_id,current_fence,repair_count,
                cost_reserved_micros,tokens_reserved,wall_reserved_seconds,
                (SELECT count(*) FROM factory.budget_reservations b
                  WHERE b.task_id=t.task_id AND b.released_at IS NULL)
                FROM factory.tasks t WHERE task_id=ANY(%s) ORDER BY task_id""",
                ([settled_task.task_id, unsettled_task.task_id],),
            )
            rows = {str(row[0]): row[1:] for row in cursor.fetchall()}
            self.assertEqual(rows[settled_task.task_id], ("dead", False, None, None, 3, 0, 0, 0, 0))
            self.assertEqual(
                rows[unsettled_task.task_id],
                ("needs_human", True, None, None, 0, 101, 202, 11, 1),
            )
            cursor.execute(
                """SELECT t.task_id,e.metadata,a.reason,a.metadata,at.failure_class,at.failure_code,
                r.state,r.released_at IS NOT NULL,ca.released_at IS NOT NULL
                FROM factory.tasks t
                JOIN factory.runs r ON r.task_id=t.task_id
                JOIN factory.attempts at ON at.run_id=r.run_id
                JOIN factory.capacity_allocations ca ON ca.run_id=r.run_id
                JOIN LATERAL (SELECT metadata FROM factory.task_events
                  WHERE task_id=t.task_id AND action='released' ORDER BY event_sequence DESC LIMIT 1) e ON true
                JOIN LATERAL (SELECT reason,metadata FROM factory.audit_log
                  WHERE task_id=t.task_id AND action='release' ORDER BY audit_id DESC LIMIT 1) a ON true
                WHERE t.task_id=ANY(%s) ORDER BY t.task_id""",
                ([settled_task.task_id, unsettled_task.task_id],),
            )
            evidence = {str(row[0]): row[1:] for row in cursor.fetchall()}
            self.assertEqual(
                evidence[settled_task.task_id],
                (
                    {
                        "from_state": "leased",
                        "target": "dead",
                        "operation": "reconcile_expired",
                        "run_id": settled_grant.run_id,
                        "fence": settled_grant.fence,
                        "reason": "deadline_expired",
                        "accounting_quarantined": False,
                    },
                    "deadline_expired",
                    {
                        "from_state": "leased",
                        "target": "dead",
                        "operation": "reconcile_expired",
                        "run_id": settled_grant.run_id,
                        "fence": settled_grant.fence,
                        "reason": "deadline_expired",
                        "accounting_quarantined": False,
                    },
                    "worker_lost",
                    "deadline_expired",
                    "expired",
                    True,
                    True,
                ),
            )
            self.assertEqual(
                evidence[unsettled_task.task_id],
                (
                    {
                        "from_state": "leased",
                        "target": "needs_human",
                        "operation": "reconcile_expired",
                        "run_id": unsettled_grant.run_id,
                        "fence": unsettled_grant.fence,
                        "reason": "deadline_expired",
                        "accounting_quarantined": True,
                    },
                    "deadline_expired",
                    {
                        "from_state": "leased",
                        "target": "needs_human",
                        "operation": "reconcile_expired",
                        "run_id": unsettled_grant.run_id,
                        "fence": unsettled_grant.fence,
                        "reason": "deadline_expired",
                        "accounting_quarantined": True,
                    },
                    "worker_lost",
                    "deadline_expired",
                    "expired",
                    True,
                    True,
                ),
            )
            cursor.execute("SELECT active_count FROM factory.capacity_counters WHERE scope_key='global:reader'")
            self.assertEqual(cursor.fetchone()[0], 0)

        for task, grant in ((settled_task, settled_grant), (unsettled_task, unsettled_grant)):
            self.assertTrue(self.store.verify_audit_chain(task.task_id))
            with self.assertRaises(FenceError):
                self.service.heartbeat(grant, actor=WORKER, now=NOW)
        readiness = self.store.readiness()
        self.assertEqual(
            (readiness["status"], readiness["capacity_consistent"], readiness["accounting_consistent"]),
            ("ready", True, True),
        )
        metrics = self.store.metrics()
        self.assertEqual(metrics["factory_lease_reclaim_and_fence_rejection_total"]["live_leases"], 0)
        self.assertEqual(metrics["factory_lease_reclaim_and_fence_rejection_total"]["reclaimed"], 2)
        self.assertEqual(
            metrics["factory_capacity_budget_kill_and_reconcile_outcomes_total"]["active_capacity"], 0
        )
        self.assertEqual(
            metrics["factory_capacity_budget_kill_and_reconcile_outcomes_total"]["accounting_blocked"], 1
        )

    def test_reconcile_uses_one_deadline_for_the_whole_candidate_page(self):
        import psycopg

        class ShortReconciliationStore(PostgresFactoryStore):
            _RECONCILIATION_TIMEOUT_SECONDS = 0.24
            _RECONCILIATION_COMMIT_RESERVE_SECONDS = 0.06

        tasks = [self.submit(source=f"bounded-total-reconcile-{index}").task for index in range(4)]
        grants = [
            self.service.claim(
                owner="bounded-total-worker",
                role=RunRole.READER,
                repositories=(task.repository_id,),
                lease_seconds=60,
                actor=WORKER,
                now=NOW,
            )
            for task in tasks
        ]
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=ANY(%s)",
                ([grant.run_id for grant in grants],),
            )
            cursor.execute(
                """CREATE FUNCTION factory.delay_reconcile_release() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN PERFORM pg_sleep(0.075); RETURN NEW; END $$"""
            )
            cursor.execute(
                """CREATE TRIGGER delay_reconcile_release BEFORE UPDATE ON factory.runs
                FOR EACH ROW WHEN (OLD.released_at IS NULL AND NEW.released_at IS NOT NULL)
                EXECUTE FUNCTION factory.delay_reconcile_release()"""
            )
        try:
            first = FactoryService(ShortReconciliationStore(self.runtime_url)).reconcile(actor=OPERATOR, now=NOW)
        finally:
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute("DROP TRIGGER delay_reconcile_release ON factory.runs")
                cursor.execute("DROP FUNCTION factory.delay_reconcile_release()")
        self.assertEqual(first.candidates, 4)
        self.assertGreater(first.repaired, 0)
        self.assertLess(first.repaired, first.candidates)
        second = FactoryService(ShortReconciliationStore(self.runtime_url)).reconcile(
            actor=OPERATOR,
            now=NOW,
            cursor=first.cursor,
        )
        self.assertEqual(first.repaired + second.repaired, 4)
        self.assertEqual(self.service.reconcile(actor=OPERATOR, now=NOW).repaired, 0)

    def test_reconcile_transaction_timeout_rolls_back_the_whole_partial_batch(self):
        import psycopg

        class ExpiringTransactionStore(PostgresFactoryStore):
            _RECONCILIATION_TIMEOUT_SECONDS = 0.2
            _RECONCILIATION_COMMIT_RESERVE_SECONDS = 0.02

            def __init__(self, database_url):
                super().__init__(database_url)
                self._delay_once = True

            def _set_reconciliation_statement_timeout(self, cursor, deadline, *, reserve_seconds=0.0):
                configured = super()._set_reconciliation_statement_timeout(
                    cursor,
                    deadline,
                    reserve_seconds=reserve_seconds,
                )
                if configured and reserve_seconds and self._delay_once:
                    self._delay_once = False
                    time.sleep(0.3)
                return configured

        tasks = [self.submit(source=f"transaction-timeout-{index}").task for index in range(2)]
        grants = [
            self.service.claim(
                owner="transaction-timeout-worker",
                role=RunRole.READER,
                repositories=(task.repository_id,),
                lease_seconds=60,
                actor=WORKER,
                now=NOW,
            )
            for task in tasks
        ]
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=ANY(%s)",
                ([grant.run_id for grant in grants],),
            )
        with self.assertRaisesRegex(StoreError, "database unavailable"):
            FactoryService(ExpiringTransactionStore(self.runtime_url)).reconcile(actor=OPERATOR, now=NOW)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                (SELECT count(*) FROM factory.runs WHERE run_id=ANY(%s) AND released_at IS NULL),
                (SELECT count(*) FROM factory.capacity_allocations WHERE run_id=ANY(%s) AND released_at IS NULL),
                (SELECT count(*) FROM factory.reconciliation_runs)""",
                ([grant.run_id for grant in grants], [grant.run_id for grant in grants]),
            )
            self.assertEqual(cursor.fetchone(), (2, 2, 0))
        self.assertTrue(self.store.readiness()["capacity_consistent"])

    def test_reconcile_terminalizes_expired_queued_and_retry_tasks_without_runs(self):
        import psycopg

        retry_task = self.submit(source="deadline-unleased-retry").task
        queued_task = self.submit(source="deadline-unleased-queued").task
        blocked_task = self.submit(source="deadline-unleased-blocked").task
        orphaned_task = self.submit(
            repository="deadline/unleased/orphaned",
            source="deadline-unleased-orphaned",
        ).task
        retry_grant = self.service.claim(
            owner="deadline-unleased-worker",
            role=RunRole.READER,
            repositories=(retry_task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        self.assertEqual(retry_grant.task_id, retry_task.task_id)
        self.assertEqual(
            self.service.release(
                retry_grant,
                outcome=FailureClass.WORKER_LOST,
                actor=WORKER,
                now=NOW,
            ),
            TaskStatus.RETRY,
        )
        orphaned_grant = self.service.claim(
            owner="deadline-unleased-worker",
            role=RunRole.READER,
            repositories=(orphaned_task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """UPDATE factory.tasks SET deadline_at=clock_timestamp()-interval '1 second'
                WHERE task_id=ANY(%s)""",
                ([retry_task.task_id, queued_task.task_id, blocked_task.task_id],),
            )
            cursor.execute(
                """UPDATE factory.tasks SET cost_reserved_micros=1
                WHERE task_id=%s""",
                (blocked_task.task_id,),
            )
            cursor.execute(
                """UPDATE factory.tasks SET state='queued',current_run_id=NULL,current_fence=NULL,
                deadline_at=clock_timestamp()-interval '1 second' WHERE task_id=%s""",
                (orphaned_task.task_id,),
            )
            cursor.execute(
                """UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second'
                WHERE run_id=%s""",
                (orphaned_grant.run_id,),
            )
        first = self.service.reconcile(actor=OPERATOR, now=NOW)
        orphan_deadline = self.service.reconcile(
            actor=OPERATOR,
            now=NOW,
            cursor=first.cursor,
        )
        replay = self.service.reconcile(
            actor=OPERATOR,
            now=NOW,
            cursor=orphan_deadline.cursor,
        )
        self.assertEqual(
            (
                first.candidates,
                first.repaired,
                orphan_deadline.candidates,
                orphan_deadline.repaired,
                replay.repaired,
            ),
            (4, 4, 0, 0, 0),
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT task_id,state,accounting_blocked,current_run_id,current_fence,
                repair_count,terminal_at IS NOT NULL
                FROM factory.tasks WHERE task_id=ANY(%s) ORDER BY task_id""",
                ([retry_task.task_id, queued_task.task_id, blocked_task.task_id, orphaned_task.task_id],),
            )
            states = {str(row[0]): row[1:] for row in cursor.fetchall()}
            self.assertEqual(states[retry_task.task_id], ("dead", False, None, None, 0, True))
            self.assertEqual(states[queued_task.task_id], ("dead", False, None, None, 0, True))
            self.assertEqual(
                states[blocked_task.task_id],
                ("needs_human", True, None, None, 0, False),
            )
            self.assertEqual(states[orphaned_task.task_id], ("dead", False, None, None, 0, True))
            cursor.execute(
                """SELECT task_id,
                (SELECT count(*) FROM factory.task_events e
                  WHERE e.task_id=t.task_id AND e.action='deadline_expired' AND e.mandatory_cleanup),
                (SELECT count(*) FROM factory.audit_log a
                  WHERE a.task_id=t.task_id AND a.action='reconcile_deadline'
                    AND a.reason='deadline_expired')
                FROM factory.tasks t WHERE task_id=ANY(%s) ORDER BY task_id""",
                ([retry_task.task_id, queued_task.task_id, blocked_task.task_id, orphaned_task.task_id],),
            )
            self.assertEqual({str(row[0]): row[1:] for row in cursor.fetchall()}, {
                retry_task.task_id: (1, 1),
                queued_task.task_id: (1, 1),
                blocked_task.task_id: (1, 1),
                orphaned_task.task_id: (1, 1),
            })
        for task in (retry_task, queued_task, blocked_task, orphaned_task):
            self.assertTrue(self.store.verify_audit_chain(task.task_id))
        self.assertEqual(self.store.readiness()["status"], "ready")

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

    def test_schema_012_retry_exhaustion_claim_is_audited_without_advancing_fence(self):
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        connection_parameters = conninfo_to_dict(DATABASE_URL)
        migrations = discover_migrations()
        for infrastructure_retries in (0, 1):
            with self.subTest(infrastructure_retries=infrastructure_retries):
                database_name = f"factory_retry_upgrade_{uuid.uuid4().hex[:12]}"
                upgrade_url = make_conninfo(**{**connection_parameters, "dbname": database_name})
                with psycopg.connect(DATABASE_URL, autocommit=True) as admin:
                    admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
                try:
                    task_id, intent_id = uuid.uuid4(), uuid.uuid4()
                    repository_id = f"upgrade/retry-limit-{infrastructure_retries}"
                    source_id = f"legacy-retry-limit-{infrastructure_retries}"
                    attempt_count = infrastructure_retries + 1
                    with psycopg.connect(upgrade_url) as connection, connection.cursor() as cursor:
                        cursor.execute("CREATE SCHEMA factory")
                        cursor.execute(
                            """CREATE TABLE factory.schema_migrations (
                            version integer PRIMARY KEY, name text UNIQUE NOT NULL,
                            sha256 char(64) NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())"""
                        )
                        for migration in migrations[:12]:
                            cursor.execute(migration.sql)
                            cursor.execute(
                                "INSERT INTO factory.schema_migrations(version,name,sha256) VALUES (%s,%s,%s)",
                                (migration.version, migration.name, migration.sha256),
                            )
                        cursor.execute(
                            """INSERT INTO factory.intake_identities(repository_id,source_type,source_id)
                            VALUES (%s,'manual',%s)""",
                            (repository_id, source_id),
                        )
                        cursor.execute(
                            """INSERT INTO factory.accepted_intents
                            (intent_id,intent_digest,idempotency_key,repository_id,source_type,source_id,
                             source_digest,exact_base_sha,spec_digest,architecture_digest,governance_digest,
                             policy_digest,body)
                            VALUES (%s,%s,%s,%s,'manual',%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
                            (
                                intent_id,
                                uuid.uuid4().hex * 2,
                                uuid.uuid4().hex * 2,
                                repository_id,
                                source_id,
                                uuid.uuid4().hex * 2,
                                uuid.uuid4().hex + uuid.uuid4().hex[:8],
                                uuid.uuid4().hex * 2,
                                uuid.uuid4().hex * 2,
                                uuid.uuid4().hex * 2,
                                uuid.uuid4().hex * 2,
                                f'{{"limits":{{"infrastructure_retries":{infrastructure_retries}}}}}',
                            ),
                        )
                        cursor.execute(
                            """INSERT INTO factory.tasks
                            (task_id,intent_id,repository_id,source_type,source_id,state,generation,
                             packet_digest,deadline_at,cost_limit_micros,token_limit,output_limit_bytes,
                             event_limit,accounting_blocked,repair_limit,repair_count,wall_limit_seconds)
                            VALUES (%s,%s,%s,'manual',%s,'retry',1,%s,now()+interval '1 hour',
                             25000000,2000000,10000000,100,false,3,0,14400)""",
                            (task_id, intent_id, repository_id, source_id, uuid.uuid4().hex * 2),
                        )
                        for attempt_no in range(1, attempt_count + 1):
                            run_id = uuid.uuid4()
                            cursor.execute(
                                """INSERT INTO factory.runs
                                (run_id,task_id,owner_id,role,packet_digest,fence,state,lease_expires_at,
                                 deadline_at,released_at)
                                SELECT %s,task_id,'legacy-worker','reader',packet_digest,%s,'failed',
                                  now()-interval '1 minute',deadline_at,now()
                                FROM factory.tasks WHERE task_id=%s""",
                                (run_id, attempt_no, task_id),
                            )
                            cursor.execute(
                                """INSERT INTO factory.attempts
                                (attempt_id,task_id,run_id,attempt_no,failure_class,failure_code,
                                 failure_digest,finished_at)
                                VALUES (%s,%s,%s,%s,'worker_lost','worker_lost',%s,now())""",
                                (uuid.uuid4(), task_id, run_id, attempt_no, uuid.uuid4().hex * 2),
                            )

                    self.assertEqual(
                        [item.version for item in self.migrate(upgrade_url)],
                        [13, 14, 15, 16, 17, 18],
                    )
                    upgraded_store = self.runtime_store(upgrade_url)
                    upgraded_service = FactoryService(upgraded_store)
                    with psycopg.connect(upgrade_url) as connection, connection.cursor() as cursor:
                        cursor.execute(
                            """SELECT state,infrastructure_retries,terminal_at IS NOT NULL,
                            (SELECT count(*) FROM factory.lease_sequences WHERE task_id=t.task_id),
                            (SELECT count(*) FROM factory.task_events WHERE task_id=t.task_id),
                            (SELECT count(*) FROM factory.audit_log WHERE task_id=t.task_id),
                            (SELECT count(*) FROM factory.runs WHERE task_id=t.task_id),
                            (SELECT count(*) FROM factory.attempts WHERE task_id=t.task_id),
                            (SELECT dead FROM factory.metric_counters),
                            (SELECT retry FROM factory.metric_counters)
                            FROM factory.tasks t WHERE task_id=%s""",
                            (task_id,),
                        )
                        self.assertEqual(
                            cursor.fetchone(),
                            ("retry", infrastructure_retries, False, 0, 0, 0, attempt_count, attempt_count, 0, 1),
                        )

                    command_key = str(infrastructure_retries + 7) * 64
                    correlation_id = f"migration-013-retry-exhausted-{infrastructure_retries}"
                    claim = partial(
                        upgraded_service.claim,
                        owner=f"post-upgrade-worker-{infrastructure_retries}",
                        role=RunRole.READER,
                        repositories=(repository_id,),
                        lease_seconds=60,
                        actor=WORKER,
                        now=NOW,
                        idempotency_key=command_key,
                        correlation_id=correlation_id,
                    )
                    self.assertIsNone(claim())
                    self.assertIsNone(claim())
                    self.assertTrue(upgraded_store.verify_audit_chain(str(task_id)))

                    with psycopg.connect(upgrade_url) as connection, connection.cursor() as cursor:
                        cursor.execute(
                            """SELECT state,infrastructure_retries,terminal_at IS NOT NULL,
                            (SELECT count(*) FROM factory.lease_sequences WHERE task_id=t.task_id),
                            (SELECT count(*) FROM factory.task_events WHERE task_id=t.task_id),
                            (SELECT count(*) FROM factory.audit_log WHERE task_id=t.task_id),
                            (SELECT count(*) FROM factory.runs WHERE task_id=t.task_id),
                            (SELECT count(*) FROM factory.attempts WHERE task_id=t.task_id),
                            (SELECT dead FROM factory.metric_counters),
                            (SELECT retry FROM factory.metric_counters),
                            (SELECT transition_events FROM factory.metric_counters),
                            (SELECT count(*) FROM factory.command_results WHERE idempotency_key=%s)
                            FROM factory.tasks t WHERE task_id=%s""",
                            (command_key, task_id),
                        )
                        self.assertEqual(
                            cursor.fetchone(),
                            (
                                "dead", infrastructure_retries, True, 0, 1, 1,
                                attempt_count, attempt_count, 1, 0, 1, 1,
                            ),
                        )
                        cursor.execute(
                            """SELECT action,actor_id,mandatory_cleanup,metadata
                            FROM factory.task_events WHERE task_id=%s""",
                            (task_id,),
                        )
                        self.assertEqual(
                            cursor.fetchone(),
                            (
                                "retry_exhausted",
                                WORKER.actor_id,
                                True,
                                {
                                    "attempts": attempt_count,
                                    "infrastructure_retries": infrastructure_retries,
                                    "from_state": "retry",
                                    "target": "dead",
                                    "operation": "retry_exhausted",
                                },
                            ),
                        )
                        cursor.execute(
                            """SELECT action,resource,reason,correlation_id,run_id,metadata,digest_version
                            FROM factory.audit_log WHERE task_id=%s""",
                            (task_id,),
                        )
                        self.assertEqual(
                            cursor.fetchone(),
                            (
                                "claim",
                                f"task:{task_id}",
                                "retry_exhausted",
                                correlation_id,
                                None,
                                {
                                    "attempts": attempt_count,
                                    "infrastructure_retries": infrastructure_retries,
                                    "from_state": "retry",
                                    "target": "dead",
                                    "operation": "retry_exhausted",
                                },
                                2,
                            ),
                        )
                finally:
                    with psycopg.connect(DATABASE_URL, autocommit=True) as admin:
                        admin.execute(
                            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",
                            (database_name,),
                        )
                        admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name)))

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
                for legacy_intent_id, source, body in (
                    (blocked_intent_id, "legacy-blocked-zero", "{}"),
                    (ready_intent_id, "legacy-ready-reservation", "{}"),
                    (
                        ready_new_intent_id,
                        "legacy-ready-reservation",
                        '{"limits":{"infrastructure_retries":0}}',
                    ),
                ):
                    cursor.execute(
                        """INSERT INTO factory.accepted_intents
                        (intent_id,intent_digest,idempotency_key,repository_id,source_type,source_id,source_digest,
                         exact_base_sha,spec_digest,architecture_digest,governance_digest,policy_digest,body)
                        VALUES (%s,%s,%s,'owner/repository','manual',%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
                        (
                            legacy_intent_id, uuid.uuid4().hex * 2, uuid.uuid4().hex * 2, source,
                            uuid.uuid4().hex * 2, uuid.uuid4().hex + uuid.uuid4().hex[:8],
                            uuid.uuid4().hex * 2, uuid.uuid4().hex * 2,
                            uuid.uuid4().hex * 2, uuid.uuid4().hex * 2, body,
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

            applied = self.migrate(upgrade_url)
            upgraded_store = self.runtime_store(upgrade_url)
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
                    [9, 10, 11, 12, 13, 14, 15, 16, 17, 18], "ready", 18, True,
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
                    "SELECT task_id,infrastructure_retries FROM factory.tasks ORDER BY task_id"
                )
                self.assertEqual(
                    dict(cursor.fetchall()),
                    {
                        task_id: 2,
                        blocked_task_id: 2,
                        ready_task_id: 2,
                        ready_new_task_id: 0,
                    },
                )
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
            self.assertEqual(self.migrate(upgrade_url), ())
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
                BEGIN IF current_setting('statement_timeout')::interval > interval '5 seconds'
                  OR current_setting('statement_timeout')::interval <= interval '0 seconds'
                  THEN RAISE EXCEPTION 'unbounded reconciliation'; END IF; RETURN NEW; END $$"""
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

    def test_runtime_api_connection_contention_is_bounded_and_typed(self):
        import psycopg
        from fastapi.testclient import TestClient
        from unittest import mock

        reader = Actor(
            "connection-reader",
            "client",
            frozenset({"task:read"}),
            frozenset({"*"}),
        )
        token = "-".join(("connection", "contention", "credential"))
        client = TestClient(
            create_app(FactoryService(self.runtime_store()), Authenticator({token: reader})),
            raise_server_exceptions=False,
        )
        headers = {"Authorization": f"Bearer {token}", "X-Correlation-ID": "connection-contention"}

        with mock.patch(
            "psycopg.connect",
            side_effect=psycopg.OperationalError("injected connection slot contention"),
        ) as connect:
            responses = (
                client.get(f"/v1/tasks/{uuid.uuid4()}", headers=headers),
                client.get("/health/ready"),
            )

        for response in responses:
            self.assertEqual(response.status_code, 503)
            self.assertEqual(
                response.json(),
                {
                    "error": "unavailable",
                    "code": "database",
                    "detail": "database unavailable",
                },
            )
            self.assertNotIn("connection slot contention", response.text)
        self.assertEqual(connect.call_count, 2)
        for call in connect.call_args_list:
            self.assertEqual(call.kwargs["connect_timeout"], 5)
            self.assertIn("lock_timeout=", call.kwargs["options"])
            self.assertIn("statement_timeout=", call.kwargs["options"])

    def test_runtime_api_reads_and_grant_checks_are_bounded_under_query_contention(self):
        import psycopg
        from fastapi.testclient import TestClient

        class FastBoundStore(PostgresFactoryStore):
            _MUTATION_LOCK_TIMEOUT = "100ms"
            _MUTATION_STATEMENT_TIMEOUT = "500ms"

        task = self.submit(source="runtime-query-contention").task
        grant = self.service.claim(
            owner="ignored",
            role=RunRole.READER,
            repositories=(task.repository_id,),
            lease_seconds=60,
            actor=WORKER,
            now=NOW,
        )
        bounded_service = FactoryService(FastBoundStore(self.runtime_url))
        reader = Actor(
            "query-reader",
            "client",
            frozenset({"task:read", "task:list"}),
            frozenset({"*"}),
        )
        reader_token = "-".join(("query", "reader", "credential"))
        worker_token = "-".join(("query", "worker", "credential"))
        operator_token = "-".join(("query", "operator", "credential"))
        authenticator = Authenticator(
            {reader_token: reader, worker_token: WORKER, operator_token: OPERATOR}
        )
        client = TestClient(create_app(bounded_service, authenticator), raise_server_exceptions=False)
        grant_body = {
            "task_id": grant.task_id,
            "run_id": grant.run_id,
            "owner": grant.owner,
            "role": grant.role.value,
            "fence": grant.fence,
            "expires_at": grant.expires_at.isoformat().replace("+00:00", "Z"),
            "packet_digest": grant.packet_digest,
        }

        requests = (
            (
                "readiness",
                "LOCK TABLE factory.schema_migrations IN ACCESS EXCLUSIVE MODE",
                lambda: client.get("/health/ready"),
            ),
            (
                "get_task",
                "LOCK TABLE factory.tasks IN ACCESS EXCLUSIVE MODE",
                lambda: client.get(
                    f"/v1/tasks/{task.task_id}",
                    headers={
                        "Authorization": f"Bearer {reader_token}",
                        "X-Correlation-ID": "bounded-get-task",
                    },
                ),
            ),
            (
                "list_tasks",
                "LOCK TABLE factory.tasks IN ACCESS EXCLUSIVE MODE",
                lambda: client.get(
                    "/v1/tasks",
                    params={"repository_id": task.repository_id},
                    headers={
                        "Authorization": f"Bearer {reader_token}",
                        "X-Correlation-ID": "bounded-list-tasks",
                    },
                ),
            ),
            (
                "grant_check",
                "LOCK TABLE factory.tasks IN ACCESS EXCLUSIVE MODE",
                lambda: client.post(
                    "/v1/heartbeats",
                    json=grant_body,
                    headers={
                        "Authorization": f"Bearer {worker_token}",
                        "Idempotency-Key": "bounded-grant-check",
                        "X-Correlation-ID": "bounded-grant-check",
                    },
                ),
            ),
            (
                "cancel",
                "LOCK TABLE factory.tasks IN ACCESS EXCLUSIVE MODE",
                lambda: client.post(
                    f"/v1/tasks/{task.task_id}/cancel",
                    json={"reason": "bounded-cancel"},
                    headers={
                        "Authorization": f"Bearer {operator_token}",
                        "Idempotency-Key": "bounded-cancel",
                        "X-Correlation-ID": "bounded-cancel",
                    },
                ),
            ),
        )

        for name, lock_statement, request in requests:
            with self.subTest(name=name):
                blocker = psycopg.connect(DATABASE_URL)
                blocker.execute(lock_statement)
                pool = ThreadPoolExecutor(max_workers=1)
                future = pool.submit(request)
                started = time.monotonic()
                try:
                    try:
                        response = future.result(timeout=0.75)
                    except FutureTimeout:
                        blocker.rollback()
                        blocker.close()
                        future.result(timeout=2)
                        self.fail(f"{name} exceeded the bounded database deadline")
                    elapsed = time.monotonic() - started
                finally:
                    if not blocker.closed:
                        blocker.rollback()
                        blocker.close()
                    pool.shutdown(wait=True)
                self.assertEqual(
                    (response.status_code, response.json()),
                    (
                        503,
                        {
                            "error": "unavailable",
                            "code": "database",
                            "detail": "database unavailable",
                        },
                    ),
                )
                self.assertLess(elapsed, 0.75)

    def test_cancel_uses_one_transaction_for_authorization_replay_and_projection(self):
        class CountingStore(PostgresFactoryStore):
            def __init__(self, database_url):
                super().__init__(database_url)
                self.connection_count = 0

            def _connect(self, **kwargs):
                self.connection_count += 1
                return super()._connect(**kwargs)

        task = self.submit(source="single-transaction-cancel").task
        counting_store = CountingStore(self.runtime_url)
        service = FactoryService(counting_store)
        key = "1" * 64

        first = service.cancel(
            task.task_id,
            reason="operator",
            idempotency_key=key,
            actor=OPERATOR,
            now=NOW,
        )
        self.assertEqual((first.status, counting_store.connection_count), (TaskStatus.CANCELLED, 1))

        counting_store.connection_count = 0
        replay = service.cancel(
            task.task_id,
            reason="operator",
            idempotency_key=key,
            actor=OPERATOR,
            now=NOW,
        )
        self.assertEqual((replay, counting_store.connection_count), (first, 1))

        other = self.submit(source="single-transaction-cancel-denied").task
        scoped = Actor(
            "scoped-operator",
            "operator",
            frozenset({"task:cancel"}),
            frozenset({"other/repository"}),
        )
        counting_store.connection_count = 0
        with self.assertRaises(AuthorizationError):
            service.cancel(
                other.task_id,
                reason="denied",
                idempotency_key="2" * 64,
                actor=scoped,
                now=NOW,
            )
        self.assertEqual(counting_store.connection_count, 1)
        self.assertEqual(self.store.get_task(other.task_id).status, TaskStatus.QUEUED)

        counting_store.connection_count = 0
        with self.assertRaises(KeyError):
            service.cancel(
                str(uuid.uuid4()),
                reason="missing",
                idempotency_key="3" * 64,
                actor=OPERATOR,
                now=NOW,
            )
        self.assertEqual(counting_store.connection_count, 1)

    def test_api_mutation_families_fail_bounded_under_database_lock_contention(self):
        import psycopg

        class FastBoundStore(PostgresFactoryStore):
            _MUTATION_LOCK_TIMEOUT = "100ms"
            _MUTATION_STATEMENT_TIMEOUT = "500ms"

        bounded = FastBoundStore(self.runtime_url)
        operations = []
        for index, name in enumerate(("heartbeat", "release", "reserve", "observe"), start=1):
            repository = f"bounds/{name}"
            task = self.submit(repository=repository, source=f"bounded-{name}").task
            grant = self.service.claim(
                owner="bounded-worker",
                role=RunRole.READER,
                repositories=(repository,),
                lease_seconds=60,
                actor=WORKER,
                now=NOW,
            )
            key = f"{index:064x}"
            if name == "heartbeat":
                operation = partial(bounded.heartbeat, grant, WORKER, NOW, idempotency_key=key)
            elif name == "release":
                operation = partial(
                    bounded.release,
                    grant, FailureClass.WORKER_LOST, WORKER, NOW, idempotency_key=key
                )
            elif name == "reserve":
                operation = partial(bounded.reserve_budget, grant, 0, 0, 0, "a" * 64, key, WORKER)
            else:
                operation = partial(
                    bounded.observe_usage,
                    grant, "bounded-provider-call", "b" * 64, 0, 0, 0, WORKER,
                    idempotency_key=key,
                )
            operations.append((name, "task", task.task_id, operation))

        cancel_task = self.submit(repository="bounds/cancel", source="bounded-cancel").task
        operations.append(
            (
                "cancel",
                "task",
                cancel_task.task_id,
                lambda: bounded.cancel(
                    cancel_task.task_id, "bounded", "5" * 64, OPERATOR, NOW
                ),
            )
        )
        kill_key = "6" * 64
        operations.append(
            (
                "kill",
                "advisory",
                kill_key,
                lambda: bounded.set_kill(
                    "repository:bounds/kill", False, "bounded", kill_key, OPERATOR, NOW
                ),
            )
        )

        outcomes = {}
        for name, lock_kind, identity, operation in operations:
            with self.subTest(name=name):
                blocker = psycopg.connect(DATABASE_URL)
                if lock_kind == "task":
                    blocker.execute(
                        "SELECT task_id FROM factory.tasks WHERE task_id=%s FOR UPDATE", (identity,)
                    )
                else:
                    blocker.execute(
                        "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (identity,)
                    )
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(operation)
                    try:
                        future.result(timeout=0.5)
                    except StoreError as exc:
                        outcomes[name] = type(exc).__name__
                    except FutureTimeout:
                        outcomes[name] = "client_timeout"
                    except Exception as exc:
                        outcomes[name] = f"raw:{type(exc).__name__}"
                    else:
                        outcomes[name] = "returned"
                    finally:
                        blocker.rollback()
                        blocker.close()
        self.assertEqual(outcomes, {name: "StoreUnavailable" for name, *_rest in operations})

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
            execution_packet_digest = "e" * 64
            cursor.execute(
                """INSERT INTO factory.execution_packets
                (packet_digest,task_id,run_id,legacy_packet_digest,provider_id,body)
                VALUES (%s,%s,%s,%s,'plan-provider','{}'::jsonb)""",
                (
                    execution_packet_digest,
                    task.task_id,
                    grant.run_id,
                    grant.packet_digest,
                ),
            )
            cursor.execute(
                """INSERT INTO factory.execution_manifests
                (manifest_digest,task_id,run_id,packet_digest,workspace_handle,stage,body)
                VALUES (%s,%s,%s,%s,%s,'prepared','{}'::jsonb)""",
                (
                    "f" * 64,
                    task.task_id,
                    grant.run_id,
                    execution_packet_digest,
                    "workspace:" + "a" * 64,
                ),
            )
            cursor.executemany(
                """INSERT INTO factory.execution_proposals
                (proposal_id,task_id,run_id,packet_digest,producer_sequence,idempotency_key,proposal_kind,body)
                VALUES (gen_random_uuid(),%s,%s,%s,%s,%s,'note','{}'::jsonb)""",
                [
                    (
                        task.task_id,
                        grant.run_id,
                        execution_packet_digest,
                        index,
                        f"{30_000 + index:064x}",
                    )
                    for index in range(1, 501)
                ],
            )
            cursor.execute(
                """INSERT INTO factory.execution_proposals
                (proposal_id,task_id,run_id,packet_digest,producer_sequence,idempotency_key,proposal_kind,body)
                VALUES (gen_random_uuid(),%s,%s,%s,501,%s,'terminal','{}'::jsonb)""",
                (task.task_id, grant.run_id, execution_packet_digest, "d" * 64),
            )
            cursor.execute(
                """ANALYZE factory.tasks; ANALYZE factory.runs; ANALYZE factory.audit_log;
                ANALYZE factory.usage_observations; ANALYZE factory.budget_reservations;
                ANALYZE factory.execution_proposals"""
            )
            cursor.execute("SET LOCAL enable_seqscan=off")
            statements = {
                "claim": ("SELECT task_id FROM factory.tasks WHERE state IN ('queued','retry') ORDER BY created_at,task_id LIMIT 1", ()),
                "audit": ("SELECT * FROM factory.audit_log WHERE task_id=%s ORDER BY audit_id LIMIT 100001", (task.task_id,)),
                "usage": ("SELECT sum(output_bytes) FROM factory.usage_observations WHERE task_id=%s", (task.task_id,)),
                "reservation": ("SELECT sum(cost_usd_micros) FROM factory.budget_reservations WHERE task_id=%s AND run_id=%s AND released_at IS NULL", (task.task_id, grant.run_id)),
                "reconcile": ("SELECT task_id FROM factory.runs WHERE released_at IS NULL AND lease_expires_at<=clock_timestamp() ORDER BY task_id LIMIT 100", ()),
                "proposal_last": ("SELECT producer_sequence FROM factory.execution_proposals WHERE run_id=%s ORDER BY producer_sequence DESC LIMIT 1", (grant.run_id,)),
                "proposal_terminal": ("SELECT 1 FROM factory.execution_proposals WHERE run_id=%s AND proposal_kind='terminal'", (grant.run_id,)),
            }
            expected = {
                "claim": {"tasks_claim_queue"},
                "audit": {"audit_log_task_order"},
                "usage": {"usage_observations_task_run"},
                "reservation": {"budget_reservations_task_run_active"},
                "reconcile": {"runs_reconcile_keyset", "runs_expired_reconcile"},
                "proposal_last": {"execution_proposals_run_id_producer_sequence_key"},
                "proposal_terminal": {"execution_proposals_one_terminal"},
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
        from adaptive_factory.admin import bootstrap_local

        result = bootstrap_local(
            DATABASE_URL,
            self.runtime_login,
            self.runtime_password,
            self.runtime_url,
        )
        self.assertEqual(result["database_role"], "factory_runtime")
        self.assertEqual(result["schema_version"], 18)
        self.assertEqual(
            PostgresMigrator(DATABASE_URL).apply(
                expected_runtime_login=self.runtime_login
            ),
            (),
        )
        with psycopg.connect(self.runtime_url) as connection, connection.cursor() as cursor:
            cursor.execute("SET ROLE factory_runtime")
            cursor.execute("SELECT session_user,current_user")
            self.assertEqual(
                cursor.fetchone(), (self.runtime_login, "factory_runtime")
            )

    def test_bootstrap_rejects_unsafe_factory_role_attributes_and_memberships(self):
        import psycopg
        from adaptive_factory.admin import BootstrapError, bootstrap_local
        from psycopg import sql

        def assert_rejected() -> None:
            with self.assertRaises(BootstrapError):
                bootstrap_local(
                    DATABASE_URL,
                    self.runtime_login,
                    self.runtime_password,
                    self.runtime_url,
                )

        with self.subTest(boundary="unsafe capability attribute"):
            try:
                with psycopg.connect(DATABASE_URL) as connection:
                    connection.execute("ALTER ROLE factory_runtime CREATEDB")
                assert_rejected()
            finally:
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute("ALTER ROLE factory_runtime NOCREATEDB")

        with self.subTest(boundary="factory role is member of another role"):
            parent = "factory_unexpected_parent_test"
            try:
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(sql.SQL("CREATE ROLE {} NOLOGIN NOINHERIT").format(sql.Identifier(parent)))
                    cursor.execute(
                        sql.SQL("GRANT {} TO factory_runtime").format(sql.Identifier(parent))
                    )
                assert_rejected()
            finally:
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        sql.SQL("REVOKE {} FROM factory_runtime").format(sql.Identifier(parent))
                    )
                    cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(parent)))

        with self.subTest(boundary="factory role has an unexpected member"):
            member = "factory_unexpected_member_test"
            try:
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(sql.SQL("CREATE ROLE {} NOLOGIN NOINHERIT").format(sql.Identifier(member)))
                    cursor.execute(
                        sql.SQL("GRANT factory_runtime TO {}").format(sql.Identifier(member))
                    )
                assert_rejected()
            finally:
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        sql.SQL("REVOKE factory_runtime FROM {}").format(sql.Identifier(member))
                    )
                    cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(member)))

    def test_bootstrap_rejects_service_login_with_unexpected_membership(self):
        import psycopg
        from adaptive_factory.admin import BootstrapError, bootstrap_local
        from psycopg import sql

        login = self.runtime_login
        password = self.runtime_password
        unexpected_role = "factory_unexpected_service_role"
        runtime_url = self.runtime_url
        try:
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("CREATE ROLE {} NOLOGIN NOINHERIT").format(sql.Identifier(unexpected_role))
                )
                cursor.execute(
                    sql.SQL("GRANT {} TO {}").format(
                        sql.Identifier(unexpected_role), sql.Identifier(login)
                    )
                )
            with self.assertRaises(BootstrapError):
                bootstrap_local(DATABASE_URL, login, password, runtime_url)
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT parent.rolname
                    FROM pg_auth_members membership
                    JOIN pg_roles parent ON parent.oid=membership.roleid
                    JOIN pg_roles member ON member.oid=membership.member
                    WHERE member.rolname=%s ORDER BY parent.rolname""",
                    (login,),
                )
                self.assertEqual(
                    cursor.fetchall(), [("factory_runtime",), (unexpected_role,)]
                )
        finally:
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("REVOKE {} FROM {}").format(
                        sql.Identifier(unexpected_role), sql.Identifier(login)
                    )
                )
                cursor.execute(
                    sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(unexpected_role))
                )

    def test_roles_are_isolated_and_audit_is_append_only_and_verifiable(self):
        task = self.submit(source="audit-role-check").task
        self.assertTrue(self.store.verify_audit_chain(task.task_id))
        self.assertEqual(self.store.readiness()["database_role"], "factory_runtime")
        import psycopg

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS trust_ci; REVOKE ALL ON SCHEMA trust_ci FROM PUBLIC")
            cursor.execute(
                "SELECT rolname,rolcanlogin,rolsuper,rolcreaterole FROM pg_roles WHERE rolname=ANY(%s) ORDER BY rolname",
                (["factory_audit_reader", "factory_migrator", "factory_runtime"],),
            )
            roles = cursor.fetchall()
            self.assertEqual([row[0] for row in roles], ["factory_audit_reader", "factory_migrator", "factory_runtime"])
            self.assertTrue(all(row[1:] == (False, False, False) for row in roles))
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


    def semantic_repair_fixture(
        self,
        *,
        namespace,
        source_id,
        result_head_sha,
        repository_id="owner/repository",
        risk_level="high",
        finding_rule="rule-output-correctness",
        original_writer_context_digest="d" * 64,
        child_source_digest=None,
        parent_repair=None,
        limit_overrides=None,
        inherit_parent_bounds=True,
        intake_only=False,
        intake_actor=None,
        align_parent_head=True,
        child_source_digest_override=None,
        direct_store_intake=False,
        before_execution=None,
    ):
        def command_key(operation):
            return canonical_digest(
                {"fixture": namespace, "operation": operation}
            )

        if intake_actor is None:
            intake_actor = (
                REPAIR_CHILD_BROKER
                if child_source_digest is not None
                else OPERATOR
            )
        intake_now = datetime.now(timezone.utc)
        intake_payload = self.payload(repository=repository_id, source=source_id)
        intake_payload["request_id"] = f"semantic-repair-{namespace}"
        intake_payload["m0_authority"]["observed_at"] = intake_now.isoformat()
        if child_source_digest is not None:
            self.assertIsNotNone(parent_repair)
            intake_payload["source_type"] = "api"
            intake_payload["source_id"] = child_source_digest
            intake_payload["source_digest"] = (
                child_source_digest_override or child_source_digest
            )
            if align_parent_head:
                parent_head = parent_repair.child_proposal.parent_exact_head_sha
                intake_payload["architecture"]["exact_head_sha"] = parent_head
                intake_payload["governance"]["exact_head_sha"] = parent_head
                intake_payload["m0_authority"]["exact_head_sha"] = parent_head
            if inherit_parent_bounds:
                intake_payload["limits"].update(
                    {
                        "max_cost_usd_micros": (
                            parent_repair.child_proposal.max_cost_usd_micros
                        ),
                        "max_token_units": (
                            parent_repair.child_proposal.max_token_units
                        ),
                        "max_output_bytes": (
                            parent_repair.child_proposal.max_output_bytes
                        ),
                        "max_events": parent_repair.child_proposal.max_events,
                        "infrastructure_retries": (
                            parent_repair.child_proposal.infrastructure_retries_remaining
                        ),
                    }
                )
                remaining_wall = int(
                    (
                        parent_repair.child_proposal.deadline_at - intake_now
                    ).total_seconds()
                ) - 1
                self.assertGreater(remaining_wall, 0)
                intake_payload["limits"]["wall_seconds"] = min(
                    intake_payload["limits"]["wall_seconds"], remaining_wall
                )
                intake_payload["limits"]["semantic_repairs"] = min(
                    intake_payload["limits"]["semantic_repairs"],
                    parent_repair.child_proposal.budget_remaining_units,
                )
        elif intake_actor == REPAIR_CHILD_BROKER:
            intake_payload["source_type"] = "api"
            intake_payload["source_digest"] = source_id
        if limit_overrides:
            intake_payload["limits"].update(limit_overrides)
        import psycopg

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO factory.m0_authority_observations
                (observation_id,observed_at,check_name,exact_head_sha,issuer,
                 evidence_digest,repository_id,policy_digest)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    uuid.uuid4(),
                    intake_now,
                    intake_payload["m0_authority"]["check_name"],
                    intake_payload["m0_authority"]["exact_head_sha"],
                    "external-trust-ci-api",
                    command_key("refreshed-m0-authority"),
                    intake_payload["repository_id"],
                    intake_payload["policy_digest"],
                ),
            )
        intake = TaskIntakeV1.from_dict(intake_payload, now=intake_now)
        if direct_store_intake:
            task = self.store.intake(intake, intake_actor, intake_now).task
        else:
            task = self.service.intake(
                intake_payload, actor=intake_actor, now=intake_now
            ).task
        if intake_only:
            return {"task": task, "intent_digest": intake.intent_digest, "intake": intake}
        child_binding = None
        if child_source_digest is not None:
            child_binding = RepairChildTaskBindingV1.from_dict(
                {
                    "schema_version": 1,
                    "child_proposal_digest": child_source_digest,
                    "child_task_id": task.task_id,
                    "child_intent_digest": intake.intent_digest,
                }
            )
            binding_store = PostgresSemanticCoordinatorStore(
                self.semantic_coordinator_url
            )
            self.assertEqual(binding_store.bind_repair_child(child_binding), child_binding)
            self.assertEqual(binding_store.bind_repair_child(child_binding), child_binding)
        if before_execution is not None:
            before_execution(task, intake)
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
            idempotency_key=command_key("claim"),
        )
        provider_call_id = "semantic-fixture-call"
        self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=1,
            event_type="usage.reported",
            payload={
                "provider_call_id": provider_call_id,
                "price_table_digest": "d" * 64,
                "input_tokens": 10,
                "output_tokens": 5,
                "reasoning_tokens": 0,
                "cost_usd_micros": 25,
                "output_bytes": 20,
            },
            actor=WORKER,
            idempotency_key=command_key("usage-proposal"),
        )
        self.service.observe_usage(
            execution.lease,
            provider_call_id=provider_call_id,
            price_table_digest="d" * 64,
            cost_usd_micros=25,
            token_units=15,
            output_bytes=20,
            actor=WORKER,
            idempotency_key=command_key("usage-observation"),
        )
        self.service.commit_execution_proposal(
            execution.lease,
            packet_digest=execution.packet_digest,
            sequence=2,
            event_type="run.completed",
            payload={"summary": f"{namespace} complete"},
            actor=WORKER,
            idempotency_key=command_key("terminal"),
        )
        for stage in (ExecutionStage.RUNNING, ExecutionStage.COLLECTING):
            self.service.advance_execution(
                execution.lease,
                packet_digest=execution.packet_digest,
                stage=stage,
                actor=WORKER,
                idempotency_key=command_key(f"stage-{stage.value}"),
            )
        result = FactoryService(
            self.store,
            snapshot_broker=TrustedPostgresTestSnapshotBroker(result_head_sha),
        ).finalize_execution(
            execution.lease,
            packet_digest=execution.packet_digest,
            actor=WORKER,
            idempotency_key=command_key("finalize"),
        )

        semantic_store = PostgresSemanticCoordinatorStore(
            self.semantic_coordinator_url
        )
        coordinator = Actor(
            "semantic-coordinator",
            "operator",
            frozenset({"semantic:publish", "semantic:read"}),
            frozenset({task.repository_id}),
        )
        inputs = {
            "schema_version": 1,
            "workspace_result_digest": result.workspace_result_digest,
            "requirements": [
                {"kind": "acceptance_criterion", "requirement_id": "AC-001"},
                {"kind": "acceptance_criterion", "requirement_id": "AC-002"},
                {"kind": "invariant", "requirement_id": "INV-001"},
            ],
            "holdout_evidence_digest": command_key("holdout"),
            "review_evidence_digest": command_key("review"),
            "original_writer_context_digest": original_writer_context_digest,
            "risk_level": risk_level,
            "diff_limit": 100,
        }
        published = FactoryService(
            self.store, semantic_store=semantic_store
        ).publish_semantic_subject(
            task.task_id,
            result.workspace_result_digest,
            inputs,
            actor=coordinator,
            idempotency_key=command_key("publish-subject"),
        )
        validator = ValidatorIdentityV1.from_dict(
            {
                "validator_id": f"validator-{namespace}",
                "role": "semantic_validator",
                "capabilities": ["repository_read", "semantic_validate"],
                "definition_digest": command_key("validator-definition"),
                "model_digest": command_key("validator-model"),
                "context_digest": command_key("validator-context"),
            }
        )
        assignment = semantic_store.create_assignment(
            published.subject,
            validator,
            idempotency_key=command_key("assignment"),
        )
        finding_value = SemanticFindingV1.from_dict(
            {
                "schema_version": 1,
                "subject_digest": published.subject.digest,
                "finding_id": f"finding-{namespace}",
                "requirement": published.subject.requirements[0].to_dict(),
                "severity": "major",
                "category": "requirement_unsatisfied",
                "rule_id": finding_rule,
                "message": f"{namespace} remains incomplete.",
                "evidence_refs": [f"fixture:{namespace}"],
                "reproduction": f"Run fixture {namespace}.",
                "repairable": True,
                "validator": validator.to_dict(),
                "created_at": "2026-09-02T00:00:00Z",
            }
        )
        coverage_value = SemanticCoverageV1.from_dict(
            {
                "schema_version": 1,
                "subject_digest": published.subject.digest,
                "validator": validator.to_dict(),
                "entries": [
                    {
                        "requirement": requirement.to_dict(),
                        "status": "unproven" if index == 0 else "proven",
                        "evidence_refs": (
                            [] if index == 0 else [f"check:{requirement.requirement_id}"]
                        ),
                    }
                    for index, requirement in enumerate(
                        published.subject.requirements
                    )
                ],
                "coverage_millionths": 1_000_000,
            }
        )
        evidence = PostgresSemanticValidatorStore(
            self.semantic_validator_url
        ).append_evidence(
            published.subject.digest,
            assignment["assignment_digest"],
            (finding_value,),
            coverage_value,
            idempotency_key=command_key("evidence"),
        )
        adjudicator_store = PostgresSemanticAdjudicatorStore(
            self.semantic_adjudicator_url
        )
        material = adjudicator_store.adjudication_material(
            task.task_id, published.subject.digest
        )
        verdict = adjudicate(
            material["subject"], material["findings"], material["coverages"]
        )
        verdict_record = adjudicator_store.append_verdict(
            material, verdict, idempotency_key=command_key("verdict")
        )
        return {
            "task": task,
            "intent_digest": intake.intent_digest,
            "intake": intake,
            "child_binding": child_binding,
            "result": result,
            "published": published,
            "finding": finding_value,
            "evidence": evidence,
            "verdict": verdict,
            "verdict_record": verdict_record,
        }


    def test_semantic_subject_publish_is_exact_replay_safe_and_role_isolated(self):
        import psycopg

        root_now = datetime.now(timezone.utc)
        root_payload = self.payload(source="m6-semantic-subject")
        root_payload["m0_authority"]["observed_at"] = root_now.isoformat()
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO factory.m0_authority_observations
                (observation_id,observed_at,check_name,exact_head_sha,issuer,
                 evidence_digest,repository_id,policy_digest)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    uuid.uuid4(),
                    root_now,
                    root_payload["m0_authority"]["check_name"],
                    root_payload["m0_authority"]["exact_head_sha"],
                    "external-trust-ci-api",
                    canonical_digest({"fixture": "main-root-authority"}),
                    root_payload["repository_id"],
                    root_payload["policy_digest"],
                ),
            )
        task = self.service.intake(
            root_payload, actor=OPERATOR, now=root_now
        ).task
        stale_authority_payload = {
            **root_payload,
            "request_id": "semantic-stale-authority",
            "source_id": "m6-stale-authority",
        }
        with self.assertRaisesRegex(ValueError, "stale_m0"):
            self.service.intake(
                stale_authority_payload,
                actor=OPERATOR,
                now=root_now + timedelta(seconds=301),
            )
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

        validator_proof = ValidatorIdentityV1.from_dict({
            "validator_id": "validator-pg-1",
            "role": "semantic_validator",
            "capabilities": ["repository_read", "semantic_validate"],
            "definition_digest": "e" * 64,
            "model_digest": "f" * 64,
            "context_digest": "1" * 64,
        })
        assignment = semantic_store.create_assignment(
            published.subject, validator_proof, idempotency_key="a" * 64
        )
        with self.assertRaisesRegex(StoreError, "assignment rejected"):
            semantic_store.create_assignment(
                published.subject,
                replace(
                    validator_proof,
                    validator_id="validator-pg-2",
                    context_digest="2" * 64,
                ),
                idempotency_key="a" * 64,
            )
        finding_value = SemanticFindingV1.from_dict({
            "schema_version": 1,
            "subject_digest": published.subject.digest,
            "finding_id": "finding-pg-1",
            "requirement": published.subject.requirements[0].to_dict(),
            "severity": "major",
            "category": "requirement_unsatisfied",
            "rule_id": "rule-output-correctness",
            "message": "Deterministic acceptance evidence is incomplete.",
            "evidence_refs": ["artifact:result-digest"],
            "reproduction": "Run the bounded deterministic PostgreSQL fixture.",
            "repairable": True,
            "validator": validator_proof.to_dict(),
            "created_at": "2026-09-02T00:00:00Z",
        })
        coverage_value = SemanticCoverageV1.from_dict({
            "schema_version": 1,
            "subject_digest": published.subject.digest,
            "validator": validator_proof.to_dict(),
            "entries": [
                {
                    "requirement": requirement.to_dict(),
                    "status": "unproven" if index == 0 else "proven",
                    "evidence_refs": (
                        []
                        if index == 0
                        else [f"check:{requirement.requirement_id.lower()}"]
                    ),
                }
                for index, requirement in enumerate(published.subject.requirements)
            ],
            "coverage_millionths": 1_000_000,
        })
        validator_store = PostgresSemanticValidatorStore(self.semantic_validator_url)
        evidence = validator_store.append_evidence(
            published.subject.digest,
            assignment["assignment_digest"],
            (finding_value,),
            coverage_value,
            idempotency_key="b" * 64,
        )
        self.assertEqual(
            validator_store.append_evidence(
                published.subject.digest,
                assignment["assignment_digest"],
                (finding_value,),
                coverage_value,
                idempotency_key="b" * 64,
            ),
            evidence,
        )
        with self.assertRaisesRegex(StoreError, "evidence publication rejected"):
            validator_store.append_evidence(
                published.subject.digest,
                assignment["assignment_digest"],
                (replace(finding_value, message="Divergent wording under the same command key."),),
                coverage_value,
                idempotency_key="b" * 64,
            )
        adjudicator_store = PostgresSemanticAdjudicatorStore(
            self.semantic_adjudicator_url
        )
        adjudication_material = adjudicator_store.adjudication_material(
            task.task_id, published.subject.digest
        )
        verdict = adjudicate(
            adjudication_material["subject"],
            adjudication_material["findings"],
            adjudication_material["coverages"],
        )
        self.assertEqual(verdict.decision, "repair")
        self.assertEqual(verdict.unsupported_pass_requirement_keys, ())
        verdict_record = adjudicator_store.append_verdict(
            adjudication_material, verdict, idempotency_key="c" * 64
        )
        self.assertEqual(
            adjudicator_store.append_verdict(
                adjudication_material, verdict, idempotency_key="c" * 64
            ),
            verdict_record,
        )
        self.assertEqual(
            semantic_store.verdict_by_subject(task.task_id, published.subject.digest),
            verdict_record,
        )
        repair_request = SemanticRepairRequestV1.from_dict({
            "schema_version": 1,
            "subject_digest": published.subject.digest,
            "verdict_digest": verdict.digest,
            "requested_cycle": 1,
            "previous_child_proposal_digest": None,
            "writer_id": published.subject.original_writer_id,
            "context_digest": "2" * 64,
            "expected_workspace_result_digest": result.workspace_result_digest,
            "expected_fence": published.binding.fence,
            "expected_head_sha": published.subject.exact_head_sha,
            "expected_base_sha": published.subject.exact_base_sha,
            "expected_architecture_digest": published.subject.architecture_digest,
            "expected_authority_digest": published.subject.authority_digest,
            "expected_diff_digest": published.subject.diff_digest,
            "expected_risk_level": published.subject.risk_level,
        })
        with ThreadPoolExecutor(max_workers=2) as pool:
            concurrent = list(pool.map(
                lambda command_key: PostgresSemanticCoordinatorStore(
                    self.semantic_coordinator_url
                ).request_repair(
                    task.task_id,
                    repair_request,
                    idempotency_key=command_key,
                ),
                ("1" * 64, "2" * 64),
            ))
        self.assertEqual(concurrent[0], concurrent[1])
        repair = concurrent[0]
        self.assertEqual(repair.decision, "repair")
        self.assertEqual(repair.child_proposal.budget_remaining_units, 3)
        self.assertEqual(
            repair.child_proposal.baseline_risk_level,
            published.subject.risk_level,
        )
        self.assertEqual(repair.child_proposal.max_cost_usd_micros, 24_999_975)
        self.assertEqual(repair.child_proposal.max_token_units, 1_999_985)
        self.assertEqual(repair.child_proposal.max_output_bytes, 9_999_980)
        self.assertLess(repair.child_proposal.max_events, 100_000)
        self.assertEqual(
            repair.child_proposal.infrastructure_retries_remaining, 2
        )
        self.assertEqual(repair.child_proposal.proposal_state, "pending_handoff")
        self.assertTrue(repair.child_proposal.requires_new_workspace_result)
        self.assertTrue(repair.child_proposal.requires_new_semantic_subject)
        self.assertEqual(
            semantic_store.request_repair(
                task.task_id, repair_request, idempotency_key="1" * 64
            ),
            repair,
        )
        with self.assertRaisesRegex(StoreError, "repair result"):
            semantic_store.request_repair(
                task.task_id,
                replace(repair_request, context_digest="3" * 64),
                idempotency_key="1" * 64,
            )
        escalation_cases = (
            ("3" * 64, {"writer_id": "wrong-writer"}, "original_writer_mismatch"),
            ("4" * 64, {"expected_fence": published.binding.fence + 1}, "stale_fence"),
            ("5" * 64, {"expected_head_sha": "5" * 40}, "head_changed"),
            ("6" * 64, {"expected_base_sha": "5" * 40}, "base_changed"),
            ("7" * 64, {"expected_architecture_digest": "5" * 64}, "architecture_changed"),
            ("8" * 64, {"expected_authority_digest": "5" * 64}, "authority_changed"),
            ("9" * 64, {"expected_diff_digest": "5" * 64}, "diff_changed"),
            ("0" * 64, {"expected_risk_level": "critical"}, "risk_increased"),
            ("b" * 64, {"expected_workspace_result_digest": "5" * 64}, "workspace_result_changed"),
            ("e" * 64, {"context_digest": published.subject.original_writer_context_digest}, "context_not_fresh"),
        )
        for command_key, changes, reason in escalation_cases:
            with self.subTest(reason=reason):
                escalated = semantic_store.request_repair(
                    task.task_id,
                    replace(repair_request, **changes),
                    idempotency_key=command_key,
                )
                self.assertEqual(
                    (escalated.decision, escalated.reason, escalated.child_proposal),
                    ("needs_human", reason, None),
                )
        same_subject = semantic_store.request_repair(
            task.task_id,
            replace(
                repair_request,
                requested_cycle=2,
                previous_child_proposal_digest=repair.child_proposal_digest,
                context_digest="4" * 64,
            ),
            idempotency_key="f" * 64,
        )
        self.assertEqual(
            (same_subject.decision, same_subject.reason, same_subject.child_proposal),
            ("needs_human", "workspace_result_changed", None),
        )
        with self.assertRaisesRegex(StoreError, "repair result"):
            semantic_store.request_repair(
                task.task_id,
                replace(
                    repair_request,
                    requested_cycle=3,
                    previous_child_proposal_digest="f" * 64,
                    context_digest="6" * 64,
                ),
                idempotency_key="d" * 64,
            )

        def request_for(fixture, cycle, previous_child, context_digest):
            fixture_published = fixture["published"]
            fixture_result = fixture["result"]
            fixture_verdict = fixture["verdict"]
            return SemanticRepairRequestV1.from_dict(
                {
                    "schema_version": 1,
                    "subject_digest": fixture_published.subject.digest,
                    "verdict_digest": fixture_verdict.digest,
                    "requested_cycle": cycle,
                    "previous_child_proposal_digest": previous_child,
                    "writer_id": fixture_published.subject.original_writer_id,
                    "context_digest": context_digest,
                    "expected_workspace_result_digest": (
                        fixture_result.workspace_result_digest
                    ),
                    "expected_fence": fixture_published.binding.fence,
                    "expected_head_sha": fixture_published.subject.exact_head_sha,
                    "expected_base_sha": fixture_published.subject.exact_base_sha,
                    "expected_architecture_digest": (
                        fixture_published.subject.architecture_digest
                    ),
                    "expected_authority_digest": (
                        fixture_published.subject.authority_digest
                    ),
                    "expected_diff_digest": fixture_published.subject.diff_digest,
                    "expected_risk_level": fixture_published.subject.risk_level,
                }
            )

        def binding_for(child_result, fixture):
            return RepairChildTaskBindingV1.from_dict(
                {
                    "schema_version": 1,
                    "child_proposal_digest": child_result.child_proposal_digest,
                    "child_task_id": fixture["task"].task_id,
                    "child_intent_digest": fixture["intent_digest"],
                }
            )

        def bind_child(child_result, fixture):
            binding = binding_for(child_result, fixture)
            if fixture.get("child_binding") is None:
                self.assertEqual(semantic_store.bind_repair_child(binding), binding)
                self.assertEqual(semantic_store.bind_repair_child(binding), binding)
            else:
                self.assertEqual(fixture["child_binding"], binding)
            return binding

        def claimable_as(fixture, owner, role):
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT factory.semantic_task_claimable(
                      task_id,intent_id,intake_actor_kind,intake_actor_id,%s,%s
                    ) FROM factory.tasks WHERE task_id=%s""",
                    (owner, role.value, fixture["task"].task_id),
                )
                return cursor.fetchone()[0]

        def claimable(fixture):
            return claimable_as(fixture, WORKER.actor_id, RunRole.WRITER)

        with self.subTest(case="repair-child-input-head-must-match-parent-result"):
            with self.assertRaisesRegex(
                StoreError, "repair child.*head.*proposal"
            ):
                self.semantic_repair_fixture(
                    namespace="mismatched-parent-head",
                    source_id=repair.child_proposal_digest,
                    child_source_digest=repair.child_proposal_digest,
                    parent_repair=repair,
                    result_head_sha="5" * 40,
                    intake_only=True,
                    align_parent_head=False,
                    direct_store_intake=True,
                )

        wrong_broker_source = canonical_digest(
            {"case": "repair-broker-wrong-proposal-source"}
        )
        with self.assertRaisesRegex(
            StoreError, "broker source is not a pending proposal"
        ):
            self.semantic_repair_fixture(
                namespace="wrong-broker-source-candidate",
                source_id=wrong_broker_source,
                result_head_sha="5" * 40,
                intake_only=True,
                intake_actor=REPAIR_CHILD_BROKER,
            )

        with self.subTest(case="ordinary-intake-cannot-occupy-repair-source"):
            with self.assertRaisesRegex(
                StoreError, "repair proposal source requires.*broker"
            ):
                self.semantic_repair_fixture(
                    namespace="ordinary-reserved-source-candidate",
                    source_id=repair.child_proposal_digest,
                    child_source_digest=repair.child_proposal_digest,
                    parent_repair=repair,
                    result_head_sha="5" * 40,
                    intake_only=True,
                    intake_actor=OPERATOR,
                    direct_store_intake=True,
                )
        def assert_bound_claim_identity(child_task, _child_intake):
            child = {"task": child_task}
            with self.subTest(case="second-worker-cannot-claim-repair-child"):
                self.assertFalse(
                    claimable_as(child, SECOND_WORKER.actor_id, RunRole.WRITER)
                )
            with self.subTest(case="reader-role-cannot-claim-repair-child"):
                self.assertFalse(
                    claimable_as(child, WORKER.actor_id, RunRole.READER)
                )
            self.assertTrue(
                claimable_as(child, WORKER.actor_id, RunRole.WRITER)
            )
            self.assertIsNone(
                self.service.claim(
                    owner=WORKER.actor_id,
                    role=RunRole.WRITER,
                    repositories=(child_task.repository_id,),
                    lease_seconds=60,
                    actor=SECOND_WORKER,
                    now=datetime.now(timezone.utc),
                    idempotency_key=canonical_digest(
                        {"case": "repair-child-second-worker-claim"}
                    ),
                )
            )
            self.assertIsNone(
                self.service.claim(
                    owner=WORKER.actor_id,
                    role=RunRole.READER,
                    repositories=(child_task.repository_id,),
                    lease_seconds=60,
                    actor=WORKER,
                    now=datetime.now(timezone.utc),
                    idempotency_key=canonical_digest(
                        {"case": "repair-child-reader-role-claim"}
                    ),
                )
            )
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT t.state,count(r.run_id)
                    FROM factory.tasks t LEFT JOIN factory.runs r ON r.task_id=t.task_id
                    WHERE t.task_id=%s GROUP BY t.state""",
                    (child_task.task_id,),
                )
                self.assertEqual(cursor.fetchone(), ("queued", 0))

        cycle_two_fixture = self.semantic_repair_fixture(
            namespace="main-cycle-2",
            source_id=repair.child_proposal_digest,
            child_source_digest=repair.child_proposal_digest,
            parent_repair=repair,
            result_head_sha="5" * 40,
            finding_rule="rule-cycle-two",
            original_writer_context_digest=repair.child_proposal.context_digest,
            before_execution=assert_bound_claim_identity,
        )
        cycle_two_request = request_for(
            cycle_two_fixture, 2, repair.child_proposal_digest, "2" * 64
        )
        self.assertEqual(
            (
                cycle_two_fixture["published"].binding.owner,
                cycle_two_fixture["published"].binding.role,
            ),
            (WORKER.actor_id, "writer"),
        )
        self.assertEqual(
            cycle_two_fixture["published"].subject.original_writer_context_digest,
            repair.child_proposal.context_digest,
        )
        self.assertGreater(
            cycle_two_fixture["intake"].m0_authority.observed_at, root_now
        )
        with self.subTest(case="repair-child-positive-head-chain"):
            self.assertEqual(
                (
                    cycle_two_fixture["intake"].m0_authority.check_name,
                    cycle_two_fixture["intake"].m0_authority.exact_head_sha,
                ),
                (
                    root_payload["m0_authority"]["check_name"],
                    repair.child_proposal.parent_exact_head_sha,
                ),
            )
            self.assertEqual(
                (
                    cycle_two_fixture["intake"].architecture.exact_head_sha,
                    cycle_two_fixture["intake"].governance.exact_head_sha,
                    cycle_two_fixture["published"].binding.input_head_sha,
                ),
                (repair.child_proposal.parent_exact_head_sha,) * 3,
            )
        bind_child(repair, cycle_two_fixture)
        reused_context = semantic_store.request_repair(
            cycle_two_fixture["task"].task_id,
            cycle_two_request,
            idempotency_key=canonical_digest({"case": "reused-cycle-context"}),
        )
        self.assertEqual(
            (reused_context.decision, reused_context.reason),
            ("needs_human", "context_not_fresh"),
        )
        cycle_two_request = replace(cycle_two_request, context_digest="3" * 64)
        cycle_two = semantic_store.request_repair(
            cycle_two_fixture["task"].task_id,
            cycle_two_request,
            idempotency_key=canonical_digest({"case": "main-cycle-2"}),
        )
        self.assertEqual(cycle_two.decision, "repair")
        self.assertEqual(cycle_two.child_proposal.budget_remaining_units, 2)
        self.assertEqual(cycle_two.child_proposal.baseline_risk_level, "high")

        cycle_three_fixture = self.semantic_repair_fixture(
            namespace="main-cycle-3",
            source_id=cycle_two.child_proposal_digest,
            child_source_digest=cycle_two.child_proposal_digest,
            parent_repair=cycle_two,
            result_head_sha="6" * 40,
            finding_rule="rule-cycle-three",
            original_writer_context_digest=cycle_two.child_proposal.context_digest,
        )
        bind_child(cycle_two, cycle_three_fixture)
        cycle_three_request = request_for(
            cycle_three_fixture, 3, cycle_two.child_proposal_digest, "4" * 64
        )
        self.assertEqual(
            cycle_three_fixture["published"].subject.original_writer_context_digest,
            cycle_two.child_proposal.context_digest,
        )
        with self.assertRaisesRegex(StoreError, "repair result"):
            semantic_store.request_repair(
                cycle_three_fixture["task"].task_id,
                replace(
                    cycle_three_request,
                    previous_child_proposal_digest=repair.child_proposal_digest,
                ),
                idempotency_key=canonical_digest({"case": "tampered-lineage"}),
            )
        cycle_three = semantic_store.request_repair(
            cycle_three_fixture["task"].task_id,
            cycle_three_request,
            idempotency_key=canonical_digest({"case": "main-cycle-3"}),
        )
        self.assertEqual(cycle_three.decision, "repair")
        self.assertEqual(cycle_three.child_proposal.budget_remaining_units, 1)
        fourth = semantic_store.request_repair(
            cycle_three_fixture["task"].task_id,
            replace(
                cycle_three_request,
                requested_cycle=4,
                previous_child_proposal_digest=cycle_three.child_proposal_digest,
                context_digest="5" * 64,
            ),
            idempotency_key=canonical_digest({"case": "main-cycle-4"}),
        )
        self.assertEqual(
            (fourth.decision, fourth.reason, fourth.child_proposal),
            ("needs_human", "repair_cycle_out_of_bounds", None),
        )

        recurrence_root = self.semantic_repair_fixture(
            namespace="recurrence-root",
            source_id="m6-recurrence-root",
            result_head_sha="7" * 40,
            finding_rule="rule-recurrence",
            limit_overrides={
                "max_cost_usd_micros": 1_000,
                "wall_seconds": 3_600,
                "semantic_repairs": 2,
            },
        )
        recurrence_root_request = request_for(
            recurrence_root, 1, None, "5" * 64
        )
        recurrence_parent = semantic_store.request_repair(
            recurrence_root["task"].task_id,
            recurrence_root_request,
            idempotency_key=canonical_digest({"case": "recurrence-root"}),
        )
        expanded_candidate = self.semantic_repair_fixture(
            namespace="expanded-limit-candidate",
            source_id=recurrence_parent.child_proposal_digest,
            child_source_digest=recurrence_parent.child_proposal_digest,
            parent_repair=recurrence_parent,
            result_head_sha="8" * 40,
            intake_only=True,
            limit_overrides={
                "max_cost_usd_micros": (
                    recurrence_parent.child_proposal.max_cost_usd_micros + 1
                )
            },
        )
        with self.assertRaisesRegex(StoreError, "binding rejected"):
            semantic_store.bind_repair_child(
                binding_for(recurrence_parent, expanded_candidate)
            )
        self.assertIsNone(
            self.service.claim(
                owner=WORKER.actor_id,
                role=RunRole.WRITER,
                repositories=(task.repository_id,),
                lease_seconds=60,
                actor=WORKER,
                now=datetime.now(timezone.utc),
                idempotency_key=canonical_digest(
                    {"case": "rejected-expanded-child-claim"}
                ),
            )
        )
        self.assertEqual(
            self.store.get_task(expanded_candidate["task"].task_id).status,
            TaskStatus.QUEUED,
        )
        deadline_reset_candidate = self.semantic_repair_fixture(
            namespace="deadline-reset-candidate",
            source_id=recurrence_parent.child_proposal_digest,
            child_source_digest=recurrence_parent.child_proposal_digest,
            parent_repair=recurrence_parent,
            result_head_sha="8" * 40,
            intake_only=True,
            limit_overrides={
                "wall_seconds": recurrence_root["intake"].limits.wall_seconds
            },
        )
        with self.assertRaisesRegex(StoreError, "binding rejected"):
            semantic_store.bind_repair_child(
                binding_for(recurrence_parent, deadline_reset_candidate)
            )
        budget_reset_candidate = self.semantic_repair_fixture(
            namespace="budget-reset-candidate",
            source_id=recurrence_parent.child_proposal_digest,
            child_source_digest=recurrence_parent.child_proposal_digest,
            parent_repair=recurrence_parent,
            result_head_sha="8" * 40,
            intake_only=True,
            limit_overrides={
                "semantic_repairs": (
                    recurrence_parent.child_proposal.budget_remaining_units + 1
                )
            },
        )
        with self.assertRaisesRegex(StoreError, "binding rejected"):
            semantic_store.bind_repair_child(
                binding_for(recurrence_parent, budget_reset_candidate)
            )
        recurrence_child = self.semantic_repair_fixture(
            namespace="recurrence-child",
            source_id=recurrence_parent.child_proposal_digest,
            child_source_digest=recurrence_parent.child_proposal_digest,
            parent_repair=recurrence_parent,
            result_head_sha="8" * 40,
            finding_rule="rule-recurrence",
            original_writer_context_digest=(
                recurrence_parent.child_proposal.context_digest
            ),
        )
        bind_child(recurrence_parent, recurrence_child)
        recurrence = semantic_store.request_repair(
            recurrence_child["task"].task_id,
            request_for(
                recurrence_child,
                2,
                recurrence_parent.child_proposal_digest,
                "6" * 64,
            ),
            idempotency_key=canonical_digest({"case": "finding-recurrence"}),
        )
        self.assertEqual(
            (recurrence.decision, recurrence.reason, recurrence.child_proposal),
            ("needs_human", "finding_recurrence", None),
        )

        risk_root = self.semantic_repair_fixture(
            namespace="risk-root",
            source_id="m6-risk-root",
            result_head_sha="9" * 40,
            risk_level="medium",
            finding_rule="rule-risk-root",
        )
        risk_parent = semantic_store.request_repair(
            risk_root["task"].task_id,
            request_for(risk_root, 1, None, "7" * 64),
            idempotency_key=canonical_digest({"case": "risk-root"}),
        )
        risk_child = self.semantic_repair_fixture(
            namespace="risk-child",
            source_id=risk_parent.child_proposal_digest,
            child_source_digest=risk_parent.child_proposal_digest,
            parent_repair=risk_parent,
            result_head_sha="a" * 40,
            risk_level="high",
            finding_rule="rule-risk-child",
            original_writer_context_digest=risk_parent.child_proposal.context_digest,
        )
        bind_child(risk_parent, risk_child)
        risk_escalation = semantic_store.request_repair(
            risk_child["task"].task_id,
            request_for(
                risk_child, 2, risk_parent.child_proposal_digest, "8" * 64
            ),
            idempotency_key=canonical_digest({"case": "cross-cycle-risk"}),
        )
        self.assertEqual(
            (
                risk_escalation.decision,
                risk_escalation.reason,
                risk_escalation.child_proposal,
            ),
            ("needs_human", "risk_increased", None),
        )

        lowered_budget_root = self.semantic_repair_fixture(
            namespace="lowered-budget-root",
            source_id="m6-lowered-budget-root",
            result_head_sha="b" * 40,
            finding_rule="rule-lowered-budget-root",
            limit_overrides={"semantic_repairs": 3},
        )
        lowered_budget_parent = semantic_store.request_repair(
            lowered_budget_root["task"].task_id,
            request_for(lowered_budget_root, 1, None, "9" * 64),
            idempotency_key=canonical_digest({"case": "lowered-budget-root"}),
        )
        self.assertEqual(
            lowered_budget_parent.child_proposal.budget_remaining_units, 3
        )
        lowered_budget_child = self.semantic_repair_fixture(
            namespace="lowered-budget-child",
            source_id=lowered_budget_parent.child_proposal_digest,
            child_source_digest=lowered_budget_parent.child_proposal_digest,
            parent_repair=lowered_budget_parent,
            result_head_sha="c" * 40,
            finding_rule="rule-lowered-budget-child",
            original_writer_context_digest=(
                lowered_budget_parent.child_proposal.context_digest
            ),
            limit_overrides={"semantic_repairs": 1},
        )
        bind_child(lowered_budget_parent, lowered_budget_child)
        self.assertEqual(lowered_budget_child["intake"].limits.semantic_repairs, 1)
        lowered_budget = semantic_store.request_repair(
            lowered_budget_child["task"].task_id,
            request_for(
                lowered_budget_child,
                2,
                lowered_budget_parent.child_proposal_digest,
                "a" * 64,
            ),
            idempotency_key=canonical_digest({"case": "lowered-budget-child"}),
        )
        self.assertEqual(
            (
                lowered_budget.decision,
                lowered_budget.reason,
                lowered_budget.child_proposal,
            ),
            ("needs_human", "budget_exhausted", None),
        )

        revoked_authority_root = self.semantic_repair_fixture(
            namespace="revoked-authority-root",
            source_id="m6-revoked-authority-root",
            result_head_sha="d" * 40,
            finding_rule="rule-revoked-authority-root",
        )
        revoked_authority_parent = semantic_store.request_repair(
            revoked_authority_root["task"].task_id,
            request_for(revoked_authority_root, 1, None, "b" * 64),
            idempotency_key=canonical_digest({"case": "revoked-authority-root"}),
        )
        stale_revoked_candidate = self.semantic_repair_fixture(
            namespace="stale-revoked-authority-child",
            source_id=revoked_authority_parent.child_proposal_digest,
            child_source_digest=revoked_authority_parent.child_proposal_digest,
            parent_repair=revoked_authority_parent,
            result_head_sha="e" * 40,
            limit_overrides={
                "max_output_bytes": (
                    revoked_authority_parent.child_proposal.max_output_bytes - 1
                )
            },
            intake_only=True,
        )
        revoked_authority_child = self.semantic_repair_fixture(
            namespace="revoked-authority-child",
            source_id=revoked_authority_parent.child_proposal_digest,
            child_source_digest=revoked_authority_parent.child_proposal_digest,
            parent_repair=revoked_authority_parent,
            result_head_sha="e" * 40,
            intake_only=True,
        )
        self.assertEqual(
            self.store.get_task(stale_revoked_candidate["task"].task_id).status,
            TaskStatus.SUPERSEDED,
        )
        stale_binding = binding_for(
            revoked_authority_parent, stale_revoked_candidate
        )
        stale_canonical = canonical_json(stale_binding.to_dict()).decode("utf-8")
        with semantic_store._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT factory.semantic_bind_repair_child(%s,%s)",
                (stale_binding.digest, stale_canonical),
            )
            stale_response = cursor.fetchone()[0]
            connection.rollback()
        with self.subTest(case="superseded-child-bind-fails-before-consuming-proposal"):
            self.assertIsNone(stale_response)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT count(*) FROM factory.semantic_child_task_bindings
                WHERE child_proposal_digest=%s""",
                (revoked_authority_parent.child_proposal_digest,),
            )
            self.assertEqual(cursor.fetchone()[0], 0)
        bind_child(revoked_authority_parent, revoked_authority_child)
        self.assertTrue(claimable(revoked_authority_child))
        revoked_intake = revoked_authority_child["intake"]
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """UPDATE factory.m0_authority_observations
                SET revoked_at=clock_timestamp()
                WHERE observed_at=%s AND check_name=%s AND exact_head_sha=%s
                  AND repository_id=%s AND policy_digest=%s
                  AND revoked_at IS NULL
                RETURNING revoked_at""",
                (
                    revoked_intake.m0_authority.observed_at,
                    revoked_intake.m0_authority.check_name,
                    revoked_intake.m0_authority.exact_head_sha,
                    revoked_intake.repository_id,
                    revoked_intake.policy_digest,
                ),
            )
            self.assertIsNotNone(cursor.fetchone()[0])
        self.assertFalse(claimable(revoked_authority_child))
        self.assertIsNone(
            self.service.claim(
                owner=WORKER.actor_id,
                role=RunRole.WRITER,
                repositories=(task.repository_id,),
                lease_seconds=60,
                actor=WORKER,
                now=datetime.now(timezone.utc),
                idempotency_key=canonical_digest(
                    {"case": "revoked-authority-child-claim"}
                ),
            )
        )
        self.assertEqual(
            self.store.get_task(revoked_authority_child["task"].task_id).status,
            TaskStatus.QUEUED,
        )
        self.assertEqual(
            self.service.cancel(
                revoked_authority_child["task"].task_id,
                reason="repair child authority revoked before claim",
                idempotency_key=canonical_digest(
                    {"case": "revoked-authority-child-cancel"}
                ),
                actor=OPERATOR,
                now=datetime.now(timezone.utc),
            ).status,
            TaskStatus.CANCELLED,
        )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                (SELECT count(*) FROM factory.semantic_directives),
                (SELECT count(*) FROM factory.semantic_child_proposals),
                (SELECT count(*) FROM factory.semantic_child_task_bindings),
                (SELECT count(*) FROM factory.semantic_escalations),
                (SELECT count(*) FROM factory.semantic_verdicts),
                (SELECT body->>'decision' FROM factory.semantic_verdicts
                  WHERE verdict_digest=%s)""",
                (verdict.digest,),
            )
            self.assertEqual(cursor.fetchone(), (7, 7, 6, 16, 10, "repair"))
        forged_verdict = {
            **verdict.to_dict(),
            "decision": "pass",
            "residual_risk": "none",
        }
        forged_digest = canonical_digest(forged_verdict)
        forged_request = {
            "contract": "adaptive-factory.semantic-adjudication-command/v1",
            "idempotency_key": "d" * 64,
            "subject_digest": published.subject.digest,
            "evidence_set_digest": adjudication_material["evidence_set_digest"],
            "verdict_digest": forged_digest,
        }
        with adjudicator_store._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT factory.semantic_append_verdict(%s,%s,%s,%s,%s,%s,%s)",
                (
                    "d" * 64,
                    canonical_digest(forged_request),
                    canonical_json(forged_request).decode("utf-8"),
                    adjudication_material["evidence_set_digest"],
                    canonical_json(adjudication_material["evidence_set"]).decode("utf-8"),
                    forged_digest,
                    canonical_json(forged_verdict).decode("utf-8"),
                ),
            )
            self.assertIsNone(cursor.fetchone()[0])

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT p.proname,
                has_function_privilege('factory_semantic_coordinator',p.oid,'EXECUTE'),
                has_function_privilege('factory_semantic_validator',p.oid,'EXECUTE'),
                has_function_privilege('factory_semantic_adjudicator',p.oid,'EXECUTE'),
                has_function_privilege('factory_runtime',p.oid,'EXECUTE')
                FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                WHERE n.nspname='factory' AND p.proname IN (
                  'semantic_create_assignment','semantic_append_evidence',
                  'semantic_adjudication_material','semantic_append_verdict',
                  'semantic_verdict_by_subject','semantic_plan_repair',
                  'semantic_bind_repair_child','semantic_repair_intake_status',
                  'semantic_task_claimable'
                ) ORDER BY p.proname"""
            )
            privileges = {row[0]: row[1:] for row in cursor.fetchall()}
        self.assertEqual(privileges, {
            "semantic_adjudication_material": (False, False, True, False),
            "semantic_append_evidence": (False, True, False, False),
            "semantic_append_verdict": (False, False, True, False),
            "semantic_bind_repair_child": (True, False, False, False),
            "semantic_create_assignment": (True, False, False, False),
            "semantic_plan_repair": (True, False, False, False),
            "semantic_repair_intake_status": (False, False, False, True),
            "semantic_task_claimable": (False, False, False, True),
            "semantic_verdict_by_subject": (True, False, False, False),
        })
        with self.store._connect() as connection, connection.cursor() as cursor:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                cursor.execute("SELECT 1 FROM factory.semantic_child_proposals")
        with self.store._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT factory.semantic_repair_intake_status(
                %s,'api',%s,%s,%s,'repair_broker',
                'semantic-repair-child-broker')""",
                (
                    task.repository_id,
                    repair.child_proposal_digest,
                    repair.child_proposal_digest,
                    repair.child_proposal.parent_exact_head_sha,
                ),
            )
            self.assertEqual(cursor.fetchone()[0], "bound")


    def test_repair_source_identity_and_claim_owner_are_atomic(self):
        import psycopg

        semantic_store = PostgresSemanticCoordinatorStore(
            self.semantic_coordinator_url
        )

        def first_repair(namespace, repository_id, result_head_sha):
            fixture = self.semantic_repair_fixture(
                namespace=f"{namespace}-root",
                repository_id=repository_id,
                source_id=f"{namespace}-root",
                result_head_sha=result_head_sha,
            )
            published = fixture["published"]
            request = SemanticRepairRequestV1.from_dict(
                {
                    "schema_version": 1,
                    "subject_digest": published.subject.digest,
                    "verdict_digest": fixture["verdict"].digest,
                    "requested_cycle": 1,
                    "previous_child_proposal_digest": None,
                    "writer_id": published.subject.original_writer_id,
                    "context_digest": canonical_digest(
                        {"case": namespace, "context": 1}
                    ),
                    "expected_workspace_result_digest": (
                        fixture["result"].workspace_result_digest
                    ),
                    "expected_fence": published.binding.fence,
                    "expected_head_sha": published.subject.exact_head_sha,
                    "expected_base_sha": published.subject.exact_base_sha,
                    "expected_architecture_digest": (
                        published.subject.architecture_digest
                    ),
                    "expected_authority_digest": published.subject.authority_digest,
                    "expected_diff_digest": published.subject.diff_digest,
                    "expected_risk_level": published.subject.risk_level,
                }
            )
            repair = semantic_store.request_repair(
                fixture["task"].task_id,
                request,
                idempotency_key=canonical_digest(
                    {"case": namespace, "operation": "repair"}
                ),
            )
            self.assertEqual(repair.decision, "repair")
            return repair

        def child_intake(namespace, repository_id, repair, **overrides):
            return self.semantic_repair_fixture(
                namespace=namespace,
                repository_id=repository_id,
                source_id=repair.child_proposal_digest,
                child_source_digest=repair.child_proposal_digest,
                parent_repair=repair,
                result_head_sha="f" * 40,
                intake_only=True,
                **overrides,
            )

        def bind_child(repair, fixture):
            binding = RepairChildTaskBindingV1.from_dict(
                {
                    "schema_version": 1,
                    "child_proposal_digest": repair.child_proposal_digest,
                    "child_task_id": fixture["task"].task_id,
                    "child_intent_digest": fixture["intent_digest"],
                }
            )
            self.assertEqual(semantic_store.bind_repair_child(binding), binding)
            return binding

        ordinary_repository = "owner/m6-ordinary-hex-source"
        ordinary_payload = self.payload(
            repository=ordinary_repository,
            source="0" * 64,
        )
        ordinary_payload["source_type"] = "api"
        ordinary_payload["source_digest"] = "1" * 64
        ordinary = self.service.intake(
            ordinary_payload,
            actor=OPERATOR,
            now=datetime.now(timezone.utc),
        )
        with self.subTest(stage="unknown-hex-api-source-remains-ordinary"):
            self.assertTrue(ordinary.created)
            self.assertEqual(ordinary.task.status, TaskStatus.QUEUED)

        pre_repository = "owner/m6-source-pre-bound"
        pre_repair = first_repair("source-pre-bound", pre_repository, "7" * 40)
        for index, direct_store in enumerate((False, True), start=1):
            with self.subTest(stage="pre-bound", direct_store=direct_store):
                with self.assertRaisesRegex(
                    StoreError, "repair proposal source digest mismatch"
                ):
                    child_intake(
                        f"source-pre-bound-poison-{index}",
                        pre_repository,
                        pre_repair,
                        child_source_digest_override=str(index) * 64,
                        intake_actor=OPERATOR,
                        direct_store_intake=direct_store,
                    )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                (SELECT count(*) FROM factory.tasks
                  WHERE repository_id=%s AND source_type='api' AND source_id=%s),
                (SELECT count(*) FROM factory.accepted_intents
                  WHERE repository_id=%s AND source_type='api' AND source_id=%s),
                (SELECT count(*) FROM factory.intake_identities
                  WHERE repository_id=%s AND source_type='api' AND source_id=%s)""",
                (
                    pre_repository,
                    pre_repair.child_proposal_digest,
                    pre_repository,
                    pre_repair.child_proposal_digest,
                    pre_repository,
                    pre_repair.child_proposal_digest,
                ),
            )
            with self.subTest(stage="pre-bound-no-poison-state"):
                self.assertEqual(cursor.fetchone(), (0, 0, 0))

        post_repository = "owner/m6-source-post-bound"
        post_repair = first_repair("source-post-bound", post_repository, "8" * 40)
        post_child = child_intake(
            "source-post-bound-child", post_repository, post_repair
        )
        post_binding = bind_child(post_repair, post_child)
        for index, direct_store in enumerate((False, True), start=3):
            with self.subTest(stage="post-bound", direct_store=direct_store):
                with self.assertRaisesRegex(
                    StoreError, "repair proposal source digest mismatch"
                ):
                    child_intake(
                        f"source-post-bound-poison-{index}",
                        post_repository,
                        post_repair,
                        child_source_digest_override=str(index) * 64,
                        intake_actor=OPERATOR,
                        direct_store_intake=direct_store,
                    )
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                (SELECT count(*) FROM factory.tasks
                  WHERE repository_id=%s AND source_type='api' AND source_id=%s),
                (SELECT state FROM factory.tasks WHERE task_id=%s),
                (SELECT child_task_id FROM factory.semantic_child_task_bindings
                  WHERE child_proposal_digest=%s)""",
                (
                    post_repository,
                    post_repair.child_proposal_digest,
                    post_child["task"].task_id,
                    post_repair.child_proposal_digest,
                ),
            )
            with self.subTest(stage="post-bound-binding-remains-current"):
                count, state, child_task_id = cursor.fetchone()
                self.assertEqual(
                    (count, state, str(child_task_id)),
                    (1, "queued", post_child["task"].task_id),
                )
        replay = self.service.intake(
            post_child["intake"],
            actor=REPAIR_CHILD_BROKER,
            now=datetime.now(timezone.utc),
        )
        with self.subTest(stage="broker-replay-remains-current"):
            self.assertEqual(
                (replay.created, replay.task.task_id, replay.task.status),
                (True, post_child["task"].task_id, TaskStatus.QUEUED),
            )
            self.assertEqual(post_binding.child_task_id, replay.task.task_id)

        mismatch_repository = "owner/m6-claim-owner-mismatch"
        mismatch_repair = first_repair(
            "claim-owner-mismatch", mismatch_repository, "9" * 40
        )
        mismatch_child = child_intake(
            "claim-owner-mismatch-child", mismatch_repository, mismatch_repair
        )
        bind_child(mismatch_repair, mismatch_child)
        mismatch_key = canonical_digest({"case": "direct-store-owner-mismatch"})

        def claim_state(task_id, command_key):
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT t.state,
                    (SELECT count(*) FROM factory.runs WHERE task_id=t.task_id),
                    (SELECT count(*) FROM factory.command_results
                      WHERE idempotency_key=%s)
                    FROM factory.tasks t WHERE t.task_id=%s""",
                    (command_key, task_id),
                )
                return cursor.fetchone()

        before_mismatch = claim_state(mismatch_child["task"].task_id, mismatch_key)
        forged_grant = None
        with self.subTest(stage="direct-store-owner-mismatch"):
            with self.assertRaisesRegex(
                StoreError, "claim owner must match worker actor"
            ):
                forged_grant = self.store.claim(
                    ClaimRequest(
                        WORKER.actor_id,
                        RunRole.WRITER,
                        (mismatch_repository,),
                        60,
                    ),
                    SECOND_WORKER,
                    datetime.now(timezone.utc),
                    idempotency_key=mismatch_key,
                )
        after_mismatch = claim_state(mismatch_child["task"].task_id, mismatch_key)
        with self.subTest(stage="owner-mismatch-has-no-durable-effects"):
            self.assertIsNone(forged_grant)
            self.assertEqual(before_mismatch, ("queued", 0, 0))
            self.assertEqual(after_mismatch, before_mismatch)

        role_repository = "owner/m6-claim-role"
        role_repair = first_repair("claim-role", role_repository, "a" * 40)
        role_child = child_intake("claim-role-child", role_repository, role_repair)
        bind_child(role_repair, role_child)
        reader_grant = self.store.claim(
            ClaimRequest(
                WORKER.actor_id,
                RunRole.READER,
                (role_repository,),
                60,
            ),
            WORKER,
            datetime.now(timezone.utc),
            idempotency_key=canonical_digest({"case": "direct-store-reader"}),
        )
        self.assertIsNone(reader_grant)
        self.assertEqual(
            claim_state(
                role_child["task"].task_id,
                canonical_digest({"case": "unused-reader-state-key"}),
            )[:2],
            ("queued", 0),
        )
        writer_grant = self.store.claim(
            ClaimRequest(
                WORKER.actor_id,
                RunRole.WRITER,
                (role_repository,),
                60,
            ),
            WORKER,
            datetime.now(timezone.utc),
            idempotency_key=canonical_digest({"case": "direct-store-writer"}),
        )
        self.assertIsNotNone(writer_grant)
        self.assertEqual(
            (
                writer_grant.task_id,
                writer_grant.owner,
                writer_grant.role,
                claim_state(
                    role_child["task"].task_id,
                    canonical_digest({"case": "unused-writer-state-key"}),
                )[:2],
            ),
            (
                role_child["task"].task_id,
                WORKER.actor_id,
                RunRole.WRITER,
                ("leased", 1),
            ),
        )


    def test_semantic_repair_functions_use_exact_digest_index_conditions(self):
        import psycopg

        repository_id = "owner/m6-repair-status-indexes"
        fixture = self.semantic_repair_fixture(
            namespace="repair-status-index-root",
            repository_id=repository_id,
            source_id="repair-status-index-root",
            result_head_sha="b" * 40,
        )
        published = fixture["published"]
        request = SemanticRepairRequestV1.from_dict(
            {
                "schema_version": 1,
                "subject_digest": published.subject.digest,
                "verdict_digest": fixture["verdict"].digest,
                "requested_cycle": 1,
                "previous_child_proposal_digest": None,
                "writer_id": published.subject.original_writer_id,
                "context_digest": canonical_digest(
                    {"case": "repair-status-index", "context": 1}
                ),
                "expected_workspace_result_digest": (
                    fixture["result"].workspace_result_digest
                ),
                "expected_fence": published.binding.fence,
                "expected_head_sha": published.subject.exact_head_sha,
                "expected_base_sha": published.subject.exact_base_sha,
                "expected_architecture_digest": (
                    published.subject.architecture_digest
                ),
                "expected_authority_digest": published.subject.authority_digest,
                "expected_diff_digest": published.subject.diff_digest,
                "expected_risk_level": published.subject.risk_level,
            }
        )
        semantic_store = PostgresSemanticCoordinatorStore(
            self.semantic_coordinator_url
        )
        repair = semantic_store.request_repair(
            fixture["task"].task_id,
            request,
            idempotency_key=canonical_digest(
                {"case": "repair-status-index", "operation": "repair"}
            ),
        )
        proposal_digest = repair.child_proposal_digest
        parent_head = repair.child_proposal.parent_exact_head_sha

        def status(source_id, source_digest, actor):
            with self.store._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    """SELECT factory.semantic_repair_intake_status(
                    %s,'api',%s,%s,%s,%s,%s)""",
                    (
                        repository_id,
                        source_id,
                        source_digest,
                        parent_head,
                        actor.kind,
                        actor.actor_id,
                    ),
                )
                return cursor.fetchone()[0]

        unknown_digest = "0" * 64
        with self.subTest(stage="functional-pre-bound-matrix"):
            self.assertEqual(status(unknown_digest, "1" * 64, OPERATOR), "ordinary")
            self.assertEqual(
                status(unknown_digest, unknown_digest, REPAIR_CHILD_BROKER),
                "not_pending",
            )
            self.assertEqual(
                status(proposal_digest, "2" * 64, OPERATOR),
                "digest_mismatch",
            )
            self.assertEqual(
                status(proposal_digest, proposal_digest, OPERATOR),
                "actor_mismatch",
            )
            self.assertEqual(
                status(proposal_digest, proposal_digest, REPAIR_CHILD_BROKER),
                "allowed",
            )

        child = self.semantic_repair_fixture(
            namespace="repair-status-index-child",
            repository_id=repository_id,
            source_id=proposal_digest,
            child_source_digest=proposal_digest,
            parent_repair=repair,
            result_head_sha="c" * 40,
            intake_only=True,
        )
        binding = RepairChildTaskBindingV1.from_dict(
            {
                "schema_version": 1,
                "child_proposal_digest": proposal_digest,
                "child_task_id": child["task"].task_id,
                "child_intent_digest": child["intent_digest"],
            }
        )
        self.assertEqual(semantic_store.bind_repair_child(binding), binding)
        with self.subTest(stage="functional-post-bound-matrix"):
            self.assertEqual(
                status(proposal_digest, proposal_digest, REPAIR_CHILD_BROKER),
                "bound",
            )
            self.assertEqual(
                status(proposal_digest, "3" * 64, OPERATOR),
                "digest_mismatch",
            )

        ordinary_payload = self.payload(
            repository=repository_id,
            source="ordinary-api-" + "x" * 64,
        )
        ordinary_payload["source_type"] = "api"
        ordinary = self.service.intake(
            ordinary_payload,
            actor=OPERATOR,
            now=datetime.now(timezone.utc),
        )
        with self.store._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT factory.semantic_task_claimable(
                task_id,intent_id,intake_actor_kind,intake_actor_id,%s,'writer')
                FROM factory.tasks WHERE task_id=%s""",
                (WORKER.actor_id, ordinary.task.task_id),
            )
            ordinary_claimable = cursor.fetchone()[0]
        with self.subTest(stage="unknown-long-api-source-remains-ordinary"):
            self.assertTrue(ordinary_claimable)

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """CREATE TEMP TABLE repair_intake_plan_args (
                p_repository_id text,
                p_source_type text,
                p_source_id text,
                p_source_digest char(64),
                p_exact_head_sha char(40),
                p_actor_kind text,
                p_actor_id text
                ) ON COMMIT DROP"""
            )
            cursor.execute(
                """INSERT INTO repair_intake_plan_args VALUES
                (%s,'api',%s,%s,%s,'repair_broker',
                 'semantic-repair-child-broker')""",
                (repository_id, proposal_digest, proposal_digest, parent_head),
            )
            cursor.execute("ANALYZE repair_intake_plan_args")
            cursor.execute(
                """SELECT p.prosrc
                FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                WHERE n.nspname='factory'
                  AND p.proname='semantic_repair_intake_status'
                  AND p.pronargs=7"""
            )
            function_body = cursor.fetchone()[0].strip().removesuffix(";")
            cursor.execute("SET LOCAL enable_seqscan=off")
            cursor.execute("SET LOCAL enable_bitmapscan=off")
            cursor.execute(
                "EXPLAIN (FORMAT JSON, COSTS OFF) "
                + function_body
                + " FROM repair_intake_plan_args"
            )
            plan = cursor.fetchone()[0][0]["Plan"]

        def plan_nodes(node):
            yield node
            for child_plan in node.get("Plans", ()):  # pragma: no branch
                yield from plan_nodes(child_plan)

        relation_scans = {
            relation: [
                node
                for node in plan_nodes(plan)
                if node.get("Relation Name") == relation
            ]
            for relation in (
                "semantic_child_proposals",
                "semantic_child_task_bindings",
            )
        }
        expected_indexes = {
            "semantic_child_proposals": "semantic_child_proposals_pkey",
            "semantic_child_task_bindings": (
                "semantic_child_task_bindings_child_proposal_digest_key"
            ),
        }
        for relation, scans in relation_scans.items():
            with self.subTest(stage="index-plan", relation=relation):
                self.assertTrue(scans, plan)
                for scan in scans:
                    self.assertEqual(scan.get("Index Name"), expected_indexes[relation])
                    self.assertIn("Index Cond", scan, plan)
                    self.assertIn("child_proposal_digest", scan["Index Cond"])
                    self.assertIn("p_source_id", scan["Index Cond"])

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """CREATE TEMP TABLE semantic_claimable_plan_args (
                p_task_id uuid,
                p_intent_id uuid,
                p_intake_actor_kind text,
                p_intake_actor_id text,
                p_requested_owner text,
                p_requested_role text
                ) ON COMMIT DROP"""
            )
            cursor.execute(
                """INSERT INTO semantic_claimable_plan_args
                SELECT task_id,intent_id,intake_actor_kind,intake_actor_id,%s,'writer'
                FROM factory.tasks WHERE task_id=%s""",
                (WORKER.actor_id, child["task"].task_id),
            )
            cursor.execute("ANALYZE semantic_claimable_plan_args")
            cursor.execute(
                """SELECT p.prosrc
                FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                WHERE n.nspname='factory'
                  AND p.proname='semantic_task_claimable'
                  AND p.pronargs=6"""
            )
            function_body = cursor.fetchone()[0].strip().removesuffix(";")
            cursor.execute("SET LOCAL enable_seqscan=off")
            cursor.execute("SET LOCAL enable_bitmapscan=off")
            cursor.execute(
                "EXPLAIN (FORMAT JSON, COSTS OFF) "
                + function_body
                + " FROM semantic_claimable_plan_args"
            )
            claimable_plan = cursor.fetchone()[0][0]["Plan"]

        proposal_scans = [
            node
            for node in plan_nodes(claimable_plan)
            if node.get("Relation Name") == "semantic_child_proposals"
            and node.get("Alias") == "proposal"
        ]
        with self.subTest(stage="claimable-proposal-index-plan"):
            self.assertTrue(proposal_scans, claimable_plan)
            for scan in proposal_scans:
                self.assertEqual(
                    scan.get("Index Name"),
                    "semantic_child_proposals_pkey",
                )
                self.assertIn("Index Cond", scan, claimable_plan)
                self.assertIn("child_proposal_digest", scan["Index Cond"])
                self.assertIn("source_digest", scan["Index Cond"])


if __name__ == "__main__":
    unittest.main()
