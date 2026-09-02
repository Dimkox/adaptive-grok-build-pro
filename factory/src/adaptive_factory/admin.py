from __future__ import annotations

import argparse
import os
import re

from .migrations import (
    PostgresMigrator,
    RoleSafetyError,
    discover_migrations,
    validate_factory_role_boundary,
)
from .store import PostgresFactoryStore


LOGIN_NAME = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


class BootstrapError(RuntimeError):
    pass


def provision_runtime_login(owner_url: str, login: str, password: str) -> None:
    if not owner_url or not LOGIN_NAME.fullmatch(login) or not 16 <= len(password) <= 1024:
        raise BootstrapError("bounded owner URL, runtime login and password are required")
    import psycopg
    from psycopg import sql

    try:
        with psycopg.connect(owner_url) as connection, connection.transaction(), connection.cursor() as cursor:
            validate_factory_role_boundary(
                cursor,
                expected_runtime_login=login,
                allow_missing_groups=False,
                require_runtime_membership=False,
            )
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (login,))
            if cursor.fetchone() is None:
                cursor.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEROLE "
                        "NOCREATEDB NOREPLICATION NOBYPASSRLS PASSWORD {}"
                    ).format(sql.Identifier(login), sql.Literal(password))
                )
            else:
                cursor.execute(
                    sql.SQL("ALTER ROLE {} PASSWORD {}").format(sql.Identifier(login), sql.Literal(password))
                )
            cursor.execute(sql.SQL("GRANT factory_runtime TO {}").format(sql.Identifier(login)))
            validate_factory_role_boundary(
                cursor,
                expected_runtime_login=login,
                allow_missing_groups=False,
                require_runtime_membership=True,
            )
    except RoleSafetyError as exc:
        raise BootstrapError("database role boundary validation failed") from exc


def bootstrap_local(owner_url: str, login: str, password: str, runtime_url: str) -> dict[str, object]:
    if not owner_url or not LOGIN_NAME.fullmatch(login) or not 16 <= len(password) <= 1024:
        raise BootstrapError("bounded owner URL, runtime login and password are required")
    try:
        PostgresMigrator(owner_url).apply(expected_runtime_login=login)
    except RoleSafetyError as exc:
        raise BootstrapError("database role boundary validation failed") from exc
    provision_runtime_login(owner_url, login, password)
    readiness = PostgresFactoryStore(runtime_url).readiness()
    if readiness.get("status") != "ready" or readiness.get("schema_version") != len(discover_migrations()):
        raise BootstrapError("runtime readiness validation failed")
    return readiness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adaptive-factory-admin")
    parser.add_argument("command", choices=("migrate", "bootstrap-local"))
    args = parser.parse_args(argv)
    owner_url = os.environ.get("FACTORY_MIGRATOR_DATABASE_URL", "")
    if args.command == "migrate":
        login = os.environ.get("FACTORY_RUNTIME_LOGIN") or None
        applied = PostgresMigrator(owner_url).apply(expected_runtime_login=login)
        print(f"schema_version={len(discover_migrations())} applied={len(applied)}")
        return 0
    login = os.environ.get("FACTORY_RUNTIME_LOGIN", "")
    password = os.environ.get("FACTORY_RUNTIME_PASSWORD", "")
    runtime_url = os.environ.get("FACTORY_DATABASE_URL", "")
    readiness = bootstrap_local(owner_url, login, password, runtime_url)
    print(f"status={readiness['status']} schema_version={readiness['schema_version']} role={readiness['database_role']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
