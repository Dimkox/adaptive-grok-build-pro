from dataclasses import asdict, replace
import json
import unittest

from fastapi.testclient import TestClient

from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.contracts import canonical_digest
from adaptive_factory.models import Actor
from adaptive_factory.semantic_bridge import build_semantic_subject
from adaptive_factory.store import PostgresSemanticCoordinatorStore, StoreError
from .test_semantic_bridge import bridge_material


def material_wire():
    packet, manifest, snapshot, result, terminal, artifacts, attestations, inputs = bridge_material()
    return {
        "result": result.to_dict(),
        "snapshot": snapshot.to_dict(),
        "packet": packet.to_dict(),
        "manifest": manifest.to_dict(),
        "terminal_proposal": asdict(terminal),
        "artifact_proposals": [asdict(value) for value in artifacts],
        "artifact_attestations": [value.to_dict() for value in attestations],
    }, inputs


class FakeCursor:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params=()):
        self.calls.append((query, params))

    def fetchone(self):
        return (next(self.rows),)


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self._cursor

    def transaction(self):
        return self


class ProbeSemanticStore(PostgresSemanticCoordinatorStore):
    def __init__(self, rows):
        self.cursor = FakeCursor(rows)
        self.database_url = "postgresql://semantic-probe"

    def _connect(self):
        return FakeConnection(self.cursor)


class SemanticPersistenceTests(unittest.TestCase):
    def test_store_reparses_exact_m5_material_and_builds_canonical_publication(self):
        wire, inputs = material_wire()
        material_store = ProbeSemanticStore([wire])
        material = material_store.execution_material(
            wire["result"]["task_id"], wire["result"]["workspace_result_digest"]
        )
        built = build_semantic_subject(**material, validation_inputs=inputs)
        expected_envelope = {
            "contract": "adaptive-factory.semantic-subject-envelope/v1",
            "binding_digest": built.binding.digest,
            "validation_inputs_digest": built.validation_inputs.digest,
            "subject_digest": built.subject.digest,
        }
        publish_store = ProbeSemanticStore([expected_envelope])
        published = publish_store.publish_subject(
            material, built, idempotency_key="1" * 64
        )
        self.assertEqual(published, built)
        query, params = publish_store.cursor.calls[-1]
        self.assertIn("semantic_publish_subject", query)
        self.assertEqual(params[0], "1" * 64)
        self.assertEqual(params[3], built.binding.digest)
        self.assertEqual(params[5], built.validation_inputs.digest)
        self.assertEqual(params[7], built.subject.digest)
        self.assertEqual(params[9], built.envelope_digest)
        for canonical in params[2::2]:
            self.assertNotIn(": ", canonical)

    def test_store_rejects_missing_corrupt_or_substituted_rows(self):
        wire, _inputs = material_wire()
        with self.assertRaises(KeyError):
            ProbeSemanticStore([None]).execution_material(
                wire["result"]["task_id"], wire["result"]["workspace_result_digest"]
            )
        corrupt = json.loads(json.dumps(wire))
        corrupt["result"]["exact_head_sha"] = "0" * 40
        with self.assertRaises(StoreError):
            ProbeSemanticStore([corrupt]).execution_material(
                wire["result"]["task_id"], wire["result"]["workspace_result_digest"]
            )

    def test_read_verifies_every_digest_and_closed_body(self):
        wire, inputs = material_wire()
        material = ProbeSemanticStore([wire]).execution_material(
            wire["result"]["task_id"], wire["result"]["workspace_result_digest"]
        )
        built = build_semantic_subject(**material, validation_inputs=inputs)
        record = {
            "envelope_digest": built.envelope_digest,
            "binding_digest": built.binding.digest,
            "validation_inputs_digest": built.validation_inputs.digest,
            "subject_digest": built.subject.digest,
            "binding": built.binding.to_dict(),
            "validation_inputs": built.validation_inputs.to_dict(),
            "subject": built.subject.to_dict(),
        }
        self.assertEqual(
            ProbeSemanticStore([record]).subject_by_digest(
                built.binding.task_id, built.subject.digest
            ),
            built,
        )
        record["subject_digest"] = "0" * 64
        with self.assertRaises(StoreError):
            ProbeSemanticStore([record]).subject_by_digest(
                built.binding.task_id, built.subject.digest
            )

    def test_subject_api_is_closed_bounded_and_uses_dedicated_scopes(self):
        wire, inputs = material_wire()
        material = ProbeSemanticStore([wire]).execution_material(
            wire["result"]["task_id"], wire["result"]["workspace_result_digest"]
        )
        built = build_semantic_subject(**material, validation_inputs=inputs)

        class Service:
            def publish_semantic_subject(self, task_id, result_digest, validation_inputs, **kwargs):
                self.call = (task_id, result_digest, validation_inputs, kwargs)
                return built

            def get_semantic_subject(self, task_id, subject_digest, **kwargs):
                self.read = (task_id, subject_digest, kwargs)
                return built

        service = Service()
        token = "semantic-coordinator-token"
        actor = Actor(
            "semantic-coordinator", "operator",
            frozenset({"semantic:publish", "semantic:read"}),
            frozenset({"owner/repository"}),
        )
        client = TestClient(create_app(service, Authenticator({token: actor})))
        headers = {
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "semantic-publish-001",
            "X-Correlation-ID": "semantic-correlation-001",
        }
        task_id = "00000000-0000-0000-0000-000000000001"
        response = client.post(
            "/v1/semantic/subjects", headers=headers,
            json={
                "task_id": task_id,
                "workspace_result_digest": built.binding.workspace_result_digest,
                "validation_inputs": built.validation_inputs.to_dict(),
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            set(response.json()),
            {"envelope_digest", "binding_digest", "validation_inputs_digest", "subject_digest", "subject"},
        )
        self.assertNotIn("terminal_proposal", response.text)
        self.assertNotIn("artifact_proposals", response.text)
        changed = {
            "task_id": task_id,
            "workspace_result_digest": built.binding.workspace_result_digest,
            "validation_inputs": built.validation_inputs.to_dict(),
            "provider_command": "forbidden",
        }
        self.assertEqual(
            client.post("/v1/semantic/subjects", headers=headers, json=changed).status_code,
            422,
        )
        read = client.get(
            f"/v1/semantic/subjects/{built.subject.digest}",
            params={"task_id": task_id},
            headers={
                "Authorization": f"Bearer {token}",
                "X-Correlation-ID": "semantic-read-001",
            },
        )
        self.assertEqual(read.status_code, 200, read.text)

    def test_task_execute_scope_cannot_publish_semantic_subject(self):
        token = "writer-execution-only-token"
        actor = Actor(
            "writer", "worker", frozenset({"task:execute"}),
            frozenset({"owner/repository"}),
        )
        client = TestClient(create_app(object(), Authenticator({token: actor})))
        response = client.post(
            "/v1/semantic/subjects",
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": "semantic-denied-001",
                "X-Correlation-ID": "semantic-denied-correlation",
            },
            json={},
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
