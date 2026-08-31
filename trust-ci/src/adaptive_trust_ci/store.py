from __future__ import annotations

import copy
import json
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Protocol

from .models import ApprovalEnvelope, ApprovalPayload, AttestationEnvelope, Job, JobRequest, parse_datetime


class ReplayError(RuntimeError):
    pass


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


class MemoryStore:
    """Thread-safe test implementation with the same transition rules as PostgreSQL."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._idempotency: dict[str, str] = {}
        self._approvals: dict[str, tuple[ApprovalPayload, ApprovalEnvelope]] = {}
        self._nonces: set[str] = set()
        self._attestations: dict[str, AttestationEnvelope] = {}
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
                        json.dumps(envelope.to_dict()["payload"]),
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
                        json.dumps(envelope.to_dict()["payload"]),
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
