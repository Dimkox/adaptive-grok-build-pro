"""Deterministic, network-free Factory release builder contracts."""

import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile


RUNTIME = Path(__file__).resolve().parents[1] / "runtime"


def load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, RUNTIME / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


setup = load("setup_manager")


class OfflineReleaseBuilderTests(unittest.TestCase):
    def setUp(self):
        self.builder = load("build_offline_release")
        self.temp = tempfile.TemporaryDirectory(prefix="factory-release-builder-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        package = self.repo / "factory/src/adaptive_factory"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("__version__='1.2.3'\n")
        (package / "server.py").write_text("raise SystemExit(0)\n")
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.repo, check=True)
        self.wheelhouse = self.base / "wheelhouse"
        self.wheelhouse.mkdir()
        wheel = self.wheelhouse / "demo-1.0.0-py3-none-any.whl"
        with zipfile.ZipFile(wheel, "w") as archive:
            info = zipfile.ZipInfo("demo/__init__.py", (2020, 1, 1, 0, 0, 0))
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, b"VALUE=1\n")
        lock = self.repo / "factory/uv.lock"
        lock.write_text(
            'version = 1\nrevision = 3\nrequires-python = ">=3.12,<3.13"\n\n'
            '[[package]]\nname = "adaptive-factory"\nversion = "1.2.3"\n\n'
            '[[package]]\nname = "demo"\nversion = "1.0.0"\n'
            f'wheels = [{{ url = "https://invalid.example/{wheel.name}", '
            f'hash = "sha256:{hashlib.sha256(wheel.read_bytes()).hexdigest()}", size = {wheel.stat().st_size} }}]\n'
        )
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.repo, check=True)
        self.head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.repo, text=True).strip()
        self.inventory = self.base / "inventory.json"
        self.inventory.write_text(json.dumps({
            "schema_version": "factory-runtime-wheels/v1",
            "profile": "ubuntu-24.04-x86_64-cpython312",
            "lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest(),
            "wheels": [{"name": "demo", "version": "1.0.0", "filename": wheel.name,
                        "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()}],
        }))

    def build(self, stem):
        return self.builder.build_release(
            repository=self.repo, expected_head=self.head, wheelhouse=self.wheelhouse,
            inventory=self.inventory, output=self.base / stem, product_version="1.2.3",
            enforce_host=False,
        )

    def test_same_clean_head_and_wheels_produce_identical_self_verified_release(self):
        first = self.build("first")
        second = self.build("second")
        self.assertEqual(first["archive_sha256"], second["archive_sha256"])
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        verified = setup.verify_release(
            archive=Path(first["archive"]), manifest=Path(first["manifest"]),
            archive_sha256=first["archive_sha256"], manifest_sha256=first["manifest_sha256"],
        )
        names = {name for name, _, _ in verified.files}
        self.assertIn("app/adaptive_factory/server.py", names)
        self.assertIn("site-packages/demo/__init__.py", names)

    def test_output_stem_with_dotted_version_is_preserved(self):
        result = self.build("factory-1.2.3")
        self.assertEqual(Path(result["archive"]).name, "factory-1.2.3.zip")
        self.assertEqual(Path(result["manifest"]).name, "factory-1.2.3.manifest.json")

    def test_dirty_source_missing_extra_or_tampered_wheel_has_zero_output(self):
        (self.repo / "dirty").write_text("untracked")
        with self.assertRaises(setup.InstallerError) as error:
            self.build("dirty")
        self.assertEqual(error.exception.code, "SOURCE_NOT_CLEAN")
        self.assertFalse((self.base / "dirty.zip").exists())
        (self.repo / "dirty").unlink()
        extra = self.wheelhouse / "extra.whl"
        extra.write_bytes(b"extra")
        with self.assertRaises(setup.InstallerError) as error:
            self.build("extra")
        self.assertEqual(error.exception.code, "WHEELHOUSE_MISMATCH")
        extra.unlink()
        wheel = next(self.wheelhouse.iterdir())
        wheel.write_bytes(wheel.read_bytes() + b"tamper")
        with self.assertRaises(setup.InstallerError) as error:
            self.build("tamper")
        self.assertEqual(error.exception.code, "WHEEL_DIGEST_MISMATCH")

    def test_wrong_head_inventory_drift_missing_and_symlink_wheels_fail_closed(self):
        with self.assertRaises(setup.InstallerError) as error:
            self.builder.build_release(repository=self.repo, expected_head="f" * 40,
                                       wheelhouse=self.wheelhouse, inventory=self.inventory,
                                       output=self.base / "wrong-head", product_version="1.2.3",
                                       enforce_host=False)
        self.assertEqual(error.exception.code, "SOURCE_HEAD_MISMATCH")
        value = json.loads(self.inventory.read_text())
        value["wheels"][0]["version"] = "9.9.9"
        self.inventory.write_text(json.dumps(value))
        with self.assertRaises(setup.InstallerError) as error:
            self.build("drift")
        self.assertEqual(error.exception.code, "WHEEL_INVENTORY_DRIFT")
        value["wheels"][0]["version"] = "1.0.0"
        self.inventory.write_text(json.dumps(value))
        wheel = next(self.wheelhouse.iterdir())
        parked = self.base / wheel.name
        wheel.rename(parked)
        with self.assertRaises(setup.InstallerError) as error:
            self.build("missing")
        self.assertEqual(error.exception.code, "WHEELHOUSE_MISMATCH")
        wheel.symlink_to(parked)
        with self.assertRaises(setup.InstallerError) as error:
            self.build("symlink")
        self.assertEqual(error.exception.code, "WHEELHOUSE_MISMATCH")

    def test_hostile_wheel_paths_duplicates_and_special_members_are_rejected(self):
        for name, mode in (("../escape", stat.S_IFREG | 0o644),
                           ("link", stat.S_IFLNK | 0o777)):
            wheel = self.base / (name.replace("/", "-") + ".whl")
            with zipfile.ZipFile(wheel, "w") as archive:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = mode << 16
                archive.writestr(info, b"bad")
            with self.assertRaises(setup.InstallerError):
                self.builder._wheel_files(wheel)
        duplicate = self.base / "duplicate.whl"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(duplicate, "w") as archive:
                for content in (b"one", b"two"):
                    info = zipfile.ZipInfo("same.py")
                    info.create_system = 3
                    info.external_attr = (stat.S_IFREG | 0o644) << 16
                    archive.writestr(info, content)
        with self.assertRaises(setup.InstallerError):
            self.builder._wheel_files(duplicate)

    def test_partial_publication_is_removed_and_host_gate_fails_closed(self):
        real_replace = self.builder.os.replace
        calls = 0

        def fail_second(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated publication failure")
            return real_replace(source, target)

        with patch.object(self.builder.os, "replace", side_effect=fail_second):
            with self.assertRaises(setup.InstallerError) as error:
                self.build("partial")
        self.assertEqual(error.exception.code, "OUTPUT_PUBLICATION_FAILED")
        self.assertFalse(any(self.base.glob("partial*")))
        with patch.object(self.builder, "_host_supported", return_value=False):
            with self.assertRaises(setup.InstallerError) as error:
                self.builder.build_release(repository=self.repo, expected_head=self.head,
                                           wheelhouse=self.wheelhouse, inventory=self.inventory,
                                           output=self.base / "host", product_version="1.2.3")
        self.assertEqual(error.exception.code, "UNSUPPORTED_HOST")

    def test_committed_inventory_is_exactly_derived_from_uv_lock(self):
        repository = Path(__file__).resolve().parents[2]
        inventory = repository / "factory/runtime/runtime-wheels-linux-x86_64-cpython312.json"
        self.builder.validate_committed_inventory(repository / "factory/uv.lock", inventory)


if __name__ == "__main__":
    unittest.main()
