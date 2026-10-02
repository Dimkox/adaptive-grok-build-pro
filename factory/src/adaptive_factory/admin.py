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


def provision_runtime_login(
    owner_url: str,
    login: str,
    password: str,
    *,
    expected_artifact_attestor_login: str | None = None,
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
                expected_artifact_attestor_login=expected_artifact_attestor_login,
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
                expected_artifact_attestor_login=expected_artifact_attestor_login,
                allow_missing_groups=False,
                require_runtime_membership=True,
                require_artifact_attestor_membership=False,
            )
    except RoleSafetyError as exc:
        raise BootstrapError("database role boundary validation failed") from exc


def provision_result_dispatcher_login(owner_url: str, login: str, password: str) -> None:
    if not owner_url or not LOGIN_NAME.fullmatch(login) or not 16 <= len(password) <= 1024:
        raise BootstrapError("bounded dispatcher login and password are required")
    import psycopg
    from psycopg import sql

    with psycopg.connect(owner_url) as connection, connection.transaction(), connection.cursor() as cursor:
        cursor.execute(
            "SELECT rolcanlogin,rolinherit,rolsuper,rolcreaterole,rolcreatedb,"
            "rolreplication,rolbypassrls FROM pg_roles WHERE rolname='factory_result_dispatcher'"
        )
        if cursor.fetchone() != (False, False, False, False, False, False, False):
            raise BootstrapError("result dispatcher capability is unavailable")
        cursor.execute(
            "SELECT rolcanlogin,rolinherit,rolsuper,rolcreaterole,rolcreatedb,"
            "rolreplication,rolbypassrls FROM pg_roles WHERE rolname=%s", (login,)
        )
        login_attributes = cursor.fetchone()
        if login_attributes is None:
            cursor.execute(sql.SQL(
                "CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEROLE NOCREATEDB "
                "NOREPLICATION NOBYPASSRLS PASSWORD {}"
            ).format(sql.Identifier(login), sql.Literal(password)))
        elif login_attributes == (True, False, False, False, False, False, False):
            cursor.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                sql.Identifier(login), sql.Literal(password)
            ))
        else:
            raise BootstrapError("result dispatcher login is unsafe")
        cursor.execute(
            "SELECT parent.rolname FROM pg_auth_members membership "
            "JOIN pg_roles parent ON parent.oid=membership.roleid "
            "JOIN pg_roles member ON member.oid=membership.member WHERE member.rolname=%s",
            (login,),
        )
        memberships = {row[0] for row in cursor.fetchall()}
        if memberships - {"factory_result_dispatcher"}:
            raise BootstrapError("result dispatcher login has unsafe membership")
        cursor.execute(sql.SQL("GRANT factory_result_dispatcher TO {}").format(
            sql.Identifier(login)
        ))


