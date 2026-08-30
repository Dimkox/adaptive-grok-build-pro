from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

from adaptive_trust_ci.migrations import PostgresMigrator
from adaptive_trust_ci.models import (
    JobRequest,
    PromotionExpectedBinding,
    PromotionPayload,
    ProtectedBranchAttestationPayload,
)
from adaptive_trust_ci.provenance import MergedPullRequestFact
from adaptive_trust_ci.signing import (
    Signer,
    sign_promotion,
    sign_protected_branch_attestation,
)
from adaptive_trust_ci.store import PostgresStore


REPOSITORY = 'Dimkox/adaptive-grok-build-pro'
HEAD_SHA = '9' * 40
BASE_SHA = '8' * 40
POLICY_DIGEST = '7' * 64
PROMOTION_ID = '11111111-1111-4111-8111-111111111111'
SOURCE_ATTESTATION_ID = '22222222-2222-4222-8222-222222222222'
OPERATION_ID = '33333333-3333-4333-8333-333333333333'
MERGED_SHA = 'a' * 40
ARTIFACT_SHA = 'b' * 64
POLICY_EPOCH = 'c' * 64


def seed_promotion_state(store: PostgresStore) -> None:
    store.activate_policy(POLICY_EPOCH)
    with store._connect() as connection:
        database_now = connection.execute(
            'SELECT statement_timestamp() AS now'
        ).fetchone()['now'].astimezone(timezone.utc).replace(microsecond=0)
        connection.rollback()
    signer = Signer.generate()
    merge_fact = MergedPullRequestFact.create(
        delivery_id='restart-drill-delivery-1',
        payload_sha256='d' * 64,
        repository_id=123,
        repository='dimkox/adaptive-grok-build-pro',
        installation_id=456,
        pr_number=800,
        head_sha='e' * 40,
        base_sha='f' * 40,
        protected_ref='refs/heads/main',
        merged_commit_sha=MERGED_SHA,
        merged_at=(database_now - timedelta(minutes=2)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        received_at=database_now,
    )
    if not store.record_merge_fact(merge_fact):
        raise SystemExit('restart drill could not record merge fact')
    evidence_payload = ProtectedBranchAttestationPayload(
        schema_version=1,
        source_attestation_id=SOURCE_ATTESTATION_ID,
        merge_fact_id=merge_fact.merge_fact_id,
        repository=merge_fact.repository,
        protected_ref=merge_fact.protected_ref,
        merged_commit_sha=MERGED_SHA,
        policy_epoch=POLICY_EPOCH,
        runner_digest='1' * 64,
        holdout_digest='2' * 64,
        image_digest='3' * 64,
        artifact_sha256=ARTIFACT_SHA,
        result='passed',
        issued_at=(database_now - timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        key_id=signer.key_id,
    )
    evidence = sign_protected_branch_attestation(evidence_payload, signer)
    if not store.record_protected_branch_evidence(evidence):
        raise SystemExit('restart drill could not record protected evidence')
    promotion_payload = PromotionPayload(
        schema_version=1,
        promotion_id=PROMOTION_ID,
        nonce='AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
        actor='restart-drill',
        key_id=signer.key_id,
        repository=merge_fact.repository,
        merged_commit_sha=MERGED_SHA,
        artifact_sha256=ARTIFACT_SHA,
        target_environment='production',
        policy_epoch=POLICY_EPOCH,
        source_attestation_id=SOURCE_ATTESTATION_ID,
        reason='Verify durable production promotion state across a real restart',
        issued_at=(database_now - timedelta(seconds=30)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        expires_at=(database_now + timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ'),
    )
    envelope = sign_promotion(promotion_payload, signer)
    _, created = store.accept_promotion(
        envelope,
        'restart-drill-idempotency-1',
        'restart-drill-correlation-1',
        database_now,
    )
    if not created:
        raise SystemExit('restart drill could not accept promotion')
    store.consume_promotion(
        PROMOTION_ID,
        PromotionExpectedBinding(
            repository=merge_fact.repository,
            merged_commit_sha=MERGED_SHA,
            artifact_sha256=ARTIFACT_SHA,
            target_environment='production',
            policy_epoch=POLICY_EPOCH,
            source_attestation_id=SOURCE_ATTESTATION_ID,
        ),
        OPERATION_ID,
        database_now,
    )
    store.record_deployment_terminal(
        PROMOTION_ID, OPERATION_ID, 'deployment.reconciled',
        reason_code='crash_reconciled',
        details={'drill': 'disposable'}, now=database_now,
    )
    if [event.event_type for event in store.list_promotion_events(PROMOTION_ID, limit=10)] != [
        'promotion.accepted',
        'promotion.consumed', 'deployment.reconciled',
    ]:
        raise SystemExit('restart drill promotion events were not atomically recorded')


def verify_promotion_state(store: PostgresStore) -> None:
    with store._connect() as connection:
        row = connection.execute(
            '''
            SELECT
              (SELECT count(*) FROM trust_ci_protected_branch_evidence
               WHERE source_attestation_id = %s) AS evidence_count,
              (SELECT count(*) FROM trust_ci_promotions
               WHERE promotion_id = %s) AS promotion_count,
              (SELECT count(*) FROM trust_ci_promotion_consumptions
               WHERE promotion_id = %s AND operation_id = %s) AS consumption_count
            ''',
            (SOURCE_ATTESTATION_ID, PROMOTION_ID, PROMOTION_ID, OPERATION_ID),
        ).fetchone()
        connection.rollback()
    if tuple(row.values()) != (1, 1, 1):
        raise SystemExit('durable promotion authority disappeared after PostgreSQL restart')
    if [event.event_type for event in store.list_promotion_events(PROMOTION_ID, limit=10)] != [
        'promotion.accepted',
        'promotion.consumed', 'deployment.reconciled',
    ]:
        raise SystemExit('durable promotion event order changed after PostgreSQL restart')
    exact = store.get_promotion_consumption(PROMOTION_ID, OPERATION_ID)
    if exact is None or exact.operation_id != OPERATION_ID:
        raise SystemExit('exact consumption reconciliation disappeared after restart')
    if store.get_promotion_consumption(
        PROMOTION_ID, '44444444-4444-4444-8444-444444444444'
    ) is not None:
        raise SystemExit('reconciliation falsely attributed an uncommitted operation')
    try:
        store.record_deployment_terminal(
            PROMOTION_ID, OPERATION_ID, 'deployment.completed',
            reason_code='completed', details={}, now=datetime.now(timezone.utc),
        )
    except Exception:
        pass
    else:
        raise SystemExit('restored terminal audit allowed a conflicting outcome')


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
        seed_promotion_state(store)
        print(job.job_id)
        return 0
    store.ping()
    job = store.get_job_for_sha(REPOSITORY, HEAD_SHA)
    if job is None:
        raise SystemExit('durable job disappeared after PostgreSQL restart')
    if job.base_sha != BASE_SHA or job.policy_digest != POLICY_DIGEST:
        raise SystemExit('durable job changed after PostgreSQL restart')
    verify_promotion_state(store)
    print(job.job_id)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
