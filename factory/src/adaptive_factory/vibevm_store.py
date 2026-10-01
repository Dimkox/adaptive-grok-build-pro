"""Linux-only, data-only package store for the optional VibeVM integration."""

from __future__ import annotations

import copy
import errno
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import unicodedata
import xml.parsers.expat
import zipfile


UPSTREAM_ADAPTER_COMMIT = "0b63caa86e80ff670dc2a62ff529079b91d08e4d"
UPSTREAM_ADAPTER_TREE = "1ff4963aeea1f3f0a925485437b8dcf7130bf17d"


class VibeVMStoreError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _valid_digest(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _scope(value, field: str) -> str:
    if (not isinstance(value, str) or not value or len(value) > 128 or value.startswith(("/", "."))
            or ".." in value.split("/") or any(character not in
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/" for character in value)):
        raise VibeVMStoreError(f"invalid_{field}")
    return value.encode().hex()


def _validate_item(item) -> None:
    required = {"name", "version", "sha256", "origin", "dependencies", "qualified", "revoked"}
    if not isinstance(item, dict) or set(item) != required:
        raise VibeVMStoreError("invalid_package")
    for key in ("name", "version", "origin"):
        _scope(item[key], f"package_{key}")
    if not _valid_digest(item["sha256"]):
        raise VibeVMStoreError("invalid_digest")
    if not isinstance(item["dependencies"], dict) or type(item["qualified"]) is not bool or type(item["revoked"]) is not bool:
        raise VibeVMStoreError("invalid_package")
    for name, version in item["dependencies"].items():
        _scope(name, "dependency_name")
        _scope(version, "dependency_version")


def _lock_item(item):
    required = {"name", "version", "sha256", "origin", "dependencies"}
    if not isinstance(item, dict) or set(item) != required:
        raise VibeVMStoreError("invalid_lock_package")
    candidate = {**item, "qualified": True, "revoked": False}
    _validate_item(candidate)
    return item


class StaticPackageRegistry:
    """Injectable trusted registry for tests and offline owner-pinned catalogs."""

    def __init__(self, packages=()):
        self._packages = {}
        for item in packages:
            self.register(item)

    def register(self, item) -> None:
        _validate_item(item)
        self._packages[(item["name"], item["version"])] = copy.deepcopy(item)

    def get_package(self, name: str, version: str):
        item = self._packages.get((name, version))
        return copy.deepcopy(item) if item is not None else None


def reconcile_boot_block(owner_text: str, managed_text: str) -> str:
    start, end = "<!-- adaptive-vibevm -->", "<!-- /adaptive-vibevm -->"
    if not isinstance(owner_text, str) or not isinstance(managed_text, str):
        raise VibeVMStoreError("invalid_boot_block")
    if start in managed_text or end in managed_text:
        raise VibeVMStoreError("boot_block_injection")
    if owner_text.count(start) != owner_text.count(end):
        raise VibeVMStoreError("boot_block_corrupt")
    if owner_text.count(start) > 1:
        raise VibeVMStoreError("boot_block_conflict")
    block = f"{start}\n{managed_text.rstrip()}\n{end}\n"
    if start not in owner_text:
        return owner_text + ("" if owner_text.endswith("\n") else "\n") + block
    before, remainder = owner_text.split(start, 1)
    _, after = remainder.split(end, 1)
    return before + block + (after[1:] if after.startswith("\n") else after)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class VibeVMStore:
    capability = "factory_package_store_v1"

    def __init__(self, root, *, tenant_id: str, repository_id: str, registry,
                 max_files: int = 128, max_bytes: int = 262_144, max_depth: int = 12):
        if max_files < 1 or max_bytes < 1 or max_depth < 1 or not hasattr(registry, "get_package"):
            raise VibeVMStoreError("invalid_configuration")
        base = Path(root).absolute()
        self._pins, self._fds, self._closed = [], {}, False
        try:
            self._pin(base, "store_root")
            tenant, repository = _scope(tenant_id, "tenant_id"), _scope(repository_id, "repository_id")
            tenant_root = self._child(base, "tenants")
            tenant_path = self._child(tenant_root, tenant)
            repositories = self._child(tenant_path, "repositories")
            self.root = self._child(repositories, repository)
            self.objects = self._child(self.root, "objects")
            self.generations = self._child(self.root, "generations")
            self.active_path = self.root / "active"
            self.registry = registry
            self.max_files, self.max_bytes, self.max_depth = max_files, max_bytes, max_depth
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        descriptors = tuple(set(self._fds.values()))
        self._fds.clear()
        self._pins.clear()
        for descriptor in descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass

    def __enter__(self):
        self._check_paths()
        return self

    def __exit__(self, _exception_type, _exception, _traceback):
        self.close()
        return False

    def __del__(self):
        try:
            self.close()
        except Exception:
            self._closed = True

    def _pin(self, path: Path, code: str, descriptor=None) -> Path:
        registered = False
        try:
            try:
                value = path.lstat()
            except FileNotFoundError:
                raise VibeVMStoreError(f"{code}_missing") from None
            if (not stat.S_ISDIR(value.st_mode) or stat.S_ISLNK(value.st_mode)
                    or value.st_uid != os.geteuid() or value.st_mode & 0o022):
                raise VibeVMStoreError(f"{code}_unsafe")
            descriptor = self._open_path(path) if descriptor is None else descriptor
            opened = os.fstat(descriptor)
            if (opened.st_dev, opened.st_ino) != (value.st_dev, value.st_ino):
                raise VibeVMStoreError("store_path_changed")
            self._pins.append((path, value.st_dev, value.st_ino, value.st_uid))
            self._fds[path] = descriptor
            registered = True
            return path
        finally:
            if descriptor is not None and not registered:
                os.close(descriptor)

    @staticmethod
    def _open_path(path: Path) -> int:
        descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        try:
            for part in path.parts[1:]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            return descriptor
        except OSError as error:
            os.close(descriptor)
            raise VibeVMStoreError("store_path_unsafe") from error

    def _child(self, parent: Path, name: str) -> Path:
        descriptor = self._fds[parent]
        try:
            try:
                os.mkdir(name, mode=0o700, dir_fd=descriptor)
                os.fsync(descriptor)
            except FileExistsError:
                pass
            child_descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
        except OSError as error:
            raise VibeVMStoreError("store_path_unsafe") from error
        return self._pin(parent / name, "store_path", child_descriptor)

    def _fd_path(self, path: Path) -> Path:
        return Path(f"/proc/self/fd/{self._fds[path]}")

    def _check_paths(self) -> None:
        if self._closed:
            raise VibeVMStoreError("store_closed")
        for path, device, inode, owner in self._pins:
            try:
                value = os.fstat(self._fds[path])
                visible = path.lstat()
            except (OSError, VibeVMStoreError):
                raise VibeVMStoreError("store_path_changed") from None
            if (stat.S_ISLNK(value.st_mode) or not stat.S_ISDIR(value.st_mode)
                    or (value.st_dev, value.st_ino, value.st_uid) != (device, inode, owner)
                    or (visible.st_dev, visible.st_ino) != (device, inode)
                    or value.st_mode & 0o022):
                raise VibeVMStoreError("store_path_changed")

    @staticmethod
    def _coordinate(item) -> str:
        return f"{item['name']}@{item['version']}"

    def _authority(self, item, *, lifecycle_flexible=False):
        _validate_item(item)
        coordinate = self._coordinate(item)
        authoritative = self.registry.get_package(item["name"], item["version"])
        self._check_paths()
        if authoritative is None:
            raise VibeVMStoreError(f"package_unknown:{coordinate}")
        _validate_item(authoritative)
        compared = ("name", "version", "sha256", "origin", "dependencies") if lifecycle_flexible else tuple(item)
        if any(item[key] != authoritative[key] for key in compared):
            raise VibeVMStoreError(f"registry_mismatch:{coordinate}")
        return authoritative

    def resolve(self, packages, *, overrides=()):
        self._check_paths()
        by_name = {}
        for supplied in packages:
            item = self._authority(supplied)
            if item["name"] in by_name:
                raise VibeVMStoreError(f"duplicate_package:{item['name']}")
            by_name[item["name"]] = item
        overrides = list(overrides)
        if len(overrides) != len(set(overrides)):
            duplicate = next(name for name in overrides if overrides.count(name) > 1)
            raise VibeVMStoreError(f"ambiguous_override:{duplicate}")
        for value in overrides:
            _scope(value, "override")
        order, visiting, visited = [], [], set()

        def visit(name):
            if name in visiting:
                cycle = visiting[visiting.index(name):] + [name]
                raise VibeVMStoreError("dependency_cycle:" + "->".join(cycle))
            if name in visited:
                return
            if name not in by_name:
                raise VibeVMStoreError(f"missing_dependency:{name}")
            visiting.append(name)
            item = by_name[name]
            for dependency in sorted(item["dependencies"]):
                expected, actual = item["dependencies"][dependency], by_name.get(dependency, {}).get("version")
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
        immutable_keys = ("name", "version", "sha256", "origin", "dependencies")
        graph = {"packages": [{key: by_name[name][key] for key in immutable_keys} for name in order],
                 "overrides": sorted(overrides)}
        return {"schema_version": 1, **graph, "graph_digest": _digest(_canonical(graph))}

    def object_path(self, digest: str) -> Path:
        self._check_paths()
        if not _valid_digest(digest):
            raise VibeVMStoreError("invalid_digest")
        return self.objects / digest

    def _read_object(self, digest: str, coordinate: str) -> bytes:
        descriptor = None
        try:
            descriptor = os.open(digest, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self._fds[self.objects])
            value = os.fstat(descriptor)
            if not stat.S_ISREG(value.st_mode) or value.st_uid != os.geteuid() or value.st_nlink != 1:
                raise VibeVMStoreError(f"object_authority_mismatch:{coordinate}")
            with os.fdopen(descriptor, "rb") as source:
                descriptor = None
                return source.read()
        except FileNotFoundError:
            raise VibeVMStoreError(f"missing_package:{coordinate}") from None
        except OSError as error:
            raise VibeVMStoreError(f"object_authority_mismatch:{coordinate}") from error
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def admit(self, item, payload: bytes) -> Path:
        self._check_paths()
        authoritative = self._authority(item)
        coordinate = self._coordinate(authoritative)
        if authoritative["revoked"]:
            raise VibeVMStoreError(f"package_revoked:{coordinate}")
        if not authoritative["qualified"]:
            raise VibeVMStoreError(f"package_unqualified:{coordinate}")
        if not isinstance(payload, bytes) or _digest(payload) != authoritative["sha256"]:
            raise VibeVMStoreError(f"digest_mismatch:{coordinate}")
        target = self.object_path(authoritative["sha256"])
        try:
            existing = self._read_object(authoritative["sha256"], coordinate)
        except VibeVMStoreError as error:
            if error.code != f"missing_package:{coordinate}":
                raise
        else:
            if _digest(existing) != authoritative["sha256"]:
                raise VibeVMStoreError(f"immutable_object_conflict:{coordinate}")
            return target
        descriptor, name = tempfile.mkstemp(prefix=".admit-", dir=self._fd_path(self.objects))
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            temporary.chmod(0o400)
            try:
                os.link(temporary, authoritative["sha256"], dst_dir_fd=self._fds[self.objects], follow_symlinks=False)
                os.fsync(self._fds[self.objects])
            except FileExistsError:
                if _digest(self._read_object(authoritative["sha256"], coordinate)) != authoritative["sha256"]:
                    raise VibeVMStoreError(f"immutable_object_conflict:{coordinate}") from None
        finally:
            temporary.unlink(missing_ok=True)
        self._check_paths()
        return target

    def replay(self, lock):
        self._check_paths()
        if not isinstance(lock, dict) or set(lock) != {"schema_version", "packages", "overrides", "graph_digest"} or lock["schema_version"] != 1:
            raise VibeVMStoreError("invalid_lock")
        graph = {"packages": lock["packages"], "overrides": lock["overrides"]}
        if not _valid_digest(lock["graph_digest"]) or _digest(_canonical(graph)) != lock["graph_digest"]:
            raise VibeVMStoreError("lock_digest_mismatch")
        # Re-resolve immutable graph against registry; lock digest alone is never authority.
        current = []
        for locked in lock["packages"]:
            _lock_item(locked)
            current.append(self._authority({**locked, "qualified": True, "revoked": False}, lifecycle_flexible=True))
        authoritative_lock = self.resolve(current, overrides=lock["overrides"])
        if authoritative_lock["packages"] != lock["packages"]:
            raise VibeVMStoreError("registry_graph_mismatch")
        result = {}
        for item in current:
            coordinate = self._coordinate(item)
            if item["revoked"]:
                raise VibeVMStoreError(f"package_revoked:{coordinate}")
            if not item["qualified"]:
                raise VibeVMStoreError(f"package_unqualified:{coordinate}")
            payload = self._read_object(item["sha256"], coordinate)
            if _digest(payload) != item["sha256"]:
                raise VibeVMStoreError(f"digest_mismatch:{coordinate}")
            result[coordinate] = payload
        self._check_paths()
        return result

    @staticmethod
    def _xml_check(data: bytes, name: str) -> None:
        parser, flags = xml.parsers.expat.ParserCreate(), {"dtd": False, "entity": False}
        parser.StartDoctypeDeclHandler = lambda *_: flags.__setitem__("dtd", True)
        parser.EntityDeclHandler = lambda *_: flags.__setitem__("entity", True)
        parser.ExternalEntityRefHandler = lambda *_: flags.__setitem__("entity", True) or 0
        try:
            parser.Parse(data, True)
        except xml.parsers.expat.ExpatError:
            if flags["entity"]:
                raise VibeVMStoreError(f"xml_entity_forbidden:{name}") from None
            if flags["dtd"]:
                raise VibeVMStoreError(f"xml_dtd_forbidden:{name}") from None
            raise VibeVMStoreError(f"invalid_xml:{name}") from None
        if flags["entity"]:
            raise VibeVMStoreError(f"xml_entity_forbidden:{name}")
        if flags["dtd"]:
            raise VibeVMStoreError(f"xml_dtd_forbidden:{name}")

    def _project(self, payload: bytes, destination: Path, coordinate: str) -> None:
        try:
            archive = zipfile.ZipFile(io.BytesIO(payload))
        except (zipfile.BadZipFile, OSError):
            raise VibeVMStoreError(f"invalid_archive:{coordinate}") from None
        with archive:
            members = archive.infolist()
            if len(members) > self.max_files:
                raise VibeVMStoreError("file_count_exceeded")
            total, exact, aliases, files = 0, set(), {}, set()
            for member in members:
                original = member.filename
                if "\\" in original or "\x00" in original:
                    raise VibeVMStoreError("noncanonical_member")
                raw = original[:-1] if original.endswith("/") else original
                raw_parts = raw.split("/")
                if original.startswith("/") or ".." in raw_parts:
                    raise VibeVMStoreError("path_escape")
                if not raw or any(part in ("", ".") for part in raw_parts):
                    raise VibeVMStoreError("noncanonical_member")
                path = PurePosixPath(original)
                if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
                    raise VibeVMStoreError("path_escape")
                parts = tuple(unicodedata.normalize("NFC", part) for part in path.parts)
                if (sum(len(part.encode("utf-8")) for part in parts) > 4096
                        or any(any(unicodedata.category(character).startswith("C") for character in part) for part in parts)):
                    raise VibeVMStoreError("noncanonical_member")
                if len(parts) > self.max_depth:
                    raise VibeVMStoreError("path_depth_exceeded")
                canonical, alias = "/".join(parts), "/".join(part.casefold() for part in parts)
                if original.rstrip("/") in exact:
                    raise VibeVMStoreError(f"duplicate_member:{original.rstrip('/')}")
                if alias in aliases:
                    raise VibeVMStoreError(f"member_alias:{original.rstrip('/')}")
                if any("/".join(parts[:index]).casefold() in files for index in range(1, len(parts))):
                    raise VibeVMStoreError(f"path_collision:{parts[0]}")
                if not member.is_dir() and any(value.startswith(alias + "/") for value in aliases):
                    raise VibeVMStoreError(f"path_collision:{parts[0]}")
                exact.add(original.rstrip("/"))
                aliases[alias] = canonical
                mode, file_type = member.external_attr >> 16, stat.S_IFMT(member.external_attr >> 16)
                if stat.S_ISLNK(mode) or file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise VibeVMStoreError(f"non_regular_member:{original}")
                lowered = tuple(part.casefold() for part in parts)
                if lowered[0] in ("hooks", "scripts") or lowered[-1] in ("install.sh", "build.sh", "postinstall"):
                    raise VibeVMStoreError("lifecycle_hook_forbidden")
                if member.flag_bits & 1:
                    raise VibeVMStoreError(f"encrypted_member:{original}")
                if member.is_dir():
                    continue
                files.add(alias)
                total += member.file_size
                if total > self.max_bytes:
                    raise VibeVMStoreError("expanded_size_exceeded")
                try:
                    data = archive.read(member)
                except (zipfile.BadZipFile, RuntimeError):
                    raise VibeVMStoreError(f"archive_crc_mismatch:{original}") from None
                if len(data) != member.file_size:
                    raise VibeVMStoreError("archive_size_mismatch")
                if parts[-1].casefold().endswith(".xml"):
                    self._xml_check(data, original)
                target = destination.joinpath(*parts)
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                target.write_bytes(data)
                target.chmod(0o400)

    @staticmethod
    def _tree_entries(directory: Path, *, exclude=()):
        entries = []
        for path in sorted(directory.rglob("*")):
            value = path.lstat()
            if (stat.S_ISLNK(value.st_mode) or not (stat.S_ISDIR(value.st_mode) or stat.S_ISREG(value.st_mode))
                    or (stat.S_ISREG(value.st_mode) and (value.st_nlink != 1 or value.st_uid != os.geteuid()))):
                raise VibeVMStoreError("generation_manifest_mismatch")
            relative = path.relative_to(directory).as_posix()
            if relative in exclude:
                continue
            entries.append({"path": relative, "kind": "directory" if path.is_dir() else "file",
                            "mode": stat.S_IMODE(value.st_mode),
                            "sha256": None if path.is_dir() else _digest(path.read_bytes())})
        return entries

    def _validate_generation(self, identity: str) -> None:
        descriptor = None
        try:
            descriptor = os.open(identity, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                 dir_fd=self._fds[self.generations])
            metadata = os.fstat(descriptor)
            visible = os.stat(identity, dir_fd=self._fds[self.generations], follow_symlinks=False)
        except OSError as error:
            if descriptor is not None:
                os.close(descriptor)
            raise VibeVMStoreError("generation_manifest_mismatch") from error
        if (not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid()
                or (metadata.st_dev, metadata.st_ino) != (visible.st_dev, visible.st_ino)):
            os.close(descriptor)
            raise VibeVMStoreError("generation_manifest_mismatch")
        directory = Path(f"/proc/self/fd/{descriptor}")
        try:
            manifest_path = directory / "manifest.json"
            manifest_value = manifest_path.lstat() if manifest_path.exists() else None
            if (manifest_value is None or stat.S_ISLNK(manifest_value.st_mode)
                    or not stat.S_ISREG(manifest_value.st_mode) or manifest_value.st_nlink != 1
                    or manifest_value.st_uid != os.geteuid()):
                raise VibeVMStoreError("generation_manifest_mismatch")
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                raise VibeVMStoreError("generation_manifest_mismatch") from None
            entries = self._tree_entries(directory, exclude={"manifest.json"})
            if manifest != {"schema_version": 1, "generation_id": identity, "entries": entries}:
                raise VibeVMStoreError("generation_manifest_mismatch")
            try:
                after = os.stat(identity, dir_fd=self._fds[self.generations], follow_symlinks=False)
            except OSError:
                raise VibeVMStoreError("generation_manifest_mismatch") from None
        finally:
            os.close(descriptor)
        if (after.st_dev, after.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise VibeVMStoreError("generation_manifest_mismatch")

    def _locked_root(self):
        descriptor = None
        try:
            descriptor = os.open(".generation.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600,
                                 dir_fd=self._fds[self.root])
            value = os.fstat(descriptor)
        except OSError as error:
            if descriptor is not None:
                os.close(descriptor)
            raise VibeVMStoreError("generation_lock_unsafe") from error
        if not stat.S_ISREG(value.st_mode) or value.st_uid != os.geteuid() or value.st_nlink != 1:
            os.close(descriptor)
            raise VibeVMStoreError("generation_lock_unsafe")
        return os.fdopen(descriptor, "a+b")

    def materialize(self, lock, owner_text: str, managed_text: str, *, crash_before_switch=False) -> str:
        self._check_paths()
        self.active_generation()
        boot, payloads = reconcile_boot_block(owner_text, managed_text), self.replay(lock)
        identity = _digest(_canonical({"lock": lock, "boot": boot}))
        secure_generations = self._fd_path(self.generations)
        final = secure_generations / identity
        staging = Path(tempfile.mkdtemp(prefix=".generation-", dir=secure_generations))
        try:
            projection = staging / "projection"
            projection.mkdir(mode=0o700)
            for item in lock["packages"]:
                coordinate = self._coordinate(item)
                self._project(payloads[coordinate], projection / coordinate, coordinate)
            (staging / "boot.md").write_text(boot, encoding="utf-8")
            (staging / "lock.json").write_bytes(_canonical(lock) + b"\n")
            entries = self._tree_entries(staging)
            (staging / "manifest.json").write_bytes(_canonical(
                {"schema_version": 1, "generation_id": identity, "entries": entries}) + b"\n")
            for path in sorted(staging.rglob("*"), reverse=True):
                if path.is_file():
                    with path.open("rb") as source:
                        os.fsync(source.fileno())
                elif path.is_dir():
                    _fsync_directory(path)
            _fsync_directory(staging)
            if final.exists() or final.is_symlink():
                self._validate_generation(identity)
                shutil.rmtree(staging)
            else:
                try:
                    os.replace(staging, final)
                    os.fsync(self._fds[self.generations])
                except OSError as error:
                    if error.errno not in (errno.EEXIST, errno.ENOTEMPTY):
                        raise
                    self._validate_generation(identity)
                    shutil.rmtree(staging)
            self._validate_generation(identity)
            if crash_before_switch:
                raise VibeVMStoreError("simulated_crash")
            with self._locked_root() as update_lock:
                fcntl.flock(update_lock, fcntl.LOCK_EX)
                self._validate_generation(identity)
                descriptor, name = tempfile.mkstemp(prefix=".active-", dir=self._fd_path(self.root))
                pointer = Path(name)
                try:
                    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                        output.write(identity + "\n")
                        output.flush()
                        os.fsync(output.fileno())
                    os.replace(pointer, "active", dst_dir_fd=self._fds[self.root])
                    os.fsync(self._fds[self.root])
                finally:
                    pointer.unlink(missing_ok=True)
            self._check_paths()
            return identity
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    def active_generation(self):
        self._check_paths()
        try:
            descriptor = os.open("active", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self._fds[self.root])
        except FileNotFoundError:
            return None
        except OSError as error:
            raise VibeVMStoreError("active_generation_corrupt") from error
        with os.fdopen(descriptor, "rb") as source:
            metadata = os.fstat(source.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid() or metadata.st_nlink != 1:
                raise VibeVMStoreError("active_generation_corrupt")
            try:
                value = source.read().decode("utf-8").strip()
            except UnicodeDecodeError:
                raise VibeVMStoreError("active_generation_corrupt") from None
        if not _valid_digest(value):
            raise VibeVMStoreError("active_generation_corrupt")
        try:
            self._validate_generation(value)
        except VibeVMStoreError:
            raise VibeVMStoreError("active_generation_corrupt") from None
        return value

    def reconcile(self) -> int:
        self._check_paths()
        removed = 0
        with self._locked_root() as update_lock:
            fcntl.flock(update_lock, fcntl.LOCK_EX)
            for candidate in self._fd_path(self.generations).iterdir():
                if candidate.name.startswith(".generation-"):
                    if candidate.is_symlink() or not candidate.is_dir():
                        raise VibeVMStoreError("generation_staging_unsafe")
                    shutil.rmtree(candidate)
                    removed += 1
            if removed:
                os.fsync(self._fds[self.generations])
        self._check_paths()
        return removed
