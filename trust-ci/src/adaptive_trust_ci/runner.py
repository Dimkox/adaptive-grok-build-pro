from __future__ import annotations

import hashlib
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol

from .github import GitHubClient
from .holdout import HoldoutError, verify_bundle
from .lease import LeaseKeeper
from .models import AttestationPayload, CommandResult, Job, RunOutcome, utc_now
from .policy import CommandSpec, Policy
from .sandbox import ContainerExecutor
from .signing import Signer, sign_attestation, verify_attestation
from .store import Store
from .workspace import GitWorkspace, WorkspaceMutationError

_SECRET_ENV_RE = re.compile(r'(?:TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|PRIVATE|AUTH|COOKIE|SESSION|KEY)', re.I)


class Workspace(Protocol):
    path: Path
    def checkout(self, job: Job): ...
    def reset(self) -> None: ...
    def assert_unmodified(self) -> None: ...
    def cleanup(self) -> None: ...


@dataclass
class JobRunner:
    store: Store
    policy: Policy
    github: GitHubClient
    signer: Signer
    github_token_provider: Callable[[], str]
    public_base_url: str
    workspace_root: Path
    workspace_host_root: Path
    holdout_host_path: Path
    now_fn: Callable[[], datetime] = utc_now
    workspace_factory: Callable[..., Workspace] = GitWorkspace
    executor_factory: Callable[..., ContainerExecutor] = ContainerExecutor

    def process(self, job: Job, worker_id: str) -> RunOutcome:
        now = self.now_fn()
        self.store.mark_running(job.job_id, worker_id, now=now)
        target_url = f'{self.public_base_url.rstrip("/")}/jobs/{job.job_id}'

        if job.policy_digest != self.policy.digest:
            self.github.post_status(
                job.repository,
                job.head_sha,
                state='failure',
                description='Trust CI policy changed; a fresh job is required',
                target_url=target_url,
                context=self.policy.status_context,
            )
            finished = self.store.finish(
                job.job_id,
                worker_id,
                'failed',
                {'expected_policy_digest': self.policy.digest, 'job_policy_digest': job.policy_digest},
                failure_code='policy-digest-mismatch',
                now=self.now_fn(),
            )
            return RunOutcome(finished.job_id, finished.status, finished.result)

        existing = self.store.get_attestation(job.job_id)
        if existing is not None:
            payload = verify_attestation(existing, self.signer.public_key_pem())
            self._validate_existing_attestation(job, payload)
            self._publish_terminal(job, target_url, payload.status, replayed=True)
            finished = self.store.finish(
                job.job_id,
                worker_id,
                payload.status,
                {'attestation': existing.to_dict(), 'replayed': True},
                failure_code=None if payload.status == 'passed' else 'verification-failed',
                now=self.now_fn(),
            )
            return RunOutcome(finished.job_id, finished.status, finished.result)

        self.github.post_status(
            job.repository,
            job.head_sha,
            state='pending',
            description='Adaptive Trust CI is verifying the exact PR SHA',
            target_url=target_url,
            context=self.policy.status_context,
        )

        token = self.github_token_provider().strip()
        if not token:
            raise RuntimeError('GitHub App installation token provider returned empty token')
        workspace = self.workspace_factory(
            job,
            github_token=token,
            checkout_depth=self.policy.checkout_depth,
            base_directory=self.workspace_root,
        )
        try:
            with LeaseKeeper(
                self.store,
                job.job_id,
                worker_id,
                self.policy.lease_seconds,
                now_fn=self.now_fn,
            ) as lease:
                checkout = workspace.checkout(job)
                lease.check()
                required_scopes = self.policy.required_scopes(checkout.changed_files)
                missing = sorted(
                    scope
                    for scope in required_scopes
                    if not self.store.has_valid_approval(
                        job.repository,
                        job.pr_number,
                        job.base_sha,
                        job.head_sha,
                        job.policy_digest,
                        scope,
                        self.now_fn(),
                    )
                )
                if missing:
                    self.github.post_status(
                        job.repository,
                        job.head_sha,
                        state='failure',
                        description=('Human approval required: ' + ', '.join(missing))[:140],
                        target_url=target_url,
                        context=self.policy.status_context,
                    )
                    finished = self.store.finish(
                        job.job_id,
                        worker_id,
                        'needs_approval',
                        {
                            'changed_files': list(checkout.changed_files),
                            'required_scopes': sorted(required_scopes),
                            'missing_scopes': missing,
                        },
                        failure_code='approval-required',
                        now=self.now_fn(),
                    )
                    return RunOutcome(finished.job_id, finished.status, finished.result)

                try:
                    workspace_relative = checkout.path.resolve().relative_to(self.workspace_root.resolve())
                except ValueError as exc:
                    raise RuntimeError('checkout escaped configured workspace root') from exc
                workspace_host_path = self.workspace_host_root / workspace_relative

                command_results: list[CommandResult] = []
                environment = self._command_environment(job)
                try:
                    holdout_digest = verify_bundle(self.policy.holdout.path, self.policy.holdout.digest)
                    command_results.append(
                        CommandResult(
                            name='holdout-bundle-integrity',
                            status='pass',
                            exit_code=0,
                            duration_seconds=0.0,
                            stdout_tail=f'holdout sha256={holdout_digest}',
                            stderr_tail='',
                            output_sha256=holdout_digest,
                        )
                    )
                except HoldoutError as exc:
                    message = str(exc)
                    command_results.append(
                        CommandResult(
                            name='holdout-bundle-integrity',
                            status='fail',
                            exit_code=98,
                            duration_seconds=0.0,
                            stdout_tail='',
                            stderr_tail=message,
                            output_sha256=hashlib.sha256(message.encode()).hexdigest(),
                        )
                    )

                if command_results[-1].status == 'pass':
                    for command in self.policy.commands:
                        lease.check()
                        if not self._run_command(
                            workspace,
                            command,
                            environment,
                            command_results,
                            workspace_host_path=workspace_host_path,
                            holdout_path=None,
                            holdout_host_path=None,
                        ):
                            break

                if all(item.status == 'pass' for item in command_results):
                    for command in self.policy.holdout.commands:
                        lease.check()
                        if not self._run_command(
                            workspace,
                            command,
                            environment,
                            command_results,
                            workspace_host_path=workspace_host_path,
                            holdout_path=self.policy.holdout.path,
                            holdout_host_path=self.holdout_host_path,
                        ):
                            break

                lease.check()
                expected_count = 1 + len(self.policy.commands) + len(self.policy.holdout.commands)
                status = 'passed' if len(command_results) == expected_count and all(
                    item.status == 'pass' for item in command_results
                ) else 'failed'
                completed = self.now_fn()
                started = job.started_at or now
                payload = AttestationPayload(
                    schema_version=1,
                    attestation_id=str(uuid.uuid4()),
                    job_id=job.job_id,
                    repository=job.repository,
                    pr_number=job.pr_number,
                    base_sha=job.base_sha,
                    head_sha=job.head_sha,
                    policy_digest=job.policy_digest,
                    status=status,
                    command_results=tuple(item.attestation_dict() for item in command_results),
                    changed_files=checkout.changed_files,
                    approved_scopes=tuple(sorted(required_scopes)),
                    started_at=started.isoformat(),
                    completed_at=completed.isoformat(),
                    key_id=self.signer.key_id,
                )
                envelope = sign_attestation(payload, self.signer)
                self.store.record_attestation(job.job_id, envelope)
                self._publish_terminal(job, target_url, status, replayed=False)
                details = {
                    'attestation': envelope.to_dict(),
                    'holdout_digest': self.policy.holdout.digest,
                    'commands': [
                        {
                            **item.attestation_dict(),
                            'stdout_tail': item.stdout_tail,
                            'stderr_tail': item.stderr_tail,
                        }
                        for item in command_results
                    ],
                }
                finished = self.store.finish(
                    job.job_id,
                    worker_id,
                    status,
                    details,
                    failure_code=None if status == 'passed' else 'verification-failed',
                    now=self.now_fn(),
                )
                return RunOutcome(finished.job_id, finished.status, finished.result)
        finally:
            workspace.cleanup()

    def _run_command(
        self,
        workspace: Workspace,
        command: CommandSpec,
        environment: dict[str, str],
        command_results: list[CommandResult],
        *,
        workspace_host_path: Path,
        holdout_path: Path | None,
        holdout_host_path: Path | None,
    ) -> bool:
        workspace.reset()
        result = self.executor_factory(self.policy.sandbox).run(
            command,
            workspace.path,
            {**environment, **dict(command.env)},
            self.policy.max_output_bytes,
            workspace_host_path=workspace_host_path,
            holdout_path=holdout_path,
            holdout_host_path=holdout_host_path,
        )
        command_results.append(result)
        try:
            workspace.assert_unmodified()
        except WorkspaceMutationError as exc:
            message = str(exc)
            command_results.append(
                CommandResult(
                    name=f'{command.name}:source-integrity',
                    status='fail',
                    exit_code=97,
                    duration_seconds=0.0,
                    stdout_tail='',
                    stderr_tail=message,
                    output_sha256=hashlib.sha256(message.encode()).hexdigest(),
                )
            )
            workspace.reset()
            return False
        workspace.reset()
        return result.status == 'pass'

    def _publish_terminal(self, job: Job, target_url: str, status: str, *, replayed: bool) -> None:
        if status == 'passed':
            state = 'success'
            description = 'Exact SHA passed independent Trust CI'
        else:
            state = 'failure'
            description = 'Exact SHA failed independent Trust CI'
        if replayed:
            description += ' (signed attestation replayed)'
        self.github.post_status(
            job.repository,
            job.head_sha,
            state=state,
            description=description[:140],
            target_url=target_url,
            context=self.policy.status_context,
        )

    def _validate_existing_attestation(self, job: Job, payload: AttestationPayload) -> None:
        if (
            payload.job_id != job.job_id
            or payload.repository != job.repository
            or payload.pr_number != job.pr_number
            or payload.base_sha != job.base_sha
            or payload.head_sha != job.head_sha
            or payload.policy_digest != job.policy_digest
        ):
            raise RuntimeError('stored attestation does not match the leased job')

    def _command_environment(self, job: Job) -> dict[str, str]:
        environment = {
            'CI': 'true',
            'TRUST_CI': '1',
            'TRUST_CI_JOB_ID': job.job_id,
            'TRUST_CI_REPOSITORY': job.repository,
            'TRUST_CI_PR_NUMBER': str(job.pr_number),
            'TRUST_CI_BASE_SHA': job.base_sha,
            'TRUST_CI_HEAD_SHA': job.head_sha,
            'TRUST_CI_HOLDOUT_DIGEST': self.policy.holdout.digest,
            'HOME': '/home/ci',
            'TMPDIR': '/tmp',
            'PYTHONDONTWRITEBYTECODE': '1',
            'GIT_TERMINAL_PROMPT': '0',
            'NO_COLOR': '1',
        }
        for name in self.policy.allowed_environment:
            if _SECRET_ENV_RE.search(name):
                raise RuntimeError(f'policy attempts to expose a secret-like environment variable: {name}')
            if name in os.environ:
                environment[name] = os.environ[name]
        for command in (*self.policy.commands, *self.policy.holdout.commands):
            for name, _ in command.env:
                if _SECRET_ENV_RE.search(name):
                    raise RuntimeError(f'command policy attempts to expose a secret-like variable: {name}')
        return environment
