"""Private single-writer caller journal; dispatch intent and input commit together."""

import os
import sqlite3
import time

from .contracts import canonical_json
from .landing_contracts import strict_json_object, landing_digest
from .landing_sqlite_store import _acquire_writer, _validate_database_path
from .settings import SettingsError


APPLICATION_ID = 0x4C35464F
MAX_SPOOL_BYTES = 64 * 1_048_576
MAX_JOBS = 10_000


class CallerJournal:
    def __init__(self, config, *, clock=time.time):
        self.config, self.clock = config, clock
        self.path = config.journal_path / "failover.sqlite3"
        if self.path.is_symlink():
            raise SettingsError("caller journal must not be a symlink")
        _validate_database_path(self.path)
        self.lock = _acquire_writer(config.journal_path)
        self.connection = None
        previous = os.umask(0o077)
        try:
            self.connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
            self.connection.execute("PRAGMA trusted_schema=OFF")
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=FULL")
            self.connection.execute("PRAGMA secure_delete=ON")
            identity = (self.connection.execute("PRAGMA application_id").fetchone()[0],
                        self.connection.execute("PRAGMA user_version").fetchone()[0])
            inventory = self.connection.execute("SELECT name FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%'").fetchall()
            if identity == (0, 0) and not inventory:
                self.connection.execute("BEGIN IMMEDIATE")
                self.connection.execute("CREATE TABLE requests (job_id TEXT PRIMARY KEY, record BLOB NOT NULL, payload BLOB, expires_at INTEGER NOT NULL) STRICT")
                self.connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
                self.connection.execute("PRAGMA user_version=1")
                self.connection.execute("COMMIT")
            elif identity != (APPLICATION_ID, 1) or inventory != [("requests",)]:
                raise SettingsError("caller journal schema unsupported")
            columns = tuple((row[1], row[2], row[3], row[5]) for row in self.connection.execute("PRAGMA table_info(requests)"))
            if columns != (("job_id", "TEXT", 1, 1), ("record", "BLOB", 1, 0), ("payload", "BLOB", 0, 0), ("expires_at", "INTEGER", 1, 0)):
                raise SettingsError("caller journal schema unsupported")
            self.connection.execute("UPDATE requests SET payload=NULL WHERE expires_at<=?", (int(self.clock()),))
        except BaseException:
            self.close()
            raise
        finally:
            os.umask(previous)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        if self.lock is not None:
            os.close(self.lock)
            self.lock = None

    def load(self, job_id):
        row = self.connection.execute("SELECT record, payload FROM requests WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            return None
        record = strict_json_object(row[0], maximum=131_072)
        self._validate(record)
        if record["request"]["job_id"] != job_id or record["request"]["config_digest"] != self.config.digest:
            raise SettingsError("caller journal identity mismatch")
        return record, row[1]

    def create(self, record, payload):
        self._seal(record)
        count, retained = self.connection.execute("SELECT count(*), coalesce(sum(length(payload)),0) FROM requests").fetchone()
        if count >= MAX_JOBS or retained + len(payload) > MAX_SPOOL_BYTES:
            raise SettingsError("caller journal capacity exhausted")
        self.connection.execute("INSERT INTO requests VALUES (?, ?, ?, ?)", (
            record["request"]["job_id"], canonical_json(record), payload, record["expires_at"],
        ))

    def save(self, record, *, purge=False):
        self._seal(record)
        raw = canonical_json(record)
        if len(raw) > 131_072:
            raise SettingsError("caller record too large")
        self.connection.execute("UPDATE requests SET record=?, payload=CASE WHEN ? THEN NULL ELSE payload END WHERE job_id=?", (
            raw, purge, record["request"]["job_id"],
        ))
        if purge:
            self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    @staticmethod
    def _seal(record):
        record["record_digest"] = landing_digest("landing-failover-record-v1", {
            key: value for key, value in record.items() if key != "record_digest"
        })

    def _validate(self, record):
        fields = {"schema_version", "request", "parent_digest", "created_at", "deadline_at", "expires_at",
                  "attempts", "winner", "state", "reason", "record_digest"}
        if set(record) != fields or type(record["schema_version"]) is not int or record["schema_version"] != 1:
            raise SettingsError("caller record invalid")
        expected = landing_digest("landing-failover-record-v1", {key: value for key, value in record.items() if key != "record_digest"})
        request_fields = {"job_id", "actor_id", "repository_id", "exact_base_sha", "exact_base_tree", "media_type",
                          "byte_length", "content_sha256", "config_digest"}
        if expected != record["record_digest"] or not isinstance(record["request"], dict) or set(record["request"]) != request_fields:
            raise SettingsError("caller record digest invalid")
        if record["parent_digest"] != landing_digest("landing-failover-request-v1", record["request"]):
            raise SettingsError("caller request digest invalid")
        if not isinstance(record["attempts"], list) or len(record["attempts"]) > len(self.config.backends):
            raise SettingsError("caller attempts invalid")
        for ordinal, attempt in enumerate(record["attempts"]):
            backend = self.config.backends[ordinal]
            child = "fo-" + landing_digest("landing-failover-child-v1", {
                "parent": record["parent_digest"], "ordinal": ordinal, "profile": backend.profile_digest,
            })[:48]
            if (not isinstance(attempt, dict) or set(attempt) != {"ordinal", "profile_id", "profile_digest", "child_id", "state", "receipt"}
                    or (attempt["ordinal"], attempt["profile_id"], attempt["profile_digest"], attempt["child_id"])
                    != (ordinal, backend.profile_id, backend.profile_digest, child)
                    or attempt["state"] not in ("planned", "dispatching", "not_submitted", "eligible_failure")):
                raise SettingsError("caller attempt identity invalid")
