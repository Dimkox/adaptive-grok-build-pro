from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

from adaptive_grok.spec import SpecError, load_schema, validate_schema


SCHEMA_REGISTRIES = (
    ("governance-rule.schema.json", "governance/rules/index.json", "rules"),
    ("debt-entry.schema.json", "governance/debt/index.json", "entries"),
    (
        "canonical-example.schema.json",
        "governance/canonical-examples/index.json",
        "examples",
    ),
)


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _load_required_schema(test: unittest.TestCase, name: str) -> dict[str, object]:
    path = ROOT / "schemas" / name
    test.assertTrue(path.is_file(), f"required governance schema is missing: {name}")
    return load_schema(path)


def _valid_rule() -> dict[str, object]:
    return {
        "approved_by": [],
        "author": {"actor_id": "agent-reader-1", "actor_kind": "agent"},
        "confidence": "medium",
        "created_at": "2026-08-28T11:30:00Z",
        "enforcement": {"kind": "advisory", "selector": "python.repository"},
        "evidence": [
            {
                "evidence_id": "EVIDENCE-RULE-001",
                "path": "engineering/evidence/rule-001.json",
                "sha256": "a" * 64,
            }
        ],
        "expires_at": "2026-11-26T11:30:00Z",
        "policy_version": 1,
        "reviewed_by": [],
        "revision": 1,
        "rule_id": "RULE-REPOSITORY-BOUNDARY",
        "scope": {
            "domains": ["architecture"],
            "repository_paths": ["src"],
            "route_intents": ["feature"],
        },
        "source_task": "task-20260828-m3",
        "statement": "Repository adapters must preserve the declared boundary.",
        "status": "candidate",
        "supersedes": [],
    }


class GovernanceSchemaTests(unittest.TestCase):
    def test_seed_registries_validate_and_are_canonical(self) -> None:
        for schema_name, registry_name, collection in SCHEMA_REGISTRIES:
            with self.subTest(registry=registry_name):
                schema = _load_required_schema(self, schema_name)
                path = ROOT / registry_name
                self.assertTrue(path.is_file(), f"required governance registry is missing: {registry_name}")
                raw = path.read_bytes()
                document = json.loads(raw)
                validate_schema(document, schema)
                self.assertEqual(raw, _canonical_bytes(document))
                self.assertEqual(document["schema_version"], 1)
                self.assertEqual(
                    document["governance_id"], "GOV-ADAPTIVE-GROK-M3"
                )
                self.assertEqual(document[collection], [])

    def test_rule_schema_accepts_candidate_and_rejects_unknown_fields(self) -> None:
        schema = _load_required_schema(self, "governance-rule.schema.json")
        rule = _valid_rule()
        document = {
            "governance_id": "GOV-ADAPTIVE-GROK-M3",
            "rules": [rule],
            "schema_version": 1,
        }
        validate_schema(document, schema)

        with self.assertRaisesRegex(SpecError, "array items must be unique"):
            validate_schema({**document, "rules": [rule, rule]}, schema)

        document["rules"][0]["unreviewed_override"] = True
        with self.assertRaisesRegex(SpecError, "additional properties"):
            validate_schema(document, schema)

    def test_rule_schema_allows_nullable_expiry_and_rejects_other_types(self) -> None:
        schema = _load_required_schema(self, "governance-rule.schema.json")
        document = {
            "governance_id": "GOV-ADAPTIVE-GROK-M3",
            "rules": [{**_valid_rule(), "expires_at": None}],
            "schema_version": 1,
        }
        try:
            validate_schema(document, schema)
        except SpecError as exc:
            self.fail(f"nullable expiry required by the governance contract was rejected: {exc}")

        document["rules"][0]["expires_at"] = 0
        with self.assertRaisesRegex(SpecError, "expected type"):
            validate_schema(document, schema)

    def test_handoff_schema_is_closed_and_requires_exact_v1_fields(self) -> None:
        schema = _load_required_schema(self, "governance-handoff-v1.schema.json")
        handoff = {
            "architecture_digest": "a" * 64,
            "exact_base_sha": "b" * 40,
            "exact_head_sha": "c" * 40,
            "governance_contract_version": 1,
            "governance_digest": "d" * 64,
            "governance_evidence_digest": "e" * 64,
        }
        validate_schema(handoff, schema)

        with self.assertRaisesRegex(SpecError, "additional properties"):
            validate_schema({**handoff, "mutable_rules": []}, schema)
        with self.assertRaisesRegex(SpecError, "expected const 1"):
            validate_schema({**handoff, "governance_contract_version": 2}, schema)

    def test_debt_and_example_schemas_validate_records_and_reject_duplicates(self) -> None:
        evidence = {
            "evidence_id": "EVIDENCE-GOVERNANCE-001",
            "path": "engineering/evidence/governance-001.json",
            "sha256": "f" * 64,
        }
        actor = {"actor_id": "owner-1", "actor_kind": "human"}
        debt = {
            "behavior_preserving_tests": ["tests/test_repository.py"],
            "created_at": "2026-08-28T11:30:00Z",
            "deadline": "2026-09-28T11:30:00Z",
            "debt_id": "DEBT-REPOSITORY-001",
            "evidence": [evidence],
            "interest": "Every new adapter duplicates boundary validation.",
            "introduced_by": actor,
            "owner": actor,
            "reason": "The compatibility adapter must ship before extraction.",
            "repayment_trigger": "A second production adapter is introduced.",
            "revision": 1,
            "status": "open",
            "updated_at": "2026-08-28T11:30:00Z",
        }
        debt_document = {
            "entries": [debt],
            "governance_id": "GOV-ADAPTIVE-GROK-M3",
            "schema_version": 1,
        }
        debt_schema = _load_required_schema(self, "debt-entry.schema.json")
        validate_schema(debt_document, debt_schema)
        with self.assertRaisesRegex(SpecError, "array items must be unique"):
            validate_schema({**debt_document, "entries": [debt, debt]}, debt_schema)

        example = {
            "approved_by": [],
            "category": "repository",
            "contract_ids": [],
            "digest": "e" * 64,
            "evidence": [evidence],
            "example_id": "EXAMPLE-REPOSITORY-001",
            "repository_paths": ["governance/canonical-examples/repository.py"],
            "reviewed_by": [],
            "status": "candidate",
            "supersedes": [],
            "version": 1,
        }
        example_document = {
            "examples": [example],
            "governance_id": "GOV-ADAPTIVE-GROK-M3",
            "schema_version": 1,
        }
        example_schema = _load_required_schema(self, "canonical-example.schema.json")
        validate_schema(example_document, example_schema)
        with self.assertRaisesRegex(SpecError, "array items must be unique"):
            validate_schema(
                {**example_document, "examples": [example, example]}, example_schema
            )


if __name__ == "__main__":
    unittest.main()
