from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.contracts import ContractError, canonical_digest
from adaptive_factory.models import Actor, LeaseGrant, RunRole
from adaptive_factory.result_contracts import ResultEnvelopeV2
from adaptive_factory.result_broker import ResultBroker
from adaptive_factory.service import (
    AuthorizationError, FactoryService,
)
from adaptive_factory.store import ResultAdmission


TASK = "11111111-1111-4111-8111-111111111111"
RUN = "22222222-2222-4222-8222-222222222222"


def envelope(**changes):
    payload = {
        "repository_id": "owner/repository", "task_id": TASK, "run_id": RUN,
        "fence": 7, "packet_digest": "3" * 64,
        "attempt_id": "44444444-4444-4444-8444-444444444444",
        "source_operation": "tool.call/read", "source_digest": "5" * 64,
        "schema_version": 2, "channel": "native_tool_result",
        "content_type": "text/plain", "outcome": "allow",
        "reason_code": "accepted", "completeness": "complete",
        "policy_version": "result-sanitizer/1", "sanitized_payload": "safe",
        "sanitized_payload_digest": canonical_digest("safe"),
    }
    payload.update(changes)
    return payload


def grant(**changes):
    payload = {
        "task_id": TASK, "run_id": RUN, "owner": "worker-01", "role": "writer",
        "fence": 7, "expires_at": "2026-10-03T00:00:00Z", "packet_digest": "3" * 64,
    }
    payload.update(changes)
    return payload


