from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime, timedelta, timezone
from functools import partial
import os
import threading
import time
import unittest
import uuid

from adaptive_factory.migrations import PostgresMigrator, discover_migrations
from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.contracts import TaskIntakeV1, canonical_digest
from adaptive_factory.models import Actor, FailureClass, RunRole, TaskStatus
from adaptive_factory.service import AuthorizationError, FactoryService
from adaptive_factory.store import BudgetError, FenceError, PostgresFactoryStore, StoreError
from factory.tests.test_contracts import valid_intake


DATABASE_URL = os.environ.get("FACTORY_TEST_DATABASE_URL")
NOW = datetime.now(timezone.utc).replace(microsecond=0)
OPERATOR = Actor(
    "operator",
    "operator",
    frozenset({"task:submit", "task:cancel", "factory:kill", "factory:reconcile"}),
    frozenset({"*"}),
)
WORKER = Actor(
    "worker", "worker", frozenset({"task:claim", "task:heartbeat", "task:release", "task:budget"}), frozenset({"*"})
)


@unittest.skipUnless(DATABASE_URL, "FACTORY_TEST_DATABASE_URL must name a disposable database")
class PostgresFactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        PostgresMigrator(DATABASE_URL).apply()

    def setUp(self):
        import psycopg

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "TRUNCATE factory.audit_log, factory.audit_heads, factory.task_events, factory.command_results, factory.metric_counters, factory.budget_reservations, factory.usage_observations, factory.capacity_allocations, factory.attempts, factory.runs, factory.lease_sequences, factory.kill_switches, factory.reconciliation_runs, factory.tasks, factory.accepted_intents, factory.intake_identities, factory.m0_authority_observations, factory.m0_bootstrap_exceptions RESTART IDENTITY"
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
        self.store = PostgresFactoryStore(DATABASE_URL)
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
                pausing_store = PausingCloseStore(DATABASE_URL)
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
        self.assertEqual((conflict.status_code, conflict.json()), (409, {"error": "conflict"}))

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
                "SELECT count(*) FROM factory.command_results WHERE action='intake'"
            )
            self.assertEqual(cursor.fetchone()[0], 3)

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
                store = PausingStore(DATABASE_URL)
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
        pausing_reserve_store = PausingReserveStore(DATABASE_URL)
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
        pausing_terminal_store = PausingTerminalStore(DATABASE_URL)
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
            },
        )
        intake = metrics["factory_intake_and_rejection_outcomes_total"]
        leases = metrics["factory_lease_reclaim_and_fence_rejection_total"]
        operations = metrics["factory_capacity_budget_kill_and_reconcile_outcomes_total"]
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
                other = FactoryService(PostgresFactoryStore(DATABASE_URL))
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
                    {"target": "dead", "reason": "deadline_expired", "accounting_quarantined": False},
                    "deadline_expired",
                    {"fence": settled_grant.fence, "accounting_quarantined": False},
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
                    {"target": "needs_human", "reason": "deadline_expired", "accounting_quarantined": True},
                    "deadline_expired",
                    {"fence": unsettled_grant.fence, "accounting_quarantined": True},
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
            first = FactoryService(ShortReconciliationStore(DATABASE_URL)).reconcile(actor=OPERATOR, now=NOW)
        finally:
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute("DROP TRIGGER delay_reconcile_release ON factory.runs")
                cursor.execute("DROP FUNCTION factory.delay_reconcile_release()")
        self.assertEqual(first.candidates, 4)
        self.assertGreater(first.repaired, 0)
        self.assertLess(first.repaired, first.candidates)
        second = FactoryService(ShortReconciliationStore(DATABASE_URL)).reconcile(
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
            FactoryService(ExpiringTransactionStore(DATABASE_URL)).reconcile(actor=OPERATOR, now=NOW)
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

                    self.assertEqual([item.version for item in PostgresMigrator(upgrade_url).apply()], [13])
                    upgraded_store = PostgresFactoryStore(upgrade_url)
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

            applied = PostgresMigrator(upgrade_url).apply()
            upgraded_store = PostgresFactoryStore(upgrade_url)
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
                    [9, 10, 11, 12, 13], "ready", 13, True,
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
            create_app(FactoryService(PostgresFactoryStore(DATABASE_URL)), Authenticator({token: reader})),
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
                {"error": "unavailable", "code": "database"},
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
        bounded_service = FactoryService(FastBoundStore(DATABASE_URL))
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
                    (503, {"error": "unavailable", "code": "database"}),
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
        counting_store = CountingStore(DATABASE_URL)
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

        bounded = FastBoundStore(DATABASE_URL)
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
        from adaptive_factory.admin import bootstrap_local

        login = "factory_service_test"
        password = "-".join(("local", "runtime", "bootstrap", "test"))
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        runtime_url = make_conninfo(**{**conninfo_to_dict(DATABASE_URL), "user": login, "password": password})
        result = bootstrap_local(DATABASE_URL, login, password, runtime_url)
        self.assertEqual(result["database_role"], "factory_runtime")
        self.assertEqual(result["schema_version"], 13)
        self.assertEqual(PostgresMigrator(DATABASE_URL).apply(expected_runtime_login=login), ())
        with psycopg.connect(runtime_url) as connection, connection.cursor() as cursor:
            cursor.execute("SET ROLE factory_runtime")
            cursor.execute("SELECT session_user,current_user")
            self.assertEqual(cursor.fetchone(), (login, "factory_runtime"))
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute("DROP ROLE IF EXISTS " + login)

    def test_bootstrap_rejects_unsafe_factory_role_attributes_and_memberships(self):
        import psycopg
        from adaptive_factory.admin import BootstrapError, bootstrap_local
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        def assert_rejected_before_login(login: str, password: str) -> None:
            runtime_url = make_conninfo(**{**conninfo_to_dict(DATABASE_URL), "user": login, "password": password})
            with self.assertRaises(BootstrapError):
                bootstrap_local(DATABASE_URL, login, password, runtime_url)
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (login,))
                self.assertIsNone(cursor.fetchone())

        with self.subTest(boundary="unsafe capability attribute"):
            login = "factory_unsafe_attribute_test"
            password = "-".join(("unsafe", "attribute", "test", "password"))
            try:
                with psycopg.connect(DATABASE_URL) as connection:
                    connection.execute("ALTER ROLE factory_runtime CREATEDB")
                assert_rejected_before_login(login, password)
            finally:
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute("ALTER ROLE factory_runtime NOCREATEDB")
                    cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(login)))

        with self.subTest(boundary="factory role is member of another role"):
            login = "factory_unsafe_parent_test"
            password = "-".join(("unsafe", "parent", "membership", "password"))
            parent = "factory_unexpected_parent_test"
            try:
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(sql.SQL("CREATE ROLE {} NOLOGIN NOINHERIT").format(sql.Identifier(parent)))
                    cursor.execute(
                        sql.SQL("GRANT {} TO factory_runtime").format(sql.Identifier(parent))
                    )
                assert_rejected_before_login(login, password)
            finally:
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        sql.SQL("REVOKE {} FROM factory_runtime").format(sql.Identifier(parent))
                    )
                    cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(login)))
                    cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(parent)))

        with self.subTest(boundary="factory role has an unexpected member"):
            login = "factory_unsafe_member_target"
            password = "-".join(("unsafe", "member", "target", "password"))
            member = "factory_unexpected_member_test"
            try:
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(sql.SQL("CREATE ROLE {} NOLOGIN NOINHERIT").format(sql.Identifier(member)))
                    cursor.execute(
                        sql.SQL("GRANT factory_runtime TO {}").format(sql.Identifier(member))
                    )
                assert_rejected_before_login(login, password)
            finally:
                with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                    cursor.execute(
                        sql.SQL("REVOKE factory_runtime FROM {}").format(sql.Identifier(member))
                    )
                    cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(login)))
                    cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(member)))

    def test_bootstrap_rejects_service_login_with_unexpected_membership(self):
        import psycopg
        from adaptive_factory.admin import BootstrapError, bootstrap_local
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        login = "factory_unsafe_service_test"
        password = "-".join(("unsafe", "service", "login", "password"))
        unexpected_role = "factory_unexpected_service_role"
        runtime_url = make_conninfo(**{**conninfo_to_dict(DATABASE_URL), "user": login, "password": password})
        try:
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("CREATE ROLE {} NOLOGIN NOINHERIT").format(sql.Identifier(unexpected_role))
                )
                cursor.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEROLE "
                        "NOCREATEDB NOREPLICATION NOBYPASSRLS PASSWORD {}"
                    ).format(sql.Identifier(login), sql.Literal(password))
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
                self.assertEqual(cursor.fetchall(), [(unexpected_role,)])
        finally:
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("REVOKE factory_runtime FROM {}").format(sql.Identifier(login))
                )
                cursor.execute(
                    sql.SQL("REVOKE {} FROM {}").format(
                        sql.Identifier(unexpected_role), sql.Identifier(login)
                    )
                )
                cursor.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(login)))
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
