from __future__ import annotations

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
