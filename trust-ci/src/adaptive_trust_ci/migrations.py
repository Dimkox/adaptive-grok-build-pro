from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol


_MIGRATION_RE = re.compile(r'^(?P<version>[0-9]{3})_(?P<name>[a-z0-9_]+)\.sql$')
_ADVISORY_LOCK_ID = 0x41544349  # ASCII ATCI


class MigrationError(RuntimeError):
    pass


class ResourceDirectory(Protocol):
    def iterdir(self) -> Iterable[Any]: ...


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    filename: str
    sql: str
    sha256: str


@dataclass(frozen=True)
class AppliedMigration:
    version: int
    name: str
    sha256: str


@dataclass(frozen=True)
class MigrationPlan:
    applied: tuple[Migration, ...]
    pending: tuple[Migration, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            'applied': [_migration_dict(item) for item in self.applied],
            'pending': [_migration_dict(item) for item in self.pending],
        }


def discover_migrations(root: Path | ResourceDirectory | None = None) -> tuple[Migration, ...]:
    directory = root or files('adaptive_trust_ci.resources')
    discovered: list[Migration] = []
    versions: set[int] = set()
    names: set[str] = set()
    for item in directory.iterdir():
        filename = str(getattr(item, 'name', ''))
        match = _MIGRATION_RE.fullmatch(filename)
        if match is None:
            continue
        version = int(match.group('version'))
        name = match.group('name')
        if version in versions:
            raise MigrationError(f'duplicate migration version: {version:03d}')
        if name in names:
            raise MigrationError(f'duplicate migration name: {name}')
        try:
            raw = item.read_bytes()
        except AttributeError:
            raw = Path(item).read_bytes()
        try:
            sql = raw.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise MigrationError(f'migration is not UTF-8: {filename}') from exc
        discovered.append(
            Migration(
                version=version,
                name=name,
                filename=filename,
                sql=sql,
                sha256=hashlib.sha256(raw).hexdigest(),
            )
        )
        versions.add(version)
        names.add(name)
    discovered.sort(key=lambda item: item.version)
    if not discovered:
        raise MigrationError('no packaged migrations were discovered')
    expected = list(range(1, discovered[-1].version + 1))
    actual = [item.version for item in discovered]
    if actual != expected:
        raise MigrationError(f'migration versions must be contiguous from 001: {actual}')
    return tuple(discovered)


def plan_migrations(
    available: Iterable[Migration],
    applied: Mapping[int, AppliedMigration],
) -> MigrationPlan:
    migrations = tuple(sorted(available, key=lambda item: item.version))
    by_version = {item.version: item for item in migrations}
    for version, record in sorted(applied.items()):
        migration = by_version.get(version)
        if migration is None:
            raise MigrationError(
                f'applied migration {version:03d}_{record.name} is missing from the deployed package'
            )
        if migration.name != record.name:
            raise MigrationError(
                f'migration name drift for {version:03d}: database={record.name} package={migration.name}'
            )
        if migration.sha256 != record.sha256:
            raise MigrationError(
                f'migration checksum drift for {version:03d}_{migration.name}: '
                f'database={record.sha256} package={migration.sha256}'
            )
    applied_migrations = tuple(item for item in migrations if item.version in applied)
    pending = tuple(item for item in migrations if item.version not in applied)
    return MigrationPlan(applied=applied_migrations, pending=pending)


class PostgresMigrator:
    def __init__(self, database_url: str, resource_root: Path | ResourceDirectory | None = None) -> None:
        if not database_url.strip():
            raise ValueError('database_url is required')
        self.database_url = database_url
        self.resource_root = resource_root

    def _connect(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError('psycopg is required for PostgreSQL migrations') from exc
        return psycopg.connect(self.database_url, autocommit=False, row_factory=dict_row)

    def status(self) -> MigrationPlan:
        available = discover_migrations(self.resource_root)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', (_ADVISORY_LOCK_ID,))
            _ensure_registry(cursor)
            applied = _read_applied(cursor)
            plan = plan_migrations(available, applied)
            connection.commit()
            return plan

    def apply(self) -> MigrationPlan:
        available = discover_migrations(self.resource_root)
        with self._connect() as connection, connection.cursor() as cursor:
            try:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', (_ADVISORY_LOCK_ID,))
                _ensure_registry(cursor)
                applied = _read_applied(cursor)
                plan = plan_migrations(available, applied)
                for migration in plan.pending:
                    cursor.execute(migration.sql)
                    cursor.execute(
                        '''
                        INSERT INTO trust_ci_schema_migrations (version, name, sha256)
                        VALUES (%s, %s, %s)
                        ''',
                        (migration.version, migration.name, migration.sha256),
                    )
                connection.commit()
                return MigrationPlan(applied=available, pending=())
            except BaseException:
                connection.rollback()
                raise


def _ensure_registry(cursor) -> None:
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS trust_ci_schema_migrations (
            version integer PRIMARY KEY CHECK (version > 0),
            name text NOT NULL UNIQUE CHECK (name ~ '^[a-z0-9_]+$'),
            sha256 char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
            applied_at timestamptz NOT NULL DEFAULT now()
        )
        '''
    )


def _read_applied(cursor) -> dict[int, AppliedMigration]:
    cursor.execute(
        'SELECT version, name, sha256 FROM trust_ci_schema_migrations ORDER BY version'
    )
    rows = cursor.fetchall()
    return {
        int(row['version']): AppliedMigration(
            version=int(row['version']),
            name=str(row['name']),
            sha256=str(row['sha256']),
        )
        for row in rows
    }


def _migration_dict(item: Migration) -> dict[str, Any]:
    return {
        'version': item.version,
        'name': item.name,
        'filename': item.filename,
        'sha256': item.sha256,
    }
