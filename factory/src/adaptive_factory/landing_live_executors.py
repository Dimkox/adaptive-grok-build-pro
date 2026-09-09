"""Default-off live Grok/Qwen executors. Tests must not perform real HTTP."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

import httpx

from .landing_intake import PrivateLandingBlobStore
from .landing_normalizer import (
    CodexExecutionRequest,
    CodexExecutionResult,
    CodexLandingProfile,
)
from .landing_provider import LandingProviderError
from .landing_runtime import (
    LandingApplicationService,
    LandingJobStore,
    LandingLiveBindingV1,
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
    source = os.environ if environ is None else environ
    key = source.get(name, "").strip()
    if not key:
        raise LandingProviderError("credential_unavailable")
    return key


class OpenAICompatibleLandingExecutor:
    """Chat Completions adapter that returns assistant JSON as executor stdout."""

    def __init__(
        self,
        *,
        provider_id: str,
        base_url: str,
        model_id: str,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if provider_id not in {"grok", "qwen"}:
            raise LandingProviderError("provider_id")
        if not base_url.startswith("https://"):
            raise LandingProviderError("base_url")
        if not model_id or not api_key.strip():
            raise LandingProviderError("credential_unavailable")
        self.provider_id = provider_id
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self._api_key = api_key.strip()
        self._transport = transport

    def run(self, request: CodexExecutionRequest) -> CodexExecutionResult:
        if not isinstance(request, CodexExecutionRequest):
            raise LandingProviderError("executor_request")
        instruction, payload = _split_stdin(request.stdin)
        body = {
            "model": self.model_id,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(
                base_url=self.base_url,
                transport=self._transport,
                timeout=request.timeout_seconds,
            ) as client:
                response = client.post("/chat/completions", json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise LandingProviderError("executor_transport") from exc
        if response.status_code != 200:
            raise LandingProviderError("executor_http")
        try:
            document = response.json()
            content = document["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LandingProviderError("executor_result") from exc
        if not isinstance(content, str) or not content.strip():
            raise LandingProviderError("executor_result")
        stdout = content.encode("utf-8")
        if len(stdout) > request.max_stdout_bytes:
            raise LandingProviderError("executor_result")
        return CodexExecutionResult(
            stdout=stdout,
            stderr_digest=hashlib.sha256(b"").hexdigest(),
            exit_code=0,
            elapsed_ms=min(request.timeout_seconds * 1000, 25),
            usage_input_units=1,
            usage_output_units=1,
        )


def grok_landing_executor(
    *,
    api_key: str,
    transport: httpx.BaseTransport | None = None,
    requirements: LandingHostRequirementsV1 = CURRENT_LANDING_HOST_REQUIREMENTS,
) -> OpenAICompatibleLandingExecutor:
    return OpenAICompatibleLandingExecutor(
        provider_id="grok",
        base_url=requirements.grok_base_url,
        model_id=requirements.grok_model_id,
        api_key=api_key,
        transport=transport,
    )


def qwen_landing_executor(
    *,
    api_key: str,
    transport: httpx.BaseTransport | None = None,
    requirements: LandingHostRequirementsV1 = CURRENT_LANDING_HOST_REQUIREMENTS,
) -> OpenAICompatibleLandingExecutor:
    return OpenAICompatibleLandingExecutor(
        provider_id="qwen",
        base_url=requirements.qwen_base_url,
        model_id=requirements.qwen_model_id,
        api_key=api_key,
        transport=transport,
    )


def compose_landing_live_grok(
    *,
    api_key: str,
    binding: LandingLiveBindingV1,
    profile: CodexLandingProfile,
    source_repository: Path,
    scratch_root: Path,
    output_directory: Path,
    blobs: PrivateLandingBlobStore,
    store: LandingJobStore | None = None,
    clock: Callable[[], datetime] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> LandingApplicationService:
    from .landing_runtime import compose_landing_live

    return compose_landing_live(
        binding=binding,
        profile=profile,
        executor=grok_landing_executor(api_key=api_key, transport=transport),
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
    profile: CodexLandingProfile,
    source_repository: Path,
    scratch_root: Path,
    output_directory: Path,
    blobs: PrivateLandingBlobStore,
    store: LandingJobStore | None = None,
    clock: Callable[[], datetime] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> LandingApplicationService:
    from .landing_runtime import compose_landing_live

    return compose_landing_live(
        binding=binding,
        profile=profile,
        executor=qwen_landing_executor(api_key=api_key, transport=transport),
        source_repository=source_repository,
        scratch_root=scratch_root,
        output_directory=output_directory,
        blobs=blobs,
        store=store,
        clock=clock,
    )


def _split_stdin(stdin: bytes) -> tuple[str, dict[str, Any]]:
    try:
        document = json.loads(stdin.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LandingProviderError("executor_request") from exc
    if not isinstance(document, dict):
        raise LandingProviderError("executor_request")
    instruction = document.get("instruction")
    payload = document.get("request")
    if not isinstance(instruction, str) or not isinstance(payload, dict):
        raise LandingProviderError("executor_request")
    return instruction, payload
