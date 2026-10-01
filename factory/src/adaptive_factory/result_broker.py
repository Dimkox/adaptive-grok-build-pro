"""Offline result sanitization foundation; no runtime channel is qualified yet."""

from __future__ import annotations

from collections.abc import Iterable
import json
import math
import unicodedata
from typing import Any

from .brokers import BrokerError, _redact
from .contracts import ContractError, canonical_digest, canonical_json
from .result_contracts import RESULT_CHANNELS, ResultEnvelopeV1
from .v15_contracts import safe_text


_CONTENT_TYPES = frozenset({"application/json", "text/plain"})


class ResultBroker:
    def __init__(
        self, *, policy_version: str, max_bytes: int = 1_000_000,
        max_records: int = 1_000, max_depth: int = 32,
    ) -> None:
        if not policy_version or min(max_bytes, max_records, max_depth) < 1:
            raise ValueError("invalid_result_policy")
        self.policy_version = policy_version
        self.max_bytes = max_bytes
        self.max_records = max_records
        self.max_depth = max_depth

    def _envelope(
        self, *, channel: str, content_type: str,
        outcome: str, reason_code: str, payload: str | None,
    ) -> ResultEnvelopeV1:
        return ResultEnvelopeV1.from_dict(
            {
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
        )

    def inspect(
        self, *, channel: str, content_type: str, chunks: Iterable[bytes],
    ) -> ResultEnvelopeV1:
        """Fail closed without consuming input while runtime interception is unproved."""
        channel, content_type, metadata_error = self._metadata(channel, content_type)
        if metadata_error is not None:
            return self._envelope(
                channel=channel, content_type=content_type,
                outcome="rejected", reason_code=metadata_error, payload=None,
            )
        return self._envelope(
            channel=channel, content_type=content_type,
            outcome="unavailable", reason_code="runtime_wiring_missing", payload=None,
        )

    def sanitize_candidate(
        self, *, channel: str, content_type: str, chunks: Iterable[bytes],
    ) -> ResultEnvelopeV1:
        """Exercise the policy offline without asserting a pre-model interception point."""
        channel, content_type, metadata_error = self._metadata(channel, content_type)
        if metadata_error is not None:
            return self._envelope(
                channel=channel, content_type=content_type,
                outcome="rejected", reason_code=metadata_error, payload=None,
            )
        if content_type not in _CONTENT_TYPES:
            return self._envelope(
                channel=channel, content_type=content_type,
                outcome="rejected", reason_code="unsupported_content_type", payload=None,
            )
        try:
            buffered = bytearray()
            for chunk in chunks:
                if not isinstance(chunk, bytes):
                    return self._envelope(
                        channel=channel, content_type=content_type,
                        outcome="rejected", reason_code="invalid_chunk", payload=None,
                    )
                buffered.extend(chunk)
                if len(buffered) > self.max_bytes:
                    return self._envelope(
                        channel=channel, content_type=content_type,
                        outcome="rejected", reason_code="result_too_large", payload=None,
                    )
        except Exception:
            return self._envelope(
                channel=channel, content_type=content_type,
                outcome="rejected", reason_code="result_stream_failure", payload=None,
            )
        try:
            text = bytes(buffered).decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return self._envelope(
                channel=channel, content_type=content_type,
                outcome="rejected", reason_code="invalid_encoding", payload=None,
            )
        try:
            if content_type == "application/json":
                value = json.loads(text)
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
            )
        except (json.JSONDecodeError, RecursionError):
            reason = "malformed_payload"
        except _ShapeError as exc:
            reason = exc.reason
        except (BrokerError, ContractError, UnicodeError):
            reason = "sanitizer_failure"
        except Exception:
            reason = "sanitizer_failure"
        return self._envelope(
            channel=channel, content_type=content_type,
            outcome="rejected", reason_code=reason, payload=None,
        )

    @staticmethod
    def _metadata(channel: Any, content_type: Any) -> tuple[str, str, str | None]:
        safe_channel = channel if isinstance(channel, str) and channel in RESULT_CHANNELS else "unknown"
        if safe_channel == "unknown":
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
