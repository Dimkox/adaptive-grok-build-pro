from __future__ import annotations

from .models import Job
from .store import MemoryStore, PostgresStore, Store, _job_from_row


def get_job_for_exact(
    store: Store,
    repository: str,
    pr_number: int,
    base_sha: str,
    head_sha: str,
    policy_digest: str,
) -> Job | None:
    """Resolve the exact approval target without accepting a same-SHA job from another PR."""
    if isinstance(store, MemoryStore):
        with store._lock:
            matches = [
                job
                for job in store._jobs.values()
                if job.repository == repository
                and job.pr_number == pr_number
                and job.base_sha == base_sha
                and job.head_sha == head_sha
                and job.policy_digest == policy_digest
            ]
            if not matches:
                return None
            import copy

            return copy.deepcopy(max(matches, key=lambda item: item.created_at))

    if isinstance(store, PostgresStore):
        with store._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM trust_ci_jobs
                WHERE repository = %s AND pr_number = %s
                  AND base_sha = %s AND head_sha = %s AND policy_digest = %s
                ORDER BY created_at DESC LIMIT 1
                """,
                (repository, pr_number, base_sha, head_sha, policy_digest),
            )
            row = cursor.fetchone()
            return _job_from_row(row) if row is not None else None

    candidate = store.get_job_for_sha(repository, head_sha)
    if candidate is None:
        return None
    if (
        candidate.pr_number != pr_number
        or candidate.base_sha != base_sha
        or candidate.policy_digest != policy_digest
    ):
        return None
    return candidate
