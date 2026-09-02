from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib import resources
import re
from typing import Iterable


MIGRATION_NAME = re.compile(r"^(\d{3})_([a-z0-9_]+)\.sql$")
ADVISORY_LOCK_KEY = 6_164_374_679_002_001
CORE_FACTORY_GROUP_ROLES = (
    "factory_migrator",
    "factory_runtime",
    "factory_audit_reader",
)
FACTORY_GROUP_ROLES = CORE_FACTORY_GROUP_ROLES + ("factory_artifact_attestor",)
SAFE_GROUP_ATTRIBUTES = (False, False, False, False, False, False, False)
SAFE_LOGIN_ATTRIBUTES = (True, False, False, False, False, False, False)


class MigrationError(RuntimeError):
    pass


class RoleSafetyError(MigrationError):
    pass


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sha256: str
    sql: str


@dataclass(frozen=True)
class AppliedMigration:
    version: int
    name: str
    sha256: str


def discover_migrations() -> tuple[Migration, ...]:
    found: list[Migration] = []
    root = resources.files("adaptive_factory.resources")
    for item in root.iterdir():
        match = MIGRATION_NAME.fullmatch(item.name)
        if not match:
            continue
        raw = item.read_bytes()
        try:
            sql = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MigrationError(f"migration is not UTF-8: {item.name}") from exc
        found.append(Migration(int(match.group(1)), item.name, hashlib.sha256(raw).hexdigest(), sql))
    found.sort(key=lambda migration: migration.version)
    if [item.version for item in found] != list(range(1, len(found) + 1)):
        raise MigrationError("migration versions must be contiguous from 001")
    if len({item.name for item in found}) != len(found):
        raise MigrationError("migration names must be unique")
    return tuple(found)


def plan_migrations(available: Iterable[Migration], applied: Iterable[AppliedMigration]) -> tuple[Migration, ...]:
    available = tuple(available)
    applied = tuple(applied)
    if [item.version for item in applied] != list(range(1, len(applied) + 1)):
        raise MigrationError("applied migration history is non-contiguous")
    if len(applied) > len(available):
        raise MigrationError("applied migration is missing from package")
    for recorded, packaged in zip(applied, available):
        if (recorded.version, recorded.name, recorded.sha256) != (packaged.version, packaged.name, packaged.sha256):
            raise MigrationError(f"migration drift at version {recorded.version}")
    return available[len(applied) :]


def validate_factory_role_boundary(
    cursor,
    *,
    expected_runtime_login: str | None,
    allow_missing_groups: bool,
    require_runtime_membership: bool,
    expected_artifact_attestor_login: str | None = None,
    require_artifact_attestor_membership: bool = False,
    required_group_roles: tuple[str, ...] = (),
) -> None:
    cursor.execute(
        """SELECT rolname,rolcanlogin,rolinherit,rolsuper,rolcreaterole,rolcreatedb,
        rolreplication,rolbypassrls FROM pg_roles WHERE rolname=ANY(%s)""",
        (list(FACTORY_GROUP_ROLES),),
    )
    group_roles = {row[0]: row[1:] for row in cursor.fetchall()}
    required_roles = set(required_group_roles)
    if not allow_missing_groups:
        required_roles = set(FACTORY_GROUP_ROLES)
    if not required_roles.issubset(group_roles):
        raise RoleSafetyError("factory group role boundary is incomplete")
    if any(attributes != SAFE_GROUP_ATTRIBUTES for attributes in group_roles.values()):
        raise RoleSafetyError("factory group role has unsafe attributes")

    expected_logins = {
        "factory_runtime": expected_runtime_login,
        "factory_artifact_attestor": expected_artifact_attestor_login,
    }
    bounded_logins = [login for login in expected_logins.values() if login is not None]
    if len(set(bounded_logins)) != len(bounded_logins):
        raise RoleSafetyError("factory service logins must be distinct")
    login_exists: dict[str, bool] = {}
    for role, login in expected_logins.items():
        if login is None:
            login_exists[role] = False
            continue
        cursor.execute(
            """SELECT rolcanlogin,rolinherit,rolsuper,rolcreaterole,rolcreatedb,
            rolreplication,rolbypassrls FROM pg_roles WHERE rolname=%s""",
            (login,),
        )
        login_attributes = cursor.fetchone()
        login_exists[role] = login_attributes is not None
        if login_exists[role] and login_attributes != SAFE_LOGIN_ATTRIBUTES:
            raise RoleSafetyError("factory service login has unsafe attributes")

    cursor.execute(
        """SELECT parent.rolname,member.rolname,membership.admin_option,
        COALESCE((to_jsonb(membership)->>'inherit_option')::boolean,false),
        COALESCE((to_jsonb(membership)->>'set_option')::boolean,true)
        FROM pg_auth_members membership
        JOIN pg_roles parent ON parent.oid=membership.roleid
        JOIN pg_roles member ON member.oid=membership.member
        WHERE parent.rolname=ANY(%s) OR member.rolname=ANY(%s)
        OR member.rolname=ANY(%s::text[])""",
        (list(FACTORY_GROUP_ROLES), list(FACTORY_GROUP_ROLES), bounded_logins),
    )
    memberships: set[tuple[str, str]] = set()
    for parent, member, admin_option, inherit_option, set_option in cursor.fetchall():
        safe_membership = (
            expected_logins.get(parent) is not None
            and member == expected_logins[parent]
            and (admin_option, inherit_option, set_option) == (False, False, True)
        )
        if not safe_membership:
            raise RoleSafetyError("factory role membership boundary is unsafe")
        memberships.add((parent, member))
    if require_runtime_membership and (
        not login_exists["factory_runtime"]
        or ("factory_runtime", expected_runtime_login) not in memberships
    ):
        raise RoleSafetyError("factory service login membership is incomplete")
    if require_artifact_attestor_membership and (
        not login_exists["factory_artifact_attestor"]
        or (
            "factory_artifact_attestor",
            expected_artifact_attestor_login,
        ) not in memberships
    ):
        raise RoleSafetyError("factory artifact attestor login membership is incomplete")


