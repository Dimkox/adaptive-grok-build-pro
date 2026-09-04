#!/usr/bin/env python3
"""Exercise M5 execution recovery across two actual PostgreSQL restarts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

SOURCE = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE))

from adaptive_factory.adapters import (
    AdapterConformance,
    AdapterRegistry,
    TrustedExecutionProfile,
)
from adaptive_factory.admin import (
    provision_artifact_attestor_login,
    provision_runtime_login,
)
from adaptive_factory.execution_contracts import ExecutionSelectionV1
from adaptive_factory.migrations import PostgresMigrator
from adaptive_factory.models import (
    Actor,
    ExecutionStage,
    FailureClass,
    RunRole,
    TaskStatus,
)
from adaptive_factory.recovery import (
    ExecutionRecovery,
    ExecutionRecoveryClaim,
)
from adaptive_factory.service import FactoryService
from adaptive_factory.store import (
    FenceError,
    PostgresArtifactAttestationStore,
    PostgresFactoryStore,
    StoreError,
)
from adaptive_factory.workspace import (
    FakeWorkspaceBroker,
    WorkspaceHandle,
    WorkspacePolicy,
    WorkspaceReleaseOutcome,
)


_CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")
_NONCE = re.compile(r"^[0-9a-f]{32}$")
_DATABASE_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


def _database_url_for_login(database_url: str, login: str, password: str) -> str:
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    values = conninfo_to_dict(database_url)
    return make_conninfo(**{**values, "user": login, "password": password})


def _database_url_at_port(database_url: str, port: int) -> str:
    if type(port) is not int or not 1 <= port <= 65_535:
        raise ValueError("invalid PostgreSQL port")
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    values = conninfo_to_dict(database_url)
    return make_conninfo(**{**values, "host": "127.0.0.1", "port": str(port)})


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _published_port(container_name: str) -> int:
    published = subprocess.run(
        ["docker", "port", container_name, "5432/tcp"],
        check=True,
        text=True,
        capture_output=True,
        timeout=10,
    ).stdout.strip()
    lines = published.splitlines()
    if len(lines) != 1:
        raise RuntimeError("PostgreSQL published port is ambiguous")
    match = re.fullmatch(r"127\.0\.0\.1:([0-9]{1,5})", lines[0])
    if match is None:
        raise RuntimeError("PostgreSQL published port is not loopback-only")
    try:
        port = int(match.group(1))
    except ValueError as exc:
        raise RuntimeError("PostgreSQL published port is unavailable") from exc
    if not 1 <= port <= 65_535:
        raise RuntimeError("PostgreSQL published port is invalid")
    return port


def _assert_disposable_target(
    database_url: str,
    container_name: str,
    container_id: str,
    nonce: str,
) -> None:
    """Fail before mutation unless the URL is bound to the named disposable DB."""

    if (
        not re.fullmatch(r"adaptive-factory-exit-[0-9a-f]{12}", container_name)
        or not _CONTAINER_ID.fullmatch(container_id)
        or not _NONCE.fullmatch(nonce)
    ):
        raise RuntimeError("invalid disposable PostgreSQL identity")
    metadata = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            '{{.Id}}\t{{.Name}}\t{{.Config.Image}}\t{{.State.Running}}\t'
            '{{index .Config.Labels "adaptive-factory.disposable-exit"}}',
            container_id,
        ],
        check=True,
        text=True,
        capture_output=True,
        timeout=10,
    ).stdout.strip().split("\t")
    if metadata != [
        container_id,
        f"/{container_name}",
        "postgres:17-alpine",
        "true",
        nonce,
    ]:
        raise RuntimeError("disposable PostgreSQL container binding mismatch")

    from psycopg.conninfo import conninfo_to_dict

    values = conninfo_to_dict(database_url)
    if (
        set(values) != {"user", "password", "dbname", "host", "port"}
        or values.get("user") != "factory_exit"
        or values.get("dbname") != "factory_exit"
        or values.get("host") != "127.0.0.1"
        or values.get("port") != str(_published_port(container_id))
        or not values.get("password")
        or not _DATABASE_ID.fullmatch(values["user"])
        or not _DATABASE_ID.fullmatch(values["dbname"])
    ):
        raise RuntimeError("database URL is not the named disposable PostgreSQL")
    pid1 = subprocess.run(
        [
            "docker",
            "exec",
            container_id,
            "sh",
            "-c",
            'test "$(sed -n "1p" "$PGDATA/postmaster.pid")" = 1',
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    if pid1.returncode != 0:
        raise RuntimeError("disposable PostgreSQL is not the final PID1 postmaster")

    import psycopg

    with psycopg.connect(database_url, connect_timeout=2) as connection:
        direct = connection.execute(
            "SELECT current_database(),session_user,"
            "current_setting('server_version_num')::integer,"
            "system_identifier::text FROM pg_control_system()"
        ).fetchone()
    inside = subprocess.run(
        [
            "docker",
            "exec",
            container_id,
            "psql",
            "--no-psqlrc",
            "--tuples-only",
            "--no-align",
            "--username=factory_exit",
            "--dbname=factory_exit",
            "--command=SELECT system_identifier::text FROM pg_control_system()",
        ],
        check=True,
        text=True,
        capture_output=True,
        timeout=10,
    ).stdout.strip()
    if not _database_session_is_bound(direct, inside):
        raise RuntimeError("disposable database session identity is invalid")


def _database_session_is_bound(direct, inside: str) -> bool:
    return bool(
        isinstance(direct, tuple)
        and len(direct) == 4
        and direct[:2] == ("factory_exit", "factory_exit")
        and type(direct[2]) is int
        and 170_000 <= direct[2] < 180_000
        and isinstance(direct[3], str)
        and direct[3] == inside
        and bool(inside)
    )


def _wait_for_database(database_url: str) -> None:
    import psycopg

    deadline = time.monotonic() + 30
    while True:
        try:
            with psycopg.connect(database_url, connect_timeout=2) as connection:
                connection.execute("SELECT 1")
            return
        except psycopg.OperationalError:
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "PostgreSQL did not become ready after actual restart"
                )
            time.sleep(0.25)


def _postmaster_started_at(database_url: str):
    import psycopg

    with psycopg.connect(database_url, connect_timeout=2) as connection:
        return connection.execute("SELECT pg_postmaster_start_time()").fetchone()[0]


def _database_identity(database_url: str) -> tuple[object, int, tuple[tuple[object, ...], ...]]:
    import psycopg

    with psycopg.connect(database_url, connect_timeout=2) as connection:
        started_at, server_version = connection.execute(
            "SELECT pg_postmaster_start_time(),"
            "current_setting('server_version_num')::integer"
        ).fetchone()
        migrations = tuple(
            connection.execute(
                "SELECT version,name,trim(sha256) "
                "FROM factory.schema_migrations ORDER BY version"
            ).fetchall()
        )
    return started_at, server_version, migrations


def _restart_database(
    container_name: str,
    container_id: str,
    nonce: str,
    owner_url: str,
    runtime_url: str,
    attestor_url: str,
):
    _assert_disposable_target(
        owner_url, container_name, container_id, nonce
    )
    previous_start = _postmaster_started_at(owner_url)
    subprocess.run(
        ["docker", "restart", container_id],
        check=True,
        timeout=30,
        stdout=subprocess.DEVNULL,
    )
    port = _published_port(container_id)
    urls = tuple(
        _database_url_at_port(value, port)
        for value in (owner_url, runtime_url, attestor_url)
    )
    _wait_for_database(urls[0])
    _assert_disposable_target(
        urls[0], container_name, container_id, nonce
    )
    _require(
        _postmaster_started_at(urls[0]) > previous_start,
        "docker restart did not replace the PostgreSQL postmaster",
    )
    return urls


def _assert_capability_roles(
    owner_url: str,
    runtime_url: str,
    attestor_url: str,
    runtime_login: str,
    attestor_login: str,
) -> PostgresFactoryStore:
    runtime = PostgresFactoryStore(runtime_url)
    readiness = runtime.readiness()
    _require(
        readiness
        == {
            "status": "ready",
            "session_user": runtime_login,
            "database_role": "factory_runtime",
            "schema_version": 18,
            "capacity_consistent": True,
            "accounting_consistent": True,
        },
        "runtime capability is not ready after restart",
    )
    attestor = PostgresArtifactAttestationStore(attestor_url)
    _require(
        attestor.readiness()
        == {
            "session_user": attestor_login,
            "database_role": "factory_artifact_attestor",
        },
        "artifact attestor capability is not ready after restart",
    )
    for forbidden in (
        PostgresFactoryStore(owner_url).readiness,
        PostgresArtifactAttestationStore(owner_url).readiness,
    ):
        try:
            forbidden()
        except StoreError:
            pass
        else:
            raise RuntimeError("owner login crossed a least-privilege capability")
    return runtime


def _reset_database(database_url: str, now: datetime) -> tuple[object, ...]:
    import psycopg

    observation = (
        uuid.uuid4(),
        now,
        "adaptive-trust-ci/verified@06ecf1c875bc",
        "3" * 40,
        "external-trust-ci-api",
        "7" * 64,
        "probe/repository",
        "06ecf1c875bc" + "9" * 52,
    )
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "TRUNCATE factory.semantic_recovery_records, "
            "factory.semantic_escalations, factory.semantic_child_task_bindings, "
            "factory.semantic_child_proposals, factory.semantic_directives, "
            "factory.semantic_verdicts, factory.semantic_coverage, "
            "factory.semantic_findings, factory.semantic_assignments, "
            "factory.semantic_metric_events, factory.semantic_command_results, "
            "factory.semantic_subjects, factory.execution_recovery_outcomes, "
            "factory.execution_recovery_claims, factory.execution_recovery_jobs, "
            "factory.workspace_results, factory.execution_artifact_attestations, "
            "factory.execution_proposals, factory.execution_stage_events, "
            "factory.execution_manifests, factory.execution_packets, "
            "factory.audit_log, factory.audit_heads, factory.task_events, "
            "factory.command_results, factory.metric_counters, "
            "factory.budget_reservations, factory.usage_observations, "
            "factory.capacity_allocations, factory.attempts, factory.runs, "
            "factory.lease_sequences, factory.kill_switches, "
            "factory.reconciliation_runs, factory.tasks, factory.accepted_intents, "
            "factory.intake_identities, factory.m0_authority_observations, "
            "factory.m0_bootstrap_exceptions RESTART IDENTITY"
        )
        cursor.execute("TRUNCATE factory.kill_switch_heads")
        cursor.execute("INSERT INTO factory.metric_counters(singleton) VALUES (true)")
        cursor.execute("UPDATE factory.capacity_counters SET active_count=0")
        cursor.execute(
            "UPDATE factory.execution_metric_counters SET "
            "execution_claimed=0,stage_prepared=0,stage_running=0,"
            "stage_collecting=0,stage_completed=0,stage_failed=0,"
            "stage_needs_human=0,stage_cancelled=0,stage_orphaned=0,"
            "proposal_note=0,proposal_artifact=0,proposal_usage=0,"
            "proposal_terminal=0,recovery_claimed=0,recovery_orphaned=0,"
            "recovery_cancelled=0,cleanup_succeeded=0,cleanup_failed=0"
        )
        cursor.execute(
            "INSERT INTO factory.m0_authority_observations("
            "observation_id,observed_at,check_name,exact_head_sha,issuer,"
            "evidence_digest,repository_id,policy_digest) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            observation,
        )
    return observation


def _payload(now: datetime, label: str) -> dict[str, object]:
    return {
        "contract_version": 1,
        "request_id": f"restart-probe-{label}",
        "repository_id": "probe/repository",
        "source_type": "manual",
        "source_id": str(uuid.uuid4()),
        "source_digest": ("1" if label == "cancelled" else "2") * 64,
        "route_id": "b7f288f1e81e",
        "change_id": "20260901-m5-execution",
        "exact_base_sha": "1" * 40,
        "spec_digest": "a" * 64,
        "architecture": {
            "architecture_contract_version": 1,
            "architecture_digest": "b" * 64,
            "architecture_evidence_digest": "c" * 64,
            "exact_base_sha": "2" * 40,
            "exact_head_sha": "3" * 40,
        },
        "governance": {
            "governance_contract_version": 1,
            "governance_digest": "e" * 64,
            "governance_evidence_digest": "f" * 64,
            "architecture_digest": "b" * 64,
            "exact_base_sha": "2" * 40,
            "exact_head_sha": "3" * 40,
        },
        "policy_digest": "06ecf1c875bc" + "9" * 52,
        "m0_authority": {
            "observed_at": now.isoformat(),
            "check_name": "adaptive-trust-ci/verified@06ecf1c875bc",
            "exact_head_sha": "3" * 40,
        },
        "acceptance_ids": ["AC-001", "AC-008"],
        "limits": {
            "wall_seconds": 14_400,
            "max_cost_usd_micros": 25_000_000,
            "max_token_units": 2_000_000,
            "max_output_bytes": 10_000_000,
            "max_events": 100_000,
            "infrastructure_retries": 2,
            "semantic_repairs": 3,
        },
    }


def _selection(workspace_handle: str) -> ExecutionSelectionV1:
    return ExecutionSelectionV1.from_dict(
        {
            "provider": {
                "provider_id": "codex",
                "adapter_id": "adaptive-factory.codex",
                "adapter_version": "1.0.0",
                "adapter_digest": "b" * 64,
                "native_version": "0.152.1",
                "native_digest": "c" * 64,
                "model_id": "configured-model",
                "capabilities": ["cancellation", "structured_output", "usage"],
                "eligible": True,
            },
            "capability_policy": {
                "allowed_paths": ["factory/src"],
                "allowed_tools": ["read_file", "write_file"],
                "network_destinations": [],
                "artifact_classes": ["patch", "report"],
                "environment_names": ["LANG", "PATH"],
            },
            "plan": {
                "stages": [
                    {"name": "prepare", "owner": "broker", "wall_seconds": 30},
                    {"name": "invoke", "owner": "adapter", "wall_seconds": 300},
                    {"name": "collect", "owner": "broker", "wall_seconds": 30},
                    {
                        "name": "finalize",
                        "owner": "control_plane",
                        "wall_seconds": 30,
                    },
                ]
            },
            "workspace_handle": workspace_handle,
            "prompt_template_digest": "7" * 64,
            "role_definition_digest": "8" * 64,
            "tool_policy_digest": "9" * 64,
            "output_schema_digest": "a" * 64,
        }
    )


def _registry(selection: ExecutionSelectionV1) -> AdapterRegistry:
    provider = selection.provider
    conformance = AdapterConformance(
        provider_id=provider.provider_id,
        native_version=provider.native_version,
        distribution_digest_hint=provider.native_digest,
        capabilities=provider.capabilities,
        missing_capabilities=(),
        fixture_conformant=True,
        execution_eligible=True,
        adapter_id=provider.adapter_id,
        adapter_version=provider.adapter_version,
        adapter_digest=provider.adapter_digest,
        native_digest=provider.native_digest,
    )
    return AdapterRegistry(
        (TrustedExecutionProfile(selection, conformance, ("reader", "writer")),)
    )


class WorkspaceBackend:
    """Persistent broker state, independent of rebuilt recovery clients."""

    def __init__(self) -> None:
        self.delegate = FakeWorkspaceBroker()
        self.known: set[WorkspaceHandle] = set()
        self.active: set[WorkspaceHandle] = set()
        self.outcomes: list[tuple[WorkspaceHandle, float, str]] = []

    def register(self, handle: WorkspaceHandle) -> None:
        _require(handle not in self.known, "duplicate workspace registration")
        self.delegate.register(
            handle,
            WorkspacePolicy(
                ("factory/src",), ("read", "write"), ("LANG", "PATH"), ()
            ),
        )
        self.known.add(handle)
        self.active.add(handle)


class AmbiguousWorkspaceReleaser:
    """Fresh bounded client over persistent exact-handle broker state."""

    def __init__(
        self,
        backend: WorkspaceBackend,
        *,
        ambiguous: WorkspaceHandle | None = None,
    ) -> None:
        self.backend = backend
        self.ambiguous = ambiguous
        self.failed_once = False

    def release(
        self, handle: WorkspaceHandle, *, timeout_seconds: float
    ) -> WorkspaceReleaseOutcome:
        if handle not in self.backend.known:
            raise RuntimeError("workspace cleanup targeted an unknown handle")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not 0 < float(timeout_seconds) < 30
        ):
            raise RuntimeError("workspace cleanup deadline is unbounded")
        outcome = self.backend.delegate.release(
            handle, timeout_seconds=timeout_seconds
        )
        self.backend.active.discard(handle)
        self.backend.outcomes.append(
            (handle, float(timeout_seconds), outcome.status)
        )
        if handle == self.ambiguous and not self.failed_once:
            self.failed_once = True
            raise TimeoutError("ambiguous workspace cleanup")
        return outcome


class RecordingRecoveryStore:
    """Record the exact claim objects returned by the runtime capability."""

    def __init__(self, delegate: PostgresFactoryStore) -> None:
        self.delegate = delegate
        self.claims: list[ExecutionRecoveryClaim] = []

    def execution_recovery_candidates(self, *, limit, cursor):
        return self.delegate.execution_recovery_candidates(limit=limit, cursor=cursor)

    def claim_execution_recovery(self, candidate, actor, *, timeout_seconds=5.0):
        result = self.delegate.claim_execution_recovery(
            candidate, actor, timeout_seconds=timeout_seconds
        )
        if isinstance(result, ExecutionRecoveryClaim):
            self.claims.append(result)
        return result

    def record_execution_cleanup_success(self, claim, *, timeout_seconds=5.0):
        return self.delegate.record_execution_cleanup_success(
            claim, timeout_seconds=timeout_seconds
        )

    def record_execution_cleanup_failure(self, claim, *, timeout_seconds=5.0):
        return self.delegate.record_execution_cleanup_failure(
            claim, timeout_seconds=timeout_seconds
        )


def _immutable_authority(database_url: str, run_ids: tuple[str, str]):
    import psycopg

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT trim(packet.packet_digest),packet.task_id,packet.run_id,"
            "trim(packet.legacy_packet_digest),packet.provider_id,packet.body::text,"
            "packet.created_at,trim(manifest.manifest_digest),manifest.task_id,"
            "trim(manifest.packet_digest),manifest.workspace_handle,"
            "manifest.body::text,manifest.created_at "
            "FROM factory.execution_packets packet "
            "JOIN factory.execution_manifests manifest USING(run_id) "
            "WHERE packet.run_id=ANY(%s) ORDER BY packet.run_id",
            (list(run_ids),),
        )
        execution = cursor.fetchall()
        _require(len(execution) == 2, "execution authority cardinality changed")
        cursor.execute(
            "SELECT observation_id,observed_at,check_name,trim(exact_head_sha),"
            "issuer,trim(evidence_digest),repository_id,trim(policy_digest) "
            "FROM factory.m0_authority_observations"
        )
        authority = cursor.fetchall()
    return execution, authority


def _late_fence_state(database_url: str, run_ids: tuple[str, ...]):
    """Fingerprint every execution relation a stale holder could mutate."""

    import psycopg

    run_values = list(run_ids)
    queries = (
        (
            "SELECT task.task_id,task.state,task.current_run_id,task.current_fence,"
            "task.updated_at,task.terminal_at,run.run_id,run.owner_id,run.role,"
            "run.fence,run.state,run.lease_expires_at,run.released_at,"
            "allocation.allocation_id,allocation.released_at "
            "FROM factory.runs run JOIN factory.tasks task USING(task_id) "
            "JOIN factory.capacity_allocations allocation USING(run_id) "
            "WHERE run.run_id=ANY(%s) ORDER BY run.run_id",
            (run_values,),
        ),
        (
            "SELECT attempt.* FROM factory.attempts attempt "
            "WHERE attempt.run_id=ANY(%s) ORDER BY attempt.run_id",
            (run_values,),
        ),
        (
            "SELECT event.* FROM factory.task_events event "
            "WHERE event.task_id IN (SELECT task_id FROM factory.runs "
            "WHERE run_id=ANY(%s)) ORDER BY event.task_id,event.event_sequence",
            (run_values,),
        ),
        (
            "SELECT audit.* FROM factory.audit_log audit "
            "WHERE audit.task_id IN (SELECT task_id FROM factory.runs "
            "WHERE run_id=ANY(%s)) ORDER BY audit.task_id,audit.audit_id",
            (run_values,),
        ),
        (
            "SELECT command.* FROM factory.command_results command "
            "ORDER BY command.idempotency_key",
            (),
        ),
        (
            "SELECT run_id,stage,terminal_at,updated_at FROM "
            "factory.execution_manifests WHERE run_id=ANY(%s) ORDER BY run_id",
            (run_values,),
        ),
        (
            "SELECT manifest.run_id,event.stage_sequence,event.stage,event.created_at "
            "FROM factory.execution_stage_events event JOIN "
            "factory.execution_manifests manifest USING(manifest_digest) "
            "WHERE manifest.run_id=ANY(%s) ORDER BY manifest.run_id,event.stage_sequence",
            (run_values,),
        ),
        (
            "SELECT run_id,producer_sequence,proposal_kind,body FROM "
            "factory.execution_proposals WHERE run_id=ANY(%s) "
            "ORDER BY run_id,producer_sequence",
            (run_values,),
        ),
        (
            "SELECT run_id,workspace_result_digest,body FROM "
            "factory.workspace_results WHERE run_id=ANY(%s) ORDER BY run_id",
            (run_values,),
        ),
        (
            "SELECT run_id,artifact_attestation_digest,body FROM "
            "factory.execution_artifact_attestations WHERE run_id=ANY(%s) "
            "ORDER BY run_id,artifact_attestation_digest",
            (run_values,),
        ),
        (
            "SELECT run_id,task_id,trim(manifest_digest),workspace_handle,"
            "candidate_updated_at,terminal_stage,status,claim_token,claim_fence,"
            "claim_expires_at,next_claim_at,attempt_count,failure_count,"
            "last_failure_code,last_failed_at,created_at,updated_at,completed_at "
            "FROM factory.execution_recovery_jobs "
            "WHERE run_id=ANY(%s) ORDER BY run_id",
            (run_values,),
        ),
        (
            "SELECT run_id,task_id,trim(manifest_digest),workspace_handle,"
            "candidate_updated_at,claim_fence,claim_token,transition,source,"
            "advances_discovery_cursor,claimed_at,claim_expires_at "
            "FROM factory.execution_recovery_claims "
            "WHERE run_id=ANY(%s) ORDER BY run_id,claim_fence",
            (run_values,),
        ),
        (
            "SELECT run_id,claim_fence,outcome,failure_code,recorded_at FROM "
            "factory.execution_recovery_outcomes WHERE run_id=ANY(%s) "
            "ORDER BY run_id,claim_fence",
            (run_values,),
        ),
        (
            "SELECT execution_claimed,stage_prepared,stage_running,"
            "stage_collecting,stage_completed,stage_failed,stage_needs_human,"
            "stage_cancelled,stage_orphaned,proposal_note,proposal_artifact,"
            "proposal_usage,proposal_terminal,recovery_claimed,recovery_orphaned,"
            "recovery_cancelled,cleanup_succeeded,cleanup_failed "
            "FROM factory.execution_metric_counters WHERE singleton",
            (),
        ),
        (
            "SELECT scope_key,active_count,ceiling FROM factory.capacity_counters "
            "ORDER BY scope_key",
            (),
        ),
    )
    result = []
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        for query, parameters in queries:
            cursor.execute(query, parameters)
            result.append(tuple(cursor.fetchall()))
    return tuple(result)


def _legacy_metrics(database_url: str) -> dict[str, object]:
    import psycopg

    with psycopg.connect(database_url) as connection:
        value = connection.execute(
            "SELECT to_jsonb(metric) FROM factory.metric_counters metric "
            "WHERE singleton"
        ).fetchone()[0]
    return dict(value)


def _assert_claim_persisted(
    database_url: str, claim: ExecutionRecoveryClaim
) -> None:
    import psycopg

    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            "SELECT task_id,run_id,trim(manifest_digest),workspace_handle,"
            "candidate_updated_at,source,claim_token,claim_fence,claim_expires_at,"
            "transition,advances_discovery_cursor,claimed_at "
            "FROM factory.execution_recovery_claims "
            "WHERE run_id=%s AND claim_fence=%s",
            (claim.candidate.run_id, claim.claim_fence),
        ).fetchone()
    expected = (
        claim.candidate.task_id,
        claim.candidate.run_id,
        claim.candidate.manifest_digest,
        claim.candidate.workspace_handle,
        claim.candidate.updated_at,
        claim.candidate.source,
        claim.claim_token,
        claim.claim_fence,
        claim.claim_expires_at,
        claim.transition,
        claim.advances_discovery_cursor,
    )
    _require(
        row is not None
        and tuple(
            str(value) if index in {0, 1, 6} else value
            for index, value in enumerate(row[:11])
        )
        == expected
        and row[11] < claim.claim_expires_at,
        "runtime recovery claim object does not match its complete durable tuple",
    )


def _assert_first_restart_state(
    database_url: str,
    cancelled_run: str,
    orphaned_run: str,
    cancelled_task: str,
    orphaned_task: str,
) -> None:
    """Prove each first-restart transition before retry time or restart two."""

    import psycopg

    run_ids = [cancelled_run, orphaned_run]
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT run_id,status,terminal_stage,attempt_count,failure_count,"
            "claim_fence,claim_token,claim_expires_at,next_claim_at,"
            "last_failure_code,last_failed_at,completed_at "
            "FROM factory.execution_recovery_jobs WHERE run_id=ANY(%s) "
            "ORDER BY run_id",
            (run_ids,),
        )
        jobs = {str(row[0]): row[1:] for row in cursor.fetchall()}
        cancelled = jobs.get(cancelled_run)
        orphaned = jobs.get(orphaned_run)
        _require(
            cancelled is not None
            and cancelled[:5] == ("failed", "cancelled", 1, 1, 1)
            and cancelled[5:7] == (None, None)
            and cancelled[7] is not None
            and cancelled[8] == "workspace_cleanup_failed"
            and cancelled[9] is not None
            and cancelled[10] is None
            and cancelled[7] > cancelled[9],
            "first restart did not persist the exact failed cleanup job",
        )
        _require(
            orphaned is not None
            and orphaned[:5] == ("succeeded", "orphaned", 1, 0, 1)
            and orphaned[5:10] == (None, None, None, None, None)
            and orphaned[10] is not None,
            "first restart did not persist the exact orphan cleanup success",
        )

        cursor.execute(
            "SELECT run_id,claim_fence,transition,source,"
            "advances_discovery_cursor FROM factory.execution_recovery_claims "
            "WHERE run_id=ANY(%s) ORDER BY run_id,claim_fence",
            (run_ids,),
        )
        claims: dict[str, list[tuple[object, ...]]] = {}
        for row in cursor.fetchall():
            claims.setdefault(str(row[0]), []).append(row[1:])
        _require(
            claims
            == {
                cancelled_run: [(1, "cancelled", "cleanup_retry", False)],
                orphaned_run: [(1, "orphaned", "fresh", True)],
            },
            "first restart recovery claims are not exact",
        )

        cursor.execute(
            "SELECT run_id,claim_fence,outcome,failure_code FROM "
            "factory.execution_recovery_outcomes WHERE run_id=ANY(%s) "
            "ORDER BY run_id,claim_fence",
            (run_ids,),
        )
        outcomes: dict[str, list[tuple[object, ...]]] = {}
        for row in cursor.fetchall():
            outcomes.setdefault(str(row[0]), []).append(row[1:])
        _require(
            outcomes
            == {
                cancelled_run: [(1, "failed", "workspace_cleanup_failed")],
                orphaned_run: [(1, "succeeded", None)],
            },
            "first restart recovery outcomes are not exact",
        )

        cursor.execute(
            "SELECT task_id,state FROM factory.tasks WHERE task_id=ANY(%s) "
            "ORDER BY task_id",
            ([cancelled_task, orphaned_task],),
        )
        _require(
            {str(row[0]): row[1] for row in cursor.fetchall()}
            == {
                cancelled_task: TaskStatus.CANCELLED.value,
                orphaned_task: TaskStatus.RETRY.value,
            },
            "first restart changed the expected M4 task states",
        )

        cursor.execute(
            "SELECT manifest.run_id,manifest.stage,manifest.terminal_at IS NOT NULL,"
            "array_agg(event.stage ORDER BY event.stage_sequence) "
            "FROM factory.execution_manifests manifest JOIN "
            "factory.execution_stage_events event USING(manifest_digest) "
            "WHERE manifest.run_id=ANY(%s) "
            "GROUP BY manifest.run_id,manifest.stage,manifest.terminal_at "
            "ORDER BY manifest.run_id",
            (run_ids,),
        )
        _require(
            {str(row[0]): row[1:] for row in cursor.fetchall()}
            == {
                cancelled_run: ("cancelled", True, ["prepared", "cancelled"]),
                orphaned_run: ("orphaned", True, ["prepared", "orphaned"]),
            },
            "first restart terminal stages are not canonical",
        )

        cursor.execute(
            "SELECT "
            "(SELECT count(*) FROM factory.execution_packets WHERE run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.execution_manifests WHERE run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.execution_stage_events event JOIN "
            " factory.execution_manifests manifest USING(manifest_digest) "
            " WHERE manifest.run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.execution_proposals WHERE run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.workspace_results WHERE run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.execution_artifact_attestations "
            " WHERE run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.execution_recovery_jobs WHERE run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.execution_recovery_claims WHERE run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.execution_recovery_outcomes WHERE run_id=ANY(%s))",
            tuple(run_ids for _ in range(9)),
        )
        _require(
            cursor.fetchone() == (2, 2, 4, 0, 0, 0, 2, 2, 2),
            "first restart durable cardinalities are not exact",
        )

        cursor.execute(
            "SELECT execution_claimed,stage_prepared,stage_running,"
            "stage_collecting,stage_completed,stage_failed,stage_needs_human,"
            "stage_cancelled,stage_orphaned,proposal_note,proposal_artifact,"
            "proposal_usage,proposal_terminal,recovery_claimed,recovery_orphaned,"
            "recovery_cancelled,cleanup_succeeded,cleanup_failed "
            "FROM factory.execution_metric_counters WHERE singleton"
        )
        _require(
            cursor.fetchone()
            == (2, 2, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 2, 1, 1, 1, 1),
            "first restart execution metrics are not exact",
        )


def _assert_active_replacement(
    database_url: str,
    *,
    task_id: str,
    run_id: str,
    fence: int,
    owner_id: str,
) -> None:
    """Prove the replacement authority remains live while stale calls fail."""

    import psycopg

    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            "SELECT task.state,task.current_run_id=run.run_id,"
            "task.current_fence=run.fence,run.owner_id,run.role,run.fence,"
            "run.state,run.released_at IS NULL,attempt.finished_at IS NULL,"
            "allocation.released_at IS NULL,"
            "(SELECT active_count FROM factory.capacity_counters "
            " WHERE scope_key='global:writer'),"
            "(SELECT count(*) FROM factory.capacity_allocations "
            " WHERE released_at IS NULL) "
            "FROM factory.tasks task JOIN factory.runs run "
            "ON run.run_id=task.current_run_id AND run.task_id=task.task_id "
            "JOIN factory.attempts attempt ON attempt.run_id=run.run_id "
            "AND attempt.task_id=task.task_id "
            "JOIN factory.capacity_allocations allocation "
            "ON allocation.run_id=run.run_id "
            "WHERE task.task_id=%s AND run.run_id=%s",
            (task_id, run_id),
        ).fetchone()
    _require(
        row
        == (
            TaskStatus.LEASED.value,
            True,
            True,
            owner_id,
            RunRole.WRITER.value,
            fence,
            "leased",
            True,
            True,
            True,
            1,
            1,
        ),
        "replacement M4 authority was not exactly live and capacity-bound",
    )


def _assert_durable_recovery(
    database_url: str,
    cancelled_run: str,
    orphaned_run: str,
    cancelled_task: str,
    orphaned_task: str,
) -> None:
    import psycopg

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT run_id,status,terminal_stage,attempt_count,failure_count,"
            "claim_fence,last_failure_code FROM factory.execution_recovery_jobs "
            "ORDER BY run_id"
        )
        jobs = {str(row[0]): row[1:] for row in cursor.fetchall()}
        _require(
            jobs
            == {
                cancelled_run: (
                    "succeeded",
                    "cancelled",
                    2,
                    1,
                    2,
                    "workspace_cleanup_failed",
                ),
                orphaned_run: ("succeeded", "orphaned", 1, 0, 1, None),
            },
            "recovery jobs did not retain exact retry history",
        )
        cursor.execute(
            "SELECT run_id,claim_fence,transition,source,advances_discovery_cursor "
            "FROM factory.execution_recovery_claims ORDER BY run_id,claim_fence"
        )
        claims: dict[str, list[tuple[object, ...]]] = {}
        for row in cursor.fetchall():
            claims.setdefault(str(row[0]), []).append(row[1:])
        _require(
            claims
            == {
                cancelled_run: [
                    (1, "cancelled", "cleanup_retry", False),
                    (2, "cleanup_retry", "cleanup_retry", False),
                ],
                orphaned_run: [(1, "orphaned", "fresh", True)],
            },
            "recovery claims lost source, transition, or fence authority",
        )
        cursor.execute(
            "SELECT run_id,claim_fence,outcome,failure_code "
            "FROM factory.execution_recovery_outcomes ORDER BY run_id,claim_fence"
        )
        outcomes: dict[str, list[tuple[object, ...]]] = {}
        for row in cursor.fetchall():
            outcomes.setdefault(str(row[0]), []).append(row[1:])
        _require(
            outcomes
            == {
                cancelled_run: [
                    (1, "failed", "workspace_cleanup_failed"),
                    (2, "succeeded", None),
                ],
                orphaned_run: [(1, "succeeded", None)],
            },
            "cleanup outcomes are not append-only across restart",
        )
        cursor.execute(
            "SELECT task_id,state FROM factory.tasks "
            "WHERE task_id=ANY(%s) ORDER BY task_id",
            ([cancelled_task, orphaned_task],),
        )
        tasks = {str(row[0]): row[1] for row in cursor.fetchall()}
        _require(
            tasks
            == {
                cancelled_task: TaskStatus.CANCELLED.value,
                orphaned_task: TaskStatus.RETRY.value,
            },
            "recovery changed canonical M4 terminal or retry state",
        )
        cursor.execute(
            "SELECT manifest.run_id,manifest.stage,manifest.terminal_at IS NOT NULL,"
            "array_agg(event.stage ORDER BY event.stage_sequence) "
            "FROM factory.execution_manifests manifest "
            "JOIN factory.execution_stage_events event USING(manifest_digest) "
            "GROUP BY manifest.run_id,manifest.stage,manifest.terminal_at "
            "ORDER BY manifest.run_id"
        )
        stages = {str(row[0]): row[1:] for row in cursor.fetchall()}
        _require(
            stages
            == {
                cancelled_run: ("cancelled", True, ["prepared", "cancelled"]),
                orphaned_run: ("orphaned", True, ["prepared", "orphaned"]),
            },
            "recovery did not create one canonical terminal stage per manifest",
        )
        cursor.execute(
            "SELECT (SELECT count(*) FROM factory.execution_proposals),"
            "(SELECT count(*) FROM factory.workspace_results),"
            "(SELECT count(*) FROM factory.execution_artifact_attestations),"
            "(SELECT count(*) FROM factory.capacity_allocations "
            " WHERE released_at IS NULL)"
        )
        _require(
            cursor.fetchone() == (0, 0, 0, 0),
            "recovery fabricated worker evidence or leaked capacity",
        )
        run_ids = [cancelled_run, orphaned_run]
        cursor.execute(
            "SELECT "
            "(SELECT count(*) FROM factory.execution_packets WHERE run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.execution_manifests WHERE run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.execution_stage_events event "
            " JOIN factory.execution_manifests manifest USING(manifest_digest) "
            " WHERE manifest.run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.execution_proposals WHERE run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.workspace_results WHERE run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.execution_artifact_attestations "
            " WHERE run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.execution_recovery_jobs WHERE run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.execution_recovery_claims WHERE run_id=ANY(%s)),"
            "(SELECT count(*) FROM factory.execution_recovery_outcomes WHERE run_id=ANY(%s))",
            tuple(run_ids for _ in range(9)),
        )
        _require(
            cursor.fetchone() == (2, 2, 4, 0, 0, 0, 2, 3, 3),
            "restart recovery durable cardinalities are not exact",
        )
        cursor.execute(
            "SELECT recovery_claimed,recovery_orphaned,recovery_cancelled,"
            "cleanup_succeeded,cleanup_failed,stage_orphaned,stage_cancelled "
            "FROM factory.execution_metric_counters"
        )
        _require(
            cursor.fetchone() == (3, 1, 1, 2, 1, 1, 1),
            "execution recovery metrics do not match durable outcomes",
        )
        cursor.execute(
            "SELECT bool_and(run.released_at IS NOT NULL),"
            "bool_and(allocation.released_at IS NOT NULL) "
            "FROM factory.runs run JOIN factory.capacity_allocations allocation "
            "USING(run_id) WHERE run.run_id=ANY(%s)",
            ([cancelled_run, orphaned_run],),
        )
        _require(
            cursor.fetchone() == (True, True),
            "canonical M4 run/allocation release did not survive restart",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url-env", default="FACTORY_TEST_DATABASE_URL")
    parser.add_argument(
        "--container-name-env", default="FACTORY_TEST_POSTGRES_CONTAINER"
    )
    parser.add_argument(
        "--container-id-env", default="FACTORY_TEST_POSTGRES_CONTAINER_ID"
    )
    parser.add_argument("--nonce-env", default="FACTORY_TEST_POSTGRES_NONCE")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    owner_url = os.environ.get(args.database_url_env)
    container_name = os.environ.get(args.container_name_env)
    container_id = os.environ.get(args.container_id_env)
    nonce = os.environ.get(args.nonce_env)
    if not owner_url or not container_name or not container_id or not nonce:
        raise SystemExit(
            f"{args.database_url_env}, {args.container_name_env}, "
            f"{args.container_id_env} and {args.nonce_env} are required"
        )

    _assert_disposable_target(owner_url, container_name, container_id, nonce)
    if args.preflight_only:
        print("PASS: disposable PostgreSQL identity preflight")
        return 0
    PostgresMigrator(owner_url).apply()
    suffix = uuid.uuid4().hex[:10]
    runtime_login = f"factory_probe_runtime_{suffix}"
    attestor_login = f"factory_probe_attestor_{suffix}"
    runtime_password = f"runtime-{uuid.uuid4().hex}"
    attestor_password = f"attestor-{uuid.uuid4().hex}"
    provision_runtime_login(owner_url, runtime_login, runtime_password)
    provision_artifact_attestor_login(
        owner_url,
        attestor_login,
        attestor_password,
        runtime_login=runtime_login,
    )
    PostgresMigrator(owner_url).apply(
        expected_runtime_login=runtime_login,
        expected_artifact_attestor_login=attestor_login,
    )
    runtime_url = _database_url_for_login(owner_url, runtime_login, runtime_password)
    attestor_url = _database_url_for_login(
        owner_url, attestor_login, attestor_password
    )
    runtime_store = _assert_capability_roles(
        owner_url, runtime_url, attestor_url, runtime_login, attestor_login
    )
    identity_before = _database_identity(owner_url)
    _require(
        identity_before[1] >= 170_000
        and tuple(row[0] for row in identity_before[2]) == tuple(range(1, 18)),
        "restart probe requires the complete PostgreSQL 17 schema",
    )

    now = datetime.now(timezone.utc).replace(microsecond=0)
    _reset_database(owner_url, now)
    operator = Actor(
        "restart-operator",
        "operator",
        frozenset({"task:submit", "task:cancel", "factory:reconcile"}),
        frozenset({"*"}),
    )
    worker_a = Actor(
        "restart-worker-a",
        "worker",
        frozenset({"task:claim", "task:execute", "task:heartbeat"}),
        frozenset({"probe/repository"}),
    )
    worker_b = Actor(
        "restart-worker-b",
        "worker",
        frozenset({"task:claim", "task:execute", "task:heartbeat"}),
        frozenset({"probe/repository"}),
    )
    control = FactoryService(runtime_store)

    selection_a = _selection("workspace:" + "a" * 64)
    task_a = control.intake(_payload(now, "cancelled"), actor=operator, now=now).task
    execution_a = FactoryService(
        runtime_store, execution_registry=_registry(selection_a)
    ).claim_execution(
        owner=worker_a.actor_id,
        role=RunRole.WRITER,
        repositories=("probe/repository",),
        lease_seconds=30,
        selection=selection_a,
        actor=worker_a,
        now=now,
        idempotency_key="a" * 64,
    )
    _require(execution_a is not None, "cancelled execution was not claimed")
    task_a = control.cancel(
        task_a.task_id,
        reason="restart recovery probe",
        idempotency_key="c" * 64,
        actor=operator,
        now=now,
    )
    _require(task_a.status is TaskStatus.CANCELLED, "execution cancellation failed")

    selection_b = _selection("workspace:" + "b" * 64)
    task_b = control.intake(_payload(now, "orphaned"), actor=operator, now=now).task
    execution_b = FactoryService(
        runtime_store, execution_registry=_registry(selection_b)
    ).claim_execution(
        owner=worker_b.actor_id,
        role=RunRole.WRITER,
        repositories=("probe/repository",),
        lease_seconds=30,
        selection=selection_b,
        actor=worker_b,
        now=now,
        idempotency_key="b" * 64,
    )
    _require(execution_b is not None, "orphaned execution was not claimed")

    handle_a = WorkspaceHandle(
        execution_a.lease.task_id,
        execution_a.lease.run_id,
        execution_a.workspace_handle,
    )
    handle_b = WorkspaceHandle(
        execution_b.lease.task_id,
        execution_b.lease.run_id,
        execution_b.workspace_handle,
    )
    workspace_backend = WorkspaceBackend()
    workspace_backend.register(handle_a)
    workspace_backend.register(handle_b)

    import psycopg

    with psycopg.connect(owner_url) as connection:
        connection.execute(
            "UPDATE factory.runs SET lease_expires_at="
            "clock_timestamp()-interval '1 second' WHERE run_id=%s",
            (execution_b.lease.run_id,),
        )
    run_ids = (execution_a.lease.run_id, execution_b.lease.run_id)
    immutable_before = _immutable_authority(owner_url, run_ids)

    owner_url, runtime_url, attestor_url = _restart_database(
        container_name,
        container_id,
        nonce,
        owner_url,
        runtime_url,
        attestor_url,
    )
    runtime_store = _assert_capability_roles(
        owner_url, runtime_url, attestor_url, runtime_login, attestor_login
    )
    identity_first = _database_identity(owner_url)
    _require(
        identity_first[0] > identity_before[0]
        and identity_first[1:] == identity_before[1:],
        "first restart changed migration identity or server version",
    )
    recording_store = RecordingRecoveryStore(runtime_store)
    first_releaser = AmbiguousWorkspaceReleaser(
        workspace_backend, ambiguous=handle_a
    )
    first = ExecutionRecovery(recording_store, first_releaser, operator).reconcile(
        limit=2, cursor=None
    )
    _require(
        (
            first.candidates,
            first.orphaned,
            first.cancelled,
            first.cleanup_failed,
            first.terminalize_failed,
        )
        == (2, 1, 1, 1, 0),
        "first restart did not recover both independent lanes",
    )
    _require(
        first.cursor is not None and first.cursor.run_id == execution_b.lease.run_id,
        "full raw page did not preserve the authoritative fresh watermark",
    )
    _require(
        [(handle, status) for handle, _timeout, status in workspace_backend.outcomes]
        == [(handle_b, "released"), (handle_a, "released")]
        and all(0 < timeout < 30 for _handle, timeout, _status in workspace_backend.outcomes)
        and workspace_backend.active == set(),
        "first restart cleanup was not exact-handle bounded",
    )
    claims_by_run: dict[str, list[ExecutionRecoveryClaim]] = {}
    for claim in recording_store.claims:
        claims_by_run.setdefault(claim.candidate.run_id, []).append(claim)
    _require(
        set(claims_by_run) == set(run_ids)
        and all(len(claims) == 1 for claims in claims_by_run.values()),
        "first restart did not expose exactly one claim for each execution",
    )
    stale_a = claims_by_run[execution_a.lease.run_id][0]
    fresh_b = claims_by_run[execution_b.lease.run_id][0]
    _assert_claim_persisted(owner_url, stale_a)
    _assert_claim_persisted(owner_url, fresh_b)
    _assert_first_restart_state(
        owner_url,
        execution_a.lease.run_id,
        execution_b.lease.run_id,
        task_a.task_id,
        task_b.task_id,
    )
    _require(
        _immutable_authority(owner_url, run_ids) == immutable_before,
        "first restart mutated packet, manifest, or M0 authority",
    )
    first_phase_state = _late_fence_state(owner_url, run_ids)
    first_phase_legacy = _legacy_metrics(owner_url)
    retry_deadline = time.monotonic() + 5
    while True:
        with psycopg.connect(owner_url) as connection:
            retry_due = connection.execute(
                "SELECT next_claim_at<=clock_timestamp() "
                "FROM factory.execution_recovery_jobs WHERE run_id=%s",
                (execution_a.lease.run_id,),
            ).fetchone()[0]
        if retry_due:
            break
        if time.monotonic() >= retry_deadline:
            raise RuntimeError("durable cleanup retry did not become naturally due")
        time.sleep(0.05)

    owner_url, runtime_url, attestor_url = _restart_database(
        container_name,
        container_id,
        nonce,
        owner_url,
        runtime_url,
        attestor_url,
    )
    runtime_store = _assert_capability_roles(
        owner_url, runtime_url, attestor_url, runtime_login, attestor_login
    )
    identity_second = _database_identity(owner_url)
    _require(
        identity_second[0] > identity_first[0]
        and identity_second[1:] == identity_before[1:],
        "second restart changed migration identity or server version",
    )
    _require(
        _late_fence_state(owner_url, run_ids) == first_phase_state
        and _legacy_metrics(owner_url) == first_phase_legacy,
        "second restart mutated the exact first-phase recovery state",
    )
    second_releaser = AmbiguousWorkspaceReleaser(workspace_backend)
    second = ExecutionRecovery(runtime_store, second_releaser, operator).reconcile(
        limit=2, cursor=first.cursor
    )
    _require(
        (
            second.candidates,
            second.orphaned,
            second.cancelled,
            second.cleanup_failed,
            second.terminalize_failed,
            second.cursor,
        )
        == (1, 0, 0, 0, 0, None),
        "second restart did not resume the durable cleanup retry",
    )
    _require(
        [
            (handle, status)
            for handle, _timeout, status in workspace_backend.outcomes
        ]
        == [
            (handle_b, "released"),
            (handle_a, "released"),
            (handle_a, "already_absent"),
        ]
        and all(0 < timeout < 30 for _handle, timeout, _status in workspace_backend.outcomes)
        and workspace_backend.active == set(),
        "cleanup retry was not deterministic and idempotent",
    )
    before_stale_cleanup = _late_fence_state(owner_url, run_ids)
    legacy_before_stale_cleanup = _legacy_metrics(owner_url)
    try:
        runtime_store.record_execution_cleanup_success(stale_a)
    except FenceError:
        pass
    else:
        raise RuntimeError("stale cleanup fence completed after restart")
    _require(
        _late_fence_state(owner_url, run_ids) == before_stale_cleanup,
        "stale cleanup completion mutated durable recovery state or metrics",
    )
    _require(
        _legacy_metrics(owner_url) == legacy_before_stale_cleanup,
        "direct stale cleanup completion mutated legacy metrics",
    )

    third = ExecutionRecovery(runtime_store, second_releaser, operator).reconcile(
        limit=2, cursor=second.cursor
    )
    _require(
        (
            third.candidates,
            third.orphaned,
            third.cancelled,
            third.cleanup_failed,
            third.terminalize_failed,
            third.cursor,
        )
        == (0, 0, 0, 0, 0, None),
        "completed restart recovery was not a no-op",
    )
    _require(
        _immutable_authority(owner_url, run_ids) == immutable_before,
        "packet, manifest, or M0 authority mutated across restart",
    )
    _assert_durable_recovery(
        owner_url,
        execution_a.lease.run_id,
        execution_b.lease.run_id,
        task_a.task_id,
        task_b.task_id,
    )
    _require(
        runtime_store.verify_audit_chain(task_a.task_id)
        and runtime_store.verify_audit_chain(task_b.task_id),
        "restart recovery broke the task audit hash chain",
    )

    replacement_actor = Actor(
        "replacement-worker",
        "worker",
        frozenset({"task:claim", "task:heartbeat", "task:release"}),
        frozenset({"probe/repository"}),
    )
    restarted_service = FactoryService(runtime_store)
    replacement = restarted_service.claim(
        owner=replacement_actor.actor_id,
        role=RunRole.WRITER,
        repositories=("probe/repository",),
        lease_seconds=30,
        actor=replacement_actor,
        now=datetime.now(timezone.utc),
        idempotency_key="d" * 64,
    )
    _require(
        replacement is not None
        and replacement.task_id == task_b.task_id
        and replacement.fence > execution_b.lease.fence,
        "retryable execution did not receive a higher M4 fence",
    )
    fenced_run_ids = (*run_ids, replacement.run_id)
    _assert_active_replacement(
        owner_url,
        task_id=replacement.task_id,
        run_id=replacement.run_id,
        fence=replacement.fence,
        owner_id=replacement.owner,
    )
    before_late_event = _late_fence_state(owner_url, fenced_run_ids)
    legacy_before_late_event = _legacy_metrics(owner_url)
    for late in (
        lambda: restarted_service.heartbeat(
            execution_b.lease,
            actor=worker_b,
            now=datetime.now(timezone.utc),
        ),
        lambda: restarted_service.advance_execution(
            execution_b.lease,
            packet_digest=execution_b.packet_digest,
            stage=ExecutionStage.RUNNING,
            actor=worker_b,
        ),
    ):
        try:
            late()
        except FenceError:
            pass
        else:
            raise RuntimeError("late execution holder crossed the replacement fence")
    _require(
        _late_fence_state(owner_url, fenced_run_ids) == before_late_event,
        "late execution holder mutated terminal or recovery authority",
    )
    _assert_active_replacement(
        owner_url,
        task_id=replacement.task_id,
        run_id=replacement.run_id,
        fence=replacement.fence,
        owner_id=replacement.owner,
    )
    legacy_after_late_event = _legacy_metrics(owner_url)
    expected_legacy = dict(legacy_before_late_event)
    expected_legacy["fence_rejected"] += 2
    _require(
        legacy_after_late_event == expected_legacy,
        "late execution holders changed more than the two fence rejection metrics",
    )
    restarted_service.release(
        replacement,
        outcome=FailureClass.WORKER_LOST,
        actor=replacement_actor,
        now=datetime.now(timezone.utc),
        idempotency_key="e" * 64,
    )
    with psycopg.connect(owner_url) as connection:
        live_allocations, active_capacity = connection.execute(
            "SELECT (SELECT count(*) FROM factory.capacity_allocations "
            "WHERE released_at IS NULL),"
            "COALESCE((SELECT sum(active_count) FROM factory.capacity_counters),0)"
        ).fetchone()
    _require(
        (live_allocations, active_capacity) == (0, 0)
        and runtime_store.readiness()["capacity_consistent"] is True,
        "replacement cleanup did not return capacity to zero",
    )
    _require(
        runtime_store.verify_audit_chain(task_a.task_id)
        and runtime_store.verify_audit_chain(task_b.task_id),
        "replacement/late-fence proof broke the task audit hash chain",
    )
    print(
        "PASS: two PostgreSQL restarts; exact runtime/attestor roles; "
        "cancelled+orphaned recovery; ambiguous cleanup fence2 replay; "
        "zero fabricated proposal/result/attestation; higher M4 fence"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