class ExplodingStore:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def explode(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            raise AssertionError(f"store side effect: {name}")
        return explode


class ResultStore:
    def __init__(self):
        self.calls = []
        self.record = ResultEnvelopeV2.from_dict(envelope())

    def admit_result(self, record, *, actor, idempotency_key, correlation_id):
        self.calls.append(("admit_result", record, actor, idempotency_key, correlation_id))
        return ResultAdmission(record.record_digest, True, False)

    def result_envelope(self, repository_id, task_id, envelope_digest):
        self.calls.append(("result_envelope", repository_id, task_id, envelope_digest))
        if (repository_id, task_id, envelope_digest) != (
            self.record.repository_id, self.record.task_id, self.record.record_digest,
        ):
            raise KeyError(envelope_digest)
        return self.record


class ResultEnvelopeV2Tests(unittest.TestCase):
    def test_v2_is_closed_immutable_digest_bound_and_rejects_bool_fence(self):
        record = ResultEnvelopeV2.from_dict(envelope())
        self.assertEqual(record.repository_id, "owner/repository")
        self.assertEqual(record.record_digest, canonical_digest(record.to_dict()))
        exported = record.to_dict()
        exported["repository_id"] = "changed/repository"
        self.assertEqual(record.repository_id, "owner/repository")
        for mutation in (
            {**envelope(), "fence": True},
            {**envelope(), "extra": True},
            {**envelope(), "source_digest": "0" * 63},
            {**envelope(), "sanitized_payload": '{"password":"secret"}',
             "content_type": "application/json",
             "sanitized_payload_digest": canonical_digest('{"password":"secret"}')},
        ):
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                ResultEnvelopeV2.from_dict(mutation)

    def test_v2_schema_and_openapi_embed_the_same_canonical_contract(self):
        factory_root = Path(__file__).resolve().parents[1]
        schema = json.loads((factory_root / "contracts/jsonschema/result-envelope.v2.schema.json").read_text())
        openapi = json.loads(
            (factory_root.parent / "engineering/contracts/openapi/factory-result-admission.v2.json").read_text()
        )
        embedded = openapi["paths"]["/v1/result-admissions"]["post"][
            "requestBody"
        ]["content"]["application/json"]["schema"]["properties"]["envelope"]
        self.assertEqual(embedded, {
            "$ref": "../../../factory/contracts/jsonschema/result-envelope.v2.schema.json"
        })
        self.assertEqual(schema["$id"], "https://adaptive-grok.local/contracts/result-envelope.v2.schema.json")
        self.assertEqual(set(openapi["paths"]), {
            "/v1/result-admissions",
            "/v1/tasks/{task_id}/result-admissions/{envelope_digest}",
        })
        for path, method in (("/v1/result-admissions", "post"),
                             ("/v1/tasks/{task_id}/result-admissions/{envelope_digest}", "get")):
            operation = openapi["paths"][path][method]
            self.assertIn("503", operation["responses"])
            self.assertIn("200", operation["responses"])
            self.assertNotIn("201", operation["responses"])
        self.assertIn("409", openapi["paths"]["/v1/result-admissions"]["post"]["responses"])
        self.assertIn("404", openapi["paths"]["/v1/tasks/{task_id}/result-admissions/{envelope_digest}"]["get"]["responses"])
        admission_result = openapi["components"]["schemas"]["AdmissionResult"]
        self.assertEqual(admission_result["required"], [
            "envelope_digest", "created", "outbox_created",
        ])
        self.assertEqual(set(admission_result["properties"]), {
            "envelope_digest", "created", "outbox_created",
        })
        self.assertEqual(admission_result["properties"]["outbox_created"], {"const": False})

    def test_broker_can_bind_v2_identity_without_qualifying_any_channel(self):
        identity = {key: value for key, value in envelope().items() if key in {
            "repository_id", "task_id", "run_id", "fence", "packet_digest",
            "attempt_id", "source_operation", "source_digest",
        }}
        broker = ResultBroker(policy_version="result-sanitizer/1")
        consumed = []

        def chunks():
            consumed.append(True)
            yield b"unsafe"

        for channel in (
            "native_tool_result", "synthetic_child_report", "attachment",
            "artifact_cache", "resume", "external_cli", "unknown",
        ):
            record = broker.inspect(
                identity=identity, channel=channel, content_type="text/plain",
                chunks=chunks(),
            )
            self.assertIsInstance(record, ResultEnvelopeV2)
            self.assertEqual((record.outcome, record.sanitized_payload), ("unavailable", None))
        self.assertEqual(consumed, [])


class ResultAdmissionApiTests(unittest.TestCase):
    def setUp(self):
        self.store = ResultStore()
        actor = Actor("worker-01", "worker", frozenset({"task:execute", "task:read"}),
                      frozenset({"owner/repository"}))
        self.client = TestClient(
            create_app(FactoryService(self.store), Authenticator({"credential": actor})),
            raise_server_exceptions=False,
        )
        self.headers = {
            "Authorization": "Bearer credential", "Idempotency-Key": "admit-1",
            "X-Correlation-ID": "corr-1", "Content-Type": "application/json",
        }

    def test_real_service_returns_durable_admission_without_outbox(self):
        response = self.client.post(
            "/v1/result-admissions", headers=self.headers,
            json={"grant": grant(), "envelope": envelope()},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {
            "envelope_digest": canonical_digest(envelope()),
            "created": True, "outbox_created": False,
        })
        self.assertEqual(response.headers["x-correlation-id"], "corr-1")
        self.assertEqual([call[0] for call in self.store.calls], ["admit_result"])

    def test_outer_duplicate_keys_and_wrong_media_type_are_rejected(self):
        raw = json.dumps({"grant": grant(), "envelope": envelope()})
        duplicate = raw[:-1] + ',"grant":' + json.dumps(grant()) + "}"
        response = self.client.post("/v1/result-admissions", headers=self.headers, content=duplicate)
        self.assertEqual((response.status_code, response.json()["code"]), (422, "duplicate_json_key"))
        malformed = self.client.post(
            "/v1/result-admissions", headers=self.headers, content=b'{"grant":',
        )
        self.assertEqual((malformed.status_code, malformed.json()["code"]), (422, "invalid_request"))
        wrong = self.client.post(
            "/v1/result-admissions", headers={**self.headers, "Content-Type": "text/plain"},
            content=raw,
        )
        self.assertEqual(wrong.status_code, 415)
        self.assertEqual(self.store.calls, [])

        get = self.client.get(
            f"/v1/tasks/{TASK}/result-admissions/{'a' * 64}",
            headers={"Authorization": "Bearer credential", "X-Correlation-ID": "corr-2",
                     "X-Repository-ID": "owner/repository"},
        )
        self.assertEqual(get.status_code, 404, get.text)
        self.assertEqual(get.json()["code"], "result_admission_not_found")
        self.assertEqual(get.headers["x-correlation-id"], "corr-2")
        self.assertEqual([call[0] for call in self.store.calls], ["result_envelope"])

    def test_identity_mismatch_is_rejected_before_unavailable_capability(self):
        for mutation in (
            {"envelope": envelope(task_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")},
            {"envelope": envelope(run_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")},
            {"envelope": envelope(packet_digest="6" * 64)},
            {"envelope": envelope(repository_id="other/repository")},
            {"grant": grant(fence=8)},
            {"grant": grant(owner="worker-02")},
        ):
            body = {"grant": grant(), "envelope": envelope(), **mutation}
            response = self.client.post("/v1/result-admissions", headers=self.headers, json=body)
            self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self.store.calls, [])


class ResultAdmissionServiceTests(unittest.TestCase):
    def setUp(self):
        self.store = ResultStore()
        self.service = FactoryService(self.store)
        self.actor = Actor(
            "worker-01", "worker", frozenset({"task:execute"}),
            frozenset({"owner/repository"}),
        )
        self.grant = LeaseGrant(
            TASK, RUN, "worker-01", RunRole.WRITER, 7,
            datetime(2026, 10, 3, tzinfo=timezone.utc), "3" * 64,
        )

    def test_valid_admission_and_repository_bound_read_delegate_to_store(self):
        record = ResultEnvelopeV2.from_dict(envelope())
        admitted = self.service.admit_result(
            self.grant, record, actor=self.actor,
            idempotency_key="a" * 64, correlation_id="corr-service",
        )
        self.assertEqual(admitted, ResultAdmission(record.record_digest, True, False))
        reader = Actor(
            "reader-01", "operator", frozenset({"task:read"}),
            frozenset({"owner/repository"}),
        )
        self.assertEqual(
            self.service.get_result_envelope(
                TASK, record.record_digest,
                repository_id="owner/repository", actor=reader,
            ),
            record,
        )
        self.assertEqual([call[0] for call in self.store.calls], ["admit_result", "result_envelope"])

    def test_each_grant_binding_rejects_before_unavailable_and_store(self):
        cases = (
            (self.grant, envelope(run_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")),
            (self.grant, envelope(packet_digest="6" * 64)),
            (LeaseGrant(
                TASK, RUN, "worker-02", RunRole.WRITER, 7,
                datetime(2026, 10, 3, tzinfo=timezone.utc), "3" * 64,
            ), envelope()),
        )
        for lease, wire in cases:
            with self.subTest(lease=lease, wire=wire), self.assertRaises(AuthorizationError):
                self.service.admit_result(
                    lease, ResultEnvelopeV2.from_dict(wire), actor=self.actor,
                    idempotency_key="a" * 64, correlation_id="corr-service",
                )
        self.assertEqual(self.store.calls, [])

    def test_result_read_rejects_cross_repository_actor_before_store(self):
        denied = Actor(
            "reader-02", "operator", frozenset({"task:read"}),
            frozenset({"other/repository"}),
        )
        with self.assertRaisesRegex(AuthorizationError, "outside actor authorization"):
            self.service.get_result_envelope(
                TASK, self.store.record.record_digest,
                repository_id="owner/repository", actor=denied,
            )
        self.assertEqual(self.store.calls, [])

if __name__ == "__main__":
    unittest.main()
