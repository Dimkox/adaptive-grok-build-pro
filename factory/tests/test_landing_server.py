"""Direct durable composition and ownership, independent of the dedicated host."""

from __future__ import annotations

import asyncio
from dataclasses import replace
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch

from adaptive_factory import landing_server, landing_sqlite_store, server
from adaptive_factory.models import Actor
from adaptive_factory.settings import FactorySettings, SettingsError
from adaptive_factory.landing_service import LandingServiceError
from adaptive_factory.landing_sqlite_store import SQLiteLandingJobStore


class LandingServerOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.control = self.root / "control"
        for name in ("control", "state", "blobs", "scratch", "artifacts"):
            (self.root / name).mkdir(mode=0o700)
        self.settings = FactorySettings(
            database_url="", socket_path=self.root / "control.sock",
            actors_file=self.root / "actors.json", landing_state_path=self.root / "state",
            landing_quarantine_path=self.root / "blobs", landing_source_path=self.root / "source",
            landing_scratch_path=self.root / "scratch", landing_output_path=self.root / "artifacts",
        )

    def open_store(self):
        store = SQLiteLandingJobStore(self.settings.landing_state_path, repository_root=self.control)
        self.addCleanup(store.close)
        return store

    def assert_writer_active(self):
        with self.assertRaises(LandingServiceError) as raised:
            self.open_store()
        self.assertEqual(raised.exception.code, "store_writer_active")

    def compose(self, settings=None):
        owned = landing_server.compose_server_landing(
            settings or self.settings, repository_root=self.control,
            qwen_env_file=self.root / "absent-key",
        )
        self.addCleanup(owned.close)
        return owned

    def test_default_off_owns_store_without_source_or_credentials_and_closes_twice(self):
        with (
            patch.object(landing_server, "_trusted_source", side_effect=AssertionError("source read")),
            patch("adaptive_factory.landing_live_executors.qwen_api_key", side_effect=AssertionError("key read")),
            patch("adaptive_factory.landing_live_executors.api_key_from_environ", side_effect=AssertionError("key read")),
        ):
            owned = self.compose()
        self.assert_writer_active()
        self.assertFalse(self.settings.landing_source_path.exists())
        self.assertFalse((self.root / "absent-key").exists())
        owned.close()
        owned.close()
        self.open_store()

    def test_default_off_rejects_double_slash_alias_of_state_as_quarantine(self):
        state = self.settings.landing_state_path
        alias = Path("/" + str(state))
        self.assertNotEqual(state, alias)
        self.assertTrue(state.samefile(alias))
        with self.assertRaisesRegex(SettingsError, "absolute and normalized"):
            self.compose(replace(self.settings, landing_quarantine_path=alias))
        self.assertEqual([], list(state.iterdir()))

    def test_every_landing_root_rejects_double_slash_before_io_for_all_profiles(self):
        for field in ("landing_state_path", "landing_quarantine_path", "landing_source_path",
                      "landing_scratch_path", "landing_output_path"):
            alias = Path("/" + str(getattr(self.settings, field)))
            for provider in ("unavailable", "grok", "qwen", "grok-vision", "qwen-omni", "qwen-omni-intl",
                             "qwen-intl"):
                settings = replace(self.settings, **{field: alias}, landing_provider=provider,
                                   landing_live_enabled=provider != "unavailable")
                with (
                    self.subTest(field=field, provider=provider),
                    patch.object(landing_server, "_private_directory", side_effect=AssertionError("root I/O")),
                    patch.object(landing_server, "_trusted_source", side_effect=AssertionError("source I/O")),
                    patch.object(landing_server, "SQLiteLandingJobStore", side_effect=AssertionError("state I/O")),
                    patch.object(landing_server, "PrivateLandingBlobStore", side_effect=AssertionError("blob I/O")),
                    self.assertRaisesRegex(SettingsError, "absolute and normalized"),
                ):
                    self.compose(settings)

    def test_competing_writer_never_initializes_quarantine(self):
        self.open_store()
        with patch.object(landing_server, "PrivateLandingBlobStore", side_effect=AssertionError("quarantine sweep")) as blobs:
            with self.assertRaises(LandingServiceError) as raised:
                self.compose()
        self.assertEqual(raised.exception.code, "store_writer_active")
        blobs.assert_not_called()

    def test_live_source_precedes_credential_and_credential_requires_ownership(self):
        events = []

        def credential(*, env_file):
            self.assertEqual(env_file, self.root / "absent-key")
            self.assert_writer_active()
            events.append("credential")
            raise RuntimeError("stop before HTTP")

        with (
            patch.object(landing_server, "_trusted_source"),
            patch("adaptive_factory.landing_renderer.ExactGitLandingWorkspace.validate_source", side_effect=lambda: events.append("source")),
            patch("adaptive_factory.landing_live_executors.qwen_api_key", side_effect=credential),
            self.assertRaisesRegex(RuntimeError, "stop before HTTP"),
        ):
            self.compose(replace(self.settings, landing_live_enabled=True, landing_provider="qwen-intl"))
        self.assertEqual(events, ["source", "credential"])
        self.open_store()

    def test_competing_writer_prevents_live_credential_access(self):
        self.open_store()
        with (
            patch.object(landing_server, "_trusted_source"),
            patch("adaptive_factory.landing_renderer.ExactGitLandingWorkspace.validate_source"),
            patch("adaptive_factory.landing_live_executors.qwen_api_key", side_effect=AssertionError("key read")) as credential,
            self.assertRaises(LandingServiceError) as raised,
        ):
            self.compose(replace(self.settings, landing_live_enabled=True, landing_provider="qwen-intl"))
        self.assertEqual(raised.exception.code, "store_writer_active")
        credential.assert_not_called()

    def test_invalid_source_or_other_provider_never_reads_qwen_file(self):
        with patch("adaptive_factory.landing_live_executors.qwen_api_key", side_effect=AssertionError("Qwen read")) as credential:
            with (
                patch.object(landing_server, "_trusted_source"),
                patch("adaptive_factory.landing_renderer.ExactGitLandingWorkspace.validate_source", side_effect=RuntimeError("invalid source")),
                self.assertRaisesRegex(RuntimeError, "invalid source"),
            ):
                self.compose(replace(self.settings, landing_live_enabled=True, landing_provider="qwen-intl"))
            with (
                patch.object(landing_server, "_trusted_source"),
                patch("adaptive_factory.landing_renderer.ExactGitLandingWorkspace.validate_source"),
                patch("adaptive_factory.landing_live_executors.api_key_from_environ", return_value="synthetic-test-key"),
                patch("adaptive_factory.landing_live_executors.compose_landing_live_grok", side_effect=RuntimeError("grok selected")),
                self.assertRaisesRegex(RuntimeError, "grok selected"),
            ):
                self.compose(replace(self.settings, landing_live_enabled=True, landing_provider="grok-vision"))
        credential.assert_not_called()
        self.open_store()

    def test_composition_failure_or_interrupt_releases_owner(self):
        for failure in (RuntimeError("blob startup"), KeyboardInterrupt("blob startup")):
            with self.subTest(failure=type(failure).__name__):
                with patch.object(landing_server, "PrivateLandingBlobStore", side_effect=failure), self.assertRaises(type(failure)) as raised:
                    self.compose()
                self.assertIs(raised.exception, failure)
                self.open_store().close()

    def build_app(self):
        actor = Actor("operator", "operator", frozenset({"factory:reconcile"}), frozenset({"*"}))
        with (
            patch.object(server, "PostgresFactoryStore"),
            patch.object(server, "_runtime_readiness", return_value={"status": "ready"}),
            patch.object(server, "load_actors", return_value={"synthetic-operator-token": actor}),
        ):
            return server.build_app(self.settings)

    def test_existing_server_lifespan_holds_and_releases_owner_on_normal_and_error_exit(self):
        for fail in (False, True):
            with self.subTest(fail=fail):
                app = self.build_app()
                self.addCleanup(app.state.owned_landing_runtime.close)

                async def run():
                    async with app.router.lifespan_context(app):
                        self.assert_writer_active()
                        if fail:
                            raise RuntimeError("lifespan body")

                if fail:
                    with self.assertRaisesRegex(RuntimeError, "lifespan body"):
                        asyncio.run(run())
                else:
                    asyncio.run(run())
                self.open_store().close()

    def test_existing_server_application_construction_failure_releases_owner(self):
        with patch.object(server, "create_app", side_effect=RuntimeError("application construction")), self.assertRaisesRegex(RuntimeError, "application construction"):
            self.build_app()
        self.open_store()

    def test_existing_server_main_cleanup_stages_survive_listener_or_runtime_close_failure(self):
        for failed_stage in ("listener", "runtime"):
            with self.subTest(failed_stage=failed_stage):
                app = self.build_app()
                owned = app.state.owned_landing_runtime
                self.addCleanup(owned.close)
                close_runtime = owned.close
                failure = OSError(failed_stage + " close failed")
                events = []

                def close_listener():
                    events.append("listener")
                    if failed_stage == "listener":
                        raise failure

                def close_owned():
                    events.append("runtime")
                    close_runtime()
                    if failed_stage == "runtime":
                        raise failure

                listener = Mock()
                listener.close.side_effect = close_listener
                socket_path = Mock()
                socket_path.lstat.return_value.st_mode = stat.S_IFSOCK
                socket_path.unlink.side_effect = lambda: events.append("unlink")
                with (
                    patch.object(server.FactorySettings, "from_environment", return_value=replace(self.settings, socket_path=socket_path)),
                    patch.object(server, "build_app", return_value=app),
                    patch.object(server, "prepare_unix_socket", return_value=listener),
                    patch.object(server.uvicorn, "Config", return_value=object()),
                    patch.object(server.uvicorn, "Server"),
                    patch.object(owned, "close", side_effect=close_owned),
                    self.assertRaises(OSError) as raised,
                ):
                    server.main()
                self.assertIs(raised.exception, failure)
                try:
                    self.open_store().close()
                finally:
                    close_runtime()
                self.assertEqual(["listener", "runtime", "unlink"], events)

    def test_interruption_after_flock_releases_unreturned_descriptor(self):
        real_flock = landing_sqlite_store.fcntl.flock
        acquired = []
        failure = KeyboardInterrupt("writer acquisition interrupted")

        def interrupted_flock(descriptor, operation):
            real_flock(descriptor, operation)
            acquired.append(descriptor)
            raise failure

        try:
            with (
                patch.object(landing_sqlite_store.fcntl, "flock", side_effect=interrupted_flock),
                self.assertRaises(KeyboardInterrupt) as raised,
            ):
                self.open_store()
            self.assertIs(raised.exception, failure)
            self.open_store().close()
        finally:
            for descriptor in acquired:
                try:
                    os.close(descriptor)
                except OSError:
                    pass

    def test_sqlite_initialization_interrupt_and_cleanup_failure_release_writer(self):
        real_acquire = landing_sqlite_store._acquire_writer
        real_connect = sqlite3.connect
        for failure, broken_close, during_connect in (
            (KeyboardInterrupt("initialize interrupted"), False, False),
            (RuntimeError("initialize failed"), True, False),
            (KeyboardInterrupt("connect interrupted"), False, True),
        ):
            with self.subTest(failure=str(failure)):
                acquired = []

                def acquire(root):
                    descriptor = real_acquire(root)
                    acquired.append(descriptor)
                    return descriptor

                class Connection:
                    def __init__(self, *args, **kwargs):
                        if during_connect:
                            raise failure
                        self.connection = real_connect(*args, **kwargs)

                    def close(self):
                        self.connection.close()
                        if broken_close:
                            raise RuntimeError("close failed")

                try:
                    with (
                        patch.object(landing_sqlite_store, "_acquire_writer", side_effect=acquire),
                        patch.object(landing_sqlite_store.sqlite3, "connect", side_effect=Connection),
                        patch.object(SQLiteLandingJobStore, "_configure", side_effect=failure),
                        self.assertRaises((type(failure), RuntimeError)),
                    ):
                        self.open_store()
                    self.open_store().close()
                finally:
                    # Failing reference code leaks an integer descriptor; keep
                    # the failure-injection test itself bounded after RED.
                    for descriptor in acquired:
                        try:
                            os.close(descriptor)
                        except OSError:
                            pass
