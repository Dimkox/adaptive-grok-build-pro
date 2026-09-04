from __future__ import annotations

from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import tempfile
from typing import Callable, Iterable
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
MAX_QUARANTINE_ENTRIES = 4_096
_PURGE_REASONS = frozenset({"cancelled", "normalized", "rejected", "expired"})
_PDF_PAGE = re.compile(rb"/Type\s*/Page(?!s)\b")
_QUARANTINE_BLOB = re.compile(r"^[0-9a-f]{64}\.blob$")
_QUARANTINE_TEMP = re.compile(r"^\.landing-[A-Za-z0-9_.-]+\.tmp$")
_XML_DECLARATION = re.compile(
    r"\A<\?xml[ \t\r\n]+version[ \t\r\n]*=[ \t\r\n]*(?:\"1\.0\"|'1\.0')"
    r"(?:[ \t\r\n]+encoding[ \t\r\n]*=[ \t\r\n]*(?:\"[Uu][Tt][Ff]-8\"|'[Uu][Tt][Ff]-8'))?"
    r"(?:[ \t\r\n]+standalone[ \t\r\n]*=[ \t\r\n]*(?:\"(?:yes|no)\"|'(?:yes|no)'))?"
    r"[ \t\r\n]*\?>"
)
_RELATIONSHIPS_ROOT = re.compile(
    r"\A<Relationships(?:[ \t\r\n]+xmlns[ \t\r\n]*=[ \t\r\n]*"
    r"(?:\"http://schemas\.openxmlformats\.org/package/2006/relationships\"|"
    r"'http://schemas\.openxmlformats\.org/package/2006/relationships'))?"
    r"[ \t\r\n]*(?P<empty>/?)>"
)
_XML_ATTRIBUTE_SOURCE = (
    r"[ \t\r\n]+[A-Za-z_][A-Za-z0-9_.:-]*[ \t\r\n]*=[ \t\r\n]*"
    r'(?:"[^"<>&\r\n\t]*"|\'[^\'<>&\r\n\t]*\')'
)
_RELATIONSHIP_TAG = re.compile(
    rf"<Relationship(?P<attributes>(?:{_XML_ATTRIBUTE_SOURCE})+)[ \t\r\n]*/>"
)
_XML_ATTRIBUTE = re.compile(
    r"[ \t\r\n]+(?P<name>[A-Za-z_][A-Za-z0-9_.:-]*)[ \t\r\n]*=[ \t\r\n]*"
    r'(?:(?:"(?P<double>[^"<>&\r\n\t]*)")|(?:\'(?P<single>[^\'<>&\r\n\t]*)\'))'
)
_INTERNAL_RELATIONSHIP_TARGET = re.compile(
    r"^(?:\.\./)*(?!\.{1,2}(?:/|$))[A-Za-z0-9_~.-]+"
    r"(?:/(?!\.{1,2}(?:/|$))[A-Za-z0-9_~.-]+)*$"
)
_MP3_BITRATES_MPEG1 = {
    1: (32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448),
    2: (32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384),
    3: (32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320),
}
_MP3_BITRATES_MPEG2 = {
    1: (32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256),
    2: (8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
    3: (8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
}


class PrivateLandingBlobStore:
    """Process-local, tenant-bound quarantine used by the offline landing vertical."""

    def __init__(
        self,
        root: Path,
        *,
        repository_root: Path,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
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
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._sweep_startup_orphans()

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
        self._sweep_expired(self._now())
        key = (tenant_id, repository_id, job_id)
        if key not in self._records and len(self._records) >= MAX_QUARANTINE_ENTRIES:
            raise LandingContractError("quarantine_capacity")
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
        now = self._now()
        if record.expires_at <= now:
            self.purge(record, reason="expired")
            raise LandingContractError("blob_expired")
        self._sweep_expired(now)
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

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise LandingContractError("invalid_time")
        return value.astimezone(timezone.utc)

    def _sweep_expired(self, now: datetime) -> None:
        expired = tuple(
            record for record in self._records.values() if record.expires_at <= now
        )
        for record in expired:
            self.purge(record, reason="expired")

    def _sweep_startup_orphans(self) -> None:
        entries = []
        with os.scandir(self._root) as iterator:
            for entry in iterator:
                entries.append(entry.name)
                if len(entries) > MAX_QUARANTINE_ENTRIES:
                    raise LandingContractError("quarantine_capacity")
        directory = os.open(
            self._root,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        removed = False
        try:
            for name in entries:
                if not (_QUARANTINE_BLOB.fullmatch(name) or _QUARANTINE_TEMP.fullmatch(name)):
                    continue
                try:
                    metadata = os.stat(name, dir_fd=directory, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                owned = metadata.st_uid == os.geteuid()
                safe_regular = (
                    stat.S_ISREG(metadata.st_mode)
                    and metadata.st_nlink == 1
                    and stat.S_IMODE(metadata.st_mode) == 0o600
                )
                if owned and (safe_regular or stat.S_ISLNK(metadata.st_mode)):
                    os.unlink(name, dir_fd=directory)
                    removed = True
            if removed:
                os.fsync(directory)
        finally:
            os.close(directory)

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
        if media_type == "audio/mpeg":
            PrivateLandingBlobStore._validate_mp3(payload)
            return
        if media_type == "audio/ogg":
            PrivateLandingBlobStore._validate_ogg(payload)
            return
        raise LandingContractError("media_signature")

    @staticmethod
    def _validate_mp3(payload: bytes) -> None:
        offset = 0
        if payload.startswith(b"ID3"):
            if len(payload) < 10 or any(value & 0x80 for value in payload[6:10]):
                raise LandingContractError("audio_shape")
            tag_size = sum(value << shift for value, shift in zip(payload[6:10], (21, 14, 7, 0)))
            offset = 10 + tag_size + (10 if payload[5] & 0x10 else 0)
        duration = Fraction(0)
        frames = 0
        while offset < len(payload):
            if len(payload) - offset == 128 and payload[offset : offset + 3] == b"TAG":
                offset = len(payload)
                break
            if offset + 4 > len(payload):
                raise LandingContractError("audio_shape")
            header = int.from_bytes(payload[offset : offset + 4], "big")
            version = (header >> 19) & 0x3
            layer_bits = (header >> 17) & 0x3
            bitrate_index = (header >> 12) & 0xF
            sample_index = (header >> 10) & 0x3
            if (
                header >> 21 != 0x7FF
                or version == 1
                or layer_bits == 0
                or bitrate_index in {0, 15}
                or sample_index == 3
            ):
                raise LandingContractError("audio_shape")
            layer = 4 - layer_bits
            rates = (44_100, 48_000, 32_000)
            sample_rate = rates[sample_index] // (1 if version == 3 else 2 if version == 2 else 4)
            table = _MP3_BITRATES_MPEG1 if version == 3 else _MP3_BITRATES_MPEG2
            bitrate = table[layer][bitrate_index - 1] * 1_000
            padding = (header >> 9) & 1
            if layer == 1:
                frame_size, samples = ((12 * bitrate // sample_rate) + padding) * 4, 384
            elif layer == 3 and version != 3:
                frame_size, samples = 72 * bitrate // sample_rate + padding, 576
            else:
                frame_size, samples = 144 * bitrate // sample_rate + padding, 1_152
            if frame_size < 4 or offset + frame_size > len(payload):
                raise LandingContractError("audio_shape")
            duration += Fraction(samples, sample_rate)
            if duration > MAX_AUDIO_SECONDS:
                raise LandingContractError("audio_duration")
            frames += 1
            offset += frame_size
        if frames == 0 or offset != len(payload):
            raise LandingContractError("audio_duration")

    @staticmethod
    def _validate_ogg(payload: bytes) -> None:
        offset = 0
        serial = None
        sequence = 0
        sample_rate = None
        granule = None
        saw_end = False
        while offset < len(payload):
            if offset + 27 > len(payload) or payload[offset : offset + 5] != b"OggS\x00":
                raise LandingContractError("audio_shape")
            header_type = payload[offset + 5]
            page_granule, page_serial, page_sequence = struct.unpack_from(
                "<QII", payload, offset + 6
            )
            segments = payload[offset + 26]
            table_end = offset + 27 + segments
            if table_end > len(payload):
                raise LandingContractError("audio_shape")
            body_end = table_end + sum(payload[offset + 27 : table_end])
            if body_end > len(payload) or page_sequence != sequence:
                raise LandingContractError("audio_shape")
            if serial is None:
                if not header_type & 0x02 or header_type & 0x01:
                    raise LandingContractError("audio_shape")
                serial = page_serial
                body = payload[table_end:body_end]
                if body.startswith(b"\x01vorbis") and len(body) >= 16:
                    sample_rate = struct.unpack_from("<I", body, 12)[0]
                elif body.startswith(b"OpusHead") and len(body) >= 19:
                    sample_rate = 48_000
                else:
                    raise LandingContractError("audio_shape")
            elif page_serial != serial or header_type & 0x02:
                raise LandingContractError("audio_shape")
            if page_granule != 0xFFFFFFFFFFFFFFFF:
                if granule is not None and page_granule < granule:
                    raise LandingContractError("audio_shape")
                granule = page_granule
            saw_end = bool(header_type & 0x04)
            sequence += 1
            offset = body_end
        if not saw_end or not sample_rate or granule is None:
            raise LandingContractError("audio_duration")
        if granule / sample_rate > MAX_AUDIO_SECONDS:
            raise LandingContractError("audio_duration")

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
                    if (
                        lowered.endswith((".bin", ".exe", ".dll", ".js", ".vbs"))
                        or "embeddings" in tuple(part.casefold() for part in path.parts)
                    ):
                        raise LandingContractError("docx_active_content")
                    if lowered.endswith(".rels"):
                        _validate_relationships_xml(archive.read(entry))
        except LandingContractError:
            raise
        except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
            raise LandingContractError("media_signature") from exc


def _validate_relationships_xml(payload: bytes) -> None:
    try:
        text = payload.decode("utf-8", "strict").strip()
    except UnicodeDecodeError as exc:
        raise LandingContractError("docx_relationships") from exc
    declaration = _XML_DECLARATION.match(text)
    if text.startswith("<?xml"):
        if declaration is None:
            raise LandingContractError("docx_relationships")
        text = text[declaration.end() :].strip()
    root = _RELATIONSHIPS_ROOT.match(text)
    if root is None:
        raise LandingContractError("docx_relationships")
    remaining = text[root.end() :]
    if root.group("empty"):
        if remaining.strip():
            raise LandingContractError("docx_relationships")
        return
    closing = "</Relationships>"
    if not remaining.endswith(closing):
        raise LandingContractError("docx_relationships")
    body = remaining[: -len(closing)]
    offset = 0
    for tag in _RELATIONSHIP_TAG.finditer(body):
        if body[offset : tag.start()].strip():
            raise LandingContractError("docx_relationships")
        pairs = tuple(
            (
                match.group("name").rsplit(":", 1)[-1].casefold(),
                match.group("double")
                if match.group("double") is not None
                else match.group("single"),
            )
            for match in _XML_ATTRIBUTE.finditer(tag.group("attributes"))
        )
        attributes = dict(pairs)
        if len(attributes) != len(pairs):
            raise LandingContractError("docx_relationships")
        mode = attributes.get("targetmode", "").strip().casefold()
        if mode == "external":
            raise LandingContractError("docx_external_relationship")
        if mode not in {"", "internal"} or set(attributes) not in (
            {"id", "type", "target"},
            {"id", "type", "target", "targetmode"},
        ):
            raise LandingContractError("docx_relationships")
        if not _INTERNAL_RELATIONSHIP_TARGET.fullmatch(attributes["target"]):
            raise LandingContractError("docx_external_relationship")
        offset = tag.end()
    if body[offset:].strip():
        raise LandingContractError("docx_relationships")
