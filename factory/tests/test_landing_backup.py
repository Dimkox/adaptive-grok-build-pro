"""Offline snapshot boundaries with private disposable roots and real SQLite."""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import textwrap
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from adaptive_factory import landing_backup
from adaptive_factory.landing_host_config import load_host_config
from adaptive_factory.settings import SettingsError
from factory.tests.landing_host_fixture import HostFixture

# Single auditable list for both offline guards in this suite. The web/database stack is
# matched by every importable name it can arrive under, not just the one we happen to use.
BLOCKED_IMPORTS = (
    "adaptive_factory.api", "adaptive_factory.server", "adaptive_factory.landing_host",
    "adaptive_factory.landing_server", "adaptive_factory.landing_live_executors",
    "fastapi", "httpx", "psycopg", "psycopg2", "starlette", "uvicorn",
)

OFFLINE_GUARD = textwrap.dedent("""
    import importlib.abc
    import os
    import sys
    from pathlib import Path
    BLOCKED = @BLOCKED@
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if any(fullname == name or fullname.startswith(name + ".") for name in BLOCKED):
                raise AssertionError("offline import reached " + fullname)
    sys.meta_path.insert(0, Guard())
""").replace("@BLOCKED@", repr(BLOCKED_IMPORTS))

# Boundary checks below are enforced with assert, which an inherited PYTHONOPTIMIZE
# would strip while the test still reported ok.
def child_env(pythonpath: str) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key != "PYTHONOPTIMIZE"}
    env["PYTHONPATH"] = pythonpath
    return env


