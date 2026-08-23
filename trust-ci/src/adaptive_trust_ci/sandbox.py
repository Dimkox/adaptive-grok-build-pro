from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .models import CommandResult
from .policy import CommandSpec, SandboxSpec


@dataclass
class ContainerExecutor:
    """Execute untrusted repository commands in a separate no-network container."""

    sandbox: SandboxSpec

    def build_argv(
        self,
        *,
        workspace: Path,
        command: tuple[str, ...],
        env: dict[str, str],
        container_name: str,
        workspace_host_path: Path,
        holdout_path: Path | None = None,
        holdout_host_path: Path | None = None,
    ) -> list[str]:
        resolved = workspace.resolve()
        if not resolved.is_dir() or not (resolved / '.git').is_dir():
            raise ValueError(f'sandbox workspace is not an exact git checkout: {resolved}')
        host_workspace = Path(workspace_host_path)
        if not host_workspace.is_absolute():
            raise ValueError('workspace_host_path must be absolute on the Docker daemon host')
        argv = [
            self.sandbox.runtime,
            'run',
            '--rm',
            '--name',
            container_name,
            '--pull',
            'never',
            '--network',
            'none',
            '--read-only',
            '--cap-drop',
            'ALL',
            '--security-opt',
            'no-new-privileges',
            '--pids-limit',
            str(self.sandbox.pids_limit),
            '--memory',
            f'{self.sandbox.memory_mb}m',
            '--cpus',
            _format_float(self.sandbox.cpus),
            '--tmpfs',
            f'/tmp:rw,noexec,nosuid,nodev,size={self.sandbox.tmpfs_mb}m',
            '--tmpfs',
            '/home/ci:rw,noexec,nosuid,nodev,size=128m',
            '--user',
            self.sandbox.user,
            '--volume',
            f'{host_workspace}:/workspace:rw',
            '--volume',
            f'{host_workspace / ".git"}:/workspace/.git:ro',
            '--workdir',
            '/workspace',
        ]
        if (holdout_path is None) != (holdout_host_path is None):
            raise ValueError('holdout local and host paths must be supplied together')
        if holdout_path is not None and holdout_host_path is not None:
            trusted = holdout_path.resolve()
            if not trusted.is_dir():
                raise ValueError(f'holdout directory does not exist: {trusted}')
            if trusted == resolved or resolved in trusted.parents or trusted in resolved.parents:
                raise ValueError('holdout must live outside the pull-request checkout')
            host_holdout = Path(holdout_host_path)
            if not host_holdout.is_absolute():
                raise ValueError('holdout_host_path must be absolute on the Docker daemon host')
            argv.extend(('--volume', f'{host_holdout}:/holdout:ro'))
        for key, value in sorted(env.items()):
            argv.extend(('--env', f'{key}={value}'))
        argv.append(self.sandbox.image)
        argv.extend(command)
        return argv

    def run(
        self,
        spec: CommandSpec,
        workspace: Path,
        env: dict[str, str],
        max_output_bytes: int,
        *,
        workspace_host_path: Path,
        holdout_path: Path | None = None,
        holdout_host_path: Path | None = None,
    ) -> CommandResult:
        started = time.monotonic()
        if shutil.which(self.sandbox.runtime, path=os.environ.get('PATH')) is None:
            return _command_result(
                spec.name,
                127,
                '',
                f'required sandbox runtime not found: {self.sandbox.runtime}',
                time.monotonic() - started,
                max_output_bytes,
            )
        suffix = uuid.uuid4().hex[:8]
        job_fragment = re.sub(r'[^A-Za-z0-9_.-]', '-', env.get('TRUST_CI_JOB_ID', 'job'))[:24]
        command_fragment = re.sub(r'[^A-Za-z0-9_.-]', '-', spec.name)[:24]
        container_name = f'trust-ci-{job_fragment}-{command_fragment}-{suffix}'.lower()
        argv = self.build_argv(
            workspace=workspace,
            command=spec.argv,
            env=env,
            container_name=container_name,
            workspace_host_path=workspace_host_path,
            holdout_path=holdout_path,
            holdout_host_path=holdout_host_path,
        )
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            try:
                process = subprocess.Popen(
                    argv,
                    cwd=workspace,
                    env=_runtime_environment(),
                    stdout=stdout_file,
                    stderr=stderr_file,
                    start_new_session=True,
                )
            except OSError as exc:
                return _command_result(
                    spec.name,
                    127,
                    '',
                    str(exc),
                    time.monotonic() - started,
                    max_output_bytes,
                )
            timed_out = False
            deadline = started + spec.timeout_seconds
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    timed_out = True
                    process.kill()
                    break
                time.sleep(0.2)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            if timed_out:
                _remove_container(self.sandbox.runtime, container_name)
            stdout = _read_temp_text(stdout_file)
            stderr = _read_temp_text(stderr_file)
            if timed_out:
                stderr += f'\ncommand timed out after {spec.timeout_seconds}s'
                exit_code = 124
            else:
                exit_code = int(process.returncode or 0)
            return _command_result(
                spec.name,
                exit_code,
                stdout,
                stderr,
                time.monotonic() - started,
                max_output_bytes,
            )


def _command_result(
    name: str,
    exit_code: int,
    stdout: str,
    stderr: str,
    duration: float,
    max_output_bytes: int,
) -> CommandResult:
    combined = stdout.encode('utf-8', errors='replace') + b'\0' + stderr.encode('utf-8', errors='replace')
    return CommandResult(
        name=name,
        status='pass' if exit_code == 0 else 'fail',
        exit_code=exit_code,
        duration_seconds=duration,
        stdout_tail=_tail(stdout, max_output_bytes // 2),
        stderr_tail=_tail(stderr, max_output_bytes // 2),
        output_sha256=hashlib.sha256(combined).hexdigest(),
    )


def _tail(value: str, limit_bytes: int) -> str:
    data = value.encode('utf-8', errors='replace')
    if len(data) <= limit_bytes:
        return value
    return data[-limit_bytes:].decode('utf-8', errors='replace')


def _read_temp_text(handle) -> str:
    handle.flush()
    handle.seek(0)
    return handle.read().decode('utf-8', errors='replace')


def _runtime_environment() -> dict[str, str]:
    allowed = ('PATH', 'HOME', 'XDG_RUNTIME_DIR', 'DOCKER_HOST', 'DOCKER_CONFIG', 'CONTAINER_HOST')
    return {name: os.environ[name] for name in allowed if name in os.environ}


def _remove_container(runtime: str, name: str) -> None:
    try:
        subprocess.run(
            [runtime, 'rm', '-f', name],
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
            env=_runtime_environment(),
        )
    except OSError:
        return


def _format_float(value: float) -> str:
    return f'{value:.3f}'.rstrip('0').rstrip('.')
