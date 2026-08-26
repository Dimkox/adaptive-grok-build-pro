from __future__ import annotations

import base64
import os
import selectors
import signal
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable, Sequence

from .models import Checkout, Job

_MAX_GIT_PATH_BYTES = 4096
_MAX_GIT_PATHS = 100_000
_MAX_GIT_PATH_OUTPUT_BYTES = 100_000_000
_MAX_GIT_COMMAND_OUTPUT_BYTES = 65_536
_MAX_GIT_STDERR_BYTES = 1_000_000


class WorkspaceError(RuntimeError):
    pass


class WorkspaceMutationError(WorkspaceError):
    def __init__(self, paths: tuple[str, ...]) -> None:
        self.paths = paths
        super().__init__('verification command mutated checkout: ' + ', '.join(repr(path) for path in paths[:20]))


class _NulPathCollector:
    def __init__(self, *, context: str, record_prefix_bytes: int) -> None:
        self.context = context
        self.record_prefix_bytes = record_prefix_bytes
        self._buffer = bytearray()
        self._records: list[bytes] = []
        self._total_bytes = 0

    def feed(self, chunk: bytes) -> None:
        self._total_bytes += len(chunk)
        if self._total_bytes > _MAX_GIT_PATH_OUTPUT_BYTES:
            raise WorkspaceError(f'{self.context} path output exceeds the configured byte limit')
        self._buffer.extend(chunk)
        while True:
            delimiter = self._buffer.find(0)
            if delimiter < 0:
                self._check_record_size(len(self._buffer))
                return
            record = bytes(self._buffer[:delimiter])
            del self._buffer[:delimiter + 1]
            if not record:
                raise WorkspaceError(f'{self.context} returned an invalid path set')
            self._check_record_size(len(record))
            if len(self._records) >= _MAX_GIT_PATHS:
                raise WorkspaceError(f'{self.context} path count exceeds the configured limit')
            self._records.append(record)

    def finish(self) -> tuple[bytes, ...]:
        if self._buffer:
            raise WorkspaceError(f'{self.context} did not return NUL-delimited paths')
        return tuple(self._records)

    def _check_record_size(self, size: int) -> None:
        if size > _MAX_GIT_PATH_BYTES + self.record_prefix_bytes:
            raise WorkspaceError(f'{self.context} path exceeds the configured byte limit')


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=1)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def _run_bounded_process(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float,
    stdout_limit: int,
    stderr_limit: int,
    stdout_consumer: Callable[[bytes], None],
) -> tuple[int, bytes]:
    try:
        process = subprocess.Popen(
            list(argv),
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        raise WorkspaceError(f'cannot start {argv[0]!r}: {exc}') from exc
    assert process.stdout is not None
    assert process.stderr is not None
    stderr = bytearray()
    stdout_bytes = 0
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
    selector.register(process.stderr, selectors.EVENT_READ, 'stderr')
    deadline = time.monotonic() + timeout
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise WorkspaceError(f'{argv[0]} process exceeded its timeout')
            events = selector.select(remaining)
            if not events:
                raise WorkspaceError(f'{argv[0]} process exceeded its timeout')
            for key, _mask in events:
                remaining_bytes = (
                    stdout_limit - stdout_bytes
                    if key.data == 'stdout'
                    else stderr_limit - len(stderr)
                )
                chunk = os.read(key.fileobj.fileno(), min(65_536, remaining_bytes + 1))
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                if key.data == 'stdout':
                    stdout_bytes += len(chunk)
                    if stdout_bytes > stdout_limit:
                        raise WorkspaceError(f'{argv[0]} stdout byte limit exceeded')
                    stdout_consumer(chunk)
                else:
                    if len(stderr) + len(chunk) > stderr_limit:
                        raise WorkspaceError(f'{argv[0]} stderr byte limit exceeded')
                    stderr.extend(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise WorkspaceError(f'{argv[0]} process exceeded its timeout')
        return process.wait(timeout=remaining), bytes(stderr)
    except subprocess.TimeoutExpired as exc:
        _terminate_process(process)
        raise WorkspaceError(f'{argv[0]} process exceeded its timeout') from exc
    except BaseException:
        _terminate_process(process)
        raise
    finally:
        selector.close()
        for stream in (process.stdout, process.stderr):
            if not stream.closed:
                stream.close()


class GitWorkspace:
    """Trusted exact-SHA checkout. Repository code is never executed by this class."""

    def __init__(
        self,
        job: Job,
        *,
        github_token: str,
        checkout_depth: int,
        base_directory: Path,
    ) -> None:
        if not github_token.strip():
            raise ValueError('GitHub token is required for checkout')
        if checkout_depth <= 0:
            raise ValueError('checkout_depth must be positive')
        base_directory.mkdir(parents=True, exist_ok=True)
        self.job = job
        self.github_token = github_token
        self.checkout_depth = checkout_depth
        self.path = Path(tempfile.mkdtemp(prefix=f'trust-ci-{job.job_id[:8]}-', dir=base_directory))
        os.chmod(self.path, 0o755)

    def checkout(self, job: Job) -> Checkout:
        if job.job_id != self.job.job_id:
            raise ValueError('workspace job mismatch')
        self._git('init', '--quiet')
        self._git('remote', 'add', 'origin', f'https://github.com/{job.repository}.git')
        self._git(
            'fetch',
            '--quiet',
            '--no-tags',
            f'--depth={self.checkout_depth}',
            'origin',
            f'+refs/heads/{job.base_ref}:refs/remotes/origin/{job.base_ref}',
            f'+refs/pull/{job.pr_number}/head:refs/remotes/origin/pr/{job.pr_number}',
            authenticated=True,
        )
        fetched_head = self._git_output('rev-parse', f'refs/remotes/origin/pr/{job.pr_number}')
        if fetched_head != job.head_sha:
            raise RuntimeError('GitHub PR ref does not match webhook head SHA')
        if not self._commit_exists(job.base_sha):
            self._git(
                'fetch',
                '--quiet',
                '--no-tags',
                f'--depth={self.checkout_depth}',
                'origin',
                job.base_sha,
                authenticated=True,
            )
        if not self._commit_exists(job.head_sha):
            raise RuntimeError('exact head SHA is unavailable after fetch')
        self._git('checkout', '--quiet', '--detach', job.head_sha)
        if self._git_output('rev-parse', 'HEAD') != job.head_sha:
            raise RuntimeError('checked-out HEAD does not match requested SHA')
        changed = self._changed_files(job.base_sha, job.head_sha)
        self.reset()
        self.assert_unchanged()
        return Checkout(path=self.path, changed_files=changed)

    def assert_unchanged(self) -> None:
        if self._git_output('rev-parse', 'HEAD') != self.job.head_sha:
            raise WorkspaceMutationError(('HEAD',))
        records = self._git_nul_records(
            'status', '--porcelain=v1', '-z', '--untracked-files=all', '--no-renames',
            context='git status',
            record_prefix_bytes=3,
        )
        if not records:
            return
        paths: list[str] = []
        for record in records:
            if len(record) < 4 or record[2:3] != b' ':
                raise WorkspaceMutationError(('unparseable-git-status',))
            paths.append(self._decode_git_path(record[3:]))
        raise WorkspaceMutationError(tuple(sorted(set(paths))))

    def _changed_files(self, base_sha: str, head_sha: str) -> tuple[str, ...]:
        if not self._commit_exists(base_sha) or not self._commit_exists(head_sha):
            raise RuntimeError('exact base/head SHA is unavailable for changed-path discovery')
        records = self._git_nul_records(
            'diff', '--name-only', '-z', '--no-renames', base_sha, head_sha, '--',
            context='git diff',
            record_prefix_bytes=0,
        )
        return tuple(sorted({self._decode_git_path(record) for record in records}))

    def _git_nul_records(
        self,
        *args: str,
        context: str,
        record_prefix_bytes: int,
    ) -> tuple[bytes, ...]:
        collector = _NulPathCollector(context=context, record_prefix_bytes=record_prefix_bytes)
        returncode, stderr = _run_bounded_process(
            ['git', *args],
            cwd=self.path,
            env=self._git_env(authenticated=False),
            timeout=120,
            stdout_limit=_MAX_GIT_PATH_OUTPUT_BYTES,
            stderr_limit=_MAX_GIT_STDERR_BYTES,
            stdout_consumer=collector.feed,
        )
        if returncode != 0:
            output = stderr[-4000:].decode('utf-8', errors='replace')
            raise WorkspaceError(f"git {' '.join(args[:2])} failed: {output}")
        return collector.finish()

    @staticmethod
    def _decode_git_path(raw: bytes) -> str:
        if len(raw) > _MAX_GIT_PATH_BYTES:
            raise WorkspaceError('git path exceeds the configured byte limit')
        try:
            value = raw.decode('utf-8', errors='strict')
        except UnicodeDecodeError as exc:
            raise WorkspaceError('git path is not strict UTF-8') from exc
        path = Path(value)
        if not value or path.is_absolute() or any(part in {'', '.', '..'} for part in path.parts):
            raise WorkspaceError('git returned an unsafe repository path')
        return value

    def reset(self) -> None:
        if not (self.path / '.git').is_dir():
            return
        self._git('reset', '--hard', '--quiet', self.job.head_sha)
        self._git('clean', '-ffdqx')
        self.assert_unchanged()

    def cleanup(self) -> None:
        shutil.rmtree(self.path, ignore_errors=True)

    def _commit_exists(self, sha: str) -> bool:
        stdout = bytearray()
        returncode, _stderr = _run_bounded_process(
            ['git', 'cat-file', '-e', f'{sha}^{{commit}}'],
            cwd=self.path,
            env=self._git_env(authenticated=False),
            timeout=60,
            stdout_limit=_MAX_GIT_COMMAND_OUTPUT_BYTES,
            stderr_limit=_MAX_GIT_STDERR_BYTES,
            stdout_consumer=stdout.extend,
        )
        return returncode == 0

    def _git(self, *args: str, authenticated: bool = False) -> None:
        stdout = bytearray()
        returncode, stderr = _run_bounded_process(
            ['git', *args],
            cwd=self.path,
            env=self._git_env(authenticated=authenticated),
            timeout=300,
            stdout_limit=_MAX_GIT_COMMAND_OUTPUT_BYTES,
            stderr_limit=_MAX_GIT_STDERR_BYTES,
            stdout_consumer=stdout.extend,
        )
        if returncode != 0:
            output = (stderr or stdout)[-4000:].decode('utf-8', errors='replace')
            raise RuntimeError(f"git {' '.join(args[:2])} failed: {output}")

    def _git_output(self, *args: str) -> str:
        try:
            return self._git_bytes(*args).decode('utf-8', errors='strict').strip()
        except UnicodeDecodeError as exc:
            raise RuntimeError(f"git {' '.join(args[:2])} returned non-UTF-8 output") from exc

    def _git_bytes(self, *args: str) -> bytes:
        stdout = bytearray()
        returncode, stderr = _run_bounded_process(
            ['git', *args],
            cwd=self.path,
            env=self._git_env(authenticated=False),
            timeout=120,
            stdout_limit=_MAX_GIT_COMMAND_OUTPUT_BYTES,
            stderr_limit=_MAX_GIT_STDERR_BYTES,
            stdout_consumer=stdout.extend,
        )
        if returncode != 0:
            output = (stderr or stdout)[-4000:].decode('utf-8', errors='replace')
            raise RuntimeError(f"git {' '.join(args[:2])} failed: {output}")
        return bytes(stdout)

    def _git_env(self, *, authenticated: bool) -> dict[str, str]:
        env = {
            'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin'),
            'HOME': str(self.path),
            'GIT_TERMINAL_PROMPT': '0',
            'GIT_CONFIG_NOSYSTEM': '1',
        }
        if authenticated:
            basic = base64.b64encode(f'x-access-token:{self.github_token}'.encode()).decode('ascii')
            env.update(
                {
                    'GIT_CONFIG_COUNT': '1',
                    'GIT_CONFIG_KEY_0': 'http.extraHeader',
                    'GIT_CONFIG_VALUE_0': f'Authorization: Basic {basic}',
                }
            )
        return env
