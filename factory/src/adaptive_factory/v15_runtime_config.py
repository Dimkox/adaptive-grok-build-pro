"""Closed operator-owned enablement for optional Factory v1.5 runtimes."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

from .settings import SettingsError, read_private_file


_IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,255}")
_SHA1 = re.compile(r"[0-9a-f]{40}")
_DIGEST = re.compile(r"[0-9a-f]{64}")


def _closed(value, keys, message):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise SettingsError(message)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SettingsError("duplicate v1.5 configuration key")
        result[key] = value
    return result


@dataclass(frozen=True)
class AdapterBinding:
    enabled: bool
    path: Path | None
    digest: str | None


@dataclass(frozen=True)
class V15RuntimeBinding:
    tenant_id: str
    repository_id: str
    exact_head_sha: str
    fpf: AdapterBinding
    vibevm: AdapterBinding
    prediction: AdapterBinding


@dataclass(frozen=True)
class V15RuntimeConfig:
    bindings: tuple[V15RuntimeBinding, ...]
    config_digest: str

    def resolve(self, tenant_id: str, repository_id: str, exact_head_sha: str):
        key = tenant_id, repository_id, exact_head_sha
        return next(
            (
                binding
                for binding in self.bindings
                if (binding.tenant_id, binding.repository_id, binding.exact_head_sha) == key
            ),
            None,
        )


def _adapter(value, name: str) -> AdapterBinding:
    _closed(value, ("enabled", "path", "digest"), f"closed {name} binding required")
    enabled, raw_path, expected = value["enabled"], value["path"], value["digest"]
    if type(enabled) is not bool:
        raise SettingsError(f"invalid {name} enablement")
    if not enabled:
        if raw_path is not None or expected is not None:
            raise SettingsError(f"disabled {name} binding must be empty")
        return AdapterBinding(False, None, None)
    if not isinstance(raw_path, str) or not isinstance(expected, str) or not _DIGEST.fullmatch(expected):
        raise SettingsError(f"exact {name} artifact binding required")
    path = Path(raw_path)
    if not path.is_absolute() or path.anchor == "//" or ".." in path.parts:
        raise SettingsError(f"absolute normalized {name} artifact path required")
    raw = read_private_file(path, 4_194_304)
    if hashlib.sha256(raw).hexdigest() != expected:
        raise SettingsError(f"{name} artifact digest mismatch")
    return AdapterBinding(True, path, expected)


def load_v15_runtime_config(path: Path) -> V15RuntimeConfig:
    try:
        raw = read_private_file(path, 131_072)
        payload = json.loads(raw, object_pairs_hook=_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise SettingsError("v1.5 runtime configuration must be valid JSON") from exc
    _closed(payload, ("schema_version", "bindings"), "closed v1.5 runtime configuration required")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise SettingsError("unsupported v1.5 runtime configuration")
    records = payload["bindings"]
    if not isinstance(records, list) or len(records) > 128:
        raise SettingsError("bounded v1.5 runtime bindings required")
    bindings = []
    keys = set()
    for record in records:
        _closed(
            record,
            ("tenant_id", "repository_id", "exact_head_sha", "fpf", "vibevm", "prediction"),
            "closed v1.5 runtime binding required",
        )
        tenant, repository, head = record["tenant_id"], record["repository_id"], record["exact_head_sha"]
        if (
            not isinstance(tenant, str)
            or not isinstance(repository, str)
            or not _IDENTITY.fullmatch(tenant)
            or not _IDENTITY.fullmatch(repository)
            or not isinstance(head, str)
            or not _SHA1.fullmatch(head)
        ):
            raise SettingsError("exact v1.5 authority binding required")
        key = tenant, repository, head
        if key in keys:
            raise SettingsError("duplicate v1.5 authority binding")
        keys.add(key)
        bindings.append(
            V15RuntimeBinding(
                tenant,
                repository,
                head,
                _adapter(record["fpf"], "fpf"),
                _adapter(record["vibevm"], "vibevm"),
                _adapter(record["prediction"], "prediction"),
            )
        )
    return V15RuntimeConfig(tuple(bindings), hashlib.sha256(raw).hexdigest())
