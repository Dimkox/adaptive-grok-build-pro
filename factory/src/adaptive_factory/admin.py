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
from .store import PostgresArtifactAttestationStore, PostgresFactoryStore


LOGIN_NAME = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


class BootstrapError(RuntimeError):
    pass


def _validate_capability_role(cursor, role: str, label: str) -> None:
    cursor.execute(
        """SELECT rolcanlogin,rolinherit,rolsuper,rolcreaterole,rolcreatedb,
        rolreplication,rolbypassrls,COALESCE(rolconfig,ARRAY[]::text[])
        FROM pg_roles WHERE rolname=%s""",
        (role,),
    )
    capability = cursor.fetchone()
    expected_config = (
        ("search_path=factory, pg_catalog",) if role == "factory_runtime" else ()
    )
    if capability is None or capability[:7] != (False, False, False, False, False, False, False) \
            or tuple(capability[7]) != expected_config:
        raise BootstrapError(f"{label} capability role has unsafe attributes")
    cursor.execute(
        """SELECT EXISTS(SELECT 1 FROM pg_auth_members m
        JOIN pg_roles member ON member.oid=m.member WHERE member.rolname=%s)""",
        (role,),
    )
    if cursor.fetchone()[0]:
        raise BootstrapError(f"{label} capability role has unsafe membership")


def _grant_and_validate_membership(cursor, login: str, role: str, label: str) -> None:
    from psycopg import sql

    if cursor.connection.info.server_version >= 160000:
        cursor.execute(sql.SQL("GRANT {} TO {} WITH ADMIN FALSE, INHERIT FALSE, SET TRUE").format(
            sql.Identifier(role), sql.Identifier(login)
        ))
        cursor.execute(
            """SELECT r.rolname,m.admin_option,m.inherit_option,m.set_option
            FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.roleid
            JOIN pg_roles u ON u.oid=m.member WHERE u.rolname=%s""",
            (login,),
        )
        expected = [(role, False, False, True)]
    else:
        cursor.execute(sql.SQL("GRANT {} TO {}").format(
            sql.Identifier(role), sql.Identifier(login)
        ))
        cursor.execute(
            """SELECT r.rolname,m.admin_option FROM pg_auth_members m
            JOIN pg_roles r ON r.oid=m.roleid JOIN pg_roles u ON u.oid=m.member
            WHERE u.rolname=%s""",
            (login,),
        )
        expected = [(role, False)]
    if cursor.fetchall() != expected:
        raise BootstrapError(f"{label} login has unsafe role membership")


def provision_runtime_login(
    owner_url: str,
    login: str,
    password: str,
    *,
    artifact_attestor_login: str | None = None,
) -> None:
    if not owner_url or not LOGIN_NAME.fullmatch(login) or not 16 <= len(password) <= 1024:
        raise BootstrapError("bounded owner URL, runtime login and password are required")
    import psycopg
    from psycopg import sql

    try:
        with psycopg.connect(owner_url) as connection, connection.transaction(), connection.cursor() as cursor:
            validate_factory_role_boundary(
                cursor,
                expected_runtime_login=login,
                expected_artifact_attestor_login=artifact_attestor_login,
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
                expected_artifact_attestor_login=artifact_attestor_login,
                allow_missing_groups=False,
                require_runtime_membership=True,
            )
    except RoleSafetyError as exc:
        raise BootstrapError("database role boundary validation failed") from exc


