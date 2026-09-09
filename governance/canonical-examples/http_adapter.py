"""Small HTTP adapter boundary with explicit transport and timeout policy."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class HttpAdapterError(RuntimeError):
    """A safe, typed adapter failure."""


class HttpAdapter:
    def __init__(self, transport: Callable[[str, str, float, str], Any]) -> None:
        self._transport = transport

    def request(
        self,
        method: str,
        path: str,
        *,
        timeout_seconds: float,
        correlation_id: str,
    ) -> Any:
        normalized_method = method.upper()
        if normalized_method not in {"DELETE", "GET", "PATCH", "POST", "PUT"}:
            raise HttpAdapterError("unsupported HTTP method")
        if not path.startswith("/") or path.startswith("//"):
            raise HttpAdapterError("path must be origin-relative")
        if isinstance(timeout_seconds, bool) or not 0 < timeout_seconds <= 30:
            raise HttpAdapterError("timeout must be between 0 and 30 seconds")
        if not correlation_id:
            raise HttpAdapterError("correlation_id is required")
        try:
            return self._transport(
                normalized_method, path, timeout_seconds, correlation_id
            )
        except TimeoutError as exc:
            raise HttpAdapterError("upstream request timed out") from exc
