from __future__ import annotations

import asyncio
from contextlib import ExitStack
import itertools
import json
import os
from pathlib import Path
import socket
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from adaptive_factory import landing_host
from adaptive_factory.landing_contracts import LandingContractError
from adaptive_factory.landing_renderer import (
    TARGET_BASE_SHA,
    TARGET_BASE_TREE,
    TARGET_REPOSITORY_ID,
)
from adaptive_factory.landing_service import LandingServiceError
from adaptive_factory.server import ServerError, prepare_unix_socket
from adaptive_factory.settings import SettingsError
from factory.tests.landing_host_fixture import HostFixture as LandingHostFixture
from factory.tests.landing_host_fixture import PATH_FIELDS, ROOT_FIELDS


# The offline scaffolding (setUp/write_config/reopen_store and the root field
# tuples) lives in factory/tests/landing_host_fixture.py so the dependency-free
# boundary suites can reuse it. This module keeps only the web-stack half.
class HostFixture(LandingHostFixture):
    def build_app(self):
        config = landing_host.load_host_config(self.config_path)
        with patch.object(landing_host, "load_actors", return_value=self.actors):
            app = landing_host.build_landing_app(config)
        self.addCleanup(app.state.owned_landing_runtime.close)
        return app


class LandingHostConfigTests(HostFixture):
    def test_profiles_require_explicit_live_enablement(self):
        for profile, enabled in itertools.product(("qwen-omni", "grok-vision", "qwen-intl"), (False, True)):
            with self.subTest(profile=profile, enabled=enabled):
                self.write_config({**self.data, "selected_profile": profile, "live_enabled": enabled})
                config = landing_host.load_host_config(self.config_path)
                self.assertEqual(profile if enabled else "unavailable", config.settings.landing_provider)
                self.assertEqual(enabled, config.settings.landing_live_enabled)
                self.assertEqual("", config.settings.database_url)
                self.assertFalse(config.settings.execution_enabled)
                self.assertEqual(Path(self.data["publication_state_path"]), config.publication_state)
                self.assertEqual(Path(self.data["control_repository"]), config.control_repository)

    def test_missing_or_unknown_configuration_keys_are_rejected(self):
        variants = [{key: value for key, value in self.data.items() if key != missing} for missing in self.data]
        variants.append({**self.data, "database_url": "unused"})
        for data in variants:
            with self.subTest(keys=sorted(data)):
                self.write_config(data)
                with self.assertRaises(SettingsError):
                    landing_host.load_host_config(self.config_path)

    def test_schema_enablement_and_profile_types_are_closed(self):
        invalid = {
            "schema_version": (True, False, 0, 2, "1", 1.0, None),
            "live_enabled": (0, 1, "false", "true", None, []),
            "selected_profile": ("qwen", "grok", "unavailable", "", True, None, []),
        }
        for name, values in invalid.items():
            for value in values:
                with self.subTest(field=name, value=value):
                    self.write_config({**self.data, name: value})
                    with self.assertRaises(SettingsError):
                        landing_host.load_host_config(self.config_path)

    def test_paths_must_be_absolute_without_parent_traversal(self):
        for name, value in itertools.product(PATH_FIELDS, (None, 3, "", "relative", "/tmp/../other")):
            with self.subTest(field=name, value=value):
                self.write_config({**self.data, name: value})
                with self.assertRaises(SettingsError):
                    landing_host.load_host_config(self.config_path)

    def test_double_leading_slash_cannot_alias_any_configured_path(self):
        for name in PATH_FIELDS:
            with self.subTest(field=name):
                self.write_config({**self.data, name: "/" + self.data[name]})
                with self.assertRaises(SettingsError):
                    landing_host.load_host_config(self.config_path)

    def test_double_leading_slash_cannot_hide_overlapping_data_roots(self):
        self.write_config({**self.data, "publication_state_path": "/" + self.data["state_path"]})
        with self.assertRaises(SettingsError):
            landing_host.load_host_config(self.config_path)

    def test_double_leading_slash_config_path_is_rejected(self):
        with self.assertRaises(SettingsError):
            landing_host.load_host_config(Path("/" + str(self.config_path)))

    def test_every_root_pair_rejects_equality_and_both_ancestor_directions(self):
        for first, second in itertools.combinations(ROOT_FIELDS, 2):
            for parent, child in ((first, second), (second, first)):
                for suffix in ("", "/nested"):
                    with self.subTest(parent=parent, child=child, suffix=suffix):
                        self.write_config({**self.data, child: self.data[parent] + suffix})
                        with self.assertRaises(SettingsError):
                            landing_host.load_host_config(self.config_path)

    def test_actors_and_socket_cannot_be_in_any_durable_root(self):
        for field, root, suffix in itertools.product(("actors_file", "socket_path"), ROOT_FIELDS, ("", "/nested")):
            with self.subTest(field=field, root=root, suffix=suffix):
                self.write_config({**self.data, field: self.data[root] + suffix})
                with self.assertRaises(SettingsError):
                    landing_host.load_host_config(self.config_path)

    def test_config_file_cannot_be_in_any_durable_root(self):
        for root in ROOT_FIELDS:
            with self.subTest(root=root):
                directory = Path(self.data[root])
                directory.mkdir(mode=0o700, exist_ok=True)
                nested_config = self.write_config(path=directory / "host.json")
                with self.assertRaises(SettingsError):
                    landing_host.load_host_config(nested_config)

    def test_json_rejects_duplicates_nonfinite_malformed_and_non_objects(self):
        for raw in (b"[]", b"null", b"{", b"\xff", b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.subTest(raw=raw):
                self.write_config(raw=raw)
                with self.assertRaises(LandingContractError):
                    landing_host.load_host_config(self.config_path)

    def test_config_size_limit_is_inclusive(self):
        raw = json.dumps(self.data).encode()
        self.write_config(raw=raw + b" " * (16_384 - len(raw)))
        self.assertFalse(landing_host.load_host_config(self.config_path).settings.landing_live_enabled)
        self.write_config(raw=raw + b" " * (16_385 - len(raw)))
        with self.assertRaises(SettingsError):
            landing_host.load_host_config(self.config_path)

    def test_private_config_rejects_public_mode_directory_and_missing_file(self):
        self.config_path.chmod(0o644)
        for path in (self.config_path, self.root, self.root / "missing"):
            with self.subTest(path=path), self.assertRaises(SettingsError):
                landing_host.load_host_config(path)

    def test_private_config_rejects_symlink_file_and_symlink_parent(self):
        link = self.root / "config-link"
        link.symlink_to(self.config_path)
        parent_link = self.root / "parent-link"
        parent_link.symlink_to(self.root, target_is_directory=True)
        for path in (link, parent_link / self.config_path.name):
            with self.subTest(path=path), self.assertRaises(SettingsError):
                landing_host.load_host_config(path)

    def test_config_path_must_be_absolute_without_parent_traversal(self):
        for path in (Path("host.json"), self.root / ".." / self.root.name / "host.json"):
            with self.subTest(path=path), self.assertRaises(SettingsError):
                landing_host.load_host_config(path)


class LandingHostCompositionTests(HostFixture):
    def test_offline_host_has_only_landing_routes_and_persists_unavailable_jobs(self):
        with ExitStack() as stack:
            for seam in (
                "adaptive_factory.server.PostgresFactoryStore",
                "adaptive_factory.server.PostgresArtifactAttestationStore",
                "adaptive_factory.server.PostgresSemanticCoordinatorStore",
                "adaptive_factory.server.PostgresSemanticValidatorStore",
                "adaptive_factory.server.PostgresSemanticAdjudicatorStore",
                "adaptive_factory.landing_live_executors.api_key_from_environ",
                "adaptive_factory.landing_server._trusted_source",
            ):
                stack.enter_context(patch(seam, side_effect=AssertionError("offline host crossed " + seam)))
            app = self.build_app()
            with TestClient(app) as client:
                self.assertEqual({"status": "live"}, client.get("/health/live").json())
                self.assertEqual({"status": "ready", "component": "landing-local", "production_verified": False},
                                 client.get("/health/ready").json())
                for path in ("/v1/tasks", "/v1/workers", "/metrics"):
                    self.assertEqual(404, client.get(path).status_code)
                self.assertEqual(404, client.post("/v1/tasks", json={}).status_code)
                self.assertEqual(401, client.post("/v1/landing-inputs", content=b"request").status_code)
                headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Idempotency-Key": "host-job",
                    "X-Correlation-ID": "host-submit",
                    "X-Repository-ID": TARGET_REPOSITORY_ID,
                    "X-Exact-Base-SHA": TARGET_BASE_SHA,
                    "X-Exact-Base-Tree": TARGET_BASE_TREE,
                    "Content-Type": "text/plain",
                }
                submitted = client.post("/v1/landing-inputs", headers=headers, content=b"bounded landing request")
                self.assertEqual(202, submitted.status_code, submitted.text)
                self.assertEqual("provider_unavailable", submitted.json()["state"])
                result = client.get("/v1/landing-jobs/host-job/result", headers=headers)
                self.assertEqual(200, result.status_code, result.text)
                self.assertIsNone(result.json()["live_url"])
                self.assertEqual([], list(Path(self.data["quarantine_path"]).glob("*.blob")))
                with self.assertRaises(LandingServiceError) as error:
                    self.reopen_store()
                self.assertEqual("store_writer_active", error.exception.code)
        store = self.reopen_store()
        self.assertEqual("provider_unavailable", store.get("tenant-host", TARGET_REPOSITORY_ID, "host-job").state)
        self.assertFalse(Path(self.data["source_path"]).exists())

    def test_offline_host_does_not_read_explicit_qwen_file(self):
        config = landing_host.load_host_config(self.config_path)
        with patch.object(landing_host, "load_actors", return_value=self.actors), patch(
            "adaptive_factory.landing_live_executors.qwen_api_key", side_effect=AssertionError("offline credential read")
        ):
            app = landing_host.build_landing_app(config, qwen_env_file=self.root / "missing")
        app.state.owned_landing_runtime.close()
        self.assertTrue(self.reopen_store().database_path.is_file())

    def test_qwen_credential_file_must_be_outside_all_host_roots(self):
        self.write_config({**self.data, "selected_profile": "qwen-intl", "live_enabled": True})
        config = landing_host.load_host_config(self.config_path)
        for root in ROOT_FIELDS:
            with self.subTest(root=root), self.assertRaises(SettingsError):
                landing_host.build_landing_app(config, qwen_env_file=Path(self.data[root]) / "key")

    def test_live_qwen_reads_file_only_after_source_validation_and_writer_lock(self):
        self.write_config({**self.data, "selected_profile": "qwen-intl", "live_enabled": True})
        config = landing_host.load_host_config(self.config_path)
        from adaptive_factory.landing_server import compose_server_landing
        path = self.root / "synthetic-credentials"
        events = []
        def load(*, env_file):
            self.assertEqual(path, env_file)
            with self.assertRaises(LandingServiceError) as error:
                self.reopen_store()
            self.assertEqual("store_writer_active", error.exception.code)
            events.append("credential")
            raise RuntimeError("stop before HTTP")
        with patch("adaptive_factory.landing_server._trusted_source"), patch(
            "adaptive_factory.landing_renderer.ExactGitLandingWorkspace.validate_source", side_effect=lambda: events.append("source")
        ), patch("adaptive_factory.landing_live_executors.qwen_api_key", side_effect=load):
            with self.assertRaisesRegex(RuntimeError, "stop before HTTP"):
                compose_server_landing(config.settings, repository_root=config.control_repository, qwen_env_file=path)
        self.assertEqual(["source", "credential"], events)
        self.assertTrue(self.reopen_store().database_path.is_file())

    def test_grok_does_not_read_qwen_file_and_qwen_validation_failure_precedes_read(self):
        from adaptive_factory.landing_server import compose_server_landing
        for profile in ("grok-vision", "qwen-intl"):
            self.write_config({**self.data, "selected_profile": profile, "live_enabled": True})
            config = landing_host.load_host_config(self.config_path)
            with self.subTest(profile=profile), patch(
                "adaptive_factory.landing_live_executors.qwen_api_key", side_effect=AssertionError("unexpected Qwen file read")
            ), patch("adaptive_factory.landing_server._trusted_source"), patch(
                "adaptive_factory.landing_renderer.ExactGitLandingWorkspace.validate_source",
                side_effect=RuntimeError("source invalid") if profile == "qwen-intl" else None
            ), patch("adaptive_factory.landing_live_executors.api_key_from_environ", return_value=self.token), patch(
                "adaptive_factory.landing_live_executors.compose_landing_live_grok", side_effect=RuntimeError("Grok selected")
            ):
                with self.assertRaisesRegex(RuntimeError, "source invalid" if profile == "qwen-intl" else "Grok selected"):
                    compose_server_landing(config.settings, repository_root=config.control_repository,
                                           qwen_env_file=self.root / "missing")
            self.reopen_store().close()

    def test_existing_writer_prevents_qwen_credential_read(self):
        from adaptive_factory.landing_server import compose_server_landing
        self.write_config({**self.data, "selected_profile": "qwen-intl", "live_enabled": True})
        config = landing_host.load_host_config(self.config_path)
        writer = self.reopen_store()
        with patch("adaptive_factory.landing_server._trusted_source"), patch(
            "adaptive_factory.landing_renderer.ExactGitLandingWorkspace.validate_source"
        ), patch("adaptive_factory.landing_live_executors.qwen_api_key", side_effect=AssertionError("read before lock")):
            with self.assertRaises(LandingServiceError) as error:
                compose_server_landing(config.settings, repository_root=config.control_repository,
                                       qwen_env_file=self.root / "missing")
        self.assertEqual("store_writer_active", error.exception.code)
        writer.close()

    def test_repeated_runtime_close_is_safe_and_releases_writer(self):
        runtime = self.build_app().state.owned_landing_runtime
        runtime.close()
        runtime.close()
        self.assertTrue(self.reopen_store().database_path.is_file())

    def test_exceptional_asgi_lifespan_releases_writer(self):
        app = self.build_app()

        async def interrupted_lifespan():
            async with app.router.lifespan_context(app):
                raise RuntimeError("ASGI interrupted")

        with self.assertRaisesRegex(RuntimeError, "ASGI interrupted"):
            asyncio.run(interrupted_lifespan())
        self.assertTrue(self.reopen_store().database_path.is_file())

    def test_actor_loading_authenticator_and_app_creation_failures_release_writer(self):
        config = landing_host.load_host_config(self.config_path)
        for failure in ("actors", "authenticator", "app"):
            with self.subTest(failure=failure), ExitStack() as stack:
                if failure == "actors":
                    stack.enter_context(patch.object(landing_host, "load_actors", side_effect=ServerError("actor load")))
                    expected = ServerError
                else:
                    stack.enter_context(patch.object(landing_host, "load_actors", return_value={} if failure == "authenticator" else self.actors))
                    expected = ValueError if failure == "authenticator" else KeyboardInterrupt
                    if failure == "app":
                        stack.enter_context(patch.object(landing_host, "create_app", side_effect=KeyboardInterrupt("app build")))
                with self.assertRaises(expected):
                    landing_host.build_landing_app(config)
                self.reopen_store().close()

    def test_in_memory_or_missing_composition_cannot_start_dedicated_host(self):
        config = landing_host.load_host_config(self.config_path)
        for runtime in (None, SimpleNamespace(store=None)):
            with self.subTest(runtime=runtime), patch.object(landing_host, "compose_server_landing", return_value=runtime):
                with self.assertRaises(SettingsError):
                    landing_host.build_landing_app(config)

    def test_publication_state_must_be_private_before_store_startup(self):
        Path(self.data["publication_state_path"]).chmod(0o755)
        with self.assertRaises(SettingsError):
            self.build_app()
        self.assertFalse((Path(self.data["state_path"]) / "landing.sqlite3").exists())


