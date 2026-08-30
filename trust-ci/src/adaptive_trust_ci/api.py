from __future__ import annotations

import hmac
import json
import os
import threading
import time
import uuid
from collections import deque
from datetime import timedelta
from typing import Any, Callable

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from .metrics import collect_metrics, render_prometheus
from .models import (
    ApprovalEnvelope,
    PromotionEnvelope,
    PromotionEvent,
    PromotionExpectedBinding,
    parse_datetime,
    utc_now,
    require_uuid_v1_5,
)
from .policy import Policy, PolicyError
from .promotion_consumer import (
    PromotionAlreadyConsumed,
    PromotionConsumer,
    PromotionDenied,
    PromotionTarget,
    PromotionUnavailable,
)
from .settings import ApiSettings
from .signing import ApprovalError, PromotionError, TrustStore, verify_approval, verify_promotion
from .store import (
    IdempotencyConflict,
    PostgresStore,
    PromotionReplay,
    ProvenanceMismatch,
    ReplayError,
    Store,
)
from .webhooks import (
    WebhookError,
    WebhookForbidden,
    WebhookUnavailable,
    ingest_merged_pull_request,
    parse_pull_request_event,
)


def create_app(
    settings: ApiSettings,
    *,
    store: Store | None = None,
    policy: Policy | None = None,
    trust_store: TrustStore | None = None,
    merge_fact_recorder: Callable | None = None,
    protected_ref: str | None = None,
    promotion_consume_store: Store | None = None,
) -> FastAPI:
    protected_ref = protected_ref or settings.protected_ref
    active_policy = policy or _load_policy_snapshot(settings.common.policy_path)

    def current_policy() -> Policy:
        # The injectable startup policy supports isolated tests and non-promotion
        # routes; it never substitutes for the mounted current policy at this
        # production-authorization boundary.
        return _load_policy_snapshot(settings.common.policy_path)
    active_store = store or PostgresStore(settings.common.database_url)
    durable_merge_fact_recorder = merge_fact_recorder or active_store.record_merge_fact
    if trust_store is None:
        TrustStore.load(settings.trust_store_path)

        def current_trust_store() -> TrustStore:
            return TrustStore.load(settings.trust_store_path)
    else:
        fixed_trust_store = trust_store

        def current_trust_store() -> TrustStore:
            return fixed_trust_store

    authorize_read = _bearer_authorizer(settings.read_token)
    promotion_limiter = _PromotionRateLimiter(settings.promotion_rate_limit_per_minute)
    consume_limiter = _PromotionRateLimiter(
        settings.promotion_consume_rate_limit_per_minute
    )
    consume_store = promotion_consume_store
    if consume_store is None and store is not None:
        consume_store = active_store
    if consume_store is None and settings.deployer_database_url:
        consume_store = PostgresStore(settings.deployer_database_url)
    promotion_consumer = (
        PromotionConsumer(
            consume_store,
            manifest_path=settings.promotion_manifest_path,
            artifact_path=settings.promotion_artifact_path,
            expected_manifest_sha256=settings.promotion_manifest_sha256,
            stopped=lambda: settings.common.stopped,
        )
        if consume_store is not None
        and settings.promotion_manifest_path is not None
        and settings.promotion_artifact_path is not None
        else None
    )

    app = FastAPI(
        title='Adaptive Trust CI',
        version='2.1.0',
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = settings
    app.state.policy = active_policy
    app.state.store = active_store
    app.state.promotion_consume_store = consume_store
    app.state.promotion_outcomes = {}
    app.state.promotion_audit_failures = 0

    @app.get('/health/live')
    def live() -> dict[str, Any]:
        return {'status': 'live', 'stopped': settings.common.stopped}

    @app.get('/health/ready')
    def ready() -> dict[str, Any]:
        if settings.common.stopped:
            raise HTTPException(status_code=503, detail='global kill switch is active')
        try:
            active_store.ping()
            if consume_store is not None and consume_store is not active_store:
                consume_store.ping()
            ready_policy = current_policy()
            active_epoch = active_store.get_active_policy_epoch()
            if active_epoch != ready_policy.digest:
                raise RuntimeError('database active policy differs from mounted policy')
            _promotion_authority(ready_policy, settings)
            report = current_trust_store().report(utc_now())
            active_keys = sum(1 for item in report['keys'] if item['status'] == 'active')
            if active_keys == 0:
                raise RuntimeError('trust store has no active approval keys')
        except Exception as exc:
            raise HTTPException(status_code=503, detail='durable state or trust store is unavailable') from exc
        return {
            'status': 'ready',
            'policy_digest': ready_policy.digest,
            'status_context': ready_policy.status_context,
            'active_approval_keys': active_keys,
            'status_publisher': 'worker-github-app',
        }

    @app.post('/webhooks/github')
    async def github_webhook(
        request: Request,
        x_hub_signature_256: str | None = Header(default=None),
        x_github_event: str | None = Header(default=None),
        x_github_delivery: str | None = Header(default=None),
    ) -> dict[str, Any]:
        body = await request.body()
        try:
            merge_fact = ingest_merged_pull_request(
                secret=settings.webhook_secret,
                signature_header=x_hub_signature_256,
                event_name=x_github_event,
                delivery_id=x_github_delivery,
                body=body,
                allowed_repositories=active_policy.allowed_repositories,
                protected_ref=protected_ref,
                record_fact=durable_merge_fact_recorder,
                now=utc_now(),
            )
        except WebhookForbidden as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except WebhookUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except WebhookError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        if merge_fact is not None:
            return {
                'accepted': True,
                'merge_fact_id': merge_fact.merge_fact_id,
                'status': 'pending',
                'status_publisher': 'worker-github-app',
            }
        try:
            event = parse_pull_request_event(x_github_event, body)
        except WebhookError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        if event is None:
            return {'accepted': False, 'reason': 'ignored-event'}
        job_request = event.request
        if not active_policy.allows_repository(job_request.repository):
            raise HTTPException(status_code=403, detail='repository is not allowed by server policy')
        if event.closed:
            count = active_store.cancel_pr(job_request.repository, job_request.pr_number, now=utc_now())
            return {'accepted': True, 'cancelled_jobs': count}
        if settings.common.stopped:
            raise HTTPException(status_code=503, detail='global kill switch is active')
        job, created = active_store.enqueue(
            job_request,
            active_policy.digest,
            active_policy.max_attempts,
            now=utc_now(),
        )
        return {
            'accepted': True,
            'created': created,
            'job_id': job.job_id,
            'status': job.status,
            'status_publisher': 'worker-github-app',
        }

    @app.post('/approvals')
    async def submit_approval(request: Request) -> dict[str, Any]:
        if settings.common.stopped:
            raise HTTPException(status_code=503, detail='global kill switch is active')
        try:
            data = await request.json()
            envelope = ApprovalEnvelope.from_dict(data)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail='malformed approval envelope') from exc
        payload = envelope.payload
        if payload.scope not in active_policy.approval_scopes:
            raise HTTPException(status_code=400, detail='approval scope is not configured by server policy')
        job = active_store.get_job_for_sha(payload.repository, payload.head_sha)
        if job is None:
            raise HTTPException(status_code=404, detail='no Trust CI job exists for this exact SHA')
        try:
            verified = verify_approval(
                envelope,
                current_trust_store(),
                expected_repository=job.repository,
                expected_pr_number=job.pr_number,
                expected_base_sha=job.base_sha,
                expected_head_sha=job.head_sha,
                expected_policy_digest=job.policy_digest,
                now=utc_now(),
                max_ttl_seconds=active_policy.max_approval_ttl_seconds,
            )
            active_store.record_approval(verified, envelope, now=utc_now())
        except ApprovalError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ReplayError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        requeued = active_store.requeue_for_approval(job.repository, job.head_sha, now=utc_now())
        return {
            'accepted': True,
            'approval_id': verified.approval_id,
            'scope': verified.scope,
            'requeued_jobs': requeued,
            'status_publisher': 'worker-github-app',
        }

    @app.post('/promotions')
    async def submit_promotion(request: Request) -> JSONResponse:
        correlation_id = str(uuid.uuid4())
        envelope: PromotionEnvelope | None = None
        try:
            if not promotion_limiter.allow():
                raise _PromotionRejection(429, 'rate_limited', persist=False)
            request_headers = _promotion_request_headers(request)
            idempotency_key = request_headers['idempotency-key']
            supplied_correlation = request_headers['x-correlation-id']
            if not _bounded_header(idempotency_key, 16, 128):
                raise _PromotionRejection(400, 'malformed_envelope')
            if not _bounded_header(supplied_correlation, 1, 128):
                raise _PromotionRejection(400, 'malformed_envelope')
            correlation_id = supplied_correlation
            body = await _limited_json_body(request, 16 * 1024)
            envelope = _decode_promotion(body)
            if settings.common.stopped:
                raise _PromotionRejection(503, 'promotion_disabled')
            try:
                request_policy = current_policy()
                active_store.ping()
                active_epoch = active_store.get_active_policy_epoch()
                if active_epoch != request_policy.digest:
                    raise RuntimeError('database active policy differs from mounted policy')
                promotion_environment, promotion_max_ttl_seconds = (
                    _promotion_authority(request_policy, settings)
                )
                trusted_keys = current_trust_store()
            except Exception as exc:
                raise _PromotionRejection(503, 'authorization_unavailable') from exc

            payload = envelope.payload
            allowed_repositories = {
                repository.lower() for repository in request_policy.allowed_repositories
            }
            if (
                payload.repository not in allowed_repositories
                or payload.target_environment != promotion_environment
            ):
                raise _PromotionRejection(403, 'target_forbidden')
            if payload.policy_epoch != request_policy.digest:
                raise _PromotionRejection(403, 'policy_mismatch')
            current = utc_now()
            issued = parse_datetime(payload.issued_at)
            expires = parse_datetime(payload.expires_at)
            if (
                issued - current > timedelta(seconds=60)
                or current >= expires
                or (expires - issued).total_seconds()
                > promotion_max_ttl_seconds
            ):
                raise _PromotionRejection(422, 'envelope_not_current')
            expected = PromotionExpectedBinding(
                repository=payload.repository,
                merged_commit_sha=payload.merged_commit_sha,
                artifact_sha256=payload.artifact_sha256,
                target_environment=promotion_environment,
                policy_epoch=request_policy.digest,
                source_attestation_id=payload.source_attestation_id,
            )
            try:
                verify_promotion(
                    envelope,
                    trusted_keys,
                    expected,
                    current,
                    promotion_max_ttl_seconds,
                )
            except PromotionError as exc:
                raise _PromotionRejection(401, 'signature_invalid') from exc
            try:
                confirmed_policy = current_policy()
                if confirmed_policy.digest != request_policy.digest:
                    raise _PromotionRejection(503, 'authorization_unavailable')
                record, created = active_store.accept_promotion(
                    envelope,
                    idempotency_key,
                    correlation_id,
                    now=current,
                )
            except IdempotencyConflict as exc:
                raise _PromotionRejection(409, 'idempotency_conflict') from exc
            except PromotionReplay as exc:
                raise _PromotionRejection(409, 'promotion_replay') from exc
            except ProvenanceMismatch as exc:
                raise _PromotionRejection(403, 'provenance_mismatch') from exc
            except ReplayError as exc:
                raise _PromotionRejection(409, 'promotion_replay') from exc
            except Exception as exc:
                raise _PromotionRejection(503, 'authorization_unavailable') from exc
            outcome = 'accepted' if created else 'replay'
            _increment(app.state.promotion_outcomes, outcome)
            data = record.public_dict(idempotent_replay=not created)
            data['correlation_id'] = correlation_id
            return JSONResponse(
                data,
                status_code=201 if created else 200,
                headers={'X-Correlation-ID': correlation_id},
            )
        except _PromotionRejection as rejection:
            _increment(app.state.promotion_outcomes, rejection.code)
            if not rejection.persist:
                return _promotion_problem(rejection.status, rejection.code, correlation_id)
            try:
                active_store.record_promotion_rejection(
                    _rejected_event(envelope, correlation_id, rejection)
                )
            except Exception:
                app.state.promotion_audit_failures += 1
                return _promotion_problem(
                    503, 'authorization_unavailable', correlation_id
                )
            return _promotion_problem(rejection.status, rejection.code, correlation_id)

    @app.post('/promotions/{promotion_id}/consume')
    async def consume_promotion(promotion_id: str, request: Request) -> JSONResponse:
        correlation_id = str(uuid.uuid4())
        try:
            headers = _consume_request_headers(request, settings.deployer_token)
            correlation_id = headers['x-correlation-id']
            if not _bounded_header(correlation_id, 1, 128):
                raise _PromotionRejection(400, 'consume_malformed')
            if not consume_limiter.allow():
                raise _PromotionRejection(429, 'consume_rate_limited')
            body = await _limited_json_body(
                request, 4 * 1024, rejection_code='consume_malformed'
            )
            target, operation_id = _decode_consume_request(body)
            try:
                require_uuid_v1_5(promotion_id, 'promotion_id')
            except ValueError as exc:
                raise _PromotionRejection(400, 'consume_malformed') from exc
            if settings.common.stopped:
                raise _PromotionRejection(503, 'promotion_disabled')
            if promotion_consumer is None or not settings.deployer_token:
                raise _PromotionRejection(503, 'consume_unavailable')
            try:
                consumption = promotion_consumer.consume(
                    promotion_id, target, operation_id, utc_now()
                )
            except PromotionAlreadyConsumed as exc:
                raise _PromotionRejection(409, 'promotion_consumed') from exc
            except PromotionDenied as exc:
                raise _PromotionRejection(403, 'consume_forbidden') from exc
            except PromotionUnavailable as exc:
                raise _PromotionRejection(503, 'consume_unavailable') from exc
            return JSONResponse(
                {
                    'promotion_id': consumption.promotion_id,
                    'operation_id': consumption.operation_id,
                    'repository': consumption.expected.repository,
                    'merged_commit_sha': consumption.expected.merged_commit_sha,
                    'artifact_sha256': consumption.expected.artifact_sha256,
                    'target_environment': consumption.expected.target_environment,
                    'policy_epoch': consumption.expected.policy_epoch,
                    'source_attestation_id': consumption.expected.source_attestation_id,
                    'consumed_at': consumption.consumed_at.isoformat().replace('+00:00', 'Z'),
                    'consumed': True,
                    'correlation_id': correlation_id,
                },
                status_code=200,
                headers={'X-Correlation-ID': correlation_id},
            )
        except _PromotionRejection as rejection:
            return _promotion_problem(rejection.status, rejection.code, correlation_id)

    @app.get('/promotions/{promotion_id}/consume/{operation_id}')
    async def reconcile_promotion_consumption(
        promotion_id: str, operation_id: str, request: Request
    ) -> JSONResponse:
        correlation_id = str(uuid.uuid4())
        try:
            headers = _consume_reconciliation_headers(request, settings.deployer_token)
            correlation_id = headers['x-correlation-id']
            if not _bounded_header(correlation_id, 1, 128):
                raise _PromotionRejection(400, 'consume_malformed')
            if not consume_limiter.allow():
                raise _PromotionRejection(429, 'consume_rate_limited')
            try:
                require_uuid_v1_5(promotion_id, 'promotion_id')
                require_uuid_v1_5(operation_id, 'operation_id')
            except ValueError as exc:
                raise _PromotionRejection(400, 'consume_malformed') from exc
            if promotion_consumer is None or not settings.deployer_token:
                raise _PromotionRejection(503, 'consume_unavailable')
            try:
                consumption = promotion_consumer.reconcile(
                    promotion_id, operation_id
                )
            except PromotionUnavailable as exc:
                raise _PromotionRejection(503, 'consume_unavailable') from exc
            if consumption is None:
                raise _PromotionRejection(404, 'consumption_not_found')
            data = _consumption_representation(consumption, correlation_id)
            data['reconciled'] = True
            return JSONResponse(
                data,
                status_code=200,
                headers={'X-Correlation-ID': correlation_id},
            )
        except _PromotionRejection as rejection:
            return _promotion_problem(rejection.status, rejection.code, correlation_id)

    @app.post('/promotions/{promotion_id}/consume/{operation_id}/terminal')
    async def record_deployment_terminal(
        promotion_id: str, operation_id: str, request: Request
    ) -> JSONResponse:
        correlation_id = str(uuid.uuid4())
        try:
            headers = _consume_request_headers(request, settings.deployer_token)
            correlation_id = headers['x-correlation-id']
            if not _bounded_header(correlation_id, 1, 128):
                raise _PromotionRejection(400, 'terminal_malformed')
            if not consume_limiter.allow():
                raise _PromotionRejection(429, 'consume_rate_limited')
            try:
                require_uuid_v1_5(promotion_id, 'promotion_id')
                require_uuid_v1_5(operation_id, 'operation_id')
            except ValueError as exc:
                raise _PromotionRejection(400, 'terminal_malformed') from exc
            body = await _limited_json_body(
                request, 8 * 1024, rejection_code='terminal_malformed'
            )
            event_type, reason_code, details = _decode_terminal_request(body)
            if consume_store is None or not settings.deployer_token:
                raise _PromotionRejection(503, 'consume_unavailable')
            try:
                event = consume_store.record_deployment_terminal(
                    promotion_id, operation_id, event_type,
                    reason_code=reason_code, details=details, now=utc_now(),
                )
            except ValueError as exc:
                raise _PromotionRejection(400, 'terminal_malformed') from exc
            except RuntimeError as exc:
                raise _PromotionRejection(409, 'terminal_conflict') from exc
            return JSONResponse(
                event.to_dict(), status_code=201,
                headers={'X-Correlation-ID': correlation_id},
            )
        except _PromotionRejection as rejection:
            return _promotion_problem(rejection.status, rejection.code, correlation_id)

    @app.get('/jobs/{job_id}', dependencies=[Depends(authorize_read)])
    def get_job(job_id: str) -> dict[str, Any]:
        try:
            job = active_store.get_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='job not found') from exc
        data = job.to_dict()
        data['result'] = _public_result(data.get('result'))
        return data

    @app.get('/attestations/{job_id}', dependencies=[Depends(authorize_read)])
    def get_attestation(job_id: str) -> dict[str, Any]:
        envelope = active_store.get_attestation(job_id)
        if envelope is None:
            raise HTTPException(status_code=404, detail='attestation not found')
        return envelope.to_dict()

    @app.get('/metrics', dependencies=[Depends(authorize_read)], response_class=PlainTextResponse)
    def metrics() -> PlainTextResponse:
        snapshot = collect_metrics(
            active_store,
            now=utc_now(),
            stopped=settings.common.stopped,
            policy_digest=active_policy.digest,
            check_name=active_policy.check_name,
        )
        rendered = render_prometheus(snapshot)
        rendered += '# HELP adaptive_trust_ci_promotion_requests_total Promotion API decisions by bounded outcome.\n'
        rendered += '# TYPE adaptive_trust_ci_promotion_requests_total counter\n'
        for outcome, count in sorted(app.state.promotion_outcomes.items()):
            rendered += f'adaptive_trust_ci_promotion_requests_total{{outcome="{outcome}"}} {count}\n'
        rendered += '# HELP adaptive_trust_ci_promotion_audit_failures_total Rejected-audit persistence failures.\n'
        rendered += '# TYPE adaptive_trust_ci_promotion_audit_failures_total counter\n'
        rendered += f'adaptive_trust_ci_promotion_audit_failures_total {app.state.promotion_audit_failures}\n'
        return PlainTextResponse(
            rendered,
            media_type='text/plain; version=0.0.4; charset=utf-8',
        )

    return app


