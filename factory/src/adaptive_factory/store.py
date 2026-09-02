from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import uuid

from .contracts import HEX64, TaskIntakeV1, canonical_digest
from .brokers import (
    ArtifactProposal,
    NoteProposal,
    ProposalContext,
    TerminalProposal,
    UsageProposal,
    proposal_idempotency_key,
)
from .execution_contracts import RunManifestV1, TaskPacketV1, WorkspaceResultV1, workspace_evidence_digest
from .migrations import discover_migrations
from .models import Actor, ExecutionGrant, ExecutionStage, FailureClass, LeaseGrant, RunRole, TaskProjection, TaskStatus
from .protocol import CanonicalEvent, PROTOCOL_VERSION
from .state import classify_retry
from .workspace import (
    ArtifactAttestationUnavailable,
    ArtifactAttestationV1,
    WorkspaceSnapshotRequest,
    WorkspaceSnapshotV1,
)


class StoreError(RuntimeError):
    pass


class FenceError(StoreError):
    pass


class BudgetError(StoreError):
    pass


class AuthorityError(StoreError):
    pass


class MetricsUnavailable(StoreError):
    pass


@dataclass(frozen=True)
class IntakeResult:
    task: TaskProjection
    created: bool


@dataclass(frozen=True)
class ReconcileResult:
    candidates: int
    repaired: int
    cursor: str | None


@dataclass(frozen=True)
class UsageResult:
    observation_id: str
    created: bool


