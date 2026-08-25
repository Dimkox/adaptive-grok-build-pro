from __future__ import annotations

import base64
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import Checkout, Job


class WorkspaceMutationError(RuntimeError):
    def __init__(self, paths: tuple[str, ...]) -> None:
        self.paths = paths
        super().__init__('verification command mutated checkout: ' + ', '.join(paths[:20]))


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
        changed = tuple(
            sorted(
                {
                    line.strip().replace('\\', '/')
                    for line in self._git_output(
                        'diff',
                        '--name-only',
                        '--no-renames',
                        job.base_sha,
                        job.head_sha,
                    ).splitlines()
                    if line.strip()
                }
            )
        )
        self.reset()
        self.assert_unchanged()
        return Checkout(path=self.path, changed_files=changed)

    def assert_unchanged(self) -> None:
        if self._git_output('rev-parse', 'HEAD') != self.job.head_sha:
            raise WorkspaceMutationError(('HEAD',))
        status = self._git_output('status', '--porcelain=v1', '--untracked-files=all')
        if not status:
            return
        paths: list[str] = []
        for line in status.splitlines():
            value = line[3:].strip()
            if ' -> ' in value:
                value = value.split(' -> ', 1)[1]
            paths.append(value.replace('\\', '/'))
        raise WorkspaceMutationError(tuple(sorted(set(paths))))

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
        process = subprocess.run(
            ['git', *args],
            cwd=self.path,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
            env=self._git_env(authenticated=False),
        )
        if process.returncode != 0:
            output = (process.stderr or process.stdout)[-4000:]
            raise RuntimeError(f"git {' '.join(args[:2])} failed: {output}")
        return process.stdout.strip()

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