class _PromotionRejection(Exception):
    def __init__(self, status: int, code: str, *, persist: bool = True) -> None:
        self.status = status
        self.code = code
        self.persist = persist


class _PromotionRateLimiter:
    def __init__(self, maximum: int) -> None:
        self._maximum = maximum
        self._attempts: deque[float] = deque(maxlen=maximum)
        self._lock = threading.Lock()

    def allow(self) -> bool:
        current = time.monotonic()
        with self._lock:
            while self._attempts and current - self._attempts[0] >= 60.0:
                self._attempts.popleft()
            if len(self._attempts) >= self._maximum:
                return False
            self._attempts.append(current)
            return True


async def _limited_json_body(
    request: Request, maximum: int, *, rejection_code: str = 'malformed_envelope'
) -> bytes:
    raw_headers = request.scope.get('headers', ())
    content_lengths = [value for name, value in raw_headers if name.lower() == b'content-length']
    transfer_encodings = [value for name, value in raw_headers if name.lower() == b'transfer-encoding']
    if len(content_lengths) > 1 or len(transfer_encodings) > 1:
        raise _PromotionRejection(400, rejection_code)
    if content_lengths and transfer_encodings:
        raise _PromotionRejection(400, rejection_code)
    if transfer_encodings and transfer_encodings[0].strip().lower() != b'chunked':
        raise _PromotionRejection(400, rejection_code)
    if content_lengths:
        raw_length = content_lengths[0].strip()
        if not raw_length.isdigit() or int(raw_length) > maximum:
            raise _PromotionRejection(400, rejection_code)
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > maximum:
            raise _PromotionRejection(400, rejection_code)
    if not body:
        raise _PromotionRejection(400, rejection_code)
    if content_lengths and int(content_lengths[0].strip()) != len(body):
        raise _PromotionRejection(400, rejection_code)
    return bytes(body)


