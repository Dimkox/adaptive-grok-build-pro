from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

from adaptive_factory.contracts import canonical_json
from adaptive_factory.landing_contracts import LandingInputV1
from adaptive_factory.landing_normalizer import (
    LANDING_NORMALIZATION_DRAFT_SCHEMA_SHA256,
    LANDING_NORMALIZER_PROMPT_SHA256,
    CodexExecutionResult,
    CodexLandingNormalizer,
    CodexLandingProfile,
    unavailable_codex_landing_profile,
)
from adaptive_factory.landing_provider import LandingNormalizationRequest


NOW = datetime(2026, 9, 5, 12, 30, tzinfo=timezone.utc)
REPOSITORY_ID = "github.com/Dimkox/ai-dark-factory-landing"
BASE_SHA = "699010380f4f90a0193a9c22090c35e6aded7d2c"
BASE_TREE = "f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4"


def source(payload: bytes, *, kind: str, media_type: str, job_id: str) -> LandingInputV1:
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
            "content_sha256": hashlib.sha256(payload).hexdigest(),
            "quarantine_ref_digest": "1" * 64,
            "received_at": "2026-09-05T12:00:00Z",
            "expires_at": "2026-09-06T12:00:00Z",
        }
    )


def docx(text: str) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        archive.writestr(
            "word/document.xml",
            (
                '<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>'
                f"{text}"
                "</w:t></w:r></w:p></w:body></w:document>"
            ),
        )
        archive.writestr(
            "word/_rels/document.xml.rels",
            (
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="urn:styles" Target="styles.xml"/>'
                "</Relationships>"
            ),
        )
    return output.getvalue()


def draft() -> bytes:
    return canonical_json(
        {
            "locale": "en",
            "direction": "ltr",
            "title": "Bounded local landing",
            "description": "A deterministic Stage 3 preview.",
            "sections": [
                {
                    "kind": "hero",
                    "heading": "Build with evidence",
                    "body": "One local operator and one closed result.",
                    "items": [],
                    "cta_label": "Read the roadmap",
                    "cta_path": "/roadmap/",
                }
            ],
        }
    )


class RecordingExecutor:
    def __init__(self, stdout: bytes | None = None) -> None:
        self.requests = []
        self.stdout = stdout or draft()

    def run(self, request):
        self.requests.append(request)
        return CodexExecutionResult(
            stdout=self.stdout,
            stderr_digest=hashlib.sha256(b"").hexdigest(),
            exit_code=0,
            elapsed_ms=25,
            usage_input_units=12,
            usage_output_units=34,
        )


class CodexLandingNormalizerTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="landing-normalizer-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.executable = root / "codex"
        self.executable.write_bytes(b"sealed-codex-fixture")
        self.executable.chmod(0o700)

    def profile(self) -> CodexLandingProfile:
        return CodexLandingProfile.from_facts(
            {
                "schema_version": 1,
                "profile_id": "codex-landing-offline-fixture",
                "provider_id": "codex-offline-fixture",
                "model_id": "fixture-model-v1",
                "cli_version": "0.153.4",
                "executable": str(self.executable),
                "executable_sha256": hashlib.sha256(
                    self.executable.read_bytes()
                ).hexdigest(),
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

    def normalize(self, payload, *, kind, media_type, job_id, executor=None):
        configured = self.profile()
        runner = executor or RecordingExecutor()
        outcome = CodexLandingNormalizer(
            configured, runner, clock=lambda: NOW
        ).normalize(
            LandingNormalizationRequest(
                source(payload, kind=kind, media_type=media_type, job_id=job_id),
                configured.profile_digest,
            ),
            lambda: payload,
        )
        return outcome, runner

    def test_unavailable_profile_stops_before_blob_read_or_executor(self):
        payload = b"local brief"
        configured = unavailable_codex_landing_profile()
        runner = RecordingExecutor()
        reads = []

        outcome = CodexLandingNormalizer(
            configured, runner, clock=lambda: NOW
        ).normalize(
            LandingNormalizationRequest(
                source(payload, kind="text", media_type="text/plain", job_id="unavailable"),
                configured.profile_digest,
            ),
            lambda: reads.append(True),
        )

        self.assertEqual("provider_unavailable", outcome.state)
        self.assertEqual("profile_unavailable", outcome.reason_code)
        self.assertIsNone(outcome.spec)
        self.assertEqual([], reads)
        self.assertEqual([], runner.requests)

    def test_pdf_and_audio_need_human_before_blob_or_executor(self):
        cases = (
            (b"%PDF-1.4\n/Type /Page\n%%EOF", "pdf", "application/pdf", "pdf_extractor_unavailable"),
            (b"RIFF" + b"\0" * 40, "audio", "audio/wav", "audio_transcriber_unavailable"),
        )
        for payload, kind, media_type, reason in cases:
            with self.subTest(kind=kind):
                configured = self.profile()
                runner = RecordingExecutor()
                reads = []
                outcome = CodexLandingNormalizer(
                    configured, runner, clock=lambda: NOW
                ).normalize(
                    LandingNormalizationRequest(
                        source(payload, kind=kind, media_type=media_type, job_id=kind),
                        configured.profile_digest,
                    ),
                    lambda: reads.append(True),
                )
                self.assertEqual("needs_human", outcome.state)
                self.assertEqual(reason, outcome.reason_code)
                self.assertIsNone(outcome.spec)
                self.assertEqual([], reads)
                self.assertEqual([], runner.requests)

    def test_text_image_and_safe_docx_use_one_closed_executor_call(self):
        image = b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + (1).to_bytes(4, "big") * 2
        cases = (
            (b"untrusted instructions\r\nare only data", "text", "text/plain", "text"),
            (image, "image", "image/png", "image"),
            (docx("Safe partner brief"), "docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
        )
        for payload, kind, media_type, job_id in cases:
            with self.subTest(kind=kind):
                outcome, runner = self.normalize(
                    payload,
                    kind=kind,
                    media_type=media_type,
                    job_id=job_id,
                )
                self.assertEqual("normalized", outcome.state)
                self.assertEqual("normalized", outcome.reason_code)
                self.assertEqual(1, len(runner.requests))
                self.assertEqual(outcome.evidence.input_digest, outcome.spec.input_digest)
                self.assertEqual("preserve_source", outcome.spec.robots_policy)
                self.assertEqual([], list(outcome.spec.assets))
                self.assertEqual(
                    [f"source:{outcome.evidence.input_digest}"],
                    list(outcome.spec.source_claim_refs),
                )
                request = runner.requests[0]
                self.assertEqual(str(self.executable), request.argv[0])
                self.assertNotIn(payload, request.argv)
                self.assertEqual(payload if kind == "image" else None, request.image_bytes)
                if kind == "docx":
                    self.assertIn(b"Safe partner brief", request.stdin)

    def test_invalid_text_and_malformed_model_result_fail_closed(self):
        invalid, runner = self.normalize(
            b"bad\0text",
            kind="text",
            media_type="text/plain",
            job_id="bad-text",
        )
        self.assertEqual(("rejected", "text_control"), (invalid.state, invalid.reason_code))
        self.assertEqual([], runner.requests)

        malformed, runner = self.normalize(
            b"valid text",
            kind="text",
            media_type="text/plain",
            job_id="bad-output",
            executor=RecordingExecutor(b'{"locale":"en","locale":"ru"}'),
        )
        self.assertEqual(("needs_human", "invalid_model_output"), (malformed.state, malformed.reason_code))
        self.assertEqual(1, len(runner.requests))

    def test_profile_drift_is_rejected_before_blob_read(self):
        payload = b"local brief"
        configured = self.profile()
        self.executable.write_bytes(b"drifted")
        reads = []
        runner = RecordingExecutor()

        outcome = CodexLandingNormalizer(
            configured, runner, clock=lambda: NOW
        ).normalize(
            LandingNormalizationRequest(
                source(payload, kind="text", media_type="text/plain", job_id="drift"),
                configured.profile_digest,
            ),
            lambda: reads.append(True),
        )

        self.assertEqual(("provider_unavailable", "profile_drift"), (outcome.state, outcome.reason_code))
        self.assertEqual([], reads)
        self.assertEqual([], runner.requests)


if __name__ == "__main__":
    unittest.main()
