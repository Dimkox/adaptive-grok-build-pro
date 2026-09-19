"""Transport-neutral identity and normalization for the opt-in HTTP providers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Protocol

from .contracts import HEX64, canonical_json
from .landing_contracts import (
    LandingContractError,
    LandingProviderEvidenceV2,
    landing_digest,
)
from .landing_intake import PrivateLandingBlobStore
from .landing_media import (
    LandingMediaError, PDF_DECODER_DIGEST, PDF_PYPDF_VERSION,
    media_preflight, prepare_landing_media,
)
from .landing_normalizer import (
    LANDING_NORMALIZATION_DRAFT_SCHEMA_SHA256,
    LANDING_NORMALIZER_PROMPT,
    decode_landing_draft,
)
from .landing_provider import (
    EXECUTOR_CODE_CATEGORIES,
    LandingNormalizationOutcome,
    LandingNormalizationRequest,
    LandingProviderError,
    MAX_PROVIDER_OUTPUT_BYTES,
)
from .landing_observation import LandingProviderObservation


HTTP_ADAPTER_ID = "https-chat-completions"
HTTP_ADAPTER_VERSION = "1.1.0"
GROK_HTTP_ADAPTER_VERSION = "1.1.1"
HTTP_NORMALIZER_PROMPT = (
    LANDING_NORMALIZER_PROMPT + "\nReturn one JSON object matching this schema; "
    "use only facts supported by the supplied media, without Markdown fences:\n"
    + (Path(__file__).resolve().parent / "resources/landing-normalization-draft.v1.schema.json").read_text(encoding="utf-8")
)
HTTP_NORMALIZER_PROMPT_SHA256 = hashlib.sha256(HTTP_NORMALIZER_PROMPT.encode()).hexdigest()
HTTP_PROTOCOL_VERSION = "adaptive-factory.http-landing-normalizer/v1"
HTTP_PROVIDER_ENDPOINTS = {
    "grok": ("https://api.x.ai/v1", "grok-4"),
    "qwen": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
}
HTTP_PROFILES = {
    "openai": ("openai", "https://api.openai.com/v1", "gpt-4.1-mini-2025-04-14", False, ("docx", "text")),
    "anthropic": ("anthropic", "https://api.anthropic.com/v1", "claude-haiku-4-5-20251001", False, ("docx", "text")),
    "openrouter": ("openrouter", "https://openrouter.ai/api/v1", "google/gemini-3.1-flash-lite", False, ("docx", "text")),
    "grok": ("grok", "https://api.x.ai/v1", "grok-4", False, ("docx", "text")),
    "qwen": ("qwen", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus", False, ("docx", "text")),
    "qwen-intl": ("qwen", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", "qwen-plus", False, ("docx", "text")),
    "grok-vision": ("grok", "https://api.x.ai/v1", "grok-4.6", False, ("docx", "image", "pdf", "text")),
    "qwen-omni": ("qwen", "https://dashscope.aliyuncs.com/compatible-mode/v1",
                  "qwen3.5-omni-plus-2026-03-15", True, ("audio", "docx", "image", "pdf", "text")),
    "qwen-omni-intl": ("qwen", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                       "qwen3.5-omni-plus-2026-03-15", True, ("audio", "docx", "image", "pdf", "text")),
}
HTTP_MEDIA_KINDS = frozenset({"text", "docx"})
MAX_HTTP_REQUEST_BYTES = 30 * 1_048_576
HTTP_TOOL_POLICY_DIGEST = hashlib.sha256(
    b"http-landing/v1.1:profile-bound-media;no-tools;no-redirect;no-proxy;no-retry"
).hexdigest()
HTTP_DECODER_DIGEST = hashlib.sha256(
    b"http-landing/v1.1:strict-json-or-omni-sse-single-stop-final-usage-draft"
).hexdigest()
GROK_HTTP_DECODER_DIGEST = hashlib.sha256(
    b"http-landing/v1.1.1:grok-strict-json-single-stop-draft;additive-or-inclusive-reasoning-usage"
).hexdigest()


_DRAFT_FAILURE_REASONS = {
    "invalid_json": "draft_invalid_json",
    "json_too_large": "draft_json_too_large",
    "duplicate_json_key": "draft_duplicate_json_key",
    "nonfinite_json": "draft_nonfinite_json",
    "invalid_json_object": "draft_invalid_json_object",
    "draft_fields": "draft_fields",
    "sections": "draft_sections",
    "locale": "draft_locale",
    "direction": "draft_direction",
    "invalid_object": "draft_invalid_object",
    "unknown_fields": "draft_unknown_fields",
    "missing_fields": "draft_missing_fields",
    "section_kind": "draft_section_kind",
    "section_items": "draft_section_items",
    "invalid_text": "draft_invalid_text",
    "unsafe_content": "draft_unsafe_content",
    "cta_path": "draft_cta_path",
}


def _draft_failure_reason(error: Exception) -> str:
    # Contract details can contain model-supplied keys; only emit fixed local codes.
    if isinstance(error, LandingContractError) and type(error.code) is str:
        return _DRAFT_FAILURE_REASONS.get(error.code, "draft_validation_failed")
    if (isinstance(error, LandingProviderError) and len(error.args) == 1
            and type(error.args[0]) is str and error.args[0] == "draft_fields"):
        return "draft_fields"
    return "draft_validation_failed"


@dataclass(frozen=True)
class HttpLandingProfile:
    provider_id: str
    base_url: str
    model_id: str
    available: bool = False
    timeout_seconds: int = 60
    max_response_bytes: int = 1_048_576
    max_output_tokens: int = 4_096
    profile_id: str | None = None
    streaming: bool = False
    media_kinds: tuple[str, ...] = ("docx", "text")

    def __post_init__(self) -> None:
        if self.profile_id is None:
            object.__setattr__(self, "profile_id", self.provider_id)
        if not isinstance(self.profile_id, str) or HTTP_PROFILES.get(self.profile_id) != (
            self.provider_id, self.base_url, self.model_id, self.streaming, self.media_kinds
        ) or type(self.streaming) is not bool:
            raise LandingProviderError("http_profile_identity")
        if type(self.available) is not bool:
            raise LandingProviderError("http_profile_available")
        for value, minimum, maximum in (
            (self.timeout_seconds, 1, 300),
            (self.max_response_bytes, 1_024, 1_048_576),
            (self.max_output_tokens, 1, 8_192),
        ):
            if type(value) is not int or not minimum <= value <= maximum:
                raise LandingProviderError("http_profile_limit")

    @classmethod
    def for_provider(cls, provider_id: str, *, available: bool = False):
        if provider_id not in HTTP_PROFILES:
            raise LandingProviderError("http_profile_identity")
        provider, endpoint, model, streaming, media = HTTP_PROFILES[provider_id]
        return cls(provider, endpoint, model, available=available,
                   profile_id=provider_id, streaming=streaming, media_kinds=media)

    @property
    def adapter_version(self) -> str:
        if self.provider_id in {"openai", "anthropic", "openrouter"}:
            return "1.0.0"
        return GROK_HTTP_ADAPTER_VERSION if self.provider_id == "grok" else HTTP_ADAPTER_VERSION

    @property
    def adapter_id(self) -> str:
        return "https-anthropic-messages" if self.provider_id == "anthropic" else HTTP_ADAPTER_ID

    @property
    def decoder_digest(self) -> str:
        if self.provider_id in {"openai", "anthropic", "openrouter"}:
            return hashlib.sha256(
                (self.provider_id + ":landing/v1:strict-schema;bounded-inclusive-usage;messages-cache-input;no-tools").encode()
            ).hexdigest()
        return GROK_HTTP_DECODER_DIGEST if self.provider_id == "grok" else HTTP_DECODER_DIGEST

    def to_facts(self) -> dict[str, object]:
        return {
            **({"api_family": "messages", "api_version": "2023-06-01"}
               if self.provider_id == "anthropic" else {}),
            **({"upstream_endpoint": "google-vertex/global", "allow_fallbacks": False,
                "require_parameters": True} if self.provider_id == "openrouter" else {}),
            **({"enable_thinking": False, "response_format": "json_object"}
               if self.profile_id == "qwen-intl" else {}),
            "schema_version": 1,
            "profile_id": self.profile_id,
            "provider_id": self.provider_id,
            "base_url": self.base_url,
            "model_id": self.model_id,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "available": self.available,
            "timeout_seconds": self.timeout_seconds,
            "max_request_bytes": MAX_HTTP_REQUEST_BYTES,
            "max_response_bytes": self.max_response_bytes,
            "max_draft_bytes": MAX_PROVIDER_OUTPUT_BYTES,
            "max_output_tokens": self.max_output_tokens,
            "media_kinds": list(self.media_kinds),
            "streaming": self.streaming,
            "pdf_decoder_digest": PDF_DECODER_DIGEST,
            "pdf_parser_version": PDF_PYPDF_VERSION,
            "prompt_template_digest": HTTP_NORMALIZER_PROMPT_SHA256,
            "output_schema_digest": LANDING_NORMALIZATION_DRAFT_SCHEMA_SHA256,
            "tool_policy_digest": HTTP_TOOL_POLICY_DIGEST,
            "decoder_digest": self.decoder_digest,
        }

    @property
    def profile_digest(self) -> str:
        return landing_digest("http-profile", self.to_facts())


@dataclass(frozen=True)
class HttpLandingExecutionRequest:
    profile_digest: str
    input_digest: str
    payload: bytes


@dataclass(frozen=True)
class HttpLandingExecutionResult:
    stdout: bytes
    response_digest: str
    elapsed_ms: int
    usage_input_units: int
    usage_output_units: int


class HttpLandingExecutor(Protocol):
    @property
    def profile_digest(self) -> str: ...

    def run(self, request: HttpLandingExecutionRequest) -> HttpLandingExecutionResult: ...


class HttpLandingNormalizer:
    def __init__(
        self,
        profile: HttpLandingProfile,
        executor: HttpLandingExecutor,
        *,
        clock: Callable[[], datetime] | None = None,
        source_preflight: Callable[[], None] | None = None,
    ) -> None:
        if not isinstance(profile, HttpLandingProfile):
            raise LandingProviderError("http_profile_type")
        if executor.profile_digest != profile.profile_digest:
            raise LandingProviderError("http_profile_mismatch")
        self._profile = profile
        self._executor = executor
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._source_preflight = source_preflight

    @property
    def profile(self):
        return self._profile

    def normalize(
        self, request: LandingNormalizationRequest, read_blob: Callable[[], bytes]
    ) -> LandingNormalizationOutcome:
        if (
            request.profile_digest != self._profile.profile_digest
            or self._executor.profile_digest != self._profile.profile_digest
        ):
            raise LandingProviderError("http_profile_mismatch")
        started = self._now()
        request_digest = landing_digest(
            "provider-request",
            {"input_digest": request.source.input_digest,
             "profile_digest": self._profile.profile_digest},
        )
        if not self._profile.available:
            return self._terminal(
                request, "provider_unavailable", "profile_unavailable", started, request_digest
            )
        try:
            media_preflight(request.source, self._profile.media_kinds)
        except LandingMediaError as exc:
            return self._terminal(
                request, "needs_human", exc.code, started, request_digest
            )
        if self._source_preflight is not None:
            try:
                self._source_preflight()
            except (OSError, RuntimeError):
                return self._terminal(
                    request, "needs_human", "source_identity", started, request_digest
                )
        try:
            blob = read_blob()
            if (
                not isinstance(blob, bytes)
                or len(blob) != request.source.byte_length
                or hashlib.sha256(blob).hexdigest() != request.source.content_sha256
            ):
                raise LandingContractError("blob_digest_mismatch")
            PrivateLandingBlobStore._validate_shape(
                request.source.media_kind, request.source.media_type, blob
            )
            source_text = prepare_landing_media(request.source, blob)
        except LandingMediaError as exc:
            return self._terminal(request, "needs_human", exc.code, started, request_digest)
        except LandingContractError as exc:
            return self._terminal(
                request, "rejected", exc.code, started, request_digest
            )
        payload = canonical_json({
            "instruction": HTTP_NORMALIZER_PROMPT,
            "request": {
                "protocol_version": HTTP_PROTOCOL_VERSION,
                "profile_digest": self._profile.profile_digest,
                "input_digest": request.source.input_digest,
                "media_kind": request.source.media_kind,
                "source_payload": source_text,
                "source_content_sha256": request.source.content_sha256,
            },
        })
        request_digest = landing_digest("provider-request", {
            "profile_digest": self._profile.profile_digest,
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
        })
        result = None
        try:
            result = self._executor.run(HttpLandingExecutionRequest(
                self._profile.profile_digest, request.source.input_digest, payload
            ))
            self._validate_result(result)
        except (LandingProviderError, LandingContractError, OSError, ValueError) as exc:
            category = getattr(exc, "category", EXECUTOR_CODE_CATEGORIES.get(str(exc), "protocol"))
            return self._terminal(
                request, "needs_human", "http_outcome_unusable", started, request_digest,
                category=category, dispatched=True, http_status=getattr(exc, "http_status", None),
            )
        try:
            spec = decode_landing_draft(
                request.source.input_digest, result.stdout, maximum=MAX_PROVIDER_OUTPUT_BYTES
            )
        except (LandingProviderError, LandingContractError, OSError, ValueError) as exc:
            return self._terminal(
                request, "needs_human", _draft_failure_reason(exc), started, request_digest,
                category="draft", dispatched=True, result=result,
            )
        evidence = self._evidence(
            request, started, request_digest, result.response_digest,
            result.usage_input_units, result.usage_output_units, "normalized",
        )
        observation = LandingProviderObservation(
            evidence, "normalized", True, "reported", result.usage_input_units, result.usage_output_units,
        )
        return LandingNormalizationOutcome(spec, evidence, "normalized", "normalized", observation)

    def _validate_result(self, result: HttpLandingExecutionResult) -> None:
        if (
            not isinstance(result, HttpLandingExecutionResult)
            or not isinstance(result.stdout, bytes)
            or len(result.stdout) > MAX_PROVIDER_OUTPUT_BYTES
            or not isinstance(result.response_digest, str)
            or not HEX64.fullmatch(result.response_digest)
            or type(result.elapsed_ms) is not int
            or not 0 <= result.elapsed_ms <= self._profile.timeout_seconds * 1_000
        ):
            raise LandingProviderError("http_result")
        for count in (result.usage_input_units, result.usage_output_units):
            if type(count) is not int or not 0 <= count <= 10_000_000:
                raise LandingProviderError("http_usage")

    def _terminal(self, request, state, reason, started, request_digest, *,
                  category="input", dispatched=False, http_status=None, result=None):
        # Only the post-validation draft failure path supplies a completed result.
        response_digest = (result.response_digest if result is not None else
                           landing_digest("provider-response", {"state": state, "reason_code": reason}))
        evidence = self._evidence(
            request, started, request_digest, response_digest,
            0, 0, "rejected" if state == "rejected" else "provider_unavailable",
        )
        observation = LandingProviderObservation(
            evidence, category, dispatched,
            "reported" if result is not None else "unavailable" if dispatched else "not_dispatched",
            result.usage_input_units if result is not None else None if dispatched else 0,
            result.usage_output_units if result is not None else None if dispatched else 0,
            http_status,
        )
        return LandingNormalizationOutcome(None, evidence, state, reason, observation)

    def _evidence(self, request, started, request_digest, response_digest,
                  usage_input, usage_output, disposition):
        return LandingProviderEvidenceV2.from_facts({
            "schema_version": 2,
            "input_digest": request.source.input_digest,
            "profile_digest": self._profile.profile_digest,
            "provider_id": self._profile.provider_id,
            "adapter_id": self._profile.adapter_id,
            "adapter_version": self._profile.adapter_version,
            "model_id": self._profile.model_id,
            "prompt_template_digest": HTTP_NORMALIZER_PROMPT_SHA256,
            "tool_policy_digest": HTTP_TOOL_POLICY_DIGEST,
            "output_schema_digest": LANDING_NORMALIZATION_DRAFT_SCHEMA_SHA256,
            "decoder_digest": self._profile.decoder_digest,
            "request_digest": request_digest,
            "response_digest": response_digest,
            "usage_input_units": usage_input,
            "usage_output_units": usage_output,
            "started_at": started.isoformat().replace("+00:00", "Z"),
            "completed_at": self._now().isoformat().replace("+00:00", "Z"),
            "disposition": disposition,
        })

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise LandingProviderError("provider_clock")
        return value.astimezone(timezone.utc)
