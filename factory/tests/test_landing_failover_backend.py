"""Durable observations and versioned backend status; legacy views stay closed."""

from dataclasses import replace
from pathlib import Path
import sqlite3
import tempfile
import unittest
from fastapi.testclient import TestClient

from adaptive_factory.landing_observation import LandingProviderObservation
from adaptive_factory.landing_contracts import LandingProviderEvidenceV2
from adaptive_factory.landing_service import LandingJobRecord
from adaptive_factory.landing_sqlite_store import SQLiteLandingJobStore
from factory.tests.test_landing_contracts import provider_facts
from factory.tests.test_landing_sqlite_store import source
from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.landing_http import HttpLandingProfile, HttpLandingNormalizer
from adaptive_factory.landing_provider import HttpProviderFailure
from adaptive_factory.landing_intake import PrivateLandingBlobStore
from adaptive_factory.landing_service import InMemoryLandingJobStore, LandingApplicationService
from adaptive_factory.models import Actor
from adaptive_factory.landing_renderer import TARGET_REPOSITORY_ID, TARGET_BASE_SHA, TARGET_BASE_TREE


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


if __name__ == "__main__":
    unittest.main()