def _consume_request_headers(request: Request, deployer_token: str) -> dict[str, str]:
    singleton_names = (
        'authorization',
        'x-correlation-id',
        'content-type',
        'content-encoding',
    )
    values: dict[str, list[bytes]] = {name: [] for name in singleton_names}
    for raw_name, raw_value in request.scope.get('headers', ()):
        name = raw_name.decode('ascii', errors='ignore').lower()
        if name in values:
            values[name].append(raw_value)
    if any(len(values[name]) != 1 for name in ('authorization', 'x-correlation-id', 'content-type')):
        if len(values['authorization']) == 0:
            raise _PromotionRejection(401, 'deployer_unauthorized')
        raise _PromotionRejection(400, 'consume_malformed')
    if len(values['content-encoding']) > 1 or any(
        b',' in item for items in values.values() for item in items
    ):
        raise _PromotionRejection(400, 'consume_malformed')
    try:
        decoded = {
            name: items[0].decode('ascii') if items else ''
            for name, items in values.items()
        }
    except UnicodeDecodeError as exc:
        raise _PromotionRejection(400, 'consume_malformed') from exc
    content_type_parts = [
        part.strip().lower() for part in decoded['content-type'].split(';')
    ]
    if content_type_parts[0] != 'application/json' or any(
        part != 'charset=utf-8' for part in content_type_parts[1:]
    ):
        raise _PromotionRejection(400, 'consume_malformed')
    if decoded['content-encoding'].strip().lower() not in {'', 'identity'}:
        raise _PromotionRejection(400, 'consume_malformed')
    expected = f'Bearer {deployer_token}'
    if not deployer_token or not hmac.compare_digest(decoded['authorization'], expected):
        raise _PromotionRejection(401, 'deployer_unauthorized')
    return decoded


