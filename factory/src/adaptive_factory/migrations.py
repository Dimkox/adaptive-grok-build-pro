from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib import resources
import re
from typing import Iterable


MIGRATION_NAME = re.compile(r"^(\d{3})_([a-z0-9_]+)\.sql$")
ADVISORY_LOCK_KEY = 6_164_374_679_002_001


class MigrationError(RuntimeError):
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
    return available[len(applied):]


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

    def apply(self) -> tuple[Migration, ...]:
        import psycopg
        available = discover_migrations()
        applied_now: list[Migration] = []
        with psycopg.connect(self._database_url) as connection:
            with connection.transaction(), connection.cursor() as cursor:
                cursor.execute("SET LOCAL lock_timeout = '5s'")
                cursor.execute("SET LOCAL statement_timeout = '5s'")
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", (ADVISORY_LOCK_KEY,))
                cursor.execute("CREATE SCHEMA IF NOT EXISTS factory")
                cursor.execute("""CREATE TABLE IF NOT EXISTS factory.schema_migrations (
                    version integer PRIMARY KEY, name text UNIQUE NOT NULL,
                    sha256 char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
                    applied_at timestamptz NOT NULL DEFAULT now())""")
                cursor.execute("SELECT version, name, sha256 FROM factory.schema_migrations ORDER BY version")
                pending = plan_migrations(available, (AppliedMigration(*row) for row in cursor.fetchall()))
                for migration in pending:
                    cursor.execute(migration.sql)
                    cursor.execute("INSERT INTO factory.schema_migrations(version,name,sha256) VALUES (%s,%s,%s)", (migration.version, migration.name, migration.sha256))
                    applied_now.append(migration)
        return tuple(applied_now)
