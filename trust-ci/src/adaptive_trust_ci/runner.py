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
    def assert_unchanged(self) -> None: ...
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
        started_at = self.now_fn()
        self.store.mark_running(job.job_id, worker_id, now=started_at)
        target_url = f'{self.public_base_url.rstrip("/")}/jobs/{job.job_id}'
        check_run_id = self.github.ensure_check_run(
            job.repository,
            job.head_sha,
            name=self.policy.check_name,
            external_id=job.job_id,
            details_url=target_url,
            started_at=job.started_at or started_at,
        )

        if job.policy_digest != self.policy.digest:
            return self._finish_without_workspace(
                job,
                worker_id,
                check_run_id,
                title='Trust CI policy changed',
                summary=(
                    f'Job policy {job.policy_digest} does not match deployed policy {self.policy.digest}. '
                    'A fresh exact-SHA job is required.'
                ),
                failure_code='policy-digest-mismatch',
                result={
                    'expected_policy_digest': self.policy.digest,
                    'job_policy_digest': job.policy_digest,
                    'check_run_id': check_run_id,
                },
            )

        try:
            verified_holdout_digest = verify_bundle(self.policy.holdout.path, self.policy.holdout.digest)
        except HoldoutError as exc:
            return self._finish_without_workspace(
                job,
                worker_id,
                check_run_id,
                title='External holdout bundle is invalid',
                summary=str(exc),
                failure_code='holdout-integrity-failed',
                result={'holdout_error': str(exc), 'check_run_id': check_run_id},
            )

        existing = self.store.get_attestation(job.job_id)
        if existing is not None:
            payload = verify_attestation(existing, self.signer.public_key_pem())
            self._validate_existing_attestation(job, payload)
            self._complete_check(
                job,
                check_run_id,
                payload.status,
                summary=(
                    'Stored signed attestation replayed without rerunning pull-request code. '
                    f'attestation={payload.attestation_id}; signer={payload.key_id}'
                ),
            )
            finished = self.store.finish(
                job.job_id,
                worker_id,
                payload.status,
                {
                    'attestation': existing.to_dict(),
                    'replayed': True,
                    'check_run_id': check_run_id,
                    'holdout_digest': verified_holdout_digest,
                },
                failure_code=None if payload.status == 'passed' else 'verification-failed',
                now=self.now_fn(),
            )
            return RunOutcome(finished.job_id, finished.status, finished.result)

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
                    self.github.complete_check_run(
                        job.repository,
                        check_run_id,
                        conclusion='action_required',
                        title='Signed human approval required',
                        summary='Missing exact-SHA approval scopes: ' + ', '.join(missing),
                        completed_at=self.now_fn(),
                    )
                    finished = self.store.finish(
                        job.job_id,
                        worker_id,
                        'needs_approval',
                        {
                            'changed_files': list(checkout.changed_files),
                            'required_scopes': sorted(required_scopes),
                            'missing_scopes': missing,
                            'check_run_id': check_run_id,
                            'holdout_digest': verified_holdout_digest,
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

                command_results: list[CommandResult] = [
                    CommandResult(
                        name='holdout-bundle-integrity',
                        status='pass',
                        exit_code=0,
                        duration_seconds=0.0,
                        stdout_tail=f'holdout sha256={verified_holdout_digest}',
                        stderr_tail='',
                        output_sha256=verified_holdout_digest,
                    )
                ]
                environment = self._command_environment(job)

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

                if all(item.status == 'pass' for item in command_results):
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

                lease.check()
                expected_count = 1 + len(self.policy.commands) + len(self.policy.holdout.commands)
                status = 'passed' if len(command_results) == expected_count and all(
                    item.status == 'pass' for item in command_results
                ) else 'failed'
                completed_at = self.now_fn()
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
                    started_at=(job.started_at or started_at).isoformat(),
                    completed_at=completed_at.isoformat(),
                    key_id=self.signer.key_id,
                )
                envelope = sign_attestation(payload, self.signer)
                self.store.record_attestation(job.job_id, envelope)
                summary = '\n'.join(
                    f'{item.name}: {item.status} (exit {item.exit_code})' for item in command_results
                )
                summary += f'\nattestation={payload.attestation_id}; signer={payload.key_id}'
                self._complete_check(job, check_run_id, status, summary=summary)
                details = {
                    'attestation': envelope.to_dict(),
                    'check_run_id': check_run_id,
                    'holdout_digest': verified_holdout_digest,
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

    def publish_dead_job(self, job: Job, error: str) -> None:
        """Publish an App-owned terminal check when durable retries are exhausted."""
        target_url = f'{self.public_base_url.rstrip("/")}/jobs/{job.job_id}'
        check_run_id = self.github.ensure_check_run(
            job.repository,
            job.head_sha,
            name=self.policy.check_name,
            external_id=job.job_id,
            details_url=target_url,
            started_at=job.started_at or self.now_fn(),
        )
        self.github.complete_check_run(
            job.repository,
            check_run_id,
            conclusion='failure',
            title='Trust CI infrastructure retries exhausted',
            summary=error[:65535],
            completed_at=self.now_fn(),
        )

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
            workspace.assert_unchanged()
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

    def _finish_without_workspace(
        self,
        job: Job,
        worker_id: str,
        check_run_id: int,
        *,
        title: str,
        summary: str,
        failure_code: str,
        result: dict,
    ) -> RunOutcome:
        self.github.complete_check_run(
            job.repository,
            check_run_id,
            conclusion='failure',
            title=title,
            summary=summary,
            completed_at=self.now_fn(),
        )
        finished = self.store.finish(
            job.job_id,
            worker_id,
            'failed',
            result,
            failure_code=failure_code,
            now=self.now_fn(),
        )
        return RunOutcome(finished.job_id, finished.status, finished.result)

    def _complete_check(self, job: Job, check_run_id: int, status: str, *, summary: str) -> None:
        passed = status == 'passed'
        self.github.complete_check_run(
            job.repository,
            check_run_id,
            conclusion='success' if passed else 'failure',
            title='Exact SHA passed independent Trust CI' if passed else 'Exact SHA failed independent Trust CI',
            summary=summary or ('Signed attestation recorded.' if passed else 'One or more mandatory checks failed.'),
            completed_at=self.now_fn(),
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
            'TRUST_CI_POLICY_DIGEST': job.policy_digest,
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
