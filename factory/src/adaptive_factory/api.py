from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import re
from typing import Any, Mapping

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from .contracts import ContractError
from .models import Actor, LeaseGrant, RunRole
from .service import AuthorizationError
from .store import BudgetError, FenceError, StoreError


MAX_BODY_BYTES = 1_048_576
HEADER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _json(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if is_dataclass(value):
        return _json(asdict(value))
    if isinstance(value, Mapping):
        return {key: _json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json(item) for item in value]
    return value


class Authenticator:
    def __init__(self, tokens: Mapping[str, Actor]) -> None:
        if not tokens:
            raise ValueError("at least one local token is required")
        self._actors = tuple((hashlib.sha256(token.encode()).digest(), actor) for token, actor in tokens.items())

    def authenticate(self, authorization: str | None, scope: str) -> Actor:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "bearer authentication required", headers={"WWW-Authenticate": "Bearer"})
        candidate = hashlib.sha256(authorization[7:].encode()).digest()
        matched = None
        for digest, actor in self._actors:
            if hmac.compare_digest(candidate, digest):
                matched = actor
        if matched is None:
            raise HTTPException(401, "invalid bearer credential", headers={"WWW-Authenticate": "Bearer"})
        if scope not in matched.scopes:
            raise HTTPException(403, "scope denied")
        return matched


def _request_id(value: str | None, name: str) -> str:
    if not value or not HEADER_ID.fullmatch(value):
        raise HTTPException(400, f"valid {name} header required")
    return value


def _grant(payload: Mapping[str, Any]) -> LeaseGrant:
    expected = {"task_id", "run_id", "owner", "role", "fence", "expires_at", "packet_digest"}
    if set(payload) != expected:
        raise HTTPException(422, "closed lease grant required")
    try:
        expires = datetime.fromisoformat(str(payload["expires_at"]).replace("Z", "+00:00"))
        return LeaseGrant(
            str(payload["task_id"]),
            str(payload["run_id"]),
            str(payload["owner"]),
            RunRole(payload["role"]),
            int(payload["fence"]),
            expires,
            str(payload["packet_digest"]),
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, "invalid lease grant") from exc


