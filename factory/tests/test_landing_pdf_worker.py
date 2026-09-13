"""Execute the sealed bounded PDF worker as the real child process (issue #63 residual).

The sibling media tests spawn a `python -c` stub, so the shipped worker body itself
(resources/landing_pdf_worker.py) never ran here. These tests drive `extract_pdf_text`
with no Popen patching: the production spawn (`python -B -I worker.py`, empty env,
rlimits, private selector loop) executes and its structured protocol is asserted.
"""

from __future__ import annotations
import io
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

from adaptive_factory import landing_media
from adaptive_factory.landing_media import LandingMediaError, extract_pdf_text

CURRENT_EPOCH_SHA = "fde60e040167c10975b00d11f578c4da6763069a"

# Mirror the worker's isolated environment exactly (landing_media.py spawns
# `python -B -I worker.py` with only PATH/LANG/LC_ALL); a parent-side probe
# would over-count a `pip install --user pypdf` and turn the parser-present
# tests red when the child still cannot import it.
_CHILD_ENV = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}


def _pypdf_pinned() -> bool:
    probe = subprocess.run(
        (
            str(Path(sys.executable).absolute()), "-B", "-I", "-c",
            "import importlib.metadata as m; import pypdf; "
            "raise SystemExit(0 if m.version('pypdf')=='6.18.1' else 1)",
        ),
        cwd="/", env=_CHILD_ENV, capture_output=True, timeout=30,
    )
    return probe.returncode == 0


def _single_page_pdf(text: str) -> bytes:
    body = f"BT /F1 12 Tf 20 100 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length " + str(len(body)).encode() + b">>\nstream\n" + body + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, payload in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + payload + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<</Size {len(objects) + 1}/Root 1 0 R>>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(out)


def _blank_pdf() -> bytes:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class PdfWorkerInputGuards(unittest.TestCase):
    def test_empty_payload_is_rejected_before_any_spawn(self):
        with self.assertRaises(LandingMediaError) as ctx:
            extract_pdf_text(b"")
        self.assertEqual(ctx.exception.code, "pdf_input_limit")

    def test_decoder_drift_is_rejected_before_any_spawn(self):
        with mock.patch.object(landing_media, "PDF_DECODER_DIGEST", "0" * 64):
            with self.assertRaises(LandingMediaError) as ctx:
                extract_pdf_text(b"%PDF-1.4\n%synthetic\n%%EOF\n")
        self.assertEqual(ctx.exception.code, "pdf_decoder_drift")


@unittest.skipIf(_pypdf_pinned(), "pinned pypdf 6.18.1 present; unavailable branch cannot run")
class PdfWorkerWithoutParser(unittest.TestCase):
    def test_worker_executes_and_reports_parser_unavailable(self):
        with self.assertRaises(LandingMediaError) as ctx:
            extract_pdf_text(b"%PDF-1.4\nnot really a pdf\n%%EOF\n")
        self.assertEqual(ctx.exception.code, "pdf_parser_unavailable")


@unittest.skipUnless(_pypdf_pinned(), "requires pypdf 6.18.1 installed for the child interpreter")
class PdfWorkerWithPinnedParser(unittest.TestCase):
    def test_textual_pdf_returns_normalized_text(self):
        self.assertEqual(extract_pdf_text(_single_page_pdf("PDFWORKER OK")).strip(), "PDFWORKER OK")

    def test_blank_pdf_reports_empty_or_scanned(self):
        with self.assertRaises(LandingMediaError) as ctx:
            extract_pdf_text(_blank_pdf())
        self.assertEqual(ctx.exception.code, "pdf_empty_or_scanned")

    def test_corrupt_pdf_reports_invalid(self):
        with self.assertRaises(LandingMediaError) as ctx:
            extract_pdf_text(b"%PDF-1.4\nbroken xref\nstartxref\n999999\n%%EOF\n")
        self.assertEqual(ctx.exception.code, "pdf_invalid")

    def test_oversized_page_count_reports_page_limit(self):
        payload = _single_page_pdf("PDFWORKER OK")
        marker = b"/Count 1>>"
        replacement = b"/Count 101>>"
        self.assertEqual(payload.count(marker), 1)
        with self.assertRaises(LandingMediaError) as ctx:
            extract_pdf_text(payload.replace(marker, replacement, 1))
        self.assertEqual(ctx.exception.code, "pdf_page_limit")


if __name__ == "__main__":
    unittest.main()
