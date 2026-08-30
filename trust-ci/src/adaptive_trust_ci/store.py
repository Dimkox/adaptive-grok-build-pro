from __future__ import annotations

import copy
import hashlib
import json
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from .models import (
    ApprovalEnvelope,
    ApprovalPayload,
    AttestationEnvelope,
    Job,
    JobRequest,
    PromotionEnvelope,
    PromotionEvent,
    PromotionExpectedBinding,
    ProtectedBranchAttestationEnvelope,
    ProtectedBranchAttestationPayload,
    parse_datetime,
    require_digest,
    require_uuid_v1_5,
    utc_now,
)
from .provenance import (
    ClaimedMergeFact,
    DeliveryConflict,
    MergedPullRequestFact,
    ReconciliationWatermark,
    rfc3339_z,
)


class ReplayError(RuntimeError):
    pass


class IdempotencyConflict(ReplayError):
    pass


class PromotionReplay(ReplayError):
    pass


class ExactOperationReplay(ReplayError):
    pass


class ProvenanceMismatch(RuntimeError):
    pass


@dataclass(frozen=True)
class PromotionRecord:
    envelope: PromotionEnvelope
    idempotency_key: str
    request_sha256: str
    accepted_at: datetime

    @property
    def promotion_id(self) -> str:
        return self.envelope.payload.promotion_id

    def public_dict(self, *, idempotent_replay: bool = False) -> dict[str, Any]:
        payload = self.envelope.payload
        return {
            "promotion_id": payload.promotion_id,
            "repository": payload.repository,
            "merged_commit_sha": payload.merged_commit_sha,
            "artifact_sha256": payload.artifact_sha256,
            "target_environment": payload.target_environment,
            "policy_epoch": payload.policy_epoch,
            "source_attestation_id": payload.source_attestation_id,
            "expires_at": payload.expires_at,
            "consumed": False,
            "idempotent_replay": idempotent_replay,
        }


@dataclass(frozen=True)
class PromotionConsumption:
    promotion_id: str
    operation_id: str
    expected: PromotionExpectedBinding
    consumed_at: datetime


class Store(Protocol):
    def ping(self) -> None: ...
    def enqueue(self, request: JobRequest, policy_digest: str, max_attempts: int, *, now: datetime) -> tuple[Job, bool]: ...
    def cancel_pr(self, repository: str, pr_number: int, *, now: datetime) -> int: ...
    def claim(self, worker_id: str, lease_seconds: int, *, now: datetime) -> Job | None: ...
    def mark_running(self, job_id: str, worker_id: str, *, now: datetime) -> Job: ...
    def heartbeat(self, job_id: str, worker_id: str, lease_seconds: int, *, now: datetime) -> Job: ...
    def finish(self, job_id: str, worker_id: str, status: str, result: dict[str, Any], *, failure_code: str | None = None, now: datetime) -> Job: ...
    def retry(self, job_id: str, worker_id: str, error: str, *, now: datetime) -> Job: ...
    def get_job(self, job_id: str) -> Job: ...
    def get_job_for_sha(self, repository: str, head_sha: str) -> Job | None: ...
    def record_approval(self, payload: ApprovalPayload, envelope: ApprovalEnvelope, *, now: datetime) -> None: ...
    def has_valid_approval(self, repository: str, pr_number: int, base_sha: str, head_sha: str, policy_digest: str, scope: str, now: datetime) -> bool: ...
    def requeue_for_approval(self, repository: str, head_sha: str, *, now: datetime) -> int: ...
    def record_attestation(self, job_id: str, envelope: AttestationEnvelope) -> None: ...
    def get_attestation(self, job_id: str) -> AttestationEnvelope | None: ...
    def record_merge_fact(self, fact: MergedPullRequestFact) -> bool: ...
    def claim_merge_fact(self, worker_id: str, lease_seconds: int, *, now: datetime) -> ClaimedMergeFact | None: ...
    def retry_merge_fact(self, claimed: ClaimedMergeFact, error: str, *, now: datetime) -> None: ...
    def fail_merge_fact(self, claimed: ClaimedMergeFact, error: str, *, now: datetime) -> None: ...
    def requeue_merge_fact(self, merge_fact_id: str, *, now: datetime) -> bool: ...
    def complete_merge_fact(self, claimed: ClaimedMergeFact, *, now: datetime) -> None: ...
    def load_reconciliation_watermark(self, repository: str) -> ReconciliationWatermark | None: ...
    def save_reconciliation_watermark(self, repository: str, watermark: ReconciliationWatermark) -> None: ...
    def record_protected_branch_evidence(self, envelope: ProtectedBranchAttestationEnvelope) -> bool: ...
    def record_or_get_protected_branch_evidence(self, envelope: ProtectedBranchAttestationEnvelope) -> ProtectedBranchAttestationEnvelope: ...
    def activate_policy(self, policy_epoch: str) -> None: ...
    def get_active_policy_epoch(self) -> str | None: ...
    def accept_promotion(self, envelope: PromotionEnvelope, idempotency_key: str, correlation_id: str, now: datetime) -> tuple[PromotionRecord, bool]: ...
    def consume_promotion(self, promotion_id: str, expected: PromotionExpectedBinding, operation_id: str, now: datetime) -> PromotionConsumption: ...
    def get_promotion_consumption(self, promotion_id: str, operation_id: str) -> PromotionConsumption | None: ...
    def record_deployment_terminal(self, promotion_id: str, operation_id: str, event_type: str, *, reason_code: str, details: dict[str, Any], now: datetime) -> PromotionEvent: ...
    def list_promotion_events(self, promotion_id: str, *, limit: int) -> tuple[PromotionEvent, ...]: ...
    def record_promotion_rejection(self, event: PromotionEvent) -> None: ...


