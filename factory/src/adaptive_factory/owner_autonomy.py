"""Owner-confirmed local M8 authority; never empirical M7 or external authority.

The checked-in policy is an owner's bounded local instruction. These records are
not signatures, human Trust CI approvals, provider grants, or merge permission.
The consumer admits named local operations only and never executes a command.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
from typing import Any, Mapping

from .contracts import ContractError, HEX40, HEX64, _closed, _hex, _id, _time, canonical_json

LOCAL_ACTIONS = ("local_read", "local_test")


def digest(value: Any) -> str:
    return hashlib.sha256(b"adaptive-factory.owner-autonomy/v1\0" + canonical_json(value)).hexdigest()


def _parse(cls: type, data: Mapping[str, Any]):
    if not isinstance(data, Mapping) or any(not isinstance(key, str) for key in data):
        raise ContractError("invalid_contract")
    _closed(data, {field.name for field in fields(cls)})
    values = dict(data)
    for name in ("expires_at", "issued_at"):
        if name in values:
            values[name] = _time(values[name], name)
    if "allowed_actions" in values:
        if not isinstance(values["allowed_actions"], list):
            raise ContractError("invalid_contract", "allowed_actions")
        values["allowed_actions"] = tuple(values["allowed_actions"])
    return cls(**values)


class _Value:
    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            elif isinstance(value, tuple):
                result[key] = list(value)
        return result

    @property
    def digest(self) -> str:
        return digest(self.to_dict())

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]):
        return _parse(cls, data)


def _version(value: Any):
    if type(value) is not int or value != 1:
        raise ContractError("unsupported_version")


def _bool(value: Any, name: str):
    if type(value) is not bool:
        raise ContractError("invalid_boolean", name)


@dataclass(frozen=True)
class OwnerPolicyV1(_Value):
    schema_version: int
    policy_id: str
    repository_id: str
    enabled: bool
    evidence_kind: str
    minimum_accepted_tasks: int
    product_repository: str
    product_source_sha: str
    factory_source_sha: str
    initial_level: str
    authority_ceiling: str
    allowed_actions: tuple[str, ...]
    activation_ttl_seconds: int
    expires_at: datetime

    def __post_init__(self):
        _version(self.schema_version)
        for name in ("policy_id", "repository_id", "product_repository"):
            _id(getattr(self, name), name)
        _bool(self.enabled, "enabled")
        if self.evidence_kind != "explicit_owner_confirmation":
            raise ContractError("unsupported_evidence_kind")
        if type(self.minimum_accepted_tasks) is not int or self.minimum_accepted_tasks != 1:
            raise ContractError("invalid_integer", "minimum_accepted_tasks")
        for name in ("product_source_sha", "factory_source_sha"):
            _hex(getattr(self, name), name, HEX40)
        if self.initial_level != "L1" or self.authority_ceiling != "L2":
            raise ContractError("unsupported_level")
        if self.allowed_actions != LOCAL_ACTIONS:
            raise ContractError("unsupported_action")
        if type(self.activation_ttl_seconds) is not int or not 1 <= self.activation_ttl_seconds <= 3600:
            raise ContractError("invalid_integer", "activation_ttl_seconds")
        if not isinstance(self.expires_at, datetime) or self.expires_at.tzinfo is None:
            raise ContractError("invalid_time", "expires_at")


@dataclass(frozen=True)
class OwnerCaseV1(_Value):
    schema_version: int
    product_repository: str
    product_source_sha: str
    factory_source_sha: str
    evidence_kind: str
    accepted: bool
    accounting_complete: bool
    human_gate_complete: bool
    cost_usd_micros: int | None
    human_intervention_count: int | None

    def __post_init__(self):
        _version(self.schema_version)
        _id(self.product_repository, "product_repository")
        for name in ("product_source_sha", "factory_source_sha"):
            _hex(getattr(self, name), name, HEX40)
        if self.evidence_kind != "explicit_owner_confirmation":
            raise ContractError("unsupported_evidence_kind")
        for name in ("accepted", "accounting_complete", "human_gate_complete"):
            _bool(getattr(self, name), name)
        for name in ("cost_usd_micros", "human_intervention_count"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0 or value > 1_000_000_000_000):
                raise ContractError("invalid_integer", name)

    @classmethod
    def from_project_state(cls, state: Mapping[str, Any]) -> "OwnerCaseV1":
        try:
            case = state["milestones"]["M8"]["completed_product_case"]
            acceptance = case["acceptance"]
            readiness = case["owner_readiness"]
            if (acceptance["evidence_kind"] != "explicit_owner_confirmation"
                    or readiness["evidence_kind"] != "explicit_owner_confirmation"
                    or case["status"] != "DONE"):
                raise ContractError("owner_confirmation_missing")
            return cls(1, case["repository"], case["release_source_sha"], case["factory_source_sha"],
                       acceptance["evidence_kind"], acceptance["completed_working_factory_built_product"],
                       readiness["accounting_complete"], readiness["human_gate_complete"],
                       readiness["cost_usd_micros"], readiness["human_intervention_count"])
        except (KeyError, TypeError) as exc:
            raise ContractError("owner_confirmation_missing") from exc


@dataclass(frozen=True)
class OwnerContextV1(_Value):
    repository_id: str
    repository_binding_digest: str
    source_digest: str
    profile_digest: str

    def __post_init__(self):
        _id(self.repository_id, "repository_id")
        for name in ("repository_binding_digest", "source_digest", "profile_digest"):
            _hex(getattr(self, name), name, HEX64)


@dataclass(frozen=True)
class OwnerActivationV1(_Value):
    schema_version: int
    policy_digest: str
    case_digest: str
    repository_id: str
    repository_binding_digest: str
    source_digest: str
    profile_digest: str
    level: str
    issued_at: datetime
    expires_at: datetime

    def __post_init__(self):
        _version(self.schema_version)
        _id(self.repository_id, "repository_id")
        for name in ("policy_digest", "case_digest", "repository_binding_digest", "source_digest", "profile_digest"):
            _hex(getattr(self, name), name, HEX64)
        if self.level != "L1":
            raise ContractError("unsupported_level")
        if any(not isinstance(t, datetime) or t.tzinfo is None for t in (self.issued_at, self.expires_at)):
            raise ContractError("invalid_time")
        if not self.issued_at < self.expires_at <= self.issued_at + timedelta(hours=1):
            raise ContractError("invalid_time")


def _decision(allowed: bool, reason: str) -> dict[str, Any]:
    return {"schema_version": 1, "allowed": allowed, "level": "L1" if allowed else "L0",
            "authority_ceiling": "L2", "reason": reason, "external_authority": False}


def qualify(policy: OwnerPolicyV1, case: OwnerCaseV1, context: OwnerContextV1, now: datetime) -> str | None:
    if not isinstance(now, datetime) or now.tzinfo is None:
        return "invalid_time"
    if not policy.enabled:
        return "disabled"
    if now >= policy.expires_at:
        return "policy_expired"
    if policy.repository_id != context.repository_id:
        return "repository_mismatch"
    if (policy.product_repository, policy.product_source_sha, policy.factory_source_sha) != (
            case.product_repository, case.product_source_sha, case.factory_source_sha):
        return "provenance_mismatch"
    if not case.accepted or not case.accounting_complete or not case.human_gate_complete:
        return "owner_confirmation_missing"
    return None


class OwnerRuntime:
    """Immutable, bounded local records. Revoke permanently tombstones this policy.

    Removing expired activation.json is an explicit local reset for reactivation;
    revocation cannot be cleared by activate and requires a new owner policy.
    """
    def __init__(self, path: Path):
        self.path = path

    def _directory(self, create: bool = False) -> int:
        # Pin every directory with no-follow descriptors, including ancestors.
        target = self.path.absolute()
        fd = os.open(target.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for name in target.parts[1:]:
                if name in (".", ".."):
                    raise ContractError("unsafe_runtime")
                if create:
                    try:
                        os.mkdir(name, mode=0o700, dir_fd=fd)
                    except FileExistsError:
                        pass
                next_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            info = os.fstat(fd)
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
                raise ContractError("unsafe_runtime")
            return fd
        except BaseException:
            os.close(fd)
            raise

    def _read(self, name: str):
        directory = self._directory()
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        finally:
            os.close(directory)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
                raise ContractError("unsafe_runtime")
            raw = stream.read(65537)
            if len(raw) > 65536:
                raise ContractError("unsafe_runtime")
            return json.loads(raw)

    def _write(self, name: str, value: dict):
        directory = self._directory(create=True)
        try:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        finally:
            os.close(directory)
        with os.fdopen(fd, "wb") as stream:
            stream.write(canonical_json(value))
            stream.flush()
            os.fsync(stream.fileno())

    def _revoked(self, policy: OwnerPolicyV1) -> bool:
        try:
            # Any present tombstone denies; malformed bytes never lift revocation.
            self._read("revoked-" + policy.digest + ".json")
            return True
        except FileNotFoundError:
            return False

    def activate(self, policy: OwnerPolicyV1, case: OwnerCaseV1, context: OwnerContextV1, *, now: datetime):
        try:
            reason = qualify(policy, case, context, now)
            if reason:
                return _decision(False, reason)
            if self._revoked(policy):
                return _decision(False, "revoked")
            record = OwnerActivationV1(1, policy.digest, case.digest, context.repository_id,
                                       context.repository_binding_digest, context.source_digest,
                                       context.profile_digest, "L1", now,
                                       min(policy.expires_at, now + timedelta(seconds=policy.activation_ttl_seconds)))
            try:
                self._write("activation.json", record.to_dict())
            except FileExistsError:
                return self.status(policy, case, context, now=now)
            return self.status(policy, case, context, now=now)
        except (OSError, ValueError, TypeError):
            return _decision(False, "invalid_runtime")

    def status(self, policy: OwnerPolicyV1, case: OwnerCaseV1, context: OwnerContextV1, *, now: datetime):
        try:
            reason = qualify(policy, case, context, now)
            if reason:
                return _decision(False, reason)
            if self._revoked(policy):
                return _decision(False, "revoked")
            record = OwnerActivationV1.from_dict(self._read("activation.json"))
            if not record.issued_at <= now < record.expires_at:
                return _decision(False, "activation_expired")
            expected = (policy.digest, case.digest, context.repository_id, context.repository_binding_digest,
                        context.source_digest, context.profile_digest)
            actual = (record.policy_digest, record.case_digest, record.repository_id, record.repository_binding_digest,
                      record.source_digest, record.profile_digest)
            if actual != expected:
                return _decision(False, "binding_mismatch")
            return _decision(True, "active")
        except FileNotFoundError:
            return _decision(False, "activation_missing")
        except (OSError, ValueError, TypeError):
            return _decision(False, "invalid_runtime")

    def admit(self, policy: OwnerPolicyV1, case: OwnerCaseV1, context: OwnerContextV1, action: str, *, now: datetime):
        decision = self.status(policy, case, context, now=now)
        if not decision["allowed"]:
            return decision
        if action not in policy.allowed_actions:
            return _decision(False, "action_not_authorized")
        return _decision(True, "admitted")

    def revoke(self, policy: OwnerPolicyV1, *, now: datetime):
        try:
            _time(now.isoformat(), "revoked_at")
            try:
                self._write("revoked-" + policy.digest + ".json", {
                    "schema_version": 1, "policy_digest": policy.digest, "revoked_at": now.isoformat()})
            except FileExistsError:
                pass
            return _decision(False, "revoked")
        except (OSError, ValueError, TypeError):
            return _decision(False, "invalid_runtime")


def current_context(root: Path) -> OwnerContextV1:
    """Derive actual origin and bytes; never accept caller-supplied current digests."""
    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL, timeout=10)

    origin = git("remote", "get-url", "origin").decode().strip()
    prefix = next((p for p in ("https://github.com/", "git@github.com:") if origin.startswith(p)), None)
    if prefix is None:
        raise ContractError("repository_mismatch")
    repository = origin[len(prefix):].removesuffix(".git")
    _id(repository, "repository_id")
    inventory = git("ls-files", "-z", "factory/src", "factory/contracts", "factory/runtime/owner-autonomy-policy.v1.json",
                    "scripts/grok_m8.py", "VERSION").split(b"\0")
    # Include newly added runtime source, too: untracked files cannot evade binding.
    inventory += git("ls-files", "--others", "--exclude-standard", "-z", "factory/src", "factory/contracts",
                     "factory/runtime/owner-autonomy-policy.v1.json", "scripts/grok_m8.py").split(b"\0")
    paths = sorted(set(path.decode() for path in inventory if path))
    source = []
    for name in paths:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ContractError("source_unavailable")
        source.append([name, hashlib.sha256(path.read_bytes()).hexdigest()])
    profile = {"task_class": "low_risk_text_only", "initial_level": "L1", "authority_ceiling": "L2",
               "allowed_actions": list(LOCAL_ACTIONS), "external_authority": False}
    # Distinct clone/worktree identity; only its hash is exposed in runtime.
    git_dir = git("rev-parse", "--absolute-git-dir").decode().strip()
    head = git("rev-parse", "HEAD").decode().strip()
    return OwnerContextV1(repository, digest(git_dir), digest({"head": head, "files": source}), digest(profile))
