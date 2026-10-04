from __future__ import annotations

import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit

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


def _unique_match(text: str, pattern: str, role: str) -> str:
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise AssertionError(f"Expected one {role} declaration, found {len(matches)}")
    return matches[0].group(1)


def _section(text: str, heading: str) -> str:
    matches = list(re.finditer(rf"(?m)^## {heading}\n", text))
    if len(matches) != 1:
        raise AssertionError(f"Expected one section for {heading}, found {len(matches)}")
    rest = text[matches[0].end():]
    end = re.search(r"(?m)^## ", rest)
    return rest[:end.start()] if end else rest


def _activation_cell(report: str, field: str) -> str:
    table = _unique_match(
        report, r"(?m)^\| Field \| Value \|\n\| --- \| --- \|\n((?:\|[^\n]*\|(?:\n|$))+)",
        "activation field table",
    )
    return _unique_match(table, rf"(?m)^\| {re.escape(field)} \| ([^|\n]*) \|$", field)


def _hostname(value: str) -> bool:
    label = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    return (
        len(value) <= 253 and value.lower() != "unknown"
        and re.fullmatch(rf"{label}(?:\.{label})*", value) is not None
        and re.search(r"[A-Za-z]", value) is not None
    )


def _consistent(values: tuple[str, ...], role: str) -> str:
    if len(set(values)) != 1:
        raise AssertionError(f"Inconsistent {role} declarations")
    return values[0]


def _m0_document_bindings(spec: str, plan: str, report: str, decisions: str) -> tuple[str, str, str]:
    """Check public/historical document relationships, never deployed identity or authority."""
    host_spec = _section(spec, "Host")
    listener = _section(plan, "M0\\.1 — Dedicated-host listener")
    intake = _section(plan, "M0\\.2 — Live authority proof \\(closed 2026-08-24\\)")
    protection = _section(plan, "M0\\.3 — Bind `main`")
    host_decision = _section(decisions, "2026-08-24 — M0 CI host is [^\\n]+, not a laptop")
    webhook_decision = _section(decisions, "2026-08-24 — GitHub App pull_request webhook is live")
    app_decision = _section(decisions, "2026-08-24 — «Приложуха» is GitHub App adaptive-trust-ci")
    bind_decision = _section(decisions, "2026-08-24 — M0\\.3 bind main; revoke bootstrap exceptions")
    host = _consistent((
        _unique_match(host_spec, r"\*\*Host is `([^`\n]+)`\*\*", "spec dedicated host"),
        _unique_match(listener, r"The named host \*\*is `([^`\n]+)`\*\*", "plan dedicated host"),
        _unique_match(_activation_cell(report, "Dedicated CI host (hostname only)"), r"^`([^`\n]+)`$", "report host"),
        _unique_match(host_decision, r"The M0 Trust CI host is hostname `([^`\n]+)`", "dated dedicated host"),
        _unique_match(decisions, r"(?m)^## 2026-08-24 — M0 CI host is ([^\n]+), not a laptop$", "dated host heading"),
    ), "dedicated host")
    if host != "<ci-host>" and not _hostname(host):
        raise AssertionError("Invalid dedicated hostname or public host placeholder")
    webhook = _consistent((
        _unique_match(intake, r"(?m)^- \[x\] Register GitHub App webhook `POST ([^`\n]+)`", "registered App webhook"),
        _unique_match(
            _activation_cell(report, "GitHub App webhook URL (inbound)"),
            r"^`([^`\n]+)`(?: \(GitHub `pull_request`/`synchronize` 200\))?$", "report inbound webhook",
        ),
        _unique_match(webhook_decision, r"GitHub POSTed `pull_request`/`synchronize` to `([^`\n]+)`", "dated GitHub intake"),
        _unique_match(app_decision, r"live intake is Funnel `([^`\n]+)`", "dated App Funnel intake"),
    ), "App Funnel webhook")
    if webhook != "https://<redacted-tailnet-host>/webhooks/github":
        try:
            parsed = urlsplit(webhook)
        except ValueError as error:
            raise AssertionError("Malformed Funnel webhook URL") from error
        if (
            parsed.scheme != "https" or not _hostname(parsed.netloc)
            or not parsed.netloc.lower().endswith(".ts.net")
            or webhook != f"https://{parsed.netloc}/webhooks/github"
        ):
            raise AssertionError("Expected an HTTPS Funnel hostname and exact inbound webhook path")
    app_id = _consistent((
        _unique_match(listener, r"Gitignored worker App ID `([^`\n]+)`", "worker App ID"),
        _unique_match(intake, r"Check Run `[0-9]+` App `([^`\n]+)`", "webhook Check Run App ID"),
        _unique_match(protection, r"`app_id` \*\*([^*\n]+)\*\*", "plan protection App ID"),
        _unique_match(protection, r"`app\.id=([^`\n]+)`", "plan Check Run App ID"),
        _activation_cell(report, "App ID"),
        _activation_cell(report, "Protection `app_id`"),
        _unique_match(bind_decision, r"bound to GitHub App ID `([^`\n]+)` on protected `main`", "dated main App binding"),
    ), "GitHub App ID")
    if app_id != "<redacted-app-id>" and re.fullmatch(r"[1-9][0-9]{0,18}", app_id) is None:
        raise AssertionError("Invalid GitHub App ID or public App placeholder")
    return host, webhook, app_id


