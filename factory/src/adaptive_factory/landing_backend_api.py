"""Versioned receipts installed only on the dedicated landing application."""

from fastapi import Header, HTTPException
from fastapi.responses import JSONResponse

from .api import _request_id, _text
from .landing_service import LandingServiceError


def install_backend_api(app, service, authenticator):
    @app.middleware("http")
    async def expected_backend(request, call_next):
        expected_profile = request.headers.get("X-Expected-Profile-Digest")
        expected_actor = request.headers.get("X-Expected-Actor-ID")
        if request.method == "POST" and request.url.path == "/v1/landing-inputs" and (
            expected_profile is not None or expected_actor is not None
        ):
            try:
                actor = authenticator.authenticate(request.headers.get("Authorization"), "landing:submit")
                authenticator.authenticate(request.headers.get("Authorization"), "landing:read")
                capability = service.backend_capability(
                    repository_id=request.headers.get("X-Repository-ID"), actor=actor,
                )
                if expected_actor != actor.actor_id or expected_profile != capability["profile_digest"]:
                    return JSONResponse({"detail": "backend identity mismatch"}, status_code=409)
            except HTTPException as exc:
                return JSONResponse({"detail": "backend authorization rejected"}, status_code=exc.status_code)
            except LandingServiceError as exc:
                return JSONResponse({"detail": "backend capability rejected"}, status_code=exc.status_code)
        return await call_next(request)

    @app.get("/v2/landing-backend", tags=["landing"], operation_id="getLandingBackendCapability")
    def capability(authorization: str | None = Header(None), x_correlation_id: str | None = Header(None),
                   x_repository_id: str | None = Header(None)):
        actor = authenticator.authenticate(authorization, "landing:submit")
        authenticator.authenticate(authorization, "landing:read")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        repository = _text(x_repository_id, "X-Repository-ID", maximum=128, identifier=True)
        return JSONResponse(service.backend_capability(repository_id=repository, actor=actor),
                            headers={"X-Correlation-ID": correlation})

    @app.get("/v2/landing-jobs/{job_id}/attempt", tags=["landing"], operation_id="getLandingProviderAttempt")
    def attempt(job_id: str, authorization: str | None = Header(None), x_correlation_id: str | None = Header(None),
                x_repository_id: str | None = Header(None)):
        actor = authenticator.authenticate(authorization, "landing:read")
        job = _request_id(job_id, "job_id")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID")
        repository = _text(x_repository_id, "X-Repository-ID", maximum=128, identifier=True)
        return JSONResponse(service.attempt_status(job, repository_id=repository, actor=actor),
                            headers={"X-Correlation-ID": correlation})
