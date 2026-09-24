from __future__ import annotations

import importlib.util
import json
import os
import re
import tempfile
import unittest
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    path = ROOT / ".grok-stack/adaptive_grok/workflow_artifacts.py"
    spec = importlib.util.spec_from_file_location("adaptive_grok.workflow_artifacts", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _write_manifest(root: Path, sources: list[dict[str, str]]) -> Path:
    path = root / "engineering/changes/change/workflow/manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "sources": sources}), encoding="utf-8")
    return path


class WorkflowSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifacts = _load_module()

    def test_runtime_route_accepts_optional_bounded_keyword_evidence(self) -> None:
        route = {'route_id': 'keywords', 'write_agent': 'data_implementer',
                 'review_agents': ['code_reviewer'], 'required_evidence': ['verification']}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / '.grok-stack/runtime/active-route.json'
            path.parent.mkdir(parents=True)
            for addition in ({}, {'matched_keywords': {}},
                             {'matched_keywords': {'data': ['sql', 'миграц']}}):
                with self.subTest(addition=addition):
                    expected = {**route, **addition}
                    path.write_text(json.dumps(expected), encoding='utf-8')
                    self.assertEqual(self.artifacts.load_runtime_authority(root, 'route'), expected)

    def test_runtime_route_rejects_malformed_keyword_evidence_and_unknown_fields(self) -> None:
        route = {'route_id': 'keywords', 'write_agent': 'data_implementer',
                 'review_agents': [], 'required_evidence': ['verification']}
        invalid = (None, [], 'sql', {'data': 'sql'}, {'data': []}, {'data': [1]},
                   {'data': ['sql', 'SQL']}, {'data': ['']}, {'data': ['sql\n']},
                   {'data': ['x' * 65]}, {'data': ['e\u0301']}, {'x' * 33: ['sql']},
                   {'bad domain': ['sql']}, {'data': [f'word{i}' for i in range(33)]},
                   {f'domain{i}': ['sql'] for i in range(17)})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / '.grok-stack/runtime/active-route.json'
            path.parent.mkdir(parents=True)
            for addition in [*({'matched_keywords': value} for value in invalid), {'unexpected': {}}]:
                with self.subTest(addition=addition):
                    path.write_text(json.dumps({**route, **addition}), encoding='utf-8')
                    with self.assertRaises(self.artifacts.WorkflowArtifactError):
                        self.artifacts.load_runtime_authority(root, 'route')

    def test_explicit_source_manifest_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / ".specify/specs/feature.md"
            source.parent.mkdir(parents=True)
            source.write_text("# Feature\n", encoding="utf-8")
            manifest = _write_manifest(
                root,
                [
                    {
                        "source_type": "spec-kit",
                        "source_version": "1",
                        "role": "spec",
                        "path": ".specify/specs/feature.md",
                    }
                ],
            )

            first = self.artifacts.load_source_manifest(root, manifest)
            second = self.artifacts.load_source_manifest(root, manifest)

            self.assertEqual(first.to_dict(), second.to_dict())
            record = first.sources[0].identity
            self.assertEqual(record["schema_version"], 1)
            self.assertEqual(record["path"], ".specify/specs/feature.md")
            self.assertEqual(len(record["sha256"]), 64)
            self.assertEqual(record["size"], len("# Feature\n".encode()))

    def test_manifest_rejects_ambiguous_and_unbounded_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = _write_manifest(root, [])
            for raw in (
                b'{"schema_version":1,"schema_version":1,"sources":[]}',
                b'{"schema_version":NaN,"sources":[]}',
                b'\xef\xbb\xbf{"schema_version":1,"sources":[]}',
            ):
                manifest.write_bytes(raw)
                with self.assertRaises(self.artifacts.WorkflowArtifactError):
                    self.artifacts.load_source_manifest(root, manifest)
            manifest.write_bytes(b" " * (self.artifacts.MAX_MANIFEST_BYTES + 1))
            with self.assertRaises(self.artifacts.WorkflowArtifactError):
                self.artifacts.load_source_manifest(root, manifest)

    def test_source_paths_are_bounded_and_no_follow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / "outside.md"
            outside.write_text("secret", encoding="utf-8")
            source = root / ".specify/specs/link.md"
            source.parent.mkdir(parents=True)
            source.symlink_to(outside)
            for path in ("../outside.md", "/etc/passwd", ".specify/specs/link.md"):
                manifest = _write_manifest(
                    root, [{"source_type": "spec-kit", "source_version": "1", "role": "spec", "path": path}]
                )
                with self.assertRaises(self.artifacts.WorkflowArtifactError):
                    self.artifacts.load_source_manifest(root, manifest)

    def test_source_manifest_rejects_absolute_path_even_inside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / ".specify/specs/absolute.md"
            source.parent.mkdir(parents=True)
            source.write_text("# Absolute\n", encoding="utf-8")
            manifest = _write_manifest(
                root,
                [
                    {
                        "source_type": "spec-kit",
                        "source_version": "1",
                        "role": "spec",
                        "path": str(source),
                    }
                ],
            )

            with self.assertRaises(self.artifacts.WorkflowArtifactError):
                self.artifacts.load_source_manifest(root, manifest)

    def test_source_rejects_special_files_non_nfc_and_yaml_authority_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            specs = root / ".specify/specs"
            specs.mkdir(parents=True)
            fifo = specs / "pipe.md"
            os.mkfifo(fifo)
            manifest = _write_manifest(
                root,
                [{"source_type": "spec-kit", "source_version": "1", "role": "spec", "path": ".specify/specs/pipe.md"}],
            )
            with self.assertRaises(self.artifacts.WorkflowArtifactError):
                self.artifacts.load_source_manifest(root, manifest)
            fifo.unlink()

            decomposed = "e\u0301.md"
            self.assertNotEqual(decomposed, unicodedata.normalize("NFC", decomposed))
            manifest = _write_manifest(
                root,
                [
                    {
                        "source_type": "spec-kit",
                        "source_version": "1",
                        "role": "spec",
                        "path": f".specify/specs/{decomposed}",
                    }
                ],
            )
            with self.assertRaises(self.artifacts.WorkflowArtifactError):
                self.artifacts.load_source_manifest(root, manifest)

            tagged = specs / "tagged.md"
            tagged.write_text("!!python/object:evil\n", encoding="utf-8")
            manifest = _write_manifest(
                root,
                [
                    {
                        "source_type": "spec-kit",
                        "source_version": "1",
                        "role": "spec",
                        "path": ".specify/specs/tagged.md",
                    }
                ],
            )
            with self.assertRaises(self.artifacts.WorkflowArtifactError):
                self.artifacts.load_source_manifest(root, manifest)

    def test_roles_and_framework_prefixes_are_closed(self) -> None:
        cases = [
            {"source_type": "spec-kit", "source_version": "1", "role": "persona", "path": ".specify/persona.md"},
            {"source_type": "bmad", "source_version": "6", "role": "persona", "path": "_bmad/persona.md"},
            {"source_type": "superpowers", "source_version": "1", "role": "spec", "path": "README.md"},
            {"source_type": "unknown", "source_version": "1", "role": "spec", "path": "docs/superpowers/x.md"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for entry in cases:
                manifest = _write_manifest(root, [entry])
                with self.assertRaises(self.artifacts.WorkflowArtifactError):
                    self.artifacts.load_source_manifest(root, manifest)


class WorkflowCompileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifacts = _load_module()

    def _root(self, tmp: str, docs: list[tuple[str, str, str, str]]) -> tuple[Path, object]:
        root = Path(tmp)
        entries = []
        for source_type, role, path, content in docs:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            entries.append({"source_type": source_type, "source_version": "1", "role": role, "path": path})
        bundle = self.artifacts.load_source_manifest(root, _write_manifest(root, entries))
        (root / "engineering/changes/change/change-spec.yaml").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "change_id": "change",
                    "objective": {"id": "OBJ-001", "statement": "native goal"},
                    "acceptance_criteria": [{"id": "AC-001", "statement": "safe import"}],
                    "invariants": [{"id": "INV-001", "statement": "native authority"}],
                    "forbidden_outcomes": [{"id": "FORBID-001", "statement": "no elevation"}],
                }
            ),
            encoding="utf-8",
        )
        return root, bundle

    def test_closed_adapters_map_only_advisory_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _root, bundle = self._root(
                tmp,
                [
                    ("spec-kit", "constitution", ".specify/memory/constitution.md", "# Constitution\n"),
                    ("spec-kit", "spec", ".specify/specs/x.md", "# Spec\n"),
                    ("bmad", "project-context", "_bmad-output/project-context.md", "# Context\n"),
                    ("bmad", "readiness", "_bmad-output/readiness.md", "# Ready\n"),
                    ("superpowers", "spec", "docs/superpowers/specs/x.md", "# Design\n"),
                    ("superpowers", "sdd-evidence", ".superpowers/sdd/x/progress.md", "# Progress\n"),
                ],
            )
            candidates = self.artifacts.adapt_sources(bundle)
            self.assertEqual(
                [item["candidate_kind"] for item in candidates],
                [
                    "governance-candidate",
                    "convergence-hint",
                    "governance-candidate",
                    "requirements-candidate",
                    "runtime-evidence",
                    "requirements-candidate",
                ],
            )
            self.assertFalse(next(item for item in candidates if item["role"] == "constitution")["authority"])
            self.assertFalse(next(item for item in candidates if item["role"] == "sdd-evidence")["receipt_eligible"])

    def test_task_graph_is_stable_and_route_bound(self) -> None:
        task = {
            "key": "core",
            "title": "Core",
            "depends_on": [],
            "covers": ["AC-001", "INV-001", "FORBID-001"],
            "files": ["src/core.py"],
            "interfaces": ["compile()"],
            "red": ["python3", "-m", "unittest", "tests.test_core"],
            "green": ["python3", "-m", "unittest", "tests.test_core"],
            "status": "pending",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root, bundle = self._root(
                tmp, [("spec-kit", "tasks", ".specify/specs/tasks.md", f"<!-- AGB-TASK {json.dumps(task)} -->\n")]
            )
            route = {
                "write_agent": "integration_implementer",
                "review_agents": ["code_reviewer", "security_reviewer"],
                "required_evidence": ["verification"],
            }
            first = self.artifacts.compile_task_graph(root, "change", bundle, route)
            self.assertEqual(first, self.artifacts.compile_task_graph(root, "change", bundle, route))
            self.assertEqual(first["write_agent"], "integration_implementer")
            self.assertTrue(first["tasks"][0]["task_id"].startswith("TASK-"))
            self.assertNotIn("tree_fingerprint", json.dumps(first))

    def test_verification_command_accepts_focused_static_landing_mode(self) -> None:
        command = [
            "python3",
            "scripts/grok_verify.py",
            "--mode",
            "focused-static-seo-landing",
        ]
        try:
            selected = self.artifacts._verification_command(command, "focused")
        except self.artifacts.WorkflowArtifactError as exc:
            self.fail(f"focused static landing mode is not allowlisted: {exc}")
        self.assertEqual(selected, command)

        with self.assertRaises(self.artifacts.WorkflowArtifactError):
            self.artifacts._verification_command(command + ["--profile", "base"], "focused")

    def test_unmodified_spec_kit_tasks_subset_compiles_phases_and_parallel_markers(self) -> None:
        content = """# Tasks
## Phase 1: Setup
- [ ] T001 [P] [US1] Implement AC-001 INV-001 FORBID-001 in src/loader.py
## Phase 2: Verify
- [ ] T002 [US1] Verify integration in tests/test_loader.py
"""
        with tempfile.TemporaryDirectory() as tmp:
            root, bundle = self._root(tmp, [("spec-kit", "tasks", ".specify/specs/tasks.md", content)])
            graph = self.artifacts.compile_task_graph(
                root,
                "change",
                bundle,
                {"write_agent": "writer", "review_agents": ["reviewer"], "required_evidence": ["verification"]},
            )
            tasks = {task["key"]: task for task in graph["tasks"]}
            self.assertEqual(set(tasks), {"t001", "t002"})
            self.assertEqual(tasks["t001"]["depends_on"], [])
            self.assertEqual(tasks["t002"]["depends_on"], [tasks["t001"]["task_id"]])
            self.assertEqual(tasks["t001"]["enrichment_required"], ["green", "interfaces", "red"])
            report = self.artifacts.converge(
                root,
                "change",
                bundle,
                graph,
                {"write_agent": "writer", "review_agents": ["reviewer"], "required_evidence": ["verification"]},
                current_fingerprint="a" * 64,
                receipt_errors=["verification: missing receipt"],
            )
            self.assertIn("needs-enrichment", {item["code"] for item in report["findings"]})

    def test_unmodified_bmad_story_subset_compiles_without_trusting_done_status(self) -> None:
        content = """# Story 1.2: Safe import
## Status
Draft
## Tasks / Subtasks
- [ ] Parse AC-001 INV-001 FORBID-001 in src/importer.py
"""
        with tempfile.TemporaryDirectory() as tmp:
            root, bundle = self._root(
                tmp,
                [
                    ("bmad", "stories", "_bmad-output/stories/1-2-safe-import.md", content),
                    (
                        "bmad",
                        "sprint-status",
                        "_bmad-output/sprint-status.yaml",
                        "development_status:\n  1-2-safe-import: done\n",
                    ),
                ],
            )
            graph = self.artifacts.compile_task_graph(
                root,
                "change",
                bundle,
                {"write_agent": "writer", "review_agents": [], "required_evidence": ["verification"]},
            )
            self.assertEqual(len(graph["tasks"]), 1)
            self.assertEqual(graph["tasks"][0]["source_status"], "pending")
            report = self.artifacts.converge(
                root,
                "change",
                bundle,
                graph,
                {"route_id": "r", "write_agent": "writer", "review_agents": [], "required_evidence": ["verification"]},
                current_fingerprint="a" * 64,
                receipt_errors=["verification: missing receipt"],
            )
            self.assertEqual(
                self.artifacts.effective_task_statuses(graph, ["verification: missing receipt"])[0]["effective_status"],
                "pending",
            )
            self.assertNotIn("advanced-status", {item["code"] for item in report["findings"]})

    def test_bmad_multi_epic_tasks_reset_identity_and_dependencies_per_heading(self) -> None:
        content = """# Epic 1: Loader
- [ ] Implement AC-001 INV-001 in src/loader.py
- [ ] Verify loader in tests/test_loader.py
# Epic 2: Exporter
- [ ] Implement FORBID-001 in src/exporter.py
- [ ] Verify exporter in tests/test_exporter.py
"""
        with tempfile.TemporaryDirectory() as tmp:
            root, bundle = self._root(tmp, [("bmad", "epics", "_bmad-output/epics.md", content)])
            graph = self.artifacts.compile_task_graph(
                root,
                "change",
                bundle,
                {"write_agent": "writer", "review_agents": [], "required_evidence": ["verification"]},
            )
            tasks = {task["key"]: task for task in graph["tasks"]}
            self.assertEqual(set(tasks), {"epic-1-001", "epic-1-002", "epic-2-001", "epic-2-002"})
            self.assertEqual(tasks["epic-1-001"]["depends_on"], [])
            self.assertEqual(tasks["epic-2-001"]["depends_on"], [])
            self.assertEqual(tasks["epic-1-002"]["depends_on"], [tasks["epic-1-001"]["task_id"]])
            self.assertEqual(tasks["epic-2-002"]["depends_on"], [tasks["epic-2-001"]["task_id"]])

    def test_graph_rejects_dependency_cycle_conflict_and_uncovered(self) -> None:
        base = {
            "title": "Task",
            "covers": ["AC-001", "INV-001", "FORBID-001"],
            "files": ["src/shared.py"],
            "interfaces": ["x()"],
            "red": ["python3", "-m", "unittest"],
            "green": ["python3", "-m", "unittest"],
            "status": "pending",
        }
        cases = [
            [{**base, "key": "a", "depends_on": ["missing"]}],
            [
                {**base, "key": "a", "depends_on": ["b"]},
                {**base, "key": "b", "depends_on": ["a"], "files": ["src/b.py"]},
            ],
            [{**base, "key": "a", "depends_on": []}, {**base, "key": "b", "depends_on": []}],
            [{**base, "key": "a", "depends_on": [], "covers": ["AC-001"]}],
        ]
        for tasks in cases:
            with self.subTest(tasks=tasks), tempfile.TemporaryDirectory() as tmp:
                content = "".join(f"<!-- AGB-TASK {json.dumps(task)} -->\n" for task in tasks)
                root, bundle = self._root(tmp, [("bmad", "stories", "_bmad-output/stories.md", content)])
                with self.assertRaises(self.artifacts.WorkflowArtifactError):
                    self.artifacts.compile_task_graph(
                        root,
                        "change",
                        bundle,
                        {"write_agent": "writer", "review_agents": ["reviewer"], "required_evidence": ["verification"]},
                    )

    def test_graph_rejects_shell_strings_and_authority_fields(self) -> None:
        task = {
            "key": "a",
            "title": "Task",
            "depends_on": [],
            "covers": ["AC-001", "INV-001", "FORBID-001"],
            "files": ["x.py"],
            "interfaces": ["x()"],
            "red": "python -m unittest",
            "green": ["python3", "-m", "unittest"],
            "status": "pending",
            "approval": "granted",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root, bundle = self._root(
                tmp, [("spec-kit", "tasks", ".specify/specs/tasks.md", f"<!-- AGB-TASK {json.dumps(task)} -->\n")]
            )
            with self.assertRaises(self.artifacts.WorkflowArtifactError):
                self.artifacts.compile_task_graph(
                    root,
                    "change",
                    bundle,
                    {"write_agent": "writer", "review_agents": [], "required_evidence": ["verification"]},
                )


class WorkflowConvergenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifacts = _load_module()

    def test_report_is_deterministic_and_blocks_placeholders_and_advanced_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            change = root / "engineering/changes/change"
            change.mkdir(parents=True)
            (change / "change-spec.yaml").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "change_id": "change",
                        "objective": {"id": "OBJ-001", "statement": "native goal"},
                        "acceptance_criteria": [{"id": "AC-001", "statement": "UNKNOWN"}],
                        "invariants": [],
                        "forbidden_outcomes": [],
                    }
                ),
                encoding="utf-8",
            )
            graph = {
                "schema_version": 1,
                "change_id": "change",
                "source_manifest_digest": "a" * 64,
                "write_agent": "writer",
                "review_agents": [],
                "tasks": [
                    {
                        "task_id": "TASK-" + "b" * 12,
                        "key": "x",
                        "title": "X",
                        "depends_on": [],
                        "covers": ["AC-001"],
                        "files": ["x.py"],
                        "interfaces": ["x()"],
                        "red": ["python3", "-m", "unittest"],
                        "green": ["python3", "-m", "unittest"],
                        "source_status": "complete",
                        "enrichment_required": [],
                        "source_sha256": "d" * 64,
                    }
                ],
            }
            graph["graph_digest"] = self.artifacts.digest_without(graph, "graph_digest")
            route = {"write_agent": "writer", "review_agents": [], "required_evidence": ["verification"]}
            first = self.artifacts.converge(
                root,
                "change",
                None,
                graph,
                route,
                current_fingerprint="a" * 64,
                receipt_errors=["verification: missing receipt"],
            )
            self.assertEqual(
                first,
                self.artifacts.converge(
                    root,
                    "change",
                    None,
                    graph,
                    route,
                    current_fingerprint="a" * 64,
                    receipt_errors=["verification: missing receipt"],
                ),
            )
            self.assertEqual(first["status"], "block")
            codes = {finding["code"] for finding in first["findings"]}
            self.assertEqual(codes, {"placeholder"})
            self.assertEqual(
                self.artifacts.effective_task_statuses(graph, ["verification: missing receipt"])[0]["effective_status"],
                "pending",
            )
            self.assertTrue(all(finding["disposition"] for finding in first["findings"]))

    def test_report_detects_explicit_goal_criterion_architecture_and_status_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            change = root / "engineering/changes/change"
            workflow = change / "workflow"
            workflow.mkdir(parents=True)
            native = {
                "schema_version": 2,
                "change_id": "change",
                "objective": {"id": "OBJ-001", "statement": "native goal"},
                "acceptance_criteria": [{"id": "AC-001", "statement": "native criterion"}],
                "invariants": [],
                "forbidden_outcomes": [],
            }
            (change / "change-spec.yaml").write_text(json.dumps(native), encoding="utf-8")
            (change / "tasks.md").write_text(
                '<!-- AGB-TASK-STATUS {"key":"core","status":"complete"} -->\n', encoding="utf-8"
            )
            architecture = root / "architecture/system.yaml"
            architecture.parent.mkdir()
            architecture.write_text(json.dumps({"architecture_id": "ARCH-NATIVE"}), encoding="utf-8")
            claims = (
                "\n".join(
                    [
                        '<!-- AGB-CLAIM {"kind":"objective","id":"OBJ-001","statement":"foreign goal"} -->',
                        '<!-- AGB-CLAIM {"kind":"criterion","id":"AC-001","statement":"foreign criterion"} -->',
                        '<!-- AGB-CLAIM {"kind":"architecture","id":"ARCH-FOREIGN","statement":"foreign architecture"} -->',
                    ]
                )
                + "\n"
            )
            source = root / ".specify/specs/spec.md"
            source.parent.mkdir(parents=True)
            source.write_text(claims, encoding="utf-8")
            manifest = _write_manifest(
                root,
                [{"source_type": "spec-kit", "source_version": "1", "role": "spec", "path": ".specify/specs/spec.md"}],
            )
            bundle = self.artifacts.load_source_manifest(root, manifest)
            graph = {
                "schema_version": 1,
                "change_id": "change",
                "source_manifest_digest": bundle.manifest_digest,
                "write_agent": "writer",
                "review_agents": [],
                "tasks": [
                    {
                        "task_id": "TASK-" + "a" * 12,
                        "key": "core",
                        "title": "Core",
                        "depends_on": [],
                        "covers": ["AC-001"],
                        "files": ["x.py"],
                        "interfaces": ["x()"],
                        "red": ["python3", "-m", "unittest"],
                        "green": ["python3", "-m", "unittest"],
                        "source_status": "pending",
                        "enrichment_required": [],
                        "source_sha256": "b" * 64,
                    }
                ],
            }
            graph["graph_digest"] = self.artifacts.digest_without(graph, "graph_digest")
            report = self.artifacts.converge(
                root,
                "change",
                bundle,
                graph,
                {"write_agent": "writer", "review_agents": [], "required_evidence": ["verification"]},
                current_fingerprint="a" * 64,
                receipt_errors=["verification: missing receipt"],
            )
            codes = {finding["code"] for finding in report["findings"]}
            self.assertTrue(
                {"goal-conflict", "criterion-conflict", "architecture-contradiction", "status-drift"}.issubset(codes)
            )



