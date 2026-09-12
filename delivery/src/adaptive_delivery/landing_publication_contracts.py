"""Versioned local-filesystem publication contracts, separate from landing API v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile
from urllib.parse import urlsplit


HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
MAX_ARCHIVE_BYTES = 100 * 1_048_576
MAX_MEMBER_BYTES = 25 * 1_048_576
MAX_DOCUMENT_BYTES = 2 * 1_048_576


class PublicationError(RuntimeError):
    pass


def canonical(value) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise PublicationError("publication_json") from None


def digest(kind: str, value) -> str:
    return hashlib.sha256(canonical({"contract": f"landing-publication/{kind}/v1",
                                     "value": value})).hexdigest()


def decode(raw: bytes, *, maximum: int = MAX_DOCUMENT_BYTES) -> dict:
    if not isinstance(raw, bytes) or len(raw) > maximum:
        raise PublicationError("publication_document_size")

    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise PublicationError("publication_duplicate_field")
            value[key] = item
        return value

    def constant(_value):
        raise PublicationError("publication_json")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=constant)
        if not isinstance(value, dict) or canonical(value) != raw:
            raise PublicationError("publication_json")
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise PublicationError("publication_json") from None


def require_digest(value) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise PublicationError("publication_digest")
    return value


def member_path(value: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not 1 <= len(value) <= 256:
        raise PublicationError("publication_member_path")
    path = PurePosixPath(value)
    if (
        path.is_absolute() or str(path) != value or ".." in path.parts
        or "\\" in value or len(path.parts) > 8
        or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in path.parts)
    ):
        raise PublicationError("publication_member_path")
    return path.parts


@dataclass(frozen=True)
class PublicationTargetV1:
    schema_version: int
    target_id: str
    root: str
    public_origin: str
    owner_uid: int
    device: int
    inode: int

    def __post_init__(self):
        if not isinstance(self.public_origin, str):
            raise PublicationError("publication_target")
        parsed = urlsplit(self.public_origin)
        if (
            type(self.schema_version) is not int or self.schema_version != 1
            or not isinstance(self.target_id, str) or not IDENTIFIER.fullmatch(self.target_id)
            or not isinstance(self.root, str) or not Path(self.root).is_absolute()
            or str(Path(self.root)) != self.root or ".." in Path(self.root).parts
            or parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
            or self.public_origin != f"https://{parsed.netloc}"
            or any(type(value) is not int or value < 0 for value in
                   (self.owner_uid, self.device, self.inode))
        ):
            raise PublicationError("publication_target")

    @property
    def target_digest(self) -> str:
        return digest("target", asdict(self))


@dataclass(frozen=True)
class PublicationBundle:
    """Owned byte snapshot produced by the factory's retained-artifact boundary."""

    artifact_json: bytes
    manifest_json: bytes
    archive: bytes
    allowed_members: tuple[str, ...]

    @property
    def artifact(self) -> dict:
        return decode(self.artifact_json)

    @property
    def artifact_digest(self) -> str:
        return require_digest(self.artifact["artifact_digest"])

    def validate(self) -> tuple[dict, ...]:
        artifact = self.artifact
        supplied = require_digest(artifact.get("artifact_digest"))
        facts = {key: value for key, value in artifact.items() if key != "artifact_digest"}
        expected = hashlib.sha256(canonical({
            "contract": "adaptive-factory.landing-site-artifact/v1", **facts,
        })).hexdigest()
        if (
            supplied != expected or artifact.get("schema_version") != 1
            or artifact.get("disposition") != "artifact_ready"
            or not isinstance(self.archive, bytes)
            or not 1 <= len(self.archive) <= MAX_ARCHIVE_BYTES
            or artifact.get("byte_length") != len(self.archive)
            or artifact.get("zip_sha256") != hashlib.sha256(self.archive).hexdigest()
            or artifact.get("manifest_digest") != hashlib.sha256(self.manifest_json).hexdigest()
            or not isinstance(self.allowed_members, tuple)
            or not 1 <= len(self.allowed_members) <= 1_024
            or tuple(sorted(set(self.allowed_members))) != self.allowed_members
            or len({item.casefold() for item in self.allowed_members}) != len(self.allowed_members)
            or artifact.get("member_count") != len(self.allowed_members)
        ):
            raise PublicationError("publication_artifact_binding")
        manifest = decode(self.manifest_json)
        for field in ("source_sha", "source_tree", "candidate_sha", "candidate_tree"):
            if not isinstance(artifact.get(field), str) or not HEX40.fullmatch(artifact[field]):
                raise PublicationError("publication_source_binding")
            if manifest.get(field) != artifact[field]:
                raise PublicationError("publication_source_binding")
        for field in ("attempt_digest", "evaluation_digest"):
            if manifest.get(field) != require_digest(artifact.get(field)):
                raise PublicationError("publication_provenance")
        members = manifest.get("members")
        changed = manifest.get("changed_paths")
        if (
            not isinstance(members, list) or not isinstance(changed, list)
            or not changed or sorted(set(changed)) != changed
            or not set(changed).issubset(self.allowed_members)
            or [item.get("path") for item in members if isinstance(item, dict)]
            != list(self.allowed_members)
        ):
            raise PublicationError("publication_members")
        total = 0
        try:
            with zipfile.ZipFile(io.BytesIO(self.archive)) as archive:
                if archive.namelist() != list(self.allowed_members) or archive.comment:
                    raise PublicationError("publication_archive_inventory")
                for member, info in zip(members, archive.infolist(), strict=True):
                    member_path(info.filename)
                    if (
                        set(member) != {"archive_mode", "candidate_object_id", "path",
                                        "provenance", "sha256", "size_bytes", "source_object_id"}
                        or not 0 < info.file_size <= MAX_MEMBER_BYTES
                        or info.external_attr >> 16 != 0o100644
                        or info.create_system != 3 or info.extra or info.comment
                        or info.flag_bits & 1 or info.compress_type != zipfile.ZIP_DEFLATED
                        or info.date_time != (2000, 1, 1, 0, 0, 0)
                        or member["archive_mode"] != "0644"
                        or member["size_bytes"] != info.file_size
                    ):
                        raise PublicationError("publication_member")
                    total += info.file_size
                    if total > MAX_ARCHIVE_BYTES:
                        raise PublicationError("publication_expanded_size")
                    body = archive.read(info)
                    candidate_object = hashlib.sha1(
                        f"blob {len(body)}\0".encode() + body, usedforsecurity=False
                    ).hexdigest()
                    if (
                        len(body) != info.file_size
                        or hashlib.sha256(body).hexdigest() != member["sha256"]
                        or candidate_object != member["candidate_object_id"]
                        or not isinstance(member["source_object_id"], str)
                        or not HEX40.fullmatch(member["source_object_id"])
                        or member["provenance"] != ("candidate" if info.filename in changed else "source")
                        or (info.filename not in changed and
                            member["source_object_id"] != member["candidate_object_id"])
                    ):
                        raise PublicationError("publication_member_provenance")
        except (OSError, ValueError, zipfile.BadZipFile, KeyError):
            raise PublicationError("publication_archive") from None
        return tuple(dict(member) for member in members)


