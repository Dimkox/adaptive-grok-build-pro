from __future__ import annotations

import copy
import importlib
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from tests.test_architecture_model import _json_schema, _rules, _system

ROOT = Path(__file__).resolve().parents[1]
ADOPTION_BASE = "25bfbe59ea188d9687b20a9caad19e7db3d031f8"
sys.path.insert(0, str(ROOT / ".grok-stack"))


def _fitness_module():
    try:
        return importlib.import_module("adaptive_grok.architecture_fitness")
    except ModuleNotFoundError as exc:
        if exc.name != "adaptive_grok.architecture_fitness":
            raise
        return None


FIT = _fitness_module()
DIFF = importlib.import_module("adaptive_grok.architecture_diff")


class GitArchitectureRepo:
    def __init__(self, testcase: unittest.TestCase) -> None:
        self._temp = tempfile.TemporaryDirectory()
        testcase.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "architecture@example.test")
        self.git("config", "user.name", "Architecture Test")
        (self.root / "schemas").mkdir()
        for name in ("architecture-system.schema.json", "architecture-rules.schema.json"):
            (self.root / "schemas" / name).write_bytes((ROOT / "schemas" / name).read_bytes())

    def git(self, *args: str) -> str:
        return subprocess.check_output(
            ["git", *args], cwd=self.root, text=True, encoding="utf-8"
        ).strip()

    def write_json(self, relative: str, value: dict) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_text(self, relative: str, value: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    def model(self, system: dict, rules: dict) -> None:
        self.write_json("architecture/system.yaml", system)
        self.write_json("architecture/rules.yaml", rules)

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD")


class ArchitectureFitnessTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        if FIT is None:
            self.fail("adaptive_grok.architecture_fitness is not implemented")

    def _repo(self, *, system: dict | None = None, rules: dict | None = None):
        repo = GitArchitectureRepo(self)
        repo.model(system or _system(), rules or _rules())
        base = repo.commit("base")
        return repo, base

    def _evaluate(self, repo: GitArchitectureRepo, base: str, head: str, pre_risk="green"):
        diff = FIT.diff_architecture(repo.root, base_sha=base, head_sha=head)
        snapshot = FIT.load_architecture(repo.root)
        return FIT.evaluate_fitness(
            repo.root,
            snapshot,
            diff,
            diff.changed_paths,
            pre_risk=pre_risk,
        )

    @staticmethod
    def _results(report):
        return {result.category: result for result in report.results}

    def test_adoption_bootstrap_uses_only_the_frozen_base(self) -> None:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, encoding="utf-8"
        ).strip()
        diff = FIT.diff_architecture(ROOT, base_sha=ADOPTION_BASE, head_sha=head)
        self.assertTrue(diff.baseline_introduced)
        self.assertEqual(diff.base_sha, ADOPTION_BASE)
        self.assertEqual(diff.head_sha, head)
        self.assertIn(("node", "NODE-LOCAL-ROUTE-POLICY", "added"), {
            (change.kind, change.id, change.change) for change in diff.changes
        })

        repo = GitArchitectureRepo(self)
        repo.write_text("README.md", "before architecture\n")
        absent = repo.commit("absent")
        repo.model(_system(), _rules())
        adopted = repo.commit("adopt")
        with self.assertRaisesRegex(FIT.ArchitectureError, "adoption|missing"):
            FIT.diff_architecture(repo.root, base_sha=absent, head_sha=adopted)

    def test_exact_commits_are_required_and_route_base_is_never_inferred(self) -> None:
        repo, base = self._repo()
        repo.write_text("src/app.py", "VALUE = 1\n")
        head = repo.commit("head")
        for label, bad_base, bad_head in (
            ("symbolic base", "HEAD~1", head),
            ("abbreviated base", base[:12], head),
            ("symbolic head", base, "HEAD"),
            ("missing", "0" * 40, head),
        ):
            with self.subTest(label=label), self.assertRaises(FIT.ArchitectureError):
                FIT.diff_architecture(repo.root, base_sha=bad_base, head_sha=bad_head)

    def test_exact_git_objects_ignore_replacement_refs(self) -> None:
        system = _system()
        repo, base = self._repo(system=system)
        original = copy.deepcopy(system)
        original["nodes"][0]["owner"] = "original-owner"
        repo.model(original, _rules())
        head = repo.commit("original head")

        replacement = copy.deepcopy(original)
        replacement["nodes"][0]["owner"] = "replacement-owner"
        repo.model(replacement, _rules())
        repo.write_text("src/evil.py", "VALUE = 'replacement'\n")
        repo.git("add", "-A")
        tree = repo.git("write-tree")
        replacement_commit = subprocess.check_output(
            ["git", "commit-tree", tree, "-p", base],
            cwd=repo.root,
            input="replacement\n",
            text=True,
            encoding="utf-8",
        ).strip()
        repo.git("replace", head, replacement_commit)

        diff = FIT.diff_architecture(repo.root, base_sha=base, head_sha=head)
        analyzed = {node["id"]: node for node in diff._head_state.snapshot.system["nodes"]}
        self.assertEqual(diff.head_sha, head)
        self.assertEqual(analyzed["NODE-A"]["owner"], "original-owner")
        self.assertNotIn("src/evil.py", diff.changed_paths)

    def test_git_changed_paths_are_nul_safe_and_deterministic(self) -> None:
        repo, base = self._repo()
        repo.write_text("odd\nname.py", "VALUE = 1\n")
        repo.write_text("tab\tname.py", "VALUE = 2\n")
        head = repo.commit("odd paths")
        first = FIT.diff_architecture(repo.root, base_sha=base, head_sha=head)
        second = FIT.diff_architecture(repo.root, base_sha=base, head_sha=head)
        self.assertEqual(first.changed_paths, ("odd\nname.py", "tab\tname.py"))
        self.assertEqual(first.digest, second.digest)

    def test_worktree_diff_binds_untracked_content_and_line_counts(self) -> None:
        repo, base = self._repo()
        repo.write_text("odd\nworktree.py", "VALUE = 1\n")
        first = FIT.diff_architecture(repo.root, base_sha=base, worktree=True)
        artifact = next(item for item in first.artifacts if item.path == "odd\nworktree.py")
        self.assertEqual(first.head_kind, "worktree")
        self.assertIsNone(first.head_sha)
        self.assertEqual(artifact.status, "added")
        self.assertEqual(artifact.added_lines, 1)
        repo.write_text("odd\nworktree.py", "VALUE = 2\nOTHER = 3\n")
        second = FIT.diff_architecture(repo.root, base_sha=base, worktree=True)
        self.assertNotEqual(first.repository_inventory_digest, second.repository_inventory_digest)

    def test_semantic_diff_records_are_sorted_typed_and_digest_bound(self) -> None:
        system = _system()
        repo, base = self._repo(system=system)
        changed = copy.deepcopy(system)
        changed["nodes"][0]["owner"] = "platform"
        changed["nodes"][0]["runtime"]["lifecycle"] = "long_running"
        changed["edges"].append(
            {
                **copy.deepcopy(changed["edges"][0]),
                "id": "EDGE-B-A",
                "from": "NODE-B",
                "to": "NODE-A",
            }
        )
        repo.model(changed, _rules())
        head = repo.commit("semantic changes")
        diff = FIT.diff_architecture(repo.root, base_sha=base, head_sha=head)
        self.assertEqual(
            [(item.kind, item.id, item.change) for item in diff.changes],
            [
                ("edge", "EDGE-B-A", "added"),
                ("node", "NODE-A", "changed"),
                ("runtime", "NODE-A", "changed"),
            ],
        )
        self.assertRegex(diff.digest, r"^[0-9a-f]{64}$")

    def test_semantic_diff_covers_trust_signal_top_level_and_contract_metadata(self) -> None:
        system = _system()
        system["contracts"] = [{
            "id": "CONTRACT-TEST",
            "kind": "json_schema",
            "path": "engineering/contracts/test.json",
            "version": "1",
            "role": "consumer",
            "compatibility": "consumer_accepts_old",
        }]
        system["nodes"][0]["public_contracts"] = ["CONTRACT-TEST"]
        rules = _rules()
        rules["contract_policies"] = [{
            "id": "FIT-CONTRACT",
            "contract_kinds": ["json_schema"],
            "compatibility": "consumer_accepts_old",
            "severity": "error",
        }]
        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        repo.write_json("engineering/contracts/test.json", _json_schema({"id": {"type": "string"}}))
        base = repo.commit("semantic base")

        changed = copy.deepcopy(system)
        changed["architecture_id"] = "ARCH-TEST-V2"
        changed["trust_domains"][0]["owner"] = "security"
        changed["signals"][0]["description"] = "changed observable meaning"
        changed["contracts"][0].update(
            version="2", role="bidirectional", compatibility="exact"
        )
        changed_rules = copy.deepcopy(rules)
        changed_rules["architecture_id"] = "ARCH-TEST-V2"
        repo.model(changed, changed_rules)
        head = repo.commit("all authority metadata")
        diff = FIT.diff_architecture(repo.root, base_sha=base, head_sha=head)
        changes = {(item.kind, item.id, item.change) for item in diff.changes}
        self.assertTrue(
            {
                ("contract", "CONTRACT-TEST", "changed"),
                ("signal", "SIG-EDGE-FAILURE", "changed"),
                ("trust_domain", "TD-LOCAL", "changed"),
                ("system", "ARCHITECTURE", "changed"),
                ("rules", "ARCHITECTURE", "changed"),
            }
            <= changes
        )
        report = self._evaluate(repo, base, head)
        contract_result = self._results(report)["contract_compatibility"]
        self.assertNotEqual(contract_result.status, "not_applicable")
        self.assertEqual(report.exemption_state, "revoked")
        self.assertIn("architecture", report.required_scopes)

    def test_all_mandatory_categories_emit_typed_applicability(self) -> None:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, encoding="utf-8"
        ).strip()
        diff = FIT.diff_architecture(ROOT, base_sha=ADOPTION_BASE, head_sha=head)
        report = FIT.evaluate_fitness(
            ROOT,
            FIT.load_architecture(ROOT),
            diff,
            diff.changed_paths,
            pre_risk="yellow",
        )
        expected = {
            "background_job",
            "change_separation",
            "code_budget",
            "contract_compatibility",
            "forbidden_edge",
            "migration_safety",
            "module_boundary",
            "network_client",
            "production_import",
            "secret_flow",
            "tenant_authorization",
            "workspace_trust",
        }
        self.assertEqual({item.category for item in report.results}, expected)
        for result in report.results:
            self.assertIn(result.status, {"pass", "fail", "not_applicable", "unsupported"})
            self.assertTrue(result.applicability.predicate)
            self.assertRegex(result.applicability.inventory_digest, r"^[0-9a-f]{64}$")
            if result.status == "not_applicable":
                self.assertTrue(result.applicability.reason_code)
                self.assertIsInstance(result.applicability.scanned_scope, tuple)
        self.assertEqual(self._results(report)["code_budget"].status, "pass")
        self.assertEqual(self._results(report)["change_separation"].status, "pass")
        self.assertEqual(report.status, "pass")
        self.assertFalse(any(path == "trust-ci" or path.startswith("trust-ci/") for path in diff.changed_paths))

    def test_model_rule_categories_fail_on_real_semantic_violations(self) -> None:
        cases = []

        rules = _rules()
        rules["forbidden_edges"] = [{
            "id": "FIT-FORBID",
            "from_trust_domains": ["TD-LOCAL"],
            "to_trust_domains": ["TD-LOCAL"],
            "edge_types": ["dependency"],
            "severity": "error",
        }]
        cases.append((
            "forbidden_edge",
            _system(),
            rules,
            lambda system: system["nodes"][0].update(owner="platform"),
        ))

        tenant_rules = _rules()
        tenant_rules["tenant_authorization_policies"] = [{
            "id": "FIT-AUTH",
            "data_classifications": ["DATA-INTERNAL"],
            "require_tenant_filter": False,
            "require_authorization": True,
            "severity": "error",
        }]
        cases.append((
            "tenant_authorization",
            _system(),
            tenant_rules,
            lambda system: system["edges"][0].update(authentication="none"),
        ))

        background_system = _system()
        background_system["nodes"][0]["type"] = "worker"
        background_system["edges"][0]["sync_or_async"] = "asynchronous"
        background_rules = _rules()
        background_rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        cases.append((
            "background_job",
            background_system,
            background_rules,
            lambda system: system["edges"][0]["failure_behavior"].update(
                max_retries=4,
                idempotency="not_required",
                correlation_id="not_required",
                terminal_action="reject",
            ),
        ))

        secret_system = _system()
        secret_system["secret_classes"] = [
            {"id": "SECRET-TEST", "classification": "trust_material"}
        ]
        secret_rules = _rules()
        secret_rules["secret_flow_policies"] = [{
            "id": "FIT-SECRETS",
            "secret_classes": ["SECRET-TEST"],
            "allowed_trust_domains": ["TD-OTHER"],
            "severity": "error",
        }]
        secret_system["trust_domains"].append(
            {"id": "TD-OTHER", "kind": "trust_ci_control", "owner": "security"}
        )
        cases.append((
            "secret_flow",
            secret_system,
            secret_rules,
            lambda system: system["nodes"][0]["secrets"].append("SECRET-TEST"),
        ))

        workspace_system = copy.deepcopy(secret_system)
        workspace_system["nodes"][1]["type"] = "runner"
        workspace_rules = _rules()
        workspace_rules["workspace_trust_policies"] = [{
            "id": "FIT-WORKSPACE",
            "node_types": ["runner"],
            "forbidden_secret_classes": ["SECRET-TEST"],
            "severity": "error",
        }]
        cases.append((
            "workspace_trust",
            workspace_system,
            workspace_rules,
            lambda system: system["nodes"][1]["secrets"].append("SECRET-TEST"),
        ))

        for category, system, rules, mutate in cases:
            with self.subTest(category=category):
                repo, base = self._repo(system=system, rules=rules)
                changed = copy.deepcopy(system)
                mutate(changed)
                repo.model(changed, rules)
                head = repo.commit(category)
                result = self._results(self._evaluate(repo, base, head))[category]
                self.assertEqual(result.status, "fail")
                self.assertTrue(result.findings)

    def test_source_analyzers_reject_boundaries_network_and_production_imports(self) -> None:
        cases = (
            (
                "module_boundary",
                {
                    "path_boundaries": [{
                        "id": "FIT-MODULE",
                        "source_prefixes": ["src"],
                        "forbidden_dependency_prefixes": ["trust-ci"],
                        "severity": "error",
                    }]
                },
                "import adaptive_trust_ci.policy\n",
            ),
            (
                "network_client",
                {
                    "network_policies": [{
                        "id": "FIT-NETWORK",
                        "node_types": ["service"],
                        "allowed_protocols": ["https"],
                        "require_declared_edge": True,
                        "severity": "error",
                    }]
                },
                "import requests\nrequests.get('https://example.test')\n",
            ),
            ("production_import", {}, "from tests import helpers\n"),
        )
        for category, rule_update, source in cases:
            with self.subTest(category=category):
                system = _system()
                system["nodes"][0]["type"] = "service"
                system["nodes"][0]["repository_paths"] = ["src"]
                rules = _rules()
                rules.update(rule_update)
                repo, base = self._repo(system=system, rules=rules)
                repo.write_text("src/app.py", source)
                head = repo.commit(category)
                result = self._results(self._evaluate(repo, base, head))[category]
                self.assertEqual(result.status, "fail")
                self.assertTrue(result.findings)

    def test_network_analysis_handles_stdlib_unowned_and_unknown_clients(self) -> None:
        cases = (
            (
                "owned http.client",
                "src/client.py",
                "import http.client\nhttp.client.HTTPSConnection('example.test')\n",
                "fail",
            ),
            (
                "unowned urllib",
                "unowned/client.py",
                "import urllib.request\nurllib.request.urlopen('https://example.test')\n",
                "fail",
            ),
            (
                "unknown external client",
                "src/client.py",
                "import mystery_http\nmystery_http.connect('example.test')\n",
                "unsupported",
            ),
        )
        for label, path, source, expected in cases:
            with self.subTest(label=label):
                system = _system()
                system["nodes"][0]["type"] = "service"
                system["nodes"][0]["repository_paths"] = ["src"]
                rules = _rules()
                rules["network_policies"] = [{
                    "id": "FIT-NETWORK",
                    "node_types": ["service"],
                    "allowed_protocols": ["https"],
                    "require_declared_edge": True,
                    "severity": "error",
                }]
                repo, base = self._repo(system=system, rules=rules)
                repo.write_text(path, source)
                head = repo.commit(label)
                report = self._evaluate(repo, base, head)
                result = self._results(report)["network_client"]
                self.assertEqual(result.status, expected)
                self.assertEqual(report.status, "fail")
                self.assertIn("new_network_client", report.triggers)

    def test_change_separation_rejects_product_and_trust_ci_mixing(self) -> None:
        rules = _rules()
        rules["change_separation_policies"] = [{
            "id": "FIT-SEPARATION",
            "implementation_prefixes": ["src"],
            "trust_ci_prefixes": ["trust-ci"],
            "severity": "error",
        }]
        repo, base = self._repo(rules=rules)
        repo.write_text("src/app.py", "VALUE = 1\n")
        repo.write_text("trust-ci/policy.py", "VALUE = 2\n")
        head = repo.commit("mixed")
        result = self._results(self._evaluate(repo, base, head))["change_separation"]
        self.assertEqual(result.status, "fail")
        self.assertIn("FIT-SEPARATION", result.rule_ids)

    def test_changed_code_budget_counts_bytes_lines_and_ast_complexity(self) -> None:
        metrics = (
            ("max_changed_bytes", 8, "VALUE = 'too large'\n"),
            ("max_changed_lines", 1, "VALUE = 1\nOTHER = 2\n"),
            ("max_ast_complexity", 1, "if True:\n    VALUE = 1\nif False:\n    VALUE = 2\n"),
        )
        for field, limit, source in metrics:
            with self.subTest(metric=field):
                rules = _rules()
                budget = {
                    "id": "FIT-BUDGET",
                    "path_prefixes": ["src"],
                    "max_changed_bytes": 1000,
                    "max_changed_lines": 100,
                    "max_ast_complexity": 100,
                    "severity": "error",
                }
                budget[field] = limit
                rules["code_budgets"] = [budget]
                repo, base = self._repo(rules=rules)
                repo.write_text("src/app.py", source)
                head = repo.commit(field)
                result = self._results(self._evaluate(repo, base, head))["code_budget"]
                self.assertEqual(result.status, "fail")
                self.assertTrue(any(field in finding for finding in result.findings))

    def test_contract_compatibility_rejects_directional_break(self) -> None:
        system = _system()
        system["contracts"] = [{
            "id": "CONTRACT-TEST",
            "kind": "json_schema",
            "path": "engineering/contracts/test.json",
            "version": "1",
            "role": "consumer",
            "compatibility": "consumer_accepts_old",
        }]
        system["nodes"][0]["public_contracts"] = ["CONTRACT-TEST"]
        rules = _rules()
        rules["contract_policies"] = [{
            "id": "FIT-CONTRACT",
            "contract_kinds": ["json_schema"],
            "compatibility": "consumer_accepts_old",
            "severity": "error",
        }]
        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        repo.write_json(
            "engineering/contracts/test.json",
            _json_schema({"id": {"type": "string"}}, ["id"]),
        )
        base = repo.commit("contract base")
        repo.write_json("engineering/contracts/test.json", _json_schema({}))
        head = repo.commit("contract break")
        result = self._results(self._evaluate(repo, base, head))["contract_compatibility"]
        self.assertEqual(result.status, "fail")
        self.assertIn("CONTRACT-TEST", " ".join(result.findings))

    def test_migration_history_and_required_phases_fail_closed(self) -> None:
        rules = _rules()
        rules["migration_policies"] = [{
            "id": "FIT-MIGRATION",
            "path_prefixes": ["migrations"],
            "required_phases": ["expand", "migrate", "contract"],
            "immutable_history": True,
            "severity": "error",
        }]
        repo, base = self._repo(rules=rules)
        repo.write_text("migrations/001_expand.sql", "CREATE TABLE item(id integer);\n")
        head = repo.commit("incomplete migration")
        result = self._results(self._evaluate(repo, base, head))["migration_safety"]
        self.assertEqual(result.status, "fail")
        self.assertIn("missing phases", " ".join(result.findings))

        repo.write_text(
            "migrations/001_migrate.sql",
            "-- adaptive-grok: bounded\n-- adaptive-grok: resumable\nUPDATE item SET id = id WHERE id IS NOT NULL;\n",
        )
        repo.write_text("migrations/001_contract.sql", "ALTER TABLE item DROP COLUMN legacy;\n")
        complete = repo.commit("complete migration")
        result = self._results(self._evaluate(repo, head, complete))["migration_safety"]
        self.assertEqual(result.status, "pass")
        repo.write_text("migrations/001_expand.sql", "DROP TABLE item;\n")
        rewritten = repo.commit("rewrite history")
        result = self._results(self._evaluate(repo, complete, rewritten))["migration_safety"]
        self.assertEqual(result.status, "fail")
        self.assertIn("immutable", " ".join(result.findings))

    def test_migration_history_requires_declared_resource_mirror(self) -> None:
        system = _system()
        system["nodes"][0]["repository_paths"] = ["migrations", "package/resources"]
        rules = _rules()
        rules["migration_policies"] = [{
            "id": "FIT-MIGRATION",
            "path_prefixes": ["migrations"],
            "required_phases": ["expand", "migrate", "contract"],
            "immutable_history": True,
            "severity": "error",
        }]
        repo, base = self._repo(system=system, rules=rules)
        repo.write_text("migrations/001_expand.sql", "CREATE TABLE item(id integer);\n")
        repo.write_text("migrations/001_migrate.sql", "UPDATE item SET id = id;\n")
        repo.write_text("migrations/001_contract.sql", "ALTER TABLE item ADD COLUMN done integer;\n")
        head = repo.commit("unmirrored migration")
        result = self._results(self._evaluate(repo, base, head))["migration_safety"]
        self.assertEqual(result.status, "fail")
        self.assertIn("mirror", " ".join(result.findings))

    def test_migration_content_and_versions_are_conservative_for_every_status(self) -> None:
        cases = (
            (
                "not null expand",
                "migrations/001_expand.sql",
                "ALTER TABLE item ADD COLUMN name text NOT NULL;\n",
                "fail",
            ),
            (
                "unbounded migrate",
                "migrations/001_migrate.sql",
                "DELETE FROM item;\n",
                "fail",
            ),
            (
                "unknown migrate safety",
                "migrations/001_migrate.sql",
                "VACUUM item;\n",
                "unsupported",
            ),
            (
                "version gap",
                "migrations/003_expand.sql",
                "CREATE TABLE item(id integer);\n",
                "fail",
            ),
        )
        for label, unsafe_path, unsafe_source, expected in cases:
            with self.subTest(label=label):
                rules = _rules()
                rules["migration_policies"] = [{
                    "id": "FIT-MIGRATION",
                    "path_prefixes": ["migrations"],
                    "required_phases": ["expand", "migrate", "contract"],
                    "immutable_history": False,
                    "severity": "error",
                }]
                repo, base = self._repo(rules=rules)
                version = "003" if "version" in label else "001"
                safe = {
                    f"migrations/{version}_expand.sql": "CREATE TABLE item(id integer);\n",
                    f"migrations/{version}_migrate.sql": (
                        "-- adaptive-grok: bounded\n-- adaptive-grok: resumable\n"
                        "UPDATE item SET id = id WHERE id IS NOT NULL;\n"
                    ),
                    f"migrations/{version}_contract.sql": "ALTER TABLE item DROP COLUMN legacy;\n",
                }
                safe[unsafe_path] = unsafe_source
                for path, source in safe.items():
                    repo.write_text(path, source)
                head = repo.commit(label)
                result = self._results(self._evaluate(repo, base, head))["migration_safety"]
                self.assertEqual(result.status, expected)

        rules = _rules()
        rules["migration_policies"] = [{
            "id": "FIT-MIGRATION",
            "path_prefixes": ["migrations"],
            "required_phases": ["expand", "migrate", "contract"],
            "immutable_history": False,
            "severity": "error",
        }]
        repo = GitArchitectureRepo(self)
        repo.model(_system(), rules)
        for phase, source in (
            ("expand", "CREATE TABLE item(id integer);\n"),
            (
                "migrate",
                "-- adaptive-grok: bounded\n-- adaptive-grok: resumable\n"
                "UPDATE item SET id = id WHERE id IS NOT NULL;\n",
            ),
            ("contract", "ALTER TABLE item DROP COLUMN legacy;\n"),
        ):
            repo.write_text(f"migrations/001_{phase}.sql", source)
        base = repo.commit("safe migration base")
        repo.write_text("migrations/001_migrate.sql", "UPDATE item SET id = id;\n")
        head = repo.commit("modified unsafe migrate")
        result = self._results(self._evaluate(repo, base, head))["migration_safety"]
        self.assertEqual(result.status, "fail")

    def test_unsupported_applicable_source_analysis_fails_the_report(self) -> None:
        rules = _rules()
        rules["path_boundaries"] = [{
            "id": "FIT-MODULE",
            "source_prefixes": ["src"],
            "forbidden_dependency_prefixes": ["trust-ci"],
            "severity": "error",
        }]
        repo, base = self._repo(rules=rules)
        repo.write_text("src/broken.py", "if :\n")
        head = repo.commit("unparseable")
        report = self._evaluate(repo, base, head)
        result = self._results(report)["module_boundary"]
        self.assertEqual(result.status, "unsupported")
        self.assertEqual(report.status, "fail")

    def test_not_applicable_has_auditable_inventory_evidence(self) -> None:
        repo, base = self._repo()
        repo.write_text("docs/guide.md", "documentation only\n")
        head = repo.commit("docs")
        report = self._evaluate(repo, base, head)
        for result in report.results:
            if result.status == "not_applicable":
                self.assertTrue(result.applicability.predicate)
                self.assertTrue(result.applicability.reason_code)
                self.assertIsInstance(result.applicability.scanned_scope, tuple)
                self.assertRegex(result.applicability.inventory_digest, r"^[0-9a-f]{64}$")
        self.assertEqual(report.exemption_state, "eligible")

    def test_not_applicable_binds_declared_and_repository_inventory(self) -> None:
        system = _system()
        system["contracts"] = [{
            "id": "CONTRACT-TEST",
            "kind": "json_schema",
            "path": "engineering/contracts/test.json",
            "version": "1",
            "role": "consumer",
            "compatibility": "consumer_accepts_old",
        }]
        rules = _rules()
        rules["contract_policies"] = [{
            "id": "FIT-CONTRACT",
            "contract_kinds": ["json_schema"],
            "compatibility": "consumer_accepts_old",
            "severity": "error",
        }]
        rules["migration_policies"] = [{
            "id": "FIT-MIGRATION",
            "path_prefixes": ["migrations"],
            "required_phases": ["expand", "migrate", "contract"],
            "immutable_history": True,
            "severity": "error",
        }]
        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        repo.write_json("engineering/contracts/test.json", _json_schema({"id": {"type": "string"}}))
        base = repo.commit("inventory base")
        repo.write_text("docs/one.md", "one\n")
        first_head = repo.commit("first docs")
        first = self._results(self._evaluate(repo, base, first_head))
        repo.write_text("docs/two.md", "two\n")
        second_head = repo.commit("second docs")
        second = self._results(self._evaluate(repo, base, second_head))
        for category, subjects in (
            ("contract_compatibility", {"CONTRACT-TEST", "FIT-CONTRACT"}),
            ("migration_safety", {"migrations", "FIT-MIGRATION"}),
        ):
            self.assertEqual(first[category].status, "not_applicable")
            self.assertTrue(subjects <= set(first[category].applicability.scanned_scope))
            self.assertNotEqual(
                first[category].applicability.inventory_digest,
                second[category].applicability.inventory_digest,
            )

    def test_capped_process_stops_output_and_timeout_producers(self) -> None:
        self.assertTrue(hasattr(DIFF, "_run_capped"), "incremental capped runner is absent")
        for label, code, timeout in (
            (
                "output",
                "import os, pathlib\n"
                "[os.write(1, b'x' * 65536) for _ in range(64)]\n"
                "pathlib.Path(os.environ['SENTINEL']).write_text('completed')\n",
                5.0,
            ),
            (
                "timeout",
                "import os, pathlib, time\n"
                "time.sleep(0.5)\n"
                "pathlib.Path(os.environ['SENTINEL']).write_text('completed')\n",
                0.05,
            ),
        ):
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as directory:
                    sentinel = Path(directory) / "completed"
                    environment = {"SENTINEL": str(sentinel)}
                    started = time.monotonic()
                    with self.assertRaises(FIT.ArchitectureError):
                        DIFF._run_capped(
                            [sys.executable, "-c", code],
                            cwd=Path(directory),
                            env=environment,
                            stdout_limit=1024,
                            stderr_limit=1024,
                            timeout=timeout,
                        )
                    self.assertLess(time.monotonic() - started, 0.4)
                    self.assertFalse(sentinel.exists())

    def test_risk_is_monotonic_and_architecture_expansion_revokes_exemption(self) -> None:
        system = _system()
        rules = _rules()
        rules["risk_escalations"] = [{
            "id": "FIT-EXPANSION",
            "triggers": ["new_edge", "new_service", "new_trust_crossing"],
            "risk": "red",
            "severity": "error",
        }]
        repo, base = self._repo(system=system, rules=rules)
        changed = copy.deepcopy(system)
        changed["nodes"][0]["type"] = "service"
        changed["edges"].append({
            **copy.deepcopy(changed["edges"][0]),
            "id": "EDGE-B-A",
            "from": "NODE-B",
            "to": "NODE-A",
        })
        repo.model(changed, rules)
        head = repo.commit("expand")
        report = self._evaluate(repo, base, head, pre_risk="red")
        self.assertEqual(report.pre_risk, "red")
        self.assertEqual(report.escalation, "red")
        self.assertEqual(report.post_risk, "red")
        self.assertIn("new_edge", report.triggers)
        self.assertIn("new_service", report.triggers)
        self.assertEqual(report.exemption_state, "revoked")
        self.assertIn("architecture", report.required_scopes)

    def test_evidence_core_and_digest_are_deterministic(self) -> None:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, encoding="utf-8"
        ).strip()
        first = FIT.architecture_evidence(
            ROOT, base_sha=ADOPTION_BASE, head_sha=head, pre_risk="yellow"
        )
        second = FIT.architecture_evidence(
            ROOT, base_sha=ADOPTION_BASE, head_sha=head, pre_risk="yellow"
        )
        self.assertEqual(first, second)
        self.assertEqual(first["architecture_contract_version"], 1)
        self.assertEqual(first["exact_base_sha"], ADOPTION_BASE)
        self.assertEqual(first["exact_head_sha"], head)
        self.assertRegex(first["architecture_evidence_digest"], r"^[0-9a-f]{64}$")
        self.assertNotIn("timestamp", first)


if __name__ == "__main__":
    unittest.main()
