from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import stat
import threading
from typing import Iterator

from .contracts import HEX64, canonical_json
from .landing_contracts import (
    LandingContractError,
    LandingInputV1,
    SiteArtifactV1,
    strict_json_object,
)
from .landing_service import (
    LANDING_STATES,
    LandingJobRecord,
    LandingServiceError,
    _validate_transition,
)


SCHEMA_VERSION = 1
APPLICATION_ID = 0x4C354C35
MAX_RECOVERY_BATCH = 100
_SCHEMA = """
CREATE TABLE IF NOT EXISTS landing_jobs (
    tenant_id TEXT NOT NULL,
    repository_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    source_json BLOB NOT NULL,
    state TEXT NOT NULL,
    artifact_json BLOB,
    provider_evidence_digest TEXT,
    reason_code TEXT,
    revision INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, repository_id, job_id)
) STRICT;
CREATE TABLE IF NOT EXISTS landing_commands (
    tenant_id TEXT NOT NULL,
    repository_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    action TEXT NOT NULL,
    command_key TEXT NOT NULL,
    request_digest TEXT NOT NULL,
    input_digest TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, repository_id, job_id, action, command_key),
    FOREIGN KEY (tenant_id, repository_id, job_id)
      REFERENCES landing_jobs (tenant_id, repository_id, job_id)
) STRICT;
"""


