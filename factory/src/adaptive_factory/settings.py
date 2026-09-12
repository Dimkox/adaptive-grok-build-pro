from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat


class SettingsError(RuntimeError):
    pass


def read_private_file(path: Path, maximum: int) -> bytes:
    if not path.is_absolute() or ".." in path.parts:
        raise SettingsError("private file path must be absolute and normalized")
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if not isinstance(nofollow, int) or not isinstance(directory, int):
        raise SettingsError("required no-follow descriptor capabilities are unavailable")
    close_on_exec = getattr(os, "O_CLOEXEC", 0)
    effective_uid = os.geteuid()
    descriptors: list[int] = []
    try:
        try:
            parent_descriptor = os.open("/", os.O_RDONLY | directory | close_on_exec)
            descriptors.append(parent_descriptor)
            parent_parts = path.parent.parts[1:]
            for index, component in enumerate(parent_parts):
                child = os.open(component, os.O_RDONLY | directory | nofollow | close_on_exec, dir_fd=parent_descriptor)
                descriptors.append(child)
                parent_descriptor = child
                metadata = os.fstat(child)
                mode = stat.S_IMODE(metadata.st_mode)
                trusted_owner = metadata.st_uid in {0, effective_uid}
                root_sticky = metadata.st_uid == 0 and bool(metadata.st_mode & stat.S_ISVTX)
                if not stat.S_ISDIR(metadata.st_mode) or not trusted_owner or (mode & 0o022 and not root_sticky):
                    raise SettingsError("private file ancestry is not trusted")
                if index == len(parent_parts) - 1 and (metadata.st_uid != effective_uid or mode & 0o022):
                    raise SettingsError("private file parent must be owned and non-writable by others")
            descriptor = os.open(path.name, os.O_RDONLY | nofollow | close_on_exec, dir_fd=parent_descriptor)
            descriptors.append(descriptor)
        except OSError as exc:
            raise SettingsError("private file cannot be opened safely") from exc
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_uid != effective_uid
        ):
            raise SettingsError("private file must be an owned regular mode-0600 file")
        raw = os.read(descriptor, maximum + 1)
        if len(raw) > maximum:
            raise SettingsError("private file is too large")
        return raw
    finally:
        for opened in reversed(descriptors):
            os.close(opened)


def read_token_file(path: Path) -> str:
    try:
        raw = read_private_file(path, 4096)
        token = raw.decode("utf-8").strip()
        if len(token) < 16 or any(character.isspace() for character in token):
            raise SettingsError("token value is invalid")
        return token
    except UnicodeDecodeError as exc:
        raise SettingsError("token value is invalid") from exc


@dataclass(frozen=True)
class FactorySettings:
    database_url: str
    socket_path: Path
    actors_file: Path
    artifact_attestor_database_url: str | None = None
    execution_enabled: bool = False
    semantic_coordinator_database_url: str | None = None
    semantic_validator_database_url: str | None = None
    semantic_adjudicator_database_url: str | None = None
    landing_quarantine_path: Path | None = None
    landing_provider: str | None = None
    landing_source_path: Path | None = None
    landing_scratch_path: Path | None = None
    landing_output_path: Path | None = None

    @classmethod
    def from_environment(cls) -> "FactorySettings":
        database_url = os.environ.get("FACTORY_DATABASE_URL", "")
        artifact_attestor_database_url = (
            os.environ.get("FACTORY_ARTIFACT_ATTESTOR_DATABASE_URL") or None
        )
        execution_flag = os.environ.get("FACTORY_EXECUTION_ENABLED", "false")
        if execution_flag not in {"true", "false"}:
            raise SettingsError("FACTORY_EXECUTION_ENABLED must be true or false")
        execution_enabled = execution_flag == "true"
        semantic_coordinator_database_url = os.environ.get(
            "FACTORY_SEMANTIC_COORDINATOR_DATABASE_URL"
        ) or None
        semantic_validator_database_url = os.environ.get(
            "FACTORY_SEMANTIC_VALIDATOR_DATABASE_URL"
        ) or None
        semantic_adjudicator_database_url = os.environ.get(
            "FACTORY_SEMANTIC_ADJUDICATOR_DATABASE_URL"
        ) or None
        landing_quarantine_raw = os.environ.get("FACTORY_LANDING_QUARANTINE_PATH")
        landing_quarantine_path = (
            Path(landing_quarantine_raw) if landing_quarantine_raw else None
        )
        landing_provider = os.environ.get("FACTORY_LANDING_PROVIDER", "").strip() or None
        if landing_provider not in {None, "grok", "qwen"}:
            raise SettingsError("FACTORY_LANDING_PROVIDER must be grok or qwen")
        landing_source_raw = os.environ.get("FACTORY_LANDING_SOURCE_PATH")
        landing_scratch_raw = os.environ.get("FACTORY_LANDING_SCRATCH_PATH")
        landing_output_raw = os.environ.get("FACTORY_LANDING_OUTPUT_PATH")
        landing_source_path = Path(landing_source_raw) if landing_source_raw else None
        landing_scratch_path = Path(landing_scratch_raw) if landing_scratch_raw else None
        landing_output_path = Path(landing_output_raw) if landing_output_raw else None
        actors_file = os.environ.get("FACTORY_ACTORS_FILE", "")
        socket_path = Path(os.environ.get("FACTORY_SOCKET_PATH", "/run/adaptive-factory/control.sock"))
        if (
            not database_url
            or not actors_file
            or not socket_path.is_absolute()
            or not Path(actors_file).is_absolute()
        ):
            raise SettingsError(
                "explicit database URL, actor file and absolute socket path are required"
            )
        if execution_enabled and (
            not artifact_attestor_database_url
            or database_url == artifact_attestor_database_url
        ):
            raise SettingsError(
                "enabled execution requires a separate artifact attestor database URL"
            )
        for label, path in (
            ("FACTORY_LANDING_QUARANTINE_PATH", landing_quarantine_path),
            ("FACTORY_LANDING_SOURCE_PATH", landing_source_path),
            ("FACTORY_LANDING_SCRATCH_PATH", landing_scratch_path),
            ("FACTORY_LANDING_OUTPUT_PATH", landing_output_path),
        ):
            if path is not None and (not path.is_absolute() or ".." in path.parts):
                raise SettingsError(f"{label} must be absolute and normalized")
        if landing_provider is not None and (
            landing_quarantine_path is None
            or landing_source_path is None
            or landing_scratch_path is None
            or landing_output_path is None
        ):
            raise SettingsError(
                "FACTORY_LANDING_PROVIDER requires quarantine, source, scratch and output paths"
            )
        return cls(
            database_url=database_url,
            socket_path=socket_path,
            actors_file=Path(actors_file),
            artifact_attestor_database_url=artifact_attestor_database_url,
            execution_enabled=execution_enabled,
            semantic_coordinator_database_url=semantic_coordinator_database_url,
            semantic_validator_database_url=semantic_validator_database_url,
            semantic_adjudicator_database_url=semantic_adjudicator_database_url,
            landing_quarantine_path=landing_quarantine_path,
            landing_provider=landing_provider,
            landing_source_path=landing_source_path,
            landing_scratch_path=landing_scratch_path,
            landing_output_path=landing_output_path,
        )