class OperatorDocumentBindingTests(unittest.TestCase):
    @staticmethod
    def documents(
        host: str = "ci.example.test",
        webhook: str = "https://ci.example.ts.net/webhooks/github",
        app_id: str = "123456",
    ) -> dict[str, str]:
        return {
            "spec": f"## Host\n\n**Host is `{host}`**.\n\n## Unrelated\n",
            "plan": (
                "## M0.1 — Dedicated-host listener\n\n"
                f"The named host **is `{host}`**. Gitignored worker App ID `{app_id}` "
                "and installation ID `654321` are set.\n\n"
                "## M0.2 — Live authority proof (closed 2026-08-24)\n\n"
                f"- [x] Register GitHub App webhook `POST {webhook}` — Funnel + HMAC.\n"
                f"- [x] Disposable docs PR; Check Run `12345678` App `{app_id}`. Earlier local HMAC.\n\n"
                "## M0.3 — Bind `main`\n\n"
                f"GET `branches/main/protection` required check `adaptive-trust-ci/verified@6737355947c2` "
                f"`app_id` **{app_id}**; App Check Run `app.id={app_id}`.\n"
            ),
            "report": (
                "| Field | Value |\n| --- | --- |\n"
                f"| Dedicated CI host (hostname only) | `{host}` |\n"
                f"| GitHub App webhook URL (inbound) | `{webhook}` "
                "(GitHub `pull_request`/`synchronize` 200) |\n"
                f"| App ID | {app_id} |\n| Protection `app_id` | {app_id} |\n"
            ),
            "decisions": (
                f"## 2026-08-24 — M0 CI host is {host}, not a laptop\n\n"
                f"The M0 Trust CI host is hostname `{host}`.\n\n"
                "## 2026-08-24 — GitHub App pull_request webhook is live\n\n"
                f"GitHub POSTed `pull_request`/`synchronize` to `{webhook}` (HTTP 200).\n\n"
                "## 2026-08-24 — «Приложуха» is GitHub App adaptive-trust-ci\n\n"
                f"Webhook configuration lives on that App registration; live intake is Funnel `{webhook}`.\n\n"
                "## 2026-08-24 — M0.3 bind main; revoke bootstrap exceptions\n\n"
                f"Live App-owned check is bound to GitHub App ID `{app_id}` on protected `main`.\n"
            ),
        }

    def test_accepts_consistent_synthetic_concrete_bindings(self) -> None:
        self.assertEqual(
            _m0_document_bindings(**self.documents()),
            ("ci.example.test", "https://ci.example.ts.net/webhooks/github", "123456"),
        )

    def test_accepts_only_the_role_specific_public_placeholders(self) -> None:
        self.assertEqual(
            _m0_document_bindings(**self.documents(
                "<ci-host>", "https://<redacted-tailnet-host>/webhooks/github", "<redacted-app-id>",
            )),
            ("<ci-host>", "https://<redacted-tailnet-host>/webhooks/github", "<redacted-app-id>"),
        )

    def test_rejects_invalid_host_webhook_and_app_identity_syntax(self) -> None:
        invalid = {
            "host": ("UNKNOWN", "", "<redacted-tailnet-host>", "https://ci.example.test", "bad_host", "127.0.0.1"),
            "webhook": (
                "UNKNOWN", "", "https://<ci-host>/webhooks/github", "http://ci.example.ts.net/webhooks/github",
                "https://ci.example.test/webhooks/github", "https://evilts.net/webhooks/github",
                "https://ci.example.ts.net.evil.test/webhooks/github", "https://user@ci.example.ts.net/webhooks/github",
                "https://ci.example.ts.net:443/webhooks/github", "https://ci.example.ts.net/approvals",
                "https://ci.example.ts.net/webhooks/github?x=1", "https://ci.example.ts.net/webhooks/github#fragment",
                "https://<redacted-tailnet-host>/webhooks/github?x=1",
            ),
            "app_id": ("UNKNOWN", "", "<redacted-installation-id>", "0", "-1", "12x", "12345678901234567890"),
        }
        for field, values in invalid.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(AssertionError):
                    _m0_document_bindings(**self.documents(**{field: value}))

    def test_rejects_missing_duplicate_and_decoy_report_fields(self) -> None:
        for field in ("Dedicated CI host (hostname only)", "GitHub App webhook URL (inbound)", "App ID", "Protection `app_id`"):
            docs = self.documents()
            row = next(line for line in docs["report"].splitlines() if line.startswith(f"| {field} |"))
            for replacement in ("", row + "\n" + row, row.replace(field, "Unrelated example")):
                with self.subTest(field=field, replacement=replacement), self.assertRaises(AssertionError):
                    _m0_document_bindings(**dict(docs, report=docs["report"].replace(row, replacement)))

    def test_rejects_mismatched_declarations_in_every_document(self) -> None:
        docs = self.documents()
        for document, before, after in (
            ("spec", "ci.example.test", "other.example.test"),
            ("plan", "ci.example.test", "other.example.test"),
            ("decisions", "hostname `ci.example.test`", "hostname `other.example.test`"),
            ("report", "https://ci.example.ts.net", "https://other.example.ts.net"),
            ("decisions", "https://ci.example.ts.net", "https://other.example.ts.net"),
            ("plan", "App ID `123456`", "App ID `123457`"),
            ("plan", "App `123456`", "App `123457`"),
            ("plan", "`app_id` **123456**", "`app_id` **123457**"),
            ("plan", "app.id=123456", "app.id=123457"),
            ("report", "Protection `app_id` | 123456", "Protection `app_id` | 123457"),
            ("decisions", "App ID `123456`", "App ID `123457`"),
        ):
            with self.subTest(document=document, before=before), self.assertRaises(AssertionError):
                _m0_document_bindings(**dict(docs, **{document: docs[document].replace(before, after)}))

    def test_rejects_missing_duplicate_and_wrong_section_role_declarations(self) -> None:
        docs = self.documents()
        for document, role in (
            ("spec", "**Host is `ci.example.test`**."),
            ("plan", "- [x] Register GitHub App webhook `POST https://ci.example.ts.net/webhooks/github` — Funnel + HMAC."),
            ("decisions", "Live App-owned check is bound to GitHub App ID `123456` on protected `main`."),
        ):
            for replacement in ("", role + "\n" + role, "decoy"):
                changed = docs[document].replace(role, replacement)
                if replacement == "decoy":
                    changed += "\n## Unrelated example\n\n" + role
                with self.subTest(document=document, replacement=replacement), self.assertRaises(AssertionError):
                    _m0_document_bindings(**dict(docs, **{document: changed}))
        for document, heading in (("spec", "## Host"), ("plan", "## M0.1 — Dedicated-host listener")):
            with self.subTest(document=document, heading=heading), self.assertRaises(AssertionError):
                _m0_document_bindings(**dict(docs, **{document: docs[document] + "\n" + heading + "\n"}))


