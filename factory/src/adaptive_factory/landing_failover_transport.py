"""Bounded authenticated Unix HTTP; ambiguity never becomes a new submission."""

import asyncio
import errno
import os
import stat
import time

import httpx

from .landing_contracts import strict_json_object
from .landing_failover_config import check_socket_ancestry
from .settings import read_token_file


class BackendUnavailable(RuntimeError):
    pass


class BackendAmbiguous(RuntimeError):
    pass


class BackendTimeout(BackendAmbiguous):
    pass


class BackendRejected(RuntimeError):
    pass


class UnixLandingBackend:
    def __init__(self, backend, *, config, timeout_seconds):
        self.backend, self.config = backend, config
        self.deadline = time.monotonic() + timeout_seconds
        token = read_token_file(backend.token_file)
        self.closed = False
        self.headers = {"Authorization": "Bearer " + token,
                        "X-Repository-ID": config.repository_id, "X-Correlation-ID": "failover-client",
                        "Accept": "application/json", "Accept-Encoding": "identity"}

    def close(self):
        self.closed = True
        self.headers.clear()

    def capability(self):
        check_socket_ancestry(self.backend.socket_path)
        try:
            metadata = self.backend.socket_path.lstat()
        except FileNotFoundError:
            raise BackendUnavailable("not_connected") from None
        if not stat.S_ISSOCK(metadata.st_mode) or metadata.st_uid != os.geteuid():
            raise BackendRejected("socket_identity")
        try:
            return self._exchange("GET", "/v2/landing-backend", expected=200, timeout_seconds=2)
        except BackendTimeout:
            raise BackendUnavailable("capability_timeout") from None
        except BackendAmbiguous as exc:
            # A failed capability GET sends no input and has no provider effect.
            cause = exc.__cause__
            while cause is not None:
                if isinstance(cause, OSError) and cause.errno in {errno.ENOENT, errno.ECONNREFUSED}:
                    raise BackendUnavailable("not_connected") from None
                cause = cause.__cause__
            raise

    def submit(self, child_id, payload, media_type):
        check_socket_ancestry(self.backend.socket_path)
        return self._exchange("POST", "/v1/landing-inputs", expected=202, payload=payload, extra={
            "Idempotency-Key": child_id, "Content-Type": media_type,
            "X-Exact-Base-SHA": self.config.exact_base_sha, "X-Exact-Base-Tree": self.config.exact_base_tree,
            "X-Expected-Actor-ID": self.config.actor_id, "X-Expected-Profile-Digest": self.backend.profile_digest,
        })

    def observe(self, child_id):
        return self._exchange("GET", "/v2/landing-jobs/" + child_id + "/attempt", expected=200)

    def _exchange(self, method, path, *, expected, payload=None, extra=None, timeout_seconds=None):
        if self.closed:
            raise BackendRejected("backend_closed")
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise BackendRejected("caller_sync_context")
        deadline = min(self.deadline, time.monotonic() + timeout_seconds) if timeout_seconds is not None else self.deadline
        return asyncio.run(self._exchange_async(method, path, expected, payload, extra, deadline))

    async def _exchange_async(self, method, path, expected, payload, extra, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BackendTimeout("deadline")
        try:
            # Each loop owns and closes its connection pool. Cancellation covers
            # blocked request writes, incomplete headers and slow response bodies.
            async with asyncio.timeout(remaining), httpx.AsyncClient(
                transport=httpx.AsyncHTTPTransport(uds=str(self.backend.socket_path), retries=0),
                base_url="http://landing", trust_env=False, follow_redirects=False,
                timeout=httpx.Timeout(remaining, connect=min(2, remaining)),
            ) as client:
                async with client.stream(method, path, content=payload, headers={**self.headers, **(extra or {})}) as response:
                    if response.status_code != expected:
                        if response.status_code in {401, 403, 409, 413, 415, 422}:
                            raise BackendRejected("backend_rejected")
                        raise BackendAmbiguous("backend_outcome_unknown")
                    if response.headers.get("content-type", "").split(";", 1)[0] != "application/json" or response.headers.get("content-encoding", "identity") != "identity":
                        raise BackendAmbiguous("backend_protocol")
                    raw = bytearray()
                    async for chunk in response.aiter_raw():
                        if time.monotonic() >= deadline:
                            raise BackendTimeout("deadline")
                        if len(raw) + len(chunk) > 65_536:
                            raise BackendAmbiguous("backend_bound")
                        raw.extend(chunk)
                    return strict_json_object(bytes(raw), maximum=65_536)
        except (TimeoutError, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
            raise BackendTimeout("deadline") from exc
        except (httpx.HTTPError, OSError, ValueError) as exc:
            raise BackendAmbiguous("backend_outcome_unknown") from exc
