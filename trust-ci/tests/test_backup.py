from __future__ import annotations

import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from _support import now
from adaptive_trust_ci.backup import (
    BackupError,
    create_backup,
    prune_backups,
    restore_drill,
    verify_backup,
)


DATABASE_URL = 'postgresql://trust_ci:secret%20password@postgres:5432/trust_ci?sslmode=require'


class RecordingRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], dict[str, str]]] = []
        self.service_files: list[str] = []

    def __call__(self, argv: list[str], env: dict[str, str]):
        self.calls.append((list(argv), dict(env)))
        service_file = Path(env['PGSERVICEFILE'])
        self.service_files.append(service_file.read_text(encoding='utf-8'))
        if argv[0] == 'pg_dump':
            output = Path(argv[argv.index('--file') + 1])
            output.write_bytes(b'postgres custom dump')
        return SimpleNamespace(returncode=0, stdout='', stderr='')


class BackupTests(unittest.TestCase):
    def test_create_backup_writes_atomic_dump_and_canonical_manifest(self) -> None:
        runner = RecordingRunner()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = create_backup(
                DATABASE_URL,
                root,
                database_label='trust-ci-primary',
                now=now(),
                runner=runner,
            )
            manifest = json.loads(result.manifest_path.read_text(encoding='utf-8'))
            self.assertEqual(verify_backup(result.dump_path, result.manifest_path)['status'], 'verified')
            self.assertEqual(manifest['database_label'], 'trust-ci-primary')
            self.assertEqual(manifest['dump_file'], result.dump_path.name)
            self.assertEqual(manifest['format'], 'custom')
            self.assertEqual(oct(result.dump_path.stat().st_mode & 0o777), '0o600')
            self.assertEqual(oct(result.manifest_path.stat().st_mode & 0o777), '0o600')
            self.assertFalse(any('secret password' in item or 'secret%20password' in item for item in runner.calls[0][0]))
            self.assertIn('PGSERVICEFILE', runner.calls[0][1])
            self.assertEqual(runner.calls[0][1]['PGSERVICE'], 'adaptive_trust_ci')
            self.assertIn('password=secret password', runner.service_files[0])
            self.assertNotIn(DATABASE_URL, ' '.join(runner.calls[0][0]))

    def test_verify_backup_rejects_tampering(self) -> None:
        runner = RecordingRunner()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = create_backup(DATABASE_URL, root, database_label='primary', now=now(), runner=runner)
            result.dump_path.write_bytes(b'tampered')
            with self.assertRaisesRegex(BackupError, 'digest mismatch'):
                verify_backup(result.dump_path, result.manifest_path)

    def test_restore_requires_explicit_disposable_confirmation(self) -> None:
        runner = RecordingRunner()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = create_backup(DATABASE_URL, root, database_label='primary', now=now(), runner=runner)
            with self.assertRaisesRegex(BackupError, 'confirm-disposable'):
                restore_drill(
                    DATABASE_URL,
                    result.dump_path,
                    result.manifest_path,
                    confirm_disposable=False,
                    runner=runner,
                )

    def test_restore_verifies_before_pg_restore_and_runs_in_fail_closed_mode(self) -> None:
        runner = RecordingRunner()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = create_backup(DATABASE_URL, root, database_label='primary', now=now(), runner=runner)
            report = restore_drill(
                DATABASE_URL,
                result.dump_path,
                result.manifest_path,
                confirm_disposable=True,
                runner=runner,
            )
        self.assertEqual(report['status'], 'restored-and-verified')
        restore_argv = runner.calls[1][0]
        verify_argv = runner.calls[2][0]
        self.assertEqual(restore_argv[0], 'pg_restore')
        self.assertIn('--clean', restore_argv)
        self.assertIn('--if-exists', restore_argv)
        self.assertIn('--exit-on-error', restore_argv)
        self.assertEqual(verify_argv[0], 'psql')
        self.assertIn('ON_ERROR_STOP=1', verify_argv)
        self.assertNotIn(DATABASE_URL, ' '.join(restore_argv + verify_argv))

    def test_failed_pg_dump_leaves_no_partial_backup(self) -> None:
        def failed_runner(argv: list[str], env: dict[str, str]):
            del argv
            Path(env['PGSERVICEFILE']).read_text(encoding='utf-8')
            return SimpleNamespace(returncode=2, stdout='', stderr='pg_dump failed')

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(BackupError, 'pg_dump failed'):
                create_backup(DATABASE_URL, root, database_label='primary', now=now(), runner=failed_runner)
            self.assertEqual(list(root.iterdir()), [])

    def test_retention_keeps_recent_and_minimum_count_then_removes_verified_old_pairs(self) -> None:
        runner = RecordingRunner()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = create_backup(
                DATABASE_URL,
                root,
                database_label='primary',
                now=now() - timedelta(days=45),
                runner=runner,
            )
            recent = create_backup(
                DATABASE_URL,
                root,
                database_label='primary',
                now=now() - timedelta(days=5),
                runner=runner,
            )
            newest = create_backup(
                DATABASE_URL,
                root,
                database_label='primary',
                now=now(),
                runner=runner,
            )
            report = prune_backups(root, keep_last=1, max_age_days=30, now=now())
            self.assertEqual(report['removed'], [old.dump_path.name])
            self.assertTrue(recent.dump_path.exists())
            self.assertTrue(newest.dump_path.exists())
            self.assertFalse(old.dump_path.exists())
            self.assertFalse(old.manifest_path.exists())

    def test_retention_fails_closed_before_deleting_any_pair_when_old_backup_is_tampered(self) -> None:
        runner = RecordingRunner()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = create_backup(
                DATABASE_URL,
                root,
                database_label='primary',
                now=now() - timedelta(days=45),
                runner=runner,
            )
            newest = create_backup(
                DATABASE_URL,
                root,
                database_label='primary',
                now=now(),
                runner=runner,
            )
            old.dump_path.write_bytes(b'tampered')
            with self.assertRaisesRegex(BackupError, 'retention verification failed'):
                prune_backups(root, keep_last=1, max_age_days=30, now=now())
            self.assertTrue(old.dump_path.exists())
            self.assertTrue(old.manifest_path.exists())
            self.assertTrue(newest.dump_path.exists())


if __name__ == '__main__':
    unittest.main()
