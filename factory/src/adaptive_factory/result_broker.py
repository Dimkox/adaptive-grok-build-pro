"""Offline result sanitization foundation; no runtime channel is qualified yet."""

from __future__ import annotations

from collections.abc import Iterable
import json
import math
import unicodedata
from typing import Any

from .brokers import BrokerError, _redact
from .contracts import ContractError, canonical_digest, canonical_json
from .result_contracts import (
    RESULT_CHANNELS, ResultEnvelopeV1, ResultEnvelopeV2, strict_json, sensitive_key,
)
from .v15_contracts import safe_text


_CONTENT_TYPES = frozenset({"application/json", "text/plain"})


class ResultBroker:
    def __init__(
        self, *, policy_version: str, max_bytes: int = 1_000_000,
        max_records: int = 1_000, max_depth: int = 32, max_chunks: int = 1_000,
    ) -> None:
        limits = ((max_bytes, 1_000_000), (max_records, 100_000),
                  (max_depth, 64), (max_chunks, 100_000))
        if any(type(value) is not int or not 1 <= value <= ceiling
               for value, ceiling in limits):
            raise ValueError("invalid_result_policy")
        try:
            safe_text(policy_version, "policy_version", 128)
        except (ContractError, TypeError, UnicodeError):
            raise ValueError("invalid_result_policy") from None
        self.policy_version = policy_version
        self.max_bytes = max_bytes
        self.max_records = max_records
        self.max_depth = max_depth
        self.max_chunks = max_chunks

    def _envelope(
        self, *, channel: str, content_type: str,
        outcome: str, reason_code: str, payload: str | None,
        identity: dict[str, Any] | None = None,
    ) -> ResultEnvelopeV1 | ResultEnvelopeV2:
        envelope = {
                "schema_version": 1,
                "channel": channel,
                "content_type": content_type,
                "outcome": outcome,
                "reason_code": reason_code,
                "completeness": "complete" if payload is not None else "missing",
                "policy_version": self.policy_version,
                "sanitized_payload": payload,
                "sanitized_payload_digest": canonical_digest(payload),
            }
        if identity is None:
            return ResultEnvelopeV1.from_dict(envelope)
        return ResultEnvelopeV2.from_dict({**identity, **envelope, "schema_version": 2})

    def inspect(
        self, *, channel: str, content_type: str, chunks: Iterable[bytes],
        identity: dict[str, Any] | None = None,
    ) -> ResultEnvelopeV1 | ResultEnvelopeV2:
        """Fail closed without consuming input while runtime interception is unproved."""
        channel, content_type, metadata_error = self._metadata(
            channel, content_type, allow_unknown=True,
        )
        if metadata_error is not None:
            return self._envelope(
                channel=channel, content_type=content_type,
                outcome="rejected", reason_code=metadata_error, payload=None, identity=identity,
            )
        return self._envelope(
            channel=channel, content_type=content_type,
            outcome="unavailable", reason_code="runtime_wiring_missing", payload=None, identity=identity,
        )

    def sanitize_candidate(
        self, *, channel: str, content_type: str, chunks: Iterable[bytes],
        identity: dict[str, Any] | None = None,
    ) -> ResultEnvelopeV1 | ResultEnvelopeV2:
        """Exercise the policy offline without asserting a pre-model interception point."""
        channel, content_type, metadata_error = self._metadata(channel, content_type)
        if metadata_error is not None:
            return self._envelope(
                channel=channel, content_type=content_type,
                outcome="rejected", reason_code=metadata_error, payload=None, identity=identity,
            )
        if content_type not in _CONTENT_TYPES:
            return self._envelope(
                channel=channel, content_type=content_type,
                outcome="rejected", reason_code="unsupported_content_type", payload=None, identity=identity,
            )
        try:
            buffered = bytearray()
            for index, chunk in enumerate(chunks):
                if index >= self.max_chunks:
                    return self._envelope(
                        channel=channel, content_type=content_type,
                        outcome="rejected", reason_code="chunk_limit", payload=None, identity=identity,
                    )
                if not isinstance(chunk, bytes):
                    return self._envelope(
                        channel=channel, content_type=content_type,
                        outcome="rejected", reason_code="invalid_chunk", payload=None, identity=identity,
                    )
                if len(chunk) > self.max_bytes - len(buffered):
                    return self._envelope(
                        channel=channel, content_type=content_type,
                        outcome="rejected", reason_code="result_too_large", payload=None, identity=identity,
                    )
                buffered.extend(chunk)
        except Exception:
            return self._envelope(
                channel=channel, content_type=content_type,
                outcome="rejected", reason_code="result_stream_failure", payload=None, identity=identity,
            )
        try:
            text = bytes(buffered).decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return self._envelope(
                channel=channel, content_type=content_type,
                outcome="rejected", reason_code="invalid_encoding", payload=None, identity=identity,
            )
        try:
            if content_type == "application/json":
                value = strict_json(text)
                self._check_shape(value)
                sanitized, changed = self._sanitize_tree(value)
                payload = canonical_json(sanitized).decode("utf-8")
            else:
                if unicodedata.normalize("NFC", text) != text or any(
                    ord(char) < 32 and char not in {"\n", "\t"} for char in text
                ):
                    raise _ShapeError("malformed_payload")
                payload = _redact(text, self.max_bytes)
                changed = payload != text
            return self._envelope(
                channel=channel, content_type=content_type,
                outcome="redacted" if changed else "allow",
                reason_code="known_secret_redacted" if changed else "accepted", payload=payload,
                identity=identity,
            )
        except (json.JSONDecodeError, RecursionError):
            reason = "malformed_payload"
        except _ShapeError as exc:
            reason = exc.reason
        except ContractError as exc:
            reason = "duplicate_json_key" if exc.code == "duplicate_json_key" else "sanitizer_failure"
        except (BrokerError, UnicodeError):
            reason = "sanitizer_failure"
        except Exception:
            reason = "sanitizer_failure"
        return self._envelope(
            channel=channel, content_type=content_type,
            outcome="rejected", reason_code=reason, payload=None, identity=identity,
        )

    @staticmethod
    def _metadata(
        channel: Any, content_type: Any, *, allow_unknown: bool = False,
    ) -> tuple[str, str, str | None]:
        known_channel = isinstance(channel, str) and channel in RESULT_CHANNELS
        safe_channel = channel if known_channel else "unknown"
        if not known_channel or (safe_channel == "unknown" and not allow_unknown):
            return safe_channel, "application/octet-stream", "invalid_channel"
        try:
            safe_content_type = safe_text(content_type, "content_type", 128)
        except (ContractError, TypeError, UnicodeError):
            return safe_channel, "application/octet-stream", "invalid_content_type"
        return safe_channel, safe_content_type, None

    def _check_shape(self, value: Any) -> None:
        records = 0

        def visit(item: Any, depth: int) -> None:
            nonlocal records
            if depth > self.max_depth:
                raise _ShapeError("depth_limit")
            if isinstance(item, dict):
                records += len(item)
                for key, child in item.items():
                    if not isinstance(key, str):
                        raise _ShapeError("malformed_payload")
                    visit(child, depth + 1)
            elif isinstance(item, list):
                records += len(item)
                for child in item:
                    visit(child, depth + 1)
            elif item is not None and not isinstance(item, (str, int, float, bool)):
                raise _ShapeError("malformed_payload")
            elif isinstance(item, float) and not math.isfinite(item):
                raise _ShapeError("malformed_payload")
            if records > self.max_records:
                raise _ShapeError("record_limit")

        visit(value, 1)

    def _sanitize_tree(self, value: Any) -> tuple[Any, bool]:
        if isinstance(value, str):
            cleaned = _redact(value, self.max_bytes)
            return cleaned, cleaned != value
        if isinstance(value, list):
            pairs = [self._sanitize_tree(item) for item in value]
            return [item for item, _ in pairs], any(changed for _, changed in pairs)
        if isinstance(value, dict):
            sanitized = {}
            changed = False
            for key, item in value.items():
                safe_key = _redact(key, self.max_bytes)
                if sensitive_key(key):
                    safe_key = "[REDACTED]"
                    item = "[REDACTED]"
                    changed = True
                if safe_key in sanitized:
                    raise BrokerError("redacted_key_collision")
                safe_item, item_changed = self._sanitize_tree(item)
                sanitized[safe_key] = safe_item
                changed = changed or safe_key != key or item_changed
            return sanitized, changed
        return value, False


class _ShapeError(ValueError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
