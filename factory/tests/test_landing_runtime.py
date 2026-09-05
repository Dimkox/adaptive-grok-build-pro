from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import tempfile
import unittest

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
    spec_facts = landing_spec().to_dict()
    spec_facts.pop("spec_digest")
    spec_facts["input_digest"] = source.input_digest
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
    return source, spec, evidence


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


if __name__ == "__main__":
    unittest.main()
