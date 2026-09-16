"""Default-off live Grok/Qwen executors. Tests must not perform real HTTP."""

from __future__ import annotations

import asyncio
import argparse
import base64
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
import hashlib
import os
from pathlib import Path
import re
import time
from typing import Mapping

import httpx

from .landing_intake import PrivateLandingBlobStore
from .contracts import HEX64, canonical_json
from .landing_contracts import LandingContractError, strict_json_object
from .landing_http import (
    HTTP_NORMALIZER_PROMPT,
    HTTP_PROTOCOL_VERSION,
    MAX_HTTP_REQUEST_BYTES,
    HttpLandingExecutionRequest,
    HttpLandingExecutionResult,
    HttpLandingNormalizer,
    HttpLandingProfile,
)
from .landing_normalizer import MAX_NORMALIZED_TEXT_BYTES, decode_landing_draft
from .landing_media import MAX_AUDIO_BASE64_BYTES, MAX_IMAGE_BYTES
from .landing_provider import (
    EXECUTOR_CODE_CATEGORIES,
    FAILURE_CATEGORIES,
    LandingProviderError,
    HttpProviderFailure,
    MAX_PROVIDER_OUTPUT_BYTES,
)
from .landing_runtime import (
    LandingApplicationService,
    LandingJobStore,
    LandingLiveBindingV1,
    create_landing_artifact_builder,
)
from .settings import SettingsError, read_private_file


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
LANDING_PROVIDER_ENV = "FACTORY_LANDING_PROVIDER"
LANDING_SOURCE_ENV = "FACTORY_LANDING_SOURCE_PATH"
LANDING_SCRATCH_ENV = "FACTORY_LANDING_SCRATCH_PATH"
LANDING_OUTPUT_ENV = "FACTORY_LANDING_OUTPUT_PATH"
PROVIDER_KEY_NAMES = {
    "qwen": QWEN_API_KEY_ENV, "grok": GROK_API_KEY_ENV,
    "openai": "FACTORY_LANDING_OPENAI_API_KEY", "anthropic": "FACTORY_LANDING_ANTHROPIC_API_KEY",
    "openrouter": "FACTORY_LANDING_OPENROUTER_API_KEY",
}


def _http_failure(status: int, body: bytes) -> HttpProviderFailure:
    category = {401: "authentication", 403: "permission", 429: "rate_limit"}.get(
        status, "unavailable" if 500 <= status <= 599 else "protocol",
    )
    try:
        document = strict_json_object(body, maximum=16_384)
        error = document.get("error", {})
        markers = (error.get("code"), error.get("type")) if isinstance(error, dict) else ()
        if any(isinstance(code, str) and code in {
            "content_policy_violation", "content_filter", "data_inspection_failed",
            "safety_violation", "moderation_blocked", "refusal",
            "unsupported_country_region_territory",
        } for code in markers):
            category = "policy"
    except (LandingContractError, ValueError, TypeError):
        # An unreadable body cannot establish absence of a policy denial.
        category = "protocol"
    return HttpProviderFailure("executor_http", category, status)


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
    if name not in PROVIDER_KEY_NAMES.values():
        raise LandingProviderError("credential_name")
    source = os.environ if environ is None else environ
    key = source.get(name, "").strip()
    if not key:
        raise LandingProviderError("credential_unavailable")
    return key


def provider_api_key(provider_id: str, *, env_file: Path | None = None, environ=None) -> str:
    """Select one named assignment as data; never source or print the file."""
    if provider_id not in PROVIDER_KEY_NAMES:
        raise LandingProviderError("credential_name")
    name = PROVIDER_KEY_NAMES[provider_id]
    if env_file is None:
        return qwen_api_key(environ=environ) if provider_id == "qwen" else api_key_from_environ(name, environ)
    if env_file.anchor == "//":
        raise LandingProviderError("credential_file_invalid")
    raw = read_private_file(env_file, 65_536)
    try:
        values = []
        for line in raw.decode("utf-8").splitlines():
            line = line.strip()
            if not re.match(r"^(?:export\s+)?" + re.escape(name) + r"\b", line):
                continue
            match = re.fullmatch(r"(?:export[ \t]+)?" + re.escape(name) + r"[ \t]*=[ \t]*(.*)", line)
            if match is None:
                raise ValueError
            value = match.group(1).strip()
            if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
                value = value[1:-1]
            if re.fullmatch(r"[A-Za-z0-9._-]{1,4096}", value) is None:
                raise ValueError
            values.append(value)
        if len(values) != 1:
            raise ValueError
        return values[0]
    except (UnicodeError, ValueError):
        raise LandingProviderError("credential_file_invalid") from None


