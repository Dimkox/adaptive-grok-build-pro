from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import os
from pathlib import Path
import re
import stat
from typing import Mapping
import zipfile

from .contracts import canonical_json
from .landing_artifact import (
    ARCHIVE_MODE,
    ARCHIVE_TIMESTAMP,
    CONTROL_REPOSITORY_ID,
    DEPLOY_MEMBERS,
    MAX_ARCHIVE_BYTES,
    LandingArtifactError,
    LandingArtifactResult,
)
from .landing_contracts import (
    LandingAttemptV1,
    LandingContractError,
    LandingEvaluationV1,
    LandingInputV1,
    LandingProviderEvidenceV1,
    SiteArtifactV1,
    strict_json_object,
)
from .landing_renderer import LANDING_WRITE_PATHS, TARGET_REPOSITORY_ID


_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX_BYTES = re.compile(r"^(?:[0-9a-f]{2})+$")
_FIELDS = frozenset(
    {
        "schema_version",
        "artifact",
        "output_root",
        "zip_name",
        "sidecar_name",
        "sidecar_hex",
        "manifest_hex",
        "member_names",
        "provider_evidence",
        "attempt",
        "evaluation",
    }
)


@dataclass(frozen=True)
class RetainedLandingArtifact:
    artifact: SiteArtifactV1
    output_root: Path
    zip_name: str
    sidecar_name: str
    sidecar_bytes: bytes
    manifest_bytes: bytes
    member_names: tuple[str, ...]
    provider_evidence: LandingProviderEvidenceV1
    attempt: LandingAttemptV1
    evaluation: LandingEvaluationV1

    @property
    def zip_path(self) -> Path:
        return self.output_root / self.zip_name

    @property
    def sidecar_path(self) -> Path:
        return self.output_root / self.sidecar_name

    @classmethod
    def capture(
        cls,
        sealed: LandingArtifactResult,
        provider_evidence: LandingProviderEvidenceV1,
        attempt: LandingAttemptV1,
        evaluation: LandingEvaluationV1,
        source: LandingInputV1,
    ) -> "RetainedLandingArtifact":
        if not isinstance(sealed, LandingArtifactResult):
            raise LandingArtifactError("artifact_integrity")
        result = cls(
            sealed.artifact,
            sealed.zip_path.parent,
            sealed.zip_path.name,
            sealed.sidecar_path.name,
            sealed.sidecar_bytes,
            sealed.manifest_bytes,
            sealed.member_names,
            provider_evidence,
            attempt,
            evaluation,
        )
        result.validate(source)
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "RetainedLandingArtifact":
        if not isinstance(data, Mapping) or set(data) != _FIELDS:
            raise LandingArtifactError("artifact_integrity")
        try:
            if data["schema_version"] != 1:
                raise LandingArtifactError("artifact_integrity")
            root_text = data["output_root"]
            zip_name = data["zip_name"]
            sidecar_name = data["sidecar_name"]
            members = data["member_names"]
            if (
                not isinstance(root_text, str)
                or not isinstance(zip_name, str)
                or not isinstance(sidecar_name, str)
                or not isinstance(members, list)
                or not all(isinstance(item, str) for item in members)
            ):
                raise LandingArtifactError("artifact_integrity")
            return cls(
                SiteArtifactV1.from_dict(data["artifact"]),
                Path(root_text),
                zip_name,
                sidecar_name,
                _hex_bytes(data["sidecar_hex"], 1_024),
                _hex_bytes(data["manifest_hex"], 1_048_576),
                tuple(members),
                LandingProviderEvidenceV1.from_dict(data["provider_evidence"]),
                LandingAttemptV1.from_dict(data["attempt"]),
                LandingEvaluationV1.from_dict(data["evaluation"]),
            )
        except (KeyError, TypeError, ValueError, LandingContractError) as exc:
            raise LandingArtifactError("artifact_integrity") from exc

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "artifact": self.artifact.to_dict(),
            "output_root": str(self.output_root),
            "zip_name": self.zip_name,
            "sidecar_name": self.sidecar_name,
            "sidecar_hex": self.sidecar_bytes.hex(),
            "manifest_hex": self.manifest_bytes.hex(),
            "member_names": list(self.member_names),
            "provider_evidence": self.provider_evidence.to_dict(),
            "attempt": self.attempt.to_dict(),
            "evaluation": self.evaluation.to_dict(),
        }

    def validate(self, source: LandingInputV1) -> None:
        try:
            self._validate(source)
        except LandingArtifactError:
            raise
        except (
            KeyError,
            LandingContractError,
            OSError,
            TypeError,
            ValueError,
            zipfile.BadZipFile,
        ) as exc:
            raise LandingArtifactError("artifact_integrity") from exc

    def _validate(self, source: LandingInputV1) -> None:
        artifact = self.artifact
        evidence = self.provider_evidence
        attempt = self.attempt
        evaluation = self.evaluation
        if (
            not isinstance(source, LandingInputV1)
            or not isinstance(artifact, SiteArtifactV1)
            or not isinstance(evidence, LandingProviderEvidenceV1)
            or not isinstance(attempt, LandingAttemptV1)
            or not isinstance(evaluation, LandingEvaluationV1)
            or evidence.disposition != "fixture_ready"
            or evidence.input_digest != source.input_digest
            or artifact.source_sha != source.exact_base_sha
            or artifact.source_tree != source.exact_base_tree
            or artifact.input_digest != source.input_digest
            or artifact.profile_digest != evidence.profile_digest
            or attempt.input_digest != source.input_digest
            or attempt.spec_digest != artifact.spec_digest
            or attempt.profile_digest != evidence.profile_digest
            or attempt.exact_base_sha != artifact.source_sha
            or attempt.exact_head_sha != artifact.candidate_sha
            or attempt.attempt_digest != artifact.attempt_digest
            or evaluation.attempt_digest != attempt.attempt_digest
            or evaluation.candidate_head_sha != artifact.candidate_sha
            or evaluation.evaluation_digest != artifact.evaluation_digest
            or evaluation.decision != "pass"
            or evaluation.reason_codes
            or evaluation.finding_digests
        ):
            raise LandingArtifactError("artifact_integrity")
        root = self.output_root
        if (
            not root.is_absolute()
            or Path(os.path.abspath(root)) != root
            or root.resolve(strict=True) != root
        ):
            raise LandingArtifactError("artifact_integrity")
        root_metadata = root.lstat()
        if (
            not stat.S_ISDIR(root_metadata.st_mode)
            or stat.S_ISLNK(root_metadata.st_mode)
            or root_metadata.st_uid != os.geteuid()
            or stat.S_IMODE(root_metadata.st_mode) & 0o077
        ):
            raise LandingArtifactError("artifact_integrity")
        expected_zip = f"therealaidarkfactory.online-{artifact.zip_sha256}.zip"
        if (
            self.zip_name != expected_zip
            or self.sidecar_name != f"{expected_zip}.sha256"
            or Path(self.zip_name).name != self.zip_name
            or Path(self.sidecar_name).name != self.sidecar_name
            or self.member_names != DEPLOY_MEMBERS
            or artifact.member_count != len(self.member_names)
        ):
            raise LandingArtifactError("artifact_integrity")
        expected_sidecar = f"{artifact.zip_sha256.upper()}  {self.zip_name}\n".encode(
            "ascii"
        )
        if (
            self.sidecar_bytes != expected_sidecar
            or hashlib.sha256(self.sidecar_bytes).hexdigest()
            != artifact.sidecar_sha256
        ):
            raise LandingArtifactError("artifact_integrity")
        zip_bytes = _read_private_file(self.zip_path, MAX_ARCHIVE_BYTES)
        sidecar_bytes = _read_private_file(self.sidecar_path, 1_024)
        if (
            len(zip_bytes) != artifact.byte_length
            or hashlib.sha256(zip_bytes).hexdigest() != artifact.zip_sha256
            or sidecar_bytes != expected_sidecar
        ):
            raise LandingArtifactError("artifact_integrity")
        if (
            not self.manifest_bytes
            or hashlib.sha256(self.manifest_bytes).hexdigest()
            != artifact.manifest_digest
        ):
            raise LandingArtifactError("artifact_integrity")
        manifest = strict_json_object(self.manifest_bytes, maximum=1_048_576)
        if canonical_json(manifest) != self.manifest_bytes:
            raise LandingArtifactError("artifact_integrity")
        self._validate_manifest(manifest, zip_bytes)

    def _validate_manifest(self, manifest: Mapping[str, object], zip_bytes: bytes) -> None:
        expected_fields = {
            "schema_version",
            "artifact_kind",
            "control_repository_id",
            "target_repository_id",
            "source_sha",
            "source_tree",
            "candidate_sha",
            "candidate_tree",
            "changed_paths",
            "attempt_digest",
            "evaluation_digest",
            "archive",
            "members",
        }
        artifact = self.artifact
        if (
            set(manifest) != expected_fields
            or manifest["schema_version"] != 1
            or manifest["artifact_kind"] != "static-deploy-root"
            or manifest["control_repository_id"] != CONTROL_REPOSITORY_ID
            or manifest["target_repository_id"] != TARGET_REPOSITORY_ID
            or manifest["source_sha"] != artifact.source_sha
            or manifest["source_tree"] != artifact.source_tree
            or manifest["candidate_sha"] != artifact.candidate_sha
            or manifest["candidate_tree"] != artifact.candidate_tree
            or manifest["changed_paths"] != list(sorted(LANDING_WRITE_PATHS))
            or manifest["attempt_digest"] != artifact.attempt_digest
            or manifest["evaluation_digest"] != artifact.evaluation_digest
        ):
            raise LandingArtifactError("artifact_integrity")
        archive_facts = manifest["archive"]
        members = manifest["members"]
        if (
            not isinstance(archive_facts, Mapping)
            or archive_facts
            != {
                "compression": "deflate-9",
                "dos_timestamp": "2000-01-01T00:00:00Z",
                "member_count": len(DEPLOY_MEMBERS),
                "member_mode": "0644",
                "members_sorted": True,
            }
            or not isinstance(members, list)
            or [item.get("path") if isinstance(item, Mapping) else None for item in members]
            != list(self.member_names)
        ):
            raise LandingArtifactError("artifact_integrity")
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            if archive.namelist() != list(self.member_names) or archive.comment:
                raise LandingArtifactError("artifact_integrity")
            for item, info in zip(members, archive.infolist(), strict=True):
                if not isinstance(item, Mapping) or set(item) != {
                    "archive_mode",
                    "candidate_object_id",
                    "path",
                    "provenance",
                    "sha256",
                    "size_bytes",
                    "source_object_id",
                }:
                    raise LandingArtifactError("artifact_integrity")
                body = archive.read(info)
                path = info.filename
                source_owned = path not in LANDING_WRITE_PATHS
                if (
                    info.date_time != ARCHIVE_TIMESTAMP
                    or info.create_system != 3
                    or info.external_attr >> 16 != ARCHIVE_MODE
                    or info.extra
                    or info.comment
                    or info.compress_type != zipfile.ZIP_DEFLATED
                    or item["archive_mode"] != "0644"
                    or item["size_bytes"] != len(body)
                    or item["sha256"] != hashlib.sha256(body).hexdigest()
                    or not isinstance(item["source_object_id"], str)
                    or not _HEX40.fullmatch(item["source_object_id"])
                    or not isinstance(item["candidate_object_id"], str)
                    or not _HEX40.fullmatch(item["candidate_object_id"])
                    or item["provenance"] != ("source" if source_owned else "candidate")
                    or (
                        source_owned
                        and item["source_object_id"] != item["candidate_object_id"]
                    )
                ):
                    raise LandingArtifactError("artifact_integrity")


def _hex_bytes(value: object, maximum: int) -> bytes:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > maximum * 2
        or not _HEX_BYTES.fullmatch(value)
    ):
        raise LandingArtifactError("artifact_integrity")
    return bytes.fromhex(value)


def _read_private_file(path: Path, maximum: int) -> bytes:
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or not 0 < metadata.st_size <= maximum
    ):
        raise LandingArtifactError("artifact_integrity")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        body = bytearray()
        while chunk := os.read(descriptor, min(1_048_576, maximum + 1)):
            body.extend(chunk)
            if len(body) > maximum:
                raise LandingArtifactError("artifact_integrity")
        return bytes(body)
    finally:
        os.close(descriptor)
