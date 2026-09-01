#!/usr/bin/env python3
"""Actual disposable PostgreSQL restart and idempotent reconciliation probe."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import time
import re
import uuid

SOURCE = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE))

from adaptive_factory.migrations import PostgresMigrator
from adaptive_factory.models import Actor, RunRole
from adaptive_factory.service import FactoryService
from adaptive_factory.store import FenceError, PostgresFactoryStore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url-env", default="FACTORY_TEST_DATABASE_URL")
    parser.add_argument("--container-name-env", default="FACTORY_TEST_POSTGRES_CONTAINER")
    args = parser.parse_args()
    database_url = os.environ.get(args.database_url_env)
    container_name = os.environ.get(args.container_name_env)
    if not database_url or not container_name:
        raise SystemExit(f"{args.database_url_env} and {args.container_name_env} are required")
    PostgresMigrator(database_url).apply()
    import psycopg

    now = datetime.now(timezone.utc).replace(microsecond=0)
    policy_digest = "0123456789ab" + "9" * 52
    check_name = "adaptive-trust-ci/verified@0123456789ab"
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE factory.audit_log, factory.audit_heads, factory.task_events, factory.command_results, factory.metric_counters, factory.budget_reservations, factory.usage_observations, factory.capacity_allocations, factory.attempts, factory.runs, factory.lease_sequences, factory.kill_switches, factory.reconciliation_runs, factory.tasks, factory.accepted_intents, factory.intake_identities, factory.m0_authority_observations, factory.m0_bootstrap_exceptions RESTART IDENTITY"
        )
        cursor.execute("UPDATE factory.capacity_counters SET active_count=0")
        cursor.execute(
            "INSERT INTO factory.m0_authority_observations(observation_id,observed_at,check_name,exact_head_sha,issuer,evidence_digest,repository_id,policy_digest) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (uuid.uuid4(), now, check_name, "6" * 40, "external-test-verifier", "a" * 64, "probe/repository", policy_digest),
        )
    payload = {
        "contract_version": 1, "request_id": "restart-probe", "repository_id": "probe/repository",
        "source_type": "manual", "source_id": str(uuid.uuid4()), "source_digest": "1" * 64,
        "route_id": "b7f288f1e81e", "change_id": "20260831-m4-control-plane", "exact_base_sha": "1" * 40,
        "spec_digest": "2" * 64,
        "architecture": {"architecture_contract_version": 1, "architecture_digest": "3" * 64, "architecture_evidence_digest": "4" * 64, "exact_base_sha": "5" * 40, "exact_head_sha": "6" * 40},
        "governance": {"governance_contract_version": 1, "governance_digest": "7" * 64, "governance_evidence_digest": "8" * 64, "architecture_digest": "3" * 64, "exact_base_sha": "5" * 40, "exact_head_sha": "6" * 40},
        "policy_digest": policy_digest,
        "m0_authority": {"observed_at": now.isoformat(), "check_name": check_name, "exact_head_sha": "6" * 40},
        "acceptance_ids": ["AC-001"],
        "limits": {"wall_seconds": 14400, "max_cost_usd_micros": 25000000, "max_token_units": 2000000, "max_output_bytes": 10000000, "max_events": 100000, "infrastructure_retries": 2, "semantic_repairs": 3},
    }
    operator = Actor("operator", "operator", frozenset({"task:submit", "factory:reconcile"}), frozenset({"*"}))
    lost_worker = Actor("lost-worker", "worker", frozenset({"task:claim", "task:heartbeat"}), frozenset({"probe/repository"}))
    service = FactoryService(PostgresFactoryStore(database_url))
    service.intake(payload, actor=operator, now=now)
    old = service.claim(owner=lost_worker.actor_id, role=RunRole.READER, repositories=("probe/repository",), lease_seconds=30, actor=lost_worker, now=now)
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (old.run_id,))

    subprocess.run(["docker", "restart", container_name], check=True, timeout=30, stdout=subprocess.DEVNULL)
    published = subprocess.run(
        ["docker", "port", container_name, "5432/tcp"], check=True, text=True, capture_output=True, timeout=10
    ).stdout.strip()
    new_port = int(published.rsplit(":", 1)[1])
    database_url = re.sub(r"(?<=@)127\.0\.0\.1:\d+(?=/)", f"127.0.0.1:{new_port}", database_url, count=1)
    deadline = time.monotonic() + 30
    while True:
        try:
            with psycopg.connect(database_url, connect_timeout=2) as connection:
                connection.execute("SELECT 1")
            break
        except psycopg.OperationalError:
            if time.monotonic() >= deadline:
                raise SystemExit("PostgreSQL did not become ready after actual restart")
            time.sleep(0.25)

    fresh = FactoryService(PostgresFactoryStore(database_url))
    first = fresh.reconcile(actor=operator, now=datetime.now(timezone.utc))
    second = fresh.reconcile(actor=operator, now=datetime.now(timezone.utc))
    new_worker = Actor("new-worker", "worker", frozenset({"task:claim"}), frozenset({"probe/repository"}))
    new = fresh.claim(owner=new_worker.actor_id, role=RunRole.READER, repositories=("probe/repository",), lease_seconds=30, actor=new_worker, now=datetime.now(timezone.utc))
    if first.repaired != 1 or second.repaired != 0 or new is None or new.fence <= old.fence:
        raise SystemExit("restart reconciliation was not exactly-once or did not issue a higher fence")
    try:
        fresh.heartbeat(old, actor=lost_worker, now=datetime.now(timezone.utc))
    except FenceError:
        print("PASS: PostgreSQL restarted; one repair; replay no-op; higher fence; late holder rejected")
        return 0
    raise SystemExit("late heartbeat unexpectedly succeeded")


if __name__ == "__main__":
    raise SystemExit(main())