def qwen_api_key(*, env_file: Path | None = None, environ: Mapping[str, str] | None = None) -> str:
    """Read one explicit private assignment as data, without sourcing shell code."""
    if env_file is None:
        source = os.environ if environ is None else environ
        if QWEN_API_KEY_ENV in source:
            return api_key_from_environ(QWEN_API_KEY_ENV, source)
        return api_key_from_environ(QWEN_API_KEY_ENV, {QWEN_API_KEY_ENV: source.get("DASHSCOPE_API_KEY", "")})
    if env_file.anchor == "//":
        raise SettingsError("credential file path must be absolute and normalized")
    raw = read_private_file(env_file, 16_384)
    try:
        text = raw.decode("utf-8")
        values = []
        for line in text.splitlines():
            line = line.strip()
            if not re.match(r"^(?:export\s+)?DASHSCOPE_API_KEY\b", line):
                continue
            match = re.fullmatch(r"(?:export[ \t]+)?DASHSCOPE_API_KEY[ \t]*=[ \t]*(.*)", line)
            if match is None:
                raise ValueError
            value = match.group(1).strip()
            if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
                value = value[1:-1]
            if re.fullmatch(r"[A-Za-z0-9._-]{1,4096}", value) is None:
                raise ValueError
            values.append(value)
        if len(values) != 1:
            raise ValueError
        return values[0]
    except (UnicodeError, ValueError):
        raise LandingProviderError("credential_file_invalid") from None


class OpenAICompatibleLandingExecutor:
    """One bounded request to an explicitly pinned provider, with no retry."""

    endpoint_path = "chat/completions"

    def __init__(
        self,
        *,
        provider_id: str,
        base_url: str,
        model_id: str,
        api_key: str,
        transport: httpx.AsyncBaseTransport | None = None,
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

    def _request_body(self, instruction, payload):
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
        if self._profile.profile_id == "qwen-intl":
            body["enable_thinking"] = False
        return body

    def _request_headers(self):
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if self._profile.streaming else "application/json",
            "Accept-Encoding": "identity",
        }

    def run(self, request: HttpLandingExecutionRequest) -> HttpLandingExecutionResult:
        if not self._profile.available:
            raise LandingProviderError("profile_unavailable")
        instruction, payload = self._request_payload(request)
        encoded = canonical_json(self._request_body(instruction, payload))
        if len(encoded) > MAX_HTTP_REQUEST_BYTES:
            raise LandingProviderError("executor_request_size")
        headers = self._request_headers()
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
        response_status = None
        try:
            async with asyncio.timeout(self._remaining(deadline)), httpx.AsyncClient(
                transport=self._transport,
                timeout=httpx.Timeout(self._profile.timeout_seconds),
                trust_env=False,
                follow_redirects=False,
            ) as client:
                self._remaining(deadline)
                async with client.stream(
                    "POST", f"{self.base_url}/{self.endpoint_path}",
                    content=encoded, headers=headers,
                    timeout=self._remaining(deadline),
                ) as response:
                    response_status = response.status_code
                    self._remaining(deadline)
                    if response.status_code != 200:
                        error_body = bytearray()
                        async for chunk in response.aiter_raw():
                            self._remaining(deadline)
                            if len(error_body) + len(chunk) > 16_384:
                                raise HttpProviderFailure("executor_http", "protocol", response.status_code)
                            error_body.extend(chunk)
                        raise _http_failure(response.status_code, bytes(error_body))
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
            if response_status is not None and response_status != 200:
                raise HttpProviderFailure("executor_http", "protocol", response_status) from None
            raise LandingProviderError("executor_deadline") from None
        except (httpx.HTTPError, OSError):
            if response_status is not None and response_status != 200:
                raise HttpProviderFailure("executor_http", "protocol", response_status) from None
            raise LandingProviderError("executor_transport") from None
        except LandingProviderError as exc:
            if response_status is not None and response_status != 200 and not isinstance(exc, HttpProviderFailure):
                raise HttpProviderFailure("executor_http", "protocol", response_status) from None
            raise
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
            if any(type(value) is not int or not 0 <= value <= 10_000_000 for value in counts):
                raise LandingProviderError("executor_usage")
            usage_input, usage_output, total = counts
            if self.provider_id == "grok":
                details = usage.get("completion_tokens_details")
                reasoning = 0
                if details is not None:
                    if not isinstance(details, dict):
                        raise LandingProviderError("executor_usage")
                    reasoning = details.get("reasoning_tokens", 0)
                    if type(reasoning) is not int or not 0 <= reasoning <= 10_000_000:
                        raise LandingProviderError("executor_usage")
                if usage_input + usage_output + reasoning == total:
                    usage_output += reasoning
                elif usage_input + usage_output != total or reasoning > usage_output:
                    raise LandingProviderError("executor_usage")
            elif usage_input + usage_output != total:
                raise LandingProviderError("executor_usage")
            # This post-response acceptance limit includes Grok reasoning; it cannot
            # prevent provider charges already incurred beyond the visible wire cap.
            if usage_output > self._profile.max_output_tokens:
                raise LandingProviderError("executor_usage")
        except (KeyError, TypeError, ValueError, LandingContractError):
            raise LandingProviderError("executor_result") from None
        try:
            stdout = content.encode("utf-8")
        except UnicodeEncodeError:
            raise LandingProviderError("executor_result") from None
        if len(stdout) > MAX_PROVIDER_OUTPUT_BYTES:
            raise LandingProviderError("executor_result")
        return HttpLandingExecutionResult(
            stdout=stdout,
            response_digest=hashlib.sha256(raw).hexdigest(),
            elapsed_ms=int((self._monotonic() - started) * 1_000),
            usage_input_units=usage_input,
            usage_output_units=usage_output,
        )


