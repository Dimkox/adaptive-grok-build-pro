from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import stat

import uvicorn

from .api import TEXT_ID, Authenticator, create_app
from .migrations import discover_migrations
from .models import Actor
from .service import FactoryService
from .settings import FactorySettings, SettingsError, read_private_file, read_token_file
from .store import (
    PostgresArtifactAttestationStore,
    PostgresFactoryStore,
    PostgresSemanticAdjudicatorStore,
    PostgresSemanticCoordinatorStore,
    PostgresSemanticValidatorStore,
)


class ServerError(RuntimeError):
    pass


def _runtime_readiness(store: PostgresFactoryStore) -> dict[str, object]:
    try:
        readiness = store.readiness()
    except Exception as exc:
        raise ServerError("database capabilities are not ready") from exc
    session = readiness.get("session_user")
    if (
        readiness.get("status") != "ready"
        or readiness.get("schema_version") != len(discover_migrations())
        or readiness.get("database_role") != "factory_runtime"
        or readiness.get("capacity_consistent") is not True
        or readiness.get("accounting_consistent") is not True
        or not isinstance(session, str)
        or not session
        or len(session) > 63
    ):
        raise ServerError("database capabilities are not ready")
    return readiness


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
        actor_id = record["actor_id"]
        if not isinstance(actor_id, str) or not TEXT_ID.fullmatch(actor_id):
            raise ServerError("invalid actor identifier")
        if record["kind"] not in {
            "client", "worker", "operator", "validator", "adjudicator"
        }:
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
            actor_id,
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


def build_app(
    settings: FactorySettings,
    *,
    execution_registry=None,
    artifact_broker=None,
    snapshot_broker=None,
):
    try:
        store = PostgresFactoryStore(settings.database_url)
        runtime_readiness = _runtime_readiness(store)
    except Exception as exc:
        raise ServerError("database capabilities are not ready") from exc

    semantic_store = (
        PostgresSemanticCoordinatorStore(settings.semantic_coordinator_database_url)
        if settings.semantic_coordinator_database_url else None
    )
    semantic_validator_store = (
        PostgresSemanticValidatorStore(settings.semantic_validator_database_url)
        if settings.semantic_validator_database_url else None
    )
    semantic_adjudicator_store = (
        PostgresSemanticAdjudicatorStore(settings.semantic_adjudicator_database_url)
        if settings.semantic_adjudicator_database_url else None
    )

    attestation_store = None
    if settings.execution_enabled:
        if (
            execution_registry is None
            or not callable(getattr(execution_registry, "resolve", None))
            or artifact_broker is None
            or not callable(getattr(artifact_broker, "attest_artifact", None))
            or snapshot_broker is None
            or not callable(getattr(snapshot_broker, "snapshot", None))
        ):
            raise ServerError("trusted execution dependencies are unavailable")
        try:
            attestation_store = PostgresArtifactAttestationStore(
                settings.artifact_attestor_database_url
            )
            attestor_readiness = attestation_store.readiness()
        except Exception as exc:
            raise ServerError("database capabilities are not ready") from exc
        runtime_session = runtime_readiness.get("session_user")
        attestor_session = attestor_readiness.get("session_user")
        if (
            attestor_readiness.get("database_role") != "factory_artifact_attestor"
            or not isinstance(attestor_session, str)
            or not attestor_session
            or len(attestor_session) > 63
            or runtime_session == attestor_session
        ):
            raise ServerError("database capabilities are not ready")

    return create_app(
        FactoryService(
            store,
            execution_registry=execution_registry if settings.execution_enabled else None,
            artifact_broker=artifact_broker if settings.execution_enabled else None,
            artifact_attestation_store=attestation_store,
            snapshot_broker=snapshot_broker if settings.execution_enabled else None,
            semantic_store=semantic_store,
            semantic_validator_store=semantic_validator_store,
            semantic_adjudicator_store=semantic_adjudicator_store,
        ),
        Authenticator(load_actors(settings.actors_file)),
        execution_enabled=settings.execution_enabled,
    )


def main(
    *,
    execution_registry=None,
    artifact_broker=None,
    snapshot_broker=None,
) -> int:
    settings = FactorySettings.from_environment()
    app = build_app(
        settings,
        execution_registry=execution_registry,
        artifact_broker=artifact_broker,
        snapshot_broker=snapshot_broker,
    )
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
