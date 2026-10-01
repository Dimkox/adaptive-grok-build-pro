"""Bounded helpers for additive, non-authoritative Factory v1.5 sidecars."""

from dataclasses import dataclass
import json
from pathlib import PurePosixPath
import re
from collections.abc import Mapping

from .contracts import ContractError, HEX40, HEX64, _hex, _id, _text, _time, canonical_json, canonical_digest
from .brokers import BrokerError, _redact


def closed(data, fields):
    if not isinstance(data, Mapping) or set(data) != set(fields):
        raise ContractError("closed_object_required")


def version(data, wanted=1):
    if type(data["schema_version"]) is not int or data["schema_version"] != wanted:
        raise ContractError("unsupported_version")


def integer(value, name, minimum=0, maximum=2**63 - 1):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ContractError("invalid_integer", name)
    return value


def sequence(value, maximum=128):
    if not isinstance(value, list) or len(value) > maximum:
        raise ContractError("invalid_collection")
    return value


def safe_text(value, name, maximum=4096):
    _text(value, name, maximum)
    try:
        if _redact(value, maximum) != value:
            raise ContractError("secret_content")
    except BrokerError as exc:
        raise ContractError("unsafe_content") from exc
    return value


def path(value):
    safe_text(value, "path", 512)
    parts = value.split("/")
    if PurePosixPath(value).is_absolute() or "\\" in value or ":" in value or any(p in ("", ".", "..") for p in parts):
        raise ContractError("unsafe_path")
    if any(
        p.lower().startswith(".env")
        or p.lower() in ("secrets", "credentials", ".ssh", ".aws", ".gnupg")
        or re.search(r"(?i)\.(pem|key|p12|pfx)$", p)
        for p in parts
    ):
        raise ContractError("secret_path")
    return value


def digest(value):
    return _hex(value, "digest", HEX64)


def sha(value):
    return _hex(value, "sha", HEX40)


def identity(value):
    safe_text(value, "identity", 128)
    return _id(value, "identity")


def timestamp(value):
    return _time(value, "timestamp")


@dataclass(frozen=True)
class FrozenWire:
    """Store canonical immutable bytes; callers receive detached JSON objects."""

    _wire: bytes

    def to_dict(self):
        return json.loads(self._wire)

    @property
    def record_digest(self):
        return canonical_digest(self.to_dict())

    @classmethod
    def freeze(cls, data):
        return cls(canonical_json(data))
