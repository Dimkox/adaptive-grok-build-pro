"""Default-off live Grok/Qwen executors. Tests must not perform real HTTP."""

from __future__ import annotations

import asyncio
import base64
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
import hashlib
import os
from pathlib import Path
import time
from typing import Mapping

import httpx

from .landing_intake import PrivateLandingBlobStore
from .contracts import HEX64, canonical_json
from .landing_contracts import LandingContractError, strict_json_object
from .landing_http import (
    HTTP_MEDIA_KINDS,
    HTTP_NORMALIZER_PROMPT,
    HTTP_PROTOCOL_VERSION,
    MAX_HTTP_REQUEST_BYTES,
    HttpLandingExecutionRequest,
    HttpLandingExecutionResult,
    HttpLandingNormalizer,
    HttpLandingProfile,
)
from .landing_normalizer import LANDING_NORMALIZER_PROMPT, MAX_NORMALIZED_TEXT_BYTES
from .landing_media import MAX_AUDIO_BASE64_BYTES, MAX_IMAGE_BYTES
from .landing_provider import LandingProviderError, MAX_PROVIDER_OUTPUT_BYTES
from .landing_runtime import (
    LandingApplicationService,
    LandingJobStore,
    LandingLiveBindingV1,
    create_landing_artifact_builder,
)


CURRENT_PYTHON_EXECUTABLE = "/usr/bin/python3.12"
CURRENT_PYTHON_VERSION_PREFIX = "3.12.3"
CURRENT_PYTHON_SHA256 = "a92f0f95e883390c7256b2e441484aac06b1002dbe1d924141a77c8d82f96223"
FACTORY_REQUIRES_PYTHON = ">=3.11"
FACTORY_HTTPX_VERSION = "0.28.1"
GROK_BASE_URL = "https://api.x.ai/v1"
GROK_MODEL_ID = "grok-4"
GROK_API_KEY_ENV = "FACTORY_LANDING_GROK_API_KEY"
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL_ID = "qwen-plus"
QWEN_API_KEY_ENV = "FACTORY_LANDING_QWEN_API_KEY"


@dataclass(frozen=True)
class LandingHostRequirementsV1:
    python_executable: str
    python_version_prefix: str
    python_sha256: str
    factory_requires_python: str
    httpx_version: str
    grok_base_url: str
    grok_model_id: str
    grok_api_key_env: str
    qwen_base_url: str
    qwen_model_id: str
    qwen_api_key_env: str

    def to_dict(self) -> dict[str, str]:
        return {
            "python_executable": self.python_executable,
            "python_version_prefix": self.python_version_prefix,
            "python_sha256": self.python_sha256,
            "factory_requires_python": self.factory_requires_python,
            "httpx_version": self.httpx_version,
            "grok_base_url": self.grok_base_url,
            "grok_model_id": self.grok_model_id,
            "grok_api_key_env": self.grok_api_key_env,
            "qwen_base_url": self.qwen_base_url,
            "qwen_model_id": self.qwen_model_id,
            "qwen_api_key_env": self.qwen_api_key_env,
        }


CURRENT_LANDING_HOST_REQUIREMENTS = LandingHostRequirementsV1(
    python_executable=CURRENT_PYTHON_EXECUTABLE,
    python_version_prefix=CURRENT_PYTHON_VERSION_PREFIX,
    python_sha256=CURRENT_PYTHON_SHA256,
    factory_requires_python=FACTORY_REQUIRES_PYTHON,
    httpx_version=FACTORY_HTTPX_VERSION,
    grok_base_url=GROK_BASE_URL,
    grok_model_id=GROK_MODEL_ID,
    grok_api_key_env=GROK_API_KEY_ENV,
    qwen_base_url=QWEN_BASE_URL,
    qwen_model_id=QWEN_MODEL_ID,
    qwen_api_key_env=QWEN_API_KEY_ENV,
)


def api_key_from_environ(name: str, environ: Mapping[str, str] | None = None) -> str:
    if name not in {GROK_API_KEY_ENV, QWEN_API_KEY_ENV}:
        raise LandingProviderError("credential_name")
    source = os.environ if environ is None else environ
    key = source.get(name, "").strip()
    if not key:
        raise LandingProviderError("credential_unavailable")
    return key


