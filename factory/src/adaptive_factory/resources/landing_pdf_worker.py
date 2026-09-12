"""One bounded PDF-to-text child process; no credentials, network or model operation."""

import io
import json
import resource
import sys


def emit(**values):
    sys.stdout.buffer.write(json.dumps({"schema_version": 1, **values}, ensure_ascii=False,
                                       separators=(",", ":")).encode("utf-8"))


def main():
    # Set limits before importing the parser or reading untrusted PDF bytes.
    resource.setrlimit(resource.RLIMIT_CPU, (5, 6))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1_048_576, 512 * 1_048_576))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
    try:
        from importlib.metadata import version
        if version("pypdf") != "6.18.1":
            emit(error="pdf_parser_unavailable")
            return
        from pypdf import PdfReader
    except (ImportError, ModuleNotFoundError):
        emit(error="pdf_parser_unavailable")
        return
    payload = sys.stdin.buffer.read(20 * 1_048_576 + 1)
    if not 1 <= len(payload) <= 20 * 1_048_576:
        emit(error="pdf_invalid")
        return
    try:
        reader = PdfReader(io.BytesIO(payload), strict=True)
        if reader.is_encrypted:
            emit(error="pdf_encrypted")
            return
        if not 1 <= len(reader.pages) <= 100:
            emit(error="pdf_page_limit")
            return
        pages = []
        length = 0
        for page in reader.pages:
            text = page.extract_text() or ""
            length += len(text.encode("utf-8")) + 1
            if length > 65_536:
                emit(error="pdf_text_limit")
                return
            pages.append(text)
        text = "\n".join(pages)
        if not text.strip():
            emit(error="pdf_empty_or_scanned")
            return
        emit(text=text)
    except Exception:
        emit(error="pdf_invalid")


if __name__ == "__main__":
    main()
