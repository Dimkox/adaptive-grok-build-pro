from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from adaptive_factory.landing_contracts import LandingInputV1
from adaptive_factory.landing_provider import (
    FixedCommandLandingProvider,
    LandingNormalizationRequest,
    LandingProviderError,
    LandingProviderProfile,
    STATIC_LANDING_SPEC_SCHEMA_SHA256,
    UnavailableLandingProvider,
    unavailable_landing_profile,
)


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "landing_provider_fixture.py"
STATIC_SPEC_SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "contracts"
    / "jsonschema"
    / "static-landing-spec.v1.schema.json"
)
NOW = datetime(2026, 9, 4, 11, 0, tzinfo=timezone.utc)
REPOSITORY_ID = "github.com/Dimkox/ai-dark-factory-landing"
BASE_SHA = "176efcaab931c2482781ff163c621b10aa05dee9"
BASE_TREE = "f2bdcecc6dbe9ecc82007610d398ca12bd75e07f"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def landing_input(payload=b"same semantic request", *, kind="text", media_type="text/plain", job_id="job-1"):
    return LandingInputV1.from_facts(
        {
            "schema_version": 1,
            "job_id": job_id,
            "tenant_id": "tenant-1",
            "repository_id": REPOSITORY_ID,
            "exact_base_sha": BASE_SHA,
            "exact_base_tree": BASE_TREE,
            "site_id": "therealaidarkfactory.online",
            "media_kind": kind,
            "media_type": media_type,
            "byte_length": len(payload),
            "content_sha256": digest(payload),
            "quarantine_ref_digest": "1" * 64,
            "received_at": "2026-09-04T11:00:00Z",
            "expires_at": "2026-09-05T11:00:00Z",
        }
    )


def profile(mode="normal", *, executable=FIXTURE, timeout_seconds=2):
    executable = Path(executable).resolve()
    return LandingProviderProfile.from_facts(
        {
            "schema_version": 1,
            "profile_id": f"sealed-{mode}",
            "provider_id": "sealed-fixture",
            "adapter_id": "fixed-command",
            "adapter_version": "1.0.0",
            "model_id": "fixture-model-v1",
            "executable": str(executable),
            "executable_sha256": digest(executable.read_bytes()),
            "argv": [f"--mode={mode}"],
            "prompt_template_digest": "2" * 64,
            "tool_policy_digest": "3" * 64,
            "output_schema_digest": STATIC_LANDING_SPEC_SCHEMA_SHA256,
            "decoder_digest": "5" * 64,
            "timeout_seconds": timeout_seconds,
            "max_stdout_bytes": 262_144,
            "max_stderr_bytes": 65_536,
            "available": True,
        }
    )


def clock():
    values = iter((NOW, NOW + timedelta(seconds=1)))
    return lambda: next(values)


