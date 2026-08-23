from __future__ import annotations

import fnmatch
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .models import canonical_json, require_digest

_IMAGE_DIGEST_RE = re.compile(r"^(?:sha256:[0-9a-f]{64}|.+@sha256:[0-9a-f]{64})$")


class PolicyError(ValueError):
    pass


@dataclass(frozen=True)
class CommandSpec:
    name: str
    argv: tuple[str, ...]
    timeout_seconds: int
    env: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> 'CommandSpec':
        if data.get('required', True) is not True:
            raise PolicyError('all Trust CI commands are mandatory; optional checks are forbidden')
        name = str(data.get('name', '')).strip()
        argv_raw = data.get('argv')
        timeout = data.get('timeout_seconds')
        if not name or not isinstance(argv_raw, list) or not argv_raw:
            raise PolicyError('command name and non-empty argv are required')
        argv = tuple(str(item) for item in argv_raw)
        if any(not item for item in argv):
            raise PolicyError(f'command {name!r} contains an empty argv element')
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 7200:
            raise PolicyError(f'command {name!r} has invalid timeout_seconds')
        env_raw = data.get('env', {})
        if not isinstance(env_raw, dict):
            raise PolicyError(f'command {name!r} env must be an object')
        env = tuple(sorted((str(key), str(value)) for key, value in env_raw.items()))
        return cls(name=name, argv=argv, timeout_seconds=timeout, env=env)

    def to_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'argv': list(self.argv),
            'timeout_seconds': self.timeout_seconds,
            'env': dict(self.env),
            'required': True,
        }


@dataclass(frozen=True)
class ApprovalRule:
    scope: str
    globs: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> 'ApprovalRule':
        scope = str(data.get('scope', '')).strip()
        globs_raw = data.get('globs')
        if not scope or not isinstance(globs_raw, list) or not globs_raw:
            raise PolicyError('approval rule requires a scope and non-empty globs')
        globs = tuple(str(item).replace('\\', '/').lstrip('./') for item in globs_raw)
        if any(not item for item in globs):
            raise PolicyError(f'approval rule {scope!r} contains an empty glob')
        return cls(scope=scope, globs=globs)

    def to_dict(self) -> dict[str, Any]:
        return {'scope': self.scope, 'globs': list(self.globs)}


@dataclass(frozen=True)
class SandboxSpec:
    runtime: str
    image: str
    user: str
    memory_mb: int
    cpus: float
    pids_limit: int
    tmpfs_mb: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> 'SandboxSpec':
        runtime = str(data.get('runtime', '')).strip()
        if runtime not in {'docker', 'podman'}:
            raise PolicyError('sandbox runtime must be docker or podman; host execution is forbidden')
        image = str(data.get('image', '')).strip()
        if not _IMAGE_DIGEST_RE.fullmatch(image):
            raise PolicyError('sandbox image must be immutable: sha256:<64-hex> or name@sha256:<64-hex>')
        user = str(data.get('user', '')).strip()
        if not re.fullmatch(r'[0-9]+(?::[0-9]+)?', user):
            raise PolicyError('sandbox user must be a numeric uid or uid:gid')
        memory_mb = _bounded_int(data, 'memory_mb', 256, 131072)
        pids_limit = _bounded_int(data, 'pids_limit', 32, 32768)
        tmpfs_mb = _bounded_int(data, 'tmpfs_mb', 64, 16384)
        cpus_raw = data.get('cpus')
        if isinstance(cpus_raw, bool) or not isinstance(cpus_raw, (int, float)) or not 0.1 <= float(cpus_raw) <= 128:
            raise PolicyError('sandbox cpus must be between 0.1 and 128')
        return cls(
            runtime=runtime,
            image=image,
            user=user,
            memory_mb=memory_mb,
            cpus=float(cpus_raw),
            pids_limit=pids_limit,
            tmpfs_mb=tmpfs_mb,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            'runtime': self.runtime,
            'image': self.image,
            'user': self.user,
            'memory_mb': self.memory_mb,
            'cpus': self.cpus,
            'pids_limit': self.pids_limit,
            'tmpfs_mb': self.tmpfs_mb,
        }


