"""Default-off live composition automatically seals the complete L5 landing artifact."""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from adaptive_factory.landing_artifact import DEPLOY_MEMBERS
from adaptive_factory.landing_intake import PrivateLandingBlobStore
from adaptive_factory.landing_normalizer import (
    LANDING_NORMALIZATION_DRAFT_SCHEMA_SHA256,
    LANDING_NORMALIZER_PROMPT_SHA256,
    CodexLandingProfile,
)
from adaptive_factory.landing_renderer import TARGET_REPOSITORY_ID
from adaptive_factory.landing_runtime import (
    LandingLiveBindingV1,
    LandingRuntimeError,
    compose_landing_live,
    compose_unavailable_landing,
    implemented_live_binding,
)
from adaptive_factory.models import Actor
from factory.tests.test_landing_normalizer import RecordingExecutor, draft
from factory.tests.test_landing_renderer import sealed_target

FIXED_TIME = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)
OBSERVED_SHA = "80d621545938e24c296420d7f685f2d0b2b5785e"
OBSERVED_TREE = "a1c2eff37ec808a53b2aeec089a5f6d7cb72bd55"


class FactoryLiveAutoLandingTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="landing-live-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.executable = self.root / "codex"
        self.executable.write_bytes(b"sealed-codex-fixture")
        self.executable.chmod(0o700)
        (self.root / "blobs").mkdir(mode=0o700)
        (self.root / "scratch").mkdir(mode=0o700)
        (self.root / "artifacts").mkdir(mode=0o700)
        self.actor = Actor(
            "tenant-1",
            "operator",
            frozenset({"landing:submit", "landing:read"}),
            frozenset({TARGET_REPOSITORY_ID}),
        )
        self.blobs = PrivateLandingBlobStore(
            self.root / "blobs",
            repository_root=Path(__file__).resolve().parents[2],
            clock=lambda: FIXED_TIME,
        )

    def _profile(self) -> CodexLandingProfile:
        return CodexLandingProfile.from_facts(
            {
                "schema_version": 1,
                "profile_id": "codex-landing-offline-fixture",
                "provider_id": "codex-offline-fixture",
                "model_id": "fixture-model-v1",
                "cli_version": "0.153.4",
                "executable": str(self.executable),
                "executable_sha256": hashlib.sha256(self.executable.read_bytes()).hexdigest(),
                "prompt_template_digest": LANDING_NORMALIZER_PROMPT_SHA256,
                "tool_policy_digest": "3" * 64,
                "output_schema_digest": LANDING_NORMALIZATION_DRAFT_SCHEMA_SHA256,
                "decoder_digest": "5" * 64,
                "timeout_seconds": 30,
                "max_stdout_bytes": 262_144,
                "max_stderr_bytes": 65_536,
                "available": True,
            }
        )

    def test_unavailable_composition_never_calls_executor_or_sets_live_url(self) -> None:
        executor = RecordingExecutor()
        service = compose_unavailable_landing(self.blobs, clock=lambda: FIXED_TIME)
        created = service.submit(
            job_id="job-live-unavailable",
            repository_id=TARGET_REPOSITORY_ID,
            exact_base_sha="699010380f4f90a0193a9c22090c35e6aded7d2c",
            exact_base_tree="f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4",
            media_type="text/plain",
            chunks=(b"Build a bounded landing candidate",),
            actor=self.actor,
        )
        self.assertEqual("provider_unavailable", created.job.state)
        self.assertIsNone(created.job.result_view()["live_url"])
        self.assertEqual([], executor.requests)
        self.assertIsNone(service._artifact_builder)

    def test_observed_landing_sha_fails_closed_before_executor(self) -> None:
        executor = RecordingExecutor()
        binding = implemented_live_binding(enabled=True)
        drifted = LandingLiveBindingV1(
            schema_version=1,
            repository_id=binding.repository_id,
            exact_base_sha=OBSERVED_SHA,
            exact_base_tree=OBSERVED_TREE,
            renderer_version=binding.renderer_version,
            deploy_members=binding.deploy_members,
            write_paths=binding.write_paths,
            enabled=True,
        )
        with self.assertRaises(LandingRuntimeError) as raised:
            compose_landing_live(
                binding=drifted,
                profile=self._profile(),
                executor=executor,
                source_repository=self.root,
                scratch_root=self.root / "scratch",
                output_directory=self.root / "artifacts",
                blobs=self.blobs,
            )
        self.assertEqual("source_binding_unimplemented", str(raised.exception))
        self.assertEqual([], executor.requests)

    def test_disabled_binding_cannot_compose_live(self) -> None:
        with self.assertRaises(LandingRuntimeError) as raised:
            compose_landing_live(
                binding=implemented_live_binding(enabled=False),
                profile=self._profile(),
                executor=RecordingExecutor(),
                source_repository=self.root,
                scratch_root=self.root / "scratch",
                output_directory=self.root / "artifacts",
                blobs=self.blobs,
            )
        self.assertEqual("live_disabled", str(raised.exception))

    def test_injected_executor_automatically_seals_complete_artifact(self) -> None:
        payload = b"Build a bounded landing candidate"
        executor = RecordingExecutor(draft())
        with sealed_target() as (target, base_sha, base_tree), patch.multiple(
            "adaptive_factory.landing_renderer",
            TARGET_BASE_SHA=base_sha,
            TARGET_BASE_TREE=base_tree,
        ), patch.multiple(
            "adaptive_factory.landing_service",
            TARGET_BASE_SHA=base_sha,
            TARGET_BASE_TREE=base_tree,
        ):
            binding = implemented_live_binding(enabled=True)
            self.assertEqual(base_sha, binding.exact_base_sha)
            service = compose_landing_live(
                binding=binding,
                profile=self._profile(),
                executor=executor,
                source_repository=target,
                scratch_root=self.root / "scratch",
                output_directory=self.root / "artifacts",
                blobs=self.blobs,
                clock=lambda: FIXED_TIME,
            )
            created = service.submit(
                job_id="job-live-ready",
                repository_id=TARGET_REPOSITORY_ID,
                exact_base_sha=base_sha,
                exact_base_tree=base_tree,
                media_type="text/plain",
                chunks=(payload,),
                actor=self.actor,
            )
            self.assertEqual("artifact_ready", created.job.state)
            self.assertIsNone(created.job.result_view()["live_url"])
            self.assertEqual(1, len(executor.requests))
            self.assertIsNotNone(created.job.artifact)
            self.assertEqual(
                tuple(sorted(DEPLOY_MEMBERS)),
                created.job.sealed_artifact.member_names,
            )
            self.assertTrue(created.job.sealed_artifact.zip_path.is_file())

    def test_pdf_stops_before_executor_on_live_composition(self) -> None:
        executor = RecordingExecutor()
        with sealed_target() as (target, base_sha, base_tree), patch.multiple(
            "adaptive_factory.landing_renderer",
            TARGET_BASE_SHA=base_sha,
            TARGET_BASE_TREE=base_tree,
        ), patch.multiple(
            "adaptive_factory.landing_service",
            TARGET_BASE_SHA=base_sha,
            TARGET_BASE_TREE=base_tree,
        ):
            service = compose_landing_live(
                binding=implemented_live_binding(enabled=True),
                profile=self._profile(),
                executor=executor,
                source_repository=target,
                scratch_root=self.root / "scratch",
                output_directory=self.root / "artifacts",
                blobs=self.blobs,
                clock=lambda: FIXED_TIME,
            )
            created = service.submit(
                job_id="job-live-pdf",
                repository_id=TARGET_REPOSITORY_ID,
                exact_base_sha=base_sha,
                exact_base_tree=base_tree,
                media_type="application/pdf",
                chunks=(b"%PDF-1.4\n/Type /Page\n%%EOF",),
                actor=self.actor,
            )
            self.assertEqual("needs_human", created.job.state)
            self.assertEqual("pdf_extractor_unavailable", created.job.reason_code)
            self.assertEqual([], executor.requests)
            self.assertIsNone(created.job.result_view()["live_url"])


if __name__ == "__main__":
    unittest.main()
