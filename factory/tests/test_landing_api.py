from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.landing_contracts import LandingProviderEvidenceV1, SiteArtifactV1
from adaptive_factory.landing_intake import PrivateLandingBlobStore
from adaptive_factory.landing_provider import (
    FixedCommandLandingProvider,
    LandingNormalizationOutcome,
    LandingProviderError,
    UnavailableLandingProvider,
    unavailable_landing_profile,
)
from adaptive_factory.landing_renderer import TARGET_REPOSITORY_ID
from adaptive_factory.landing_service import (
    InMemoryLandingJobStore,
    LandingApplicationService,
)
from adaptive_factory.models import Actor
from factory.tests.test_api import FakeService
from factory.tests.test_landing_provider import clock as provider_clock
from factory.tests.test_landing_provider import profile as fixture_profile


NOW = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
TOKEN_A = "landing-tenant-a-credential"
TOKEN_B = "landing-tenant-b-credential"
CURRENT_BASE_SHA = "699010380f4f90a0193a9c22090c35e6aded7d2c"
CURRENT_BASE_TREE = "f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4"
PRIOR_BASE_SHA = "176efcaab931c2482781ff163c621b10aa05dee9"
PRIOR_BASE_TREE = "f2bdcecc6dbe9ecc82007610d398ca12bd75e07f"


class CountingBlobStore(PrivateLandingBlobStore):
    def __init__(self, root: Path, *, repository_root: Path) -> None:
        super().__init__(root, repository_root=repository_root, clock=lambda: NOW)
        self.reads = 0

    def read(self, *args, **kwargs):
        self.reads += 1
        return super().read(*args, **kwargs)


class BoundArtifactBuilder:
    def __init__(self):
        self.calls = 0

    def build(self, source, spec, evidence):
        self.calls += 1
        return SiteArtifactV1.from_facts(
            {
                "schema_version": 1,
                "site_id": "therealaidarkfactory.online",
                "canonical_origin": "https://therealaidarkfactory.online/",
                "source_sha": source.exact_base_sha,
                "source_tree": source.exact_base_tree,
                "candidate_sha": "a" * 40,
                "candidate_tree": "b" * 40,
                "input_digest": source.input_digest,
                "spec_digest": spec.spec_digest,
                "profile_digest": evidence.profile_digest,
                "attempt_digest": "c" * 64,
                "evaluation_digest": "d" * 64,
                "manifest_digest": "e" * 64,
                "zip_sha256": "f" * 64,
                "sidecar_sha256": "1" * 64,
                "member_count": 20,
                "byte_length": 4096,
                "disposition": "artifact_ready",
            }
        )


class FailingLandingProvider:
    def __init__(self):
        self.calls = 0

    def normalize(self, request, read_blob):
        self.calls += 1
        read_blob()
        raise LandingProviderError("provider_timeout")


class ContradictoryLandingProvider:
    def __init__(self, delegate):
        self.delegate = delegate

    def normalize(self, request, read_blob):
        valid = self.delegate.normalize(request, read_blob)
        facts = valid.evidence.to_dict()
        facts.pop("provider_evidence_digest")
        facts["disposition"] = "provider_unavailable"
        forged = object.__new__(LandingNormalizationOutcome)
        object.__setattr__(forged, "spec", valid.spec)
        object.__setattr__(
            forged, "evidence", LandingProviderEvidenceV1.from_facts(facts)
        )
        object.__setattr__(forged, "state", "normalized")
        object.__setattr__(forged, "reason_code", "normalized")
        return forged


class LandingApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="landing-api-")
        self.addCleanup(self.temporary.cleanup)
        self.blobs = CountingBlobStore(
            Path(self.temporary.name) / "blobs",
            repository_root=Path(__file__).resolve().parents[2],
        )
        scopes = frozenset(
            {"landing:submit", "landing:read", "landing:cancel", "task:submit"}
        )
        self.actors = {
            TOKEN_A: Actor(
                "tenant-a",
                "client",
                scopes,
                frozenset({TARGET_REPOSITORY_ID, "owner/repository"}),
            ),
            TOKEN_B: Actor(
                "tenant-b",
                "client",
                scopes,
                frozenset({TARGET_REPOSITORY_ID}),
            ),
        }

    def client(self, *, provider=None, profile_digest=None, artifact_builder=None):
        if provider is None:
            configured = unavailable_landing_profile()
            provider = UnavailableLandingProvider(
                configured, clock=lambda: NOW
            )
            profile_digest = configured.profile_digest
        service = LandingApplicationService(
            InMemoryLandingJobStore(),
            self.blobs,
            provider,
            profile_digest=profile_digest,
            artifact_builder=artifact_builder,
            clock=lambda: NOW,
        )
        return TestClient(
            create_app(
                FakeService(),
                Authenticator(self.actors),
                landing_service=service,
            )
        )

    @staticmethod
    def submit_headers(token=TOKEN_A, *, key="landing-job-1", media_type="text/plain"):
        return {
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": key,
            "X-Correlation-ID": f"correlation-{key}",
            "X-Repository-ID": TARGET_REPOSITORY_ID,
            "X-Exact-Base-SHA": CURRENT_BASE_SHA,
            "X-Exact-Base-Tree": CURRENT_BASE_TREE,
            "Content-Type": media_type,
        }

    @staticmethod
    def read_headers(token=TOKEN_A, *, correlation="landing-read"):
        return {
            "Authorization": f"Bearer {token}",
            "X-Correlation-ID": correlation,
            "X-Repository-ID": TARGET_REPOSITORY_ID,
        }

    def test_routes_are_visible_and_default_provider_is_unavailable_without_blob_read(self):
        client = self.client()
        with patch(
            "adaptive_factory.landing_provider.subprocess.Popen",
            side_effect=AssertionError("default provider started a process"),
        ):
            submitted = client.post(
                "/v1/landing-inputs",
                headers=self.submit_headers(),
                content=b"bounded landing request",
            )
        self.assertEqual(202, submitted.status_code, submitted.text)
        self.assertEqual("provider_unavailable", submitted.json()["state"])
        self.assertEqual("correlation-landing-job-1", submitted.headers["X-Correlation-ID"])
        self.assertEqual(0, self.blobs.reads)
        self.assertEqual([], list((Path(self.temporary.name) / "blobs").glob("*.blob")))

        status = client.get(
            "/v1/landing-jobs/landing-job-1", headers=self.read_headers()
        )
        result = client.get(
            "/v1/landing-jobs/landing-job-1/result",
            headers=self.read_headers(correlation="landing-result"),
        )
        self.assertEqual(200, status.status_code)
        self.assertEqual("provider_unavailable", status.json()["state"])
        self.assertEqual(
            {
                "schema_version": 1,
                "job_id": "landing-job-1",
                "state": "provider_unavailable",
                "artifact_digest": None,
                "live_url": None,
            },
            result.json(),
        )

    def test_prior_and_mixed_source_tuples_fail_before_provider_or_blob_work(self):
        provider = FailingLandingProvider()
        client = self.client(provider=provider, profile_digest="9" * 64)
        cases = (
            (PRIOR_BASE_SHA, PRIOR_BASE_TREE),
            (PRIOR_BASE_SHA, CURRENT_BASE_TREE),
            (CURRENT_BASE_SHA, PRIOR_BASE_TREE),
        )
        for index, (sha, tree) in enumerate(cases):
            headers = {
                **self.submit_headers(key=f"stale-source-{index}"),
                "X-Exact-Base-SHA": sha,
                "X-Exact-Base-Tree": tree,
            }
            response = client.post(
                "/v1/landing-inputs", headers=headers, content=b"same"
            )
            with self.subTest(sha=sha, tree=tree):
                self.assertEqual(409, response.status_code, response.text)
                self.assertEqual("source_identity", response.json()["code"])
        self.assertEqual(0, provider.calls)
        self.assertEqual(0, self.blobs.reads)
        self.assertEqual([], list((Path(self.temporary.name) / "blobs").glob("*.blob")))

    def test_auth_repository_tenant_and_idempotency_are_bound(self):
        client = self.client()
        headers = self.submit_headers(key="landing-replay")
        self.assertEqual(
            401,
            client.post(
                "/v1/landing-inputs", content=b"same", headers={"Content-Type": "text/plain"}
            ).status_code,
        )
        wrong_repository = {**headers, "X-Repository-ID": "owner/repository"}
        self.assertEqual(
            403,
            client.post(
                "/v1/landing-inputs", content=b"same", headers=wrong_repository
            ).status_code,
        )

        first = client.post("/v1/landing-inputs", content=b"same", headers=headers)
        replay = client.post("/v1/landing-inputs", content=b"same", headers=headers)
        conflict = client.post("/v1/landing-inputs", content=b"changed", headers=headers)
        self.assertEqual((202, 202, 409), (first.status_code, replay.status_code, conflict.status_code))
        self.assertEqual(first.json(), replay.json())
        cross_tenant = client.get(
            "/v1/landing-jobs/landing-replay",
            headers=self.read_headers(TOKEN_B),
        )
        self.assertEqual(404, cross_tenant.status_code)

    def test_injected_local_artifact_is_ready_then_cancelled_without_live_state(self):
        configured = fixture_profile()
        client = self.client(
            provider=FixedCommandLandingProvider(configured, clock=provider_clock()),
            profile_digest=configured.profile_digest,
            artifact_builder=BoundArtifactBuilder(),
        )
        submitted = client.post(
            "/v1/landing-inputs",
            headers=self.submit_headers(key="landing-artifact"),
            content=b"local sealed fixture input",
        )
        self.assertEqual(202, submitted.status_code, submitted.text)
        self.assertEqual("artifact_ready", submitted.json()["state"])
        self.assertEqual([], list((Path(self.temporary.name) / "blobs").glob("*.blob")))

        result = client.get(
            "/v1/landing-jobs/landing-artifact/result",
            headers=self.read_headers(correlation="artifact-result"),
        )
        self.assertEqual(200, result.status_code)
        self.assertEqual("artifact_ready", result.json()["state"])
        self.assertRegex(result.json()["artifact_digest"], r"^[0-9a-f]{64}$")
        self.assertIsNone(result.json()["live_url"])
        self.assertNotIn("indexed", result.text)

        cancelled = client.post(
            "/v1/landing-jobs/landing-artifact/cancel",
            headers={
                **self.read_headers(correlation="artifact-cancel"),
                "Idempotency-Key": "cancel-artifact",
            },
        )
        self.assertEqual(200, cancelled.status_code)
        self.assertEqual("cancelled", cancelled.json()["state"])
        after = client.get(
            "/v1/landing-jobs/landing-artifact/result",
            headers=self.read_headers(correlation="artifact-after-cancel"),
        )
        self.assertEqual(
            ("cancelled", None, None),
            (
                after.json()["state"],
                after.json()["artifact_digest"],
                after.json()["live_url"],
            ),
        )

    def test_provider_exception_persists_terminal_state_before_idempotent_replay(self):
        profile_digest = "9" * 64
        provider = FailingLandingProvider()
        client = self.client(
            provider=provider, profile_digest=profile_digest
        )
        headers = self.submit_headers(key="landing-provider-failure")

        first = client.post(
            "/v1/landing-inputs", headers=headers, content=b"provider failure"
        )
        replay = client.post(
            "/v1/landing-inputs", headers=headers, content=b"provider failure"
        )
        result = client.get(
            "/v1/landing-jobs/landing-provider-failure/result",
            headers=self.read_headers(correlation="provider-failure-result"),
        )

        self.assertEqual((202, 202, 200), (first.status_code, replay.status_code, result.status_code))
        self.assertEqual("provider_unavailable", first.json()["state"])
        self.assertEqual(first.json(), replay.json())
        self.assertEqual("provider_unavailable", result.json()["state"])
        self.assertEqual(1, provider.calls)
        self.assertEqual([], list((Path(self.temporary.name) / "blobs").glob("*.blob")))

    def test_contradictory_provider_outcome_fails_closed_before_artifact_builder(self):
        configured = fixture_profile()
        builder = BoundArtifactBuilder()
        client = self.client(
            provider=ContradictoryLandingProvider(
                FixedCommandLandingProvider(configured, clock=provider_clock())
            ),
            profile_digest=configured.profile_digest,
            artifact_builder=builder,
        )
        response = client.post(
            "/v1/landing-inputs",
            headers=self.submit_headers(key="landing-contradictory"),
            content=b"contradictory provider evidence",
        )

        self.assertEqual(202, response.status_code, response.text)
        self.assertEqual("provider_unavailable", response.json()["state"])
        self.assertEqual(0, builder.calls)

    def test_landing_streams_above_global_limit_without_raising_task_limit(self):
        client = self.client()
        header = (
            (0x7FF << 21)
            | (3 << 19)
            | (1 << 17)
            | (1 << 16)
            | (14 << 12)
            | (2 << 10)
        ).to_bytes(4, "big")
        payload = (header + b"\x00" * 1_436) * 729
        landing = client.post(
            "/v1/landing-inputs",
            headers=self.submit_headers(
                key="landing-large-audio", media_type="audio/mpeg"
            ),
            content=payload,
        )
        self.assertEqual(202, landing.status_code, landing.text)
        legacy = client.post(
            "/v1/tasks",
            headers={
                "Authorization": f"Bearer {TOKEN_A}",
                "Idempotency-Key": "legacy-large",
                "X-Correlation-ID": "legacy-large-correlation",
                "Content-Type": "application/json",
            },
            content=payload,
        )
        self.assertEqual(413, legacy.status_code)

    def test_landing_upload_uses_one_awaited_sync_call_without_background_queue(self):
        source = Path(create_app.__code__.co_filename).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        called_attributes = [
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        ]

        self.assertNotIn("queue", imported_modules)
        self.assertNotIn("create_task", called_attributes)
        self.assertEqual(1, called_attributes.count("to_thread"))

    def test_predecessor_contract_migration_showcase_and_published_package_are_frozen(self):
        def aggregate(paths):
            digest = hashlib.sha256()
            values = tuple(sorted(paths, key=lambda item: item.as_posix()))
            for path in values:
                name = path.as_posix().encode()
                body = path.read_bytes()
                digest.update(len(name).to_bytes(4, "big"))
                digest.update(name)
                digest.update(len(body).to_bytes(8, "big"))
                digest.update(body)
            return len(values), digest.hexdigest()

        migrations = Path("factory/src/adaptive_factory/resources").glob("[0-9][0-9][0-9]_*.sql")
        predecessor_contracts = (
            path
            for path in Path("factory/contracts").rglob("*")
            if path.is_file()
            and "landing-" not in path.name
            and path.name != "static-landing-spec.v1.schema.json"
        )
        showcase = (
            path for path in Path("side-projects/seo-landing-showcase").rglob("*") if path.is_file()
        )
        self.assertEqual(
            (18, "7f66b4b72f2ab8807e5ea3c1a924f588f1f5e09feb73a59c847d08ca19663c1c"),
            aggregate(migrations),
        )
        self.assertEqual(
            (23, "98818e23ea78821c1c602774072c77bf7d891ef69fe2ba03f0ecbad9220134fc"),
            aggregate(predecessor_contracts),
        )
        self.assertEqual(
            (6, "f7b4e8b3a53efa226cd198d7ca9449db882ddbc63792af7284457251c8e17c96"),
            aggregate(showcase),
        )
        package = Path("packages/adaptive-grok-build-pro-v2.0.13.zip")
        self.assertEqual(
            "3d5179f589c507143f4b93a98d2518e37e470e8566a62f77b31c35743ed8240c",
            hashlib.sha256(package.read_bytes()).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