class LandingHostMainTests(HostFixture):
    def run_main(self, app, *, run=None, prepare=None, server_error=None):
        with ExitStack() as stack:
            stack.enter_context(patch("sys.argv", ["adaptive-landing-server", "--config", str(self.config_path)]))
            stack.enter_context(patch.object(landing_host, "build_landing_app", return_value=app))
            server = stack.enter_context(patch.object(landing_host.uvicorn, "Server"))
            if server_error is not None:
                server.side_effect = server_error
            else:
                server.return_value.run.side_effect = run
            if prepare is not None:
                stack.enter_context(patch.object(landing_host, "prepare_unix_socket", side_effect=prepare))
            result = landing_host.main()
            self.server_config = server.call_args.args[0]
            return result

    def assert_writer_released(self):
        self.assertTrue(self.reopen_store().database_path.exists())

    def test_success_uses_owned_listener_and_releases_all_resources(self):
        app = self.build_app()
        listeners = []

        def run(*, sockets):
            self.assertEqual(1, len(sockets))
            listener = sockets[0]
            listeners.append(listener)
            self.assertGreaterEqual(listener.fileno(), 0)
            self.assertEqual(self.data["socket_path"], listener.getsockname())
            self.assertEqual(0o660, stat.S_IMODE(Path(self.data["socket_path"]).stat().st_mode))

        self.assertEqual(0, self.run_main(app, run=run))
        self.assertEqual(-1, listeners[0].fileno())
        self.assertFalse(Path(self.data["socket_path"]).exists())
        self.assertFalse(self.server_config.access_log)
        self.assertFalse(self.server_config.server_header)
        self.assertIsNone(self.server_config.log_config)
        self.assertEqual(330, self.server_config.timeout_graceful_shutdown)
        self.assert_writer_released()

    def test_socket_prepare_failure_releases_runtime_and_preserves_regular_entry(self):
        path = Path(self.data["socket_path"])
        path.write_text("keep me")
        with self.assertRaises(ServerError):
            self.run_main(self.build_app())
        self.assertEqual("keep me", path.read_text())
        self.assert_writer_released()

    def test_uvicorn_config_server_construction_and_run_failures_release_resources(self):
        for stage in ("config", "server", "run"):
            with self.subTest(stage=stage):
                app = self.build_app()
                with ExitStack() as stack:
                    if stage == "config":
                        stack.enter_context(patch.object(landing_host.uvicorn, "Config", side_effect=RuntimeError("config failed")))
                    with self.assertRaisesRegex(RuntimeError, stage + " failed"):
                        self.run_main(app, server_error=RuntimeError("server failed") if stage == "server" else None,
                                      run=RuntimeError("run failed") if stage == "run" else None)
                self.assertFalse(Path(self.data["socket_path"]).exists())
                self.reopen_store().close()

    def test_listener_close_failure_still_releases_runtime_and_unlinks_socket(self):
        app = self.build_app()

        def prepare(path):
            listener = prepare_unix_socket(path)
            self.addCleanup(listener.close)

            class FailingListener:
                def close(self):
                    listener.close()
                    raise OSError("listener close failed")

            return FailingListener()

        with self.assertRaisesRegex(OSError, "listener close failed"):
            self.run_main(app, prepare=prepare)
        self.assertFalse(Path(self.data["socket_path"]).exists())
        self.assert_writer_released()

    def test_runtime_close_failure_still_unlinks_socket(self):
        app = self.build_app()
        runtime = app.state.owned_landing_runtime
        real_close = runtime.close

        def failing_close():
            real_close()
            raise RuntimeError("runtime close failed")

        with patch.object(runtime, "close", side_effect=failing_close):
            with self.assertRaisesRegex(RuntimeError, "runtime close failed"):
                self.run_main(app)
        self.assertFalse(Path(self.data["socket_path"]).exists())
        self.assert_writer_released()

    def test_run_failure_remains_in_cleanup_failure_exception_chain(self):
        app = self.build_app()
        real_close = app.state.owned_landing_runtime.close

        def failing_close():
            real_close()
            raise OSError("runtime cleanup failed")

        with patch.object(app.state.owned_landing_runtime, "close", side_effect=failing_close):
            with self.assertRaisesRegex(OSError, "runtime cleanup failed") as error:
                self.run_main(app, run=RuntimeError("run failed"))
        self.assertIsInstance(error.exception.__context__, RuntimeError)
        self.assertEqual("run failed", str(error.exception.__context__))
        self.assertFalse(Path(self.data["socket_path"]).exists())
        self.assert_writer_released()

    def test_shutdown_preserves_replacement_regular_file_symlink_and_socket(self):
        path = Path(self.data["socket_path"])
        for kind in ("file", "symlink", "socket"):
            with self.subTest(kind=kind):
                replacement = []

                def run(*, sockets):
                    path.unlink()
                    if kind == "file":
                        path.write_text("replacement")
                    elif kind == "symlink":
                        path.symlink_to(self.config_path)
                    else:
                        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        self.addCleanup(listener.close)
                        listener.bind(str(path))
                        replacement.append(listener)
                    replacement.append(path.lstat())

                self.run_main(self.build_app(), run=run)
                self.assertEqual(replacement[-1].st_ino, path.lstat().st_ino)
                if kind == "file":
                    self.assertEqual("replacement", path.read_text())
                elif kind == "symlink":
                    self.assertTrue(path.is_symlink())
                else:
                    self.assertTrue(stat.S_ISSOCK(path.lstat().st_mode))
                    replacement[0].close()
                path.unlink()
                self.reopen_store().close()

    def test_shutdown_preserves_socket_when_effective_owner_changes(self):
        path = Path(self.data["socket_path"])
        real_uid = os.geteuid()
        with ExitStack() as stack:
            def run(*, sockets):
                stack.enter_context(patch.object(landing_host.os, "geteuid", return_value=real_uid + 1))

            self.run_main(self.build_app(), run=run)
        self.assertTrue(stat.S_ISSOCK(path.lstat().st_mode))
        self.assert_writer_released()

    def test_socket_removed_by_server_is_harmless_at_shutdown(self):
        path = Path(self.data["socket_path"])

        def run(*, sockets):
            path.unlink()

        self.assertEqual(0, self.run_main(self.build_app(), run=run))
        self.assertFalse(path.exists())
        self.assert_writer_released()

    def test_startup_identity_failure_does_not_delete_unidentified_socket(self):
        path = Path(self.data["socket_path"])
        original_lstat = Path.lstat
        calls = 0

        def fail_identity(candidate, *args, **kwargs):
            nonlocal calls
            if candidate == path:
                calls += 1
                # prepare_unix_socket first checks for an existing path.
                if calls == 2:
                    raise OSError("identity unavailable")
            return original_lstat(candidate, *args, **kwargs)

        app = self.build_app()
        with patch.object(Path, "lstat", fail_identity):
            with self.assertRaisesRegex(OSError, "identity unavailable"):
                self.run_main(app)
        self.assertTrue(stat.S_ISSOCK(path.lstat().st_mode))
        self.assert_writer_released()


if __name__ == "__main__":
    unittest.main()