def create_app(service, authenticator: Authenticator) -> FastAPI:
    app = FastAPI(title="Adaptive Factory Local Control API", version="1.0.0", docs_url=None, redoc_url=None)

    @app.exception_handler(ContractError)
    async def contract_error(_request: Request, error: ContractError):
        return JSONResponse({"error": "invalid", "code": error.code}, status_code=422)

    @app.exception_handler(AuthorizationError)
    async def authorization_error(_request: Request, _error: AuthorizationError):
        return JSONResponse({"error": "unauthorized"}, status_code=403)

    @app.exception_handler(FenceError)
    async def fence_error(_request: Request, _error: FenceError):
        return JSONResponse({"error": "conflict", "code": "stale_fence"}, status_code=409)

    @app.exception_handler(BudgetError)
    async def budget_error(_request: Request, _error: BudgetError):
        return JSONResponse({"error": "stopped", "code": "budget"}, status_code=409)

    @app.exception_handler(StoreError)
    async def store_error(_request: Request, _error: StoreError):
        return JSONResponse({"error": "conflict"}, status_code=409)

    @app.middleware("http")
    async def bound_body(request: Request, call_next):
        length = request.headers.get("content-length")
        if length and int(length) > MAX_BODY_BYTES:
            return JSONResponse({"detail": "request body too large"}, status_code=413)
        return await call_next(request)

    @app.get("/health/live", tags=["health"])
    def live():
        return {"status": "live"}

    @app.get("/health/ready", tags=["health"])
    def ready():
        return {"status": "ready"}

    @app.post("/v1/tasks", tags=["tasks"])
    def submit(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:submit")
        key = _request_id(idempotency_key, "Idempotency-Key")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        if payload.get("request_id") != key:
            raise HTTPException(409, "idempotency header does not match closed request")
        result = service.intake(payload, actor=actor, now=datetime.now(timezone.utc))
        return JSONResponse(
            _json({"task": result.task, "created": result.created}),
            status_code=201 if result.created else 200,
            headers={"X-Correlation-ID": correlation},
        )

    @app.get("/v1/tasks/{task_id}", tags=["tasks"])
    def show(task_id: str, authorization: str | None = Header(None), x_correlation_id: str | None = Header(None)):
        actor = authenticator.authenticate(authorization, "task:read")
        correlation = _request_id(x_correlation_id or "generated-read", "X-Correlation-ID")
        try:
            task = service.get_task(task_id, actor=actor)
        except KeyError:
            raise HTTPException(404, "task not found")
        return JSONResponse(_json(task), headers={"X-Correlation-ID": correlation})

    @app.get("/v1/tasks", tags=["tasks"])
    def list_tasks(
        repository_id: str,
        limit: int = 100,
        cursor: str | None = None,
        authorization: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:list")
        correlation = _request_id(x_correlation_id or "generated-list", "X-Correlation-ID")
        return JSONResponse(
            _json({"items": service.list_tasks(repository_id=repository_id, limit=limit, cursor=cursor, actor=actor)}),
            headers={"X-Correlation-ID": correlation},
        )

    @app.post("/v1/tasks/{task_id}/cancel", tags=["tasks"])
    def cancel(
        task_id: str,
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:cancel")
        key = _request_id(idempotency_key, "Idempotency-Key")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        if set(payload) != {"reason"}:
            raise HTTPException(422, "closed cancel body required")
        try:
            task = service.cancel(
                task_id, reason=str(payload["reason"]), idempotency_key=key, actor=actor, now=datetime.now(timezone.utc)
            )
        except KeyError:
            raise HTTPException(404, "task not found")
        return JSONResponse(_json(task), headers={"X-Correlation-ID": correlation})

    @app.post("/v1/claims", tags=["worker"])
    def claim(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:claim")
        _request_id(idempotency_key, "Idempotency-Key")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        expected = {"owner", "role", "repositories", "lease_seconds"}
        if set(payload) != expected:
            raise HTTPException(422, "closed claim body required")
        grant = service.claim(
            owner=payload["owner"],
            role=RunRole(payload["role"]),
            repositories=payload["repositories"],
            lease_seconds=payload["lease_seconds"],
            actor=actor,
            now=datetime.now(timezone.utc),
        )
        return JSONResponse(_json({"grant": grant}), headers={"X-Correlation-ID": correlation})

    @app.post("/v1/heartbeats", tags=["worker"])
    def heartbeat(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:heartbeat")
        _request_id(idempotency_key, "Idempotency-Key")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        return JSONResponse(
            _json(service.heartbeat(_grant(payload), actor=actor, now=datetime.now(timezone.utc))),
            headers={"X-Correlation-ID": correlation},
        )

    @app.post("/v1/proposals", tags=["worker"])
    def proposal(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:release")
        _request_id(idempotency_key, "Idempotency-Key")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        if set(payload) != {"grant", "outcome"}:
            raise HTTPException(422, "closed proposal body required")
        status = service.release(
            _grant(payload["grant"]), outcome=payload["outcome"], actor=actor, now=datetime.now(timezone.utc)
        )
        return JSONResponse(_json({"status": status}), headers={"X-Correlation-ID": correlation})

    @app.post("/v1/kill-switches", tags=["operator"])
    def kill(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "factory:kill")
        key = _request_id(idempotency_key, "Idempotency-Key")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        if set(payload) != {"scope_key", "enabled", "reason"}:
            raise HTTPException(422, "closed kill body required")
        enabled = service.set_kill(
            scope_key=payload["scope_key"],
            enabled=payload["enabled"],
            reason=payload["reason"],
            idempotency_key=key,
            actor=actor,
            now=datetime.now(timezone.utc),
        )
        return JSONResponse({"enabled": enabled}, headers={"X-Correlation-ID": correlation})

    @app.post("/v1/reconcile", tags=["operator"])
    def reconcile(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "factory:reconcile")
        _request_id(idempotency_key, "Idempotency-Key")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        if set(payload) - {"limit", "cursor"}:
            raise HTTPException(422, "closed reconcile body required")
        result = service.reconcile(
            actor=actor,
            now=datetime.now(timezone.utc),
            limit=int(payload.get("limit", 100)),
            cursor=payload.get("cursor"),
        )
        return JSONResponse(_json(result), headers={"X-Correlation-ID": correlation})

    return app