@dataclass(frozen=True)
class HoldoutSpec:
    path: Path
    digest: str
    commands: tuple[CommandSpec, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> 'HoldoutSpec':
        raw_path = str(data.get('path', '')).strip()
        if not raw_path:
            raise PolicyError('holdout.path is required')
        path = Path(raw_path)
        if not path.is_absolute():
            raise PolicyError('holdout.path must be absolute and outside the checkout')
        try:
            digest = require_digest(str(data.get('digest', '')), 'holdout.digest')
        except ValueError as exc:
            raise PolicyError(str(exc)) from exc
        commands_raw = data.get('commands')
        if not isinstance(commands_raw, list) or not commands_raw:
            raise PolicyError('holdout.commands must be non-empty')
        commands = tuple(CommandSpec.from_dict(item) for item in commands_raw if isinstance(item, Mapping))
        if len(commands) != len(commands_raw):
            raise PolicyError('every holdout command must be an object')
        if len({item.name for item in commands}) != len(commands):
            raise PolicyError('holdout command names must be unique')
        return cls(path=path, digest=digest, commands=commands)

    def to_dict(self) -> dict[str, Any]:
        return {
            'path': str(self.path),
            'digest': self.digest,
            'commands': [item.to_dict() for item in self.commands],
        }


@dataclass(frozen=True)
class Policy:
    schema_version: int
    allowed_repositories: tuple[str, ...]
    status_context: str
    pipeline: str
    checkout_depth: int
    lease_seconds: int
    max_attempts: int
    max_approval_ttl_seconds: int
    max_output_bytes: int
    allowed_environment: tuple[str, ...]
    sandbox: SandboxSpec
    commands: tuple[CommandSpec, ...]
    holdout: HoldoutSpec
    approval_rules: tuple[ApprovalRule, ...]
    digest: str

    @classmethod
    def load(cls, path: Path) -> 'Policy':
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except FileNotFoundError as exc:
            raise PolicyError(f'policy file does not exist: {path}') from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise PolicyError(f'cannot load policy file {path}: {exc}') from exc
        if not isinstance(data, dict):
            raise PolicyError('policy root must be an object')
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> 'Policy':
        if data.get('schema_version') != 1:
            raise PolicyError('unsupported policy schema_version')
        repositories = data.get('allowed_repositories')
        commands_raw = data.get('commands')
        rules_raw = data.get('approval_rules', [])
        sandbox_raw = data.get('sandbox')
        holdout_raw = data.get('holdout')
        if not isinstance(repositories, list) or not repositories:
            raise PolicyError('allowed_repositories must be non-empty')
        if not isinstance(commands_raw, list) or not commands_raw:
            raise PolicyError('commands must be non-empty')
        if not isinstance(rules_raw, list):
            raise PolicyError('approval_rules must be a list')
        if not isinstance(sandbox_raw, Mapping):
            raise PolicyError('sandbox configuration is mandatory')
        if not isinstance(holdout_raw, Mapping):
            raise PolicyError('external holdout configuration is mandatory')

        parsed_commands = tuple(CommandSpec.from_dict(item) for item in commands_raw if isinstance(item, Mapping))
        if len(parsed_commands) != len(commands_raw):
            raise PolicyError('every command must be an object')
        if len({item.name for item in parsed_commands}) != len(parsed_commands):
            raise PolicyError('command names must be unique')
        parsed_rules = tuple(ApprovalRule.from_dict(item) for item in rules_raw if isinstance(item, Mapping))
        if len(parsed_rules) != len(rules_raw):
            raise PolicyError('every approval rule must be an object')
        holdout = HoldoutSpec.from_dict(holdout_raw)
        all_names = [item.name for item in parsed_commands] + [item.name for item in holdout.commands]
        if len(set(all_names)) != len(all_names):
            raise PolicyError('repository and holdout command names must be globally unique')

        normalized_repositories = tuple(sorted({str(item).strip() for item in repositories if str(item).strip()}))
        status_context = str(data.get('status_context', '')).strip()
        pipeline = str(data.get('pipeline', '')).strip()
        if not status_context or '@' in status_context or not pipeline:
            raise PolicyError('status_context prefix and pipeline are required; policy epoch is appended automatically')
        normalized = {
            'schema_version': 1,
            'allowed_repositories': list(normalized_repositories),
            'status_context': status_context,
            'pipeline': pipeline,
            'checkout_depth': _bounded_int(data, 'checkout_depth', 1, 1000),
            'lease_seconds': _bounded_int(data, 'lease_seconds', 30, 3600),
            'max_attempts': _bounded_int(data, 'max_attempts', 1, 20),
            'max_approval_ttl_seconds': _bounded_int(data, 'max_approval_ttl_seconds', 60, 86400),
            'max_output_bytes': _bounded_int(data, 'max_output_bytes', 1024, 10_000_000),
            'allowed_environment': sorted({str(item).strip() for item in data.get('allowed_environment', []) if str(item).strip()}),
            'sandbox': SandboxSpec.from_dict(sandbox_raw).to_dict(),
            'commands': [item.to_dict() for item in parsed_commands],
            'holdout': holdout.to_dict(),
            'approval_rules': [item.to_dict() for item in parsed_rules],
        }
        digest = hashlib.sha256(canonical_json(normalized)).hexdigest()
        return cls(
            schema_version=1,
            allowed_repositories=normalized_repositories,
            status_context=status_context,
            pipeline=pipeline,
            checkout_depth=normalized['checkout_depth'],
            lease_seconds=normalized['lease_seconds'],
            max_attempts=normalized['max_attempts'],
            max_approval_ttl_seconds=normalized['max_approval_ttl_seconds'],
            max_output_bytes=normalized['max_output_bytes'],
            allowed_environment=tuple(normalized['allowed_environment']),
            sandbox=SandboxSpec.from_dict(normalized['sandbox']),
            commands=parsed_commands,
            holdout=holdout,
            approval_rules=parsed_rules,
            digest=digest,
        )

    @property
    def check_name(self) -> str:
        """Policy epoch: a green check from an old policy cannot satisfy the new gate."""
        return f'{self.status_context}@{self.digest[:12]}'

    @property
    def approval_scopes(self) -> frozenset[str]:
        return frozenset(rule.scope for rule in self.approval_rules)

    def allows_repository(self, repository: str) -> bool:
        return repository in self.allowed_repositories

    def required_scopes(self, paths: Iterable[str]) -> set[str]:
        normalized = [str(path).replace('\\', '/').lstrip('./') for path in paths]
        scopes: set[str] = set()
        for rule in self.approval_rules:
            if any(_glob_match(path, pattern) for path in normalized for pattern in rule.globs):
                scopes.add(rule.scope)
        return scopes


def _glob_match(path: str, pattern: str) -> bool:
    if fnmatch.fnmatchcase(path, pattern):
        return True
    if pattern.endswith('/**'):
        prefix = pattern[:-3].rstrip('/')
        return path == prefix or path.startswith(prefix + '/')
    return False


def _bounded_int(data: Mapping[str, Any], key: str, minimum: int, maximum: int) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise PolicyError(f'{key} must be an integer between {minimum} and {maximum}')
    return value