def _consume_reconciliation_headers(
    request: Request, deployer_token: str
) -> dict[str, str]:
    values: dict[str, list[bytes]] = {
        'authorization': [],
        'x-correlation-id': [],
    }
    for raw_name, raw_value in request.scope.get('headers', ()):
        name = raw_name.decode('ascii', errors='ignore').lower()
        if name in values:
            values[name].append(raw_value)
    if any(len(values[name]) != 1 for name in values):
        if not values['authorization']:
            raise _PromotionRejection(401, 'deployer_unauthorized')
        raise _PromotionRejection(400, 'consume_malformed')
    if any(b',' in item for items in values.values() for item in items):
        raise _PromotionRejection(400, 'consume_malformed')
    try:
        decoded = {name: items[0].decode('ascii') for name, items in values.items()}
    except UnicodeDecodeError as exc:
        raise _PromotionRejection(400, 'consume_malformed') from exc
    expected = f'Bearer {deployer_token}'
    if not deployer_token or not hmac.compare_digest(decoded['authorization'], expected):
        raise _PromotionRejection(401, 'deployer_unauthorized')
    return decoded


def _consumption_representation(
    consumption: Any, correlation_id: str
) -> dict[str, Any]:
    return {
        'promotion_id': consumption.promotion_id,
        'operation_id': consumption.operation_id,
        'repository': consumption.expected.repository,
        'merged_commit_sha': consumption.expected.merged_commit_sha,
        'artifact_sha256': consumption.expected.artifact_sha256,
        'target_environment': consumption.expected.target_environment,
        'policy_epoch': consumption.expected.policy_epoch,
        'source_attestation_id': consumption.expected.source_attestation_id,
        'consumed_at': consumption.consumed_at.isoformat().replace('+00:00', 'Z'),
        'consumed': True,
        'correlation_id': correlation_id,
    }