def grok_landing_executor(
    *,
    api_key: str,
    transport: httpx.AsyncBaseTransport | None = None,
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
    transport: httpx.AsyncBaseTransport | None = None,
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
    transport: httpx.AsyncBaseTransport | None = None,
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
    transport: httpx.AsyncBaseTransport | None = None,
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


def compose_landing_live_provider(*, api_key, profile, transport=None, **kwargs):
    from .landing_extra_providers import landing_provider_executor

    return _compose_http_landing(profile=profile, executor=landing_provider_executor(
        profile, api_key=api_key, transport=transport,
    ), **kwargs)


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
def _absolute_env_path(environ: Mapping[str, str], name: str) -> Path:
    raw = environ.get(name, "").strip()
    if not raw:
        raise LandingProviderError("landing_path")
    path = Path(raw)
    if not path.is_absolute() or ".." in path.parts:
        raise LandingProviderError("landing_path")
    return path


def compose_env_landing(
    blobs: PrivateLandingBlobStore,
    *,
    profile: HttpLandingProfile | None = None,
    environ: Mapping[str, str] | None = None,
    store: LandingJobStore | None = None,
    clock: Callable[[], datetime] | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> LandingApplicationService | None:
    """Compose live Grok/Qwen landing when FACTORY_LANDING_PROVIDER is set.

    Unset provider returns None so the caller keeps the unavailable default.
    Does not read files named .env; only the provided mapping or process env.
    """
    source_env = os.environ if environ is None else environ
    provider = source_env.get(LANDING_PROVIDER_ENV, "").strip()
    if not provider:
        return None
    if provider not in {"grok", "qwen", "qwen-intl", "qwen-omni", "qwen-omni-intl"}:
        raise LandingProviderError("landing_provider")
    if profile is None:
        profile = HttpLandingProfile.for_provider(provider, available=True)
    elif not isinstance(profile, HttpLandingProfile) or profile.profile_id != provider:
        raise LandingProviderError("http_profile_identity")
    key_name = GROK_API_KEY_ENV if provider == "grok" else QWEN_API_KEY_ENV
    api_key = api_key_from_environ(key_name, source_env) if provider == "grok" else qwen_api_key(environ=source_env)
    from .landing_runtime import implemented_live_binding

    composer = compose_landing_live_grok if provider == "grok" else compose_landing_live_qwen
    return composer(
        api_key=api_key,
        binding=implemented_live_binding(enabled=True),
        profile=profile,
        source_repository=_absolute_env_path(source_env, LANDING_SOURCE_ENV),
        scratch_root=_absolute_env_path(source_env, LANDING_SCRATCH_ENV),
        output_directory=_absolute_env_path(source_env, LANDING_OUTPUT_ENV),
        blobs=blobs,
        store=store,
        clock=clock,
        transport=transport,
    )


# One tuple feeds both the CLI parser and probe_qwen, so the accepted set cannot drift in one of them.
PROBE_PROFILES = ("qwen", "qwen-intl", "qwen-omni", "qwen-omni-intl")


def _probe_failure_fields(exc: LandingProviderError) -> dict[str, object]:
    """Bounded classification for operator output; never includes an upstream body."""

    category = getattr(exc, "category", None)
    if not isinstance(category, str) or category not in FAILURE_CATEGORIES:
        category = EXECUTOR_CODE_CATEGORIES.get(str(exc), "protocol")
    status = getattr(exc, "http_status", None)
    if status is not None and (type(status) is not int or not 100 <= status <= 599):
        status = None
    return {"category": category, "http_status": status}


def probe_qwen(*, profile_id: str = "qwen-intl", qwen_env_file: Path | None = None,
               transport: httpx.AsyncBaseTransport | None = None) -> dict[str, object]:
    """One synthetic normalization request; never reads project or customer inputs."""
    if profile_id not in PROBE_PROFILES:
        raise LandingProviderError("http_profile_identity")
    profile = HttpLandingProfile.for_provider(profile_id, available=True)
    executor = qwen_landing_executor(
        api_key=qwen_api_key(env_file=qwen_env_file), profile=profile, transport=transport,
    )
    brief = "Create an English landing page for a fictional local gardening club. One hero section. No links, prices, contacts or factual claims."
    input_digest = hashlib.sha256(brief.encode()).hexdigest()
    payload = canonical_json({"instruction": HTTP_NORMALIZER_PROMPT, "request": {
        "protocol_version": HTTP_PROTOCOL_VERSION, "profile_digest": profile.profile_digest,
        "input_digest": input_digest, "media_kind": "text", "source_payload": brief,
        "source_content_sha256": input_digest,
    }})
    result = executor.run(HttpLandingExecutionRequest(profile.profile_digest, input_digest, payload))
    spec = decode_landing_draft(input_digest, result.stdout, maximum=MAX_PROVIDER_OUTPUT_BYTES)
    return {
        "state": "normalized", "profile_id": profile.profile_id, "model_id": profile.model_id,
        "profile_digest": profile.profile_digest, "input_digest": input_digest,
        "spec_digest": spec.spec_digest, "response_digest": result.response_digest,
        "usage_input_units": result.usage_input_units, "usage_output_units": result.usage_output_units,
        "elapsed_ms": result.elapsed_ms,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="One synthetic Qwen landing normalization probe")
    parser.add_argument("--profile", choices=PROBE_PROFILES, default="qwen-intl")
    parser.add_argument("--qwen-env-file", type=Path)
    args = parser.parse_args()
    try:
        result = probe_qwen(profile_id=args.profile, qwen_env_file=args.qwen_env_file)
    except LandingProviderError as exc:
        # Dependency exceptions and provider bodies can contain credentials or
        # untrusted text, so the operator output stays closed: only the allowlisted
        # classification the executor already computed may leave the process.
        print(canonical_json({"state": "failed", "reason": "qwen_probe_failed",
                              **_probe_failure_fields(exc)}).decode())
        return 1
    except (LandingContractError, SettingsError, OSError):
        print(canonical_json({"state": "failed", "reason": "qwen_probe_failed",
                              "category": "protocol", "http_status": None}).decode())
        return 1
    print(canonical_json(result).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
