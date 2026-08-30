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
PROMOTION_OUTCOMES = ('accepted', 'rejected', 'consumed', 'completed', 'failed', 'reconciled')
PROMOTION_REASONS = (
    'accepted', 'consumed', 'completed', 'failed', 'reconciled',
    'malformed_envelope', 'unsupported_contract', 'signature_invalid',
    'target_forbidden', 'policy_mismatch', 'provenance_mismatch',
    'idempotency_conflict', 'promotion_replay', 'envelope_not_current',
    'rate_limited', 'authorization_unavailable', 'promotion_disabled',
    'consume_malformed', 'deployer_unauthorized', 'consume_forbidden',
    'promotion_consumed', 'consume_rate_limited', 'consume_unavailable',
    'consumption_not_found', 'other',
)
DEPENDENCY_CATEGORIES = ('authorization', 'provenance', 'signature')
PROTECTED_BRANCH_OUTCOMES = ('passed', 'failed')


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
    promotion_outcomes: dict[str, int]
    promotion_reasons: dict[str, int]
    dependency_failures: dict[str, int]
    accepted_unconsumed: int
    consumed_without_terminal: int
    consumed_without_terminal_oldest_age_seconds: float
    promotion_accept_latency_seconds_sum: float
    promotion_accept_latency_count: int
    promotion_consume_latency_seconds_sum: float
    promotion_consume_latency_count: int
    merge_facts_pending: int
    merge_fact_oldest_pending_age_seconds: float
    reconciliation_lag_seconds: float
    protected_branch_validation_outcomes: dict[str, int]
    expired_promotions: int


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
        promotion_outcomes={
            item: max(0, int(values.get('promotion_outcomes', {}).get(item, 0)))
            for item in PROMOTION_OUTCOMES
        },
        promotion_reasons={
            item: max(0, int(values.get('promotion_reasons', {}).get(item, 0)))
            for item in PROMOTION_REASONS
        },
        dependency_failures={
            item: max(0, int(values.get('dependency_failures', {}).get(item, 0)))
            for item in DEPENDENCY_CATEGORIES
        },
        accepted_unconsumed=max(0, int(values.get('accepted_unconsumed', 0))),
        consumed_without_terminal=max(0, int(values.get('consumed_without_terminal', 0))),
        consumed_without_terminal_oldest_age_seconds=max(
            0.0, float(values.get('consumed_without_terminal_oldest_age_seconds', 0.0))
        ),
        promotion_accept_latency_seconds_sum=max(
            0.0, float(values.get('promotion_accept_latency_seconds_sum', 0.0))
        ),
        promotion_accept_latency_count=max(
            0, int(values.get('promotion_accept_latency_count', 0))
        ),
        promotion_consume_latency_seconds_sum=max(
            0.0, float(values.get('promotion_consume_latency_seconds_sum', 0.0))
        ),
        promotion_consume_latency_count=max(
            0, int(values.get('promotion_consume_latency_count', 0))
        ),
        merge_facts_pending=max(0, int(values.get('merge_facts_pending', 0))),
        merge_fact_oldest_pending_age_seconds=max(
            0.0, float(values.get('merge_fact_oldest_pending_age_seconds', 0.0))
        ),
        reconciliation_lag_seconds=max(
            0.0, float(values.get('reconciliation_lag_seconds', 0.0))
        ),
        protected_branch_validation_outcomes={
            outcome: max(
                0,
                int(
                    values.get('protected_branch_validation_outcomes', {}).get(
                        outcome, 0
                    )
                ),
            )
            for outcome in PROTECTED_BRANCH_OUTCOMES
        },
        expired_promotions=max(0, int(values.get('expired_promotions', 0))),
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
    lines.extend(
        [
            '# HELP adaptive_trust_ci_promotion_decisions_total Durable promotion decisions by bounded outcome.',
            '# TYPE adaptive_trust_ci_promotion_decisions_total counter',
            *[
                f'adaptive_trust_ci_promotion_decisions_total{{outcome="{outcome}"}} {snapshot.promotion_outcomes[outcome]}'
                for outcome in PROMOTION_OUTCOMES
            ],
            '# HELP adaptive_trust_ci_promotion_reasons_total Durable promotion decisions by bounded reason.',
            '# TYPE adaptive_trust_ci_promotion_reasons_total counter',
            *[
                f'adaptive_trust_ci_promotion_reasons_total{{reason="{reason}"}} {snapshot.promotion_reasons[reason]}'
                for reason in PROMOTION_REASONS
            ],
            '# HELP adaptive_trust_ci_dependency_failures_total Durable fail-closed dependency decisions.',
            '# TYPE adaptive_trust_ci_dependency_failures_total counter',
            *[
                f'adaptive_trust_ci_dependency_failures_total{{dependency="{category}"}} {snapshot.dependency_failures[category]}'
                for category in DEPENDENCY_CATEGORIES
            ],
            '# HELP adaptive_trust_ci_promotions_accepted_unconsumed Accepted promotions without consumption.',
            '# TYPE adaptive_trust_ci_promotions_accepted_unconsumed gauge',
            f'adaptive_trust_ci_promotions_accepted_unconsumed {snapshot.accepted_unconsumed}',
            '# HELP adaptive_trust_ci_consumed_without_terminal Consumed promotions without terminal deployment evidence.',
            '# TYPE adaptive_trust_ci_consumed_without_terminal gauge',
            f'adaptive_trust_ci_consumed_without_terminal {snapshot.consumed_without_terminal}',
            '# HELP adaptive_trust_ci_consumed_without_terminal_oldest_age_seconds Oldest nonterminal consumption age.',
            '# TYPE adaptive_trust_ci_consumed_without_terminal_oldest_age_seconds gauge',
            f'adaptive_trust_ci_consumed_without_terminal_oldest_age_seconds {_number(snapshot.consumed_without_terminal_oldest_age_seconds)}',
            '# TYPE adaptive_trust_ci_promotion_accept_latency_seconds_sum counter',
            f'adaptive_trust_ci_promotion_accept_latency_seconds_sum {_number(snapshot.promotion_accept_latency_seconds_sum)}',
            '# TYPE adaptive_trust_ci_promotion_accept_latency_seconds_count counter',
            f'adaptive_trust_ci_promotion_accept_latency_seconds_count {snapshot.promotion_accept_latency_count}',
            '# TYPE adaptive_trust_ci_promotion_consume_latency_seconds_sum counter',
            f'adaptive_trust_ci_promotion_consume_latency_seconds_sum {_number(snapshot.promotion_consume_latency_seconds_sum)}',
            '# TYPE adaptive_trust_ci_promotion_consume_latency_seconds_count counter',
            f'adaptive_trust_ci_promotion_consume_latency_seconds_count {snapshot.promotion_consume_latency_count}',
            '# HELP adaptive_trust_ci_merge_facts_pending Durable merge facts awaiting terminal validation.',
            '# TYPE adaptive_trust_ci_merge_facts_pending gauge',
            f'adaptive_trust_ci_merge_facts_pending {snapshot.merge_facts_pending}',
            '# HELP adaptive_trust_ci_merge_fact_oldest_pending_age_seconds Age of the oldest nonterminal merge fact.',
            '# TYPE adaptive_trust_ci_merge_fact_oldest_pending_age_seconds gauge',
            f'adaptive_trust_ci_merge_fact_oldest_pending_age_seconds {_number(snapshot.merge_fact_oldest_pending_age_seconds)}',
            '# HELP adaptive_trust_ci_reconciliation_lag_seconds Lag of the oldest durable reconciliation watermark.',
            '# TYPE adaptive_trust_ci_reconciliation_lag_seconds gauge',
            f'adaptive_trust_ci_reconciliation_lag_seconds {_number(snapshot.reconciliation_lag_seconds)}',
            '# HELP adaptive_trust_ci_protected_branch_validations_total Terminal protected-branch validation outcomes.',
            '# TYPE adaptive_trust_ci_protected_branch_validations_total counter',
            *[
                f'adaptive_trust_ci_protected_branch_validations_total{{outcome="{outcome}"}} {snapshot.protected_branch_validation_outcomes[outcome]}'
                for outcome in PROTECTED_BRANCH_OUTCOMES
            ],
            '# HELP adaptive_trust_ci_promotions_expired Accepted promotion records whose authority has expired.',
            '# TYPE adaptive_trust_ci_promotions_expired gauge',
            f'adaptive_trust_ci_promotions_expired {snapshot.expired_promotions}',
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
        promotion = _promotion_event_snapshot(store._promotion_events, now)
        accept_latencies = [
            max(
                0.0,
                (record.accepted_at - parse_datetime(record.envelope.payload.issued_at)).total_seconds(),
            )
            for record in store._promotions.values()
        ]
        promotion['promotion_accept_latency_seconds_sum'] = sum(accept_latencies)
        promotion['promotion_accept_latency_count'] = len(accept_latencies)
        pending_facts = [
            store._merge_facts[merge_fact_id]
            for merge_fact_id, queue in store._merge_queue.items()
            if queue['status'] in {'pending', 'leased'}
        ]
        watermark_times = [
            parse_datetime(watermark.updated_at)
            for watermark in store._reconciliation_watermarks.values()
        ]
        protected_outcomes = {
            'passed': len(store._protected_evidence),
            'failed': sum(
                1 for queue in store._merge_queue.values()
                if queue['status'] == 'dead'
            ),
        }
        expired_promotions = sum(
            1
            for record in store._promotions.values()
            if parse_datetime(record.envelope.payload.expires_at) <= now
        )
        return {
            'job_counts': job_counts,
            'oldest_queued_age_seconds': oldest_age,
            'expired_leases': expired,
            'active_approvals': active_approvals,
            'attestations_total': len(store._attestations),
            'attempts_total': attempts_total,
            'merge_facts_pending': len(pending_facts),
            'merge_fact_oldest_pending_age_seconds': (
                max(
                    0.0,
                    (
                        now
                        - min(parse_datetime(fact.received_at) for fact in pending_facts)
                    ).total_seconds(),
                )
                if pending_facts else 0.0
            ),
            'reconciliation_lag_seconds': (
                max(0.0, (now - min(watermark_times)).total_seconds())
                if watermark_times else 0.0
            ),
            'protected_branch_validation_outcomes': protected_outcomes,
            'expired_promotions': expired_promotions,
            **promotion,
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
        cursor.execute('SELECT trust_ci_promotion_metrics() AS metrics')
        promotion = dict(cursor.fetchone()['metrics'])
        connection.rollback()
        return {
            'job_counts': job_counts,
            'oldest_queued_age_seconds': oldest,
            'expired_leases': expired,
            'active_approvals': approvals,
            'attestations_total': attestations,
            'attempts_total': attempts,
            **promotion,
        }


def _promotion_event_snapshot(events: list[Any], now: datetime) -> dict[str, Any]:
    outcomes = {item: 0 for item in PROMOTION_OUTCOMES}
    reasons = {item: 0 for item in PROMOTION_REASONS}
    dependencies = {item: 0 for item in DEPENDENCY_CATEGORIES}
    accepted: dict[str, datetime] = {}
    consumed: dict[str, datetime] = {}
    terminal: set[str] = set()
    for event in events:
        if event.outcome in outcomes:
            outcomes[event.outcome] += 1
        reason = event.reason_code if event.reason_code in reasons else 'other'
        reasons[reason] += 1
        if event.reason_code in {'authorization_unavailable', 'consume_unavailable'}:
            dependencies['authorization'] += 1
        elif event.reason_code == 'provenance_mismatch':
            dependencies['provenance'] += 1
        elif event.reason_code == 'signature_invalid':
            dependencies['signature'] += 1
        if event.promotion_id is None:
            continue
        occurred = parse_datetime(event.occurred_at)
        if event.event_type == 'promotion.accepted':
            accepted[event.promotion_id] = occurred
        elif event.event_type == 'promotion.consumed':
            consumed[event.promotion_id] = occurred
        elif event.event_type in {
            'deployment.completed', 'deployment.failed', 'deployment.reconciled'
        }:
            terminal.add(event.promotion_id)
    pending_consumed = {
        promotion_id: occurred
        for promotion_id, occurred in consumed.items()
        if promotion_id not in terminal
    }
    consume_latencies = [
        max(0.0, (occurred - accepted[promotion_id]).total_seconds())
        for promotion_id, occurred in consumed.items()
        if promotion_id in accepted
    ]
    oldest = (
        max(0.0, (now - min(pending_consumed.values())).total_seconds())
        if pending_consumed
        else 0.0
    )
    return {
        'promotion_outcomes': outcomes,
        'promotion_reasons': reasons,
        'dependency_failures': dependencies,
        'accepted_unconsumed': len(set(accepted) - set(consumed)),
        'consumed_without_terminal': len(pending_consumed),
        'consumed_without_terminal_oldest_age_seconds': oldest,
        'promotion_consume_latency_seconds_sum': sum(consume_latencies),
        'promotion_consume_latency_count': len(consume_latencies),
    }


def _escape(value: str) -> str:
    return value.replace('\\', '\\\\').replace('\n', '\\n').replace('"', '\\"')


def _number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f'{value:.6f}'.rstrip('0').rstrip('.')
