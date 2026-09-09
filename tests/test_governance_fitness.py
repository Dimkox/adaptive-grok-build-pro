from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

from tests.test_architecture_fitness import GitArchitectureRepo
from tests.test_architecture_model import _rules, _system
from tests.test_governance import _valid_debt, _valid_example, _valid_rule

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

from adaptive_grok import architecture_fitness as FIT  # noqa: E402


GOVERNANCE_ID = "GOV-ADAPTIVE-GROK-M3"
RULES_PATH = "governance/rules/index.json"
DEBT_PATH = "governance/debt/index.json"
EXAMPLES_PATH = "governance/canonical-examples/index.json"
HANDOFF_SCHEMA_PATH = "schemas/governance-handoff-v1.schema.json"


class GovernanceFitnessTests(unittest.TestCase):
    maxDiff = None

    @staticmethod
    def _results(report):
        return {item.category: item for item in report.results}

    @staticmethod
    def _registry(collection: str, records: list[dict], *, version: int = 1) -> dict:
        return {
            collection: records,
            "governance_id": GOVERNANCE_ID,
            "schema_version": version,
        }

    def _seed(
        self,
        repo: GitArchitectureRepo,
        *,
        rules: list[dict] | None = None,
        debt: list[dict] | None = None,
        examples: list[dict] | None = None,
        version: int = 1,
    ) -> None:
        repo.write_json(RULES_PATH, self._registry("rules", rules or [], version=version))
        repo.write_json(DEBT_PATH, self._registry("entries", debt or [], version=version))
        repo.write_json(
            EXAMPLES_PATH,
            self._registry("examples", examples or [], version=version),
        )
        for name in (
            "governance-rule.schema.json",
            "debt-entry.schema.json",
            "canonical-example.schema.json",
            "governance-handoff-v1.schema.json",
        ):
            repo.write_bytes(f"schemas/{name}", (ROOT / "schemas" / name).read_bytes())
        repo.write_text(".grok-stack/adaptive_grok/governance.py", "VERSION = 1\n")
        repo.write_text("scripts/grok_governance.py", "VERSION = 1\n")

    def _repo(
        self,
        *,
        rules: list[dict] | None = None,
        debt: list[dict] | None = None,
        examples: list[dict] | None = None,
    ):
        repo = GitArchitectureRepo(self)
        repo.model(_system(), _rules())
        self._seed(repo, rules=rules, debt=debt, examples=examples)
        base = repo.commit("governance base")
        return repo, base

    def _evaluate(self, repo: GitArchitectureRepo, base: str, head: str):
        diff = FIT.diff_architecture(repo.root, base_sha=base, head_sha=head)
        return FIT.evaluate_fitness(
            repo.root,
            diff._head_state.snapshot,
            diff,
            diff.changed_paths,
            pre_risk="yellow",
        )

    @staticmethod
    def _activated_rule(*, projection_only: bool = False) -> dict:
        rule = _valid_rule()
        rule.update(
            {
                "status": "active",
                "revision": 4,
                "reviewed_by": [
                    {
                        "actor_id": "agent-reader-1",
                        "actor_kind": "system",
                        "reviewed_at": "2026-08-28T12:00:00Z",
                    }
                ],
                "approved_by": [],
                "evidence": [],
            }
        )
        if projection_only:
            body = b"# NON-AUTHORITATIVE PROJECTION\n"
            rule["reviewed_by"] = [
                {
                    "actor_id": "independent-reviewer",
                    "actor_kind": "system",
                    "reviewed_at": "2026-08-28T12:00:00Z",
                }
            ]
            rule["approved_by"] = [
                {
                    "actor_id": "governance-owner",
                    "actor_kind": "human",
                    "approved_at": "2026-08-28T12:30:00Z",
                    "scope": "governance",
                }
            ]
            rule["evidence"] = [
                {
                    "evidence_id": "EVIDENCE-PROJECTION",
                    "path": "decisions.md",
                    "sha256": hashlib.sha256(body).hexdigest(),
                }
            ]
        return rule

    def test_agent_promoted_active_rule_fails_governance_fitness(self) -> None:
        candidate = _valid_rule()
        repo, base = self._repo(rules=[candidate])
        repo.write_json(
            RULES_PATH,
            self._registry("rules", [self._activated_rule()]),
        )
        head = repo.commit("agent activates rule")

        report = self._evaluate(repo, base, head)
        result = self._results(report)["governance_promotion"]

        self.assertEqual(result.status, "fail")
        self.assertEqual(report.status, "fail")
        self.assertIn("independent", " ".join(result.findings))

    def test_projection_only_authority_cannot_promote_a_rule(self) -> None:
        candidate = _valid_rule()
        repo, base = self._repo(rules=[candidate])
        repo.write_text("decisions.md", "# NON-AUTHORITATIVE PROJECTION\n")
        repo.write_json(
            RULES_PATH,
            self._registry("rules", [self._activated_rule(projection_only=True)]),
        )
        head = repo.commit("projection promotion")

        result = self._results(self._evaluate(repo, base, head))["governance_promotion"]

        self.assertEqual(result.status, "fail")
        self.assertIn("projection", " ".join(result.findings))
        self.assertIn("external", " ".join(result.findings))

    def test_deleting_an_active_rule_without_revocation_fails(self) -> None:
        active = self._activated_rule(projection_only=True)
        repo, base = self._repo(rules=[active])
        repo.write_json(RULES_PATH, self._registry("rules", []))
        head = repo.commit("delete active rule")

        result = self._results(self._evaluate(repo, base, head))["governance_promotion"]

        self.assertEqual(result.status, "fail")
        self.assertIn("revocation", " ".join(result.findings))

    def test_deleting_live_debt_or_active_example_fails(self) -> None:
        for status, deadline in (
            ("open", "2026-09-28T11:30:00Z"),
            ("repaying", "2026-08-01T11:30:00Z"),
        ):
            with self.subTest(record="debt", status=status):
                debt = _valid_debt()
                debt.update(status=status, deadline=deadline)
                repo, base = self._repo(debt=[debt])
                repo.write_json(DEBT_PATH, self._registry("entries", []))
                head = repo.commit(f"delete {status} debt")
                result = self._results(self._evaluate(repo, base, head))[
                    "governance_promotion"
                ]
                self.assertEqual(result.status, "fail")
                self.assertIn("debt", " ".join(result.findings))

        example = _valid_example()
        example["status"] = "active"
        repo, base = self._repo(examples=[example])
        repo.write_json(EXAMPLES_PATH, self._registry("examples", []))
        head = repo.commit("delete active example")
        result = self._results(self._evaluate(repo, base, head))[
            "governance_promotion"
        ]
        self.assertEqual(result.status, "fail")
        self.assertIn("example", " ".join(result.findings))

    def test_registry_schemas_are_exact_frozen_v1_contracts(self) -> None:
        cases = (
            ("governance-rule.schema.json", ("$defs", "rule", "properties", "status", "enum"), ["candidate", "active"]),
            ("debt-entry.schema.json", ("$defs", "entry", "required"), ["debt_id"]),
            ("canonical-example.schema.json", ("$defs", "example", "properties", "category", "type"), "integer"),
            ("governance-rule.schema.json", ("$defs", "id", "pattern"), ".*"),
            ("debt-entry.schema.json", ("$defs", "entry", "properties", "revision", "maximum"), 10_000_000),
            ("canonical-example.schema.json", ("properties", "examples", "uniqueItems"), False),
            ("governance-rule.schema.json", ("$defs", "rule", "additionalProperties"), True),
        )
        for name, path, replacement in cases:
            with self.subTest(schema=name, keyword=path[-1]):
                repo, base = self._repo()
                schema_path = repo.root / "schemas" / name
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                parent = schema
                for key in path[:-1]:
                    parent = parent[key]
                parent[path[-1]] = replacement
                repo.write_json(f"schemas/{name}", schema)
                head = repo.commit(f"weaken {name} {path[-1]}")
                result = self._results(self._evaluate(repo, base, head))[
                    "governance_promotion"
                ]
                self.assertEqual(result.status, "fail")
                self.assertIn("frozen v1", " ".join(result.findings))

        repo, base = self._repo()
        repo.write_text("governance/README.md", "governance change\n")
        head = repo.commit("exact frozen schemas")
        result = self._results(self._evaluate(repo, base, head))[
            "governance_promotion"
        ]
        self.assertEqual(result.status, "pass")

    def test_schema_downgrade_fails_and_unknown_version_is_unsupported(self) -> None:
        for label, version, status in (
            ("downgrade", 0, "fail"),
            ("unknown", 2, "unsupported"),
        ):
            with self.subTest(label=label):
                repo, base = self._repo()
                repo.write_json(RULES_PATH, self._registry("rules", [], version=version))
                head = repo.commit(label)
                report = self._evaluate(repo, base, head)
                result = self._results(report)["governance_promotion"]
                self.assertEqual(result.status, status)
                self.assertEqual(report.status, "fail")

    def test_frozen_handoff_shape_mismatch_fails(self) -> None:
        repo, base = self._repo()
        handoff = json.loads((ROOT / HANDOFF_SCHEMA_PATH).read_text(encoding="utf-8"))
        handoff["required"].remove("exact_head_sha")
        repo.write_json(HANDOFF_SCHEMA_PATH, handoff)
        repo.write_text("governance/README.md", "governance change\n")
        head = repo.commit("mismatched handoff")

        result = self._results(self._evaluate(repo, base, head))["governance_promotion"]

        self.assertEqual(result.status, "fail")
        self.assertIn("handoff", " ".join(result.findings))

    def test_frozen_handoff_rejects_integrity_schema_weakening(self) -> None:
        cases = (
            (
                "architecture digest property",
                ("properties", "architecture_digest"),
                {"type": "boolean"},
            ),
            (
                "base SHA property",
                ("properties", "exact_base_sha"),
                {"type": "boolean"},
            ),
            (
                "head SHA property",
                ("properties", "exact_head_sha"),
                {"type": "boolean"},
            ),
            (
                "governance digest property",
                ("properties", "governance_digest"),
                {"type": "boolean"},
            ),
            (
                "evidence digest property",
                ("properties", "governance_evidence_digest"),
                {"type": "boolean"},
            ),
            ("definitions removed", ("$defs",), None),
            ("draft identity removed", ("$schema",), None),
            ("schema identity changed", ("$id",), "https://example.test/weakened.json"),
            ("unknown root metadata", ("$comment",), "locally trusted"),
            ("additional definition", ("$defs", "unbounded"), {"type": "string"}),
            ("SHA-40 type", ("$defs", "sha40", "type"), "boolean"),
            ("SHA-40 pattern", ("$defs", "sha40", "pattern"), "^.*$"),
            ("SHA-40 minimum length", ("$defs", "sha40", "minLength"), 0),
            ("SHA-40 maximum length", ("$defs", "sha40", "maxLength"), 400),
            ("SHA-256 type", ("$defs", "sha256", "type"), "boolean"),
            ("SHA-256 pattern", ("$defs", "sha256", "pattern"), "^.*$"),
            ("SHA-256 minimum length", ("$defs", "sha256", "minLength"), 0),
            ("SHA-256 maximum length", ("$defs", "sha256", "maxLength"), 640),
        )
        for label, path, replacement in cases:
            with self.subTest(label=label):
                repo, base = self._repo()
                handoff = json.loads(
                    (ROOT / HANDOFF_SCHEMA_PATH).read_text(encoding="utf-8")
                )
                parent = handoff
                for key in path[:-1]:
                    parent = parent[key]
                if replacement is None:
                    parent.pop(path[-1])
                else:
                    parent[path[-1]] = replacement
                repo.write_json(HANDOFF_SCHEMA_PATH, handoff)
                repo.write_text("governance/README.md", "governance change\n")
                head = repo.commit(f"weaken {label}")

                report = self._evaluate(repo, base, head)
                result = self._results(report)["governance_promotion"]

                self.assertEqual(result.status, "fail")
                self.assertEqual(report.status, "fail")
                self.assertIn("handoff", " ".join(result.findings))

    def test_malformed_applicable_input_is_unsupported_and_fails_report(self) -> None:
        repo, base = self._repo()
        repo.write_text(RULES_PATH, "{not-json\n")
        head = repo.commit("malformed governance")

        report = self._evaluate(repo, base, head)
        result = self._results(report)["governance_promotion"]

        self.assertEqual(result.status, "unsupported")
        self.assertEqual(report.status, "fail")

    def test_only_the_fixed_governance_paths_are_applicable(self) -> None:
        relevant_paths = (
            "governance/notes.txt",
            "schemas/governance-rule.schema.json",
            "schemas/debt-entry.schema.json",
            "schemas/canonical-example.schema.json",
            ".grok-stack/adaptive_grok/governance.py",
            "scripts/grok_governance.py",
        )
        for path in relevant_paths:
            with self.subTest(path=path):
                repo, base = self._repo()
                original = (repo.root / path).read_bytes() if (repo.root / path).is_file() else b""
                repo.write_bytes(path, original + b"\n")
                head = repo.commit(f"change {path}")
                result = self._results(self._evaluate(repo, base, head))[
                    "governance_promotion"
                ]
                self.assertNotEqual(result.status, "not_applicable")

        repo, base = self._repo()
        repo.write_text("docs/governance-guide.md", "documentation only\n")
        head = repo.commit("unrelated governance prose")
        result = self._results(self._evaluate(repo, base, head))["governance_promotion"]
        self.assertEqual(result.status, "not_applicable")


if __name__ == "__main__":
    unittest.main()
