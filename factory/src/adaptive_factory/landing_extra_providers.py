"""Explicit reserve-provider protocols over the existing bounded HTTP transport."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path

from .contracts import canonical_json
from .landing_contracts import LandingContractError, strict_json_object
from .landing_live_executors import OpenAICompatibleLandingExecutor
from .landing_provider import HttpProviderFailure, LandingProviderError


def structured_schema(provider_id):
    schema = json.loads((Path(__file__).parent / "resources/landing-normalization-draft.v1.schema.json").read_bytes())
    # Native constrained decoding supports a smaller vocabulary than the local
    # validator. Keep the canonical schema and all local checks unchanged.
    omitted = {"$schema", "$id", "minLength", "maxLength", "uniqueItems"}
    if provider_id == "anthropic":
        omitted.add("maxItems")
    def project(value):
        if isinstance(value, list):
            return [project(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: project(item) for key, item in value.items() if key not in omitted}
        if "enum" in result and "type" not in result:
            result["type"] = "string"
        return result
    return project(schema)


class StructuredChatLandingExecutor(OpenAICompatibleLandingExecutor):
    def _request_body(self, instruction, payload):
        body = super()._request_body(instruction, payload)
        body["response_format"] = {"type": "json_schema", "json_schema": {
            "name": "landing_draft", "strict": True, "schema": structured_schema(self.provider_id),
        }}
        if self.provider_id == "openai":
            body["max_completion_tokens"] = body.pop("max_tokens")
        elif self.provider_id == "openrouter":
            body["provider"] = {"only": ["google-vertex/global"], "order": ["google-vertex/global"],
                                "allow_fallbacks": False, "require_parameters": True}
        return body


class AnthropicLandingExecutor(OpenAICompatibleLandingExecutor):
    endpoint_path = "messages"

    def _request_body(self, instruction, payload):
        return {
            "model": self.model_id, "max_tokens": self._profile.max_output_tokens,
            "system": instruction, "messages": [{"role": "user", "content": self._user_content(payload)}],
            "output_config": {"format": {"type": "json_schema", "schema": structured_schema(self.provider_id)}},
        }

    def _request_headers(self):
        return {"x-api-key": self._api_key, "anthropic-version": "2023-06-01",
                "Content-Type": "application/json", "Accept": "application/json", "Accept-Encoding": "identity"}

    def _decode_response(self, raw, started):
        try:
            document = strict_json_object(raw, maximum=self._profile.max_response_bytes)
            if document.get("stop_reason") == "refusal":
                raise HttpProviderFailure("executor_result", "policy")
            content = document["content"]
            if (document["type"] != "message" or document["role"] != "assistant"
                    or document["model"] != self.model_id or document["stop_reason"] != "end_turn"
                    or not isinstance(content, list) or len(content) != 1
                    or not isinstance(content[0], dict) or content[0].get("type") != "text"):
                raise LandingProviderError("executor_result")
            usage = document["usage"]
            counts = (usage["input_tokens"], usage.get("cache_read_input_tokens", 0),
                      usage.get("cache_creation_input_tokens", 0), usage["output_tokens"])
            if any(type(value) is not int or not 0 <= value <= 10_000_000 for value in counts):
                raise LandingProviderError("executor_usage")
            prompt, completion = sum(counts[:3]), counts[3]
            translated = {"object": "chat.completion", "model": document["model"],
                          "choices": [{"index": 0, "finish_reason": "stop", "message": {
                              "role": "assistant", "content": content[0]["text"],
                          }}], "usage": {"prompt_tokens": prompt, "completion_tokens": completion,
                                          "total_tokens": prompt + completion}}
        except (KeyError, TypeError, ValueError, LandingContractError):
            raise LandingProviderError("executor_result") from None
        result = super()._decode_response(canonical_json(translated), started)
        return replace(result, response_digest=hashlib.sha256(raw).hexdigest())


def landing_provider_executor(profile, *, api_key, transport=None):
    executor = (AnthropicLandingExecutor if profile.provider_id == "anthropic"
                else StructuredChatLandingExecutor if profile.provider_id in {"openai", "openrouter"}
                else OpenAICompatibleLandingExecutor)
    return executor(provider_id=profile.provider_id, base_url=profile.base_url, model_id=profile.model_id,
                    profile=profile, api_key=api_key, transport=transport)
