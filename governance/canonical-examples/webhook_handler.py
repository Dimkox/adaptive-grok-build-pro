"""Constant-time SHA-256 webhook verification without secret logging."""

from __future__ import annotations

import hashlib
import hmac


class WebhookVerificationError(ValueError):
    """A typed malformed-input failure."""


def verify_webhook(raw_body: bytes, signature: str, secret: bytes) -> bool:
    if not isinstance(raw_body, bytes) or not isinstance(secret, bytes) or not secret:
        raise WebhookVerificationError("raw_body and non-empty secret must be bytes")
    if not isinstance(signature, str) or len(signature) != 64:
        return False
    try:
        supplied = bytes.fromhex(signature)
    except ValueError:
        return False
    expected = hmac.new(secret, raw_body, hashlib.sha256).digest()
    return hmac.compare_digest(expected, supplied)
