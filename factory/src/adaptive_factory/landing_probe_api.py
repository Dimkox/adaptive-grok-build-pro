"""Operator-only activation probe endpoints installed on the landing Unix-socket app."""

from fastapi import Header, HTTPException
from fastapi.responses import JSONResponse

from .api import _closed, _request_id, _text
from .landing_service import LandingServiceError


def _operator(authenticator, authorization: str | None):
    actor = authenticator.authenticate(authorization, "landing:probe")
    if actor.kind != "operator":
        raise HTTPException(403, "operator actor required")
    return actor


def install_landing_probe_api(app, service, authenticator):
    @app.post("/v1/landing-probes", tags=["landing-probe"], operation_id="createLandingActivationProbe")
    def create_probe(
        payload: dict,
        authorization: str | None = Header(None),
        idempotency_key: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        _operator(authenticator, authorization)
        key = _request_id(idempotency_key, "Idempotency-Key")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID") if x_correlation_id is not None else None
        payload = _closed(payload, {"profile_id"})
        profile_id = _text(payload["profile_id"], "profile_id", maximum=128, identifier=True)
        if service is None:
            raise LandingServiceError("probe_unavailable", 503, "activation probe unavailable")
        result = service.create(idempotency_key=key, profile_id=profile_id)
        headers = {"X-Correlation-ID": correlation} if correlation else None
        return JSONResponse(result, headers=headers)

    @app.get("/v1/landing-probes/{probe_id}", tags=["landing-probe"], operation_id="getLandingActivationProbe")
    def get_probe(
        probe_id: str,
        authorization: str | None = Header(None),
        x_correlation_id: str | None = Header(None),
    ):
        _operator(authenticator, authorization)
        probe_id = _request_id(probe_id, "probe_id")
        correlation = _request_id(x_correlation_id, "X-Correlation-ID") if x_correlation_id is not None else None
        if service is None:
            raise LandingServiceError("probe_unavailable", 503, "activation probe unavailable")
        result = service.get(probe_id)
        headers = {"X-Correlation-ID": correlation} if correlation else None
        return JSONResponse(result, headers=headers)
