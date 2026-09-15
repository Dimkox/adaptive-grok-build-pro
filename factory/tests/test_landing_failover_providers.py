"""Offline provider protocol and durable failure-observation regressions."""

from datetime import datetime, timezone
import hashlib
import json
import unittest
from pathlib import Path
import tempfile

import httpx

from adaptive_factory.contracts import canonical_json
from adaptive_factory.landing_http import HttpLandingNormalizer, HttpLandingProfile, HttpLandingExecutionRequest, HTTP_NORMALIZER_PROMPT, HTTP_PROTOCOL_VERSION
from adaptive_factory.landing_live_executors import OpenAICompatibleLandingExecutor
from adaptive_factory.landing_provider import LandingNormalizationRequest
from factory.tests.test_landing_normalizer import draft, source


class ProviderObservationTests(unittest.TestCase):
    def test_selected_file_reads_only_the_named_provider_and_rejects_shell_values(self):
        from adaptive_factory.landing_live_executors import PROVIDER_KEY_NAMES, provider_api_key
        from adaptive_factory.landing_provider import LandingProviderError
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "providers.conf"
            path.write_text("\n".join(name + "=test-" + provider for provider, name in PROVIDER_KEY_NAMES.items()))
            path.chmod(0o600)
            for provider in PROVIDER_KEY_NAMES:
                self.assertEqual("test-" + provider, provider_api_key(provider, env_file=path))
            path.write_text("FACTORY_LANDING_OPENAI_API_KEY=$(touch unsafe)\n")
            with self.assertRaisesRegex(LandingProviderError, "credential_file_invalid"):
                provider_api_key("openai", env_file=path)
            path.write_text("FACTORY_LANDING_OPENAI_API_KEY=test\nFACTORY_LANDING_OPENAI_API_KEY=test\n")
            with self.assertRaisesRegex(LandingProviderError, "credential_file_invalid"):
                provider_api_key("openai", env_file=path)

    def test_permission_and_region_denials_are_ineligible_explicit_categories(self):
        for code, category in (("forbidden", "permission"), ("unsupported_country_region_territory", "policy")):
            with self.subTest(code=code):
                observation = self.normalize(403, error={"error": {"code": code}}).observation
                self.assertEqual(category, observation.category)
                self.assertEqual(403, observation.http_status)
    def test_unreadable_error_body_cannot_turn_permission_or_policy_into_transport_fallback(self):
        class BrokenBody(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b'{"error":{"code":"content_'
                raise httpx.ReadTimeout("synthetic truncated error")
        for status in (403, 503):
            with self.subTest(status=status):
                observation = self.normalize(status, stream=BrokenBody()).observation
                self.assertEqual("protocol", observation.category)
                self.assertEqual(status, observation.http_status)

    def normalize(self, status=200, *, content=None, error=None, stream=None):
        profile = HttpLandingProfile.for_provider("qwen-intl", available=True)
        body = error if error is not None else {
            "object": "chat.completion", "model": profile.model_id,
            "choices": [{"index": 0, "finish_reason": "stop", "message": {
                "role": "assistant", "content": draft().decode() if content is None else content,
            }}], "usage": {"prompt_tokens": 12, "completion_tokens": 34, "total_tokens": 46},
        }
        transport = httpx.MockTransport(lambda request: httpx.Response(
            status, headers={"content-type": "application/json"},
            stream=stream if stream is not None else httpx.ByteStream(canonical_json(body)),
        ))
        executor = OpenAICompatibleLandingExecutor(
            provider_id=profile.provider_id, base_url=profile.base_url,
            model_id=profile.model_id, profile=profile, api_key="test-qwen", transport=transport,
        )
        payload = b"A synthetic garden club brief"
        request = LandingNormalizationRequest(
            source(payload, kind="text", media_type="text/plain", job_id="observation"),
            profile.profile_digest,
        )
        return HttpLandingNormalizer(profile, executor, clock=lambda: datetime(
            2026, 9, 15, tzinfo=timezone.utc,
        )).normalize(request, lambda: payload)

    def test_valid_usage_survives_rejected_draft(self):
        result = self.normalize(content="{}")
        self.assertEqual("needs_human", result.state)
        observation = getattr(result, "observation", None)
        self.assertIsNotNone(observation, "failed draft must retain independently validated usage")
        self.assertEqual("draft", observation.category)
        self.assertEqual("reported", observation.usage_status)
        self.assertEqual((12, 34), (observation.usage_input_units, observation.usage_output_units))

    def test_provider_authentication_is_distinct_and_usage_is_unknown(self):
        result = self.normalize(401, error={"error": {"code": "invalid_api_key"}})
        observation = getattr(result, "observation", None)
        self.assertIsNotNone(observation, "provider authentication needs authoritative classification")
        self.assertEqual("authentication", observation.category)
        self.assertEqual(401, observation.http_status)
        self.assertEqual("unavailable", observation.usage_status)
        self.assertIsNone(observation.usage_input_units)
        self.assertIsNone(observation.usage_output_units)

    def test_policy_code_overrides_availability_status(self):
        result = self.normalize(503, error={"error": {"code": "content_policy_violation"}})
        observation = getattr(result, "observation", None)
        self.assertIsNotNone(observation)
        self.assertEqual("policy", observation.category)


class AdditionalProviderTests(unittest.TestCase):
    def run_provider(self, profile_id, *, response=None):
        from adaptive_factory.landing_extra_providers import landing_provider_executor

        profile = HttpLandingProfile.for_provider(profile_id, available=True)
        self.sent = []
        def handler(request):
            self.sent.append((request.url.path, dict(request.headers), json.loads(request.content)))
            document = response or {
                "object": "chat.completion", "model": profile.model_id,
                "choices": [{"index": 0, "finish_reason": "stop", "message": {
                    "role": "assistant", "content": draft().decode(),
                }}], "usage": {"prompt_tokens": 12, "completion_tokens": 34, "total_tokens": 46,
                                "completion_tokens_details": {"reasoning_tokens": 10}},
            }
            return httpx.Response(200, headers={"content-type": "application/json"},
                                  stream=httpx.ByteStream(canonical_json(document)))
        executor = landing_provider_executor(profile, api_key="test-key", transport=httpx.MockTransport(handler))
        payload = "Build a bounded landing page"
        request = HttpLandingExecutionRequest(profile.profile_digest, "a" * 64, canonical_json({
            "instruction": HTTP_NORMALIZER_PROMPT,
            "request": {"protocol_version": HTTP_PROTOCOL_VERSION,
                        "profile_digest": profile.profile_digest, "input_digest": "a" * 64,
                        "media_kind": "text", "source_payload": payload,
                        "source_content_sha256": hashlib.sha256(payload.encode()).hexdigest()},
        }))
        return executor.run(request)

    def test_openai_uses_snapshot_and_completion_limit_with_strict_schema(self):
        result = self.run_provider("openai")
        path, _, body = self.sent[0]
        self.assertEqual("/v1/chat/completions", path)
        self.assertEqual("gpt-4.1-mini-2025-04-14", body["model"])
        self.assertEqual(4096, body["max_completion_tokens"])
        self.assertNotIn("max_tokens", body)
        self.assertTrue(body["response_format"]["json_schema"]["strict"])
        self.assertEqual((12, 34), (result.usage_input_units, result.usage_output_units))

    def test_openrouter_pins_one_upstream_without_nested_fallback(self):
        result = self.run_provider("openrouter")
        path, _, body = self.sent[0]
        self.assertEqual("/api/v1/chat/completions", path)
        self.assertEqual("google/gemini-3.1-flash-lite", body["model"])
        self.assertEqual({"only": ["google-vertex/global"], "order": ["google-vertex/global"],
                          "allow_fallbacks": False, "require_parameters": True}, body["provider"])
        self.assertNotIn("models", body)
        self.assertEqual(34, result.usage_output_units)

    def test_anthropic_messages_includes_cached_input_once(self):
        response = {"id": "msg_test", "type": "message", "role": "assistant",
                    "model": "claude-haiku-4-5-20251001", "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": draft().decode()}],
                    "usage": {"input_tokens": 12, "cache_read_input_tokens": 7,
                              "cache_creation_input_tokens": 3, "output_tokens": 34}}
        result = self.run_provider("anthropic", response=response)
        path, headers, body = self.sent[0]
        self.assertEqual("/v1/messages", path)
        self.assertEqual("2023-06-01", headers["anthropic-version"])
        self.assertEqual("test-key", headers["x-api-key"])
        self.assertIn("system", body)
        self.assertNotIn("response_format", body)
        self.assertEqual("json_schema", body["output_config"]["format"]["type"])
        self.assertEqual((22, 34), (result.usage_input_units, result.usage_output_units))


if __name__ == "__main__":
    unittest.main()
