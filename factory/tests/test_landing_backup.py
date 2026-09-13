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
from factory.tests.test_landing_host import HostFixture


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
        code = textwrap.dedent("""
            import importlib.abc
            import sys
            from pathlib import Path
            class Guard(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path=None, target=None):
                    blocked = ("adaptive_factory.api", "adaptive_factory.server",
                               "adaptive_factory.landing_host", "adaptive_factory.landing_server",
                               "adaptive_factory.landing_live_executors", "psycopg", "httpx",
                               "uvicorn", "fastapi")
                    if any(fullname == name or fullname.startswith(name + ".") for name in blocked):
                        raise AssertionError("offline import reached " + fullname)
            sys.meta_path.insert(0, Guard())
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
                                env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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
        saved = self.save()
        self.assertEqual("snapshot_saved", saved["status"])
        self.assertFalse(saved["provider_replay"])
        self.move_old_roots()
        restored = landing_backup.restore_snapshot(self.config, self.snapshot, saved["manifest_sha256"])
        self.assertEqual({"status": "restored_inactive", "provider_replay": False,
                          "publication_reconciliation_required": True}, restored)
        self.assertEqual(b"opaque retained artifact bytes", self.artifact.read_bytes())
        self.assertTrue(self.reopen_store().database_path.is_file())

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