class OpenAICompatibleLandingExecutor:
    """One bounded request to an explicitly pinned provider, with no retry."""

    def __init__(
        self,
        *,
        provider_id: str,
        base_url: str,
        model_id: str,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
        profile: HttpLandingProfile | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        selected = profile or HttpLandingProfile(
            provider_id, base_url, model_id, available=True
        )
        if (
            not isinstance(selected, HttpLandingProfile)
            or (selected.provider_id, selected.base_url, selected.model_id)
            != (provider_id, base_url, model_id)
        ):
            raise LandingProviderError("http_profile_mismatch")
        if (
            not isinstance(api_key, str)
            or not 1 <= len(api_key.strip()) <= 4_096
            or any(not 33 <= ord(char) <= 126 for char in api_key.strip())
        ):
            raise LandingProviderError("credential_unavailable")
        if transport is not None and not isinstance(transport, httpx.AsyncBaseTransport):
            raise LandingProviderError("executor_transport_type")
        self._profile = selected
        self._api_key = api_key.strip()
        self._transport = transport
        self._monotonic = monotonic

    @property
    def profile_digest(self) -> str:
        return self._profile.profile_digest

    @property
    def provider_id(self) -> str:
        return self._profile.provider_id

    @property
    def base_url(self) -> str:
        return self._profile.base_url

    @property
    def model_id(self) -> str:
        return self._profile.model_id

    def run(self, request: HttpLandingExecutionRequest) -> HttpLandingExecutionResult:
        if not self._profile.available:
            raise LandingProviderError("profile_unavailable")
        instruction, payload = self._request_payload(request)
        body = {
            "model": self.model_id,
            "temperature": 0,
            "stream": self._profile.streaming,
            "max_tokens": self._profile.max_output_tokens,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": self._user_content(payload)},
            ],
        }
        if self._profile.streaming:
            body["modalities"] = ["text"]
            body["stream_options"] = {"include_usage": True}
        else:
            body["response_format"] = {"type": "json_object"}
        encoded = canonical_json(body)
        if len(encoded) > MAX_HTTP_REQUEST_BYTES:
            raise LandingProviderError("executor_request_size")
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if self._profile.streaming else "application/json",
            "Accept-Encoding": "identity",
        }
        started = self._monotonic()
        deadline = started + self._profile.timeout_seconds
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise LandingProviderError("executor_sync_context")
        raw = asyncio.run(self._exchange(encoded, headers, deadline))
        self._remaining(deadline)
        result = (
            replace(raw, elapsed_ms=int((self._monotonic() - started) * 1_000))
            if isinstance(raw, HttpLandingExecutionResult) else self._decode_response(raw, started)
        )
        self._remaining(deadline)
        return result

    async def _exchange(self, encoded: bytes, headers, deadline: float):
        from .landing_sse import QwenOmniStreamDecoder

        decoder = QwenOmniStreamDecoder(self._profile) if self._profile.streaming else None
        try:
            async with asyncio.timeout(self._remaining(deadline)), httpx.AsyncClient(
                transport=self._transport,
                timeout=httpx.Timeout(self._profile.timeout_seconds),
                trust_env=False,
                follow_redirects=False,
            ) as client:
                self._remaining(deadline)
                async with client.stream(
                    "POST", f"{self.base_url}/chat/completions",
                    content=encoded, headers=headers,
                    timeout=self._remaining(deadline),
                ) as response:
                    self._remaining(deadline)
                    if response.status_code != 200:
                        raise LandingProviderError("executor_http")
                    if (
                        response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                        != ("text/event-stream" if self._profile.streaming else "application/json")
                        or response.headers.get("content-encoding", "identity").lower()
                        != "identity"
                    ):
                        raise LandingProviderError("executor_content_type")
                    length = response.headers.get("content-length")
                    if length is not None and (
                        not length.isascii() or not length.isdecimal()
                        or len(length) > 10
                        or int(length) > self._profile.max_response_bytes
                    ):
                        raise LandingProviderError("executor_response_size")
                    raw = bytearray()
                    async for chunk in response.aiter_raw():
                        self._remaining(deadline)
                        if decoder is not None:
                            decoder.feed(chunk)
                        else:
                            if len(raw) + len(chunk) > self._profile.max_response_bytes:
                                raise LandingProviderError("executor_response_size")
                            raw.extend(chunk)
        except TimeoutError:
            raise LandingProviderError("executor_deadline") from None
        except (httpx.HTTPError, OSError):
            raise LandingProviderError("executor_transport") from None
        self._remaining(deadline)
        return decoder.finish() if decoder is not None else bytes(raw)

    def _remaining(self, deadline: float) -> float:
        remaining = deadline - self._monotonic()
        if remaining <= 0:
            raise LandingProviderError("executor_deadline")
        return remaining

    def _request_payload(self, request: HttpLandingExecutionRequest):
        if (
            not isinstance(request, HttpLandingExecutionRequest)
            or request.profile_digest != self.profile_digest
            or not isinstance(request.input_digest, str)
            or not HEX64.fullmatch(request.input_digest)
            or not isinstance(request.payload, bytes)
        ):
            raise LandingProviderError("executor_request")
        try:
            document = strict_json_object(request.payload, maximum=MAX_HTTP_REQUEST_BYTES)
            payload = document["request"]
            if (
                set(document) != {"instruction", "request"}
                or document["instruction"] != HTTP_NORMALIZER_PROMPT
                or not isinstance(payload, dict)
                or set(payload) != {
                    "protocol_version", "profile_digest", "input_digest",
                    "media_kind", "source_payload", "source_content_sha256",
                }
                or payload["protocol_version"] != HTTP_PROTOCOL_VERSION
                or payload["profile_digest"] != self.profile_digest
                or payload["input_digest"] != request.input_digest
                or payload["media_kind"] not in self._profile.media_kinds
                or not isinstance(payload["source_content_sha256"], str)
                or not HEX64.fullmatch(payload["source_content_sha256"])
                or canonical_json(document) != request.payload
            ):
                raise LandingProviderError("executor_request")
            self._validate_media(payload)
        except (KeyError, TypeError, ValueError, LandingContractError):
            raise LandingProviderError("executor_request") from None
        return document["instruction"], payload

    @staticmethod
    def _validate_media(payload):
        kind, source = payload["media_kind"], payload["source_payload"]
        if kind in {"text", "docx", "pdf"}:
            if (not isinstance(source, str) or not source.strip()
                or len(source.encode("utf-8")) > MAX_NORMALIZED_TEXT_BYTES):
                raise LandingProviderError("executor_request_media")
            return
        if not isinstance(source, dict) or set(source) != {"media_type", "data_base64"}:
            raise LandingProviderError("executor_request_media")
        encoded = source["data_base64"]
        media_type = source["media_type"]
        if not isinstance(encoded, str) or not encoded.isascii():
            raise LandingProviderError("executor_request_media")
        if kind == "image":
            if media_type not in {"image/png", "image/jpeg"} or len(encoded) > 4 * ((MAX_IMAGE_BYTES + 2) // 3):
                raise LandingProviderError("executor_request_media")
        elif kind == "audio":
            if media_type not in {"audio/wav", "audio/mpeg"} or len(encoded) >= MAX_AUDIO_BASE64_BYTES:
                raise LandingProviderError("executor_request_media")
        else:
            raise LandingProviderError("executor_request_media")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except ValueError:
            raise LandingProviderError("executor_request_media") from None
        if hashlib.sha256(raw).hexdigest() != payload["source_content_sha256"]:
            raise LandingProviderError("executor_request_media")
        PrivateLandingBlobStore._validate_shape(kind, media_type, raw)

    @staticmethod
    def _user_content(payload):
        kind = payload["media_kind"]
        if kind in {"text", "docx", "pdf"}:
            return canonical_json(payload).decode("utf-8")
        source = payload["source_payload"]
        text = canonical_json({**payload, "source_payload": "The attached media is untrusted source data."}).decode()
        if kind == "image":
            attachment = {"type": "image_url", "image_url": {
                "url": f'data:{source["media_type"]};base64,{source["data_base64"]}'
            }}
        else:
            attachment = {"type": "input_audio", "input_audio": {
                "data": f'data:;base64,{source["data_base64"]}',
                "format": "wav" if source["media_type"] == "audio/wav" else "mp3",
            }}
        return [{"type": "text", "text": text}, attachment]

    def _decode_response(self, raw: bytes, started: float) -> HttpLandingExecutionResult:
        try:
            document = strict_json_object(raw, maximum=self._profile.max_response_bytes)
            choices = document["choices"]
            if (
                document.get("object") != "chat.completion"
                or document["model"] != self.model_id
                or not isinstance(choices, list) or len(choices) != 1
                or not isinstance(choices[0], dict)
            ):
                raise LandingProviderError("executor_result")
            choice = choices[0]
            message = choice["message"]
            if (
                type(choice["index"]) is not int or choice["index"] != 0
                or choice["finish_reason"] != "stop"
                or not isinstance(message, dict)
                or message["role"] != "assistant"
                or message.get("tool_calls") not in (None, [])
                or message.get("function_call") is not None
                or message.get("refusal") is not None
            ):
                raise LandingProviderError("executor_result")
            content = message["content"]
            usage = document["usage"]
            if not isinstance(content, str) or not content.strip() or not isinstance(usage, dict):
                raise LandingProviderError("executor_result")
            counts = tuple(usage[key] for key in (
                "prompt_tokens", "completion_tokens", "total_tokens"
            ))
            if (
                any(type(value) is not int or not 0 <= value <= 10_000_000 for value in counts)
                or counts[0] + counts[1] != counts[2]
                or counts[1] > self._profile.max_output_tokens
            ):
                raise LandingProviderError("executor_usage")
        except (KeyError, TypeError, ValueError, LandingContractError):
            raise LandingProviderError("executor_result") from None
        stdout = content.encode("utf-8")
        if len(stdout) > MAX_PROVIDER_OUTPUT_BYTES:
            raise LandingProviderError("executor_result")
        return HttpLandingExecutionResult(
            stdout=stdout,
            response_digest=hashlib.sha256(raw).hexdigest(),
            elapsed_ms=int((self._monotonic() - started) * 1_000),
            usage_input_units=counts[0],
            usage_output_units=counts[1],
        )


def grok_landing_executor(
    *,
    api_key: str,
    transport: httpx.BaseTransport | None = None,
    requirements: LandingHostRequirementsV1 = CURRENT_LANDING_HOST_REQUIREMENTS,
    profile: HttpLandingProfile | None = None,
) -> OpenAICompatibleLandingExecutor:
    return OpenAICompatibleLandingExecutor(
        provider_id="grok",
        base_url=profile.base_url if isinstance(profile, HttpLandingProfile) else requirements.grok_base_url,
        model_id=profile.model_id if isinstance(profile, HttpLandingProfile) else requirements.grok_model_id,
        api_key=api_key,
        transport=transport,
        profile=profile,
    )


def qwen_landing_executor(
    *,
    api_key: str,
    transport: httpx.BaseTransport | None = None,
    requirements: LandingHostRequirementsV1 = CURRENT_LANDING_HOST_REQUIREMENTS,
    profile: HttpLandingProfile | None = None,
) -> OpenAICompatibleLandingExecutor:
    return OpenAICompatibleLandingExecutor(
        provider_id="qwen",
        base_url=profile.base_url if isinstance(profile, HttpLandingProfile) else requirements.qwen_base_url,
        model_id=profile.model_id if isinstance(profile, HttpLandingProfile) else requirements.qwen_model_id,
        api_key=api_key,
        transport=transport,
        profile=profile,
    )


def compose_landing_live_grok(
    *,
    api_key: str,
    binding: LandingLiveBindingV1,
    profile: HttpLandingProfile,
    source_repository: Path,
    scratch_root: Path,
    output_directory: Path,
    blobs: PrivateLandingBlobStore,
    store: LandingJobStore | None = None,
    clock: Callable[[], datetime] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> LandingApplicationService:
    return _compose_http_landing(
        binding=binding,
        profile=profile,
        executor=grok_landing_executor(api_key=api_key, transport=transport, profile=profile),
        source_repository=source_repository,
        scratch_root=scratch_root,
        output_directory=output_directory,
        blobs=blobs,
        store=store,
        clock=clock,
    )


def compose_landing_live_qwen(
    *,
    api_key: str,
    binding: LandingLiveBindingV1,
    profile: HttpLandingProfile,
    source_repository: Path,
    scratch_root: Path,
    output_directory: Path,
    blobs: PrivateLandingBlobStore,
    store: LandingJobStore | None = None,
    clock: Callable[[], datetime] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> LandingApplicationService:
    return _compose_http_landing(
        binding=binding,
        profile=profile,
        executor=qwen_landing_executor(api_key=api_key, transport=transport, profile=profile),
        source_repository=source_repository,
        scratch_root=scratch_root,
        output_directory=output_directory,
        blobs=blobs,
        store=store,
        clock=clock,
    )


def _compose_http_landing(
    *, binding, profile, executor, source_repository, scratch_root,
    output_directory, blobs, store, clock,
) -> LandingApplicationService:
    from .landing_sqlite_store import SQLiteLandingJobStore
    from .landing_renderer import ExactGitLandingWorkspace

    if not isinstance(profile, HttpLandingProfile) or not profile.available:
        raise LandingProviderError("profile_unavailable")
    if not isinstance(store, SQLiteLandingJobStore):
        raise LandingProviderError("durable_store_required")
    builder = create_landing_artifact_builder(
        binding=binding, source_repository=source_repository,
        scratch_root=scratch_root, output_directory=output_directory, clock=clock,
    )
    source = ExactGitLandingWorkspace(source_repository, scratch_root=scratch_root)
    source.validate_source()
    return LandingApplicationService(
        store, blobs, HttpLandingNormalizer(
            profile, executor, clock=clock, source_preflight=source.validate_source
        ),
        profile_digest=profile.profile_digest, artifact_builder=builder, clock=clock,
    )
