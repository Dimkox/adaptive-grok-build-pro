from __future__ import annotations

import hashlib
import base64
import logging
import random
import signal
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

from .github_app import (
    GitHubAppAuth, GitHubAppClient, IncompleteGitHubSearch, RetryableGitHubError,
)
from .models import canonical_json, utc_now
from .policy import Policy
from .provenance import (
    ClaimedMergeFact, MergedPullRequestFact, ProtectedBranchJobRequest, ProvenanceMismatch,
)
from .provenance import ReconciliationWatermark
from .runner import JobRunner
from .settings import SettingsError, WorkerSettings
from .signing import Signer
from .store import PostgresStore


LOGGER = logging.getLogger(__name__)


class ReconciliationIncomplete(RuntimeError):
    """The bounded GitHub result could not prove a complete watermark interval."""


@dataclass
class MergeReconciler:
    """Bounded missed-webhook repair with caller-provided durable persistence."""

    github: object
    load_watermark: Callable[[str], tuple[str, int]]
    save_watermark: Callable[[str, tuple[str, int]], None]
    record_fact: Callable[[MergedPullRequestFact, object], None]
    now_fn: Callable = utc_now
    sleep_fn: Callable[[float], None] = time.sleep
    jitter_fn: Callable[[], float] = random.random
    max_attempts: int = 3
    max_retry_delay_seconds: float = 30.0

    def __post_init__(self) -> None:
        if type(self.max_attempts) is not int or not 1 <= self.max_attempts <= 5:
            raise ValueError('max_attempts must be between 1 and 5')
        if not 0 < self.max_retry_delay_seconds <= 60:
            raise ValueError('invalid maximum retry delay')

    def _retry(self, operation):
        for attempt in range(self.max_attempts):
            try:
                return operation()
            except IncompleteGitHubSearch as exc:
                raise ReconciliationIncomplete(str(exc)) from exc
            except RetryableGitHubError as exc:
                if attempt + 1 >= self.max_attempts:
                    raise
                requested = exc.retry_after_seconds
                delay = requested if requested is not None else 0.25 * (2**attempt)
                delay = min(self.max_retry_delay_seconds, delay + min(0.25, max(0.0, self.jitter_fn())))
                self.sleep_fn(delay)
        raise AssertionError('unreachable')

    def run(
        self,
        *,
        repository: str,
        repository_id: int,
        installation_id: int,
        protected_ref: str,
        max_pages: int = 5,
        per_page: int = 100,
    ) -> int:
        if type(max_pages) is not int or not 1 <= max_pages <= 20:
            raise ValueError('max_pages must be between 1 and 20')
        if type(per_page) is not int or not 1 <= per_page <= 100:
            raise ValueError('per_page must be between 1 and 100')
        watermark = self.load_watermark(repository)
        if not isinstance(watermark, tuple) or len(watermark) != 2:
            raise ValueError('invalid reconciliation watermark')
        initial_watermark = watermark
        query_watermark = watermark[0]
        repaired = 0
        base_ref = protected_ref.removeprefix('refs/heads/')
        batch: list[dict] = []
        complete = False
        for page in range(1, max_pages + 1):
            pulls = self._retry(
                lambda: self.github.list_closed_pulls(
                    repository,
                    updated_after=query_watermark,
                    page=page,
                    per_page=per_page,
                )
            )
            batch.extend(pulls)
            if not pulls:
                complete = True
                break
            if len(pulls) < per_page:
                complete = True
                break
        if not complete:
            raise ReconciliationIncomplete('bounded merge reconciliation result is incomplete')

        deduplicated: dict[tuple[str, int], tuple[bytes, dict]] = {}
        try:
            for pull in batch:
                key = (pull['updated_at'], pull['number'])
                if not isinstance(key[0], str) or type(key[1]) is not int:
                    raise ValueError
                canonical_pull = canonical_json(pull)
                existing = deduplicated.get(key)
                if existing is not None and existing[0] != canonical_pull:
                    raise ValueError
                deduplicated[key] = (canonical_pull, pull)
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError('malformed GitHub reconciliation record') from exc

        for candidate_watermark in sorted(deduplicated):
            if candidate_watermark <= initial_watermark:
                continue
            canonical_pull, pull = deduplicated[candidate_watermark]
            try:
                base = pull['base']
                head = pull['head']
                api_repository = base['repo']
                if (
                    pull.get('merged') is not True
                    or base.get('ref') != base_ref
                    or api_repository.get('id') != repository_id
                    or str(api_repository.get('full_name', '')).lower() != repository.lower()
                ):
                    self.save_watermark(repository, candidate_watermark)
                    continue
                digest = hashlib.sha256(canonical_pull).hexdigest()
                fact = MergedPullRequestFact.create(
                    delivery_id='reconcile:' + digest[:64],
                    payload_sha256=digest,
                    repository_id=repository_id,
                    repository=repository,
                    installation_id=installation_id,
                    pr_number=candidate_watermark[1],
                    head_sha=head['sha'],
                    base_sha=base['sha'],
                    protected_ref=protected_ref,
                    merged_commit_sha=pull['merge_commit_sha'],
                    merged_at=pull['merged_at'],
                    received_at=self.now_fn(),
                )
                corroborated = self._retry(lambda: self.github.corroborate_merge(fact))
                self.record_fact(fact, corroborated)
                repaired += 1
                self.save_watermark(repository, candidate_watermark)
            except (KeyError, TypeError, ValueError) as exc:
                raise RuntimeError('malformed GitHub reconciliation record') from exc
        return repaired


