from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

from adaptive_factory.contracts import canonical_json
from adaptive_factory.landing_contracts import (
    LandingInputV1, LandingContractError, StaticLandingSpecV1,
)
from adaptive_factory.landing_normalizer import (
    LANDING_NORMALIZATION_DRAFT_SCHEMA_SHA256,
    LANDING_NORMALIZER_PROMPT_SHA256,
    CodexExecutionResult,
    CodexLandingNormalizer,
    CodexLandingProfile,
    unavailable_codex_landing_profile,
    normalize_landing_text,
    decode_landing_draft,
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


class DraftItemCanonicalizationTests(unittest.TestCase):
    """Canonicalize model item order without changing strict input validation."""

    def _payload(self, items):
        return canonical_json(
            {
                "locale": "ru",
                "direction": "ltr",
                "title": "Услуги по уходу за садом",
                "description": "Профессиональный уход за участком.",
                "sections": [
                    {
                        "kind": "features",
                        "heading": "Что мы делаем",
                        "body": "Полный цикл работ на участке.",
                        "items": items,
                        "cta_label": "Оставить заявку",
                        "cta_path": "/contact/",
                    }
                ],
            }
        )

    def test_model_order_and_duplicates_are_canonicalized(self):
        spec = decode_landing_draft(
            "a" * 64,
            self._payload(
                ["Уборка листвы", "Стрижка газона", "Уборка листвы", "Аэрация почвы"]
            ),
            maximum=1_000_000,
        )
        self.assertEqual(
            ("Аэрация почвы", "Стрижка газона", "Уборка листвы"),
            spec.sections[0].items,
        )

    def test_mixed_language_and_escaped_items_have_stable_canonical_digest(self):
        cases = (
            ("é", "a"),
            ("A", '"quoted"', "\\path", "\nitem", "\titem", "é", "Ж", "中", "a"),
        )
        for expected in cases:
            with self.subTest(expected=expected):
                specs = []
                for items in (list(expected), list(reversed(expected)), [*expected, expected[0]]):
                    spec = decode_landing_draft(
                        "a" * 64, self._payload(items), maximum=1_000_000,
                    )
                    self.assertEqual(expected, spec.sections[0].items)
                    specs.append(spec)
                self.assertEqual(1, len({spec.spec_digest for spec in specs}))

    def test_malformed_outer_sections_raise_contract_error(self):
        document = json.loads(self._payload([]))
        for sections in (None, 3, 1.5, True, False, "", "section", {}, {"items": []}, [],
                         document["sections"] * 13):
            with self.subTest(sections=sections), self.assertRaisesRegex(LandingContractError, "^sections$"):
                decode_landing_draft(
                    "a" * 64, canonical_json({**document, "sections": sections}), maximum=1_000_000,
                )

    def test_twelve_sections_keep_their_original_order(self):
        document = json.loads(self._payload(["z", "a", "z"]))
        headings = [f"Section {index}" for index in range(12, 0, -1)]
        document["sections"] = [
            {**document["sections"][0], "heading": heading} for heading in headings
        ]
        spec = decode_landing_draft("a" * 64, canonical_json(document), maximum=1_000_000)
        self.assertEqual(headings, [section.heading for section in spec.sections])
        self.assertEqual([("a", "z")] * 12, [section.items for section in spec.sections])

    def test_item_limit_applies_before_deduplication(self):
        for items, expected in (([], ()), (["z", "a"] * 6, ("a", "z"))):
            with self.subTest(items=items):
                spec = decode_landing_draft("a" * 64, self._payload(items), maximum=1_000_000)
                self.assertEqual(expected, spec.sections[0].items)
        for items in (["a"] * 13, [f"item-{index}" for index in range(13)]):
            with self.subTest(items=items), self.assertRaisesRegex(LandingContractError, "^section_items$"):
                decode_landing_draft("a" * 64, self._payload(items), maximum=1_000_000)

    def test_invalid_items_keep_their_strict_rejection(self):
        cases = (
            (None, "section_items"), ("a", "section_items"), ({}, "section_items"),
            (["z", None], "invalid_text"), (["z", 3], "invalid_text"),
            (["z", True], "invalid_text"), (["z", {}], "invalid_text"),
            (["z", []], "invalid_text"), (["", ""], "invalid_text"),
            (["e\u0301"], "invalid_text"), (["\0"], "invalid_text"),
            (["a" * 513], "invalid_text"), (["é" * 257], "invalid_text"),
            (["\ud800"], "invalid_text"), (["<script>"], "unsafe_content"),
        )
        document = json.loads(self._payload([]))
        for items, code in cases:
            document["sections"][0]["items"] = items
            with self.subTest(items=items), self.assertRaisesRegex(LandingContractError, f"^{code}(?::|$)"):
                decode_landing_draft(
                    "a" * 64, json.dumps(document).encode(), maximum=1_000_000,
                )

    def test_section_fields_and_content_remain_closed(self):
        document = json.loads(self._payload(["z", "a", "z"]))
        section = document["sections"][0]
        cases = (
            (None, "invalid_object"),
            ({**section, "unknown": True}, "unknown_fields"),
            ({key: value for key, value in section.items() if key != "items"}, "missing_fields"),
            ({**section, "heading": "<script>"}, "unsafe_content"),
            ({**section, "cta_path": "https://example.invalid/"}, "cta_path"),
        )
        for malformed, code in cases:
            with self.subTest(section=malformed), self.assertRaisesRegex(LandingContractError, f"^{code}(?::|$)"):
                decode_landing_draft(
                    "a" * 64, canonical_json({**document, "sections": [malformed]}), maximum=1_000_000,
                )

    def test_strict_spec_still_rejects_noncanonical_items_outside_decoder(self):
        spec = decode_landing_draft("a" * 64, self._payload([]), maximum=1_000_000)
        facts = spec.to_dict()
        del facts["spec_digest"]
        for items in (["z", "a"], ["a", "a"], ["a", "é"]):
            facts["sections"][0]["items"] = items
            with self.subTest(items=items), self.assertRaisesRegex(LandingContractError, "^section_items$"):
                StaticLandingSpecV1.from_facts(facts)


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

    def test_duplicate_docx_document_members_are_rejected_in_both_orders(self):
        for names in (("word/document.xml", "word/document.xml"),
                      ("word/document.xml", "WORD/DOCUMENT.XML")):
            for texts in (("First text", "Second text"), ("Second text", "First text")):
                with self.subTest(names=names, texts=texts):
                    output = io.BytesIO()
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)
                        with zipfile.ZipFile(output, "w") as archive:
                            archive.writestr("[Content_Types].xml", "<Types/>")
                            for name, text in zip(names, texts):
                                archive.writestr(name, '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>' + text + '</w:t></w:r></w:p></w:body></w:document>')
                    with self.assertRaisesRegex(LandingContractError, "docx_path"):
                        normalize_landing_text("docx", output.getvalue())

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

    def test_malformed_sections_return_controlled_outcome_with_evidence(self):
        document = json.loads(draft())
        for sections in (None, 3, True):
            with self.subTest(sections=sections):
                outcome, _ = self.normalize(
                    b"valid text", kind="text", media_type="text/plain", job_id="bad-sections",
                    executor=RecordingExecutor(canonical_json({**document, "sections": sections})),
                )
                self.assertEqual(("needs_human", "invalid_model_output"),
                                 (outcome.state, outcome.reason_code))
                self.assertIsNone(outcome.spec)
                self.assertEqual("provider_unavailable", outcome.evidence.disposition)
                self.assertRegex(outcome.evidence.provider_evidence_digest, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