def provision_artifact_attestor_login(
    owner_url: str,
    login: str,
    password: str,
    *,
    runtime_login: str | None = None,
) -> None:
    if (
        not owner_url
        or not LOGIN_NAME.fullmatch(login)
        or not 16 <= len(password) <= 1024
        or login == runtime_login
    ):
        raise BootstrapError(
            "distinct bounded artifact attestor login and password are required"
        )
    import psycopg
    from psycopg import sql

    try:
        with (
            psycopg.connect(owner_url) as connection,
            connection.transaction(),
            connection.cursor() as cursor,
        ):
            validate_factory_role_boundary(
                cursor,
                expected_runtime_login=runtime_login,
                expected_artifact_attestor_login=login,
                allow_missing_groups=False,
                require_runtime_membership=runtime_login is not None,
                require_artifact_attestor_membership=False,
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
                    sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                        sql.Identifier(login), sql.Literal(password)
                    )
                )
            cursor.execute(
                sql.SQL("GRANT factory_artifact_attestor TO {}").format(
                    sql.Identifier(login)
                )
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


def _validate_semantic_capability_role(cursor, role: str, label: str) -> None:
    cursor.execute(
        """SELECT rolcanlogin,rolinherit,rolsuper,rolcreaterole,rolcreatedb,
        rolreplication,rolbypassrls,COALESCE(rolconfig,ARRAY[]::text[])
        FROM pg_roles WHERE rolname=%s""",
        (role,),
    )
    capability = cursor.fetchone()
    if (
        capability is None
        or capability[:7] != (False, False, False, False, False, False, False)
        or tuple(capability[7]) != ()
    ):
        raise BootstrapError(f"{label} capability role has unsafe attributes")
    cursor.execute(
        """SELECT EXISTS(SELECT 1 FROM pg_auth_members membership
        JOIN pg_roles member ON member.oid=membership.member
        WHERE member.rolname=%s)""",
        (role,),
    )
    if cursor.fetchone()[0]:
        raise BootstrapError(f"{label} capability role has unsafe membership")


def _grant_and_validate_semantic_membership(
    cursor, login: str, role: str, label: str
) -> None:
    from psycopg import sql

    cursor.execute(
        sql.SQL("GRANT {} TO {} WITH ADMIN FALSE, INHERIT FALSE, SET TRUE").format(
            sql.Identifier(role), sql.Identifier(login)
        )
    )
    cursor.execute(
        """SELECT parent.rolname,membership.admin_option,
        membership.inherit_option,membership.set_option
        FROM pg_auth_members membership
        JOIN pg_roles parent ON parent.oid=membership.roleid
        JOIN pg_roles member ON member.oid=membership.member
        WHERE member.rolname=%s""",
        (login,),
    )
    if cursor.fetchall() != [(role, False, False, True)]:
        raise BootstrapError(f"{label} login has unsafe role membership")


def _provision_semantic_login(
    owner_url: str,
    login: str,
    password: str,
    *,
    role: str,
    label: str,
) -> None:
    if not owner_url or not LOGIN_NAME.fullmatch(login) or not 16 <= len(password) <= 1024:
        raise BootstrapError(f"bounded owner URL, {label} login and password are required")
    if role not in {
        "factory_semantic_coordinator",
        "factory_semantic_validator",
        "factory_semantic_adjudicator",
        "factory_m7_registry", "factory_m7_outcome", "factory_m7_check_context", "factory_m7_reader",
    }:
        raise BootstrapError("unknown semantic capability role")
    import psycopg
    from psycopg import sql

    with psycopg.connect(owner_url) as connection, connection.transaction(), connection.cursor() as cursor:
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
            raise BootstrapError(f"existing {label} login has unsafe attributes")
        else:
            cursor.execute(
                sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(login), sql.Literal(password)
                )
            )
        _validate_semantic_capability_role(cursor, role, label)
        for forbidden_role in (
            "factory_runtime",
            "factory_artifact_attestor",
            "factory_semantic_coordinator",
            "factory_semantic_validator",
            "factory_semantic_adjudicator",
        ):
            if forbidden_role == role:
                continue
            cursor.execute("SELECT pg_has_role(%s,%s,'MEMBER')", (login, forbidden_role))
            if cursor.fetchone()[0]:
                raise BootstrapError(f"{label} login has unsafe role membership")
        _grant_and_validate_semantic_membership(cursor, login, role, label)


def provision_semantic_coordinator_login(
    owner_url: str, login: str, password: str
) -> None:
    _provision_semantic_login(
        owner_url,
        login,
        password,
        role="factory_semantic_coordinator",
        label="semantic coordinator",
    )


def provision_semantic_validator_login(
    owner_url: str, login: str, password: str
) -> None:
    _provision_semantic_login(
        owner_url,
        login,
        password,
        role="factory_semantic_validator",
        label="semantic validator",
    )


def provision_semantic_adjudicator_login(
    owner_url: str, login: str, password: str
) -> None:
    _provision_semantic_login(
        owner_url,
        login,
        password,
        role="factory_semantic_adjudicator",
        label="semantic adjudicator",
    )


