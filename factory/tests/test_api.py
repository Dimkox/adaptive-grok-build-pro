from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock
import os

from fastapi.testclient import TestClient

from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.cli import main as cli_main
from adaptive_factory.contracts import TaskIntakeV1
from adaptive_factory.models import Actor, TaskProjection, TaskStatus
from adaptive_factory.service import FactoryService
from adaptive_factory.settings import SettingsError, read_token_file
from adaptive_factory.store import IntakeResult
from factory.tests.test_contracts import valid_intake


class FakeService:
    def __init__(self):
        self.calls = []

    def intake(self, payload, *, actor, now):
        intake = TaskIntakeV1.from_dict(payload, now=now)
        self.calls.append(("intake", actor, intake))
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

    def cancel(self, task_id, *, reason, idempotency_key, actor, now):
        raise KeyError(task_id)

    def readiness(self):
        return {"status": "ready", "database_role": "factory_runtime", "schema_version": 8}

    def claim(self, **kwargs):
        self.calls.append(("claim", kwargs))
        return None

    def reconcile(self, **kwargs):
        self.calls.append(("reconcile", kwargs))
        return {"candidates": 0, "repaired": 0, "cursor": None}

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

    def test_mutation_requires_bearer_idempotency_and_correlation(self):
        self.assertEqual(self.client.post("/v1/tasks", json=self.payload()).status_code, 401)
        missing = {"Authorization": f"Bearer {self.token}"}
        self.assertEqual(self.client.post("/v1/tasks", headers=missing, json=self.payload()).status_code, 400)
        response = self.client.post("/v1/tasks", headers=self.auth, json=self.payload())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["X-Correlation-ID"], "correlation-001")
        self.assertNotIn(self.token, response.text)

    def test_api_has_no_execution_external_write_or_systemd_endpoint(self):
        paths = set(self.client.get("/openapi.json").json()["paths"])
        forbidden = {"/v1/providers/run", "/v1/git/push", "/v1/pull-requests", "/v1/deploy", "/v1/systemd", "/v1/shell"}
        self.assertFalse(paths & forbidden)
        self.assertIn("/v1/budget-reservations", paths)
        self.assertIn("/v1/usage-observations", paths)
        self.assertEqual(self.client.get("/health/ready").json()["database_role"], "factory_runtime")

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
        ):
            self.assertIn(command, output.getvalue())


if __name__ == "__main__":
    unittest.main()
