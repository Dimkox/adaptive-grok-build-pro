from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import stat

import uvicorn

from .api import Authenticator, create_app
from .models import Actor
from .service import FactoryService
from .settings import FactorySettings, SettingsError, read_private_file, read_token_file
from .store import PostgresFactoryStore


class ServerError(RuntimeError):
    pass


def _read_private_file(path: Path, maximum: int) -> bytes:
    try:
        return read_private_file(path, maximum)
    except SettingsError as exc:
        raise ServerError("configuration file cannot be opened safely") from exc


def load_actors(path: Path) -> dict[str, Actor]:
    try:
        payload = json.loads(_read_private_file(path, 65_536))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ServerError("actor configuration must be valid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {"actors"} or not isinstance(payload["actors"], list):
        raise ServerError("closed actor configuration required")
    tokens: dict[str, Actor] = {}
    for record in payload["actors"]:
        expected = {"actor_id", "kind", "scopes", "repositories", "token_file"}
        if not isinstance(record, dict) or set(record) != expected:
            raise ServerError("closed actor record required")
        if record["kind"] not in {"client", "worker", "operator"}:
            raise ServerError("invalid actor kind")
        if not all(isinstance(item, str) and item for item in record["scopes"] + record["repositories"]):
            raise ServerError("invalid actor authorization")
        try:
            token = read_token_file(Path(record["token_file"]))
        except SettingsError as exc:
            raise ServerError("actor token cannot be loaded safely") from exc
        if token in tokens:
            raise ServerError("duplicate actor token")
        tokens[token] = Actor(
            str(record["actor_id"]),
            record["kind"],
            frozenset(record["scopes"]),
            frozenset(record["repositories"]),
        )
    if not tokens:
        raise ServerError("at least one actor is required")
    return tokens


def prepare_unix_socket(path: Path) -> socket.socket:
    if not path.is_absolute():
        raise ServerError("socket path must be absolute")
    parent = path.parent
    metadata = parent.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) & 0o022:
        raise ServerError("socket parent must be owned and not group/world writable")
    try:
        existing = path.lstat()
    except FileNotFoundError:
        existing = None
    if existing is not None:
        if not stat.S_ISSOCK(existing.st_mode) or existing.st_uid != os.geteuid():
            raise ServerError("refusing to replace non-owned socket path")
        path.unlink()
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        listener.bind(str(path))
        # Group access is the explicit contract after owner/private-parent validation above.
        os.chmod(path, 0o660, follow_symlinks=False)  # nosec B103
        listener.listen(128)
        return listener
    except Exception:
        listener.close()
        if path.exists() and stat.S_ISSOCK(path.lstat().st_mode):
            path.unlink()
        raise


def build_app(settings: FactorySettings):
    store = PostgresFactoryStore(settings.database_url)
    return create_app(FactoryService(store), Authenticator(load_actors(settings.actors_file)))


def main() -> int:
    settings = FactorySettings.from_environment()
    app = build_app(settings)
    listener = prepare_unix_socket(settings.socket_path)
    try:
        config = uvicorn.Config(app, access_log=False, log_config=None, server_header=False)
        uvicorn.Server(config).run(sockets=[listener])
    finally:
        listener.close()
        try:
            if stat.S_ISSOCK(settings.socket_path.lstat().st_mode):
                settings.socket_path.unlink()
        except FileNotFoundError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
