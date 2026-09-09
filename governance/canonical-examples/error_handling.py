"""Domain failure exposing only an allowlisted safe message."""

from __future__ import annotations


class DomainError(Exception):
    def __init__(self, code: str, safe_message: str) -> None:
        if not code or not safe_message:
            raise ValueError("code and safe_message are required")
        self.code = code
        self.safe_message = safe_message
        super().__init__(safe_message)
