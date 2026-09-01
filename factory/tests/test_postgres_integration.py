from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
import unittest
import uuid

from adaptive_factory.migrations import PostgresMigrator
from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.models import Actor, FailureClass, RunRole, TaskStatus
from adaptive_factory.service import FactoryService
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
            cursor.execute("UPDATE factory.capacity_counters SET active_count=0")
            cursor.execute(
                "INSERT INTO factory.m0_authority_observations(observation_id,observed_at,check_name,exact_head_sha,issuer,evidence_digest) VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    uuid.uuid4(),
                    NOW,
                    "adaptive-trust-ci/verified@06ecf1c875bc",
                    "3" * 40,
                    "external-trust-ci-api",
                    "7" * 64,
                ),
            )
        self.store = PostgresFactoryStore(DATABASE_URL)
        self.service = FactoryService(self.store)

    def payload(self, repository="owner/repository", source=None):
        value = valid_intake()
        value["repository_id"] = repository
        value["source_id"] = source or str(uuid.uuid4())
        value["m0_authority"]["observed_at"] = NOW.isoformat()
        return value

    def submit(self, repository="owner/repository", source=None):
        return self.service.intake(self.payload(repository, source), actor=OPERATOR, now=NOW)

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
                "SELECT has_column_privilege('factory_runtime','factory.capacity_counters','ceiling','UPDATE'), has_column_privilege('factory_runtime','factory.capacity_counters','active_count','UPDATE'), has_table_privilege('factory_runtime','factory.intake_identities','UPDATE')"
            )
            self.assertEqual(cursor.fetchone(), (False, True, False))
        forbidden = (
            ("UPDATE factory.accepted_intents SET body='{}'::jsonb",),
            ("UPDATE factory.task_events SET actor_id='tampered'",),
            ("UPDATE factory.audit_log SET actor_id='tampered'",),
            ("DELETE FROM factory.accepted_intents",),
            ("UPDATE factory.capacity_counters SET ceiling=999 WHERE scope_key='global:reader'",),
            ("UPDATE factory.intake_identities SET source_id='tampered'",),
        )
        for (statement,) in forbidden:
            with self.subTest(statement=statement), psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL ROLE factory_runtime")
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        cursor.execute(statement)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE factory_runtime")
            cursor.execute(
                "UPDATE factory.capacity_counters SET active_count=active_count WHERE scope_key='global:reader'"
            )
            self.assertEqual(cursor.rowcount, 1)


if __name__ == "__main__":
    unittest.main()
