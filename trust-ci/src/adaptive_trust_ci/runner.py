from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol

from .github import GitHubClient
from .lease import LeaseKeeper
from .models import AttestationPayload, Job, RunOutcome, utc_now
from .policy import Policy
from .sandbox import ContainerExecutor
from .signing import Signer, sign_attestation, verify_attestation
from .store import Store
from .workspace import GitWorkspace

_SECRET_ENV_RE = re.compile(r"(?:TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|PRIVATE|AUTH|COOKIE|SESSION|KEY)", re.I)


class Workspace(Protocol):
    path: Path
    def checkout(self, job: Job): ...
    def reset(self) -> None: ...
    def cleanup(self) -> None: ...


@dataclass
class JobRunner:
    store: Store
    policy: Policy
    github: GitHubClient
    signer: Signer
    github_token: str
    public_base_url: str
    workspace_root: Path
    now_fn: Callable[[], datetime] = utc_now
    workspace_factory: Callable[..., Workspace] = GitWorkspace
    executor_factory: Callable[..., ContainerExecutor] = ContainerExecutor

    def process(self, job: Job, worker_id: str) -> RunOutcome:
        now = self.now_fn()
        self.store.mark_running(job.job_id, worker_id, now=now)
        target_url = f"{self.public_base_url.rstrip('/')}/jobs/{job.job_id}"

        if job.policy_digest != self.policy.digest:
            self.github.post_status(
                job.repository,
                job.head_sha,
                state="failure",
                description="Trust CI policy changed; a fresh job is required",
                target_url=target_url,
                context=self.policy.status_context,
            )
            finished = self.store.finish(
                job.job_id,
                worker_id,
                "failed",
                {"expected_policy_digest": self.policy.digest, "job_policy_digest": job.policy_digest},
                failure_code="policy-digest-mismatch",
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
                {"attestation": existing.to_dict(), "replayed": True},
                failure_code=None if payload.status == "passed" else "verification-failed",
                now=self.now_fn(),
            )
            return RunOutcome(finished.job_id, finished.status, finished.result)

        self.github.post_status(
            job.repository,
            job.head_sha,
            state="pending",
            description="Adaptive Trust CI is verifying the exact PR SHA",
            target_url=target_url,
            context=self.policy.status_context,
        )

        workspace = self.workspace_factory(
            job,
            github_token=self.github_token,
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
                        state="failure",
                        description=("Human approval required: " + ", ".join(missing))[:140],
                        target_url=target_url,
                        context=self.policy.status_context,
                    )
                    finished = self.store.finish(
                        job.job_id,
                        worker_id,
                        "needs_approval",
                        {
                            "changed_files": list(checkout.changed_files),
                            "required_scopes": sorted(required_scopes),
                            "missing_scopes": missing,
                        },
                        failure_code="approval-required",
                        now=self.now_fn(),
                    )
                    return RunOutcome(finished.job_id, finished.status, finished.result)

                command_results = []
                environment = self._command_environment(job)
                for command in self.policy.commands:
                    lease.check()
                    workspace.reset()
                    result = self.executor_factory(self.policy.sandbox).run(
                        command,
                        checkout.path,
                        {**environment, **dict(command.env)},
                        self.policy.max_output_bytes,
                    )
                    workspace.reset()
                    command_results.append(result)
                    if result.status == "fail":
                        break

                lease.check()
                status = "passed" if len(command_results) == len(self.policy.commands) and all(
                    item.status == "pass" for item in command_results
                ) else "failed"
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
                    "attestation": envelope.to_dict(),
                    "commands": [
                        {
                            **item.attestation_dict(),
                            "stdout_tail": item.stdout_tail,
                            "stderr_tail": item.stderr_tail,
                        }
                        for item in command_results
                    ],
                }
                finished = self.store.finish(
                    job.job_id,
                    worker_id,
                    status,
                    details,
                    failure_code=None if status == "passed" else "verification-failed",
                    now=self.now_fn(),
                )
                return RunOutcome(finished.job_id, finished.status, finished.result)
        finally:
            workspace.cleanup()

    def _publish_terminal(self, job: Job, target_url: str, status: str, *, replayed: bool) -> None:
        if status == "passed":
            state = "success"
            description = "Exact SHA passed independent Trust CI"
        else:
            state = "failure"
            description = "Exact SHA failed independent Trust CI"
        if replayed:
            description += " (signed attestation replayed)"
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
            raise RuntimeError("stored attestation does not match the leased job")

    def _command_environment(self, job: Job) -> dict[str, str]:
        environment = {
            "CI": "true",
            "TRUST_CI": "1",
            "TRUST_CI_JOB_ID": job.job_id,
            "TRUST_CI_REPOSITORY": job.repository,
            "TRUST_CI_PR_NUMBER": str(job.pr_number),
            "TRUST_CI_BASE_SHA": job.base_sha,
            "TRUST_CI_HEAD_SHA": job.head_sha,
            "HOME": "/home/ci",
            "TMPDIR": "/tmp",
            "PYTHONDONTWRITEBYTECODE": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "NO_COLOR": "1",
        }
        for name in self.policy.allowed_environment:
            if _SECRET_ENV_RE.search(name):
                raise RuntimeError(f"policy attempts to expose a secret-like environment variable: {name}")
            if name in os.environ:
                environment[name] = os.environ[name]
        for command in self.policy.commands:
            for name, _ in command.env:
                if _SECRET_ENV_RE.search(name):
                    raise RuntimeError(f"command policy attempts to expose a secret-like variable: {name}")
        return environment
