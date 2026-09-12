"""Durable exact-action publication intents and observation-only ambiguity handling."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import stat
from urllib.parse import quote

from .landing_filesystem import FilesystemLandingPublisher, owned_lock, private_root
from .landing_publication_contracts import (
    PublicationError, PublicationRequestV1, canonical, decode, require_digest,
)


APPLICATION_ID = 0x4C355055
PHASES = {"prepared", "inflight", "staged", "activated", "restored", "needs_human"}
_SCHEMA = """CREATE TABLE publication_intents (
    request_digest TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
    body BLOB NOT NULL, phase TEXT NOT NULL, observation BLOB,
    grant_digest TEXT, reason TEXT, updated_at TEXT NOT NULL
) STRICT"""


class PublicationStore:
    def __init__(self, root: Path, *, readonly: bool = False):
        self.root = Path(root)
        self._root_descriptor = private_root(self.root)
        self._lock = None
        self._connection = None
        self._readonly = readonly
        try:
            if not readonly:
                self._lock = owned_lock(self._root_descriptor, ".intent-writer.lock", create=True, exclusive=True)
            path = self.root / "publication.sqlite3"
            existed = path.exists()
            if existed:
                self._database_file(path)
            elif readonly:
                raise PublicationError("publication_state_unavailable")
            previous = os.umask(0o077)
            try:
                self._connection = sqlite3.connect(
                    f"file:{quote(str(path), safe='/')}?mode={'ro' if readonly else 'rwc'}",
                    uri=True, timeout=5, isolation_level=None,
                )
            finally:
                os.umask(previous)
            self._database_file(path)
            self._connection.execute("PRAGMA trusted_schema=OFF")
            if readonly:
                self._connection.execute("PRAGMA query_only=ON")
            else:
                if self._connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] != "wal":
                    raise PublicationError("publication_state_wal")
                self._connection.execute("PRAGMA synchronous=FULL")
            identity = (
                self._connection.execute("PRAGMA application_id").fetchone()[0],
                self._connection.execute("PRAGMA user_version").fetchone()[0],
            )
            if not existed and not readonly:
                if identity != (0, 0):
                    raise PublicationError("publication_state_identity")
                self._connection.execute("BEGIN IMMEDIATE")
                try:
                    self._connection.execute(_SCHEMA)
                    self._connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
                    self._connection.execute("PRAGMA user_version=1")
                    self._connection.execute("COMMIT")
                except BaseException:
                    self._connection.execute("ROLLBACK")
                    raise
            elif identity != (APPLICATION_ID, 1):
                raise PublicationError("publication_state_identity")
            tables = self._connection.execute(
                "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            columns = self._connection.execute("PRAGMA table_info(publication_intents)").fetchall()
            if tables != [("publication_intents",)] or [row[1] for row in columns] != [
                "request_digest", "request_id", "body", "phase", "observation",
                "grant_digest", "reason", "updated_at",
            ]:
                raise PublicationError("publication_state_schema")
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _database_file(path):
        metadata = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise PublicationError("publication_state_file")

    def close(self):
        try:
            if self._connection is not None:
                self._connection.close()
                self._connection = None
        finally:
            if self._lock is not None:
                os.close(self._lock)
                self._lock = None
            if self._root_descriptor is not None:
                os.close(self._root_descriptor)
                self._root_descriptor = None

    def find_id(self, request_id):
        row = self._connection.execute(
            "SELECT request_digest FROM publication_intents WHERE request_id=?", (request_id,)
        ).fetchone()
        return self.get(row[0]) if row else None

    def get(self, request_digest):
        require_digest(request_digest)
        row = self._connection.execute(
            "SELECT body, phase, observation, grant_digest, reason, updated_at "
            "FROM publication_intents WHERE request_digest=?", (request_digest,)
        ).fetchone()
        if row is None:
            raise PublicationError("publication_request_unavailable")
        request = PublicationRequestV1.from_dict(decode(bytes(row[0])))
        if request.request_digest != request_digest or row[1] not in PHASES:
            raise PublicationError("publication_state_record")
        return {
            "schema_version": 1, "scope": "owner-controlled-filesystem",
            "request": request.to_dict(), "phase": row[1],
            "observation": decode(bytes(row[2])) if row[2] is not None else None,
            "grant_digest": row[3], "reason": row[4], "updated_at": row[5],
            "http_origin_verified": False,
        }

    def prepare(self, request):
        if self._readonly:
            raise PublicationError("publication_state_readonly")
        body = canonical(request.to_dict())
        try:
            self._connection.execute(
                "INSERT INTO publication_intents "
                "(request_digest,request_id,body,phase,updated_at) VALUES (?,?,?,?,?)",
                (request.request_digest, request.request_id, body, "prepared", _now()),
            )
        except sqlite3.IntegrityError:
            prior = self.find_id(request.request_id)
            if prior is None or canonical(prior["request"]) != body:
                raise PublicationError("publication_idempotency_conflict") from None
        return self.get(request.request_digest)

    def transition(self, request, expected, phase, *, observation=None, grant_digest=None, reason=None):
        if self._readonly or phase not in PHASES:
            raise PublicationError("publication_state_transition")
        changed = self._connection.execute(
            "UPDATE publication_intents SET phase=?, observation=?, "
            "grant_digest=COALESCE(?,grant_digest), reason=?, updated_at=? "
            "WHERE request_digest=? AND phase=? AND body=?",
            (phase, canonical(observation) if observation is not None else None,
             grant_digest, reason, _now(), request.request_digest, expected,
             canonical(request.to_dict())),
        ).rowcount
        if changed != 1:
            raise PublicationError("publication_state_conflict")
        return self.get(request.request_digest)


class LandingPublicationCoordinator:
    def __init__(self, store: PublicationStore, adapter: FilesystemLandingPublisher, artifact_loader):
        self.store = store
        self.adapter = adapter
        self._artifact_loader = artifact_loader

    def prepare(self, *, request_id, action, artifact_ref=None, restore_from=None):
        previous = self.store.find_id(request_id)
        if previous is not None:
            facts = previous["request"]
            if (facts["action"], facts["artifact_ref"], facts["restore_from"]) != (
                action, artifact_ref, restore_from
            ):
                raise PublicationError("publication_idempotency_conflict")
            return previous
        baseline = self.adapter.observe()
        artifact_digest = desired_release = desired_manifest = None
        if action in {"stage", "activate"}:
            bundle = self._artifact_loader(artifact_ref)
            bundle.validate()
            artifact_digest = desired_release = bundle.artifact_digest
            desired_manifest = bundle.artifact["manifest_digest"]
        elif action == "restore":
            prior = self.store.get(restore_from)
            activation = PublicationRequestV1.from_dict(prior["request"])
            if (
                activation.action != "activate" or prior["phase"] != "activated"
                or activation.target_digest != self.adapter.target.target_digest
                or baseline["release_id"] != activation.desired_release
                or baseline["manifest_digest"] != activation.desired_manifest
            ):
                raise PublicationError("publication_restore_chain")
            desired_release, desired_manifest = activation.baseline_release, activation.baseline_manifest
        else:
            raise PublicationError("publication_action")
        return self.store.prepare(PublicationRequestV1(
            1, request_id, action, self.adapter.target.target_digest,
            artifact_ref, artifact_digest, desired_release, desired_manifest,
            baseline["release_id"], baseline["manifest_digest"], restore_from,
        ))

    def apply(self, request_digest, authority):
        saved = self.store.get(request_digest)
        if saved["phase"] == "inflight":
            return self.reconcile(request_digest)
        if saved["phase"] != "prepared":
            return saved
        request = PublicationRequestV1.from_dict(saved["request"])
        self._target(request)
        observation = self.adapter.observe(request.desired_release)
        if self._achieved(request, observation):
            return self.store.transition(request, "prepared", self._success(request), observation=observation,
                                         reason="already_observed")
        if (observation["release_id"], observation["manifest_digest"]) != (
            request.baseline_release, request.baseline_manifest
        ):
            return self.store.transition(request, "prepared", "needs_human", observation=observation,
                                         reason="baseline_drift")
        bundle = None
        if request.action != "restore":
            bundle = self._artifact_loader(request.artifact_ref)
            bundle.validate()
            if (bundle.artifact_digest, bundle.artifact["manifest_digest"]) != (
                request.artifact_digest, request.desired_manifest
            ):
                raise PublicationError("publication_artifact_drift")
        # This callback must independently bind current control state and one
        # exact operation grant; its returned digest is retained before transport.
        grant_digest = require_digest(authority(request))
        self.store.transition(request, "prepared", "inflight", observation=observation,
                              grant_digest=grant_digest, reason="effect_intent_persisted")
        try:
            if request.action == "stage":
                self.adapter.stage(request, bundle)
            else:
                self.adapter.activate(request)
        except Exception:
            # Even an apparently local error after intent can mask a committed
            # filesystem operation. Reconciliation observes and never writes.
            return self.reconcile(request_digest)
        return self.reconcile(request_digest)

    def reconcile(self, request_digest):
        saved = self.store.get(request_digest)
        if saved["phase"] != "inflight":
            return saved
        request = PublicationRequestV1.from_dict(saved["request"])
        self._target(request)
        try:
            observation = self.adapter.observe(request.desired_release)
        except Exception:
            return self.store.transition(request, "inflight", "needs_human",
                                         reason="observation_unavailable_no_replay")
        if self._achieved(request, observation):
            return self.store.transition(request, "inflight", self._success(request),
                                         observation=observation, reason="effect_observed")
        return self.store.transition(request, "inflight", "needs_human", observation=observation,
                                     reason="effect_ambiguous_no_replay")

    def _target(self, request):
        if request.target_digest != self.adapter.target.target_digest:
            raise PublicationError("publication_target_drift")

    @staticmethod
    def _achieved(request, observation):
        if request.action == "stage":
            desired = observation["desired_staged"]
            return desired == {"release_id": request.desired_release,
                               "manifest_digest": request.desired_manifest}
        return (observation["release_id"], observation["manifest_digest"]) == (
            request.desired_release, request.desired_manifest
        )

    @staticmethod
    def _success(request):
        return {"stage": "staged", "activate": "activated", "restore": "restored"}[request.action]


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
