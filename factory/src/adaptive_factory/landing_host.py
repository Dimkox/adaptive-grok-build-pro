"""Dedicated Unix-socket landing host: no PostgreSQL composition or discovery."""

from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import stat

import uvicorn

from .api import Authenticator, create_app
from .landing_contracts import strict_json_object
from .landing_server import compose_server_landing, _private_directory
from .server import load_actors, prepare_unix_socket
from .settings import FactorySettings, SettingsError, read_private_file


@dataclass(frozen=True)
class LandingHostConfig:
    settings: FactorySettings
    control_repository: Path
    publication_state: Path


def load_host_config(path: Path) -> LandingHostConfig:
    data = strict_json_object(read_private_file(path, 16_384), maximum=16_384)
    expected = {"schema_version", "control_repository", "socket_path", "actors_file",
                "state_path", "quarantine_path", "source_path", "scratch_path",
                "output_path", "publication_state_path", "live_enabled", "selected_profile"}
    if set(data) != expected or type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise SettingsError("closed landing host configuration required")
    if type(data["live_enabled"]) is not bool or data["selected_profile"] not in ("qwen-omni", "grok-vision"):
        raise SettingsError("explicit landing capability profile required")
    paths = {}
    for name in expected - {"schema_version", "live_enabled", "selected_profile"}:
        value = data[name]
        if not isinstance(value, str) or not value.startswith("/") or ".." in Path(value).parts:
            raise SettingsError("absolute normalized landing host paths required")
        paths[name] = Path(value)
    settings = FactorySettings(
        database_url="", socket_path=paths["socket_path"], actors_file=paths["actors_file"],
        landing_state_path=paths["state_path"], landing_quarantine_path=paths["quarantine_path"],
        landing_source_path=paths["source_path"], landing_scratch_path=paths["scratch_path"],
        landing_output_path=paths["output_path"], landing_live_enabled=data["live_enabled"],
        landing_provider=data["selected_profile"] if data["live_enabled"] else "unavailable",
    )
    settings.validate_landing()
    roots = [paths[name] for name in (
        "state_path", "quarantine_path", "source_path", "scratch_path", "output_path",
        "publication_state_path", "control_repository",
    )]
    if any(left == right or left in right.parents or right in left.parents
           for index, left in enumerate(roots) for right in roots[index + 1:]):
        raise SettingsError("landing host roots must be disjoint")
    for secret_path in (paths["actors_file"], paths["socket_path"], path):
        if any(secret_path == root or root in secret_path.parents for root in roots):
            raise SettingsError("configuration and sockets must be outside durable data roots")
    return LandingHostConfig(settings, paths["control_repository"], paths["publication_state_path"])


def build_landing_app(config: LandingHostConfig):
    _private_directory(config.publication_state, repository_root=config.control_repository)
    owned = compose_server_landing(config.settings, repository_root=config.control_repository)
    if owned is None or owned.store is None:
        raise SettingsError("dedicated landing host requires durable composition")
    try:
        app = create_app(None, Authenticator(load_actors(config.settings.actors_file)),
                         execution_enabled=False, landing_service=owned.service, landing_only=True)

        @asynccontextmanager
        async def lifespan(_application):
            try:
                yield
            finally:
                owned.close()

        app.router.lifespan_context = lifespan
        app.state.owned_landing_runtime = owned
        return app
    except BaseException:
        owned.close()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Dedicated default-off landing Unix-socket host")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config = load_host_config(args.config)
    app = build_landing_app(config)
    listener = None
    socket_identity = None
    try:
        listener = prepare_unix_socket(config.settings.socket_path)
        metadata = config.settings.socket_path.lstat()
        socket_identity = (metadata.st_dev, metadata.st_ino)
        uvicorn.Server(uvicorn.Config(
            app, access_log=False, log_config=None, server_header=False,
            timeout_graceful_shutdown=330,
        )).run(sockets=[listener])
    finally:
        if listener is not None:
            listener.close()
        app.state.owned_landing_runtime.close()
        try:
            metadata = config.settings.socket_path.lstat()
            if (stat.S_ISSOCK(metadata.st_mode) and metadata.st_uid == os.geteuid()
                    and (metadata.st_dev, metadata.st_ino) == socket_identity):
                config.settings.socket_path.unlink()
        except FileNotFoundError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
