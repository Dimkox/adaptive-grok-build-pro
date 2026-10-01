"""Shared PostgreSQL assertions for the bounded Factory v1.5 decision contour."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
from functools import partial

from adaptive_factory.contracts import canonical_digest, canonical_json
from adaptive_factory.decision_contracts import DecisionRecordV1
from adaptive_factory.models import RunRole, TaskStatus
from adaptive_factory.store import PostgresFactoryStore, StoreError
from tests.factory_v15_decision_cases import decision_facts


def assert_v15_decision_persistence(case, *, database_url, worker, now, psycopg):
    """Exercise atomic append, exact replay, supersession and least privilege."""
    unavailable = "cc37cbe49cbf74f722413d345a76197162a263353554ae3eb463da8fc249c14d"
    task = case.submit(source="v15-decision").task
    grant = case.service.claim(
        owner=worker.actor_id,
        role=RunRole.READER,
        repositories=(task.repository_id,),
        lease_seconds=60,
        actor=worker,
        now=now,
    )
    with psycopg.connect(database_url) as connection:
        attempt, base_sha, spec_digest, head_sha = connection.execute(
            """SELECT a.attempt_id,i.exact_base_sha,i.spec_digest,
            i.body->'m0_authority'->>'exact_head_sha'
            FROM factory.attempts a JOIN factory.tasks t ON t.task_id=a.task_id
            JOIN factory.accepted_intents i ON i.intent_id=t.intent_id
            WHERE a.run_id=%s""",
            (grant.run_id,),
        ).fetchone()
    facts = decision_facts()
    facts.update(
        repository_id=task.repository_id,
        task_id=grant.task_id,
        run_id=grant.run_id,
        attempt_id=str(attempt),
        fence=grant.fence,
        base_sha=base_sha,
        head_sha=head_sha,
        spec_digest=spec_digest,
        context_digest=unavailable,
        profile_digest=unavailable,
        rule_id="FACTORY-STATE-TRANSITION",
        evidence_refs=[],
    )
    record = DecisionRecordV1.from_dict(facts)
    key = "9" * 64
    call = partial(
        case.service.transition_phase,
        grant,
        target=TaskStatus.ANALYZING,
        actor=worker,
        now=now,
        idempotency_key=key,
        decision_record=record,
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        case.assertEqual(
            tuple(pool.map(lambda _: call(), range(2))),
            (TaskStatus.ANALYZING,) * 2,
        )
    case.assertEqual(
        case.store.transition_phase(
            grant,
            TaskStatus.ANALYZING,
            worker,
            now,
            idempotency_key=key,
            decision_record=record,
        ),
        TaskStatus.ANALYZING,
    )
    with case.assertRaises(StoreError):
        case.store.transition_phase(
            grant, TaskStatus.ANALYZING, worker, now, idempotency_key=key
        )
    changed = record.to_dict()
    changed["decision_id"] = "changed-replay-decision"
    with case.assertRaises(StoreError):
        case.store.transition_phase(
            grant,
            TaskStatus.ANALYZING,
            worker,
            now,
            idempotency_key=key,
            decision_record=DecisionRecordV1.from_dict(changed),
        )
    facts["facts"] = [
        {"name": "from_state", "value": "analyzing"},
        {"name": "target", "value": "implementing"},
    ]
    facts.update(decision_id="decision-2", supersedes="decision-1")
    correction = DecisionRecordV1.from_dict(facts)
    case.store.transition_phase(
        grant,
        TaskStatus.IMPLEMENTING,
        worker,
        now,
        idempotency_key="7" * 64,
        decision_record=correction,
    )
    with psycopg.connect(database_url) as connection:
        saved = connection.execute(
            "SELECT record FROM factory.decision_records_v1 "
            "WHERE decision_id='decision-2'"
        ).fetchone()[0]
        for field, value in (("schema_version", "1"), ("fence", "1")):
            bad = dict(saved)
            bad[field] = value
            with case.assertRaises(psycopg.errors.RaiseException):
                connection.execute(
                    "SELECT factory._append_decision_v1(%s,%s,%s,%s)",
                    (
                        canonical_json(bad).decode(),
                        canonical_digest(bad),
                        grant.run_id,
                        grant.fence,
                    ),
                )
            connection.rollback()
    with psycopg.connect(case.runtime_url) as db:
        db.execute("SET ROLE factory_runtime")
        with case.assertRaises(psycopg.errors.InsufficientPrivilege):
            db.execute("INSERT INTO factory.decision_records_v1 DEFAULT VALUES")
        db.rollback()
        db.execute("SET ROLE factory_runtime")
        with case.assertRaises(psycopg.errors.InsufficientPrivilege):
            db.execute(
                "SELECT factory._append_decision_v1(%s,%s,%s,%s)",
                ("{}", "0" * 64, grant.run_id, grant.fence),
            )
        db.rollback()
        db.execute("SET ROLE factory_runtime")
        forged = dict(saved)
        forged["decision_id"] = "direct-forgery"
        with case.assertRaises(psycopg.errors.RaiseException):
            db.execute(
                "SELECT factory.persist_phase_decision_v1(%s,%s,%s,%s,%s,%s)",
                (
                    canonical_json(forged).decode(),
                    canonical_digest(forged),
                    grant.run_id,
                    grant.fence,
                    "7" * 64,
                    correction.record_digest,
                ),
            )
        db.rollback()
        db.execute("SET ROLE factory_runtime")
        bad_wire = " " + canonical_json(saved).decode()
        with case.assertRaises(psycopg.errors.RaiseException):
            db.execute(
                "SELECT factory.persist_phase_decision_v1(%s,%s,%s,%s,%s,%s)",
                (
                    bad_wire,
                    hashlib.sha256(bad_wire.encode()).hexdigest(),
                    grant.run_id,
                    grant.fence,
                    "7" * 64,
                    correction.record_digest,
                ),
            )

    class FailingStore(PostgresFactoryStore):
        def _audit(self, *args, **kwargs):
            if args[3] == "phase_transition":
                raise StoreError("injected decision audit failure")
            return super()._audit(*args, **kwargs)

    failed = correction.to_dict()
    failed.update(
        decision_id="rollback-decision",
        supersedes="decision-2",
        facts=[
            {"name": "from_state", "value": "implementing"},
            {"name": "target", "value": "verifying"},
        ],
    )
    with case.assertRaisesRegex(StoreError, "decision audit"):
        FailingStore(case.runtime_url).transition_phase(
            grant,
            TaskStatus.VERIFYING,
            worker,
            now,
            idempotency_key="8" * 64,
            decision_record=DecisionRecordV1.from_dict(failed),
        )
    with psycopg.connect(database_url) as connection:
        case.assertEqual(
            connection.execute(
                """SELECT t.state,
                (SELECT count(*) FROM factory.task_events
                 WHERE task_id=t.task_id AND action='phase_transitioned'),
                (SELECT count(*) FROM factory.audit_log
                 WHERE task_id=t.task_id AND action='phase_transition'),
                (SELECT count(*) FROM factory.command_results
                 WHERE idempotency_key=%s),
                (SELECT count(*) FROM factory.decision_records_v1
                 WHERE task_id=t.task_id)
                FROM factory.tasks t WHERE task_id=%s""",
                ("8" * 64, task.task_id),
            ).fetchone(),
            ("implementing", 2, 2, 0, 2),
        )