class SQLiteLandingJobStore:
    """Private, single-writer landing state for one local operator."""

    def __init__(
        self,
        root: Path,
        *,
        repository_root: Path,
        recovery_limit: int = MAX_RECOVERY_BATCH,
        busy_timeout_ms: int = 5_000,
        clock=None,
    ) -> None:
        if type(recovery_limit) is not int or not 0 <= recovery_limit <= MAX_RECOVERY_BATCH:
            raise LandingServiceError("recovery_limit", 500, "landing recovery limit invalid")
        if type(busy_timeout_ms) is not int or not 1 <= busy_timeout_ms <= 30_000:
            raise LandingServiceError("store_timeout", 500, "landing store timeout invalid")
        self._root = _private_root(Path(root), Path(repository_root))
        self._database_path = self._root / "landing.sqlite3"
        _validate_database_path(self._database_path)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = threading.RLock()
        self._closed = False
        previous = os.umask(0o077)
        try:
            self._connection = sqlite3.connect(
                self._database_path,
                timeout=busy_timeout_ms / 1_000,
                isolation_level=None,
                check_same_thread=False,
            )
        except sqlite3.Error as exc:
            raise LandingServiceError("store_open", 500, "landing store unavailable") from exc
        finally:
            os.umask(previous)
        os.chmod(self._database_path, 0o600)
        try:
            self._configure(busy_timeout_ms)
            self._initialize_schema()
            self._recover_interrupted(recovery_limit)
        except Exception:
            self._connection.close()
            self._closed = True
            raise

    @property
    def database_path(self) -> Path:
        return self._database_path

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._connection.execute("PRAGMA wal_checkpoint(PASSIVE)")
            self._connection.close()
            self._closed = True

    def get(
        self, tenant_id: str, repository_id: str, job_id: str
    ) -> LandingJobRecord:
        record = self.find(tenant_id, repository_id, job_id)
        if record is None:
            raise LandingServiceError("not_found", 404, "landing job not found")
        return record

    def find(
        self, tenant_id: str, repository_id: str, job_id: str
    ) -> LandingJobRecord | None:
        with self._lock:
            self._ensure_open()
            row = self._connection.execute(
                """SELECT source_json, state, artifact_json,
                          provider_evidence_digest, reason_code, revision
                     FROM landing_jobs
                    WHERE tenant_id = ? AND repository_id = ? AND job_id = ?""",
                (tenant_id, repository_id, job_id),
            ).fetchone()
        return _decode_record(row) if row is not None else None

    def create_or_replay(
        self,
        record: LandingJobRecord,
        *,
        command_key: str,
        request_digest: str,
    ) -> tuple[LandingJobRecord, bool]:
        _validate_record(record)
        _validate_command(command_key, request_digest)
        source = record.source
        identity = (source.tenant_id, source.repository_id, source.job_id)
        with self._transaction():
            command = self._connection.execute(
                """SELECT request_digest, input_digest FROM landing_commands
                    WHERE tenant_id = ? AND repository_id = ? AND job_id = ?
                      AND action = 'submit' AND command_key = ?""",
                (*identity, command_key),
            ).fetchone()
            current = self._select_record(identity)
            if command is not None:
                if command != (request_digest, source.input_digest) or current is None:
                    raise _conflict()
                return current, False
            if current is not None:
                if current.source != source:
                    raise _conflict()
                created = False
            else:
                self._insert_record(record)
                current = record
                created = True
            self._connection.execute(
                """INSERT INTO landing_commands
                   (tenant_id, repository_id, job_id, action, command_key,
                    request_digest, input_digest, created_at)
                   VALUES (?, ?, ?, 'submit', ?, ?, ?, ?)""",
                (
                    *identity,
                    command_key,
                    request_digest,
                    source.input_digest,
                    self._timestamp(),
                ),
            )
            return current, created

    def put(self, record: LandingJobRecord) -> LandingJobRecord:
        _validate_record(record)
        identity = (
            record.source.tenant_id,
            record.source.repository_id,
            record.source.job_id,
        )
        with self._transaction():
            current = self._select_record(identity)
            if current is None:
                raise LandingServiceError("not_found", 404, "landing job not found")
            if current.source != record.source or current.revision != record.revision:
                raise LandingServiceError("stale_job", 409, "landing job is stale")
            _validate_transition(current.state, record.state)
            stored = replace(record, revision=record.revision + 1)
            values = _record_values(stored)
            cursor = self._connection.execute(
                """UPDATE landing_jobs
                      SET state = ?, artifact_json = ?, provider_evidence_digest = ?,
                          reason_code = ?, revision = ?, updated_at = ?
                    WHERE tenant_id = ? AND repository_id = ? AND job_id = ?
                      AND revision = ?""",
                (
                    values[1],
                    values[2],
                    values[3],
                    values[4],
                    values[5],
                    self._timestamp(),
                    *identity,
                    record.revision,
                ),
            )
            if cursor.rowcount != 1:
                raise LandingServiceError("stale_job", 409, "landing job is stale")
            return stored

    def cancel_or_replay(
        self,
        record: LandingJobRecord,
        *,
        command_key: str,
        request_digest: str,
    ) -> LandingJobRecord:
        _validate_record(record)
        _validate_command(command_key, request_digest)
        source = record.source
        identity = (source.tenant_id, source.repository_id, source.job_id)
        with self._transaction():
            current = self._select_record(identity)
            if current is None:
                raise LandingServiceError("not_found", 404, "landing job not found")
            command = self._connection.execute(
                """SELECT request_digest, input_digest FROM landing_commands
                    WHERE tenant_id = ? AND repository_id = ? AND job_id = ?
                      AND action = 'cancel' AND command_key = ?""",
                (*identity, command_key),
            ).fetchone()
            if command is not None:
                if command != (request_digest, source.input_digest):
                    raise _conflict()
                return current
            _validate_transition(current.state, "cancelled")
            cancelled = replace(
                current,
                state="cancelled",
                artifact=None,
                reason_code="cancelled",
                revision=current.revision + 1,
            )
            values = _record_values(cancelled)
            self._connection.execute(
                """UPDATE landing_jobs
                      SET state = ?, artifact_json = ?, provider_evidence_digest = ?,
                          reason_code = ?, revision = ?, updated_at = ?
                    WHERE tenant_id = ? AND repository_id = ? AND job_id = ?""",
                (
                    values[1],
                    values[2],
                    values[3],
                    values[4],
                    values[5],
                    self._timestamp(),
                    *identity,
                ),
            )
            self._connection.execute(
                """INSERT INTO landing_commands
                   (tenant_id, repository_id, job_id, action, command_key,
                    request_digest, input_digest, created_at)
                   VALUES (?, ?, ?, 'cancel', ?, ?, ?, ?)""",
                (
                    *identity,
                    command_key,
                    request_digest,
                    source.input_digest,
                    self._timestamp(),
                ),
            )
            return cancelled

    def _configure(self, busy_timeout_ms: int) -> None:
        connection = self._connection
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute(f"PRAGMA busy_timeout = {busy_timeout_ms}")
        mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
        if str(mode).casefold() != "wal":
            raise LandingServiceError("store_wal", 500, "landing WAL unavailable")
        connection.execute("PRAGMA synchronous = FULL")
        if connection.execute("PRAGMA synchronous").fetchone()[0] != 2:
            raise LandingServiceError("store_sync", 500, "landing sync unavailable")
        if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise LandingServiceError("store_foreign_keys", 500, "landing FK unavailable")

    def _initialize_schema(self) -> None:
        version = self._connection.execute("PRAGMA user_version").fetchone()[0]
        application = self._connection.execute("PRAGMA application_id").fetchone()[0]
        if version not in {0, SCHEMA_VERSION} or application not in {0, APPLICATION_ID}:
            raise LandingServiceError("store_schema", 500, "landing store schema unsupported")
        if version == 0:
            with self._transaction():
                for statement in _SCHEMA.split(";"):
                    if statement.strip():
                        self._connection.execute(statement)
                self._connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
                self._connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        result = self._connection.execute("PRAGMA quick_check").fetchone()[0]
        if result != "ok":
            raise LandingServiceError("store_integrity", 500, "landing store corrupt")

    def _recover_interrupted(self, limit: int) -> None:
        if limit == 0:
            return
        with self._transaction():
            rows = self._connection.execute(
                """SELECT tenant_id, repository_id, job_id, state, revision
                     FROM landing_jobs
                    WHERE state IN ('accepted', 'normalizing', 'generating', 'evaluating')
                    ORDER BY tenant_id, repository_id, job_id
                    LIMIT ?""",
                (limit,),
            ).fetchall()
            for tenant_id, repository_id, job_id, state, revision in rows:
                if state == "accepted":
                    reason = "input_unavailable_after_restart"
                elif state == "normalizing":
                    reason = "provider_outcome_ambiguous"
                else:
                    reason = "local_run_interrupted"
                self._connection.execute(
                    """UPDATE landing_jobs
                          SET state = 'needs_human', reason_code = ?,
                              revision = ?, updated_at = ?
                        WHERE tenant_id = ? AND repository_id = ? AND job_id = ?
                          AND revision = ?""",
                    (
                        reason,
                        revision + 1,
                        self._timestamp(),
                        tenant_id,
                        repository_id,
                        job_id,
                        revision,
                    ),
                )

    def _select_record(self, identity: tuple[str, str, str]) -> LandingJobRecord | None:
        row = self._connection.execute(
            """SELECT source_json, state, artifact_json,
                      provider_evidence_digest, reason_code, revision
                 FROM landing_jobs
                WHERE tenant_id = ? AND repository_id = ? AND job_id = ?""",
            identity,
        ).fetchone()
        return _decode_record(row) if row is not None else None

    def _insert_record(self, record: LandingJobRecord) -> None:
        values = _record_values(record)
        self._connection.execute(
            """INSERT INTO landing_jobs
               (tenant_id, repository_id, job_id, source_json, state,
                artifact_json, provider_evidence_digest, reason_code, revision, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.source.tenant_id,
                record.source.repository_id,
                record.source.job_id,
                *values,
                self._timestamp(),
            ),
        )

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        with self._lock:
            self._ensure_open()
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                yield
                self._connection.execute("COMMIT")
            except Exception:
                self._connection.execute("ROLLBACK")
                raise

    def _timestamp(self) -> str:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise LandingServiceError("clock", 500, "landing clock unavailable")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def _ensure_open(self) -> None:
        if self._closed:
            raise LandingServiceError("store_closed", 500, "landing store closed")


def _private_root(root: Path, repository_root: Path) -> Path:
    if not root.is_absolute():
        raise LandingServiceError("store_path", 500, "landing store path must be absolute")
    repository = repository_root.resolve(strict=True)
    lexical_root = Path(os.path.abspath(root))
    candidate = root.resolve(strict=False)
    if lexical_root != candidate:
        raise LandingServiceError("store_symlink", 500, "landing store path is a link")
    try:
        candidate.relative_to(repository)
    except ValueError:
        pass
    else:
        raise LandingServiceError(
            "store_inside_repository", 500, "landing store must be outside repository"
        )
    previous = os.umask(0o077)
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
    finally:
        os.umask(previous)
    metadata = os.lstat(root)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
    ):
        raise LandingServiceError("store_owner", 500, "landing store ownership invalid")
    os.chmod(root, 0o700)
    return root.resolve(strict=True)


def _validate_database_path(path: Path) -> None:
    if not path.exists():
        return
    metadata = os.lstat(path)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        raise LandingServiceError("store_file", 500, "landing store file invalid")


def _record_values(
    record: LandingJobRecord,
) -> tuple[bytes, str, bytes | None, str | None, str | None, int]:
    return (
        canonical_json(record.source.to_dict()),
        record.state,
        canonical_json(record.artifact.to_dict()) if record.artifact else None,
        record.provider_evidence_digest,
        record.reason_code,
        record.revision,
    )


def _decode_record(row) -> LandingJobRecord:
    source_json, state, artifact_json, evidence_digest, reason_code, revision = row
    try:
        source = LandingInputV1.from_dict(strict_json_object(source_json))
        artifact = (
            SiteArtifactV1.from_dict(strict_json_object(artifact_json))
            if artifact_json is not None
            else None
        )
    except (LandingContractError, ValueError, TypeError) as exc:
        raise LandingServiceError("store_record", 500, "landing store record invalid") from exc
    record = LandingJobRecord(source, state, artifact, evidence_digest, reason_code, revision)
    _validate_record(record)
    return record


def _validate_record(record: LandingJobRecord) -> None:
    if not isinstance(record, LandingJobRecord) or record.state not in LANDING_STATES:
        raise LandingServiceError("state", 500, "landing state invalid")
    if (
        record.provider_evidence_digest is not None
        and not HEX64.fullmatch(record.provider_evidence_digest)
    ):
        raise LandingServiceError("provider_binding", 500, "landing evidence invalid")
    if type(record.revision) is not int or record.revision < 0:
        raise LandingServiceError("revision", 500, "landing revision invalid")
    if record.state == "artifact_ready" and record.artifact is None:
        raise LandingServiceError("artifact_binding", 500, "landing artifact missing")
    if record.state != "artifact_ready" and record.artifact is not None:
        raise LandingServiceError("artifact_binding", 500, "landing artifact not terminal")


def _validate_command(command_key: str, request_digest: str) -> None:
    if (
        not isinstance(command_key, str)
        or not command_key
        or len(command_key.encode("utf-8")) > 128
        or not isinstance(request_digest, str)
        or not HEX64.fullmatch(request_digest)
    ):
        raise LandingServiceError("idempotency", 422, "landing idempotency invalid")


def _conflict() -> LandingServiceError:
    return LandingServiceError("idempotency_conflict", 409, "landing idempotency conflict")
