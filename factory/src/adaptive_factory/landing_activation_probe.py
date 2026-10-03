"""Durable, server-executed activation probes for the operator landing host."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import hashlib
import re
import time
import uuid

from .landing_http import HttpLandingProfile
from .landing_provider import FAILURE_CATEGORIES
from .landing_service import LandingServiceError


PROBE_PROFILES = ("qwen", "qwen-intl", "qwen-omni", "qwen-omni-intl")
SYNTHETIC_PROBE_BRIEF = (
    "Create an English landing page for a fictional local gardening club. One hero section. "
    "No links, prices, contacts or factual claims."
)
IDEMPOTENCY_DOMAIN = b"adaptive-factory.landing-activation-probe/idempotency/v1\0"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def activation_probe_profile(profile_id: str) -> dict[str, str]:
    if profile_id not in PROBE_PROFILES:
        raise LandingServiceError("probe_profile", 422, "activation probe profile is not configured")
    profile = HttpLandingProfile.for_provider(profile_id, available=True)
    return {
        "profile_id": profile.profile_id,
        "provider_id": profile.provider_id,
        "model_id": profile.model_id,
        "profile_digest": profile.profile_digest,
        "input_digest": hashlib.sha256(SYNTHETIC_PROBE_BRIEF.encode("utf-8")).hexdigest(),
    }


class LandingActivationProbeService:
    """Reserve before executing; same idempotency key can never dispatch twice."""

    def __init__(self, store, *, profiles: Mapping[str, Mapping[str, str]], runner: Callable[[str], dict] | None):
        self._store = store
        self._profiles = {name: dict(value) for name, value in profiles.items()}
        self._runner = runner
        for name, facts in self._profiles.items():
            expected = activation_probe_profile(name)
            if facts != expected:
                raise ValueError("activation probe profile snapshot mismatch")

    def create(self, *, idempotency_key: str, profile_id: str) -> dict[str, object]:
        if not isinstance(idempotency_key, str) or not _ID.fullmatch(idempotency_key):
            raise LandingServiceError("idempotency", 400, "activation probe idempotency key invalid")
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise LandingServiceError("probe_profile", 422, "activation probe profile is not configured")
        if self._runner is None:
            raise LandingServiceError("probe_unavailable", 503, "activation probe profile unavailable")
        idempotency_digest = hashlib.sha256(IDEMPOTENCY_DOMAIN + idempotency_key.encode("utf-8")).hexdigest()
        probe_id = uuid.uuid4().hex
        record, created = self._store.reserve_activation_probe(
            probe_id=probe_id,
            idempotency_digest=idempotency_digest,
            **profile,
        )
        if not created:
            return record
        started = time.monotonic()
        try:
            result = self._runner(profile_id)
            outcome = self._success_outcome(profile, result)
        except Exception as exc:
            category = getattr(exc, "category", None)
            if category not in FAILURE_CATEGORIES:
                category = "protocol"
            status = getattr(exc, "http_status", None)
            if type(status) is not int or not 100 <= status <= 599:
                status = None
            outcome = {
                "state": "failed", "spec_digest": None, "response_digest": None,
                "usage_input_units": None, "usage_output_units": None,
                "elapsed_ms": min(2_147_483_647, max(0, int((time.monotonic() - started) * 1000))),
                "failure_category": category, "http_status": status,
            }
        return self._store.finish_activation_probe(record["probe_id"], outcome)

    def get(self, probe_id: str) -> dict[str, object]:
        return self._store.get_activation_probe(probe_id)

    @staticmethod
    def _success_outcome(profile: Mapping[str, str], result: object) -> dict[str, object]:
        required = {
            "state", "profile_id", "provider_id", "model_id", "profile_digest", "input_digest",
            "spec_digest", "response_digest", "usage_input_units", "usage_output_units", "elapsed_ms",
        }
        if not isinstance(result, dict) or set(result) != required or result.get("state") != "normalized":
            raise ValueError("probe result shape")
        for key, value in profile.items():
            if result.get(key) != value:
                raise ValueError("probe result identity")
        if any(not isinstance(result.get(name), str) or not _HEX64.fullmatch(result[name])
               for name in ("spec_digest", "response_digest")):
            raise ValueError("probe result digest")
        if any(type(result.get(name)) is not int or not 0 <= result[name] <= 2_147_483_647
               for name in ("usage_input_units", "usage_output_units", "elapsed_ms")):
            raise ValueError("probe result facts")
        return {
            "state": "normalized", "spec_digest": result["spec_digest"],
            "response_digest": result["response_digest"],
            "usage_input_units": result["usage_input_units"],
            "usage_output_units": result["usage_output_units"],
            "elapsed_ms": result["elapsed_ms"], "failure_category": None, "http_status": None,
        }
