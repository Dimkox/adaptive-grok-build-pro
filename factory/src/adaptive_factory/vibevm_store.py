"""Linux-only, data-only package store for the optional VibeVM integration.

This module resolves, admits, replays and projects Factory packages.  It does
not execute VibeVM, package hooks, or claim an upstream adapter qualification.
"""

from __future__ import annotations

import fcntl
import errno
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile


# Reviewed provenance for the optional upstream adapter surface.  These pins do
# not mean that this data-only store executes or qualifies that adapter.
UPSTREAM_ADAPTER_COMMIT = "0b63caa86e80ff670dc2a62ff529079b91d08e4d"
UPSTREAM_ADAPTER_TREE = "1ff4963aeea1f3f0a925485437b8dcf7130bf17d"


class VibeVMStoreError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _valid_digest(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _scope(value, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 128
        or value.startswith(("/", "."))
        or ".." in value.split("/")
        or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/" for character in value)
    ):
        raise VibeVMStoreError(f"invalid_{field}")
    # Reversible encoding prevents aliases such as a/b and a_b.
    return value.encode("utf-8").hex()


def reconcile_boot_block(owner_text: str, managed_text: str) -> str:
    """Replace one owned block while preserving all owner-authored bytes."""
    start = "<!-- adaptive-vibevm -->"
    end = "<!-- /adaptive-vibevm -->"
    if owner_text.count(start) != owner_text.count(end):
        raise VibeVMStoreError("boot_block_corrupt")
    if owner_text.count(start) > 1:
        raise VibeVMStoreError("boot_block_conflict")
    block = f"{start}\n{managed_text.rstrip()}\n{end}\n"
    if start not in owner_text:
        separator = "" if owner_text.endswith("\n") else "\n"
        return owner_text + separator + block
    before, remainder = owner_text.split(start, 1)
    _, after = remainder.split(end, 1)
    if after.startswith("\n"):
        after = after[1:]
    return before + block + after


class VibeVMStore:
    """Tenant/repository-scoped immutable package and generation store."""

    def __init__(
        self,
        root,
        *,
        tenant_id: str,
        repository_id: str,
        allowed_origins,
        max_files: int = 128,
        max_bytes: int = 262_144,
        max_depth: int = 12,
    ):
        if max_files < 1 or max_bytes < 1 or max_depth < 1:
            raise VibeVMStoreError("invalid_bounds")
        tenant = _scope(tenant_id, "tenant_id")
        repository = _scope(repository_id, "repository_id")
        self.root = Path(root).resolve() / "tenants" / tenant / "repositories" / repository
        self.objects = self.root / "objects"
        self.generations = self.root / "generations"
        self.active_path = self.root / "active"
        self.allowed_origins = frozenset(allowed_origins)
        self.max_files = max_files
        self.max_bytes = max_bytes
        self.max_depth = max_depth

    @staticmethod
    def _coordinate(item) -> str:
        return f"{item['name']}@{item['version']}"

    @staticmethod
    def _validate_item(item) -> None:
        required = {"name", "version", "sha256", "origin", "dependencies", "qualified", "revoked"}
        if not isinstance(item, dict) or set(item) != required:
            raise VibeVMStoreError("invalid_package")
        _scope(item["name"], "package_name")
        _scope(item["version"], "package_version")
        _scope(item["origin"], "package_origin")
        if not _valid_digest(item["sha256"]):
            raise VibeVMStoreError("invalid_digest")
        if not isinstance(item["dependencies"], dict) or type(item["qualified"]) is not bool or type(item["revoked"]) is not bool:
            raise VibeVMStoreError("invalid_package")
        for name, version in item["dependencies"].items():
            _scope(name, "dependency_name")
            _scope(version, "dependency_version")

    def resolve(self, packages, *, overrides=()):
        by_name = {}
        for source in packages:
            self._validate_item(source)
            item = dict(source)
            item["dependencies"] = dict(source["dependencies"])
            if item["name"] in by_name:
                raise VibeVMStoreError(f"duplicate_package:{item['name']}")
            by_name[item["name"]] = item
        override_list = list(overrides)
        if len(override_list) != len(set(override_list)):
            duplicate = next(name for name in override_list if override_list.count(name) > 1)
            raise VibeVMStoreError(f"ambiguous_override:{duplicate}")
        for name in override_list:
            _scope(name, "override")

        order, visiting, visited = [], [], set()

        def visit(name):
            if name in visiting:
                cycle = visiting[visiting.index(name) :] + [name]
                raise VibeVMStoreError("dependency_cycle:" + "->".join(cycle))
            if name in visited:
                return
            if name not in by_name:
                raise VibeVMStoreError(f"missing_dependency:{name}")
            visiting.append(name)
            item = by_name[name]
            for dependency in sorted(item["dependencies"]):
                expected = item["dependencies"][dependency]
                actual = by_name.get(dependency, {}).get("version")
                if actual is None:
                    raise VibeVMStoreError(f"missing_dependency:{name}->{dependency}")
                if actual != expected:
                    raise VibeVMStoreError(f"version_conflict:{name}->{dependency}:{expected}!={actual}")
                visit(dependency)
            visiting.pop()
            visited.add(name)
            order.append(name)

        for name in sorted(by_name):
            visit(name)
        locked = [by_name[name] for name in order]
        graph = {"packages": locked, "overrides": sorted(override_list)}
        return {"schema_version": 1, **graph, "graph_digest": _digest(_canonical(graph))}

    def object_path(self, digest: str) -> Path:
        if not _valid_digest(digest):
            raise VibeVMStoreError("invalid_digest")
        return self.objects / digest

    def admit(self, item, payload: bytes) -> Path:
        self._validate_item(item)
        coordinate = self._coordinate(item)
        if not isinstance(payload, bytes):
            raise VibeVMStoreError("invalid_payload")
        if item["origin"] not in self.allowed_origins:
            raise VibeVMStoreError(f"origin_not_allowed:{item['origin']}")
        if item["revoked"]:
            raise VibeVMStoreError(f"package_revoked:{coordinate}")
        if not item["qualified"]:
            raise VibeVMStoreError(f"package_unqualified:{coordinate}")
        if _digest(payload) != item["sha256"]:
            raise VibeVMStoreError(f"digest_mismatch:{coordinate}")
        self.objects.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = self.object_path(item["sha256"])
        if target.exists():
            if not target.is_file() or target.is_symlink() or _digest(target.read_bytes()) != item["sha256"]:
                raise VibeVMStoreError(f"immutable_object_conflict:{coordinate}")
            return target
        descriptor, temporary_name = tempfile.mkstemp(prefix=".admit-", dir=self.objects)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            temporary.chmod(0o400)
            try:
                os.link(temporary, target)
            except FileExistsError:
                if not target.is_file() or target.is_symlink() or _digest(target.read_bytes()) != item["sha256"]:
                    raise VibeVMStoreError(f"immutable_object_conflict:{coordinate}") from None
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def replay(self, lock):
        if not isinstance(lock, dict) or set(lock) != {"schema_version", "packages", "overrides", "graph_digest"} or lock["schema_version"] != 1:
            raise VibeVMStoreError("invalid_lock")
        graph = {"packages": lock["packages"], "overrides": lock["overrides"]}
        if not _valid_digest(lock["graph_digest"]) or _digest(_canonical(graph)) != lock["graph_digest"]:
            raise VibeVMStoreError("lock_digest_mismatch")
        result = {}
        for item in lock["packages"]:
            self._validate_item(item)
            coordinate = self._coordinate(item)
            if item["origin"] not in self.allowed_origins:
                raise VibeVMStoreError(f"origin_not_allowed:{item['origin']}")
            if item["revoked"]:
                raise VibeVMStoreError(f"package_revoked:{coordinate}")
            if not item["qualified"]:
                raise VibeVMStoreError(f"package_unqualified:{coordinate}")
            target = self.object_path(item["sha256"])
            if not target.is_file() or target.is_symlink():
                raise VibeVMStoreError(f"missing_package:{coordinate}")
            payload = target.read_bytes()
            if _digest(payload) != item["sha256"]:
                raise VibeVMStoreError(f"digest_mismatch:{coordinate}")
            result[coordinate] = payload
        return result

    def _project(self, payload: bytes, destination: Path, coordinate: str) -> None:
        try:
            archive = zipfile.ZipFile(io.BytesIO(payload))
        except (zipfile.BadZipFile, OSError):
            raise VibeVMStoreError(f"invalid_archive:{coordinate}") from None
        with archive:
            members = archive.infolist()
            if len(members) > self.max_files:
                raise VibeVMStoreError("file_count_exceeded")
            total, seen = 0, set()
            for member in members:
                path = PurePosixPath(member.filename)
                if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
                    raise VibeVMStoreError("path_escape")
                if len(path.parts) > self.max_depth:
                    raise VibeVMStoreError("path_depth_exceeded")
                if member.filename in seen:
                    raise VibeVMStoreError(f"duplicate_member:{member.filename}")
                seen.add(member.filename)
                mode = member.external_attr >> 16
                file_type = stat.S_IFMT(mode)
                if stat.S_ISLNK(mode) or file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise VibeVMStoreError(f"non_regular_member:{member.filename}")
                lowered = tuple(part.lower() for part in path.parts)
                if lowered[0] in ("hooks", "scripts") or lowered[-1] in ("install.sh", "build.sh", "postinstall"):
                    raise VibeVMStoreError("lifecycle_hook_forbidden")
                if member.is_dir():
                    continue
                total += member.file_size
                if total > self.max_bytes:
                    raise VibeVMStoreError("expanded_size_exceeded")
                data = archive.read(member)
                if len(data) != member.file_size:
                    raise VibeVMStoreError("archive_size_mismatch")
                if path.suffix.lower() == ".xml" and (b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper()):
                    raise VibeVMStoreError(f"xml_external_entity_forbidden:{member.filename}")
                target = destination.joinpath(*path.parts)
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                target.write_bytes(data)
                target.chmod(0o400)

    def materialize(self, lock, owner_text: str, managed_text: str, *, crash_before_switch=False) -> str:
        boot = reconcile_boot_block(owner_text, managed_text)
        payloads = self.replay(lock)
        identity = _digest(_canonical({"lock": lock, "boot": boot}))
        self.generations.mkdir(parents=True, exist_ok=True, mode=0o700)
        final = self.generations / identity
        staging = Path(tempfile.mkdtemp(prefix=".generation-", dir=self.generations))
        try:
            projection = staging / "projection"
            projection.mkdir(mode=0o700)
            for item in lock["packages"]:
                coordinate = self._coordinate(item)
                self._project(payloads[coordinate], projection / coordinate, coordinate)
            (staging / "boot.md").write_text(boot, encoding="utf-8")
            (staging / "lock.json").write_bytes(_canonical(lock) + b"\n")
            if final.exists():
                shutil.rmtree(staging)
            else:
                try:
                    os.replace(staging, final)
                except OSError as error:
                    # Concurrent identical materializations converge on the
                    # same content-addressed generation.
                    if error.errno not in (errno.EEXIST, errno.ENOTEMPTY) or not final.is_dir() or final.is_symlink():
                        raise
                    shutil.rmtree(staging)
            if crash_before_switch:
                raise VibeVMStoreError("simulated_crash")
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            with (self.root / ".generation.lock").open("a+b") as update_lock:
                fcntl.flock(update_lock, fcntl.LOCK_EX)
                descriptor, pointer_name = tempfile.mkstemp(prefix=".active-", dir=self.root)
                pointer = Path(pointer_name)
                try:
                    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                        output.write(identity + "\n")
                        output.flush()
                        os.fsync(output.fileno())
                    os.replace(pointer, self.active_path)
                finally:
                    pointer.unlink(missing_ok=True)
            return identity
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    def active_generation(self):
        if not self.active_path.is_file() or self.active_path.is_symlink():
            return None
        value = self.active_path.read_text(encoding="utf-8").strip()
        if not _valid_digest(value) or not (self.generations / value).is_dir():
            raise VibeVMStoreError("active_generation_corrupt")
        return value

    def reconcile(self) -> int:
        """Remove interrupted staging directories without changing active state."""
        if not self.generations.is_dir():
            return 0
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        removed = 0
        with (self.root / ".generation.lock").open("a+b") as update_lock:
            fcntl.flock(update_lock, fcntl.LOCK_EX)
            for candidate in self.generations.iterdir():
                if candidate.is_dir() and not candidate.is_symlink() and candidate.name.startswith(".generation-"):
                    shutil.rmtree(candidate)
                    removed += 1
        return removed
