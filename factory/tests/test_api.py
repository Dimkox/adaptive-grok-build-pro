from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.contracts import TaskIntakeV1
from adaptive_factory.models import Actor, TaskProjection, TaskStatus
from adaptive_factory.settings import SettingsError, read_token_file
from adaptive_factory.store import IntakeResult
from factory.tests.test_contracts import valid_intake


class FakeService:
    def __init__(self): self.calls = []
    def intake(self, payload, *, actor, now):
        intake = TaskIntakeV1.from_dict(payload, now=now)
        self.calls.append(("intake", actor, intake))
        task = TaskProjection("00000000-0000-0000-0000-000000000001", intake.repository_id, TaskStatus.QUEUED, 1, "a" * 64, "b" * 64, datetime.now(timezone.utc))
        return IntakeResult(task, True)

    def get_task(self, task_id, *, actor): raise KeyError(task_id)
    def list_tasks(self, *, repository_id, limit, cursor, actor): return ()
    def cancel(self, task_id, *, reason, idempotency_key, actor, now): raise KeyError(task_id)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.token = "test-operator-token-value"
        actor = Actor("operator", "operator", frozenset({"task:submit", "task:read", "task:list", "task:cancel"}), frozenset({"owner/repository"}))
        self.service = FakeService()
        self.client = TestClient(create_app(self.service, Authenticator({self.token: actor})))
        self.auth = {"Authorization": f"Bearer {self.token}", "Idempotency-Key": "request-001", "X-Correlation-ID": "correlation-001"}

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

    def test_body_over_one_mebibyte_is_rejected_without_parsing(self):
        response = self.client.post("/v1/tasks", headers={**self.auth, "Content-Type": "application/json"}, content=b"{" + b"x" * 1_048_576 + b"}")
        self.assertEqual(response.status_code, 413)

    def test_contract_failure_returns_bounded_structured_error(self):
        payload = self.payload(); payload["shell_command"] = "forbidden"
        response = self.client.post("/v1/tasks", headers=self.auth, json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"], "invalid")
        self.assertNotIn("shell_command", response.text)

    def test_token_file_rejects_symlink_and_non_private_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); token_file = root / "token"; token_file.write_text("secret-token-value\n", encoding="utf-8")
            token_file.chmod(0o644)
            with self.assertRaises(SettingsError): read_token_file(token_file)
            token_file.chmod(0o600)
            self.assertEqual(read_token_file(token_file), "secret-token-value")
            link = root / "link"; link.symlink_to(token_file)
            with self.assertRaises(SettingsError): read_token_file(link)


if __name__ == "__main__":
    unittest.main()
