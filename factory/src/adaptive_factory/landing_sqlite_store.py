from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import re
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
from .landing_artifact import LandingArtifactError
from .landing_artifact_retention import RetainedLandingArtifact
from .landing_observation import LandingProviderObservation
from .landing_service import (
    LANDING_STATES,
    LandingJobRecord,
    LandingServiceError,
    _validate_transition,
)


SCHEMA_VERSION = 3
MIGRATION_002_EXPAND = "ALTER TABLE landing_jobs ADD COLUMN observation_json BLOB"
APPLICATION_ID = 0x4C354C35
MAX_RECOVERY_BATCH = 100
_PROBE_TABLE = """
CREATE TABLE landing_activation_probes (
    probe_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    idempotency_digest TEXT UNIQUE,
    state TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    profile_digest TEXT NOT NULL,
    input_digest TEXT NOT NULL,
    spec_digest TEXT,
    response_digest TEXT,
    usage_input_units INTEGER,
    usage_output_units INTEGER,
    provider_attempts INTEGER NOT NULL,
    elapsed_ms INTEGER,
    request_started_at TEXT NOT NULL,
    completed_at TEXT,
    failure_category TEXT,
    http_status INTEGER,
    PRIMARY KEY (probe_id, revision),
    CHECK (state IN ('pending', 'normalized', 'failed', 'unknown')),
    CHECK (revision >= 1),
    CHECK (provider_attempts IN (0, 1)),
    CHECK (http_status IS NULL OR http_status BETWEEN 100 AND 599)
) STRICT;
"""
_PROBE_TRIGGERS = (
    "CREATE TRIGGER landing_activation_probes_no_update BEFORE UPDATE ON landing_activation_probes "
    "BEGIN SELECT RAISE(ABORT, 'landing activation probes are append-only'); END",
    "CREATE TRIGGER landing_activation_probes_no_delete BEFORE DELETE ON landing_activation_probes "
    "BEGIN SELECT RAISE(ABORT, 'landing activation probes are append-only'); END",
)
_SCHEMA = """
CREATE TABLE IF NOT EXISTS landing_jobs (
    tenant_id TEXT NOT NULL,
    repository_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    source_json BLOB NOT NULL,
    state TEXT NOT NULL,
    artifact_json BLOB,
    sealed_artifact_json BLOB,
    provider_evidence_digest TEXT,
    reason_code TEXT,
    revision INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    observation_json BLOB,
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
_EXPECTED_COLUMNS = {
    "landing_jobs": (
        ("tenant_id", "TEXT", 1, 1),
        ("repository_id", "TEXT", 1, 2),
        ("job_id", "TEXT", 1, 3),
        ("source_json", "BLOB", 1, 0),
        ("state", "TEXT", 1, 0),
        ("artifact_json", "BLOB", 0, 0),
        ("sealed_artifact_json", "BLOB", 0, 0),
        ("provider_evidence_digest", "TEXT", 0, 0),
        ("reason_code", "TEXT", 0, 0),
        ("revision", "INTEGER", 1, 0),
        ("updated_at", "TEXT", 1, 0),
        ("observation_json", "BLOB", 0, 0),
    ),
    "landing_commands": (
        ("tenant_id", "TEXT", 1, 1),
        ("repository_id", "TEXT", 1, 2),
        ("job_id", "TEXT", 1, 3),
        ("action", "TEXT", 1, 4),
        ("command_key", "TEXT", 1, 5),
        ("request_digest", "TEXT", 1, 0),
        ("input_digest", "TEXT", 1, 0),
        ("created_at", "TEXT", 1, 0),
    ),
    "landing_activation_probes": (
        ("probe_id", "TEXT", 1, 1),
        ("revision", "INTEGER", 1, 2),
        ("idempotency_digest", "TEXT", 0, 0),
        ("state", "TEXT", 1, 0),
        ("profile_id", "TEXT", 1, 0),
        ("provider_id", "TEXT", 1, 0),
        ("model_id", "TEXT", 1, 0),
        ("profile_digest", "TEXT", 1, 0),
        ("input_digest", "TEXT", 1, 0),
        ("spec_digest", "TEXT", 0, 0),
        ("response_digest", "TEXT", 0, 0),
        ("usage_input_units", "INTEGER", 0, 0),
        ("usage_output_units", "INTEGER", 0, 0),
        ("provider_attempts", "INTEGER", 1, 0),
        ("elapsed_ms", "INTEGER", 0, 0),
        ("request_started_at", "TEXT", 1, 0),
        ("completed_at", "TEXT", 0, 0),
        ("failure_category", "TEXT", 0, 0),
        ("http_status", "INTEGER", 0, 0),
    ),
}
_EXPECTED_FOREIGN_KEY = (
    (0, "landing_jobs", "tenant_id", "tenant_id", "NO ACTION", "NO ACTION", "NONE"),
    (1, "landing_jobs", "repository_id", "repository_id", "NO ACTION", "NO ACTION", "NONE"),
    (2, "landing_jobs", "job_id", "job_id", "NO ACTION", "NO ACTION", "NONE"),
)
_PROBE_VIEW_KEYS = (
    "probe_id", "revision", "state", "profile_id", "provider_id", "model_id",
    "profile_digest", "input_digest", "spec_digest", "response_digest",
    "usage_input_units", "usage_output_units", "provider_attempts", "elapsed_ms",
    "request_started_at", "completed_at", "failure_category", "http_status",
)
_PROBE_FAILURE_CATEGORIES = frozenset({
    "accounting", "authentication", "deadline", "permission", "policy", "protocol",
    "rate_limit", "transport", "unavailable", "outcome_ambiguous",
})


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
        self._writer_descriptor = _acquire_writer(self._root)
        previous = os.umask(0o077)
        try:
            self._connection = sqlite3.connect(
                self._database_path,
                timeout=busy_timeout_ms / 1_000,
                isolation_level=None,
                check_same_thread=False,
            )
        except BaseException as exc:
            os.close(self._writer_descriptor)
            self._closed = True
            if isinstance(exc, sqlite3.Error):
                raise LandingServiceError("store_open", 500, "landing store unavailable") from exc
            raise
        finally:
            os.umask(previous)
        try:
            os.chmod(self._database_path, 0o600)
            self._configure(busy_timeout_ms)
            self._initialize_schema()
            self._recover_pending_activation_probes()
            self._recover_interrupted(recovery_limit)
        except BaseException:
            try:
                self._connection.close()
            finally:
                os.close(self._writer_descriptor)
                self._closed = True
            raise

    @property
    def database_path(self) -> Path:
        return self._database_path

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            try:
                self._connection.execute("PRAGMA wal_checkpoint(PASSIVE)")
            finally:
                try:
                    self._connection.close()
                finally:
                    os.close(self._writer_descriptor)
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
        with self._transaction():
            return self._select_record((tenant_id, repository_id, job_id))

    def reserve_activation_probe(
        self, *, probe_id: str, idempotency_digest: str, profile_id: str,
        provider_id: str, model_id: str, profile_digest: str, input_digest: str,
    ) -> tuple[dict[str, object], bool]:
        if (not isinstance(probe_id, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,64}", probe_id)
                or not isinstance(idempotency_digest, str) or not HEX64.fullmatch(idempotency_digest)
                or any(not isinstance(value, str) or not value or len(value) > 128
                       for value in (profile_id, provider_id, model_id))
                or not HEX64.fullmatch(profile_digest) or not HEX64.fullmatch(input_digest)):
            raise LandingServiceError("probe_record", 422, "activation probe record invalid")
        with self._transaction():
            existing = self._connection.execute(
                "SELECT probe_id, profile_id, provider_id, model_id, profile_digest, input_digest "
                "FROM landing_activation_probes WHERE idempotency_digest = ?",
                (idempotency_digest,),
            ).fetchone()
            if existing is not None:
                existing_id, *identity = existing
                if identity != [profile_id, provider_id, model_id, profile_digest, input_digest]:
                    raise LandingServiceError("idempotency_conflict", 409, "activation probe idempotency conflict")
                return self._select_activation_probe(existing_id), False
            facts = {
                "probe_id": probe_id, "revision": 1, "idempotency_digest": idempotency_digest,
                "state": "pending", "profile_id": profile_id, "provider_id": provider_id,
                "model_id": model_id, "profile_digest": profile_digest, "input_digest": input_digest,
                "spec_digest": None, "response_digest": None, "usage_input_units": None,
                "usage_output_units": None, "provider_attempts": 1, "elapsed_ms": None,
                "request_started_at": self._timestamp(), "completed_at": None,
                "failure_category": None, "http_status": None,
            }
            self._insert_activation_probe(facts)
            return self._activation_probe_view(facts), True

    def finish_activation_probe(
        self, probe_id: str, outcome: dict[str, object],
    ) -> dict[str, object]:
        allowed = {"state", "spec_digest", "response_digest", "usage_input_units",
                   "usage_output_units", "elapsed_ms", "failure_category", "http_status"}
        if not isinstance(outcome, dict) or set(outcome) != allowed or outcome.get("state") not in {
            "normalized", "failed", "unknown"
        }:
            raise LandingServiceError("probe_record", 422, "activation probe result invalid")
        with self._transaction():
            current = self._select_activation_probe(probe_id)
            if current is None:
                raise LandingServiceError("not_found", 404, "activation probe not found")
            if current["state"] != "pending":
                return current
            facts = {key: value for key, value in current.items() if key in _PROBE_VIEW_KEYS}
            facts.update(outcome)
            facts["revision"] = int(current["revision"]) + 1
            facts["idempotency_digest"] = None
            facts["completed_at"] = self._timestamp()
            self._validate_activation_probe_result(facts)
            self._insert_activation_probe(facts)
            return self._activation_probe_view(facts)

    def get_activation_probe(self, probe_id: str) -> dict[str, object]:
        if not isinstance(probe_id, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,64}", probe_id):
            raise LandingServiceError("probe_id", 400, "activation probe id invalid")
        with self._transaction():
            record = self._select_activation_probe(probe_id)
            if record is None:
                raise LandingServiceError("not_found", 404, "activation probe not found")
            return record

    def _recover_pending_activation_probes(self) -> None:
        while True:
            with self._transaction():
                pending = self._connection.execute(
                    """SELECT probe_id FROM landing_activation_probes AS p
                         WHERE state = 'pending' AND revision = (
                               SELECT MAX(latest.revision) FROM landing_activation_probes AS latest
                                WHERE latest.probe_id = p.probe_id)
                         ORDER BY probe_id LIMIT ?""",
                    (MAX_RECOVERY_BATCH,),
                ).fetchall()
                for (probe_id,) in pending:
                    current = self._select_activation_probe(probe_id)
                    if current is None:
                        raise LandingServiceError("probe_record", 500, "activation probe recovery failed")
                    facts = {key: value for key, value in current.items() if key in _PROBE_VIEW_KEYS}
                    facts.update(
                        revision=int(current["revision"]) + 1, idempotency_digest=None,
                        state="unknown", completed_at=self._timestamp(), failure_category="outcome_ambiguous",
                    )
                    self._insert_activation_probe(facts)
            if len(pending) < MAX_RECOVERY_BATCH:
                return

    def _insert_activation_probe(self, facts: dict[str, object]) -> None:
        self._connection.execute(
            """INSERT INTO landing_activation_probes (
                   probe_id, revision, idempotency_digest, state, profile_id, provider_id,
                   model_id, profile_digest, input_digest, spec_digest, response_digest,
                   usage_input_units, usage_output_units, provider_attempts, elapsed_ms,
                   request_started_at, completed_at, failure_category, http_status
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                facts.get("probe_id"), facts.get("revision"), facts.get("idempotency_digest"),
                facts.get("state"), facts.get("profile_id"), facts.get("provider_id"),
                facts.get("model_id"), facts.get("profile_digest"), facts.get("input_digest"),
                facts.get("spec_digest"), facts.get("response_digest"),
                facts.get("usage_input_units"), facts.get("usage_output_units"),
                facts.get("provider_attempts"), facts.get("elapsed_ms"),
                facts.get("request_started_at"), facts.get("completed_at"),
                facts.get("failure_category"), facts.get("http_status"),
            ),
        )

    def _select_activation_probe(self, probe_id: str) -> dict[str, object] | None:
        row = self._connection.execute(
            """SELECT probe_id, revision, state, profile_id, provider_id, model_id,
                      profile_digest, input_digest, spec_digest, response_digest,
                      usage_input_units, usage_output_units, provider_attempts, elapsed_ms,
                      request_started_at, completed_at, failure_category, http_status
                 FROM landing_activation_probes
                WHERE probe_id = ? ORDER BY revision DESC LIMIT 1""",
            (probe_id,),
        ).fetchone()
        if row is None:
            return None
        return self._activation_probe_view(dict(zip(_PROBE_VIEW_KEYS, row)))

    @staticmethod
    def _activation_probe_view(facts: dict[str, object]) -> dict[str, object]:
        return {"schema_version": 1, **{key: facts.get(key) for key in _PROBE_VIEW_KEYS}}

    @staticmethod
    def _validate_activation_probe_result(facts: dict[str, object]) -> None:
        state = facts["state"]
        if state == "normalized":
            if (not isinstance(facts["spec_digest"], str) or not HEX64.fullmatch(facts["spec_digest"])
                    or not isinstance(facts["response_digest"], str) or not HEX64.fullmatch(facts["response_digest"])
                    or any(type(facts[name]) is not int or not 0 <= facts[name] <= 2_147_483_647
                           for name in ("usage_input_units", "usage_output_units", "elapsed_ms"))
                    or facts["failure_category"] is not None or facts["http_status"] is not None):
                raise LandingServiceError("probe_record", 500, "activation probe result invalid")
        elif state == "failed":
            if (facts["failure_category"] not in _PROBE_FAILURE_CATEGORIES
                    or (facts["http_status"] is not None
                        and (type(facts["http_status"]) is not int or not 100 <= facts["http_status"] <= 599))
                    or type(facts["elapsed_ms"]) is not int or not 0 <= facts["elapsed_ms"] <= 2_147_483_647
                    or any(facts[name] is not None for name in (
                        "spec_digest", "response_digest", "usage_input_units", "usage_output_units"
                    ))):
                raise LandingServiceError("probe_record", 500, "activation probe result invalid")
        elif state == "unknown":
            if facts["failure_category"] != "outcome_ambiguous":
                raise LandingServiceError("probe_record", 500, "activation probe result invalid")

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
                if (
                    current is None
                    or current.source != source
                    or command != (request_digest, current.source.input_digest)
                ):
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
        _validate_record(record, validate_files=True)
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
                      SET state = ?, artifact_json = ?, sealed_artifact_json = ?,
                          provider_evidence_digest = ?, reason_code = ?,
                          revision = ?, updated_at = ?, observation_json = ?
                    WHERE tenant_id = ? AND repository_id = ? AND job_id = ?
                      AND revision = ?""",
                (
                    values[1],
                    values[2],
                    values[3],
                    values[4],
                    values[5],
                    values[6],
                    self._timestamp(),
                    canonical_json(stored.observation.to_dict()) if stored.observation else None,
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
            if current.source != source:
                raise _conflict()
            command = self._connection.execute(
                """SELECT request_digest, input_digest FROM landing_commands
                    WHERE tenant_id = ? AND repository_id = ? AND job_id = ?
                      AND action = 'cancel' AND command_key = ?""",
                (*identity, command_key),
            ).fetchone()
            if command is not None:
                if command != (request_digest, current.source.input_digest):
                    raise _conflict()
                return current
            _validate_transition(current.state, "cancelled")
            cancelled = replace(
                current,
                state="cancelled",
                reason_code="cancelled",
                revision=current.revision + 1,
            )
            values = _record_values(cancelled)
            self._connection.execute(
                """UPDATE landing_jobs
                      SET state = ?, artifact_json = ?, sealed_artifact_json = ?,
                          provider_evidence_digest = ?, reason_code = ?,
                          revision = ?, updated_at = ?, observation_json = ?
                    WHERE tenant_id = ? AND repository_id = ? AND job_id = ?""",
                (
                    values[1],
                    values[2],
                    values[3],
                    values[4],
                    values[5],
                    values[6],
                    self._timestamp(),
                    canonical_json(cancelled.observation.to_dict()) if cancelled.observation else None,
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
        try:
            version = self._connection.execute("PRAGMA user_version").fetchone()[0]
            application = self._connection.execute("PRAGMA application_id").fetchone()[0]
            identity = (version, application)
            if identity == (0, 0):
                if _schema_inventory(self._connection):
                    raise _schema_error()
                with self._transaction():
                    for statement in _SCHEMA.split(";"):
                        if statement.strip():
                            self._connection.execute(statement)
                    self._connection.execute(_PROBE_TABLE)
                    for statement in _PROBE_TRIGGERS:
                        self._connection.execute(statement)
                    self._connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
                    self._connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            elif identity == (1, APPLICATION_ID):
                # Validate the old schema before adding one nullable field. Historical
                # rows retain NULL; they cannot authorize provider fallback.
                _validate_schema(self._connection, version=1)
                with self._transaction():
                    self._connection.execute(MIGRATION_002_EXPAND)
                    self._connection.execute("PRAGMA user_version = 2")
                    self._connection.execute(_PROBE_TABLE)
                    for statement in _PROBE_TRIGGERS:
                        self._connection.execute(statement)
                    self._connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            elif identity == (2, APPLICATION_ID):
                _validate_schema(self._connection, version=2)
                with self._transaction():
                    self._connection.execute(_PROBE_TABLE)
                    for statement in _PROBE_TRIGGERS:
                        self._connection.execute(statement)
                    self._connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            elif identity != (SCHEMA_VERSION, APPLICATION_ID):
                raise _schema_error()
            _validate_schema(self._connection)
            result = self._connection.execute("PRAGMA quick_check").fetchone()[0]
        except LandingServiceError:
            raise
        except sqlite3.Error as exc:
            raise _schema_error() from exc
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
            """SELECT tenant_id, repository_id, job_id, source_json, state,
                      artifact_json, sealed_artifact_json,
                      provider_evidence_digest, reason_code, revision, observation_json
                 FROM landing_jobs
                WHERE tenant_id = ? AND repository_id = ? AND job_id = ?""",
            identity,
        ).fetchone()
        if row is None:
            return None
        record = _decode_record(row)
        try:
            _validate_record(record, validate_files=True)
        except LandingServiceError as exc:
            if exc.code != "artifact_integrity" or record.state != "artifact_ready":
                raise
            revision = record.revision + 1
            cursor = self._connection.execute(
                """UPDATE landing_jobs
                      SET state = 'needs_human', reason_code = 'artifact_integrity',
                          revision = ?, updated_at = ?
                    WHERE tenant_id = ? AND repository_id = ? AND job_id = ?
                      AND revision = ?""",
                (revision, self._timestamp(), *identity, record.revision),
            )
            if cursor.rowcount != 1:
                raise LandingServiceError("stale_job", 409, "landing job is stale")
            return replace(
                record,
                state="needs_human",
                reason_code="artifact_integrity",
                revision=revision,
            )
        return record

    def _insert_record(self, record: LandingJobRecord) -> None:
        values = _record_values(record)
        self._connection.execute(
            """INSERT INTO landing_jobs
               (tenant_id, repository_id, job_id, source_json, state,
                artifact_json, sealed_artifact_json, provider_evidence_digest,
                reason_code, revision, updated_at, observation_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.source.tenant_id,
                record.source.repository_id,
                record.source.job_id,
                *values,
                self._timestamp(),
                canonical_json(record.observation.to_dict()) if record.observation else None,
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


def _acquire_writer(root: Path) -> int:
    """Keep the advisory lifetime lock until the connection has been closed."""
    descriptor = None
    try:
        path = root / "landing.writer.lock"
        descriptor = os.open(
            path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600
        )
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise LandingServiceError("store_lock_file", 500, "landing writer lock invalid")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise LandingServiceError("store_writer_active", 503, "landing writer already active") from None
        current = path.lstat()
        if (metadata.st_dev, metadata.st_ino) != (current.st_dev, current.st_ino):
            raise LandingServiceError("store_lock_file", 500, "landing writer lock replaced")
        return descriptor
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        raise


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


def _schema_inventory(connection: sqlite3.Connection) -> tuple[tuple[str, str], ...]:
    return tuple(
        connection.execute(
            """SELECT type, name FROM sqlite_schema
                WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"""
        ).fetchall()
    )


def _validate_schema(connection: sqlite3.Connection, *, version: int = SCHEMA_VERSION) -> None:
    expected_inventory = (
        ("table", "landing_commands"),
        ("table", "landing_jobs"),
    ) if version in {1, 2} else (
        ("table", "landing_activation_probes"),
        ("table", "landing_commands"),
        ("table", "landing_jobs"),
        ("trigger", "landing_activation_probes_no_delete"),
        ("trigger", "landing_activation_probes_no_update"),
    )
    if _schema_inventory(connection) != expected_inventory:
        raise _schema_error()
    table_list = {
        row[1]: (row[2], row[3], row[4], row[5])
        for row in connection.execute("PRAGMA table_list").fetchall()
        if row[0] == "main" and row[1] in _EXPECTED_COLUMNS
    }
    expected_tables = ("landing_jobs", "landing_commands") if version in {1, 2} else tuple(_EXPECTED_COLUMNS)
    for table in expected_tables:
        expected = _EXPECTED_COLUMNS[table]
        if version == 1 and table == "landing_jobs":
            expected = expected[:-1]
        columns = tuple(
            (row[1], row[2], row[3], row[5])
            for row in connection.execute(f"PRAGMA table_xinfo({table})").fetchall()
            if row[6] == 0
        )
        if columns != expected or table_list.get(table) != (
            "table",
            len(expected),
            0,
            1,
        ):
            raise _schema_error()
    foreign_keys = tuple(
        (row[1], row[2], row[3], row[4], row[5], row[6], row[7])
        for row in connection.execute("PRAGMA foreign_key_list(landing_commands)")
    )
    if foreign_keys != _EXPECTED_FOREIGN_KEY:
        raise _schema_error()


def _schema_error() -> LandingServiceError:
    return LandingServiceError("store_schema", 500, "landing store schema unsupported")


def _record_values(
    record: LandingJobRecord,
) -> tuple[bytes, str, bytes | None, bytes | None, str | None, str | None, int]:
    return (
        canonical_json(record.source.to_dict()),
        record.state,
        canonical_json(record.artifact.to_dict()) if record.artifact else None,
        (
            canonical_json(record.sealed_artifact.to_dict())
            if record.sealed_artifact
            else None
        ),
        record.provider_evidence_digest,
        record.reason_code,
        record.revision,
    )


def _decode_record(row) -> LandingJobRecord:
    (
        tenant_id,
        repository_id,
        job_id,
        source_json,
        state,
        artifact_json,
        sealed_json,
        evidence_digest,
        reason_code,
        revision,
        observation_json,
    ) = row
    try:
        source = LandingInputV1.from_dict(strict_json_object(source_json))
        artifact = (
            SiteArtifactV1.from_dict(strict_json_object(artifact_json))
            if artifact_json is not None
            else None
        )
        sealed_artifact = (
            RetainedLandingArtifact.from_dict(strict_json_object(sealed_json))
            if sealed_json is not None
            else None
        )
        observation = (LandingProviderObservation.from_dict(strict_json_object(observation_json))
                       if observation_json is not None else None)
    except (LandingArtifactError, LandingContractError, ValueError, TypeError) as exc:
        raise LandingServiceError("store_record", 500, "landing store record invalid") from exc
    if (tenant_id, repository_id, job_id) != (
        source.tenant_id,
        source.repository_id,
        source.job_id,
    ):
        raise LandingServiceError("store_identity", 500, "landing row identity invalid")
    record = LandingJobRecord(
        source,
        state,
        artifact,
        evidence_digest,
        reason_code,
        revision,
        sealed_artifact,
        observation,
    )
    return record


def _validate_record(record: LandingJobRecord, *, validate_files: bool = False) -> None:
    if not isinstance(record, LandingJobRecord) or record.state not in LANDING_STATES:
        raise LandingServiceError("state", 500, "landing state invalid")
    if (
        record.provider_evidence_digest is not None
        and not HEX64.fullmatch(record.provider_evidence_digest)
    ):
        raise LandingServiceError("provider_binding", 500, "landing evidence invalid")
    if type(record.revision) is not int or record.revision < 0:
        raise LandingServiceError("revision", 500, "landing revision invalid")
    if record.observation is not None and (
        not isinstance(record.observation, LandingProviderObservation)
        or record.observation.evidence.input_digest != record.source.input_digest
        or record.observation.evidence.provider_evidence_digest != record.provider_evidence_digest
    ):
        raise LandingServiceError("provider_binding", 500, "landing observation invalid")
    if record.state == "artifact_ready" and (
        record.artifact is None or record.sealed_artifact is None
    ):
        raise LandingServiceError("artifact_binding", 500, "landing artifact missing")
    if (record.artifact is None) != (record.sealed_artifact is None):
        raise LandingServiceError("artifact_integrity", 500, "landing artifact incomplete")
    if record.state == "needs_human" and record.reason_code == "artifact_integrity":
        return
    if record.artifact is not None:
        if record.state not in {"artifact_ready", "needs_human", "cancelled"}:
            raise LandingServiceError("artifact_binding", 500, "landing artifact not terminal")
        sealed = record.sealed_artifact
        if (
            sealed is None
            or sealed.artifact != record.artifact
            or record.provider_evidence_digest
            != sealed.provider_evidence.provider_evidence_digest
            or record.artifact.site_id != record.source.site_id
            or record.artifact.source_sha != record.source.exact_base_sha
            or record.artifact.source_tree != record.source.exact_base_tree
            or record.artifact.input_digest != record.source.input_digest
        ):
            raise LandingServiceError("artifact_integrity", 500, "landing artifact invalid")
        if validate_files and record.state == "artifact_ready":
            try:
                sealed.validate(record.source)
            except LandingArtifactError as exc:
                raise LandingServiceError(
                    "artifact_integrity", 500, "landing artifact invalid"
                ) from exc


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
