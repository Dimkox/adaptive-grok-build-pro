from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from adaptive_trust_ci.migrations import PostgresMigrator
from adaptive_trust_ci.models import JobRequest
from adaptive_trust_ci.store import PostgresStore


REPOSITORY = 'Dimkox/adaptive-grok-build-pro'
HEAD_SHA = '9' * 40
BASE_SHA = '8' * 40
POLICY_DIGEST = '7' * 64


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if len(args) != 1 or args[0] not in {'seed', 'verify'}:
        raise SystemExit('usage: python -m tests.postgres_restart_probe seed|verify')
    database_url = os.environ.get('TRUST_CI_TEST_DATABASE_URL', '').strip()
    if not database_url:
        raise SystemExit('TRUST_CI_TEST_DATABASE_URL is required')
    store = PostgresStore(database_url)
    if args[0] == 'seed':
        PostgresMigrator(database_url).apply()
        request = JobRequest(
            repository=REPOSITORY,
            pr_number=799,
            base_sha=BASE_SHA,
            head_sha=HEAD_SHA,
            head_ref='feat/postgres-restart-probe',
            base_ref='main',
        )
        job, _ = store.enqueue(request, POLICY_DIGEST, 3, now=datetime.now(timezone.utc))
        print(job.job_id)
        return 0
    store.ping()
    job = store.get_job_for_sha(REPOSITORY, HEAD_SHA)
    if job is None:
        raise SystemExit('durable job disappeared after PostgreSQL restart')
    if job.base_sha != BASE_SHA or job.policy_digest != POLICY_DIGEST:
        raise SystemExit('durable job changed after PostgreSQL restart')
    print(job.job_id)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
