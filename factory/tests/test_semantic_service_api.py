from copy import deepcopy
from types import SimpleNamespace
import unittest

from fastapi.testclient import TestClient

from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.models import Actor
from adaptive_factory.semantic_adjudication import adjudicate
from adaptive_factory.semantic_contracts import (
    SemanticCoverageV1,
    SemanticFindingV1,
    SemanticSubjectV1,
    ValidatorIdentityV1,
)
from adaptive_factory.service import AuthorizationError, FactoryService
from .test_semantic_contracts import coverage, finding, subject, validator


TASK_ID = "00000000-0000-0000-0000-000000000001"
ASSIGNMENT_DIGEST = "1" * 64
EVIDENCE_SET_DIGEST = "2" * 64


def semantic_fixture():
    root = SemanticSubjectV1.from_dict(subject())
    proof = ValidatorIdentityV1.from_dict(validator())
    finding_value = SemanticFindingV1.from_dict(finding(root.digest))
    coverage_value = SemanticCoverageV1.from_dict(coverage(root.digest))
    return root, proof, finding_value, coverage_value


class CoreStore:
    def get_task(self, task_id):
        if task_id != TASK_ID:
            raise KeyError(task_id)
        return SimpleNamespace(repository_id="owner/repository")


class CoordinatorStore:
    def __init__(self, root):
        self.root = root

    def subject_by_digest(self, task_id, subject_digest):
        if task_id != TASK_ID or subject_digest != self.root.digest:
            raise KeyError(subject_digest)
        return SimpleNamespace(subject=self.root)

    def create_assignment(self, root, proof, *, idempotency_key):
        self.assignment_call = (root, proof, idempotency_key)
        return {
            "assignment_digest": ASSIGNMENT_DIGEST,
            "subject_digest": root.digest,
            "validator_id": proof.validator_id,
        }

    def verdict_by_subject(self, task_id, subject_digest):
        self.verdict_read = (task_id, subject_digest)
        return self.verdict


class ValidatorStore:
    def append_evidence(
        self,
        subject_digest,
        assignment_digest,
        findings,
        coverage_value,
        *,
        idempotency_key,
    ):
        self.evidence_call = (
            subject_digest,
            assignment_digest,
            findings,
            coverage_value,
            idempotency_key,
        )
        return {
            "evidence_set_digest": EVIDENCE_SET_DIGEST,
            "subject_digest": subject_digest,
            "assignment_digest": assignment_digest,
            "finding_digests": [item.digest for item in findings],
            "coverage_digest": coverage_value.digest,
        }


class AdjudicatorStore:
    def __init__(self, material):
        self.material = material

    def adjudication_material(self, task_id, subject_digest):
        self.material_read = (task_id, subject_digest)
        return self.material

    def append_verdict(self, material, verdict, *, idempotency_key):
        self.verdict_call = (material, verdict, idempotency_key)
        return {
            "verdict_digest": verdict.digest,
            "evidence_set_digest": material["evidence_set_digest"],
            "subject_digest": verdict.subject_digest,
            "verdict": verdict.to_dict(),
        }


