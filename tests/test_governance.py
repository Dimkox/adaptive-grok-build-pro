from __future__ import annotations

import dataclasses
import json
import hashlib
import hmac
import inspect
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

import adaptive_grok.governance as governance
from adaptive_grok.architecture_fitness import architecture_evidence
from adaptive_grok.spec import SpecError, load_schema, validate_schema
from adaptive_grok.governance import (
    ActorRef,
    DebtRecord,
    ExampleRecord,
    GovernanceError,
    GovernanceHandoffV1,
    MAX_DEBT_ENTRIES,
    MAX_DEPTH,
    MAX_DOCUMENT_BYTES,
    MAX_EVIDENCE_REFERENCES,
    MAX_EXAMPLES,
    MAX_PARSED_NODES,
    MAX_RULES,
    RuleRecord,
    build_governance_handoff,
    effective_examples,
    effective_rules,
    governance_digests,
    load_bytes,
    load_governance,
    open_debt,
    render_markdown_projections,
    transition_rule,
    validate_example_deviation,
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


def _active_rule(
    rule_id: str = "RULE-LIVE",
    *,
    author_id: str = "agent-author",
    reviewer_id: str = "reviewer-1",
    statement: str = "Repository adapters must use bounded operations.",
) -> dict[str, object]:
    rule = _valid_rule()
    rule.update(
        {
            "approved_by": [
                {
                    "actor_id": "governance-owner",
                    "actor_kind": "human",
                    "approved_at": "2026-08-28T12:30:00Z",
                    "scope": "governance",
                }
            ],
            "author": {"actor_id": author_id, "actor_kind": "agent"},
            "created_at": "2026-08-28T11:30:00Z",
            "expires_at": "2026-08-29T11:30:00Z",
            "reviewed_by": [
                {
                    "actor_id": reviewer_id,
                    "actor_kind": "system",
                    "reviewed_at": "2026-08-28T12:00:00Z",
                }
            ],
            "revision": 4,
            "rule_id": rule_id,
            "statement": statement,
            "status": "active",
        }
    )
    rule["evidence"] = [
        {
            "evidence_id": f"EVIDENCE-{rule_id}",
            "path": f"engineering/evidence/{rule_id.lower()}.json",
            "sha256": "0" * 64,
        }
    ]
    return rule


def _make_fixture(
    test: unittest.TestCase,
    *,
    rules: list[dict[str, object]] | None = None,
    debt: list[dict[str, object]] | None = None,
    examples: list[dict[str, object]] | None = None,
    rules_symlink: bool = False,
    materialize_evidence: bool = False,
) -> Path:
    temporary = tempfile.TemporaryDirectory()
    test.addCleanup(temporary.cleanup)
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
    if materialize_evidence:
        for collection in (rules or [], debt or [], examples or []):
            for record in collection:
                for evidence in record["evidence"]:
                    evidence_path = root / evidence["path"]
                    evidence_path.parent.mkdir(parents=True, exist_ok=True)
                    content = f'{evidence["evidence_id"]}\n'.encode()
                    evidence_path.write_bytes(content)
                    evidence["sha256"] = hashlib.sha256(content).hexdigest()
    for relative, document in documents.items():
        (root / relative).write_bytes(_canonical_bytes(document))
    if rules_symlink:
        rules_path = root / "governance" / "rules" / "index.json"
        outside = root / "outside-rules.json"
        outside.write_bytes(rules_path.read_bytes())
        rules_path.unlink()
        rules_path.symlink_to(outside)
    return root


def _git_commit_fixture(root: Path) -> str:
    commands = (
        ("init", "-q"),
        ("config", "user.email", "governance-tests@example.invalid"),
        ("config", "user.name", "Governance Tests"),
        ("add", "."),
        ("commit", "-q", "-m", "fixture"),
    )
    for command in commands:
        subprocess.run(
            ["git", *command],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _materialize_architecture(root: Path) -> None:
    shutil.copytree(ROOT / "architecture", root / "architecture")
    shutil.copytree(ROOT / "engineering" / "contracts", root / "engineering" / "contracts")
    for schema_name in (
        "architecture-system.schema.json",
        "architecture-rules.schema.json",
    ):
        shutil.copy2(ROOT / "schemas" / schema_name, root / "schemas" / schema_name)


def _architecture_evidence(
    root: Path, base_sha: str, head_sha: str
) -> dict[str, object]:
    return architecture_evidence(
        root,
        base_sha=base_sha,
        head_sha=head_sha,
        pre_risk="red",
    )


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
        materialize_evidence: bool = False,
    ) -> Path:
        return _make_fixture(
            self,
            rules=rules,
            debt=debt,
            examples=examples,
            rules_symlink=rules_symlink,
            materialize_evidence=materialize_evidence,
        )

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

    def test_loader_rejects_self_referential_schema_definition(self) -> None:
        root = self._fixture()
        path = root / "schemas" / "governance-handoff-v1.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema["$defs"]["BROKEN"] = {"$ref": "#/$defs/BROKEN"}
        schema["properties"]["architecture_digest"] = {
            "$ref": "#/$defs/BROKEN"
        }
        path.write_bytes(_canonical_bytes(schema))

        with self.assertRaisesRegex(GovernanceError, "reference aliases are unsupported"):
            load_governance(root)

    def test_loader_rejects_mutually_referential_schema_definitions(self) -> None:
        root = self._fixture()
        path = root / "schemas" / "governance-handoff-v1.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema["$defs"]["BROKEN_A"] = {"$ref": "#/$defs/BROKEN_B"}
        schema["$defs"]["BROKEN_B"] = {"$ref": "#/$defs/BROKEN_A"}
        schema["properties"]["architecture_digest"] = {
            "$ref": "#/$defs/BROKEN_A"
        }
        path.write_bytes(_canonical_bytes(schema))

        with self.assertRaisesRegex(GovernanceError, "reference aliases are unsupported"):
            load_governance(root)

    def test_loader_rejects_reference_alias_that_drops_target_constraints(self) -> None:
        root = self._fixture()
        path = root / "schemas" / "governance-handoff-v1.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema["$defs"]["BROKEN"] = {"$ref": "#/$defs/sha256"}
        schema["properties"]["architecture_digest"] = {
            "$ref": "#/$defs/BROKEN"
        }
        path.write_bytes(_canonical_bytes(schema))

        with self.assertRaisesRegex(GovernanceError, "reference aliases are unsupported"):
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


class GovernanceLifecycleTests(unittest.TestCase):
    NOW = datetime(2026, 8, 28, 13, 0, tzinfo=timezone.utc)

    def _fixture(
        self,
        *,
        rules: list[dict[str, object]] | None = None,
        materialize_evidence: bool = False,
    ) -> Path:
        return _make_fixture(
            self,
            rules=rules,
            materialize_evidence=materialize_evidence,
        )

    def _repository_validated_rule(
        self, rule: dict[str, object]
    ) -> RuleRecord:
        root = self._fixture(rules=[rule], materialize_evidence=True)
        snapshot = load_governance(root)
        self.assertEqual(len(snapshot.rule_records), 1)
        return snapshot.rule_records[0]

    def test_agent_can_only_create_candidate_and_exact_graph_preserves_identity(self) -> None:
        candidate_data = _valid_rule()
        candidate_data["author"] = {
            "actor_id": "same-agent",
            "actor_kind": "agent",
        }
        candidate = self._repository_validated_rule(candidate_data)

        with self.assertRaisesRegex(GovernanceError, "agent may only create candidate"):
            transition_rule(
                candidate,
                "active",
                ActorRef("same-agent", "agent"),
                at=self.NOW,
            )

        reviewer = ActorRef("reviewer-1", "system")
        reviewed = transition_rule(candidate, "reviewed", reviewer, at=self.NOW)
        self.assertEqual(reviewed.status, "reviewed")
        self.assertEqual(reviewed.revision, candidate.revision + 1)
        self.assertEqual(reviewed.rule_id, candidate.rule_id)
        self.assertEqual(reviewed.source_task, candidate.source_task)
        self.assertEqual(reviewed.author, candidate.author)
        self.assertEqual(reviewed.created_at, candidate.created_at)
        self.assertEqual(reviewed.reviewed_by[-1].actor_id, "reviewer-1")

        approved = transition_rule(
            reviewed,
            "approved",
            ActorRef("governance-owner", "human"),
            at=self.NOW,
        )
        active = transition_rule(
            approved,
            "active",
            ActorRef("activation-controller", "system"),
            at=self.NOW,
        )
        deprecated = transition_rule(
            active,
            "deprecated",
            ActorRef("governance-owner", "human"),
            at=self.NOW,
        )
        revoked = transition_rule(
            deprecated,
            "revoked",
            ActorRef("governance-owner", "human"),
            at=self.NOW,
        )
        emergency = transition_rule(
            active,
            "revoked",
            ActorRef("revocation-controller", "system"),
            at=self.NOW,
        )
        self.assertEqual(revoked.status, "revoked")
        self.assertEqual(emergency.status, "revoked")
        with self.assertRaisesRegex(GovernanceError, "invalid rule transition"):
            transition_rule(
                active,
                "reviewed",
                ActorRef("governance-owner", "human"),
                at=self.NOW,
            )

    def test_transition_requires_evidence_independent_review_and_human_approval(self) -> None:
        missing_evidence = _valid_rule()
        missing_evidence["evidence"] = []
        with self.assertRaisesRegex(GovernanceError, "live evidence"):
            transition_rule(
                RuleRecord.from_dict(missing_evidence),
                "reviewed",
                ActorRef("reviewer-1", "system"),
                at=self.NOW,
            )

        candidate = self._repository_validated_rule(_valid_rule())
        with self.assertRaisesRegex(GovernanceError, "independent reviewer"):
            transition_rule(
                candidate,
                "reviewed",
                ActorRef(candidate.author.actor_id, "system"),
                at=self.NOW,
            )

        unapproved_data = _active_rule("RULE-UNAPPROVED")
        unapproved_data["approved_by"] = []
        unapproved_data["revision"] = 3
        unapproved_data["status"] = "approved"
        unapproved = self._repository_validated_rule(unapproved_data)
        with self.assertRaisesRegex(GovernanceError, "human governance approval"):
            transition_rule(
                unapproved,
                "active",
                ActorRef("activation-controller", "system"),
                at=self.NOW,
            )

    def test_transition_rejects_unvalidated_traversal_evidence(self) -> None:
        candidate = _valid_rule()
        candidate["evidence"] = [
            {
                "evidence_id": "EVIDENCE-ESCAPE",
                "path": "../outside",
                "sha256": "a" * 64,
            }
        ]

        with self.assertRaisesRegex(
            GovernanceError, "repository-validated live evidence"
        ):
            transition_rule(
                RuleRecord.from_dict(candidate),
                "reviewed",
                ActorRef("reviewer-1", "system"),
                at=self.NOW,
            )

    def test_repository_validation_binding_is_not_caller_constructible(self) -> None:
        candidate = RuleRecord.from_dict(_valid_rule())
        with self.assertRaises(TypeError):
            RuleRecord(candidate._canonical_document, object())

    def test_caller_cannot_rebind_candidate_content_as_active(self) -> None:
        candidate = _valid_rule()
        root = self._fixture(rules=[candidate], materialize_evidence=True)
        snapshot = load_governance(root)
        bound = snapshot.rule_records[0]
        forged_document = bound.to_dict()
        forged_document.update(
            {
                "approved_by": [
                    {
                        "actor_id": "forged-human",
                        "actor_kind": "human",
                        "approved_at": "2026-08-28T12:30:00Z",
                        "scope": "governance",
                    }
                ],
                "reviewed_by": [
                    {
                        "actor_id": "forged-reviewer",
                        "actor_kind": "system",
                        "reviewed_at": "2026-08-28T12:00:00Z",
                    }
                ],
                "revision": 4,
                "status": "active",
            }
        )
        rebind = getattr(bound, "_with_document", None)
        forged = (
            rebind(forged_document)
            if rebind is not None
            else RuleRecord.from_dict(forged_document)
        )
        forged_snapshot = replace(
            snapshot,
            rules={**snapshot.rules, "rules": [forged_document]},
            rule_records=(forged,),
        )

        self.assertEqual(effective_rules(forged_snapshot, now=self.NOW), ())

    def test_equal_content_clone_does_not_inherit_repository_authority(self) -> None:
        active = _active_rule("RULE-CLONED-PROVENANCE")
        root = self._fixture(rules=[active], materialize_evidence=True)
        snapshot = load_governance(root)
        bound = snapshot.rule_records[0]
        clone = RuleRecord.from_dict(bound.to_dict())
        cloned_snapshot = replace(
            snapshot,
            rule_records=(clone,),
        )

        self.assertIsNot(bound, clone)
        self.assertNotEqual(bound, clone)
        self.assertEqual(effective_rules(snapshot, now=self.NOW), (bound,))
        self.assertEqual(effective_rules(cloned_snapshot, now=self.NOW), ())

    def test_effective_rules_reject_missing_and_mismatched_evidence(self) -> None:
        for case, materialize in (("missing", False), ("mismatch", True)):
            with self.subTest(case=case):
                rule = _active_rule(f"RULE-{case.upper()}")
                root = self._fixture(
                    rules=[rule], materialize_evidence=materialize
                )
                snapshot = load_governance(root)
                if materialize:
                    evidence = root / rule["evidence"][0]["path"]
                    evidence.write_text("mutated after registry load\n", encoding="utf-8")

                self.assertEqual(
                    effective_rules(snapshot, now=self.NOW), ()
                )

    def test_agent_authored_self_reviewed_unapproved_active_rule_is_rejected(self) -> None:
        rule = _active_rule(
            "RULE-SELF-REVIEWED",
            author_id="agent-a",
            reviewer_id="agent-a",
        )
        rule["approved_by"] = []
        root = self._fixture(rules=[rule], materialize_evidence=True)

        findings = validate_governance(
            load_governance(root), root, now=self.NOW
        )
        self.assertIn(
            "rule-review-not-independent", {item.code for item in findings}
        )
        self.assertIn("rule-approval-required", {item.code for item in findings})

    def test_live_evidence_is_required_after_candidate_status(self) -> None:
        rule = _active_rule("RULE-EVIDENCE")
        root = self._fixture(rules=[rule])
        findings = validate_governance(load_governance(root), root, now=self.NOW)
        self.assertIn("rule-evidence-unavailable", {item.code for item in findings})

        evidence = root / rule["evidence"][0]["path"]
        evidence.parent.mkdir(parents=True)
        evidence.write_text("different\n", encoding="utf-8")
        findings = validate_governance(load_governance(root), root, now=self.NOW)
        self.assertIn("rule-evidence-digest-mismatch", {item.code for item in findings})

    def test_expired_revoked_and_deprecated_rules_are_not_effective(self) -> None:
        expired = _active_rule("RULE-EXPIRED")
        expired["expires_at"] = "2026-08-28T12:59:59Z"
        revoked = _active_rule("RULE-REVOKED")
        revoked["status"] = "revoked"
        deprecated = _active_rule("RULE-DEPRECATED")
        deprecated["status"] = "deprecated"
        live = _active_rule("RULE-LIVE")
        root = self._fixture(
            rules=[expired, revoked, deprecated, live],
            materialize_evidence=True,
        )
        snapshot = load_governance(root)

        self.assertEqual(
            [item.rule_id for item in effective_rules(snapshot, now=self.NOW)],
            ["RULE-LIVE"],
        )
        self.assertIn(
            "rule-expired",
            {item.code for item in validate_governance(snapshot, root, now=self.NOW)},
        )
        with self.assertRaisesRegex(GovernanceError, "timezone-aware"):
            effective_rules(snapshot, now=self.NOW.replace(tzinfo=None))

    def test_duplicate_and_conflict_findings_are_deterministic(self) -> None:
        first = _active_rule("RULE-A", statement="Use explicit timeouts.")
        duplicate = _active_rule(
            "RULE-B", statement="  Use   explicit\n timeouts.  "
        )
        conflict = _active_rule("RULE-C", statement="Retries are unbounded.")
        conflict["scope"] = {
            "domains": ["ai"],
            "repository_paths": ["src"],
            "route_intents": ["feature"],
        }
        for rule in (first, duplicate):
            rule["scope"] = {
                "domains": ["ai"],
                "repository_paths": ["src/adapters"],
                "route_intents": ["feature"],
            }

        def relevant_findings(rules: list[dict[str, object]]) -> list[tuple[str, str]]:
            root = self._fixture(rules=rules, materialize_evidence=True)
            findings = validate_governance(load_governance(root), root, now=self.NOW)
            return [
                (item.code, item.path)
                for item in findings
                if item.code in {"rule-conflict", "rule-duplicate"}
            ]

        expected = [
            ("rule-conflict", "rules[RULE-A,RULE-C]"),
            ("rule-conflict", "rules[RULE-B,RULE-C]"),
            ("rule-duplicate", "rules[RULE-A,RULE-B]"),
        ]
        self.assertEqual(relevant_findings([first, duplicate, conflict]), expected)
        self.assertEqual(relevant_findings([conflict, duplicate, first]), expected)

    def test_seven_canonical_examples_expose_small_safe_surfaces(self) -> None:
        examples = ROOT / "governance" / "canonical-examples"
        expected = {
            "authorization.py",
            "background_job.py",
            "error_handling.py",
            "http_adapter.py",
            "migration.sql",
            "repository.py",
            "webhook_handler.py",
        }
        self.assertTrue(expected.issubset({path.name for path in examples.iterdir()}))

        http = runpy.run_path(examples / "http_adapter.py")
        calls: list[tuple[object, ...]] = []
        adapter = http["HttpAdapter"](
            lambda method, path, timeout, correlation: calls.append(
                (method, path, timeout, correlation)
            )
            or {"status": 204}
        )
        self.assertEqual(
            adapter.request(
                "GET", "/health", timeout_seconds=5, correlation_id="corr-1"
            ),
            {"status": 204},
        )
        self.assertEqual(calls, [("GET", "/health", 5, "corr-1")])
        with self.assertRaises(http["HttpAdapterError"]):
            adapter.request(
                "GET", "/health", timeout_seconds=0, correlation_id="corr-1"
            )

        repository = runpy.run_path(examples / "repository.py")
        queries: list[tuple[str, tuple[object, ...]]] = []
        repo = repository["Repository"](
            lambda query, parameters: queries.append((query, parameters)) or {"id": 7}
        )
        self.assertEqual(repo.get_by_id(7), {"id": 7})
        repo.save({"id": 7}, "save-7")
        self.assertEqual(queries[0][1], (7,))
        self.assertEqual(queries[1][1], ({"id": 7}, "save-7"))

        background = runpy.run_path(examples / "background_job.py")
        attempts = 0

        def flaky_job(correlation_id: str) -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise background["RetryableJobError"]("temporary")
            return correlation_id

        self.assertEqual(
            background["run_background_job"](
                flaky_job, max_attempts=2, correlation_id="corr-2"
            ),
            "corr-2",
        )
        self.assertEqual(attempts, 2)

        webhook = runpy.run_path(examples / "webhook_handler.py")
        body = b'{"event":"ping"}'
        secret = b"test-secret"
        signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
        self.assertTrue(webhook["verify_webhook"](body, signature, secret))
        self.assertFalse(webhook["verify_webhook"](body, "0" * 64, secret))

        authorization = runpy.run_path(examples / "authorization.py")
        actor = authorization["Actor"](
            actor_id="human-1", permissions=frozenset({("read", "document")})
        )
        resource = authorization["Resource"]("document", "doc-1")
        self.assertTrue(authorization["authorize"](actor, "read", resource))
        self.assertFalse(authorization["authorize"](actor, "delete", resource))

        errors = runpy.run_path(examples / "error_handling.py")
        error = errors["DomainError"]("not_found", "Resource not found")
        self.assertEqual((error.code, str(error)), ("not_found", "Resource not found"))
        self.assertEqual(
            list(inspect.signature(errors["DomainError"]).parameters),
            ["code", "safe_message"],
        )

        migration = (examples / "migration.sql").read_text(encoding="utf-8")
        self.assertIn("ADD COLUMN IF NOT EXISTS correlation_id text", migration)
        self.assertIn("CREATE INDEX CONCURRENTLY IF NOT EXISTS", migration)
        self.assertNotIn("NOT NULL", migration.upper())
        self.assertNotIn("DROP ", migration.upper())


class GovernanceKnowledgeTests(unittest.TestCase):
    NOW = datetime(2026, 8, 28, 13, 0, tzinfo=timezone.utc)

    def _example(self, example_id: str = "EXAMPLE-REPOSITORY-001") -> dict[str, object]:
        return {
            "approved_by": [{
                "actor_id": "governance-owner",
                "actor_kind": "human",
                "approved_at": "2026-08-28T12:30:00Z",
                "scope": "governance",
            }],
            "category": "repository",
            "contract_ids": ["CONTRACT-TRUST-CI-OPENAPI"],
            "digest": "0" * 64,
            "evidence": [{
                "evidence_id": f"EVIDENCE-{example_id}",
                "path": f"engineering/evidence/{example_id.lower()}.json",
                "sha256": "0" * 64,
            }],
            "example_id": example_id,
            "repository_paths": [f"examples/{example_id.lower()}.py"],
            "reviewed_by": [{
                "actor_id": "independent-reviewer",
                "actor_kind": "system",
                "reviewed_at": "2026-08-28T12:00:00Z",
            }],
            "status": "active",
            "supersedes": [],
            "version": 1,
        }

    def _debt(self, debt_id: str = "DEBT-REPOSITORY-001") -> dict[str, object]:
        debt = _valid_debt()
        debt["debt_id"] = debt_id
        debt["evidence"] = [{
            "evidence_id": f"EVIDENCE-{debt_id}",
            "path": f"engineering/evidence/{debt_id.lower()}.json",
            "sha256": "0" * 64,
        }]
        return debt

    def _fixture(
        self,
        *,
        examples: list[dict[str, object]] | None = None,
        debt: list[dict[str, object]] | None = None,
        evidence_documents: dict[str, object] | None = None,
    ) -> Path:
        root = _make_fixture(self)
        shutil.copytree(ROOT / "architecture", root / "architecture")
        for schema_name in ("architecture-system.schema.json", "architecture-rules.schema.json"):
            shutil.copy2(ROOT / "schemas" / schema_name, root / "schemas" / schema_name)
        shutil.copytree(ROOT / "engineering" / "contracts", root / "engineering" / "contracts")
        for example in examples or []:
            files = []
            for relative in example["repository_paths"]:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                content = f"canonical example {relative}\n".encode()
                path.write_bytes(content)
                files.append({"path": relative, "sha256": hashlib.sha256(content).hexdigest()})
            payload = {
                "contract": "adaptive-grok.canonical-example-content",
                "files": sorted(files, key=lambda item: item["path"]),
                "version": 1,
            }
            example["digest"] = hashlib.sha256(
                json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
        for record in [*(examples or []), *(debt or [])]:
            for evidence in record["evidence"]:
                path = root / evidence["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                document = (evidence_documents or {}).get(evidence["path"], {"status": "observed"})
                content = _canonical_bytes(document)
                path.write_bytes(content)
                evidence["sha256"] = hashlib.sha256(content).hexdigest()
        for entry in debt or []:
            for relative in entry["behavior_preserving_tests"]:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("def test_behavior():\n    assert True\n", encoding="utf-8")
        (root / "governance/canonical-examples/index.json").write_bytes(_canonical_bytes({
            "examples": examples or [],
            "governance_id": "GOV-ADAPTIVE-GROK-M3",
            "schema_version": 1,
        }))
        (root / "governance/debt/index.json").write_bytes(_canonical_bytes({
            "entries": debt or [],
            "governance_id": "GOV-ADAPTIVE-GROK-M3",
            "schema_version": 1,
        }))
        return root

    def _fixture_with_raw_debt_evidence(
        self, debt: dict[str, object], content: bytes
    ) -> Path:
        root = self._fixture(debt=[debt])
        evidence = debt["evidence"][0]
        evidence_path = root / evidence["path"]
        evidence_path.write_bytes(content)
        evidence["sha256"] = hashlib.sha256(content).hexdigest()
        (root / "governance/debt/index.json").write_bytes(_canonical_bytes({
            "entries": [debt],
            "governance_id": "GOV-ADAPTIVE-GROK-M3",
            "schema_version": 1,
        }))
        return root

    def test_active_example_requires_review_approval_live_digest_and_contracts(self) -> None:
        mutations = {
            "example-evidence-required": lambda item: item.update(evidence=[]),
            "example-evidence-digest-mismatch": lambda item: item["evidence"][0].update(sha256="f" * 64),
            "example-review-required": lambda item: item.update(reviewed_by=[]),
            "example-approval-required": lambda item: item.update(approved_by=[]),
            "example-path-unavailable": lambda item: item.update(repository_paths=["examples/missing.py"]),
            "example-digest-mismatch": lambda item: item.update(digest="f" * 64),
            "example-contract-unresolved": lambda item: item.update(contract_ids=["CONTRACT-MISSING"]),
        }
        for code, mutate in mutations.items():
            with self.subTest(code=code):
                example = self._example()
                root = self._fixture(examples=[example])
                snapshot = load_governance(root)
                mutate(example)
                snapshot = replace(
                    snapshot,
                    examples={**snapshot.examples, "examples": [example]},
                    example_records=(ExampleRecord.from_dict(example),),
                )
                findings = validate_governance(snapshot, root, now=self.NOW)
                self.assertIn(code, {finding.code for finding in findings})

    def test_repository_authored_example_authority_cannot_make_example_effective(self) -> None:
        example = self._example()
        root = self._fixture(examples=[example])
        snapshot = load_governance(root)
        self.assertIn(
            "example-external-authority-required",
            {
                item.code
                for item in validate_governance(snapshot, root, now=self.NOW)
            },
        )
        self.assertEqual(effective_examples(snapshot), ())

    def test_effective_examples_require_loaded_provenance_and_explicit_supersession(self) -> None:
        example = self._example()
        root = self._fixture(examples=[example])
        snapshot = load_governance(root)
        clone = ExampleRecord.from_dict(snapshot.example_records[0].to_dict())
        self.assertEqual(effective_examples(replace(snapshot, example_records=(clone,))), ())
        (root / example["repository_paths"][0]).write_text("mutated\n", encoding="utf-8")
        self.assertEqual(effective_examples(snapshot), ())

        older = self._example("EXAMPLE-REPOSITORY-000")
        older.update(status="deprecated", version=1)
        newer = self._example("EXAMPLE-REPOSITORY-002")
        older["repository_paths"] = list(newer["repository_paths"])
        newer.update(version=2, supersedes=[])
        root = self._fixture(examples=[older, newer])
        codes = {item.code for item in validate_governance(load_governance(root), root, now=self.NOW)}
        self.assertIn("example-supersession-required", codes)

    def test_multiple_active_examples_for_one_category_scope_fail_closed(self) -> None:
        first = self._example("EXAMPLE-REPOSITORY-001")
        second = self._example("EXAMPLE-REPOSITORY-002")
        second["repository_paths"] = list(first["repository_paths"])
        second.update(version=2, supersedes=[first["example_id"]])
        root = self._fixture(examples=[first, second])
        snapshot = load_governance(root)
        self.assertIn(
            "example-active-version-conflict",
            {item.code for item in validate_governance(snapshot, root, now=self.NOW)},
        )
        self.assertEqual(effective_examples(snapshot), ())

    def test_deviation_requires_justification_criteria_and_evidence(self) -> None:
        example = self._example("EXAMPLE-MIGRATION-001")
        example["category"] = "migration"
        root = self._fixture(examples=[example])
        snapshot = load_governance(root)
        self.assertIsNone(validate_example_deviation(
            snapshot, category="migration", justification=None
        ))
        self.assertIsNone(validate_example_deviation(
            snapshot,
            category="migration",
            justification="The approved criterion requires a different table.",
            criterion_ids=("AC-013",),
            evidence=(example["evidence"][0]["path"],),
        ))

    def test_open_debt_requires_complete_live_record_and_overdue_stays_visible(self) -> None:
        debt = self._debt()
        debt["deadline"] = "2026-08-27T13:00:00Z"
        root = self._fixture(debt=[debt])
        snapshot = load_governance(root)
        self.assertEqual([item.debt_id for item in open_debt(snapshot, now=self.NOW)], [debt["debt_id"]])
        self.assertIn(
            "debt-overdue",
            {item.code for item in validate_governance(snapshot, root, now=self.NOW)},
        )
        clone = DebtRecord.from_dict(open_debt(snapshot, now=self.NOW)[0].to_dict())
        self.assertEqual(open_debt(replace(snapshot, debt_records=(clone,)), now=self.NOW), ())
        (root / debt["evidence"][0]["path"]).write_text("mutated\n", encoding="utf-8")
        self.assertEqual(open_debt(snapshot, now=self.NOW), ())

    def test_open_debt_reports_missing_owner_trigger_deadline_tests_and_evidence(self) -> None:
        mutations = {
            "debt-owner-required": lambda item: item.update(owner={"actor_id": " ", "actor_kind": "human"}),
            "debt-trigger-required": lambda item: item.update(repayment_trigger=" "),
            "debt-deadline-invalid": lambda item: item.update(deadline="2026-09-28T13:00:00+00:00"),
            "debt-tests-required": lambda item: item.update(behavior_preserving_tests=[]),
            "debt-test-unavailable": lambda item: item.update(behavior_preserving_tests=["tests/missing.py"]),
            "debt-evidence-required": lambda item: item.update(evidence=[]),
            "debt-evidence-digest-mismatch": lambda item: item["evidence"][0].update(sha256="f" * 64),
        }
        for code, mutate in mutations.items():
            with self.subTest(code=code):
                debt = self._debt()
                root = self._fixture(debt=[debt])
                snapshot = load_governance(root)
                mutate(debt)
                snapshot = replace(
                    snapshot,
                    debt={**snapshot.debt, "entries": [debt]},
                    debt_records=(DebtRecord.from_dict(debt),),
                )
                self.assertIn(
                    code,
                    {item.code for item in validate_governance(snapshot, root, now=self.NOW)},
                )

    def test_debt_repaid_and_accepted_require_structured_evidence(self) -> None:
        repaid = self._debt("DEBT-REPAID-001")
        repaid["status"] = "repaid"
        accepted = self._debt("DEBT-ACCEPTED-001")
        accepted.update(status="accepted", deadline="2026-09-28T13:00:00Z")
        root = self._fixture(debt=[repaid, accepted])
        codes = {item.code for item in validate_governance(load_governance(root), root, now=self.NOW)}
        self.assertIn("debt-repayment-evidence-required", codes)
        self.assertIn("debt-acceptance-approval-required", codes)

    def test_repository_authored_debt_evidence_cannot_repay_or_accept_debt(self) -> None:
        repaid = self._debt("DEBT-REPAID-001")
        repaid["status"] = "repaid"
        accepted = self._debt("DEBT-ACCEPTED-001")
        accepted.update(status="accepted", deadline="2026-09-28T13:00:00Z")
        evidence_documents = {
            repaid["evidence"][0]["path"]: {
                "behavior_preserving_tests": list(repaid["behavior_preserving_tests"]),
                "debt_id": repaid["debt_id"],
                "revision": repaid["revision"],
                "status": "pass",
            },
            accepted["evidence"][0]["path"]: {
                "approved_by": {
                    "actor_id": "governance-owner",
                    "actor_kind": "human",
                    "approved_at": "2026-08-28T12:00:00Z",
                    "scope": "governance",
                },
                "debt_id": accepted["debt_id"],
                "revision": accepted["revision"],
                "status": "accepted",
            },
        }
        root = self._fixture(
            debt=[repaid, accepted], evidence_documents=evidence_documents
        )
        codes = {
            item.code
            for item in validate_governance(load_governance(root), root, now=self.NOW)
        }
        self.assertNotIn("debt-repayment-evidence-required", codes)
        self.assertNotIn("debt-acceptance-approval-required", codes)
        self.assertIn("debt-repayment-authority-required", codes)
        self.assertIn("debt-acceptance-authority-required", codes)

    def test_malformed_repayment_evidence_is_a_finding_not_an_exception(self) -> None:
        debt = self._debt("DEBT-REPAID-MALFORMED")
        debt["status"] = "repaid"
        test_path = debt["behavior_preserving_tests"][0]
        documents = {
            "scalar-tests": {"behavior_preserving_tests": 7},
            "null-tests": {"behavior_preserving_tests": None},
            "mixed-tests": {
                "behavior_preserving_tests": [test_path, 7],
            },
            "oversized-tests": {
                "behavior_preserving_tests": [
                    f"tests/behavior_{index}.py" for index in range(129)
                ],
            },
            "unknown-field": {
                "behavior_preserving_tests": [test_path],
                "untrusted": True,
            },
            "duplicate-tests": {
                "behavior_preserving_tests": [test_path, test_path],
            },
            "null-receipt": None,
        }
        for label, document in documents.items():
            with self.subTest(label=label):
                current = self._debt(f"DEBT-REPAID-{label.upper()}")
                current["status"] = "repaid"
                if document is None:
                    content = b"null"
                else:
                    content = _canonical_bytes({
                        "debt_id": current["debt_id"],
                        "revision": current["revision"],
                        "status": "pass",
                        **document,
                    })
                root = self._fixture_with_raw_debt_evidence(current, content)
                codes = {
                    item.code
                    for item in validate_governance(
                        load_governance(root), root, now=self.NOW
                    )
                }
                self.assertIn("debt-evidence-document-invalid", codes)
                self.assertIn("debt-repayment-authority-required", codes)

    def test_malformed_acceptance_receipt_is_a_finding_not_authority(self) -> None:
        invalid_receipts = {
            "scalar-approval": {
                "approved_by": 7,
                "status": "accepted",
            },
            "null-approval": {
                "approved_by": None,
                "status": "accepted",
            },
            "unknown-field": {
                "approved_by": {
                    "actor_id": "governance-owner",
                    "actor_kind": "human",
                    "approved_at": "2026-08-28T12:00:00Z",
                    "scope": "governance",
                },
                "status": "accepted",
                "untrusted": True,
            },
        }
        for label, receipt in invalid_receipts.items():
            with self.subTest(label=label):
                debt = self._debt(f"DEBT-ACCEPTED-{label.upper()}")
                debt.update(status="accepted", deadline="2026-09-28T13:00:00Z")
                content = _canonical_bytes({
                    "debt_id": debt["debt_id"],
                    "revision": debt["revision"],
                    **receipt,
                })
                root = self._fixture_with_raw_debt_evidence(debt, content)
                codes = {
                    item.code
                    for item in validate_governance(
                        load_governance(root), root, now=self.NOW
                    )
                }
                self.assertIn("debt-evidence-document-invalid", codes)
                self.assertIn("debt-acceptance-authority-required", codes)


class GovernanceHandoffTests(unittest.TestCase):
    NOW = datetime(2026, 8, 28, 13, 0, tzinfo=timezone.utc)

    def _clean_fixture(self) -> tuple[Path, object, str, dict[str, object]]:
        root = _make_fixture(self)
        _materialize_architecture(root)
        shutil.copy2(ROOT / "decisions.md", root / "decisions.md")
        shutil.copy2(ROOT / "mistakes.md", root / "mistakes.md")
        head = _git_commit_fixture(root)
        return root, load_governance(root), head, _architecture_evidence(root, head, head)

    def _invoke(self, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "grok_governance.py"),
                "--root",
                str(root),
                *arguments,
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_handoff_has_exact_closed_immutable_v1_shape(self) -> None:
        _, snapshot, head, architecture = self._clean_fixture()

        handoff = build_governance_handoff(
            snapshot,
            architecture=architecture,
            base_sha=head,
            head_sha=head,
            now=self.NOW,
        )

        self.assertIsInstance(handoff, GovernanceHandoffV1)
        self.assertEqual(
            tuple(field.name for field in dataclasses.fields(handoff)),
            (
                "governance_contract_version",
                "governance_digest",
                "governance_evidence_digest",
                "architecture_digest",
                "exact_base_sha",
                "exact_head_sha",
            ),
        )
        self.assertEqual(
            handoff.to_dict(),
            {
                "governance_contract_version": 1,
                "governance_digest": governance_digests(snapshot)[
                    "governance_digest"
                ],
                "governance_evidence_digest": handoff.governance_evidence_digest,
                "architecture_digest": architecture["architecture_digest"],
                "exact_base_sha": head,
                "exact_head_sha": head,
            },
        )
        self.assertRegex(handoff.governance_evidence_digest, r"^[0-9a-f]{64}$")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            handoff.exact_head_sha = "f" * 40

    def test_handoff_rejects_dirty_worktree_sha_and_digest_mismatches(self) -> None:
        root, snapshot, head, architecture = self._clean_fixture()
        invalid_cases = {
            "worktree": {**architecture, "head_kind": "worktree"},
            "base SHA": {**architecture, "exact_base_sha": "a" * 40},
            "evidence digest": {
                **architecture,
                "architecture_evidence_digest": "f" * 64,
            },
            "architecture digest": {
                **architecture,
                "architecture_digest": "e" * 64,
            },
            "independently derived M2 architecture evidence": {
                **architecture,
                "architecture_digest": hashlib.sha256(
                    json.dumps(
                        {
                            "contract": "adaptive-grok.architecture",
                            "contract_version": 1,
                            "rules_digest": "9" * 64,
                            "schema_digest": architecture["schema_digest"],
                            "system_digest": architecture["system_digest"],
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest(),
                "rules_digest": "9" * 64,
            },
        }
        for message, evidence in invalid_cases.items():
            if message in {
                "worktree",
                "base SHA",
                "architecture digest",
                "independently derived M2 architecture evidence",
            }:
                evidence = dict(evidence)
                evidence.pop("architecture_evidence_digest", None)
                evidence["architecture_evidence_digest"] = hashlib.sha256(
                    (
                        json.dumps(
                            evidence,
                            ensure_ascii=True,
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                        + "\n"
                    ).encode("ascii")
                ).hexdigest()
            with self.subTest(message=message):
                with self.assertRaisesRegex(GovernanceError, message):
                    build_governance_handoff(
                        snapshot,
                        architecture=evidence,
                        base_sha=head,
                        head_sha=head,
                        now=self.NOW,
                    )

        (root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(GovernanceError, "dirty"):
            build_governance_handoff(
                snapshot,
                architecture=architecture,
                base_sha=head,
                head_sha=head,
                now=self.NOW,
            )

    def test_handoff_rejects_non_json_architecture_values_as_typed_error(self) -> None:
        _, snapshot, head, architecture = self._clean_fixture()
        architecture["fitness_results"] = [float("nan")]

        with self.assertRaisesRegex(GovernanceError, "canonical JSON"):
            build_governance_handoff(
                snapshot,
                architecture=architecture,
                base_sha=head,
                head_sha=head,
                now=self.NOW,
            )

    def test_handoff_rejects_self_hashed_forged_m2_fitness_risk_and_scope(self) -> None:
        _, snapshot, head, architecture = self._clean_fixture()
        mutations = {
            "fitness_results": [],
            "risk_pre": "green",
            "risk_escalation": "yellow",
            "risk_post": "green",
            "risk_triggers": ["forged_trigger"],
            "required_scopes": ["security"],
            "diff_digest": "0" * 64,
            "repository_inventory_digest": "0" * 64,
            "contract_inventory_digest": "0" * 64,
            "base_adoption_state": "forged",
            "head_adoption_state": "forged",
            "base_adoption_digest": "0" * 64,
            "head_adoption_digest": "0" * 64,
            "baseline_introduced": not architecture["baseline_introduced"],
            "exemption_state": "eligible",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                forged = json.loads(json.dumps(architecture))
                forged[field] = value
                forged.pop("architecture_evidence_digest")
                forged["architecture_evidence_digest"] = hashlib.sha256(
                    (
                        json.dumps(
                            forged,
                            ensure_ascii=True,
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                        + "\n"
                    ).encode("ascii")
                ).hexdigest()

                with self.assertRaisesRegex(
                    GovernanceError, "independently derived M2 architecture evidence"
                ):
                    build_governance_handoff(
                        snapshot,
                        architecture=forged,
                        base_sha=head,
                        head_sha=head,
                        now=self.NOW,
                    )

    def test_handoff_preserves_external_authority_findings_as_a_hard_gate(self) -> None:
        example = _valid_example()
        example.update(
            {
                "approved_by": [
                    {
                        "actor_id": "repository-claim",
                        "actor_kind": "human",
                        "approved_at": "2026-08-28T12:30:00Z",
                        "scope": "governance",
                    }
                ],
                "reviewed_by": [
                    {
                        "actor_id": "repository-review-claim",
                        "actor_kind": "system",
                        "reviewed_at": "2026-08-28T12:00:00Z",
                    }
                ],
                "status": "active",
            }
        )
        root = _make_fixture(self, examples=[example])
        _materialize_architecture(root)
        head = _git_commit_fixture(root)
        snapshot = load_governance(root)

        with self.assertRaisesRegex(
            GovernanceError, "example-external-authority-required"
        ):
            build_governance_handoff(
                snapshot,
                architecture=_architecture_evidence(root, head, head),
                base_sha=head,
                head_sha=head,
                now=self.NOW,
            )

    def test_projection_is_deterministic_and_explicitly_non_authoritative(self) -> None:
        _, snapshot, _, _ = self._clean_fixture()

        rendered = render_markdown_projections(snapshot, now=self.NOW)

        self.assertEqual(rendered, render_markdown_projections(snapshot, now=self.NOW))
        self.assertEqual(tuple(rendered), ("decisions.md", "mistakes.md"))
        for content in rendered.values():
            self.assertIn("NON-AUTHORITATIVE PROJECTION", content)
            self.assertIn("cannot approve, activate, repay, or accept", content)
        self.assertIn("## Active governance rules", rendered["decisions.md"])
        self.assertIn("## Candidate governance rules", rendered["decisions.md"])
        self.assertIn("## Open governance debt", rendered["mistakes.md"])
        self.assertIn("## Overdue governance debt", rendered["mistakes.md"])

    def test_cli_is_deterministic_and_project_never_mutates_files(self) -> None:
        root, _, head, architecture = self._clean_fixture()
        evidence_directory = tempfile.TemporaryDirectory()
        self.addCleanup(evidence_directory.cleanup)
        evidence_file = Path(evidence_directory.name) / "architecture-evidence.json"
        evidence_file.write_bytes(_canonical_bytes(architecture))

        for command in ("validate", "summary"):
            first = self._invoke(root, command, "--now", "2026-08-28T13:00:00Z", "--json")
            second = self._invoke(root, command, "--now", "2026-08-28T13:00:00Z", "--json")
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            self.assertTrue(json.loads(first.stdout)["ok"])

        handoff = self._invoke(
            root,
            "handoff",
            "--base",
            head,
            "--head",
            head,
            "--architecture-evidence",
            str(evidence_file),
            "--now",
            "2026-08-28T13:00:00Z",
            "--json",
        )
        self.assertEqual(handoff.returncode, 0, handoff.stderr)
        self.assertEqual(tuple(json.loads(handoff.stdout)), (
            "architecture_digest",
            "exact_base_sha",
            "exact_head_sha",
            "governance_contract_version",
            "governance_digest",
            "governance_evidence_digest",
        ))

        paths = (root / "decisions.md", root / "mistakes.md")
        before = {path: path.read_bytes() for path in paths}
        first_project = self._invoke(root, "project")
        second_project = self._invoke(root, "project")
        self.assertEqual(first_project.returncode, 0, first_project.stderr)
        self.assertEqual(first_project.stdout, second_project.stdout)
        self.assertEqual(before, {path: path.read_bytes() for path in paths})
        project_payload = json.loads(first_project.stdout)
        self.assertEqual(tuple(project_payload["projections"]), ("decisions.md", "mistakes.md"))
        self.assertEqual(
            tuple(project_payload["digests"]), ("decisions.md", "mistakes.md")
        )

        checked = self._invoke(root, "check-projections")
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertTrue(json.loads(checked.stdout)["ok"])
        self.assertEqual(before, {path: path.read_bytes() for path in paths})


if __name__ == "__main__":
    unittest.main()