class M0InvariantTests(unittest.TestCase):
    @staticmethod
    def operator_document_bindings() -> tuple[str, str, str]:
        return _m0_document_bindings(*(path.read_text(encoding="utf-8") for path in (SPEC, PLAN, REPORT, DECISIONS)))

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
        self.operator_document_bindings()

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

    def test_m0_docs_bind_the_dedicated_ci_host(self) -> None:
        spec = SPEC.read_text(encoding="utf-8")
        self.operator_document_bindings()
        self.assertNotIn("laptop", spec)

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
        self.operator_document_bindings()
        self.assertIn("340420982", report)
        self.assertIn("disabled_manually", report)
        self.assertNotIn(
            "The App-owned check is not live in this release; merge of PR #2 is a bootstrap exception",
            readme,
        )
        self.assertIn("2026-08-24 — M0.3 bind main", decisions)
        self.assertIn("adaptive-trust-ci/verified@6737355947c2", decisions.split("M0.3 bind main", 1)[1][:800])
        self.assertIn("revoke", decisions.split("M0.3 bind main", 1)[1][:800].lower())
        current_state = readme.split("## Current state", 1)[1].split("## Read first", 1)[0].lower()
        self.assertNotIn("main is unprotected", current_state)
        self.assertNotIn("main is still unprotected", report.lower().split("| field |", 1)[0])


if __name__ == "__main__":
    unittest.main()
