from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterator
from urllib.parse import parse_qsl, unquote, urlsplit

from .models import canonical_json, parse_datetime, utc_now


class BackupError(RuntimeError):
    pass


Runner = Callable[[list[str], dict[str, str]], object]
_ALLOWED_LIBPQ_QUERY = {
    'sslmode',
    'sslcert',
    'sslkey',
    'sslrootcert',
    'sslcrl',
    'connect_timeout',
    'application_name',
    'target_session_attrs',
    'options',
}


@dataclass(frozen=True)
class BackupResult:
    dump_path: Path
    manifest_path: Path
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class BackupRecord:
    dump_path: Path
    manifest_path: Path
    created_at: datetime


def create_backup(
    database_url: str,
    output_directory: Path,
    *,
    database_label: str,
    now: datetime | None = None,
    runner: Runner | None = None,
) -> BackupResult:
    label = database_label.strip()
    if not label or any(character in label for character in '\r\n\0'):
        raise BackupError('database_label must be a non-empty single-line value')
    current = (now or utc_now()).astimezone(timezone.utc)
    root = output_directory.resolve()
    root.mkdir(parents=True, exist_ok=True)
    timestamp = current.strftime('%Y%m%dT%H%M%SZ')
    dump_path = root / f'adaptive-trust-ci-{timestamp}.dump'
    manifest_path = root / f'adaptive-trust-ci-{timestamp}.manifest.json'
    if dump_path.exists() or manifest_path.exists():
        raise BackupError(f'backup target already exists for timestamp {timestamp}')

    descriptor, temporary_name = tempfile.mkstemp(prefix='.trust-ci-backup-', suffix='.dump.tmp', dir=root)
    os.close(descriptor)
    temporary_dump = Path(temporary_name)
    try:
        with _service_environment(database_url) as environment:
            result = (runner or _run)(
                [
                    'pg_dump',
                    '--format=custom',
                    '--no-owner',
                    '--compress=9',
                    '--file',
                    str(temporary_dump),
                ],
                environment,
            )
        _require_success(result, 'pg_dump')
        if not temporary_dump.is_file() or temporary_dump.stat().st_size <= 0:
            raise BackupError('pg_dump produced no backup data')
        _fsync_file(temporary_dump)
        digest = _sha256(temporary_dump)
        size = temporary_dump.stat().st_size
        os.chmod(temporary_dump, 0o600)
        os.replace(temporary_dump, dump_path)
        _fsync_directory(root)

        manifest = {
            'schema_version': 1,
            'created_at': current.isoformat(),
            'database_label': label,
            'dump_file': dump_path.name,
            'format': 'custom',
            'size_bytes': size,
            'sha256': digest,
        }
        _atomic_private_write(manifest_path, canonical_json(manifest) + b'\n')
        return BackupResult(dump_path=dump_path, manifest_path=manifest_path, sha256=digest, size_bytes=size)
    except BaseException:
        temporary_dump.unlink(missing_ok=True)
        dump_path.unlink(missing_ok=True)
        manifest_path.unlink(missing_ok=True)
        raise


def verify_backup(dump_path: Path, manifest_path: Path) -> dict[str, object]:
    try:
        data = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupError(f'cannot read backup manifest: {exc}') from exc
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise BackupError('unsupported backup manifest')
    if data.get('format') != 'custom':
        raise BackupError('backup manifest format must be custom')
    if data.get('dump_file') != dump_path.name:
        raise BackupError('backup manifest dump filename mismatch')
    try:
        parse_datetime(str(data['created_at']))
        expected_size = int(data['size_bytes'])
        expected_digest = str(data['sha256'])
    except (KeyError, TypeError, ValueError) as exc:
        raise BackupError('backup manifest is incomplete') from exc
    if not dump_path.is_file():
        raise BackupError(f'backup dump is missing: {dump_path}')
    actual_size = dump_path.stat().st_size
    if actual_size != expected_size:
        raise BackupError(f'backup size mismatch: expected={expected_size} actual={actual_size}')
    actual_digest = _sha256(dump_path)
    if actual_digest != expected_digest:
        raise BackupError(f'backup digest mismatch: expected={expected_digest} actual={actual_digest}')
    return {
        'status': 'verified',
        'dump_path': str(dump_path),
        'manifest_path': str(manifest_path),
        'sha256': actual_digest,
        'size_bytes': actual_size,
        'database_label': data.get('database_label'),
    }