class SemanticServiceApiTests(unittest.TestCase):
    def test_coordinator_assignment_is_exact_and_task_execute_cannot_assign(self):
        root, proof, _finding, _coverage = semantic_fixture()
        coordinator = CoordinatorStore(root)
        service = FactoryService(CoreStore(), semantic_store=coordinator)
        actor = Actor(
            "semantic-coordinator",
            "operator",
            frozenset({"semantic:assign"}),
            frozenset({"owner/repository"}),
        )

        result = service.create_semantic_assignment(
            TASK_ID,
            root.digest,
            proof.to_dict(),
            actor=actor,
            idempotency_key="a" * 64,
        )
        self.assertEqual(
            result,
            {
                "assignment_digest": ASSIGNMENT_DIGEST,
                "subject_digest": root.digest,
                "validator_id": proof.validator_id,
            },
        )
        self.assertEqual(coordinator.assignment_call, (root, proof, "a" * 64))

        writer = Actor(
            "writer-1",
            "worker",
            frozenset({"task:execute"}),
            frozenset({"owner/repository"}),
        )
        with self.assertRaises(AuthorizationError):
            service.create_semantic_assignment(
                TASK_ID,
                root.digest,
                proof.to_dict(),
                actor=writer,
                idempotency_key="b" * 64,
            )

    def test_validator_evidence_is_assignment_bound_and_validator_cannot_adjudicate(self):
        root, proof, finding_value, coverage_value = semantic_fixture()
        validator_store = ValidatorStore()
        service = FactoryService(
            CoreStore(), semantic_validator_store=validator_store
        )
        actor = Actor(
            proof.validator_id,
            "validator",
            frozenset({"semantic:validate"}),
            frozenset({"owner/repository"}),
        )
        result = service.submit_semantic_evidence(
            TASK_ID,
            root.digest,
            ASSIGNMENT_DIGEST,
            [finding_value.to_dict()],
            coverage_value.to_dict(),
            actor=actor,
            idempotency_key="c" * 64,
        )
        self.assertEqual(result["assignment_digest"], ASSIGNMENT_DIGEST)
        self.assertEqual(result["evidence_set_digest"], EVIDENCE_SET_DIGEST)
        self.assertEqual(
            validator_store.evidence_call,
            (
                root.digest,
                ASSIGNMENT_DIGEST,
                (finding_value,),
                coverage_value,
                "c" * 64,
            ),
        )

        with self.assertRaises(AuthorizationError):
            service.adjudicate_semantic_subject(
                TASK_ID,
                root.digest,
                actor=Actor(
                    proof.validator_id,
                    "validator",
                    frozenset({"semantic:validate", "semantic:adjudicate"}),
                    frozenset({"owner/repository"}),
                ),
                idempotency_key="d" * 64,
            )

    def test_adjudicator_recomputes_contradiction_from_persisted_evidence(self):
        root, _proof, finding_value, coverage_value = semantic_fixture()
        second_entries = deepcopy(coverage(root.digest)["entries"])
        second_entries[0] = {**second_entries[0], "status": "contradicted"}
        second_coverage = SemanticCoverageV1.from_dict(
            coverage(
                root.digest,
                validator=validator(
                    validator_id="validator-2", context_digest="b" * 64
                ),
                entries=second_entries,
            )
        )
        material = {
            "subject": root,
            "findings": (finding_value,),
            "coverages": (coverage_value, second_coverage),
            "evidence_set_digest": EVIDENCE_SET_DIGEST,
        }
        adjudicator_store = AdjudicatorStore(material)
        coordinator = CoordinatorStore(root)
        service = FactoryService(
            CoreStore(),
            semantic_store=coordinator,
            semantic_adjudicator_store=adjudicator_store,
        )
        actor = Actor(
            "semantic-adjudicator",
            "adjudicator",
            frozenset({"semantic:adjudicate", "semantic:read"}),
            frozenset({"owner/repository"}),
        )
        record = service.adjudicate_semantic_subject(
            TASK_ID,
            root.digest,
            actor=actor,
            idempotency_key="e" * 64,
        )
        expected = adjudicate(root, (finding_value,), (coverage_value, second_coverage))
        self.assertEqual(record["verdict"], expected.to_dict())
        self.assertEqual(record["verdict"]["decision"], "needs_human")
        self.assertEqual(
            record["verdict"]["contradicted_requirement_keys"],
            ["acceptance_criterion:AC-001"],
        )
        self.assertEqual(adjudicator_store.verdict_call, (material, expected, "e" * 64))

        coordinator.verdict = record
        self.assertEqual(
            service.get_semantic_verdict(
                TASK_ID, root.digest, actor=actor
            ),
            record,
        )

    def test_api_shapes_are_closed_and_each_command_uses_its_own_scope(self):
        root, proof, finding_value, coverage_value = semantic_fixture()
        verdict = adjudicate(root, (), (coverage_value,))

        class Service:
            def create_semantic_assignment(self, *args, **kwargs):
                return {
                    "assignment_digest": ASSIGNMENT_DIGEST,
                    "subject_digest": root.digest,
                    "validator_id": proof.validator_id,
                }

            def submit_semantic_evidence(self, *args, **kwargs):
                return {
                    "evidence_set_digest": EVIDENCE_SET_DIGEST,
                    "subject_digest": root.digest,
                    "assignment_digest": ASSIGNMENT_DIGEST,
                    "finding_digests": [finding_value.digest],
                    "coverage_digest": coverage_value.digest,
                }

            def adjudicate_semantic_subject(self, *args, **kwargs):
                return {
                    "verdict_digest": verdict.digest,
                    "evidence_set_digest": EVIDENCE_SET_DIGEST,
                    "subject_digest": root.digest,
                    "verdict": verdict.to_dict(),
                }

            def get_semantic_verdict(self, *args, **kwargs):
                return self.adjudicate_semantic_subject()

        tokens = {
            "coordinator-token": Actor(
                "semantic-coordinator",
                "operator",
                frozenset({"semantic:assign", "semantic:read"}),
                frozenset({"owner/repository"}),
            ),
            "validator-token": Actor(
                proof.validator_id,
                "validator",
                frozenset({"semantic:validate"}),
                frozenset({"owner/repository"}),
            ),
            "adjudicator-token": Actor(
                "semantic-adjudicator",
                "adjudicator",
                frozenset({"semantic:adjudicate"}),
                frozenset({"owner/repository"}),
            ),
        }
        client = TestClient(create_app(Service(), Authenticator(tokens)))
        command_headers = {
            "Idempotency-Key": "semantic-command-001",
            "X-Correlation-ID": "semantic-correlation-001",
        }
        assignment = client.post(
            f"/v1/semantic/subjects/{root.digest}/assignments",
            headers={"Authorization": "Bearer coordinator-token", **command_headers},
            json={"task_id": TASK_ID, "validator": proof.to_dict()},
        )
        self.assertEqual(assignment.status_code, 200, assignment.text)
        self.assertEqual(
            set(assignment.json()),
            {"assignment_digest", "subject_digest", "validator_id"},
        )

        evidence = client.post(
            f"/v1/semantic/assignments/{ASSIGNMENT_DIGEST}/evidence",
            headers={"Authorization": "Bearer validator-token", **command_headers},
            json={
                "task_id": TASK_ID,
                "subject_digest": root.digest,
                "findings": [finding_value.to_dict()],
                "coverage": coverage_value.to_dict(),
            },
        )
        self.assertEqual(evidence.status_code, 200, evidence.text)
        self.assertEqual(
            set(evidence.json()),
            {
                "evidence_set_digest",
                "subject_digest",
                "assignment_digest",
                "finding_digests",
                "coverage_digest",
            },
        )

        adjudication = client.post(
            f"/v1/semantic/subjects/{root.digest}/adjudications",
            headers={"Authorization": "Bearer adjudicator-token", **command_headers},
            json={"task_id": TASK_ID},
        )
        self.assertEqual(adjudication.status_code, 200, adjudication.text)
        self.assertEqual(
            set(adjudication.json()),
            {"verdict_digest", "evidence_set_digest", "subject_digest", "verdict"},
        )
        self.assertNotIn("provider", adjudication.text)
        self.assertNotIn("prompt", adjudication.text)

        exact_read = client.get(
            f"/v1/semantic/subjects/{root.digest}/verdict",
            params={"task_id": TASK_ID},
            headers={
                "Authorization": "Bearer coordinator-token",
                "X-Correlation-ID": "semantic-verdict-read",
            },
        )
        self.assertEqual(exact_read.status_code, 200, exact_read.text)
        self.assertEqual(exact_read.json(), adjudication.json())

        forbidden = client.post(
            f"/v1/semantic/subjects/{root.digest}/adjudications",
            headers={"Authorization": "Bearer validator-token", **command_headers},
            json={"task_id": TASK_ID},
        )
        self.assertEqual(forbidden.status_code, 403)
        unknown = client.post(
            f"/v1/semantic/subjects/{root.digest}/assignments",
            headers={"Authorization": "Bearer coordinator-token", **command_headers},
            json={
                "task_id": TASK_ID,
                "validator": proof.to_dict(),
                "provider_command": "forbidden",
            },
        )
        self.assertEqual(unknown.status_code, 422)


if __name__ == "__main__":
    unittest.main()
