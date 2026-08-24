from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md"
PLAN = ROOT / "docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md"
REPORT = ROOT / "engineering/runbooks/trust-ci-activation-report.md"
COMPOSE = ROOT / "trust-ci/compose.yaml"
API = ROOT / "trust-ci/src/adaptive_trust_ci/api.py"
WORKER = ROOT / "trust-ci/src/adaptive_trust_ci/worker.py"
PEM_MARKERS = ("BEGIN RSA PRIVATE KEY", "BEGIN OPENSSH PRIVATE KEY")


class M0InvariantTests(unittest.TestCase):
    def test_m0_spec_and_plan_exist(self) -> None:
        self.assertTrue(SPEC.is_file(), SPEC.as_posix())
        self.assertTrue(PLAN.is_file(), PLAN.as_posix())
        spec = SPEC.read_text(encoding="utf-8")
        plan = PLAN.read_text(encoding="utf-8")
        self.assertIn("adaptive-trust-ci/verified@", spec)
        self.assertIn("48cb9737fac7f26fb70b425957a3ed64d4c1eb55", spec)
        self.assertIn("M0.0", plan)
        self.assertIn("M0.3", plan)
        self.assertNotIn("BEGIN RSA PRIVATE KEY", spec)
        self.assertNotIn("BEGIN RSA PRIVATE KEY", plan)

    def test_activation_report_operator_safe(self) -> None:
        self.assertTrue(REPORT.is_file(), REPORT.as_posix())
        report = REPORT.read_text(encoding="utf-8")
        spec = SPEC.read_text(encoding="utf-8")
        plan = PLAN.read_text(encoding="utf-8")
        for marker in PEM_MARKERS:
            self.assertNotIn(marker, spec)
            self.assertNotIn(marker, plan)
            self.assertNotIn(marker, report)
        self.assertNotIn("UNKNOWN", report.split("Check Run id", 1)[1].split("|", 2)[1])
        self.assertIn("local HMAC", plan)
        self.assertTrue("no public HTTPS" in plan or "not done" in plan)

    def test_no_github_actions_workflows_tree(self) -> None:
        self.assertFalse((ROOT / ".github" / "workflows").exists())

    def test_api_cannot_hold_github_app_or_client(self) -> None:
        text = API.read_text(encoding="utf-8")
        self.assertNotIn("GitHubClient", text)
        self.assertNotIn("GitHubAppAuth", text)

    def test_worker_uses_github_app_auth(self) -> None:
        text = WORKER.read_text(encoding="utf-8")
        self.assertIn("GitHubAppAuth", text)

    def test_compose_publishes_loopback_not_all_interfaces(self) -> None:
        text = COMPOSE.read_text(encoding="utf-8")
        self.assertIn("name: adaptive-trust-ci", text)
        self.assertIn("127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080", text)
        self.assertNotIn("127.0.0.1:8080:8080", text)
        self.assertNotIn("0.0.0.0:8080", text)
        self.assertIn("http://127.0.0.1:8080/health/ready", text)

    def test_m0_docs_name_claw_not_laptop(self) -> None:
        spec = SPEC.read_text(encoding="utf-8")
        plan = PLAN.read_text(encoding="utf-8")
        self.assertIn("claw", spec)
        self.assertNotIn("laptop", spec)
        self.assertIn("claw", plan)

    def test_holdout_example_forbids_github_actions(self) -> None:
        holdout = (ROOT / "trust-ci/holdout.example/validate.py").read_text(encoding="utf-8")
        self.assertIn("GitHub Actions workflows are forbidden", holdout)
        self.assertIn("webhook API must not hold the GitHub App key", holdout)


if __name__ == "__main__":
    unittest.main()
