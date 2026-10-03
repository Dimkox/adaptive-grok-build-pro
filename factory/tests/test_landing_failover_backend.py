"""Durable observations and versioned backend status; legacy views stay closed."""

from contextlib import nullcontext
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from adaptive_factory.landing_observation import FALLBACK_CATEGORIES, LandingProviderObservation
from adaptive_factory.landing_contracts import LandingInputV1, LandingProviderEvidenceV2
from adaptive_factory.landing_failover_contracts import validate_receipt
from adaptive_factory.landing_service import LandingJobRecord
from adaptive_factory.landing_sqlite_store import SQLiteLandingJobStore
from factory.tests.test_landing_contracts import provider_facts
from factory.tests.test_landing_sqlite_store import source
from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.landing_http import HttpLandingProfile, HttpLandingNormalizer, HttpLandingExecutionResult
from adaptive_factory.landing_provider import HttpProviderFailure
from adaptive_factory.landing_intake import PrivateLandingBlobStore
from adaptive_factory.landing_service import InMemoryLandingJobStore, LandingApplicationService
from adaptive_factory.models import Actor
from adaptive_factory.landing_renderer import TARGET_REPOSITORY_ID, TARGET_BASE_SHA, TARGET_BASE_TREE
from factory.tests.test_landing_normalizer import draft