@dataclass
class Worker:
    settings: WorkerSettings
    store: PostgresStore
    runner: JobRunner
    stop_event: threading.Event
    merge_client: object | None = None
    protected_ref: str | None = None

    def process_claimed_merge_fact(self, claimed, request_factory):
        """Execute one fact claimed by Task 3's durable lease implementation."""
        if not isinstance(claimed, ClaimedMergeFact):
            raise TypeError('protected merge processing requires a claimed durable fact')
        if self.merge_client is None or self.protected_ref is None:
            raise RuntimeError('protected merge processing is not configured')
        if claimed.fact.protected_ref != self.protected_ref:
            raise RuntimeError('claimed merge fact targets the wrong protected ref')
        corroborated = self.merge_client.corroborate_merge(claimed.fact)
        if corroborated.merge_fact_id != claimed.fact.merge_fact_id:
            raise RuntimeError('corroborated merge does not match claimed fact')
        request = request_factory(corroborated)
        if not isinstance(request, ProtectedBranchJobRequest) or request.merge != corroborated:
            raise RuntimeError('protected job request does not match corroborated merge')
        return self.runner.run_protected_branch(request)

    def process_next_merge_fact(self, request_factory, *, now) -> bool:
        """Claim, corroborate, persist evidence and complete one durable merge fact."""
        claimed = self.store.claim_merge_fact(
            self.settings.worker_id,
            self.runner.policy.lease_seconds,
            now=now,
        )
        if claimed is None:
            return False
        try:
            evidence = self.process_claimed_merge_fact(claimed, request_factory)
            evidence = self.store.record_or_get_protected_branch_evidence(evidence)
            self.runner.publish_protected_success(evidence)
            self.store.complete_merge_fact(claimed, now=now)
            return True
        except ProvenanceMismatch as exc:
            self.store.fail_merge_fact(claimed, str(exc), now=now)
            LOGGER.error(
                'merge fact permanently denied',
                extra={'merge_fact_id': claimed.fact.merge_fact_id, 'attempt': claimed.attempt},
            )
            raise
        except BaseException as exc:
            self.store.retry_merge_fact(claimed, str(exc), now=now)
            LOGGER.warning(
                'merge fact retry scheduled',
                extra={'merge_fact_id': claimed.fact.merge_fact_id, 'attempt': claimed.attempt},
            )
            raise

    @classmethod
    def build(
        cls,
        settings: WorkerSettings,
    ) -> 'Worker':
        protected_ref = settings.protected_ref
        supply_chain_verifier = _cosign_verifier(settings.cosign_public_key_path)
        policy = Policy.load(settings.common.policy_path)
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
        github = GitHubAppClient(
            token_provider=github_auth.installation_token,
            required_check_name=policy.check_name,
            required_check_app_id=settings.github_app_id,
            expected_protected_ref=protected_ref,
        )
        runner = JobRunner(
            store=store,
            policy=policy,
            github=github,
            signer=signer,
            github_token_provider=github_auth.installation_token,
            public_base_url=settings.common.public_base_url,
            workspace_root=settings.workspace_root,
            workspace_host_root=settings.workspace_host_root,
            holdout_host_path=settings.holdout_host_path,
            github_app_id=settings.github_app_id,
            protected_ref=protected_ref,
            supply_chain_verifier=supply_chain_verifier,
        )
        return cls(
            settings=settings,
            store=store,
            runner=runner,
            stop_event=threading.Event(),
            merge_client=github,
            protected_ref=protected_ref,
        )

    def _protected_request(self, merge) -> ProtectedBranchJobRequest:
        return ProtectedBranchJobRequest(
            job_id=str(uuid.uuid5(uuid.NAMESPACE_URL, 'adaptive-trust-ci:protected:' + merge.merge_fact_id)),
            merge=merge,
            policy_epoch=self.runner.policy.digest,
            supply_chain_dir=str(self.settings.supply_chain_dir),
            artifact_path=str(self.settings.protected_artifact_path),
            started_at=utc_now(),
        )

    def reconcile_merges(self) -> int:
        def load(repository: str) -> tuple[str, int]:
            watermark = self.store.load_reconciliation_watermark(repository)
            if watermark is None:
                return ('1970-01-01T00:00:00Z', 0)
            return (watermark.updated_at, watermark.pr_number)

        def save(repository: str, value: tuple[str, int]) -> None:
            self.store.save_reconciliation_watermark(
                repository, ReconciliationWatermark(value[0], value[1])
            )

        reconciler = MergeReconciler(
            github=self.merge_client, load_watermark=load, save_watermark=save,
            record_fact=lambda fact, _corroborated: (
                self.store.record_merge_fact(fact)
                or self.store.requeue_merge_fact(fact.merge_fact_id, now=utc_now())
            ),
        )
        return reconciler.run(
            repository=self.settings.protected_repository,
            repository_id=self.settings.protected_repository_id,
            installation_id=self.settings.github_installation_id,
            protected_ref=self.settings.protected_ref,
        )

    def run(self, *, once: bool = False) -> int:
        self.store.ping()
        next_reconciliation = 0.0
        while not self.stop_event.is_set():
            if self.settings.common.stopped:
                if once:
                    return 0
                self.stop_event.wait(self.settings.poll_interval_seconds)
                continue
            did_work = False
            try:
                did_work = self.process_next_merge_fact(
                    self._protected_request, now=utc_now()
                )
            except Exception:
                # The claimed fact was durably retried by process_next_merge_fact.
                # Keep normal polling cadence while its durable backoff is active.
                did_work = False
            if once and did_work:
                return 0
            monotonic_now = time.monotonic()
            if monotonic_now >= next_reconciliation:
                try:
                    self.reconcile_merges()
                except Exception:
                    # A failed/incomplete interval deliberately leaves its watermark unchanged.
                    pass
                next_reconciliation = monotonic_now + self.settings.reconciliation_interval_seconds
            job = self.store.claim(
                self.settings.worker_id,
                self.runner.policy.lease_seconds,
                now=utc_now(),
            )
            if job is None:
                if once:
                    return 0
                if not did_work:
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
                        self.runner.publish_dead_job(result, str(exc))
                except Exception:
                    # Lease expiry and the PostgreSQL claim function provide reconciliation.
                    pass
            if once:
                return 0
        return 0