def prune_backups(
    directory: Path,
    *,
    keep_last: int,
    max_age_days: int,
    now: datetime | None = None,
) -> dict[str, object]:
    if isinstance(keep_last, bool) or keep_last < 1:
        raise BackupError('keep_last must be at least 1')
    if isinstance(max_age_days, bool) or max_age_days < 1:
        raise BackupError('max_age_days must be at least 1')
    root = directory.resolve()
    if not root.is_dir():
        raise BackupError(f'backup directory does not exist: {root}')
    records = _backup_records(root)
    current = (now or utc_now()).astimezone(timezone.utc)
    cutoff = current - timedelta(days=max_age_days)
    protected = set(record.manifest_path for record in records[:keep_last])
    candidates = [
        record
        for record in records
        if record.manifest_path not in protected and record.created_at < cutoff
    ]
    failures: list[str] = []
    for record in candidates:
        try:
            verify_backup(record.dump_path, record.manifest_path)
        except BackupError as exc:
            failures.append(f'{record.manifest_path.name}: {exc}')
    if failures:
        raise BackupError('retention verification failed; no files deleted: ' + '; '.join(failures))
    removed: list[str] = []
    for record in candidates:
        record.dump_path.unlink()
        record.manifest_path.unlink()
        removed.append(record.dump_path.name)
    if removed:
        _fsync_directory(root)
    retained = [record.dump_path.name for record in records if record not in candidates]
    return {
        'status': 'pruned',
        'removed': removed,
        'retained': retained,
        'keep_last': keep_last,
        'max_age_days': max_age_days,
    }


def restore_drill(
    target_database_url: str,
    dump_path: Path,
    manifest_path: Path,
    *,
    confirm_disposable: bool,
    runner: Runner | None = None,
) -> dict[str, object]:
    if not confirm_disposable:
        raise BackupError('restore drill requires --confirm-disposable for the target database')
    verified = verify_backup(dump_path, manifest_path)
    execute = runner or _run
    with _service_environment(target_database_url) as environment:
        restored = execute(
            [
                'pg_restore',
                '--clean',
                '--if-exists',
                '--no-owner',
                '--exit-on-error',
                str(dump_path),
            ],
            environment,
        )
        _require_success(restored, 'pg_restore')
        checked = execute(
            [
                'psql',
                '--no-psqlrc',
                '--set',
                'ON_ERROR_STOP=1',
                '--tuples-only',
                '--command',
                (
                    "SELECT CASE WHEN to_regclass('public.trust_ci_jobs') IS NOT NULL "
                    "AND to_regclass('public.trust_ci_schema_migrations') IS NOT NULL "
                    "THEN 'ok' ELSE 'missing' END;"
                ),
            ],
            environment,
        )
        _require_success(checked, 'restore verification')
        stdout = str(getattr(checked, 'stdout', '') or '')
        if 'ok' not in stdout and runner is None:
            raise BackupError('restored database is missing required Trust CI tables')
    return {
        **verified,
        'status': 'restored-and-verified',
    }