@dataclass(frozen=True)
class PublicationRequestV1:
    schema_version: int
    request_id: str
    action: str
    target_digest: str
    artifact_ref: dict | None
    artifact_digest: str | None
    desired_release: str | None
    desired_manifest: str | None
    baseline_release: str | None
    baseline_manifest: str | None
    restore_from: str | None = None

    def __post_init__(self):
        if (
            type(self.schema_version) is not int or self.schema_version != 1
            or not isinstance(self.request_id, str) or not IDENTIFIER.fullmatch(self.request_id)
            or self.action not in {"stage", "activate", "restore"}
        ):
            raise PublicationError("publication_request")
        require_digest(self.target_digest)
        for value in (self.artifact_digest, self.desired_release, self.desired_manifest,
                      self.baseline_release, self.baseline_manifest, self.restore_from):
            if value is not None:
                require_digest(value)
        if ((self.desired_release is None) != (self.desired_manifest is None)
            or (self.baseline_release is None) != (self.baseline_manifest is None)):
            raise PublicationError("publication_release_identity")
        if self.action != "restore":
            if (
                self.artifact_digest != self.desired_release or self.artifact_digest is None
                or not isinstance(self.artifact_ref, dict)
                or set(self.artifact_ref) != {"tenant_id", "repository_id", "job_id"}
                or any(not isinstance(value, str) or not 1 <= len(value) <= 256
                       for value in self.artifact_ref.values())
                or self.restore_from is not None
            ):
                raise PublicationError("publication_artifact_reference")
        elif self.artifact_ref is not None or self.artifact_digest is not None or self.restore_from is None:
            raise PublicationError("publication_restore_reference")

    @property
    def request_digest(self) -> str:
        return digest("request", asdict(self))

    @property
    def resource(self) -> str:
        return f"landing-publication/v1/{self.action}/{self.request_digest}"

    def to_dict(self) -> dict:
        return {**asdict(self), "request_digest": self.request_digest, "resource": self.resource}

    @classmethod
    def from_dict(cls, value):
        value = dict(value)
        supplied = value.pop("request_digest", None)
        resource = value.pop("resource", None)
        try:
            result = cls(**value)
        except TypeError:
            raise PublicationError("publication_request") from None
        if supplied != result.request_digest or resource != result.resource:
            raise PublicationError("publication_request_digest")
        return result