def _decode_consume_request(body: bytes) -> tuple[PromotionTarget, str]:
    fields = {
        'repository',
        'merged_commit_sha',
        'artifact_sha256',
        'target_environment',
        'policy_epoch',
        'source_attestation_id',
        'operation_id',
    }
    try:
        data = json.loads(
            body.decode('utf-8'),
            object_pairs_hook=_strict_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
        )
        if not isinstance(data, dict) or set(data) != fields:
            raise ValueError
        operation_id = data.pop('operation_id')
        require_uuid_v1_5(operation_id, 'operation_id')
        target = PromotionTarget(**data)
        return target, operation_id
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _PromotionRejection(400, 'consume_malformed') from exc


def _decode_terminal_request(body: bytes) -> tuple[str, str, dict[str, Any]]:
    try:
        data = json.loads(
            body.decode('utf-8'), object_pairs_hook=_strict_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
        )
        if not isinstance(data, dict) or set(data) != {
            'event_type', 'reason_code', 'details'
        }:
            raise ValueError
        event_type = data['event_type']
        reason_code = data['reason_code']
        details = data['details']
        # The event model/store performs the final bounded semantic validation.
        if not isinstance(event_type, str) or not isinstance(reason_code, str) or not isinstance(details, dict):
            raise ValueError
        return event_type, reason_code, details
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _PromotionRejection(400, 'terminal_malformed') from exc


