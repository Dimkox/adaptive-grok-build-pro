from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md"
PLAN = ROOT / "docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md"
REPORT = ROOT / "engineering/runbooks/trust-ci-activation-report.md"
README = ROOT / "README.md"
DECISIONS = ROOT / "decisions.md"
MISTAKES = ROOT / "mistakes.md"
COMPOSE = ROOT / "trust-ci/compose.yaml"
API = ROOT / "trust-ci/src/adaptive_trust_ci/api.py"
WORKER = ROOT / "trust-ci/src/adaptive_trust_ci/worker.py"
PEM_MARKERS = ("BEGIN RSA PRIVATE KEY", "BEGIN OPENSSH PRIVATE KEY")
CHATGPT_WEBHOOK_URL = "https://trust-ci.ii-tonya.ru/webhooks/github"
CHATGPT_WEBHOOK_HOST = "trust-ci.ii-tonya.ru"
FUNNEL_WEBHOOK_URL = "https://claw.taild9f611.ts.net/webhooks/github"


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
        backup_cell = report.split("Backup/restore/restart drill", 1)[1].split("|", 2)[1]
        if "2026-" in backup_cell and "pass" in backup_cell:
            self.assertIn("2026-", backup_cell)
            self.assertIn("pass", backup_cell)

    def test_operator_docs_do_not_present_chatgpt_webhook_as_live(self) -> None:
        operator_docs = (SPEC, PLAN, REPORT, README, DECISIONS)
        for path in operator_docs:
            self.assertTrue(path.is_file(), path.as_posix())
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(CHATGPT_WEBHOOK_URL, text, path.as_posix())
            self.assertNotIn(CHATGPT_WEBHOOK_HOST, text, path.as_posix())
            self.assertNotIn("ii-tonya", text, path.as_posix())

    def test_decisions_name_github_app_as_the_application(self) -> None:
        text = DECISIONS.read_text(encoding="utf-8")
        self.assertIn("https://github.com/apps/adaptive-trust-ci", text)

    def test_operator_docs_name_funnel_app_webhook_url(self) -> None:
        for path in (PLAN, REPORT, DECISIONS):
            text = path.read_text(encoding="utf-8")
            self.assertIn(FUNNEL_WEBHOOK_URL, text, path.as_posix())

    def test_m0_2_webhook_stage_closed_on_github_delivery(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        report = REPORT.read_text(encoding="utf-8")
        self.assertIn("- [x] Register GitHub App webhook", plan)
        self.assertIn("pull_request", plan)
        self.assertIn("9d56734d9050fb3cb2543565084bcb83ded5c73b", plan)
        self.assertIn("97524725228", plan)
        self.assertIn("GitHub webhook", plan)
        self.assertIn("9d56734d9050fb3cb2543565084bcb83ded5c73b", report)
        self.assertIn("97524725228", report)
        self.assertIn("0e147461-6de8-415f-b712-d06b2034c735", report)
        self.assertIn("pull_request", report)
        self.assertIn("not done", plan)
        self.assertIn("**Do not protect `main`**", plan)
        self.assertIn("M0.3 bind follows", plan)

    def test_mistakes_do_not_call_nginx_the_application(self) -> None:
        text = MISTAKES.read_text(encoding="utf-8")
        self.assertNotIn("nginx for the existing app", text)

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

    def test_m0_3_main_is_app_bound(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        report = REPORT.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")
        decisions = DECISIONS.read_text(encoding="utf-8")
        self.assertIn("- [x] Temporary human admin token", plan)
        self.assertIn("- [x] Prove same text from another actor fails", plan)
        self.assertIn("- [x] Disable leftover Actions workflow `340420982`", plan)
        self.assertIn("- [x] Supersede bootstrap-exception language", plan)
        self.assertIn("- [x] Fill activation report with IDs and digests; no secrets", plan)
        self.assertIn("- [ ] Mark PR ready; merge only through the live App-owned check", plan)
        self.assertNotIn("- [x] Mark PR ready; merge", plan)
        self.assertIn("| `main` protected | true |", report)
        self.assertIn("| Protection `app_id` | 4694114 |", report)
        self.assertIn("340420982", report)
        self.assertIn("disabled_manually", report)
        self.assertNotIn(
            "The App-owned check is not live in this release; merge of PR #2 is a bootstrap exception",
            readme,
        )
        self.assertIn("2026-08-24 — M0.3 bind main", decisions)
        self.assertIn("4694114", decisions.split("M0.3 bind main", 1)[1][:800])
        self.assertIn("adaptive-trust-ci/verified@6737355947c2", decisions.split("M0.3 bind main", 1)[1][:800])
        self.assertIn("revoke", decisions.split("M0.3 bind main", 1)[1][:800].lower())
        current_state = readme.split("## Current state", 1)[1].split("## Read first", 1)[0].lower()
        self.assertNotIn("main is unprotected", current_state)
        self.assertNotIn("main is still unprotected", report.lower().split("| field |", 1)[0])


if __name__ == "__main__":
    unittest.main()
