from __future__ import annotations

import os
import base64
import shutil
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from datetime import timedelta, timezone

from _support import digest, now, sha
from adaptive_trust_ci.migrations import PostgresMigrator
from adaptive_trust_ci.metrics import collect_metrics, render_prometheus
from adaptive_trust_ci.models import (
    ApprovalPayload,
    AttestationPayload,
    JobRequest,
    PromotionExpectedBinding,
    PromotionEvent,
    PromotionPayload,
    ProtectedBranchAttestationPayload,
)
from adaptive_trust_ci.provenance import MergedPullRequestFact, ReconciliationWatermark
from adaptive_trust_ci.signing import (
    Signer,
    sign_approval,
    sign_attestation,
    sign_promotion,
    sign_protected_branch_attestation,
    verify_attestation,
)
from adaptive_trust_ci.store import ExactOperationReplay, PostgresStore, ProvenanceMismatch, ReplayError


DATABASE_URL = os.environ.get('TRUST_CI_TEST_DATABASE_URL', '').strip()
API_DATABASE_URL = os.environ.get('TRUST_CI_TEST_API_DATABASE_URL', '').strip()
WORKER_DATABASE_URL = os.environ.get('TRUST_CI_TEST_WORKER_DATABASE_URL', '').strip()
BACKUP_DATABASE_URL = os.environ.get('TRUST_CI_TEST_BACKUP_DATABASE_URL', '').strip()
DEPLOYER_DATABASE_URL = os.environ.get('TRUST_CI_TEST_DEPLOYER_DATABASE_URL', '').strip()


def wait_for_advisory_waiter(store: PostgresStore, lock_id: int) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        with store._connect() as connection:
            waiting = connection.execute(
                """
                SELECT count(*) AS count
                FROM pg_locks
                WHERE locktype = 'advisory'
                  AND objid = %s
                  AND NOT granted
                """,
                (lock_id,),
            ).fetchone()['count']
            connection.rollback()
        if waiting:
            return
        time.sleep(0.01)
    raise AssertionError(f'no transaction waited on advisory lock {lock_id}')


def _capture(results: list, operation) -> None:
    try:
        results.append(operation())
    except BaseException as exc:
        results.append(exc)