def _promotion_request_headers(request: Request) -> dict[str, str]:
    singleton_names = (
        'idempotency-key',
        'x-correlation-id',
        'content-type',
        'content-encoding',
    )
    raw_headers = request.scope.get('headers', ())
    values: dict[str, list[bytes]] = {name: [] for name in singleton_names}
    for raw_name, raw_value in raw_headers:
        name = raw_name.decode('ascii', errors='ignore').lower()
        if name in values:
            values[name].append(raw_value)
    for required in ('idempotency-key', 'x-correlation-id', 'content-type'):
        if len(values[required]) != 1:
            raise _PromotionRejection(400, 'malformed_envelope')
    if len(values['content-encoding']) > 1:
        raise _PromotionRejection(400, 'malformed_envelope')
    if any(b',' in item for items in values.values() for item in items):
        raise _PromotionRejection(400, 'malformed_envelope')
    try:
        decoded = {
            name: items[0].decode('ascii') if items else ''
            for name, items in values.items()
        }
    except UnicodeDecodeError as exc:
        raise _PromotionRejection(400, 'malformed_envelope') from exc
    content_type_parts = [
        part.strip().lower() for part in decoded['content-type'].split(';')
    ]
    if content_type_parts[0] != 'application/json' or any(
        part != 'charset=utf-8' for part in content_type_parts[1:]
    ):
        raise _PromotionRejection(400, 'malformed_envelope')
    if decoded['content-encoding'].strip().lower() not in {'', 'identity'}:
        raise _PromotionRejection(400, 'malformed_envelope')
    return decoded


