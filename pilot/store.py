"""Private, append-only SQLite evidence for one serial pilot operator."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import stat
import threading
from typing import Iterator

from .contracts import (
    CandidateChangeV1,
    CandidateValidationV1,
    ContractError,
    DesignPartnerOutcomeV1,
    IssueSnapshotV1,
    PullRequestProposalV1,
    canonical_json,
    contract_digest,
)


APPLICATION_ID = 0x50494C54
SCHEMA_VERSION = 1
ZERO_DIGEST = "0" * 64
RECOVERY_LIMIT = 100

_SCHEMA = """
CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY NOT NULL,
    profile_digest TEXT NOT NULL,
    state TEXT NOT NULL,
    reason_code TEXT,
    workspace_digest TEXT,
    snapshot_json BLOB NOT NULL,
    candidate_json BLOB,
    validation_json BLOB,
    proposal_json BLOB,
    outcome_json BLOB,
    revision INTEGER NOT NULL,
    last_event_digest TEXT NOT NULL,
    updated_at TEXT NOT NULL
) STRICT;
CREATE TABLE events (
    job_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    kind TEXT NOT NULL,
    command_key TEXT,
    prior_digest TEXT NOT NULL,
    payload_digest TEXT NOT NULL,
    event_digest TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (job_id, sequence),
    UNIQUE (job_id, kind, command_key),
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
) STRICT;
CREATE TABLE effects (
    job_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    command_key TEXT NOT NULL,
    resource TEXT NOT NULL,
    grant_digest TEXT NOT NULL,
    candidate_digest TEXT NOT NULL,
    state TEXT NOT NULL,
    observation_json BLOB,
    created_at TEXT NOT NULL,
    PRIMARY KEY (job_id, kind),
    UNIQUE (job_id, command_key),
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
) STRICT;
"""

_TRANSITIONS = {
    "issue_snapshotted": {"workspace_ready", "needs_human", "rejected"},
    "workspace_ready": {"invocation_intent", "needs_human", "rejected"},
    "invocation_intent": {"candidate_sealed", "needs_human", "rejected"},
    "candidate_sealed": {"validation_intent", "needs_human", "rejected"},
    "validation_intent": {"gate_passed", "needs_human", "rejected"},
    "gate_passed": {"awaiting_grants", "branch_intent", "needs_human", "rejected"},
    "awaiting_grants": {"branch_intent", "needs_human", "rejected"},
    "branch_intent": {"branch_observed", "needs_human"},
    "branch_observed": {"pr_intent", "needs_human"},
    "pr_intent": {"pr_observed", "needs_human"},
    "pr_observed": {"awaiting_human", "needs_human"},
    "awaiting_human": {"merged_accepted", "closed_rejected", "merge_gate_unavailable"},
    "needs_human": set(),
    "rejected": set(),
    "merged_accepted": set(),
    "closed_rejected": set(),
    "merge_gate_unavailable": set(),
}


class PilotStoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class PilotJob:
    job_id: str
    profile_digest: str
    state: str
    reason_code: str | None
    workspace_digest: str | None
    snapshot: IssueSnapshotV1
    candidate: CandidateChangeV1 | None
    validation: CandidateValidationV1 | None
    proposal: PullRequestProposalV1 | None
    outcome: DesignPartnerOutcomeV1 | None
    revision: int
    last_event_digest: str


class PilotStore:
    def __init__(self, root: Path, *, control_repository: Path, clock=None, busy_timeout_ms: int = 5_000) -> None:
        if type(busy_timeout_ms) is not int or not 1 <= busy_timeout_ms <= 30_000:
            raise PilotStoreError("store_timeout")
        self._root = _private_root(Path(root), Path(control_repository))
        self._database_path = self._root / "pilot.sqlite3"
        _validate_database(self._database_path, allow_missing=True)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = threading.RLock()
        self._closed = False
        previous = os.umask(0o077)
        try:
            self._connection = sqlite3.connect(
                self._database_path,
                isolation_level=None,
                check_same_thread=False,
                timeout=busy_timeout_ms / 1000,
            )
        except sqlite3.Error as exc:
            raise PilotStoreError("store_open") from exc
        finally:
            os.umask(previous)
        os.chmod(self._database_path, 0o600)
        try:
            self._configure(busy_timeout_ms)
            self._initialize()
            _validate_database(self._database_path, allow_missing=False)
            self._recover()
        except BaseException:
            self._connection.close()
            self._closed = True
            raise

    @property
    def database_path(self) -> Path:
        return self._database_path

    def __enter__(self) -> "PilotStore":
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._connection.execute("PRAGMA wal_checkpoint(PASSIVE)")
            self._connection.close()
            self._closed = True

    def create_or_replay(self, snapshot: IssueSnapshotV1, *, command_key: str) -> tuple[PilotJob, bool]:
        snapshot = IssueSnapshotV1.from_dict(snapshot.to_dict())
        _bounded_text(command_key, "command_key")
        with self._transaction():
            row = self._connection.execute(
                "SELECT payload_digest FROM events WHERE job_id=? AND kind='submit' AND command_key=?",
                (snapshot.job_id, command_key),
            ).fetchone()
            current = self._select(snapshot.job_id)
            if row is not None:
                if current is None or row[0] != snapshot.issue_snapshot_digest or current.snapshot != snapshot:
                    raise PilotStoreError("command_conflict")
                return current, False
            if current is not None:
                raise PilotStoreError("command_conflict")
            timestamp = self._timestamp()
            event_digest = _event_digest(snapshot.job_id, 1, "submit", command_key, ZERO_DIGEST, snapshot.issue_snapshot_digest, timestamp)
            self._connection.execute(
                """INSERT INTO jobs
                   (job_id, profile_digest, state, reason_code, workspace_digest,
                    snapshot_json, candidate_json, validation_json, proposal_json,
                    outcome_json, revision, last_event_digest, updated_at)
                   VALUES (?, ?, 'issue_snapshotted', NULL, NULL, ?, NULL, NULL,
                           NULL, NULL, 1, ?, ?)""",
                (snapshot.job_id, snapshot.profile_digest, canonical_json(snapshot.to_dict()), event_digest, timestamp),
            )
            self._connection.execute(
                """INSERT INTO events
                   (job_id, sequence, kind, command_key, prior_digest,
                    payload_digest, event_digest, created_at)
                   VALUES (?, 1, 'submit', ?, ?, ?, ?, ?)""",
                (snapshot.job_id, command_key, ZERO_DIGEST, snapshot.issue_snapshot_digest, event_digest, timestamp),
            )
            return self._select_required(snapshot.job_id), True

    def get(self, job_id: str) -> PilotJob:
        _bounded_text(job_id, "job_id")
        with self._transaction():
            return self._select_required(job_id)

    def mark_workspace_ready(self, job_id: str, *, workspace_digest: str) -> PilotJob:
        _digest(workspace_digest)
        return self._transition(job_id, "workspace_ready", kind="workspace", payload_digest=workspace_digest, workspace_digest=workspace_digest)

    def begin_invocation(self, job_id: str, *, command_key: str) -> PilotJob:
        _bounded_text(command_key, "command_key")
        with self._transaction():
            if self._connection.execute(
                "SELECT 1 FROM events WHERE job_id=? AND kind='invocation_intent'", (job_id,)
            ).fetchone():
                raise PilotStoreError("attempt_consumed")
            return self._transition_locked(
                job_id,
                "invocation_intent",
                kind="invocation_intent",
                command_key=command_key,
                payload_digest=contract_digest("invocation-intent", {"job_id": job_id, "command_key": command_key}),
            )

    def store_candidate(self, job_id: str, candidate: CandidateChangeV1) -> PilotJob:
        candidate = CandidateChangeV1.from_dict(candidate.to_dict())
        with self._transaction():
            current = self._select_required(job_id)
            if (
                candidate.job_id != current.job_id
                or candidate.profile_digest != current.profile_digest
                or candidate.issue_snapshot_digest != current.snapshot.issue_snapshot_digest
                or candidate.base_sha != current.snapshot.base_sha
                or candidate.base_tree != current.snapshot.base_tree
                or candidate.workspace_digest != current.workspace_digest
            ):
                raise PilotStoreError("candidate_binding")
            return self._transition_locked(
                job_id,
                "candidate_sealed",
                kind="candidate",
                payload_digest=candidate.candidate_digest,
                candidate=candidate,
            )

    def mark_terminal(self, job_id: str, *, reason_code: str) -> PilotJob:
        _bounded_text(reason_code, "reason_code")
        return self._transition(
            job_id,
            "needs_human",
            kind="terminal",
            payload_digest=contract_digest("terminal", {"job_id": job_id, "reason_code": reason_code}),
            reason_code=reason_code,
        )

    def _transition(self, job_id: str, state: str, *, kind: str, payload_digest: str, command_key: str | None = None, workspace_digest: str | None = None, candidate: CandidateChangeV1 | None = None, reason_code: str | None = None) -> PilotJob:
        with self._transaction():
            return self._transition_locked(job_id, state, kind=kind, payload_digest=payload_digest, command_key=command_key, workspace_digest=workspace_digest, candidate=candidate, reason_code=reason_code)

    def _transition_locked(self, job_id: str, state: str, *, kind: str, payload_digest: str, command_key: str | None = None, workspace_digest: str | None = None, candidate: CandidateChangeV1 | None = None, reason_code: str | None = None) -> PilotJob:
        current = self._select_required(job_id)
        if state not in _TRANSITIONS.get(current.state, set()):
            raise PilotStoreError("invalid_transition")
        _digest(payload_digest)
        sequence = current.revision + 1
        timestamp = self._timestamp()
        event_digest = _event_digest(job_id, sequence, kind, command_key, current.last_event_digest, payload_digest, timestamp)
        new_candidate = candidate or current.candidate
        new_workspace = workspace_digest or current.workspace_digest
        cursor = self._connection.execute(
            """UPDATE jobs SET state=?, reason_code=?, workspace_digest=?,
                      candidate_json=?, revision=?, last_event_digest=?, updated_at=?
                 WHERE job_id=? AND revision=?""",
            (state, reason_code, new_workspace, canonical_json(new_candidate.to_dict()) if new_candidate else None, sequence, event_digest, timestamp, job_id, current.revision),
        )
        if cursor.rowcount != 1:
            raise PilotStoreError("stale_revision")
        try:
            self._connection.execute(
                """INSERT INTO events
                   (job_id, sequence, kind, command_key, prior_digest,
                    payload_digest, event_digest, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (job_id, sequence, kind, command_key, current.last_event_digest, payload_digest, event_digest, timestamp),
            )
        except sqlite3.IntegrityError as exc:
            raise PilotStoreError("command_conflict") from exc
        return self._select_required(job_id)

    def _configure(self, busy_timeout_ms: int) -> None:
        connection = self._connection
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
        if str(connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]).lower() != "wal":
            raise PilotStoreError("store_wal")
        connection.execute("PRAGMA synchronous=FULL")
        if connection.execute("PRAGMA synchronous").fetchone()[0] != 2:
            raise PilotStoreError("store_sync")

    def _initialize(self) -> None:
        identity = (self._connection.execute("PRAGMA user_version").fetchone()[0], self._connection.execute("PRAGMA application_id").fetchone()[0])
        tables = _tables(self._connection)
        if identity == (0, 0) and not tables:
            with self._transaction():
                for statement in _SCHEMA.split(";"):
                    if statement.strip():
                        self._connection.execute(statement)
                self._connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
                self._connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        elif identity != (SCHEMA_VERSION, APPLICATION_ID):
            raise PilotStoreError("store_schema")
        if _tables(self._connection) != {"effects", "events", "jobs"}:
            raise PilotStoreError("store_schema")
        if self._connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise PilotStoreError("store_integrity")

    def _recover(self) -> None:
        with self._transaction():
            rows = self._connection.execute(
                "SELECT job_id, state FROM jobs WHERE state IN ('invocation_intent','validation_intent') ORDER BY job_id LIMIT ?",
                (RECOVERY_LIMIT,),
            ).fetchall()
            for job_id, state in rows:
                reason = "model_outcome_ambiguous" if state == "invocation_intent" else "gate_outcome_ambiguous"
                self._transition_locked(
                    job_id,
                    "needs_human",
                    kind="recovery",
                    payload_digest=contract_digest("recovery", {"job_id": job_id, "reason_code": reason}),
                    reason_code=reason,
                )

    def _select(self, job_id: str) -> PilotJob | None:
        row = self._connection.execute(
            """SELECT job_id, profile_digest, state, reason_code,
                      workspace_digest, snapshot_json, candidate_json,
                      validation_json, proposal_json, outcome_json,
                      revision, last_event_digest
                 FROM jobs WHERE job_id=?""",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        try:
            snapshot = IssueSnapshotV1.from_dict(_decode(row[5]))
            candidate = CandidateChangeV1.from_dict(_decode(row[6])) if row[6] else None
            validation = CandidateValidationV1.from_dict(_decode(row[7])) if row[7] else None
            proposal = PullRequestProposalV1.from_dict(_decode(row[8])) if row[8] else None
            outcome = DesignPartnerOutcomeV1.from_dict(_decode(row[9])) if row[9] else None
        except (ContractError, ValueError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
            raise PilotStoreError("record_integrity") from exc
        record = PilotJob(row[0], row[1], row[2], row[3], row[4], snapshot, candidate, validation, proposal, outcome, row[10], row[11])
        if record.profile_digest != snapshot.profile_digest:
            raise PilotStoreError("record_integrity")
        if candidate and (
            candidate.job_id != record.job_id
            or candidate.profile_digest != record.profile_digest
            or candidate.issue_snapshot_digest != snapshot.issue_snapshot_digest
            or candidate.workspace_digest != record.workspace_digest
        ):
            raise PilotStoreError("record_integrity")
        event = self._connection.execute(
            "SELECT sequence, event_digest FROM events WHERE job_id=? ORDER BY sequence DESC LIMIT 1", (job_id,)
        ).fetchone()
        if event != (record.revision, record.last_event_digest):
            raise PilotStoreError("event_integrity")
        return record

    def _select_required(self, job_id: str) -> PilotJob:
        record = self._select(job_id)
        if record is None:
            raise PilotStoreError("not_found")
        return record

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        with self._lock:
            if self._closed:
                raise PilotStoreError("store_closed")
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                yield
                self._connection.execute("COMMIT")
            except BaseException:
                if self._connection.in_transaction:
                    self._connection.execute("ROLLBACK")
                raise

    def _timestamp(self) -> str:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise PilotStoreError("clock")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _private_root(root: Path, control_repository: Path) -> Path:
    if not root.is_absolute():
        raise PilotStoreError("state_root_absolute")
    control = control_repository.resolve(strict=True)
    absolute = Path(os.path.abspath(root))
    if absolute == control or control in absolute.parents:
        raise PilotStoreError("state_root_repository")
    previous = os.umask(0o077)
    try:
        absolute.mkdir(mode=0o700, parents=False, exist_ok=True)
    except OSError as exc:
        raise PilotStoreError("state_root") from exc
    finally:
        os.umask(previous)
    metadata = absolute.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_mode & 0o777 != 0o700:
        raise PilotStoreError("state_root_mode")
    return absolute.resolve(strict=True)


def _validate_database(path: Path, *, allow_missing: bool) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        if allow_missing:
            return
        raise PilotStoreError("database_missing")
    if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_uid != os.getuid() or metadata.st_mode & 0o777 != 0o600:
        raise PilotStoreError("database_mode")


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {row[0] for row in connection.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%'")}


def _decode(value: bytes) -> dict:
    if not isinstance(value, bytes) or len(value) > 1_000_000:
        raise PilotStoreError("record_integrity")
    decoded = json.loads(value.decode("utf-8"))
    if not isinstance(decoded, dict) or canonical_json(decoded) != value:
        raise PilotStoreError("record_integrity")
    return decoded


def _bounded_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 128:
        raise PilotStoreError(field)
    return value


def _digest(value: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise PilotStoreError("digest")
    return value


def _event_digest(job_id: str, sequence: int, kind: str, command_key: str | None, prior_digest: str, payload_digest: str, created_at: str) -> str:
    return contract_digest(
        "event",
        {
            "job_id": job_id,
            "sequence": sequence,
            "kind": kind,
            "command_key": command_key,
            "prior_digest": prior_digest,
            "payload_digest": payload_digest,
            "created_at": created_at,
        },
    )