class MemoryStore:
    """Thread-safe test implementation with the same transition rules as PostgreSQL."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._idempotency: dict[str, str] = {}
        self._approvals: dict[str, tuple[ApprovalPayload, ApprovalEnvelope]] = {}
        self._nonces: set[str] = set()
        self._attestations: dict[str, AttestationEnvelope] = {}
        self._merge_facts: dict[str, MergedPullRequestFact] = {}
        self._merge_delivery_digests: dict[str, str] = {}
        self._merge_queue: dict[str, dict[str, Any]] = {}
        self._reconciliation_watermarks: dict[str, ReconciliationWatermark] = {}
        self._protected_evidence: dict[str, ProtectedBranchAttestationEnvelope] = {}
        self._active_policy_epoch: str | None = None
        self._promotions: dict[str, PromotionRecord] = {}
        self._promotion_idempotency: dict[str, tuple[str, str]] = {}
        self._promotion_nonces: set[str] = set()
        self._promotion_payload_digests: set[str] = set()
        self._promotion_consumptions: dict[str, PromotionConsumption] = {}
        self._promotion_operations: set[str] = set()
        self._promotion_events: list[PromotionEvent] = []
        self._lock = threading.RLock()

    def ping(self) -> None:
        return None

    def enqueue(
        self,
        request: JobRequest,
        policy_digest: str,
        max_attempts: int,
        *,
        now: datetime,
    ) -> tuple[Job, bool]:
        with self._lock:
            key = request.idempotency_key(policy_digest)
            existing_id = self._idempotency.get(key)
            if existing_id:
                return copy.deepcopy(self._jobs[existing_id]), False
            for job in self._jobs.values():
                if (
                    job.repository == request.repository
                    and job.pr_number == request.pr_number
                    and job.head_sha != request.head_sha
                    and job.status in {"queued", "leased", "running", "needs_approval"}
                ):
                    job.status = "cancelled"
                    job.failure_code = "superseded-head"
                    job.lease_owner = None
                    job.lease_expires_at = None
                    job.updated_at = now
                    job.finished_at = now
            job = Job(
                job_id=str(uuid.uuid4()),
                repository=request.repository,
                pr_number=request.pr_number,
                base_sha=request.base_sha,
                head_sha=request.head_sha,
                head_ref=request.head_ref,
                base_ref=request.base_ref,
                pipeline=request.pipeline,
                policy_digest=policy_digest,
                idempotency_key=key,
                max_attempts=max_attempts,
                created_at=now,
                updated_at=now,
            )
            self._jobs[job.job_id] = job
            self._idempotency[key] = job.job_id
            return copy.deepcopy(job), True

    def cancel_pr(self, repository: str, pr_number: int, *, now: datetime) -> int:
        with self._lock:
            count = 0
            for job in self._jobs.values():
                if job.repository == repository and job.pr_number == pr_number and job.status in {
                    "queued",
                    "leased",
                    "running",
                    "needs_approval",
                }:
                    job.status = "cancelled"
                    job.failure_code = "pull-request-closed"
                    job.lease_owner = None
                    job.lease_expires_at = None
                    job.updated_at = now
                    job.finished_at = now
                    count += 1
            return count

    def claim(self, worker_id: str, lease_seconds: int, *, now: datetime) -> Job | None:
        if not worker_id.strip() or lease_seconds <= 0:
            raise ValueError("valid worker_id and lease_seconds are required")
        with self._lock:
            candidates = sorted(self._jobs.values(), key=lambda item: item.created_at)
            for job in candidates:
                reclaimable = job.status in {"leased", "running"} and job.lease_expires_at is not None and job.lease_expires_at < now
                if job.attempts >= job.max_attempts:
                    if reclaimable:
                        job.status = "dead"
                        job.failure_code = "attempts-exhausted"
                        job.updated_at = now
                        job.finished_at = now
                    continue
                if job.status != "queued" and not reclaimable:
                    continue
                job.status = "leased"
                job.attempts += 1
                job.lease_owner = worker_id
                job.lease_expires_at = now + timedelta(seconds=lease_seconds)
                job.started_at = job.started_at or now
                job.updated_at = now
                return copy.deepcopy(job)
            return None

    def mark_running(self, job_id: str, worker_id: str, *, now: datetime) -> Job:
        with self._lock:
            job = self._owned(job_id, worker_id, {"leased"}, now)
            job.status = "running"
            job.updated_at = now
            return copy.deepcopy(job)

    def heartbeat(self, job_id: str, worker_id: str, lease_seconds: int, *, now: datetime) -> Job:
        with self._lock:
            job = self._owned(job_id, worker_id, {"leased", "running"}, now)
            job.lease_expires_at = now + timedelta(seconds=lease_seconds)
            job.updated_at = now
            return copy.deepcopy(job)

    def finish(
        self,
        job_id: str,
        worker_id: str,
        status: str,
        result: dict[str, Any],
        *,
        failure_code: str | None = None,
        now: datetime,
    ) -> Job:
        if status not in {"passed", "failed", "needs_approval", "cancelled", "dead"}:
            raise ValueError(f"invalid terminal status: {status}")
        with self._lock:
            job = self._owned(job_id, worker_id, {"leased", "running"}, now)
            job.status = status
            job.result = copy.deepcopy(result)
            job.failure_code = failure_code
            job.lease_owner = None
            job.lease_expires_at = None
            job.updated_at = now
            job.finished_at = now
            return copy.deepcopy(job)

    def retry(self, job_id: str, worker_id: str, error: str, *, now: datetime) -> Job:
        with self._lock:
            job = self._owned(job_id, worker_id, {"leased", "running"}, now)
            job.result = {"infrastructure_error": error[:4000]}
            job.lease_owner = None
            job.lease_expires_at = None
            job.updated_at = now
            if job.attempts >= job.max_attempts:
                job.status = "dead"
                job.failure_code = "infrastructure-attempts-exhausted"
                job.finished_at = now
            else:
                job.status = "queued"
                job.failure_code = "retryable-infrastructure-error"
            return copy.deepcopy(job)

    def get_job(self, job_id: str) -> Job:
        with self._lock:
            try:
                return copy.deepcopy(self._jobs[job_id])
            except KeyError as exc:
                raise KeyError(job_id) from exc

    def get_job_for_sha(self, repository: str, head_sha: str) -> Job | None:
        with self._lock:
            matches = [job for job in self._jobs.values() if job.repository == repository and job.head_sha == head_sha]
            if not matches:
                return None
            return copy.deepcopy(max(matches, key=lambda item: item.created_at))

    def record_approval(self, payload: ApprovalPayload, envelope: ApprovalEnvelope, *, now: datetime) -> None:
        del now
        with self._lock:
            if payload.approval_id in self._approvals or payload.nonce in self._nonces:
                raise ReplayError("approval ID or nonce has already been used")
            self._approvals[payload.approval_id] = (payload, envelope)
            self._nonces.add(payload.nonce)

    def has_valid_approval(
        self,
        repository: str,
        pr_number: int,
        base_sha: str,
        head_sha: str,
        policy_digest: str,
        scope: str,
        now: datetime,
    ) -> bool:
        with self._lock:
            for payload, _ in self._approvals.values():
                if (
                    payload.repository == repository
                    and payload.pr_number == pr_number
                    and payload.base_sha == base_sha
                    and payload.head_sha == head_sha
                    and payload.policy_digest == policy_digest
                    and payload.scope == scope
                    and parse_datetime(payload.issued_at) <= now < parse_datetime(payload.expires_at)
                ):
                    return True
            return False

    def requeue_for_approval(self, repository: str, head_sha: str, *, now: datetime) -> int:
        with self._lock:
            count = 0
            for job in self._jobs.values():
                if job.repository == repository and job.head_sha == head_sha and job.status == "needs_approval":
                    job.status = "queued"
                    job.failure_code = None
                    job.result = {}
                    job.finished_at = None
                    job.updated_at = now
                    count += 1
            return count

    def record_attestation(self, job_id: str, envelope: AttestationEnvelope) -> None:
        with self._lock:
            if job_id in self._attestations:
                raise ReplayError("attestation already exists for job")
            self._attestations[job_id] = envelope

    def get_attestation(self, job_id: str) -> AttestationEnvelope | None:
        with self._lock:
            value = self._attestations.get(job_id)
            return copy.deepcopy(value) if value is not None else None

    def record_merge_fact(self, fact: MergedPullRequestFact) -> bool:
        if not isinstance(fact, MergedPullRequestFact):
            raise TypeError("merge fact is required")
        with self._lock:
            existing_digest = self._merge_delivery_digests.get(fact.delivery_id)
            if existing_digest is not None:
                if existing_digest != fact.payload_sha256:
                    raise DeliveryConflict("delivery digest conflict")
                return False
            self._merge_delivery_digests[fact.delivery_id] = fact.payload_sha256
            if fact.merge_fact_id in self._merge_facts:
                return False
            self._merge_facts[fact.merge_fact_id] = fact
            self._merge_queue[fact.merge_fact_id] = {
                "status": "pending",
                "attempt": 0,
                "claim_id": None,
                "lease_owner": None,
                "lease_expires_at": None,
                "next_attempt_at": parse_datetime(fact.received_at),
                "last_error": None,
            }
            return True

    def claim_merge_fact(
        self, worker_id: str, lease_seconds: int, *, now: datetime
    ) -> ClaimedMergeFact | None:
        if not worker_id.strip() or lease_seconds <= 0:
            raise ValueError("valid worker_id and lease_seconds are required")
        with self._lock:
            for fact in sorted(self._merge_facts.values(), key=lambda item: item.received_at):
                queue = self._merge_queue[fact.merge_fact_id]
                expired = (
                    queue["status"] == "leased"
                    and queue["lease_expires_at"] is not None
                    and queue["lease_expires_at"] < now
                )
                if queue["status"] != "pending" and not expired:
                    continue
                if queue["status"] == "pending" and queue["next_attempt_at"] > now:
                    continue
                if queue["attempt"] >= 20:
                    queue["status"] = "dead"
                    continue
                queue["status"] = "leased"
                queue["attempt"] += 1
                queue["claim_id"] = str(uuid.uuid4())
                queue["lease_owner"] = worker_id
                queue["lease_expires_at"] = now + timedelta(seconds=lease_seconds)
                return ClaimedMergeFact(
                    fact=copy.deepcopy(fact),
                    claim_id=queue["claim_id"],
                    attempt=queue["attempt"],
                )
            return None

    def retry_merge_fact(
        self, claimed: ClaimedMergeFact, error: str, *, now: datetime
    ) -> None:
        with self._lock:
            queue = self._owned_merge_claim(claimed, now)
            queue["status"] = "pending" if queue["attempt"] < 20 else "dead"
            queue["last_error"] = (
                ('retry-exhausted:' if queue["status"] == "dead" else '') + str(error)
            )[:512]
            queue["claim_id"] = None
            queue["lease_owner"] = None
            queue["lease_expires_at"] = None
            queue["next_attempt_at"] = now + timedelta(
                seconds=min(300, 5 * (2 ** max(0, claimed.attempt - 1)))
            )

    def requeue_merge_fact(self, merge_fact_id: str, *, now: datetime) -> bool:
        with self._lock:
            queue = self._merge_queue.get(merge_fact_id)
            if (
                queue is None or queue["status"] != "dead"
                or not str(queue["last_error"] or '').startswith(
                    ('attempts-exhausted', 'retry-exhausted:')
                )
            ):
                return False
            queue.update({
                "status": "pending", "attempt": 0, "claim_id": None,
                "lease_owner": None, "lease_expires_at": None,
                "next_attempt_at": now, "last_error": "requeued-by-reconciliation",
            })
            return True

    def fail_merge_fact(
        self, claimed: ClaimedMergeFact, error: str, *, now: datetime
    ) -> None:
        with self._lock:
            queue = self._owned_merge_claim(claimed, now)
            queue.update({
                "status": "dead", "claim_id": None, "lease_owner": None,
                "lease_expires_at": None, "last_error": ('permanent:' + str(error))[:512],
            })

    def complete_merge_fact(self, claimed: ClaimedMergeFact, *, now: datetime) -> None:
        with self._lock:
            queue = self._owned_merge_claim(claimed, now)
            queue["status"] = "completed"
            queue["claim_id"] = None
            queue["lease_owner"] = None
            queue["lease_expires_at"] = None

    def load_reconciliation_watermark(
        self, repository: str
    ) -> ReconciliationWatermark | None:
        with self._lock:
            return copy.deepcopy(self._reconciliation_watermarks.get(repository))

    def save_reconciliation_watermark(
        self, repository: str, watermark: ReconciliationWatermark
    ) -> None:
        if not repository or not isinstance(watermark, ReconciliationWatermark):
            raise ValueError("valid repository and watermark are required")
        with self._lock:
            current = self._reconciliation_watermarks.get(repository)
            if current is not None and _watermark_key(watermark) < _watermark_key(current):
                raise ValueError("reconciliation watermark cannot move backwards")
            self._reconciliation_watermarks[repository] = watermark

    def record_protected_branch_evidence(
        self, envelope: ProtectedBranchAttestationEnvelope
    ) -> bool:
        if not isinstance(envelope, ProtectedBranchAttestationEnvelope):
            raise TypeError("protected-branch evidence is required")
        with self._lock:
            created = envelope.payload.source_attestation_id not in self._protected_evidence
            stored = self.record_or_get_protected_branch_evidence(envelope)
            return created and stored == envelope

    def record_or_get_protected_branch_evidence(
        self, envelope: ProtectedBranchAttestationEnvelope
    ) -> ProtectedBranchAttestationEnvelope:
        if not isinstance(envelope, ProtectedBranchAttestationEnvelope):
            raise TypeError("protected-branch evidence is required")
        payload = envelope.payload
        exact_tuple = (
            payload.repository, payload.protected_ref, payload.merged_commit_sha,
            payload.policy_epoch, payload.artifact_sha256,
        )
        with self._lock:
            fact = self._merge_facts.get(payload.merge_fact_id)
            if fact is None or (
                fact.repository, fact.protected_ref, fact.merged_commit_sha,
            ) != (payload.repository, payload.protected_ref, payload.merged_commit_sha):
                raise RuntimeError("protected-branch provenance mismatch")
            for existing in self._protected_evidence.values():
                existing_payload = existing.payload
                existing_tuple = (
                    existing_payload.repository, existing_payload.protected_ref,
                    existing_payload.merged_commit_sha, existing_payload.policy_epoch,
                    existing_payload.artifact_sha256,
                )
                if existing_tuple != exact_tuple:
                    continue
                if _protected_evidence_identity(existing_payload) != _protected_evidence_identity(payload):
                    raise ReplayError("protected-branch exact tuple conflict")
                return copy.deepcopy(existing)
            existing = self._protected_evidence.get(payload.source_attestation_id)
            if existing is not None:
                raise ReplayError("protected-branch evidence identity conflict")
            self._protected_evidence[payload.source_attestation_id] = envelope
            return copy.deepcopy(envelope)

    def accept_promotion(
        self,
        envelope: PromotionEnvelope,
        idempotency_key: str,
        correlation_id: str,
        now: datetime,
    ) -> tuple[PromotionRecord, bool]:
        _require_store_text(idempotency_key, "idempotency_key", 16, 128)
        _require_store_text(correlation_id, "correlation_id", 1, 128)
        if not isinstance(envelope, PromotionEnvelope):
            raise TypeError("promotion envelope is required")
        request_sha256 = hashlib.sha256(envelope.canonical_bytes()).hexdigest()
        payload_sha256 = hashlib.sha256(envelope.payload.canonical_bytes()).hexdigest()
        payload = envelope.payload
        with self._lock:
            if self._active_policy_epoch != payload.policy_epoch:
                raise ProvenanceMismatch("promotion current policy mismatch")
            existing_request = self._promotion_idempotency.get(idempotency_key)
            if existing_request is not None:
                existing_digest, promotion_id = existing_request
                if existing_digest != request_sha256:
                    raise IdempotencyConflict("idempotency key conflict")
                return copy.deepcopy(self._promotions[promotion_id]), False
            if (
                payload.promotion_id in self._promotions
                or payload.nonce in self._promotion_nonces
                or payload_sha256 in self._promotion_payload_digests
            ):
                raise PromotionReplay("promotion ID, nonce or payload has already been used")
            evidence = self._protected_evidence.get(payload.source_attestation_id)
            if evidence is None or _promotion_binding(payload) != _evidence_binding(evidence):
                raise ProvenanceMismatch("promotion provenance mismatch or unavailable")
            record = PromotionRecord(
                envelope=envelope,
                idempotency_key=idempotency_key,
                request_sha256=request_sha256,
                accepted_at=now,
            )
            event = _promotion_event(
                "promotion.accepted", record, correlation_id, now, outcome="accepted"
            )
            self._promotions[payload.promotion_id] = record
            self._promotion_idempotency[idempotency_key] = (
                request_sha256,
                payload.promotion_id,
            )
            self._promotion_nonces.add(payload.nonce)
            self._promotion_payload_digests.add(payload_sha256)
            self._promotion_events.append(event)
            return copy.deepcopy(record), True

    def activate_policy(self, policy_epoch: str) -> None:
        selected = require_digest(policy_epoch, "policy_epoch")
        with self._lock:
            self._active_policy_epoch = selected

    def get_active_policy_epoch(self) -> str | None:
        with self._lock:
            return self._active_policy_epoch

    def consume_promotion(
        self,
        promotion_id: str,
        expected: PromotionExpectedBinding,
        operation_id: str,
        now: datetime,
    ) -> PromotionConsumption:
        require_uuid_v1_5(promotion_id, "promotion_id")
        require_uuid_v1_5(operation_id, "operation_id")
        if not isinstance(expected, PromotionExpectedBinding):
            raise TypeError("expected promotion binding is required")
        with self._lock:
            record = self._promotions.get(promotion_id)
            if record is None:
                raise RuntimeError("promotion is unavailable")
            existing_consumption = self._promotion_consumptions.get(promotion_id)
            if (
                existing_consumption is not None
                and existing_consumption.operation_id == operation_id
            ):
                raise ExactOperationReplay(
                    "promotion was consumed by this exact operation"
                )
            if existing_consumption is not None or operation_id in self._promotion_operations:
                raise ReplayError("promotion or operation has already been consumed")
            payload = record.envelope.payload
            if self._active_policy_epoch != payload.policy_epoch:
                raise ProvenanceMismatch("promotion current policy mismatch")
            if _promotion_binding(payload) != _expected_binding(expected):
                raise RuntimeError("promotion tuple mismatch")
            if not (parse_datetime(payload.issued_at) <= now < parse_datetime(payload.expires_at)):
                raise RuntimeError("promotion is not current")
            consumption = PromotionConsumption(
                promotion_id=promotion_id,
                operation_id=operation_id,
                expected=expected,
                consumed_at=now,
            )
            event = _promotion_event(
                "promotion.consumed",
                record,
                operation_id,
                now,
                outcome="consumed",
                operation_id=operation_id,
            )
            self._promotion_consumptions[promotion_id] = consumption
            self._promotion_operations.add(operation_id)
            self._promotion_events.append(event)
            return copy.deepcopy(consumption)

    def list_promotion_events(
        self, promotion_id: str, *, limit: int
    ) -> tuple[PromotionEvent, ...]:
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("event limit must be between 1 and 1000")
        with self._lock:
            return tuple(
                copy.deepcopy(event)
                for event in self._promotion_events
                if event.promotion_id == promotion_id
            )[:limit]

    def get_promotion_consumption(
        self, promotion_id: str, operation_id: str
    ) -> PromotionConsumption | None:
        require_uuid_v1_5(promotion_id, "promotion_id")
        require_uuid_v1_5(operation_id, "operation_id")
        with self._lock:
            consumption = self._promotion_consumptions.get(promotion_id)
            if consumption is None or consumption.operation_id != operation_id:
                return None
            return copy.deepcopy(consumption)

    def record_deployment_terminal(
        self, promotion_id: str, operation_id: str, event_type: str, *,
        reason_code: str, details: dict[str, Any], now: datetime,
    ) -> PromotionEvent:
        require_uuid_v1_5(promotion_id, "promotion_id")
        require_uuid_v1_5(operation_id, "operation_id")
        outcomes = {
            "deployment.completed": "completed",
            "deployment.failed": "failed",
            "deployment.reconciled": "reconciled",
        }
        if event_type not in outcomes:
            raise ValueError("invalid terminal deployment event type")
        with self._lock:
            consumption = self._promotion_consumptions.get(promotion_id)
            record = self._promotions.get(promotion_id)
            if consumption is None or record is None or consumption.operation_id != operation_id:
                raise RuntimeError("terminal deployment event requires exact consumption")
            if any(
                event.promotion_id == promotion_id
                and event.operation_id == operation_id
                and event.event_type in outcomes
                for event in self._promotion_events
            ):
                raise RuntimeError("terminal deployment event already exists")
            payload = record.envelope.payload
            event = PromotionEvent(
                schema_version=1, event_id=str(uuid.uuid4()), event_type=event_type,
                occurred_at=rfc3339_z(now.replace(microsecond=0)),
                promotion_id=promotion_id, correlation_id=operation_id,
                operation_id=operation_id, actor=payload.actor, key_id=payload.key_id,
                repository=payload.repository, merged_commit_sha=payload.merged_commit_sha,
                artifact_sha256=payload.artifact_sha256,
                target_environment=payload.target_environment,
                policy_epoch=payload.policy_epoch, outcome=outcomes[event_type],
                reason_code=reason_code, details=details,
            )
            self._promotion_events.append(event)
            return copy.deepcopy(event)

    def record_promotion_rejection(self, event: PromotionEvent) -> None:
        if (
            not isinstance(event, PromotionEvent)
            or event.event_type != "promotion.rejected"
            or event.outcome != "rejected"
            or event.promotion_id is not None
        ):
            raise ValueError("bounded promotion rejection event is required")
        with self._lock:
            self._promotion_events.append(copy.deepcopy(event))

    def _owned_merge_claim(
        self, claimed: ClaimedMergeFact, now: datetime
    ) -> dict[str, Any]:
        if not isinstance(claimed, ClaimedMergeFact):
            raise TypeError("claimed merge fact is required")
        queue = self._merge_queue.get(claimed.fact.merge_fact_id)
        if (
            queue is None
            or queue["status"] != "leased"
            or queue["claim_id"] != claimed.claim_id
            or queue["attempt"] != claimed.attempt
            or queue["lease_expires_at"] is None
            or queue["lease_expires_at"] < now
        ):
            raise RuntimeError("worker does not own a live merge fact lease")
        return queue

    def _owned(self, job_id: str, worker_id: str, statuses: set[str], now: datetime) -> Job:
        try:
            job = self._jobs[job_id]
        except KeyError as exc:
            raise KeyError(job_id) from exc
        if job.status not in statuses or job.lease_owner != worker_id:
            raise RuntimeError("worker does not own the job lease")
        if job.lease_expires_at is None or job.lease_expires_at < now:
            raise RuntimeError("job lease has expired")
        return job


class PostgresStore:
    def __init__(self, database_url: str) -> None:
        if not database_url.strip():
            raise ValueError("database_url is required")
        self.database_url = database_url

    def _connect(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("psycopg is required for PostgreSQL durable state") from exc
        return psycopg.connect(self.database_url, autocommit=False, row_factory=dict_row)

    def ping(self) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

    def migrate(self, sql: str) -> None:
        with self._connect() as connection:
            connection.execute(sql)
            connection.commit()

    def enqueue(
        self,
        request: JobRequest,
        policy_digest: str,
        max_attempts: int,
        *,
        now: datetime,
    ) -> tuple[Job, bool]:
        key = request.idempotency_key(policy_digest)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE trust_ci_jobs
                SET status = 'cancelled', failure_code = 'superseded-head',
                    lease_owner = NULL, lease_expires_at = NULL,
                    updated_at = %s, finished_at = %s
                WHERE repository = %s AND pr_number = %s AND head_sha <> %s
                  AND status IN ('queued', 'leased', 'running', 'needs_approval')
                """,
                (now, now, request.repository, request.pr_number, request.head_sha),
            )

            job_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO trust_ci_jobs (
                    job_id, repository, pr_number, base_sha, head_sha, head_ref, base_ref,
                    pipeline, policy_digest, idempotency_key, status, max_attempts,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'queued', %s, %s, %s)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING *
                """,
                (
                    job_id,
                    request.repository,
                    request.pr_number,
                    request.base_sha,
                    request.head_sha,
                    request.head_ref,
                    request.base_ref,
                    request.pipeline,
                    policy_digest,
                    key,
                    max_attempts,
                    now,
                    now,
                ),
            )
            row = cursor.fetchone()
            created = row is not None
            if row is None:
                cursor.execute("SELECT * FROM trust_ci_jobs WHERE idempotency_key = %s", (key,))
                row = cursor.fetchone()
            if row is None:
                raise RuntimeError("idempotent enqueue did not return a job")
            connection.commit()
            return _job_from_row(row), created

    def cancel_pr(self, repository: str, pr_number: int, *, now: datetime) -> int:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE trust_ci_jobs
                SET status = 'cancelled', failure_code = 'pull-request-closed',
                    lease_owner = NULL, lease_expires_at = NULL,
                    updated_at = %s, finished_at = %s
                WHERE repository = %s AND pr_number = %s
                  AND status IN ('queued', 'leased', 'running', 'needs_approval')
                """,
                (now, now, repository, pr_number),
            )
            count = cursor.rowcount
            connection.commit()
            return count

    def claim(self, worker_id: str, lease_seconds: int, *, now: datetime) -> Job | None:
        del now
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM trust_ci_claim_job(%s, %s)", (worker_id, lease_seconds))
            row = cursor.fetchone()
            connection.commit()
            return _job_from_row(row) if row is not None else None

    def mark_running(self, job_id: str, worker_id: str, *, now: datetime) -> Job:
        return self._owned_update(
            job_id,
            worker_id,
            "status = 'running', updated_at = %s",
            (now,),
            now=now,
            allowed=("leased",),
        )

    def heartbeat(self, job_id: str, worker_id: str, lease_seconds: int, *, now: datetime) -> Job:
        return self._owned_update(
            job_id,
            worker_id,
            "lease_expires_at = %s, updated_at = %s",
            (now + timedelta(seconds=lease_seconds), now),
            now=now,
            allowed=("leased", "running"),
        )

    def finish(
        self,
        job_id: str,
        worker_id: str,
        status: str,
        result: dict[str, Any],
        *,
        failure_code: str | None = None,
        now: datetime,
    ) -> Job:
        if status not in {"passed", "failed", "needs_approval", "cancelled", "dead"}:
            raise ValueError(f"invalid terminal status: {status}")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE trust_ci_jobs
                SET status = %s, result = %s::jsonb, failure_code = %s,
                    lease_owner = NULL, lease_expires_at = NULL,
                    updated_at = %s, finished_at = %s
                WHERE job_id = %s AND lease_owner = %s
                  AND status IN ('leased', 'running') AND lease_expires_at >= %s
                RETURNING *
                """,
                (status, json.dumps(result), failure_code, now, now, job_id, worker_id, now),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("worker does not own a live job lease")
            cursor.execute(
                """
                UPDATE trust_ci_job_attempts
                SET finished_at = %s, status = %s, result = %s::jsonb
                WHERE job_id = %s AND attempt_no = %s
                """,
                (now, status, json.dumps(result), job_id, row["attempts"]),
            )
            connection.commit()
            return _job_from_row(row)

    def retry(self, job_id: str, worker_id: str, error: str, *, now: datetime) -> Job:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE trust_ci_jobs
                SET status = CASE WHEN attempts >= max_attempts THEN 'dead' ELSE 'queued' END,
                    failure_code = CASE WHEN attempts >= max_attempts
                        THEN 'infrastructure-attempts-exhausted'
                        ELSE 'retryable-infrastructure-error' END,
                    result = %s::jsonb,
                    lease_owner = NULL, lease_expires_at = NULL,
                    updated_at = %s,
                    finished_at = CASE WHEN attempts >= max_attempts THEN %s ELSE NULL END
                WHERE job_id = %s AND lease_owner = %s
                  AND status IN ('leased', 'running') AND lease_expires_at >= %s
                RETURNING *
                """,
                (json.dumps({"infrastructure_error": error[:4000]}), now, now, job_id, worker_id, now),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("worker does not own a live job lease")
            cursor.execute(
                """
                UPDATE trust_ci_job_attempts
                SET finished_at = %s, status = %s, error = %s
                WHERE job_id = %s AND attempt_no = %s
                """,
                (now, row["status"], error[:4000], job_id, row["attempts"]),
            )
            connection.commit()
            return _job_from_row(row)

    def get_job(self, job_id: str) -> Job:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM trust_ci_jobs WHERE job_id = %s", (job_id,))
            row = cursor.fetchone()
            if row is None:
                raise KeyError(job_id)
            return _job_from_row(row)

    def get_job_for_sha(self, repository: str, head_sha: str) -> Job | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM trust_ci_jobs
                WHERE repository = %s AND head_sha = %s
                ORDER BY created_at DESC LIMIT 1
                """,
                (repository, head_sha),
            )
            row = cursor.fetchone()
            return _job_from_row(row) if row is not None else None

    def record_approval(self, payload: ApprovalPayload, envelope: ApprovalEnvelope, *, now: datetime) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO trust_ci_approvals (
                        approval_id, nonce, repository, pr_number, base_sha, head_sha,
                        policy_digest, scope, actor, key_id, reason, issued_at, expires_at,
                        payload, signature, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                    """,
                    (
                        payload.approval_id,
                        payload.nonce,
                        payload.repository,
                        payload.pr_number,
                        payload.base_sha,
                        payload.head_sha,
                        payload.policy_digest,
                        payload.scope,
                        payload.actor,
                        payload.key_id,
                        payload.reason,
                        parse_datetime(payload.issued_at),
                        parse_datetime(payload.expires_at),
                        json.dumps(payload.to_dict()),
                        envelope.signature,
                        now,
                    ),
                )
                connection.commit()
            except Exception as exc:
                connection.rollback()
                if getattr(exc, "sqlstate", None) == "23505":
                    raise ReplayError("approval ID or nonce has already been used") from exc
                raise

    def has_valid_approval(
        self,
        repository: str,
        pr_number: int,
        base_sha: str,
        head_sha: str,
        policy_digest: str,
        scope: str,
        now: datetime,
    ) -> bool:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM trust_ci_approvals
                    WHERE repository = %s AND pr_number = %s AND base_sha = %s AND head_sha = %s
                      AND policy_digest = %s AND scope = %s
                      AND issued_at <= %s AND expires_at > %s
                ) AS valid
                """,
                (repository, pr_number, base_sha, head_sha, policy_digest, scope, now, now),
            )
            row = cursor.fetchone()
            return bool(row and row["valid"])

    def requeue_for_approval(self, repository: str, head_sha: str, *, now: datetime) -> int:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE trust_ci_jobs
                SET status = 'queued', failure_code = NULL, result = '{}'::jsonb,
                    finished_at = NULL, updated_at = %s
                WHERE repository = %s AND head_sha = %s AND status = 'needs_approval'
                """,
                (now, repository, head_sha),
            )
            count = cursor.rowcount
            connection.commit()
            return count

    def record_attestation(self, job_id: str, envelope: AttestationEnvelope) -> None:
        payload = envelope.payload
        with self._connect() as connection, connection.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO trust_ci_attestations (
                        attestation_id, job_id, repository, head_sha, status, key_id, payload, signature
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        payload.attestation_id,
                        job_id,
                        payload.repository,
                        payload.head_sha,
                        payload.status,
                        payload.key_id,
                        json.dumps(payload.to_dict()),
                        envelope.signature,
                    ),
                )
                connection.commit()
            except Exception as exc:
                connection.rollback()
                if getattr(exc, "sqlstate", None) == "23505":
                    raise ReplayError("attestation already exists for job") from exc
                raise

    def get_attestation(self, job_id: str) -> AttestationEnvelope | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT payload, signature FROM trust_ci_attestations WHERE job_id = %s", (job_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            return AttestationEnvelope.from_dict({"payload": row["payload"], "signature": row["signature"]})

    def record_merge_fact(self, fact: MergedPullRequestFact) -> bool:
        if not isinstance(fact, MergedPullRequestFact):
            raise TypeError("merge fact is required")
        with self._connect() as connection, connection.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    SELECT trust_ci_record_merge_fact(
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) AS created
                    """,
                    (
                        fact.merge_fact_id,
                        fact.delivery_id,
                        fact.payload_sha256,
                        fact.repository_id,
                        fact.repository,
                        fact.installation_id,
                        fact.pr_number,
                        fact.head_sha,
                        fact.base_sha,
                        fact.protected_ref,
                        fact.merged_commit_sha,
                        parse_datetime(fact.merged_at),
                        parse_datetime(fact.received_at),
                    ),
                )
                row = cursor.fetchone()
                connection.commit()
                return bool(row and row["created"])
            except Exception as exc:
                connection.rollback()
                if getattr(exc, "sqlstate", None) == "23505":
                    raise DeliveryConflict("delivery digest conflict") from exc
                raise

    def claim_merge_fact(
        self, worker_id: str, lease_seconds: int, *, now: datetime
    ) -> ClaimedMergeFact | None:
        del now
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM trust_ci_claim_merge_fact(%s, %s)",
                (worker_id, lease_seconds),
            )
            row = cursor.fetchone()
            connection.commit()
            if row is None:
                return None
            fact = _merge_fact_from_row(row)
            return ClaimedMergeFact(
                fact=fact,
                claim_id=str(row["claim_id"]),
                attempt=int(row["processing_attempt"]),
            )

    def retry_merge_fact(
        self, claimed: ClaimedMergeFact, error: str, *, now: datetime
    ) -> None:
        del now
        self._finish_merge_claim("trust_ci_retry_merge_fact", claimed, str(error)[:512])

    def requeue_merge_fact(self, merge_fact_id: str, *, now: datetime) -> bool:
        del now
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT trust_ci_requeue_merge_fact(%s) AS transitioned", (merge_fact_id,)
            )
            row = cursor.fetchone()
            connection.commit()
            return bool(row and row["transitioned"])

    def fail_merge_fact(
        self, claimed: ClaimedMergeFact, error: str, *, now: datetime
    ) -> None:
        del now
        self._finish_merge_claim("trust_ci_fail_merge_fact", claimed, str(error)[:502])

    def complete_merge_fact(self, claimed: ClaimedMergeFact, *, now: datetime) -> None:
        del now
        self._finish_merge_claim("trust_ci_complete_merge_fact", claimed)

    def _finish_merge_claim(
        self, function_name: str, claimed: ClaimedMergeFact, error: str | None = None
    ) -> None:
        if not isinstance(claimed, ClaimedMergeFact):
            raise TypeError("claimed merge fact is required")
        if function_name not in {
            "trust_ci_retry_merge_fact",
            "trust_ci_fail_merge_fact",
            "trust_ci_complete_merge_fact",
        }:
            raise ValueError("invalid merge claim transition")
        values: tuple[Any, ...] = (
            claimed.fact.merge_fact_id,
            claimed.claim_id,
            claimed.attempt,
        )
        if error is not None:
            values += (error,)
        placeholders = ", ".join(["%s"] * len(values))
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {function_name}({placeholders}) AS transitioned", values
            )
            row = cursor.fetchone()
            if row is None or not row["transitioned"]:
                connection.rollback()
                raise RuntimeError("worker does not own a live merge fact lease")
            connection.commit()

    def load_reconciliation_watermark(
        self, repository: str
    ) -> ReconciliationWatermark | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM trust_ci_get_reconciliation_watermark(%s)",
                (repository,),
            )
            row = cursor.fetchone()
            connection.rollback()
        if row is None:
            return None
        return ReconciliationWatermark(
            updated_at=rfc3339_z(row["updated_at"]),
            pr_number=int(row["pr_number"]),
        )

    def save_reconciliation_watermark(
        self, repository: str, watermark: ReconciliationWatermark
    ) -> None:
        if not isinstance(watermark, ReconciliationWatermark):
            raise TypeError("reconciliation watermark is required")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT trust_ci_save_reconciliation_watermark(%s, %s, %s)",
                (
                    repository,
                    parse_datetime(watermark.updated_at),
                    watermark.pr_number,
                ),
            )
            cursor.fetchone()
            connection.commit()

    def record_deployment_terminal(
        self, promotion_id: str, operation_id: str, event_type: str, *,
        reason_code: str, details: dict[str, Any], now: datetime,
    ) -> PromotionEvent:
        del now
        require_uuid_v1_5(promotion_id, "promotion_id")
        require_uuid_v1_5(operation_id, "operation_id")
        outcomes = {
            "deployment.completed": "completed",
            "deployment.failed": "failed",
            "deployment.reconciled": "reconciled",
        }
        if event_type not in outcomes:
            raise ValueError("invalid terminal deployment event type")
        # Constructing validates the bounded reason/details before a database call.
        probe = PromotionEvent(
            schema_version=1, event_id=str(uuid.uuid4()), event_type=event_type,
            occurred_at=rfc3339_z(utc_now().replace(microsecond=0)),
            promotion_id=promotion_id, correlation_id=operation_id,
            operation_id=operation_id, actor=None, key_id=None, repository=None,
            merged_commit_sha=None, artifact_sha256=None, target_environment=None,
            policy_epoch=None, outcome=outcomes[event_type],
            reason_code=reason_code, details=details,
        )
        with self._connect() as connection, connection.cursor() as cursor:
            try:
                cursor.execute(
                    "SELECT trust_ci_record_deployment_terminal(%s, %s, %s, %s, %s, %s::jsonb) AS occurred_at",
                    (promotion_id, operation_id, probe.event_id, event_type,
                     reason_code, json.dumps(details)),
                )
                cursor.fetchone()
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        events = self.list_promotion_events(promotion_id, limit=1000)
        for event in reversed(events):
            if event.event_id == probe.event_id:
                return event
        raise RuntimeError("terminal deployment event was not returned")

    def record_protected_branch_evidence(
        self, envelope: ProtectedBranchAttestationEnvelope
    ) -> bool:
        if not isinstance(envelope, ProtectedBranchAttestationEnvelope):
            raise TypeError("protected-branch evidence is required")
        payload = envelope.payload
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT trust_ci_record_protected_branch_evidence(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s::jsonb, %s, %s
                ) AS created
                """,
                (
                    payload.source_attestation_id,
                    payload.merge_fact_id,
                    payload.repository,
                    payload.protected_ref,
                    payload.merged_commit_sha,
                    payload.policy_epoch,
                    payload.runner_digest,
                    payload.holdout_digest,
                    payload.image_digest,
                    payload.artifact_sha256,
                    parse_datetime(payload.issued_at),
                    payload.key_id,
                    json.dumps(envelope.to_dict()),
                    envelope.signature,
                    datetime.now(timezone.utc),
                ),
            )
            row = cursor.fetchone()
            connection.commit()
            return bool(row and row["created"])

    def record_or_get_protected_branch_evidence(
        self, envelope: ProtectedBranchAttestationEnvelope
    ) -> ProtectedBranchAttestationEnvelope:
        if not isinstance(envelope, ProtectedBranchAttestationEnvelope):
            raise TypeError("protected-branch evidence is required")
        payload = envelope.payload
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT trust_ci_record_or_get_protected_branch_evidence(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s::jsonb, %s, %s
                ) AS envelope
                """,
                (
                    payload.source_attestation_id, payload.merge_fact_id,
                    payload.repository, payload.protected_ref, payload.merged_commit_sha,
                    payload.policy_epoch, payload.runner_digest, payload.holdout_digest,
                    payload.image_digest, payload.artifact_sha256,
                    parse_datetime(payload.issued_at), payload.key_id,
                    json.dumps(envelope.to_dict()), envelope.signature,
                    datetime.now(timezone.utc),
                ),
            )
            row = cursor.fetchone()
            connection.commit()
        if row is None or not isinstance(row["envelope"], dict):
            raise RuntimeError("protected-branch evidence was not returned")
        return ProtectedBranchAttestationEnvelope.from_dict(row["envelope"])

    def accept_promotion(
        self,
        envelope: PromotionEnvelope,
        idempotency_key: str,
        correlation_id: str,
        now: datetime,
    ) -> tuple[PromotionRecord, bool]:
        _require_store_text(idempotency_key, "idempotency_key", 16, 128)
        _require_store_text(correlation_id, "correlation_id", 1, 128)
        if not isinstance(envelope, PromotionEnvelope):
            raise TypeError("promotion envelope is required")
        payload = envelope.payload
        request_sha256 = hashlib.sha256(envelope.canonical_bytes()).hexdigest()
        payload_sha256 = hashlib.sha256(payload.canonical_bytes()).hexdigest()
        with self._connect() as connection, connection.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    SELECT * FROM trust_ci_accept_promotion(
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        payload.promotion_id,
                        payload.nonce,
                        payload.actor,
                        payload.key_id,
                        payload.repository,
                        payload.merged_commit_sha,
                        payload.artifact_sha256,
                        payload.target_environment,
                        payload.policy_epoch,
                        payload.source_attestation_id,
                        payload.reason,
                        parse_datetime(payload.issued_at),
                        parse_datetime(payload.expires_at),
                        json.dumps(payload.to_dict()),
                        json.dumps(envelope.to_dict()),
                        envelope.signature,
                        payload_sha256,
                        request_sha256,
                        idempotency_key,
                        correlation_id,
                        str(uuid.uuid4()),
                        now,
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("promotion acceptance returned no record")
                connection.commit()
            except Exception as exc:
                connection.rollback()
                if getattr(exc, "sqlstate", None) == "23505":
                    if "idempotency" in str(exc).lower():
                        raise IdempotencyConflict("promotion idempotency conflict") from exc
                    raise PromotionReplay("promotion replay") from exc
                if (
                    "provenance mismatch or unavailable" in str(exc).lower()
                    or "current policy mismatch" in str(exc).lower()
                ):
                    raise ProvenanceMismatch("promotion provenance mismatch") from exc
                raise
        return (
            PromotionRecord(
                envelope=envelope,
                idempotency_key=idempotency_key,
                request_sha256=request_sha256,
                accepted_at=row["result_accepted_at"],
            ),
            bool(row["result_created"]),
        )

    def activate_policy(self, policy_epoch: str) -> None:
        selected = require_digest(policy_epoch, "policy_epoch")
        with self._connect() as connection, connection.cursor() as cursor:
            try:
                cursor.execute("SELECT trust_ci_activate_policy(%s)", (selected,))
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def get_active_policy_epoch(self) -> str | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT trust_ci_get_active_policy_epoch() AS policy_epoch")
            row = cursor.fetchone()
            connection.rollback()
        if row is None or row["policy_epoch"] is None:
            return None
        return str(row["policy_epoch"])

    def consume_promotion(
        self,
        promotion_id: str,
        expected: PromotionExpectedBinding,
        operation_id: str,
        now: datetime,
    ) -> PromotionConsumption:
        del now
        if not isinstance(expected, PromotionExpectedBinding):
            raise TypeError("expected promotion binding is required")
        require_uuid_v1_5(promotion_id, "promotion_id")
        require_uuid_v1_5(operation_id, "operation_id")
        with self._connect() as connection, connection.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    SELECT trust_ci_consume_promotion(
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) AS consumed_at
                    """,
                    (
                        promotion_id,
                        expected.repository,
                        expected.merged_commit_sha,
                        expected.artifact_sha256,
                        expected.target_environment,
                        expected.policy_epoch,
                        expected.source_attestation_id,
                        operation_id,
                        str(uuid.uuid4()),
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("promotion consumption returned no record")
                connection.commit()
            except Exception as exc:
                connection.rollback()
                if getattr(exc, "sqlstate", None) == "23505":
                    if "exact operation already consumed" in str(exc).lower():
                        raise ExactOperationReplay(
                            "promotion was consumed by this exact operation"
                        ) from exc
                    raise ReplayError("promotion or operation has already been consumed") from exc
                if (
                    "current policy mismatch" in str(exc).lower()
                    or "tuple mismatch or not current" in str(exc).lower()
                ):
                    raise ProvenanceMismatch(
                        "promotion tuple mismatch or not current"
                    ) from exc
                raise
        return PromotionConsumption(
            promotion_id=promotion_id,
            operation_id=operation_id,
            expected=expected,
            consumed_at=row["consumed_at"],
        )

    def list_promotion_events(
        self, promotion_id: str, *, limit: int
    ) -> tuple[PromotionEvent, ...]:
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("event limit must be between 1 and 1000")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM trust_ci_list_promotion_events(%s, %s)",
                (promotion_id, limit),
            )
            rows = cursor.fetchall()
            connection.rollback()
        return tuple(_promotion_event_from_row(row) for row in rows)

    def get_promotion_consumption(
        self, promotion_id: str, operation_id: str
    ) -> PromotionConsumption | None:
        require_uuid_v1_5(promotion_id, "promotion_id")
        require_uuid_v1_5(operation_id, "operation_id")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM trust_ci_get_promotion_consumption(%s, %s)",
                (promotion_id, operation_id),
            )
            row = cursor.fetchone()
            connection.rollback()
        if row is None:
            return None
        return PromotionConsumption(
            promotion_id=str(row["promotion_id"]),
            operation_id=str(row["operation_id"]),
            expected=PromotionExpectedBinding(
                repository=str(row["repository"]),
                merged_commit_sha=str(row["merged_commit_sha"]),
                artifact_sha256=str(row["artifact_sha256"]),
                target_environment=str(row["target_environment"]),
                policy_epoch=str(row["policy_epoch"]),
                source_attestation_id=str(row["source_attestation_id"]),
            ),
            consumed_at=row["consumed_at"],
        )

    def record_promotion_rejection(self, event: PromotionEvent) -> None:
        if (
            not isinstance(event, PromotionEvent)
            or event.event_type != "promotion.rejected"
            or event.outcome != "rejected"
            or event.promotion_id is not None
        ):
            raise ValueError("bounded promotion rejection event is required")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT trust_ci_record_promotion_rejection(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
                )
                """,
                (
                    event.event_id,
                    parse_datetime(event.occurred_at),
                    event.correlation_id,
                    event.actor,
                    event.key_id,
                    event.repository,
                    event.merged_commit_sha,
                    event.artifact_sha256,
                    event.target_environment,
                    event.policy_epoch,
                    event.reason_code,
                    json.dumps(event.details),
                ),
            )
            cursor.fetchone()
            connection.commit()

    def _owned_update(
        self,
        job_id: str,
        worker_id: str,
        assignments: str,
        assignment_values: tuple[Any, ...],
        *,
        now: datetime,
        allowed: tuple[str, ...],
    ) -> Job:
        placeholders = ", ".join(["%s"] * len(allowed))
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE trust_ci_jobs SET {assignments}
                WHERE job_id = %s AND lease_owner = %s
                  AND status IN ({placeholders}) AND lease_expires_at >= %s
                RETURNING *
                """,
                (*assignment_values, job_id, worker_id, *allowed, now),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("worker does not own a live job lease")
            connection.commit()
            return _job_from_row(row)