def bootstrap_local(
    owner_url: str,
    login: str,
    password: str,
    runtime_url: str,
    *,
    artifact_attestor_login: str | None = None,
    artifact_attestor_password: str | None = None,
    artifact_attestor_url: str | None = None,
) -> dict[str, object]:
    if not owner_url or not LOGIN_NAME.fullmatch(login) or not 16 <= len(password) <= 1024:
        raise BootstrapError("bounded owner URL, runtime login and password are required")
    attestor_values = (
        artifact_attestor_login,
        artifact_attestor_password,
        artifact_attestor_url,
    )
    if any(attestor_values) and not all(attestor_values):
        raise BootstrapError("complete artifact attestor configuration is required")
    try:
        PostgresMigrator(owner_url).apply(
            expected_runtime_login=login,
            expected_artifact_attestor_login=artifact_attestor_login,
            require_artifact_attestor_membership=False,
        )
    except RoleSafetyError as exc:
        raise BootstrapError("database role boundary validation failed") from exc
    provision_runtime_login(
        owner_url,
        login,
        password,
        expected_artifact_attestor_login=artifact_attestor_login,
    )
    if artifact_attestor_login is not None:
        provision_artifact_attestor_login(
            owner_url,
            artifact_attestor_login,
            artifact_attestor_password,
            runtime_login=login,
        )
        try:
            PostgresMigrator(owner_url).apply(
                expected_runtime_login=login,
                expected_artifact_attestor_login=artifact_attestor_login,
            )
        except RoleSafetyError as exc:
            raise BootstrapError("database role boundary validation failed") from exc
    runtime_store = PostgresFactoryStore(runtime_url)
    readiness = runtime_store.readiness()
    with runtime_store._transaction() as cursor:
        cursor.execute("SELECT session_user")
        runtime_session_user = cursor.fetchone()[0]
    if (
        readiness.get("status") != "ready"
        or readiness.get("schema_version") != len(discover_migrations())
        or runtime_session_user != login
    ):
        raise BootstrapError("runtime readiness validation failed")
    if artifact_attestor_login is not None:
        attestor_readiness = PostgresArtifactAttestationStore(
            artifact_attestor_url
        ).readiness()
        if attestor_readiness != {
            "session_user": artifact_attestor_login,
            "database_role": "factory_artifact_attestor",
        }:
            raise BootstrapError("artifact attestor readiness validation failed")
        readiness["artifact_attestor_database_role"] = attestor_readiness[
            "database_role"
        ]
    return readiness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adaptive-factory-admin")
    parser.add_argument("command", choices=("migrate", "bootstrap-local"))
    args = parser.parse_args(argv)
    owner_url = os.environ.get("FACTORY_MIGRATOR_DATABASE_URL", "")
    artifact_attestor_login = os.environ.get("FACTORY_ARTIFACT_ATTESTOR_LOGIN") or None
    if args.command == "migrate":
        login = os.environ.get("FACTORY_RUNTIME_LOGIN") or None
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
        owner_url,
        login,
        password,
        runtime_url,
        artifact_attestor_login=artifact_attestor_login,
        artifact_attestor_password=(
            os.environ.get("FACTORY_ARTIFACT_ATTESTOR_PASSWORD") or None
        ),
        artifact_attestor_url=(
            os.environ.get("FACTORY_ARTIFACT_ATTESTOR_DATABASE_URL") or None
        ),
    )
    print(f"status={readiness['status']} schema_version={readiness['schema_version']} role={readiness['database_role']}")
    return 0


M7_CAPABILITIES = frozenset({"registry", "outcome", "check_context", "reader"})


def provision_m7_login(owner_url: str, login: str, password: str, *, capability_kind: str) -> None:
    if capability_kind not in M7_CAPABILITIES:
        raise BootstrapError("unknown M7 capability")
    _provision_semantic_login(owner_url, login, password,
                             role="factory_m7_" + capability_kind, label="M7 " + capability_kind)


