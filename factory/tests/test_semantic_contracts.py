import json
from pathlib import Path
import unittest

from adaptive_factory.contracts import ContractError, canonical_digest
from adaptive_factory.semantic_contracts import (
    RepairDirectiveV1,
    RequirementRefV1,
    SemanticCoverageV1,
    SemanticFindingV1,
    SemanticSubjectV1,
    SemanticVerdictV1,
)


SCHEMAS = Path(__file__).parents[1] / "contracts" / "jsonschema"


def validator(**changes):
    value = {
        "validator_id": "validator-1",
        "role": "semantic_validator",
        "capabilities": ["repository_read", "semantic_validate"],
        "definition_digest": "d" * 64,
        "model_digest": "e" * 64,
        "context_digest": "f" * 64,
    }
    value.update(changes)
    return value


def subject(**changes):
    value = {
        "schema_version": 1,
        "subject_id": "subject-1",
        "requirements": [
            {"kind": "acceptance_criterion", "requirement_id": "AC-001"},
            {"kind": "invariant", "requirement_id": "INV-001"},
        ],
        "exact_base_sha": "1" * 40,
        "exact_head_sha": "2" * 40,
        "spec_digest": "3" * 64,
        "architecture_digest": "4" * 64,
        "authority_digest": "5" * 64,
        "diff_digest": "6" * 64,
        "deterministic_evidence_digest": "7" * 64,
        "holdout_evidence_digest": "8" * 64,
        "review_evidence_digest": "9" * 64,
        "original_writer_id": "writer-1",
        "original_writer_context_digest": "a" * 64,
        "risk_level": "medium",
        "diff_lines": 20,
        "diff_limit": 100,
    }
    value.update(changes)
    return value


def finding(subject_digest, **changes):
    value = {
        "schema_version": 1,
        "subject_digest": subject_digest,
        "finding_id": "finding-1",
        "requirement": {"kind": "acceptance_criterion", "requirement_id": "AC-001"},
        "severity": "major",
        "category": "requirement_unsatisfied",
        "rule_id": "rule-output-correctness",
        "message": "Observed output is incomplete.",
        "evidence_refs": ["artifact:result-digest"],
        "reproduction": "Run the deterministic fixture.",
        "repairable": True,
        "validator": validator(),
        "created_at": "2026-09-02T00:00:00Z",
    }
    value.update(changes)
    return value


def coverage(subject_digest, **changes):
    value = {
        "schema_version": 1,
        "subject_digest": subject_digest,
        "validator": validator(),
        "entries": [
            {
                "requirement": {"kind": "acceptance_criterion", "requirement_id": "AC-001"},
                "status": "proven",
                "evidence_refs": ["check:acceptance"],
            },
            {
                "requirement": {"kind": "invariant", "requirement_id": "INV-001"},
                "status": "proven",
                "evidence_refs": ["check:invariant"],
            },
        ],
        "coverage_millionths": 1_000_000,
    }
    value.update(changes)
    return value


