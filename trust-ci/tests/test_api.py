from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from _support import now, policy_data, sha
from adaptive_trust_ci.api import create_app
from adaptive_trust_ci.models import ApprovalPayload, JobRequest
from adaptive_trust_ci.policy import Policy
from adaptive_trust_ci.settings import ApiSettings, CommonSettings
from adaptive_trust_ci.signing import Signer, TrustStore, sign_approval
from adaptive_trust_ci.store import MemoryStore


class FakeGitHub:
    def __init__(self) -> None:
        self.statuses = []

    def post_status(self, repository, sha_value, **kwargs):
        self.statuses.append((repository, sha_value, kwargs))


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.common = CommonSettings(
            database_url="postgresql://unused",
            policy_path=base / "policy.json",
            github_token="token",
            public_base_url="https://ci.example.com",
            kill_switch_path=base / "STOP",
        )
        self.settings = ApiSettings(
            common=self.common,
            webhook_secret="webhook-secret",
            trust_store_path=base / "trust-store.json",
        )
        self.policy = Policy.from_dict(policy_data())
        self.human = Signer.generate()
        self.trust_store = TrustStore.from_dict(
            {
                "schema_version": 1,
                "keys": [
                    {
                        "key_id": self.human.key_id,
                        "actor": "dmitry",
                        "scopes": ["governance", "database"],
                        "public_key_pem": self.human.public_key_pem().decode(),
                    }
                ],
            }
        )
        self.store = MemoryStore()
        self.github = FakeGitHub()
        self.client = TestClient(
            create_app(
                self.settings,
                store=self.store,
                policy=self.policy,
                trust_store=self.trust_store,
                github=self.github,
            )
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def webhook_body(self, action="opened", *, repository="Dimkox/adaptive-grok-build-pro") -> bytes:
        return json.dumps(
            {
                "action": action,
                "repository": {"full_name": repository},
                "pull_request": {
                    "number": 15,
                    "draft": False,
                    "head": {"sha": sha("b"), "ref": "feat/x"},
                    "base": {"sha": sha("a"), "ref": "main"},
                },
            }
        ).encode()

    def headers(self, body: bytes) -> dict[str, str]:
        signature = hmac.new(self.settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        return {"X-Hub-Signature-256": f"sha256={signature}", "X-GitHub-Event": "pull_request"}

    def test_health_reports_policy_digest(self) -> None:
        response = self.client.get("/health/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["policy_digest"], self.policy.digest)

    def test_signed_webhook_enqueues_and_posts_pending_status(self) -> None:
        body = self.webhook_body()
        response = self.client.post("/webhooks/github", content=body, headers=self.headers(body))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["created"])
        self.assertEqual(self.github.statuses[-1][2]["state"], "pending")

    def test_duplicate_webhook_reuses_idempotent_job(self) -> None:
        body = self.webhook_body()
        first = self.client.post("/webhooks/github", content=body, headers=self.headers(body))
        second = self.client.post("/webhooks/github", content=body, headers=self.headers(body))
        self.assertEqual(first.json()["job_id"], second.json()["job_id"])
        self.assertFalse(second.json()["created"])

    def test_invalid_webhook_signature_is_rejected(self) -> None:
        body = self.webhook_body()
        response = self.client.post(
            "/webhooks/github",
            content=body,
            headers={"X-Hub-Signature-256": "sha256=" + "0" * 64, "X-GitHub-Event": "pull_request"},
        )
        self.assertEqual(response.status_code, 401)

    def test_disallowed_repository_is_rejected(self) -> None:
        body = self.webhook_body(repository="attacker/repo")
        response = self.client.post("/webhooks/github", content=body, headers=self.headers(body))
        self.assertEqual(response.status_code, 403)

    def test_kill_switch_blocks_new_jobs_and_posts_error(self) -> None:
        self.common.kill_switch_path.write_text("stop")
        body = self.webhook_body()
        response = self.client.post("/webhooks/github", content=body, headers=self.headers(body))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.github.statuses[-1][2]["state"], "error")

    def test_closed_pull_request_cancels_active_job(self) -> None:
        opened = self.webhook_body()
        self.client.post("/webhooks/github", content=opened, headers=self.headers(opened))
        closed = self.webhook_body("closed")
        response = self.client.post("/webhooks/github", content=closed, headers=self.headers(closed))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cancelled_jobs"], 1)

    def test_signed_approval_requeues_matching_waiting_job(self) -> None:
        request = JobRequest(
            repository="Dimkox/adaptive-grok-build-pro",
            pr_number=15,
            base_sha=sha("a"),
            head_sha=sha("b"),
            head_ref="feat/x",
            base_ref="main",
        )
        job, _ = self.store.enqueue(request, self.policy.digest, self.policy.max_attempts, now=now())
        claimed = self.store.claim("worker", self.policy.lease_seconds, now=now())
        assert claimed is not None
        self.store.finish(
            job.job_id,
            "worker",
            "needs_approval",
            {"missing_scopes": ["governance"]},
            failure_code="approval-required",
            now=now(),
        )
        payload = ApprovalPayload.new(
            actor="dmitry",
            key_id=self.human.key_id,
            repository=job.repository,
            pr_number=job.pr_number,
            base_sha=job.base_sha,
            head_sha=job.head_sha,
            policy_digest=job.policy_digest,
            scope="governance",
            reason="reviewed exact SHA",
            now=now(),
        )
        response = self.client.post("/approvals", json=sign_approval(payload, self.human).to_dict())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["requeued_jobs"], 1)
        self.assertEqual(self.store.get_job(job.job_id).status, "queued")

    def test_tampered_approval_is_rejected(self) -> None:
        request = JobRequest(
            repository="Dimkox/adaptive-grok-build-pro",
            pr_number=15,
            base_sha=sha("a"),
            head_sha=sha("b"),
            head_ref="feat/x",
            base_ref="main",
        )
        job, _ = self.store.enqueue(request, self.policy.digest, self.policy.max_attempts, now=now())
        payload = ApprovalPayload.new(
            actor="dmitry",
            key_id=self.human.key_id,
            repository=job.repository,
            pr_number=job.pr_number,
            base_sha=job.base_sha,
            head_sha=job.head_sha,
            policy_digest=job.policy_digest,
            scope="governance",
            reason="reviewed",
            now=now(),
        )
        envelope = sign_approval(payload, self.human).to_dict()
        envelope["payload"]["reason"] = "tampered"
        response = self.client.post("/approvals", json=envelope)
        self.assertEqual(response.status_code, 403)

    def test_public_job_endpoint_does_not_return_command_output(self) -> None:
        request = JobRequest(
            repository="Dimkox/adaptive-grok-build-pro",
            pr_number=15,
            base_sha=sha("a"),
            head_sha=sha("b"),
            head_ref="feat/x",
            base_ref="main",
        )
        job, _ = self.store.enqueue(request, self.policy.digest, self.policy.max_attempts, now=now())
        claimed = self.store.claim("worker", self.policy.lease_seconds, now=now())
        assert claimed is not None
        self.store.finish(
            job.job_id,
            "worker",
            "failed",
            {"commands": [{"name": "unit", "status": "fail", "stdout_tail": "secret output"}]},
            now=now(),
        )
        response = self.client.get(f"/jobs/{job.job_id}")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("stdout_tail", response.text)
        self.assertNotIn("secret output", response.text)


if __name__ == "__main__":
    unittest.main()
