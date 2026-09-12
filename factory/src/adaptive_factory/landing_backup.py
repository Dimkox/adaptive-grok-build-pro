"""Offline, bounded landing snapshots. No provider replay or service commands."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
from urllib.parse import quote

from .contracts import canonical_json
from .landing_contracts import strict_json_object
from .landing_host import load_host_config
from .landing_server import _private_directory
from .landing_sqlite_store import APPLICATION_ID, SCHEMA_VERSION, _acquire_writer
from .settings import read_private_file


MAX_FILE = 512 * 1024 * 1024
MAX_TOTAL = 4 * 1024 * 1024 * 1024
MAX_FILES = 4096
DEADLINE_SECONDS = 180
_ARTIFACT_NAME = re.compile(r"therealaidarkfactory\.online-[0-9a-f]{64}\.zip(?:\.sha256)?")


class BackupError(RuntimeError):
    pass


class Budget:
    def __init__(self):
        self.deadline = time.monotonic() + DEADLINE_SECONDS
        self.total = 0

    def consume(self, amount=0):
        self.total += amount
        if time.monotonic() >= self.deadline or self.total > MAX_TOTAL:
            raise BackupError("snapshot_budget")


def _roots(config):
    return {"landing": config.settings.landing_state_path,
            "publication": config.publication_state,
            "artifacts": config.settings.landing_output_path}


def _sync(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _new_root(path, repository):
    if not path.is_absolute() or ".." in path.parts:
        raise BackupError("snapshot_path")
    _private_directory(path.parent, repository_root=repository)
    path.mkdir(mode=0o700)  # Refuse any pre-existing destination, including links.
    _sync(path.parent)


def _file_metadata(path):
    metadata = path.lstat()
    if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
            or not 0 <= metadata.st_size <= MAX_FILE):
        raise BackupError("snapshot_private_file")
    return metadata


def _stable(metadata):
    return (metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_uid,
            metadata.st_nlink, metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns)


def _copy(source, destination, budget):
    before = _file_metadata(source)
    digest = hashlib.sha256()
    count = 0
    with ExitStack() as stack:
        descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        stack.callback(os.close, descriptor)
        if _stable(os.fstat(descriptor)) != _stable(before):
            raise BackupError("snapshot_file_changed")
        target = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        stack.callback(os.close, target)
        while True:
            budget.consume()
            raw = os.read(descriptor, 1024 * 1024)
            if not raw:
                break
            count += len(raw)
            budget.consume(len(raw))
            if count > MAX_FILE:
                raise BackupError("snapshot_file_size")
            digest.update(raw)
            remaining = memoryview(raw)
            while remaining:
                written = os.write(target, remaining)
                if written <= 0:
                    raise BackupError("snapshot_write")
                remaining = remaining[written:]
        if _stable(os.fstat(descriptor)) != _stable(before) or count != before.st_size:
            raise BackupError("snapshot_file_changed")
        os.fsync(target)
    return {"size": count, "sha256": digest.hexdigest()}


def _snapshot(database, destination, identity, budget):
    _file_metadata(database)
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(descriptor)
    source = sqlite3.connect(f"file:{quote(str(database), safe='/')}?mode=ro", uri=True, timeout=5)
    target = None
    try:
        source.execute("PRAGMA query_only=ON")
        source.execute("PRAGMA trusted_schema=OFF")
        actual = (source.execute("PRAGMA application_id").fetchone()[0],
                  source.execute("PRAGMA user_version").fetchone()[0])
        if actual != identity:
            raise BackupError("snapshot_schema")
        target = sqlite3.connect(destination, timeout=5)
        page_size = source.execute("PRAGMA page_size").fetchone()[0]

        def progress(_status, _remaining, total):
            budget.consume()
            if total * page_size > MAX_FILE:
                raise BackupError("snapshot_database_size")

        source.backup(target, pages=128, progress=progress, sleep=0.01)
        # The backup API captures WAL-visible committed pages. Normalize the
        # standalone destination so restoration does not depend on side files.
        target.execute("PRAGMA journal_mode=DELETE")
        target.close()
        target = None
        _file_metadata(destination)
        descriptor = os.open(destination, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if target is not None:
            target.close()
        source.close()


def _hash_file(path, budget):
    metadata = _file_metadata(path)
    digest = hashlib.sha256()
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        count = 0
        while True:
            budget.consume()
            raw = os.read(descriptor, 1024 * 1024)
            if not raw:
                break
            count += len(raw)
            budget.consume(len(raw))
            if count > MAX_FILE:
                raise BackupError("snapshot_file_size")
            digest.update(raw)
        if count != metadata.st_size or _stable(os.fstat(descriptor)) != _stable(metadata):
            raise BackupError("snapshot_file_changed")
        return {"size": count, "sha256": digest.hexdigest()}
    finally:
        os.close(descriptor)


def create_snapshot(config, destination):
    from adaptive_delivery.landing_filesystem import owned_lock, private_root
    from adaptive_delivery.landing_publication import APPLICATION_ID as PUBLICATION_ID

    roots = _roots(config)
    if any(destination == root or root in destination.parents or destination in root.parents
           for root in (*roots.values(), config.control_repository, config.settings.landing_source_path)):
        raise BackupError("snapshot_destination_overlap")
    for root in roots.values():
        _private_directory(root, repository_root=config.control_repository)
    budget = Budget()
    entries = []
    with ExitStack() as locks:
        # Taking the same lifetime locks is the offline boundary. A running
        # landing host or publication writer makes this fail before snapshot.
        locks.callback(os.close, _acquire_writer(roots["landing"]))
        descriptor = private_root(roots["publication"])
        locks.callback(os.close, descriptor)
        locks.callback(os.close, owned_lock(descriptor, ".intent-writer.lock", create=True, exclusive=True))
        _new_root(destination, config.control_repository)
        for category in roots:
            (destination / category).mkdir(mode=0o700)
        for category, filename, identity in (
            ("landing", "landing.sqlite3", (APPLICATION_ID, SCHEMA_VERSION)),
            ("publication", "publication.sqlite3", (PUBLICATION_ID, 1)),
        ):
            source = roots[category] / filename
            if category == "publication" and not source.exists():
                continue
            target = destination / category / filename
            _snapshot(source, target, identity, budget)
            entries.append({"category": category, "name": filename, **_hash_file(target, budget)})
        with os.scandir(roots["artifacts"]) as candidates:
            for item in candidates:
                budget.consume()
                if len(entries) >= MAX_FILES or not _ARTIFACT_NAME.fullmatch(item.name):
                    raise BackupError("snapshot_artifact_inventory")
                entries.append({"category": "artifacts", "name": item.name,
                                **_copy(Path(item.path), destination / "artifacts" / item.name, budget)})
        manifest = {"schema_version": 1, "kind": "adaptive-landing-offline-snapshot",
                    "roots": {key: str(value) for key, value in roots.items()},
                    "entries": sorted(entries, key=lambda item: (item["category"], item["name"])),
                    "provider_replay": False, "publication_target_included": False}
        raw = canonical_json(manifest)
        if len(raw) > 2 * 1024 * 1024:
            raise BackupError("snapshot_manifest_size")
        for category in roots:
            _sync(destination / category)
        descriptor = os.open(destination / "manifest.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        _sync(destination)
        return {"status": "snapshot_saved", "manifest_sha256": hashlib.sha256(raw).hexdigest(),
                "files": len(entries), "provider_replay": False}


def restore_snapshot(config, snapshot, manifest_sha256):
    roots = _roots(config)
    _private_directory(snapshot, repository_root=config.control_repository)
    raw = read_private_file(snapshot / "manifest.json", 2 * 1024 * 1024)
    if not re.fullmatch(r"[0-9a-f]{64}", manifest_sha256) or hashlib.sha256(raw).hexdigest() != manifest_sha256:
        raise BackupError("restore_manifest_digest")
    manifest = strict_json_object(raw, maximum=2 * 1024 * 1024)
    if (set(manifest) != {"schema_version", "kind", "roots", "entries", "provider_replay", "publication_target_included"}
            or manifest["schema_version"] != 1 or manifest["kind"] != "adaptive-landing-offline-snapshot"
            or manifest["roots"] != {key: str(value) for key, value in roots.items()}
            or manifest["provider_replay"] is not False or manifest["publication_target_included"] is not False
            or not isinstance(manifest["entries"], list) or not 1 <= len(manifest["entries"]) <= MAX_FILES):
        raise BackupError("restore_manifest")
    if config.settings.landing_live_enabled:
        raise BackupError("restore_requires_disabled_provider")
    budget = Budget()
    seen = set()
    for entry in manifest["entries"]:
        if not isinstance(entry, dict) or set(entry) != {"category", "name", "size", "sha256"}:
            raise BackupError("restore_entry")
        category, name = entry["category"], entry["name"]
        if not isinstance(category, str) or category not in roots or not isinstance(name, str):
            raise BackupError("restore_entry")
        allowed = (_ARTIFACT_NAME.fullmatch(name) if category == "artifacts"
                   else name == {"landing": "landing.sqlite3", "publication": "publication.sqlite3"}[category])
        if not allowed or (category, name) in seen or type(entry["size"]) is not int:
            raise BackupError("restore_inventory")
        seen.add((category, name))
        _private_directory(snapshot / category, repository_root=config.control_repository)
        if _hash_file(snapshot / category / name, budget) != {"size": entry["size"], "sha256": entry["sha256"]}:
            raise BackupError("restore_content_digest")
    if ("landing", "landing.sqlite3") not in seen:
        raise BackupError("restore_landing_missing")
    # Retained artifacts contain absolute output paths. Preserve their exact
    # locations and restore only after operators move old inactive roots away.
    # Never rewrite sealed records or overwrite an existing data root.
    for root in roots.values():
        _private_directory(root.parent, repository_root=config.control_repository)
        if root.exists() or root.is_symlink():
            raise BackupError("restore_destination_exists")
    with ExitStack() as locks:
        for root in roots.values():
            _new_root(root, config.control_repository)
        from adaptive_delivery.landing_filesystem import owned_lock, private_root

        locks.callback(os.close, _acquire_writer(roots["landing"]))
        descriptor = private_root(roots["publication"])
        locks.callback(os.close, descriptor)
        locks.callback(os.close, owned_lock(descriptor, ".intent-writer.lock", create=True, exclusive=True))
        for entry in manifest["entries"]:
            category, name = entry["category"], entry["name"]
            observed = _copy(snapshot / category / name, roots[category] / name, budget)
            if observed != {"size": entry["size"], "sha256": entry["sha256"]}:
                raise BackupError("restore_content_changed")
        for root in roots.values():
            _sync(root)
    return {"status": "restored_inactive", "provider_replay": False,
            "publication_reconciliation_required": True}


def main():
    parser = argparse.ArgumentParser(description="Offline landing snapshot and same-path inactive restore")
    parser.add_argument("action", choices=("backup", "restore"))
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--manifest-sha256")
    args = parser.parse_args()
    try:
        config = load_host_config(args.config)
        result = (create_snapshot(config, args.snapshot) if args.action == "backup"
                  else restore_snapshot(config, args.snapshot, args.manifest_sha256 or ""))
    except Exception as exc:
        reason = str(exc) if isinstance(exc, BackupError) else "snapshot_unavailable"
        print(json.dumps({"status": "needs_human", "reason": reason}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
