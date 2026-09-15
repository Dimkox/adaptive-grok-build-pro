from __future__ import annotations

import importlib.util
import io
import json
import multiprocessing
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ARTIFACTS = _load("adaptive_grok.workflow_artifacts", ROOT / ".grok-stack/adaptive_grok/workflow_artifacts.py")
CLI = _load("workflow_artifacts_cli", ROOT / "scripts/grok_artifacts.py")


def _run_cli_process(root: str, argv: list[str], queue: multiprocessing.Queue) -> None:
    output = io.StringIO()
    project = Path(root)
    with (
        patch.object(sys, "argv", ["grok_artifacts.py", *argv]),
        patch.object(CLI, "ROOT", project),
        patch.object(CLI, "find_root", lambda *_: project),
        redirect_stdout(output),
    ):
        queue.put((CLI.main(), output.getvalue()))


class WorkflowArtifactsCliTests(unittest.TestCase):
    def _project(self, tmp: str) -> tuple[Path, str]:
        root = Path(tmp)
        change_id = "change"
        change = root / "engineering/changes" / change_id
        workflow = change / "workflow"
        workflow.mkdir(parents=True)
        source = root / ".specify/specs/tasks.md"
        source.parent.mkdir(parents=True)
        task = {
            "key": "core",
            "title": "Core",
            "depends_on": [],
            "covers": ["AC-001", "INV-001", "FORBID-001"],
            "files": ["x.py"],
            "interfaces": ["x()"],
            "red": ["python3", "-m", "unittest"],
            "green": ["python3", "-m", "unittest"],
            "status": "pending",
        }
        source.write_text(f"<!-- AGB-TASK {json.dumps(task)} -->\n", encoding="utf-8")
        (workflow / "manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "sources": [
                        {
                            "source_type": "spec-kit",
                            "source_version": "1",
                            "role": "tasks",
                            "path": ".specify/specs/tasks.md",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (change / "change-spec.yaml").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "change_id": change_id,
                    "objective": {"id": "OBJ-001", "statement": "Goal"},
                    "acceptance_criteria": [{"id": "AC-001", "statement": "A"}],
                    "invariants": [{"id": "INV-001", "statement": "I"}],
                    "forbidden_outcomes": [{"id": "FORBID-001", "statement": "F"}],
                }
            ),
            encoding="utf-8",
        )
        (root / ".grok-stack/runtime").mkdir(parents=True)
        (root / ".grok-stack/runtime/active-route.json").write_text(
            json.dumps(
                {
                    "route_id": "route",
                    "write_agent": "writer",
                    "review_agents": ["reviewer"],
                    "required_evidence": ["verification"],
                }
            ),
            encoding="utf-8",
        )
        (root / ".grok-stack/runtime/active-change.json").write_text(
            json.dumps({"change_id": change_id, "path": f"engineering/changes/{change_id}"}), encoding="utf-8"
        )
        return root, change_id

    def _run(self, root: Path, argv: list[str]) -> tuple[int, dict]:
        output = io.StringIO()
        with (
            patch.object(sys, "argv", ["grok_artifacts.py", *argv]),
            patch.object(CLI, "ROOT", root),
            patch.object(CLI, "find_root", lambda *_: root),
            redirect_stdout(output),
        ):
            code = CLI.main()
        return code, json.loads(output.getvalue())

    def test_compile_is_read_only_by_default_and_cas_write_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, change_id = self._project(tmp)
            target = root / f"engineering/changes/{change_id}/workflow/task-graph.json"
            code, result = self._run(root, ["compile", "--change-id", change_id])
            self.assertEqual(code, 0)
            self.assertFalse(target.exists())
            self.assertEqual(result["status"], "compiled")
            code, _ = self._run(root, ["compile", "--change-id", change_id, "--write", "--expected-digest", "0" * 64])
            self.assertEqual(code, 0)
            self.assertTrue(target.is_file())
            before = target.read_bytes()
            code, _ = self._run(root, ["compile", "--change-id", change_id, "--write", "--expected-digest", "f" * 64])
            self.assertEqual(code, 1)
            self.assertEqual(target.read_bytes(), before)

    def test_runtime_authority_rejects_symlink_and_unknown_route_fields(self) -> None:
        for filename in ("active-route.json", "active-change.json"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                root, change_id = self._project(tmp)
                runtime = root / ".grok-stack/runtime"
                target = runtime / filename
                outside = root / f"outside-{filename}"
                outside.write_bytes(target.read_bytes())
                target.unlink()
                target.symlink_to(outside)
                code, result = self._run(root, ["compile", "--change-id", change_id])
                self.assertEqual(code, 1)
                self.assertIn(result["code"], {"io", "file", "route", "change"})

        with tempfile.TemporaryDirectory() as tmp:
            root, change_id = self._project(tmp)
            route_path = root / ".grok-stack/runtime/active-route.json"
            route = json.loads(route_path.read_text(encoding="utf-8"))
            route["unexpected"] = True
            route_path.write_text(json.dumps(route), encoding="utf-8")
            code, result = self._run(root, ["compile", "--change-id", change_id])
            self.assertEqual(code, 1)
            self.assertEqual(result["code"], "route")

    def test_runtime_authority_fifo_fails_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, change_id = self._project(tmp)
            route = root / ".grok-stack/runtime/active-route.json"
            route.unlink()
            os.mkfifo(route)
            queue: multiprocessing.Queue = multiprocessing.Queue()
            process = multiprocessing.Process(
                target=_run_cli_process,
                args=(str(root), ["compile", "--change-id", change_id], queue),
            )
            process.start()
            process.join(0.5)
            if process.is_alive():
                process.terminate()
                process.join()
            self.assertFalse(process.is_alive())
            code, output = queue.get(timeout=1)
            self.assertEqual(code, 1)
            self.assertIn(json.loads(output)["code"], {"file", "io"})

    def test_export_is_marked_non_authoritative_and_never_mutates_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, change_id = self._project(tmp)
            source = root / ".specify/specs/tasks.md"
            before = source.read_bytes()
            target = root / f"engineering/changes/{change_id}/workflow/exports/spec-kit.md"
            code, _ = self._run(
                root, ["export", "spec-kit", "--change-id", change_id, "--write", "--expected-digest", "0" * 64]
            )
            self.assertEqual(code, 0)
            self.assertIn("NON-AUTHORITATIVE", target.read_text(encoding="utf-8"))
            self.assertEqual(source.read_bytes(), before)

    def test_export_rejects_symlink_parent_without_external_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, change_id = self._project(tmp)
            outside = root / "outside"
            outside.mkdir()
            exports = root / f"engineering/changes/{change_id}/workflow/exports"
            exports.symlink_to(outside, target_is_directory=True)
            code, _ = self._run(
                root, ["export", "spec-kit", "--change-id", change_id, "--write", "--expected-digest", "0" * 64]
            )
            self.assertEqual(code, 1)
            self.assertEqual(list(outside.iterdir()), [])

    def test_cas_rejects_symlink_workflow_directory_without_external_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, change_id = self._project(tmp)
            workflow = root / f"engineering/changes/{change_id}/workflow"
            workflow.rename(workflow.with_name("workflow-original"))
            outside = root / "outside"
            outside.mkdir()
            workflow.symlink_to(outside, target_is_directory=True)

            with self.assertRaises(ARTIFACTS.WorkflowArtifactError):
                ARTIFACTS.cas_write(root, change_id, "exports/test.md", b"projection", "0" * 64)
            self.assertEqual(list(outside.iterdir()), [])

    def test_validate_blocks_stale_stored_report_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, change_id = self._project(tmp)
            self._run(root, ["compile", "--change-id", change_id, "--write", "--expected-digest", "0" * 64])
            self._run(root, ["converge", "--change-id", change_id, "--write", "--expected-digest", "0" * 64])
            report = root / f"engineering/changes/{change_id}/workflow/convergence-report.json"
            data = json.loads(report.read_text())
            data["report_digest"] = "f" * 64
            report.write_text(json.dumps(data), encoding="utf-8")
            before = report.read_bytes()
            code, result = self._run(root, ["validate", "--change-id", change_id])
            self.assertEqual(code, 1)
            self.assertFalse(result["ok"])
            self.assertEqual(report.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
