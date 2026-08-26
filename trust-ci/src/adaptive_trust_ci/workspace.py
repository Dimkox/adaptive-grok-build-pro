from __future__ import annotations

import base64
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import Checkout, Job

_MAX_GIT_PATH_BYTES = 4096
_MAX_GIT_PATHS = 100_000
_MAX_GIT_PATH_OUTPUT_BYTES = 100_000_000


class WorkspaceMutationError(RuntimeError):
    def __init__(self, paths: tuple[str, ...]) -> None:
        self.paths = paths
        super().__init__('verification command mutated checkout: ' + ', '.join(repr(path) for path in paths[:20]))


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
        status = self._git_bytes('status', '--porcelain=v1', '-z', '--untracked-files=all', '--no-renames')
        if not status:
            return
        records = self._nul_records(status, context='git status')
        paths: list[str] = []
        for record in records:
            if len(record) < 4 or record[2:3] != b' ':
                raise WorkspaceMutationError(('unparseable-git-status',))
            paths.append(self._decode_git_path(record[3:]))
        raise WorkspaceMutationError(tuple(sorted(set(paths))))

    def _changed_files(self, base_sha: str, head_sha: str) -> tuple[str, ...]:
        if not self._commit_exists(base_sha) or not self._commit_exists(head_sha):
            raise RuntimeError('exact base/head SHA is unavailable for changed-path discovery')
        raw = self._git_bytes('diff', '--name-only', '-z', '--no-renames', base_sha, head_sha, '--')
        records = self._nul_records(raw, context='git diff')
        return tuple(sorted({self._decode_git_path(record) for record in records}))

    @staticmethod
    def _nul_records(raw: bytes, *, context: str) -> tuple[bytes, ...]:
        if len(raw) > _MAX_GIT_PATH_OUTPUT_BYTES:
            raise RuntimeError(f'{context} path output exceeds the configured byte limit')
        if not raw:
            return ()
        if not raw.endswith(b'\0'):
            raise RuntimeError(f'{context} did not return NUL-delimited paths')
        records = tuple(raw[:-1].split(b'\0'))
        if len(records) > _MAX_GIT_PATHS or any(not record for record in records):
            raise RuntimeError(f'{context} returned an invalid path set')
        return records

    @staticmethod
    def _decode_git_path(raw: bytes) -> str:
        if len(raw) > _MAX_GIT_PATH_BYTES:
            raise RuntimeError('git path exceeds the configured byte limit')
        try:
            value = raw.decode('utf-8', errors='strict')
        except UnicodeDecodeError as exc:
            raise RuntimeError('git path is not strict UTF-8') from exc
        path = Path(value)
        if not value or path.is_absolute() or any(part in {'', '.', '..'} for part in path.parts):
            raise RuntimeError('git returned an unsafe repository path')
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
        process = subprocess.run(
            ['git', 'cat-file', '-e', f'{sha}^{{commit}}'],
            cwd=self.path,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
            env=self._git_env(authenticated=False),
        )
        return process.returncode == 0

    def _git(self, *args: str, authenticated: bool = False) -> None:
        process = subprocess.run(
            ['git', *args],
            cwd=self.path,
            text=True,
            capture_output=True,
            check=False,
            timeout=300,
            env=self._git_env(authenticated=authenticated),
        )
        if process.returncode != 0:
            output = (process.stderr or process.stdout)[-4000:]
            raise RuntimeError(f"git {' '.join(args[:2])} failed: {output}")

    def _git_output(self, *args: str) -> str:
        try:
            return self._git_bytes(*args).decode('utf-8', errors='strict').strip()
        except UnicodeDecodeError as exc:
            raise RuntimeError(f"git {' '.join(args[:2])} returned non-UTF-8 output") from exc

    def _git_bytes(self, *args: str) -> bytes:
        process = subprocess.run(
            ['git', *args],
            cwd=self.path,
            capture_output=True,
            check=False,
            timeout=120,
            env=self._git_env(authenticated=False),
        )
        if process.returncode != 0:
            output = (process.stderr or process.stdout)[-4000:].decode('utf-8', errors='replace')
            raise RuntimeError(f"git {' '.join(args[:2])} failed: {output}")
        return process.stdout

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
