from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator
import pytest


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "factory" / "src"))

from adaptive_factory.context_contracts import ContextManifestV1  # noqa: E402
from adaptive_factory.contracts import ContractError  # noqa: E402


SCHEMA = ROOT / "factory/contracts/jsonschema/context-manifest.v1.schema.json"


def context_facts():
    content = "safe project fact"
    source = {
        "path": "AGENTS.md",
        "kind": "instruction",
        "content": content,
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
        "reason": "affected_path",
        "applicable_scope": "repository",
        "mode": "full",
    }
    return {
        "schema_version": 1,
        "builder_version": "native-1",
        "tenant_id": "tenant-1",
        "repository_id": "owner/project",
        "source_snapshot": {"base_sha": "1" * 40, "head_sha": "2" * 40, "dirty_fingerprint": "3" * 64},
        "change_id": "change-1",
        "route_id": "route-1",
        "change_spec_digest": "4" * 64,
        "observed_at": "2026-09-30T12:00:00Z",
        "mandatory_sources": [source],
        "selected_sources": [],
        "rule_bindings": [{
            "criterion_id": "AC-001", "rule_id": "RULE-1", "revision": "1",
            "repository_id": "owner/project", "source_digest": source["sha256"],
            "source_path": source["path"], "applicable_scope": source["applicable_scope"],
            "mode": source["mode"], "status": "active",
        }],
    }


def test_draft_2020_12_and_python_share_structural_admission_corpus():
    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    valid = context_facts()
    assert not list(validator.iter_errors(valid))
    ContextManifestV1.from_dict(valid)

    mutations = (
        lambda value: value.update(builder_version="bad value"),
        lambda value: value["mandatory_sources"][0].update(path=".env"),
        lambda value: value["mandatory_sources"][0].update(path="keys/private.pem"),
        lambda value: value["mandatory_sources"][0].update(content="password=synthetic-secret"),
        lambda value: value["mandatory_sources"][0].update(reason="bad reason"),
        lambda value: value["mandatory_sources"][0].update(mode="summary"),
        lambda value: value["rule_bindings"][0].pop("source_digest"),
    )
    for mutate in mutations:
        candidate = deepcopy(valid)
        mutate(candidate)
        assert list(validator.iter_errors(candidate))
        with pytest.raises(ContractError):
            ContextManifestV1.from_dict(candidate)
