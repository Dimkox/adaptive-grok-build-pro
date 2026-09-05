from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from adaptive_factory.landing_artifact import (
    DEPLOY_MEMBERS,
    ExactGitLandingArtifactSource,
    LandingArtifactPackager,
)
from adaptive_factory.landing_contracts import (
    LandingInputV1,
    LandingProviderEvidenceV1,
    StaticLandingSpecV1,
)
from adaptive_factory.landing_coordinator import LandingCoordinator
from adaptive_factory.landing_evaluation import DeterministicLandingEvaluator
from adaptive_factory.landing_intake import PrivateLandingBlobStore
from adaptive_factory.landing_provider import (
    LandingNormalizationOutcome,
    LandingNormalizationRequest,
)
from adaptive_factory.landing_renderer import (
    DeterministicLandingRenderer,
    ExactGitLandingWorkspace,
    TARGET_REPOSITORY_ID,
)
from adaptive_factory.landing_runtime import (
    CoordinatedLandingArtifactBuilder,
    CoordinatedLandingArtifactResult,
)
from adaptive_factory.landing_service import LandingArtifactBuildResult
from adaptive_factory.landing_service import LandingApplicationService
from adaptive_factory.landing_sqlite_store import SQLiteLandingJobStore
from adaptive_factory.models import Actor
from factory.tests.test_landing_renderer import landing_spec, sealed_target


FIXED_TIME = datetime(2026, 9, 5, 14, 0, tzinfo=timezone.utc)
PROFILE_DIGEST = "7" * 64


def _bound_records(base_sha: str, base_tree: str):
    body = b"Build a bounded landing candidate"
    source = LandingInputV1.from_facts(
        {
            "schema_version": 1,
            "job_id": "job-runtime-1",
            "tenant_id": "tenant-1",
            "repository_id": TARGET_REPOSITORY_ID,
            "exact_base_sha": base_sha,
            "exact_base_tree": base_tree,
            "site_id": "therealaidarkfactory.online",
            "media_kind": "text",
            "media_type": "text/plain",
            "byte_length": len(body),
            "content_sha256": hashlib.sha256(body).hexdigest(),
            "quarantine_ref_digest": hashlib.sha256(b"quarantine:" + body).hexdigest(),
            "received_at": "2026-09-05T13:59:00Z",
            "expires_at": "2026-09-06T13:59:00Z",
        }
    )
    spec, evidence = _bound_output(source)
    return source, spec, evidence


def _bound_output(source: LandingInputV1):
    spec_facts = landing_spec().to_dict()
    spec_facts.pop("spec_digest")
    spec_facts["input_digest"] = source.input_digest
    spec_facts["title"] = f"Bounded landing {source.job_id}"
    spec = StaticLandingSpecV1.from_facts(spec_facts)
    evidence = LandingProviderEvidenceV1.from_facts(
        {
            "schema_version": 1,
            "input_digest": source.input_digest,
            "profile_digest": PROFILE_DIGEST,
            "provider_id": "sealed-fixture",
            "adapter_id": "fixed-command",
            "adapter_version": "1.0.0",
            "model_id": "fixture-model",
            "prompt_template_digest": "1" * 64,
            "tool_policy_digest": "2" * 64,
            "output_schema_digest": "3" * 64,
            "decoder_digest": "4" * 64,
            "request_digest": "5" * 64,
            "response_digest": "6" * 64,
            "usage_input_units": 1,
            "usage_output_units": 1,
            "started_at": "2026-09-05T14:00:00Z",
            "completed_at": "2026-09-05T14:00:00Z",
            "disposition": "fixture_ready",
        }
    )
    return spec, evidence


class BoundProvider:
    def __init__(self) -> None:
        self.calls = 0

    def normalize(self, request: LandingNormalizationRequest, read_blob):
        self.calls += 1
        read_blob()
        spec, evidence = _bound_output(request.source)
        return LandingNormalizationOutcome(spec, evidence)


class NeverProvider:
    def __init__(self) -> None:
        self.calls = 0

    def normalize(self, _request, _read_blob):
        self.calls += 1
        raise AssertionError("replayed provider work")


class NeverBuilder:
    def __init__(self) -> None:
        self.calls = 0

    def build(self, *_args):
        self.calls += 1
        raise AssertionError("replayed artifact work")


class RecordingBuilder:
    def __init__(self, delegate) -> None:
        self.delegate = delegate
        self.error = None

    def build(self, *args):
        try:
            return self.delegate.build(*args)
        except Exception as exc:
            self.error = exc
            raise


