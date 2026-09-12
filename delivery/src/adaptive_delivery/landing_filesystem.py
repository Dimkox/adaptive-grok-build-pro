"""Real owner-controlled release directories and atomic current-pointer changes."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import io
import os
from pathlib import Path
import re
import stat
import zipfile

from .landing_publication_contracts import (
    MAX_DOCUMENT_BYTES, MAX_MEMBER_BYTES, PublicationBundle, PublicationError,
    PublicationRequestV1, PublicationTargetV1, canonical, decode, member_path,
    require_digest,
)


def private_root(path: Path) -> int:
    if not path.is_absolute() or ".." in path.parts:
        raise PublicationError("publication_root")
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            metadata = os.fstat(descriptor)
            sticky = metadata.st_uid == 0 and bool(metadata.st_mode & stat.S_ISVTX)
            if metadata.st_uid not in {0, os.geteuid()} or (metadata.st_mode & 0o022 and not sticky):
                raise PublicationError("publication_root_ancestry")
        metadata = os.fstat(descriptor)
        if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
            raise PublicationError("publication_root_owner")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def owned_lock(root: int, name: str, *, create: bool, exclusive: bool) -> int:
    flags = os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open(name, flags | (os.O_CREAT if create else 0), 0o600, dir_fd=root)
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise PublicationError("publication_lock_file")
        try:
            fcntl.flock(descriptor, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        except BlockingIOError:
            raise PublicationError("publication_writer_active") from None
        linked = os.stat(name, dir_fd=root, follow_symlinks=False)
        if (metadata.st_dev, metadata.st_ino) != (linked.st_dev, linked.st_ino):
            raise PublicationError("publication_lock_replaced")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


class FilesystemLandingPublisher:
    """Only a configured private root; no shell, network, remote path or cPanel API."""

    def __init__(self, target: PublicationTargetV1) -> None:
        self.target = target

    @contextmanager
    def _locked(self, *, exclusive: bool):
        root = private_root(Path(self.target.root))
        lock = None
        try:
            metadata = os.fstat(root)
            if (metadata.st_uid, metadata.st_dev, metadata.st_ino) != (
                self.target.owner_uid, self.target.device, self.target.inode
            ):
                raise PublicationError("publication_target_replaced")
            lock = owned_lock(root, ".publication.lock", create=False, exclusive=exclusive)
            yield root
        finally:
            if lock is not None:
                os.close(lock)
            os.close(root)

    def observe(self, desired_release: str | None = None) -> dict:
        with self._locked(exclusive=False) as root:
            current = self._current(root)
            staged = None
            if desired_release is not None:
                require_digest(desired_release)
                try:
                    staged = self._release(root, desired_release)
                except FileNotFoundError:
                    staged = None
            return {"schema_version": 1, "target_digest": self.target.target_digest,
                    **current, "desired_staged": staged}

    def stage(self, request: PublicationRequestV1, bundle: PublicationBundle) -> None:
        members = bundle.validate()
        artifact = bundle.artifact
        if (
            request.action != "stage" or request.target_digest != self.target.target_digest
            or request.artifact_digest != bundle.artifact_digest
            or request.desired_manifest != artifact["manifest_digest"]
        ):
            raise PublicationError("publication_request_binding")
        with self._locked(exclusive=True) as root:
            self._baseline(root, request)
            try:
                os.mkdir("releases", 0o700, dir_fd=root)
                os.fsync(root)
            except FileExistsError:
                pass
            releases = self._directory(root, "releases", mode=0o700)
            try:
                # mkdir is exclusive. A partial previous attempt is preserved,
                # never overwritten or resumed after an ambiguous side effect.
                os.mkdir(bundle.artifact_digest, 0o700, dir_fd=releases)
                release = self._directory(releases, bundle.artifact_digest, mode=0o700)
                try:
                    os.mkdir("site", 0o700, dir_fd=release)
                    site = self._directory(release, "site", mode=0o700)
                    try:
                        with zipfile.ZipFile(io.BytesIO(bundle.archive)) as archive:
                            for member in members:
                                self._install_member(site, member["path"], archive.read(member["path"]))
                        self._freeze_directories(site)
                    finally:
                        os.close(site)
                    self._write_file(release, "release.json", canonical({
                        "schema_version": 1, "artifact": artifact,
                        "manifest": decode(bundle.manifest_json),
                    }))
                    os.fchmod(release, 0o500)
                    os.fsync(release)
                finally:
                    os.close(release)
                os.fsync(releases)
            finally:
                os.close(releases)

    def activate(self, request: PublicationRequestV1) -> None:
        if request.action not in {"activate", "restore"} or request.target_digest != self.target.target_digest:
            raise PublicationError("publication_request_binding")
        with self._locked(exclusive=True) as root:
            self._baseline(root, request)
            if request.desired_release is None:
                if request.action != "restore":
                    raise PublicationError("publication_restore")
                os.unlink("current", dir_fd=root)
            else:
                target = self._release(root, request.desired_release)
                if target["manifest_digest"] != request.desired_manifest:
                    raise PublicationError("publication_desired_manifest")
                temporary = f".current-{request.request_digest}"
                os.symlink(f"releases/{request.desired_release}/site", temporary, dir_fd=root)
                os.replace(temporary, "current", src_dir_fd=root, dst_dir_fd=root)
            os.fsync(root)

    def _baseline(self, root: int, request: PublicationRequestV1) -> None:
        current = self._current(root)
        if (current["release_id"], current["manifest_digest"]) != (
            request.baseline_release, request.baseline_manifest
        ):
            raise PublicationError("publication_baseline_drift")

    def _current(self, root: int) -> dict:
        try:
            metadata = os.stat("current", dir_fd=root, follow_symlinks=False)
        except FileNotFoundError:
            return {"release_id": None, "manifest_digest": None}
        if not stat.S_ISLNK(metadata.st_mode) or metadata.st_uid != self.target.owner_uid:
            raise PublicationError("publication_current_type")
        value = os.readlink("current", dir_fd=root)
        match = re.fullmatch(r"releases/([0-9a-f]{64})/site", value)
        if match is None:
            raise PublicationError("publication_current_path")
        return self._release(root, match.group(1))

    def _release(self, root: int, release_id: str) -> dict:
        require_digest(release_id)
        releases = self._directory(root, "releases", mode=0o700)
        release = None
        try:
            release = self._directory(releases, release_id, mode=0o500)
            if set(os.listdir(release)) != {"site", "release.json"}:
                raise PublicationError("publication_release_inventory")
            record = decode(self._read_file(release, "release.json", MAX_DOCUMENT_BYTES))
            if set(record) != {"schema_version", "artifact", "manifest"} or record["schema_version"] != 1:
                raise PublicationError("publication_release_record")
            artifact, manifest = record["artifact"], record["manifest"]
            if not isinstance(artifact, dict) or not isinstance(manifest, dict):
                raise PublicationError("publication_release_record")
            artifact_facts = {key: value for key, value in artifact.items() if key != "artifact_digest"}
            if (
                artifact.get("artifact_digest") != release_id
                or hashlib.sha256(canonical({"contract": "adaptive-factory.landing-site-artifact/v1",
                                            **artifact_facts})).hexdigest() != release_id
                or hashlib.sha256(canonical(manifest)).hexdigest() != artifact.get("manifest_digest")
            ):
                raise PublicationError("publication_release_digest")
            members = manifest.get("members")
            if not isinstance(members, list) or not 1 <= len(members) <= 1_024:
                raise PublicationError("publication_release_members")
            site = self._directory(release, "site", mode=0o500)
            try:
                expected = {member["path"]: member for member in members}
                if len(expected) != len(members):
                    raise PublicationError("publication_release_members")
                actual = self._walk(site)
                if set(actual) != set(expected):
                    raise PublicationError("publication_release_inventory")
                for path, body in actual.items():
                    member = expected[path]
                    member_path(path)
                    if (
                        member["size_bytes"] != len(body)
                        or member["sha256"] != hashlib.sha256(body).hexdigest()
                        or member["candidate_object_id"] != hashlib.sha1(
                            f"blob {len(body)}\0".encode() + body, usedforsecurity=False
                        ).hexdigest()
                    ):
                        raise PublicationError("publication_release_content")
            finally:
                os.close(site)
            return {"release_id": release_id, "manifest_digest": artifact["manifest_digest"]}
        finally:
            if release is not None:
                os.close(release)
            os.close(releases)

    def _directory(self, parent, name, *, mode):
        descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                             dir_fd=parent)
        metadata = os.fstat(descriptor)
        if (metadata.st_uid != self.target.owner_uid or metadata.st_dev != self.target.device
            or stat.S_IMODE(metadata.st_mode) != mode):
            os.close(descriptor)
            raise PublicationError("publication_directory_owner")
        return descriptor

    def _read_file(self, parent, name, maximum):
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
                or metadata.st_uid != self.target.owner_uid or metadata.st_dev != self.target.device
                or stat.S_IMODE(metadata.st_mode) != 0o400 or not 0 < metadata.st_size <= maximum
            ):
                raise PublicationError("publication_file_owner")
            value = bytearray()
            while chunk := os.read(descriptor, min(65_536, maximum + 1 - len(value))):
                value.extend(chunk)
                if len(value) > maximum:
                    raise PublicationError("publication_file_size")
            if len(value) != metadata.st_size:
                raise PublicationError("publication_file_changed")
            return bytes(value)
        finally:
            os.close(descriptor)

    def _walk(self, directory, prefix="", *, depth=0, budget=None):
        if budget is None:
            budget = {"nodes": 0, "bytes": 0}
        if depth > 8:
            raise PublicationError("publication_tree_depth")
        result = {}
        names = os.listdir(directory)
        if len(names) > 1_024:
            raise PublicationError("publication_tree_size")
        for name in names:
            budget["nodes"] += 1
            if budget["nodes"] > 8_192:
                raise PublicationError("publication_tree_size")
            path = f"{prefix}{name}"
            member_path(path)
            metadata = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if stat.S_ISDIR(metadata.st_mode):
                child = self._directory(directory, name, mode=0o500)
                try:
                    result.update(self._walk(child, path + "/", depth=depth + 1, budget=budget))
                finally:
                    os.close(child)
            else:
                result[path] = self._read_file(directory, name, MAX_MEMBER_BYTES)
                budget["bytes"] += len(result[path])
                if budget["bytes"] > 100 * 1_048_576:
                    raise PublicationError("publication_tree_size")
            if len(result) > 1_024 or sum(map(len, result.values())) > 100 * 1_048_576:
                raise PublicationError("publication_tree_size")
        return result

    def _install_member(self, site, path, body):
        parts = member_path(path)
        parent = os.dup(site)
        try:
            for part in parts[:-1]:
                try:
                    os.mkdir(part, 0o700, dir_fd=parent)
                except FileExistsError:
                    pass
                child = self._directory(parent, part, mode=0o700)
                os.close(parent)
                parent = child
            self._write_file(parent, parts[-1], body)
        finally:
            os.close(parent)

    @staticmethod
    def _write_file(parent, name, body):
        descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                             0o600, dir_fd=parent)
        try:
            remaining = memoryview(body)
            while remaining:
                count = os.write(descriptor, remaining)
                if count <= 0:
                    raise PublicationError("publication_short_write")
                remaining = remaining[count:]
            os.fchmod(descriptor, 0o400)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.fsync(parent)

    def _freeze_directories(self, directory):
        for name in os.listdir(directory):
            if stat.S_ISDIR(os.stat(name, dir_fd=directory, follow_symlinks=False).st_mode):
                child = self._directory(directory, name, mode=0o700)
                try:
                    self._freeze_directories(child)
                finally:
                    os.close(child)
        os.fchmod(directory, 0o500)
        os.fsync(directory)