def _cosign_verifier(public_key_path: Path) -> Callable[[Path], bool]:
    def verify(root: Path) -> bool:
        manifest = root / 'supply-chain.manifest.json'
        signature_path = root / 'supply-chain.manifest.json.sig'
        try:
            if public_key_path.is_symlink() or manifest.is_symlink() or signature_path.is_symlink():
                return False
            public_bytes = public_key_path.read_bytes()
            manifest_bytes = manifest.read_bytes()
            signature_text = signature_path.read_text(encoding='ascii').strip()
            if len(public_bytes) > 64 * 1024 or len(manifest_bytes) > 64 * 1024 or len(signature_text) > 16 * 1024:
                return False
            signature = base64.b64decode(signature_text, validate=True)
            key = serialization.load_pem_public_key(public_bytes)
            if isinstance(key, ec.EllipticCurvePublicKey):
                key.verify(signature, manifest_bytes, ec.ECDSA(hashes.SHA256()))
            elif isinstance(key, rsa.RSAPublicKey):
                key.verify(signature, manifest_bytes, padding.PKCS1v15(), hashes.SHA256())
            else:
                return False
            return True
        except (OSError, UnicodeError, ValueError, InvalidSignature):
            return False

    return verify


def install_signal_handlers(worker: Worker) -> None:
    def stop(_signum, _frame) -> None:
        worker.stop_event.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
