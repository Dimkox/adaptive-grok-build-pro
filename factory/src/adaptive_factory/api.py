from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import re
import queue
import threading
import uuid
from typing import Any, Mapping

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .brokers import BrokerError, secret_free_identity
from .contracts import ContractError, canonical_digest
from .execution_contracts import ExecutionContractError
from .landing_contracts import MAX_INPUT_BYTES, MEDIA_TYPES
from .landing_service import LandingApplicationService, LandingServiceError
from .models import Actor, ExecutionStage, LeaseGrant, RunRole, TaskStatus
from .service import (
    AuthorizationError,
    SnapshotBrokerIntegrityError,
    SnapshotBrokerUnavailable,
)
from .store import (
    AuthorityError,
    BudgetError,
    FenceError,
    IntegrityError,
    MetricsUnavailable,
    StoreError,
    StoreUnavailable,
    TransitionError,
)


MAX_BODY_BYTES = 1_048_576
HEADER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
TEXT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
HEX64_TEXT = re.compile(r"^[0-9a-f]{64}$")
BODY_BEARING_METHODS = frozenset({"POST", "PUT", "PATCH"})
LANDING_SUBMIT_PATH = "/v1/landing-inputs"


def _json(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if is_dataclass(value):
        return {field.name: _json(getattr(value, field.name)) for field in fields(value)}
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
        self._rejection_lock = threading.Lock()
        self._rejections = 0

    def record_rejection(self) -> None:
        with self._rejection_lock:
            if self._rejections < 9_223_372_036_854_775_807:
                self._rejections += 1

    def rejection_count(self) -> int:
        with self._rejection_lock:
            return self._rejections

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


def _execution_request_id(value: str | None, name: str) -> str:
    value = _request_id(value, name)
    try:
        secret_free_identity(value, 128)
    except BrokerError as exc:
        raise HTTPException(400, f"valid {name} header required") from exc
    return value


def _command_key(value: str | None) -> str:
    return canonical_digest({"contract": "adaptive-factory.command/v1", "idempotency_key": _request_id(value, "Idempotency-Key")})


def _execution_command_key(value: str | None) -> str:
    return canonical_digest(
        {
            "contract": "adaptive-factory.command/v1",
            "idempotency_key": _execution_request_id(value, "Idempotency-Key"),
        }
    )


def _closed(payload: Any, expected: set[str], *, optional: set[str] | None = None) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise HTTPException(422, "closed object required")
    optional = optional or set()
    if set(payload) - expected - optional or expected - set(payload):
        raise HTTPException(422, "closed command body required")
    return payload


def _text(value: Any, name: str, *, maximum: int = 128, identifier: bool = False) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise HTTPException(422, f"invalid {name}")
    if any(ord(character) < 32 for character in value) or (identifier and not TEXT_ID.fullmatch(value)):
        raise HTTPException(422, f"invalid {name}")
    return value


def _uuid(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise HTTPException(422, f"invalid {name}")
    try:
        parsed = str(uuid.UUID(value))
    except ValueError as exc:
        raise HTTPException(422, f"invalid {name}") from exc
    if parsed != value:
        raise HTTPException(422, f"invalid {name}")
    return value


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise HTTPException(422, f"invalid {name}")
    return value


def _digest(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not HEX64_TEXT.fullmatch(value):
        raise HTTPException(422, f"invalid {name}")
    return value


def _repositories(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or len(value) > 100:
        raise HTTPException(422, "invalid repositories")
    repositories = tuple(_text(item, "repository", identifier=True) for item in value)
    if len(set(repositories)) != len(repositories):
        raise HTTPException(422, "invalid repositories")
    return repositories


def _grant(payload: Mapping[str, Any]) -> LeaseGrant:
    expected = {"task_id", "run_id", "owner", "role", "fence", "expires_at", "packet_digest"}
    payload = _closed(payload, expected)
    try:
        expires_raw = _text(payload["expires_at"], "expires_at", maximum=64)
        expires = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
        if expires.tzinfo is None:
            raise ValueError("timezone required")
        return LeaseGrant(
            _uuid(payload["task_id"], "task_id"),
            _uuid(payload["run_id"], "run_id"),
            _text(payload["owner"], "owner", identifier=True),
            RunRole(payload["role"]),
            _integer(payload["fence"], "fence", 1, 9_223_372_036_854_775_807),
            expires,
            _digest(payload["packet_digest"], "packet_digest"),
        )
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(422, "invalid lease grant") from exc


def _error_response(
    error: str,
    code: str,
    detail: str,
    status_code: int,
    *,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        {"error": error, "code": code, "detail": detail},
        status_code=status_code,
        headers=dict(headers or {}),
    )


def _http_error(status_code: int, detail: Any) -> tuple[str, str, str]:
    safe_detail = detail if isinstance(detail, str) and len(detail) <= 160 else "request rejected"
    if status_code == 401:
        return "unauthorized", "authentication", safe_detail
    if status_code == 403:
        return "unauthorized", "authorization", safe_detail
    if status_code == 404:
        return "not_found", "not_found", safe_detail
    if status_code == 409:
        return "conflict", "conflict", safe_detail
    if status_code == 413:
        return "invalid", "body_too_large", safe_detail
    if status_code == 503:
        return "unavailable", "unavailable", safe_detail
    return "invalid", "invalid_request", safe_detail


def _landing_media(content_type: str | None) -> tuple[str, int]:
    if not isinstance(content_type, str):
        raise HTTPException(415, "landing media type required")
    media_type = content_type.split(";", 1)[0].strip().lower()
    for kind, allowed in MEDIA_TYPES.items():
        if media_type in allowed:
            return media_type, MAX_INPUT_BYTES[kind]
    raise HTTPException(415, "landing media type unsupported")


def _landing_content_length(value: str | None, maximum: int) -> None:
    if value is None:
        return
    try:
        declared = int(value)
    except ValueError as exc:
        raise HTTPException(400, "invalid content length") from exc
    if declared < 0:
        raise HTTPException(400, "invalid content length")
    if declared > maximum:
        raise HTTPException(413, "request body too large")


async def _stream_landing_body(
    request: Request,
    submit: Callable[[Iterable[bytes]], Any],
) -> Any:
    chunks: queue.Queue[bytes | object] = queue.Queue(maxsize=2)
    sentinel = object()

    def values() -> Iterable[bytes]:
        while True:
            value = chunks.get()
            if value is sentinel:
                return
            if not isinstance(value, bytes):
                raise LandingServiceError("stream", 500, "landing input stream failed")
            yield value

    worker = asyncio.create_task(asyncio.to_thread(submit, values()))

    async def offer(value: bytes | object) -> bool:
        while not worker.done():
            try:
                chunks.put_nowait(value)
                return True
            except queue.Full:
                await asyncio.sleep(0)
        return False

    terminal_sent = False
    try:
        async for chunk in request.stream():
            for offset in range(0, len(chunk), 65_536):
                if not await offer(bytes(chunk[offset : offset + 65_536])):
                    return await worker
        terminal_sent = await offer(sentinel)
        return await worker
    except BaseException:
        if not terminal_sent and not worker.done():
            await offer(sentinel)
        if not worker.done():
            with suppress(Exception):
                await worker
        raise


def create_app(
    service,
    authenticator: Authenticator,
    *,
    execution_enabled: bool = True,
    landing_service: LandingApplicationService | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Adaptive Factory Local Control API",
        version="1.0.0",
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, error: StarletteHTTPException):
        category, code, detail = _http_error(error.status_code, error.detail)
        return _error_response(
            category,
            code,
            detail,
            error.status_code,
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error(_request: Request, _error: RequestValidationError):
        return _error_response(
            "invalid", "invalid_request", "request validation failed", 422
        )

    @app.exception_handler(ContractError)
    async def contract_error(_request: Request, error: ContractError):
        return _error_response(
            "invalid", error.code, "contract validation failed", 422
        )

    @app.exception_handler(ExecutionContractError)
    async def execution_contract_error(_request: Request, error: ExecutionContractError):
        return JSONResponse({"error": "invalid", "code": error.code}, status_code=422)

    @app.exception_handler(BrokerError)
    async def broker_error(_request: Request, error: BrokerError):
        return JSONResponse({"error": "invalid", "code": error.code}, status_code=422)

    @app.exception_handler(LandingServiceError)
    async def landing_service_error(_request: Request, error: LandingServiceError):
        category, _, _ = _http_error(error.status_code, error.detail)
        return _error_response(
            category,
            error.code,
            error.detail,
            error.status_code,
        )

    @app.exception_handler(AuthorizationError)
    async def authorization_error(_request: Request, _error: AuthorizationError):
        return _error_response(
            "unauthorized", "authorization", "authorization denied", 403
        )

    @app.exception_handler(AuthorityError)
    async def authority_error(_request: Request, _error: AuthorityError):
        return _error_response(
            "unauthorized", "m0_authority", "M0 authority rejected", 403
        )

    @app.exception_handler(FenceError)
    async def fence_error(_request: Request, _error: FenceError):
        return _error_response(
            "conflict", "stale_fence", "lease fence is stale", 409
        )

    @app.exception_handler(BudgetError)
    async def budget_error(_request: Request, _error: BudgetError):
        return _error_response(
            "stopped", "budget", "bounded budget rejected the command", 409
        )

    @app.exception_handler(TransitionError)
    async def transition_error(_request: Request, _error: TransitionError):
        return _error_response(
            "conflict", "invalid_transition", "task transition is not allowed", 409
        )

    @app.exception_handler(StoreUnavailable)
    async def store_unavailable(_request: Request, _error: StoreUnavailable):
        return _error_response(
            "unavailable", "database", "database unavailable", 503
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error(_request: Request, _error: IntegrityError):
        return JSONResponse(
            {"error": "internal", "code": "internal_integrity"}, status_code=500
        )

    @app.exception_handler(SnapshotBrokerIntegrityError)
    async def snapshot_integrity_error(
        _request: Request, _error: SnapshotBrokerIntegrityError
    ):
        return JSONResponse(
            {"error": "internal", "code": "internal_integrity"}, status_code=500
        )

    @app.exception_handler(SnapshotBrokerUnavailable)
    async def snapshot_unavailable(
        _request: Request, _error: SnapshotBrokerUnavailable
    ):
        return JSONResponse(
            {"error": "unavailable", "code": "workspace_snapshot"},
            status_code=503,
        )

    @app.exception_handler(StoreError)
    async def store_error(_request: Request, _error: StoreError):
        return _error_response(
            "conflict", "store_conflict", "stored command conflicts with request", 409
        )

    @app.exception_handler(MetricsUnavailable)
    async def metrics_unavailable(_request: Request, _error: MetricsUnavailable):
        return _error_response(
            "unavailable", "metrics", "metrics snapshot unavailable", 503
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, _error: Exception):
        correlation = getattr(request.state, "correlation_id", None)
        if not isinstance(correlation, str) or not HEADER_ID.fullmatch(correlation):
            correlation = str(uuid.uuid4())
        return _error_response(
            "unavailable",
            "internal",
            "internal server error",
            500,
            headers={"X-Correlation-ID": correlation},
        )

    @app.middleware("http")
    async def bound_body(request: Request, call_next):
        supplied_correlation = request.headers.get("x-correlation-id")
        correlation = (
            supplied_correlation
            if supplied_correlation and HEADER_ID.fullmatch(supplied_correlation)
            else str(uuid.uuid4())
        )
        request.state.correlation_id = correlation

        landing_stream = (
            request.method == "POST" and request.url.path == LANDING_SUBMIT_PATH
        )
        if request.method in BODY_BEARING_METHODS and not landing_stream:
            length = request.headers.get("content-length")
            if length:
                try:
                    declared = int(length)
                except ValueError:
                    response = _error_response(
                        "invalid", "invalid_request", "invalid content length", 400
                    )
                    response.headers["X-Correlation-ID"] = correlation
                    return response
                if declared < 0:
                    response = _error_response(
                        "invalid", "invalid_request", "invalid content length", 400
                    )
                    response.headers["X-Correlation-ID"] = correlation
                    return response
                if declared > MAX_BODY_BYTES:
                    response = _error_response(
                        "invalid", "body_too_large", "request body too large", 413
                    )
                    response.headers["X-Correlation-ID"] = correlation
                    return response
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > MAX_BODY_BYTES:
                    response = _error_response(
                        "invalid", "body_too_large", "request body too large", 413
                    )
                    response.headers["X-Correlation-ID"] = correlation
                    return response
                body.extend(chunk)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation
        if response.status_code in {401, 403}:
            authenticator.record_rejection()
        return response

    @app.get("/health/live", tags=["health"])
    def live():
        return {"status": "live"}

    @app.get("/health/ready", tags=["health"])
    def ready():
        result = service.readiness()
        if result.get("status") != "ready":
            raise HTTPException(503, "schema not ready")
        return result

    @app.get("/metrics", tags=["operator"])
    def metrics(authorization: str | None = Header(None)):
        actor = authenticator.authenticate(authorization, "factory:reconcile")
        result = dict(service.metrics(actor=actor))
        family = dict(result["factory_capacity_budget_kill_and_reconcile_outcomes_total"])
        family["auth_rejected"] = authenticator.rejection_count()
        result["factory_capacity_budget_kill_and_reconcile_outcomes_total"] = family
        return result

    @app.post(
        LANDING_SUBMIT_PATH,
        tags=["landing"],
        operation_id="submitLandingInput",
        status_code=202,
    )
    async def submit_landing_input(
        request: Request,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
        x_repository_id: str | None = Header(None),
        x_exact_base_sha: str | None = Header(None),
        x_exact_base_tree: str | None = Header(None),
        content_type: str | None = Header(None),
        content_length: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "landing:submit")
        job_id = _request_id(idempotency_key, "Idempotency-Key")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        repository_id = _text(
            x_repository_id, "X-Repository-ID", maximum=128, identifier=True
        )
        exact_base_sha = _text(
            x_exact_base_sha, "X-Exact-Base-SHA", maximum=40
        )
        exact_base_tree = _text(
            x_exact_base_tree, "X-Exact-Base-Tree", maximum=40
        )
        media_type, maximum = _landing_media(content_type)
        _landing_content_length(content_length, maximum)
        if landing_service is None:
            raise LandingServiceError(
                "provider_unavailable", 503, "landing composition unavailable"
            )

        result = await _stream_landing_body(
            request,
            lambda chunks: landing_service.submit(
                job_id=job_id,
                repository_id=repository_id,
                exact_base_sha=exact_base_sha,
                exact_base_tree=exact_base_tree,
                media_type=media_type,
                chunks=chunks,
                actor=actor,
            ),
        )
        return JSONResponse(
            result.job.job_view(),
            status_code=202,
            headers={"X-Correlation-ID": correlation},
        )

    @app.get(
        "/v1/landing-jobs/{job_id}",
        tags=["landing"],
        operation_id="getLandingJob",
    )
    def get_landing_job(
        job_id: str,
        authorization: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
        x_repository_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "landing:read")
        job_id = _request_id(job_id, "job_id")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        repository_id = _text(
            x_repository_id, "X-Repository-ID", maximum=128, identifier=True
        )
        if landing_service is None:
            raise LandingServiceError(
                "provider_unavailable", 503, "landing composition unavailable"
            )
        record = landing_service.get(job_id, repository_id=repository_id, actor=actor)
        return JSONResponse(
            record.job_view(), headers={"X-Correlation-ID": correlation}
        )

    @app.post(
        "/v1/landing-jobs/{job_id}/cancel",
        tags=["landing"],
        operation_id="cancelLandingJob",
    )
    def cancel_landing_job(
        job_id: str,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
        x_repository_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "landing:cancel")
        job_id = _request_id(job_id, "job_id")
        key = _request_id(idempotency_key, "Idempotency-Key")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        repository_id = _text(
            x_repository_id, "X-Repository-ID", maximum=128, identifier=True
        )
        if landing_service is None:
            raise LandingServiceError(
                "provider_unavailable", 503, "landing composition unavailable"
            )
        record = landing_service.cancel(
            job_id,
            repository_id=repository_id,
            idempotency_key=key,
            actor=actor,
        )
        return JSONResponse(
            record.job_view(), headers={"X-Correlation-ID": correlation}
        )

    @app.get(
        "/v1/landing-jobs/{job_id}/result",
        tags=["landing"],
        operation_id="getLandingResult",
    )
    def get_landing_result(
        job_id: str,
        authorization: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
        x_repository_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "landing:read")
        job_id = _request_id(job_id, "job_id")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        repository_id = _text(
            x_repository_id, "X-Repository-ID", maximum=128, identifier=True
        )
        if landing_service is None:
            raise LandingServiceError(
                "provider_unavailable", 503, "landing composition unavailable"
            )
        record = landing_service.result(
            job_id, repository_id=repository_id, actor=actor
        )
        return JSONResponse(
            record.result_view(), headers={"X-Correlation-ID": correlation}
        )

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
        result = service.intake(
            payload,
            actor=actor,
            now=datetime.now(timezone.utc),
            correlation_id=correlation,
        )
        return JSONResponse(
            _json({"task": result.task, "created": result.created}),
            status_code=201 if result.created else 200,
            headers={"X-Correlation-ID": correlation},
        )

    @app.get("/v1/tasks/{task_id}", tags=["tasks"])
    def show(task_id: str, authorization: str | None = Header(None)):
        actor = authenticator.authenticate(authorization, "task:read")
        task_id = _uuid(task_id, "task_id")
        try:
            task = service.get_task(task_id, actor=actor)
        except KeyError:
            raise HTTPException(404, "task not found")
        return JSONResponse(_json(task))

    @app.get("/v1/tasks", tags=["tasks"])
    def list_tasks(
        repository_id: str,
        limit: int = 100,
        cursor: str | None = None,
        authorization: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:list")
        repository_id = _text(repository_id, "repository_id", identifier=True)
        limit = _integer(limit, "limit", 1, 100)
        cursor = _uuid(cursor, "cursor") if cursor is not None else None
        return JSONResponse(
            _json({"items": service.list_tasks(repository_id=repository_id, limit=limit, cursor=cursor, actor=actor)}),
        )

    @app.get("/v1/tasks/{task_id}/runs", tags=["tasks"])
    def list_task_runs(
        task_id: str,
        limit: int = 100,
        cursor: str | None = None,
        authorization: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:read")
        task_id = _uuid(task_id, "task_id")
        limit = _integer(limit, "limit", 1, 100)
        cursor = _uuid(cursor, "cursor") if cursor is not None else None
        try:
            result = service.list_task_runs(
                task_id, limit=limit, cursor=cursor, actor=actor
            )
        except KeyError as exc:
            raise HTTPException(404, "task not found") from exc
        except ValueError as exc:
            raise HTTPException(422, "invalid cursor") from exc
        return JSONResponse(_json(result))

    @app.get("/v1/tasks/{task_id}/events", tags=["tasks"])
    def list_task_events(
        task_id: str,
        limit: int = 100,
        cursor: int | None = None,
        authorization: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:read")
        task_id = _uuid(task_id, "task_id")
        limit = _integer(limit, "limit", 1, 100)
        cursor = _integer(cursor, "cursor", 0, 9_223_372_036_854_775_807) if cursor is not None else None
        try:
            result = service.list_task_events(
                task_id, limit=limit, cursor=cursor, actor=actor
            )
        except KeyError as exc:
            raise HTTPException(404, "task not found") from exc
        return JSONResponse(_json(result))

    @app.post("/v1/tasks/{task_id}/cancel", tags=["tasks"])
    def cancel(
        task_id: str,
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:cancel")
        _request_id(idempotency_key, "Idempotency-Key")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        payload = _closed(payload, {"reason"})
        task_id = _uuid(task_id, "task_id")
        reason = _text(payload["reason"], "reason", maximum=128)
        try:
            task = service.cancel(
                task_id, reason=reason, idempotency_key=_command_key(idempotency_key), actor=actor,
                now=datetime.now(timezone.utc), correlation_id=correlation
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
        key = _command_key(idempotency_key)
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        payload = _closed(payload, {"role", "repositories", "lease_seconds"})
        try:
            role = RunRole(payload["role"])
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, "invalid role") from exc
        grant = service.claim(
            owner=actor.actor_id,
            role=role,
            repositories=_repositories(payload["repositories"]),
            lease_seconds=_integer(payload["lease_seconds"], "lease_seconds", 30, 300),
            actor=actor,
            now=datetime.now(timezone.utc),
            idempotency_key=key,
            correlation_id=correlation,
        )
        return JSONResponse(_json({"grant": grant}), headers={"X-Correlation-ID": correlation})

    @app.post("/v2/execution/claims", tags=["execution"])
    @app.post("/v1/execution/claims", tags=["execution"])
    def claim_execution(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:execute")
        key = _execution_command_key(idempotency_key)
        correlation = _execution_request_id(x_correlation_id, "X-Correlation-ID")
        fields = {
            "role",
            "repositories",
            "lease_seconds",
            "provider",
            "capability_policy",
            "plan",
            "workspace_handle",
            "prompt_template_digest",
            "role_definition_digest",
            "tool_policy_digest",
            "output_schema_digest",
        }
        payload = _closed(payload, fields)
        try:
            role = RunRole(payload["role"])
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, "invalid role") from exc
        selection = {name: payload[name] for name in fields - {"role", "repositories", "lease_seconds"}}
        grant = service.claim_execution(
            owner=actor.actor_id,
            role=role,
            repositories=_repositories(payload["repositories"]),
            lease_seconds=_integer(payload["lease_seconds"], "lease_seconds", 30, 300),
            selection=selection,
            actor=actor,
            now=datetime.now(timezone.utc),
            idempotency_key=key,
            correlation_id=correlation,
        )
        return JSONResponse(_json({"grant": grant}), headers={"X-Correlation-ID": correlation})

    @app.post("/v2/execution/stages", tags=["execution"])
    @app.post("/v1/execution/stages", tags=["execution"])
    def advance_execution(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:execute")
        key = _execution_command_key(idempotency_key)
        correlation = _execution_request_id(x_correlation_id, "X-Correlation-ID")
        payload = _closed(payload, {"grant", "packet_digest", "stage"})
        try:
            stage = ExecutionStage(payload["stage"])
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, "invalid execution stage") from exc
        if stage is ExecutionStage.ORPHANED:
            raise HTTPException(403, "orphaned is reconciliation-only")
        result = service.advance_execution(
            _grant(payload["grant"]),
            packet_digest=_digest(payload["packet_digest"], "packet_digest"),
            stage=stage,
            actor=actor,
            idempotency_key=key,
            correlation_id=correlation,
        )
        return JSONResponse(_json({"stage": result}), headers={"X-Correlation-ID": correlation})

    def execution_proposal(
        payload: Mapping[str, Any],
        *,
        actor: Actor,
        event_type: str,
        proposal_payload: Mapping[str, Any],
        idempotency_key: str | None,
        correlation_id: str | None,
    ):
        key = _execution_command_key(idempotency_key)
        correlation = _execution_request_id(correlation_id, "X-Correlation-ID")
        proposal = service.commit_execution_proposal(
            _grant(payload["grant"]),
            packet_digest=_digest(payload["packet_digest"], "packet_digest"),
            sequence=_integer(payload["sequence"], "sequence", 1, 100_000),
            event_type=event_type,
            payload=proposal_payload,
            actor=actor,
            idempotency_key=key,
            correlation_id=correlation,
        )
        return JSONResponse(_json({"proposal": proposal}), headers={"X-Correlation-ID": correlation})

    @app.post("/v2/execution/notes", tags=["execution"])
    @app.post("/v1/execution/notes", tags=["execution"])
    def execution_note(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:execute")
        payload = _closed(payload, {"grant", "packet_digest", "sequence", "note_type", "body", "evidence"})
        return execution_proposal(
            payload, actor=actor, event_type="note.proposed",
            proposal_payload={name: payload[name] for name in ("note_type", "body", "evidence")},
            idempotency_key=idempotency_key, correlation_id=x_correlation_id,
        )

    @app.post("/v2/execution/artifacts", tags=["execution"])
    @app.post("/v1/execution/artifacts", tags=["execution"])
    def execution_artifact(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:execute")
        fields = {"grant", "packet_digest", "sequence", "artifact_class", "path", "sha256", "size_bytes", "media_type"}
        payload = _closed(payload, fields)
        return execution_proposal(
            payload, actor=actor, event_type="artifact.proposed",
            proposal_payload={name: payload[name] for name in fields - {"grant", "packet_digest", "sequence"}},
            idempotency_key=idempotency_key, correlation_id=x_correlation_id,
        )

    @app.post("/v2/execution/usage", tags=["execution"])
    @app.post("/v1/execution/usage", tags=["execution"])
    def execution_usage(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:execute")
        fields = {
            "grant", "packet_digest", "sequence", "provider_call_id", "price_table_digest",
            "input_tokens", "output_tokens", "reasoning_tokens", "cost_usd_micros", "output_bytes",
        }
        payload = _closed(payload, fields)
        return execution_proposal(
            payload, actor=actor, event_type="usage.reported",
            proposal_payload={name: payload[name] for name in fields - {"grant", "packet_digest", "sequence"}},
            idempotency_key=idempotency_key, correlation_id=x_correlation_id,
        )

    @app.post("/v2/execution/terminal", tags=["execution"])
    @app.post("/v1/execution/terminal", tags=["execution"])
    def execution_terminal(
        payload: dict,
        request: Request,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:execute")
        common = {"grant", "packet_digest", "sequence", "terminal_type"}
        payload = _closed(payload, common, optional={"summary", "failure_class", "diagnostic", "reason"})
        terminal_type = payload["terminal_type"]
        terminal_fields = {
            "run.completed": {"summary"},
            "run.failed": {"failure_class", "diagnostic"},
            "run.needs_human": {"reason", "diagnostic"},
        }
        expected = terminal_fields.get(terminal_type)
        if expected is None or set(payload) != common | expected:
            raise HTTPException(422, "invalid terminal proposal")
        key = _execution_command_key(idempotency_key)
        correlation = _execution_request_id(x_correlation_id, "X-Correlation-ID")
        completion = service.commit_terminal_and_finalize(
            _grant(payload["grant"]),
            packet_digest=_digest(payload["packet_digest"], "packet_digest"),
            sequence=_integer(payload["sequence"], "sequence", 1, 100_000),
            event_type=terminal_type,
            payload={name: payload[name] for name in expected},
            actor=actor,
            idempotency_key=key,
            correlation_id=correlation,
        )
        response = {"proposal": completion.proposal}
        matched_route = request.scope.get("route")
        if getattr(matched_route, "path", None) == "/v2/execution/terminal":
            response["result"] = completion.result
        return JSONResponse(_json(response), headers={"X-Correlation-ID": correlation})

    @app.post("/v1/heartbeats", tags=["worker"])
    def heartbeat(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:heartbeat")
        key = _command_key(idempotency_key)
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        return JSONResponse(
            _json(service.heartbeat(_grant(payload), actor=actor, now=datetime.now(timezone.utc), idempotency_key=key, correlation_id=correlation)),
            headers={"X-Correlation-ID": correlation},
        )

    @app.post("/v1/transitions", tags=["worker"])
    def transition_phase(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:release")
        key = _command_key(idempotency_key)
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        payload = _closed(payload, {"grant", "target"})
        try:
            target = TaskStatus(payload["target"])
        except (TypeError, ValueError) as exc:
            raise HTTPException(422, "invalid phase target") from exc
        if target not in {
            TaskStatus.ANALYZING,
            TaskStatus.IMPLEMENTING,
            TaskStatus.VERIFYING,
            TaskStatus.REVIEWING,
        }:
            raise HTTPException(422, "invalid phase target")
        status = service.transition_phase(
            _grant(payload["grant"]),
            target=target,
            actor=actor,
            now=datetime.now(timezone.utc),
            idempotency_key=key,
            correlation_id=correlation,
        )
        return JSONResponse(
            _json({"status": status}), headers={"X-Correlation-ID": correlation}
        )

    @app.post("/v1/proposals", tags=["worker"])
    def proposal(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:release")
        key = _command_key(idempotency_key)
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        payload = _closed(payload, {"grant", "outcome"})
        outcome = payload["outcome"]
        if outcome != "completed":
            from .models import FailureClass
            try:
                outcome = FailureClass(outcome)
            except (ValueError, TypeError) as exc:
                raise HTTPException(422, "invalid outcome") from exc
        status = service.release(
            _grant(payload["grant"]), outcome=outcome, actor=actor, now=datetime.now(timezone.utc),
            idempotency_key=key, correlation_id=correlation
        )
        return JSONResponse(_json({"status": status}), headers={"X-Correlation-ID": correlation})

    @app.post("/v1/budget-reservations", tags=["worker"])
    def reserve_budget(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:budget")
        key = _command_key(idempotency_key)
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        payload = _closed(payload, {"grant", "cost_usd_micros", "token_units", "wall_seconds", "reason_digest"})
        reservation_id = service.reserve_budget(
            _grant(payload["grant"]),
            cost_usd_micros=_integer(payload["cost_usd_micros"], "cost_usd_micros", 0, 25_000_000),
            token_units=_integer(payload["token_units"], "token_units", 0, 2_000_000),
            wall_seconds=_integer(payload["wall_seconds"], "wall_seconds", 0, 14_400),
            reason_digest=_digest(payload["reason_digest"], "reason_digest"),
            idempotency_key=key,
            actor=actor,
            correlation_id=correlation,
        )
        return JSONResponse({"reservation_id": reservation_id}, headers={"X-Correlation-ID": correlation})

    @app.post("/v1/usage-observations", tags=["worker"])
    def observe_usage(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "task:budget")
        key = _command_key(idempotency_key)
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        payload = _closed(payload, {"grant", "provider_call_id", "price_table_digest", "cost_usd_micros", "token_units", "output_bytes"})
        result = service.observe_usage(
            _grant(payload["grant"]),
            provider_call_id=_text(payload["provider_call_id"], "provider_call_id", maximum=128),
            price_table_digest=_digest(payload["price_table_digest"], "price_table_digest", nullable=True),
            cost_usd_micros=_integer(payload["cost_usd_micros"], "cost_usd_micros", 0, 25_000_000),
            token_units=_integer(payload["token_units"], "token_units", 0, 2_000_000),
            output_bytes=_integer(payload["output_bytes"], "output_bytes", 0, 10_000_000),
            actor=actor,
            idempotency_key=key,
            correlation_id=correlation,
        )
        return JSONResponse(_json(result), headers={"X-Correlation-ID": correlation})

    @app.post("/v1/kill-switches", tags=["operator"])
    def kill(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "factory:kill")
        key = _command_key(idempotency_key)
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        payload = _closed(payload, {"scope_key", "enabled", "reason"})
        scope_key = _text(payload["scope_key"], "scope_key", maximum=139)
        if scope_key != "global":
            if not scope_key.startswith("repository:"):
                raise HTTPException(422, "invalid scope_key")
            _text(
                scope_key.removeprefix("repository:"),
                "repository scope",
                identifier=True,
            )
        if type(payload["enabled"]) is not bool:
            raise HTTPException(422, "invalid enabled")
        enabled = service.set_kill(
            scope_key=scope_key,
            enabled=payload["enabled"],
            reason=_text(payload["reason"], "reason", maximum=128),
            idempotency_key=key,
            actor=actor,
            now=datetime.now(timezone.utc),
            correlation_id=correlation,
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
        key = _command_key(idempotency_key)
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        payload = _closed(payload, set(), optional={"limit", "cursor"})
        limit = _integer(payload.get("limit", 100), "limit", 1, 100)
        cursor = payload.get("cursor")
        cursor = _uuid(cursor, "cursor") if cursor is not None else None
        result = service.reconcile(
            actor=actor,
            now=datetime.now(timezone.utc),
            limit=limit,
            cursor=cursor,
            idempotency_key=key,
            correlation_id=correlation,
        )
        return JSONResponse(_json(result), headers={"X-Correlation-ID": correlation})

    def semantic_response(record):
        return {
            "envelope_digest": record.envelope_digest,
            "binding_digest": record.binding.digest,
            "validation_inputs_digest": record.validation_inputs.digest,
            "subject_digest": record.subject.digest,
            "subject": record.subject.to_dict(),
        }

    @app.post("/v1/semantic/subjects", tags=["semantic"])
    def publish_semantic_subject(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "semantic:publish")
        key = _command_key(idempotency_key)
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        payload = _closed(
            payload,
            {"task_id", "workspace_result_digest", "validation_inputs"},
        )
        task_id = _uuid(payload["task_id"], "task_id")
        result_digest = _digest(
            payload["workspace_result_digest"], "workspace_result_digest"
        )
        if not isinstance(payload["validation_inputs"], Mapping):
            raise HTTPException(422, "invalid validation_inputs")
        try:
            record = service.publish_semantic_subject(
                task_id,
                result_digest,
                payload["validation_inputs"],
                actor=actor,
                idempotency_key=key,
                correlation_id=correlation,
            )
        except KeyError:
            raise HTTPException(404, "workspace result not found")
        return JSONResponse(
            _json(semantic_response(record)),
            headers={"X-Correlation-ID": correlation},
        )

    @app.get("/v1/semantic/subjects/{subject_digest}", tags=["semantic"])
    def read_semantic_subject(
        subject_digest: str,
        task_id: str,
        authorization: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "semantic:read")
        correlation = _request_id(
            x_correlation_id or "generated-semantic-read", "X-Correlation-ID"
        )
        task_id = _uuid(task_id, "task_id")
        subject_digest = _digest(subject_digest, "subject_digest")
        try:
            record = service.get_semantic_subject(
                task_id, subject_digest, actor=actor
            )
        except KeyError:
            raise HTTPException(404, "semantic subject not found")
        return JSONResponse(
            _json(semantic_response(record)),
            headers={"X-Correlation-ID": correlation},
        )

    @app.post(
        "/v1/semantic/subjects/{subject_digest}/assignments", tags=["semantic"]
    )
    def create_semantic_assignment(
        subject_digest: str,
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "semantic:assign")
        key = _command_key(idempotency_key)
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        subject_digest = _digest(subject_digest, "subject_digest")
        payload = _closed(payload, {"task_id", "validator"})
        task_id = _uuid(payload["task_id"], "task_id")
        if not isinstance(payload["validator"], Mapping):
            raise HTTPException(422, "invalid validator")
        try:
            result = service.create_semantic_assignment(
                task_id,
                subject_digest,
                payload["validator"],
                actor=actor,
                idempotency_key=key,
                correlation_id=correlation,
            )
        except KeyError:
            raise HTTPException(404, "semantic subject not found")
        return JSONResponse(_json(result), headers={"X-Correlation-ID": correlation})

    @app.post(
        "/v1/semantic/assignments/{assignment_digest}/evidence", tags=["semantic"]
    )
    def submit_semantic_evidence(
        assignment_digest: str,
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "semantic:validate")
        key = _command_key(idempotency_key)
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        assignment_digest = _digest(assignment_digest, "assignment_digest")
        payload = _closed(
            payload, {"task_id", "subject_digest", "findings", "coverage"}
        )
        task_id = _uuid(payload["task_id"], "task_id")
        subject_digest = _digest(payload["subject_digest"], "subject_digest")
        if (
            not isinstance(payload["findings"], list)
            or len(payload["findings"]) > 256
            or any(not isinstance(value, Mapping) for value in payload["findings"])
            or not isinstance(payload["coverage"], Mapping)
        ):
            raise HTTPException(422, "invalid semantic evidence")
        result = service.submit_semantic_evidence(
            task_id,
            subject_digest,
            assignment_digest,
            payload["findings"],
            payload["coverage"],
            actor=actor,
            idempotency_key=key,
            correlation_id=correlation,
        )
        return JSONResponse(_json(result), headers={"X-Correlation-ID": correlation})

    @app.post(
        "/v1/semantic/subjects/{subject_digest}/adjudications", tags=["semantic"]
    )
    def adjudicate_semantic_subject(
        subject_digest: str,
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "semantic:adjudicate")
        key = _command_key(idempotency_key)
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        subject_digest = _digest(subject_digest, "subject_digest")
        payload = _closed(payload, {"task_id"})
        task_id = _uuid(payload["task_id"], "task_id")
        try:
            result = service.adjudicate_semantic_subject(
                task_id,
                subject_digest,
                actor=actor,
                idempotency_key=key,
                correlation_id=correlation,
            )
        except KeyError:
            raise HTTPException(404, "semantic subject not found")
        return JSONResponse(_json(result), headers={"X-Correlation-ID": correlation})

    @app.get(
        "/v1/semantic/subjects/{subject_digest}/verdict", tags=["semantic"]
    )
    def read_semantic_verdict(
        subject_digest: str,
        task_id: str,
        authorization: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        actor = authenticator.authenticate(authorization, "semantic:read")
        correlation = _request_id(
            x_correlation_id or "generated-semantic-verdict-read",
            "X-Correlation-ID",
        )
        task_id = _uuid(task_id, "task_id")
        subject_digest = _digest(subject_digest, "subject_digest")
        try:
            result = service.get_semantic_verdict(
                task_id, subject_digest, actor=actor
            )
        except KeyError:
            raise HTTPException(404, "semantic verdict not found")
        return JSONResponse(_json(result), headers={"X-Correlation-ID": correlation})

    if not execution_enabled:
        execution_paths = {
            "/v1/execution/claims",
            "/v1/execution/stages",
            "/v1/execution/notes",
            "/v1/execution/artifacts",
            "/v1/execution/usage",
            "/v1/execution/terminal",
            "/v2/execution/claims",
            "/v2/execution/stages",
            "/v2/execution/notes",
            "/v2/execution/artifacts",
            "/v2/execution/usage",
            "/v2/execution/terminal",
        }
        app.router.routes = [
            route
            for route in app.router.routes
            if getattr(route, "path", None) not in execution_paths
        ]
    return app
