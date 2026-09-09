import unittest

from adaptive_factory.contracts import canonical_digest, canonical_json
from adaptive_factory.semantic_adjudication import adjudicate
from adaptive_factory.semantic_contracts import (
    SemanticCoverageV1,
    SemanticFindingV1,
    SemanticSubjectV1,
    ValidatorIdentityV1,
)
from adaptive_factory import store as store_module
from adaptive_factory.store import StoreError
from .test_semantic_contracts import coverage, finding, subject, validator
from .test_semantic_persistence import FakeConnection, FakeCursor


ASSIGNMENT_KEY = "1" * 64


def fixture():
    root = SemanticSubjectV1.from_dict(subject())
    proof = ValidatorIdentityV1.from_dict(validator())
    finding_value = SemanticFindingV1.from_dict(finding(root.digest))
    coverage_value = SemanticCoverageV1.from_dict(coverage(root.digest))
    assignment_body = {
        "schema_version": 1,
        "subject_digest": root.digest,
        "validator": proof.to_dict(),
    }
    return (
        root,
        proof,
        finding_value,
        coverage_value,
        assignment_body,
        canonical_digest(assignment_body),
    )


def probe(class_name, rows):
    base = getattr(store_module, class_name)

    class Probe(base):
        def __init__(self):
            self.cursor = FakeCursor(rows)
            self.database_url = "postgresql://semantic-probe"

        def _connect(self):
            return FakeConnection(self.cursor)

    return Probe()


