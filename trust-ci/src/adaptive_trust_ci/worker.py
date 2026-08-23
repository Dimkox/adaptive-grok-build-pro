from __future__ import annotations

import signal
import threading
from dataclasses import dataclass

from .github import GitHubClient
from .github_app import GitHubAppAuth
from .models import utc_now
from .policy import Policy
from .runner import JobRunner
from .settings import WorkerSettings
from .signing import Signer
from .store import PostgresStore


@dataclass
class Worker:
    settings: WorkerSettings
    store: PostgresStore
    runner: JobRunner
    stop_event: threading.Event

    @classmethod
    def build(cls, settings: WorkerSettings) -> 'Worker':
        policy = Policy.load(settings.common.policy_path)
        store = PostgresStore(settings.common.database_url)
        signer = Signer.from_private_file(settings.ci_signing_key_path)
        github_auth = GitHubAppAuth(
            app_id=settings.github_app_id,
            installation_id=settings.github_installation_id,
            private_key_path=settings.github_app_private_key_path,
        )
        github = GitHubClient(token_provider=github_auth.installation_token)
        runner = JobRunner(
            store=store,
            policy=policy,
            github=github,
            signer=signer,
            github_token_provider=github_auth.installation_token,
            public_base_url=settings.common.public_base_url,
            workspace_root=settings.workspace_root,
        )
        return cls(settings=settings, store=store, runner=runner, stop_event=threading.Event())

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
                self.runner.policy.lease_seconds,
                now=utc_now(),
            )
            if job is None:
                if once:
                    return 0
                self.stop_event.wait(self.settings.poll_interval_seconds)
                continue
            try:
                self.runner.process(job, self.settings.worker_id)
            except BaseException as exc:
                try:
                    result = self.store.retry(
                        job.job_id,
                        self.settings.worker_id,
                        str(exc),
                        now=utc_now(),
                    )
                    if result.status == 'dead':
                        self.runner.github.post_status(
                            result.repository,
                            result.head_sha,
                            state='error',
                            description='Adaptive Trust CI infrastructure retries exhausted',
                            target_url=f'{self.settings.common.public_base_url}/jobs/{result.job_id}',
                            context=self.runner.policy.status_context,
                        )
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