def _job_from_row(row: dict[str, Any]) -> Job:
    result = row.get("result") or {}
    if isinstance(result, str):
        result = json.loads(result)
    return Job(
        job_id=str(row["job_id"]),
        repository=row["repository"],
        pr_number=int(row["pr_number"]),
        base_sha=str(row["base_sha"]),
        head_sha=str(row["head_sha"]),
        head_ref=row["head_ref"],
        base_ref=row["base_ref"],
        pipeline=row["pipeline"],
        policy_digest=str(row["policy_digest"]),
        idempotency_key=str(row["idempotency_key"]),
        status=row["status"],
        attempts=int(row["attempts"]),
        max_attempts=int(row["max_attempts"]),
        lease_owner=row.get("lease_owner"),
        lease_expires_at=row.get("lease_expires_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        started_at=row.get("started_at"),
        finished_at=row.get("finished_at"),
        failure_code=row.get("failure_code"),
        result=dict(result),
    )


def _protected_evidence_identity(payload: ProtectedBranchAttestationPayload) -> tuple[str, ...]:
    return (
        payload.merge_fact_id, payload.repository, payload.protected_ref,
        payload.merged_commit_sha, payload.policy_epoch, payload.runner_digest,
        payload.holdout_digest, payload.image_digest, payload.artifact_sha256,
        payload.result, payload.key_id,
    )


def _merge_fact_from_row(row: dict[str, Any]) -> MergedPullRequestFact:
    return MergedPullRequestFact(
        merge_fact_id=str(row["merge_fact_id"]),
        delivery_id=str(row["delivery_id"]),
        payload_sha256=str(row["payload_sha256"]),
        repository_id=int(row["repository_id"]),
        repository=str(row["repository"]),
        installation_id=int(row["installation_id"]),
        pr_number=int(row["pr_number"]),
        head_sha=str(row["head_sha"]),
        base_sha=str(row["base_sha"]),
        protected_ref=str(row["protected_ref"]),
        merged_commit_sha=str(row["merged_commit_sha"]),
        merged_at=rfc3339_z(row["merged_at"]),
        received_at=rfc3339_z(row["received_at"]),
    )


def _promotion_event_from_row(row: dict[str, Any]) -> PromotionEvent:
    details = row.get("details") or {}
    if isinstance(details, str):
        details = json.loads(details)
    return PromotionEvent(
        schema_version=1,
        event_id=str(row["event_id"]),
        event_type=str(row["event_type"]),
        occurred_at=rfc3339_z(row["occurred_at"]),
        promotion_id=str(row["promotion_id"]) if row.get("promotion_id") else None,
        correlation_id=str(row["correlation_id"]),
        operation_id=str(row["operation_id"]) if row.get("operation_id") else None,
        actor=str(row["actor"]) if row.get("actor") else None,
        key_id=str(row["key_id"]) if row.get("key_id") else None,
        repository=str(row["repository"]) if row.get("repository") else None,
        merged_commit_sha=(
            str(row["merged_commit_sha"]) if row.get("merged_commit_sha") else None
        ),
        artifact_sha256=(
            str(row["artifact_sha256"]) if row.get("artifact_sha256") else None
        ),
        target_environment=(
            str(row["target_environment"]) if row.get("target_environment") else None
        ),
        policy_epoch=str(row["policy_epoch"]) if row.get("policy_epoch") else None,
        outcome=str(row["outcome"]),
        reason_code=str(row["reason_code"]),
        details=dict(details),
    )


def _require_store_text(value: str, name: str, minimum: int, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not minimum <= len(value.encode("utf-8")) <= maximum
        or value != value.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ValueError(f"invalid {name}")
    return value


def _watermark_key(watermark: ReconciliationWatermark) -> tuple[datetime, int]:
    timestamp = datetime.fromisoformat(
        watermark.updated_at.removesuffix("Z") + "+00:00"
    )
    return timestamp, watermark.pr_number


def _promotion_binding(payload: Any) -> tuple[str, str, str, str, str, str]:
    return (
        payload.repository,
        payload.merged_commit_sha,
        payload.artifact_sha256,
        payload.target_environment,
        payload.policy_epoch,
        payload.source_attestation_id,
    )


def _expected_binding(
    expected: PromotionExpectedBinding,
) -> tuple[str, str, str, str, str, str]:
    return (
        expected.repository,
        expected.merged_commit_sha,
        expected.artifact_sha256,
        expected.target_environment,
        expected.policy_epoch,
        expected.source_attestation_id,
    )


def _evidence_binding(
    envelope: ProtectedBranchAttestationEnvelope,
) -> tuple[str, str, str, str, str, str]:
    payload = envelope.payload
    return (
        payload.repository,
        payload.merged_commit_sha,
        payload.artifact_sha256,
        "production",
        payload.policy_epoch,
        payload.source_attestation_id,
    )


def _promotion_event(
    event_type: str,
    record: PromotionRecord,
    correlation_id: str,
    now: datetime,
    *,
    outcome: str,
    operation_id: str | None = None,
) -> PromotionEvent:
    payload = record.envelope.payload
    return PromotionEvent(
        schema_version=1,
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        occurred_at=rfc3339_z(now.replace(microsecond=0)),
        promotion_id=payload.promotion_id,
        correlation_id=correlation_id,
        operation_id=operation_id,
        actor=payload.actor,
        key_id=payload.key_id,
        repository=payload.repository,
        merged_commit_sha=payload.merged_commit_sha,
        artifact_sha256=payload.artifact_sha256,
        target_environment=payload.target_environment,
        policy_epoch=payload.policy_epoch,
        outcome=outcome,
        reason_code=outcome,
        details={},
    )
