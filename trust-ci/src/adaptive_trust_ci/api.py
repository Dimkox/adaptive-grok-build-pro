from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

from .models import ApprovalEnvelope, utc_now
from .policy import Policy
from .settings import ApiSettings
from .signing import ApprovalError, TrustStore, verify_approval
from .store import PostgresStore, ReplayError, Store
from .webhooks import WebhookError, parse_pull_request_event, verify_webhook_signature


def create_app(
    settings: ApiSettings,
    *,
    store: Store | None = None,
    policy: Policy | None = None,
    trust_store: TrustStore | None = None,
) -> FastAPI:
    active_policy = policy or Policy.load(settings.common.policy_path)
    trusted_keys = trust_store or TrustStore.load(settings.trust_store_path)
    active_store = store or PostgresStore(settings.common.database_url)

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
    app.state.trust_store = trusted_keys

    @app.get('/health/live')
    def live() -> dict[str, Any]:
        return {'status': 'live', 'stopped': settings.common.stopped}

    @app.get('/health/ready')
    def ready() -> dict[str, Any]:
        if settings.common.stopped:
            raise HTTPException(status_code=503, detail='global kill switch is active')
        try:
            active_store.ping()
        except Exception as exc:
            raise HTTPException(status_code=503, detail='durable state is unavailable') from exc
        return {
            'status': 'ready',
            'policy_digest': active_policy.digest,
            'status_context': active_policy.status_context,
            'status_publisher': 'worker-github-app',
        }

    @app.post('/webhooks/github')
    async def github_webhook(
        request: Request,
        x_hub_signature_256: str | None = Header(default=None),
        x_github_event: str | None = Header(default=None),
    ) -> dict[str, Any]:
        body = await request.body()
        try:
            verify_webhook_signature(settings.webhook_secret, body, x_hub_signature_256)
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
                trusted_keys,
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

    @app.get('/jobs/{job_id}')
    def get_job(job_id: str) -> dict[str, Any]:
        try:
            job = active_store.get_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail='job not found') from exc
        data = job.to_dict()
        data['result'] = _public_result(data.get('result'))
        return data

    @app.get('/attestations/{job_id}')
    def get_attestation(job_id: str) -> dict[str, Any]:
        envelope = active_store.get_attestation(job_id)
        if envelope is None:
            raise HTTPException(status_code=404, detail='attestation not found')
        return envelope.to_dict()

    return app


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
