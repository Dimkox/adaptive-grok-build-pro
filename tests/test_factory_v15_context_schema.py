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


def test_draft_2020_12_schema_is_structural_and_python_is_mandatory_admission():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["x-admission"] == {
        "level": "structural",
        "semantic_validator": "adaptive_factory.context_contracts.ContextManifestV1.from_dict",
        "semantic_validation_required": True,
        "semantic_checks": ["utf8_byte_limits", "secret_detection", "content_digest", "source_binding", "safe_path"],
    }
    validator = Draft202012Validator(schema)
    valid = context_facts()
    for harmless in (
        "safe project fact",
        "Token budgets and authorization policies contain no credentials.",
        "Secret detection documents private key handling without carrying a value.",
        "NoAuthorization=harmless structural example",
    ):
        candidate = deepcopy(valid)
        _replace_bound_content(candidate, harmless)
        assert not list(validator.iter_errors(candidate))
        ContextManifestV1.from_dict(candidate)

    mutations = (
        lambda value: value.update(builder_version="bad value"),
        lambda value: value["mandatory_sources"][0].update(path=".env"),
        lambda value: value["mandatory_sources"][0].update(path="keys/private.pem"),
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

    for semantically_unsafe in (
        "password=synthetic-secret",
        "Authorization: Basic synthetic-value",
        "Bearer synthetic-token",
        "-----BEGIN " + "PRIVATE KEY-----synthetic-----END " + "PRIVATE KEY-----",
        "github_pat_syntheticvalue",
    ):
        candidate = deepcopy(valid)
        _replace_bound_content(candidate, semantically_unsafe)
        assert not list(validator.iter_errors(candidate))
        with pytest.raises(ContractError, match="secret_content"):
            ContextManifestV1.from_dict(candidate)

    unicode_candidate = deepcopy(valid)
    _replace_bound_content(unicode_candidate, "é" * 3000)
    assert not list(validator.iter_errors(unicode_candidate))
    with pytest.raises(ContractError, match="invalid_text: content"):
        ContextManifestV1.from_dict(unicode_candidate)


def _replace_bound_content(value, content):
    source = value["mandatory_sources"][0]
    source["content"] = content
    source["sha256"] = hashlib.sha256(content.encode()).hexdigest()
    binding = value["rule_bindings"][0]
    binding["source_digest"] = source["sha256"]
    binding["source_path"] = source["path"]
    binding["applicable_scope"] = source["applicable_scope"]
    binding["mode"] = source["mode"]
