from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from fastapi.testclient import TestClient

from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.landing_activation_probe import LandingActivationProbeService, activation_probe_profile
from adaptive_factory.landing_sqlite_store import SQLiteLandingJobStore
from adaptive_factory.models import Actor


REPOSITORY = Path(__file__).resolve().parents[2]
PROFILE = activation_probe_profile("qwen-intl")
PROFILE_QWEN = activation_probe_profile("qwen")
SUCCESS = {
    "state": "normalized", **PROFILE,
    "spec_digest": "c" * 64, "response_digest": "d" * 64,
    "usage_input_units": 769, "usage_output_units": 191, "elapsed_ms": 1234,
}


class LandingActivationProbeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="landing-probe-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "runtime"
        self.store = self.open_store()
        self.calls = []
        self.probes = LandingActivationProbeService(
            self.store, profiles={"qwen-intl": PROFILE, "qwen": PROFILE_QWEN},
            runner=self.run_profile,
        )
        actors = {
            "operator-auth-value": Actor("operator-1", "operator", frozenset({"landing:probe"}), frozenset({"*"})),
            "wrong-scope-auth-value": Actor("operator-2", "operator", frozenset({"landing:read"}), frozenset({"*"})),
            "client-auth-value": Actor("client-1", "client", frozenset({"landing:probe"}), frozenset({"*"})),
        }
        self.client = TestClient(create_app(
            None, Authenticator(actors), execution_enabled=False,
            landing_service=object(), landing_only=True, landing_probe_service=self.probes,
        ))

    def open_store(self):
        return SQLiteLandingJobStore(self.root, repository_root=REPOSITORY, recovery_limit=0)

    def run_profile(self, profile_id):
        with sqlite3.connect(self.store.database_path) as connection:
            reservation = connection.execute(
                """SELECT state, provider_attempts, request_started_at, idempotency_digest
                     FROM landing_activation_probes
                    WHERE revision=1 ORDER BY rowid DESC LIMIT 1""",
            ).fetchone()
        self.assertIsNotNone(reservation)
        self.assertEqual("pending", reservation[0])
        self.assertEqual(1, reservation[1])
        self.assertTrue(reservation[2])
        self.assertNotEqual("probe-1", reservation[3])
        self.calls.append(profile_id)
        return {
            "state": "normalized", **activation_probe_profile(profile_id),
            "spec_digest": "c" * 64, "response_digest": "d" * 64,
            "usage_input_units": 769, "usage_output_units": 191, "elapsed_ms": 1234,
        }

    def tearDown(self):
        if getattr(self, "store", None) is not None:
            self.store.close()

    @staticmethod
    def headers(credential="operator-auth-value", key="probe-1"):
        return {"Authorization": f"Bearer {credential}", "Idempotency-Key": key}

    def test_landing_post_persists_before_one_mock_server_provider_call_and_same_key_never_replays(self):
        response = self.client.post("/v1/landing-probes", headers=self.headers(), json={"profile_id": "qwen-intl"})
        self.assertEqual(200, response.status_code, response.text)
        result = response.json()
        self.assertEqual("normalized", result["state"])
        self.assertEqual(1, result["provider_attempts"])
        self.assertEqual(["qwen-intl"], self.calls)
        replay = self.client.post("/v1/landing-probes", headers=self.headers(), json={"profile_id": "qwen-intl"})
        self.assertEqual(result, replay.json())
        self.assertEqual(1, len(self.calls))
        conflict = self.client.post("/v1/landing-probes", headers=self.headers(), json={"profile_id": "qwen"})
        self.assertEqual(409, conflict.status_code)
        self.assertEqual(1, len(self.calls))
        with sqlite3.connect(self.store.database_path) as connection:
            self.assertEqual(3, connection.execute("PRAGMA user_version").fetchone()[0])
            self.assertEqual(2, connection.execute(
                "SELECT count(*) FROM landing_activation_probes WHERE probe_id=?", (result["probe_id"],)
            ).fetchone()[0])
            self.assertEqual([(1, "pending"), (2, "normalized")], connection.execute(
                "SELECT revision, state FROM landing_activation_probes WHERE probe_id=? ORDER BY revision",
                (result["probe_id"],),
            ).fetchall())
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE landing_activation_probes SET state='failed' WHERE probe_id=?",
                    (result["probe_id"],),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "DELETE FROM landing_activation_probes WHERE probe_id=?",
                    (result["probe_id"],),
                )

    def test_operator_kind_dedicated_scope_landing_only_and_closed_profile_contract(self):
        self.assertEqual(403, self.client.post("/v1/landing-probes", headers=self.headers("wrong-scope-auth-value"), json={"profile_id": "qwen-intl"}).status_code)
        self.assertEqual(403, self.client.post("/v1/landing-probes", headers=self.headers("client-auth-value"), json={"profile_id": "qwen-intl"}).status_code)
        self.assertEqual(422, self.client.post("/v1/landing-probes", headers=self.headers(), json={"profile_id": "qwen-intl", "client_result": "forged"}).status_code)
        self.assertEqual(422, self.client.post("/v1/landing-probes", headers=self.headers("operator-auth-value", "bad-profile"), json={"profile_id": "grok-vision"}).status_code)
        self.assertEqual([], self.calls)
        general = TestClient(create_app(None, Authenticator({"operator-auth-value": Actor(
            "operator-1", "operator", frozenset({"landing:probe"}), frozenset({"*"})
        )}), execution_enabled=False, landing_service=object(), landing_only=False))
        self.assertEqual(404, general.post("/v1/landing-probes", headers=self.headers(), json={"profile_id": "qwen-intl"}).status_code)

    def test_read_is_restart_durable_and_never_calls_provider(self):
        created = self.client.post("/v1/landing-probes", headers=self.headers(), json={"profile_id": "qwen-intl"}).json()
        self.assertEqual(1, len(self.calls))
        result = self.client.get(f"/v1/landing-probes/{created['probe_id']}", headers={"Authorization": "Bearer operator-auth-value"})
        self.assertEqual(200, result.status_code, result.text)
        self.assertEqual(created, result.json())
        self.assertEqual(1, len(self.calls))

    def test_read_after_store_restart_is_durable_and_historical_769_191_id_is_not_backfilled(self):
        created = self.client.post("/v1/landing-probes", headers=self.headers(), json={"profile_id": "qwen-intl"}).json()
        self.store.close()
        self.store = self.open_store()
        probes = LandingActivationProbeService(
            self.store, profiles={"qwen-intl": PROFILE, "qwen": PROFILE_QWEN}, runner=self.run_profile,
        )
        self.client = TestClient(create_app(
            None, Authenticator({"operator-auth-value": Actor(
                "operator-1", "operator", frozenset({"landing:probe"}), frozenset({"*"})
            )}), execution_enabled=False, landing_service=object(), landing_only=True,
            landing_probe_service=probes,
        ))
        result = self.client.get(
            f"/v1/landing-probes/{created['probe_id']}",
            headers={"Authorization": "Bearer operator-auth-value"},
        )
        self.assertEqual(200, result.status_code)
        self.assertEqual(created, result.json())
        historical = self.client.get(
            "/v1/landing-probes/omni-activate-20260916-e7d0f72b",
            headers={"Authorization": "Bearer operator-auth-value"},
        )
        self.assertEqual(404, historical.status_code)
        self.assertEqual(["qwen-intl"], self.calls)

    def test_contract_is_closed_matches_only_landing_only_routes_and_declares_auth(self):
        contract_path = REPOSITORY / "factory/contracts/openapi/landing-probe.v1.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract_ops = {
            (path, method): operation["operationId"]
            for path, path_item in contract["paths"].items()
            for method, operation in path_item.items()
        }
        runtime_ops = {
            (route.path, method.lower()): route.operation_id
            for route in self.client.app.routes
            if route.path.startswith("/v1/landing-probes")
            for method in route.methods
        }
        self.assertEqual(runtime_ops, contract_ops)
        for path_item in contract["paths"].values():
            for operation in path_item.values():
                self.assertTrue(operation["x-landing-only"])
                self.assertEqual("operator", operation["x-required-actor-kind"])
                self.assertEqual("landing:probe", operation["x-required-scope"])
                self.assertTrue(operation["security"])
        self.assertFalse(contract["components"]["schemas"]["ProbeRecord"]["additionalProperties"])
        self.assertFalse(contract["paths"]["/v1/landing-probes"]["post"]["requestBody"]["content"]["application/json"]["schema"]["additionalProperties"])

    def test_pending_after_restart_becomes_unknown_and_same_key_never_dispatches(self):
        class SimulatedProcessCrash(BaseException):
            pass

        def crash_after_dispatch(profile_id):
            self.calls.append(profile_id)
            raise SimulatedProcessCrash

        crashed = LandingActivationProbeService(
            self.store, profiles={"qwen-intl": PROFILE}, runner=crash_after_dispatch,
        )
        with self.assertRaises(SimulatedProcessCrash):
            crashed.create(idempotency_key="crashed-key", profile_id="qwen-intl")
        with sqlite3.connect(self.store.database_path) as connection:
            probe_id, state = connection.execute(
                "SELECT probe_id, state FROM landing_activation_probes ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
        self.assertEqual("pending", state)
        self.assertEqual(["qwen-intl"], self.calls)

        self.store.close()
        self.store = self.open_store()
        self.assertEqual("unknown", self.store.get_activation_probe(probe_id)["state"])
        replay_calls = []
        replay_service = LandingActivationProbeService(
            self.store, profiles={"qwen-intl": PROFILE}, runner=replay_calls.append,
        )
        self.client = TestClient(create_app(
            None, Authenticator({"operator-auth-value": Actor(
                "operator-1", "operator", frozenset({"landing:probe"}), frozenset({"*"})
            )}), execution_enabled=False, landing_service=object(), landing_only=True,
            landing_probe_service=replay_service,
        ))
        response = self.client.post(
            "/v1/landing-probes", headers=self.headers(key="crashed-key"),
            json={"profile_id": "qwen-intl"},
        )
        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual(probe_id, response.json()["probe_id"])
        self.assertEqual("unknown", response.json()["state"])
        self.assertEqual([], replay_calls)
        self.assertEqual(["qwen-intl"], self.calls)

    def test_provider_failure_persists_only_allowlisted_category_and_status(self):
        def unsafe_failure(_profile_id):
            self.calls.append("dispatched")
            error = RuntimeError("secret-token raw-provider-body: private details")
            error.category = "permission"
            error.http_status = 403
            raise error

        failing = LandingActivationProbeService(
            self.store, profiles={"qwen-intl": PROFILE}, runner=unsafe_failure,
        )
        record = failing.create(idempotency_key="failure", profile_id="qwen-intl")
        self.assertEqual(("failed", "permission", 403),
                         (record["state"], record["failure_category"], record["http_status"]))
        self.assertNotIn("secret-token", repr(record))
        self.assertNotIn("raw-provider-body", repr(record))
        with sqlite3.connect(self.store.database_path) as connection:
            persisted = repr(connection.execute(
                "SELECT * FROM landing_activation_probes WHERE probe_id=?", (record["probe_id"],)
            ).fetchall())
        self.assertNotIn("secret-token", persisted)
        self.assertNotIn("raw-provider-body", persisted)

    def test_concurrent_same_key_causes_one_call(self):
        def post(_):
            return self.client.post("/v1/landing-probes", headers=self.headers("operator-auth-value", "concurrent"), json={"profile_id": "qwen-intl"})
        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(post, range(8)))
        self.assertTrue(all(item.status_code == 200 for item in responses), [item.text for item in responses])
        self.assertEqual(1, len(self.calls))
        self.assertEqual(1, len({item.json()["probe_id"] for item in responses}))


if __name__ == "__main__":
    unittest.main()
