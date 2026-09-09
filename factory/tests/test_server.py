import json
import os
from pathlib import Path
import socket
import stat
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

import httpx
import uvicorn

from adaptive_factory import admin as admin_module
from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.models import Actor
from adaptive_factory.server import ServerError, build_app, load_actors, prepare_unix_socket
from adaptive_factory.settings import FactorySettings, SettingsError


class ServerTests(unittest.TestCase):
    @staticmethod
    def execution_dependencies():
        class Registry:
            def resolve(self, requested, *, role):
                return requested, role

        class ArtifactVerifier:
            def attest_artifact(self, request):
                return request

        class SnapshotBroker:
            def snapshot(self, request, *, timeout_seconds):
                return request

        return Registry(), ArtifactVerifier(), SnapshotBroker()

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
                    "postgresql://owner",
                    "validator_login",
                    "bounded-validator-password",
                    role="factory_semantic_validator",
                    label="semantic validator",
                ),
                unittest.mock.call(
                    "postgresql://owner",
                    "adjudicator_login",
                    "bounded-adjudicator-password",
                    role="factory_semantic_adjudicator",
                    label="semantic adjudicator",
                ),
            ],
        )

    def test_semantic_dsn_wires_only_the_coordinator_capability(self):
        settings = FactorySettings(
            "postgresql://runtime",
            Path("/run/factory.sock"),
            Path("/run/actors.json"),
            semantic_coordinator_database_url="postgresql://semantic-coordinator",
        )
        with (
            patch("adaptive_factory.server.PostgresFactoryStore") as runtime_store,
            patch("adaptive_factory.server.PostgresArtifactAttestationStore") as attestor,
            patch("adaptive_factory.server.PostgresSemanticCoordinatorStore") as coordinator,
            patch("adaptive_factory.server.PostgresSemanticValidatorStore") as validator,
            patch("adaptive_factory.server.PostgresSemanticAdjudicatorStore") as adjudicator,
            patch("adaptive_factory.server._runtime_readiness"),
            patch("adaptive_factory.server.load_actors", return_value={}),
            patch("adaptive_factory.server.Authenticator"),
            patch(
                "adaptive_factory.server.create_app",
                side_effect=lambda service, _auth, **_options: service,
            ),
        ):
            service = build_app(settings)
        runtime_store.assert_called_once_with(settings.database_url)
        coordinator.assert_called_once_with(settings.semantic_coordinator_database_url)
        attestor.assert_not_called()
        validator.assert_not_called()
        adjudicator.assert_not_called()
        self.assertIs(service.semantic_store, coordinator.return_value)
        self.assertIsNone(service.semantic_validator_store)
        self.assertIsNone(service.semantic_adjudicator_store)
        self.assertIsNone(service.execution_registry)

    def test_semantic_capability_dsns_wire_three_isolated_stores(self):
        settings = FactorySettings(
            "postgresql://runtime",
            Path("/run/factory.sock"),
            Path("/run/actors.json"),
            semantic_coordinator_database_url="postgresql://semantic-coordinator",
            semantic_validator_database_url="postgresql://semantic-validator",
            semantic_adjudicator_database_url="postgresql://semantic-adjudicator",
        )
        with (
            patch("adaptive_factory.server.PostgresFactoryStore"),
            patch("adaptive_factory.server.PostgresSemanticCoordinatorStore") as coordinator,
            patch("adaptive_factory.server.PostgresSemanticValidatorStore") as validator,
            patch("adaptive_factory.server.PostgresSemanticAdjudicatorStore") as adjudicator,
            patch("adaptive_factory.server._runtime_readiness"),
            patch("adaptive_factory.server.load_actors", return_value={}),
            patch("adaptive_factory.server.Authenticator"),
            patch(
                "adaptive_factory.server.create_app",
                side_effect=lambda service, _auth, **_options: service,
            ),
        ):
            service = build_app(settings)
        coordinator.assert_called_once_with(settings.semantic_coordinator_database_url)
        validator.assert_called_once_with(settings.semantic_validator_database_url)
        adjudicator.assert_called_once_with(settings.semantic_adjudicator_database_url)
        self.assertIs(service.semantic_store, coordinator.return_value)
        self.assertIs(service.semantic_validator_store, validator.return_value)
        self.assertIs(service.semantic_adjudicator_store, adjudicator.return_value)

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
                records.append(
                    {
                        "actor_id": kind,
                        "kind": kind,
                        "scopes": [scope],
                        "repositories": ["owner/repository"],
                        "token_file": str(token),
                    }
                )
            config = root / "actors.json"
            config.write_text(json.dumps({"actors": records}), encoding="utf-8")
            config.chmod(0o600)
            actors = load_actors(config)
        self.assertEqual(
            {actor.kind for actor in actors.values()}, {"validator", "adjudicator"}
        )

    def test_build_app_requires_distinct_ready_runtime_and_attestor_capabilities(self):
        settings = FactorySettings(
            "postgresql://runtime",
            Path("/run/factory.sock"),
            Path("/run/actors.json"),
            "postgresql://attestor",
            True,
        )
        execution_registry = Mock()
        artifact_broker = Mock()
        snapshot_broker = Mock()
        execution_registry.resolve = Mock()
        artifact_broker.attest_artifact = Mock()
        snapshot_broker.snapshot = Mock()
        with (
            patch("adaptive_factory.server.PostgresFactoryStore") as runtime_store,
            patch(
                "adaptive_factory.server.PostgresArtifactAttestationStore"
            ) as attestor_store,
            patch("adaptive_factory.server.load_actors", return_value={}),
            patch("adaptive_factory.server.Authenticator"),
            patch(
                "adaptive_factory.server.create_app",
                side_effect=lambda service, _auth, **_options: service,
            ),
        ):
            runtime_store.return_value.readiness.return_value = {
                "status": "ready",
                "session_user": "factory_runtime_login",
                "database_role": "factory_runtime",
                "schema_version": 18,
                "capacity_consistent": True,
                "accounting_consistent": True,
            }
            attestor_store.return_value.readiness.return_value = {
                "session_user": "factory_attestor_login",
                "database_role": "factory_artifact_attestor",
            }
            service = build_app(
                settings,
                execution_registry=execution_registry,
                artifact_broker=artifact_broker,
                snapshot_broker=snapshot_broker,
            )

        runtime_store.assert_called_once_with(settings.database_url)
        attestor_store.assert_called_once_with(
            settings.artifact_attestor_database_url
        )
        runtime_store.return_value.readiness.assert_called_once_with()
        attestor_store.return_value.readiness.assert_called_once_with()
        self.assertIs(service.store, runtime_store.return_value)
        self.assertIs(
            service.artifact_attestation_store, attestor_store.return_value
        )
        self.assertIs(service.execution_registry, execution_registry)
        self.assertIs(service.artifact_broker, artifact_broker)
        self.assertIs(service.snapshot_broker, snapshot_broker)

    def test_build_app_fails_closed_before_loading_actors_when_capability_is_not_ready(self):
        settings = FactorySettings(
            "postgresql://runtime",
            Path("/run/factory.sock"),
            Path("/run/actors.json"),
            "postgresql://attestor",
            True,
        )
        execution_registry = Mock(resolve=Mock())
        artifact_broker = Mock(attest_artifact=Mock())
        snapshot_broker = Mock(snapshot=Mock())
        for runtime_readiness, attestor_readiness in (
            (
                {
                    "status": "not_ready",
                    "session_user": "factory_runtime_login",
                    "database_role": "factory_runtime",
                },
                {
                    "session_user": "factory_attestor_login",
                    "database_role": "factory_artifact_attestor",
                },
            ),
            (
                {
                    "status": "ready",
                    "session_user": "factory_runtime_login",
                    "database_role": "factory_runtime",
                    "schema_version": 18,
                    "capacity_consistent": True,
                    "accounting_consistent": True,
                },
                {
                    "session_user": "factory_attestor_login",
                    "database_role": "factory_runtime",
                },
            ),
            (
                {
                    "status": "ready",
                    "session_user": "factory_runtime_login",
                    "database_role": "factory_artifact_attestor",
                    "schema_version": 18,
                    "capacity_consistent": True,
                    "accounting_consistent": True,
                },
                {
                    "session_user": "factory_attestor_login",
                    "database_role": "factory_artifact_attestor",
                },
            ),
            (
                {
                    "status": "ready",
                    "session_user": "same_login",
                    "database_role": "factory_runtime",
                    "schema_version": 18,
                    "capacity_consistent": True,
                    "accounting_consistent": True,
                },
                {
                    "session_user": "same_login",
                    "database_role": "factory_artifact_attestor",
                },
            ),
        ):
            with self.subTest(
                runtime=runtime_readiness, attestor=attestor_readiness
            ):
                with (
                    patch(
                        "adaptive_factory.server.PostgresFactoryStore"
                    ) as runtime_store,
                    patch(
                        "adaptive_factory.server.PostgresArtifactAttestationStore"
                    ) as attestor_store,
                    patch("adaptive_factory.server.load_actors") as load,
                ):
                    runtime_store.return_value.readiness.return_value = (
                        runtime_readiness
                    )
                    attestor_store.return_value.readiness.return_value = (
                        attestor_readiness
                    )
                    with self.assertRaisesRegex(
                        ServerError, "database capabilities are not ready"
                    ):
                        build_app(
                            settings,
                            execution_registry=execution_registry,
                            artifact_broker=artifact_broker,
                            snapshot_broker=snapshot_broker,
                        )
                    load.assert_not_called()

    def test_build_app_has_no_fallback_for_trusted_execution_dependencies(self):
        settings = FactorySettings(
            "postgresql://runtime",
            Path("/run/factory.sock"),
            Path("/run/actors.json"),
            "postgresql://attestor",
            True,
        )
        valid = {
            "execution_registry": Mock(resolve=Mock()),
            "artifact_broker": Mock(attest_artifact=Mock()),
            "snapshot_broker": Mock(snapshot=Mock()),
        }
        for missing in tuple(valid):
            dependencies = {**valid, missing: None}
            with self.subTest(missing=missing), self.assertRaisesRegex(
                ServerError, "trusted execution dependencies are unavailable"
            ):
                build_app(settings, **dependencies)

    def test_main_accepts_explicit_composition_before_preparing_socket(self):
        from adaptive_factory import server

        settings = FactorySettings(
            "postgresql://runtime",
            Path("/run/factory.sock"),
            Path("/run/actors.json"),
            "postgresql://attestor",
            True,
        )
        registry, artifact, snapshot = self.execution_dependencies()
        landing = object()
        order = []
        listener = Mock()
        listener.close = Mock(side_effect=lambda: order.append("close"))
        application = object()
        with (
            patch.object(
                server.FactorySettings,
                "from_environment",
                return_value=settings,
            ),
            patch.object(
                server,
                "build_app",
                side_effect=lambda *_args, **_kwargs: (
                    order.append("build"),
                    application,
                )[1],
            ) as build,
            patch.object(
                server,
                "prepare_unix_socket",
                side_effect=lambda _path: (
                    order.append("socket"),
                    listener,
                )[1],
            ),
            patch.object(server.uvicorn, "Config", return_value=object()),
            patch.object(server.uvicorn, "Server") as uvicorn_server,
        ):
            self.assertEqual(
                server.main(
                    execution_registry=registry,
                    artifact_broker=artifact,
                    snapshot_broker=snapshot,
                    landing_service=landing,
                ),
                0,
            )
        self.assertEqual(order[:2], ["build", "socket"])
        build.assert_called_once_with(
            settings,
            execution_registry=registry,
            artifact_broker=artifact,
            snapshot_broker=snapshot,
            landing_service=landing,
        )
        uvicorn_server.return_value.run.assert_called_once_with(sockets=[listener])

    def test_settings_require_separate_runtime_and_attestor_urls(self):
        base = {
            "FACTORY_DATABASE_URL": "postgresql://runtime",
            "FACTORY_ARTIFACT_ATTESTOR_DATABASE_URL": "postgresql://attestor",
            "FACTORY_EXECUTION_ENABLED": "true",
            "FACTORY_ACTORS_FILE": "/run/actors.json",
            "FACTORY_SOCKET_PATH": "/run/factory.sock",
        }
        with patch.dict(os.environ, base, clear=True):
            settings = FactorySettings.from_environment()
        self.assertEqual(
            settings.artifact_attestor_database_url, "postgresql://attestor"
        )
        for override in (
            {"FACTORY_ARTIFACT_ATTESTOR_DATABASE_URL": ""},
            {"FACTORY_ARTIFACT_ATTESTOR_DATABASE_URL": "postgresql://runtime"},
        ):
            with self.subTest(override=override), patch.dict(
                os.environ, {**base, **override}, clear=True
            ), self.assertRaises(SettingsError):
                FactorySettings.from_environment()

    def test_execution_is_strictly_disabled_by_default_and_routes_are_absent(self):
        settings = FactorySettings(
            "postgresql://runtime",
            Path("/run/factory.sock"),
            Path("/run/actors.json"),
        )
        token = "legacy-" + "control-token"
        actor = Actor(
            "legacy-operator",
            "operator",
            frozenset({"factory:reconcile"}),
            frozenset({"*"}),
        )
        with (
            patch("adaptive_factory.server.PostgresFactoryStore") as runtime_store,
            patch("adaptive_factory.server.PostgresArtifactAttestationStore") as attestor,
            patch(
                "adaptive_factory.server.load_actors", return_value={token: actor}
            ),
        ):
            runtime_store.return_value.readiness.return_value = {
                "status": "ready",
                "session_user": "factory_runtime_login",
                "database_role": "factory_runtime",
                "schema_version": 18,
                "capacity_consistent": True,
                "accounting_consistent": True,
            }
            app = build_app(settings)
        runtime_store.assert_called_once_with(settings.database_url)
        runtime_store.return_value.readiness.assert_called_once_with()
        attestor.assert_not_called()
        paths = {getattr(route, "path", None) for route in app.router.routes}
        self.assertTrue({"/health/live", "/health/ready", "/v1/tasks"} <= paths)
        self.assertFalse(any(path and path.startswith("/v1/execution/") for path in paths))

    def test_enabled_app_registers_exactly_six_execution_routes(self):
        class Service:
            pass

        token = "enabled-" + "execution-token"
        actor = Actor(
            "enabled-worker",
            "worker",
            frozenset({"task:execute"}),
            frozenset({"*"}),
        )
        app = create_app(Service(), Authenticator({token: actor}), execution_enabled=True)
        paths = {
            getattr(route, "path", None)
            for route in app.router.routes
            if getattr(route, "path", "").startswith("/v1/execution/")
        }
        self.assertEqual(
            paths,
            {
                "/v1/execution/claims",
                "/v1/execution/stages",
                "/v1/execution/notes",
                "/v1/execution/artifacts",
                "/v1/execution/usage",
                "/v1/execution/terminal",
            },
        )

    def test_settings_reject_noncanonical_execution_flag(self):
        base = {
            "FACTORY_DATABASE_URL": "postgresql://runtime",
            "FACTORY_ACTORS_FILE": "/run/actors.json",
            "FACTORY_SOCKET_PATH": "/run/factory.sock",
        }
        for value in ("1", "TRUE", "yes", " false", ""):
            with self.subTest(value=value), patch.dict(
                os.environ,
                {**base, "FACTORY_EXECUTION_ENABLED": value},
                clear=True,
            ), self.assertRaisesRegex(SettingsError, "must be true or false"):
                FactorySettings.from_environment()
        with patch.dict(os.environ, base, clear=True):
            settings = FactorySettings.from_environment()
        self.assertFalse(settings.execution_enabled)
        self.assertIsNone(settings.artifact_attestor_database_url)

    def test_landing_quarantine_setting_is_optional_absolute_and_append_only(self):
        base = {
            "FACTORY_DATABASE_URL": "postgresql://runtime",
            "FACTORY_ACTORS_FILE": "/run/actors.json",
            "FACTORY_SOCKET_PATH": "/run/factory.sock",
        }
        with patch.dict(os.environ, base, clear=True):
            settings = FactorySettings.from_environment()
        self.assertIsNone(settings.landing_quarantine_path)
        self.assertEqual(
            tuple(FactorySettings.__dataclass_fields__)[-1],
            "landing_quarantine_path",
        )

        with patch.dict(
            os.environ,
            {**base, "FACTORY_LANDING_QUARANTINE_PATH": "/var/tmp/factory-landing"},
            clear=True,
        ):
            configured = FactorySettings.from_environment()
        self.assertEqual(
            configured.landing_quarantine_path,
            Path("/var/tmp/factory-landing"),
        )

        with patch.dict(
            os.environ,
            {**base, "FACTORY_LANDING_QUARANTINE_PATH": "relative/landing"},
            clear=True,
        ), self.assertRaisesRegex(SettingsError, "absolute and normalized"):
            FactorySettings.from_environment()

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

    def test_actor_config_rejects_noncanonical_actor_ids_before_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            token = root / "worker.token"
            token.write_text("worker-token-value-123\n", encoding="utf-8")
            token.chmod(0o600)
            config = root / "actors.json"
            for actor_id in (None, 7, "", "x" * 129, "control\nid", "space id"):
                config.write_text(
                    json.dumps(
                        {
                            "actors": [
                                {
                                    "actor_id": actor_id,
                                    "kind": "worker",
                                    "scopes": ["task:claim"],
                                    "repositories": ["owner/repo"],
                                    "token_file": str(token),
                                }
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                config.chmod(0o600)
                with self.subTest(actor_id=actor_id), self.assertRaises(ServerError):
                    load_actors(config)

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
