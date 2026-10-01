"""Real PostgreSQL authority and recovery tests; no provider is ever called."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
from importlib.resources import files
import json
import unittest

from adaptive_factory.contracts import ContractError, canonical_digest
from adaptive_factory.model_rotator import (
    ModelRotator, PostgresRotationStore, ProviderRegistryV1, RotationBindingV1,
    TransportResult,
)
from factory.tests import test_execution_persistence_postgres as execution_fixture
from factory.tests.test_postgres_integration import DATABASE_URL


@unittest.skipUnless(DATABASE_URL, "FACTORY_TEST_DATABASE_URL must name a disposable database")
class ModelRotatorPostgresTests(unittest.TestCase):
    # Compose the existing fixture methods, not its TestCase inheritance: inheriting
    # the class would silently discover its hundreds of unrelated tests a second time.
    setUpClass = classmethod(execution_fixture.ExecutionPersistencePostgresTests.setUpClass.__func__)
    tearDownClass = classmethod(execution_fixture.ExecutionPersistencePostgresTests.tearDownClass.__func__)
    runtime_store = classmethod(execution_fixture.ExecutionPersistencePostgresTests.runtime_store.__func__)
    setUp = execution_fixture.ExecutionPersistencePostgresTests.setUp
    submit = execution_fixture.ExecutionPersistencePostgresTests.submit
    selection = staticmethod(execution_fixture.ExecutionPersistencePostgresTests.selection)
    claim_execution = execution_fixture.ExecutionPersistencePostgresTests.claim_execution

    def binding(self, *, requests=2, token_limit=512, request_limit=None, grant=True):
        import psycopg

        registry = ProviderRegistryV1.from_dict(json.loads(
            files("adaptive_factory.resources").joinpath("model-rotator-registry.v1.json").read_text()
        ))
        task, execution = self.claim_execution("rotator-fixture", capabilities=["usage"])
        self.store.reserve_budget(
            execution.lease, 1, 1024, 30, "a" * 64, "b" * 64,
            execution_fixture.WORKER,
        )
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "UPDATE factory.runs SET lease_expires_at=clock_timestamp()+interval '5 minutes' WHERE run_id=%s",
                (execution.lease.run_id,),
            )
            row = connection.execute(
                "SELECT reservation_id,task_id,run_id,token_units,cost_usd_micros,wall_seconds,trim(reason_digest) "
                "FROM factory.budget_reservations WHERE run_id=%s AND released_at IS NULL",
                (execution.lease.run_id,),
            ).fetchone()
            attempt_id = connection.execute(
                "SELECT attempt_id::text FROM factory.attempts WHERE run_id=%s",
                (execution.lease.run_id,),
            ).fetchone()[0]
            grant_digest = canonical_digest({"fixture": "owner-request-grant", "request_units": requests})
            if grant:
                connection.execute(
                    "INSERT INTO factory.model_rotator_request_grants VALUES(%s,%s,%s,%s)",
                    (row[0], registry.registry_digest, requests, grant_digest),
                )
        budget_digest = hashlib.sha256("|".join(str(value) for value in (*row, requests, grant_digest)).encode()).hexdigest()
        bind = RotationBindingV1.from_dict({
            "schema_version": 1, "tenant_id": task.repository_id, "repository_id": task.repository_id,
            "task_id": task.task_id, "run_id": execution.lease.run_id,
            "attempt_id": attempt_id, "fence": execution.lease.fence,
            "budget_reservation_id": str(row[0]), "budget_digest": budget_digest,
            "registry_digest": registry.registry_digest, "operation_id": "rotator-op-1",
            "requested_provider_id": "openrouter", "requested_model_id": "qwen/qwen3-coder:free",
            "remaining_token_units": token_limit,
            "remaining_request_units": requests if request_limit is None else request_limit,
        })
        return registry, bind, PostgresRotationStore(self.runtime_url)

    @staticmethod
    def requested_digest(binding):
        return canonical_digest({"provider_id": binding.requested_provider_id, "model_id": binding.requested_model_id})

    def claim(self, store, bind):
        return store.claim(bind, bind.registry_digest, 0, self.requested_digest(bind), 100)

    def owner_row(self, query, arguments=()):
        import psycopg
        with psycopg.connect(DATABASE_URL) as connection:
            return connection.execute(query, arguments).fetchone()

    def test_ddl_and_roles_expose_functions_not_mutable_state_or_request_grants(self):
        import psycopg
        tables = ("registry_policies", "states", "operations", "reservation_accounting", "request_grants")
        for suffix in tables:
            with self.subTest(table=suffix):
                privileges = self.owner_row(
                    "SELECT has_table_privilege('factory_runtime',%s,'INSERT'), "
                    "has_table_privilege('factory_runtime',%s,'UPDATE'), "
                    "has_table_privilege('factory_runtime',%s,'DELETE')",
                    (f"factory.model_rotator_{suffix}",) * 3,
                )
                self.assertEqual(privileges, (False, False, False))
        self.assertEqual(self.owner_row(
            "SELECT has_table_privilege('factory_runtime','factory.model_rotator_safe_status','SELECT'), "
            "has_function_privilege('factory_runtime','factory.model_rotator_reconcile_v1(character, text)','EXECUTE'), "
            "has_function_privilege('factory_migrator','factory.model_rotator_reconcile_v1(character, text)','EXECUTE')"
        ), (True, False, True))
        for query in (
            "UPDATE factory.model_rotator_states SET quarantined=false",
            "DELETE FROM factory.model_rotator_request_grants",
            "SELECT factory.model_rotator_reconcile_v1(%s,'release')",
        ):
            with self.subTest(query=query), psycopg.connect(self.runtime_url) as connection:
                connection.execute("SET LOCAL ROLE factory_runtime")
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    connection.execute(query, ("a" * 64,) if "%s" in query else ())

    def test_runtime_entrypoints_reject_null_invalid_and_open_persistence_shapes(self):
        import psycopg

        _, bind, store = self.binding()
        claim = self.claim(store, bind)
        token = claim["claim_token"]
        with psycopg.connect(self.runtime_url) as connection:
            connection.execute("SET LOCAL ROLE factory_runtime")
            self.assertEqual(connection.execute(
                "SELECT factory.model_rotator_reserve_v1(%s,%s,NULL,1), "
                "factory.model_rotator_reserve_v1(%s,%s,'request',NULL)",
                (bind.binding_digest, token, bind.binding_digest, token),
            ).fetchone(), (False, False))
            self.assertEqual(connection.execute(
                "SELECT factory.model_rotator_finish_v1(%s,%s,%s::jsonb,%s::jsonb,0,0), "
                "factory.model_rotator_quarantine_v1(%s,%s,%s::jsonb), "
                "factory.model_rotator_finish_v1(%s,%s,'[]'::jsonb,'[]'::jsonb,0,0)",
                (
                    bind.binding_digest, token,
                    json.dumps({"evidence_digest": "a" * 64, "next_model_digest": "b" * 64, "secret": "no"}),
                    json.dumps({"raw/provider": 123}), bind.binding_digest, token,
                    json.dumps({"evidence_digest": "a" * 64, "outcome_digest": "b" * 64, "secret": "no"}),
                    bind.binding_digest, token,
                ),
            ).fetchone(), (False, False, False))
            malformed = dict(bind.to_dict(), task_id="not-a-uuid")
            result = connection.execute(
                "SELECT factory.model_rotator_claim_v1(%s::jsonb,%s,%s,%s,0,%s,100)",
                (json.dumps(malformed), json.dumps(malformed), bind.binding_digest,
                 bind.registry_digest, self.requested_digest(bind)),
            ).fetchone()[0]
            self.assertEqual(result, {"error": "binding_digest_mismatch"})
            scalar_result = connection.execute(
                "SELECT factory.model_rotator_claim_v1('[]'::jsonb,'[]',%s,%s,0,%s,100)",
                (bind.binding_digest, bind.registry_digest, self.requested_digest(bind)),
            ).fetchone()[0]
            self.assertEqual(scalar_result, {"error": "binding_digest_mismatch"})
        with psycopg.connect(DATABASE_URL) as connection:
            self.assertEqual(connection.execute(
                "SELECT factory.model_rotator_reconcile_v1(NULL,NULL)"
            ).fetchone(), (False,))

    def test_python_sql_digest_parity_wire_independence_and_authority_join(self):
        import psycopg
        registry, bind, store = self.binding()
        with self.assertRaisesRegex(ContractError, "authority_not_granted"):
            self.claim(store, replace(bind, budget_digest="0" * 64))
        with self.assertRaisesRegex(ContractError, "authority_not_granted"):
            self.claim(store, replace(bind, tenant_id="other/repository"))
        # Alternate JSON whitespace/order must not alter the SQL-derived field digest.
        wire = json.dumps(bind.to_dict(), indent=2)
        with psycopg.connect(self.runtime_url) as connection:
            connection.execute("SET LOCAL ROLE factory_runtime")
            claim = connection.execute(
                "SELECT factory.model_rotator_claim_v1(%s::jsonb,%s,%s,%s,0,%s,100)",
                (wire, wire, bind.binding_digest, registry.registry_digest, self.requested_digest(bind)),
            ).fetchone()[0]
        self.assertIsNone(claim.get("error"))
        stored = self.owner_row(
            "SELECT trim(binding_digest),trim(budget_digest),task_id::text,run_id::text,attempt_id::text,fence "
            "FROM factory.model_rotator_operations"
        )
        self.assertEqual(stored, (bind.binding_digest, bind.budget_digest, bind.task_id, bind.run_id, bind.attempt_id, bind.fence))
        with self.assertRaisesRegex(ContractError, "operation_already_claimed"):
            self.claim(PostgresRotationStore(self.runtime_url), bind)

    def test_no_owner_request_grant_means_no_dispatch_authority(self):
        _, bind, store = self.binding(grant=False)
        with self.assertRaisesRegex(ContractError, "authority_not_granted"):
            self.claim(store, bind)
        self.assertEqual(self.owner_row("SELECT count(*) FROM factory.model_rotator_operations"), (0,))

    def test_concurrent_claim_and_reserve_do_not_duplicate_or_exceed_binding_limits(self):
        _, bind, store = self.binding(requests=2, request_limit=1, token_limit=0)
        def claim_once(_):
            try:
                return self.claim(PostgresRotationStore(self.runtime_url), bind)
            except ContractError as error:
                return str(error)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(claim_once, range(2)))
        claims = [value for value in results if isinstance(value, dict)]
        self.assertEqual(len(claims), 1)
        self.assertIn("operation_already_claimed", results)
        token = claims[0]["claim_token"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            reserved = list(pool.map(lambda _: PostgresRotationStore(self.runtime_url).reserve_dispatch(
                bind.binding_digest, token, "request", 1), range(2)))
        self.assertEqual(sorted(reserved), [False, True])
        self.assertFalse(store.reserve_dispatch(bind.binding_digest, token, "token", 1))
        self.assertEqual(self.owner_row(
            "SELECT held_request_units,settled_request_units,held_token_units FROM factory.model_rotator_reservation_accounting"
        ), (1, 0, 0))

    def test_expired_claim_quarantine_commits_before_error_and_owner_release_unblocks(self):
        _, bind, store = self.binding()
        claim = self.claim(store, bind)
        self.assertTrue(store.reserve_dispatch(bind.binding_digest, claim["claim_token"], "request", 1))
        self.owner_row(
            "UPDATE factory.model_rotator_operations SET claim_expires_at=clock_timestamp()-interval '1 second' "
            "WHERE binding_digest=%s RETURNING state", (bind.binding_digest,)
        )
        with self.assertRaisesRegex(ContractError, "reconciliation_required"):
            self.claim(PostgresRotationStore(self.runtime_url), bind)
        self.assertEqual(self.owner_row("SELECT state FROM factory.model_rotator_operations"), ("quarantined",))
        PostgresRotationStore(DATABASE_URL).reconcile(bind.binding_digest, settle=False)
        self.assertEqual(self.owner_row(
            "SELECT held_request_units,settled_request_units FROM factory.model_rotator_reservation_accounting"
        ), (0, 0))
        self.assertIn("claim_token", self.claim(store, replace(bind, operation_id="rotator-op-2")))

    def test_lease_expiry_rejects_dispatch_and_finish_without_partial_settlement(self):
        _, bind, store = self.binding()
        claim = self.claim(store, bind)
        self.owner_row(
            "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s RETURNING state",
            (bind.run_id,),
        )
        self.assertFalse(store.reserve_dispatch(bind.binding_digest, claim["claim_token"], "request", 1))
        with self.assertRaisesRegex(ContractError, "stale_rotation_claim"):
            store.finish(bind.binding_digest, claim["claim_token"], {
                "next_model_digest": self.requested_digest(bind), "evidence_digest": "e" * 64,
            }, {}, 0, 0)
        self.assertEqual(self.owner_row("SELECT state,evidence FROM factory.model_rotator_operations"), ("claimed", None))
        self.assertEqual(self.owner_row("SELECT held_request_units,settled_request_units FROM factory.model_rotator_reservation_accounting"), (0, 0))

    def test_finish_cas_failure_rolls_back_and_success_settles_once(self):
        import psycopg
        _, bind, store = self.binding()
        claim = self.claim(store, bind)
        token = claim["claim_token"]
        self.assertTrue(store.reserve_dispatch(bind.binding_digest, token, "request", 1))
        self.owner_row("UPDATE factory.model_rotator_states SET version=1 RETURNING version")
        evidence = {
            "next_model_digest": self.requested_digest(bind),
            "evidence_digest": "e" * 64,
            "status": "selected",
            "state_version": 0,
        }
        with self.assertRaises(psycopg.errors.SerializationFailure):
            store.finish(bind.binding_digest, token, evidence, {}, 0, 0)
        self.assertEqual(self.owner_row("SELECT state,evidence FROM factory.model_rotator_operations"), ("claimed", None))
        self.assertEqual(self.owner_row("SELECT held_request_units,settled_request_units FROM factory.model_rotator_reservation_accounting"), (1, 0))
        self.owner_row("UPDATE factory.model_rotator_states SET version=0 RETURNING version")
        store.finish(bind.binding_digest, token, evidence, {}, 0, 0)
        self.assertEqual(self.claim(PostgresRotationStore(self.runtime_url), bind), {"replay": {
            "evidence_digest": "e" * 64,
            "next_model_digest": self.requested_digest(bind),
        }})
        self.assertEqual(self.owner_row("SELECT held_request_units,settled_request_units FROM factory.model_rotator_reservation_accounting"), (0, 1))

    def test_bundled_registry_two_operations_reconnect_and_owner_settlement(self):
        registry, bind, store = self.binding(requests=3)
        result = TransportResult.success(response_digest="a" * 64, input_tokens=2, output_tokens=1)
        transport_calls = []
        def transport(*args):
            transport_calls.append(args)
            return result
        first = ModelRotator(registry, store, enabled=True).execute(bind, transport, now=100)
        self.assertEqual(first["status"], "selected")
        replay = ModelRotator(
            registry, PostgresRotationStore(self.runtime_url), enabled=True
        ).execute(bind, transport, now=101)
        self.assertEqual(replay, {
            "evidence_digest": first["evidence_digest"],
            "next_model_digest": first["next_model_digest"],
        })
        self.assertEqual(len(transport_calls), 1)
        self.assertEqual(self.owner_row(
            "SELECT evidence,held_request_units,settled_request_units "
            "FROM factory.model_rotator_operations o JOIN factory.model_rotator_reservation_accounting a "
            "ON a.reservation_id=o.reservation_id AND a.registry_digest=o.registry_digest "
            "WHERE o.binding_digest=%s", (bind.binding_digest,)
        ), (replay, 0, 1))
        second_binding = replace(bind, operation_id="rotator-op-2")
        second = ModelRotator(registry, PostgresRotationStore(self.runtime_url), enabled=True).execute(
            second_binding, transport, now=102)
        self.assertEqual((second["status"], second["state_version"]), ("selected", 1))
        third = replace(bind, operation_id="rotator-op-3")
        claim = store.claim(third, third.registry_digest, 0, self.requested_digest(third), 103)
        self.assertTrue(store.reserve_dispatch(third.binding_digest, claim["claim_token"], "request", 1))
        store.quarantine(third.binding_digest, claim["claim_token"], {
            "evidence_digest": "f" * 64, "status": "needs_human", "state_version": claim["version"],
        })
        PostgresRotationStore(DATABASE_URL).reconcile(third.binding_digest, settle=True)
        self.assertEqual(self.owner_row("SELECT held_request_units,settled_request_units FROM factory.model_rotator_reservation_accounting"), (0, 3))
