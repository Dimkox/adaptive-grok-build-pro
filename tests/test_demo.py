from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

from adaptive_grok.architecture import (  # noqa: E402
    architecture_digests,
    contract_inventory,
    load_architecture,
)
from adaptive_grok.governance import governance_summary, load_governance  # noqa: E402
from adaptive_grok.router import build_route  # noqa: E402
from adaptive_grok.spec import (  # noqa: E402
    canonical_spec_digest,
    criterion_coverage,
    generate_spec,
    load_spec,
)


NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)


def _demo_module():
    try:
        return importlib.import_module("adaptive_grok.demo")
    except ModuleNotFoundError:
        return None


class DemoServiceTests(unittest.TestCase):
    def test_sample_snapshot_uses_real_repository_engines_with_provenance(self) -> None:
        demo = _demo_module()
        self.assertIsNotNone(demo, "adaptive_grok.demo must provide the demo service")

        snapshot = demo.build_sample_snapshot(ROOT, now=NOW, request_id="req-sample")
        fixtures = demo.load_demo_fixtures(ROOT)
        direct_route = build_route(ROOT, fixtures["task"]["primary_prompt"], "demo-sample").to_dict()
        direct_spec = load_spec(ROOT / ".grok-stack/demo/sample/change-spec.json", allow_legacy=False)
        architecture = load_architecture(ROOT)
        governance = governance_summary(load_governance(ROOT), now=NOW)

        self.assertEqual(snapshot["schema_version"], 1)
        self.assertEqual(snapshot["request_id"], "req-sample")
        self.assertEqual(snapshot["generated_at"], "2026-08-30T12:00:00Z")
        self.assertEqual(snapshot["mode"], "bundled_sample")
        self.assertFalse(snapshot["external_writes"])
        for key in ("intent", "risk", "complexity", "domains", "workflow_skills", "write_agent"):
            self.assertEqual(snapshot["route"][key], direct_route[key])
        self.assertEqual(snapshot["route"]["source"], "computed_preview")
        self.assertEqual(snapshot["spec"]["digest"], canonical_spec_digest(direct_spec))
        self.assertEqual(
            snapshot["spec"]["criterion_mapped"],
            criterion_coverage(direct_spec)["criterion_mapped"],
        )
        self.assertEqual(
            snapshot["architecture"]["digest"],
            architecture_digests(architecture)["architecture_digest"],
        )
        self.assertEqual(
            snapshot["architecture"]["contract_count"],
            len(contract_inventory(ROOT, architecture)),
        )
        self.assertEqual(snapshot["governance"]["digest"], governance["governance_digest"])
        self.assertEqual(snapshot["verification"]["source"], "bundled_sample")
        self.assertEqual(snapshot["verification"]["status"], "pass")
        self.assertNotIn("merge_eligible", json.dumps(snapshot, sort_keys=True).lower())
        self.assertNotIn("production verified", json.dumps(snapshot, sort_keys=True).lower())

    def test_prompt_preview_is_real_draft_and_verification_is_not_run(self) -> None:
        demo = _demo_module()
        self.assertIsNotNone(demo, "adaptive_grok.demo must provide prompt previews")
        prompt = "Add authentication security to a responsive API dashboard"

        preview = demo.build_prompt_preview(ROOT, prompt, now=NOW, request_id="req-preview")
        direct_route = build_route(ROOT, prompt, "demo-preview").to_dict()
        direct_spec = generate_spec(direct_route)

        self.assertEqual(preview["mode"], "computed_preview")
        self.assertEqual(preview["route"]["risk"], direct_route["risk"])
        self.assertEqual(preview["route"]["domains"], direct_route["domains"])
        self.assertEqual(preview["spec"]["digest"], canonical_spec_digest(direct_spec))
        self.assertEqual(preview["spec"]["source"], "computed_preview")
        self.assertEqual(preview["spec"]["status"], "draft")
        self.assertEqual(preview["verification"], {
            "source": "computed_preview",
            "status": "not_run",
            "digest": None,
            "checks": [],
            "pass": 0,
            "fail": 0,
            "skip": 0,
        })

    def test_alternate_scenario_claims_match_its_computed_route(self) -> None:
        demo = _demo_module()
        self.assertIsNotNone(demo, "adaptive_grok.demo must provide alternate scenario evidence")
        snapshot = demo.build_sample_snapshot(ROOT, now=NOW, request_id="req-alternate")
        scenario = snapshot["scenario"]
        self.assertIn("alternate_route", scenario)
        self.assertIn("alternate_action_label", scenario)

        metadata = demo.DEMO_ROUTE_METADATA
        direct = build_route(
            ROOT,
            scenario["alternate_prompt"],
            "demo-alternate",
            base_commit_override=metadata["base_commit"],
            base_fingerprint_override=metadata["base_fingerprint"],
        ).to_dict()
        alternate = scenario["alternate_route"]
        for field in ("intent", "risk", "domains", "write_agent"):
            self.assertEqual(alternate[field], direct[field])
        self.assertEqual(alternate["intent"], "review")
        self.assertEqual(alternate["risk"], "medium")
        self.assertEqual(alternate["domains"], ["api"])
        self.assertIsNone(alternate["write_agent"])
        self.assertEqual(
            scenario["alternate_action_label"],
            "Use contrasting review route · medium risk · no write owner",
        )
        if alternate["risk"] != "low":
            self.assertNotIn("low risk", scenario["alternate_action_label"].lower())

    def test_fixture_loader_rejects_duplicate_keys_and_invalid_verification_status(self) -> None:
        demo = _demo_module()
        self.assertIsNotNone(demo, "adaptive_grok.demo must validate bundled fixtures")
        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp)
            sample = copied / ".grok-stack/demo/sample"
            sample.mkdir(parents=True)
            for name in ("task.json", "change-spec.json", "verification-report.json"):
                (sample / name).write_bytes((ROOT / ".grok-stack/demo/sample" / name).read_bytes())

            (sample / "task.json").write_text(
                '{"schema_version":1,"schema_version":1,"primary_prompt":"x","alternate_prompt":"y"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                demo.load_demo_fixtures(copied)

            (sample / "task.json").write_bytes((ROOT / ".grok-stack/demo/sample/task.json").read_bytes())
            report = json.loads((sample / "verification-report.json").read_text(encoding="utf-8"))
            report["checks"][0]["status"] = "verified"
            (sample / "verification-report.json").write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "status"):
                demo.load_demo_fixtures(copied)

    def test_architecture_failure_degrades_only_that_panel(self) -> None:
        demo = _demo_module()
        self.assertIsNotNone(demo, "adaptive_grok.demo must support partial degradation")
        original = demo.load_architecture

        def unavailable(_root):
            raise OSError("private absolute path must not leak")

        demo.load_architecture = unavailable
        try:
            snapshot = demo.build_sample_snapshot(ROOT, now=NOW, request_id="req-degraded")
        finally:
            demo.load_architecture = original
        self.assertEqual(snapshot["architecture"], {
            "source": "live_repository",
            "status": "unavailable",
            "error": {"code": "resource_unavailable", "message": "Repository model is unavailable."},
        })
        self.assertEqual(snapshot["spec"]["status"], "complete")
        self.assertEqual(snapshot["governance"]["status"], "pass")
        self.assertEqual(snapshot["verification"]["status"], "pass")


