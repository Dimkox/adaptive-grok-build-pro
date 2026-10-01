import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from adaptive_factory.settings import FactorySettings, SettingsError


class V15RuntimeConfigTests(unittest.TestCase):
    def write_config(self, root: Path, *, mutate=None):
        artifact = root / "prediction.json"
        artifact.write_text("{}", encoding="utf-8")
        artifact.chmod(0o600)
        disabled = {"enabled": False, "path": None, "digest": None}
        binding = {
            "tenant_id": "owner/project",
            "repository_id": "owner/project",
            "exact_head_sha": "a" * 40,
            "fpf": disabled,
            "vibevm": disabled,
            "prediction": {
                "enabled": True,
                "path": str(artifact),
                "digest": hashlib.sha256(b"{}").hexdigest(),
            },
        }
        payload = {"schema_version": 1, "bindings": [binding]}
        if mutate is not None:
            mutate(payload)
        path = root / "v15-runtime.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        path.chmod(0o600)
        return path, artifact

    def test_absent_configuration_is_default_off(self):
        environment = {
            "FACTORY_DATABASE_URL": "postgresql://runtime",
            "FACTORY_ACTORS_FILE": "/run/actors.json",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = FactorySettings.from_environment()
        self.assertIsNone(settings.v15_runtime_config_path)

    def test_private_closed_configuration_resolves_only_exact_authority(self):
        from adaptive_factory.v15_runtime_config import load_v15_runtime_config

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, artifact = self.write_config(root)
            config = load_v15_runtime_config(path)
            binding = config.resolve("owner/project", "owner/project", "a" * 40)
            self.assertTrue(binding.prediction.enabled)
            self.assertEqual(binding.prediction.path, artifact)
            self.assertIsNone(config.resolve("other/project", "owner/project", "a" * 40))
            self.assertIsNone(config.resolve("owner/project", "owner/project", "b" * 40))

    def test_unknown_duplicate_or_unbound_artifact_configuration_rejects(self):
        from adaptive_factory.v15_runtime_config import load_v15_runtime_config

        mutations = (
            lambda data: data.update({"unexpected": True}),
            lambda data: data["bindings"].append(dict(data["bindings"][0])),
            lambda data: data["bindings"][0]["prediction"].update({"digest": "f" * 64}),
            lambda data: data["bindings"][0]["fpf"].update(
                {"enabled": True, "path": "relative.json", "digest": "f" * 64}
            ),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                path, _ = self.write_config(Path(directory), mutate=mutation)
                with self.assertRaises(SettingsError):
                    load_v15_runtime_config(path)

    def test_public_or_symlinked_configuration_rejects(self):
        from adaptive_factory.v15_runtime_config import load_v15_runtime_config

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, _ = self.write_config(root)
            path.chmod(0o644)
            with self.assertRaises(SettingsError):
                load_v15_runtime_config(path)
            path.unlink()
            target, _ = self.write_config(root)
            alias = root / "alias.json"
            alias.symlink_to(target)
            with self.assertRaises(SettingsError):
                load_v15_runtime_config(alias)

    def test_server_loads_runtime_config_before_exposing_application(self):
        from adaptive_factory.server import build_app

        with tempfile.TemporaryDirectory() as directory:
            path, _ = self.write_config(Path(directory))
            settings = FactorySettings(
                "postgresql://runtime",
                Path("/run/factory.sock"),
                Path("/run/actors.json"),
                v15_runtime_config_path=path,
            )
            application = SimpleNamespace(state=SimpleNamespace())
            with (
                patch("adaptive_factory.server.PostgresFactoryStore"),
                patch("adaptive_factory.server._runtime_readiness"),
                patch("adaptive_factory.server.load_actors", return_value={}),
                patch("adaptive_factory.server.Authenticator"),
                patch("adaptive_factory.server.create_app", return_value=application),
            ):
                result = build_app(settings)
        self.assertIs(result, application)
        self.assertIsNotNone(result.state.v15_runtime_config)
