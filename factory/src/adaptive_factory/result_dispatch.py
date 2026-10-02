"""Bounded delivery of admitted result envelopes to the next-model boundary."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from pathlib import Path
import stat
from typing import Mapping

import httpx

from .contracts import canonical_digest



HEX64 = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


@dataclass(frozen=True)
class DispatchClaim:
    request_digest: str
    operation_id: str
    envelope_digest: str
    repository_id: str
    task_id: str
    run_id: str
    fence: int
    packet_digest: str
    attempt_id: str
    claim_token: str
    dispatcher_id: str
    state: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if (
            not HEX64.fullmatch(self.request_digest)
            or not HEX64.fullmatch(self.envelope_digest)
            or not HEX64.fullmatch(self.packet_digest)
        ):
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
        expected_identity = {
            "repository_id": self.repository_id,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "fence": self.fence,
            "packet_digest": self.packet_digest,
            "attempt_id": self.attempt_id,
        }
        if any(self.payload.get(key) != value for key, value in expected_identity.items()):
            raise ValueError("dispatch payload identity mismatch")


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


class UdsResultHandoffClient:
    """Authenticated ingress-only result handoff over one configured UDS."""

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
        self._socket_identity = self._validate_socket()

    def _validate_socket(self) -> tuple[int, int]:
        effective_uid = os.geteuid()
        parents = tuple(reversed(self._socket_path.parents))
        try:
            for index, parent in enumerate(parents):
                metadata = parent.lstat()
                mode = stat.S_IMODE(metadata.st_mode)
                root_sticky = metadata.st_uid == 0 and bool(metadata.st_mode & stat.S_ISVTX)
                if (
                    not stat.S_ISDIR(metadata.st_mode)
                    or metadata.st_uid not in {0, effective_uid}
                    or (mode & 0o022 and not root_sticky)
                    or (index == len(parents) - 1 and (metadata.st_uid != effective_uid or mode & 0o022))
                ):
                    raise ValueError("model request socket ancestry is not trusted")
            metadata = self._socket_path.lstat()
        except OSError as exc:
            raise ValueError("model request socket identity is not trusted") from exc
        if (
            not stat.S_ISSOCK(metadata.st_mode)
            or metadata.st_uid != effective_uid
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise ValueError("model request socket identity is not trusted")
        return metadata.st_dev, metadata.st_ino

    def _revalidate_socket(self) -> None:
        if self._validate_socket() != self._socket_identity:
            raise ValueError("model request socket identity changed")

    def _client(self) -> httpx.Client:
        transport = self._transport or httpx.HTTPTransport(uds=str(self._socket_path), retries=0)
        return httpx.Client(
            transport=transport,
            timeout=self._timeout,
            base_url="http://factory-result-handoff",
            trust_env=False,
            follow_redirects=False,
        )

    def _headers(self, claim: DispatchClaim) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Idempotency-Key": claim.operation_id,
            "X-Operation-ID": claim.operation_id,
        }

    @staticmethod
    def _postcondition_digest(claim: DispatchClaim) -> str:
        return canonical_digest({
            "contract": "next-model-result-postcondition/v1",
            "operation_id": claim.operation_id,
            "request_digest": claim.request_digest,
            "envelope_digest": claim.envelope_digest,
        })

    @classmethod
    def _outcome(
        cls, status_code: int, content_type: str, raw: bytes,
        claim: DispatchClaim, *, observation: bool
    ) -> DispatchOutcome:
        ambiguous_reason = "observation_unavailable" if observation else "post_outcome_ambiguous"
        if status_code not in {200, 409}:
            return DispatchOutcome("unknown", ambiguous_reason, None)
        if content_type != "application/json":
            return DispatchOutcome("unknown", "invalid_observation", None)
        def closed_pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("duplicate response key")
                result[key] = value
            return result
        try:
            body = json.loads(raw, object_pairs_hook=closed_pairs)
        except (UnicodeDecodeError, ValueError):
            return DispatchOutcome(
                "unknown", ambiguous_reason if status_code >= 400 else "invalid_observation", None
            )
        required = {
            "status", "operation_id", "request_digest", "envelope_digest",
            "postcondition_digest",
        }
        if (
            not isinstance(body, dict)
            or set(body) != required
            or body.get("operation_id") != claim.operation_id
            or body.get("request_digest") != claim.request_digest
            or body.get("envelope_digest") != claim.envelope_digest
        ):
            return DispatchOutcome(
                "unknown", ambiguous_reason if status_code >= 400 else "invalid_observation", None
            )
        status = body.get("status")
        digest = body.get("postcondition_digest")
        if status == "delivered":
            if digest == cls._postcondition_digest(claim):
                return DispatchOutcome("delivered", "observed", digest)
            return DispatchOutcome("unknown", "invalid_observation", None)
        if status == "failed":
            if digest is not None:
                return DispatchOutcome("unknown", "invalid_observation", None)
            return DispatchOutcome("failed", "effect_failed", None)
        if status_code >= 400:
            return DispatchOutcome("unknown", ambiguous_reason, None)
        return DispatchOutcome("unknown", "observation_pending", None)

    def _request(self, method: str, path: str, claim: DispatchClaim, **kwargs) -> DispatchOutcome:
        self._revalidate_socket()
        try:
            with self._client() as client, client.stream(
                method, path, headers=self._headers(claim), **kwargs
            ) as response:
                raw = bytearray()
                for chunk in response.iter_bytes():
                    if len(raw) + len(chunk) > 65_536:
                        return DispatchOutcome("unknown", "invalid_observation", None)
                    raw.extend(chunk)
                self._revalidate_socket()
                return self._outcome(
                    response.status_code, response.headers.get("content-type", ""),
                    bytes(raw), claim, observation=method == "GET"
                )
        except httpx.HTTPError:
            return DispatchOutcome(
                "unknown", "observation_unavailable" if method == "GET" else "post_outcome_ambiguous", None
            )

    def dispatch(self, claim: DispatchClaim) -> DispatchOutcome:
        body = {
            "contract": "adaptive-factory.native-result-handoff/v1",
            "operation_id": claim.operation_id,
            "request_digest": claim.request_digest,
            "envelope_digest": claim.envelope_digest,
            "repository_id": claim.repository_id,
            "task_id": claim.task_id,
            "run_id": claim.run_id,
            "fence": claim.fence,
            "packet_digest": claim.packet_digest,
            "attempt_id": claim.attempt_id,
            "result_envelope": dict(claim.payload),
        }
        outcome = self._request("POST", "/v1/native-result-handoffs", claim, json=body)
        if outcome.state == "delivered":
            return DispatchOutcome("delivered", "accepted", outcome.observation_digest)
        return outcome

    def observe(self, claim: DispatchClaim) -> DispatchOutcome:
        return self._request("GET", f"/v1/native-result-handoffs/{claim.operation_id}", claim)


class ResultDispatcher:
    """Single bounded poller. Durable state remains in PostgreSQL."""

    def __init__(
        self,
        store,
        client: UdsResultHandoffClient,
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
