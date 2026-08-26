from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from adaptive_trust_ci import workspace as workspace_module


class GitWorkspaceLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base_directory = Path(self.temp.name) / 'workspaces'
        self.base_directory.mkdir()
        self.job = SimpleNamespace(job_id='lifecycle-test', head_sha='0' * 40)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _construct(self) -> workspace_module.GitWorkspace:
        return workspace_module.GitWorkspace(
            self.job,
            github_token='token',
            checkout_depth=1,
            base_directory=self.base_directory,
        )

    def _assert_constructor_failure_leaves_no_workspace(
        self,
        failure: OSError,
        patcher: mock._patch,
    ) -> None:
        with patcher:
            with self.assertRaises(OSError) as raised:
                self._construct()
        self.assertIs(raised.exception, failure)
        self.assertEqual(tuple(self.base_directory.iterdir()), ())

    def test_constructor_cleans_checkout_when_checkout_chmod_fails(self) -> None:
        failure = OSError('synthetic checkout chmod failure')
        self._assert_constructor_failure_leaves_no_workspace(
            failure,
            mock.patch.object(workspace_module.os, 'chmod', side_effect=failure),
        )

    def test_constructor_cleans_checkout_when_config_mkdtemp_fails(self) -> None:
        failure = OSError('synthetic config mkdtemp failure')
        real_mkdtemp = tempfile.mkdtemp
        calls = 0

        def fail_second_mkdtemp(*args: object, **kwargs: object) -> str:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise failure
            return real_mkdtemp(*args, **kwargs)

        self._assert_constructor_failure_leaves_no_workspace(
            failure,
            mock.patch.object(workspace_module.tempfile, 'mkdtemp', side_effect=fail_second_mkdtemp),
        )

    def test_constructor_cleans_both_paths_when_config_chmod_fails(self) -> None:
        failure = OSError('synthetic config chmod failure')
        self._assert_constructor_failure_leaves_no_workspace(
            failure,
            mock.patch.object(workspace_module.os, 'chmod', side_effect=(None, failure)),
        )

    def test_constructor_cleans_both_paths_when_xdg_mkdir_fails(self) -> None:
        failure = OSError('synthetic XDG mkdir failure')
        real_mkdir = Path.mkdir

        def fail_xdg_mkdir(path: Path, *args: object, **kwargs: object) -> None:
            if path.name == 'xdg':
                raise failure
            real_mkdir(path, *args, **kwargs)

        self._assert_constructor_failure_leaves_no_workspace(
            failure,
            mock.patch.object(Path, 'mkdir', autospec=True, side_effect=fail_xdg_mkdir),
        )

    def test_cleanup_is_idempotent(self) -> None:
        workspace = self._construct()
        workspace.cleanup()
        workspace.cleanup()
        self.assertEqual(tuple(self.base_directory.iterdir()), ())


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

    @staticmethod
    def _pid_exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True

    def _force_probe_cleanup(self, pid: int | None) -> None:
        if pid is None or not self._pid_exists(pid):
            return
        os.kill(pid, signal.SIGKILL)
        deadline = time.monotonic() + 2
        while self._pid_exists(pid) and time.monotonic() < deadline:
            time.sleep(0.01)

    @staticmethod
    def _descendant_leader_script(mode: str) -> str:
        descendant = (
            'import os,signal,sys,time\n'
            'signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
            'os.close(1); os.close(2)\n'
            'open(sys.argv[1], "w").write(str(os.getpid()))\n'
            'time.sleep(60)\n'
        )
        action = {
            'stdout': 'while True: os.write(1, b"x" * 4096)\n',
            'stderr': 'while True: os.write(2, b"e" * 4096)\n',
            'timeout': 'os.close(1); os.close(2); time.sleep(60)\n',
        }[mode]
        return (
            'import os,subprocess,sys,time\n'
            f'descendant={descendant!r}\n'
            'subprocess.Popen([sys.executable, "-c", descendant, sys.argv[1]])\n'
            'deadline=time.monotonic()+2\n'
            'while not os.path.exists(sys.argv[1]) and time.monotonic() < deadline: time.sleep(0.01)\n'
            + action
        )

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

    def test_git_commands_ignore_committed_executable_global_config(self) -> None:
        marker = Path(self.temp.name) / 'untrusted-config-executed'
        executable = Path(self.temp.name) / 'untrusted-git-command'
        executable.write_text(
            '#!/bin/sh\nprintf executed >> "$1"\nprintf token\n',
            encoding='utf-8',
        )
        executable.chmod(0o755)
        hooks = Path(self.temp.name) / 'untrusted-hooks'
        hooks.mkdir()
        hook = hooks / 'post-checkout'
        hook.write_text(f'#!/bin/sh\nprintf hook >> {marker}\n', encoding='utf-8')
        hook.chmod(0o755)
        config = (
            '[core]\n'
            f'\tfsmonitor = {executable} {marker}\n'
            f'\thooksPath = {hooks}\n'
            '[diff]\n'
            f'\texternal = {executable} {marker}\n'
        )
        (self.workspace.path / '.gitconfig').write_text(config, encoding='utf-8')
        unusual = self.workspace.path / 'line\nbreak.txt'
        unusual.write_text('exact\n', encoding='utf-8')
        subprocess.run(['git', 'add', '.'], cwd=self.workspace.path, check=True)
        subprocess.run(['git', 'commit', '-qm', 'untrusted config'], cwd=self.workspace.path, check=True)
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.workspace.path, text=True).strip()
        self.workspace.job.head_sha = head

        changed = self.workspace._changed_files(self.base, head)
        self.assertEqual(changed, tuple(sorted(('.gitconfig', 'line\nbreak.txt'))))
        self.workspace.reset()
        self.workspace.assert_unchanged()
        self.assertFalse(marker.exists(), 'repository-controlled Git config executed on the host')

        env = self.workspace._git_env(authenticated=False)
        trusted_home = Path(env['HOME'])
        self.assertNotEqual(trusted_home, self.workspace.path)
        self.assertEqual(env['GIT_CONFIG_GLOBAL'], os.devnull)
        self.assertEqual(env['GIT_CONFIG_SYSTEM'], os.devnull)
        self.assertEqual(env['XDG_CONFIG_HOME'], str(trusted_home / 'xdg'))
        authenticated = self.workspace._git_env(authenticated=True)
        self.assertEqual(authenticated['GIT_CONFIG_COUNT'], '3')
        self.assertEqual(authenticated['GIT_CONFIG_KEY_0'], 'core.hooksPath')
        self.assertEqual(authenticated['GIT_CONFIG_KEY_1'], 'core.fsmonitor')
        self.assertEqual(authenticated['GIT_CONFIG_KEY_2'], 'http.extraHeader')
        self.assertTrue(authenticated['GIT_CONFIG_VALUE_2'].startswith('Authorization: Basic '))
        self.workspace.cleanup()
        self.assertFalse(trusted_home.exists())

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

    def test_bounded_process_kills_sigterm_ignoring_descendants(self) -> None:
        for mode, error in (
            ('stdout', 'stdout byte limit'),
            ('stderr', 'stderr byte limit'),
            ('timeout', 'timeout'),
        ):
            with self.subTest(mode=mode):
                pid_file = Path(self.temp.name) / f'{mode}-descendant.pid'
                descendant_pid = None
                try:
                    with self.assertRaisesRegex(workspace_module.WorkspaceError, error):
                        workspace_module._run_bounded_process(
                            [sys.executable, '-c', self._descendant_leader_script(mode), str(pid_file)],
                            cwd=Path(self.temp.name),
                            env=dict(os.environ),
                            timeout=0.2 if mode == 'timeout' else 5,
                            stdout_limit=128,
                            stderr_limit=128,
                            stdout_consumer=lambda _chunk: None,
                        )
                    descendant_pid = int(pid_file.read_text(encoding='ascii'))
                    self.assertFalse(
                        self._pid_exists(descendant_pid),
                        f'{mode} cleanup left a same-group descendant alive',
                    )
                finally:
                    self._force_probe_cleanup(descendant_pid)

    def test_process_group_cleanup_refuses_own_group_and_tolerates_esrch(self) -> None:
        with self.assertRaisesRegex(workspace_module.WorkspaceError, 'worker process group'):
            workspace_module._signal_process_group(os.getpgrp(), signal.SIGTERM)
        missing_group = 2_000_000_000
        self.assertFalse(workspace_module._process_group_exists(missing_group))
        workspace_module._signal_process_group(missing_group, signal.SIGKILL)


if __name__ == '__main__':
    unittest.main()
