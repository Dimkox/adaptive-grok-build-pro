import json
import os
from pathlib import Path
import socket
import stat
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import httpx
import uvicorn

from adaptive_factory import admin as admin_module
from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.models import Actor
from adaptive_factory.server import ServerError, build_app, load_actors, prepare_unix_socket
from adaptive_factory.settings import FactorySettings


class ServerTests(unittest.TestCase):
    def test_semantic_login_provisioners_bind_distinct_capability_roles(self):
        with patch("adaptive_factory.admin._provision_semantic_login") as provision:
            admin_module.provision_semantic_validator_login(
                "postgresql://owner", "validator_login", "bounded-validator-password"
            )
            admin_module.provision_semantic_adjudicator_login(
                "postgresql://owner", "adjudicator_login", "bounded-adjudicator-password"
            )
        self.assertEqual(
            provision.call_args_list,
            [
                unittest.mock.call(
                    "postgresql://owner", "validator_login", "bounded-validator-password",
                    role="factory_semantic_validator", label="semantic validator",
                ),
                unittest.mock.call(
                    "postgresql://owner", "adjudicator_login", "bounded-adjudicator-password",
                    role="factory_semantic_adjudicator", label="semantic adjudicator",
                ),
            ],
        )

    def test_attestor_dsn_alone_never_becomes_a_workspace_observer(self):
        settings = FactorySettings(
            "postgresql://runtime", Path("/run/factory.sock"), Path("/run/actors.json"),
            "postgresql://attestor",
        )
        with (
            patch("adaptive_factory.server.PostgresFactoryStore") as runtime_store,
            patch("adaptive_factory.server.PostgresArtifactAttestationStore") as attestor_store,
            patch("adaptive_factory.server.load_actors", return_value={}),
            patch("adaptive_factory.server.Authenticator"),
            patch("adaptive_factory.server.create_app", side_effect=lambda service, auth: service),
        ):
            service = build_app(settings)
        runtime_store.assert_called_once_with(settings.database_url)
        attestor_store.assert_called_once_with(settings.artifact_attestor_database_url)
        self.assertIsNone(service.artifact_broker)
        self.assertIs(service.artifact_attestation_store, attestor_store.return_value)

    def test_semantic_dsn_wires_only_the_coordinator_capability(self):
        settings = FactorySettings(
            "postgresql://runtime",
            Path("/run/factory.sock"),
            Path("/run/actors.json"),
            "postgresql://attestor",
            "postgresql://semantic-coordinator",
        )
        with (
            patch("adaptive_factory.server.PostgresFactoryStore") as runtime_store,
            patch("adaptive_factory.server.PostgresArtifactAttestationStore") as attestor_store,
            patch("adaptive_factory.server.PostgresSemanticCoordinatorStore") as semantic_store,
            patch("adaptive_factory.server.load_actors", return_value={}),
            patch("adaptive_factory.server.Authenticator"),
            patch("adaptive_factory.server.create_app", side_effect=lambda service, auth: service),
        ):
            service = build_app(settings)
        runtime_store.assert_called_once_with(settings.database_url)
        attestor_store.assert_called_once_with(settings.artifact_attestor_database_url)
        semantic_store.assert_called_once_with(settings.semantic_coordinator_database_url)
        self.assertIs(service.semantic_store, semantic_store.return_value)
        self.assertIsNone(service.snapshot_broker)
        self.assertIsNone(service.artifact_broker)

    def test_semantic_capability_dsns_wire_three_isolated_stores(self):
        settings = FactorySettings(
            "postgresql://runtime",
            Path("/run/factory.sock"),
            Path("/run/actors.json"),
            None,
            "postgresql://semantic-coordinator",
            "postgresql://semantic-validator",
            "postgresql://semantic-adjudicator",
        )
        with (
            patch("adaptive_factory.server.PostgresFactoryStore"),
            patch("adaptive_factory.server.PostgresSemanticCoordinatorStore") as coordinator,
            patch("adaptive_factory.server.PostgresSemanticValidatorStore") as validator,
            patch("adaptive_factory.server.PostgresSemanticAdjudicatorStore") as adjudicator,
            patch("adaptive_factory.server.load_actors", return_value={}),
            patch("adaptive_factory.server.Authenticator"),
            patch("adaptive_factory.server.create_app", side_effect=lambda service, auth: service),
        ):
            service = build_app(settings)
        coordinator.assert_called_once_with(settings.semantic_coordinator_database_url)
        validator.assert_called_once_with(settings.semantic_validator_database_url)
        adjudicator.assert_called_once_with(settings.semantic_adjudicator_database_url)
        self.assertIs(service.semantic_store, coordinator.return_value)
        self.assertIs(service.semantic_validator_store, validator.return_value)
        self.assertIs(service.semantic_adjudicator_store, adjudicator.return_value)

    def test_authenticated_request_reaches_real_unix_socket(self):
        class Service:
            @staticmethod
            def metrics(*, actor):
                return {
                    "actor": actor.actor_id,
                    "factory_capacity_budget_kill_and_reconcile_outcomes_total": {},
                }

        token = "-".join(("uds", "operator", "token", "value"))
        actor = Actor("uds-operator", "operator", frozenset({"factory:reconcile"}), frozenset({"*"}))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            path = root / "control.sock"
            listener = prepare_unix_socket(path)
            server = uvicorn.Server(
                uvicorn.Config(create_app(Service(), Authenticator({token: actor})), access_log=False, log_config=None)
            )
            thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
            thread.start()
            try:
                client = httpx.Client(transport=httpx.HTTPTransport(uds=str(path)), base_url="http://factory.local")
                deadline = time.monotonic() + 2
                while True:
                    try:
                        unauthorized = client.get("/metrics")
                        break
                    except httpx.ConnectError:
                        if time.monotonic() >= deadline:
                            self.fail("Unix socket server did not become ready")
                        time.sleep(0.02)
                self.assertEqual(unauthorized.status_code, 401)
                response = client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
                self.assertEqual(
                    response.json(),
                    {
                        "actor": "uds-operator",
                        "factory_capacity_budget_kill_and_reconcile_outcomes_total": {"auth_rejected": 1},
                    },
                )
                client.close()
            finally:
                server.should_exit = True
                thread.join(timeout=2)
                listener.close()

    def test_server_prepares_only_an_owned_mode_0660_unix_socket(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            path = root / "control.sock"
            listener = prepare_unix_socket(path)
            try:
                metadata = path.lstat()
                self.assertTrue(stat.S_ISSOCK(metadata.st_mode))
                self.assertEqual(stat.S_IMODE(metadata.st_mode), 0o660)
                self.assertEqual(metadata.st_uid, os.geteuid())
                self.assertEqual(listener.family, socket.AF_UNIX)
            finally:
                listener.close()
                path.unlink()
            regular = root / "not-a-socket"
            regular.write_text("do not replace", encoding="utf-8")
            with self.assertRaises(ServerError):
                prepare_unix_socket(regular)
            with self.assertRaises(ServerError):
                prepare_unix_socket(Path("relative.sock"))

    def test_actor_config_loads_no_follow_private_token_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            token = root / "worker.token"
            token.write_text("worker-token-value-123\n", encoding="utf-8")
            token.chmod(0o600)
            config = root / "actors.json"
            config.write_text(
                json.dumps({"actors": [{"actor_id": "worker", "kind": "worker", "scopes": ["task:claim"], "repositories": ["owner/repo"], "token_file": str(token)}]}),
                encoding="utf-8",
            )
            config.chmod(0o600)
            actors = load_actors(config)
            self.assertEqual(actors["worker-token-value-123"].actor_id, "worker")
            config.chmod(0o644)
            with self.assertRaises(ServerError):
                load_actors(config)

    def test_actor_config_accepts_only_named_semantic_capability_kinds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            records = []
            for kind, scope in (
                ("validator", "semantic:validate"),
                ("adjudicator", "semantic:adjudicate"),
            ):
                token = root / f"{kind}.token"
                token.write_text(f"bounded-{kind}-token-value\n", encoding="utf-8")
                token.chmod(0o600)
                records.append({
                    "actor_id": kind,
                    "kind": kind,
                    "scopes": [scope],
                    "repositories": ["owner/repository"],
                    "token_file": str(token),
                })
            config = root / "actors.json"
            config.write_text(json.dumps({"actors": records}), encoding="utf-8")
            config.chmod(0o600)
            actors = load_actors(config)
        self.assertEqual({actor.kind for actor in actors.values()}, {"validator", "adjudicator"})

    def test_actor_config_rejects_relative_and_symlinked_ancestry(self):
        with self.assertRaises(ServerError):
            load_actors(Path("actors.json"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            private = root / "private"
            private.mkdir(mode=0o700)
            token = private / "token"
            token.write_text("-".join(("actor", "token", "value", "123")) + "\n", encoding="utf-8")
            token.chmod(0o600)
            config = private / "actors.json"
            config.write_text(
                json.dumps({"actors": [{
                    "actor_id": "actor", "kind": "operator", "scopes": ["factory:reconcile"],
                    "repositories": ["*"], "token_file": str(token),
                }]}),
                encoding="utf-8",
            )
            config.chmod(0o600)
            alias = root / "alias"
            alias.symlink_to(private, target_is_directory=True)
            with self.assertRaises(ServerError):
                load_actors(alias / "actors.json")


if __name__ == "__main__":
    unittest.main()
