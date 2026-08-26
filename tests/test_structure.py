from __future__ import annotations

import itertools
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StructureTests(unittest.TestCase):
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