class CurrentUpstreamFormatTests(unittest.TestCase):
    """Parser contract against CURRENT upstream document grammar.

    Provenance (2026-09-15, gh api at exact tags): the two spec-kit emphasis
    lines are byte-verbatim from github/spec-kit v1.0.7
    templates/spec-template.md:96 and templates/plan-template.md:41, and
    ``NEEDS CLARIFICATION`` is upstream's unresolved-requirement token.
    Task rows, ``## Epic N:``/``### Story N.M:`` headings, dashed
    ``development_status:`` keys and the bare ``Status:`` line mirror the
    v1.0.7/v6.12.0 grammars with synthesized content; letter-suffixed story
    ids (``1.2a``) and the ``ready-for-review``/``in-review`` tokens are
    parser-side grammar extensions over template samples (``in-review`` is
    real in v6.12 build-spec front matter), kept here deliberately so newer
    documents do not silently drop.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.artifacts = _load_module()

    def _docs(self, root: Path, docs: list[tuple[str, str, str, str]], version: str) -> Path:
        entries = []
        for source_type, role, path, content in docs:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            entries.append({"source_type": source_type, "source_version": version, "role": role, "path": path})
        return _write_manifest(root, entries)

    def test_spec_kit_emphasis_loads_but_yaml_authority_fails_closed(self) -> None:
        emphasis = (
            "# Specification: Authentication\n"
            "*Example of marking unclear requirements:*\n"
            "- [ ] T001 [P] [US1] Create skeleton in src/a.py\n"
        )
        gate = "*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._docs(
                root,
                [
                    ("spec-kit", "spec", ".specify/specs/001-auth/spec.md", emphasis),
                    ("spec-kit", "plan", "specs/001-auth/plan.md", gate),
                ],
                "1.0.7",
            )
            bundle = self.artifacts.load_source_manifest(root, manifest)
            self.assertEqual(len(bundle.sources), 2)
            self.assertEqual({s.identity["source_version"] for s in bundle.sources}, {"1.0.7"})
        for hostile in (
            "base: &anchor\n",
            "name: *anchor\n",
            "- *anchor\n",
            "auth:\n  <<: *defaults\n",
            "type: !!python/object:evil\n",
            "&anchor\n",
            "- &anchor\n",
        ):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest = self._docs(root, [("spec-kit", "spec", ".specify/specs/bad.md", hostile)], "1.0.7")
                with self.assertRaises(self.artifacts.WorkflowArtifactError):
                    self.artifacts.load_source_manifest(root, manifest)

    def test_spec_kit_tasks_under_specs_prefix_parse_current_grammar(self) -> None:
        content = """# Tasks: Authentication Feature

