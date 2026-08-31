from __future__ import annotations

import itertools
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StructureTests(unittest.TestCase):
    def test_frozen_m2_handoff_digests_match_canonical_summary(self) -> None:
        result = subprocess.run(
            ['python3', 'scripts/grok_architecture.py', 'summary', '--json'],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        summary = json.loads(result.stdout)
        requirements = (
            ROOT / 'engineering/changes/20260826-m2-executable-architecture-015603/requirements.md'
        ).read_text(encoding='utf-8')
        labels = {
            'architecture_digest': 'Composite architecture digest',
            'system_digest': 'System digest',
            'rules_digest': 'Rules digest',
            'schema_digest': 'Composite schema digest',
            'contract_inventory_digest': 'Contract inventory digest',
        }
        for field, label in labels.items():
            matches = re.findall(rf'^- {re.escape(label)}: `([0-9a-f]{{64}})`\.$', requirements, re.M)
            self.assertEqual(len(matches), 1, label)
            self.assertEqual(matches[0], summary[field], label)

    def test_core_product_files_exist(self) -> None:
        required = (
            "AGENTS.md",
            "README.md",
            "VERSION",
            "CHANGELOG.md",
            "decisions.md",
            "mistakes.md",
            "Makefile",
            ".grok/hooks/adaptive.json",
            ".grok-stack/config/routing.json",
            ".grok-stack/config/policy.json",
            "scripts/grok_route.py",
            "scripts/grok_change.py",
            "scripts/grok_spec.py",
            "scripts/grok_verify.py",
            "scripts/grok_review.py",
            "scripts/grok_approve.py",
            "scripts/grok_deploy.py",
            "scripts/install_into.py",
            "architecture/adoption.json",
            "architecture/system.yaml",
            "architecture/rules.yaml",
            "architecture/generated/context.mmd",
            "architecture/generated/container.mmd",
            "architecture/generated/deployment.mmd",
            "architecture/generated/data-flow.mmd",
            "architecture/generated/trust-boundary.mmd",
            ".grok-stack/templates/architecture/system.example.yaml",
            ".grok-stack/templates/architecture/rules.example.yaml",
            "schemas/architecture-system.schema.json",
            "schemas/architecture-rules.schema.json",
            "scripts/grok_architecture.py",
        )
        for relative in required:
            self.assertTrue((ROOT / relative).exists(), relative)

    def test_agent_contract_starts_with_self_learning(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertLess(text.index("## Agent self-learning"), text.index("## README before push"))
        self.assertIn("decisions.md", text)
        self.assertIn("mistakes.md", text)

    def test_merge_trust_is_external_and_pr_only(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("adaptive-trust-ci/verified", text)
        self.assertIn("Direct push to `main`", text)
        self.assertIn("GitHub Actions", text)
        self.assertIn("local receipts", text.lower())
        self.assertIn("not merge authority", text.lower())
        self.assertNotIn("git push origin main", text)

    def test_version_identity_matches_readme(self) -> None:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertTrue(readme.startswith(f"# Adaptive Grok Build Pro v{version}\n"))

    def test_readme_stack_graph_is_complete(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        nodes = [
            "Route",
            "Skills",
            "Agents",
            "Hooks",
            "Policy",
            "Verify",
            "Packages",
            "Contract",
            "Decisions",
            "Mistakes",
            "TrustAPI",
            "TrustWorker",
            "Postgres",
            "Runner",
            "Holdout",
            "GitHubApp",
        ]
        missing = []
        for left, right in itertools.combinations(nodes, 2):
            forward = f"{left} --- {right}"
            reverse = f"{right} --- {left}"
            if forward not in readme and reverse not in readme:
                missing.append(f"{left}<->{right}")
        self.assertEqual(missing, [])
        mermaid = re.search(r"```mermaid\n(.*?)```", readme, re.S)
        self.assertIsNotNone(mermaid)
        edge_lines = [line for line in mermaid.group(1).splitlines() if re.search(r"\S+ --- \S+", line)]
        self.assertEqual(len(edge_lines), len(list(itertools.combinations(nodes, 2))))

    def test_architecture_authority_and_manual_adoption_are_documented(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        quickstart = (ROOT / "QUICKSTART.md").read_text(encoding="utf-8")
        self.assertIn("decorative inventory", readme.lower())
        for relative in (
            "architecture/system.yaml",
            "architecture/rules.yaml",
            "architecture/generated/context.mmd",
            "schemas/architecture-system.schema.json",
            "schemas/architecture-rules.schema.json",
            "scripts/grok_architecture.py",
        ):
            self.assertIn(f"]({relative})", readme, relative)
        self.assertIn("architecture/adoption.json", quickstart)
        self.assertIn('"architecture_id": "ARCH-REPLACE-ME"', quickstart)
        self.assertIn('"schema_version": 1', quickstart)
        self.assertIn('"state": "adopted"', quickstart)
        self.assertIn("marker last", quickstart.lower())

    def test_installer_safety_pivot_is_documented(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        quickstart = (ROOT / "QUICKSTART.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "DARK_FACTORY_ROADMAP.md").read_text(encoding="utf-8")
        package = ROOT / "engineering/changes/20260826-m2-executable-architecture-015603"
        architecture = (package / "architecture.md").read_text(encoding="utf-8")
        release = (package / "release.md").read_text(encoding="utf-8")
        test_plan = (package / "test-plan.md").read_text(encoding="utf-8")
        package_text = "\n".join(
            (package / name).read_text(encoding="utf-8")
            for name in (
                "architecture.md",
                "requirements.md",
                "test-plan.md",
                "tasks.md",
                "release.md",
                "rollback.md",
            )
        )

        for text in (readme, quickstart):
            self.assertIn("scripts/install_into.py --plan /path/to/your/repo", text)
            materialize = "scripts/install_into.py --materialize-new /path/to/new/repo"
            self.assertEqual(text.count(materialize), 1)
            adjacent_contract = text[text.index(materialize):text.index(materialize) + 1400]
            self.assertIn("Linux", adjacent_contract)
            self.assertIn("descriptor-relative", adjacent_contract)
            self.assertIn("renameat2(RENAME_NOREPLACE)", adjacent_contract)
            self.assertIn("fails closed", adjacent_contract)
            self.assertIn("no fallback", adjacent_contract)
            self.assertIn("--plan", adjacent_contract)
            self.assertIn("normal reviewed source-change", adjacent_contract)
            self.assertIn("`--force` is rejected", text)
            self.assertIn("existing repositories are read-only", text.lower())
            self.assertIn("dependency advice", text.lower())
            self.assertIn("architecture/adoption.json", text)
            self.assertIn("architecture/system.yaml", text)
            self.assertIn("architecture/rules.yaml", text)
            for pattern in (
                r"\b(?:the )?installer (?:updates?|overwrites?|modifies?|merges into) "
                r"(?:an? )?existing (?:repository|checkout|target|consumer)",
                r"\b(?:use|using|with) `?--force`? to "
                r"(?:update|overwrite|modify|merge)",
                r"`--materialize-new` (?:updates?|overwrites?|modifies?|merges) "
                r"(?:an? )?existing (?:repository|checkout|target|consumer)",
            ):
                self.assertIsNone(re.search(pattern, text, re.I), pattern)

        for surface in (architecture, release):
            self.assertIn("Linux", surface)
            self.assertIn("descriptor-relative", surface)
            self.assertIn("renameat2(RENAME_NOREPLACE)", surface)
            self.assertIn("fails closed", surface)
            self.assertIn("no fallback", surface)
            self.assertIn("--plan", surface)
            self.assertIn("normal reviewed source-change", surface)

        reviewed_head = "<reviewed-40-character-head-sha>"
        adoption_base = "25bfbe59ea188d9687b20a9caad19e7db3d031f8"
        self.assertIn("python3 scripts/grok_architecture.py summary --json", test_plan)
        self.assertIn(
            f"python3 scripts/grok_architecture.py diff --base {adoption_base} "
            f"--head {reviewed_head} --json",
            test_plan,
        )
        self.assertIn(
            f"python3 scripts/grok_architecture.py fitness --base {adoption_base} "
            f"--head {reviewed_head} --pre-risk red --json",
            test_plan,
        )
        self.assertIn("replace the placeholder", test_plan.lower())
        self.assertIn("never use `head` or `--worktree`", test_plan.lower())

        self.assertIn(
            "docs/superpowers/specs/2026-08-27-m2a-queue-installer-pivot-design.md",
            readme,
        )
        self.assertIn(
            "docs/superpowers/plans/2026-08-27-m2a-queue-installer-pivot.md",
            readme,
        )
        self.assertNotIn(
            "copies the local stack and installs missing required tools",
            readme,
        )
        self.assertNotIn("installs the stack and missing required tools", quickstart)
        self.assertIn("bounded abstract interpreter", roadmap.lower())
        self.assertIn("bounded abstract interpreter", package_text.lower())
        self.assertIn("manual cleanup required: installer ownership is unresolved", package_text)
        self.assertIn("AC-007 remains open", package_text)
        self.assertIn("M2-B", package_text)
        self.assertIn("App-owned", package_text)

    def test_no_github_actions_workflow_exists(self) -> None:
        self.assertFalse((ROOT / ".github/workflows").exists())
        for path in ROOT.rglob("*.yml"):
            self.assertFalse(path.as_posix().startswith((ROOT / ".github/workflows").as_posix()))
        for path in ROOT.rglob("*.yaml"):
            self.assertFalse(path.as_posix().startswith((ROOT / ".github/workflows").as_posix()))

    def test_trust_ci_control_plane_is_complete(self) -> None:
        required = (
            "trust-ci/pyproject.toml",
            "trust-ci/README.md",
            "trust-ci/compose.yaml",
            "trust-ci/Dockerfile.api",
            "trust-ci/Dockerfile.worker",
            "trust-ci/runner.Dockerfile",
            "trust-ci/config/policy.example.json",
            "trust-ci/config/trust-store.example.json",
            "trust-ci/sql/001_schema.sql",
            "trust-ci/src/adaptive_trust_ci/api.py",
            "trust-ci/src/adaptive_trust_ci/runner.py",
            "trust-ci/src/adaptive_trust_ci/store.py",
            "trust-ci/src/adaptive_trust_ci/signing.py",
            "trust-ci/tests/test_runner.py",
            "engineering/runbooks/trust-ci-rollout.md",
        )
        for relative in required:
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_local_policy_protects_control_plane(self) -> None:
        policy = json.loads((ROOT / ".grok-stack/config/policy.json").read_text(encoding="utf-8"))
        protected = set(policy["protected_paths"])
        for expected in (
            ".github/**",
            ".grok/**",
            ".grok-stack/**",
            "AGENTS.md",
            "trust-ci/**",
        ):
            self.assertIn(expected, protected)
        self.assertTrue(
            "scripts/grok_verify.py" in protected or "scripts/grok_*.py" in protected,
            "local policy must protect scripts/grok_verify.py",
        )

    def test_trust_ci_policy_uses_immutable_sandbox_and_external_status(self) -> None:
        policy = json.loads((ROOT / "trust-ci/config/policy.example.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["status_context"], "adaptive-trust-ci/verified")
        image = str(policy["sandbox"]["image"])
        self.assertTrue(
            image.endswith("@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST")
            or re.search(r"(?:^sha256:|@sha256:)[0-9a-f]{64}$", image),
            image,
        )
        self.assertEqual(policy["sandbox"]["runtime"], "docker")
        self.assertTrue(all(command.get("required") is True for command in policy["commands"]))

    def test_hook_registration_has_required_lifecycle_events(self) -> None:
        hooks = json.loads((ROOT / ".grok/hooks/adaptive.json").read_text(encoding="utf-8"))["hooks"]
        for event in (
            "SessionStart",
            "UserPromptSubmit",
            "PreToolUse",
            "PostToolUse",
            "PreCompact",
            "SubagentStart",
            "SubagentStop",
            "Stop",
            "SessionEnd",
        ):
            self.assertIn(event, hooks)

    def test_root_has_no_packaging_marker(self) -> None:
        for name in ("pyproject.toml", "requirements.txt", "setup.py"):
            self.assertFalse((ROOT / name).exists(), name)
        self.assertTrue((ROOT / "trust-ci/pyproject.toml").is_file())


if __name__ == "__main__":
    unittest.main()
