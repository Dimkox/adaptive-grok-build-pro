from __future__ import annotations

import importlib.util
import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "trust-ci/holdout.example/change_spec_validate.py"


def _load():
    spec = importlib.util.spec_from_file_location("change_spec_validate", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _valid(change_id: str) -> dict:
    return {
        "schema_version": 2, "change_id": change_id,
        "objective": {"id": "OBJ-001", "statement": "holdout", "success_metric": "exit", "target": "zero"},
        "risk": {"tier": "red", "domains": ["security"]},
        "acceptance_criteria": [{"id": "AC-001", "statement": "valid", "evidence": [{"production_signal": "SIG-001"}]}],
        "invariants": [],
        "forbidden_outcomes": [{"id": "FORBID-001", "statement": "downgrade", "evidence": [{"attestation": "trust-ci"}]}],
        "contracts": {"openapi": [], "json_schema": [], "events": []},
        "observability": [{"id": "SIG-001", "metric": "holdout_exit", "proves": ["OBJ-001"]}],
        "rollback": {"strategy": "forward_fix", "maximum_steps": 1},
        "approvals": {"required_scopes": ["governance"]},
    }


class HoldoutChangeSpecTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.root, check=True)
        (self.root / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=self.root, check=True)
        self.base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _commit_spec(self, raw: bytes) -> tuple[str, Path]:
        path = self.root / "engineering/changes/20260826-holdout/change-spec.yaml"
        path.parent.mkdir(parents=True)
        path.write_bytes(raw)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "spec"], cwd=self.root, check=True)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()
        return head, path

    def _assert_document_rejected(self, mutate) -> None:
        document = copy.deepcopy(_valid("20260826-holdout"))
        mutate(document)
        with self.assertRaises(SystemExit):
            self.module._validate_document("engineering/changes/x/change-spec.yaml", document)

    def test_independent_exact_sha_validation_passes(self) -> None:
        head, _ = self._commit_spec(json.dumps(_valid("20260826-holdout"), sort_keys=True).encode())
        self.module.validate(self.root, base_sha=self.base, head_sha=head)
        self.assertNotIn("adaptive_grok.spec", MODULE_PATH.read_text(encoding="utf-8"))

    def test_missing_sha_and_malformed_json_fail_closed(self) -> None:
        with self.assertRaises(SystemExit):
            with patch.dict(os.environ, {}, clear=True):
                self.module.validate(self.root)
        head, _ = self._commit_spec(b"schema_version: 2\n")
        with self.assertRaises(SystemExit):
            self.module.validate(self.root, base_sha=self.base, head_sha=head)

    def test_symlink_spec_fails_closed(self) -> None:
        outside = self.root / "outside.json"
        outside.write_text(json.dumps(_valid("20260826-holdout")), encoding="utf-8")
        path = self.root / "engineering/changes/20260826-holdout/change-spec.yaml"
        path.parent.mkdir(parents=True)
        path.symlink_to(outside)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "symlink"], cwd=self.root, check=True)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()
        with self.assertRaises(SystemExit):
            self.module.validate(self.root, base_sha=self.base, head_sha=head)

    def test_ancestor_symlink_spec_fails_closed(self) -> None:
        outside = Path(self.temp.name) / "outside"
        path = outside / "changes/20260826-holdout/change-spec.yaml"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(_valid("20260826-holdout")), encoding="utf-8")
        (self.root / "engineering").symlink_to(outside)
        with self.assertRaises(SystemExit):
            self.module._read(self.root, "engineering/changes/20260826-holdout/change-spec.yaml")

    def test_nested_v2_contract_is_fail_closed(self) -> None:
        mutations = [
            lambda d: d["objective"].pop("statement"),
            lambda d: d["acceptance_criteria"][0].update(statement=""),
            lambda d: d["acceptance_criteria"][0].update(evidence=[{"test": None}]),
            lambda d: d["acceptance_criteria"][0].update(evidence=[{"test": ""}]),
            lambda d: d["forbidden_outcomes"][0].update(evidence=[{"receipt": "bogus"}]),
            lambda d: d["observability"][0].update(proves=[]),
            lambda d: d["observability"][0].update(proves=["OBJ-999"]),
            lambda d: d.update(contracts={"openapi": ["../escape"], "json_schema": [], "events": []}),
            lambda d: d.update(contracts={"openapi": [], "json_schema": [], "events": [], "other": []}),
            lambda d: d.update(rollback={"strategy": "forward_fix", "maximum_steps": True}),
            lambda d: d.update(rollback={"strategy": "forward_fix", "maximum_steps": 21}),
            lambda d: d.update(approvals={"required_scopes": True}),
            lambda d: d.update(approvals={"required_scopes": [""]}),
            lambda d: d.update(approvals={"required_scopes": [{}]}),
            lambda d: d["risk"].update(domains=[{}]),
        ]
        for mutate in mutations:
            with self.subTest(mutate=repr(mutate)):
                self._assert_document_rejected(mutate)

    def test_deep_json_fails_with_controlled_error(self) -> None:
        raw = b'{"schema_version":2,"x":' + (b"[" * 2000) + (b"]" * 2000) + b"}"
        with self.assertRaises(SystemExit):
            self.module._parse("deep/change-spec.yaml", raw)

    def test_changed_v1_is_rejected_and_unchanged_v1_is_ignored(self) -> None:
        legacy = self.root / "engineering/changes/legacy/change-spec.yaml"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "legacy baseline"], cwd=self.root, check=True)
        legacy_base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()
        head, _ = self._commit_spec(json.dumps(_valid("20260826-holdout"), sort_keys=True).encode())
        self.module.validate(self.root, base_sha=legacy_base, head_sha=head)
        legacy.write_text(json.dumps({"schema_version": 1, "changed": True}), encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "legacy changed"], cwd=self.root, check=True)
        changed_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()
        with self.assertRaises(SystemExit):
            self.module.validate(self.root, base_sha=head, head_sha=changed_head)

    def test_bad_or_mismatched_sha_and_deleted_spec_fail(self) -> None:
        head, path = self._commit_spec(json.dumps(_valid("20260826-holdout"), sort_keys=True).encode())
        with self.assertRaises(SystemExit):
            self.module.validate(self.root, base_sha="bad", head_sha=head)
        with self.assertRaises(SystemExit):
            self.module.validate(self.root, base_sha=self.base, head_sha=self.base)
        path.unlink()
        subprocess.run(["git", "add", "-u"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "delete spec"], cwd=self.root, check=True)
        deleted_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()
        with self.assertRaises(SystemExit):
            self.module.validate(self.root, base_sha=head, head_sha=deleted_head)

    def test_diff_failure_is_fail_closed(self) -> None:
        head, _ = self._commit_spec(json.dumps(_valid("20260826-holdout"), sort_keys=True).encode())
        original = self.module._git
        def failing_git(root, *args):
            if args and args[0] == "diff":
                raise SystemExit("diff failed")
            return original(root, *args)
        with patch.object(self.module, "_git", side_effect=failing_git):
            with self.assertRaises(SystemExit):
                self.module.validate(self.root, base_sha=self.base, head_sha=head)

    def test_multiple_changed_specs_pass_exact_sha(self) -> None:
        for name in ('alpha', 'bravo'):
            path = self.root / f'engineering/changes/20260826-{name}/change-spec.yaml'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(_valid(f'20260826-{name}'), sort_keys=True), encoding='utf-8')
        subprocess.run(['git', 'add', '.'], cwd=self.root, check=True)
        subprocess.run(['git', 'commit', '-qm', 'multiple specs'], cwd=self.root, check=True)
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.root, text=True).strip()
        self.module.validate(self.root, base_sha=self.base, head_sha=head)

    def test_exact_sha_size_node_and_file_count_limits_fail_closed(self) -> None:
        oversized = b'{"schema_version":2,"padding":"' + b'a' * self.module.MAX_BYTES + b'"}'
        head, _ = self._commit_spec(oversized)
        with self.assertRaises(SystemExit):
            self.module.validate(self.root, base_sha=self.base, head_sha=head)

        node_base = head
        node_path = self.root / 'engineering/changes/20260826-nodes/change-spec.yaml'
        node_path.parent.mkdir(parents=True)
        node_path.write_text(json.dumps({'schema_version': 2, 'nodes': [None] * (self.module.MAX_NODES + 1)}), encoding='utf-8')
        subprocess.run(['git', 'add', '.'], cwd=self.root, check=True)
        subprocess.run(['git', 'commit', '-qm', 'node limit'], cwd=self.root, check=True)
        node_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.root, text=True).strip()
        with self.assertRaises(SystemExit):
            self.module.validate(self.root, base_sha=node_base, head_sha=node_head)

        file_base = node_head
        for index in range(self.module.MAX_FILES + 1):
            path = self.root / f'engineering/changes/20260826-many-{index:03d}/change-spec.yaml'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(_valid(f'20260826-many-{index:03d}')), encoding='utf-8')
        subprocess.run(['git', 'add', '.'], cwd=self.root, check=True)
        subprocess.run(['git', 'commit', '-qm', 'file count'], cwd=self.root, check=True)
        file_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.root, text=True).strip()
        with self.assertRaises(SystemExit):
            self.module.validate(self.root, base_sha=file_base, head_sha=file_head)


if __name__ == "__main__":
    unittest.main()