## Phase 1: Setup
- [ ] T001 [P] Create project skeleton per **research.md**
- [ ] T002 [US1] Implement User model in src/models/user.py

## Phase 2: User Story 1
- [ ] T003 [P] [US1] Add repository in src/repos/user.py (depends on T002)
- [ ] [missing-id] not a parseable upstream row
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._docs(
                root, [("spec-kit", "tasks", "specs/001-authentication/tasks.md", content)], "1.0.7"
            )
            bundle = self.artifacts.load_source_manifest(root, manifest)
            tasks = self.artifacts._native_framework_tasks(bundle.sources[0])
            self.assertEqual([task["key"] for task in tasks], ["t001", "t002", "t003"])
            self.assertEqual(tasks[0]["depends_on"], [])
            self.assertEqual(tasks[1]["depends_on"], ["t001"])
            self.assertEqual(tasks[2]["depends_on"], ["t001", "t002"])

    def test_bmad_v612_heading_levels_produce_tasks_the_h1_parser_missed(self) -> None:
        epics = """# Auth System - Epic Breakdown

## Epic 1: Foundation

### Story 1.1: Loader bootstraps
- [ ] Implement AC-001 INV-001 FORBID-001 in src/loader.py

### Story 1.2: Exporter binds
- [ ] Wire FORBID-001 in src/export.py

## Epic 2: Operations
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._docs(root, [("bmad", "epics", "_bmad-output/epics.md", epics)], "6.12.0")
            bundle = self.artifacts.load_source_manifest(root, manifest)
            tasks = self.artifacts._native_framework_tasks(bundle.sources[0])
            self.assertEqual([task["key"] for task in tasks], ["story-1-1-001", "story-1-2-001"])
            self.assertEqual(tasks[1]["depends_on"], [])  # heading resets the dependency chain

    def test_bmad_dotted_story_ids_do_not_collide(self) -> None:
        content = """### Story 1.1.1: Deep one
