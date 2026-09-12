"""Bounded Qwen Omni text-only SSE decoder; reasoning/audio are never retained."""

from __future__ import annotations

import hashlib

from .landing_contracts import strict_json_object
from .landing_http import HttpLandingExecutionResult
from .landing_provider import LandingProviderError, MAX_PROVIDER_OUTPUT_BYTES


class QwenOmniStreamDecoder:
    def __init__(self, profile):
        self._profile = profile
        self._received = 0
        self._hash = hashlib.sha256()
        self._pending = bytearray()
        self._data = []
        self._content = bytearray()
        self._identity = None
        self._stop = False
        self._usage = None
        self._done = False
        self._events = 0

    def feed(self, raw: bytes):
        self._received += len(raw)
        if self._received > self._profile.max_response_bytes:
            raise LandingProviderError("executor_response_size")
        self._hash.update(raw)
        self._pending.extend(raw)
        while b"\n" in self._pending:
            line, _separator, rest = self._pending.partition(b"\n")
            self._pending = bytearray(rest)
            self._line(bytes(line).removesuffix(b"\r"))
        if len(self._pending) > 524_288:
            raise LandingProviderError("executor_sse_line_size")

    def _line(self, line: bytes):
        if len(line) > 524_288:
            raise LandingProviderError("executor_sse_line_size")
        if not line:
            if self._data:
                self._event(b"\n".join(self._data))
                self._data.clear()
            return
        if self._done:
            raise LandingProviderError("executor_sse_after_done")
        if line.startswith(b":"):
            return
        if not line.startswith(b"data:"):
            raise LandingProviderError("executor_sse_field")
        self._data.append(line[5:].removeprefix(b" "))
        if sum(map(len, self._data)) > 524_288:
            raise LandingProviderError("executor_sse_event_size")

    def _event(self, raw: bytes):
        self._events += 1
        if self._events > 16_384:
            raise LandingProviderError("executor_sse_event_limit")
        if raw == b"[DONE]":
            if not self._stop or self._usage is None:
                raise LandingProviderError("executor_sse_incomplete")
            self._done = True
            return
        document = strict_json_object(raw, maximum=524_288)
        identity = document.get("id")
        if (
            not isinstance(identity, str) or not 1 <= len(identity) <= 128
            or document.get("object") != "chat.completion.chunk"
            or document.get("model") != self._profile.model_id
            or (self._identity is not None and self._identity != identity)
        ):
            raise LandingProviderError("executor_sse_identity")
        self._identity = identity
        choices = document.get("choices")
        if choices == []:
            if not self._stop or self._usage is not None:
                raise LandingProviderError("executor_sse_usage_order")
            usage = document.get("usage")
            if not isinstance(usage, dict):
                raise LandingProviderError("executor_usage")
            counts = tuple(usage.get(key) for key in ("prompt_tokens", "completion_tokens", "total_tokens"))
            if (
                any(type(count) is not int or not 0 <= count <= 10_000_000 for count in counts)
                or counts[0] + counts[1] != counts[2]
                or counts[1] > self._profile.max_output_tokens
            ):
                raise LandingProviderError("executor_usage")
            self._usage = counts
            return
        if self._stop or document.get("usage") is not None:
            raise LandingProviderError("executor_sse_choice_order")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise LandingProviderError("executor_sse_choice")
        choice = choices[0]
        delta = choice.get("delta")
        if (
            type(choice.get("index")) is not int or choice["index"] != 0
            or choice.get("finish_reason") not in {None, "stop"}
            or not isinstance(delta, dict) or delta.get("role") not in {None, "assistant"}
            or delta.get("tool_calls") not in (None, []) or delta.get("function_call") is not None
            or delta.get("audio") is not None or delta.get("refusal") is not None
        ):
            raise LandingProviderError("executor_sse_delta")
        content = delta.get("content")
        if content is not None:
            if not isinstance(content, str):
                raise LandingProviderError("executor_sse_content")
            self._content.extend(content.encode("utf-8"))
            if len(self._content) > MAX_PROVIDER_OUTPUT_BYTES:
                raise LandingProviderError("executor_result")
        # Optional reasoning fields are intentionally discarded, never joined
        # with output, logged, or included in retained evidence.
        if choice.get("finish_reason") == "stop":
            self._stop = True

    def finish(self):
        if self._pending:
            self._line(bytes(self._pending).removesuffix(b"\r"))
            self._pending.clear()
        if self._data:
            self._event(b"\n".join(self._data))
            self._data.clear()
        if not self._done or not self._stop or self._usage is None or not self._content.strip():
            raise LandingProviderError("executor_sse_incomplete")
        return HttpLandingExecutionResult(bytes(self._content), self._hash.hexdigest(), 0,
                                           self._usage[0], self._usage[1])