class SemanticContractTests(unittest.TestCase):
    def test_public_schemas_are_closed_bounded_and_have_exact_versions(self):
        semantic_names = {
            "semantic-execution-binding.v1.schema.json",
            "semantic-subject.v1.schema.json",
            "semantic-finding.v1.schema.json",
            "semantic-coverage.v1.schema.json",
            "semantic-verdict.v1.schema.json",
            "semantic-validation-inputs.v1.schema.json",
            "repair-directive.v1.schema.json",
        }
        names = semantic_names | {
            "earned-autonomy.v1.schema.json",
            "landing-attempt.v1.schema.json",
            "landing-evaluation.v1.schema.json",
            "landing-input.v1.schema.json",
            "landing-provider-evidence.v1.schema.json",
            "landing-site-artifact.v1.schema.json",
            "m7-autonomy-bridge.v1.schema.json",
            "m7-predecessor-bridges.v1.schema.json",
            "operator-handoff-proposal.v1.schema.json",
            "ready-for-pr-bundle.v1.schema.json",
            "shadow-cohort.v1.schema.json",
            "shadow-outcome.v1.schema.json",
            "shadow-task-evidence.v1.schema.json",
            "static-landing-spec.v1.schema.json",
        }
        self.assertEqual({path.name for path in SCHEMAS.glob("*.json")}, names)
        for name in semantic_names:
            with self.subTest(name=name):
                schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertFalse(schema["additionalProperties"])
                self.assertIn("schema_version", schema["required"])
                self.assertEqual(schema["properties"]["schema_version"], {"const": 1})

    def test_subject_is_closed_sorted_typed_and_digest_stable(self):
        parsed = SemanticSubjectV1.from_dict(subject())
        reordered = dict(reversed(list(subject().items())))
        self.assertEqual(SemanticSubjectV1.from_json(json.dumps(reordered)).digest, parsed.digest)
        self.assertEqual(parsed.requirement_set_digest, canonical_digest(parsed.to_dict()["requirements"]))
        unknown = subject(command="git push")
        with self.assertRaisesRegex(ContractError, "unknown_fields"):
            SemanticSubjectV1.from_dict(unknown)
        unsorted = subject(requirements=list(reversed(subject()["requirements"])))
        duplicate = subject(requirements=[subject()["requirements"][0]] * 2)
        for value in (unsorted, duplicate):
            with self.subTest(value=value), self.assertRaisesRegex(ContractError, "requirements"):
                SemanticSubjectV1.from_dict(value)

    def test_requirement_kinds_are_closed_and_identifiers_are_typed(self):
        expected = {
            "acceptance_criterion",
            "invariant",
            "forbidden_outcome",
            "architecture_rule",
            "non_functional_requirement",
        }
        actual = {
            RequirementRefV1.from_dict({"kind": kind, "requirement_id": "RULE-001"}).kind
            for kind in expected
        }
        self.assertEqual(actual, expected)
        with self.assertRaisesRegex(ContractError, "requirement_kind"):
            RequirementRefV1.from_dict({"kind": "free_form", "requirement_id": "RULE-001"})

    def test_finding_identity_ignores_wording_but_not_typed_identity(self):
        root = SemanticSubjectV1.from_dict(subject())
        original = SemanticFindingV1.from_dict(finding(root.digest))
        paraphrase = finding(
            root.digest,
            finding_id="finding-2",
            message="Different words for the same defect.",
            evidence_refs=["artifact:other-prose"],
            reproduction="A differently worded reproduction.",
            created_at="2026-09-02T00:01:00Z",
        )
        self.assertEqual(SemanticFindingV1.from_dict(paraphrase).identity_digest, original.identity_digest)
        changed = finding(root.digest, category="security_boundary")
        self.assertNotEqual(SemanticFindingV1.from_dict(changed).identity_digest, original.identity_digest)

    def test_validator_proof_requires_independence_and_read_only_capabilities(self):
        root = SemanticSubjectV1.from_dict(subject())
        valid = SemanticFindingV1.from_dict(finding(root.digest))
        valid.validate_for(root)
        invalid = (
            validator(validator_id="writer-1"),
            validator(context_digest="a" * 64),
            validator(capabilities=["application_write", "repository_read", "semantic_validate"]),
            validator(capabilities=["repository_read"]),
        )
        for proof in invalid:
            payload = finding(root.digest, validator=proof)
            with self.subTest(proof=proof), self.assertRaises(ContractError):
                SemanticFindingV1.from_dict(payload).validate_for(root)

    def test_coverage_is_exact_sorted_and_integer_millionths(self):
        root = SemanticSubjectV1.from_dict(subject())
        parsed = SemanticCoverageV1.from_dict(coverage(root.digest))
        parsed.validate_for(root)
        incomplete = coverage(root.digest, entries=coverage(root.digest)["entries"][:1])
        excessive = coverage(
            root.digest,
            entries=[
                coverage(root.digest)["entries"][0],
                {"requirement": {"kind": "architecture_rule", "requirement_id": "ARCH-001"}, "status": "proven", "evidence_refs": ["check:arch"]},
                coverage(root.digest)["entries"][1],
            ],
        )
        for payload in (incomplete, excessive):
            with self.subTest(payload=payload), self.assertRaisesRegex(ContractError, "coverage_requirement_set"):
                SemanticCoverageV1.from_dict(payload).validate_for(root)
        with self.assertRaisesRegex(ContractError, "coverage_millionths"):
            SemanticCoverageV1.from_dict(coverage(root.digest, coverage_millionths=1.0))

    def test_stale_subject_binding_rejects_finding_coverage_verdict_and_directive(self):
        root = SemanticSubjectV1.from_dict(subject())
        stale = "0" * 64
        finding_value = SemanticFindingV1.from_dict(finding(stale))
        coverage_value = SemanticCoverageV1.from_dict(coverage(stale))
        verdict = SemanticVerdictV1.from_dict(
            {
                "schema_version": 1,
                "subject_digest": stale,
                "decision": "repair",
                "decision_source": "deterministic_adjudicator",
                "finding_identity_digests": [finding_value.identity_digest],
                "duplicate_identity_digests": [],
                "correlated_requirement_keys": [],
                "contradicted_requirement_keys": [],
                "unsupported_pass_requirement_keys": [],
                "residual_risk": "medium",
            }
        )
        directive = RepairDirectiveV1.from_dict(
            {
                "schema_version": 1,
                "subject_digest": stale,
                "verdict_digest": verdict.digest,
                "cycle": 1,
                "writer_id": "writer-1",
                "context_digest": "b" * 64,
                "exact_head_sha": "2" * 40,
                "finding_identity_digests": [finding_value.identity_digest],
            }
        )
        for value in (finding_value, coverage_value, verdict, directive):
            with self.subTest(value=type(value).__name__), self.assertRaisesRegex(ContractError, "stale_semantic_evidence"):
                value.validate_for(root)

    def test_bounds_versions_unicode_and_derived_fields_fail_closed(self):
        cases = [
            subject(schema_version=2),
            subject(subject_id="x" * 129),
            subject(subject_id="bad\ud800"),
            subject(diff_lines=-1),
            subject(diff_limit=1_000_001),
        ]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ContractError):
                SemanticSubjectV1.from_dict(payload)
        supplied = subject(subject_digest="0" * 64)
        with self.assertRaisesRegex(ContractError, "unknown_fields"):
            SemanticSubjectV1.from_dict(supplied)

    def test_json_parser_rejects_duplicate_keys_non_objects_and_large_payloads(self):
        with self.assertRaisesRegex(ContractError, "duplicate_json_key"):
            SemanticSubjectV1.from_json('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(ContractError, "invalid_json_object"):
            SemanticSubjectV1.from_json("[]")
        with self.assertRaisesRegex(ContractError, "json_too_large"):
            SemanticSubjectV1.from_json(" " * 1_000_001)


if __name__ == "__main__":
    unittest.main()
