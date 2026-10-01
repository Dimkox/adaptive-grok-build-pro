"""Bounded delivery of admitted result envelopes to the next-model boundary."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Mapping

import httpx



HEX64 = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


@dataclass(frozen=True)
class DispatchClaim:
    request_digest: str
    operation_id: str
    envelope_digest: str
    task_id: str
    run_id: str
    attempt_id: str
    claim_token: str
    dispatcher_id: str
    state: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if not HEX64.fullmatch(self.request_digest) or not HEX64.fullmatch(self.envelope_digest):
            raise ValueError("invalid dispatch digest")
        if not HEX64.fullmatch(self.claim_token):
            raise ValueError("invalid dispatch claim token")
        if not IDENTIFIER.fullmatch(self.dispatcher_id):
            raise ValueError("invalid dispatcher identifier")
        if self.operation_id != f"factory-result:{self.request_digest}":
            raise ValueError("operation identity is not bound to request")
        if self.state not in {"claimed", "unknown"}:
            raise ValueError("invalid dispatch claim state")
        if not isinstance(self.payload, Mapping):
            raise ValueError("invalid dispatch payload")


@dataclass(frozen=True)
class DispatchOutcome:
    state: str
    reason_code: str
    observation_digest: str | None

    def __post_init__(self) -> None:
        if self.state not in {"delivered", "failed", "unknown"}:
            raise ValueError("invalid dispatch outcome")
        if not IDENTIFIER.fullmatch(self.reason_code):
            raise ValueError("invalid dispatch reason")
        if self.observation_digest is not None and not HEX64.fullmatch(self.observation_digest):
            raise ValueError("invalid observation digest")
        if self.state == "delivered" and self.observation_digest is None:
            raise ValueError("delivered dispatch requires observation")


class UdsModelRequestClient:
    """Authenticated, non-retrying HTTP client over an explicitly configured UDS."""

    def __init__(
        self,
        socket_path: Path,
        token: str,
        *,
        timeout_seconds: float = 5.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not isinstance(socket_path, Path) or not socket_path.is_absolute() or ".." in socket_path.parts:
            raise ValueError("model request socket must be an absolute normalized path")
        if not isinstance(token, str) or len(token) < 16 or any(character.isspace() for character in token):
            raise ValueError("model request token is invalid")
        if not isinstance(timeout_seconds, (int, float)) or not 0.1 <= timeout_seconds <= 30:
            raise ValueError("model request timeout is invalid")
        self._socket_path = socket_path
        self._token = token
        self._timeout = float(timeout_seconds)
        self._transport = transport

    def _client(self) -> httpx.Client:
        transport = self._transport or httpx.HTTPTransport(uds=str(self._socket_path), retries=0)
        return httpx.Client(transport=transport, timeout=self._timeout, base_url="http://factory-model")

    def _headers(self, claim: DispatchClaim) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Idempotency-Key": claim.operation_id,
            "X-Operation-ID": claim.operation_id,
        }

    @staticmethod
    def _outcome(response: httpx.Response, *, observation: bool) -> DispatchOutcome:
        if response.status_code >= 500:
            return DispatchOutcome("unknown", "observation_unavailable" if observation else "post_outcome_ambiguous", None)
        if response.status_code >= 400:
            return DispatchOutcome("failed", "recipient_rejected", None)
        try:
            body = response.json()
        except ValueError:
            return DispatchOutcome("unknown", "invalid_observation", None)
        if not isinstance(body, dict) or set(body) - {"status", "observation_digest", "reason_code"}:
            return DispatchOutcome("unknown", "invalid_observation", None)
        status = body.get("status")
        digest = body.get("observation_digest")
        if status == "delivered":
            if isinstance(digest, str) and HEX64.fullmatch(digest):
                return DispatchOutcome("delivered", "observed", digest)
            return DispatchOutcome("unknown", "invalid_observation", None)
        if status == "failed":
            if digest is not None and (not isinstance(digest, str) or not HEX64.fullmatch(digest)):
                return DispatchOutcome("unknown", "invalid_observation", None)
            return DispatchOutcome("failed", "effect_failed", digest)
        return DispatchOutcome("unknown", "observation_pending", None)

    def dispatch(self, claim: DispatchClaim) -> DispatchOutcome:
        body = {
            "operation_id": claim.operation_id,
            "request_digest": claim.request_digest,
            "envelope_digest": claim.envelope_digest,
            "task_id": claim.task_id,
            "run_id": claim.run_id,
            "attempt_id": claim.attempt_id,
            "result_envelope": dict(claim.payload),
        }
        try:
            with self._client() as client:
                response = client.post("/v1/model-requests", headers=self._headers(claim), json=body)
        except httpx.HTTPError:
            return DispatchOutcome("unknown", "post_outcome_ambiguous", None)
        outcome = self._outcome(response, observation=False)
        if outcome.state == "delivered":
            return DispatchOutcome("delivered", "accepted", outcome.observation_digest)
        return outcome

    def observe(self, claim: DispatchClaim) -> DispatchOutcome:
        try:
            with self._client() as client:
                response = client.get(
                    f"/v1/model-requests/{claim.operation_id}", headers=self._headers(claim)
                )
        except httpx.HTTPError:
            return DispatchOutcome("unknown", "observation_unavailable", None)
        return self._outcome(response, observation=True)


class ResultDispatcher:
    """Single bounded poller. Durable state remains in PostgreSQL."""

    def __init__(
        self,
        store,
        client: UdsModelRequestClient,
        *,
        dispatcher_id: str,
        batch_size: int = 8,
        lease_seconds: int = 30,
        poll_seconds: float = 1.0,
    ) -> None:
        if not isinstance(dispatcher_id, str) or not IDENTIFIER.fullmatch(dispatcher_id):
            raise ValueError("invalid dispatcher identifier")
        if type(batch_size) is not int or not 1 <= batch_size <= 100:
            raise ValueError("invalid dispatcher batch size")
        if type(lease_seconds) is not int or not 5 <= lease_seconds <= 300:
            raise ValueError("invalid dispatcher lease")
        if not isinstance(poll_seconds, (int, float)) or not 0.05 <= poll_seconds <= 60:
            raise ValueError("invalid dispatcher poll interval")
        self.store = store
        self.client = client
        self.dispatcher_id = dispatcher_id
        self.batch_size = batch_size
        self.lease_seconds = lease_seconds
        self.poll_seconds = float(poll_seconds)
        self.last_error: Exception | None = None

    def run_once(self) -> int:
        self.store.reconcile_model_requests(self.dispatcher_id, limit=self.batch_size)
        claims = self.store.claim_model_requests(
            self.dispatcher_id, limit=self.batch_size, lease_seconds=self.lease_seconds
        )
        for claim in claims:
            if claim.dispatcher_id != self.dispatcher_id:
                raise RuntimeError("dispatch claim owner mismatch")
            if claim.state == "unknown":
                outcome = self.client.observe(claim)
            else:
                self.store.start_model_request_dispatch(claim)
                outcome = self.client.dispatch(claim)
            self.store.record_model_request_dispatch(claim, outcome)
        return len(claims)
