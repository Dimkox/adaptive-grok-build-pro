#!/usr/bin/env python3
"""Bounded disposable-PostgreSQL lease-holder loss and stale-fence probe."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import multiprocessing
import os
from pathlib import Path
import sys
import uuid

SOURCE = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE))

from adaptive_factory.migrations import PostgresMigrator
from adaptive_factory.models import Actor, RunRole
from adaptive_factory.service import FactoryService
from adaptive_factory.store import FenceError, PostgresFactoryStore


def _claim(database_url: str, queue, payload: dict) -> None:
    service = FactoryService(PostgresFactoryStore(database_url))
    actor = Actor("lost-worker", "worker", frozenset({"task:claim"}), frozenset({"probe/repository"}))
    grant = service.claim(
        owner="lost-worker",
        role=RunRole.READER,
        repositories=("probe/repository",),
        lease_seconds=30,
        actor=actor,
        now=datetime.now(timezone.utc),
    )
    queue.put(grant)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url-env", default="FACTORY_TEST_DATABASE_URL")
    args = parser.parse_args()
    database_url = os.environ.get(args.database_url_env)
    if not database_url:
        raise SystemExit(f"{args.database_url_env} is required")
    PostgresMigrator(database_url).apply()
    import psycopg

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE factory.audit_log, factory.audit_heads, factory.task_events, factory.budget_reservations, factory.usage_observations, factory.capacity_allocations, factory.attempts, factory.runs, factory.lease_sequences, factory.kill_switches, factory.reconciliation_runs, factory.tasks, factory.accepted_intents, factory.intake_identities RESTART IDENTITY"
        )
        cursor.execute("UPDATE factory.capacity_counters SET active_count=0")
    now = datetime.now(timezone.utc)
    payload = {
        "contract_version": 1,
        "request_id": "restart-probe",
        "repository_id": "probe/repository",
        "source_type": "manual",
        "source_id": str(uuid.uuid4()),
        "source_digest": "1" * 64,
        "route_id": "b7f288f1e81e",
        "change_id": "20260831-m4-control-plane",
        "exact_base_sha": "1" * 40,
        "spec_digest": "2" * 64,
        "architecture": {
            "architecture_contract_version": 1,
            "architecture_digest": "3" * 64,
            "architecture_evidence_digest": "4" * 64,
            "exact_base_sha": "5" * 40,
            "exact_head_sha": "6" * 40,
        },
        "governance": {
            "governance_contract_version": 1,
            "governance_digest": "7" * 64,
            "governance_evidence_digest": "8" * 64,
            "architecture_digest": "3" * 64,
            "exact_base_sha": "5" * 40,
            "exact_head_sha": "6" * 40,
        },
        "policy_digest": "9" * 64,
        "m0_authority": {
            "observed_at": now.isoformat(),
            "check_name": "adaptive-trust-ci/verified@probe",
            "exact_head_sha": "6" * 40,
        },
        "acceptance_ids": ["AC-001"],
        "limits": {
            "wall_seconds": 14400,
            "max_cost_usd_micros": 25000000,
            "max_token_units": 2000000,
            "max_output_bytes": 10000000,
            "max_events": 100000,
            "infrastructure_retries": 2,
            "semantic_repairs": 3,
        },
    }
    operator = Actor("operator", "operator", frozenset({"task:submit", "factory:reconcile"}), frozenset({"*"}))
    worker = Actor("new-worker", "worker", frozenset({"task:claim", "task:heartbeat"}), frozenset({"probe/repository"}))
    service = FactoryService(PostgresFactoryStore(database_url))
    service.intake(payload, actor=operator, now=now)
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=_claim, args=(database_url, queue, payload))
    process.start()
    process.join(timeout=10)
    if process.is_alive():
        process.kill()
        process.join(timeout=5)
    old = queue.get(timeout=5)
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",
            (old.run_id,),
        )
    result = service.reconcile(actor=operator, now=now)
    new = service.claim(
        owner="new-worker",
        role=RunRole.READER,
        repositories=("probe/repository",),
        lease_seconds=30,
        actor=worker,
        now=now,
    )
    if result.repaired != 1 or new is None or new.fence <= old.fence:
        raise SystemExit("restart reconciliation did not issue a higher fence")
    try:
        service.heartbeat(old, actor=worker, now=now)
    except FenceError:
        print("PASS: expired holder reclaimed once; higher fence issued; late heartbeat rejected")
        return 0
    raise SystemExit("late heartbeat unexpectedly succeeded")


if __name__ == "__main__":
    raise SystemExit(main())