- [ ] Do AC-001 in src/a.py
### Story 1.1.2: Deep two
- [ ] Do AC-001 in src/b.py
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._docs(root, [("bmad", "stories", "_bmad-output/stories/deep.md", content)], "6.12.0")
            bundle = self.artifacts.load_source_manifest(root, manifest)
            tasks = self.artifacts._native_framework_tasks(bundle.sources[0])
            self.assertEqual([task["key"] for task in tasks], ["story-1-1-1-001", "story-1-1-2-001"])

    def test_sprint_status_advances_only_from_nested_key_values(self) -> None:
        story = """# Story 9.9: Solo

Status: ready-for-dev

## Tasks / Subtasks
- [ ] Do AC-001 INV-001 FORBID-001 in src/solo.py
"""
        sprint = "development_status:\n  story-9-9: in-progress\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._docs(
                root,
                [
                    ("bmad", "stories", "_bmad-output/stories/9-9-solo.md", story),
                    ("bmad", "sprint-status", "_bmad-output/sprint-status.yaml", sprint),
                ],
                "6.12.0",
            )
            bundle = self.artifacts.load_source_manifest(root, manifest)
            self.assertEqual(self.artifacts._advanced_status_hints(bundle), set())  # non-terminal status advances nothing
            sprint_path = root / "_bmad-output/sprint-status.yaml"
            sprint_path.write_text("development_status:\n  story-9-9: done\n", encoding="utf-8")
            advanced = self.artifacts.load_source_manifest(root, manifest)
            self.assertEqual(self.artifacts._advanced_status_hints(advanced), {"story-9-9-001"})

    def test_bmad_v612_front_matter_status_advances_story_tasks(self) -> None:
        epics = """# Auth System - Epic Breakdown

## Epic 1: Foundation

### Story 1.1: Loader bootstraps

### Story 1.2a: Legacy shim

## Epic 2: Export
"""
        story = """---
status: 'in-review'
route: bmad-build
deferred: []
---

# Story 1.1: Loader bootstraps

## Tasks / Subtasks
- [ ] Implement AC-001 INV-001 FORBID-001 in src/loader.py
- [x] Verify loader in tests/test_loader.py
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._docs(
                root,
                [
                    ("bmad", "epics", "_bmad-output/epics.md", epics),
                    ("bmad", "stories", "_bmad-output/stories/1-1-loader-bootstraps.md", story),
                ],
                "6.12.0",
            )
            bundle = self.artifacts.load_source_manifest(root, manifest)
            by_path = {source.identity["path"]: source for source in bundle.sources}
            self.assertEqual(self.artifacts._native_framework_tasks(by_path["_bmad-output/epics.md"]), [])
            story_tasks = self.artifacts._native_framework_tasks(
                by_path["_bmad-output/stories/1-1-loader-bootstraps.md"]
            )
            self.assertEqual([task["key"] for task in story_tasks], ["story-1-1-001", "story-1-1-002"])
            self.assertEqual(story_tasks[0]["status"], "pending")
            self.assertEqual(story_tasks[1]["status"], "complete")
            self.assertEqual(self.artifacts._advanced_status_hints(bundle), {"story-1-1-001", "story-1-1-002"})

    def test_bmad_bare_status_line_vocabulary_is_total(self) -> None:
        for status, terminal in (
            ("Status: ready-for-dev", False),
            ("Status: in-progress", False),
            ("Status: blocked", False),
            ("Status: review", True),
            ("Status: done", True),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest = self._docs(
                    root,
                    [
                        (
                            "bmad",
                            "stories",
                            "_bmad-output/stories/3-1-x.md",
                            f"# Story 3.1: X\n\n{status}\n\n## Tasks / Subtasks\n- [ ] Do AC-001 in src/x.py\n",
                        )
                    ],
                    "6.12.0",
                )
                bundle = self.artifacts.load_source_manifest(root, manifest)
                hints = self.artifacts._advanced_status_hints(bundle)
                self.assertEqual(bool(hints), terminal, status)

    def test_receipt_kind_sets_match_and_domain_kinds_validate(self) -> None:
        import sys

        for entry in (str(ROOT), str(ROOT / ".grok-stack")):
            if entry not in sys.path:
                sys.path.insert(0, entry)
        from adaptive_grok import receipts as canonical

        self.assertEqual(set(self.artifacts.RECEIPT_KINDS), set(canonical.RECEIPT_KINDS))
        router_src = (ROOT / ".grok-stack/adaptive_grok/router.py").read_text(encoding="utf-8")
        emitted = set(re.findall(r"evidence\.append\('([a-z_]+)'\)", router_src))
        self.assertTrue(emitted, "router emits no receipt kinds")
        self.assertEqual(emitted - {"verification"}, set(canonical.RECEIPT_KINDS) - {"verification"})
        self.assertTrue({"bitrix_review", "data_review"}.issubset(canonical.RECEIPT_KINDS))
        route = {
            "route_id": "route",
            "write_agent": "writer",
            "review_agents": ["reviewer"],
            "required_evidence": [
                "verification",
                "code_review",
                "test_review",
                "bitrix_review",
                "security_review",
                "data_review",
                "release_review",
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            gaps = canonical.validate_evidence(Path(tmp), route)
        self.assertEqual(len(gaps), 7)
        self.assertFalse(any("closed receipt set" in gap for gap in gaps))

    def test_placeholder_vocabulary_covers_spec_kit_clarification_token(self) -> None:
        placeholder = self.artifacts.PLACEHOLDER
        self.assertTrue(placeholder.search("[NEEDS CLARIFICATION: auth method not specified]"))
        self.assertTrue(placeholder.search("TBD"))
        self.assertTrue(placeholder.search("TODO"))
        self.assertFalse(placeholder.search("The status is stable and documented"))


if __name__ == "__main__":
    unittest.main()
