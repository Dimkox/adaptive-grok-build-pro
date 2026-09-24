from __future__ import annotations

import contextlib
import io
import json
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.grok-stack'))

from adaptive_grok import util


class FingerprintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix='fingerprint-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.com')
        self.write('source.py', 'initial')
        self.commit()

    def git(self, *args: str) -> str:
        return subprocess.check_output(['git', *args], cwd=self.root, text=True).strip()

    def write(self, rel: str, content: str = 'one') -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def commit(self) -> None:
        self.git('add', '-A')
        self.git('commit', '-qm', 'fixture')

    def assert_bound(self, rel: str, before: str) -> None:
        self.assertIn(rel, util.changed_files(self.root))
        self.assertNotEqual(before, util.tree_fingerprint(self.root))

    def test_untracked_scratch_create_edit_remove_does_not_change_binding(self) -> None:
        before = util.tree_fingerprint(self.root)
        for rel in ('.qwen/tmp/probe.txt', '.qwen/tmp/nested/space and\nnewline.txt'):
            with self.subTest(rel=rel):
                path = self.write(rel)
                self.assertEqual([], util.changed_files(self.root))
                self.assertEqual(before, util.tree_fingerprint(self.root))
                path.write_text('two', encoding='utf-8')
                self.assertEqual(before, util.tree_fingerprint(self.root))
                path.unlink()
                self.assertEqual(before, util.tree_fingerprint(self.root))

    def test_staging_scratch_immediately_binds_it(self) -> None:
        before = util.tree_fingerprint(self.root)
        rel = '.qwen/tmp/staged.txt'
        self.write(rel)
        self.git('add', rel)
        self.assert_bound(rel, before)

    @unittest.skipUnless(os.name == 'posix', 'literal backslashes are POSIX filename characters')
    def test_literal_backslashes_do_not_become_scratch_separators(self) -> None:
        for rel in (r'.qwen\tmp\payload.py', r'.qwen/tmp\payload.py', r'.qwen\tmp/payload.py'):
            with self.subTest(rel=rel):
                before = util.tree_fingerprint(self.root)
                path = self.write(rel)
                self.assert_bound(rel, before)
                created = util.tree_fingerprint(self.root)
                path.write_text('two', encoding='utf-8')
                self.assert_bound(rel, created)
                path.unlink()
                self.assertEqual(before, util.tree_fingerprint(self.root))

    @unittest.skipUnless(os.name == 'posix', 'POSIX filenames can contain non-UTF-8 bytes')
    def test_non_utf8_scratch_and_clean_tracked_names_allow_fingerprints(self) -> None:
        before = util.tree_fingerprint(self.root)
        scratch = self.write(os.fsdecode(b'.qwen/tmp/probe-\xff'))
        self.assertEqual([], util.changed_files(self.root))
        self.assertEqual(before, util.tree_fingerprint(self.root))
        scratch.unlink()
        self.write(os.fsdecode(b'tracked-\xff'))
        self.commit()
        self.assertEqual([], util.changed_files(self.root))
        self.assertEqual(64, len(util.tree_fingerprint(self.root)))

    @unittest.skipUnless(os.name == 'posix', 'POSIX filenames can contain non-UTF-8 bytes')
    def test_non_utf8_included_names_bind_exact_path_and_content(self) -> None:
        for raw in (b'source-\xff.py', b'source-\xfe.py', b'source-\r.py'):
            with self.subTest(raw=raw):
                rel = os.fsdecode(raw)
                before = util.tree_fingerprint(self.root)
                path = self.write(rel)
                self.assert_bound(rel, before)
                untracked = util.tree_fingerprint(self.root)
                path.write_text('two', encoding='utf-8')
                self.assert_bound(rel, untracked)
                self.commit()
                before = util.tree_fingerprint(self.root)
                path.write_text('three', encoding='utf-8')
                self.assert_bound(rel, before)
                self.commit()

    @unittest.skipUnless(os.name == 'posix', 'POSIX symlink targets can contain non-UTF-8 bytes')
    def test_non_utf8_symlink_target_bytes_remain_bound(self) -> None:
        before = util.tree_fingerprint(self.root)
        path = self.root / 'source-link'
        path.symlink_to(os.fsdecode(b'target-\xff'))
        self.assert_bound('source-link', before)
        before = util.tree_fingerprint(self.root)
        path.unlink()
        path.symlink_to(os.fsdecode(b'target-\xfe'))
        self.assert_bound('source-link', before)

    def test_changed_file_json_preserves_filesystem_names_in_utf8_document(self) -> None:
        rel = os.fsdecode(b'source-\xff.py')
        payload = {'changed_files': [rel], 'ordinary_unicode': 'Обзор'}
        path = self.root / 'report.json'
        util.dump_json(path, payload)
        self.assertEqual(payload, json.loads(path.read_bytes().decode('utf-8')))

    def test_verifier_json_output_roundtrips_filesystem_names_and_unicode(self) -> None:
        report = {'status': 'pass', 'changed_files': [os.fsdecode(b'source-\xff.py'), 'Обзор.py']}
        output = io.StringIO()
        script = Path(__file__).resolve().parents[1] / 'scripts/grok_verify.py'
        with (patch.object(sys, 'argv', [str(script), '--json']),
              patch('adaptive_grok.verification.verify', return_value=report),
              patch.object(util, 'find_root', return_value=self.root),
              contextlib.redirect_stdout(output)):
            with self.assertRaises(SystemExit) as raised:
                runpy.run_path(str(script), run_name='__main__')
        self.assertEqual(0, raised.exception.code)
        encoded = output.getvalue().encode('utf-8')
        self.assertEqual(report, json.loads(encoded.decode('utf-8')))

    def test_tracked_noise_paths_bind_edits_and_deletions(self) -> None:
        for rel in ('.qwen/tmp/probe', '.grok-stack/runtime/probe', 'vendor/source.py',
                    'node_modules/source.js', '__pycache__/source.py', 'coverage/source',
                    '.coverage', 'source.pyc', '.pytest_cache/source'):
            for operation in ('edit', 'staged_edit', 'delete', 'staged_delete'):
                with self.subTest(rel=rel, operation=operation):
                    path = self.write(rel)
                    self.commit()
                    before = util.tree_fingerprint(self.root)
                    if operation.endswith('edit'):
                        path.write_text('two', encoding='utf-8')
                    else:
                        path.unlink()
                    if operation.startswith('staged'):
                        self.git('add', '-A')
                    try:
                        self.assert_bound(rel, before)
                    finally:
                        if path.exists():
                            path.unlink()
                        self.commit()

    def test_force_added_ignored_scratch_is_bound(self) -> None:
        self.write('.gitignore', '.qwen/tmp/\n')
        self.commit()
        rel = '.qwen/tmp/ignored'
        path = self.write(rel)
        before = util.tree_fingerprint(self.root)
        self.git('add', '-f', rel)
        self.assert_bound(rel, before)
        self.git('commit', '-qm', 'track ignored scratch')
        before = util.tree_fingerprint(self.root)
        path.write_text('two', encoding='utf-8')
        self.assert_bound(rel, before)

    def test_staged_deletion_recreated_as_untracked_still_binds_its_bytes(self) -> None:
        rel = '.qwen/tmp/recreated'
        self.write(rel)
        self.commit()
        self.git('rm', rel)
        self.assertNotIn(rel, self.git('ls-files', '--cached'))
        self.write(rel, 'replacement one')
        before = util.tree_fingerprint(self.root)
        self.write(rel, 'replacement two')
        self.assert_bound(rel, before)

    def test_rename_and_base_relative_deletion_keep_tracked_provenance(self) -> None:
        old, new = '.qwen/tmp/old', '.qwen/tmp/new'
        self.write(old)
        self.commit()
        base = self.git('rev-parse', 'HEAD')
        before = util.tree_fingerprint(self.root)
        self.git('mv', old, new)
        self.assert_bound(new, before)
        self.assertIn(old, util.changed_files(self.root))
        self.commit()
        self.assertEqual([new, old], util.changed_files(self.root, base=base))
        self.git('rm', new)
        self.git('commit', '-qm', 'delete')
        self.assertEqual([old], util.changed_files(self.root, base=base))

    def test_changed_file_statuses_preserve_deleted_and_renamed_paths(self) -> None:
        old = 'side-projects/seo-landings/winston-wolfe/index.html'
        renamed = 'side-projects/seo-landings/winston-wolfe/renamed.html'
        deleted = 'side-projects/seo-landings/winston-wolfe/robots.txt'
        self.write(old, 'same\n')
        self.write(deleted, 'delete\n')
        self.commit()

        self.git('mv', old, renamed)
        (self.root / deleted).unlink()
        statuses = util.changed_file_statuses(self.root)

        self.assertIsNotNone(statuses)
        self.assertTrue(any(
            item['status'].startswith('R')
            and item['original_path'] == old
            and item['path'] == renamed
            for item in statuses
        ))
        self.assertTrue(any(
            item['status'] == 'D' and item['path'] == deleted
            for item in statuses
        ))

    def test_changed_file_statuses_preserve_copied_paths_in_commit_range(self) -> None:
        source = 'tests/test_winston_wolfe_seo_landing.py'
        copied = 'tests/test_winston_wolfe_seo_landing_copy.py'
        self.write(source, 'same\n')
        self.commit()
        base = self.git('rev-parse', 'HEAD')

        self.write(copied, 'same\n')
        self.commit()
        statuses = util.changed_file_statuses(
            self.root,
            base=base,
            include_worktree=False,
            include_untracked=False,
        )

        self.assertIsNotNone(statuses)
        self.assertTrue(any(
            item['status'].startswith('C')
            and item['original_path'] == source
            and item['path'] == copied
            for item in statuses
        ))

    def test_meaningful_configuration_source_and_prefix_lookalikes_stay_bound(self) -> None:
        for rel in ('.qwen/settings.json', '.codex/config.toml', '.agents/skills/task.md',
                    '.claude/settings.json', 'new.py', '.qwen/tmpfile', '.qwen/tmp-config.json',
                    'nested/.qwen/tmp/file', '.qwen/tmp', '.qwen/tmp-link/file'):
            with self.subTest(rel=rel):
                before = util.tree_fingerprint(self.root)
                path = self.write(rel)
                self.assert_bound(rel, before)
                self.commit()
                before = util.tree_fingerprint(self.root)
                path.write_text('two', encoding='utf-8')
                self.assert_bound(rel, before)
                self.commit()

    def test_existing_untracked_runtime_noise_remains_excluded(self) -> None:
        before = util.tree_fingerprint(self.root)
        for rel in ('.grok-stack/runtime/receipt.json', '__pycache__/cache.pyc',
                    '.pytest_cache/file', 'vendor/generated', 'node_modules/generated',
                    'coverage/report', '.coverage', 'module.pyo'):
            self.write(rel)
        self.assertEqual([], util.changed_files(self.root))
        self.assertEqual(before, util.tree_fingerprint(self.root))

    def test_failed_timed_out_or_malformed_tracking_inventory_keeps_candidates(self) -> None:
        original_run = subprocess.run
        for code, output in ((1, b''), ('timeout', b''), ('oserror', b''), (0, b'unterminated')):
            with self.subTest(code=code, output=output):
                def failed_inventory(args, **kwargs):
                    if args[:3] == ['git', 'ls-files', '--cached']:
                        if code == 'timeout':
                            raise subprocess.TimeoutExpired(args, 60)
                        if code == 'oserror':
                            raise OSError('Git unavailable')
                        return subprocess.CompletedProcess(args, code, output, b'failure')
                    return original_run(args, **kwargs)

                with patch.object(subprocess, 'run', side_effect=failed_inventory):
                    before = util.tree_fingerprint(self.root)
                    for rel in ('.qwen/tmp/probe', '.grok-stack/runtime/probe'):
                        path = self.write(rel)
                        self.assert_bound(rel, before)
                        path.unlink()

    def test_non_git_and_unborn_repositories_conservatively_bind_scratch(self) -> None:
        with tempfile.TemporaryDirectory(prefix='fingerprint-no-head-') as tmp:
            self.root = Path(tmp)
            rel = '.qwen/tmp/probe'
            before = util.tree_fingerprint(self.root)
            path = self.write(rel)
            self.assert_bound(rel, before)
            self.git('init', '-q')
            before = util.tree_fingerprint(self.root)
            path.write_text('two', encoding='utf-8')
            self.assert_bound(rel, before)
            tracked = '.grok-stack/runtime/tracked'
            self.write(tracked)
            self.git('add', tracked)
            before = util.tree_fingerprint(self.root)
            (self.root / tracked).unlink()
            self.assert_bound(tracked, before)

    def test_failed_diff_does_not_authorize_scratch_filtering(self) -> None:
        original_run = subprocess.run

        def failed_diff(args, **kwargs):
            if args[:2] == ['git', 'diff']:
                return subprocess.CompletedProcess(args, 1, b'', b'failure')
            return original_run(args, **kwargs)

        with patch.object(subprocess, 'run', side_effect=failed_diff):
            before = util.tree_fingerprint(self.root)
            self.write('.qwen/tmp/probe')
            self.assert_bound('.qwen/tmp/probe', before)


if __name__ == '__main__':
    unittest.main()
