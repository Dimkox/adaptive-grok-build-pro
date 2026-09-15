"""Dedicated Unix-socket landing host: no PostgreSQL composition or discovery."""

from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
import os
from pathlib import Path
import stat

import uvicorn

from .api import Authenticator, create_app
from .landing_host_config import LandingHostConfig, load_host_config, _private_directory
from .landing_server import compose_server_landing
from .server import load_actors, prepare_unix_socket
from .settings import SettingsError


def build_landing_app(config: LandingHostConfig, *, qwen_env_file: Path | None = None,
                      provider_env_file: Path | None = None):
    credential_file = provider_env_file or qwen_env_file
    if credential_file is not None:
        roots = (config.control_repository, config.publication_state,
                 config.settings.landing_source_path, config.settings.landing_state_path,
                 config.settings.landing_quarantine_path, config.settings.landing_scratch_path,
                 config.settings.landing_output_path)
        if any(credential_file == root or root in credential_file.parents for root in roots if root is not None):
            raise SettingsError("Qwen credential file must be outside landing roots")
    _private_directory(config.publication_state, repository_root=config.control_repository)
    owned = compose_server_landing(config.settings, repository_root=config.control_repository,
                                   qwen_env_file=qwen_env_file, provider_env_file=provider_env_file)
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
    credential = parser.add_mutually_exclusive_group()
    credential.add_argument("--qwen-env-file", type=Path)
    credential.add_argument("--provider-env-file", type=Path)
    args = parser.parse_args()
    config = load_host_config(args.config)
    app = build_landing_app(config, qwen_env_file=args.qwen_env_file, provider_env_file=args.provider_env_file)
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
        try:
            if listener is not None:
                listener.close()
        finally:
            try:
                app.state.owned_landing_runtime.close()
            finally:
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