class PostgresMigrator:
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise MigrationError("database URL is required")
        self._database_url = database_url

    def status(self) -> tuple[AppliedMigration, ...]:
        import psycopg

        with psycopg.connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT to_regclass('factory.schema_migrations')")
                if cursor.fetchone()[0] is None:
                    return ()
                cursor.execute("SELECT version, name, sha256 FROM factory.schema_migrations ORDER BY version")
                return tuple(AppliedMigration(*row) for row in cursor.fetchall())

    def apply(
        self,
        *,
        expected_runtime_login: str | None = None,
        expected_artifact_attestor_login: str | None = None,
    ) -> tuple[Migration, ...]:
        import psycopg

        available = discover_migrations()
        applied_now: list[Migration] = []
        with psycopg.connect(self._database_url) as connection:
            with connection.transaction(), connection.cursor() as cursor:
                cursor.execute("SET LOCAL lock_timeout = '5s'")
                cursor.execute("SET LOCAL statement_timeout = '5s'")
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", (ADVISORY_LOCK_KEY,))
                validate_factory_role_boundary(
                    cursor,
                    expected_runtime_login=expected_runtime_login,
                    expected_artifact_attestor_login=expected_artifact_attestor_login,
                    allow_missing_groups=True,
                    require_runtime_membership=False,
                )
                cursor.execute("CREATE SCHEMA IF NOT EXISTS factory")
                cursor.execute("""CREATE TABLE IF NOT EXISTS factory.schema_migrations (
                    version integer PRIMARY KEY, name text UNIQUE NOT NULL,
                    sha256 char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
                    applied_at timestamptz NOT NULL DEFAULT now())""")
                cursor.execute("SELECT version, name, sha256 FROM factory.schema_migrations ORDER BY version")
                pending = plan_migrations(available, (AppliedMigration(*row) for row in cursor.fetchall()))
                for migration in pending:
                    cursor.execute(migration.sql)
                    if migration.version == 1:
                        validate_factory_role_boundary(
                            cursor,
                            expected_runtime_login=expected_runtime_login,
                            expected_artifact_attestor_login=expected_artifact_attestor_login,
                            allow_missing_groups=True,
                            require_runtime_membership=False,
                            required_group_roles=CORE_FACTORY_GROUP_ROLES,
                        )
                    cursor.execute(
                        "INSERT INTO factory.schema_migrations(version,name,sha256) VALUES (%s,%s,%s)",
                        (migration.version, migration.name, migration.sha256),
                    )
                    applied_now.append(migration)
                validate_factory_role_boundary(
                    cursor,
                    expected_runtime_login=expected_runtime_login,
                    expected_artifact_attestor_login=expected_artifact_attestor_login,
                    allow_missing_groups=False,
                    require_runtime_membership=False,
                )
        return tuple(applied_now)
