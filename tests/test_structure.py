from __future__ import annotations

import hashlib
import itertools
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StructureTests(unittest.TestCase):
    @staticmethod
    def _resolve_openapi_schema(openapi: dict, schema: dict) -> dict:
        reference = schema.get("$ref") if isinstance(schema, dict) else None
        if reference is None:
            return schema
        prefix = "#/components/schemas/"
        if not isinstance(reference, str) or not reference.startswith(prefix):
            raise AssertionError(f"unsafe OpenAPI schema reference: {reference!r}")
        return openapi["components"]["schemas"][reference[len(prefix):]]

    def test_m3_route_binds_exact_reviewed_m2_fingerprint(self) -> None:
        route_path = (
            ROOT
            / "engineering/changes/20260826-m3-m9-production-delivery-continuation-355689/route.json"
        )
        route = json.loads(
            route_path.read_text(encoding="utf-8")
        )
        expected_commit = "635c9ddf2d63c1ea823074106976a8f3de6299a9"
        expected_fingerprint = (
            "6b4212f06a6c095db1a9e9c6eeb8c51d731dfa900e596bc915f98c012a4ac59c"
        )

        self.assertEqual(route["base_commit"], expected_commit)
        self.assertEqual(len(route["base_fingerprint"]), 64)
        self.assertEqual(route["base_fingerprint"], expected_fingerprint)
        self.assertEqual(
            route["base_fingerprint"],
            hashlib.sha256(expected_commit.encode("ascii")).hexdigest(),
        )
        package = route_path.parent
        state = json.loads((package / "state.json").read_text(encoding="utf-8"))
        change_spec = json.loads(
            (package / "change-spec.yaml").read_text(encoding="utf-8")
        )
        expected_change_id = package.name
        self.assertEqual(route["change_id"], expected_change_id)
        self.assertEqual(state["change_id"], expected_change_id)
        self.assertEqual(change_spec["change_id"], expected_change_id)

        roadmap = (ROOT / "DARK_FACTORY_ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn(
            "Require independent review and explicit human approval before promotion to `active`.",
            roadmap,
        )
        self.assertNotIn(
            "Require independent review or explicit human approval before promotion to `active`.",
            roadmap,
        )

    def test_frozen_m2_handoff_digests_match_canonical_summary(self) -> None:
        base = '635c9ddf2d63c1ea823074106976a8f3de6299a9'
        with tempfile.TemporaryDirectory(prefix='adaptive-grok-frozen-m2-') as tmp:
            archive = subprocess.Popen(
                ['git', 'archive', base],
                cwd=ROOT,
                stdout=subprocess.PIPE,
            )
            extracted = subprocess.run(
                ['tar', '-x', '-C', tmp],
                stdin=archive.stdout,
                check=True,
            )
            self.assertEqual(extracted.returncode, 0)
            assert archive.stdout is not None
            archive.stdout.close()
            self.assertEqual(archive.wait(), 0)
            result = subprocess.run(
                [
                    'python3',
                    'scripts/grok_architecture.py',
                    '--root',
                    tmp,
                    'summary',
                    '--json',
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
        summary = json.loads(result.stdout)
        requirements = subprocess.check_output(
            [
                'git',
                'show',
                f'{base}:engineering/changes/20260826-m2-executable-architecture-015603/requirements.md',
            ],
            cwd=ROOT,
            text=True,
            encoding='utf-8',
        )
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
            "governance/rules/index.json",
            "governance/debt/index.json",
            "governance/canonical-examples/index.json",
            "schemas/governance-rule.schema.json",
            "schemas/debt-entry.schema.json",
            "schemas/canonical-example.schema.json",
            "schemas/governance-handoff-v1.schema.json",
            "scripts/grok_governance.py",
            "factory/src/adaptive_factory/semantic_contracts.py",
            "factory/src/adaptive_factory/semantic_adjudication.py",
            "factory/src/adaptive_factory/semantic_repair.py",
            "factory/contracts/jsonschema/semantic-subject.v1.schema.json",
            "factory/contracts/jsonschema/semantic-finding.v1.schema.json",
            "factory/contracts/jsonschema/semantic-coverage.v1.schema.json",
            "factory/contracts/jsonschema/semantic-verdict.v1.schema.json",
            "factory/contracts/jsonschema/repair-directive.v1.schema.json",
            "docs/superpowers/specs/2026-09-01-m6-semantic-validation-provisional-design.md",
            "docs/superpowers/plans/2026-09-01-m6-semantic-validation-provisional.md",
            "engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/brief.md",
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
            "Factory",
            "M5Execution",
            "M6Semantic",
            "M7Shadow",
            "M8Autonomy",
            "M9Delivery",
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

    def test_m6_current_docs_are_bidirectionally_connected_and_factual(self) -> None:
        package = "engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8"
        paths = {
            "readme": ROOT / "README.md",
            "roadmap": ROOT / "DARK_FACTORY_ROADMAP.md",
            "factory": ROOT / "factory/README.md",
            "spec": ROOT / "docs/superpowers/specs/2026-09-01-m6-semantic-validation-provisional-design.md",
            "plan": ROOT / "docs/superpowers/plans/2026-09-01-m6-semantic-validation-provisional.md",
            "package": ROOT / package / "brief.md",
            "release": ROOT / package / "release.md",
            "rollback": ROOT / package / "rollback.md",
            "evidence": ROOT / package / "evidence/README.md",
        }
        text = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
        for relative in (
            "DARK_FACTORY_ROADMAP.md",
            "docs/superpowers/specs/2026-09-01-m6-semantic-validation-provisional-design.md",
            "docs/superpowers/plans/2026-09-01-m6-semantic-validation-provisional.md",
            f"{package}/brief.md",
            f"{package}/release.md",
            f"{package}/rollback.md",
            f"{package}/evidence/README.md",
        ):
            self.assertIn(relative, text["readme"], relative)
        self.assertIn("README.md", text["roadmap"])
        for name in ("spec", "plan", "package", "release", "rollback", "evidence"):
            self.assertIn("README.md", text[name], name)
            self.assertIn("DARK_FACTORY_ROADMAP.md", text[name], name)
        combined = "\n".join(text.values())
        for marker in (
            "94fc5ad878e6b15df6418303caada49a3b93bf4c",
            "TaskPacket",
            "RunManifest",
            "WorkspaceResult",
            "BLOCKED",
            "not full M6",
            "2026-09-08T00:00:00+03:00",
        ):
            self.assertIn(marker, combined, marker)
    def test_m5_execution_contracts_openapi_and_current_docs_are_connected(self) -> None:
        schema_dir = ROOT / "factory/contracts/schemas"
        expected_schema_paths = {
            "factory/contracts/schemas/execution-event.v1.json",
            "factory/contracts/schemas/execution-invocation.v1.json",
            "factory/contracts/schemas/task-packet.v1.json",
            "factory/contracts/schemas/workspace-result.v1.json",
        }
        self.assertEqual(
            {
                path.relative_to(ROOT).as_posix()
                for path in schema_dir.glob("*.json")
            },
            expected_schema_paths,
        )

        def assert_closed_objects(value, label: str) -> None:
            if isinstance(value, dict):
                if value.get("type") == "object":
                    self.assertIs(value.get("additionalProperties"), False, label)
                    self.assertTrue(
                        set(value.get("required", []))
                        <= set(value.get("properties", {})),
                        label,
                    )
                for key, child in value.items():
                    assert_closed_objects(child, f"{label}/{key}")
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    assert_closed_objects(child, f"{label}/{index}")

        for relative in sorted(expected_schema_paths):
            document = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            assert_closed_objects(document, relative)

        openapi_path = ROOT / "factory/contracts/openapi/factory-control.v1.json"
        openapi = json.loads(openapi_path.read_text(encoding="utf-8"))
        expected_operations = {
            ("GET", "/health/live", "healthLive"),
            ("GET", "/health/ready", "healthReady"),
            ("GET", "/metrics", "readMetrics"),
            ("GET", "/v1/tasks", "listTasks"),
            ("POST", "/v1/tasks", "submitTask"),
            ("GET", "/v1/tasks/{task_id}", "getTask"),
            ("POST", "/v1/tasks/{task_id}/cancel", "cancelTask"),
            ("POST", "/v1/claims", "claimLegacyTask"),
            ("POST", "/v1/execution/claims", "claimExecution"),
            ("POST", "/v1/execution/stages", "advanceExecution"),
            ("POST", "/v1/execution/notes", "proposeExecutionNote"),
            ("POST", "/v1/execution/artifacts", "proposeExecutionArtifact"),
            ("POST", "/v1/execution/usage", "reportExecutionUsage"),
            ("POST", "/v1/execution/terminal", "proposeExecutionTerminal"),
            ("POST", "/v1/heartbeats", "heartbeatLease"),
            ("POST", "/v1/proposals", "releaseProposal"),
            ("POST", "/v1/budget-reservations", "reserveBudget"),
            ("POST", "/v1/usage-observations", "observeUsage"),
            ("POST", "/v1/kill-switches", "setKillSwitch"),
            ("POST", "/v1/reconcile", "reconcileFactory"),
            ("POST", "/v1/semantic/subjects", "publishSemanticSubject"),
            ("GET", "/v1/semantic/subjects/{subject_digest}", "getSemanticSubject"),
            ("POST", "/v1/semantic/subjects/{subject_digest}/assignments", "createSemanticAssignment"),
            ("POST", "/v1/semantic/assignments/{assignment_digest}/evidence", "submitSemanticEvidence"),
            ("POST", "/v1/semantic/subjects/{subject_digest}/adjudications", "adjudicateSemanticSubject"),
            ("GET", "/v1/semantic/subjects/{subject_digest}/verdict", "getSemanticVerdict"),
        }
        operations = {
            (method.upper(), path, operation.get("operationId"))
            for path, path_item in openapi["paths"].items()
            for method, operation in path_item.items()
            if method in {"get", "post", "put", "patch", "delete"}
        }
        self.assertEqual(operations, expected_operations)
        operation_ids = {operation_id for _, _, operation_id in operations}
        self.assertEqual(len(operation_ids), len(operations))

        for method, path, operation_id in sorted(operations):
            operation = openapi["paths"][path][method.lower()]
            parameters = {
                (parameter["in"], parameter["name"]): parameter
                for parameter in operation.get("parameters", [])
            }
            if path not in {"/health/live", "/health/ready"}:
                self.assertTrue(
                    parameters[("header", "Authorization")]["required"],
                    operation_id,
                )
            if method == "POST":
                for name in ("Idempotency-Key", "X-Correlation-ID"):
                    self.assertTrue(
                        parameters[("header", name)]["required"], operation_id
                    )
                body = operation.get("requestBody", {})
                self.assertTrue(body.get("required"), operation_id)
                request_schema = body["content"]["application/json"]["schema"]
                request_schema = self._resolve_openapi_schema(openapi, request_schema)
                self.assertEqual(request_schema.get("type"), "object", operation_id)
                self.assertIs(request_schema.get("additionalProperties"), False, operation_id)
            for status, response in operation["responses"].items():
                self.assertRegex(status, r"^[1-5][0-9]{2}$")
                self.assertIn("content", response, f"{operation_id}:{status}")
                for media in response["content"].values():
                    self.assertIn("schema", media, f"{operation_id}:{status}")
            success = next(
                response
                for status, response in operation["responses"].items()
                if status.startswith("2")
            )
            if path not in {"/health/live", "/health/ready", "/metrics"}:
                self.assertIn("X-Correlation-ID", success.get("headers", {}), operation_id)

        assert_closed_objects(openapi["components"]["schemas"], "openapi/components/schemas")

        package = ROOT / "engineering/changes/20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f"
        current_docs = {
            "README": ROOT / "README.md",
            "roadmap": ROOT / "DARK_FACTORY_ROADMAP.md",
            "factory": ROOT / "factory/README.md",
            "architecture": package / "architecture.md",
            "tasks": package / "tasks.md",
            "schedule": package / "schedule.md",
            "release": package / "release.md",
            "rollback": package / "rollback.md",
            "evidence": package / "evidence/README.md",
        }
        texts = {name: path.read_text(encoding="utf-8") for name, path in current_docs.items()}
        combined = "\n".join(texts.values())
        for fact in (
            "161199bb163e0ba84ac1b32010be87f113df5e86",
            "01a10f5",
            "460a8a01a6394cac710b4e3f9eea3d94d4beef89",
            "94fc5ad878e6b15df6418303caada49a3b93bf4c",
            "37b05f579320",
            "2026-09-08 00:00 UTC+3",
            "BLOCKED",
        ):
            self.assertIn(fact, combined)
        for phrase in (
            "no WorkspaceResult fabrication",
            "restack",
            "not pushed",
            "not merged",
            "M6 paused",
            "provider facts are not authority",
            "production remains human-owned",
        ):
            self.assertIn(phrase, combined)
        for name, text in texts.items():
            if name in {"README", "roadmap", "factory"}:
                self.assertIn("2026-09-01-m5-isolated-provider-execution-design.md", text, name)
                self.assertIn("2026-09-01-m5-isolated-provider-execution.md", text, name)
                self.assertIn(package.name, text, name)
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