@unittest.skipUnless(DATABASE_URL, 'TRUST_CI_TEST_DATABASE_URL is not configured')
class PostgresIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.store = PostgresStore(DATABASE_URL)
        cls.migrator = PostgresMigrator(DATABASE_URL)
        migration_root = Path(__file__).resolve().parents[1] / 'sql'
        with tempfile.TemporaryDirectory() as directory:
            partial_root = Path(directory)
            for version in ('001', '002', '003'):
                source = next(migration_root.glob(f'{version}_*.sql'))
                shutil.copyfile(source, partial_root / source.name)
            PostgresMigrator(DATABASE_URL, partial_root).apply()
        populated, _ = cls.store.enqueue(
            JobRequest(
                repository='Dimkox/adaptive-grok-build-pro',
                pr_number=700,
                base_sha=sha('8'),
                head_sha=sha('9'),
                head_ref='feat/populated-003',
                base_ref='main',
            ),
            digest('7'),
            3,
            now=now(),
        )
        cls.populated_job_id = populated.job_id
        cls.migrator.apply()
        cls.populated_upgrade_preserved = (
            cls.store.get_job(cls.populated_job_id).job_id == cls.populated_job_id
        )

    def setUp(self) -> None:
        with self.store._connect() as connection:
            connection.execute(
                'TRUNCATE trust_ci_active_policy, trust_ci_promotion_events, trust_ci_promotion_consumptions, '
                'trust_ci_promotions, trust_ci_promotion_idempotency, '
                'trust_ci_protected_branch_evidence, '
                'trust_ci_reconciliation_watermarks, trust_ci_merge_facts, '
                'trust_ci_events, trust_ci_attestations, trust_ci_approvals, '
                'trust_ci_job_attempts, trust_ci_jobs RESTART IDENTITY CASCADE'
            )
            connection.commit()
        self.store.activate_policy(digest('c'))
        with self.store._connect() as connection:
            self.database_now = connection.execute(
                'SELECT statement_timestamp() AS now'
            ).fetchone()['now'].astimezone(timezone.utc).replace(microsecond=0)
            connection.rollback()
        self.signer = Signer.generate()
        self.merge_fact = MergedPullRequestFact.create(
            delivery_id=str(uuid.uuid4()),
            payload_sha256=digest('d'),
            repository_id=123,
            repository='dimkox/adaptive-grok-build-pro',
            installation_id=456,
            pr_number=701,
            head_sha=sha('e'),
            base_sha=sha('f'),
            protected_ref='refs/heads/main',
            merged_commit_sha=sha('a'),
            merged_at='2026-08-23T11:59:00Z',
            received_at=now(),
        )
        attestation_payload = ProtectedBranchAttestationPayload(
            schema_version=1,
            source_attestation_id=str(uuid.uuid4()),
            merge_fact_id=self.merge_fact.merge_fact_id,
            repository=self.merge_fact.repository,
            protected_ref=self.merge_fact.protected_ref,
            merged_commit_sha=self.merge_fact.merged_commit_sha,
            policy_epoch=digest('c'),
            runner_digest=digest('1'),
            holdout_digest=digest('2'),
            image_digest=digest('3'),
            artifact_sha256=digest('b'),
            result='passed',
            issued_at='2026-08-23T12:00:00Z',
            key_id=self.signer.key_id,
        )
        self.protected_evidence = sign_protected_branch_attestation(
            attestation_payload, self.signer
        )
        promotion_payload = PromotionPayload(
            schema_version=1,
            promotion_id=str(uuid.uuid4()),
            nonce=base64.urlsafe_b64encode(os.urandom(32)).decode('ascii').rstrip('='),
            actor='dmitry',
            key_id=self.signer.key_id,
            repository=attestation_payload.repository,
            merged_commit_sha=attestation_payload.merged_commit_sha,
            artifact_sha256=attestation_payload.artifact_sha256,
            target_environment='production',
            policy_epoch=attestation_payload.policy_epoch,
            source_attestation_id=attestation_payload.source_attestation_id,
            reason='Deploy the immutable reviewed artifact',
            issued_at=(self.database_now - timedelta(seconds=30)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            expires_at=(self.database_now + timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        )
        self.promotion_envelope = sign_promotion(promotion_payload, self.signer)
        self.expected_promotion = PromotionExpectedBinding(
            repository=promotion_payload.repository,
            merged_commit_sha=promotion_payload.merged_commit_sha,
            artifact_sha256=promotion_payload.artifact_sha256,
            target_environment=promotion_payload.target_environment,
            policy_epoch=promotion_payload.policy_epoch,
            source_attestation_id=promotion_payload.source_attestation_id,
        )

    def request(self, *, head='b') -> JobRequest:
        return JobRequest(
            repository='Dimkox/adaptive-grok-build-pro',
            pr_number=701,
            base_sha=sha('a'),
            head_sha=sha(head),
            head_ref='feat/postgres-test',
            base_ref='main',
        )

    def enqueue(self, *, max_attempts=3):
        return self.store.enqueue(self.request(), digest('c'), max_attempts, now=now())

    def test_migration_registry_is_current_and_idempotent(self) -> None:
        first = self.migrator.status()
        self.assertEqual(first.pending, ())
        self.assertGreaterEqual(len(first.applied), 2)
        second = self.migrator.apply()
        self.assertEqual(second.pending, ())
        self.assertEqual(
            [(item.version, item.sha256) for item in first.applied],
            [(item.version, item.sha256) for item in second.applied],
        )
        with self.store._connect() as connection:
            rows = connection.execute(
                'SELECT version, name, sha256 FROM trust_ci_schema_migrations ORDER BY version'
            ).fetchall()
            connection.rollback()
        self.assertEqual(len(rows), len(first.applied))
        self.assertEqual(first.applied[-1].version, 4)
        self.assertEqual(first.applied[-1].name, 'production_promotions')

    def seed_promotion_provenance(self, *, store=None) -> None:
        selected = store or self.store
        self.assertTrue(selected.record_merge_fact(self.merge_fact))
        self.assertTrue(selected.record_protected_branch_evidence(self.protected_evidence))

    def test_populated_003_upgrade_preserved_existing_job(self) -> None:
        self.assertTrue(self.populated_upgrade_preserved)

    def test_merge_fact_claim_retry_watermark_and_restart_are_durable(self) -> None:
        self.assertTrue(self.store.record_merge_fact(self.merge_fact))
        claimed = self.store.claim_merge_fact('worker-1', 60, now=now())
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.store.retry_merge_fact(claimed, 'transient', now=now())
        restarted = PostgresStore(DATABASE_URL)
        self.assertIsNone(restarted.claim_merge_fact('worker-early', 60, now=now()))
        with restarted._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE trust_ci_merge_facts SET next_attempt_at = statement_timestamp() - interval '1 second' WHERE merge_fact_id = %s",
                (self.merge_fact.merge_fact_id,),
            )
            connection.commit()
        reclaimed = restarted.claim_merge_fact('worker-2', 60, now=now())
        self.assertIsNotNone(reclaimed)
        assert reclaimed is not None
        self.assertEqual(reclaimed.attempt, 2)
        restarted.complete_merge_fact(reclaimed, now=now())
        watermark = ReconciliationWatermark('2026-08-23T12:00:00Z', 701)
        restarted.save_reconciliation_watermark(self.merge_fact.repository, watermark)
        self.assertEqual(
            PostgresStore(DATABASE_URL).load_reconciliation_watermark(
                self.merge_fact.repository
            ),
            watermark,
        )

    def test_dead_merge_fact_is_explicitly_requeued_after_restart(self) -> None:
        self.store.record_merge_fact(self.merge_fact)
        with self.store._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE trust_ci_merge_facts SET processing_status = 'dead', processing_attempt = 20, last_error = 'retry-exhausted:outage' WHERE merge_fact_id = %s",
                (self.merge_fact.merge_fact_id,),
            )
            connection.commit()
        restarted = PostgresStore(DATABASE_URL)
        self.assertTrue(restarted.requeue_merge_fact(self.merge_fact.merge_fact_id, now=now()))
        claimed = restarted.claim_merge_fact('worker-recovery', 60, now=now())
        self.assertIsNotNone(claimed)
        assert claimed is not None
        self.assertEqual(claimed.attempt, 1)

    def test_crash_after_evidence_commit_reuses_exact_tuple_and_completes_after_restart(self) -> None:
        self.store.record_merge_fact(self.merge_fact)
        first_claim = self.store.claim_merge_fact('worker-before-crash', 60, now=now())
        self.assertIsNotNone(first_claim)
        self.assertTrue(self.store.record_protected_branch_evidence(self.protected_evidence))
        with self.store._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE trust_ci_merge_facts SET lease_expires_at = statement_timestamp() - interval '1 second' WHERE merge_fact_id = %s",
                (self.merge_fact.merge_fact_id,),
            )
            connection.commit()

        restarted = PostgresStore(DATABASE_URL)
        reclaimed = restarted.claim_merge_fact('worker-after-restart', 60, now=now())
        self.assertIsNotNone(reclaimed)
        assert reclaimed is not None
        replay_payload = ProtectedBranchAttestationPayload(
            **{
                **self.protected_evidence.payload.to_dict(),
                'source_attestation_id': str(uuid.uuid4()),
                'issued_at': '2026-08-23T12:00:01Z',
            }
        )
        replay = sign_protected_branch_attestation(replay_payload, self.signer)
        stored = restarted.record_or_get_protected_branch_evidence(replay)
        self.assertEqual(stored, self.protected_evidence)
        restarted.complete_merge_fact(reclaimed, now=now())
        with restarted._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT processing_status, (SELECT count(*) FROM trust_ci_protected_branch_evidence WHERE merge_fact_id = %s) AS evidence_count FROM trust_ci_merge_facts WHERE merge_fact_id = %s",
                (self.merge_fact.merge_fact_id, self.merge_fact.merge_fact_id),
            )
            row = cursor.fetchone()
        self.assertEqual((row['processing_status'], row['evidence_count']), ('completed', 1))

    def test_promotion_and_consumption_survive_restart_with_atomic_events(self) -> None:
        self.seed_promotion_provenance()
        record, created = self.store.accept_promotion(
            self.promotion_envelope, 'request-00000001', 'correlation-1', self.database_now,
        )
        self.assertTrue(created)
        restarted = PostgresStore(DATABASE_URL)
        replay, replay_created = restarted.accept_promotion(
            self.promotion_envelope, 'request-00000001', 'correlation-2', self.database_now,
        )
        self.assertFalse(replay_created)
        self.assertEqual(replay.promotion_id, record.promotion_id)
        operation_id = str(uuid.uuid4())
        restarted.consume_promotion(
            record.promotion_id, self.expected_promotion, operation_id, self.database_now
        )
        events = PostgresStore(DATABASE_URL).list_promotion_events(
            record.promotion_id, limit=10
        )
        self.assertEqual(
            [event.event_type for event in events],
            ['promotion.accepted', 'promotion.consumed'],
        )

    def test_acceptance_transaction_requires_current_server_policy_epoch(self) -> None:
        self.seed_promotion_provenance()
        self.store.activate_policy(digest('f'))
        with self.assertRaises(ProvenanceMismatch):
            self.store.accept_promotion(
                self.promotion_envelope,
                'request-policy-epoch-0001',
                'correlation-policy-epoch',
                self.database_now,
            )
        with self.store._connect() as connection:
            counts = connection.execute(
                """
                SELECT
                    (SELECT count(*) FROM trust_ci_promotion_idempotency) AS reservations,
                    (SELECT count(*) FROM trust_ci_promotions) AS promotions,
                    (SELECT count(*) FROM trust_ci_promotion_events) AS events
                """
            ).fetchone()
            connection.rollback()
        self.assertEqual(tuple(counts.values()), (0, 0, 0))

    def test_exact_policy_activation_retry_preserves_activation_timestamp(self) -> None:
        with self.store._connect() as connection:
            before = connection.execute(
                'SELECT policy_epoch, activated_at FROM trust_ci_active_policy WHERE singleton'
            ).fetchone()
            connection.rollback()
        time.sleep(0.01)
        self.store.activate_policy(digest('c'))
        with self.store._connect() as connection:
            after = connection.execute(
                'SELECT policy_epoch, activated_at FROM trust_ci_active_policy WHERE singleton'
            ).fetchone()
            connection.rollback()
        self.assertEqual(after, before)

    def test_acceptance_before_activation_serializes_as_old_epoch_then_rotation(self) -> None:
        self.seed_promotion_provenance()
        lock_id = 8123401
        with self.store._connect() as setup:
            setup.execute(
                f"""
                CREATE FUNCTION trust_ci_test_pause_acceptance()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    PERFORM pg_advisory_xact_lock({lock_id});
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trust_ci_test_pause_acceptance
                BEFORE INSERT ON trust_ci_promotions
                FOR EACH ROW EXECUTE FUNCTION trust_ci_test_pause_acceptance()
                """
            )
            setup.commit()
        results = []
        api_store = PostgresStore(API_DATABASE_URL)
        with self.store._connect() as gate:
            gate.execute('SELECT pg_advisory_lock(%s)', (lock_id,))
            accept = threading.Thread(
                target=lambda: _capture(
                    results,
                    lambda: api_store.accept_promotion(
                        self.promotion_envelope,
                        'request-accept-first-0001',
                        'correlation-accept-first',
                        self.database_now,
                    ),
                )
            )
            accept.start()
            wait_for_advisory_waiter(self.store, lock_id)
            activate = threading.Thread(
                target=lambda: _capture(
                    results, lambda: self.store.activate_policy(digest('f'))
                )
            )
            activate.start()
            time.sleep(0.05)
            self.assertTrue(activate.is_alive())
            gate.execute('SELECT pg_advisory_unlock(%s)', (lock_id,))
            gate.rollback()
        accept.join(timeout=10)
        activate.join(timeout=10)
        try:
            self.assertFalse(accept.is_alive())
            self.assertFalse(activate.is_alive())
            self.assertTrue(any(isinstance(item, tuple) and item[1] for item in results), results)
            self.assertFalse(any(isinstance(item, BaseException) for item in results), results)
            self.assertEqual(self.store.get_active_policy_epoch(), digest('f'))
        finally:
            with self.store._connect() as cleanup:
                cleanup.execute('DROP TRIGGER trust_ci_test_pause_acceptance ON trust_ci_promotions')
                cleanup.execute('DROP FUNCTION trust_ci_test_pause_acceptance()')
                cleanup.commit()

    def test_activation_before_acceptance_serializes_as_new_epoch_and_rejects(self) -> None:
        self.seed_promotion_provenance()
        lock_id = 8123402
        with self.store._connect() as setup:
            setup.execute(
                f"""
                CREATE FUNCTION trust_ci_test_pause_activation()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    PERFORM pg_advisory_xact_lock({lock_id});
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trust_ci_test_pause_activation
                BEFORE UPDATE ON trust_ci_active_policy
                FOR EACH ROW EXECUTE FUNCTION trust_ci_test_pause_activation()
                """
            )
            setup.commit()
        results = []
        api_store = PostgresStore(API_DATABASE_URL)
        with self.store._connect() as gate:
            gate.execute('SELECT pg_advisory_lock(%s)', (lock_id,))
            activate = threading.Thread(
                target=lambda: _capture(
                    results, lambda: self.store.activate_policy(digest('f'))
                )
            )
            activate.start()
            wait_for_advisory_waiter(self.store, lock_id)
            accept = threading.Thread(
                target=lambda: _capture(
                    results,
                    lambda: api_store.accept_promotion(
                        self.promotion_envelope,
                        'request-activate-first-0001',
                        'correlation-activate-first',
                        self.database_now,
                    ),
                )
            )
            accept.start()
            time.sleep(0.05)
            self.assertTrue(accept.is_alive())
            gate.execute('SELECT pg_advisory_unlock(%s)', (lock_id,))
            gate.rollback()
        activate.join(timeout=10)
        accept.join(timeout=10)
        try:
            self.assertFalse(activate.is_alive())
            self.assertFalse(accept.is_alive())
            self.assertTrue(any(isinstance(item, ProvenanceMismatch) for item in results), results)
            with self.store._connect() as connection:
                counts = connection.execute(
                    """
                    SELECT
                        (SELECT count(*) FROM trust_ci_promotion_idempotency) AS reservations,
                        (SELECT count(*) FROM trust_ci_promotions) AS promotions,
                        (SELECT count(*) FROM trust_ci_promotion_events) AS events
                    """
                ).fetchone()
                connection.rollback()
            self.assertEqual(tuple(counts.values()), (0, 0, 0))
        finally:
            with self.store._connect() as cleanup:
                cleanup.execute('DROP TRIGGER trust_ci_test_pause_activation ON trust_ci_active_policy')
                cleanup.execute('DROP FUNCTION trust_ci_test_pause_activation()')
                cleanup.commit()

    def test_consumption_rechecks_database_active_policy_before_writing(self) -> None:
        self.seed_promotion_provenance()
        record, _ = self.store.accept_promotion(
            self.promotion_envelope,
            'request-consume-policy-0001',
            'correlation-consume-policy',
            self.database_now,
        )
        self.store.activate_policy(digest('f'))
        with self.assertRaises(Exception):
            PostgresStore(DEPLOYER_DATABASE_URL).consume_promotion(
                record.promotion_id,
                self.expected_promotion,
                str(uuid.uuid4()),
                self.database_now,
            )
        with self.store._connect() as connection:
            counts = connection.execute(
                """
                SELECT
                    (SELECT count(*) FROM trust_ci_promotion_consumptions) AS consumptions,
                    (SELECT count(*) FROM trust_ci_promotion_events) AS events
                """
            ).fetchone()
            connection.rollback()
        self.assertEqual((counts['consumptions'], counts['events']), (0, 1))

    def test_consumption_rechecks_protected_evidence_before_writing(self) -> None:
        self.seed_promotion_provenance()
        record, _ = self.store.accept_promotion(
            self.promotion_envelope,
            'request-consume-evidence-0001',
            'correlation-consume-evidence',
            self.database_now,
        )
        with self.store._connect() as connection:
            connection.execute(
                """
                UPDATE trust_ci_protected_branch_evidence
                SET artifact_sha256 = %s
                WHERE source_attestation_id = %s
                """,
                (digest('f'), self.expected_promotion.source_attestation_id),
            )
            connection.commit()
        with self.assertRaises(Exception):
            PostgresStore(DEPLOYER_DATABASE_URL).consume_promotion(
                record.promotion_id,
                self.expected_promotion,
                str(uuid.uuid4()),
                self.database_now,
            )
        with self.store._connect() as connection:
            counts = connection.execute(
                """
                SELECT
                    (SELECT count(*) FROM trust_ci_promotion_consumptions) AS consumptions,
                    (SELECT count(*) FROM trust_ci_promotion_events) AS events
                """
            ).fetchone()
            connection.rollback()
        self.assertEqual((counts['consumptions'], counts['events']), (0, 1))

    def test_consumption_before_activation_serializes_as_old_epoch_then_rotation(self) -> None:
        self.seed_promotion_provenance()
        record, _ = self.store.accept_promotion(
            self.promotion_envelope,
            'request-consume-first-0001',
            'correlation-consume-first',
            self.database_now,
        )
        lock_id = 8123403
        with self.store._connect() as setup:
            setup.execute(
                f"""
                CREATE FUNCTION trust_ci_test_pause_consumption()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    PERFORM pg_advisory_xact_lock({lock_id});
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trust_ci_test_pause_consumption
                BEFORE INSERT ON trust_ci_promotion_consumptions
                FOR EACH ROW EXECUTE FUNCTION trust_ci_test_pause_consumption()
                """
            )
            setup.commit()
        results = []
        deployer_store = PostgresStore(DEPLOYER_DATABASE_URL)
        with self.store._connect() as gate:
            gate.execute('SELECT pg_advisory_lock(%s)', (lock_id,))
            consume = threading.Thread(
                target=lambda: _capture(
                    results,
                    lambda: deployer_store.consume_promotion(
                        record.promotion_id,
                        self.expected_promotion,
                        str(uuid.uuid4()),
                        self.database_now,
                    ),
                )
            )
            consume.start()
            wait_for_advisory_waiter(self.store, lock_id)
            activate = threading.Thread(
                target=lambda: _capture(
                    results, lambda: self.store.activate_policy(digest('f'))
                )
            )
            activate.start()
            time.sleep(0.05)
            self.assertTrue(activate.is_alive())
            gate.execute('SELECT pg_advisory_unlock(%s)', (lock_id,))
            gate.rollback()
        consume.join(timeout=10)
        activate.join(timeout=10)
        try:
            self.assertFalse(consume.is_alive())
            self.assertFalse(activate.is_alive())
            self.assertEqual(sum(not isinstance(item, BaseException) for item in results), 2)
            self.assertEqual(self.store.get_active_policy_epoch(), digest('f'))
        finally:
            with self.store._connect() as cleanup:
                cleanup.execute(
                    'DROP TRIGGER trust_ci_test_pause_consumption ON trust_ci_promotion_consumptions'
                )
                cleanup.execute('DROP FUNCTION trust_ci_test_pause_consumption()')
                cleanup.commit()

    def test_activation_before_consumption_serializes_as_new_epoch_and_rejects(self) -> None:
        self.seed_promotion_provenance()
        record, _ = self.store.accept_promotion(
            self.promotion_envelope,
            'request-activate-before-consume-0001',
            'correlation-activate-before-consume',
            self.database_now,
        )
        lock_id = 8123404
        with self.store._connect() as setup:
            setup.execute(
                f"""
                CREATE FUNCTION trust_ci_test_pause_consume_activation()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    PERFORM pg_advisory_xact_lock({lock_id});
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trust_ci_test_pause_consume_activation
                BEFORE UPDATE ON trust_ci_active_policy
                FOR EACH ROW EXECUTE FUNCTION trust_ci_test_pause_consume_activation()
                """
            )
            setup.commit()
        results = []
        deployer_store = PostgresStore(DEPLOYER_DATABASE_URL)
        with self.store._connect() as gate:
            gate.execute('SELECT pg_advisory_lock(%s)', (lock_id,))
            activate = threading.Thread(
                target=lambda: _capture(
                    results, lambda: self.store.activate_policy(digest('f'))
                )
            )
            activate.start()
            wait_for_advisory_waiter(self.store, lock_id)
            consume = threading.Thread(
                target=lambda: _capture(
                    results,
                    lambda: deployer_store.consume_promotion(
                        record.promotion_id,
                        self.expected_promotion,
                        str(uuid.uuid4()),
                        self.database_now,
                    ),
                )
            )
            consume.start()
            time.sleep(0.05)
            self.assertTrue(consume.is_alive())
            gate.execute('SELECT pg_advisory_unlock(%s)', (lock_id,))
            gate.rollback()
        activate.join(timeout=10)
        consume.join(timeout=10)
        try:
            self.assertFalse(activate.is_alive())
            self.assertFalse(consume.is_alive())
            self.assertEqual(sum(not isinstance(item, BaseException) for item in results), 1)
            with self.store._connect() as connection:
                counts = connection.execute(
                    """
                    SELECT
                        (SELECT count(*) FROM trust_ci_promotion_consumptions) AS consumptions,
                        (SELECT count(*) FROM trust_ci_promotion_events) AS events
                    """
                ).fetchone()
                connection.rollback()
            self.assertEqual((counts['consumptions'], counts['events']), (0, 1))
        finally:
            with self.store._connect() as cleanup:
                cleanup.execute(
                    'DROP TRIGGER trust_ci_test_pause_consume_activation ON trust_ci_active_policy'
                )
                cleanup.execute('DROP FUNCTION trust_ci_test_pause_consume_activation()')
                cleanup.commit()

    def test_concurrent_nonce_and_consume_have_one_winner(self) -> None:
        self.seed_promotion_provenance()

        def race(callable_):
            barrier = threading.Barrier(3)
            results = []

            def run():
                barrier.wait(timeout=10)
                try:
                    results.append(callable_())
                except BaseException as exc:
                    results.append(exc)

            threads = [threading.Thread(target=run) for _ in range(2)]
            for thread in threads:
                thread.start()
            barrier.wait(timeout=10)
            for thread in threads:
                thread.join(timeout=20)
            return results

        accepted = race(
            lambda: self.store.accept_promotion(
                self.promotion_envelope,
                f'request-{uuid.uuid4()}',
                'correlation-race',
                self.database_now,
            )
        )
        self.assertEqual(
            sum(isinstance(value, tuple) and value[1] for value in accepted), 1
        )
        consumed = race(
            lambda: self.store.consume_promotion(
                self.promotion_envelope.payload.promotion_id,
                self.expected_promotion,
                str(uuid.uuid4()),
                self.database_now,
            )
        )
        self.assertEqual(sum(not isinstance(value, BaseException) for value in consumed), 1)

    def test_exact_operation_retry_is_distinguished_without_misidentifying_conflict(self) -> None:
        self.seed_promotion_provenance()
        record, _ = self.store.accept_promotion(
            self.promotion_envelope,
            'request-operation-retry-0001',
            'correlation-operation-retry',
            self.database_now,
        )
        deployer_store = PostgresStore(DEPLOYER_DATABASE_URL)
        operation_id = str(uuid.uuid4())
        deployer_store.consume_promotion(
            record.promotion_id,
            self.expected_promotion,
            operation_id,
            self.database_now,
        )
        with self.assertRaises(ExactOperationReplay):
            deployer_store.consume_promotion(
                record.promotion_id,
                self.expected_promotion,
                operation_id,
                self.database_now,
            )
        with self.assertRaises(ReplayError) as conflicting:
            deployer_store.consume_promotion(
                record.promotion_id,
                self.expected_promotion,
                str(uuid.uuid4()),
                self.database_now,
            )
        self.assertNotIsInstance(conflicting.exception, ExactOperationReplay)
        self.assertEqual(
            [
                event.event_type
                for event in deployer_store.list_promotion_events(
                    record.promotion_id, limit=10
                )
            ],
            ['promotion.accepted', 'promotion.consumed'],
        )
        exact = deployer_store.get_promotion_consumption(
            record.promotion_id, operation_id
        )
        self.assertIsNotNone(exact)
        assert exact is not None
        self.assertEqual(exact.operation_id, operation_id)
        self.assertIsNone(
            deployer_store.get_promotion_consumption(
                record.promotion_id, str(uuid.uuid4())
            )
        )

    def test_deployer_terminal_event_is_exact_append_only_and_concurrency_safe(self) -> None:
        self.seed_promotion_provenance()
        record, _ = self.store.accept_promotion(
            self.promotion_envelope, 'request-terminal-0001',
            'correlation-terminal', self.database_now,
        )
        deployer = PostgresStore(DEPLOYER_DATABASE_URL)
        operation_id = str(uuid.uuid4())
        deployer.consume_promotion(
            record.promotion_id, self.expected_promotion, operation_id,
            self.database_now,
        )
        barrier = threading.Barrier(3)
        results = []

        def append(event_type: str) -> None:
            barrier.wait(timeout=10)
            try:
                results.append(deployer.record_deployment_terminal(
                    record.promotion_id, operation_id, event_type,
                    reason_code=event_type.rsplit('.', 1)[1], details={},
                    now=self.database_now,
                ))
            except BaseException as exc:
                results.append(exc)

        threads = [
            threading.Thread(target=append, args=(event_type,))
            for event_type in ('deployment.completed', 'deployment.failed')
        ]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=10)
        for thread in threads:
            thread.join(timeout=20)
        self.assertEqual(sum(not isinstance(value, BaseException) for value in results), 1)
        self.assertEqual(
            len([event for event in deployer.list_promotion_events(
                record.promotion_id, limit=10
            ) if event.event_type.startswith('deployment.')]),
            1,
        )

    def test_sql_rejects_nil_and_uuid_versions_six_through_eight_atomically(self) -> None:
        self.seed_promotion_provenance()
        record, _ = self.store.accept_promotion(
            self.promotion_envelope,
            'request-invalid-operation-0001',
            'correlation-invalid-operation',
            self.database_now,
        )
        invalid_ids = (
            '00000000-0000-0000-0000-000000000000',
            '00000000-0000-6000-8000-000000000000',
            '00000000-0000-7000-8000-000000000000',
            '00000000-0000-8000-8000-000000000000',
        )
        deployer = PostgresStore(DEPLOYER_DATABASE_URL)
        with deployer._connect() as connection:
            for operation_id in invalid_ids:
                with self.subTest(operation_id=operation_id), self.assertRaises(Exception):
                    connection.execute(
                        "SELECT trust_ci_consume_promotion(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (
                            record.promotion_id,
                            self.expected_promotion.repository,
                            self.expected_promotion.merged_commit_sha,
                            self.expected_promotion.artifact_sha256,
                            self.expected_promotion.target_environment,
                            self.expected_promotion.policy_epoch,
                            self.expected_promotion.source_attestation_id,
                            operation_id,
                            str(uuid.uuid4()),
                        ),
                    )
                connection.rollback()
        with self.store._connect() as connection:
            counts = connection.execute(
                """
                SELECT
                  (SELECT count(*) FROM trust_ci_promotion_consumptions) AS consumptions,
                  (SELECT count(*) FROM trust_ci_promotion_events WHERE event_type = 'promotion.consumed') AS events
                """
            ).fetchone()
            connection.rollback()
        self.assertEqual((counts['consumptions'], counts['events']), (0, 0))

    def test_runtime_roles_are_function_scoped_and_backup_sees_authority(self) -> None:
        self.assertTrue(API_DATABASE_URL and WORKER_DATABASE_URL and BACKUP_DATABASE_URL and DEPLOYER_DATABASE_URL)
        api_store = PostgresStore(API_DATABASE_URL)
        worker_store = PostgresStore(WORKER_DATABASE_URL)
        self.assertTrue(api_store.record_merge_fact(self.merge_fact))
        claimed = worker_store.claim_merge_fact('worker-role', 60, now=now())
        self.assertIsNotNone(claimed)
        assert claimed is not None
        worker_store.complete_merge_fact(claimed, now=now())
        self.assertTrue(worker_store.record_protected_branch_evidence(self.protected_evidence))
        record, _ = api_store.accept_promotion(
            self.promotion_envelope, 'request-00000001', 'correlation-role', self.database_now,
        )
        current_accept_signature = (
            'trust_ci_accept_promotion(uuid,text,text,text,text,text,text,text,text,'
            'uuid,text,timestamptz,timestamptz,jsonb,jsonb,text,text,text,text,text,uuid,timestamptz)'
        )
        api_epoch_accept_signature = (
            'trust_ci_accept_promotion(uuid,text,text,text,text,text,text,text,text,text,uuid,'
            'text,timestamptz,timestamptz,jsonb,jsonb,text,text,text,text,text,uuid,timestamptz)'
        )
        with api_store._connect() as connection:
            for statement in (
                'INSERT INTO trust_ci_promotions DEFAULT VALUES',
                'UPDATE trust_ci_promotions SET reason = reason',
                'DELETE FROM trust_ci_promotions',
                'TRUNCATE trust_ci_promotions',
            ):
                with self.subTest(statement=statement), self.assertRaises(Exception) as caught:
                    connection.execute(statement)
                self.assertEqual(caught.exception.sqlstate, '42501')
                connection.rollback()
            privileges = connection.execute(
                """
                SELECT
                    has_function_privilege(
                        current_user,
                        'trust_ci_record_merge_fact(uuid,text,text,bigint,text,bigint,bigint,text,text,text,text,timestamptz,timestamptz)',
                        'EXECUTE'
                    ) AS can_record,
                    has_function_privilege(
                        current_user,
                        'trust_ci_claim_merge_fact(text,integer)',
                        'EXECUTE'
                    ) AS can_claim,
                    has_function_privilege(
                        current_user,
                        %s,
                        'EXECUTE'
                    ) AS can_accept_current,
                    to_regprocedure(%s) AS api_epoch_accept
                """,
                (current_accept_signature, api_epoch_accept_signature),
            ).fetchone()
            connection.rollback()
        self.assertTrue(privileges['can_record'])
        self.assertFalse(privileges['can_claim'])
        self.assertTrue(privileges['can_accept_current'])
        self.assertIsNone(privileges['api_epoch_accept'])

        activation_signature = 'trust_ci_activate_policy(text)'
        read_signature = 'trust_ci_get_active_policy_epoch()'
        for database_url, can_activate, can_read in (
            (DATABASE_URL, True, True),
            (API_DATABASE_URL, False, True),
            (WORKER_DATABASE_URL, False, False),
            (BACKUP_DATABASE_URL, False, False),
            (DEPLOYER_DATABASE_URL, False, False),
        ):
            with PostgresStore(database_url)._connect() as connection:
                policy_privileges = connection.execute(
                    """
                    SELECT
                        has_function_privilege(current_user, %s, 'EXECUTE') AS can_activate,
                        has_function_privilege(current_user, %s, 'EXECUTE') AS can_read
                    """,
                    (activation_signature, read_signature),
                ).fetchone()
                if database_url in (DATABASE_URL, BACKUP_DATABASE_URL):
                    connection.execute('SELECT * FROM trust_ci_active_policy')
                    direct_read = None
                else:
                    with self.assertRaises(Exception) as denied:
                        connection.execute('SELECT * FROM trust_ci_active_policy')
                    direct_read = denied.exception
                connection.rollback()
                if database_url == DATABASE_URL:
                    direct_update = None
                else:
                    with self.assertRaises(Exception) as update_denied:
                        connection.execute(
                            "UPDATE trust_ci_active_policy SET policy_epoch = %s WHERE singleton",
                            (digest('f'),),
                        )
                    direct_update = update_denied.exception
                connection.rollback()
            self.assertEqual(policy_privileges['can_activate'], can_activate)
            self.assertEqual(policy_privileges['can_read'], can_read)
            if direct_read is not None:
                self.assertEqual(direct_read.sqlstate, '42501')
            if direct_update is not None:
                self.assertEqual(direct_update.sqlstate, '42501')
            if not can_activate:
                with self.assertRaises(Exception):
                    PostgresStore(database_url).activate_policy(digest('f'))
        with worker_store._connect() as connection:
            privileges = connection.execute(
                """
                SELECT
                    has_function_privilege(
                        current_user,
                        'trust_ci_record_merge_fact(uuid,text,text,bigint,text,bigint,bigint,text,text,text,text,timestamptz,timestamptz)',
                        'EXECUTE'
                    ) AS can_record,
                    has_function_privilege(
                        current_user,
                        'trust_ci_claim_merge_fact(text,integer)',
                        'EXECUTE'
                    ) AS can_claim
                """
            ).fetchone()
            connection.rollback()
        self.assertFalse(privileges['can_record'])
        self.assertTrue(privileges['can_claim'])
        deployer_store = PostgresStore(DEPLOYER_DATABASE_URL)
        consumed = deployer_store.consume_promotion(
            record.promotion_id,
            self.expected_promotion,
            str(uuid.uuid4()),
            self.database_now,
        )
        self.assertEqual(consumed.promotion_id, record.promotion_id)
        self.assertEqual(
            [event.event_type for event in deployer_store.list_promotion_events(record.promotion_id, limit=10)],
            ['promotion.accepted', 'promotion.consumed'],
        )
        consume_signature = (
            'trust_ci_consume_promotion(uuid,text,text,text,text,text,uuid,text,uuid)'
        )
        reconcile_signature = 'trust_ci_get_promotion_consumption(uuid,text)'
        for database_url, expected_execute in (
            (API_DATABASE_URL, False),
            (WORKER_DATABASE_URL, False),
            (BACKUP_DATABASE_URL, False),
            (DEPLOYER_DATABASE_URL, True),
        ):
            selected_store = PostgresStore(database_url)
            with selected_store._connect() as connection:
                allowed = connection.execute(
                    "SELECT has_function_privilege(current_user, %s, 'EXECUTE') AS allowed",
                    (consume_signature,),
                ).fetchone()['allowed']
                connection.rollback()
            self.assertEqual(allowed, expected_execute)
            with selected_store._connect() as connection:
                reconciliation_allowed = connection.execute(
                    "SELECT has_function_privilege(current_user, %s, 'EXECUTE') AS allowed",
                    (reconcile_signature,),
                ).fetchone()['allowed']
                connection.rollback()
            self.assertEqual(reconciliation_allowed, expected_execute)
        with deployer_store._connect() as connection:
            for statement in (
                'INSERT INTO trust_ci_promotion_consumptions DEFAULT VALUES',
                'UPDATE trust_ci_promotions SET reason = reason',
                'DELETE FROM trust_ci_promotions',
                'TRUNCATE trust_ci_promotions',
            ):
                with self.subTest(deployer_statement=statement), self.assertRaises(Exception) as caught:
                    connection.execute(statement)
                self.assertEqual(caught.exception.sqlstate, '42501')
                connection.rollback()
        backup = PostgresStore(BACKUP_DATABASE_URL)
        with backup._connect() as connection:
            row = connection.execute(
                'SELECT count(*) AS count FROM trust_ci_promotions'
            ).fetchone()
            connection.rollback()
        self.assertEqual(row['count'], 1)

    def test_accept_and_consume_roll_back_when_atomic_event_append_fails(self) -> None:
        self.seed_promotion_provenance()

        def install_failure_trigger() -> None:
            with self.store._connect() as connection:
                connection.execute(
                    """
                    CREATE OR REPLACE FUNCTION trust_ci_test_reject_event()
                    RETURNS trigger LANGUAGE plpgsql AS $$
                    BEGIN
                        RAISE EXCEPTION 'test event append failure';
                    END;
                    $$;
                    CREATE TRIGGER trust_ci_test_reject_event
                    BEFORE INSERT ON trust_ci_promotion_events
                    FOR EACH ROW EXECUTE FUNCTION trust_ci_test_reject_event()
                    """
                )
                connection.commit()

        def remove_failure_trigger() -> None:
            with self.store._connect() as connection:
                connection.execute(
                    'DROP TRIGGER trust_ci_test_reject_event ON trust_ci_promotion_events'
                )
                connection.execute('DROP FUNCTION trust_ci_test_reject_event()')
                connection.commit()

        install_failure_trigger()
        try:
            with self.assertRaisesRegex(Exception, 'event append failure'):
                self.store.accept_promotion(
                    self.promotion_envelope,
                    'request-00000001',
                    'correlation-atomic',
                    self.database_now,
                )
        finally:
            remove_failure_trigger()
        with self.store._connect() as connection:
            counts = connection.execute(
                """
                SELECT
                    (SELECT count(*) FROM trust_ci_promotions) AS promotions,
                    (SELECT count(*) FROM trust_ci_promotion_events) AS events
                """
            ).fetchone()
            connection.rollback()
        self.assertEqual((counts['promotions'], counts['events']), (0, 0))

        record, _ = self.store.accept_promotion(
            self.promotion_envelope,
            'request-00000001',
            'correlation-atomic',
            self.database_now,
        )
        install_failure_trigger()
        try:
            with self.assertRaisesRegex(Exception, 'event append failure'):
                self.store.consume_promotion(
                    record.promotion_id,
                    self.expected_promotion,
                    str(uuid.uuid4()),
                    self.database_now,
                )
        finally:
            remove_failure_trigger()
        with self.store._connect() as connection:
            counts = connection.execute(
                """
                SELECT
                    (SELECT count(*) FROM trust_ci_promotion_consumptions) AS consumptions,
                    (SELECT count(*) FROM trust_ci_promotion_events) AS events
                """
            ).fetchone()
            connection.rollback()
        self.assertEqual((counts['consumptions'], counts['events']), (0, 1))

    def test_api_role_records_bounded_rejection_but_other_roles_cannot(self) -> None:
        event = PromotionEvent(
            schema_version=1,
            event_id=str(uuid.uuid4()),
            event_type='promotion.rejected',
            occurred_at=self.database_now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            promotion_id=None,
            correlation_id='correlation-rejected',
            operation_id=None,
            actor='dmitry',
            key_id=self.signer.key_id,
            repository='dimkox/adaptive-grok-build-pro',
            merged_commit_sha=sha('a'),
            artifact_sha256=digest('b'),
            target_environment='production',
            policy_epoch=digest('c'),
            outcome='rejected',
            reason_code='signature_invalid',
            details={'http_status': 401},
        )
        api_store = PostgresStore(API_DATABASE_URL)
        api_store.record_promotion_rejection(event)
        with self.store._connect() as connection:
            stored = connection.execute(
                "SELECT event_type, reason_code, details FROM trust_ci_promotion_events WHERE event_id = %s",
                (event.event_id,),
            ).fetchone()
            connection.rollback()
        self.assertEqual((stored['event_type'], stored['reason_code']), ('promotion.rejected', 'signature_invalid'))
        self.assertEqual(stored['details'], {'http_status': 401})
        signature = 'trust_ci_record_promotion_rejection(uuid,timestamptz,text,text,text,text,text,text,text,text,text,jsonb)'
        for database_url, expected in (
            (API_DATABASE_URL, True),
            (WORKER_DATABASE_URL, False),
            (BACKUP_DATABASE_URL, False),
            (DEPLOYER_DATABASE_URL, False),
        ):
            with PostgresStore(database_url)._connect() as connection:
                allowed = connection.execute(
                    "SELECT has_function_privilege(current_user, %s, 'EXECUTE') AS allowed",
                    (signature,),
                ).fetchone()['allowed']
                connection.rollback()
            self.assertEqual(allowed, expected)

    def test_api_metrics_use_only_bounded_durable_promotion_aggregate(self) -> None:
        self.seed_promotion_provenance()
        record, _ = self.store.accept_promotion(
            self.promotion_envelope,
            'request-metrics-0001',
            'correlation-metrics',
            self.database_now,
        )
        expired_payload = PromotionPayload(
            **{
                **self.promotion_envelope.payload.to_dict(),
                'promotion_id': str(uuid.uuid4()),
                'nonce': base64.urlsafe_b64encode(os.urandom(32)).decode('ascii').rstrip('='),
                'issued_at': (self.database_now - timedelta(minutes=20)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'expires_at': (self.database_now - timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            }
        )
        self.store.accept_promotion(
            sign_promotion(expired_payload, self.signer),
            'request-metrics-expired-0001',
            'correlation-metrics-expired',
            self.database_now,
        )
        pending_fact = MergedPullRequestFact.create(
            delivery_id=str(uuid.uuid4()),
            payload_sha256=digest('6'),
            repository_id=123,
            repository=self.merge_fact.repository,
            installation_id=456,
            pr_number=702,
            head_sha=sha('6'),
            base_sha=sha('f'),
            protected_ref=self.merge_fact.protected_ref,
            merged_commit_sha=sha('7'),
            merged_at=(self.database_now - timedelta(minutes=3)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            received_at=self.database_now - timedelta(seconds=120),
        )
        failed_fact = MergedPullRequestFact.create(
            delivery_id=str(uuid.uuid4()),
            payload_sha256=digest('8'),
            repository_id=123,
            repository=self.merge_fact.repository,
            installation_id=456,
            pr_number=703,
            head_sha=sha('8'),
            base_sha=sha('f'),
            protected_ref=self.merge_fact.protected_ref,
            merged_commit_sha=sha('9'),
            merged_at=(self.database_now - timedelta(minutes=3)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            received_at=self.database_now - timedelta(seconds=60),
        )
        self.assertTrue(self.store.record_merge_fact(pending_fact))
        self.assertTrue(self.store.record_merge_fact(failed_fact))
        self.store.save_reconciliation_watermark(
            self.merge_fact.repository,
            ReconciliationWatermark(
                (self.database_now - timedelta(seconds=75)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                703,
            ),
        )
        with self.store._connect() as connection:
            connection.execute(
                "UPDATE trust_ci_merge_facts SET processing_status = 'completed', processed_at = statement_timestamp() WHERE merge_fact_id = %s",
                (self.merge_fact.merge_fact_id,),
            )
            connection.execute(
                "UPDATE trust_ci_merge_facts SET processing_status = 'dead', processed_at = statement_timestamp() WHERE merge_fact_id = %s",
                (failed_fact.merge_fact_id,),
            )
            connection.commit()
        rejection = PromotionEvent(
            schema_version=1,
            event_id=str(uuid.uuid4()),
            event_type='promotion.rejected',
            occurred_at=self.database_now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            promotion_id=None,
            correlation_id='correlation-metrics-rejected',
            operation_id=None,
            actor=None,
            key_id=None,
            repository=None,
            merged_commit_sha=None,
            artifact_sha256=None,
            target_environment=None,
            policy_epoch=None,
            outcome='rejected',
            reason_code='authorization_unavailable',
            details={'http_status': 503},
        )
        PostgresStore(API_DATABASE_URL).record_promotion_rejection(rejection)
        snapshot = collect_metrics(
            PostgresStore(API_DATABASE_URL),
            now=self.database_now,
            stopped=False,
            policy_digest=digest('c'),
            check_name='adaptive-trust-ci/verified@cccccccccccc',
        )
        self.assertEqual(snapshot.promotion_outcomes['accepted'], 2)
        self.assertEqual(snapshot.promotion_outcomes['rejected'], 1)
        self.assertEqual(snapshot.dependency_failures['authorization'], 1)
        self.assertEqual(snapshot.accepted_unconsumed, 2)
        self.assertEqual(snapshot.merge_facts_pending, 1)
        self.assertGreaterEqual(snapshot.merge_fact_oldest_pending_age_seconds, 120)
        self.assertGreaterEqual(snapshot.reconciliation_lag_seconds, 75)
        self.assertEqual(
            snapshot.protected_branch_validation_outcomes,
            {'passed': 1, 'failed': 1},
        )
        self.assertEqual(snapshot.expired_promotions, 1)
        rendered = render_prometheus(snapshot)
        self.assertNotIn(record.promotion_id, rendered)
        self.assertNotIn(self.promotion_envelope.signature, rendered)
        signature = 'trust_ci_promotion_metrics()'
        for database_url, expected in (
            (API_DATABASE_URL, True),
            (WORKER_DATABASE_URL, False),
            (BACKUP_DATABASE_URL, False),
            (DEPLOYER_DATABASE_URL, False),
        ):
            with PostgresStore(database_url)._connect() as connection:
                allowed = connection.execute(
                    "SELECT has_function_privilege(current_user, %s, 'EXECUTE') AS allowed",
                    (signature,),
                ).fetchone()['allowed']
                connection.rollback()
            self.assertEqual(allowed, expected)

    def test_004_constraints_and_operational_indexes_exist(self) -> None:
        with self.store._connect() as connection:
            indexes = {
                row['indexname']
                for row in connection.execute(
                    "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
                ).fetchall()
            }
            foreign_keys = connection.execute(
                """
                SELECT count(*) AS count
                FROM pg_constraint
                WHERE contype = 'f'
                  AND conrelid IN (
                    'trust_ci_protected_branch_evidence'::regclass,
                    'trust_ci_promotions'::regclass,
                    'trust_ci_promotion_consumptions'::regclass,
                    'trust_ci_promotion_events'::regclass
                  )
                  AND confdeltype = 'r'
                """
            ).fetchone()
            connection.rollback()
        self.assertTrue(
            {
                'trust_ci_merge_facts_pending_idx',
                'trust_ci_promotions_consume_idx',
                'trust_ci_promotions_unconsumed_idx',
                'trust_ci_promotion_events_order_idx',
            }.issubset(indexes)
        )
        self.assertGreaterEqual(foreign_keys['count'], 4)

    def test_concurrent_exact_idempotent_retry_returns_the_stored_winner(self) -> None:
        self.seed_promotion_provenance()
        with self.store._connect() as connection:
            connection.execute(
                """
                CREATE FUNCTION trust_ci_test_slow_accept()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    PERFORM pg_sleep(0.2);
                    RETURN NEW;
                END;
                $$;
                CREATE TRIGGER trust_ci_test_slow_accept
                BEFORE INSERT ON trust_ci_promotions
                FOR EACH ROW EXECUTE FUNCTION trust_ci_test_slow_accept()
                """
            )
            connection.commit()
        barrier = threading.Barrier(3)
        results = []

        def accept() -> None:
            barrier.wait(timeout=10)
            try:
                results.append(
                    self.store.accept_promotion(
                        self.promotion_envelope,
                        'request-same-key-0001',
                        'correlation-same-key',
                        self.database_now,
                    )
                )
            except BaseException as exc:
                results.append(exc)

        threads = [threading.Thread(target=accept) for _ in range(2)]
        try:
            for thread in threads:
                thread.start()
            barrier.wait(timeout=10)
            for thread in threads:
                thread.join(timeout=20)
        finally:
            with self.store._connect() as connection:
                connection.execute('DROP TRIGGER trust_ci_test_slow_accept ON trust_ci_promotions')
                connection.execute('DROP FUNCTION trust_ci_test_slow_accept()')
                connection.commit()
        self.assertTrue(all(isinstance(value, tuple) for value in results), results)
        self.assertEqual(sorted(value[1] for value in results), [False, True])
        self.assertEqual(len({value[0].promotion_id for value in results}), 1)
        self.assertEqual(len({value[0].accepted_at for value in results}), 1)
        self.assertEqual(len({value[0].request_sha256 for value in results}), 1)
        events = self.store.list_promotion_events(
            self.promotion_envelope.payload.promotion_id, limit=10
        )
        self.assertEqual([event.event_type for event in events], ['promotion.accepted'])

    def test_database_clock_rejects_expired_promotion_despite_historical_caller_time(self) -> None:
        self.seed_promotion_provenance()
        expired_payload = PromotionPayload(
            **{
                **self.promotion_envelope.payload.to_dict(),
                'promotion_id': str(uuid.uuid4()),
                'nonce': base64.urlsafe_b64encode(os.urandom(32)).decode('ascii').rstrip('='),
                'issued_at': (self.database_now - timedelta(minutes=20)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'expires_at': (self.database_now - timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            }
        )
        expired = sign_promotion(expired_payload, self.signer)
        record, _ = self.store.accept_promotion(
            expired,
            'request-expired-0001',
            'correlation-expired',
            self.database_now - timedelta(minutes=19),
        )
        expected = PromotionExpectedBinding(
            repository=expired_payload.repository,
            merged_commit_sha=expired_payload.merged_commit_sha,
            artifact_sha256=expired_payload.artifact_sha256,
            target_environment=expired_payload.target_environment,
            policy_epoch=expired_payload.policy_epoch,
            source_attestation_id=expired_payload.source_attestation_id,
        )
        with self.assertRaisesRegex(Exception, 'not current'):
            self.store.consume_promotion(
                record.promotion_id,
                expected,
                str(uuid.uuid4()),
                self.database_now - timedelta(minutes=19),
            )
        with self.store._connect() as connection:
            count = connection.execute(
                'SELECT count(*) AS count FROM trust_ci_promotion_consumptions'
            ).fetchone()['count']
            connection.rollback()
        self.assertEqual(count, 0)

    def test_high_cardinality_exact_and_unconsumed_queries_use_bounded_indexes(self) -> None:
        self.seed_promotion_provenance()
        source_attestation_id = self.protected_evidence.payload.source_attestation_id
        with self.store._connect() as connection:
            connection.execute(
                """
                INSERT INTO trust_ci_promotions (
                    promotion_id, nonce, actor, key_id, repository, merged_commit_sha,
                    artifact_sha256, target_environment, policy_epoch, source_attestation_id,
                    reason, issued_at, expires_at, payload, envelope, signature,
                    payload_sha256, request_sha256, idempotency_key, accepted_at
                )
                SELECT
                    md5('promotion-' || value::text)::uuid,
                    lpad(value::text, 43, 'n'), 'load-test', 'load-test-key',
                    'dimkox/adaptive-grok-build-pro', repeat('a', 40), repeat('b', 64),
                    'production', repeat('c', 64), %s,
                    'bounded query-plan fixture', statement_timestamp() - interval '1 minute',
                    statement_timestamp() + interval '1 day', '{}'::jsonb, '{}'::jsonb,
                    repeat('A', 86), md5('payload-' || value::text) || md5('payload-b-' || value::text),
                    md5('request-' || value::text) || md5('request-b-' || value::text),
                    'load-request-' || lpad(value::text, 8, '0'), statement_timestamp()
                FROM generate_series(1, 10000) AS value
                """,
                (source_attestation_id,),
            )
            connection.execute('ANALYZE trust_ci_promotions')
            connection.execute('SET LOCAL enable_seqscan = off')
            exact_plan = connection.execute(
                """
                EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
                SELECT promotion_id
                FROM trust_ci_promotions
                WHERE promotion_id = md5('promotion-5000')::uuid
                  AND repository = 'dimkox/adaptive-grok-build-pro'
                  AND merged_commit_sha = repeat('a', 40)
                  AND artifact_sha256 = repeat('b', 64)
                  AND target_environment = 'production'
                  AND policy_epoch = repeat('c', 64)
                  AND source_attestation_id = %s
                  AND expires_at > statement_timestamp()
                """,
                (source_attestation_id,),
            ).fetchone()['QUERY PLAN']
            unconsumed_plan = connection.execute(
                """
                EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
                SELECT promotions.promotion_id
                FROM trust_ci_promotions AS promotions
                LEFT JOIN trust_ci_promotion_consumptions AS consumptions
                  ON consumptions.promotion_id = promotions.promotion_id
                WHERE promotions.target_environment = 'production'
                  AND promotions.expires_at > statement_timestamp()
                  AND consumptions.promotion_id IS NULL
                ORDER BY promotions.expires_at, promotions.promotion_id
                LIMIT 100
                """
            ).fetchone()['QUERY PLAN']
            connection.rollback()
        self.assertIn('Index Scan', str(exact_plan))
        self.assertIn('trust_ci_promotions_pkey', str(exact_plan))
        self.assertLessEqual(exact_plan[0]['Plan']['Actual Rows'], 1)
        self.assertIn('trust_ci_promotions_unconsumed_idx', str(unconsumed_plan))
        self.assertLessEqual(unconsumed_plan[0]['Plan']['Actual Rows'], 100)

    def test_two_concurrent_workers_cannot_claim_same_live_job(self) -> None:
        job, _ = self.enqueue()
        barrier = threading.Barrier(3)
        claimed = []
        errors = []

        def claim(worker_id: str) -> None:
            try:
                barrier.wait(timeout=10)
                claimed.append(self.store.claim(worker_id, 60, now=now()))
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=claim, args=(f'worker-{number}',)) for number in (1, 2)]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=10)
        for thread in threads:
            thread.join(timeout=20)
        self.assertEqual(errors, [])
        winners = [item for item in claimed if item is not None]
        self.assertEqual(len(winners), 1)
        self.assertEqual(winners[0].job_id, job.job_id)
        self.assertEqual(self.store.get_job(job.job_id).attempts, 1)

    def test_expired_database_lease_is_reclaimed_by_another_worker(self) -> None:
        job, _ = self.enqueue()
        first = self.store.claim('worker-1', 60, now=now())
        assert first is not None
        with self.store._connect() as connection:
            connection.execute(
                "UPDATE trust_ci_jobs SET lease_expires_at = now() - interval '1 second' WHERE job_id = %s",
                (job.job_id,),
            )
            connection.commit()
        second = self.store.claim('worker-2', 60, now=now() + timedelta(minutes=1))
        assert second is not None
        self.assertEqual(second.job_id, job.job_id)
        self.assertEqual(second.lease_owner, 'worker-2')
        self.assertEqual(second.attempts, 2)

    def test_heartbeat_requires_current_lease_owner(self) -> None:
        job, _ = self.enqueue()
        self.store.claim('worker-1', 60, now=now())
        heartbeat = self.store.heartbeat(job.job_id, 'worker-1', 120, now=now() + timedelta(seconds=1))
        self.assertEqual(heartbeat.lease_owner, 'worker-1')
        with self.assertRaisesRegex(RuntimeError, 'own'):
            self.store.heartbeat(job.job_id, 'worker-2', 120, now=now() + timedelta(seconds=2))

    def test_expired_lease_at_attempt_limit_becomes_dead(self) -> None:
        job, _ = self.enqueue(max_attempts=1)
        self.store.claim('worker-1', 60, now=now())
        with self.store._connect() as connection:
            connection.execute(
                "UPDATE trust_ci_jobs SET lease_expires_at = now() - interval '1 second' WHERE job_id = %s",
                (job.job_id,),
            )
            connection.commit()
        self.assertIsNone(self.store.claim('worker-2', 60, now=now() + timedelta(minutes=1)))
        dead = self.store.get_job(job.job_id)
        self.assertEqual(dead.status, 'dead')
        self.assertEqual(dead.failure_code, 'attempts-exhausted-after-worker-loss')

    def test_duplicate_webhook_identity_returns_same_job(self) -> None:
        first, created = self.enqueue()
        second, duplicate = self.enqueue()
        self.assertTrue(created)
        self.assertFalse(duplicate)
        self.assertEqual(first.job_id, second.job_id)

    def test_approval_nonce_replay_is_rejected_by_database_constraint(self) -> None:
        signer = Signer.generate()
        payload = ApprovalPayload.new(
            actor='dmitry',
            key_id=signer.key_id,
            repository='Dimkox/adaptive-grok-build-pro',
            pr_number=701,
            base_sha=sha('a'),
            head_sha=sha('b'),
            policy_digest=digest('c'),
            scope='governance',
            reason='reviewed exact SHA',
            now=now(),
        )
        envelope = sign_approval(payload, signer)
        self.store.record_approval(payload, envelope, now=now())
        with self.assertRaises(ReplayError):
            self.store.record_approval(payload, envelope, now=now())

    def test_signed_attestation_survives_new_store_instance(self) -> None:
        job, _ = self.enqueue()
        signer = Signer.generate()
        payload = AttestationPayload(
            schema_version=1,
            attestation_id='00000000-0000-0000-0000-000000000701',
            job_id=job.job_id,
            repository=job.repository,
            pr_number=job.pr_number,
            base_sha=job.base_sha,
            head_sha=job.head_sha,
            policy_digest=job.policy_digest,
            status='passed',
            command_results=({'name': 'unit', 'status': 'pass', 'exit_code': 0, 'output_sha256': digest('d')},),
            changed_files=('docs/x.md',),
            approved_scopes=(),
            started_at=now().isoformat(),
            completed_at=(now() + timedelta(seconds=2)).isoformat(),
            key_id=signer.key_id,
        )
        envelope = sign_attestation(payload, signer)
        self.store.record_attestation(job.job_id, envelope)
        reconnected = PostgresStore(DATABASE_URL)
        stored = reconnected.get_attestation(job.job_id)
        self.assertIsNotNone(stored)
        assert stored is not None
        verified = verify_attestation(stored, signer.public_key_pem())
        self.assertEqual(verified.job_id, job.job_id)
        self.assertEqual(verified.head_sha, job.head_sha)


if __name__ == '__main__':
    unittest.main()
