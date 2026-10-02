from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from adaptive_factory.result_dispatch_cli import (
    ResultDispatchCliError,
    compose_result_dispatcher,
    main,
)
from adaptive_factory.settings import FactorySettings, SettingsError


class ResultDispatchServerTests(unittest.TestCase):
    def settings(self, root: Path) -> FactorySettings:
        return FactorySettings(
            database_url="postgresql://runtime",
            socket_path=root / "control.sock",
            actors_file=root / "actors.json",
        )

    def test_dispatcher_is_default_off_and_requires_complete_private_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = self.settings(root)
            with self.assertRaisesRegex(ResultDispatchCliError, "disabled"):
                compose_result_dispatcher(settings, object())
            with self.assertRaisesRegex(SettingsError, "requires database, socket and token"):
                replace(settings, result_dispatch_enabled=True).validate_result_dispatch()

    def test_enabled_dispatcher_reads_private_token_and_builds_bounded_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            token = root / "token"
            token.write_text("private-dispatch-token")
            token.chmod(0o600)
            settings = replace(
                self.settings(root),
                result_dispatch_enabled=True,
                result_dispatch_database_url="postgresql://dispatcher",
                result_dispatch_socket_path=root / "model.sock",
                result_dispatch_token_file=token,
                result_dispatcher_id="dispatcher-a",
                result_dispatch_batch_size=3,
                result_dispatch_lease_seconds=20,
                result_dispatch_poll_seconds=0.2,
                result_dispatch_timeout_seconds=0.5,
            )
            with patch(
                "adaptive_factory.result_dispatch_cli.UdsResultHandoffClient", return_value=object()
            ):
                dispatcher = compose_result_dispatcher(settings, object())
            self.assertEqual(
                (
                    dispatcher.dispatcher_id, dispatcher.batch_size,
                    dispatcher.lease_seconds, dispatcher.poll_seconds,
                ),
                ("dispatcher-a", 3, 20, 0.2),
            )

    def test_enabled_dispatcher_rejects_non_private_token(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            token = root / "token"
            token.write_text("private-dispatch-token")
            token.chmod(0o644)
            settings = replace(
                self.settings(root), result_dispatch_enabled=True,
                result_dispatch_database_url="postgresql://dispatcher",
                result_dispatch_socket_path=root / "model.sock",
                result_dispatch_token_file=token,
            )
            with self.assertRaisesRegex(ResultDispatchCliError, "configuration is invalid"):
                compose_result_dispatcher(settings, object())

    def test_lease_must_cover_http_timeout_and_processing_margin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = replace(
                self.settings(root),
                result_dispatch_lease_seconds=8,
                result_dispatch_timeout_seconds=5,
                result_dispatch_processing_margin_seconds=3,
            )
            with self.assertRaisesRegex(SettingsError, "lease must exceed"):
                settings.validate_result_dispatch()

    def test_environment_parser_is_strict_and_default_off(self):
        base = {
            "FACTORY_DATABASE_URL": "postgresql://runtime",
            "FACTORY_ACTORS_FILE": "/run/factory/actors.json",
        }
        with patch.dict(os.environ, base, clear=True):
            settings = FactorySettings.from_environment()
        self.assertFalse(settings.result_dispatch_enabled)
        self.assertIsNone(settings.result_dispatch_socket_path)

        enabled = {
            **base,
            "FACTORY_RESULT_DISPATCH_ENABLED": "true",
            "FACTORY_RESULT_DISPATCH_DATABASE_URL": "postgresql://dispatcher",
            "FACTORY_RESULT_DISPATCH_SOCKET_PATH": "/run/model/control.sock",
            "FACTORY_RESULT_DISPATCH_TOKEN_FILE": "/run/secrets/model-token",
            "FACTORY_RESULT_DISPATCH_BATCH_SIZE": "4",
        }
        with patch.dict(os.environ, enabled, clear=True):
            settings = FactorySettings.from_environment()
        self.assertTrue(settings.result_dispatch_enabled)
        self.assertEqual(settings.result_dispatch_batch_size, 4)

        for key, value in (
            ("FACTORY_RESULT_DISPATCH_ENABLED", "yes"),
            ("FACTORY_RESULT_DISPATCH_BATCH_SIZE", "0"),
            ("FACTORY_RESULT_DISPATCH_SOCKET_PATH", "relative.sock"),
        ):
            malformed = {**enabled, key: value}
            with self.subTest(key=key), patch.dict(os.environ, malformed, clear=True), self.assertRaises(SettingsError):
                FactorySettings.from_environment()

    def test_once_process_has_a_bounded_lifecycle(self):
        dispatcher = unittest.mock.Mock()
        with (
            patch("adaptive_factory.result_dispatch_cli.FactorySettings.from_environment"),
            patch("adaptive_factory.result_dispatch_cli.PostgresResultDispatcherStore"),
            patch("adaptive_factory.result_dispatch_cli.compose_result_dispatcher", return_value=dispatcher),
        ):
            self.assertEqual(main(["--once"]), 0)
        dispatcher.run_once.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
