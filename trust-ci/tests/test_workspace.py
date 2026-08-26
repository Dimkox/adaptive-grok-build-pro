from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from adaptive_trust_ci import workspace as workspace_module


class WorkspaceStreamingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.workspace = workspace_module.GitWorkspace(
            SimpleNamespace(job_id='streaming-test', head_sha='0' * 40),
            github_token='token',
            checkout_depth=1,
            base_directory=root / 'workspaces',
        )
        subprocess.run(['git', 'init', '-q'], cwd=self.workspace.path, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=self.workspace.path, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.workspace.path, check=True)
        (self.workspace.path / 'README.md').write_text('base\n', encoding='utf-8')
        subprocess.run(['git', 'add', '.'], cwd=self.workspace.path, check=True)
        subprocess.run(['git', 'commit', '-qm', 'base'], cwd=self.workspace.path, check=True)
        self.base = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.workspace.path, text=True).strip()

    def tearDown(self) -> None:
        self.workspace.cleanup()
        self.temp.cleanup()

    def _commit_paths(self, paths: tuple[str, ...]) -> str:
        for rel in paths:
            target = self.workspace.path / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rel, encoding='utf-8')
        subprocess.run(['git', 'add', '.'], cwd=self.workspace.path, check=True)
        subprocess.run(['git', 'commit', '-qm', 'paths'], cwd=self.workspace.path, check=True)
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.workspace.path, text=True).strip()

    def test_real_git_diff_enforces_byte_count_and_path_limits(self) -> None:
        paths = ('a.txt', 'directory/long-name.txt')
        head = self._commit_paths(paths)
        encoded_size = sum(len(path.encode('utf-8')) + 1 for path in paths)
        with mock.patch.object(workspace_module, '_MAX_GIT_PATH_OUTPUT_BYTES', encoded_size):
            self.assertEqual(self.workspace._changed_files(self.base, head), paths)
        with mock.patch.object(workspace_module, '_MAX_GIT_PATH_OUTPUT_BYTES', encoded_size - 1):
            with self.assertRaisesRegex(workspace_module.WorkspaceError, 'byte limit'):
                self.workspace._changed_files(self.base, head)
        with mock.patch.object(workspace_module, '_MAX_GIT_PATHS', 1):
            with self.assertRaisesRegex(workspace_module.WorkspaceError, 'path count'):
                self.workspace._changed_files(self.base, head)
        with mock.patch.object(workspace_module, '_MAX_GIT_PATH_BYTES', len('a.txt') - 1):
            with self.assertRaisesRegex(workspace_module.WorkspaceError, 'path.*byte limit'):
                self.workspace._changed_files(self.base, head)

    def test_real_git_status_preserves_exact_paths_and_enforces_limits(self) -> None:
        paths = ('line\nbreak.txt', 'tab\tname.txt', 'back\\slash.txt')
        self.workspace.job.head_sha = self.base
        for rel in paths:
            (self.workspace.path / rel).write_text(rel, encoding='utf-8')
        with self.assertRaises(workspace_module.WorkspaceMutationError) as raised:
            self.workspace.assert_unchanged()
        self.assertEqual(raised.exception.paths, tuple(sorted(paths)))
        status_size = sum(3 + len(path.encode('utf-8')) + 1 for path in paths)
        with mock.patch.object(workspace_module, '_MAX_GIT_PATH_OUTPUT_BYTES', status_size - 1):
            with self.assertRaisesRegex(workspace_module.WorkspaceError, 'byte limit'):
                self.workspace.assert_unchanged()
        with mock.patch.object(workspace_module, '_MAX_GIT_PATHS', len(paths) - 1):
            with self.assertRaisesRegex(workspace_module.WorkspaceError, 'path count'):
                self.workspace.assert_unchanged()
        with mock.patch.object(workspace_module, '_MAX_GIT_PATH_BYTES', len('tab\tname.txt') - 1):
            with self.assertRaisesRegex(workspace_module.WorkspaceError, 'path.*byte limit'):
                self.workspace.assert_unchanged()

    def test_nul_parser_enforces_limits_incrementally_across_chunks(self) -> None:
        collector = workspace_module._NulPathCollector(context='synthetic', record_prefix_bytes=0)
        collector.feed(b'line\n')
        collector.feed(b'name\0tab\tname\0')
        self.assertEqual(collector.finish(), (b'line\nname', b'tab\tname'))
        with mock.patch.object(workspace_module, '_MAX_GIT_PATHS', 1):
            collector = workspace_module._NulPathCollector(context='synthetic', record_prefix_bytes=0)
            with self.assertRaisesRegex(workspace_module.WorkspaceError, 'path count'):
                collector.feed(b'a\0b\0')
        with mock.patch.object(workspace_module, '_MAX_GIT_PATH_BYTES', 3):
            collector = workspace_module._NulPathCollector(context='synthetic', record_prefix_bytes=0)
            with self.assertRaisesRegex(workspace_module.WorkspaceError, 'path.*byte limit'):
                collector.feed(b'abcd')
        with mock.patch.object(workspace_module, '_MAX_GIT_PATH_OUTPUT_BYTES', 4):
            collector = workspace_module._NulPathCollector(context='synthetic', record_prefix_bytes=0)
            collector.feed(b'a\0b\0')
            self.assertEqual(collector.finish(), (b'a', b'b'))
            collector = workspace_module._NulPathCollector(context='synthetic', record_prefix_bytes=0)
            with self.assertRaisesRegex(workspace_module.WorkspaceError, 'byte limit'):
                collector.feed(b'a\0b\0c')

    def test_bounded_process_terminates_child_on_stdout_overflow(self) -> None:
        pid_file = Path(self.temp.name) / 'child.pid'
        script = (
            'import os,sys\n'
            'open(sys.argv[1], "w").write(str(os.getpid()))\n'
            'while True: os.write(1, b"x" * 4096)\n'
        )
        with self.assertRaisesRegex(workspace_module.WorkspaceError, 'stdout byte limit'):
            workspace_module._run_bounded_process(
                [sys.executable, '-c', script, str(pid_file)],
                cwd=Path(self.temp.name),
                env=dict(os.environ),
                timeout=5,
                stdout_limit=128,
                stderr_limit=128,
                stdout_consumer=lambda _chunk: None,
            )
        pid = int(pid_file.read_text(encoding='ascii'))
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_bounded_process_caps_stderr_before_returning(self) -> None:
        script = 'import os; os.write(2, b"e" * 4096)'
        with self.assertRaisesRegex(workspace_module.WorkspaceError, 'stderr byte limit'):
            workspace_module._run_bounded_process(
                [sys.executable, '-c', script],
                cwd=Path(self.temp.name),
                env=dict(os.environ),
                timeout=5,
                stdout_limit=128,
                stderr_limit=128,
                stdout_consumer=lambda _chunk: None,
            )

    def test_bounded_process_never_reads_more_than_remaining_limit_plus_one(self) -> None:
        real_read = os.read
        requested_sizes: list[int] = []

        def tracked_read(descriptor: int, size: int) -> bytes:
            requested_sizes.append(size)
            return real_read(descriptor, size)

        output = bytearray()
        with mock.patch.object(workspace_module.os, 'read', side_effect=tracked_read):
            returncode, stderr = workspace_module._run_bounded_process(
                [sys.executable, '-c', 'import os; os.write(1, b"x" * 128)'],
                cwd=Path(self.temp.name),
                env=dict(os.environ),
                timeout=5,
                stdout_limit=128,
                stderr_limit=128,
                stdout_consumer=output.extend,
            )
        self.assertEqual(returncode, 0)
        self.assertEqual(stderr, b'')
        self.assertEqual(bytes(output), b'x' * 128)
        stream_read_sizes = [size for size in requested_sizes if size != 50_000]
        self.assertTrue(stream_read_sizes)
        self.assertLessEqual(max(stream_read_sizes), 129)

    def test_bounded_process_terminates_child_on_timeout(self) -> None:
        pid_file = Path(self.temp.name) / 'timeout-child.pid'
        script = (
            'import os,sys,time\n'
            'open(sys.argv[1], "w").write(str(os.getpid()))\n'
            'os.close(1); os.close(2)\n'
            'time.sleep(60)\n'
        )
        with self.assertRaisesRegex(workspace_module.WorkspaceError, 'timeout'):
            workspace_module._run_bounded_process(
                [sys.executable, '-c', script, str(pid_file)],
                cwd=Path(self.temp.name),
                env=dict(os.environ),
                timeout=0.1,
                stdout_limit=128,
                stderr_limit=128,
                stdout_consumer=lambda _chunk: None,
            )
        pid = int(pid_file.read_text(encoding='ascii'))
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)


if __name__ == '__main__':
    unittest.main()