class CoordinatedLandingArtifactBuilderTests(unittest.TestCase):
    def test_offline_fixture_reaches_artifact_and_retains_full_sealed_metadata(self):
        with sealed_target() as (target, base_sha, base_tree), tempfile.TemporaryDirectory(
            prefix="landing-runtime-scratch-"
        ) as scratch, tempfile.TemporaryDirectory(
            prefix="landing-runtime-output-"
        ) as output:
            source, spec, evidence = _bound_records(base_sha, base_tree)
            builder = CoordinatedLandingArtifactBuilder(
                LandingCoordinator(
                    ExactGitLandingWorkspace(target, scratch_root=Path(scratch)),
                    DeterministicLandingRenderer(),
                    DeterministicLandingEvaluator(clock=lambda: FIXED_TIME),
                    clock=lambda: FIXED_TIME,
                ),
                LandingArtifactPackager(ExactGitLandingArtifactSource(target)),
                Path(output),
            )

            result = builder.build(source, spec, evidence)

            self.assertIsInstance(result, CoordinatedLandingArtifactResult)
            self.assertIsInstance(result, LandingArtifactBuildResult)
            self.assertEqual("candidate_ready", result.run.disposition)
            self.assertIs(result.artifact, result.sealed.artifact)
            self.assertEqual(source.input_digest, result.artifact.input_digest)
            self.assertEqual(spec.spec_digest, result.artifact.spec_digest)
            self.assertEqual(PROFILE_DIGEST, result.artifact.profile_digest)
            self.assertEqual(tuple(sorted(DEPLOY_MEMBERS)), result.sealed.member_names)
            self.assertTrue(result.sealed.zip_path.is_file())
            self.assertTrue(result.sealed.sidecar_path.is_file())
            self.assertTrue(result.sealed.manifest_bytes)

    def test_sqlite_service_restart_retains_revalidates_and_never_replays_artifact(self):
        actor = Actor(
            "tenant-1",
            "operator",
            frozenset({"landing:submit", "landing:read"}),
            frozenset({TARGET_REPOSITORY_ID}),
        )
        payload = b"Build a bounded landing candidate"
        with sealed_target() as (target, base_sha, base_tree), tempfile.TemporaryDirectory(
            prefix="landing-runtime-durable-"
        ) as directory, patch.multiple(
            "adaptive_factory.landing_service",
            TARGET_BASE_SHA=base_sha,
            TARGET_BASE_TREE=base_tree,
        ):
            root = Path(directory)
            (root / "scratch").mkdir(mode=0o700)
            provider = BoundProvider()
            store = SQLiteLandingJobStore(
                root / "state", repository_root=Path(__file__).resolve().parents[2]
            )
            builder = RecordingBuilder(CoordinatedLandingArtifactBuilder(
                LandingCoordinator(
                    ExactGitLandingWorkspace(target, scratch_root=root / "scratch"),
                    DeterministicLandingRenderer(),
                    DeterministicLandingEvaluator(clock=lambda: FIXED_TIME),
                    clock=lambda: FIXED_TIME,
                ),
                LandingArtifactPackager(ExactGitLandingArtifactSource(target)),
                root / "artifacts",
            ))
            service = LandingApplicationService(
                store,
                PrivateLandingBlobStore(
                    root / "blobs", repository_root=Path(__file__).resolve().parents[2]
                ),
                provider,
                profile_digest=PROFILE_DIGEST,
                artifact_builder=builder,
                clock=lambda: FIXED_TIME,
            )

            created = service.submit(
                job_id="job-runtime-1",
                repository_id=TARGET_REPOSITORY_ID,
                exact_base_sha=base_sha,
                exact_base_tree=base_tree,
                media_type="text/plain",
                chunks=(payload,),
                actor=actor,
            )
            self.assertEqual(
                "artifact_ready", created.job.state, (created.job, builder.error)
            )
            self.assertIsNotNone(created.job.sealed_artifact)
            retained = created.job.sealed_artifact
            second = service.submit(
                job_id="job-runtime-2",
                repository_id=TARGET_REPOSITORY_ID,
                exact_base_sha=base_sha,
                exact_base_tree=base_tree,
                media_type="text/plain",
                chunks=(payload,),
                actor=actor,
            )
            self.assertEqual("artifact_ready", second.job.state, second.job)
            self.assertIsNotNone(second.job.sealed_artifact)
            self.assertNotEqual(
                retained.zip_path, second.job.sealed_artifact.zip_path
            )
            third = service.submit(
                job_id="job-runtime-3",
                repository_id=TARGET_REPOSITORY_ID,
                exact_base_sha=base_sha,
                exact_base_tree=base_tree,
                media_type="text/plain",
                chunks=(payload,),
                actor=actor,
            )
            self.assertEqual("artifact_ready", third.job.state, third.job)
            self.assertIsNotNone(third.job.sealed_artifact)
            store.close()

            replay_provider = NeverProvider()
            replay_builder = NeverBuilder()
            reopened = SQLiteLandingJobStore(
                root / "state", repository_root=Path(__file__).resolve().parents[2]
            )
            replay_service = LandingApplicationService(
                reopened,
                PrivateLandingBlobStore(
                    root / "blobs", repository_root=Path(__file__).resolve().parents[2]
                ),
                replay_provider,
                profile_digest=PROFILE_DIGEST,
                artifact_builder=replay_builder,
                clock=lambda: FIXED_TIME,
            )
            replay = replay_service.submit(
                job_id="job-runtime-1",
                repository_id=TARGET_REPOSITORY_ID,
                exact_base_sha=base_sha,
                exact_base_tree=base_tree,
                media_type="text/plain",
                chunks=(payload,),
                actor=actor,
            )
            self.assertFalse(replay.created)
            self.assertEqual(retained, replay.job.sealed_artifact)
            self.assertEqual((0, 0), (replay_provider.calls, replay_builder.calls))
            self.assertEqual(
                created.job.result_view(),
                replay_service.result(
                    "job-runtime-1",
                    repository_id=TARGET_REPOSITORY_ID,
                    actor=actor,
                ).result_view(),
            )
            reopened.close()

            with sqlite3.connect(store.database_path) as connection:
                connection.execute(
                    """UPDATE landing_jobs
                          SET artifact_json = (
                                SELECT artifact_json FROM landing_jobs
                                 WHERE tenant_id = 'tenant-1' AND job_id = 'job-runtime-1'
                              ),
                              sealed_artifact_json = (
                                SELECT sealed_artifact_json FROM landing_jobs
                                 WHERE tenant_id = 'tenant-1' AND job_id = 'job-runtime-1'
                              )
                        WHERE tenant_id = 'tenant-1' AND job_id = 'job-runtime-2'"""
                )
            retained.sidecar_path.write_bytes(b"tampered\n")
            third.job.sealed_artifact.zip_path.unlink()
            tampered = SQLiteLandingJobStore(
                root / "state", repository_root=Path(__file__).resolve().parents[2]
            )
            failed_service = LandingApplicationService(
                tampered,
                PrivateLandingBlobStore(
                    root / "blobs", repository_root=Path(__file__).resolve().parents[2]
                ),
                NeverProvider(),
                profile_digest=PROFILE_DIGEST,
                artifact_builder=NeverBuilder(),
                clock=lambda: FIXED_TIME,
            )
            failed = failed_service.result(
                "job-runtime-1", repository_id=TARGET_REPOSITORY_ID, actor=actor
            )
            swapped = failed_service.result(
                "job-runtime-2", repository_id=TARGET_REPOSITORY_ID, actor=actor
            )
            missing = failed_service.result(
                "job-runtime-3", repository_id=TARGET_REPOSITORY_ID, actor=actor
            )
            self.assertEqual(("needs_human", "artifact_integrity"), (failed.state, failed.reason_code))
            self.assertEqual(
                ("needs_human", "artifact_integrity"),
                (swapped.state, swapped.reason_code),
            )
            self.assertEqual(
                ("needs_human", "artifact_integrity"),
                (missing.state, missing.reason_code),
            )
            self.assertEqual(
                failed,
                failed_service.result(
                    "job-runtime-1",
                    repository_id=TARGET_REPOSITORY_ID,
                    actor=actor,
                ),
            )
            self.assertEqual(
                swapped,
                failed_service.result(
                    "job-runtime-2",
                    repository_id=TARGET_REPOSITORY_ID,
                    actor=actor,
                ),
            )
            self.assertEqual(
                missing,
                failed_service.result(
                    "job-runtime-3",
                    repository_id=TARGET_REPOSITORY_ID,
                    actor=actor,
                ),
            )
            tampered.close()

if __name__ == "__main__":
    unittest.main()
