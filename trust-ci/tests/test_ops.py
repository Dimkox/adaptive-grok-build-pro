from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _support import policy_data
from adaptive_trust_ci.github import branch_protection_payload
from adaptive_trust_ci.policy import Policy
from adaptive_trust_ci.sandbox import ContainerExecutor


ROOT = Path(__file__).resolve().parents[2]


class OperationsTests(unittest.TestCase):
    def test_sandbox_has_no_network_caps_or_writable_git_metadata(self) -> None:
        policy = Policy.from_dict(policy_data())
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / ".git").mkdir()
            argv = ContainerExecutor(policy.sandbox).build_argv(
                workspace=workspace,
                command=("python3", "-m", "unittest"),
                env={"CI": "true", "TRUST_CI_HEAD_SHA": "b" * 40},
                container_name="trust-ci-test",
            )
        joined = " ".join(argv)
        self.assertIn("--network none", joined)
        self.assertIn("--cap-drop ALL", joined)
        self.assertIn("no-new-privileges", joined)
        self.assertIn("--read-only", joined)
        self.assertIn("/workspace/.git:ro", joined)
        self.assertNotIn("GITHUB_TOKEN", joined)
        self.assertNotIn("TRUST_CI_GITHUB_TOKEN", joined)

    def test_postgres_schema_has_durable_lease_and_replay_constraints(self) -> None:
        sql = (ROOT / "trust-ci/sql/001_schema.sql").read_text(encoding="utf-8")
        self.assertIn("FOR UPDATE SKIP LOCKED", sql)
        self.assertIn("idempotency_key char(64) NOT NULL UNIQUE", sql)
        self.assertIn("nonce text NOT NULL UNIQUE", sql)
        self.assertIn("lease_expires_at", sql)
        self.assertIn("attempts-exhausted-after-worker-loss", sql)

    def test_packaged_schema_matches_deployment_schema(self) -> None:
        deployment = (ROOT / "trust-ci/sql/001_schema.sql").read_bytes()
        packaged = (ROOT / "trust-ci/src/adaptive_trust_ci/resources/001_schema.sql").read_bytes()
        self.assertEqual(deployment, packaged)

    def test_api_and_worker_images_are_separate(self) -> None:
        api = (ROOT / "trust-ci/Dockerfile.api").read_text(encoding="utf-8")
        worker = (ROOT / "trust-ci/Dockerfile.worker").read_text(encoding="utf-8")
        compose = (ROOT / "trust-ci/compose.yaml").read_text(encoding="utf-8")
        self.assertNotIn("docker.io", api)
        self.assertIn("docker.io", worker)
        self.assertNotIn("trust-ci-signing-key.pem:/run/secrets", compose.split("  worker:", 1)[0])
        self.assertIn("trust-ci-signing-key.pem:/run/secrets", compose.split("  worker:", 1)[1])
        self.assertNotIn("docker.sock", compose.split("  worker:", 1)[0])

    def test_branch_protection_is_actions_independent(self) -> None:
        payload = branch_protection_payload("adaptive-trust-ci/verified")
        self.assertEqual(payload["required_status_checks"]["contexts"], ["adaptive-trust-ci/verified"])
        self.assertNotIn("actions", str(payload).lower())

    def test_repository_contains_no_github_actions_workflow(self) -> None:
        workflows = ROOT / ".github" / "workflows"
        self.assertFalse(workflows.exists(), "GitHub Actions are forbidden for this project")


if __name__ == "__main__":
    unittest.main()