class LandingBackupTests(HostFixture):
    def setUp(self):
        super().setUp()
        control = tempfile.TemporaryDirectory(prefix="landing-backup-control-")
        self.addCleanup(control.cleanup)
        self.data["control_repository"] = control.name
        self.write_config()
        self.reopen_store().close()
        self.config = load_host_config(self.config_path)
        self.snapshot = self.root / "snapshot"
        self.artifact_name = "therealaidarkfactory.online-" + "a" * 64 + ".zip"
        self.artifact = Path(self.data["output_path"]) / self.artifact_name
        self.artifact.write_bytes(b"opaque retained artifact bytes")
        self.artifact.chmod(0o600)

    def test_offline_config_and_backup_import_without_host_or_live_composition(self):
        code = OFFLINE_GUARD + textwrap.dedent("""
            from adaptive_factory import settings
            private_read = settings.read_private_file
            def bounded_read(path, maximum):
                assert path == Path(sys.argv[1]), "unexpected private file acquisition"
                return private_read(path, maximum)
            settings.read_private_file = bounded_read
            from adaptive_factory import landing_backup
            from adaptive_factory.landing_host_config import load_host_config
            config = load_host_config(Path(sys.argv[1]))
            assert config.settings.landing_live_enabled is False
            assert landing_backup.load_host_config is load_host_config
        """)
        result = subprocess.run([sys.executable, "-c", code, str(self.config_path)],
                                env=child_env(str(Path(__file__).resolve().parents[1] / "src")),
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_offline_test_support_imports_no_web_stack(self):
        code = OFFLINE_GUARD + textwrap.dedent("""
            REPO = Path(sys.argv[1])
            STDLIB = frozenset(sys.stdlib_module_names) | frozenset(sys.builtin_module_names)
            def crossed():
                return [name for name in BLOCKED
                        if any(loaded == name or loaded.startswith(name + ".") for loaded in sys.modules)]
            loaded = set(sys.modules)
            from factory.tests import landing_host_fixture
            REPO_REAL = os.path.realpath(str(REPO)) + os.sep
            def foreign():
                bad = []
                for name in sorted(set(sys.modules) - loaded):
                    if name.split(".")[0] in STDLIB:
                        continue
                    module = sys.modules[name]
                    spec = getattr(module, "__spec__", None)
                    # Only an absolute path can be a location. realpath() resolves whatever it is
                    # given, so a sentinel ("built-in", "frozen", "unknown", "") or a relative
                    # spelling would silently become a cwd-derived path and answer the containment
                    # question from the directory the suite happens to run in.
                    origin = getattr(spec, "origin", None)
                    locations = [os.path.realpath(origin)] if origin and os.path.isabs(origin) else []
                    locations += [os.path.realpath(str(entry))
                                  for entry in (getattr(module, "__path__", None) or [])
                                  if str(entry) and os.path.isabs(str(entry))]
                    if not any(location.startswith(REPO_REAL) for location in locations):
                        bad.append((name, locations))
                return bad
            assert crossed() == [], crossed()
            assert foreign() == [], foreign()
            # The whole offline scaffolding must work with no web/db package present:
            # private roots, synthetic actors, 0600 config and a real SQLite store.
            case = landing_host_fixture.HostFixture()
            case.setUp()
            try:
                assert case.data["live_enabled"] is False
                assert case.actors[case.token].repositories == {landing_host_fixture.TARGET_REPOSITORY_ID}
                # Pinned literally: asserting against the fixture's own tuple would stay
                # green if a root were dropped from it.
                for root in ("state_path", "quarantine_path", "scratch_path", "output_path",
                             "publication_state_path", "control_repository"):
                    assert Path(case.data[root]).stat().st_mode & 0o077 == 0, root
                config = case.write_config()
                assert config == case.config_path
                assert config.stat().st_mode & 0o777 == 0o600
                store = case.reopen_store()
                assert store.database_path.is_file()
                assert crossed() == [], crossed()
                assert foreign() == [], foreign()
                print("offline_test_support_ok")
            finally:
                case.tearDown()
                case.doCleanups()
        """)
        result = subprocess.run([sys.executable, "-c", code, str(Path(__file__).resolve().parents[2])],
                                env=child_env(os.pathsep.join(
                                    (str(Path(__file__).resolve().parents[2]),
                                     str(Path(__file__).resolve().parents[1] / "src")))),
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("offline_test_support_ok", result.stdout)
        self.assertNotIn("offline import reached", result.stderr)

    def save(self):
        return landing_backup.create_snapshot(self.config, self.snapshot)

    def move_old_roots(self):
        for name in ("state_path", "publication_state_path", "output_path"):
            path = Path(self.data[name])
            path.rename(path.with_name(path.name + "-old"))

    def rewrite_manifest(self, edit):
        path = self.snapshot / "manifest.json"
        data = json.loads(path.read_bytes())
        edit(data)
        raw = json.dumps(data).encode()
        path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def test_round_trip_restores_inactive_sqlite_and_artifacts_without_replay(self):
        store = self.reopen_store()
        store.reserve_activation_probe(
            probe_id="probe-snapshot",
            idempotency_digest="e" * 64,
            profile_id="qwen-intl",
            provider_id="qwen",
            model_id="qwen-plus",
            profile_digest="a" * 64,
            input_digest="b" * 64,
        )
        store.close()
        saved = self.save()
        self.assertEqual("snapshot_saved", saved["status"])
        self.assertFalse(saved["provider_replay"])
        self.move_old_roots()
        restored = landing_backup.restore_snapshot(self.config, self.snapshot, saved["manifest_sha256"])
        self.assertEqual({"status": "restored_inactive", "provider_replay": False,
                          "publication_reconciliation_required": True}, restored)
        self.assertEqual(b"opaque retained artifact bytes", self.artifact.read_bytes())
        with sqlite3.connect(Path(self.data["state_path"]) / "landing.sqlite3") as connection:
            row = connection.execute(
                "SELECT probe_id, revision, state, idempotency_digest FROM landing_activation_probes"
            ).fetchone()
        self.assertEqual(("probe-snapshot", 1, "pending", "e" * 64), row)
        restored_store = self.reopen_store()
        self.assertTrue(restored_store.database_path.is_file())
        self.assertEqual("unknown", restored_store.get_activation_probe("probe-snapshot")["state"])

    def test_snapshot_accepts_legacy_v2_database_and_restores_it(self):
        database = Path(self.data["state_path"]) / "landing.sqlite3"
        with sqlite3.connect(database) as connection:
            connection.execute("DROP TRIGGER landing_activation_probes_no_delete")
            connection.execute("DROP TRIGGER landing_activation_probes_no_update")
            connection.execute("DROP TABLE landing_activation_probes")
            connection.execute("PRAGMA user_version=2")
        saved = self.save()
        self.assertEqual("snapshot_saved", saved["status"])
        self.move_old_roots()
        landing_backup.restore_snapshot(self.config, self.snapshot, saved["manifest_sha256"])
        restored = self.reopen_store()
        self.assertEqual(3, restored._connection.execute("PRAGMA user_version").fetchone()[0])

    def test_restore_reserves_known_copy_budget_before_creating_any_root(self):
        probe = self.root / "probe-snapshot"
        landing_backup.create_snapshot(self.config, probe)
        total = sum(entry["size"] for entry in json.loads((probe / "manifest.json").read_bytes())["entries"])
        self.assertGreater(total, 1)
        with patch.object(landing_backup, "MAX_TOTAL", total + 1):
            saved = self.save()
            self.assertEqual("snapshot_saved", saved["status"])
            self.move_old_roots()
            with self.assertRaisesRegex(landing_backup.BackupError, "snapshot_budget"):
                landing_backup.restore_snapshot(self.config, self.snapshot, saved["manifest_sha256"])
        for name in ("state_path", "publication_state_path", "output_path"):
            self.assertFalse(Path(self.data[name]).exists(), name)
        # Exactly two passes fit without redefining payload bytes as I/O or
        # resetting the shared operation budget between verification and copy.
        with patch.object(landing_backup, "MAX_TOTAL", 2 * total):
            restored = landing_backup.restore_snapshot(self.config, self.snapshot, saved["manifest_sha256"])
        self.assertEqual("restored_inactive", restored["status"])
        self.assertEqual(b"opaque retained artifact bytes", self.artifact.read_bytes())

    def test_active_landing_and_publication_writers_reject_before_snapshot_and_release(self):
        from adaptive_delivery.landing_publication import PublicationStore
        from adaptive_delivery.landing_publication_contracts import PublicationError
        from adaptive_factory.landing_service import LandingServiceError

        for kind in ("landing", "publication"):
            owner = (self.reopen_store() if kind == "landing"
                     else PublicationStore(Path(self.data["publication_state_path"])))
            self.addCleanup(owner.close)
            destination = self.root / (kind + "-snapshot")
            failure = LandingServiceError if kind == "landing" else PublicationError
            reason = "store_writer_active" if kind == "landing" else "publication_writer_active"
            with self.subTest(kind=kind), self.assertRaisesRegex(failure, reason):
                landing_backup.create_snapshot(self.config, destination)
            self.assertFalse(destination.exists())
            owner.close()
            self.assertEqual("snapshot_saved", landing_backup.create_snapshot(self.config, destination)["status"])
            self.reopen_store().close()
            publication = PublicationStore(Path(self.data["publication_state_path"]))
            self.addCleanup(publication.close)
            publication.close()

    def test_snapshot_includes_committed_wal_pages_without_side_file_dependencies(self):
        database = Path(self.data["state_path"]) / "landing.sqlite3"
        connection = sqlite3.connect(database)
        self.addCleanup(connection.close)
        connection.execute("PRAGMA wal_autocheckpoint=0")
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("CREATE TABLE backup_wal_fixture(value TEXT) STRICT")
        connection.execute("INSERT INTO backup_wal_fixture VALUES ('committed in WAL')")
        connection.commit()
        wal = Path(str(database) + "-wal")
        self.assertGreater(wal.stat().st_size, 0)
        # The main database alone cannot contain the new table until a checkpoint.
        main_only = self.root / "main-only.sqlite3"
        main_only.write_bytes(database.read_bytes())
        direct = sqlite3.connect(main_only)
        self.addCleanup(direct.close)
        with self.assertRaises(sqlite3.OperationalError):
            direct.execute("SELECT value FROM backup_wal_fixture").fetchone()
        destination = self.root / "standalone.sqlite3"
        landing_backup._snapshot(database, destination,
                                 (landing_backup.APPLICATION_ID, landing_backup.SCHEMA_VERSION),
                                 landing_backup.Budget())
        restored = sqlite3.connect(destination)
        self.addCleanup(restored.close)
        self.assertEqual(("committed in WAL",), restored.execute("SELECT value FROM backup_wal_fixture").fetchone())
        self.assertEqual(("delete",), restored.execute("PRAGMA journal_mode").fetchone())
        self.assertFalse(Path(str(destination) + "-wal").exists())
        self.assertFalse(Path(str(destination) + "-shm").exists())

    def test_populated_publication_intent_round_trip_remains_observation_only(self):
        from adaptive_delivery.landing_publication import PublicationStore
        from adaptive_delivery.landing_publication_contracts import PublicationRequestV1

        request = PublicationRequestV1(
            1, "snapshot-intent", "stage", "a" * 64,
            {"tenant_id": "fixture-tenant", "repository_id": "fixture-repository", "job_id": "fixture-job"},
            "b" * 64, "b" * 64, "c" * 64, None, None,
        )
        publication = PublicationStore(Path(self.data["publication_state_path"]))
        self.addCleanup(publication.close)
        prepared = publication.prepare(request)
        publication.close()
        saved = self.save()
        manifest = json.loads((self.snapshot / "manifest.json").read_bytes())
        self.assertIn(("publication", "publication.sqlite3"),
                      {(entry["category"], entry["name"]) for entry in manifest["entries"]})
        self.move_old_roots()
        with (
            patch("adaptive_delivery.landing_filesystem.FilesystemLandingPublisher.stage", side_effect=AssertionError("publication effect")),
            patch("adaptive_delivery.landing_filesystem.FilesystemLandingPublisher.activate", side_effect=AssertionError("publication effect")),
        ):
            result = landing_backup.restore_snapshot(self.config, self.snapshot, saved["manifest_sha256"])
        self.assertEqual("restored_inactive", result["status"])
        self.assertTrue(result["publication_reconciliation_required"])
        reader = PublicationStore(Path(self.data["publication_state_path"]), readonly=True)
        self.addCleanup(reader.close)
        self.assertEqual(prepared, reader.get(request.request_digest))

    def test_canonical_and_double_slash_destination_overlap_fail_before_creation(self):
        for alias in (False, True):
            canonical = Path(self.data["state_path"]) / "nested-snapshot"
            destination = Path("/" + str(canonical)) if alias else canonical
            with self.subTest(alias=alias), self.assertRaises(landing_backup.BackupError):
                landing_backup.create_snapshot(self.config, destination)
            self.assertFalse(canonical.exists())

    def test_double_slash_snapshot_read_is_rejected(self):
        saved = self.save()
        self.move_old_roots()
        with self.assertRaisesRegex(landing_backup.BackupError, "snapshot_path"):
            landing_backup.restore_snapshot(self.config, Path("/" + str(self.snapshot)), saved["manifest_sha256"])
        self.assertFalse(Path(self.data["state_path"]).exists())

    def test_backup_never_overwrites_existing_directory_or_symlink(self):
        self.snapshot.mkdir(mode=0o700)
        marker = self.snapshot / "keep"
        marker.write_text("untouched")
        with self.assertRaises(FileExistsError):
            self.save()
        self.assertEqual("untouched", marker.read_text())
        link = self.root / "snapshot-link"
        link.symlink_to(self.snapshot, target_is_directory=True)
        with self.assertRaises(FileExistsError):
            landing_backup.create_snapshot(self.config, link)
        self.assertTrue(link.is_symlink())

    def test_restore_refuses_existing_roots_without_touching_them(self):
        saved = self.save()
        before = self.artifact.read_bytes()
        with self.assertRaisesRegex(landing_backup.BackupError, "restore_destination_exists"):
            landing_backup.restore_snapshot(self.config, self.snapshot, saved["manifest_sha256"])
        self.assertEqual(before, self.artifact.read_bytes())

    def test_restore_rejects_snapshot_symlink_before_destination_creation(self):
        saved = self.save()
        self.move_old_roots()
        link = self.root / "snapshot-link"
        link.symlink_to(self.snapshot, target_is_directory=True)
        with self.assertRaises(SettingsError):
            landing_backup.restore_snapshot(self.config, link, saved["manifest_sha256"])
        self.assertFalse(Path(self.data["state_path"]).exists())

    def test_manifest_tamper_is_detected_before_restore(self):
        saved = self.save()
        self.move_old_roots()
        with (self.snapshot / "manifest.json").open("ab") as stream:
            stream.write(b" ")
        with self.assertRaisesRegex(landing_backup.BackupError, "restore_manifest_digest"):
            landing_backup.restore_snapshot(self.config, self.snapshot, saved["manifest_sha256"])
        self.assertFalse(Path(self.data["state_path"]).exists())

    def test_content_tamper_is_detected_before_restore(self):
        saved = self.save()
        self.move_old_roots()
        (self.snapshot / "artifacts" / self.artifact_name).write_bytes(b"modified")
        with self.assertRaisesRegex(landing_backup.BackupError, "restore_content_digest"):
            landing_backup.restore_snapshot(self.config, self.snapshot, saved["manifest_sha256"])
        self.assertFalse(Path(self.data["state_path"]).exists())

    def test_duplicate_manifest_entry_is_rejected_even_with_matching_manifest_digest(self):
        self.save()
        self.move_old_roots()
        digest = self.rewrite_manifest(lambda manifest: manifest["entries"].append(manifest["entries"][0]))
        with self.assertRaisesRegex(landing_backup.BackupError, "restore_inventory"):
            landing_backup.restore_snapshot(self.config, self.snapshot, digest)
        self.assertFalse(Path(self.data["state_path"]).exists())

    def test_symlink_and_hardlink_artifacts_are_rejected(self):
        self.artifact.rename(self.root / "original-artifact")
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind):
                if kind == "symlink":
                    self.artifact.symlink_to(self.root / "original-artifact")
                else:
                    os.link(self.root / "original-artifact", self.artifact)
                with self.assertRaisesRegex(landing_backup.BackupError, "snapshot_private_file"):
                    landing_backup.create_snapshot(self.config, self.root / ("snapshot-" + kind))
                self.artifact.unlink()


if __name__ == "__main__":
    unittest.main()