def _promotion_authority(policy: Policy, settings: ApiSettings) -> tuple[str, int]:
    if (
        settings.promotion_environment not in policy.promotion.environments
        or settings.promotion_max_ttl_seconds > policy.promotion.max_ttl_seconds
    ):
        raise RuntimeError('runtime promotion controls would widen current policy')
    return settings.promotion_environment, settings.promotion_max_ttl_seconds


def _load_policy_snapshot(path) -> Policy:
    try:
        with path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            raw = stream.read()
            after = os.fstat(stream.fileno())
        current = path.stat()
        def identity(item):
            return (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
        if identity(before) != identity(after) or identity(after) != identity(current):
            raise PolicyError('policy changed while being resolved')
        data = json.loads(raw.decode('utf-8'))
        if not isinstance(data, dict):
            raise PolicyError('policy root must be an object')
        return Policy.from_dict(data)
    except PolicyError:
        raise
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PolicyError('current policy is unavailable') from exc


def _decode_promotion(body: bytes) -> PromotionEnvelope:
    try:
        raw = body.decode('utf-8')
        data = json.loads(
            raw,
            object_pairs_hook=_strict_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
        )
        if not isinstance(data, dict):
            raise ValueError
        if set(data) == {'payload', 'algorithm', 'signature'} and isinstance(data.get('payload'), dict):
            if data.get('algorithm') != 'Ed25519' or data['payload'].get('schema_version') != 1:
                raise _PromotionRejection(400, 'unsupported_contract')
        return PromotionEnvelope.from_dict(data)
    except _PromotionRejection:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _PromotionRejection(400, 'malformed_envelope') from exc


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _bounded_header(value: str | None, minimum: int, maximum: int) -> bool:
    return bool(
        isinstance(value, str)
        and minimum <= len(value.encode('utf-8')) <= maximum
        and value == value.strip()
        and all(ord(character) >= 32 and ord(character) != 127 for character in value)
    )


def _rejected_event(
    envelope: PromotionEnvelope | None,
    correlation_id: str,
    rejection: _PromotionRejection,
) -> PromotionEvent:
    payload = envelope.payload if envelope is not None else None
    return PromotionEvent(
        schema_version=1,
        event_id=str(uuid.uuid4()),
        event_type='promotion.rejected',
        occurred_at=utc_now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        promotion_id=None,
        correlation_id=correlation_id,
        operation_id=None,
        actor=payload.actor if payload else None,
        key_id=payload.key_id if payload else None,
        repository=payload.repository if payload else None,
        merged_commit_sha=payload.merged_commit_sha if payload else None,
        artifact_sha256=payload.artifact_sha256 if payload else None,
        target_environment=payload.target_environment if payload else None,
        policy_epoch=payload.policy_epoch if payload else None,
        outcome='rejected',
        reason_code=rejection.code,
        details={'http_status': rejection.status},
    )


def _promotion_problem(status: int, code: str, correlation_id: str) -> JSONResponse:
    return JSONResponse(
        {
            'type': f'https://dimkox.github.io/adaptive-grok-build-pro/problems/{code}',
            'title': 'Promotion request rejected',
            'status': status,
            'code': code,
            'correlation_id': correlation_id,
        },
        status_code=status,
        media_type='application/problem+json',
        headers={'X-Correlation-ID': correlation_id},
    )


def _increment(counters: dict[str, int], key: str) -> None:
    counters[key] = counters.get(key, 0) + 1


def _bearer_authorizer(expected_token: str) -> Callable[..., None]:
    expected = f'Bearer {expected_token}'

    def authorize(authorization: str | None = Header(default=None)) -> None:
        supplied = authorization or ''
        if not hmac.compare_digest(supplied, expected):
            raise HTTPException(
                status_code=401,
                detail='valid read bearer token required',
                headers={'WWW-Authenticate': 'Bearer'},
            )

    return authorize


def _public_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    public: dict[str, Any] = {}
    for key in (
        'expected_policy_digest',
        'job_policy_digest',
        'changed_files',
        'required_scopes',
        'missing_scopes',
        'infrastructure_error',
        'replayed',
        'attestation',
    ):
        if key in value:
            public[key] = value[key]
    commands = value.get('commands')
    if isinstance(commands, list):
        public['commands'] = [
            {
                key: item[key]
                for key in ('name', 'status', 'exit_code', 'duration_seconds', 'output_sha256')
                if isinstance(item, dict) and key in item
            }
            for item in commands
            if isinstance(item, dict)
        ]
    return public
