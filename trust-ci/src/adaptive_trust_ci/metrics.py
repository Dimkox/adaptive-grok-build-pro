from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .models import parse_datetime
from .store import MemoryStore, PostgresStore, Store


JOB_STATUSES = (
    'queued',
    'leased',
    'running',
    'passed',
    'failed',
    'needs_approval',
    'cancelled',
    'dead',
)


@dataclass(frozen=True)
class OperationalMetrics:
    job_counts: dict[str, int]
    oldest_queued_age_seconds: float
    expired_leases: int
    active_approvals: int
    attestations_total: int
    attempts_total: int
    stopped: bool
    policy_epoch: str
    check_name: str


def collect_metrics(
    store: Store,
    *,
    now: datetime,
    stopped: bool,
    policy_digest: str,
    check_name: str,
) -> OperationalMetrics:
    current = now.astimezone(timezone.utc)
    if isinstance(store, MemoryStore):
        values = _memory_snapshot(store, current)
    elif isinstance(store, PostgresStore):
        values = _postgres_snapshot(store, current)
    else:
        snapshot = getattr(store, 'operational_snapshot', None)
        if snapshot is None:
            raise TypeError(f'unsupported metrics store: {type(store).__name__}')
        values = snapshot(current)
    return OperationalMetrics(
        job_counts={status: int(values['job_counts'].get(status, 0)) for status in JOB_STATUSES},
        oldest_queued_age_seconds=max(0.0, float(values.get('oldest_queued_age_seconds', 0.0))),
        expired_leases=max(0, int(values.get('expired_leases', 0))),
        active_approvals=max(0, int(values.get('active_approvals', 0))),
        attestations_total=max(0, int(values.get('attestations_total', 0))),
        attempts_total=max(0, int(values.get('attempts_total', 0))),
        stopped=bool(stopped),
        policy_epoch=policy_digest[:12],
        check_name=check_name,
    )


def render_prometheus(snapshot: OperationalMetrics) -> str:
    lines = [
        '# HELP adaptive_trust_ci_jobs Durable jobs by finite state.',
        '# TYPE adaptive_trust_ci_jobs gauge',
    ]
    for status in JOB_STATUSES:
        lines.append(f'adaptive_trust_ci_jobs{{status="{status}"}} {snapshot.job_counts.get(status, 0)}')
    lines.extend(
        [
            '# HELP adaptive_trust_ci_queue_oldest_age_seconds Age of the oldest queued job.',
            '# TYPE adaptive_trust_ci_queue_oldest_age_seconds gauge',
            f'adaptive_trust_ci_queue_oldest_age_seconds {_number(snapshot.oldest_queued_age_seconds)}',
            '# HELP adaptive_trust_ci_expired_leases Leased or running jobs whose lease has expired.',
            '# TYPE adaptive_trust_ci_expired_leases gauge',
            f'adaptive_trust_ci_expired_leases {snapshot.expired_leases}',
            '# HELP adaptive_trust_ci_active_approvals Unexpired exact-SHA approvals.',
            '# TYPE adaptive_trust_ci_active_approvals gauge',
            f'adaptive_trust_ci_active_approvals {snapshot.active_approvals}',
            '# HELP adaptive_trust_ci_attestations_total Stored signed attestations.',
            '# TYPE adaptive_trust_ci_attestations_total gauge',
            f'adaptive_trust_ci_attestations_total {snapshot.attestations_total}',
            '# HELP adaptive_trust_ci_attempts_total Durable worker attempts.',
            '# TYPE adaptive_trust_ci_attempts_total gauge',
            f'adaptive_trust_ci_attempts_total {snapshot.attempts_total}',
            '# HELP adaptive_trust_ci_kill_switch Whether the emergency stop is active.',
            '# TYPE adaptive_trust_ci_kill_switch gauge',
            f'adaptive_trust_ci_kill_switch {1 if snapshot.stopped else 0}',
            '# HELP adaptive_trust_ci_policy_info Active server policy epoch and required check.',
            '# TYPE adaptive_trust_ci_policy_info gauge',
            (
                'adaptive_trust_ci_policy_info'
                f'{{check_name="{_escape(snapshot.check_name)}",policy_epoch="{_escape(snapshot.policy_epoch)}"}} 1'
            ),
        ]
    )
    return '\n'.join(lines) + '\n'


def _memory_snapshot(store: MemoryStore, now: datetime) -> dict[str, Any]:
    with store._lock:
        jobs = list(store._jobs.values())
        queued = [item.created_at for item in jobs if item.status == 'queued']
        job_counts = {status: 0 for status in JOB_STATUSES}
        for job in jobs:
            job_counts[job.status] = job_counts.get(job.status, 0) + 1
        active_approvals = sum(
            1
            for payload, _ in store._approvals.values()
            if parse_datetime(payload.issued_at) <= now < parse_datetime(payload.expires_at)
        )
        expired = sum(
            1
            for job in jobs
            if job.status in {'leased', 'running'}
            and job.lease_expires_at is not None
            and job.lease_expires_at < now
        )
        attempts_total = sum(job.attempts for job in jobs)
        oldest_age = (now - min(queued)).total_seconds() if queued else 0.0
        return {
            'job_counts': job_counts,
            'oldest_queued_age_seconds': oldest_age,
            'expired_leases': expired,
            'active_approvals': active_approvals,
            'attestations_total': len(store._attestations),
            'attempts_total': attempts_total,
        }


def _postgres_snapshot(store: PostgresStore, now: datetime) -> dict[str, Any]:
    with store._connect() as connection, connection.cursor() as cursor:
        cursor.execute('SELECT status, count(*) AS count FROM trust_ci_jobs GROUP BY status')
        job_counts = {str(row['status']): int(row['count']) for row in cursor.fetchall()}
        cursor.execute(
            '''
            SELECT COALESCE(EXTRACT(EPOCH FROM (%s - MIN(created_at))), 0) AS age
            FROM trust_ci_jobs WHERE status = 'queued'
            ''',
            (now,),
        )
        oldest = float(cursor.fetchone()['age'])
        cursor.execute(
            '''
            SELECT count(*) AS count FROM trust_ci_jobs
            WHERE status IN ('leased', 'running') AND lease_expires_at < %s
            ''',
            (now,),
        )
        expired = int(cursor.fetchone()['count'])
        cursor.execute(
            'SELECT count(*) AS count FROM trust_ci_approvals WHERE issued_at <= %s AND expires_at > %s',
            (now, now),
        )
        approvals = int(cursor.fetchone()['count'])
        cursor.execute('SELECT count(*) AS count FROM trust_ci_attestations')
        attestations = int(cursor.fetchone()['count'])
        cursor.execute('SELECT count(*) AS count FROM trust_ci_job_attempts')
        attempts = int(cursor.fetchone()['count'])
        connection.rollback()
        return {
            'job_counts': job_counts,
            'oldest_queued_age_seconds': oldest,
            'expired_leases': expired,
            'active_approvals': approvals,
            'attestations_total': attestations,
            'attempts_total': attempts,
        }


def _escape(value: str) -> str:
    return value.replace('\\', '\\\\').replace('\n', '\\n').replace('"', '\\"')


def _number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f'{value:.6f}'.rstrip('0').rstrip('.')
