from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

TERMINAL_STATUSES = frozenset({"succeeded", "failed", "cancelled", "dead"})


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None = None) -> str:
    return (value or now_utc()).astimezone(timezone.utc).isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


class DurableStore:
    """Single-host durable queue with leases, audit events, approvals, and receipts."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o770)
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = FULL")
        try:
            yield conn
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    repo TEXT NOT NULL,
                    clone_url TEXT NOT NULL,
                    base_sha TEXT NOT NULL,
                    head_sha TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    route_id TEXT,
                    change_id TEXT,
                    status_context TEXT NOT NULL,
                    profiles_json TEXT NOT NULL,
                    required_approvals_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    lease_owner TEXT,
                    lease_expires_at TEXT,
                    blocked_reason TEXT,
                    last_error TEXT,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(repo, head_sha, status_context)
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_queue ON jobs(status, created_at);
                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    nonce TEXT NOT NULL UNIQUE,
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    repo TEXT NOT NULL,
                    head_sha TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    key_id TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    payload_hash TEXT NOT NULL UNIQUE,
                    envelope_json TEXT NOT NULL,
                    imported_at TEXT NOT NULL,
                    revoked_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_approvals_match
                    ON approvals(job_id, scope, head_sha, expires_at);
                CREATE TABLE IF NOT EXISTS receipts (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    head_sha TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    signature TEXT,
                    key_id TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(job_id, kind, head_sha)
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                "INSERT OR IGNORE INTO settings(key, value_json, updated_at) VALUES('kill_switch', ?, ?)",
                (_json({"enabled": True, "reason": "not commissioned"}), iso()),
            )
        try:
            os.chmod(self.path, 0o660)
        except OSError:
            pass

    @staticmethod
    def _job(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        value = dict(row)
        value["profiles"] = _decode(value.pop("profiles_json"), [])
        value["required_approvals"] = _decode(value.pop("required_approvals_json"), [])
        value["result"] = _decode(value.pop("result_json"), None)
        return value

    @staticmethod
    def _event(
        conn: sqlite3.Connection,
        event_type: str,
        *,
        job_id: str | None = None,
        actor: str = "system",
        payload: dict[str, Any] | None = None,
    ) -> None:
        conn.execute(
            "INSERT INTO events(job_id, event_type, actor, payload_json, created_at) VALUES(?, ?, ?, ?, ?)",
            (job_id, event_type, actor, _json(payload or {}), iso()),
        )

    def enqueue_job(
        self,
        *,
        repo: str,
        clone_url: str,
        base_sha: str,
        head_sha: str,
        branch: str,
        profiles: list[str] | None = None,
        required_approvals: list[str] | None = None,
        route_id: str | None = None,
        change_id: str | None = None,
        status_context: str = "adaptive-grok-ci/trusted",
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        if len(base_sha) != 40 or len(head_sha) != 40:
            raise ValueError("base_sha and head_sha must be full Git SHAs")
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT * FROM jobs WHERE repo = ? AND head_sha = ? AND status_context = ?",
                (repo, head_sha, status_context),
            ).fetchone()
            if existing:
                conn.commit()
                return self._job(existing) or {}
            job_id = uuid.uuid4().hex
            created = iso()
            conn.execute(
                """
                INSERT INTO jobs(
                    id, repo, clone_url, base_sha, head_sha, branch, route_id, change_id,
                    status_context, profiles_json, required_approvals_json, status,
                    attempts, max_attempts, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', 0, ?, ?, ?)
                """,
                (
                    job_id, repo, clone_url, base_sha, head_sha, branch, route_id, change_id,
                    status_context, _json(sorted(set(profiles or ["base"]))),
                    _json(sorted(set(required_approvals or []))), max_attempts, created, created,
                ),
            )
            self._event(conn, "job.enqueued", job_id=job_id, payload={"head_sha": head_sha})
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            conn.commit()
        return self._job(row) or {}

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            return self._job(conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone())

    def find_job(self, repo: str, head_sha: str, status_context: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE repo = ? AND head_sha = ? AND status_context = ?",
                (repo, head_sha, status_context),
            ).fetchone()
        return self._job(row)

    def list_jobs(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status, limit)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._job(row) or {} for row in rows]

    def kill_switch_state(self) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT value_json, updated_at FROM settings WHERE key = 'kill_switch'").fetchone()
        if not row:
            return {"enabled": True, "reason": "setting missing", "updated_at": None}
        value = _decode(row["value_json"], {})
        return {"enabled": bool(value.get("enabled", True)), "reason": str(value.get("reason", "")), "updated_at": row["updated_at"]}

    def set_kill_switch(self, enabled: bool, reason: str, actor: str = "human") -> dict[str, Any]:
        value = {"enabled": bool(enabled), "reason": reason.strip()}
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO settings(key, value_json, updated_at) VALUES('kill_switch', ?, ?)
                ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at
                """,
                (_json(value), iso()),
            )
            self._event(conn, "kill-switch.changed", actor=actor, payload=value)
            conn.commit()
        return self.kill_switch_state()

    def _recover_expired(self, conn: sqlite3.Connection, current: str) -> None:
        rows = conn.execute(
            "SELECT id, attempts, max_attempts FROM jobs WHERE status = 'running' AND lease_expires_at < ?",
            (current,),
        ).fetchall()
        for row in rows:
            target = "dead" if row["attempts"] >= row["max_attempts"] else "queued"
            conn.execute(
                "UPDATE jobs SET status = ?, lease_owner = NULL, lease_expires_at = NULL, last_error = ?, updated_at = ? WHERE id = ?",
                (target, "worker lease expired", current, row["id"]),
            )
            self._event(conn, f"job.{target}", job_id=row["id"], payload={"reason": "lease expired"})

    def lease_next(self, worker_id: str, lease_seconds: int = 1800) -> dict[str, Any] | None:
        if not worker_id.strip() or lease_seconds < 1:
            raise ValueError("worker_id and positive lease_seconds are required")
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            switch = conn.execute("SELECT value_json FROM settings WHERE key = 'kill_switch'").fetchone()
            if not switch or _decode(switch["value_json"], {"enabled": True}).get("enabled"):
                conn.commit()
                return None
            current = iso()
            self._recover_expired(conn, current)
            row = conn.execute(
                "SELECT * FROM jobs WHERE status = 'queued' AND attempts < max_attempts ORDER BY created_at LIMIT 1"
            ).fetchone()
            if not row:
                conn.commit()
                return None
            expires = iso(now_utc() + timedelta(seconds=lease_seconds))
            conn.execute(
                """
                UPDATE jobs SET status = 'running', attempts = attempts + 1, lease_owner = ?,
                    lease_expires_at = ?, blocked_reason = NULL, updated_at = ? WHERE id = ?
                """,
                (worker_id, expires, current, row["id"]),
            )
            self._event(conn, "job.leased", job_id=row["id"], actor=worker_id, payload={"expires_at": expires})
            leased = conn.execute("SELECT * FROM jobs WHERE id = ?", (row["id"],)).fetchone()
            conn.commit()
        return self._job(leased)

    def renew_lease(self, job_id: str, worker_id: str, lease_seconds: int) -> dict[str, Any]:
        expires = iso(now_utc() + timedelta(seconds=lease_seconds))
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            updated = conn.execute(
                "UPDATE jobs SET lease_expires_at = ?, updated_at = ? WHERE id = ? AND status = 'running' AND lease_owner = ?",
                (expires, iso(), job_id, worker_id),
            ).rowcount
            if updated != 1:
                conn.rollback()
                raise RuntimeError("job lease is not owned by this worker")
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            conn.commit()
        return self._job(row) or {}

    def block_job(self, job_id: str, worker_id: str, reason: str) -> dict[str, Any]:
        return self._finish_active(job_id, worker_id, "blocked", reason=reason)

    def retry_or_dead(self, job_id: str, worker_id: str, error: str) -> dict[str, Any]:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT attempts, max_attempts FROM jobs WHERE id = ? AND status = 'running' AND lease_owner = ?",
                (job_id, worker_id),
            ).fetchone()
            if not row:
                conn.rollback()
                raise RuntimeError("job lease is not owned by this worker")
            target = "dead" if row["attempts"] >= row["max_attempts"] else "queued"
            conn.execute(
                "UPDATE jobs SET status = ?, last_error = ?, lease_owner = NULL, lease_expires_at = NULL, updated_at = ? WHERE id = ?",
                (target, error, iso(), job_id),
            )
            self._event(conn, f"job.{target}", job_id=job_id, actor=worker_id, payload={"reason": error})
            result = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            conn.commit()
        return self._job(result) or {}

    def _finish_active(
        self,
        job_id: str,
        worker_id: str,
        status: str,
        *,
        result: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        if status not in {"blocked", "succeeded", "failed", "cancelled"}:
            raise ValueError("invalid status")
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            updated = conn.execute(
                """
                UPDATE jobs SET status = ?, result_json = ?, last_error = ?, blocked_reason = ?,
                    lease_owner = NULL, lease_expires_at = NULL, updated_at = ?
                WHERE id = ? AND status = 'running' AND lease_owner = ?
                """,
                (
                    status, _json(result) if result is not None else None,
                    reason if status == "failed" else None,
                    reason if status == "blocked" else None,
                    iso(), job_id, worker_id,
                ),
            ).rowcount
            if updated != 1:
                conn.rollback()
                raise RuntimeError("job lease is not owned by this worker")
            self._event(conn, f"job.{status}", job_id=job_id, actor=worker_id, payload={"reason": reason})
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            conn.commit()
        return self._job(row) or {}

    def finish_job(self, job_id: str, worker_id: str, *, status: str, result: dict[str, Any] | None = None, error: str | None = None) -> dict[str, Any]:
        return self._finish_active(job_id, worker_id, status, result=result, reason=error)

    def requeue_job(self, job_id: str, reason: str, actor: str = "system") -> dict[str, Any]:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT status, attempts, max_attempts FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if not row:
                conn.rollback()
                raise KeyError(job_id)
            if row["status"] in TERMINAL_STATUSES:
                conn.rollback()
                raise ValueError(f"cannot requeue terminal job {row['status']}")
            target = "dead" if row["attempts"] >= row["max_attempts"] else "queued"
            conn.execute(
                "UPDATE jobs SET status = ?, blocked_reason = NULL, last_error = ?, lease_owner = NULL, lease_expires_at = NULL, updated_at = ? WHERE id = ?",
                (target, reason, iso(), job_id),
            )
            self._event(conn, f"job.{target}", job_id=job_id, actor=actor, payload={"reason": reason})
            result = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            conn.commit()
        return self._job(result) or {}

    def record_approval(self, approval: dict[str, Any]) -> None:
        required = {
            "approval_id", "nonce", "job_id", "repo", "head_sha", "scope", "actor", "key_id",
            "issued_at", "expires_at", "payload_hash", "envelope_json",
        }
        missing = sorted(required - approval.keys())
        if missing:
            raise ValueError("approval fields missing: " + ", ".join(missing))
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            job = conn.execute("SELECT repo, head_sha FROM jobs WHERE id = ?", (approval["job_id"],)).fetchone()
            if not job or job["repo"] != approval["repo"] or job["head_sha"] != approval["head_sha"]:
                conn.rollback()
                raise ValueError("approval does not match a durable job")
            try:
                conn.execute(
                    """
                    INSERT INTO approvals(
                        approval_id, nonce, job_id, repo, head_sha, scope, actor, key_id,
                        issued_at, expires_at, payload_hash, envelope_json, imported_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        approval["approval_id"], approval["nonce"], approval["job_id"], approval["repo"],
                        approval["head_sha"], approval["scope"], approval["actor"], approval["key_id"],
                        approval["issued_at"], approval["expires_at"], approval["payload_hash"],
                        approval["envelope_json"], iso(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                conn.rollback()
                raise ValueError("approval replay or duplicate detected") from exc
            self._event(conn, "approval.imported", job_id=approval["job_id"], actor=approval["actor"], payload={"scope": approval["scope"]})
            conn.commit()

    def has_approval(self, job_id: str, scope: str, head_sha: str, at: datetime | None = None) -> bool:
        moment = iso(at)
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM approvals WHERE job_id = ? AND scope IN (?, '*') AND head_sha = ?
                    AND revoked_at IS NULL AND issued_at <= ? AND expires_at >= ? LIMIT 1
                """,
                (job_id, scope, head_sha, moment, moment),
            ).fetchone()
        return row is not None

    def missing_approvals(self, job_id: str, scopes: list[str], head_sha: str) -> list[str]:
        return sorted(scope for scope in set(scopes) if not self.has_approval(job_id, scope, head_sha))

    def valid_approvals(self, job_id: str, scopes: list[str], head_sha: str) -> list[dict[str, Any]]:
        moment = iso()
        evidence: list[dict[str, Any]] = []
        with self.connect() as conn:
            for requested in sorted(set(scopes)):
                row = conn.execute(
                    """
                    SELECT approval_id, scope, actor, key_id, issued_at, expires_at, payload_hash
                    FROM approvals WHERE job_id = ? AND scope IN (?, '*') AND head_sha = ?
                        AND revoked_at IS NULL AND issued_at <= ? AND expires_at >= ?
                    ORDER BY imported_at DESC LIMIT 1
                    """,
                    (job_id, requested, head_sha, moment, moment),
                ).fetchone()
                if row:
                    item = dict(row)
                    item["requested_scope"] = requested
                    item["granted_scope"] = item.pop("scope")
                    evidence.append(item)
        return evidence

    def record_receipt(
        self,
        *,
        job_id: str,
        head_sha: str,
        kind: str,
        status: str,
        payload_hash: str,
        payload: dict[str, Any],
        signature: str | None = None,
        key_id: str | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO receipts(id, job_id, head_sha, kind, status, payload_hash, payload_json, signature, key_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id, kind, head_sha) DO UPDATE SET
                    status=excluded.status, payload_hash=excluded.payload_hash, payload_json=excluded.payload_json,
                    signature=excluded.signature, key_id=excluded.key_id, created_at=excluded.created_at
                """,
                (uuid.uuid4().hex, job_id, head_sha, kind, status, payload_hash, _json(payload), signature, key_id, iso()),
            )
            self._event(conn, "receipt.recorded", job_id=job_id, payload={"kind": kind, "status": status})
            conn.commit()