class SemanticRuntimeStoreTests(unittest.TestCase):
    def test_coordinator_assignment_command_is_canonical_and_replay_record_is_closed(self):
        root, proof, _finding, _coverage, assignment_body, assignment_digest = fixture()
        expected = {
            "assignment_digest": assignment_digest,
            "subject_digest": root.digest,
            "validator_id": proof.validator_id,
        }
        semantic_store = probe("PostgresSemanticCoordinatorStore", [expected])
        self.assertEqual(
            semantic_store.create_assignment(
                root, proof, idempotency_key=ASSIGNMENT_KEY
            ),
            expected,
        )
        query, params = semantic_store.cursor.calls[-1]
        self.assertIn("semantic_create_assignment", query)
        self.assertEqual(params[0], ASSIGNMENT_KEY)
        self.assertEqual(params[3], expected["assignment_digest"])
        self.assertNotIn(": ", params[2])
        self.assertNotIn(": ", params[4])

        corrupt = dict(expected, validator_id="other-validator")
        with self.assertRaises(StoreError):
            probe("PostgresSemanticCoordinatorStore", [corrupt]).create_assignment(
                root, proof, idempotency_key=ASSIGNMENT_KEY
            )

    def test_validator_atomic_bundle_binds_assignment_findings_and_coverage(self):
        root, _proof, finding_value, coverage_value, _assignment, assignment_digest = fixture()
        identity_document = {
            "contract": "adaptive-factory.semantic-finding-identity/v1",
            "requirement": finding_value.requirement.to_dict(),
            "severity": finding_value.severity,
            "category": finding_value.category,
            "rule_id": finding_value.rule_id,
        }
        evidence_document = {
            "contract": "adaptive-factory.semantic-evidence-submission/v1",
            "subject_digest": root.digest,
            "assignment_digest": assignment_digest,
            "findings": [
                {
                    "finding_digest": finding_value.digest,
                    "identity_digest": finding_value.identity_digest,
                    "canonical": canonical_json(
                        finding_value.to_dict()
                    ).decode("utf-8"),
                    "identity_canonical": canonical_json(
                        identity_document
                    ).decode("utf-8"),
                }
            ],
            "coverage": {
                "coverage_digest": coverage_value.digest,
                "canonical": canonical_json(
                    coverage_value.to_dict()
                ).decode("utf-8"),
            },
        }
        expected = {
            "evidence_set_digest": canonical_digest(evidence_document),
            "subject_digest": root.digest,
            "assignment_digest": assignment_digest,
            "finding_digests": [finding_value.digest],
            "coverage_digest": coverage_value.digest,
        }
        validator_store = probe("PostgresSemanticValidatorStore", [expected])
        actual = validator_store.append_evidence(
            root.digest,
            assignment_digest,
            (finding_value,),
            coverage_value,
            idempotency_key="3" * 64,
        )
        self.assertEqual(actual, expected)
        query, params = validator_store.cursor.calls[-1]
        self.assertIn("semantic_append_evidence", query)
        self.assertEqual(params[0], "3" * 64)
        self.assertEqual(params[3], root.digest)
        self.assertEqual(params[4], assignment_digest)
        self.assertNotIn(": ", params[2])
        self.assertNotIn(": ", params[6])

    def test_adjudication_material_reparses_every_assignment_and_evidence_digest(self):
        root, _proof, finding_value, coverage_value, assignment_body, assignment_digest = fixture()
        finding_record = {
            "finding_digest": finding_value.digest,
            "assignment_digest": assignment_digest,
            "body": finding_value.to_dict(),
        }
        coverage_record = {
            "coverage_digest": coverage_value.digest,
            "assignment_digest": assignment_digest,
            "body": coverage_value.to_dict(),
        }
        wire = {
            "subject_digest": root.digest,
            "subject": root.to_dict(),
            "assignments": [
                {"assignment_digest": assignment_digest, "body": assignment_body}
            ],
            "findings": [finding_record],
            "coverages": [coverage_record],
        }
        adjudicator_store = probe("PostgresSemanticAdjudicatorStore", [wire])
        material = adjudicator_store.adjudication_material(
            "00000000-0000-0000-0000-000000000001", root.digest
        )
        expected_set = {
            "contract": "adaptive-factory.semantic-adjudication-evidence-set/v1",
            "subject_digest": root.digest,
            "assignments": [
                {
                    "assignment_digest": assignment_digest,
                    "finding_digests": [finding_value.digest],
                    "coverage_digest": coverage_value.digest,
                }
            ],
        }
        self.assertEqual(material["subject"], root)
        self.assertEqual(material["findings"], (finding_value,))
        self.assertEqual(material["coverages"], (coverage_value,))
        self.assertEqual(
            material["evidence_set_digest"], canonical_digest(expected_set)
        )
        self.assertEqual(material["evidence_set"], expected_set)

        incomplete = {**wire, "coverages": []}
        with self.assertRaises(StoreError):
            probe("PostgresSemanticAdjudicatorStore", [incomplete]).adjudication_material(
                "00000000-0000-0000-0000-000000000001", root.digest
            )

    def test_adjudicator_append_and_coordinator_read_verify_exact_verdict(self):
        root, _proof, finding_value, coverage_value, assignment_body, assignment_digest = fixture()
        evidence_set = {
            "contract": "adaptive-factory.semantic-adjudication-evidence-set/v1",
            "subject_digest": root.digest,
            "assignments": [
                {
                    "assignment_digest": assignment_digest,
                    "finding_digests": [finding_value.digest],
                    "coverage_digest": coverage_value.digest,
                }
            ],
        }
        material = {
            "subject": root,
            "findings": (finding_value,),
            "coverages": (coverage_value,),
            "evidence_set": evidence_set,
            "evidence_set_digest": canonical_digest(evidence_set),
            "assignment_bodies": {assignment_digest: assignment_body},
        }
        verdict = adjudicate(root, material["findings"], material["coverages"])
        expected = {
            "verdict_digest": verdict.digest,
            "evidence_set_digest": material["evidence_set_digest"],
            "subject_digest": root.digest,
            "verdict": verdict.to_dict(),
        }
        adjudicator_store = probe("PostgresSemanticAdjudicatorStore", [expected])
        self.assertEqual(
            adjudicator_store.append_verdict(
                material, verdict, idempotency_key="4" * 64
            ),
            expected,
        )
        query, params = adjudicator_store.cursor.calls[-1]
        self.assertIn("semantic_append_verdict", query)
        self.assertEqual(params[0], "4" * 64)
        self.assertEqual(params[3], material["evidence_set_digest"])
        self.assertEqual(params[5], verdict.digest)

        coordinator = probe("PostgresSemanticCoordinatorStore", [expected])
        self.assertEqual(
            coordinator.verdict_by_subject(
                "00000000-0000-0000-0000-000000000001", root.digest
            ),
            expected,
        )
        corrupt = {**expected, "verdict_digest": "0" * 64}
        with self.assertRaises(StoreError):
            probe("PostgresSemanticCoordinatorStore", [corrupt]).verdict_by_subject(
                "00000000-0000-0000-0000-000000000001", root.digest
            )


if __name__ == "__main__":
    unittest.main()
