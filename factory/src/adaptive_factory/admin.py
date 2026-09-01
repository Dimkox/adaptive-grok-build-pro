from __future__ import annotations

import argparse
import os
import re

from .migrations import PostgresMigrator, discover_migrations
from .store import PostgresFactoryStore


LOGIN_NAME = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


class BootstrapError(RuntimeError):
    pass


def provision_runtime_login(owner_url: str, login: str, password: str) -> None:
    if not owner_url or not LOGIN_NAME.fullmatch(login) or not 16 <= len(password) <= 1024:
        raise BootstrapError("bounded owner URL, runtime login and password are required")
    import psycopg
    from psycopg import sql

    with psycopg.connect(owner_url) as connection, connection.transaction(), connection.cursor() as cursor:
        cursor.execute("SELECT rolcanlogin,rolinherit,rolsuper,rolcreaterole,rolcreatedb FROM pg_roles WHERE rolname=%s", (login,))
        existing = cursor.fetchone()
        if existing is None:
            cursor.execute(
                sql.SQL("CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEROLE NOCREATEDB PASSWORD {}").format(
                    sql.Identifier(login), sql.Literal(password)
                )
            )
        elif existing != (True, False, False, False, False):
            raise BootstrapError("existing runtime login has unsafe attributes")
        else:
            cursor.execute(
                sql.SQL("ALTER ROLE {} PASSWORD {}").format(sql.Identifier(login), sql.Literal(password))
            )
        cursor.execute(sql.SQL("GRANT factory_runtime TO {}").format(sql.Identifier(login)))


def bootstrap_local(owner_url: str, login: str, password: str, runtime_url: str) -> dict[str, object]:
    PostgresMigrator(owner_url).apply()
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
        applied = PostgresMigrator(owner_url).apply()
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
