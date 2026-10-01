from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

from tests.json_schema_subset import SchemaDefinitionError, SubsetValidator


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


class ContextManifestSchemaTests(unittest.TestCase):
    def test_schema_preflight_rejects_malformed_unused_branches_and_annotations(
        self,
    ) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        malformed_branch = deepcopy(schema)
        malformed_branch["properties"]["source_snapshot"]["properties"][
            "dirty_fingerprint"
        ]["anyOf"].append(7)
        with self.assertRaises(SchemaDefinitionError):
            SubsetValidator(malformed_branch)

        malformed_format = deepcopy(schema)
        malformed_format["properties"]["observed_at"]["format"] = 7
        with self.assertRaises(SchemaDefinitionError):
            SubsetValidator(malformed_format)

    def test_draft_2020_12_schema_is_structural_and_python_is_mandatory_admission(
        self,
    ) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["x-admission"],
            {
                "level": "structural",
                "semantic_validator": "adaptive_factory.context_contracts.ContextManifestV1.from_dict",
                "semantic_validation_required": True,
                "semantic_checks": [
                    "utf8_byte_limits",
                    "secret_detection",
                    "content_digest",
                    "source_binding",
                    "safe_path",
                ],
            },
        )
        validator = SubsetValidator(schema)
        valid = context_facts()
        for harmless in (
            "safe project fact",
            "Token budgets and authorization policies contain no credentials.",
            "Secret detection documents private key handling without carrying a value.",
            "NoAuthorization=harmless structural example",
        ):
            with self.subTest(harmless=harmless):
                candidate = deepcopy(valid)
                _replace_bound_content(candidate, harmless)
                validator.validate(candidate)
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
            with self.subTest(structural_mutation=mutate):
                candidate = deepcopy(valid)
                mutate(candidate)
                self.assertFalse(validator.is_valid(candidate))
                with self.assertRaises(ContractError):
                    ContextManifestV1.from_dict(candidate)

        for semantically_unsafe in (
            "password=synthetic-secret",
            "Authorization: Basic synthetic-value",
            "Bearer synthetic-token",
            "-----BEGIN " + "PRIVATE KEY-----synthetic-----END " + "PRIVATE KEY-----",
            "github_pat_syntheticvalue",
        ):
            with self.subTest(semantically_unsafe=semantically_unsafe):
                candidate = deepcopy(valid)
                _replace_bound_content(candidate, semantically_unsafe)
                validator.validate(candidate)
                with self.assertRaisesRegex(ContractError, "secret_content"):
                    ContextManifestV1.from_dict(candidate)

        unicode_candidate = deepcopy(valid)
        _replace_bound_content(unicode_candidate, "é" * 3000)
        validator.validate(unicode_candidate)
        with self.assertRaisesRegex(ContractError, "invalid_text: content"):
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


if __name__ == "__main__":
    unittest.main()
