"""Deterministic, data-only local package projection for the optional U6 adapter."""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
from types import MappingProxyType
import zipfile
from urllib.parse import urlsplit


class VibeVMError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _scope(value: str, field: str) -> str:
    if not value or len(value) > 128 or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/" for character in value):
        raise VibeVMError(f"invalid_{field}")
    if value.startswith(("/", ".")) or ".." in value.split("/"):
        raise VibeVMError(f"invalid_{field}")
    return value.encode("utf-8").hex()


def _generation_id(value: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise VibeVMError("invalid_generation_id")
    return value


def reconcile_boot_block(owner_text: str, managed_text: str) -> str:
    start = "<!-- adaptive-vibevm -->"
    end = "<!-- /adaptive-vibevm -->"
    starts, ends = owner_text.count(start), owner_text.count(end)
    if starts != ends:
        raise VibeVMError("boot_block_corrupt")
    if starts > 1:
        raise VibeVMError("boot_block_conflict")
    block = f"{start}\n{managed_text.rstrip()}\n{end}\n"
    if not starts:
        separator = "" if owner_text.endswith("\n") else "\n"
        return owner_text + separator + block
    before, remainder = owner_text.split(start, 1)
    _, after = remainder.split(end, 1)
    if after.startswith("\n"):
        after = after[1:]
    return before + block + after


@dataclass(frozen=True)
class Snapshot:
    generation_id: str
    native_export: MappingProxyType


class VibeVMStore:
    def __init__(self, root, *, tenant_id: str, repository_id: str, allowed_origins,
                 max_files: int = 128, max_bytes: int = 262_144, max_depth: int = 12):
        if max_files < 1 or max_bytes < 1 or max_depth < 1:
            raise VibeVMError("invalid_bounds")
        tenant = _scope(tenant_id, "tenant_id")
        repository = _scope(repository_id, "repository_id")
        self.root = Path(root).resolve() / "tenants" / tenant / "repositories" / repository
        self.allowed_origins = frozenset(allowed_origins)
        self.max_files, self.max_bytes, self.max_depth = max_files, max_bytes, max_depth
        self.objects = self.root / "objects"
        self.generations = self.root / "generations"
        self.active_path = self.root / "active"

    @staticmethod
    def _coordinate(item):
        return f"{item['name']}@{item['version']}"

    @staticmethod
    def _validate_item(item):
        required = {"name", "version", "sha256", "origin", "dependencies", "qualified", "revoked"}
        if set(item) != required:
            raise VibeVMError("invalid_package")
        _scope(item["name"], "package_name"); _scope(item["version"], "package_version")
        if len(item["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in item["sha256"]):
            raise VibeVMError("invalid_digest")
        if not isinstance(item["dependencies"], dict) or type(item["qualified"]) is not bool or type(item["revoked"]) is not bool:
            raise VibeVMError("invalid_package")

    def resolve(self, packages, *, overrides=()):
        by_name = {}
        for item in packages:
            self._validate_item(item)
            if item["name"] in by_name:
                raise VibeVMError(f"duplicate_package:{item['name']}")
            by_name[item["name"]] = dict(item)
        if len(set(overrides)) != len(overrides):
            duplicate = next(name for name in overrides if overrides.count(name) > 1)
            raise VibeVMError(f"ambiguous_override:{duplicate}")
        order, visiting, visited = [], [], set()

        def visit(name):
            if name in visiting:
                cycle = visiting[visiting.index(name):] + [name]
                raise VibeVMError("dependency_cycle:" + "->".join(cycle))
            if name in visited:
                return
            if name not in by_name:
                raise VibeVMError(f"missing_dependency:{name}")
            visiting.append(name)
            item = by_name[name]
            for dependency in sorted(item["dependencies"]):
                expected = item["dependencies"][dependency]
                actual = by_name.get(dependency, {}).get("version")
                if actual is None:
                    raise VibeVMError(f"missing_dependency:{name}->{dependency}")
                if actual != expected:
                    raise VibeVMError(f"version_conflict:{name}->{dependency}:{expected}!={actual}")
                visit(dependency)
            visiting.pop(); visited.add(name); order.append(name)

        for name in sorted(by_name):
            visit(name)
        locked = [{key: by_name[name][key] for key in ("name", "version", "sha256", "origin", "dependencies", "qualified", "revoked")} for name in order]
        override_list = sorted(overrides)
        return {"schema_version": 1, "packages": locked, "overrides": override_list,
                "graph_digest": hashlib.sha256(_canonical({"packages": locked, "overrides": override_list})).hexdigest()}

    def object_path(self, digest: str) -> Path:
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise VibeVMError("invalid_digest")
        return self.objects / digest

    def admit(self, item, payload: bytes):
        self._validate_item(item)
        coordinate = self._coordinate(item)
        if item["origin"] not in self.allowed_origins:
            raise VibeVMError(f"origin_not_allowed:{item['origin']}")
        if item["revoked"]:
            raise VibeVMError(f"package_revoked:{coordinate}")
        if not item["qualified"]:
            raise VibeVMError(f"package_unqualified:{coordinate}")
        if hashlib.sha256(payload).hexdigest() != item["sha256"]:
            raise VibeVMError(f"digest_mismatch:{coordinate}")
        self.objects.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = self.object_path(item["sha256"])
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]:
                raise VibeVMError(f"immutable_object_conflict:{coordinate}")
            return target
        descriptor, temporary = tempfile.mkstemp(prefix=".admit-", dir=self.objects)
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(payload); output.flush(); os.fsync(output.fileno())
            os.chmod(temporary, 0o400)
            try:
                os.link(temporary, target)
            except FileExistsError:
                if hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]:
                    raise VibeVMError(f"immutable_object_conflict:{coordinate}")
        finally:
            Path(temporary).unlink(missing_ok=True)
        return target

    def replay(self, lock, *, historical_audit=False):
        if set(lock) != {"schema_version", "packages", "overrides", "graph_digest"} or lock["schema_version"] != 1:
            raise VibeVMError("invalid_lock")
        locked_graph = {"packages": lock["packages"], "overrides": lock["overrides"]}
        if hashlib.sha256(_canonical(locked_graph)).hexdigest() != lock["graph_digest"]:
            raise VibeVMError("lock_digest_mismatch")
        result = {}
        for item in lock.get("packages", []):
            self._validate_item(item); coordinate = self._coordinate(item)
            if item["origin"] not in self.allowed_origins:
                raise VibeVMError(f"origin_not_allowed:{item['origin']}")
            if (item["revoked"] or not item["qualified"]) and not historical_audit:
                code = "package_revoked" if item["revoked"] else "package_unqualified"
                raise VibeVMError(f"{code}:{coordinate}")
            target = self.object_path(item["sha256"])
            if not target.is_file():
                raise VibeVMError(f"missing_package:{coordinate}")
            payload = target.read_bytes()
            if hashlib.sha256(payload).hexdigest() != item["sha256"]:
                raise VibeVMError(f"digest_mismatch:{coordinate}")
            result[coordinate] = payload
        return result

    def semantic_identity(self, lock, configuration, *, observed_at=None):
        semantic = {"lock": lock, "configuration": configuration}
        return hashlib.sha256(_canonical(semantic)).hexdigest()

    def generation_identity(self, lock, configuration, boot_owner_text, boot_block, bindings):
        semantic = {"lock": lock, "configuration": configuration, "boot_owner_text": boot_owner_text,
                    "boot_block": boot_block, "bindings": bindings}
        return hashlib.sha256(_canonical(semantic)).hexdigest()

    @staticmethod
    def _validate_configuration(value, key="configuration"):
        if isinstance(value, dict):
            for child_key, child in value.items():
                if any(token in child_key.lower() for token in ("password", "secret", "credential", "token")):
                    raise VibeVMError("unsafe_configuration")
                VibeVMStore._validate_configuration(child, child_key)
        elif isinstance(value, list):
            for child in value:
                VibeVMStore._validate_configuration(child, key)
        elif isinstance(value, str) and "://" in value:
            parsed = urlsplit(value)
            if parsed.username is not None or parsed.password is not None:
                raise VibeVMError("unsafe_configuration")

    def _project(self, payload, destination, coordinate):
        try:
            archive = zipfile.ZipFile(io := __import__("io").BytesIO(payload))
        except (zipfile.BadZipFile, OSError):
            raise VibeVMError(f"invalid_archive:{coordinate}") from None
        members = archive.infolist()
        if len(members) > self.max_files:
            raise VibeVMError("file_count_exceeded")
        total = 0; seen = set()
        for member in members:
            path = PurePosixPath(member.filename)
            if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
                raise VibeVMError("path_escape")
            if len(path.parts) > self.max_depth:
                raise VibeVMError("path_depth_exceeded")
            if member.filename in seen:
                raise VibeVMError(f"duplicate_member:{member.filename}")
            seen.add(member.filename)
            mode = member.external_attr >> 16
            file_type = stat.S_IFMT(mode)
            if stat.S_ISLNK(mode) or file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise VibeVMError(f"non_regular_member:{member.filename}")
            lowered = tuple(part.lower() for part in path.parts)
            if lowered[0] in ("hooks", "scripts") or lowered[-1] in ("install.sh", "build.sh", "postinstall"):
                raise VibeVMError("lifecycle_hook_forbidden")
            if member.is_dir():
                continue
            total += member.file_size
            if total > self.max_bytes:
                raise VibeVMError("expanded_size_exceeded")
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            data = archive.read(member)
            if len(data) != member.file_size:
                raise VibeVMError("archive_size_mismatch")
            if path.suffix.lower() == ".xml" and (b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper()):
                raise VibeVMError(f"xml_external_entity_forbidden:{member.filename}")
            target.write_bytes(data); target.chmod(0o400)

    def publish(self, lock, *, boot_owner_text, boot_block, bindings, configuration,
                expected_active=None, crash_before_switch=False):
        self._validate_configuration(configuration)
        conditions = configuration.get("conditions", {})
        if conditions.get("mandatory") == "unknown":
            raise VibeVMError("mandatory_condition_unknown")
        current = self.active_generation()
        if expected_active is not None and current != expected_active:
            raise VibeVMError("generation_conflict")
        payloads = self.replay(lock)
        generation_id = self.generation_identity(lock, configuration, boot_owner_text, boot_block, bindings)
        self.generations.mkdir(parents=True, exist_ok=True, mode=0o700)
        final = self.generations / generation_id
        staging = Path(tempfile.mkdtemp(prefix=".generation-", dir=self.generations))
        try:
            projection = staging / "projection"; projection.mkdir(mode=0o700)
            for item in lock["packages"]:
                coordinate = self._coordinate(item)
                self._project(payloads[coordinate], projection / coordinate, coordinate)
            normalized_bindings = []
            for binding in bindings:
                if set(binding) != {"criterion_id", "rule_id", "revision", "source_digest", "status"} or binding["status"] != "mapped":
                    raise VibeVMError("invalid_binding")
                for field in ("criterion_id", "rule_id", "revision"):
                    _scope(binding[field], field)
                if len(binding["source_digest"]) != 64 or any(character not in "0123456789abcdef" for character in binding["source_digest"]):
                    raise VibeVMError("invalid_binding")
                normalized_bindings.append(dict(binding))
            sources = []
            for source in sorted(projection.rglob("*")):
                if source.is_file():
                    sources.append({"path": source.relative_to(projection).as_posix(),
                                    "content": source.read_text(encoding="utf-8"),
                                    "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
            source_digests = {source["sha256"] for source in sources}
            for binding in normalized_bindings:
                if binding["source_digest"] not in source_digests:
                    raise VibeVMError(f"binding_source_missing:{binding['rule_id']}")
            native = {"schema_version": 1, "generation_id": generation_id, "lock": lock,
                      "bindings": normalized_bindings, "sources": sources, "authority_effect": "none"}
            (staging / "boot.md").write_text(reconcile_boot_block(boot_owner_text, boot_block), encoding="utf-8")
            (staging / "lock.json").write_bytes(_canonical(lock) + b"\n")
            (staging / "native-export.json").write_bytes(_canonical(native) + b"\n")
            status_value = {"qualified": True, "revoked": False,
                            "safety_known": configuration.get("safety_known", True),
                            "mandatory_rules_complete": configuration.get("mandatory_rules_complete", True)}
            (staging / "status.json").write_bytes(_canonical(status_value) + b"\n")
            if final.exists():
                shutil.rmtree(staging)
            else:
                os.replace(staging, final)
            if crash_before_switch:
                raise VibeVMError("simulated_crash")
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            lock_path = self.root / ".generation.lock"
            with lock_path.open("a+b") as update_lock:
                fcntl.flock(update_lock, fcntl.LOCK_EX)
                descriptor, pointer = tempfile.mkstemp(prefix=".active-", dir=self.root)
                try:
                    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                        output.write(generation_id + "\n"); output.flush(); os.fsync(output.fileno())
                    if expected_active is not None and self.active_generation() != expected_active:
                        raise VibeVMError("generation_conflict")
                    os.replace(pointer, self.active_path)
                finally:
                    Path(pointer).unlink(missing_ok=True)
            return self.open_snapshot(generation_id)
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    def active_generation(self):
        if not self.active_path.is_file():
            return None
        value = self.active_path.read_text(encoding="utf-8").strip()
        if len(value) != 64 or not (self.generations / value).is_dir():
            raise VibeVMError("active_generation_corrupt")
        return value

    def export_native(self, generation_id):
        _generation_id(generation_id)
        path = self.generations / generation_id / "native-export.json"
        if not path.is_file():
            raise VibeVMError("generation_missing")
        return json.loads(path.read_text(encoding="utf-8"))

    def open_snapshot(self, generation_id):
        _generation_id(generation_id)
        value = json.loads(json.dumps(self.export_native(generation_id)))
        return Snapshot(generation_id, MappingProxyType(value))

    def set_generation_status(self, generation_id, *, qualified, revoked=False):
        _generation_id(generation_id)
        directory = self.generations / generation_id
        if not directory.is_dir():
            raise VibeVMError("generation_missing")
        lock_path = self.root / ".generation.lock"
        with lock_path.open("a+b") as update_lock:
            fcntl.flock(update_lock, fcntl.LOCK_EX)
            status_path = directory / "status.json"
            status_value = json.loads(status_path.read_text(encoding="utf-8"))
            status_value.update({"qualified": bool(qualified), "revoked": bool(revoked)})
            descriptor, temporary = tempfile.mkstemp(prefix=".status-", dir=directory)
            try:
                with os.fdopen(descriptor, "wb") as output:
                    output.write(_canonical(status_value) + b"\n"); output.flush(); os.fsync(output.fileno())
                os.replace(temporary, status_path)
            finally:
                Path(temporary).unlink(missing_ok=True)
            if revoked and self.active_generation() == generation_id:
                self.active_path.unlink()

    def rollback(self, generation_id):
        _generation_id(generation_id)
        directory = self.generations / generation_id
        if not directory.is_dir():
            raise VibeVMError("rollback_target_missing")
        lock_path = self.root / ".generation.lock"
        with lock_path.open("a+b") as update_lock:
            fcntl.flock(update_lock, fcntl.LOCK_EX)
            status_value = json.loads((directory / "status.json").read_text(encoding="utf-8"))
            if status_value.get("revoked"):
                raise VibeVMError("rollback_target_revoked")
            if not status_value.get("qualified"):
                raise VibeVMError("rollback_target_unqualified")
            descriptor, pointer = tempfile.mkstemp(prefix=".rollback-", dir=self.root)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                    output.write(generation_id + "\n"); output.flush(); os.fsync(output.fileno())
                os.replace(pointer, self.active_path)
            finally:
                Path(pointer).unlink(missing_ok=True)
        return self.open_snapshot(generation_id)

    def native_fallback(self, generation_id, *, adapter_available):
        _generation_id(generation_id)
        status_value = json.loads((self.generations / generation_id / "status.json").read_text(encoding="utf-8"))
        if status_value.get("revoked"):
            raise VibeVMError("fallback_target_revoked")
        if not status_value.get("qualified"):
            raise VibeVMError("fallback_target_unqualified")
        if not status_value.get("safety_known"):
            raise VibeVMError("fallback_safety_unknown")
        if not status_value.get("mandatory_rules_complete"):
            raise VibeVMError("fallback_mandatory_rules_missing")
        exported = self.export_native(generation_id)
        return {"generation_id": generation_id, "backend": "vibevm" if adapter_available else "native",
                "native_export": exported}

    def recover(self):
        """Remove interrupted staging directories without touching immutable generations."""
        if not self.generations.is_dir():
            return 0
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        removed = 0
        with (self.root / ".generation.lock").open("a+b") as update_lock:
            fcntl.flock(update_lock, fcntl.LOCK_EX)
            for candidate in self.generations.iterdir():
                if candidate.is_dir() and candidate.name.startswith(".generation-"):
                    shutil.rmtree(candidate); removed += 1
        return removed