class VerificationSummaryTests(unittest.TestCase):
    def test_report_summary_counts_real_checks_and_rejects_unknown_fields(self) -> None:
        verification = importlib.import_module("adaptive_grok.verification")
        self.assertTrue(
            hasattr(verification, "summarize_verification_report"),
            "verification module must expose a pure report summarizer",
        )
        report = {
            "schema_version": 1,
            "sample_id": "investor-demo-reviewed-intent-v1",
            "status": "sample_evidence",
            "checks": [
                {"name": "typed-spec", "status": "pass", "summary": "complete"},
                {"name": "architecture", "status": "pass", "summary": "model valid"},
                {"name": "browser-e2e", "status": "skip", "summary": "optional runner absent"},
            ],
        }
        summary = verification.summarize_verification_report(report)
        self.assertEqual((summary["pass"], summary["fail"], summary["skip"]), (2, 0, 1))
        self.assertEqual(summary["status"], "pass")
        with self.assertRaisesRegex(ValueError, "unknown"):
            verification.summarize_verification_report({**report, "command": "git push"})


class DashboardAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.demo_root = ROOT / ".grok-stack/demo"
        cls.html = (cls.demo_root / "index.html").read_text(encoding="utf-8") if (cls.demo_root / "index.html").is_file() else ""
        cls.css = (cls.demo_root / "assets/app.css").read_text(encoding="utf-8") if (cls.demo_root / "assets/app.css").is_file() else ""
        cls.javascript = "\n".join(
            (cls.demo_root / f"assets/{name}").read_text(encoding="utf-8")
            for name in ("api.js", "render.js", "app.js")
            if (cls.demo_root / f"assets/{name}").is_file()
        )

    def test_semantic_shell_wires_landmarks_labels_live_regions_and_focus(self) -> None:
        self.assertIn('<html lang="en">', self.html)
        self.assertIn('name="viewport"', self.html)
        self.assertIn('class="skip-link" href="#main"', self.html)
        self.assertIn("<header", self.html)
        self.assertIn('<main id="main"', self.html)
        self.assertIn('<form id="preview-form"', self.html)
        self.assertRegex(self.html, r'<label[^>]+for="prompt"')
        self.assertRegex(self.html, r'<textarea[^>]+id="prompt"[^>]+aria-describedby="prompt-help prompt-error"')
        self.assertRegex(self.html, r'id="prompt-error"[^>]+role="alert"')
        self.assertRegex(self.html, r'id="live-status"[^>]+aria-live="polite"')
        self.assertRegex(self.html, r'id="results-heading"[^>]+tabindex="-1"')
        for panel in ("route", "spec", "architecture", "governance", "verification"):
            self.assertIn(f'id="{panel}-panel"', self.html)

    def test_browser_assets_use_only_safe_text_rendering_and_same_origin_resources(self) -> None:
        for forbidden in ("innerHTML", "insertAdjacentHTML", "eval(", "localStorage", "sessionStorage", "serviceWorker"):
            self.assertNotIn(forbidden, self.javascript)
        self.assertNotRegex(self.html, r"<(?:script|style)[^>]*>\s*[^<\s]")
        self.assertNotRegex(self.html, r'https?://')
        self.assertNotRegex(self.javascript, r'https?://')
        self.assertIn("textContent", self.javascript)
        self.assertIn("fetch(path", self.javascript)
        self.assertIn('request("/api/v1/snapshot")', self.javascript)
        self.assertIn('request("/api/v1/preview"', self.javascript)

        html_ids = set(re.findall(r'id="([A-Za-z0-9_-]+)"', self.html))
        referenced = set(re.findall(r'getElementById\("([A-Za-z0-9_-]+)"\)', self.javascript))
        self.assertEqual(referenced - html_ids, set())

    def test_dashboard_implements_loading_validation_degraded_stale_and_retry_states(self) -> None:
        for phrase in (
            "Loading local evidence",
            "Prompt must contain",
            "Repository model is unavailable",
            "Stale — local server unavailable",
            "Retry",
            "Draft route/spec preview — verification not run",
        ):
            self.assertIn(phrase, self.html + self.javascript)
        self.assertIn("aria-busy", self.javascript)
        self.assertIn("lastGood", self.javascript)
        self.assertIn("resultsHeading.focus", self.javascript)

    def test_alternate_button_uses_the_computed_route_label(self) -> None:
        self.assertNotIn("low-risk", (self.html + self.javascript).lower())
        self.assertIn(
            "snapshot.scenario?.alternate_action_label",
            self.javascript,
        )
        self.assertIn("alternateButton.textContent", self.javascript)

    def test_styles_cover_mobile_focus_reduced_motion_and_forced_colors(self) -> None:
        self.assertIn("@media (max-width: 760px)", self.css)
        self.assertIn("grid-template-columns: 1fr", self.css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.css)
        self.assertIn("@media (forced-colors: active)", self.css)
        self.assertIn(":focus-visible", self.css)
        self.assertRegex(self.css, r"min-height:\s*44px")
        self.assertIn("overflow-wrap: anywhere", self.css)


if __name__ == "__main__":
    unittest.main()
