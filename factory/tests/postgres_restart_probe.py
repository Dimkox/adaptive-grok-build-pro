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
import uuid

SOURCE = Path(__file__).resolve().parents[1] / "src"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE))
sys.path.insert(0, str(ROOT))

from adaptive_factory.admin import provision_artifact_attestor_login, provision_runtime_login
from adaptive_factory.migrations import PostgresMigrator
from adaptive_factory.models import Actor, RunRole, TaskStatus
from adaptive_factory.recovery import ExecutionRecovery
from adaptive_factory.service import FactoryService
from adaptive_factory.store import FenceError, PostgresArtifactAttestationStore, PostgresFactoryStore
from adaptive_factory.workspace import (
    ArtifactAttestationV1,
    FakeWorkspaceBroker,
    WorkspaceHandle,
    WorkspacePolicy,
)
from factory.tests.test_execution_contracts import valid_packet
from factory.tests.test_execution_service import trusted_registry


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
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    runtime_login = "factory_restart_runtime"
    runtime_password = "local-restart-runtime-test"
    attestor_login = "factory_restart_attestor"
    attestor_password = "local-restart-attestor-test"
    provision_runtime_login(database_url, runtime_login, runtime_password)
    provision_artifact_attestor_login(
        database_url, attestor_login, attestor_password, runtime_login=runtime_login,
    )
    runtime_url = make_conninfo(**{
        **conninfo_to_dict(database_url), "user": runtime_login,
        "password": runtime_password,
    })
    attestor_url = make_conninfo(**{
        **conninfo_to_dict(database_url), "user": attestor_login,
        "password": attestor_password,
    })

    now = datetime.now(timezone.utc).replace(microsecond=0)
    policy_digest = "0123456789ab" + "9" * 52
    check_name = "adaptive-trust-ci/verified@0123456789ab"
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE factory.execution_recovery_cleanup_successes, factory.execution_recovery_cleanup_failures, factory.workspace_results, factory.execution_proposals, factory.execution_artifact_attestations, factory.execution_stage_events, factory.execution_manifests, factory.execution_packets, factory.audit_log, factory.audit_heads, factory.task_events, factory.command_results, factory.metric_counters, factory.budget_reservations, factory.usage_observations, factory.capacity_allocations, factory.attempts, factory.runs, factory.lease_sequences, factory.kill_switches, factory.reconciliation_runs, factory.tasks, factory.accepted_intents, factory.intake_identities, factory.m0_authority_observations, factory.m0_bootstrap_exceptions RESTART IDENTITY"
        )
        cursor.execute("TRUNCATE factory.kill_switch_heads")
        cursor.execute("INSERT INTO factory.metric_counters(singleton) VALUES (true)")
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
    lost_worker = Actor(
        "lost-worker", "worker",
        frozenset({"task:claim", "task:execute", "task:heartbeat"}),
        frozenset({"probe/repository"}),
    )
    packet = valid_packet()
    packet["provider"]["capabilities"] = sorted(
        {*packet["provider"]["capabilities"], "artifacts"}
    )
    selection = {
        "provider": packet["provider"],
        "capability_policy": packet["capability_policy"],
        "plan": packet["plan"],
        "workspace_handle": packet["workspace_handle"],
        "prompt_template_digest": "7" * 64,
        "role_definition_digest": "8" * 64,
        "tool_policy_digest": "9" * 64,
        "output_schema_digest": "a" * 64,
    }
    service = FactoryService(
        PostgresFactoryStore(runtime_url), execution_registry=trusted_registry(selection),
    )
    zero_payload = {
        **payload,
        "request_id": "restart-probe-zero-retries",
        "source_id": str(uuid.uuid4()),
        "limits": {**payload["limits"], "infrastructure_retries": 0},
    }
    two_payload = {
        **payload,
        "request_id": "restart-probe-two-retries",
        "source_id": str(uuid.uuid4()),
        "limits": {**payload["limits"], "infrastructure_retries": 2},
    }
    zero_task = service.intake(zero_payload, actor=operator, now=now).task
    old_zero = service.claim(
        owner=lost_worker.actor_id, role=RunRole.READER,
        repositories=("probe/repository",), lease_seconds=30,
        actor=lost_worker, now=now,
    )
    two_task = service.intake(two_payload, actor=operator, now=now).task
    old_two = service.claim_execution(
        owner=lost_worker.actor_id, role=RunRole.WRITER,
        repositories=("probe/repository",), lease_seconds=30, selection=selection,
        actor=lost_worker, now=now,
    )
    workspace = FakeWorkspaceBroker()
    workspace.register(
        WorkspaceHandle(
            old_two.lease.task_id, old_two.lease.run_id, old_two.workspace_handle,
        ),
        WorkspacePolicy(("factory/src",), ("read", "write"), ("LANG",), ()),
    )
    attestation = ArtifactAttestationV1.from_facts({
        "contract_version": 1,
        "task_id": old_two.lease.task_id,
        "run_id": old_two.lease.run_id,
        "repository_id": "probe/repository",
        "packet_digest": old_two.packet_digest,
        "workspace_handle": old_two.workspace_handle,
        "producer_sequence": 1,
        "fence": old_two.lease.fence,
        "author_role": "writer",
        "artifact_class": "report",
        "path": "factory/src/restart-evidence.patch",
        "sha256": "b" * 64,
        "size_bytes": 12,
        "media_type": "text/plain",
        "source": "trusted_workspace_broker",
    })
    if PostgresArtifactAttestationStore(attestor_url).record_artifact_attestation(
        attestation,
    ) != attestation:
        raise SystemExit("restart probe could not seed exact artifact attestation")
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE factory.runs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=ANY(%s)",
            ([old_zero.run_id, old_two.lease.run_id],),
        )
        cursor.execute(
            "SELECT coalesce(jsonb_agg(to_jsonb(a) ORDER BY a.artifact_attestation_digest),'[]') FROM factory.execution_artifact_attestations a"
        )
        attestations_before = cursor.fetchone()[0]

    subprocess.run(["docker", "restart", container_name], check=True, timeout=30, stdout=subprocess.DEVNULL)
    published = subprocess.run(
        ["docker", "port", container_name, "5432/tcp"], check=True, text=True, capture_output=True, timeout=10
    ).stdout.strip()
    new_port = int(published.rsplit(":", 1)[1])
    database_url = make_conninfo(**{
        **conninfo_to_dict(database_url), "port": new_port,
    })
    runtime_url = make_conninfo(**{
        **conninfo_to_dict(runtime_url), "port": new_port,
    })
    attestor_url = make_conninfo(**{
        **conninfo_to_dict(attestor_url), "port": new_port,
    })
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

    if PostgresArtifactAttestationStore(attestor_url).readiness()["session_user"] != attestor_login:
        raise SystemExit("artifact attestor capability did not survive restart")

    fresh_store = PostgresFactoryStore(runtime_url)
    fresh = FactoryService(fresh_store)
    first = fresh.reconcile(actor=operator, now=datetime.now(timezone.utc))
    second = fresh.reconcile(actor=operator, now=datetime.now(timezone.utc))
    zero_status = fresh.store.get_task(zero_task.task_id).status
    two_status = fresh.store.get_task(two_task.task_id).status
    recovery = ExecutionRecovery(fresh_store, workspace)
    m5 = recovery.reconcile(limit=100)
    m5_replay = recovery.reconcile(limit=100, cursor=m5.cursor)
    new_worker = Actor(
        "new-worker", "worker", frozenset({"task:claim", "task:execute"}),
        frozenset({"probe/repository"}),
    )
    replacement = FactoryService(
        fresh_store, execution_registry=trusted_registry(selection),
    ).claim_execution(
        owner=new_worker.actor_id, role=RunRole.WRITER,
        repositories=("probe/repository",), lease_seconds=30, selection=selection,
        actor=new_worker, now=datetime.now(timezone.utc),
    )
    if (
        first.repaired != 2
        or second.repaired != 0
        or zero_status is not TaskStatus.DEAD
        or two_status is not TaskStatus.RETRY
        or m5.orphaned != 1
        or m5_replay.candidates != 0
        or replacement is None
        or replacement.lease.task_id != two_task.task_id
        or replacement.lease.fence <= old_two.lease.fence
    ):
        raise SystemExit(
            "restart recovery did not preserve retry limits and M5 orphan fencing"
        )
    try:
        fresh.commit_execution_proposal(
            old_two.lease, packet_digest=old_two.packet_digest, sequence=1,
            event_type="note.proposed",
            payload={"note_type": "finding", "body": "late", "evidence": []},
            actor=lost_worker,
        )
    except FenceError:
        pass
    else:
        raise SystemExit("late execution proposal unexpectedly succeeded")
    try:
        fresh.heartbeat(old_two.lease, actor=lost_worker, now=datetime.now(timezone.utc))
    except FenceError:
        pass
    else:
        raise SystemExit("late heartbeat unexpectedly succeeded")
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """SELECT
            (SELECT count(*) FROM factory.execution_stage_events e
              JOIN factory.execution_manifests m USING(manifest_digest)
              WHERE m.run_id=%s AND e.stage='orphaned'),
            (SELECT count(*) FROM factory.workspace_results WHERE run_id=%s),
            (SELECT coalesce(jsonb_agg(to_jsonb(a) ORDER BY a.artifact_attestation_digest),'[]')
              FROM factory.execution_artifact_attestations a)""",
            (old_two.lease.run_id, old_two.lease.run_id),
        )
        orphan_events, workspace_results, attestations_after = cursor.fetchone()
    if (orphan_events, workspace_results, attestations_after) != (
        1, 0, attestations_before,
    ):
        raise SystemExit("restart recovery mutated factual evidence or duplicated orphan stage")
    print(
        "PASS: PostgreSQL restarted; retry limits persisted; two M4 repairs; "
        "M5 orphaned once; replays no-op; higher fence; late holder rejected"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
