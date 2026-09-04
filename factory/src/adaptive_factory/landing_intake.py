from __future__ import annotations

from datetime import datetime
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import struct
import tempfile
from typing import Iterable
import zipfile

from .landing_contracts import (
    MAX_INPUT_BYTES,
    MEDIA_TYPES,
    LandingContractError,
    LandingInputV1,
    landing_digest,
)


MAX_TEXT_SCALARS = 200_000
MAX_AUDIO_SECONDS = 900
MAX_IMAGE_PIXELS = 40_000_000
MAX_PDF_PAGES = 100
MAX_DOCX_EXPANDED_BYTES = 50 * 1_048_576
MAX_DOCX_ENTRIES = 2_000
_PURGE_REASONS = frozenset({"cancelled", "normalized", "rejected", "expired"})
_PDF_PAGE = re.compile(rb"/Type\s*/Page(?!s)\b")


class PrivateLandingBlobStore:
    """Process-local, tenant-bound quarantine used by the offline landing vertical."""

    def __init__(self, root: Path, *, repository_root: Path) -> None:
        root = Path(root)
        repository = Path(repository_root).resolve(strict=True)
        if root.is_symlink():
            raise LandingContractError("quarantine_symlink")
        candidate = root.resolve(strict=False)
        try:
            candidate.relative_to(repository)
        except ValueError:
            pass
        else:
            raise LandingContractError("quarantine_inside_repository")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if root.is_symlink() or not root.is_dir():
            raise LandingContractError("quarantine_symlink")
        os.chmod(root, 0o700)
        self._root = root.resolve(strict=True)
        self._records: dict[tuple[str, str, str], LandingInputV1] = {}

    def accept(
        self,
        *,
        job_id: str,
        tenant_id: str,
        repository_id: str,
        exact_base_sha: str,
        exact_base_tree: str,
        site_id: str,
        media_kind: str,
        media_type: str,
        chunks: Iterable[bytes],
        received_at: datetime,
        expires_at: datetime,
    ) -> LandingInputV1:
        if media_kind not in MEDIA_TYPES or media_type not in MEDIA_TYPES[media_kind]:
            raise LandingContractError("media_type")
        maximum = MAX_INPUT_BYTES[media_kind]
        descriptor, temporary_name = tempfile.mkstemp(prefix=".landing-", suffix=".tmp", dir=self._root)
        temporary = Path(temporary_name)
        digest = hashlib.sha256()
        length = 0
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                descriptor = -1
                for chunk in chunks:
                    if not isinstance(chunk, (bytes, bytearray, memoryview)):
                        raise LandingContractError("invalid_input_chunk")
                    value = bytes(chunk)
                    length += len(value)
                    if length > maximum:
                        raise LandingContractError("input_too_large", media_kind)
                    digest.update(value)
                    stream.write(value)
                stream.flush()
                os.fsync(stream.fileno())
            if length == 0:
                raise LandingContractError("input_empty")
            payload = temporary.read_bytes()
            self._validate_shape(media_kind, media_type, payload)
            content_sha256 = digest.hexdigest()
            reference = landing_digest(
                "quarantine-ref",
                {
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                    "repository_id": repository_id,
                    "exact_base_sha": exact_base_sha,
                    "exact_base_tree": exact_base_tree,
                    "media_kind": media_kind,
                    "media_type": media_type,
                    "byte_length": length,
                    "content_sha256": content_sha256,
                },
            )
            facts = {
                "schema_version": 1,
                "job_id": job_id,
                "tenant_id": tenant_id,
                "repository_id": repository_id,
                "exact_base_sha": exact_base_sha,
                "exact_base_tree": exact_base_tree,
                "site_id": site_id,
                "media_kind": media_kind,
                "media_type": media_type,
                "byte_length": length,
                "content_sha256": content_sha256,
                "quarantine_ref_digest": reference,
                "received_at": self._format_time(received_at),
                "expires_at": self._format_time(expires_at),
            }
            record = LandingInputV1.from_facts(facts)
            key = (tenant_id, repository_id, job_id)
            existing = self._records.get(key)
            if existing is not None:
                if existing != record:
                    raise LandingContractError("idempotency_conflict")
                return existing
            target = self._root / f"{reference}.blob"
            if target.exists():
                if target.is_symlink() or target.read_bytes() != payload:
                    raise LandingContractError("quarantine_collision")
                temporary.unlink()
            else:
                os.replace(temporary, target)
                os.chmod(target, 0o600)
                self._fsync_directory()
            self._records[key] = record
            return record
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if temporary.exists():
                temporary.unlink()

    def read(
        self,
        record: LandingInputV1,
        *,
        tenant_id: str,
        repository_id: str,
        job_id: str,
    ) -> bytes:
        key = (tenant_id, repository_id, job_id)
        if key != (record.tenant_id, record.repository_id, record.job_id):
            raise LandingContractError("blob_access_denied")
        existing = self._records.get(key)
        if existing != record:
            raise LandingContractError("blob_unavailable")
        path = self._root / f"{record.quarantine_ref_digest}.blob"
        if path.is_symlink() or not path.is_file():
            raise LandingContractError("blob_unavailable")
        payload = path.read_bytes()
        if len(payload) != record.byte_length or hashlib.sha256(payload).hexdigest() != record.content_sha256:
            raise LandingContractError("blob_digest_mismatch")
        return payload

    def purge(self, record: LandingInputV1, *, reason: str) -> str:
        if reason not in _PURGE_REASONS:
            raise LandingContractError("purge_reason")
        key = (record.tenant_id, record.repository_id, record.job_id)
        existing = self._records.get(key)
        if existing is not None and existing != record:
            raise LandingContractError("blob_access_denied")
        path = self._root / f"{record.quarantine_ref_digest}.blob"
        if path.is_symlink():
            raise LandingContractError("blob_access_denied")
        if path.exists():
            path.unlink()
            self._records.pop(key, None)
            self._fsync_directory()
            return "purged"
        self._records.pop(key, None)
        return "already_absent"

    @staticmethod
    def _format_time(value: datetime) -> str:
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise LandingContractError("invalid_time")
        return value.isoformat().replace("+00:00", "Z")

    def _fsync_directory(self) -> None:
        descriptor = os.open(self._root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @classmethod
    def _validate_shape(cls, media_kind: str, media_type: str, payload: bytes) -> None:
        if media_kind == "text":
            cls._validate_text(payload)
        elif media_kind == "audio":
            cls._validate_audio(media_type, payload)
        elif media_kind == "image":
            cls._validate_image(media_type, payload)
        elif media_kind == "pdf":
            cls._validate_pdf(payload)
        elif media_kind == "docx":
            cls._validate_docx(payload)
        else:
            raise LandingContractError("media_kind")

    @staticmethod
    def _validate_text(payload: bytes) -> None:
        try:
            text = payload.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise LandingContractError("text_encoding") from exc
        if len(text) > MAX_TEXT_SCALARS:
            raise LandingContractError("text_scalars")
        if any(ord(char) == 0 or (ord(char) < 32 and char not in "\n\r\t") for char in text):
            raise LandingContractError("text_control")

    @staticmethod
    def _validate_audio(media_type: str, payload: bytes) -> None:
        if media_type == "audio/wav":
            if len(payload) < 44 or payload[:4] != b"RIFF" or payload[8:12] != b"WAVE":
                raise LandingContractError("media_signature")
            offset = 12
            byte_rate = None
            data_size = None
            while offset + 8 <= len(payload):
                kind = payload[offset : offset + 4]
                size = struct.unpack_from("<I", payload, offset + 4)[0]
                start = offset + 8
                end = start + size
                if end > len(payload):
                    raise LandingContractError("audio_shape")
                if kind == b"fmt " and size >= 16:
                    byte_rate = struct.unpack_from("<I", payload, start + 8)[0]
                elif kind == b"data":
                    data_size = size
                offset = end + (size % 2)
            if not byte_rate or data_size is None or data_size / byte_rate > MAX_AUDIO_SECONDS:
                raise LandingContractError("audio_duration")
            return
        if media_type == "audio/mpeg" and (payload.startswith(b"ID3") or payload[:1] == b"\xff"):
            return
        if media_type == "audio/ogg" and payload.startswith(b"OggS"):
            return
        raise LandingContractError("media_signature")

    @classmethod
    def _validate_image(cls, media_type: str, payload: bytes) -> None:
        if media_type == "image/png":
            if len(payload) < 24 or payload[:8] != b"\x89PNG\r\n\x1a\n":
                raise LandingContractError("media_signature")
            width, height = struct.unpack_from(">II", payload, 16)
        elif media_type == "image/jpeg":
            width, height = cls._jpeg_dimensions(payload)
        elif media_type == "image/webp":
            width, height = cls._webp_dimensions(payload)
        else:
            raise LandingContractError("media_signature")
        if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
            raise LandingContractError("image_pixels")

    @staticmethod
    def _jpeg_dimensions(payload: bytes) -> tuple[int, int]:
        if len(payload) < 4 or not payload.startswith(b"\xff\xd8"):
            raise LandingContractError("media_signature")
        offset = 2
        while offset + 9 <= len(payload):
            if payload[offset] != 0xFF:
                offset += 1
                continue
            marker = payload[offset + 1]
            offset += 2
            if marker in {0xD8, 0xD9}:
                continue
            if offset + 2 > len(payload):
                break
            length = struct.unpack_from(">H", payload, offset)[0]
            if length < 2 or offset + length > len(payload):
                break
            if marker in {0xC0, 0xC1, 0xC2} and length >= 7:
                height, width = struct.unpack_from(">HH", payload, offset + 3)
                return width, height
            offset += length
        raise LandingContractError("image_shape")

    @staticmethod
    def _webp_dimensions(payload: bytes) -> tuple[int, int]:
        if len(payload) < 30 or payload[:4] != b"RIFF" or payload[8:12] != b"WEBP":
            raise LandingContractError("media_signature")
        if payload[12:16] == b"VP8X":
            width = 1 + int.from_bytes(payload[24:27], "little")
            height = 1 + int.from_bytes(payload[27:30], "little")
            return width, height
        raise LandingContractError("image_shape")

    @staticmethod
    def _validate_pdf(payload: bytes) -> None:
        if not payload.startswith(b"%PDF-") or b"%%EOF" not in payload[-1_024:]:
            raise LandingContractError("media_signature")
        if re.search(rb"/Encrypt\b", payload, re.IGNORECASE):
            raise LandingContractError("pdf_encrypted")
        pages = len(_PDF_PAGE.findall(payload))
        if not 1 <= pages <= MAX_PDF_PAGES:
            raise LandingContractError("pdf_pages")

    @staticmethod
    def _validate_docx(payload: bytes) -> None:
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                entries = archive.infolist()
                if not 1 <= len(entries) <= MAX_DOCX_ENTRIES:
                    raise LandingContractError("docx_entries")
                names = {entry.filename for entry in entries}
                if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                    raise LandingContractError("docx_shape")
                expanded = 0
                for entry in entries:
                    path = PurePosixPath(entry.filename)
                    if path.is_absolute() or ".." in path.parts or str(path) != entry.filename:
                        raise LandingContractError("docx_path")
                    if entry.flag_bits & 0x1:
                        raise LandingContractError("docx_encrypted")
                    mode = (entry.external_attr >> 16) & 0o170000
                    if mode == 0o120000:
                        raise LandingContractError("docx_path")
                    expanded += entry.file_size
                    if expanded > MAX_DOCX_EXPANDED_BYTES:
                        raise LandingContractError("docx_expanded")
                    lowered = entry.filename.lower()
                    if lowered.endswith(("vbaproject.bin", ".exe", ".dll", ".js", ".vbs")):
                        raise LandingContractError("docx_active_content")
                    if lowered.endswith(".rels") and b'TargetMode="External"' in archive.read(entry):
                        raise LandingContractError("docx_external_relationship")
        except LandingContractError:
            raise
        except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
            raise LandingContractError("media_signature") from exc
