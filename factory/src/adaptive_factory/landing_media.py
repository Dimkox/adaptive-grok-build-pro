"""Bounded media preparation; PDF parsing runs in a separate constrained process."""

from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

from .landing_contracts import strict_json_object
from .landing_normalizer import normalize_landing_text


PDF_WORKER = Path(__file__).resolve().parent / "resources/landing_pdf_worker.py"
PDF_DECODER_DIGEST = hashlib.sha256(PDF_WORKER.read_bytes()).hexdigest()
PDF_PYPDF_VERSION = "6.18.1"
MAX_AUDIO_BASE64_BYTES = 10_000_000
MAX_IMAGE_BYTES = 20 * 1_048_576


class LandingMediaError(RuntimeError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def media_preflight(source, media_kinds):
    if source.media_kind not in media_kinds:
        raise LandingMediaError("http_media_unsupported")
    if source.media_kind == "image" and (
        source.media_type not in {"image/png", "image/jpeg"} or source.byte_length > MAX_IMAGE_BYTES
    ):
        raise LandingMediaError("http_image_format_or_size")
    if source.media_kind == "audio" and (
        source.media_type not in {"audio/wav", "audio/mpeg"}
        or 4 * ((source.byte_length + 2) // 3) >= MAX_AUDIO_BASE64_BYTES
    ):
        raise LandingMediaError("http_audio_format_or_size")


def prepare_landing_media(source, blob):
    if source.media_kind in {"text", "docx"}:
        return normalize_landing_text(source.media_kind, blob)
    if source.media_kind == "pdf":
        return extract_pdf_text(blob)
    if source.media_kind in {"image", "audio"}:
        return {"media_type": source.media_type,
                "data_base64": base64.b64encode(blob).decode("ascii")}
    raise LandingMediaError("http_media_unsupported")


def extract_pdf_text(payload: bytes) -> str:
    if not isinstance(payload, bytes) or not 1 <= len(payload) <= 20 * 1_048_576:
        raise LandingMediaError("pdf_input_limit")
    if hashlib.sha256(PDF_WORKER.read_bytes()).hexdigest() != PDF_DECODER_DIGEST:
        raise LandingMediaError("pdf_decoder_drift")
    process = subprocess.Popen(
        (str(Path(sys.executable).absolute()), "-B", "-I", str(PDF_WORKER)),
        cwd="/", env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True, close_fds=True,
    )
    deadline = time.monotonic() + 20
    output = bytearray()
    stderr_bytes = 0
    offset = 0
    selector = selectors.DefaultSelector()
    try:
        for stream, role, event in ((process.stdin, "input", selectors.EVENT_WRITE),
                                    (process.stdout, "output", selectors.EVENT_READ),
                                    (process.stderr, "error", selectors.EVENT_READ)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, event, role)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise LandingMediaError("pdf_decoder_timeout")
            for key, _events in selector.select(min(remaining, 0.25)):
                stream, role = key.fileobj, key.data
                if role == "input":
                    try:
                        offset += os.write(stream.fileno(), payload[offset:offset + 65_536])
                    except BrokenPipeError:
                        offset = len(payload)
                    if offset == len(payload):
                        selector.unregister(stream)
                        stream.close()
                    continue
                chunk = os.read(stream.fileno(), 65_536)
                if not chunk:
                    selector.unregister(stream)
                    stream.close()
                elif role == "output":
                    output.extend(chunk)
                    if len(output) > 131_072:
                        raise LandingMediaError("pdf_decoder_output_limit")
                else:
                    stderr_bytes += len(chunk)
                    if stderr_bytes > 16_384:
                        raise LandingMediaError("pdf_decoder_error_limit")
        try:
            code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            raise LandingMediaError("pdf_decoder_timeout") from None
        if code != 0:
            raise LandingMediaError("pdf_decoder_unavailable")
        document = strict_json_object(bytes(output), maximum=131_072)
        if set(document) == {"schema_version", "error"} and document["schema_version"] == 1:
            reason = document["error"]
            if reason in {"pdf_encrypted", "pdf_page_limit", "pdf_empty_or_scanned", "pdf_text_limit",
                          "pdf_parser_unavailable", "pdf_invalid"}:
                raise LandingMediaError(reason)
        if set(document) != {"schema_version", "text"} or document["schema_version"] != 1:
            raise LandingMediaError("pdf_decoder_protocol")
        text = document["text"]
        if not isinstance(text, str):
            raise LandingMediaError("pdf_decoder_protocol")
        return normalize_landing_text("text", text.encode("utf-8"))
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
        process.wait()
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None and not stream.closed:
                stream.close()
