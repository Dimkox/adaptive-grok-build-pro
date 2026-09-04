from datetime import datetime, timedelta, timezone
import io
import os
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from adaptive_factory.landing_contracts import LandingContractError
from adaptive_factory.landing_intake import PrivateLandingBlobStore


NOW = datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
REPOSITORY_ID = "github.com/Dimkox/ai-dark-factory-landing"
BASE_SHA = "176efcaab931c2482781ff163c621b10aa05dee9"
BASE_TREE = "f2bdcecc6dbe9ecc82007610d398ca12bd75e07f"


def png(width=1, height=1):
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + struct.pack(">II", width, height) + b"fixture"


def wav(seconds=1):
    sample_rate = 8_000
    data = b"\x00\x00" * sample_rate * seconds
    size = 36 + len(data)
    return (
        b"RIFF"
        + struct.pack("<I", size)
        + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
        + b"data"
        + struct.pack("<I", len(data))
        + data
    )


def docx(*, macro=False, traversal=False):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document><p>Build with evidence</p></document>")
        if macro:
            archive.writestr("word/vbaProject.bin", b"macro")
        if traversal:
            archive.writestr("../escape.txt", b"escape")
    return stream.getvalue()


class LandingIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "quarantine"
        self.store = PrivateLandingBlobStore(self.root, repository_root=Path(__file__).resolve().parents[2])

    def tearDown(self):
        self.temp.cleanup()

    def accept(self, kind, media_type, data, *, job_id="job-1", chunks=None):
        return self.store.accept(
            job_id=job_id,
            tenant_id="tenant-1",
            repository_id=REPOSITORY_ID,
            exact_base_sha=BASE_SHA,
            exact_base_tree=BASE_TREE,
            site_id="therealaidarkfactory.online",
            media_kind=kind,
            media_type=media_type,
            chunks=chunks if chunks is not None else [data],
            received_at=NOW,
            expires_at=NOW + timedelta(hours=24),
        )

    def test_all_five_media_kinds_stream_to_private_tenant_bound_records(self):
        fixtures = (
            ("text", "text/plain", "Build with evidence".encode()),
            ("audio", "audio/wav", wav()),
            ("image", "image/png", png()),
            ("pdf", "application/pdf", b"%PDF-1.7\n1 0 obj<</Type /Page>>endobj\n%%EOF"),
            ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", docx()),
        )
        for index, (kind, media_type, data) in enumerate(fixtures, 1):
            with self.subTest(kind=kind):
                record = self.accept(kind, media_type, data, job_id=f"job-{index}", chunks=(data[:3], data[3:]))
                self.assertEqual(record.media_kind, kind)
                self.assertEqual(record.byte_length, len(data))
                self.assertNotIn(data[:12].decode("utf-8", "ignore"), repr(record))
                self.assertEqual(
                    self.store.read(
                        record,
                        tenant_id="tenant-1",
                        repository_id=REPOSITORY_ID,
                        job_id=f"job-{index}",
                    ),
                    data,
                )
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(path.stat().st_mode & 0o777 == 0o600 for path in self.root.rglob("*.blob")))

    def test_replay_is_idempotent_but_changed_bytes_conflict(self):
        original = self.accept("text", "text/plain", b"same", job_id="job-replay")
        self.assertEqual((original.exact_base_sha, original.exact_base_tree), (BASE_SHA, BASE_TREE))
        replay = self.accept("text", "text/plain", b"same", job_id="job-replay")
        self.assertEqual(replay, original)
        with self.assertRaisesRegex(LandingContractError, "idempotency_conflict"):
            self.accept("text", "text/plain", b"changed", job_id="job-replay")

    def test_cross_tenant_repository_and_job_access_fail_closed(self):
        record = self.accept("text", "text/plain", b"private")
        for changes in (
            {"tenant_id": "tenant-2"},
            {"repository_id": "other-repository"},
            {"job_id": "job-2"},
        ):
            arguments = {
                "tenant_id": "tenant-1",
                "repository_id": REPOSITORY_ID,
                "job_id": "job-1",
            }
            arguments.update(changes)
            with self.subTest(changes=changes), self.assertRaisesRegex(LandingContractError, "blob_access_denied"):
                self.store.read(record, **arguments)

    def test_type_shape_and_hard_limits_reject_without_retained_partial_blob(self):
        invalid = (
            ("image", "image/png", b"not-a-png", "media_signature"),
            ("image", "image/png", png(10_000, 10_000), "image_pixels"),
            ("pdf", "application/pdf", b"%PDF-1.7\n/Encrypt true\n%%EOF", "pdf_encrypted"),
            ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", docx(macro=True), "docx_active_content"),
            ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", docx(traversal=True), "docx_path"),
            ("text", "text/plain", b"x" * (1_048_576 + 1), "input_too_large"),
        )
        for index, (kind, media_type, data, code) in enumerate(invalid, 1):
            with self.subTest(code=code), self.assertRaisesRegex(LandingContractError, code):
                self.accept(kind, media_type, data, job_id=f"invalid-{index}")
        self.assertEqual(list(self.root.rglob("*.blob")), [])

    def test_purge_is_bounded_idempotent_and_makes_blob_unavailable(self):
        record = self.accept("text", "text/plain", b"purge me")
        self.assertEqual(self.store.purge(record, reason="cancelled"), "purged")
        self.assertEqual(self.store.purge(record, reason="cancelled"), "already_absent")
        with self.assertRaisesRegex(LandingContractError, "blob_unavailable"):
            self.store.read(
                record,
                tenant_id="tenant-1",
                repository_id=REPOSITORY_ID,
                job_id="job-1",
            )

    def test_quarantine_root_cannot_be_inside_repository_or_a_symlink(self):
        with self.assertRaisesRegex(LandingContractError, "quarantine_inside_repository"):
            PrivateLandingBlobStore(Path(__file__).resolve().parents[1] / "unsafe", repository_root=Path(__file__).resolve().parents[2])
        link = Path(self.temp.name) / "link"
        os.symlink(self.root, link)
        with self.assertRaisesRegex(LandingContractError, "quarantine_symlink"):
            PrivateLandingBlobStore(link, repository_root=Path(__file__).resolve().parents[2])


if __name__ == "__main__":
    unittest.main()
