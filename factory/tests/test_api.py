from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock
from types import SimpleNamespace
import os

from fastapi.testclient import TestClient

from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.cli import main as cli_main
from adaptive_factory.contracts import TaskIntakeV1
from adaptive_factory.models import (
    Actor,
    FactoryAttemptV1,
    FactoryEventHistoryPageV1,
    FactoryEventV1,
    FactoryRunAttemptV1,
    FactoryRunHistoryPageV1,
    FactoryRunV1,
    RunRole,
    RunStatus,
    TaskProjection,
    TaskStatus,
)
from adaptive_factory.service import (
    FactoryService,
    SnapshotBrokerIntegrityError,
    SnapshotBrokerUnavailable,
)
from adaptive_factory.settings import SettingsError, read_token_file
from adaptive_factory.store import IntegrityError, IntakeResult, StoreError, TransitionError
from factory.tests.test_contracts import valid_intake


class FakeService:
    def __init__(self):
        self.calls = []

    def intake(self, payload, *, actor, now, correlation_id=None):
        intake = TaskIntakeV1.from_dict(payload, now=now)
        self.calls.append(("intake", actor, intake, correlation_id))
        task = TaskProjection(
            "00000000-0000-0000-0000-000000000001",
            intake.repository_id,
            TaskStatus.QUEUED,
            1,
            "a" * 64,
            "b" * 64,
            datetime.now(timezone.utc),
        )
        return IntakeResult(task, True)

    def get_task(self, task_id, *, actor):
        raise KeyError(task_id)

    def list_tasks(self, *, repository_id, limit, cursor, actor):
        return ()

    def list_task_runs(self, task_id, *, limit, cursor, actor):
        now = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
        run = FactoryRunV1(
            "00000000-0000-0000-0000-000000000002",
            task_id,
            "worker-1",
            RunRole.READER,
            "b" * 64,
            1,
            RunStatus.COMPLETED,
            now,
            now,
            now,
            now,
        )
        attempt = FactoryAttemptV1(
            "00000000-0000-0000-0000-000000000003",
            task_id,
            run.run_id,
            1,
            None,
            None,
            None,
            now,
            now,
        )
        self.calls.append(("runs", task_id, limit, cursor, actor.actor_id))
        return FactoryRunHistoryPageV1((FactoryRunAttemptV1(run, attempt),), None)

    def list_task_events(self, task_id, *, limit, cursor, actor):
        now = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
        event = FactoryEventV1(
            "00000000-0000-0000-0000-000000000004",
            task_id,
            1,
            "c" * 64,
            "worker-1",
            "phase_transitioned",
            {
                "from_state": "leased",
                "target": "analyzing",
                "operation": "phase",
                "attempts": 1,
                "infrastructure_retries": 2,
            },
            False,
            now,
        )
        self.calls.append(("events", task_id, limit, cursor, actor.actor_id))
        return FactoryEventHistoryPageV1((event,), None)

    def cancel(
        self,
        task_id,
        *,
        reason,
        idempotency_key,
        actor,
        now,
        correlation_id,
    ):
        raise KeyError(task_id)

    def readiness(self):
        return {"status": "ready", "database_role": "factory_runtime", "schema_version": 8}

    def claim(self, **kwargs):
        self.calls.append(("claim", kwargs))
        return None

    def claim_execution(self, **kwargs):
        self.calls.append(("claim_execution", kwargs))
        return None

    def advance_execution(self, *args, **kwargs):
        self.calls.append(("advance_execution", args, kwargs))
        return kwargs["stage"]

    def commit_execution_proposal(self, *args, **kwargs):
        self.calls.append(("commit_execution_proposal", args, kwargs))
        return self._proposal(args[0], **kwargs)

    def commit_terminal_and_finalize(self, *args, **kwargs):
        self.calls.append(("commit_terminal_and_finalize", args, kwargs))
        proposal = self._proposal(args[0], **kwargs)
        terminal_stage = {
            "run.completed": "completed",
            "run.failed": "failed",
            "run.needs_human": "needs_human",
        }[kwargs["event_type"]]
        m4_status = "ready_for_human" if terminal_stage == "completed" else "needs_human"
        return SimpleNamespace(
            proposal=proposal,
            result={
                "contract_version": 1,
                "task_id": args[0].task_id,
                "run_id": args[0].run_id,
                "task_packet_digest": kwargs["packet_digest"],
                "run_manifest_digest": "1" * 64,
                "exact_head_sha": "2" * 40,
                "workspace_snapshot_digest": "3" * 64,
                "terminal_stage": terminal_stage,
                "terminal_proposal_digest": proposal["idempotency_key"],
                "artifact_manifest_digest": "4" * 64,
                "note_manifest_digest": "5" * 64,
                "usage_evidence_digest": "6" * 64,
                "diagnostics_digest": "7" * 64,
                "m4_status": m4_status,
                "failure_class": (
                    kwargs["payload"].get("failure_class")
                    if kwargs["event_type"] == "run.failed"
                    else None
                ),
                "failure_reason": (
                    kwargs["payload"].get("diagnostic")
                    if kwargs["event_type"] == "run.failed"
                    else kwargs["payload"].get("reason")
                    if kwargs["event_type"] == "run.needs_human"
                    else None
                ),
                "workspace_result_digest": "8" * 64,
            },
        )

    @staticmethod
    def _proposal(grant, **kwargs):
        payload = kwargs["payload"]
        common = {
            "task_id": grant.task_id,
            "run_id": grant.run_id,
            "packet_digest": kwargs["packet_digest"],
            "fence": grant.fence,
            "sequence": kwargs["sequence"],
            "author_role": grant.role.value,
            "idempotency_key": "a" * 64,
        }
        event_type = kwargs["event_type"]
        if event_type == "note.proposed":
            return {**common, **payload}
        if event_type == "artifact.proposed":
            return {**common, **payload, "artifact_attestation_digest": "b" * 64}
        if event_type == "usage.reported":
            return {**common, **payload}
        if event_type == "run.completed":
            return {
                **common,
                "terminal_type": event_type,
                "summary": payload["summary"],
                "failure_class": None,
                "reason": None,
                "diagnostic": None,
            }
        if event_type == "run.failed":
            return {
                **common,
                "terminal_type": event_type,
                "summary": f"{payload['failure_class']}: {payload['diagnostic']}",
                "failure_class": payload["failure_class"],
                "reason": None,
                "diagnostic": payload["diagnostic"],
            }
        return {
            **common,
            "terminal_type": event_type,
            "summary": f"{payload['reason']}: {payload['diagnostic']}",
            "failure_class": None,
            "reason": payload["reason"],
            "diagnostic": payload["diagnostic"],
        }

    def reconcile(self, **kwargs):
        self.calls.append(("reconcile", kwargs))
        return {"candidates": 0, "repaired": 0, "cursor": None}

    def transition_phase(self, grant, *, target, actor, now, idempotency_key, correlation_id):
        self.calls.append(("transition", grant, target, actor, idempotency_key, correlation_id))
        return target

    def set_kill(self, *, scope_key, enabled, reason, idempotency_key, actor, now, correlation_id):
        self.calls.append(
            (
                "kill",
                scope_key,
                enabled,
                reason,
                idempotency_key,
                actor,
                now,
                correlation_id,
            )
        )
        return enabled

    def metrics(self, *, actor=None):
        self.calls.append(("metrics", actor))
        return {
            "factory_intake_and_rejection_outcomes_total": {},
            "factory_lease_reclaim_and_fence_rejection_total": {},
            "factory_capacity_budget_kill_and_reconcile_outcomes_total": {},
        }


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.token = "test-" + "operator-" + "credential"
        actor = Actor(
            "operator",
            "operator",
            frozenset({"task:submit", "task:read", "task:list", "task:cancel"}),
            frozenset({"owner/repository"}),
        )
        self.service = FakeService()
        self.client = TestClient(create_app(self.service, Authenticator({self.token: actor})))
        self.auth = {
            "Authorization": f"Bearer {self.token}",
            "Idempotency-Key": "request-001",
            "X-Correlation-ID": "correlation-001",
        }

    @staticmethod
    def payload():
        payload = valid_intake()
        payload["m0_authority"]["observed_at"] = datetime.now(timezone.utc).isoformat()
        return payload

    @staticmethod
    def execution_claim_payload():
        packet = __import__(
            "factory.tests.test_execution_contracts", fromlist=["valid_packet"]
        ).valid_packet()
        return {
            "role": "writer",
            "repositories": ["owner/repository"],
            "lease_seconds": 60,
            "provider": packet["provider"],
            "capability_policy": packet["capability_policy"],
            "plan": packet["plan"],
            "workspace_handle": packet["workspace_handle"],
            "prompt_template_digest": "7" * 64,
            "role_definition_digest": "8" * 64,
            "tool_policy_digest": "9" * 64,
            "output_schema_digest": "a" * 64,
        }

    def test_mutation_requires_bearer_idempotency_and_correlation(self):
        self.assertEqual(self.client.post("/v1/tasks", json=self.payload()).status_code, 401)
        missing = {"Authorization": f"Bearer {self.token}"}
        self.assertEqual(self.client.post("/v1/tasks", headers=missing, json=self.payload()).status_code, 400)
        response = self.client.post("/v1/tasks", headers=self.auth, json=self.payload())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["X-Correlation-ID"], "correlation-001")
        self.assertEqual(self.service.calls[-1][3], "correlation-001")
        self.assertNotIn(self.token, response.text)

    def test_checked_contract_is_the_only_openapi_surface(self):
        self.assertEqual(self.client.get("/openapi.json").status_code, 404)
        contract = json.loads(
            (Path(__file__).resolve().parents[1] / "contracts/openapi/factory-control.v1.json").read_text(
                encoding="utf-8"
            )
        )
        paths = set(contract["paths"])
        forbidden = {"/v1/providers/run", "/v1/git/push", "/v1/pull-requests", "/v1/deploy", "/v1/systemd", "/v1/shell"}
        self.assertFalse(paths & forbidden)
        self.assertIn("/v1/budget-reservations", paths)
        self.assertIn("/v1/usage-observations", paths)
        self.assertEqual(self.client.get("/health/ready").json()["database_role"], "factory_runtime")

    def test_legacy_request_identity_retains_m4_syntax_only_contract(self):
        identity = "ghp_" + "abcdefghijklmnopqrstuvwxyz1234567890"
        payload = self.payload()
        payload["request_id"] = identity
        response = self.client.post(
            "/v1/tasks",
            headers={
                **self.auth,
                "Idempotency-Key": identity,
                "X-Correlation-ID": identity,
            },
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)

    def test_all_execution_request_identities_reject_secret_shapes_before_service(self):
        token = "execution-identity-credential"
        actor = Actor(
            "worker-01",
            "worker",
            frozenset({"task:execute"}),
            frozenset({"owner/repository"}),
        )
        client = TestClient(create_app(self.service, Authenticator({token: actor})))
        secret_identity = "ghp_" + "abcdefghijklmnopqrstuvwxyz1234567890"
        base_headers = {
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "execution-identity-001",
            "X-Correlation-ID": "execution-correlation-001",
        }
        grant = {
            "task_id": "00000000-0000-0000-0000-000000000001",
            "run_id": "00000000-0000-0000-0000-000000000002",
            "owner": "worker-01",
            "role": "writer",
            "fence": 7,
            "expires_at": "2026-09-02T01:00:00Z",
            "packet_digest": "0" * 64,
        }
        common = {"grant": grant, "packet_digest": "d" * 64, "sequence": 3}
        cases = {
            "claims": self.execution_claim_payload(),
            "stages": {"grant": grant, "packet_digest": "d" * 64, "stage": "running"},
            "notes": {**common, "note_type": "finding", "body": "safe", "evidence": []},
            "artifacts": {
                **common,
                "artifact_class": "patch",
                "path": "factory/change.patch",
                "sha256": "e" * 64,
                "size_bytes": 12,
                "media_type": "text/plain",
            },
            "usage": {
                **common,
                "provider_call_id": "fixture-call",
                "price_table_digest": "f" * 64,
                "input_tokens": 1,
                "output_tokens": 2,
                "reasoning_tokens": 0,
                "cost_usd_micros": 3,
                "output_bytes": 4,
            },
            "terminal": {
                **common,
                "terminal_type": "run.completed",
                "summary": "fixture complete",
            },
        }
        for header_name in ("Idempotency-Key", "X-Correlation-ID"):
            headers = {**base_headers, header_name: secret_identity}
            for endpoint, payload in cases.items():
                with self.subTest(header=header_name, endpoint=endpoint):
                    response = client.post(
                        f"/v1/execution/{endpoint}", headers=headers, json=payload
                    )
                    self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(self.service.calls, [])

    def test_api_has_no_execution_external_write_or_systemd_endpoint(self):
        paths = {
            route.path
            for route in self.client.app.routes
            if isinstance(getattr(route, "path", None), str)
        }
        forbidden = {"/v1/providers/run", "/v1/git/push", "/v1/pull-requests", "/v1/deploy", "/v1/systemd", "/v1/shell"}
        forbidden.add("/v1/execution/workspace-results")
        self.assertFalse(paths & forbidden)
        self.assertIn("/v1/budget-reservations", paths)
        self.assertIn("/v1/usage-observations", paths)
        self.assertIn("/v1/execution/claims", paths)
        self.assertIn("/v1/execution/stages", paths)
        for kind in ("notes", "artifacts", "usage", "terminal"):
            self.assertIn(f"/v1/execution/{kind}", paths)
        for kind in ("claims", "stages", "notes", "artifacts", "usage", "terminal"):
            self.assertIn(f"/v2/execution/{kind}", paths)
        self.assertEqual(self.client.get("/health/ready").json()["database_role"], "factory_runtime")

    def test_declared_errors_are_normalized_correlated_and_preserve_auth_challenge(self):
        unauthorized = self.client.post("/v1/tasks", json=self.payload())
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(unauthorized.headers["WWW-Authenticate"], "Bearer")
        self.assertRegex(unauthorized.headers["X-Correlation-ID"], r"^[0-9a-f-]{36}$")
        self.assertEqual(
            unauthorized.json(),
            {
                "error": "unauthorized",
                "code": "authentication",
                "detail": "bearer authentication required",
            },
        )

        malformed = self.client.post(
            "/v1/tasks",
            headers={
                "Authorization": f"Bearer {self.token}",
                "X-Correlation-ID": "error-correlation",
            },
            json=self.payload(),
        )
        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(malformed.headers["X-Correlation-ID"], "error-correlation")
        self.assertEqual(
            malformed.json(),
            {
                "error": "invalid",
                "code": "invalid_request",
                "detail": "valid Idempotency-Key header required",
            },
        )

    def test_body_limit_applies_only_to_body_bearing_methods(self):
        response = self.client.request(
            "GET",
            "/health/live",
            headers={"Content-Length": "not-a-number"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "live"})
        self.assertRegex(response.headers["X-Correlation-ID"], r"^[0-9a-f-]{36}$")

    def test_optional_read_correlation_is_normalized_at_the_response_boundary(self):
        response = self.client.get(
            "/v1/tasks",
            params={"repository_id": "owner/repository"},
            headers={
                "Authorization": f"Bearer {self.token}",
                "X-Correlation-ID": "not valid whitespace",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"items": []})
        self.assertNotEqual(
            response.headers["X-Correlation-ID"], "not valid whitespace"
        )
        self.assertRegex(response.headers["X-Correlation-ID"], r"^[0-9a-f-]{36}$")

    def test_uuid_inputs_must_use_canonical_lowercase_dashed_spelling(self):
        for value in (
            "00000000000000000000000000000001",
            "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA",
        ):
            with self.subTest(value=value):
                response = self.client.get(
                    f"/v1/tasks/{value}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["code"], "invalid_request")

    def test_text_max_length_counts_unicode_code_points_like_the_contract(self):
        accepted = self.client.post(
            "/v1/tasks/00000000-0000-0000-0000-000000000001/cancel",
            headers=self.auth,
            json={"reason": "é" * 128},
        )
        self.assertEqual(accepted.status_code, 404)
        rejected = self.client.post(
            "/v1/tasks/00000000-0000-0000-0000-000000000001/cancel",
            headers=self.auth,
            json={"reason": "é" * 129},
        )
        self.assertEqual(rejected.status_code, 422)

    def test_repository_kill_scope_requires_a_bounded_repository_identifier(self):
        token = "kill-" + "scope-" + "token"
        actor = Actor(
            "operator",
            "operator",
            frozenset({"factory:kill"}),
            frozenset({"*"}),
        )
        client = TestClient(create_app(self.service, Authenticator({token: actor})))
        headers = {
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "kill-scope-command",
            "X-Correlation-ID": "kill-scope-correlation",
        }
        for scope_key in ("repository:", "repository: ", "repository:not valid"):
            with self.subTest(scope_key=scope_key):
                response = client.post(
                    "/v1/kill-switches",
                    headers=headers,
                    json={"scope_key": scope_key, "enabled": True, "reason": "test"},
                )
                self.assertEqual(response.status_code, 422)

    def test_unexpected_failures_are_redacted_normalized_and_correlated(self):
        marker = "sensitive-internal-marker"
        failing_client = TestClient(self.client.app, raise_server_exceptions=False)
        self.service.readiness = mock.Mock(side_effect=RuntimeError(marker))
        health = failing_client.get(
            "/health/ready", headers={"X-Correlation-ID": "health-failure"}
        )
        self.assertEqual(health.headers.get("content-type"), "application/json")
        self.assertEqual(
            (health.status_code, health.json()),
            (
                500,
                {
                    "error": "unavailable",
                    "code": "internal",
                    "detail": "internal server error",
                },
            ),
        )
        self.assertEqual(health.headers["X-Correlation-ID"], "health-failure")
        self.assertNotIn(marker, health.text)

        self.service.list_tasks = mock.Mock(side_effect=RuntimeError(marker))
        protected = failing_client.get(
            "/v1/tasks",
            params={"repository_id": "owner/repository"},
            headers={
                "Authorization": f"Bearer {self.token}",
                "X-Correlation-ID": "protected-failure",
            },
        )
        self.assertEqual(protected.status_code, 500)
        self.assertEqual(protected.json()["code"], "internal")
        self.assertEqual(protected.headers["X-Correlation-ID"], "protected-failure")
        self.assertNotIn(marker, protected.text)

    def test_bounded_run_attempt_and_event_history_are_exposed(self):
        task_id = "00000000-0000-0000-0000-000000000001"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-Correlation-ID": "history-correlation",
        }
        runs = self.client.get(
            f"/v1/tasks/{task_id}/runs",
            headers=headers,
            params={"limit": 3},
        )
        self.assertEqual(runs.status_code, 200)
        self.assertEqual(runs.headers["X-Correlation-ID"], "history-correlation")
        self.assertEqual(runs.json()["items"][0]["run"]["state"], "completed")
        self.assertEqual(runs.json()["items"][0]["attempt"]["attempt_no"], 1)
        self.assertIsNone(runs.json()["cursor"])

        events = self.client.get(
            f"/v1/tasks/{task_id}/events",
            headers=headers,
            params={"limit": 10, "cursor": 0},
        )
        self.assertEqual(events.status_code, 200)
        self.assertEqual(events.json()["items"][0]["event_sequence"], 1)
        self.assertEqual(events.json()["items"][0]["metadata"]["attempts"], 1)
        self.assertIsNone(events.json()["cursor"])
        self.assertEqual(self.service.calls[-2][0], "runs")
        self.assertEqual(self.service.calls[-1][0], "events")

    def test_history_rejects_unbounded_pages_and_malformed_cursors(self):
        task_id = "00000000-0000-0000-0000-000000000001"
        headers = {"Authorization": f"Bearer {self.token}"}
        cases = (
            (f"/v1/tasks/{task_id}/runs?limit=0", 422),
            (f"/v1/tasks/{task_id}/runs?limit=101", 422),
            (f"/v1/tasks/{task_id}/runs?cursor=not-a-uuid", 422),
            (f"/v1/tasks/{task_id}/events?limit=0", 422),
            (f"/v1/tasks/{task_id}/events?limit=101", 422),
            (f"/v1/tasks/{task_id}/events?cursor=-1", 422),
        )
        for path, expected in cases:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path, headers=headers).status_code, expected)

    def test_phase_transition_endpoint_is_closed_and_uses_release_scope(self):
        token = "phase-" + "worker-" + "token"
        worker = Actor(
            "worker-1",
            "worker",
            frozenset({"task:release"}),
            frozenset({"owner/repository"}),
        )
        client = TestClient(create_app(self.service, Authenticator({token: worker})))
        headers = {
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "phase-command",
            "X-Correlation-ID": "phase-correlation",
        }
        grant = {
            "task_id": "00000000-0000-0000-0000-000000000001",
            "run_id": "00000000-0000-0000-0000-000000000002",
            "owner": "worker-1",
            "role": "reader",
            "fence": 1,
            "expires_at": "2026-09-03T12:00:00Z",
            "packet_digest": "b" * 64,
        }
        response = client.post(
            "/v1/transitions",
            headers=headers,
            json={"grant": grant, "target": "analyzing"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "analyzing"})
        self.assertEqual(response.headers["X-Correlation-ID"], "phase-correlation")
        self.service.transition_phase = mock.Mock(
            side_effect=TransitionError("internal transition policy detail")
        )
        conflict = client.post(
            "/v1/transitions",
            headers={**headers, "Idempotency-Key": "phase-conflict"},
            json={"grant": grant, "target": "implementing"},
        )
        self.assertEqual(
            (conflict.status_code, conflict.json()),
            (
                409,
                {
                    "error": "conflict",
                    "code": "invalid_transition",
                    "detail": "task transition is not allowed",
                },
            ),
        )
        self.assertNotIn("internal transition policy detail", conflict.text)
        for payload in (
            {"grant": grant, "target": "ready_for_human"},
            {"grant": grant, "target": "analyzing", "skip": True},
        ):
            with self.subTest(payload=payload):
                self.assertEqual(
                    client.post("/v1/transitions", headers=headers, json=payload).status_code,
                    422,
                )
    def test_execution_claim_is_explicit_and_rejects_provider_command_fields(self):
        token = "execution-worker-credential"
        actor = Actor("worker-01", "worker", frozenset({"task:execute"}), frozenset({"owner/repository"}))
        client = TestClient(create_app(self.service, Authenticator({token: actor})))
        payload = self.execution_claim_payload()
        headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "execution-001", "X-Correlation-ID": "execution-correlation"}
        self.assertEqual(client.post("/v1/execution/claims", headers=headers, json=payload).status_code, 200)
        payload["provider_command"] = "codex exec"
        self.assertEqual(client.post("/v1/execution/claims", headers=headers, json=payload).status_code, 422)

    def test_execution_proposal_endpoints_are_typed_and_closed(self):
        token = "proposal-worker-credential"
        actor = Actor("worker-01", "worker", frozenset({"task:execute"}), frozenset({"owner/repository"}))
        client = TestClient(create_app(self.service, Authenticator({token: actor})))
        headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "proposal-001", "X-Correlation-ID": "proposal-correlation"}
        grant = {
            "task_id": "00000000-0000-0000-0000-000000000001",
            "run_id": "00000000-0000-0000-0000-000000000002",
            "owner": "worker-01", "role": "writer", "fence": 7,
            "expires_at": "2026-09-02T01:00:00Z", "packet_digest": "0" * 64,
        }
        common = {"grant": grant, "packet_digest": "d" * 64, "sequence": 3}
        cases = {
            "notes": {"note_type": "finding", "body": "safe", "evidence": []},
            "artifacts": {"artifact_class": "patch", "path": "factory/change.patch", "sha256": "e" * 64, "size_bytes": 12, "media_type": "text/plain"},
            "usage": {"provider_call_id": "fixture-call", "price_table_digest": "f" * 64, "input_tokens": 1, "output_tokens": 2, "reasoning_tokens": 0, "cost_usd_micros": 3, "output_bytes": 4},
            "terminal": {"terminal_type": "run.completed", "summary": "fixture complete"},
        }
        contract_root = Path(__file__).resolve().parents[1] / "contracts"
        execution_schemas = json.loads(
            (contract_root / "openapi/factory-execution.v2.json").read_text(
                encoding="utf-8"
            )
        )["components"]["schemas"]
        response_proposals = {
            "notes": "NoteProposal",
            "artifacts": "ArtifactProposal",
            "usage": "UsageProposal",
            "terminal": "TerminalProposal",
        }
        for endpoint, body in cases.items():
            with self.subTest(endpoint=endpoint):
                response = client.post(f"/v2/execution/{endpoint}", headers=headers, json={**common, **body})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(
                set(response.json()["proposal"]),
                set(execution_schemas[response_proposals[endpoint]]["required"]),
            )
            if endpoint == "terminal":
                self.assertEqual(set(response.json()), {"proposal", "result"})
                workspace_result = json.loads(
                    (contract_root / "schemas/workspace-result.v1.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(
                    set(response.json()["result"]),
                    set(workspace_result["required"]),
                )
                self.assertEqual(
                    self.service.calls[-1][0], "commit_terminal_and_finalize"
                )
            else:
                self.assertEqual(set(response.json()), {"proposal"})
        legacy_terminal = client.post(
            "/v1/execution/terminal",
            headers=headers,
            json={**common, **cases["terminal"]},
        )
        self.assertEqual(legacy_terminal.status_code, 200, legacy_terminal.text)
        self.assertEqual(set(legacy_terminal.json()), {"proposal"})
        self.assertEqual(
            self.service.calls[-1][0], "commit_terminal_and_finalize"
        )
        unsafe = {**common, **cases["notes"], "provider_command": "codex exec"}
        self.assertEqual(client.post("/v1/execution/notes", headers=headers, json=unsafe).status_code, 422)
        terminal_snapshot = {
            **common,
            **cases["terminal"],
            "workspace_snapshot": {"source": "worker"},
        }
        calls = len(self.service.calls)
        self.assertEqual(
            client.post(
                "/v1/execution/terminal", headers=headers, json=terminal_snapshot
            ).status_code,
            422,
        )
        self.assertEqual(len(self.service.calls), calls)

    def test_terminal_response_version_uses_matched_route_under_root_path(self):
        token = "execution-root-path-credential"
        actor = Actor(
            "worker-01",
            "worker",
            frozenset({"task:execute"}),
            frozenset({"owner/repository"}),
        )
        client = TestClient(
            create_app(self.service, Authenticator({token: actor})),
            root_path="/gateway",
        )
        grant = {
            "task_id": "00000000-0000-0000-0000-000000000001",
            "run_id": "00000000-0000-0000-0000-000000000002",
            "owner": "worker-01",
            "role": "writer",
            "fence": 7,
            "expires_at": "2026-09-02T01:00:00Z",
            "packet_digest": "0" * 64,
        }
        payload = {
            "grant": grant,
            "packet_digest": "d" * 64,
            "sequence": 3,
            "terminal_type": "run.completed",
            "summary": "fixture complete",
        }
        for path, expected_fields in (
            ("/v1/execution/terminal", {"proposal"}),
            ("/v2/execution/terminal", {"proposal", "result"}),
        ):
            with self.subTest(path=path):
                response = client.post(
                    path,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Idempotency-Key": f"root-path-{path[2]}",
                        "X-Correlation-ID": f"root-path-correlation-{path[2]}",
                    },
                    json=payload,
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(set(response.json()), expected_fields)

    def test_execution_usage_authenticates_exactly_once(self):
        token = "execution-usage-credential"
        actor = Actor(
            "worker-01",
            "worker",
            frozenset({"task:execute"}),
            frozenset({"owner/repository"}),
        )
        authenticator = Authenticator({token: actor})
        client = TestClient(create_app(self.service, authenticator))
        grant = {
            "task_id": "00000000-0000-0000-0000-000000000001",
            "run_id": "00000000-0000-0000-0000-000000000002",
            "owner": "worker-01",
            "role": "writer",
            "fence": 7,
            "expires_at": "2026-09-02T01:00:00Z",
            "packet_digest": "0" * 64,
        }
        payload = {
            "grant": grant,
            "packet_digest": "d" * 64,
            "sequence": 3,
            "provider_call_id": "fixture-call",
            "price_table_digest": "f" * 64,
            "input_tokens": 1,
            "output_tokens": 2,
            "reasoning_tokens": 0,
            "cost_usd_micros": 3,
            "output_bytes": 4,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "execution-usage-001",
            "X-Correlation-ID": "execution-usage-correlation",
        }
        with mock.patch.object(
            authenticator, "authenticate", wraps=authenticator.authenticate
        ) as authenticate:
            response = client.post(
                "/v1/execution/usage", headers=headers, json=payload
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(authenticate.call_count, 1)

    def test_terminal_snapshot_failures_are_server_errors_without_private_detail(self):
        token = "execution-terminal-failure-credential"
        actor = Actor(
            "worker-01",
            "worker",
            frozenset({"task:execute"}),
            frozenset({"owner/repository"}),
        )
        client = TestClient(create_app(self.service, Authenticator({token: actor})))
        headers = {
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "execution-terminal-failure-001",
            "X-Correlation-ID": "execution-terminal-failure-correlation",
        }
        payload = {
            "grant": {
                "task_id": "00000000-0000-0000-0000-000000000001",
                "run_id": "00000000-0000-0000-0000-000000000002",
                "owner": "worker-01",
                "role": "writer",
                "fence": 7,
                "expires_at": "2026-09-02T01:00:00Z",
                "packet_digest": "0" * 64,
            },
            "packet_digest": "d" * 64,
            "sequence": 1,
            "terminal_type": "run.completed",
            "summary": "complete",
        }
        cases = (
            (
                SnapshotBrokerUnavailable("private broker timeout detail"),
                503,
                {"error": "unavailable", "code": "workspace_snapshot"},
            ),
            (
                SnapshotBrokerIntegrityError("private mismatched head detail"),
                500,
                {"error": "internal", "code": "internal_integrity"},
            ),
        )
        for error, status, body in cases:
            with self.subTest(error=type(error).__name__):
                self.service.commit_terminal_and_finalize = mock.Mock(
                    side_effect=error
                )
                response = client.post(
                    "/v1/execution/terminal", headers=headers, json=payload
                )
                self.assertEqual((response.status_code, response.json()), (status, body))
                self.assertNotIn("private", response.text)

    def test_body_over_one_mebibyte_is_rejected_without_parsing(self):
        response = self.client.post(
            "/v1/tasks",
            headers={**self.auth, "Content-Type": "application/json"},
            content=b"{" + b"x" * 1_048_576 + b"}",
        )
        self.assertEqual(response.status_code, 413)

    def test_body_limit_rejects_missing_or_malformed_length(self):
        oversized = b"{" + b"x" * 1_048_576 + b"}"
        response = self.client.post(
            "/v1/tasks",
            headers={**self.auth, "Content-Type": "application/json", "Transfer-Encoding": "chunked"},
            content=oversized,
        )
        self.assertEqual(response.status_code, 413)
        response = self.client.post(
            "/v1/tasks",
            headers={**self.auth, "Content-Type": "application/json", "Content-Length": "not-a-number"},
            content=b"{}",
        )
        self.assertEqual(response.status_code, 400)

    def test_contract_failure_returns_bounded_structured_error(self):
        payload = self.payload()
        payload["shell_command"] = "forbidden"
        response = self.client.post("/v1/tasks", headers=self.auth, json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"], "invalid")
        self.assertNotIn("shell_command", response.text)

    def test_database_contention_returns_stable_bounded_unavailable_error(self):
        from adaptive_factory import store as store_module

        error_type = getattr(store_module, "StoreUnavailable", StoreError)
        self.service.intake = mock.Mock(side_effect=error_type("internal database detail"))
        response = self.client.post("/v1/tasks", headers=self.auth, json=self.payload())
        self.assertEqual(
            (response.status_code, response.json()),
            (
                503,
                {
                    "error": "unavailable",
                    "code": "database",
                    "detail": "database unavailable",
                },
            ),
        )
        self.assertNotIn("internal database detail", response.text)

        contract = json.loads(
            (Path(__file__).resolve().parents[1] / "contracts/openapi/factory-control.v1.json").read_text(
                encoding="utf-8"
            )
        )
        mutation_paths = (
            "/v1/tasks",
            "/v1/tasks/{task_id}/cancel",
            "/v1/claims",
            "/v1/heartbeats",
            "/v1/proposals",
            "/v1/budget-reservations",
            "/v1/usage-observations",
            "/v1/kill-switches",
            "/v1/reconcile",
        )
        for path in mutation_paths:
            with self.subTest(path=path):
                self.assertIn("503", contract["paths"][path]["post"]["responses"])
        for path in ("/health/ready", "/v1/tasks", "/v1/tasks/{task_id}"):
            with self.subTest(path=path):
                self.assertIn("503", contract["paths"][path]["get"]["responses"])
        readiness_unavailable = contract["paths"]["/health/ready"]["get"]["responses"]["503"][
            "description"
        ]
        for required_semantic in (
            "database unavailable or timed out",
            "schema",
            "capacity",
            "accounting",
            "not ready",
        ):
            self.assertIn(required_semantic, readiness_unavailable)

    def test_integrity_error_has_generic_500_without_database_detail(self):
        self.service.intake = mock.Mock(
            side_effect=IntegrityError("database integrity violation: private detail")
        )
        response = self.client.post("/v1/tasks", headers=self.auth, json=self.payload())
        self.assertEqual(
            (response.status_code, response.json()),
            (500, {"error": "internal", "code": "internal_integrity"}),
        )
        self.assertNotIn("private detail", response.text)
        contract = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "contracts/openapi/factory-execution.v1.json"
            ).read_text(encoding="utf-8")
        )
        for path in contract["paths"].values():
            self.assertEqual(
                path["post"]["responses"]["500"]["description"],
                "internal integrity failure",
            )

    def test_metrics_counts_auth_rejections_without_exposing_credentials(self):
        operator_token = "metrics-" + "operator-" + "credential"
        no_scope_token = "metrics-" + "no-scope-" + "credential"
        repository_token = "metrics-" + "repository-" + "credential"
        wrong_kind_token = "metrics-" + "wrong-kind-" + "credential"
        operator = Actor(
            "metrics-operator", "operator", frozenset({"factory:reconcile"}), frozenset({"*"})
        )
        no_scope = Actor("metrics-no-scope", "operator", frozenset(), frozenset({"*"}))
        repository = Actor(
            "metrics-repository", "operator", frozenset({"factory:reconcile"}),
            frozenset({"owner/repository"}),
        )
        wrong_kind = Actor(
            "metrics-wrong-kind", "worker", frozenset({"factory:reconcile"}), frozenset({"*"})
        )
        client = TestClient(
            create_app(
                FactoryService(self.service),
                Authenticator({
                    operator_token: operator,
                    no_scope_token: no_scope,
                    repository_token: repository,
                    wrong_kind_token: wrong_kind,
                }),
            )
        )
        self.assertEqual(client.get("/metrics").status_code, 401)
        self.assertEqual(client.get("/metrics", headers={"Authorization": "Bearer invalid"}).status_code, 401)
        self.assertEqual(
            client.get("/metrics", headers={"Authorization": f"Bearer {no_scope_token}"}).status_code, 403
        )
        self.assertEqual(
            client.get("/metrics", headers={"Authorization": f"Bearer {repository_token}"}).status_code, 403
        )
        self.assertEqual(
            client.get("/metrics", headers={"Authorization": f"Bearer {wrong_kind_token}"}).status_code, 403
        )
        response = client.get("/metrics", headers={"Authorization": f"Bearer {operator_token}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["factory_capacity_budget_kill_and_reconcile_outcomes_total"]["auth_rejected"],
            5,
        )
        for secret in (
            operator_token, no_scope_token, repository_token, wrong_kind_token,
            "metrics-repository", "owner/repository",
        ):
            self.assertNotIn(secret, response.text)
        self.assertLessEqual(len(response.content), 2048)

        fresh = TestClient(create_app(FactoryService(self.service), Authenticator({operator_token: operator})))
        restarted = fresh.get("/metrics", headers={"Authorization": f"Bearer {operator_token}"})
        self.assertEqual(
            restarted.json()["factory_capacity_budget_kill_and_reconcile_outcomes_total"]["auth_rejected"],
            0,
        )

    def test_malformed_closed_commands_return_bounded_4xx(self):
        token = "-".join(("test", "worker", "operator", "credential"))
        actor = Actor(
            "combined-local-test",
            "operator",
            frozenset({"task:claim", "task:cancel", "factory:reconcile"}),
            frozenset({"*"}),
        )
        client = TestClient(create_app(self.service, Authenticator({token: actor})), raise_server_exceptions=False)
        headers = {
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "malformed-command",
            "X-Correlation-ID": "malformed-correlation",
        }
        cases = (
            ("/v1/claims", {"role": "root", "repositories": ["owner/repository"], "lease_seconds": 60}),
            ("/v1/claims", {"role": "reader", "repositories": "owner/repository", "lease_seconds": 60}),
            ("/v1/claims", {"role": "reader", "repositories": ["owner/repository"], "lease_seconds": "60"}),
            ("/v1/reconcile", {"limit": "many"}),
            ("/v1/reconcile", {"cursor": "not-a-uuid"}),
            ("/v1/tasks/not-a-uuid/cancel", {"reason": "operator"}),
            ("/v1/tasks/00000000-0000-0000-0000-000000000001/cancel", {"reason": {"nested": True}}),
            ("/v1/tasks/00000000-0000-0000-0000-000000000001/cancel", {"reason": "x" * 129}),
        )
        for path, payload in cases:
            with self.subTest(path=path, payload=payload):
                response = client.post(path, headers=headers, json=payload)
                self.assertIn(response.status_code, {400, 422})
                self.assertLessEqual(len(response.content), 256)

    def test_token_file_rejects_symlink_and_non_private_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            token_file = root / "token"
            token_file.write_text("secret-token-value\n", encoding="utf-8")
            token_file.chmod(0o644)
            with self.assertRaises(SettingsError):
                read_token_file(token_file)
            token_file.chmod(0o600)
            self.assertEqual(read_token_file(token_file), "secret-token-value")
            link = root / "link"
            link.symlink_to(token_file)
            with self.assertRaises(SettingsError):
                read_token_file(link)

    def test_token_file_requires_absolute_owned_nofollow_ancestry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            private = root / "private"
            private.mkdir(mode=0o700)
            token = private / "token"
            token.write_text("secret-token-value\n", encoding="utf-8")
            token.chmod(0o600)
            with self.assertRaises(SettingsError):
                read_token_file(Path("relative-token"))
            alias = root / "alias"
            alias.symlink_to(private, target_is_directory=True)
            with self.assertRaises(SettingsError):
                read_token_file(alias / "token")
            with mock.patch.object(os, "O_NOFOLLOW", None):
                with self.assertRaises(SettingsError):
                    read_token_file(token)
            with mock.patch("adaptive_factory.settings.os.geteuid", return_value=os.geteuid() + 1):
                with self.assertRaises(SettingsError):
                    read_token_file(token)

    def test_cli_exposes_the_complete_local_control_surface(self):
        output = StringIO()
        with self.assertRaises(SystemExit), redirect_stdout(output):
            cli_main(["--help"])
        for command in (
            "health",
            "intake",
            "show",
            "list",
            "cancel",
            "claim",
            "heartbeat",
            "proposal",
            "reserve-budget",
            "observe-usage",
            "kill",
            "unkill",
            "reconcile",
            "runs",
            "events",
            "transition",
        ):
            self.assertIn(command, output.getvalue())


if __name__ == "__main__":
    unittest.main()