def configure_m7_source(owner_url: str, *, login: str, repository_id: str, source_id: str,
                        capability_kind: str, source_kind: str, mode: str,
                        trust_config_digest: str, valid_until, max_age_seconds: int, enabled: bool = True) -> None:
    """Owner-only configuration. No source is configured by migration or runtime input."""
    import psycopg
    from .shadow_lookup import canonical_m7_bytes, m7_digest
    from .shadow_lookup import _identifier, _digest, _time, _instant
    if not LOGIN_NAME.fullmatch(login) or capability_kind not in M7_CAPABILITIES:
        raise BootstrapError("invalid M7 principal")
    _identifier(repository_id)
    _identifier(source_id)
    _digest(trust_config_digest)
    expires = _time(valid_until.isoformat() if hasattr(valid_until, "isoformat") else valid_until)
    if (source_kind not in {"registry", "human_outcome", "signed_ci", "github_current", "deployed_epoch"}
            or mode not in {"synthetic", "imported", "authenticated"}
            or type(max_age_seconds) is not int or not 1 <= max_age_seconds <= 86400 or type(enabled) is not bool):
        raise BootstrapError("invalid M7 source configuration")
    expected = {"registry": {"registry"}, "outcome": {"human_outcome"},
                "check_context": {"signed_ci", "github_current", "deployed_epoch"}}
    if capability_kind != "reader" and source_kind not in expected[capability_kind]:
        raise BootstrapError("M7 source capability mismatch")
    with psycopg.connect(owner_url) as connection, connection.cursor() as cursor:
        _validate_semantic_capability_role(cursor, "factory_m7_" + capability_kind, "M7")
        cursor.execute("SELECT oid FROM pg_roles WHERE rolname=%s", (login,))
        row = cursor.fetchone()
        if row is None:
            raise BootstrapError("M7 login missing")
        principal = row[0]
        cursor.execute("SELECT pg_has_role(%s,%s,'MEMBER')", (login, "factory_m7_" + capability_kind))
        if not cursor.fetchone()[0]:
            raise BootstrapError("M7 login capability missing")
        body = {"principal_oid": principal, "principal_name": login, "repository_id": repository_id,
                "source_id": source_id, "capability_kind": capability_kind, "source_kind": source_kind,
                "mode": mode, "trust_config_digest": trust_config_digest,
                "valid_until": expires, "max_age_seconds": max_age_seconds, "enabled": enabled}
        digest = m7_digest("adaptive-factory.m7-source-binding/v1", body)
        cursor.execute("""DELETE FROM factory.m7_source_bindings WHERE principal_name=%s AND repository_id=%s
                       AND source_id=%s AND capability_kind=%s AND principal_oid<>%s""",
                       (login, repository_id, source_id, capability_kind, principal))
        cursor.execute("""INSERT INTO factory.m7_source_bindings(principal_oid,principal_name,repository_id,source_id,
            capability_kind,source_kind,mode,trust_config_digest,binding_digest,enabled,valid_until,max_age_seconds,canonical_body)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(principal_oid,repository_id,source_id,capability_kind) DO UPDATE SET
            source_kind=EXCLUDED.source_kind,mode=EXCLUDED.mode,trust_config_digest=EXCLUDED.trust_config_digest,
            binding_digest=EXCLUDED.binding_digest,enabled=EXCLUDED.enabled,valid_until=EXCLUDED.valid_until,
            max_age_seconds=EXCLUDED.max_age_seconds,canonical_body=EXCLUDED.canonical_body""",
            (principal, login, repository_id, source_id, capability_kind, source_kind, mode,
             trust_config_digest, digest, enabled, _instant(expires), max_age_seconds, canonical_m7_bytes(body).decode("utf-8")))


if __name__ == "__main__":
    raise SystemExit(main())