def provision_artifact_attestor_login(
    owner_url: str, login: str, password: str, *, runtime_login: str | None = None
) -> None:
    if (
        not owner_url or not LOGIN_NAME.fullmatch(login) or not 16 <= len(password) <= 1024
        or login == runtime_login
    ):
        raise BootstrapError("distinct bounded artifact attestor login and password are required")
    import psycopg
    from psycopg import sql

    try:
        with psycopg.connect(owner_url) as connection, connection.transaction(), connection.cursor() as cursor:
            validate_factory_role_boundary(
                cursor,
                expected_runtime_login=runtime_login,
                expected_artifact_attestor_login=login,
                allow_missing_groups=False,
                require_runtime_membership=runtime_login is not None,
                require_artifact_attestor_membership=False,
            )
            cursor.execute(
                """SELECT rolcanlogin,rolinherit,rolsuper,rolcreaterole,rolcreatedb,
                rolreplication,rolbypassrls,COALESCE(rolconfig,ARRAY[]::text[])
                FROM pg_roles WHERE rolname=%s""",
                (login,),
            )
            existing = cursor.fetchone()
            if existing is None:
                cursor.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEROLE NOCREATEDB PASSWORD {}"
                    ).format(sql.Identifier(login), sql.Literal(password))
                )
            elif existing[:7] != (True, False, False, False, False, False, False) \
                    or tuple(existing[7]) != ():
                raise BootstrapError("existing artifact attestor login has unsafe attributes")
            else:
                cursor.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(login), sql.Literal(password)
                ))
            _validate_capability_role(cursor, "factory_artifact_attestor", "artifact attestor")
            _grant_and_validate_membership(
                cursor, login, "factory_artifact_attestor", "artifact attestor"
            )
            validate_factory_role_boundary(
                cursor,
                expected_runtime_login=runtime_login,
                expected_artifact_attestor_login=login,
                allow_missing_groups=False,
                require_runtime_membership=runtime_login is not None,
                require_artifact_attestor_membership=True,
            )
    except RoleSafetyError as exc:
        raise BootstrapError("database role boundary validation failed") from exc


def bootstrap_local(
    owner_url: str, login: str, password: str, runtime_url: str,
    artifact_attestor_login: str | None = None,
    artifact_attestor_password: str | None = None,
    artifact_attestor_url: str | None = None,
) -> dict[str, object]:
    if not owner_url or not LOGIN_NAME.fullmatch(login) or not 16 <= len(password) <= 1024:
        raise BootstrapError("bounded owner URL, runtime login and password are required")
    attestor_values = (artifact_attestor_login, artifact_attestor_password, artifact_attestor_url)
    if any(attestor_values) and not all(attestor_values):
        raise BootstrapError("complete artifact attestor configuration is required")
    try:
        PostgresMigrator(owner_url).apply(
            expected_runtime_login=login,
            expected_artifact_attestor_login=artifact_attestor_login,
        )
    except RoleSafetyError as exc:
        raise BootstrapError("database role boundary validation failed") from exc
    provision_runtime_login(
        owner_url,
        login,
        password,
        artifact_attestor_login=artifact_attestor_login,
    )
    readiness = PostgresFactoryStore(runtime_url).readiness()
    if (
        readiness.get("status") != "ready"
        or readiness.get("schema_version") != len(discover_migrations())
        or readiness.get("session_user") != login
    ):
        raise BootstrapError("runtime readiness validation failed")
    if any(attestor_values):
        provision_artifact_attestor_login(
            owner_url, artifact_attestor_login, artifact_attestor_password,
            runtime_login=login,
        )
        attestor = PostgresArtifactAttestationStore(artifact_attestor_url).readiness()
        if (
            attestor["database_role"] != "factory_artifact_attestor"
            or attestor["session_user"] != artifact_attestor_login
        ):
            raise BootstrapError("artifact attestor readiness validation failed")
        readiness["artifact_attestor_database_role"] = attestor["database_role"]
    return readiness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adaptive-factory-admin")
    parser.add_argument("command", choices=("migrate", "bootstrap-local"))
    args = parser.parse_args(argv)
    owner_url = os.environ.get("FACTORY_MIGRATOR_DATABASE_URL", "")
    if args.command == "migrate":
        login = os.environ.get("FACTORY_RUNTIME_LOGIN") or None
        artifact_attestor_login = os.environ.get("FACTORY_ARTIFACT_ATTESTOR_LOGIN") or None
        applied = PostgresMigrator(owner_url).apply(
            expected_runtime_login=login,
            expected_artifact_attestor_login=artifact_attestor_login,
        )
        print(f"schema_version={len(discover_migrations())} applied={len(applied)}")
        return 0
    login = os.environ.get("FACTORY_RUNTIME_LOGIN", "")
    password = os.environ.get("FACTORY_RUNTIME_PASSWORD", "")
    runtime_url = os.environ.get("FACTORY_DATABASE_URL", "")
    readiness = bootstrap_local(
        owner_url, login, password, runtime_url,
        os.environ.get("FACTORY_ARTIFACT_ATTESTOR_LOGIN") or None,
        os.environ.get("FACTORY_ARTIFACT_ATTESTOR_PASSWORD") or None,
        os.environ.get("FACTORY_ARTIFACT_ATTESTOR_DATABASE_URL") or None,
    )
    print(f"status={readiness['status']} schema_version={readiness['schema_version']} role={readiness['database_role']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
