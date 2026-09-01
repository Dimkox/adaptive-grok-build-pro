from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
import time
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

        exception_payload = self.payload(source="wrong-exception-scope")
        exception_payload["m0_authority"] = {
            "bootstrap_exception": "local-bootstrap",
            "issuer": "repository-owner",
            "scope": "task:intake",
            "expires_at": "2026-09-01T20:00:00+00:00",
        }
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO factory.m0_bootstrap_exceptions
                (exception_id,issuer,scope,expires_at,approval_digest,repository_id,policy_digest,action)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'task:intake')""",
                (
                    "local-bootstrap", "repository-owner", "task:intake", "2026-09-01T20:00:00+00:00",
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

    def test_event_repair_and_database_deadline_limits_fail_closed(self):
        import psycopg

        event_payload = self.payload(source="event-limit")
        event_payload["limits"]["max_events"] = 2
        event_task = self.service.intake(event_payload, actor=OPERATOR, now=NOW).task
        event_grant = self.service.claim(
            owner="event-worker", role=RunRole.READER, repositories=(event_task.repository_id,),
            lease_seconds=60, actor=WORKER, now=NOW,
        )
        with self.assertRaises(BudgetError):
            self.service.release(event_grant, outcome=FailureClass.WORKER_LOST, actor=WORKER, now=NOW)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT state,current_run_id,(SELECT count(*) FROM factory.task_events WHERE task_id=t.task_id) FROM factory.tasks t WHERE task_id=%s",
                (event_task.task_id,),
            )
            self.assertEqual(cursor.fetchone(), ("leased", uuid.UUID(event_grant.run_id), 2))

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
        from adaptive_factory.admin import bootstrap_local

        login = "factory_service_test"
        password = "-".join(("local", "runtime", "bootstrap", "test"))
        from psycopg.conninfo import conninfo_to_dict, make_conninfo

        runtime_url = make_conninfo(**{**conninfo_to_dict(DATABASE_URL), "user": login, "password": password})
        result = bootstrap_local(DATABASE_URL, login, password, runtime_url)
        self.assertEqual(result["database_role"], "factory_runtime")
        self.assertEqual(result["schema_version"], 9)
        with psycopg.connect(runtime_url) as connection, connection.cursor() as cursor:
            cursor.execute("SET ROLE factory_runtime")
            cursor.execute("SELECT session_user,current_user")
            self.assertEqual(cursor.fetchone(), (login, "factory_runtime"))
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute("DROP ROLE IF EXISTS " + login)

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