def _backup_records(root: Path) -> list[BackupRecord]:
    manifests = sorted(root.glob('adaptive-trust-ci-*.manifest.json'))
    records: list[BackupRecord] = []
    referenced_dumps: set[Path] = set()
    for manifest_path in manifests:
        try:
            data = json.loads(manifest_path.read_text(encoding='utf-8'))
            created = parse_datetime(str(data['created_at']))
            dump_name = str(data['dump_file'])
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
            raise BackupError(f'invalid backup manifest {manifest_path.name}: {exc}') from exc
        if Path(dump_name).name != dump_name:
            raise BackupError(f'backup manifest references a non-local dump: {manifest_path.name}')
        dump_path = root / dump_name
        referenced_dumps.add(dump_path)
        records.append(BackupRecord(dump_path=dump_path, manifest_path=manifest_path, created_at=created))
    orphan_dumps = sorted(set(root.glob('adaptive-trust-ci-*.dump')) - referenced_dumps)
    if orphan_dumps:
        raise BackupError('orphan backup dumps require investigation: ' + ', '.join(path.name for path in orphan_dumps))
    records.sort(key=lambda item: (item.created_at, item.dump_path.name), reverse=True)
    return records


@contextmanager
def _service_environment(database_url: str) -> Iterator[dict[str, str]]:
    parameters = _parse_database_url(database_url)
    with tempfile.TemporaryDirectory(prefix='adaptive-trust-ci-libpq-') as directory:
        service_path = Path(directory) / 'pg_service.conf'
        lines = ['[adaptive_trust_ci]']
        for key, value in parameters:
            lines.append(f'{key}={_service_value(value)}')
        service_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        os.chmod(service_path, 0o600)
        environment = os.environ.copy()
        environment.update(
            {
                'PGSERVICEFILE': str(service_path),
                'PGSERVICE': 'adaptive_trust_ci',
                'PGCONNECT_TIMEOUT': parameters_dict(parameters).get('connect_timeout', '10'),
            }
        )
        yield environment


def _parse_database_url(database_url: str) -> list[tuple[str, str]]:
    parsed = urlsplit(database_url)
    if parsed.scheme not in {'postgresql', 'postgres'}:
        raise BackupError('database URL must use postgresql:// or postgres://')
    if not parsed.hostname or not parsed.path or parsed.path == '/':
        raise BackupError('database URL must include host and database name')
    try:
        port = parsed.port or 5432
    except ValueError as exc:
        raise BackupError('database URL contains an invalid port') from exc
    parameters: list[tuple[str, str]] = [
        ('host', parsed.hostname),
        ('port', str(port)),
        ('dbname', unquote(parsed.path.lstrip('/'))),
    ]
    if parsed.username is not None:
        parameters.append(('user', unquote(parsed.username)))
    if parsed.password is not None:
        parameters.append(('password', unquote(parsed.password)))
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key not in _ALLOWED_LIBPQ_QUERY:
            raise BackupError(f'unsupported libpq URL parameter: {key}')
        parameters.append((key, value))
    return parameters


def parameters_dict(items: list[tuple[str, str]]) -> dict[str, str]:
    return {key: value for key, value in items}


def _service_value(value: str) -> str:
    if any(character in value for character in '\r\n\0'):
        raise BackupError('database URL contains a control character')
    return value.replace('\\', '\\\\')


def _run(argv: list[str], env: dict[str, str]):
    try:
        return subprocess.run(
            argv,
            env=env,
            text=True,
            capture_output=True,
            timeout=7200,
            check=False,
        )
    except FileNotFoundError as exc:
        raise BackupError(f'required PostgreSQL utility is missing: {argv[0]}') from exc
    except subprocess.TimeoutExpired as exc:
        raise BackupError(f'{argv[0]} timed out') from exc


def _require_success(result: object, operation: str) -> None:
    code = int(getattr(result, 'returncode', 1))
    if code == 0:
        return
    stderr = str(getattr(result, 'stderr', '') or '').strip()
    stdout = str(getattr(result, 'stdout', '') or '').strip()
    detail = stderr or stdout or f'exit={code}'
    raise BackupError(f'{operation} failed: {detail[-4000:]}')


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open('rb') as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_private_write(path: Path, payload: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)
