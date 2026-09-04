from __future__ import annotations

import hashlib
import itertools
import json
import jsonschema
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StructureTests(unittest.TestCase):
    @staticmethod
    def _resolve_openapi_schema(openapi: dict, schema: dict) -> dict:
        reference = schema.get("$ref")
        if reference is None:
            return schema
        prefix = "#/components/schemas/"
        if not reference.startswith(prefix) or "/" in reference[len(prefix):]:
            raise AssertionError(f"unsafe OpenAPI schema reference: {reference!r}")
        return openapi["components"]["schemas"][reference[len(prefix):]]

    def test_factory_control_v1_retains_exact_m4_baseline(self) -> None:
        baseline = ROOT / "factory/contracts/openapi/factory-control.v1.json"
        raw = baseline.read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "566209fdcf4db042ba4b7fa0c349d3308b86832208849dd4cbe3b8bf86ecec9e",
        )
        git_blob = b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
        self.assertEqual(
            hashlib.sha1(git_blob, usedforsecurity=False).hexdigest(),
            "78365e2367c31b22fbdcab16133ff0973f4460b5",
        )

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
            "factory/src/adaptive_factory/semantic_bridge.py",
            "factory/src/adaptive_factory/semantic_repair.py",
            "factory/contracts/jsonschema/repair-directive.v1.schema.json",
            "factory/contracts/jsonschema/semantic-coverage.v1.schema.json",
            "factory/contracts/jsonschema/semantic-execution-binding.v1.schema.json",
            "factory/contracts/jsonschema/semantic-finding.v1.schema.json",
            "factory/contracts/jsonschema/semantic-subject.v1.schema.json",
            "factory/contracts/jsonschema/semantic-validation-inputs.v1.schema.json",
            "factory/contracts/jsonschema/semantic-verdict.v1.schema.json",
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
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "DARK_FACTORY_ROADMAP.md").read_text(encoding="utf-8")
        self.assertEqual(version, "2.0.13")
        self.assertTrue(readme.startswith(f"# Adaptive Grok Build Pro v{version}\n"))
        self.assertIn("Identity: **2.0.13**", readme)
        self.assertTrue(changelog.startswith("# Changelog\n\n## 2.0.13 — 2026-09-02\n"))
        self.assertIn("product version: 2.0.13", roadmap)
        sys.path.insert(0, str(ROOT / ".grok-stack"))
        try:
            import adaptive_grok

            self.assertEqual(adaptive_grok.__version__, version)
        finally:
            sys.path.pop(0)

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

    def test_m5_execution_openapi_v1_is_immutable_and_v2_is_closed_additive(self) -> None:
        control = json.loads(
            (ROOT / "factory/contracts/openapi/factory-control.v1.json").read_text(
                encoding="utf-8"
            )
        )
        v1_path = ROOT / "factory/contracts/openapi/factory-execution.v1.json"
        self.assertEqual(
            hashlib.sha256(v1_path.read_bytes()).hexdigest(),
            "30bb6feab2623052fffe099d66fb758cd60c76b69ad13d85610791ae70c83e61",
        )
        execution_v1 = json.loads(v1_path.read_text(encoding="utf-8"))
        execution = json.loads(
            (ROOT / "factory/contracts/openapi/factory-execution.v2.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(execution_v1["info"]["version"], "1.0.0")
        self.assertEqual(execution["info"]["version"], "2.0.0")
        expected = {
            ("POST", "/v2/execution/claims", "claimExecution"),
            ("POST", "/v2/execution/stages", "advanceExecution"),
            ("POST", "/v2/execution/notes", "proposeExecutionNote"),
            ("POST", "/v2/execution/artifacts", "proposeExecutionArtifact"),
            ("POST", "/v2/execution/usage", "reportExecutionUsage"),
            ("POST", "/v2/execution/terminal", "completeExecutionTerminal"),
        }

        def operations(document: dict) -> set[tuple[str, str, str]]:
            return {
                (method.upper(), path, operation.get("operationId"))
                for path, path_item in document["paths"].items()
                for method, operation in path_item.items()
                if method in {"get", "post", "put", "patch", "delete"}
            }

        execution_operations = operations(execution)
        v1_operations = operations(execution_v1)
        control_operations = operations(control)
        self.assertEqual(execution_operations, expected)
        self.assertEqual(
            v1_operations,
            {
                ("POST", "/v1/execution/claims", "claimExecution"),
                ("POST", "/v1/execution/stages", "advanceExecution"),
                ("POST", "/v1/execution/notes", "proposeExecutionNote"),
                ("POST", "/v1/execution/artifacts", "proposeExecutionArtifact"),
                ("POST", "/v1/execution/usage", "reportExecutionUsage"),
                ("POST", "/v1/execution/terminal", "proposeExecutionTerminal"),
            },
        )
        self.assertEqual(
            execution_v1["paths"]["/v1/execution/terminal"]["post"]["responses"]
            ["200"]["content"]["application/json"]["schema"],
            {"$ref": "#/components/schemas/ProposalResponse"},
        )
        self.assertFalse(
            {path for _, path, _ in execution_operations}
            & {path for _, path, _ in control_operations}
        )
        self.assertFalse(
            {operation_id for _, _, operation_id in execution_operations}
            & {operation_id for _, _, operation_id in control_operations}
        )
        self.assertEqual(
            sum(
                len(operation["responses"])
                for path_item in execution["paths"].values()
                for method, operation in path_item.items()
                if method in {"get", "post", "put", "patch", "delete"}
            ),
            54,
        )

        for method, path, operation_id in sorted(execution_operations):
            operation = execution["paths"][path][method.lower()]
            self.assertEqual(
                set(operation["responses"]),
                {"200", "400", "401", "403", "409", "413", "422", "500", "503"},
                operation_id,
            )
            parameters = {
                (parameter["in"], parameter["name"]): parameter
                for parameter in operation.get("parameters", [])
            }
            self.assertEqual(operation.get("security"), [{"bearerAuth": []}])
            self.assertEqual(
                operation["responses"]["500"],
                {
                    "description": "internal integrity failure",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    },
                },
                operation_id,
            )
            self.assertNotIn(("header", "Authorization"), parameters)
            for name in ("Idempotency-Key", "X-Correlation-ID"):
                self.assertTrue(
                    parameters[("header", name)]["required"], operation_id
                )
            body = operation.get("requestBody", {})
            self.assertTrue(body.get("required"), operation_id)
            request_schema = self._resolve_openapi_schema(
                execution, body["content"]["application/json"]["schema"]
            )
            request_variants = request_schema.get("oneOf", [request_schema])
            self.assertTrue(request_variants, operation_id)
            for request_variant in request_variants:
                self.assertEqual(request_variant.get("type"), "object", operation_id)
                self.assertIs(
                    request_variant.get("additionalProperties"), False, operation_id
                )
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
            self.assertIn(
                "X-Correlation-ID", success.get("headers", {}), operation_id
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

        self.assertEqual(len(execution["components"]["schemas"]), 23)
        response_schemas = {
            "notes": "NoteProposalResponse",
            "artifacts": "ArtifactProposalResponse",
            "usage": "UsageProposalResponse",
        }
        for route, schema_name in response_schemas.items():
            self.assertEqual(
                execution["paths"][f"/v2/execution/{route}"]["post"]["responses"]
                ["200"]["content"]["application/json"]["schema"],
                {"$ref": f"#/components/schemas/{schema_name}"},
            )
        self.assertEqual(
            execution["paths"]["/v2/execution/terminal"]["post"]["responses"]["200"]
            ["content"]["application/json"]["schema"],
            {"$ref": "#/components/schemas/TerminalCompletionResponse"},
        )
        self.assertEqual(
            execution["components"]["schemas"]["TerminalCompletionResponse"]
            ["properties"]["proposal"],
            {"$ref": "#/components/schemas/TerminalProposal"},
        )
        assert_closed_objects(
            execution["components"]["schemas"], "execution/components/schemas"
        )

        common_proposal = {
            "task_id": "00000000-0000-0000-0000-000000000001",
            "run_id": "00000000-0000-0000-0000-000000000002",
            "packet_digest": "d" * 64,
            "fence": 7,
            "sequence": 3,
            "author_role": "writer",
            "idempotency_key": "e" * 64,
        }
        proposals = {
            "NoteProposalResponse": {
                **common_proposal,
                "note_type": "finding",
                "body": "bounded",
                "evidence": ["factory/change.patch"],
            },
            "ArtifactProposalResponse": {
                **common_proposal,
                "artifact_class": "patch",
                "path": "factory/change.patch",
                "sha256": "a" * 64,
                "size_bytes": 12,
                "media_type": "text/plain",
                "artifact_attestation_digest": "b" * 64,
            },
            "UsageProposalResponse": {
                **common_proposal,
                "provider_call_id": "call-1",
                "price_table_digest": "c" * 64,
                "input_tokens": 1,
                "output_tokens": 2,
                "reasoning_tokens": 0,
                "cost_usd_micros": 3,
                "output_bytes": 4,
            },
        }
        for schema_name, proposal in proposals.items():
            validator = jsonschema.Draft202012Validator(
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$ref": f"#/components/schemas/{schema_name}",
                    "components": execution["components"],
                }
            )
            response = {"proposal": proposal}
            with self.subTest(valid_response=schema_name):
                validator.validate(response)
            with self.subTest(common_only=schema_name):
                self.assertFalse(
                    validator.is_valid({"proposal": common_proposal}), schema_name
                )
            wrong = next(
                value for name, value in proposals.items() if name != schema_name
            )
            with self.subTest(wrong_subtype=schema_name):
                self.assertFalse(validator.is_valid({"proposal": wrong}), schema_name)

        terminal_proposal_validator = jsonschema.Draft202012Validator(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$ref": "#/components/schemas/TerminalProposal",
                "components": execution["components"],
            }
        )
        terminal_proposal = {
            **common_proposal,
            "terminal_type": "run.completed",
            "summary": "complete",
            "failure_class": None,
            "reason": None,
            "diagnostic": None,
        }
        terminal_proposal_validator.validate(terminal_proposal)
        self.assertFalse(terminal_proposal_validator.is_valid(common_proposal))
        self.assertFalse(
            terminal_proposal_validator.is_valid(
                {**common_proposal, "note_type": "finding", "body": "wrong", "evidence": []}
            )
        )
        terminal_response_invalid = (
            {
                **terminal_proposal,
                "terminal_type": "run.failed",
                "summary": "unknown: bounded",
                "failure_class": "unknown",
                "diagnostic": "bounded",
            },
            {
                **terminal_proposal,
                "terminal_type": "run.failed",
                "summary": "validation: bounded",
                "failure_class": "validation",
                "diagnostic": "x" * 4097,
            },
            {
                **terminal_proposal,
                "terminal_type": "run.needs_human",
                "summary": "review: bounded",
                "reason": "x" * 4097,
                "diagnostic": "bounded",
            },
        )
        for proposal in terminal_response_invalid:
            with self.subTest(invalid_terminal_proposal=proposal["terminal_type"]):
                self.assertFalse(terminal_proposal_validator.is_valid(proposal))
        response_contract_negatives = {
            "NoteProposalResponse": {**proposals["NoteProposalResponse"], "note_type": "free-form"},
            "ArtifactProposalResponse": {**proposals["ArtifactProposalResponse"], "author_role": "reader"},
            "ArtifactProposalResponse/media": {**proposals["ArtifactProposalResponse"], "media_type": "Text/Plain"},
        }
        for label, proposal in response_contract_negatives.items():
            schema_name = label.split("/", 1)[0]
            validator = jsonschema.Draft202012Validator(
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$ref": f"#/components/schemas/{schema_name}",
                    "components": execution["components"],
                }
            )
            with self.subTest(response_parity=label):
                self.assertFalse(validator.is_valid({"proposal": proposal}))

        terminal_validator = jsonschema.Draft202012Validator(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$ref": "#/components/schemas/TerminalRequest",
                "components": execution["components"],
            }
        )
        grant = {
            "task_id": "00000000-0000-0000-0000-000000000001",
            "run_id": "00000000-0000-0000-0000-000000000002",
            "owner": "worker-01",
            "role": "writer",
            "fence": 7,
            "expires_at": "2026-09-02T01:00:00Z",
            "packet_digest": "0" * 64,
        }
        common = {"grant": grant, "packet_digest": "d" * 64, "sequence": 3}
        valid_terminal_payloads = (
            {**common, "terminal_type": "run.completed", "summary": "complete"},
            {
                **common,
                "terminal_type": "run.failed",
                "failure_class": "validation",
                "diagnostic": "bounded",
            },
            {
                **common,
                "terminal_type": "run.needs_human",
                "reason": "review",
                "diagnostic": "bounded",
            },
        )
        for payload in valid_terminal_payloads:
            with self.subTest(valid=payload["terminal_type"]):
                terminal_validator.validate(payload)
        invalid_terminal_payloads = (
            {
                **common,
                "terminal_type": "run.completed",
                "summary": "complete",
                "diagnostic": "cross-shape",
            },
            {
                **common,
                "terminal_type": "run.failed",
                "summary": "wrong variant",
            },
            {
                **common,
                "terminal_type": "run.needs_human",
                "failure_class": "validation",
                "diagnostic": "wrong variant",
            },
            {
                **common,
                "terminal_type": "run.failed",
                "failure_class": "unknown",
                "diagnostic": "bounded",
            },
            {
                **common,
                "terminal_type": "run.failed",
                "failure_class": "validation",
                "diagnostic": "x" * 4097,
            },
            {
                **common,
                "terminal_type": "run.needs_human",
                "reason": "x" * 4097,
                "diagnostic": "bounded",
            },
        )
        for payload in invalid_terminal_payloads:
            with self.subTest(invalid=payload["terminal_type"]):
                self.assertFalse(terminal_validator.is_valid(payload))

    def test_m6_semantic_control_openapi_is_closed_additive(self) -> None:
        document = json.loads(
            (ROOT / "factory/contracts/openapi/factory-control.v1.json").read_text(
                encoding="utf-8"
            )
        )
        operations = {
            (method.upper(), path, operation.get("operationId"))
            for path, path_item in document["paths"].items()
            for method, operation in path_item.items()
            if method in {"get", "post", "put", "patch", "delete"}
        }
        semantic = {
            operation for operation in operations if operation[1].startswith("/v1/semantic/")
        }
        self.assertEqual(
            semantic,
            {
                ("POST", "/v1/semantic/subjects", "publishSemanticSubject"),
                ("GET", "/v1/semantic/subjects/{subject_digest}", "getSemanticSubject"),
                (
                    "POST",
                    "/v1/semantic/subjects/{subject_digest}/assignments",
                    "createSemanticAssignment",
                ),
                (
                    "POST",
                    "/v1/semantic/assignments/{assignment_digest}/evidence",
                    "submitSemanticEvidence",
                ),
                (
                    "POST",
                    "/v1/semantic/subjects/{subject_digest}/adjudications",
                    "adjudicateSemanticSubject",
                ),
                (
                    "GET",
                    "/v1/semantic/subjects/{subject_digest}/verdict",
                    "getSemanticVerdict",
                ),
            },
        )
        self.assertEqual(len(operations), 23)
        for method, path, operation_id in semantic:
            operation = document["paths"][path][method.lower()]
            self.assertEqual(operation.get("security"), [{"bearerAuth": []}], operation_id)
            if method == "POST":
                self.assertTrue(operation.get("requestBody", {}).get("required"), operation_id)
            for status, response in operation["responses"].items():
                self.assertRegex(status, r"^[1-5][0-9]{2}$")
                self.assertIn("content", response, f"{operation_id}:{status}")

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