class BackendObservationTests(unittest.TestCase):
    def test_authenticated_capability_and_expected_profile_guard_precede_provider_dispatch(self):
        calls = []
        with tempfile.TemporaryDirectory() as temporary:
            profile = HttpLandingProfile.for_provider("qwen-intl", available=True)
            class UnauthorizedExecutor:
                profile_digest = profile.profile_digest
                def run(self, request):
                    calls.append(request)
                    raise HttpProviderFailure("executor_http", "authentication", 401)
            executor = UnauthorizedExecutor()
            blobs = PrivateLandingBlobStore(Path(temporary) / "blobs", repository_root=Path(__file__).parents[2])
            service = LandingApplicationService(InMemoryLandingJobStore(), blobs, HttpLandingNormalizer(profile, executor),
                                                profile_digest=profile.profile_digest)
            actor = Actor("tenant-1", "operator", frozenset({"landing:submit", "landing:read"}), frozenset({TARGET_REPOSITORY_ID}))
            token = "a" * 32
            auth = Authenticator({token: actor})
            app = create_app(None, auth, landing_service=service, landing_only=True, execution_enabled=False)
            with TestClient(app) as client:
                headers = {"Authorization": "Bearer " + token, "X-Correlation-ID": "cap-test", "X-Repository-ID": TARGET_REPOSITORY_ID}
                capability = client.get("/v2/landing-backend", headers=headers)
                self.assertEqual(200, capability.status_code)
                self.assertEqual(profile.profile_digest, capability.json()["profile_digest"])
                self.assertEqual(401, client.get("/v2/landing-backend", headers={**headers, "Authorization": "Bearer bad"}).status_code)
                submit_headers = {**headers, "Idempotency-Key": "backend-test", "Content-Type": "text/plain",
                                  "X-Exact-Base-SHA": TARGET_BASE_SHA, "X-Exact-Base-Tree": TARGET_BASE_TREE,
                                  "X-Expected-Actor-ID": actor.actor_id, "X-Expected-Profile-Digest": "0" * 64}
                self.assertEqual(409, client.post("/v1/landing-inputs", headers=submit_headers, content=b"brief").status_code)
                self.assertEqual([], calls)
                submitted = client.post("/v1/landing-inputs", headers={**submit_headers, "X-Expected-Profile-Digest": profile.profile_digest}, content=b"brief")
                self.assertEqual(202, submitted.status_code)
                self.assertEqual({"schema_version", "job_id", "state", "input_digest"}, set(submitted.json()))
                receipt = client.get("/v2/landing-jobs/backend-test/attempt", headers=headers).json()
                self.assertTrue(receipt["terminal"])
                self.assertIsNone(receipt["artifact"])
                self.assertEqual("provider", receipt["phase"])
                self.assertEqual("authentication", receipt["observation"]["category"])
                self.assertIsNone(receipt["observation"]["usage_input_units"])
                self.assertEqual(1, len(calls))

    def test_observation_and_terminal_state_survive_restart_atomically(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "state"
            store = SQLiteLandingJobStore(root, repository_root=Path(__file__).parents[2])
            self.addCleanup(store.close)
            item = source()
            record, _ = store.create_or_replay(LandingJobRecord(item, "accepted", None, None),
                                               command_key=item.job_id, request_digest=item.input_digest)
            evidence = LandingProviderEvidenceV2.from_facts(provider_facts(
                schema_version=2, input_digest=item.input_digest, disposition="provider_unavailable",
            ))
            observation = LandingProviderObservation(evidence, "authentication", True, "unavailable", None, None, 401)
            record = store.put(replace(record, state="needs_human", observation=observation,
                                       provider_evidence_digest=evidence.provider_evidence_digest))
            self.assertEqual({"schema_version", "job_id", "state", "input_digest"}, set(record.job_view()))
            store.close()
            reopened = SQLiteLandingJobStore(root, repository_root=Path(__file__).parents[2])
            self.addCleanup(reopened.close)
            retained = reopened.get(item.tenant_id, item.repository_id, item.job_id)
            self.assertEqual(record, retained)
            self.assertEqual("authentication", retained.observation.category)

    def test_v1_store_migrates_without_fabricating_historical_observations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "state"
            store = SQLiteLandingJobStore(root, repository_root=Path(__file__).parents[2])
            item = source()
            store.create_or_replay(LandingJobRecord(item, "needs_human", None, None),
                                   command_key=item.job_id, request_digest=item.input_digest)
            store.close()
            with sqlite3.connect(root / "landing.sqlite3") as connection:
                connection.execute("DROP TRIGGER landing_activation_probes_no_delete")
                connection.execute("DROP TRIGGER landing_activation_probes_no_update")
                connection.execute("DROP TABLE landing_activation_probes")
                connection.execute("ALTER TABLE landing_jobs DROP COLUMN observation_json")
                connection.execute("PRAGMA user_version = 1")
            migrated = SQLiteLandingJobStore(root, repository_root=Path(__file__).parents[2])
            self.addCleanup(migrated.close)
            retained = migrated.get(item.tenant_id, item.repository_id, item.job_id)
            self.assertIsNone(retained.observation)
            with sqlite3.connect(migrated.database_path) as connection:
                self.assertEqual(3, connection.execute("PRAGMA user_version").fetchone()[0])


class DraftReceiptPersistenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="landing-draft-receipt-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repository_root = Path(__file__).parents[2]
        self.profile = HttpLandingProfile.for_provider("qwen-intl", available=True)
        self.actor = Actor("tenant-1", "operator", frozenset({"landing:submit", "landing:read"}),
                           frozenset({TARGET_REPOSITORY_ID}))
        self.token = "a" * 32
        self.headers = {"Authorization": "Bearer " + self.token, "X-Correlation-ID": "draft-test",
                        "X-Repository-ID": TARGET_REPOSITORY_ID}
        self.now = datetime(2026, 9, 15, tzinfo=timezone.utc)

    def app(self, store, executor):
        blobs = PrivateLandingBlobStore(self.root / "blobs", repository_root=self.repository_root,
                                        clock=lambda: self.now)
        normalizer = HttpLandingNormalizer(self.profile, executor, clock=lambda: self.now)
        service = LandingApplicationService(store, blobs, normalizer,
                                            profile_digest=self.profile.profile_digest, clock=lambda: self.now)
        return create_app(None, Authenticator({self.token: self.actor}), landing_service=service,
                          landing_only=True, execution_enabled=False)

    def forbidden_executor(self):
        profile = self.profile
        class NeverRun:
            profile_digest = profile.profile_digest
            def run(self, request):
                raise AssertionError("a stored terminal receipt must not replay provider work")
        return NeverRun()

    def test_draft_diagnostics_survive_restart_and_authenticated_receipt_read(self):
        sensitive = "SENSITIVE_PERSISTED_EXCEPTION_152"
        cases = (
            (b"{}", None, "draft_fields"),
            (json.dumps({**json.loads(draft()), "sections": []}).encode(), None, "draft_sections"),
            (draft(), ValueError(sensitive), "draft_validation_failed"),
        )
        for index, (stdout, error, reason) in enumerate(cases):
            with self.subTest(reason=reason):
                state_root = self.root / f"state-{index}"
                store = SQLiteLandingJobStore(state_root, repository_root=self.repository_root)
                self.addCleanup(store.close)
                response_digest = hashlib.sha256(b"complete provider envelope:" + stdout).hexdigest()
                self.assertNotEqual(hashlib.sha256(stdout).hexdigest(), response_digest)
                profile = self.profile
                calls = []
                class CompletedExecutor:
                    profile_digest = profile.profile_digest
                    def run(self, request):
                        calls.append(request)
                        return HttpLandingExecutionResult(stdout, response_digest, 25, 12, 34)
                job_id = f"draft-rejection-{index}"
                with TestClient(self.app(store, CompletedExecutor())) as client:
                    submit_headers = {
                        **self.headers, "Idempotency-Key": job_id, "Content-Type": "text/plain",
                        "X-Exact-Base-SHA": TARGET_BASE_SHA, "X-Exact-Base-Tree": TARGET_BASE_TREE,
                        "X-Expected-Actor-ID": self.actor.actor_id,
                        "X-Expected-Profile-Digest": self.profile.profile_digest,
                    }
                    decoder = (patch("adaptive_factory.landing_http.decode_landing_draft", side_effect=error)
                               if error is not None else nullcontext())
                    with decoder:
                        submitted = client.post("/v1/landing-inputs", headers=submit_headers,
                                                content=b"A bounded garden brief")
                    self.assertEqual(202, submitted.status_code)
                    self.assertEqual({"schema_version", "job_id", "state", "input_digest"}, set(submitted.json()))
                    response = client.get(f"/v2/landing-jobs/{job_id}/attempt", headers=self.headers)
                    self.assertEqual(200, response.status_code)
                    receipt = response.json()
                    item, observation, artifact = validate_receipt(receipt)
                    self.assertEqual(("needs_human", reason), (receipt["state"], receipt["reason_code"]))
                    self.assertEqual((self.actor.actor_id, TARGET_REPOSITORY_ID, job_id),
                                     (item.tenant_id, item.repository_id, item.job_id))
                    self.assertTrue(receipt["terminal"])
                    self.assertEqual("provider", receipt["phase"])
                    self.assertIsNone(artifact)
                    self.assertEqual("draft", observation.category)
                    self.assertNotIn(observation.category, FALLBACK_CATEGORIES)
                    self.assertEqual(response_digest, observation.evidence.response_digest)
                    self.assertEqual("reported", observation.usage_status)
                    self.assertEqual((12, 34), (observation.usage_input_units, observation.usage_output_units))
                    self.assertEqual(2, receipt["revision"])
                    self.assertNotIn(sensitive, json.dumps(receipt))
                    self.assertEqual(1, len(calls))
                store.close()
                reopened = SQLiteLandingJobStore(state_root, repository_root=self.repository_root)
                self.addCleanup(reopened.close)
                with TestClient(self.app(reopened, self.forbidden_executor())) as client:
                    endpoint = f"/v2/landing-jobs/{job_id}/attempt"
                    self.assertEqual(401, client.get(endpoint, headers={
                        **self.headers, "Authorization": "Bearer bad",
                    }).status_code)
                    response = client.get(endpoint, headers=self.headers)
                    self.assertEqual(200, response.status_code)
                    retained = response.json()
                    validate_receipt(retained)
                    self.assertEqual(receipt, retained)
                    job = client.get(f"/v1/landing-jobs/{job_id}", headers=self.headers)
                    self.assertEqual(200, job.status_code)
                    self.assertEqual(submitted.json(), job.json())
                    result = client.get(f"/v1/landing-jobs/{job_id}/result", headers=self.headers)
                    self.assertEqual(200, result.status_code)
                    self.assertEqual({"schema_version": 1, "job_id": job_id, "state": "needs_human",
                                      "artifact_digest": None, "live_url": None}, result.json())
                reopened.close()

    def test_historical_generic_receipt_is_not_rewritten_or_enriched(self):
        # Frozen from the pre-fix normalizer, including its synthetic response hash.
        legacy = json.loads((Path(__file__).parent / "fixtures/landing-legacy-draft-attempt.json").read_text())
        item = LandingInputV1.from_dict(legacy["source"])
        state_root = self.root / "legacy-state"
        store = SQLiteLandingJobStore(state_root, repository_root=self.repository_root)
        self.addCleanup(store.close)
        store.create_or_replay(LandingJobRecord(
            item, legacy["state"], None, legacy["provider_evidence_digest"],
            legacy["reason_code"], revision=legacy["revision"],
        ), command_key=item.job_id, request_digest=item.input_digest)
        store.close()
        raw_observation = json.dumps(legacy["observation"], sort_keys=True, indent=2).encode()
        identity = (item.tenant_id, item.repository_id, item.job_id)
        with sqlite3.connect(state_root / "landing.sqlite3") as connection:
            connection.execute(
                "UPDATE landing_jobs SET observation_json = ? WHERE tenant_id = ? AND repository_id = ? AND job_id = ?",
                (raw_observation, *identity),
            )
        reopened = SQLiteLandingJobStore(state_root, repository_root=self.repository_root)
        self.addCleanup(reopened.close)
        with TestClient(self.app(reopened, self.forbidden_executor())) as client:
            response = client.get(f"/v2/landing-jobs/{item.job_id}/attempt", headers=self.headers)
            self.assertEqual(200, response.status_code)
            retained = response.json()
            validate_receipt(retained)
            self.assertEqual(legacy, retained)
        with sqlite3.connect(reopened.database_path) as connection:
            self.assertEqual((legacy["reason_code"], legacy["provider_evidence_digest"],
                              raw_observation, legacy["revision"]), connection.execute(
                "SELECT reason_code, provider_evidence_digest, observation_json, revision FROM landing_jobs "
                "WHERE tenant_id = ? AND repository_id = ? AND job_id = ?", identity,
            ).fetchone())


if __name__ == "__main__":
    unittest.main()