class PostgresArtifactAttestationStore:
    """Dedicated capability boundary; its login must not inherit factory_runtime."""

    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise StoreError("artifact attestor database URL is required")
        self.database_url = database_url

    def _connect(self):
        import psycopg

        connection = psycopg.connect(self.database_url)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT session_user,rolinherit,rolsuper,rolcreaterole,rolcreatedb,
                    pg_has_role(session_user,'factory_artifact_attestor','MEMBER'),
                    pg_has_role(session_user,'factory_runtime','MEMBER')
                    FROM pg_roles WHERE rolname=session_user"""
                )
                identity = cursor.fetchone()
                if identity is None or identity[1:] != (False, False, False, False, True, False):
                    raise StoreError("artifact attestor login is not least privilege")
                cursor.execute(
                    """SELECT COALESCE(array_agg(r.rolname ORDER BY r.rolname),ARRAY[]::name[])
                    FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.roleid
                    JOIN pg_roles u ON u.oid=m.member WHERE u.rolname=session_user"""
                )
                if tuple(cursor.fetchone()[0]) != ("factory_artifact_attestor",):
                    raise StoreError("artifact attestor login has excess role membership")
                cursor.execute("SET ROLE factory_artifact_attestor")
                cursor.execute("SELECT current_user")
                if cursor.fetchone()[0] != "factory_artifact_attestor":
                    raise StoreError("artifact attestor capability unavailable")
            return connection
        except Exception:
            connection.close()
            raise

    def readiness(self) -> dict[str, str]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT session_user,current_user")
            session_user, current_user = cursor.fetchone()
            return {"session_user": session_user, "database_role": current_user}

    def record_artifact_attestation(
        self, attestation: ArtifactAttestationV1
    ) -> ArtifactAttestationV1 | ArtifactAttestationUnavailable:
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute(
                "SELECT factory.execution_record_artifact_attestation(%s::jsonb)",
                (json.dumps(attestation.to_dict(), sort_keys=True, separators=(",", ":")),),
            )
            value = cursor.fetchone()[0]
        if value is None:
            return ArtifactAttestationUnavailable(reason="trusted_artifact_attestation_rejected")
        if isinstance(value, str):
            value = json.loads(value)
        try:
            return ArtifactAttestationV1.from_dict(value)
        except (TypeError, ValueError) as exc:
            raise StoreError("corrupt artifact attestation envelope") from exc


class PostgresFactoryStore:
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise StoreError("database URL is required")
        self.database_url = database_url

    def _connect(self, *, connect_timeout: int | None = None):
        import psycopg

        options = {} if connect_timeout is None else {"connect_timeout": connect_timeout}
        connection = psycopg.connect(self.database_url, **options)
        try:
            connection.execute("SET ROLE factory_runtime")
        except Exception:
            connection.close()
            raise
        return connection

    def readiness(self) -> dict[str, object]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT current_user,COALESCE(max(version),0) FROM factory.schema_migrations")
            role, version = cursor.fetchone()
            capacity_consistent = self._capacity_consistent(cursor)
            accounting_consistent = self._accounting_consistent(cursor)
            return {
                "status": "ready" if version == len(discover_migrations()) and capacity_consistent and accounting_consistent else "not_ready",
                "database_role": role,
                "schema_version": version,
                "capacity_consistent": capacity_consistent,
                "accounting_consistent": accounting_consistent,
            }

    @staticmethod
    def _accounting_consistent(cursor) -> bool:
        cursor.execute(
            """SELECT NOT EXISTS (
            SELECT 1 FROM factory.tasks t
            WHERE (
              (t.state IN ('queued','retry','ready_for_human') OR
               (t.state='superseded' AND NOT t.accounting_blocked)) AND (
                t.accounting_blocked OR t.cost_reserved_micros<>0 OR t.tokens_reserved<>0
                OR t.wall_reserved_seconds<>0 OR EXISTS (
                  SELECT 1 FROM factory.budget_reservations b
                  WHERE b.task_id=t.task_id AND b.released_at IS NULL
                )
              )
            ))"""
        )
        return bool(cursor.fetchone()[0])

    @staticmethod
    def _capacity_consistent(cursor) -> bool:
        cursor.execute(
            """SELECT count(*) FILTER (WHERE scope_key IN ('global:reader','global:writer'))=2
            AND bool_and(active_count = CASE
              WHEN scope_key='global:reader' THEN (SELECT count(*) FROM factory.capacity_allocations WHERE role='reader' AND released_at IS NULL)
              WHEN scope_key='global:writer' THEN (SELECT count(*) FROM factory.capacity_allocations WHERE role='writer' AND released_at IS NULL)
              ELSE (SELECT count(*) FROM factory.capacity_allocations
                    WHERE role='reader' AND released_at IS NULL
                    AND repository_id=substring(c.scope_key FROM 12 FOR char_length(c.scope_key)-18))
            END) FROM factory.capacity_counters c"""
        )
        return bool(cursor.fetchone()[0])

    def metrics(self) -> dict[str, dict[str, int]]:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout='5s'")
                cursor.execute("SET LOCAL lock_timeout='500ms'")
                cursor.execute("SELECT * FROM factory.read_metrics_snapshot()")
                row = cursor.fetchone()
        except Exception as exc:
            raise MetricsUnavailable("metrics snapshot unavailable") from exc
        (
            _singleton, intake, superseded, queued, retry, dead, transition_events,
            live_leases, reclaimed, fence_rejected, active_capacity,
            reserved_cost, observed_cost, reserved_tokens, observed_tokens, reserved_wall,
            observed_output, blocked, kills, reconciliation_runs,
            reconciliation_candidates, repaired,
        ) = row
        return {
            "factory_intake_and_rejection_outcomes_total": {
                "accepted": intake, "superseded": superseded, "queued": queued, "retry": retry,
                "dead": dead, "transition_events": transition_events,
            },
            "factory_lease_reclaim_and_fence_rejection_total": {
                "live_leases": live_leases, "reclaimed": reclaimed, "fence_rejected": fence_rejected,
            },
            "factory_capacity_budget_kill_and_reconcile_outcomes_total": {
                "active_capacity": active_capacity, "cost_reserved_micros": reserved_cost,
                "cost_observed_micros": observed_cost, "tokens_reserved": reserved_tokens,
                "tokens_observed": observed_tokens, "wall_reserved_seconds": reserved_wall,
                "output_observed_bytes": observed_output, "accounting_blocked": blocked,
                "active_kills": kills, "reconciliation_runs": reconciliation_runs,
                "reconciliation_candidates": reconciliation_candidates, "repaired": repaired,
            },
        }

    def record_fence_rejection(self) -> None:
        with self._connect(connect_timeout=1) as connection, connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='100ms'")
            cursor.execute("SET LOCAL statement_timeout='250ms'")
            cursor.execute("SELECT factory.increment_fence_rejected()")

    def _command_replay(self, cursor, key: str | None, actor: Actor, action: str, request: dict):
        if key is None:
            return False, None, canonical_digest(request)
        digest = canonical_digest(request)
        cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (key,))
        cursor.execute(
            "SELECT actor_id,action,request_digest,result FROM factory.command_results WHERE idempotency_key=%s",
            (key,),
        )
        row = cursor.fetchone()
        if row is None:
            return False, None, digest
        if (row[0], row[1], row[2].strip()) != (actor.actor_id, action, digest):
            raise StoreError("idempotency key reused with different command")
        return True, row[3], digest

    @staticmethod
    def _record_command(cursor, key: str | None, actor: Actor, action: str, digest: str, correlation: str | None, result: dict) -> None:
        if key is None:
            return
        cursor.execute(
            "INSERT INTO factory.command_results(idempotency_key,actor_id,action,request_digest,correlation_id,result) VALUES (%s,%s,%s,%s,%s,%s::jsonb)",
            (key, actor.actor_id, action, digest, correlation or key, json.dumps(result, sort_keys=True, separators=(",", ":"))),
        )

    @staticmethod
    def _verify_m0_authority(cursor, intake: TaskIntakeV1) -> bool:
        authority = intake.m0_authority
        if authority.observed_at is not None:
            cursor.execute(
                "SELECT factory.m0_observation_valid(%s,%s,%s,%s,%s)",
                (
                    authority.observed_at,
                    authority.check_name,
                    authority.exact_head_sha,
                    intake.repository_id,
                    intake.policy_digest,
                ),
            )
        else:
            cursor.execute(
                "SELECT factory.m0_exception_valid(%s,%s,%s,%s,%s,%s)",
                (
                    authority.bootstrap_exception,
                    authority.issuer,
                    authority.scope,
                    authority.expires_at,
                    intake.repository_id,
                    intake.policy_digest,
                ),
            )
        return bool(cursor.fetchone()[0])

    @staticmethod
    def _projection(row) -> TaskProjection:
        return TaskProjection(str(row[0]), row[1], TaskStatus(row[2]), row[3], row[4].strip(), row[5].strip(), row[6])

    @staticmethod
    def _task_select() -> str:
        return "SELECT t.task_id,t.repository_id,t.state,t.generation,i.intent_digest,t.packet_digest,t.deadline_at FROM factory.tasks t JOIN factory.accepted_intents i ON i.intent_id=t.intent_id"

    def _event(
        self, cursor, task_id: str, actor: Actor, action: str, idempotency_key: str,
        metadata: dict | None = None, *, mandatory_cleanup: bool = False,
    ) -> None:
        cursor.execute(
            """SELECT t.event_limit,
            count(e.event_id) FILTER (WHERE NOT e.mandatory_cleanup),
            COALESCE(max(e.event_sequence),0)
            FROM factory.tasks t LEFT JOIN factory.task_events e ON e.task_id=t.task_id
            WHERE t.task_id=%s GROUP BY t.event_limit""",
            (task_id,),
        )
        event_limit, ordinary_count, previous_sequence = cursor.fetchone()
        if not mandatory_cleanup and ordinary_count >= event_limit:
            raise BudgetError("event budget exceeded")
        sequence = previous_sequence + 1
        cursor.execute(
            "INSERT INTO factory.task_events(event_id,task_id,event_sequence,idempotency_key,actor_id,action,metadata,mandatory_cleanup) VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s) ON CONFLICT(task_id,idempotency_key) DO NOTHING",
            (
                uuid.uuid4(),
                task_id,
                sequence,
                idempotency_key,
                actor.actor_id,
                action,
                json.dumps(metadata or {}, separators=(",", ":")),
                mandatory_cleanup,
            ),
        )

    @staticmethod
    def _ordinary_event_capacity_available(cursor, task_id: str) -> bool:
        cursor.execute(
            """SELECT count(e.event_id) FILTER (WHERE NOT e.mandatory_cleanup) < t.event_limit
            FROM factory.tasks t LEFT JOIN factory.task_events e ON e.task_id=t.task_id
            WHERE t.task_id=%s GROUP BY t.event_limit""",
            (task_id,),
        )
        row = cursor.fetchone()
        return bool(row and row[0])

    def _audit(
        self,
        cursor,
        task_id: str,
        actor: Actor,
        action: str,
        resource: str,
        reason: str,
        correlation_id: str,
        metadata: dict | None = None,
        run_id: str | None = None,
    ) -> None:
        cursor.execute("SELECT last_digest FROM factory.audit_heads WHERE task_id=%s FOR UPDATE", (task_id,))
        row = cursor.fetchone()
        previous = row[0].strip() if row else "0" * 64
        if row is None:
            cursor.execute("INSERT INTO factory.audit_heads(task_id,last_digest) VALUES (%s,%s)", (task_id, previous))
        cursor.execute("SELECT clock_timestamp()")
        received_at = cursor.fetchone()[0]
        bounded = metadata or {}
        digest = canonical_digest(
            {
                "digest_version": 2,
                "previous_digest": previous,
                "task_id": task_id,
                "run_id": run_id,
                "correlation_id": correlation_id,
                "actor": actor.actor_id,
                "action": action,
                "resource": resource,
                "reason": reason,
                "received_at": received_at,
                "metadata_digest": canonical_digest(bounded),
            }
        )
        cursor.execute(
            "INSERT INTO factory.audit_log(task_id,run_id,previous_digest,current_digest,actor_id,action,resource,reason,correlation_id,metadata,created_at,digest_version) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,2)",
            (
                task_id,
                run_id,
                previous,
                digest,
                actor.actor_id,
                action,
                resource,
                reason,
                correlation_id,
                json.dumps(bounded, separators=(",", ":")),
                received_at,
            ),
        )
        cursor.execute("UPDATE factory.audit_heads SET last_digest=%s WHERE task_id=%s", (digest, task_id))

    def intake(self, intake: TaskIntakeV1, actor: Actor, now: datetime) -> IntakeResult:
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                (f"{intake.repository_id}\x1f{intake.source_type}\x1f{intake.source_id}",),
            )
            if not self._verify_m0_authority(cursor, intake):
                raise AuthorityError("M0 authority is not trusted for repository/policy/action")
            cursor.execute(
                "INSERT INTO factory.intake_identities(repository_id,source_type,source_id) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                (intake.repository_id, intake.source_type, intake.source_id),
            )
            cursor.execute(
                self._task_select() + " WHERE i.idempotency_key=%s ORDER BY t.generation DESC LIMIT 1",
                (intake.idempotency_key,),
            )
            duplicate = cursor.fetchone()
            if duplicate:
                return IntakeResult(self._projection(duplicate), False)
            cursor.execute(
                "SELECT task_id FROM factory.tasks WHERE repository_id=%s AND source_type=%s AND source_id=%s AND state NOT IN ('ready_for_human','dead','cancelled','superseded')",
                (intake.repository_id, intake.source_type, intake.source_id),
            )
            old_ids = [str(row[0]) for row in cursor.fetchall()]
            for old_id in old_ids:
                self._close_active_lease(cursor, old_id)
                cursor.execute(
                    "UPDATE factory.tasks SET state='superseded',terminal_at=clock_timestamp(),updated_at=clock_timestamp(),current_run_id=NULL,current_fence=NULL WHERE task_id=%s",
                    (old_id,),
                )
                key = canonical_digest({"action": "superseded", "replacement": intake.intent_digest})
                self._event(
                    cursor, old_id, actor, "superseded", key,
                    {"replacement_intent_digest": intake.intent_digest}, mandatory_cleanup=True,
                )
                self._audit(
                    cursor,
                    old_id,
                    actor,
                    "superseded",
                    f"task:{old_id}",
                    "frozen_input_changed",
                    intake.request_id,
                    {"replacement_intent_digest": intake.intent_digest},
                )
            cursor.execute(
                "SELECT COALESCE(max(generation),0)+1 FROM factory.tasks WHERE repository_id=%s AND source_type=%s AND source_id=%s",
                (intake.repository_id, intake.source_type, intake.source_id),
            )
            generation = cursor.fetchone()[0]
            intent_id, task_id = uuid.uuid4(), uuid.uuid4()
            body = json.dumps(intake.to_dict(), sort_keys=True, separators=(",", ":"))
            cursor.execute(
                """INSERT INTO factory.accepted_intents(intent_id,intent_digest,idempotency_key,repository_id,source_type,source_id,source_digest,exact_base_sha,spec_digest,architecture_digest,governance_digest,policy_digest,body)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
                (
                    intent_id,
                    intake.intent_digest,
                    intake.idempotency_key,
                    intake.repository_id,
                    intake.source_type,
                    intake.source_id,
                    intake.source_digest,
                    intake.exact_base_sha,
                    intake.spec_digest,
                    intake.architecture.architecture_digest,
                    intake.governance.governance_digest,
                    intake.policy_digest,
                    body,
                ),
            )
            cursor.execute(
                """INSERT INTO factory.tasks(task_id,intent_id,repository_id,source_type,source_id,state,generation,packet_digest,deadline_at,cost_limit_micros,token_limit,output_limit_bytes,event_limit,repair_limit,wall_limit_seconds)
                VALUES (%s,%s,%s,%s,%s,'queued',%s,%s,now()+(%s * interval '1 second'),%s,%s,%s,%s,%s,%s) RETURNING deadline_at""",
                (
                    task_id,
                    intent_id,
                    intake.repository_id,
                    intake.source_type,
                    intake.source_id,
                    generation,
                    intake.intent_digest,
                    intake.limits.wall_seconds,
                    intake.limits.max_cost_usd_micros,
                    intake.limits.max_token_units,
                    intake.limits.max_output_bytes,
                    intake.limits.max_events,
                    intake.limits.semantic_repairs,
                    intake.limits.wall_seconds,
                ),
            )
            deadline = cursor.fetchone()[0]
            self._event(
                cursor, str(task_id), actor, "intake_queued", intake.idempotency_key, {"generation": generation}
            )
            self._audit(
                cursor,
                str(task_id),
                actor,
                "intake",
                f"task:{task_id}",
                "accepted",
                intake.request_id,
                {"intent_digest": intake.intent_digest},
            )
            return IntakeResult(
                TaskProjection(
                    str(task_id),
                    intake.repository_id,
                    TaskStatus.QUEUED,
                    generation,
                    intake.intent_digest,
                    intake.intent_digest,
                    deadline,
                ),
                True,
            )

    def get_task(self, task_id: str) -> TaskProjection:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(self._task_select() + " WHERE t.task_id=%s", (task_id,))
            row = cursor.fetchone()
            if not row:
                raise KeyError(task_id)
            return self._projection(row)

    def list_tasks(
        self, *, repository_id: str | None = None, limit: int = 100, cursor_task_id: str | None = None
    ) -> tuple[TaskProjection, ...]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        conditions, params = [], []
        if repository_id:
            conditions.append("t.repository_id=%s")
            params.append(repository_id)
        if cursor_task_id:
            conditions.append("t.task_id>%s")
            params.append(cursor_task_id)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        with self._connect() as connection, connection.cursor() as db:
            db.execute("SET statement_timeout='5s'")
            db.execute(self._task_select() + where + " ORDER BY t.task_id LIMIT %s", (*params, limit))
            return tuple(self._projection(row) for row in db.fetchall())

    def verify_audit_chain(self, task_id: str) -> bool:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SET statement_timeout='5s'")
            cursor.execute(
                """SELECT previous_digest,current_digest,task_id,run_id,correlation_id,actor_id,action,resource,reason,created_at,metadata,digest_version
                FROM factory.audit_log WHERE task_id=%s ORDER BY audit_id LIMIT 100001""",
                (task_id,),
            )
            rows = cursor.fetchall()
            if not rows or len(rows) > 100_000:
                return False
            previous = "0" * 64
            for row in rows:
                recorded_previous, recorded_current, stored_task_id, run_id, correlation_id, actor, action, resource, reason, received_at, metadata, digest_version = row
                if recorded_previous.strip() != previous:
                    return False
                envelope = {
                    "previous_digest": previous,
                    "actor": actor,
                    "action": action,
                    "resource": resource,
                    "reason": reason,
                    "received_at": received_at,
                    "metadata_digest": canonical_digest(metadata),
                }
                if digest_version == 2:
                    envelope.update(
                        {
                            "digest_version": 2,
                            "task_id": str(stored_task_id),
                            "run_id": str(run_id) if run_id is not None else None,
                            "correlation_id": correlation_id,
                        }
                    )
                expected = canonical_digest(envelope)
                if recorded_current.strip() != expected:
                    return False
                previous = expected
            cursor.execute("SELECT last_digest FROM factory.audit_heads WHERE task_id=%s", (task_id,))
            head = cursor.fetchone()
            return bool(head and head[0].strip() == previous)

    def _is_killed(self, cursor, repositories: tuple[str, ...]) -> bool:
        scopes = ("global",) + tuple(f"repository:{item}" for item in repositories)
        cursor.execute(
            "SELECT bool_or(enabled) FROM (SELECT DISTINCT ON (scope_key) scope_key,enabled FROM factory.kill_switches WHERE scope_key=ANY(%s) ORDER BY scope_key,created_at DESC,switch_id DESC) current",
            (list(scopes),),
        )
        return bool(cursor.fetchone()[0])

    def claim(self, request, actor: Actor, now: datetime, *, idempotency_key: str | None = None, correlation_id: str | None = None) -> LeaseGrant | None:
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            command = {
                "owner": request.owner,
                "role": request.role.value,
                "repositories": list(request.repositories),
                "lease_seconds": request.lease_seconds,
            }
            replay, prior, request_digest = self._command_replay(cursor, idempotency_key, actor, "claim", command)
            if replay:
                value = prior["grant"]
                if value is None:
                    return None
                return LeaseGrant(
                    value["task_id"], value["run_id"], value["owner"], RunRole(value["role"]), value["fence"],
                    datetime.fromisoformat(value["expires_at"].replace("Z", "+00:00")), value["packet_digest"]
                )
            def no_grant() -> None:
                self._record_command(
                    cursor, idempotency_key, actor, "claim", request_digest, correlation_id, {"grant": None}
                )
                return None
            if self._is_killed(cursor, request.repositories):
                return no_grant()
            cursor.execute(
                "SELECT * FROM factory.capacity_eligible_repositories(%s,%s)",
                (request.role.value, list(request.repositories)),
            )
            eligible_repositories = tuple(row[0] for row in cursor.fetchall())
            if not eligible_repositories:
                return no_grant()
            cursor.execute(
                """SELECT t.task_id,t.repository_id,t.packet_digest,t.deadline_at
                FROM factory.tasks t WHERE t.state IN ('queued','retry') AND t.repository_id=ANY(%s)
                AND t.deadline_at>clock_timestamp() AND NOT t.accounting_blocked
                AND t.cost_reserved_micros=0 AND t.tokens_reserved=0 AND t.wall_reserved_seconds=0
                AND NOT EXISTS (SELECT 1 FROM factory.budget_reservations b
                  WHERE b.task_id=t.task_id AND b.released_at IS NULL)
                ORDER BY t.created_at,t.task_id FOR UPDATE SKIP LOCKED LIMIT 1""",
                (list(eligible_repositories),),
            )
            row = cursor.fetchone()
            if not row:
                return no_grant()
            task_id, repository_id, packet_digest, deadline = row
            cursor.execute(
                "INSERT INTO factory.lease_sequences(task_id,last_fence) VALUES (%s,1) ON CONFLICT(task_id) DO UPDATE SET last_fence=factory.lease_sequences.last_fence+1 RETURNING last_fence",
                (task_id,),
            )
            fence = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(max(attempt_no),0)+1 FROM factory.attempts WHERE task_id=%s", (task_id,))
            attempt_no = cursor.fetchone()[0]
            if attempt_no > 3:
                cursor.execute(
                    "UPDATE factory.tasks SET state='dead',terminal_at=clock_timestamp(),updated_at=clock_timestamp() WHERE task_id=%s",
                    (task_id,),
                )
                return no_grant()
            run_id = uuid.uuid4()
            cursor.execute(
                "SELECT LEAST(clock_timestamp()+(%s * interval '1 second'),%s)", (request.lease_seconds, deadline)
            )
            expires = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO factory.runs(run_id,task_id,owner_id,role,packet_digest,fence,state,lease_expires_at,deadline_at) VALUES (%s,%s,%s,%s,%s,%s,'leased',%s,%s)",
                (run_id, task_id, request.owner, request.role.value, packet_digest, fence, expires, deadline),
            )
            cursor.execute(
                "INSERT INTO factory.attempts(attempt_id,task_id,run_id,attempt_no) VALUES (%s,%s,%s,%s)",
                (uuid.uuid4(), task_id, run_id, attempt_no),
            )
            cursor.execute(
                "SELECT factory.capacity_allocate(%s,%s,%s,%s,%s)",
                (uuid.uuid4(), run_id, task_id, repository_id, request.role.value),
            )
            if not cursor.fetchone()[0]:
                raise StoreError("capacity changed during claim")
            cursor.execute(
                "UPDATE factory.tasks SET state='leased',current_run_id=%s,current_fence=%s,updated_at=clock_timestamp() WHERE task_id=%s",
                (run_id, fence, task_id),
            )
            key = canonical_digest({"action": "claim", "run_id": str(run_id), "fence": fence})
            self._event(
                cursor,
                str(task_id),
                actor,
                "claimed",
                key,
                {"run_id": str(run_id), "fence": fence, "role": request.role.value},
            )
            self._audit(
                cursor, str(task_id), actor, "claim", f"run:{run_id}", "scheduled", key, {"fence": fence}, str(run_id)
            )
            grant = LeaseGrant(
                str(task_id), str(run_id), request.owner, request.role, fence, expires, packet_digest.strip()
            )
            self._record_command(
                cursor, idempotency_key, actor, "claim", request_digest, correlation_id,
                {"grant": {
                    "task_id": grant.task_id, "run_id": grant.run_id, "owner": grant.owner,
                    "role": grant.role.value, "fence": grant.fence,
                    "expires_at": grant.expires_at.isoformat().replace("+00:00", "Z"),
                    "packet_digest": grant.packet_digest,
                }},
            )
            return grant

    def execution_material(self, grant: LeaseGrant) -> dict[str, object]:
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            self._lock_grant(cursor, grant)
            cursor.execute(
                """SELECT t.repository_id,t.packet_digest,t.deadline_at,i.body
                FROM factory.tasks t JOIN factory.accepted_intents i ON i.intent_id=t.intent_id
                WHERE t.task_id=%s AND t.current_run_id=%s""",
                (grant.task_id, grant.run_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise FenceError("stale or expired fence")
            repository_id, legacy_digest, deadline, body = row
            if isinstance(body, str):
                body = json.loads(body)
            try:
                return {
                    "repository_id": repository_id,
                    "legacy_intent_digest": legacy_digest.strip(),
                    "route_id": body["route_id"],
                    "change_id": body["change_id"],
                    "exact_base_sha": body["exact_base_sha"],
                    "exact_head_sha": body["governance"]["exact_head_sha"],
                    "spec_digest": body["spec_digest"],
                    "architecture_digest": body["architecture"]["architecture_digest"],
                    "governance_digest": body["governance"]["governance_digest"],
                    "policy_digest": body["policy_digest"],
                    "acceptance_ids": body["acceptance_ids"],
                    "limits": body["limits"],
                    "deadline": deadline.isoformat().replace("+00:00", "Z"),
                }
            except (KeyError, TypeError) as exc:
                raise StoreError("accepted intent cannot build an execution packet") from exc

    def start_execution(
        self,
        grant: LeaseGrant,
        packet,
        manifest,
        actor: Actor,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> ExecutionGrant:
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            self._lock_grant(cursor, grant)
            command = {
                "run_id": grant.run_id,
                "legacy_packet_digest": grant.packet_digest,
                "execution_packet_digest": packet.packet_digest,
                "manifest_digest": manifest.manifest_digest,
            }
            replay, prior, request_digest = self._command_replay(
                cursor, idempotency_key, actor, "execution_start", command
            )
            if replay:
                return ExecutionGrant(
                    grant,
                    prior["packet_digest"],
                    prior["manifest_digest"],
                    prior["workspace_handle"],
                    prior["provider_id"],
                    ExecutionStage(prior["stage"]),
                )
            cursor.execute(
                "SELECT factory.execution_start(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)",
                (
                    grant.task_id,
                    grant.run_id,
                    grant.owner,
                    grant.fence,
                    grant.packet_digest,
                    packet.packet_digest,
                    manifest.manifest_digest,
                    manifest.workspace_handle,
                    manifest.provider_id,
                    json.dumps(packet.to_dict(), sort_keys=True, separators=(",", ":")),
                    json.dumps(manifest.to_dict(), sort_keys=True, separators=(",", ":")),
                ),
            )
            if not cursor.fetchone()[0]:
                raise FenceError("stale or expired fence")
            result = ExecutionGrant(
                grant,
                packet.packet_digest,
                manifest.manifest_digest,
                manifest.workspace_handle,
                manifest.provider_id,
                ExecutionStage.PREPARED,
            )
            recorded = {
                "packet_digest": result.packet_digest,
                "manifest_digest": result.manifest_digest,
                "workspace_handle": result.workspace_handle,
                "provider_id": result.provider_id,
                "stage": result.stage.value,
            }
            self._record_command(
                cursor,
                idempotency_key,
                actor,
                "execution_start",
                request_digest,
                correlation_id,
                recorded,
            )
            self._audit(
                cursor,
                grant.task_id,
                actor,
                "execution_start",
                f"run:{grant.run_id}",
                "packet_manifest_persisted",
                correlation_id or idempotency_key or packet.packet_digest,
                {"packet_digest": packet.packet_digest, "manifest_digest": manifest.manifest_digest},
                grant.run_id,
            )
            return result

    def advance_execution(
        self,
        grant: LeaseGrant,
        packet_digest: str,
        stage: ExecutionStage,
        actor: Actor,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> ExecutionStage:
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            self._lock_grant(cursor, grant)
            command = {"run_id": grant.run_id, "packet_digest": packet_digest, "stage": stage.value}
            replay, prior, request_digest = self._command_replay(
                cursor, idempotency_key, actor, "execution_advance", command
            )
            if replay:
                return ExecutionStage(prior["stage"])
            cursor.execute(
                "SELECT factory.execution_advance(%s,%s,%s,%s,%s,%s,%s)",
                (
                    grant.task_id,
                    grant.run_id,
                    grant.owner,
                    grant.fence,
                    grant.packet_digest,
                    packet_digest,
                    stage.value,
                ),
            )
            if not cursor.fetchone()[0]:
                raise FenceError("stale execution stage or fence")
            self._record_command(
                cursor,
                idempotency_key,
                actor,
                "execution_advance",
                request_digest,
                correlation_id,
                {"stage": stage.value},
            )
            return stage

    def proposal_context(self, grant: LeaseGrant, packet_digest: str) -> ProposalContext:
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            locked_grant = self._lock_grant(cursor, grant)
            cursor.execute(
                "SELECT factory.execution_proposal_context(%s,%s,%s,%s,%s,%s)",
                (
                    grant.task_id, grant.run_id, grant.owner, grant.fence,
                    grant.packet_digest, packet_digest,
                ),
            )
            row = cursor.fetchone()
            if row is None or row[0] is None:
                raise FenceError("stale execution packet or terminal manifest")
            body = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            limits = body["limits"]
            return ProposalContext(
                grant.task_id,
                grant.run_id,
                grant.owner,
                grant.fence,
                packet_digest,
                locked_grant[1],
                body["repository_id"],
                body["workspace_handle"],
                tuple(body["capability_policy"]["allowed_paths"]),
                tuple(body["capability_policy"]["artifact_classes"]),
                min(65_536, limits["max_output_bytes"]),
                limits["max_output_bytes"],
                limits["max_output_bytes"],
                limits["max_cost_usd_micros"],
                limits["max_token_units"],
                tuple(body["provider"]["capabilities"]),
            )

    @staticmethod
    def _execution_proposal_command(grant: LeaseGrant, event: CanonicalEvent) -> dict:
        return {
            "contract": "adaptive-factory.execution-propose-command/v1",
            "grant": {
                "task_id": grant.task_id,
                "run_id": grant.run_id,
                "owner": grant.owner,
                "role": grant.role.value,
                "fence": grant.fence,
                "legacy_packet_digest": grant.packet_digest,
            },
            "event": event.to_dict(),
        }

    @staticmethod
    def _proposal_kind(event_type: str) -> str:
        if event_type == "note.proposed":
            return "note"
        if event_type == "artifact.proposed":
            return "artifact"
        if event_type == "usage.reported":
            return "usage"
        if event_type in {"run.completed", "run.failed", "run.needs_human"}:
            return "terminal"
        raise StoreError("unsupported execution proposal")

    @classmethod
    def _stored_execution_proposal(
        cls,
        cursor,
        grant: LeaseGrant,
        event: CanonicalEvent,
        result: dict,
    ):
        if not isinstance(result, dict) or set(result) != {
            "proposal_kind", "sequence", "proposal_idempotency_key"
        }:
            raise StoreError("persisted execution proposal command is corrupt")
        expected_kind = cls._proposal_kind(event.event_type)
        proposal_digest = result["proposal_idempotency_key"]
        if (
            result["proposal_kind"] != expected_kind
            or type(result["sequence"]) is not int
            or result["sequence"] != event.sequence
            or not isinstance(proposal_digest, str)
            or not HEX64.fullmatch(proposal_digest)
        ):
            raise StoreError("persisted execution proposal command is corrupt")
        cursor.execute(
            "SELECT factory.execution_proposal_by_key(%s,%s,%s)",
            (grant.task_id, grant.run_id, proposal_digest),
        )
        envelope = cursor.fetchone()[0]
        if envelope is None:
            raise StoreError("persisted execution proposal is missing")
        if isinstance(envelope, str):
            envelope = json.loads(envelope)
        if not isinstance(envelope, dict) or set(envelope) != {
            "task_id", "run_id", "packet_digest", "producer_sequence", "proposal_kind",
            "idempotency_key", "body",
        }:
            raise StoreError("persisted execution proposal is corrupt")
        task_id = envelope["task_id"]
        run_id = envelope["run_id"]
        packet_digest = envelope["packet_digest"]
        sequence = envelope["producer_sequence"]
        kind = envelope["proposal_kind"]
        stored_digest = envelope["idempotency_key"]
        body = envelope["body"]
        if (
            str(task_id) != grant.task_id
            or str(run_id) != grant.run_id
            or packet_digest != event.packet_digest
            or sequence != event.sequence
            or kind != expected_kind
            or stored_digest != proposal_digest
        ):
            raise StoreError("persisted execution proposal is corrupt")
        classes = {
            "note": NoteProposal,
            "artifact": ArtifactProposal,
            "usage": UsageProposal,
            "terminal": TerminalProposal,
        }
        proposal_type = classes.get(kind)
        if proposal_type is None or not isinstance(body, dict) or set(body) != set(proposal_type.__dataclass_fields__):
            raise StoreError("persisted execution proposal is corrupt")
        try:
            if proposal_type is NoteProposal:
                if not isinstance(body.get("evidence"), list):
                    raise TypeError("invalid persisted evidence")
                body["evidence"] = tuple(body["evidence"])
            proposal = proposal_type(**body)
        except (TypeError, ValueError) as exc:
            raise StoreError("persisted execution proposal is corrupt") from exc
        if (
            proposal.task_id != grant.task_id
            or proposal.run_id != grant.run_id
            or proposal.packet_digest != event.packet_digest
            or proposal.fence != grant.fence
            or proposal.author_role != grant.role.value
            or proposal.sequence != sequence
            or proposal.idempotency_key != stored_digest
            or proposal.idempotency_key != proposal_digest
            or proposal_idempotency_key(proposal) != proposal_digest
            or (
                isinstance(proposal, TerminalProposal)
                and proposal.terminal_type != event.event_type
            )
        ):
            raise StoreError("persisted execution proposal is corrupt")
        return proposal

    def execution_proposal_replay(
        self,
        grant: LeaseGrant,
        event: CanonicalEvent,
        actor: Actor,
        *,
        idempotency_key: str | None,
    ):
        if idempotency_key is None:
            return None
        command = self._execution_proposal_command(grant, event)
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            replay, prior, _request_digest = self._command_replay(
                cursor, idempotency_key, actor, "execution_propose", command
            )
            if not replay:
                return None
            return self._stored_execution_proposal(
                cursor, grant, event, prior
            )

    def commit_execution_proposal(
        self,
        grant: LeaseGrant,
        proposal,
        actor: Actor,
        *,
        event: CanonicalEvent,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ):
        kinds = {
            NoteProposal: "note",
            ArtifactProposal: "artifact",
            UsageProposal: "usage",
            TerminalProposal: "terminal",
        }
        kind = kinds.get(type(proposal))
        if kind is None:
            raise StoreError("unsupported execution proposal")
        expected_kind = self._proposal_kind(event.event_type)
        if (
            kind != expected_kind
            or event.protocol_version != PROTOCOL_VERSION
            or event.task_id != grant.task_id
            or event.run_id != grant.run_id
            or proposal.task_id != grant.task_id
            or proposal.run_id != grant.run_id
            or proposal.packet_digest != event.packet_digest
            or proposal.fence != grant.fence
            or proposal.sequence != event.sequence
            or proposal.author_role != grant.role.value
            or proposal.idempotency_key != proposal_idempotency_key(proposal)
            or (
                isinstance(proposal, TerminalProposal)
                and proposal.terminal_type != event.event_type
            )
        ):
            raise StoreError("execution proposal does not match command")
        body = asdict(proposal)
        command = self._execution_proposal_command(grant, event)
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            replay, prior, request_digest = self._command_replay(
                cursor, idempotency_key, actor, "execution_propose", command
            )
            if replay:
                return self._stored_execution_proposal(
                    cursor, grant, event, prior
                )
            self._lock_grant(cursor, grant)
            cursor.execute(
                "SELECT factory.execution_propose(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
                (
                    grant.task_id, grant.run_id, grant.owner, grant.fence, grant.packet_digest,
                    proposal.packet_digest, proposal.sequence, proposal.idempotency_key, kind,
                    json.dumps(body, sort_keys=True, separators=(",", ":")),
                ),
            )
            if not cursor.fetchone()[0]:
                raise FenceError("stale execution proposal or fence")
            self._record_command(
                cursor, idempotency_key, actor, "execution_propose", request_digest,
                correlation_id, {
                    "proposal_kind": kind,
                    "sequence": proposal.sequence,
                    "proposal_idempotency_key": proposal.idempotency_key,
                },
            )
            return proposal

    @staticmethod
    def _workspace_bundle(value) -> tuple[WorkspaceResultV1, WorkspaceSnapshotV1, TaskPacketV1, RunManifestV1] | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = json.loads(value)
        try:
            packet_wire = dict(value["packet"])
            packet_digest = packet_wire.pop("packet_digest")
            packet = TaskPacketV1.from_dict(packet_wire)
            if packet.packet_digest != packet_digest:
                raise StoreError("stored workspace packet digest mismatch")
            manifest_wire = dict(value["manifest"])
            manifest_digest = manifest_wire.pop("manifest_digest")
            manifest = RunManifestV1.from_packet(packet, deadline=manifest_wire["deadline"])
            if manifest.to_dict() != {**manifest_wire, "manifest_digest": manifest_digest}:
                raise StoreError("stored workspace manifest mismatch")
            result = WorkspaceResultV1.from_dict(value["result"])
            snapshot = WorkspaceSnapshotV1.from_dict(value["snapshot"])
            row = value["row"]
            expected_row = {
                "workspace_result_digest": result.workspace_result_digest,
                "task_id": result.task_id,
                "run_id": result.run_id,
                "task_packet_digest": result.task_packet_digest,
                "run_manifest_digest": result.run_manifest_digest,
                "exact_head_sha": result.exact_head_sha,
                "workspace_snapshot_digest": result.workspace_snapshot_digest,
                "terminal_stage": result.terminal_stage,
                "terminal_proposal_digest": result.terminal_proposal_digest,
                "terminal_proposal_kind": "terminal",
                "artifact_manifest_digest": result.artifact_manifest_digest,
                "note_manifest_digest": result.note_manifest_digest,
                "usage_evidence_digest": result.usage_evidence_digest,
                "diagnostics_digest": result.diagnostics_digest,
                "m4_status": result.m4_status,
                "failure_class": result.failure_class,
                "failure_reason": result.failure_reason,
            }
            if row != expected_row:
                raise StoreError("stored workspace row mismatch")
            if (
                result.task_id != packet.task_id
                or result.run_id != packet.run_id
                or result.task_packet_digest != packet.packet_digest
                or result.run_manifest_digest != manifest.manifest_digest
                or snapshot.repository_id != packet.repository_id
                or snapshot.workspace_handle != packet.workspace_handle
                or snapshot.input_head_sha != packet.authority.exact_head_sha
                or snapshot.result_head_sha != result.exact_head_sha
                or snapshot.workspace_snapshot_digest != result.workspace_snapshot_digest
            ):
                raise StoreError("stored workspace bundle binding mismatch")
            return result, snapshot, packet, manifest
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, StoreError):
                raise
            raise StoreError("stored workspace bundle is corrupt") from exc

    def finalize_execution(
        self,
        grant: LeaseGrant,
        packet_digest: str,
        snapshot: WorkspaceSnapshotV1,
        actor: Actor,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> WorkspaceResultV1:
        command = {
            "task_id": grant.task_id,
            "run_id": grant.run_id,
            "packet_digest": packet_digest,
        }
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            replay, prior, request_digest = self._command_replay(
                cursor, idempotency_key, actor, "execution_finalize", command
            )
            if replay:
                return WorkspaceResultV1.from_dict(prior["result"])
            cursor.execute("SELECT factory.execution_result_for_run(%s,%s)", (grant.task_id, grant.run_id))
            existing = self._workspace_bundle(cursor.fetchone()[0])
            if existing is not None:
                result, stored_snapshot, _packet, _manifest = existing
                if (
                    result.task_packet_digest != packet_digest
                    or stored_snapshot.workspace_snapshot_digest != snapshot.workspace_snapshot_digest
                ):
                    raise StoreError("workspace result already exists with different facts")
                self._record_command(
                    cursor, idempotency_key, actor, "execution_finalize", request_digest,
                    correlation_id, {"result": result.to_dict()},
                )
                return result
            cursor.execute(
                "SELECT factory.execution_finalize_context(%s,%s,%s,%s,%s,%s)",
                (
                    grant.task_id, grant.run_id, grant.owner, grant.fence,
                    grant.packet_digest, packet_digest,
                ),
            )
            context = cursor.fetchone()[0]
            if context is None:
                raise FenceError("execution cannot be finalized")
            if isinstance(context, str):
                context = json.loads(context)
            if (
                snapshot.repository_id != context["repository_id"]
                or snapshot.workspace_handle != context["workspace_handle"]
                or snapshot.input_head_sha != context["input_head_sha"]
            ):
                raise FenceError("workspace snapshot does not bind execution")
            result = WorkspaceResultV1.from_facts(
                {
                    "contract_version": 1,
                    "task_id": grant.task_id,
                    "run_id": grant.run_id,
                    "task_packet_digest": packet_digest,
                    "run_manifest_digest": context["run_manifest_digest"],
                    "exact_head_sha": snapshot.result_head_sha,
                    "workspace_snapshot_digest": snapshot.workspace_snapshot_digest,
                    "terminal_stage": context["terminal_stage"],
                    "terminal_proposal_digest": context["terminal_proposal_digest"],
                    "artifact_manifest_digest": workspace_evidence_digest(
                        "artifacts", context["artifact_digests"]
                    ),
                    "note_manifest_digest": workspace_evidence_digest("notes", context["note_digests"]),
                    "usage_evidence_digest": workspace_evidence_digest("usage", context["usage_digests"]),
                    "diagnostics_digest": workspace_evidence_digest(
                        "diagnostics", context["diagnostic_digests"]
                    ),
                    "m4_status": context["m4_status"],
                    "failure_class": context["failure_class"],
                    "failure_reason": context["failure_reason"],
                }
            )
            cursor.execute(
                "SELECT factory.execution_finalize_commit(%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)",
                (
                    grant.task_id, grant.run_id, grant.owner, grant.fence, grant.packet_digest,
                    packet_digest, result.workspace_result_digest,
                    json.dumps(snapshot.to_dict(), sort_keys=True, separators=(",", ":")),
                    json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":")),
                ),
            )
            if not cursor.fetchone()[0]:
                raise FenceError("execution finalization rejected")
            status = TaskStatus(result.m4_status)
            release_key = canonical_digest(
                {
                    "action": "execution_finalize",
                    "fence": grant.fence,
                    "run_id": grant.run_id,
                    "target": status.value,
                }
            )
            self._event(
                cursor,
                grant.task_id,
                actor,
                "released",
                release_key,
                {"target": status.value, "workspace_result_digest": result.workspace_result_digest},
                mandatory_cleanup=True,
            )
            self._audit(
                cursor,
                grant.task_id,
                actor,
                "execution_finalize",
                f"run:{grant.run_id}",
                status.value,
                correlation_id or release_key,
                {"fence": grant.fence, "workspace_result_digest": result.workspace_result_digest},
                grant.run_id,
            )
            self._record_command(
                cursor, idempotency_key, actor, "execution_finalize", request_digest,
                correlation_id, {"result": result.to_dict()},
            )
            return result

    def execution_finalization_replay(
        self,
        grant: LeaseGrant,
        packet_digest: str,
        actor: Actor,
        *,
        idempotency_key: str | None,
    ) -> WorkspaceResultV1 | None:
        if idempotency_key is None:
            return None
        command = {"task_id": grant.task_id, "run_id": grant.run_id, "packet_digest": packet_digest}
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            replay, prior, _request_digest = self._command_replay(
                cursor, idempotency_key, actor, "execution_finalize", command
            )
            return WorkspaceResultV1.from_dict(prior["result"]) if replay else None

    def workspace_snapshot_request(self, grant: LeaseGrant, packet_digest: str) -> WorkspaceSnapshotRequest:
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            cursor.execute(
                "SELECT factory.execution_finalize_context(%s,%s,%s,%s,%s,%s)",
                (
                    grant.task_id, grant.run_id, grant.owner, grant.fence,
                    grant.packet_digest, packet_digest,
                ),
            )
            context = cursor.fetchone()[0]
            if context is None:
                cursor.execute("SELECT factory.execution_result_for_run(%s,%s)", (grant.task_id, grant.run_id))
                existing = self._workspace_bundle(cursor.fetchone()[0])
                if existing is None:
                    raise FenceError("execution snapshot context unavailable")
                result, snapshot, _packet, _manifest = existing
                return WorkspaceSnapshotRequest(
                    result.task_id,
                    result.run_id,
                    snapshot.repository_id,
                    snapshot.workspace_handle,
                    snapshot.input_head_sha,
                )
            if isinstance(context, str):
                context = json.loads(context)
            return WorkspaceSnapshotRequest(
                grant.task_id,
                grant.run_id,
                context["repository_id"],
                context["workspace_handle"],
                context["input_head_sha"],
            )

    def workspace_result(self, task_id: str, workspace_result_digest: str):
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SET statement_timeout='5s'")
            cursor.execute(
                "SELECT factory.execution_result_by_digest(%s,%s)",
                (task_id, workspace_result_digest),
            )
            bundle = self._workspace_bundle(cursor.fetchone()[0])
            if bundle is None:
                raise KeyError(workspace_result_digest)
            result, snapshot, packet, manifest = bundle
            if result.workspace_result_digest != workspace_result_digest:
                raise StoreError("requested workspace result digest mismatch")
            return {"result": result, "snapshot": snapshot, "packet": packet, "manifest": manifest}

    @staticmethod
    def _lock_capacity_for_run(cursor, run_id: str) -> bool:
        cursor.execute("SELECT factory.capacity_lock_run(%s)", (run_id,))
        return bool(cursor.fetchone()[0])

    def _close_active_lease(self, cursor, task_id: str) -> None:
        cursor.execute(
            """SELECT r.run_id,r.role,a.repository_id FROM factory.tasks t
            JOIN factory.runs r ON r.run_id=t.current_run_id
            JOIN factory.capacity_allocations a ON a.run_id=r.run_id
            WHERE t.task_id=%s AND r.released_at IS NULL""",
            (task_id,),
        )
        candidate = cursor.fetchone()
        if candidate is None:
            return
        run_id, _role, _repository_id = candidate
        if not self._lock_capacity_for_run(cursor, str(run_id)):
            return
        cursor.execute(
            """SELECT r.run_id FROM factory.tasks t JOIN factory.runs r ON r.run_id=t.current_run_id
            JOIN factory.capacity_allocations a ON a.run_id=r.run_id
            WHERE t.task_id=%s AND r.run_id=%s AND r.released_at IS NULL FOR UPDATE OF t,r""",
            (task_id, run_id),
        )
        if cursor.fetchone() is None:
            return
        cursor.execute("UPDATE factory.runs SET state='released',released_at=clock_timestamp() WHERE run_id=%s", (run_id,))
        cursor.execute("UPDATE factory.attempts SET finished_at=clock_timestamp() WHERE run_id=%s", (run_id,))
        cursor.execute("SELECT factory.capacity_release(%s)", (run_id,))
        if not cursor.fetchone()[0]:
            raise StoreError("live lease capacity was not released")

    def _close_orphan_run(self, cursor, run_id: str, task_id: str, role: str, repository_id: str, actor: Actor) -> bool:
        if not self._lock_capacity_for_run(cursor, run_id):
            return False
        cursor.execute(
            """SELECT r.run_id FROM factory.runs r JOIN factory.capacity_allocations a ON a.run_id=r.run_id
            WHERE r.run_id=%s AND r.task_id=%s AND r.released_at IS NULL AND a.released_at IS NULL
            FOR UPDATE OF r""",
            (run_id, task_id),
        )
        if cursor.fetchone() is None:
            return False
        cursor.execute("UPDATE factory.runs SET state='expired',released_at=clock_timestamp() WHERE run_id=%s", (run_id,))
        cursor.execute(
            """UPDATE factory.attempts SET failure_class='worker_lost',failure_code='orphaned_projection',
            failure_digest=%s,finished_at=clock_timestamp() WHERE run_id=%s""",
            (canonical_digest({"failure": "orphaned_projection"}), run_id),
        )
        cursor.execute("SELECT factory.capacity_release(%s)", (run_id,))
        if not cursor.fetchone()[0]:
            raise StoreError("orphan capacity was not released")
        key = canonical_digest({"action": "reconcile_orphan", "run_id": run_id})
        self._event(
            cursor, task_id, actor, "orphan_reconciled", key, {"run_id": run_id}, mandatory_cleanup=True
        )
        self._audit(cursor, task_id, actor, "reconcile_orphan", f"run:{run_id}", "orphaned_projection", key, run_id=run_id)
        return True

    def _lock_grant(self, cursor, grant: LeaseGrant, *, allow_expired: bool = False):
        cursor.execute(
            """SELECT r.task_id,r.role,a.repository_id,at.attempt_no
            FROM factory.runs r JOIN factory.tasks t ON t.task_id=r.task_id
            JOIN factory.capacity_allocations a ON a.run_id=r.run_id
            JOIN factory.attempts at ON at.run_id=r.run_id
            WHERE r.run_id=%s AND r.task_id=%s AND r.owner_id=%s AND r.role=%s
            AND r.fence=%s AND r.packet_digest=%s
            AND r.state='leased' AND r.released_at IS NULL
            AND a.released_at IS NULL
            AND (%s OR r.lease_expires_at>clock_timestamp())
            AND t.current_run_id=r.run_id AND t.current_fence=r.fence AND t.state='leased' AND t.deadline_at>clock_timestamp()
            FOR UPDATE OF r,t""",
            (
                grant.run_id,
                grant.task_id,
                grant.owner,
                grant.role.value,
                grant.fence,
                grant.packet_digest,
                allow_expired,
            ),
        )
        row = cursor.fetchone()
        if not row:
            raise FenceError("stale or expired fence")
        return row

    def heartbeat(self, grant: LeaseGrant, actor: Actor, now: datetime, *, idempotency_key: str | None = None, correlation_id: str | None = None) -> LeaseGrant:
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            command = {"grant": {"task_id": grant.task_id, "run_id": grant.run_id, "owner": grant.owner, "role": grant.role.value, "fence": grant.fence, "packet_digest": grant.packet_digest}}
            replay, prior, request_digest = self._command_replay(cursor, idempotency_key, actor, "heartbeat", command)
            if replay:
                return LeaseGrant(grant.task_id, grant.run_id, grant.owner, grant.role, grant.fence, datetime.fromisoformat(prior["expires_at"].replace("Z", "+00:00")), grant.packet_digest)
            self._lock_grant(cursor, grant)
            cursor.execute(
                "UPDATE factory.runs SET lease_expires_at=LEAST(clock_timestamp()+interval '30 seconds',deadline_at) WHERE run_id=%s RETURNING lease_expires_at",
                (grant.run_id,),
            )
            expires = cursor.fetchone()[0]
            result = LeaseGrant(
                grant.task_id, grant.run_id, grant.owner, grant.role, grant.fence, expires, grant.packet_digest
            )
            self._record_command(cursor, idempotency_key, actor, "heartbeat", request_digest, correlation_id, {"expires_at": expires.isoformat().replace("+00:00", "Z")})
            return result

    def _release_locked(
        self, cursor, grant: LeaseGrant, outcome: str | FailureClass, actor: Actor, *, allow_expired: bool = False,
        correlation_id: str | None = None
    ) -> TaskStatus:
        cursor.execute("SELECT repository_id FROM factory.tasks WHERE task_id=%s", (grant.task_id,))
        repository = cursor.fetchone()
        if repository is None:
            raise FenceError("stale or expired fence")
        if not self._lock_capacity_for_run(cursor, grant.run_id):
            raise FenceError("stale or expired fence")
        task_id, _role, _repository_id, attempt_no = self._lock_grant(cursor, grant, allow_expired=allow_expired)
        if isinstance(outcome, FailureClass):
            decision = classify_retry(outcome, attempt_no=attempt_no)
            target = TaskStatus.RETRY if decision.retry else (decision.terminal or TaskStatus.NEEDS_HUMAN)
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM factory.budget_reservations WHERE task_id=%s AND run_id=%s AND released_at IS NULL)",
                (grant.task_id, grant.run_id),
            )
            if cursor.fetchone()[0]:
                target = TaskStatus.NEEDS_HUMAN
                cursor.execute(
                    "UPDATE factory.tasks SET accounting_blocked=true WHERE task_id=%s", (grant.task_id,)
                )
            cursor.execute(
                "UPDATE factory.attempts SET failure_class=%s,failure_code=%s,failure_digest=%s,finished_at=clock_timestamp() WHERE run_id=%s",
                (outcome.value, outcome.value, canonical_digest({"failure": outcome.value}), grant.run_id),
            )
        elif outcome == "completed":
            cursor.execute(
                """SELECT t.accounting_blocked,
                EXISTS(SELECT 1 FROM factory.usage_observations u WHERE u.task_id=t.task_id AND u.run_id=%s),
                EXISTS(SELECT 1 FROM factory.budget_reservations b WHERE b.task_id=t.task_id AND b.released_at IS NULL),
                t.cost_reserved_micros,t.tokens_reserved,t.wall_reserved_seconds
                FROM factory.tasks t WHERE t.task_id=%s""",
                (grant.run_id, grant.task_id),
            )
            blocked, has_usage, has_reservation, reserved_cost, reserved_tokens, reserved_wall = cursor.fetchone()
            if blocked or not has_usage or has_reservation or any((reserved_cost, reserved_tokens, reserved_wall)):
                raise BudgetError("completion requires settled accounting")
            target = TaskStatus.READY_FOR_HUMAN
            cursor.execute("UPDATE factory.attempts SET finished_at=clock_timestamp() WHERE run_id=%s", (grant.run_id,))
        else:
            raise StoreError("unsupported release outcome")
        if target is TaskStatus.RETRY and not self._ordinary_event_capacity_available(cursor, grant.task_id):
            target = TaskStatus.NEEDS_HUMAN
        cursor.execute(
            "UPDATE factory.runs SET state=%s,released_at=clock_timestamp() WHERE run_id=%s",
            ("failed" if isinstance(outcome, FailureClass) else "completed", grant.run_id),
        )
        cursor.execute("SELECT factory.capacity_release(%s)", (grant.run_id,))
        if not cursor.fetchone()[0]:
            raise StoreError("lease capacity was not released")
        terminal = target in {TaskStatus.DEAD, TaskStatus.READY_FOR_HUMAN}
        cursor.execute(
            "UPDATE factory.tasks SET state=%s,current_run_id=NULL,current_fence=NULL,updated_at=clock_timestamp(),terminal_at=CASE WHEN %s THEN clock_timestamp() ELSE terminal_at END WHERE task_id=%s",
            (target.value, terminal, task_id),
        )
        key = canonical_digest(
            {"action": "release", "run_id": grant.run_id, "fence": grant.fence, "target": target.value}
        )
        self._event(
            cursor, str(task_id), actor, "released", key, {"target": target.value}, mandatory_cleanup=True
        )
        self._audit(
            cursor,
            str(task_id),
            actor,
            "release",
            f"run:{grant.run_id}",
            target.value,
            correlation_id or key,
            {"fence": grant.fence},
            grant.run_id,
        )
        return target

    def release(self, grant: LeaseGrant, outcome: str | FailureClass, actor: Actor, now: datetime, *, idempotency_key: str | None = None, correlation_id: str | None = None) -> TaskStatus:
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            outcome_value = outcome.value if isinstance(outcome, FailureClass) else outcome
            command = {"task_id": grant.task_id, "run_id": grant.run_id, "fence": grant.fence, "outcome": outcome_value}
            replay, prior, request_digest = self._command_replay(cursor, idempotency_key, actor, "release", command)
            if replay:
                return TaskStatus(prior["status"])
            cursor.execute(
                "SELECT factory.execution_has_packet(%s)",
                (grant.run_id,),
            )
            if cursor.fetchone()[0]:
                raise FenceError("M5 execution outcome is derived only by finalization")
            result = self._release_locked(cursor, grant, outcome, actor, correlation_id=correlation_id)
            self._record_command(cursor, idempotency_key, actor, "release", request_digest, correlation_id, {"status": result.value})
            return result

    def reserve_budget(
        self, grant: LeaseGrant, cost: int, tokens: int, wall: int, reason_digest: str, key: str, actor: Actor,
        *, correlation_id: str | None = None,
    ) -> str:
        if (
            any(type(value) is not int or value < 0 for value in (cost, tokens, wall))
            or not HEX64.fullmatch(reason_digest)
            or not HEX64.fullmatch(key)
        ):
            raise BudgetError("invalid budget evidence")
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            command = {
                "task_id": grant.task_id, "run_id": grant.run_id, "fence": grant.fence,
                "cost_usd_micros": cost, "token_units": tokens, "wall_seconds": wall,
                "reason_digest": reason_digest,
            }
            replay, prior, request_digest = self._command_replay(cursor, key, actor, "reserve_budget", command)
            if replay:
                return prior["reservation_id"]
            self._lock_grant(cursor, grant)
            cursor.execute(
                """SELECT reservation_id,task_id,run_id,cost_usd_micros,token_units,wall_seconds,reason_digest
                FROM factory.budget_reservations WHERE idempotency_key=%s""",
                (key,),
            )
            duplicate = cursor.fetchone()
            if duplicate:
                expected = (grant.task_id, grant.run_id, cost, tokens, wall, reason_digest)
                actual = (str(duplicate[1]), str(duplicate[2]), duplicate[3], duplicate[4], duplicate[5], duplicate[6].strip())
                if actual != expected:
                    raise StoreError("idempotency key reused with different budget request")
                reservation_id = str(duplicate[0])
                self._record_command(
                    cursor, key, actor, "reserve_budget", request_digest, correlation_id,
                    {"reservation_id": reservation_id},
                )
                return reservation_id
            cursor.execute(
                "SELECT cost_limit_micros,token_limit,wall_limit_seconds,cost_reserved_micros,cost_observed_micros,tokens_reserved,tokens_observed,wall_reserved_seconds,accounting_blocked FROM factory.tasks WHERE task_id=%s FOR UPDATE",
                (grant.task_id,),
            )
            cost_limit, token_limit, wall_limit, reserved_cost, observed_cost, reserved_tokens, observed_tokens, reserved_wall, blocked = cursor.fetchone()
            if (
                blocked
                or reserved_cost + observed_cost + cost > cost_limit
                or reserved_tokens + observed_tokens + tokens > token_limit
                or reserved_wall + wall > wall_limit
            ):
                raise BudgetError("budget exceeded or accounting blocked")
            reservation_id = uuid.uuid4()
            cursor.execute(
                "INSERT INTO factory.budget_reservations(reservation_id,task_id,run_id,idempotency_key,cost_usd_micros,token_units,wall_seconds,reason_digest) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(idempotency_key) DO NOTHING RETURNING reservation_id",
                (reservation_id, grant.task_id, grant.run_id, key, cost, tokens, wall, reason_digest),
            )
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    "UPDATE factory.tasks SET cost_reserved_micros=cost_reserved_micros+%s,tokens_reserved=tokens_reserved+%s,wall_reserved_seconds=wall_reserved_seconds+%s WHERE task_id=%s",
                    (cost, tokens, wall, grant.task_id),
                )
            result = str(row[0] if row else reservation_id)
            self._record_command(
                cursor, key, actor, "reserve_budget", request_digest, correlation_id,
                {"reservation_id": result},
            )
            return result

    def observe_usage(
        self,
        grant: LeaseGrant,
        provider_call_id: str,
        price_table_digest: str | None,
        cost: int,
        tokens: int,
        output: int,
        actor: Actor,
        *,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> UsageResult:
        if (
            not isinstance(provider_call_id, str)
            or not 1 <= len(provider_call_id.encode("utf-8")) <= 128
            or any(type(value) is not int or value < 0 for value in (cost, tokens, output))
        ):
            raise BudgetError("invalid usage evidence")
        blocked_reason = None
        result = None
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            command = {
                "task_id": grant.task_id, "run_id": grant.run_id, "fence": grant.fence,
                "provider_call_id": provider_call_id, "price_table_digest": price_table_digest,
                "cost_usd_micros": cost, "token_units": tokens, "output_bytes": output,
            }
            replay, prior, request_digest = self._command_replay(
                cursor, idempotency_key, actor, "observe_usage", command
            )
            if replay:
                if "error" in prior:
                    raise BudgetError(prior["error"])
                return UsageResult(prior["observation_id"], prior["created"])
            self._lock_grant(cursor, grant)
            if not isinstance(price_table_digest, str) or not HEX64.fullmatch(price_table_digest):
                blocked_reason = "missing_price_table"
            else:
                cursor.execute(
                    """SELECT observation_id,price_table_digest,cost_usd_micros,token_units,output_bytes
                    FROM factory.usage_observations WHERE run_id=%s AND provider_call_id=%s""",
                    (grant.run_id, provider_call_id),
                )
                duplicate = cursor.fetchone()
                if duplicate:
                    if (duplicate[1].strip(), duplicate[2], duplicate[3], duplicate[4]) != (price_table_digest, cost, tokens, output):
                        raise StoreError("provider call id reused with different usage evidence")
                    result = UsageResult(str(duplicate[0]), False)
                    self._record_command(
                        cursor, idempotency_key, actor, "observe_usage", request_digest, correlation_id,
                        {"observation_id": result.observation_id, "created": result.created},
                    )
                    return result
                cursor.execute(
                    """SELECT COALESCE(sum(cost_usd_micros),0),COALESCE(sum(token_units),0),COALESCE(sum(wall_seconds),0)
                    FROM factory.budget_reservations WHERE task_id=%s AND run_id=%s AND released_at IS NULL""",
                    (grant.task_id, grant.run_id),
                )
                released_cost, released_tokens, released_wall = cursor.fetchone()
                cursor.execute(
                    "UPDATE factory.budget_reservations SET released_at=clock_timestamp() WHERE task_id=%s AND run_id=%s AND released_at IS NULL",
                    (grant.task_id, grant.run_id),
                )
                cursor.execute(
                    """UPDATE factory.tasks SET cost_reserved_micros=cost_reserved_micros-%s,
                    tokens_reserved=tokens_reserved-%s,wall_reserved_seconds=wall_reserved_seconds-%s WHERE task_id=%s""",
                    (released_cost, released_tokens, released_wall, grant.task_id),
                )
                cursor.execute(
                    """SELECT cost_limit_micros,token_limit,output_limit_bytes,cost_observed_micros,tokens_observed,
                    COALESCE((SELECT sum(output_bytes) FROM factory.usage_observations WHERE task_id=t.task_id),0)
                    FROM factory.tasks t WHERE task_id=%s FOR UPDATE""",
                    (grant.task_id,),
                )
                cost_limit, token_limit, output_limit, observed_cost, observed_tokens, observed_output = (
                    cursor.fetchone()
                )
                if (
                    observed_cost + cost > cost_limit
                    or observed_tokens + tokens > token_limit
                    or observed_output + output > output_limit
                ):
                    blocked_reason = "usage_limit_exceeded"
                else:
                    observation_id = uuid.uuid4()
                    cursor.execute(
                        """INSERT INTO factory.usage_observations
                        (observation_id,task_id,run_id,provider_call_id,price_table_digest,cost_usd_micros,token_units,output_bytes)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (
                            observation_id,
                            grant.task_id,
                            grant.run_id,
                            provider_call_id,
                            price_table_digest,
                            cost,
                            tokens,
                            output,
                        ),
                    )
                    cursor.execute(
                        "UPDATE factory.tasks SET cost_observed_micros=cost_observed_micros+%s,tokens_observed=tokens_observed+%s WHERE task_id=%s",
                        (cost, tokens, grant.task_id),
                    )
                    result = UsageResult(str(observation_id), True)
            if blocked_reason:
                cursor.execute(
                    "UPDATE factory.tasks SET accounting_blocked=true,updated_at=clock_timestamp() WHERE task_id=%s",
                    (grant.task_id,),
                )
                key = canonical_digest(
                    {"action": "accounting_blocked", "run_id": grant.run_id, "reason": blocked_reason}
                )
                self._audit(
                    cursor,
                    grant.task_id,
                    actor,
                    "accounting_blocked",
                    f"run:{grant.run_id}",
                    blocked_reason,
                    correlation_id or key,
                    run_id=grant.run_id,
                )
                self._record_command(
                    cursor, idempotency_key, actor, "observe_usage", request_digest, correlation_id,
                    {"error": "accounting blocked"},
                )
            elif result is not None:
                self._record_command(
                    cursor, idempotency_key, actor, "observe_usage", request_digest, correlation_id,
                    {"observation_id": result.observation_id, "created": result.created},
                )
        if blocked_reason:
            raise BudgetError("accounting blocked")
        assert result is not None
        return result

    def set_kill(self, scope: str, enabled: bool, reason: str, key: str, actor: Actor, now: datetime, *, correlation_id: str | None = None) -> bool:
        if scope != "global" and not scope.startswith("repository:"):
            raise StoreError("invalid kill scope")
        if not HEX64.fullmatch(key) or not reason or len(reason) > 128:
            raise StoreError("invalid kill evidence")
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            command = {"scope": scope, "enabled": enabled, "reason": reason}
            replay, prior, request_digest = self._command_replay(cursor, key, actor, "set_kill", command)
            if replay:
                return bool(prior["enabled"])
            cursor.execute(
                "INSERT INTO factory.kill_switches(switch_id,scope_key,enabled,actor_id,reason,idempotency_key) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(idempotency_key) DO NOTHING RETURNING enabled",
                (uuid.uuid4(), scope, enabled, actor.actor_id, reason, key),
            )
            row = cursor.fetchone()
            actual = bool(row[0]) if row else enabled
            self._record_command(cursor, key, actor, "set_kill", request_digest, correlation_id, {"enabled": actual})
            return actual

    def reconcile(self, actor: Actor, now: datetime, limit: int, cursor_id: str | None, *, idempotency_key: str | None = None, correlation_id: str | None = None) -> ReconcileResult:
        repaired = 0
        last = None
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout='5s'")
            if not self._capacity_consistent(cursor):
                raise StoreError("capacity counters do not match live allocations")
            command = {"limit": limit, "cursor": cursor_id}
            replay, prior, request_digest = self._command_replay(cursor, idempotency_key, actor, "reconcile", command)
            if replay:
                return ReconcileResult(prior["candidates"], prior["repaired"], prior["cursor"])
            cursor.execute(
                """SELECT r.run_id,r.task_id,r.owner_id,r.role,r.fence,r.lease_expires_at,r.packet_digest,a.repository_id
                FROM factory.runs r JOIN factory.capacity_allocations a ON a.run_id=r.run_id
                WHERE r.released_at IS NULL AND a.released_at IS NULL AND r.lease_expires_at<=clock_timestamp()
                AND (%s::uuid IS NULL OR r.task_id>%s::uuid) ORDER BY r.task_id LIMIT %s""",
                (cursor_id, cursor_id, limit),
            )
            rows = cursor.fetchall()
            reconciliation_id = uuid.uuid4()
            cursor.execute(
                "INSERT INTO factory.reconciliation_runs(reconciliation_id,cursor_task_id,status,candidates) VALUES (%s,%s,'running',%s)",
                (reconciliation_id, cursor_id, len(rows)),
            )
            for row in rows:
                run_id, task_id, owner, role, fence, expires, packet, repository_id = row
                if not self._lock_capacity_for_run(cursor, str(run_id)):
                    continue
                cursor.execute(
                    "SELECT repair_count,repair_limit,state,current_run_id,current_fence FROM factory.tasks WHERE task_id=%s FOR UPDATE",
                    (task_id,),
                )
                repair_count, repair_limit, state, current_run_id, current_fence = cursor.fetchone()
                grant = LeaseGrant(str(task_id), str(run_id), owner, RunRole(role), fence, expires, packet.strip())
                failure = FailureClass.PROVIDER_QUALITY if repair_count >= repair_limit else FailureClass.WORKER_LOST
                if state == "leased" and str(current_run_id) == str(run_id) and current_fence == fence:
                    self._release_locked(cursor, grant, failure, actor, allow_expired=True)
                    cursor.execute("UPDATE factory.runs SET state='expired' WHERE run_id=%s", (run_id,))
                    if repair_count < repair_limit:
                        cursor.execute("UPDATE factory.tasks SET repair_count=repair_count+1 WHERE task_id=%s", (task_id,))
                    repaired += 1
                elif self._close_orphan_run(cursor, str(run_id), str(task_id), role, repository_id, actor):
                    repaired += 1
                last = str(task_id)
            cursor.execute(
                "UPDATE factory.reconciliation_runs SET status='completed',repaired=%s,finished_at=clock_timestamp(),cursor_task_id=%s WHERE reconciliation_id=%s",
                (repaired, last, reconciliation_id),
            )
            result = ReconcileResult(len(rows), repaired, last)
            self._record_command(cursor, idempotency_key, actor, "reconcile", request_digest, correlation_id, {"candidates": result.candidates, "repaired": result.repaired, "cursor": result.cursor})
        return result

    def cancel(self, task_id: str, reason: str, key: str, actor: Actor, now: datetime, *, correlation_id: str | None = None) -> TaskProjection:
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            command = {"task_id": task_id, "reason": reason}
            replay, _prior, request_digest = self._command_replay(cursor, key, actor, "cancel", command)
            if replay:
                return self.get_task(task_id)
            self._close_active_lease(cursor, task_id)
            cursor.execute("SELECT state FROM factory.tasks WHERE task_id=%s FOR UPDATE", (task_id,))
            row = cursor.fetchone()
            if not row:
                raise KeyError(task_id)
            if row[0] not in {"ready_for_human", "dead", "cancelled", "superseded"}:
                cursor.execute(
                    "UPDATE factory.tasks SET state='cancelled',current_run_id=NULL,current_fence=NULL,terminal_at=clock_timestamp(),updated_at=clock_timestamp() WHERE task_id=%s",
                    (task_id,),
                )
                self._event(
                    cursor, task_id, actor, "cancelled", key, {"reason": reason}, mandatory_cleanup=True
                )
                self._audit(cursor, task_id, actor, "cancel", f"task:{task_id}", reason, correlation_id or key)
            self._record_command(cursor, key, actor, "cancel", request_digest, correlation_id, {"task_id": task_id})
        return self.get_task(task_id)
