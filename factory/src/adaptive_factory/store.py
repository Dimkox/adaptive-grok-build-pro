from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import uuid

from .contracts import HEX64, TaskIntakeV1, canonical_digest
from .models import Actor, FailureClass, LeaseGrant, RunRole, TaskProjection, TaskStatus
from .state import classify_retry


class StoreError(RuntimeError):
    pass


class FenceError(StoreError):
    pass


class BudgetError(StoreError):
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


class PostgresFactoryStore:
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise StoreError("database URL is required")
        self.database_url = database_url

    def _connect(self):
        import psycopg

        return psycopg.connect(self.database_url)

    @staticmethod
    def _projection(row) -> TaskProjection:
        return TaskProjection(str(row[0]), row[1], TaskStatus(row[2]), row[3], row[4].strip(), row[5].strip(), row[6])

    @staticmethod
    def _task_select() -> str:
        return "SELECT t.task_id,t.repository_id,t.state,t.generation,i.intent_digest,t.packet_digest,t.deadline_at FROM factory.tasks t JOIN factory.accepted_intents i ON i.intent_id=t.intent_id"

    def _event(
        self, cursor, task_id: str, actor: Actor, action: str, idempotency_key: str, metadata: dict | None = None
    ) -> None:
        cursor.execute(
            """SELECT t.event_limit,COALESCE(max(e.event_sequence),0)
            FROM factory.tasks t LEFT JOIN factory.task_events e ON e.task_id=t.task_id
            WHERE t.task_id=%s GROUP BY t.event_limit""",
            (task_id,),
        )
        event_limit, previous_sequence = cursor.fetchone()
        if previous_sequence >= event_limit:
            raise BudgetError("event budget exceeded")
        sequence = previous_sequence + 1
        cursor.execute(
            "INSERT INTO factory.task_events(event_id,task_id,event_sequence,idempotency_key,actor_id,action,metadata) VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT(task_id,idempotency_key) DO NOTHING",
            (
                uuid.uuid4(),
                task_id,
                sequence,
                idempotency_key,
                actor.actor_id,
                action,
                json.dumps(metadata or {}, separators=(",", ":")),
            ),
        )

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
                "previous_digest": previous,
                "actor": actor.actor_id,
                "action": action,
                "resource": resource,
                "reason": reason,
                "received_at": received_at,
                "metadata_digest": canonical_digest(bounded),
            }
        )
        cursor.execute(
            "INSERT INTO factory.audit_log(task_id,run_id,previous_digest,current_digest,actor_id,action,resource,reason,correlation_id,metadata,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)",
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
                "INSERT INTO factory.intake_identities(repository_id,source_type,source_id) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                (intake.repository_id, intake.source_type, intake.source_id),
            )
            cursor.execute(
                "SELECT repository_id FROM factory.intake_identities WHERE repository_id=%s AND source_type=%s AND source_id=%s FOR UPDATE",
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
                "SELECT task_id FROM factory.tasks WHERE repository_id=%s AND source_type=%s AND source_id=%s AND state NOT IN ('ready_for_human','dead','cancelled','superseded') FOR UPDATE",
                (intake.repository_id, intake.source_type, intake.source_id),
            )
            old_ids = [str(row[0]) for row in cursor.fetchall()]
            for old_id in old_ids:
                cursor.execute(
                    "UPDATE factory.tasks SET state='superseded',terminal_at=clock_timestamp(),updated_at=clock_timestamp(),current_run_id=NULL,current_fence=NULL WHERE task_id=%s",
                    (old_id,),
                )
                key = canonical_digest({"action": "superseded", "replacement": intake.intent_digest})
                self._event(
                    cursor, old_id, actor, "superseded", key, {"replacement_intent_digest": intake.intent_digest}
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
                """INSERT INTO factory.tasks(task_id,intent_id,repository_id,source_type,source_id,state,generation,packet_digest,deadline_at,cost_limit_micros,token_limit,output_limit_bytes,event_limit,repair_limit)
                VALUES (%s,%s,%s,%s,%s,'queued',%s,%s,now()+(%s * interval '1 second'),%s,%s,%s,%s,%s) RETURNING deadline_at""",
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
                """SELECT previous_digest,current_digest,actor_id,action,resource,reason,created_at,metadata
                FROM factory.audit_log WHERE task_id=%s ORDER BY audit_id LIMIT 100001""",
                (task_id,),
            )
            rows = cursor.fetchall()
            if not rows or len(rows) > 100_000:
                return False
            previous = "0" * 64
            for row in rows:
                recorded_previous, recorded_current, actor, action, resource, reason, received_at, metadata = row
                if recorded_previous.strip() != previous:
                    return False
                expected = canonical_digest(
                    {
                        "previous_digest": previous,
                        "actor": actor,
                        "action": action,
                        "resource": resource,
                        "reason": reason,
                        "received_at": received_at,
                        "metadata_digest": canonical_digest(metadata),
                    }
                )
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

    def claim(self, request, actor: Actor, now: datetime) -> LeaseGrant | None:
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='5s'")
            if self._is_killed(cursor, request.repositories):
                return None
            global_key = f"global:{request.role.value}"
            repo_keys = (
                [f"repository:{repository}:reader" for repository in request.repositories]
                if request.role is RunRole.READER
                else []
            )
            for key in repo_keys:
                cursor.execute(
                    "INSERT INTO factory.capacity_counters(scope_key,ceiling) VALUES (%s,10) ON CONFLICT DO NOTHING",
                    (key,),
                )
            keys = [global_key, *repo_keys]
            cursor.execute(
                "SELECT scope_key,active_count,ceiling FROM factory.capacity_counters WHERE scope_key=ANY(%s) ORDER BY scope_key FOR UPDATE",
                (keys,),
            )
            counters = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
            if counters[global_key][0] >= counters[global_key][1]:
                return None
            eligible_repositories = request.repositories
            if request.role is RunRole.READER:
                eligible_repositories = tuple(
                    repository
                    for repository in request.repositories
                    if counters[f"repository:{repository}:reader"][0] < counters[f"repository:{repository}:reader"][1]
                )
                if not eligible_repositories:
                    return None
            cursor.execute(
                """SELECT t.task_id,t.repository_id,t.packet_digest,t.deadline_at
                FROM factory.tasks t WHERE t.state IN ('queued','retry') AND t.repository_id=ANY(%s)
                AND t.deadline_at>clock_timestamp() AND NOT t.accounting_blocked
                ORDER BY t.created_at,t.task_id FOR UPDATE SKIP LOCKED LIMIT 1""",
                (list(eligible_repositories),),
            )
            row = cursor.fetchone()
            if not row:
                return None
            task_id, repository_id, packet_digest, deadline = row
            repo_key = f"repository:{repository_id}:reader"
            if request.role is RunRole.READER and counters[repo_key][0] >= counters[repo_key][1]:
                return None
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
                return None
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
                "INSERT INTO factory.capacity_allocations(allocation_id,run_id,task_id,repository_id,role) VALUES (%s,%s,%s,%s,%s)",
                (uuid.uuid4(), run_id, task_id, repository_id, request.role.value),
            )
            cursor.execute(
                "UPDATE factory.capacity_counters SET active_count=active_count+1 WHERE scope_key=%s", (global_key,)
            )
            if request.role is RunRole.READER:
                cursor.execute(
                    "UPDATE factory.capacity_counters SET active_count=active_count+1 WHERE scope_key=%s", (repo_key,)
                )
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
            return LeaseGrant(
                str(task_id), str(run_id), request.owner, request.role, fence, expires, packet_digest.strip()
            )

    def _lock_grant(self, cursor, grant: LeaseGrant, *, allow_expired: bool = False):
        expiry_guard = "" if allow_expired else "AND r.lease_expires_at>clock_timestamp()"
        cursor.execute(
            f"""SELECT r.task_id,r.role,a.repository_id,at.attempt_no
            FROM factory.runs r JOIN factory.tasks t ON t.task_id=r.task_id
            JOIN factory.capacity_allocations a ON a.run_id=r.run_id
            JOIN factory.attempts at ON at.run_id=r.run_id
            WHERE r.run_id=%s AND r.task_id=%s AND r.owner_id=%s AND r.fence=%s AND r.packet_digest=%s
            AND r.state='leased' AND r.released_at IS NULL {expiry_guard}
            AND t.current_run_id=r.run_id AND t.current_fence=r.fence AND t.state='leased' AND t.deadline_at>clock_timestamp()
            FOR UPDATE OF r,t,a""",
            (grant.run_id, grant.task_id, grant.owner, grant.fence, grant.packet_digest),
        )
        row = cursor.fetchone()
        if not row:
            raise FenceError("stale or expired fence")
        return row

    def heartbeat(self, grant: LeaseGrant, actor: Actor, now: datetime) -> LeaseGrant:
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            self._lock_grant(cursor, grant)
            cursor.execute(
                "UPDATE factory.runs SET lease_expires_at=LEAST(clock_timestamp()+interval '30 seconds',deadline_at) WHERE run_id=%s RETURNING lease_expires_at",
                (grant.run_id,),
            )
            expires = cursor.fetchone()[0]
            return LeaseGrant(
                grant.task_id, grant.run_id, grant.owner, grant.role, grant.fence, expires, grant.packet_digest
            )

    def _release_locked(
        self, cursor, grant: LeaseGrant, outcome: str | FailureClass, actor: Actor, *, allow_expired: bool = False
    ) -> TaskStatus:
        task_id, role, repository_id, attempt_no = self._lock_grant(cursor, grant, allow_expired=allow_expired)
        if isinstance(outcome, FailureClass):
            decision = classify_retry(outcome, attempt_no=attempt_no)
            target = TaskStatus.RETRY if decision.retry else (decision.terminal or TaskStatus.NEEDS_HUMAN)
            cursor.execute(
                "UPDATE factory.attempts SET failure_class=%s,failure_code=%s,failure_digest=%s,finished_at=clock_timestamp() WHERE run_id=%s",
                (outcome.value, outcome.value, canonical_digest({"failure": outcome.value}), grant.run_id),
            )
        elif outcome == "completed":
            target = TaskStatus.READY_FOR_HUMAN
            cursor.execute("UPDATE factory.attempts SET finished_at=clock_timestamp() WHERE run_id=%s", (grant.run_id,))
        else:
            raise StoreError("unsupported release outcome")
        cursor.execute(
            "UPDATE factory.runs SET state=%s,released_at=clock_timestamp() WHERE run_id=%s",
            ("failed" if isinstance(outcome, FailureClass) else "completed", grant.run_id),
        )
        cursor.execute(
            "UPDATE factory.capacity_allocations SET released_at=clock_timestamp() WHERE run_id=%s AND released_at IS NULL",
            (grant.run_id,),
        )
        cursor.execute(
            "UPDATE factory.capacity_counters SET active_count=active_count-1 WHERE scope_key=%s", (f"global:{role}",)
        )
        if role == "reader":
            cursor.execute(
                "UPDATE factory.capacity_counters SET active_count=active_count-1 WHERE scope_key=%s",
                (f"repository:{repository_id}:reader",),
            )
        terminal = target in {TaskStatus.DEAD, TaskStatus.READY_FOR_HUMAN}
        cursor.execute(
            "UPDATE factory.tasks SET state=%s,current_run_id=NULL,current_fence=NULL,updated_at=clock_timestamp(),terminal_at=CASE WHEN %s THEN clock_timestamp() ELSE terminal_at END WHERE task_id=%s",
            (target.value, terminal, task_id),
        )
        key = canonical_digest(
            {"action": "release", "run_id": grant.run_id, "fence": grant.fence, "target": target.value}
        )
        self._event(cursor, str(task_id), actor, "released", key, {"target": target.value})
        self._audit(
            cursor,
            str(task_id),
            actor,
            "release",
            f"run:{grant.run_id}",
            target.value,
            key,
            {"fence": grant.fence},
            grant.run_id,
        )
        return target

    def release(self, grant: LeaseGrant, outcome: str | FailureClass, actor: Actor, now: datetime) -> TaskStatus:
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            return self._release_locked(cursor, grant, outcome, actor)

    def reserve_budget(
        self, grant: LeaseGrant, cost: int, tokens: int, wall: int, reason_digest: str, key: str, actor: Actor
    ) -> str:
        if (
            any(type(value) is not int or value < 0 for value in (cost, tokens, wall))
            or not HEX64.fullmatch(reason_digest)
            or not HEX64.fullmatch(key)
        ):
            raise BudgetError("invalid budget evidence")
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            self._lock_grant(cursor, grant)
            cursor.execute(
                "SELECT cost_limit_micros,token_limit,cost_reserved_micros,cost_observed_micros,tokens_reserved,tokens_observed,accounting_blocked FROM factory.tasks WHERE task_id=%s FOR UPDATE",
                (grant.task_id,),
            )
            cost_limit, token_limit, reserved_cost, observed_cost, reserved_tokens, observed_tokens, blocked = (
                cursor.fetchone()
            )
            if (
                blocked
                or reserved_cost + observed_cost + cost > cost_limit
                or reserved_tokens + observed_tokens + tokens > token_limit
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
                    "UPDATE factory.tasks SET cost_reserved_micros=cost_reserved_micros+%s,tokens_reserved=tokens_reserved+%s WHERE task_id=%s",
                    (cost, tokens, grant.task_id),
                )
            return str(row[0] if row else reservation_id)

    def observe_usage(
        self,
        grant: LeaseGrant,
        provider_call_id: str,
        price_table_digest: str | None,
        cost: int,
        tokens: int,
        output: int,
        actor: Actor,
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
            self._lock_grant(cursor, grant)
            if not isinstance(price_table_digest, str) or not HEX64.fullmatch(price_table_digest):
                blocked_reason = "missing_price_table"
            else:
                cursor.execute(
                    "SELECT observation_id FROM factory.usage_observations WHERE run_id=%s AND provider_call_id=%s",
                    (grant.run_id, provider_call_id),
                )
                duplicate = cursor.fetchone()
                if duplicate:
                    return UsageResult(str(duplicate[0]), False)
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
                    key,
                    run_id=grant.run_id,
                )
        if blocked_reason:
            raise BudgetError("accounting blocked")
        assert result is not None
        return result

    def set_kill(self, scope: str, enabled: bool, reason: str, key: str, actor: Actor, now: datetime) -> bool:
        if scope != "global" and not scope.startswith("repository:"):
            raise StoreError("invalid kill scope")
        if not HEX64.fullmatch(key) or not reason or len(reason) > 128:
            raise StoreError("invalid kill evidence")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO factory.kill_switches(switch_id,scope_key,enabled,actor_id,reason,idempotency_key) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(idempotency_key) DO NOTHING RETURNING enabled",
                (uuid.uuid4(), scope, enabled, actor.actor_id, reason, key),
            )
            row = cursor.fetchone()
            return bool(row[0]) if row else enabled

    def reconcile(self, actor: Actor, now: datetime, limit: int, cursor_id: str | None) -> ReconcileResult:
        repaired = 0
        last = None
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout='5s'")
            cursor.execute(
                """SELECT r.run_id,r.task_id,r.owner_id,r.role,r.fence,r.lease_expires_at,r.packet_digest
                FROM factory.runs r WHERE r.released_at IS NULL AND r.lease_expires_at<=clock_timestamp()
                AND (%s::uuid IS NULL OR r.task_id>%s::uuid) ORDER BY r.task_id FOR UPDATE SKIP LOCKED LIMIT %s""",
                (cursor_id, cursor_id, limit),
            )
            rows = cursor.fetchall()
            reconciliation_id = uuid.uuid4()
            cursor.execute(
                "INSERT INTO factory.reconciliation_runs(reconciliation_id,cursor_task_id,status,candidates) VALUES (%s,%s,'running',%s)",
                (reconciliation_id, cursor_id, len(rows)),
            )
            for row in rows:
                run_id, task_id, owner, role, fence, expires, packet = row
                cursor.execute(
                    "SELECT repair_count,repair_limit FROM factory.tasks WHERE task_id=%s FOR UPDATE", (task_id,)
                )
                repair_count, repair_limit = cursor.fetchone()
                grant = LeaseGrant(str(task_id), str(run_id), owner, RunRole(role), fence, expires, packet.strip())
                failure = FailureClass.PROVIDER_QUALITY if repair_count >= repair_limit else FailureClass.WORKER_LOST
                self._release_locked(cursor, grant, failure, actor, allow_expired=True)
                cursor.execute("UPDATE factory.runs SET state='expired' WHERE run_id=%s", (run_id,))
                if repair_count < repair_limit:
                    cursor.execute("UPDATE factory.tasks SET repair_count=repair_count+1 WHERE task_id=%s", (task_id,))
                repaired += 1
                last = str(task_id)
            cursor.execute(
                "UPDATE factory.reconciliation_runs SET status='completed',repaired=%s,finished_at=clock_timestamp(),cursor_task_id=%s WHERE reconciliation_id=%s",
                (repaired, last, reconciliation_id),
            )
        return ReconcileResult(len(rows), repaired, last)

    def cancel(self, task_id: str, reason: str, key: str, actor: Actor, now: datetime) -> TaskProjection:
        with self._connect() as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SELECT state FROM factory.tasks WHERE task_id=%s FOR UPDATE", (task_id,))
            row = cursor.fetchone()
            if not row:
                raise KeyError(task_id)
            if row[0] not in {"ready_for_human", "dead", "cancelled", "superseded"}:
                cursor.execute(
                    "UPDATE factory.tasks SET state='cancelled',terminal_at=clock_timestamp(),updated_at=clock_timestamp() WHERE task_id=%s",
                    (task_id,),
                )
                self._event(cursor, task_id, actor, "cancelled", key, {"reason": reason})
                self._audit(cursor, task_id, actor, "cancel", f"task:{task_id}", reason, key)
        return self.get_task(task_id)