class LandingProviderTests(unittest.TestCase):
    def test_unavailable_default_stops_before_blob_read_or_process_creation(self):
        source = landing_input()
        configured = unavailable_landing_profile()
        request = LandingNormalizationRequest(source, configured.profile_digest)
        reads = []

        def read_blob():
            reads.append(True)
            raise AssertionError("unavailable provider read the blob")

        with patch("adaptive_factory.landing_provider.subprocess.Popen", side_effect=AssertionError("spawned")):
            outcome = UnavailableLandingProvider(clock=clock()).normalize(request, read_blob)
        self.assertIsNone(outcome.spec)
        self.assertEqual(outcome.evidence.disposition, "provider_unavailable")
        self.assertEqual((outcome.evidence.usage_input_units, outcome.evidence.usage_output_units), (0, 0))
        self.assertEqual(reads, [])

    def test_explicit_sealed_fixture_normalizes_all_five_kinds_to_same_semantics(self):
        self.assertEqual(
            digest(STATIC_SPEC_SCHEMA.read_bytes()),
            STATIC_LANDING_SPEC_SCHEMA_SHA256,
        )
        kinds = (
            ("text", "text/plain"),
            ("audio", "audio/wav"),
            ("image", "image/png"),
            ("pdf", "application/pdf"),
            ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        )
        semantic = []
        for index, (kind, media_type) in enumerate(kinds, 1):
            with self.subTest(kind=kind):
                payload = f"equivalent-{kind}".encode()
                source = landing_input(payload, kind=kind, media_type=media_type, job_id=f"job-{index}")
                configured = profile()
                outcome = FixedCommandLandingProvider(configured, clock=clock()).normalize(
                    LandingNormalizationRequest(source, configured.profile_digest), lambda: payload
                )
                self.assertEqual(outcome.evidence.disposition, "fixture_ready")
                self.assertEqual(outcome.evidence.input_digest, source.input_digest)
                self.assertEqual(outcome.spec.robots_policy, "preserve_source")
                value = outcome.spec.to_dict()
                value.pop("input_digest")
                value.pop("spec_digest")
                semantic.append(value)
        self.assertEqual(semantic, [semantic[0]] * 5)

    def test_profile_mismatch_and_executable_drift_fail_before_blob_read(self):
        source = landing_input()
        configured = profile()
        reads = []
        provider = FixedCommandLandingProvider(configured, clock=clock())
        with self.assertRaisesRegex(LandingProviderError, "profile_mismatch"):
            provider.normalize(LandingNormalizationRequest(source, "0" * 64), lambda: reads.append(True))
        self.assertEqual(reads, [])

        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "fixture"
            shutil.copyfile(FIXTURE, copied)
            copied.chmod(0o755)
            drift_profile = profile(executable=copied)
            copied.write_text("#!/usr/bin/python3\nraise SystemExit(0)\n", encoding="utf-8")
            with self.assertRaisesRegex(LandingProviderError, "executable_digest_mismatch"):
                FixedCommandLandingProvider(drift_profile, clock=clock()).normalize(
                    LandingNormalizationRequest(source, drift_profile.profile_digest), lambda: reads.append(True)
                )
        self.assertEqual(reads, [])

    def test_blob_digest_mismatch_fails_without_process(self):
        source = landing_input(b"expected")
        configured = profile()
        with patch("adaptive_factory.landing_provider.subprocess.Popen", side_effect=AssertionError("spawned")):
            with self.assertRaisesRegex(LandingProviderError, "blob_digest_mismatch"):
                FixedCommandLandingProvider(configured, clock=clock()).normalize(
                    LandingNormalizationRequest(source, configured.profile_digest), lambda: b"changed"
                )

    def test_strict_jsonl_and_closed_spec_fail_without_native_retention(self):
        source_payload = b"private source bytes"
        source = landing_input(source_payload)
        cases = {
            "duplicate": "duplicate_json_key",
            "nonfinite": "nonfinite_json",
            "invalid-utf8": "invalid_json",
            "missing-terminal": "missing_terminal",
            "after-terminal": "after_terminal",
            "hostile": "unsafe_content",
        }
        for mode, code in cases.items():
            configured = profile(mode)
            with self.subTest(mode=mode), self.assertRaisesRegex(LandingProviderError, code) as raised:
                FixedCommandLandingProvider(configured, clock=clock()).normalize(
                    LandingNormalizationRequest(source, configured.profile_digest), lambda: source_payload
                )
            self.assertNotIn(source_payload.decode(), str(raised.exception))
            self.assertNotIn("native fixture diagnostic", str(raised.exception))

    def test_stdout_stderr_and_wall_time_are_hard_bounded(self):
        payload = b"bounded"
        source = landing_input(payload)
        cases = {
            "stdout-overflow": "provider_stdout_limit",
            "stderr-overflow": "provider_stderr_limit",
            "sleep": "provider_timeout",
        }
        for mode, code in cases.items():
            configured = profile(mode, timeout_seconds=1)
            with self.subTest(mode=mode), self.assertRaisesRegex(LandingProviderError, code):
                FixedCommandLandingProvider(configured, clock=clock()).normalize(
                    LandingNormalizationRequest(source, configured.profile_digest), lambda: payload
                )

    def test_profile_rejects_shell_or_environment_shaped_configuration(self):
        facts = profile().to_facts()
        for mutation, code in (
            ({"executable": "fixture"}, "profile_executable"),
            ({"argv": ["--mode=normal", "$(touch /tmp/nope)"]}, "profile_argv"),
            ({"output_schema_digest": "4" * 64}, "profile_output_schema"),
            ({"environment_names": ["TOKEN"]}, "unknown_fields"),
        ):
            changed = {**facts, **mutation}
            with self.subTest(code=code), self.assertRaisesRegex(LandingProviderError, code):
                LandingProviderProfile.from_facts(changed)


if __name__ == "__main__":
    unittest.main()
