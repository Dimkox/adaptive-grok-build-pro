from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat


class SettingsError(RuntimeError):
    pass


def read_token_file(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SettingsError("token file cannot be opened safely") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise SettingsError("token file must be a regular mode-0600 file")
        raw = os.read(descriptor, 4097)
        if len(raw) > 4096:
            raise SettingsError("token file is too large")
        token = raw.decode("utf-8").strip()
        if len(token) < 16 or any(character.isspace() for character in token):
            raise SettingsError("token value is invalid")
        return token
    finally:
        os.close(descriptor)


@dataclass(frozen=True)
class FactorySettings:
    database_url: str
    socket_path: Path
    token_file: Path

    @classmethod
    def from_environment(cls) -> "FactorySettings":
        database_url = os.environ.get("FACTORY_DATABASE_URL", "")
        token_file = os.environ.get("FACTORY_API_TOKEN_FILE", "")
        socket_path = Path(os.environ.get("FACTORY_SOCKET_PATH", "/run/adaptive-factory/control.sock"))
        if not database_url or not token_file or not socket_path.is_absolute():
            raise SettingsError("explicit database URL, token file and absolute socket path are required")
        return cls(database_url, socket_path, Path(token_file))
