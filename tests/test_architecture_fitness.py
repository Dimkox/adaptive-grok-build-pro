from __future__ import annotations

import ast
import copy
import importlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

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
ARCHITECTURE = importlib.import_module("adaptive_grok.architecture")


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

    def write_bytes(self, relative: str, value: bytes) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)

    def model(self, system: dict, rules: dict) -> None:
        self.write_json("architecture/system.yaml", system)
        self.write_json("architecture/rules.yaml", rules)
        self.write_json("architecture/adoption.json", {
            "architecture_id": system["architecture_id"],
            "schema_version": 1,
            "state": "adopted",
        })

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

    def test_exact_and_worktree_diffs_fail_when_adoption_marker_is_removed(self) -> None:
        script = ROOT / "scripts/grok_architecture.py"

        def invoke(repo: GitArchitectureRepo, *args: str):
            return subprocess.run(
                [sys.executable, str(script), "--root", str(repo.root), *args],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        repo, base = self._repo()
        (repo.root / "architecture/adoption.json").unlink()
        removed = repo.commit("remove adoption marker")
        with self.assertRaisesRegex(FIT.ArchitectureError, "adoption marker"):
            FIT.diff_architecture(repo.root, base_sha=base, head_sha=removed)
        for command in ("diff", "fitness"):
            result = invoke(repo, command, "--base", base, "--head", removed, "--json")
            self.assertNotEqual(result.returncode, 0, (command, result.stdout, result.stderr))
            self.assertIn("adoption marker", result.stdout + result.stderr)

        repo.git("reset", "--hard", base)
        (repo.root / "architecture/adoption.json").unlink()
        with self.assertRaisesRegex(FIT.ArchitectureError, "adoption marker"):
            FIT.diff_architecture(repo.root, base_sha=base, worktree=True)
        for command in ("diff", "fitness"):
            result = invoke(repo, command, "--base", base, "--worktree", "--json")
            self.assertNotEqual(result.returncode, 0, (command, result.stdout, result.stderr))
            self.assertIn("adoption marker", result.stdout + result.stderr)

    def test_adoption_marker_state_is_bound_into_exact_diff_evidence(self) -> None:
        repo, base = self._repo()
        repo.write_text("src/app.py", "VALUE = 1\n")
        head = repo.commit("head")
        diff = FIT.diff_architecture(repo.root, base_sha=base, head_sha=head)
        self.assertEqual(diff.base_adoption_state, "adopted")
        self.assertEqual(diff.head_adoption_state, "adopted")
        self.assertRegex(diff.base_adoption_digest, r"^[0-9a-f]{64}$")
        self.assertEqual(diff.base_adoption_digest, diff.head_adoption_digest)
        evidence = FIT.architecture_evidence(
            repo.root, base_sha=base, head_sha=head, pre_risk="green"
        )
        self.assertEqual(evidence["base_adoption_state"], "adopted")
        self.assertEqual(evidence["head_adoption_state"], "adopted")
        self.assertEqual(evidence["base_adoption_digest"], diff.base_adoption_digest)
        self.assertEqual(evidence["head_adoption_digest"], diff.head_adoption_digest)

    def test_invalid_adoption_marker_fails_exact_and_worktree_state(self) -> None:
        repo, base = self._repo()
        repo.write_text(
            "architecture/adoption.json",
            '{"architecture_id":"ARCH-TEST","schema_version":1,"state":"adopted"}\n',
        )
        invalid = repo.commit("noncanonical marker")
        with self.assertRaisesRegex(FIT.ArchitectureError, "canonical"):
            FIT.diff_architecture(repo.root, base_sha=base, head_sha=invalid)
        repo.git("reset", "--hard", base)
        repo.write_text("architecture/adoption.json", "{}\n")
        with self.assertRaisesRegex(FIT.ArchitectureError, "marker fields"):
            FIT.diff_architecture(repo.root, base_sha=base, worktree=True)

    def test_merge_and_shallow_exact_marker_deletions_fail_closed(self) -> None:
        repo, adopted = self._repo()
        repo.git("checkout", "-qb", "side")
        repo.write_text("side.txt", "side\n")
        repo.commit("side")
        repo.git("checkout", "-q", "main")
        (repo.root / "architecture/adoption.json").unlink()
        repo.commit("remove marker")
        repo.git("merge", "--no-edit", "side")
        merge_head = repo.git("rev-parse", "HEAD")
        with self.assertRaisesRegex(FIT.ArchitectureError, "adoption marker"):
            FIT.diff_architecture(repo.root, base_sha=adopted, head_sha=merge_head)

        with tempfile.TemporaryDirectory() as directory:
            clone = Path(directory) / "shallow"
            subprocess.run(
                ["git", "clone", "-q", "--depth=1", f"file://{repo.root}", str(clone)],
                check=True,
            )
            subprocess.run(
                ["git", "fetch", "-q", "--depth=1", "origin", f"{adopted}:refs/architecture/adopted"],
                cwd=clone,
                check=True,
            )
            with self.assertRaisesRegex(FIT.ArchitectureError, "adoption marker"):
                FIT.diff_architecture(clone, base_sha=adopted, head_sha=merge_head)

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

    def test_source_only_queue_signals_fail_background_fitness(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        cases = (
            ("celery alias", "", "import celery as c\napp = c.Celery('jobs')\n"),
            ("rq from import", "", "from rq import Queue as WorkQueue\njobs = WorkQueue()\n"),
            ("stdlib queue", "", "from queue import Queue\njobs = Queue()\n"),
            ("existing import new call", "import celery as c\n", "import celery as c\napp = c.Celery('jobs')\n"),
            (
                "rq instance enqueue",
                "from rq import Queue\njobs = Queue()\n",
                "from rq import Queue\njobs = Queue()\njobs.enqueue(task)\n",
            ),
            (
                "rq multi-hop enqueue",
                "from rq import Queue\njobs = Queue()\nq1 = jobs\nq2 = q1\n",
                "from rq import Queue\njobs = Queue()\nq1 = jobs\nq2 = q1\nq2.enqueue(task)\n",
            ),
            (
                "rq getattr multi-hop enqueue",
                "from rq import Queue\njobs = Queue()\nop = getattr(jobs, 'enqueue')\nalias = op\n",
                "from rq import Queue\njobs = Queue()\nop = getattr(jobs, 'enqueue')\nalias = op\nalias(task)\n",
            ),
            (
                "celery app decorator",
                "import celery\napp = celery.Celery('jobs')\n",
                "import celery\napp = celery.Celery('jobs')\n@app.task\ndef job():\n    return None\n",
            ),
            (
                "aliased factory assignment",
                "import celery as c\nfactory = c.Celery\napp = factory('jobs')\n",
                "import celery as c\nfactory = c.Celery\napp = factory('jobs')\n@app.task\ndef job():\n    return None\n",
            ),
            (
                "getattr factory",
                "import celery\napp = getattr(celery, 'Celery')('jobs')\n",
                "import celery\napp = getattr(celery, 'Celery')('jobs')\n@app.task\ndef job():\n    return None\n",
            ),
            (
                "getattr project adapter",
                "from project.jobs import app\ntask = getattr(app, 'task')\n",
                "from project.jobs import app\ntask = getattr(app, 'task')\n@task\ndef job():\n    return None\n",
            ),
            (
                "project adapter decorator",
                "from project.jobs import app\n",
                "from project.jobs import app\n@app.task\ndef job():\n    return None\n",
            ),
            (
                "multi-hop project adapter decorator",
                "from project.jobs import app\nd1 = app.task\nd2 = d1\n",
                "from project.jobs import app\nd1 = app.task\nd2 = d1\n@d2\ndef job():\n    return None\n",
            ),
        )
        for label, before, after in cases:
            with self.subTest(label=label):
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                if "project adapter" in label:
                    repo.write_text(
                        "project/jobs.py",
                        "import celery\napp = celery.Celery('jobs')\n",
                    )
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", after)
                head = repo.commit("queue source")
                report = self._evaluate(repo, base, head)
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "unsupported")
                self.assertEqual(report.status, "fail")
                self.assertIn("src/jobs.py", result.applicability.scanned_scope)
                self.assertIn("new_queue", report.triggers)

        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        base = repo.commit("base")
        repo.write_text("src/jobs.py", "VALUE = 1\n")
        head = repo.commit("ordinary source")
        report = self._evaluate(repo, base, head)
        self.assertEqual(
            self._results(report)["background_job"].status,
            "not_applicable",
        )
        self.assertNotIn("new_queue", report.triggers)

        no_policy = _rules()
        repo = GitArchitectureRepo(self)
        repo.model(system, no_policy)
        base = repo.commit("base")
        repo.write_text("src/jobs.py", "from rq import Queue\njobs = Queue()\n")
        head = repo.commit("unconfigured queue")
        report = self._evaluate(repo, base, head)
        self.assertEqual(
            self._results(report)["background_job"].status,
            "unsupported",
        )
        self.assertEqual(report.status, "fail")

    def test_owner_resolution_rejects_equal_specificity_ties(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "service"
        system["nodes"][0]["repository_paths"] = ["src"]
        system["nodes"][1]["repository_paths"] = ["other"]
        repo, _ = self._repo(system=system)
        snapshot = FIT.load_architecture(repo.root)
        snapshot.system["nodes"][1]["repository_paths"] = ["src"]
        with self.assertRaisesRegex(FIT.ArchitectureError, "ambiguous repository owner"):
            FIT._owner_for_path(snapshot, "src/client.py")

    def test_network_fitness_uses_the_unique_most_specific_owner(self) -> None:
        system = _system()
        system["nodes"][0]["repository_paths"] = ["src"]
        system["nodes"][1]["type"] = "service"
        system["nodes"][1]["repository_paths"] = ["src/network"]
        rules = _rules()
        rules["network_policies"] = [{
            "id": "FIT-NETWORK",
            "node_types": ["service"],
            "allowed_protocols": ["https"],
            "require_declared_edge": True,
            "severity": "error",
        }]
        repo, base = self._repo(system=system, rules=rules)
        repo.write_text("src/network/client.py", "import requests\nrequests.get('https://example.test')\n")
        head = repo.commit("network client")
        result = self._results(self._evaluate(repo, base, head))["network_client"]
        self.assertEqual(result.status, "fail")
        self.assertTrue(any("NODE-B" in finding for finding in result.findings))

    def test_queue_provenance_covers_wildcards_and_structured_assignments(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        cases = (
            (
                "celery wildcard",
                "from celery import *\n",
                "@shared_task\ndef job():\n    return None\n",
            ),
            (
                "tuple unpack",
                "import celery\napps = (celery.Celery('a'), celery.Celery('b'))\n"
                "app, backup = apps\n",
                "@app.task\ndef job():\n    return None\n",
            ),
            (
                "list unpack rq",
                "from rq import Queue\nqueues = [Queue(), Queue()]\n"
                "jobs, backup = queues\n",
                "jobs.enqueue(task)\n",
            ),
            (
                "subscript derived",
                "import celery\napps = [celery.Celery('a')]\napp = apps[0]\n",
                "@app.task\ndef job():\n    return None\n",
            ),
            (
                "annotated derived",
                "import celery\napp: object = celery.Celery('a')\n",
                "@app.task\ndef job():\n    return None\n",
            ),
            (
                "chained derived",
                "import celery\napp = backup = celery.Celery('a')\n",
                "@app.task\ndef job():\n    return None\n",
            ),
            (
                "starred unpack",
                "import celery\napps = [celery.Celery('a')]\napp, *rest = apps\n",
                "@app.task\ndef job():\n    return None\n",
            ),
        )
        for label, before, addition in cases:
            with self.subTest(label=label):
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", before + addition)
                head = repo.commit("queue operation")
                report = self._evaluate(repo, base, head, pre_risk="green")
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "unsupported")
                self.assertEqual(report.status, "fail")
                self.assertIn("src/jobs.py", result.applicability.scanned_scope)
                self.assertIn("new_queue", report.triggers)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        before = (
            "class Pipeline:\n"
            "    def task(self, function):\n"
            "        return function\n"
            "pipelines = [Pipeline()]\n"
            "pipeline = pipelines[0]\n"
        )
        repo.write_text("src/jobs.py", before)
        base = repo.commit("ordinary base")
        repo.write_text("src/jobs.py", before + "@pipeline.task\ndef stage():\n    return None\n")
        head = repo.commit("ordinary decorator")
        report = self._evaluate(repo, base, head, pre_risk="yellow")
        self.assertEqual(
            self._results(report)["background_job"].status,
            "not_applicable",
        )
        self.assertNotIn("new_queue", report.triggers)

    def test_queue_provenance_is_operation_and_element_specific(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        positives = (
            (
                "wildcard celery decorator alias",
                "from celery import *\ndecorator = shared_task\n",
                "@decorator\ndef job():\n    return None\n",
            ),
            (
                "wildcard celery factory alias",
                "from celery import *\nfactory = Celery\napp = factory('jobs')\n",
                "@app.task\ndef job():\n    return None\n",
            ),
            (
                "wildcard rq factory alias",
                "from rq import *\nfactory = Queue\njobs = factory()\n",
                "jobs.enqueue(task)\n",
            ),
            (
                "ambiguous mixed subscript",
                "import celery\n"
                "class Pipeline:\n    def task(self, fn):\n        return fn\n"
                "values = [celery.Celery('jobs'), Pipeline()]\n"
                "receiver = values[index]\n",
                "@receiver.task\ndef stage():\n    return None\n",
            ),
        )
        for label, before, addition in positives:
            with self.subTest(label=label):
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", before + addition)
                head = repo.commit("queue operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "unsupported")
                self.assertEqual(report.status, "fail")
                self.assertIn("src/jobs.py", result.applicability.scanned_scope)
                self.assertIn("new_queue", report.triggers)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

        negatives = (
            (
                "wildcard unrelated receiver",
                "from celery import *\n"
                "class Pipeline:\n    def task(self, fn):\n        return fn\n"
                "pipeline = Pipeline()\n",
                "@pipeline.task\ndef stage():\n    return None\n",
            ),
            (
                "tuple sibling",
                "import celery\n"
                "class Pipeline:\n    def task(self, fn):\n        return fn\n"
                "app, pipeline = (celery.Celery('jobs'), Pipeline())\n",
                "@pipeline.task\ndef stage():\n    return None\n",
            ),
            (
                "list subscript sibling",
                "import celery\n"
                "class Pipeline:\n    def task(self, fn):\n        return fn\n"
                "values = [celery.Celery('jobs'), Pipeline()]\n"
                "pipeline = values[1]\n",
                "@pipeline.task\ndef stage():\n    return None\n",
            ),
            (
                "dict key sibling",
                "import celery\n"
                "class Pipeline:\n    def task(self, fn):\n        return fn\n"
                "values = {'queue': celery.Celery('jobs'), 'pipeline': Pipeline()}\n"
                "pipeline = values['pipeline']\n",
                "@pipeline.task\ndef stage():\n    return None\n",
            ),
        )
        for label, before, addition in negatives:
            with self.subTest(label=label):
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", before + addition)
                head = repo.commit("ordinary operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "not_applicable")
                self.assertEqual(report.status, "pass")
                self.assertNotIn("new_queue", report.triggers)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

    def test_queue_control_flow_and_python_equal_keys_fail_closed(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        pipeline = (
            "class Pipeline:\n"
            "    def task(self, function):\n"
            "        return function\n\n"
        )
        cases = (
            (
                "queue branch first",
                pipeline
                + "import celery\n"
                + "if enabled:\n"
                + "    receiver = celery.Celery('jobs')\n"
                + "else:\n"
                + "    receiver = Pipeline()\n",
            ),
            (
                "queue branch second",
                pipeline
                + "import celery\n"
                + "if enabled:\n"
                + "    receiver = Pipeline()\n"
                + "else:\n"
                + "    receiver = celery.Celery('jobs')\n",
            ),
            (
                "bool key then integer key",
                pipeline
                + "import celery\n"
                + "values = {True: Pipeline(), 1: celery.Celery('jobs')}\n"
                + "receiver = values[True]\n",
            ),
            (
                "integer key then bool key",
                pipeline
                + "import celery\n"
                + "values = {1: Pipeline(), True: celery.Celery('jobs')}\n"
                + "receiver = values[1]\n",
            ),
        )
        addition = "@receiver.task\ndef stage():\n    return None\n"
        for label, before in cases:
            with self.subTest(label=label):
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", before + addition)
                head = repo.commit("queue operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "unsupported")
                self.assertEqual(report.status, "fail")
                self.assertIn("src/jobs.py", result.applicability.scanned_scope)
                self.assertIn("new_queue", report.triggers)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

    def test_queue_container_mutations_and_signed_selections(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        pipeline = (
            "class Pipeline:\n"
            "    def task(self, function):\n"
            "        return function\n"
            "    def enqueue(self, function):\n"
            "        return function\n\n"
        )
        operations = (
            ("append", "values = []\nvalues.append({queue})\nreceiver = values[0]\n"),
            (
                "extend",
                "values = []\nvalues.extend([Pipeline(), {queue}])\n"
                "receiver = values[1]\n",
            ),
            (
                "subscript assignment",
                "values = [Pipeline()]\nvalues[0] = {queue}\nreceiver = values[0]\n",
            ),
            (
                "list concatenation",
                "values = [Pipeline()] + [{queue}]\nreceiver = values[1]\n",
            ),
            (
                "tuple concatenation",
                "values = (Pipeline(),) + ({queue},)\nreceiver = values[1]\n",
            ),
        )
        frameworks = (
            (
                "celery",
                "import celery\n",
                "celery.Celery('jobs')",
                "@receiver.task\ndef stage():\n    return None\n",
            ),
            (
                "rq",
                "from rq import Queue\n",
                "Queue()",
                "receiver.enqueue(task)\n",
            ),
        )
        for framework, imported, queue_value, addition in frameworks:
            for operation, source in operations:
                with self.subTest(framework=framework, operation=operation):
                    before = pipeline + imported + source.format(queue=queue_value)
                    repo = GitArchitectureRepo(self)
                    repo.model(system, rules)
                    repo.write_text("src/jobs.py", before)
                    base = repo.commit("base")
                    repo.write_text("src/jobs.py", before + addition)
                    head = repo.commit("queue operation")
                    report = self._evaluate(repo, base, head, pre_risk="yellow")
                    result = self._results(report)["background_job"]
                    self.assertEqual(result.status, "unsupported")
                    self.assertEqual(report.status, "fail")
                    self.assertIn("src/jobs.py", result.applicability.scanned_scope)
                    self.assertIn("new_queue", report.triggers)
                    self.assertGreaterEqual(
                        FIT.RISK_ORDER[report.post_risk],
                        FIT.RISK_ORDER[report.pre_risk],
                    )

        controls = (
            (
                "negative list index",
                "from rq import Queue\nvalues = [Queue(), Pipeline()]\n"
                "receiver = values[-1]\n",
            ),
            (
                "negative tuple index",
                "import celery\nvalues = (celery.Celery('jobs'), Pipeline())\n"
                "receiver = values[-1]\n",
            ),
            (
                "negative integer mapping key",
                "from rq import Queue\nvalues = {-1: Pipeline(), 0: Queue()}\n"
                "receiver = values[-1]\n",
            ),
        )
        addition = "@receiver.task\ndef stage():\n    return None\n"
        for label, source in controls:
            with self.subTest(label=label):
                before = pipeline + source
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", before + addition)
                head = repo.commit("ordinary operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "not_applicable")
                self.assertEqual(report.status, "pass")
                self.assertNotIn("new_queue", report.triggers)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

    def test_queue_operations_keep_operation_site_and_lexical_provenance(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        pipeline = (
            "class Pipeline:\n"
            "    def task(self, function):\n"
            "        return function\n\n"
        )
        cases = (
            (
                "operation before overwrite",
                pipeline
                + "import celery\n"
                + "receiver = celery.Celery('jobs')\n"
                + "receiver = Pipeline()\n",
                pipeline
                + "import celery\n"
                + "receiver = celery.Celery('jobs')\n"
                + "receiver.delay(task)\n"
                + "receiver = Pipeline()\n",
            ),
            (
                "function local decorator",
                pipeline
                + "import celery\n"
                + "def configure():\n"
                + "    receiver = celery.Celery('jobs')\n"
                + "    def stage():\n"
                + "        return None\n",
                pipeline
                + "import celery\n"
                + "def configure():\n"
                + "    receiver = celery.Celery('jobs')\n"
                + "    @receiver.task\n"
                + "    def stage():\n"
                + "        return None\n",
            ),
            (
                "method local decorator",
                pipeline
                + "import celery\n"
                + "class Configurer:\n"
                + "    def configure(self):\n"
                + "        receiver = celery.Celery('jobs')\n"
                + "        def stage():\n"
                + "            return None\n",
                pipeline
                + "import celery\n"
                + "class Configurer:\n"
                + "    def configure(self):\n"
                + "        receiver = celery.Celery('jobs')\n"
                + "        @receiver.task\n"
                + "        def stage():\n"
                + "            return None\n",
            ),
        )
        for label, before, after in cases:
            with self.subTest(label=label):
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", after)
                head = repo.commit("queue operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "unsupported")
                self.assertEqual(report.status, "fail")
                self.assertIn("src/jobs.py", result.applicability.scanned_scope)
                self.assertIn("new_queue", report.triggers)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

    def test_queue_alias_mutations_propagate_without_tainting_unrelated_aliases(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        pipeline = (
            "class Pipeline:\n"
            "    def task(self, function):\n"
            "        return function\n"
            "    def enqueue(self, function):\n"
            "        return function\n\n"
        )
        frameworks = (
            (
                "celery",
                "import celery\n",
                "celery.Celery('jobs')",
                "@receiver.task\ndef stage():\n    return None\n",
            ),
            (
                "rq",
                "from rq import Queue\n",
                "Queue()",
                "receiver.enqueue(task)\n",
            ),
        )
        mutations = (
            (
                "alias append",
                "values = []\nalias = values\nalias.append({queue})\n"
                "receiver = values[0]\n",
            ),
            (
                "alias subscript store",
                "values = [Pipeline()]\nalias = values\nalias[0] = {queue}\n"
                "receiver = values[0]\n",
            ),
            (
                "unsupported alias mutator",
                "values = []\nalias = values\nalias.insert(0, {queue})\n"
                "receiver = values[0]\n",
            ),
        )
        for framework, imported, queue_value, addition in frameworks:
            for mutation, source in mutations:
                with self.subTest(framework=framework, mutation=mutation):
                    before = pipeline + imported + source.format(queue=queue_value)
                    repo = GitArchitectureRepo(self)
                    repo.model(system, rules)
                    repo.write_text("src/jobs.py", before)
                    base = repo.commit("base")
                    repo.write_text("src/jobs.py", before + addition)
                    head = repo.commit("queue operation")
                    report = self._evaluate(repo, base, head, pre_risk="yellow")
                    result = self._results(report)["background_job"]
                    self.assertEqual(result.status, "unsupported")
                    self.assertEqual(report.status, "fail")
                    self.assertIn("src/jobs.py", result.applicability.scanned_scope)
                    self.assertIn("new_queue", report.triggers)
                    self.assertGreaterEqual(
                        FIT.RISK_ORDER[report.post_risk],
                        FIT.RISK_ORDER[report.pre_risk],
                    )

        before = (
            pipeline
            + "from rq import Queue\n"
            + "queue_values = [Queue()]\n"
            + "ordinary_values = [Pipeline()]\n"
            + "alias = ordinary_values\n"
            + "queue_values.insert(0, Queue())\n"
            + "receiver = alias[0]\n"
        )
        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        repo.write_text("src/jobs.py", before)
        base = repo.commit("base")
        repo.write_text(
            "src/jobs.py",
            before + "@receiver.task\ndef stage():\n    return None\n",
        )
        head = repo.commit("ordinary aliased operation")
        report = self._evaluate(repo, base, head, pre_risk="yellow")
        result = self._results(report)["background_job"]
        self.assertEqual(result.status, "not_applicable")
        self.assertEqual(report.status, "pass")
        self.assertNotIn("new_queue", report.triggers)
        self.assertGreaterEqual(
            FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
        )

    def test_queue_free_names_join_bounded_module_flow(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        pipeline = (
            "class Pipeline:\n"
            "    def delay(self, task):\n"
            "        return task\n\n"
            "import celery\n"
        )
        cases = (
            (
                "function queue rebound after definition before call",
                "receiver = Pipeline()\n"
                "def configure():\n"
                "    return None\n"
                "receiver = celery.Celery('jobs')\n"
                "configure()\n",
                "receiver = Pipeline()\n"
                "def configure():\n"
                "    receiver.delay(task)\n"
                "receiver = celery.Celery('jobs')\n"
                "configure()\n",
            ),
            (
                "function queue rebound before definition and ordinary after call",
                "receiver = celery.Celery('jobs')\n"
                "def configure():\n"
                "    return None\n"
                "configure()\n"
                "receiver = Pipeline()\n",
                "receiver = celery.Celery('jobs')\n"
                "def configure():\n"
                "    receiver.delay(task)\n"
                "configure()\n"
                "receiver = Pipeline()\n",
            ),
            (
                "method queue rebound after definition before call",
                "receiver = Pipeline()\n"
                "class Configurer:\n"
                "    def configure(self):\n"
                "        return None\n"
                "receiver = celery.Celery('jobs')\n"
                "Configurer().configure()\n",
                "receiver = Pipeline()\n"
                "class Configurer:\n"
                "    def configure(self):\n"
                "        receiver.delay(task)\n"
                "receiver = celery.Celery('jobs')\n"
                "Configurer().configure()\n",
            ),
            (
                "method queue rebound before definition and ordinary after call",
                "receiver = celery.Celery('jobs')\n"
                "class Configurer:\n"
                "    def configure(self):\n"
                "        return None\n"
                "Configurer().configure()\n"
                "receiver = Pipeline()\n",
                "receiver = celery.Celery('jobs')\n"
                "class Configurer:\n"
                "    def configure(self):\n"
                "        receiver.delay(task)\n"
                "Configurer().configure()\n"
                "receiver = Pipeline()\n",
            ),
        )
        for label, before_body, after_body in cases:
            with self.subTest(label=label):
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text("src/jobs.py", pipeline + before_body)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", pipeline + after_body)
                head = repo.commit("queue operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "unsupported")
                self.assertEqual(report.status, "fail")
                self.assertIn("src/jobs.py", result.applicability.scanned_scope)
                self.assertIn("new_queue", report.triggers)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

    def test_queue_nonlocal_names_resolve_nearest_enclosing_scope(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        pipeline = (
            "class Pipeline:\n"
            "    def delay(self, task):\n"
            "        return task\n"
            "    def enqueue(self, task):\n"
            "        return task\n\n"
        )
        positives = (
            (
                "nested function enclosing binding before definition",
                "import celery\n"
                "receiver = Pipeline()\n"
                "def outer():\n"
                "    receiver = celery.Celery('jobs')\n"
                "    def inner():\n"
                "        nonlocal receiver\n"
                "        {operation}"
                "    inner()\n"
                "outer()\n",
                "receiver.delay(task)\n",
            ),
            (
                "nested function enclosing binding after definition",
                "import celery\n"
                "receiver = Pipeline()\n"
                "def outer():\n"
                "    def inner():\n"
                "        nonlocal receiver\n"
                "        {operation}"
                "    receiver = celery.Celery('jobs')\n"
                "    inner()\n"
                "outer()\n",
                "receiver.delay(task)\n",
            ),
            (
                "method closure enclosing binding before definition",
                "from rq import Queue\n"
                "receiver = Pipeline()\n"
                "class Configurer:\n"
                "    def configure(self):\n"
                "        receiver = Queue()\n"
                "        def inner():\n"
                "            nonlocal receiver\n"
                "            {operation}"
                "        inner()\n"
                "Configurer().configure()\n",
                "receiver.enqueue(task)\n",
            ),
            (
                "method closure enclosing binding after definition",
                "from rq import Queue\n"
                "receiver = Pipeline()\n"
                "class Configurer:\n"
                "    def configure(self):\n"
                "        def inner():\n"
                "            nonlocal receiver\n"
                "            {operation}"
                "        receiver = Queue()\n"
                "        inner()\n"
                "Configurer().configure()\n",
                "receiver.enqueue(task)\n",
            ),
        )
        for label, template, operation in positives:
            with self.subTest(label=label):
                before = pipeline + template.format(operation="return None\n")
                after = pipeline + template.format(operation=operation)
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", after)
                head = repo.commit("nested queue operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "unsupported")
                self.assertEqual(report.status, "fail")
                self.assertIn("src/jobs.py", result.applicability.scanned_scope)
                self.assertIn("new_queue", report.triggers)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

        controls = (
            (
                "nonlocal ordinary enclosing binding beats queue module",
                "import celery\n"
                "receiver = celery.Celery('jobs')\n"
                "def outer():\n"
                "    receiver = Pipeline()\n"
                "    def inner():\n"
                "        nonlocal receiver\n"
                "        {operation}"
                "    inner()\n"
                "outer()\n",
            ),
            (
                "explicit global ordinary module beats queue enclosing binding",
                "import celery\n"
                "receiver = Pipeline()\n"
                "def outer():\n"
                "    receiver = celery.Celery('jobs')\n"
                "    def inner():\n"
                "        global receiver\n"
                "        {operation}"
                "    inner()\n"
                "outer()\n",
            ),
        )
        for label, template in controls:
            with self.subTest(label=label):
                before = pipeline + template.format(operation="return None\n")
                after = pipeline + template.format(operation="receiver.delay(task)\n")
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", after)
                head = repo.commit("ordinary nested operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "not_applicable")
                self.assertEqual(report.status, "pass")
                self.assertNotIn("new_queue", report.triggers)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

    def test_queue_inplace_add_mutates_only_mutable_alias_groups(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        pipeline = (
            "class Pipeline:\n"
            "    def task(self, function):\n"
            "        return function\n"
            "    def enqueue(self, function):\n"
            "        return function\n\n"
        )
        frameworks = (
            (
                "celery",
                "import celery\n",
                "celery.Celery('jobs')",
                "@receiver.task\ndef stage():\n    return None\n",
            ),
            (
                "rq",
                "from rq import Queue\n",
                "Queue()",
                "receiver.enqueue(task)\n",
            ),
        )
        for framework, imported, queue_value, addition in frameworks:
            with self.subTest(framework=framework, mutable="list"):
                before = (
                    pipeline
                    + imported
                    + "values = []\n"
                    + "alias = values\n"
                    + f"alias += [{queue_value}]\n"
                    + "receiver = values[0]\n"
                )
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", before + addition)
                head = repo.commit("queue operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "unsupported")
                self.assertEqual(report.status, "fail")
                self.assertIn("src/jobs.py", result.applicability.scanned_scope)
                self.assertIn("new_queue", report.triggers)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

            with self.subTest(framework=framework, mutable="tuple rebind"):
                before = (
                    pipeline
                    + imported
                    + "values = (Pipeline(),)\n"
                    + "alias = values\n"
                    + f"alias += ({queue_value},)\n"
                    + "receiver = values[0]\n"
                )
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", before + addition)
                head = repo.commit("ordinary tuple operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "not_applicable")
                self.assertEqual(report.status, "pass")
                self.assertNotIn("new_queue", report.triggers)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

        before = (
            pipeline
            + "from rq import Queue\n"
            + "queue_values = [Queue()]\n"
            + "ordinary_values = []\n"
            + "alias = ordinary_values\n"
            + "alias += [Pipeline()]\n"
            + "receiver = ordinary_values[0]\n"
        )
        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        repo.write_text("src/jobs.py", before)
        base = repo.commit("base")
        repo.write_text(
            "src/jobs.py",
            before + "@receiver.task\ndef stage():\n    return None\n",
        )
        head = repo.commit("unrelated alias operation")
        report = self._evaluate(repo, base, head, pre_risk="yellow")
        self.assertEqual(
            self._results(report)["background_job"].status,
            "not_applicable",
        )
        self.assertEqual(report.status, "pass")
        self.assertNotIn("new_queue", report.triggers)

    def test_queue_alias_work_is_bounded_before_branch_closure(self) -> None:
        alias_chain = "\n".join(f"alias{index} = values" for index in range(40))
        with self.assertRaisesRegex(FIT.QueueAnalysisLimit, "alias"):
            FIT.analyze_queue_tree(
                ast.parse("import celery\nvalues = []\n" + alias_chain + "\n"),
                value_limit=32,
            )

        left_aliases = "\n".join(f"left{index} = left" for index in range(10))
        right_aliases = "\n".join(f"right{index} = right" for index in range(10))
        branch_aliases = "\n".join(
            f"    bridge{index} = {'left' if index % 2 == 0 else 'right'}"
            for index in range(10)
        )
        with self.assertRaisesRegex(FIT.QueueAnalysisLimit, "alias"):
            FIT.analyze_queue_tree(
                ast.parse(
                    "import celery\nleft = []\nright = []\n"
                    + left_aliases
                    + "\n"
                    + right_aliases
                    + "\nif enabled:\n"
                    + branch_aliases
                    + "\nelse:\n"
                    + branch_aliases.replace("left", "right")
                    + "\n"
                ),
                value_limit=150,
            )

        ordinary = FIT.analyze_queue_tree(
            ast.parse("values = []\n" + alias_chain + "\nform.submit()\n"),
            value_limit=1,
        )
        self.assertEqual(ordinary.signals, ())
        self.assertFalse(ordinary.uncertain)

    def test_unrelated_semantic_method_names_remain_background_not_applicable(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        cases = (
            (
                "form submit",
                "class Form:\n    def submit(self):\n        return None\nform = Form()\n",
                "form.submit()\n",
            ),
            (
                "timer delay",
                "class Timer:\n    def delay(self):\n        return None\ntimer = Timer()\n",
                "timer.delay()\n",
            ),
            (
                "pipeline task decorator",
                "class Pipeline:\n    def task(self, function):\n        return function\npipeline = Pipeline()\n",
                "@pipeline.task\ndef stage():\n    return None\n",
            ),
            (
                "unresolved project adapter",
                "from project.jobs import app\n",
                "@app.task\ndef stage():\n    return None\n",
            ),
        )
        for label, before, addition in cases:
            with self.subTest(label=label):
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text("src/local.py", before)
                base = repo.commit("base")
                repo.write_text("src/local.py", before + addition)
                head = repo.commit("ordinary local semantics")
                report = self._evaluate(repo, base, head)
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "not_applicable")
                self.assertEqual(report.status, "pass")
                self.assertNotIn("new_queue", report.triggers)
                self.assertEqual(
                    ARCHITECTURE.validate_repository_drift(
                        repo.root, FIT.load_architecture(repo.root)
                    ),
                    (),
                )

    def test_mixed_queue_files_ignore_operations_without_queue_provenance(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["project", "src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        cases = (
            (
                "rq and form",
                "from rq import Queue\njobs = Queue()\n"
                "class Form:\n    def submit(self):\n        return None\nform = Form()\n",
                "form.submit()\n",
            ),
            (
                "celery and timer",
                "import celery\napp = celery.Celery('jobs')\n"
                "class Timer:\n    def delay(self):\n        return None\ntimer = Timer()\n",
                "timer.delay()\n",
            ),
            (
                "adapter and pipeline",
                "from project.jobs import app\n"
                "class Pipeline:\n    def task(self, fn):\n        return fn\npipeline = Pipeline()\n",
                "@pipeline.task\ndef stage():\n    return None\n",
            ),
            (
                "rq and generic call",
                "from rq import Queue\njobs = Queue()\n"
                "def format_value():\n    return 'value'\n",
                "format_value()\n",
            ),
        )
        for label, before, addition in cases:
            with self.subTest(label=label):
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text("project/__init__.py", "")
                if label.startswith("adapter"):
                    repo.write_text(
                        "project/jobs.py",
                        "import celery\napp = celery.Celery('jobs')\n",
                    )
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", before + addition)
                head = repo.commit("ordinary operation")
                report = self._evaluate(repo, base, head)
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "not_applicable")
                self.assertEqual(report.status, "pass")
                self.assertNotIn("new_queue", report.triggers)
                self.assertEqual(
                    ARCHITECTURE.validate_repository_drift(
                        repo.root, FIT.load_architecture(repo.root)
                    ),
                    (),
                )

    def test_queue_adapter_resolution_bounds_fail_closed_only_for_possible_operations(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]

        for label, modules in (("depth nine", 9),):
            with self.subTest(label=label):
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                for index in range(modules):
                    if index == modules - 1:
                        value = "import celery\napp = celery.Celery('jobs')\n"
                    else:
                        value = f"from adapters.m{index + 1} import app\n"
                    repo.write_text(f"adapters/m{index}.py", value)
                before = "from adapters.m0 import app\n"
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text(
                    "src/jobs.py",
                    before + "@app.task\ndef stage():\n    return None\n",
                )
                head = repo.commit("bounded adapter operation")
                report = self._evaluate(repo, base, head)
                self.assertEqual(
                    self._results(report)["background_job"].status,
                    "unsupported",
                )
                self.assertEqual(report.status, "fail")
                self.assertIn("new_queue", report.triggers)

        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        imports = []
        for index in range(FIT.MAX_QUEUE_ADAPTER_MODULES):
            imports.append(f"from absent.m{index} import app{index}")
        imports.append("from adapters.valid import app")
        repo.write_text("adapters/aggregate.py", "\n".join(imports) + "\n")
        repo.write_text(
            "adapters/valid.py",
            "import celery\napp = celery.Celery('jobs')\n",
        )
        imported = "from adapters.aggregate import " + ", ".join(
            [f"app{index}" for index in range(FIT.MAX_QUEUE_ADAPTER_MODULES)] + ["app"]
        ) + "\n"
        repo.write_text("src/jobs.py", imported)
        base = repo.commit("base")
        calls = "".join(
            f"app{index}()\n" for index in range(FIT.MAX_QUEUE_ADAPTER_MODULES)
        )
        repo.write_text(
            "src/jobs.py",
            imported + calls + "@app.task\ndef stage():\n    return None\n",
        )
        head = repo.commit("adapter import ceiling")
        report = self._evaluate(repo, base, head)
        self.assertEqual(self._results(report)["background_job"].status, "unsupported")
        self.assertEqual(report.status, "fail")
        self.assertIn("new_queue", report.triggers)

        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        repo.write_text(
            "project/celery_app.py",
            "import celery\napp = celery.Celery('jobs')\n",
        )
        repo.write_text("project/jobs.py", "from .celery_app import app\n")
        before = "from project.jobs import app\n"
        repo.write_text("src/jobs.py", before)
        base = repo.commit("base")
        repo.write_text(
            "src/jobs.py",
            before + "@app.task\ndef stage():\n    return None\n",
        )
        head = repo.commit("relative adapter operation")
        report = self._evaluate(repo, base, head)
        self.assertEqual(self._results(report)["background_job"].status, "unsupported")
        self.assertIn("new_queue", report.triggers)

        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        for index in range(10):
            value = f"from ordinary.m{index + 1} import value\n" if index < 9 else "value = 1\n"
            repo.write_text(f"ordinary/m{index}.py", value)
        before = "from ordinary.m0 import value\n"
        repo.write_text("src/jobs.py", before)
        base = repo.commit("base")
        repo.write_text("src/jobs.py", before + "RESULT = value\n")
        head = repo.commit("ordinary deep import")
        report = self._evaluate(repo, base, head)
        self.assertEqual(self._results(report)["background_job"].status, "not_applicable")
        self.assertEqual(report.status, "pass")
        self.assertNotIn("new_queue", report.triggers)

    def test_local_queue_adapter_dependency_chains_do_not_silently_truncate(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["project", "src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]

        dependency_boundary = FIT.MAX_QUEUE_DEPENDENCY_WORK
        boundary_cases = (
            ("below", dependency_boundary - 2, False),
            ("at", dependency_boundary - 1, False),
            ("above", dependency_boundary, True),
        )
        for label, links, expected_exhausted in boundary_cases:
            with self.subTest(boundary=label, links=links):
                chain = ["from project.jobs import app"]
                previous = "app"
                for index in range(links):
                    current = f"alias{index}"
                    chain.append(f"{current} = {previous}")
                    previous = current
                before = "\n".join(chain) + "\n"
                operation = f"{previous}.delay(task)\n"
                dependency_result = FIT._operation_dependencies(
                    ast.parse(before + operation)
                )
                self.assertEqual(dependency_result.exhausted, expected_exhausted)
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text(
                    "project/jobs.py",
                    "import celery\napp = celery.Celery('jobs')\n",
                )
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", before + operation)
                head = repo.commit("long local queue dependency")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "unsupported")
                self.assertEqual(report.status, "fail")
                self.assertIn("src/jobs.py", result.applicability.scanned_scope)
                self.assertIn("new_queue", report.triggers)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

        unrelated_chain = [
            "class Form:\n    def submit(self):\n        return None",
            "value0 = Form()",
        ]
        for index in range(1, dependency_boundary + 1):
            unrelated_chain.append(f"value{index} = value{index - 1}")
        before = "\n".join(unrelated_chain) + "\n"
        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        repo.write_text("src/jobs.py", before)
        base = repo.commit("base")
        repo.write_text(
            "src/jobs.py",
            before + f"value{dependency_boundary}.submit()\n",
        )
        head = repo.commit("long unrelated dependency")
        report = self._evaluate(repo, base, head, pre_risk="yellow")
        self.assertEqual(
            self._results(report)["background_job"].status,
            "not_applicable",
        )
        self.assertEqual(report.status, "pass")
        self.assertNotIn("new_queue", report.triggers)

    def test_queue_dependency_frontier_resolves_reachable_local_exports(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["project", "src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        wide = ", ".join(
            f"wide{index}" for index in range(FIT.MAX_QUEUE_DEPENDENCY_WORK)
        )
        cases = (
            (
                "neutral module queue export",
                "project/runtime.py",
                "import celery\napp = celery.Celery('jobs')\n",
                "from project.runtime import app\nzzzz = app\n",
                "app",
                "unsupported",
                "fail",
                True,
            ),
            (
                "queue-adjacent module nonqueue export",
                "project/jobs.py",
                "class Form:\n    def submit(self):\n        return None\nform = Form()\n",
                "from project.jobs import form\nzzzz = form\n",
                "form",
                "not_applicable",
                "pass",
                False,
            ),
        )
        for (
            label,
            module_path,
            module_source,
            prefix,
            imported_name,
            expected_background,
            expected_status,
            expected_trigger,
        ) in cases:
            with self.subTest(case=label):
                before = prefix + f"receiver = ({wide}, zzzz)\n"
                operation = "receiver.delay(task)\n"
                dependency_result = FIT._operation_dependencies(
                    ast.parse(before + operation)
                )
                self.assertTrue(dependency_result.exhausted)
                self.assertNotIn(imported_name, dependency_result.names)
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text(module_path, module_source)
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", before + operation)
                worktree_diff = FIT.diff_architecture(
                    repo.root, base_sha=base, worktree=True
                )
                worktree_report = FIT.evaluate_fitness(
                    repo.root,
                    FIT.load_architecture(repo.root),
                    worktree_diff,
                    worktree_diff.changed_paths,
                    pre_risk="yellow",
                )
                head = repo.commit("frontier operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, expected_background)
                self.assertEqual(report.status, expected_status)
                self.assertEqual("new_queue" in report.triggers, expected_trigger)
                if expected_trigger:
                    self.assertIn("src/jobs.py", result.applicability.scanned_scope)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )
                self.assertEqual(
                    (
                        worktree_report.status,
                        self._results(worktree_report)["background_job"].status,
                        worktree_report.triggers,
                    ),
                    (report.status, result.status, report.triggers),
                )

    def test_unrelated_exhausted_dependency_frontier_remains_not_applicable(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["project", "src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        wide = ", ".join(
            f"wide{index}" for index in range(FIT.MAX_QUEUE_DEPENDENCY_WORK)
        )
        before = "from project.jobs import form\nform.submit()\n"
        head_source = before + f"receiver = ({wide})\nreceiver.delay(task)\n"
        dependency_result = FIT._operation_dependencies(ast.parse(head_source))
        self.assertTrue(dependency_result.exhausted)
        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        repo.write_text(
            "project/jobs.py",
            "class Form:\n    def submit(self):\n        return None\nform = Form()\n",
        )
        repo.write_text("src/jobs.py", before)
        base = repo.commit("base")
        repo.write_text("src/jobs.py", head_source)
        head = repo.commit("unrelated exhausted graph")
        report = self._evaluate(repo, base, head, pre_risk="yellow")
        self.assertEqual(
            self._results(report)["background_job"].status,
            "not_applicable",
        )
        self.assertEqual(report.status, "pass")
        self.assertNotIn("new_queue", report.triggers)
        self.assertGreaterEqual(
            FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
        )

    def test_queue_local_resolution_is_reused_across_changed_importers(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["project", "src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        repo.write_text(
            "project/runtime.py",
            "import celery\napp = celery.Celery('jobs')\n",
        )
        before = "from project.runtime import app\n"
        for path in ("src/first.py", "src/second.py"):
            repo.write_text(path, before)
        base = repo.commit("base")
        for path in ("src/first.py", "src/second.py"):
            repo.write_text(path, before + "app.delay(task)\n")
        head = repo.commit("two queue importers")
        real_batch = FIT.read_diff_files
        with patch.object(FIT, "read_diff_files", wraps=real_batch) as batches:
            report = self._evaluate(repo, base, head, pre_risk="yellow")
        runtime_reads = sorted(
            (path, call.args[3])
            for call in batches.call_args_list
            for path in call.args[2]
            if path == "project/runtime.py"
        )
        self.assertEqual(
            runtime_reads,
            [("project/runtime.py", "head")],
        )
        result = self._results(report)["background_job"]
        self.assertEqual(result.status, "unsupported")
        self.assertEqual(report.status, "fail")
        self.assertEqual(
            set(result.applicability.scanned_scope),
            {"FIT-JOBS", "src/first.py", "src/second.py"},
        )
        self.assertIn("new_queue", report.triggers)
        self.assertGreaterEqual(
            FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
        )

    def test_shared_queue_cache_does_not_share_importer_work_budget(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["adapters", "src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        per_importer = FIT.MAX_QUEUE_ADAPTER_MODULES // 2 + 1
        wide = ", ".join(
            f"wide{index}" for index in range(FIT.MAX_QUEUE_DEPENDENCY_WORK)
        )
        for group in ("a", "b"):
            imports = []
            aliases = []
            for index in range(per_importer):
                alias = f"zz{group}{index:02d}"
                imports.append(
                    f"from adapters.{group}{index:02d} import value as {alias}"
                )
                aliases.append(alias)
                repo.write_text(f"adapters/{group}{index:02d}.py", "value = 1\n")
            before = "\n".join(imports) + f"\nreceiver = ({wide}, {', '.join(aliases)})\n"
            repo.write_text(f"src/{group}.py", before)
        base = repo.commit("base")
        for group in ("a", "b"):
            path = repo.root / f"src/{group}.py"
            repo.write_text(
                f"src/{group}.py",
                path.read_text(encoding="utf-8") + "receiver.delay(task)\n",
            )
        head = repo.commit("two bounded exhausted importers")
        real_batch = FIT.read_diff_files
        with patch.object(FIT, "read_diff_files", wraps=real_batch) as batches:
            report = self._evaluate(repo, base, head, pre_risk="yellow")
        modules = {
            path
            for call in batches.call_args_list
            if call.args[3] == "head"
            for path in call.args[2]
            if path.startswith("adapters/")
        }
        self.assertGreater(len(modules), FIT.MAX_QUEUE_ADAPTER_MODULES)
        self.assertEqual(
            self._results(report)["background_job"].status, "not_applicable"
        )
        self.assertEqual(report.status, "pass")
        self.assertNotIn("new_queue", report.triggers)

    def test_external_imports_use_batched_local_module_inventory(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        before = "import external_alpha as alpha\nimport external_beta as beta\n"
        for path in ("src/first.py", "src/second.py"):
            repo.write_text(path, before)
        base = repo.commit("base")
        for path in ("src/first.py", "src/second.py"):
            repo.write_text(path, before + "alpha.render()\nbeta.validate()\n")
        head = repo.commit("ordinary external imports")
        real_batch = FIT.read_diff_files
        with patch.object(FIT, "read_diff_files", wraps=real_batch) as batches:
            report = self._evaluate(repo, base, head, pre_risk="yellow")
        external_reads = [
            path
            for call in batches.call_args_list
            for path in call.args[2]
            if path.startswith("external_")
        ]
        self.assertEqual(external_reads, [])
        self.assertEqual(
            self._results(report)["background_job"].status, "not_applicable"
        )
        self.assertNotIn("new_queue", report.triggers)

    def test_exact_batch_blob_reader_is_bounded_and_validates_entries(self) -> None:
        repo = GitArchitectureRepo(self)
        repo.model(_system(), _rules())
        paths = tuple(f"src/module{index:02d}.py" for index in range(32))
        for path in paths:
            repo.write_text(path, "VALUE = 1\n")
        base = repo.commit("base")
        repo.write_text("src/changed.py", "VALUE = 2\n")
        head = repo.commit("head")
        diff = FIT.diff_architecture(repo.root, base_sha=base, head_sha=head)
        real_git = DIFF._git
        with patch.object(DIFF, "_git", wraps=real_git) as git:
            values = DIFF.read_diff_files(repo.root, diff, (*paths, "src/missing.py"))
        self.assertEqual(values[paths[0]], b"VALUE = 1\n")
        self.assertIsNone(values["src/missing.py"])
        batch_calls = [
            call
            for call in git.call_args_list
            if any("--batch" in argument for argument in call.args[1])
        ]
        self.assertEqual(len(batch_calls), 1)

        os.symlink("module00.py", repo.root / "src/link.py")
        repo.write_bytes(
            "src/oversized.py", b"x" * (DIFF.MAX_ANALYZED_FILE_BYTES + 1)
        )
        bad_base = repo.commit("unsafe entries")
        repo.write_text("src/changed.py", "VALUE = 3\n")
        bad_head = repo.commit("query unsafe entries")
        bad_diff = FIT.diff_architecture(repo.root, base_sha=bad_base, head_sha=bad_head)
        with self.assertRaisesRegex(ARCHITECTURE.ArchitectureError, "not a regular file"):
            DIFF.read_diff_files(repo.root, bad_diff, ("src/link.py",))
        with self.assertRaisesRegex(ARCHITECTURE.ArchitectureError, "exceeds analysis limit"):
            DIFF.read_diff_files(repo.root, bad_diff, ("src/oversized.py",))

    def test_local_module_and_wildcard_imports_resolve_queue_exports(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["project", "src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        queue_source = "import celery\napp = celery.Celery('jobs')\n"
        nonqueue_source = (
            "class Form:\n"
            "    def delay(self, value):\n"
            "        return value\n"
            "app = Form()\n"
        )
        cases = (
            (
                "module alias queue",
                "import project.runtime as runtime\n",
                "runtime.app.delay(task)\n",
                queue_source,
                True,
            ),
            (
                "module alias nonqueue",
                "import project.runtime as runtime\n",
                "runtime.app.delay(task)\n",
                nonqueue_source,
                False,
            ),
            (
                "wildcard queue",
                "from project.runtime import *\n",
                "app.delay(task)\n",
                queue_source,
                True,
            ),
            (
                "wildcard nonqueue",
                "from project.runtime import *\n",
                "app.delay(task)\n",
                nonqueue_source,
                False,
            ),
        )
        for label, imported, operation, module_source, expected_queue in cases:
            with self.subTest(case=label):
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text("project/runtime.py", module_source)
                repo.write_text("src/jobs.py", imported)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", imported + operation)
                head = repo.commit("local import operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(
                    result.status,
                    "unsupported" if expected_queue else "not_applicable",
                )
                self.assertEqual(report.status, "fail" if expected_queue else "pass")
                self.assertEqual("new_queue" in report.triggers, expected_queue)
                if expected_queue:
                    self.assertIn("src/jobs.py", result.applicability.scanned_scope)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

    def test_relative_child_import_requires_a_resolved_local_source(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        cases = (
            ("missing below", FIT.MAX_QUEUE_DEPENDENCY_WORK - 3, None, True),
            ("missing at", FIT.MAX_QUEUE_DEPENDENCY_WORK - 2, None, True),
            ("missing above", FIT.MAX_QUEUE_DEPENDENCY_WORK - 1, None, True),
            (
                "queue child at frontier",
                FIT.MAX_QUEUE_DEPENDENCY_WORK - 2,
                "import celery\napp = celery.Celery('jobs')\n",
                True,
            ),
            (
                "nonqueue child at frontier",
                FIT.MAX_QUEUE_DEPENDENCY_WORK - 2,
                "class Runtime:\n    pass\nruntime = Runtime()\n",
                False,
            ),
        )
        for label, width, child_source, expected_queue in cases:
            with self.subTest(case=label):
                wide = ", ".join(f"wide{index}" for index in range(width))
                before = (
                    "from . import runtime\n"
                    "zzzz = runtime\n"
                    f"receiver = ({wide}, zzzz)\n"
                )
                dependency_result = FIT._operation_dependencies(
                    ast.parse(before + "receiver.delay(task)\n")
                )
                self.assertEqual(
                    dependency_result.exhausted,
                    width >= FIT.MAX_QUEUE_DEPENDENCY_WORK - 2,
                )
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                repo.write_text("src/project/__init__.py", "")
                if child_source is not None:
                    repo.write_text("src/project/runtime.py", child_source)
                repo.write_text("src/project/jobs.py", before)
                base = repo.commit("base")
                repo.write_text(
                    "src/project/jobs.py", before + "receiver.delay(task)\n"
                )
                head = repo.commit("relative child operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(
                    result.status,
                    "unsupported" if expected_queue else "not_applicable",
                )
                self.assertEqual(report.status, "fail" if expected_queue else "pass")
                self.assertEqual("new_queue" in report.triggers, expected_queue)
                if expected_queue:
                    self.assertIn(
                        "src/project/jobs.py", result.applicability.scanned_scope
                    )
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

    def test_package_aware_queue_provenance_is_shared_by_fitness_and_risk(self) -> None:
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = ["project", "src"]
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        cases = (
            (
                "package initializer child export",
                {
                    "project/jobs/__init__.py": "from .celery_app import app\n",
                    "project/jobs/celery_app.py": (
                        "import celery\napp = celery.Celery('jobs')\n"
                    ),
                },
                "from project.jobs import app\n",
                "@app.task\ndef stage():\n    return None\n",
            ),
            (
                "regular module child export",
                {
                    "project/jobs/worker.py": "from .celery_app import app\n",
                    "project/jobs/celery_app.py": (
                        "import celery\napp = celery.Celery('jobs')\n"
                    ),
                },
                "from project.jobs.worker import app\n",
                "@app.task\ndef stage():\n    return None\n",
            ),
            (
                "package import child module",
                {
                    "project/jobs/__init__.py": "from . import celery_app\n",
                    "project/jobs/celery_app.py": (
                        "import celery\napp = celery.Celery('jobs')\n"
                    ),
                },
                "from project.jobs import celery_app\n",
                "@celery_app.app.task\ndef stage():\n    return None\n",
            ),
            (
                "parent relative package export",
                {
                    "project/jobs/subpackage/__init__.py": "from ..celery_app import app\n",
                    "project/jobs/celery_app.py": (
                        "import celery\napp = celery.Celery('jobs')\n"
                    ),
                },
                "from project.jobs.subpackage import app\n",
                "@app.task\ndef stage():\n    return None\n",
            ),
            (
                "multi hop package re-export",
                {
                    "project/__init__.py": "from .jobs import app\n",
                    "project/jobs/__init__.py": "from .celery_app import app\n",
                    "project/jobs/celery_app.py": (
                        "import celery\napp = celery.Celery('jobs')\n"
                    ),
                },
                "from project import app\n",
                "@app.task\ndef stage():\n    return None\n",
            ),
            (
                "relevant unresolved local adapter",
                {"project/__init__.py": "VALUE = 1\n"},
                "from project.jobs import app\n",
                "@app.task\ndef stage():\n    return None\n",
            ),
        )
        for label, modules, before, addition in cases:
            with self.subTest(label=label):
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                for path, value in modules.items():
                    repo.write_text(path, value)
                repo.write_text("src/jobs.py", before)
                base = repo.commit("base")
                repo.write_text("src/jobs.py", before + addition)
                head = repo.commit("queue operation")
                report = self._evaluate(repo, base, head)
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "unsupported")
                self.assertEqual(report.status, "fail")
                self.assertIn("src/jobs.py", result.applicability.scanned_scope)
                self.assertIn("new_queue", report.triggers)

    def test_queue_adapter_uncertainty_and_source_roots_fail_closed(self) -> None:
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        cases = (
            (
                "present adapter with unsupported factory export",
                ["project", "src"],
                {
                    "project/jobs.py": (
                        "import celery\n\n"
                        "def build_app():\n"
                        "    return celery.Celery('jobs')\n\n"
                        "app = build_app()\n"
                    ),
                },
                "src/consumer.py",
                "unsupported",
            ),
            (
                "src layout adapter",
                ["src"],
                {
                    "src/project/jobs.py": (
                        "import celery\napp = celery.Celery('jobs')\n"
                    ),
                },
                "src/consumer.py",
                "unsupported",
            ),
            (
                "ambiguous source roots",
                ["src", "lib"],
                {
                    "src/project/jobs.py": (
                        "import celery\napp = celery.Celery('src-jobs')\n"
                    ),
                    "lib/project/jobs.py": (
                        "import celery\napp = celery.Celery('lib-jobs')\n"
                    ),
                },
                "src/consumer.py",
                "unsupported",
            ),
            (
                "grounded source root with missing adapter",
                ["src"],
                {"src/project/__init__.py": "VALUE = 1\n"},
                "src/consumer.py",
                "unsupported",
            ),
        )
        for label, repository_paths, modules, consumer, expected in cases:
            with self.subTest(label=label):
                system = _system()
                system["nodes"][0]["type"] = "worker"
                system["nodes"][0]["repository_paths"] = repository_paths
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                for path, value in modules.items():
                    repo.write_text(path, value)
                before = "from project.jobs import app\n"
                repo.write_text(consumer, before)
                base = repo.commit("base")
                repo.write_text(
                    consumer,
                    before + "@app.task\ndef stage():\n    return None\n",
                )
                head = repo.commit("queue operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, expected)
                self.assertEqual(report.status, "fail")
                self.assertIn(consumer, result.applicability.scanned_scope)
                self.assertIn("new_queue", report.triggers)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

    def test_queue_source_root_limit_is_lazy_and_returns_shared_evidence(self) -> None:
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        cases = (
            ("unrelated below root limit", FIT.MAX_QUEUE_SOURCE_ROOTS - 1, False),
            ("unrelated above root limit", FIT.MAX_QUEUE_SOURCE_ROOTS, False),
            ("relevant at root limit", FIT.MAX_QUEUE_SOURCE_ROOTS - 1, True),
            ("relevant above root limit", FIT.MAX_QUEUE_SOURCE_ROOTS, True),
        )
        for label, declared_root_count, relevant in cases:
            with self.subTest(label=label):
                repository_paths = [
                    f"root{index}" for index in range(declared_root_count)
                ]
                system = _system()
                system["nodes"][0]["type"] = "worker"
                system["nodes"][0]["repository_paths"] = repository_paths
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                for source_root in repository_paths:
                    repo.write_text(f"{source_root}/__init__.py", "")
                consumer = "root0/consumer.py"
                if relevant:
                    adapter_root = repository_paths[-1]
                    repo.write_text(
                        f"{adapter_root}/project/jobs.py",
                        "import celery\napp = celery.Celery('jobs')\n",
                    )
                    before = "from project.jobs import app\n"
                    addition = "@app.task\ndef stage():\n    return None\n"
                else:
                    before = (
                        "class Form:\n"
                        "    def submit(self):\n"
                        "        return None\n\n"
                        "form = Form()\n"
                    )
                    addition = "form.submit()\n"
                repo.write_text(consumer, before)
                base = repo.commit("base")
                repo.write_text(consumer, before + addition)
                head = repo.commit("changed operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                if relevant:
                    self.assertEqual(result.status, "unsupported")
                    self.assertEqual(report.status, "fail")
                    self.assertIn(consumer, result.applicability.scanned_scope)
                    self.assertIn("new_queue", report.triggers)
                else:
                    self.assertEqual(result.status, "not_applicable")
                    self.assertEqual(report.status, "pass")
                    self.assertNotIn("new_queue", report.triggers)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

        repository_paths = [
            f"root{index}" for index in range(FIT.MAX_QUEUE_SOURCE_ROOTS)
        ]
        system = _system()
        system["nodes"][0]["type"] = "worker"
        system["nodes"][0]["repository_paths"] = repository_paths
        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        for source_root in repository_paths:
            repo.write_text(f"{source_root}/__init__.py", "")
        repo.write_text(
            f"{repository_paths[-1]}/project/jobs.py",
            "import celery\napp = celery.Celery('jobs')\n",
        )
        consumer = "root0/consumer.py"
        before = (
            "from project.jobs import app\n\n"
            "@app.task\n"
            "def existing():\n"
            "    return None\n\n"
            "class Form:\n"
            "    def submit(self):\n"
            "        return None\n\n"
            "form = Form()\n"
        )
        repo.write_text(consumer, before)
        base = repo.commit("base with existing queue operation")
        repo.write_text(consumer, before + "form.submit()\n")
        head = repo.commit("unrelated operation only")
        report = self._evaluate(repo, base, head, pre_risk="yellow")
        result = self._results(report)["background_job"]
        self.assertEqual(result.status, "not_applicable")
        self.assertEqual(report.status, "pass")
        self.assertNotIn("new_queue", report.triggers)
        self.assertGreaterEqual(
            FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
        )

    def test_queue_root_limit_does_not_inherit_sibling_export_provenance(self) -> None:
        rules = _rules()
        rules["background_job_policies"] = [{
            "id": "FIT-JOBS",
            "node_types": ["worker"],
            "max_retries": 3,
            "require_idempotency": True,
            "require_correlation_id": True,
            "terminal_actions": ["dead_letter"],
            "severity": "error",
        }]
        for declared_root_count in (
            FIT.MAX_QUEUE_SOURCE_ROOTS - 1,
            FIT.MAX_QUEUE_SOURCE_ROOTS,
        ):
            with self.subTest(declared_root_count=declared_root_count):
                repository_paths = [
                    f"root{index:03d}" for index in range(declared_root_count)
                ]
                system = _system()
                system["nodes"][0]["type"] = "worker"
                system["nodes"][0]["repository_paths"] = repository_paths
                repo = GitArchitectureRepo(self)
                repo.model(system, rules)
                for source_root in repository_paths:
                    repo.write_text(f"{source_root}/__init__.py", "")
                repo.write_text(
                    "root000/project/forms.py",
                    "import celery\n"
                    "app = celery.Celery('jobs')\n\n"
                    "class Form:\n"
                    "    def submit(self):\n"
                    "        return None\n\n"
                    "form = Form()\n",
                )
                consumer = "root000/consumer.py"
                before = "from project.forms import form\n"
                repo.write_text(consumer, before)
                base = repo.commit("base with mixed exports")
                repo.write_text(consumer, before + "form.submit()\n")
                head = repo.commit("unrelated export operation")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["background_job"]
                self.assertEqual(result.status, "not_applicable")
                self.assertEqual(report.status, "pass")
                self.assertNotIn("new_queue", report.triggers)
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

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
            (
                "unknown external constructor",
                "src/client.py",
                "import paramiko as ssh\nclient = ssh.transport.SSHClient()\n",
                "unsupported",
            ),
            (
                "cloud sdk client factory",
                "src/client.py",
                "import boto3\ns3 = boto3.client('s3')\n"
                "s3.get_object(Bucket='bucket', Key='key')\n",
                "unsupported",
            ),
            (
                "cloud sdk resource factory",
                "src/client.py",
                "import boto3\ns3 = boto3.resource('s3')\n",
                "unsupported",
            ),
            (
                "cloud sdk session constructor",
                "src/client.py",
                "from boto3.session import Session\nsession = Session()\n",
                "unsupported",
            ),
            (
                "cloud core session factory",
                "src/client.py",
                "import botocore.session as core\nsession = core.get_session()\n",
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

    def test_network_unknown_detection_excludes_non_network_calls(self) -> None:
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
        repo.write_text("src/local_client.py", "class SSHClient:\n    pass\n")
        repo.write_text(
            "src/use.py",
            "import pathlib\nimport local_client\nimport pydantic\n"
            "pathlib.Path('value')\nlocal_client.SSHClient()\npydantic.BaseModel()\n",
        )
        head = repo.commit("local constructors")
        report = self._evaluate(repo, base, head)
        result = self._results(report)["network_client"]
        self.assertEqual(result.status, "not_applicable")
        self.assertNotIn("new_network_client", report.triggers)

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

    def test_changed_code_budget_rejects_unknown_non_python_line_metrics(self) -> None:
        for label, content in (
            ("nul", b"line one\0\nline two\n"),
            ("invalid utf8", b"line one\n\xff\n"),
        ):
            with self.subTest(label=label):
                rules = _rules()
                rules["code_budgets"] = [{
                    "id": "FIT-BUDGET",
                    "path_prefixes": ["src"],
                    "max_changed_bytes": 1000,
                    "max_changed_lines": 1,
                    "max_ast_complexity": 100,
                    "severity": "error",
                }]
                repo, base = self._repo(rules=rules)
                repo.write_text("src/readable.js", "const value = 1;\n")
                repo.write_bytes("src/opaque.js", content)
                head = repo.commit("unknown line metric")
                report = self._evaluate(repo, base, head, pre_risk="yellow")
                result = self._results(report)["code_budget"]
                self.assertEqual(result.status, "unsupported")
                self.assertEqual(report.status, "fail")
                self.assertIn("src/opaque.js", result.applicability.scanned_scope)
                self.assertIn("unknown line statistics", " ".join(result.findings))
                self.assertGreaterEqual(
                    FIT.RISK_ORDER[report.post_risk], FIT.RISK_ORDER[report.pre_risk]
                )

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

    def test_added_contracts_must_have_supported_baseline_semantics(self) -> None:
        system = _system()
        rules = _rules()
        rules["contract_policies"] = [{
            "id": "FIT-CONTRACT",
            "contract_kinds": ["json_schema"],
            "compatibility": "consumer_accepts_old",
            "severity": "error",
        }]
        repo = GitArchitectureRepo(self)
        repo.model(system, rules)
        base = repo.commit("pre-contract baseline")
        added = copy.deepcopy(system)
        added["contracts"] = [{
            "id": "CONTRACT-UNSUPPORTED",
            "kind": "json_schema",
            "path": "engineering/contracts/unsupported.json",
            "version": "1",
            "role": "consumer",
            "compatibility": "consumer_accepts_old",
        }]
        added["nodes"][0]["public_contracts"] = ["CONTRACT-UNSUPPORTED"]
        repo.model(added, rules)
        document = _json_schema({"value": {"type": "string"}})
        document["properties"]["value"]["oneOf"] = [{"type": "string"}]
        repo.write_json("engineering/contracts/unsupported.json", document)
        head = repo.commit("unsupported contract addition")
        report = self._evaluate(repo, base, head, pre_risk="yellow")
        result = self._results(report)["contract_compatibility"]
        self.assertEqual(result.status, "unsupported")
        self.assertEqual(report.status, "fail")
        self.assertIn("CONTRACT-UNSUPPORTED", " ".join(result.findings))

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
            "UPDATE item SET id = id WHERE id >= 1 AND id <= 100;\n",
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
                "tautological marker migrate",
                "migrations/001_migrate.sql",
                "-- adaptive-grok: bounded\n-- adaptive-grok: resumable\n"
                "DELETE FROM item WHERE 1=1;\n",
                "fail",
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
                        "UPDATE item SET id = id WHERE id >= 1 AND id <= 100;\n"
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
                "UPDATE item SET id = id WHERE id >= 1 AND id <= 100;\n",
            ),
            ("contract", "ALTER TABLE item DROP COLUMN legacy;\n"),
        ):
            repo.write_text(f"migrations/001_{phase}.sql", source)
        base = repo.commit("safe migration base")
        repo.write_text("migrations/001_migrate.sql", "UPDATE item SET id = id;\n")
        head = repo.commit("modified unsafe migrate")
        result = self._results(self._evaluate(repo, base, head))["migration_safety"]
        self.assertEqual(result.status, "fail")

        repo = GitArchitectureRepo(self)
        repo.model(_system(), rules)
        duplicate_base = repo.commit("duplicate base")
        for group in ("001_alpha", "001_beta"):
            for phase, source in (
                ("expand", "CREATE TABLE item(id integer);\n"),
                (
                    "migrate",
                    "UPDATE item SET id = id WHERE id >= 1 AND id <= 100;\n",
                ),
                ("contract", "ALTER TABLE item DROP COLUMN legacy;\n"),
                ):
                repo.write_text(f"migrations/{group}_{phase}.sql", source)
        duplicate_head = repo.commit("duplicate version inventory")
        duplicate = self._results(
            self._evaluate(repo, duplicate_base, duplicate_head)
        )["migration_safety"]
        self.assertEqual(duplicate.status, "fail")
        self.assertIn("duplicate", " ".join(duplicate.findings))

        bounded_repo, bounded_base = self._repo(rules=rules)
        for phase, source in (
            ("expand", "CREATE TABLE item(id integer);\n"),
            (
                "migrate",
                "UPDATE item SET id = id WHERE id >= 1 AND id <= 100;\n",
            ),
            ("contract", "ALTER TABLE item DROP COLUMN legacy;\n"),
        ):
            bounded_repo.write_text(f"migrations/001_{phase}.sql", source)
        bounded_head = bounded_repo.commit("bounded range migration")
        bounded = self._results(
            self._evaluate(bounded_repo, bounded_base, bounded_head)
        )["migration_safety"]
        self.assertEqual(bounded.status, "pass")

    def test_migration_phase_identity_rejects_duplicate_artifacts(self) -> None:
        rules = _rules()
        rules["migration_policies"] = [{
            "id": "FIT-MIGRATION",
            "path_prefixes": ["migrations"],
            "required_phases": ["expand", "migrate", "contract"],
            "immutable_history": False,
            "severity": "error",
        }]
        cases = (
            (
                "suffix variants",
                {
                    "migrations/001_expand.sql": "CREATE TABLE item(id integer);\n",
                    "migrations/001_expand_copy.sql": "CREATE TABLE other(id integer);\n",
                    "migrations/001_migrate.sql": (
                        "UPDATE item SET id = id WHERE id >= 1 AND id <= 100;\n"
                    ),
                    "migrations/001_contract.sql": "ALTER TABLE item DROP COLUMN legacy;\n",
                },
            ),
            (
                "duplicate subdirectories",
                {
                    f"migrations/{directory}/001_{phase}.sql": source
                    for directory in ("one", "two")
                    for phase, source in (
                        ("expand", "CREATE TABLE item(id integer);\n"),
                        (
                            "migrate",
                            "UPDATE item SET id = id WHERE id >= 1 AND id <= 100;\n",
                        ),
                        ("contract", "ALTER TABLE item DROP COLUMN legacy;\n"),
                    )
                },
            ),
        )
        for label, files in cases:
            with self.subTest(label=label):
                repo, base = self._repo(rules=rules)
                for path, source in files.items():
                    repo.write_text(path, source)
                head = repo.commit(label)
                result = self._results(self._evaluate(repo, base, head))["migration_safety"]
                self.assertEqual(result.status, "fail")
                self.assertIn("duplicate migration artifact", " ".join(result.findings))

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

    def test_capped_process_reaps_children_when_selector_setup_fails(self) -> None:
        real_popen = DIFF.subprocess.Popen
        for stage in ("selector", "set_blocking", "register"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                processes = []

                def capture_popen(*args, **kwargs):
                    process = real_popen(*args, **kwargs)
                    processes.append(process)
                    return process

                selector = DIFF.selectors.DefaultSelector()
                if stage == "selector":
                    setup_patch = patch.object(
                        DIFF.selectors,
                        "DefaultSelector",
                        side_effect=OSError("forced selector failure"),
                    )
                elif stage == "set_blocking":
                    setup_patch = patch.object(
                        DIFF.os,
                        "set_blocking",
                        side_effect=OSError("forced set_blocking failure"),
                    )
                else:
                    setup_patch = patch.object(
                        selector,
                        "register",
                        side_effect=OSError("forced register failure"),
                    )
                selector_patch = (
                    patch.object(DIFF.selectors, "DefaultSelector", return_value=selector)
                    if stage == "register"
                    else None
                )
                caught = None
                try:
                    with patch.object(DIFF.subprocess, "Popen", side_effect=capture_popen):
                        if selector_patch is None:
                            with setup_patch:
                                DIFF._run_capped(
                                    [sys.executable, "-c", "import time; time.sleep(30)"],
                                    cwd=Path(directory),
                                    env={},
                                    stdout_limit=1024,
                                    stderr_limit=1024,
                                    timeout=5.0,
                                )
                        else:
                            with selector_patch, setup_patch:
                                DIFF._run_capped(
                                    [sys.executable, "-c", "import time; time.sleep(30)"],
                                    cwd=Path(directory),
                                    env={},
                                    stdout_limit=1024,
                                    stderr_limit=1024,
                                    timeout=5.0,
                                )
                except Exception as exc:  # asserted after leak cleanup
                    caught = exc
                self.assertEqual(len(processes), 1)
                alive = processes[0].poll() is None
                if alive:
                    os.killpg(processes[0].pid, signal.SIGKILL)
                    processes[0].wait()
                selector.close()
                self.assertIsInstance(caught, FIT.ArchitectureError)
                self.assertFalse(alive, f"{stage} setup failure leaked the process group")

    def test_git_exact_and_worktree_modes_disable_hostile_local_fsmonitor(self) -> None:
        repo, base = self._repo()
        repo.write_text("src/app.py", "VALUE = 1\n")
        head = repo.commit("head")
        sentinel = repo.root / "fsmonitor-ran"
        hook = repo.root / "hostile-fsmonitor"
        hook.write_text(
            f"#!/bin/sh\n: > '{sentinel}'\nexit 0\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)
        repo.git("config", "core.fsmonitor", str(hook))

        FIT.diff_architecture(repo.root, base_sha=base, head_sha=head)
        FIT.diff_architecture(repo.root, base_sha=base, worktree=True)
        for arguments in (
            ["ls-files", "-s", "-z"],
            ["diff", "--name-only", "-z", "HEAD"],
            ["ls-files", "--others", "--exclude-standard", "-z"],
        ):
            with self.subTest(arguments=arguments):
                DIFF._git(repo.root, arguments)
        self.assertFalse(sentinel.exists())

    def test_line_stats_are_linear_and_have_an_explicit_line_ceiling(self) -> None:
        self.assertTrue(hasattr(DIFF, "MAX_LINE_STAT_LINES"), "line-stat ceiling is absent")
        before = (b"x\n" * 6_000) + b"before\n"
        after = (b"x\n" * 6_000) + b"after\n"
        started = time.monotonic()
        self.assertEqual(DIFF._line_stats(before, after), (1, 1))
        self.assertLess(time.monotonic() - started, 0.25)
        disjoint_before = b"first\nunchanged one\nunchanged two\nlast\n"
        disjoint_after = b"changed first\nunchanged one\nunchanged two\nchanged last\n"
        self.assertEqual(DIFF._line_stats(disjoint_before, disjoint_after), (2, 2))

        repo, _architecture_base = self._repo()
        repo.write_text("src/disjoint.py", disjoint_before.decode("utf-8"))
        source_base = repo.commit("source base")
        repo.write_text("src/disjoint.py", disjoint_after.decode("utf-8"))
        source_head = repo.commit("disjoint changes")
        artifact = next(
            item
            for item in FIT.diff_architecture(
                repo.root, base_sha=source_base, head_sha=source_head
            ).artifacts
            if item.path == "src/disjoint.py"
        )
        self.assertEqual((artifact.added_lines, artifact.deleted_lines), (2, 2))
        oversized = b"x\n" * (DIFF.MAX_LINE_STAT_LINES + 1)
        with self.assertRaises(FIT.ArchitectureError):
            DIFF._line_stats(oversized, b"")
        over_bytes = b"x" * (DIFF.MAX_ANALYZED_FILE_BYTES + 1)
        with self.assertRaises(FIT.ArchitectureError):
            DIFF._line_stats(over_bytes, b"")

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

    def test_architecture_cli_is_deterministic_and_labels_worktree_evidence(self) -> None:
        repo, base = self._repo()
        script = ROOT / "scripts/grok_architecture.py"

        def invoke(*args: str):
            return subprocess.run(
                [sys.executable, str(script), "--root", str(repo.root), *args],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        first = invoke("summary", "--json")
        second = invoke("summary", "--json")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(json.loads(first.stdout)["architecture_id"], "ARCH-TEST")

        repo.write_text("src/app.py", "VALUE = 1\n")
        worktree = invoke("fitness", "--base", base, "--worktree", "--json")
        self.assertEqual(worktree.returncode, 0, worktree.stderr)
        payload = json.loads(worktree.stdout)
        self.assertEqual(payload["head_kind"], "worktree")
        self.assertNotIn("exact_head_sha", payload)

    def test_architecture_cli_exact_diff_and_diagram_check(self) -> None:
        repo, base = self._repo()
        repo.write_text("src/app.py", "VALUE = 1\n")
        head = repo.commit("head")
        script = ROOT / "scripts/grok_architecture.py"
        repo.write_text(
            ".grok-stack/runtime/active-route.json",
            json.dumps({"base_commit": "0" * 40, "head_commit": "f" * 40}),
        )
        exact = subprocess.run(
            [sys.executable, str(script), "--root", str(repo.root), "diff", "--base", base, "--head", head, "--json"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(exact.returncode, 0, exact.stderr)
        self.assertEqual(json.loads(exact.stdout)["exact_head_sha"], head)
        generated = subprocess.run(
            [sys.executable, str(script), "--root", str(repo.root), "diagram", "--json"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        rendered_payload = json.loads(generated.stdout)
        self.assertIn("artifacts", rendered_payload)
        self.assertEqual(rendered_payload["checked"], False)
        self.assertEqual(rendered_payload["mismatches"], [])
        self.assertEqual(
            tuple(rendered_payload["artifacts"]),
            ("container", "context", "data-flow", "deployment", "trust-boundary"),
        )
        generated_dir = repo.root / "architecture/generated"
        generated_dir.mkdir()
        for name, value in rendered_payload["artifacts"].items():
            (generated_dir / f"{name}.mmd").write_text(value, encoding="utf-8")
        checked = subprocess.run(
            [sys.executable, str(script), "--root", str(repo.root), "diagram", "--check", "--json"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)
        (repo.root / "architecture/generated/context.mmd").write_text("stale\n", encoding="utf-8")
        stale = subprocess.run(
            [sys.executable, str(script), "--root", str(repo.root), "diagram", "--check", "--json"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(stale.returncode, 1)
        for child in generated_dir.iterdir():
            child.unlink()
        generated_dir.rmdir()
        with tempfile.TemporaryDirectory() as outside_raw:
            outside = Path(outside_raw)
            generated_dir.symlink_to(outside, target_is_directory=True)
            escaped_write = subprocess.run(
                [sys.executable, str(script), "--root", str(repo.root), "diagram", "--json"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            escaped_check = subprocess.run(
                [sys.executable, str(script), "--root", str(repo.root), "diagram", "--check", "--json"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(escaped_write.returncode, 0)
            self.assertEqual(json.loads(escaped_write.stdout)["checked"], False)
            self.assertEqual(escaped_check.returncode, 2)
            self.assertEqual(tuple(outside.iterdir()), ())

            generated_dir.unlink()
            generated_dir.mkdir()
            outside_file = outside / "outside.mmd"
            outside_file.write_text("outside\n", encoding="utf-8")
            (generated_dir / "context.mmd").symlink_to(outside_file)
            final_link = subprocess.run(
                [sys.executable, str(script), "--root", str(repo.root), "diagram", "--json"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(final_link.returncode, 0)
            self.assertEqual(outside_file.read_text(encoding="utf-8"), "outside\n")

    def test_architecture_cli_invalid_model_is_nonzero_and_bootstrap_is_explicit(self) -> None:
        repo, _base = self._repo()
        repo.write_text("architecture/system.yaml", "{}\n")
        invalid = subprocess.run(
            [sys.executable, str(ROOT / "scripts/grok_architecture.py"), "--root", str(repo.root), "validate", "--json"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(invalid.returncode, 0)
        self.assertFalse(json.loads(invalid.stdout)["ok"])

        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, encoding="utf-8"
        ).strip()
        bootstrap = subprocess.run(
            [sys.executable, str(ROOT / "scripts/grok_architecture.py"), "--root", str(ROOT), "diff", "--base", ADOPTION_BASE, "--head", head, "--json"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(bootstrap.returncode, 0, bootstrap.stderr)
        self.assertTrue(json.loads(bootstrap.stdout)["baseline_introduced"])

    def test_exact_cli_diff_and_fitness_ignore_mutable_worktree_models(self) -> None:
        repo, base = self._repo()
        repo.write_text("README.md", "exact head\n")
        head = repo.commit("exact head")
        script = ROOT / "scripts/grok_architecture.py"

        repo.write_text("architecture/system.yaml", "{}\n")
        exact_diff = subprocess.run(
            [sys.executable, str(script), "--root", str(repo.root), "diff", "--base", base, "--head", head, "--json"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(exact_diff.returncode, 0, exact_diff.stdout + exact_diff.stderr)
        self.assertEqual(json.loads(exact_diff.stdout)["exact_head_sha"], head)

        (repo.root / "architecture/system.yaml").unlink()
        (repo.root / "architecture/rules.yaml").unlink()
        exact_fitness = subprocess.run(
            [sys.executable, str(script), "--root", str(repo.root), "fitness", "--base", base, "--head", head, "--json"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(
            exact_fitness.returncode,
            0,
            exact_fitness.stdout + exact_fitness.stderr,
        )
        payload = json.loads(exact_fitness.stdout)
        self.assertEqual(payload["head_kind"], "commit")
        self.assertEqual(payload["fitness_status"], "pass")


if __name__ == "__main__":
    unittest.main()
