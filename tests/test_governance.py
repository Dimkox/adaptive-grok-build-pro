from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

import adaptive_grok.governance as governance
from adaptive_grok.spec import SpecError, load_schema, validate_schema
from adaptive_grok.governance import (
    GovernanceError,
    MAX_DEBT_ENTRIES,
    MAX_DEPTH,
    MAX_DOCUMENT_BYTES,
    MAX_EVIDENCE_REFERENCES,
    MAX_EXAMPLES,
    MAX_PARSED_NODES,
    MAX_RULES,
    governance_digests,
    load_bytes,
    load_governance,
    validate_governance,
)


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


def _valid_debt() -> dict[str, object]:
    evidence = {
        "evidence_id": "EVIDENCE-DEBT-001",
        "path": "engineering/evidence/debt-001.json",
        "sha256": "b" * 64,
    }
    actor = {"actor_id": "owner-1", "actor_kind": "human"}
    return {
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


def _valid_example() -> dict[str, object]:
    return {
        "approved_by": [],
        "category": "repository",
        "contract_ids": ["CONTRACT-REPOSITORY", "CONTRACT-ENTITY"],
        "digest": "e" * 64,
        "evidence": [
            {
                "evidence_id": "EVIDENCE-EXAMPLE-001",
                "path": "engineering/evidence/example-001.json",
                "sha256": "f" * 64,
            }
        ],
        "example_id": "EXAMPLE-REPOSITORY-001",
        "repository_paths": [
            "governance/canonical-examples/repository.py",
            "tests/test_repository.py",
        ],
        "reviewed_by": [],
        "status": "candidate",
        "supersedes": ["EXAMPLE-REPOSITORY-000", "EXAMPLE-LEGACY-REPOSITORY"],
        "version": 1,
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


class GovernanceLoaderTests(unittest.TestCase):
    def _fixture(
        self,
        *,
        rules: list[dict[str, object]] | None = None,
        debt: list[dict[str, object]] | None = None,
        examples: list[dict[str, object]] | None = None,
        rules_symlink: bool = False,
    ) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "schemas").mkdir()
        (root / "governance" / "rules").mkdir(parents=True)
        (root / "governance" / "debt").mkdir(parents=True)
        (root / "governance" / "canonical-examples").mkdir(parents=True)
        for schema_name in (
            "governance-rule.schema.json",
            "debt-entry.schema.json",
            "canonical-example.schema.json",
            "governance-handoff-v1.schema.json",
        ):
            shutil.copy2(ROOT / "schemas" / schema_name, root / "schemas" / schema_name)

        documents = {
            "governance/rules/index.json": {
                "governance_id": "GOV-ADAPTIVE-GROK-M3",
                "rules": rules if rules is not None else [],
                "schema_version": 1,
            },
            "governance/debt/index.json": {
                "entries": debt if debt is not None else [],
                "governance_id": "GOV-ADAPTIVE-GROK-M3",
                "schema_version": 1,
            },
            "governance/canonical-examples/index.json": {
                "examples": examples if examples is not None else [],
                "governance_id": "GOV-ADAPTIVE-GROK-M3",
                "schema_version": 1,
            },
        }
        for relative, document in documents.items():
            (root / relative).write_bytes(_canonical_bytes(document))
        if rules_symlink:
            rules_path = root / "governance" / "rules" / "index.json"
            outside = root / "outside-rules.json"
            outside.write_bytes(rules_path.read_bytes())
            rules_path.unlink()
            rules_path.symlink_to(outside)
        return root

    def _rules_for_digest(self) -> list[dict[str, object]]:
        first = _valid_rule()
        first["scope"] = {
            "domains": ["architecture", "ai"],
            "repository_paths": ["src", "tests"],
            "route_intents": ["feature", "refactor"],
        }
        first["supersedes"] = ["RULE-OLD-B", "RULE-OLD-A"]
        first["evidence"] = [
            {
                "evidence_id": "EVIDENCE-RULE-002",
                "path": "engineering/evidence/rule-002.json",
                "sha256": "2" * 64,
            },
            {
                "evidence_id": "EVIDENCE-RULE-001",
                "path": "engineering/evidence/rule-001.json",
                "sha256": "1" * 64,
            },
        ]
        second = json.loads(json.dumps(first))
        second["rule_id"] = "RULE-ADAPTER-BOUNDARY"
        second["statement"] = "Adapters must preserve the declared boundary."
        second["evidence"][0]["evidence_id"] = "EVIDENCE-ADAPTER-002"
        second["evidence"][1]["evidence_id"] = "EVIDENCE-ADAPTER-001"
        return [first, second]

    def test_loads_seed_snapshot_and_exposes_structural_validation(self) -> None:
        snapshot = load_governance(ROOT)

        self.assertEqual(snapshot.rules["governance_id"], "GOV-ADAPTIVE-GROK-M3")
        self.assertEqual(snapshot.debt["entries"], [])
        self.assertEqual(snapshot.examples["examples"], [])
        self.assertEqual(
            validate_governance(snapshot, ROOT, now=datetime.now(timezone.utc)), ()
        )

    def test_parser_rejects_duplicate_keys_bom_non_finite_and_surrogates(self) -> None:
        invalid_documents = (
            (b'{"schema_version":1,"schema_version":1}', "duplicate JSON key"),
            (b'\xef\xbb\xbf{"schema_version":1}', "BOM"),
            (b'{"value":NaN}', "non-finite"),
            (b'{"value":"\\ud800"}', "surrogate"),
        )
        for data, message in invalid_documents:
            with self.subTest(message=message):
                with self.assertRaisesRegex(GovernanceError, message):
                    load_bytes(data)

    def test_parser_enforces_document_node_and_depth_limits(self) -> None:
        oversized = b'{"value":"' + b"x" * MAX_DOCUMENT_BYTES + b'"}'
        with self.assertRaisesRegex(GovernanceError, "document byte limit"):
            load_bytes(oversized)

        with mock.patch("adaptive_grok.governance.MAX_PARSED_NODES", 3):
            with self.assertRaisesRegex(GovernanceError, "parsed-node limit"):
                load_bytes(b'{"value":[1,2]}')

        nested = b'{"value":' + b"[" * 65 + b"0" + b"]" * 65 + b"}"
        with self.assertRaisesRegex(GovernanceError, "nesting limit"):
            load_bytes(nested)

    def test_loader_rejects_symlink_and_read_mutation(self) -> None:
        with self.assertRaisesRegex(GovernanceError, "regular non-symlink"):
            load_governance(self._fixture(rules_symlink=True))

        root = self._fixture()
        real_fstat = os.fstat
        calls = 0

        def changed_identity(descriptor: int) -> object:
            nonlocal calls
            calls += 1
            info = real_fstat(descriptor)
            if calls != 2:
                return info
            return SimpleNamespace(
                st_ctime_ns=info.st_ctime_ns,
                st_dev=info.st_dev,
                st_ino=info.st_ino,
                st_mode=info.st_mode,
                st_mtime_ns=info.st_mtime_ns + 1,
                st_size=info.st_size,
            )

        with mock.patch("adaptive_grok.governance.os.fstat", side_effect=changed_identity):
            with self.assertRaisesRegex(GovernanceError, "changed while reading"):
                load_governance(root)

    def test_loader_pins_one_root_identity_for_the_complete_snapshot(self) -> None:
        root = self._fixture()
        original = root.with_name(f"{root.name}-original")
        replacement = root.with_name(f"{root.name}-replacement")
        shutil.copytree(root, replacement)
        replacement_rules = {
            "governance_id": "GOV-ADAPTIVE-GROK-M3",
            "rules": [_valid_rule()],
            "schema_version": 1,
        }
        (replacement / "governance" / "rules" / "index.json").write_bytes(
            _canonical_bytes(replacement_rules)
        )
        self.addCleanup(shutil.rmtree, original, True)
        self.addCleanup(shutil.rmtree, replacement, True)

        real_read = governance._read_regular_bytes
        reads = 0

        def swap_after_four_reads(*args: object, **kwargs: object) -> bytes:
            nonlocal reads
            data = real_read(*args, **kwargs)
            reads += 1
            if reads == 4:
                root.rename(original)
                replacement.rename(root)
            return data

        with mock.patch(
            "adaptive_grok.governance._read_regular_bytes",
            side_effect=swap_after_four_reads,
        ):
            with self.assertRaisesRegex(GovernanceError, "repository root changed"):
                load_governance(root)

    def test_loader_requires_nonzero_nonblocking_open_before_any_read(self) -> None:
        root = self._fixture()
        real_open = os.open
        open_call = mock.Mock(wraps=real_open)
        supports_dir_fd = set(os.supports_dir_fd)
        supports_dir_fd.discard(real_open)
        supports_dir_fd.add(open_call)
        with (
            mock.patch.object(governance.os, "O_NONBLOCK", 0),
            mock.patch.object(governance.os, "open", open_call),
            mock.patch.object(governance.os, "supports_dir_fd", supports_dir_fd),
        ):
            with self.assertRaisesRegex(GovernanceError, "no-follow reads are unavailable"):
                load_governance(root)
        open_call.assert_not_called()

    def test_loader_rejects_invalid_handoff_schema_references(self) -> None:
        mutations = {
            "missing": lambda schema: schema["properties"].__setitem__(
                "architecture_digest", {"$ref": "#/$defs/DOES_NOT_EXIST"}
            ),
            "external": lambda schema: schema["properties"].__setitem__(
                "architecture_digest", {"$ref": "https://example.invalid/schema.json"}
            ),
            "non-object": lambda schema: (
                schema["$defs"].__setitem__("BROKEN", "not-an-object"),
                schema["properties"].__setitem__(
                    "architecture_digest", {"$ref": "#/$defs/BROKEN"}
                ),
            ),
        }
        for case, mutate in mutations.items():
            with self.subTest(case=case):
                root = self._fixture()
                path = root / "schemas" / "governance-handoff-v1.schema.json"
                schema = json.loads(path.read_text(encoding="utf-8"))
                mutate(schema)
                path.write_bytes(_canonical_bytes(schema))
                with self.assertRaisesRegex(GovernanceError, "schema reference"):
                    load_governance(root)

    def test_loader_enforces_record_and_evidence_limits(self) -> None:
        fixtures = (
            ("MAX_RULES", self._fixture(rules=[_valid_rule()]), "rule limit"),
            ("MAX_DEBT_ENTRIES", self._fixture(debt=[_valid_debt()]), "debt-entry limit"),
            ("MAX_EXAMPLES", self._fixture(examples=[_valid_example()]), "example limit"),
            (
                "MAX_EVIDENCE_REFERENCES",
                self._fixture(rules=[_valid_rule()]),
                "evidence-reference limit",
            ),
        )
        for constant, root, message in fixtures:
            with self.subTest(constant=constant):
                with mock.patch(f"adaptive_grok.governance.{constant}", 0):
                    with self.assertRaisesRegex(GovernanceError, message):
                        load_governance(root)

        self.assertEqual(MAX_RULES, 512)
        self.assertEqual(MAX_DEBT_ENTRIES, 2048)
        self.assertEqual(MAX_EXAMPLES, 256)
        self.assertEqual(MAX_EVIDENCE_REFERENCES, 4096)
        self.assertEqual(MAX_PARSED_NODES, 100_000)
        self.assertEqual(MAX_DEPTH, 64)

    def test_loader_rejects_unsafe_non_nfc_and_escaping_paths(self) -> None:
        unsafe_paths = (
            "/absolute/path",
            "../escape",
            "path//segment",
            "path/",
            "path\\segment",
            "e\u0301vidence/path.json",
        )
        for unsafe in unsafe_paths:
            rule = _valid_rule()
            rule["scope"] = {**rule["scope"], "repository_paths": [unsafe]}
            with self.subTest(path=unsafe):
                with self.assertRaises(GovernanceError):
                    load_governance(self._fixture(rules=[rule]))

        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside)
        rule = _valid_rule()
        rule["evidence"] = [
            {
                "evidence_id": "EVIDENCE-RULE-001",
                "path": "escape/evidence.json",
                "sha256": "a" * 64,
            }
        ]
        root = self._fixture(rules=[rule])
        (root / "escape").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(GovernanceError, "escapes repository"):
            load_governance(root)

        rule["evidence"][0]["path"] = "loop/evidence.json"
        root = self._fixture(rules=[rule])
        (root / "loop").symlink_to("loop", target_is_directory=True)
        with self.assertRaisesRegex(GovernanceError, "cannot resolve safely"):
            load_governance(root)

    def test_loader_rejects_duplicate_stable_ids_and_noncanonical_sources(self) -> None:
        first = _valid_rule()
        second = json.loads(json.dumps(first))
        second["revision"] = 2
        with self.assertRaisesRegex(GovernanceError, "duplicate rule_id"):
            load_governance(self._fixture(rules=[first, second]))

        root = self._fixture()
        rules_path = root / "governance" / "rules" / "index.json"
        rules_path.write_text(
            '{"schema_version": 1, "governance_id": "GOV-ADAPTIVE-GROK-M3", "rules": []}\n',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(GovernanceError, "not canonical"):
            load_governance(root)

    def test_digest_is_order_stable_but_semantic_changes_rotate_it(self) -> None:
        rules = self._rules_for_digest()
        first = governance_digests(
            load_governance(
                self._fixture(rules=rules, debt=[_valid_debt()], examples=[_valid_example()])
            )
        )

        reordered_rules = json.loads(json.dumps(rules))
        reordered_rules.reverse()
        for rule in reordered_rules:
            rule["scope"]["domains"].reverse()
            rule["scope"]["repository_paths"].reverse()
            rule["scope"]["route_intents"].reverse()
            rule["evidence"].reverse()
            rule["supersedes"].reverse()
        reordered_debt = _valid_debt()
        reordered_example = _valid_example()
        reordered_example["contract_ids"].reverse()
        reordered_example["repository_paths"].reverse()
        reordered_example["supersedes"].reverse()
        reordered = governance_digests(
            load_governance(
                self._fixture(
                    rules=reordered_rules,
                    debt=[reordered_debt],
                    examples=[reordered_example],
                )
            )
        )

        changed_rules = json.loads(json.dumps(rules))
        changed_rules[0]["statement"] = "different"
        changed = governance_digests(
            load_governance(
                self._fixture(
                    rules=changed_rules,
                    debt=[_valid_debt()],
                    examples=[_valid_example()],
                )
            )
        )
        self.assertEqual(first, reordered)
        self.assertNotEqual(first["rules_digest"], changed["rules_digest"])
        self.assertNotEqual(first["governance_digest"], changed["governance_digest"])
        self.assertEqual(first["debt_digest"], changed["debt_digest"])
        self.assertEqual(first["examples_digest"], changed["examples_digest"])


if __name__ == "__main__":
    unittest.main()
