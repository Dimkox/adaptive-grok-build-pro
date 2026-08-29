from __future__ import annotations

import signal
import threading
from dataclasses import dataclass
from typing import Callable

from .github import GitHubClient
from .github_app import GitHubAppAuth
from .models import utc_now
from .policy import Policy, PolicyCatalog, PolicyError
from .runner import JobRunner
from .settings import SettingsError, WorkerSettings
from .signing import Signer
from .store import PostgresStore, Store


@dataclass
class Worker:
    settings: WorkerSettings
    store: Store
    catalog: PolicyCatalog
    runner_factory: Callable[[Policy], JobRunner]
    stop_event: threading.Event

    @classmethod
    def build(cls, settings: WorkerSettings) -> 'Worker':
        catalog = PolicyCatalog.load(settings.common.policy_path)
        for policy in catalog.profiles:
            if policy.sandbox.image != settings.runner_image:
                raise SettingsError(
                    'TRUST_CI_RUNNER_IMAGE must exactly match policy.sandbox.image: '
                    f'env={settings.runner_image} policy={policy.sandbox.image}'
                )
        store = PostgresStore(settings.common.database_url)
        signer = Signer.from_private_file(settings.ci_signing_key_path)
        github_auth = GitHubAppAuth(
            app_id=settings.github_app_id,
            installation_id=settings.github_installation_id,
            private_key_path=settings.github_app_private_key_path,
        )
        github = GitHubClient(token_provider=github_auth.installation_token)
        def runner_factory(policy: Policy) -> JobRunner:
            return JobRunner(
                store=store,
                policy=policy,
                github=github,
                signer=signer,
                github_token_provider=github_auth.installation_token,
                public_base_url=settings.common.public_base_url,
                workspace_root=settings.workspace_root,
                workspace_host_root=settings.workspace_host_root,
                holdout_host_path=settings.holdout_host_path,
            )
        return cls(settings=settings, store=store, catalog=catalog, runner_factory=runner_factory, stop_event=threading.Event())

    def run(self, *, once: bool = False) -> int:
        self.store.ping()
        while not self.stop_event.is_set():
            if self.settings.common.stopped:
                if once:
                    return 0
                self.stop_event.wait(self.settings.poll_interval_seconds)
                continue
            job = self.store.claim(
                self.settings.worker_id,
                self.catalog.lease_seconds,
                now=utc_now(),
            )
            if job is None:
                if once:
                    return 0
                self.stop_event.wait(self.settings.poll_interval_seconds)
                continue
            try:
                selected = self.catalog.resolve_bound(job.repository, job.policy_digest)
            except PolicyError:
                try:
                    self.store.finish(
                        job.job_id,
                        self.settings.worker_id,
                        'failed',
                        {
                            'expected_policy_digest': self.catalog.resolve_repository(job.repository).digest
                            if any(p.allows_repository(job.repository) for p in self.catalog.profiles)
                            else None,
                            'job_policy_digest': job.policy_digest,
                        },
                        failure_code='policy-binding-unavailable',
                        now=utc_now(),
                    )
                except Exception:
                    pass
                if once:
                    return 0
                continue
            runner = self.runner_factory(selected)
            try:
                runner.process(job, self.settings.worker_id)
            except BaseException as exc:
                try:
                    result = self.store.retry(
                        job.job_id,
                        self.settings.worker_id,
                        str(exc),
                        now=utc_now(),
                    )
                    if result.status == 'dead':
                        runner.publish_dead_job(result, str(exc))
                except Exception:
                    # Lease expiry and the PostgreSQL claim function provide reconciliation.
                    pass
            if once:
                return 0
        return 0


def install_signal_handlers(worker: Worker) -> None:
    def stop(_signum, _frame) -> None:
        worker.stop_event.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
