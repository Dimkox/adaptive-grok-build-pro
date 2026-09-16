"""Grok/Qwen live executors; HTTP is mocked and never leaves process."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import json
import io
from contextlib import redirect_stdout
from dataclasses import replace
from uuid import uuid4
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

import httpx

from adaptive_factory import landing_live_executors as live
from adaptive_factory.contracts import canonical_json
from adaptive_factory.landing_contracts import decode_provider_evidence
from adaptive_factory.landing_http import HTTP_NORMALIZER_PROMPT, HTTP_PROTOCOL_VERSION, HttpLandingProfile, HttpLandingExecutionRequest, HttpLandingNormalizer
from adaptive_factory.landing_sqlite_store import SQLiteLandingJobStore
from adaptive_factory.settings import SettingsError
from adaptive_factory.landing_artifact import DEPLOY_MEMBERS
from adaptive_factory.landing_intake import PrivateLandingBlobStore
from adaptive_factory.landing_live_executors import (
    CURRENT_LANDING_HOST_REQUIREMENTS,
    CURRENT_PYTHON_SHA256,
    GROK_API_KEY_ENV,
    OpenAICompatibleLandingExecutor,
    QWEN_API_KEY_ENV,
    api_key_from_environ,
    compose_env_landing,
    compose_landing_live_grok,
    compose_landing_live_qwen,
    LANDING_OUTPUT_ENV,
    LANDING_PROVIDER_ENV,
    LANDING_SCRATCH_ENV,
    LANDING_SOURCE_ENV,
    grok_landing_executor,
    qwen_landing_executor,
)
from adaptive_factory.landing_provider import LandingProviderError, LandingNormalizationRequest
from adaptive_factory.landing_http import HTTP_PROFILES
from adaptive_factory.landing_failover_config import PROVIDER_ORDER
from adaptive_factory.settings import LANDING_PROVIDERS
from adaptive_factory.landing_renderer import TARGET_REPOSITORY_ID
from adaptive_factory.landing_runtime import implemented_live_binding
from adaptive_factory.models import Actor
from factory.tests.test_landing_normalizer import draft, source
from factory.tests.test_landing_contracts import provider_facts
from factory.tests.test_landing_renderer import sealed_target

FIXED_TIME = datetime(2026, 9, 6, 19, 0, tzinfo=timezone.utc)
FACTORY_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = FACTORY_ROOT.parent


def _transport(expected_model: str, *, status: int = 200, payload=None) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        assert request.headers["Authorization"].startswith("Bearer ")
        body = json.loads(request.content.decode("utf-8"))
        assert body["model"] == expected_model
        document = payload if payload is not None else {
            "object": "chat.completion", "model": expected_model,
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": draft().decode("utf-8")}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 34, "total_tokens": 46},
        }
        return httpx.Response(status, headers={"content-type": "application/json"},
                              stream=httpx.ByteStream(canonical_json(document)))


    return httpx.MockTransport(handler)


def _request(executor) -> HttpLandingExecutionRequest:
    return HttpLandingExecutionRequest(executor.profile_digest, "a" * 64, canonical_json({
        "instruction": HTTP_NORMALIZER_PROMPT,
        "request": {"protocol_version": HTTP_PROTOCOL_VERSION,
                    "profile_digest": executor.profile_digest, "input_digest": "a" * 64,
                    "media_kind": "text", "source_payload": "Build a bounded landing page",
                    "source_content_sha256": hashlib.sha256(b"Build a bounded landing page").hexdigest()},
    }))


class LandingLiveExecutorTests(unittest.TestCase):
    def test_host_requirements_match_current_python_and_httpx(self) -> None:
        requirements = CURRENT_LANDING_HOST_REQUIREMENTS
        self.assertEqual("/usr/bin/python3.12", requirements.python_executable)
        self.assertEqual("3.12.3", requirements.python_version_prefix)
        self.assertEqual(
            "a92f0f95e883390c7256b2e441484aac06b1002dbe1d924141a77c8d82f96223",
            requirements.python_sha256,
        )
        self.assertEqual(CURRENT_PYTHON_SHA256, requirements.python_sha256)
        self.assertEqual(">=3.11", requirements.factory_requires_python)
        self.assertEqual("0.28.1", requirements.httpx_version)
        self.assertEqual("FACTORY_LANDING_GROK_API_KEY", requirements.grok_api_key_env)
        self.assertEqual("FACTORY_LANDING_QWEN_API_KEY", requirements.qwen_api_key_env)
        self.assertEqual("https://api.x.ai/v1", requirements.grok_base_url)
        self.assertEqual("grok-4", requirements.grok_model_id)
        self.assertEqual("https://dashscope.aliyuncs.com/compatible-mode/v1", requirements.qwen_base_url)
        self.assertEqual("qwen-plus", requirements.qwen_model_id)

    def test_pyproject_pins_match_host_record(self) -> None:
        document = tomllib.loads((FACTORY_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        project = document["project"]
        self.assertEqual(CURRENT_LANDING_HOST_REQUIREMENTS.factory_requires_python, project["requires-python"])
        self.assertIn("httpx==0.28.1", project["dependencies"])

    def test_factory_server_does_not_import_httpx_or_live_executors(self) -> None:
        source = (FACTORY_ROOT / "src/adaptive_factory/server.py").read_text(encoding="utf-8")
        imported = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
                imported.add(node.module.split(".")[-1])
        self.assertNotIn("httpx", imported)
        self.assertNotIn("landing_live_executors", imported)

    def test_landing_runtime_does_not_import_httpx(self) -> None:
        source = (FACTORY_ROOT / "src/adaptive_factory/landing_runtime.py").read_text(encoding="utf-8")
        imported = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
                imported.add(node.module.split(".")[-1])
        self.assertNotIn("httpx", imported)
        self.assertNotIn("landing_live_executors", imported)

    def test_missing_env_key_fails_closed(self) -> None:
        with self.assertRaises(LandingProviderError) as raised:
            api_key_from_environ(GROK_API_KEY_ENV, {})
        self.assertEqual("credential_unavailable", str(raised.exception))
        self.assertEqual("secret", api_key_from_environ(QWEN_API_KEY_ENV, {QWEN_API_KEY_ENV: "secret"}))

    def test_empty_constructor_key_fails_closed(self) -> None:
        with self.assertRaises(LandingProviderError) as raised:
            grok_landing_executor(api_key="  ")
        self.assertEqual("credential_unavailable", str(raised.exception))

    def test_non_https_base_url_fails_closed(self) -> None:
        with self.assertRaises(LandingProviderError) as raised:
            OpenAICompatibleLandingExecutor(
                provider_id="grok",
                base_url="http://api.x.ai/v1",
                model_id="grok-4",
                api_key="test-grok",
            )
        self.assertEqual("http_profile_identity", str(raised.exception))

    def test_grok_mock_transport_returns_draft_json(self) -> None:
        executor = grok_landing_executor(api_key="test-grok", transport=_transport("grok-4"))
        result = executor.run(_request(executor))
        self.assertEqual((12, 34), (result.usage_input_units, result.usage_output_units))
        self.assertEqual(draft(), result.stdout)

    def test_qwen_mock_transport_returns_draft_json(self) -> None:
        executor = qwen_landing_executor(api_key="test-qwen", transport=_transport("qwen-plus"))
        self.assertEqual(draft(), executor.run(_request(executor)).stdout)

    def test_http_error_status_fails_closed(self) -> None:
        executor = grok_landing_executor(
            api_key="test-grok",
            transport=_transport("grok-4", status=500, payload={"error": "no"}),
        )
        with self.assertRaises(LandingProviderError) as raised:
            executor.run(_request(executor))
        self.assertEqual("executor_http", str(raised.exception))

    def test_transport_error_fails_closed(self) -> None:
        class Boom(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                raise httpx.ConnectError("boom", request=request)

        executor = grok_landing_executor(api_key="test-grok", transport=Boom())
        with self.assertRaises(LandingProviderError) as raised:
            executor.run(_request(executor))
        self.assertEqual("executor_transport", str(raised.exception))

    def test_sync_only_transport_is_rejected_before_any_request(self) -> None:
        class SyncOnly(httpx.BaseTransport):
            def handle_request(self, request):
                raise AssertionError("synchronous transport was invoked")

        with self.assertRaisesRegex(LandingProviderError, "executor_transport_type"):
            qwen_landing_executor(api_key="test-qwen", transport=SyncOnly())

    def test_malformed_body_fails_closed(self) -> None:
        executor = qwen_landing_executor(
            api_key="test-qwen",
            transport=_transport("qwen-plus", payload={"choices": []}),
        )
        with self.assertRaises(LandingProviderError) as raised:
            executor.run(_request(executor))
        self.assertEqual("executor_result", str(raised.exception))


class GrokReasoningUsageTests(unittest.TestCase):
    # Counts captured from the sanitized grok-4.6 response on 2026-09-15.
    CAPTURED_USAGE = {
        "prompt_tokens": 1336, "completion_tokens": 93, "total_tokens": 2598,
        "completion_tokens_details": {"reasoning_tokens": 1169},
    }
    LEGACY_DECODER = "9513c336dc2e6cfecae92ebb743e10ea1bb37755e6a5a1da34393b6cd8512d43"
    LEGACY_GROK_PROFILES = {
        "grok": "5a38fabf2eb2cd2039129e7dcde570c771d885e26aaaf9fbcdfe5eec3ea0703c",
        "grok-vision": "9d1d6e8ea8019ff1d371681cad01cfef5110a8bd997bcadedc401b810e239339",
    }

    def executor(self, usage, profile_id="grok-vision", *, limit=4096, response_model=None):
        profile = replace(HttpLandingProfile.for_provider(profile_id, available=True),
                          max_output_tokens=limit)
        response = {
            "object": "chat.completion", "model": response_model or profile.model_id,
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": draft().decode()}}],
            "usage": usage,
        }
        executor = OpenAICompatibleLandingExecutor(
            provider_id=profile.provider_id, base_url=profile.base_url,
            model_id=profile.model_id, profile=profile, api_key="test-grok",
            transport=_transport(profile.model_id, payload=response),
        )
        return executor, profile, response

    def normalize(self, usage, profile_id="grok-vision", *, limit=4096):
        executor, profile, response = self.executor(usage, profile_id, limit=limit)
        payload = b"A synthetic garden club brief"
        request = LandingNormalizationRequest(
            source(payload, kind="text", media_type="text/plain", job_id="grok-usage"),
            profile.profile_digest,
        )
        outcome = HttpLandingNormalizer(profile, executor, clock=lambda: FIXED_TIME).normalize(
            request, lambda: payload,
        )
        return outcome, profile, response

    def test_captured_reasoning_normalizes_into_aggregate_output_and_current_evidence(self):
        for profile_id in ("grok", "grok-vision"):
            with self.subTest(profile=profile_id):
                outcome, profile, response = self.normalize(self.CAPTURED_USAGE, profile_id)
                self.assertEqual(("normalized", "normalized"),
                                 (outcome.state, outcome.reason_code))
                self.assertIsNotNone(outcome.spec)
                evidence = outcome.evidence
                self.assertEqual((1336, 1262),
                                 (evidence.usage_input_units, evidence.usage_output_units))
                self.assertEqual(hashlib.sha256(canonical_json(response)).hexdigest(),
                                 evidence.response_digest)
                self.assertEqual(profile.profile_digest, evidence.profile_digest)
                self.assertEqual(profile.model_id, evidence.model_id)
                self.assertEqual("normalized", evidence.disposition)
                self.assertEqual("1.1.1", evidence.adapter_version)
                self.assertEqual(profile.to_facts()["adapter_version"], evidence.adapter_version)
                self.assertEqual(profile.to_facts()["decoder_digest"], evidence.decoder_digest)
                self.assertNotEqual(self.LEGACY_DECODER, evidence.decoder_digest)
                self.assertNotEqual(self.LEGACY_GROK_PROFILES[profile_id], profile.profile_digest)
                self.assertEqual(evidence, decode_provider_evidence(evidence.to_dict()))

    def test_aggregate_output_at_cap_passes_but_one_token_over_is_rejected(self):
        executor, _, _ = self.executor(self.CAPTURED_USAGE, limit=1262)
        self.assertEqual(1262, executor.run(_request(executor)).usage_output_units)
        executor, _, _ = self.executor(self.CAPTURED_USAGE, limit=1261)
        with self.assertRaisesRegex(LandingProviderError, "executor_usage"):
            executor.run(_request(executor))
        outcome, profile, _ = self.normalize(self.CAPTURED_USAGE, limit=1261)
        self.assertEqual(("needs_human", "http_outcome_unusable"),
                         (outcome.state, outcome.reason_code))
        self.assertIsNone(outcome.spec)
        self.assertEqual("1.1.1", outcome.evidence.adapter_version)
        self.assertEqual(profile.to_facts()["decoder_digest"], outcome.evidence.decoder_digest)

    def test_legacy_usage_absent_zero_or_inclusive_reasoning_is_not_double_counted(self):
        base = {"prompt_tokens": 12, "completion_tokens": 34, "total_tokens": 46}
        cases = [base, {**base, "completion_tokens_details": None},
                 {**base, "completion_tokens_details": {}},
                 {**base, "completion_tokens_details": {"audio_tokens": 0}}]
        cases.extend({**base, "completion_tokens_details": {"reasoning_tokens": count}}
                     for count in (0, 7, 34))
        cases.append({"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                      "completion_tokens_details": {"reasoning_tokens": 0}})
        for usage in cases:
            with self.subTest(usage=usage):
                executor, _, _ = self.executor(usage)
                result = executor.run(_request(executor))
                self.assertEqual((usage["prompt_tokens"], usage["completion_tokens"]),
                                 (result.usage_input_units, result.usage_output_units))

    def test_unexplained_totals_and_inclusive_reasoning_above_completion_are_rejected(self):
        cases = [
            {**self.CAPTURED_USAGE, "completion_tokens_details": details}
            for details in (None, {}, {"reasoning_tokens": 0}, {"reasoning_tokens": 1168})
        ]
        cases.extend((
            {key: value for key, value in self.CAPTURED_USAGE.items()
             if key != "completion_tokens_details"},
            {**self.CAPTURED_USAGE, "total_tokens": 2597},
            {**self.CAPTURED_USAGE, "total_tokens": 2599},
            {**self.CAPTURED_USAGE, "total_tokens": 1429},
            {**self.CAPTURED_USAGE, "total_tokens": 1000},
        ))
        for usage in cases:
            with self.subTest(usage=usage):
                executor, _, _ = self.executor(usage)
                with self.assertRaisesRegex(LandingProviderError, "executor_usage"):
                    executor.run(_request(executor))

    def test_malformed_reasoning_is_rejected_even_when_totals_are_inclusive(self):
        for total in (1429, 2598):
            for value in (None, True, False, -1, 10_000_001, "1169", 1169.0, [], {}):
                with self.subTest(total=total, reasoning=value):
                    usage = {**self.CAPTURED_USAGE, "total_tokens": total,
                             "completion_tokens_details": {"reasoning_tokens": value}}
                    executor, _, _ = self.executor(usage)
                    with self.assertRaisesRegex(LandingProviderError, "executor_usage"):
                        executor.run(_request(executor))

    def test_malformed_detail_containers_are_rejected(self):
        for details in (True, False, 0, 1169, "1169", [], [1169]):
            with self.subTest(details=details):
                usage = {**self.CAPTURED_USAGE, "total_tokens": 1429,
                         "completion_tokens_details": details}
                executor, _, _ = self.executor(usage)
                with self.assertRaisesRegex(LandingProviderError, "executor_usage"):
                    executor.run(_request(executor))

    def test_required_usage_counters_remain_bounded_integers(self):
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            for value in (None, True, False, -1, 10_000_001, "93", 93.0, [], {}):
                with self.subTest(key=key, value=value):
                    executor, _, _ = self.executor({**self.CAPTURED_USAGE, key: value})
                    with self.assertRaisesRegex(LandingProviderError, "executor_usage"):
                        executor.run(_request(executor))
            with self.subTest(missing=key):
                executor, _, _ = self.executor({name: value for name, value
                                               in self.CAPTURED_USAGE.items() if name != key})
                with self.assertRaises(LandingProviderError):
                    executor.run(_request(executor))

    def test_separate_reasoning_does_not_relax_exact_model_binding(self):
        for profile_id, wrong_model in (("grok", "grok-4.6"), ("grok-vision", "grok-4")):
            with self.subTest(profile=profile_id):
                executor, _, _ = self.executor(self.CAPTURED_USAGE, profile_id,
                                               response_model=wrong_model)
                with self.assertRaisesRegex(LandingProviderError, "executor_result"):
                    executor.run(_request(executor))

    def test_qwen_nonstreaming_accounting_and_evidence_remain_unchanged(self):
        for profile_id in ("qwen", "qwen-intl"):
            with self.subTest(profile=profile_id):
                inclusive = {**self.CAPTURED_USAGE, "total_tokens": 1429,
                             "completion_tokens_details": {"reasoning_tokens": "ignored"}}
                outcome, profile, _ = self.normalize(inclusive, profile_id)
                self.assertEqual("normalized", outcome.state)
                self.assertEqual((1336, 93), (outcome.evidence.usage_input_units,
                                             outcome.evidence.usage_output_units))
                self.assertEqual("1.1.0", outcome.evidence.adapter_version)
                self.assertEqual(self.LEGACY_DECODER, outcome.evidence.decoder_digest)
                self.assertEqual(profile.to_facts()["decoder_digest"], outcome.evidence.decoder_digest)
                executor, _, _ = self.executor(self.CAPTURED_USAGE, profile_id)
                with self.assertRaisesRegex(LandingProviderError, "executor_usage"):
                    executor.run(_request(executor))

    def test_all_enabled_qwen_profile_digests_retain_existing_bindings(self):
        expected = {
            "qwen": "63bee9e18255cbbbe940f94e96e130f6fffb103147d8cf1baf9cfa09595091be",
            "qwen-intl": "2616a276a5a6257515dc30e40d27fe32a667aa7d75f8205990c567166116de08",
            "qwen-omni": "d8738006a475fbbdb5700876cec4669256933ae8c928a250853bd1775225212b",
            "qwen-omni-intl": "4cc85b8a61d1a0b51e69b9a28d8766bbdf6158db4e145d8a8ab81992a9157f67",
        }
        for profile_id, digest in expected.items():
            with self.subTest(profile=profile_id):
                profile = HttpLandingProfile.for_provider(profile_id, available=True)
                self.assertEqual(digest, profile.profile_digest)

    def test_retained_grok_v1_v2_evidence_preserves_old_identity_and_counts(self):
        # Frozen synthetic envelopes created with the pre-repair adapter at e7e8ad1.
        for version, digest in (
            (1, "9b6b1e78de5de061d29ccb3f4e14d95eee199a3fe1b8aa55eddc23264868634b"),
            (2, "a48a4e7e48f484ef61cfb51eba38cc1a37d3dd99c4251ef792cf3fdbead1919d"),
        ):
            with self.subTest(version=version):
                document = provider_facts(
                    schema_version=version, provider_id="grok", model_id="grok-4.6",
                    profile_digest=self.LEGACY_GROK_PROFILES["grok-vision"],
                    adapter_id="https-chat-completions", adapter_version="1.1.0",
                    decoder_digest=self.LEGACY_DECODER, disposition="provider_unavailable",
                    provider_evidence_digest=digest,
                )
                retained = decode_provider_evidence(document)
                self.assertEqual(document, retained.to_dict())
                self.assertEqual((12, 34), (retained.usage_input_units, retained.usage_output_units))


class HttpLandingDraftNormalizationTests(unittest.TestCase):
    def normalize(self, document, provider="qwen"):
        profile = HttpLandingProfile.for_provider(provider, available=True)
        response = {
            "object": "chat.completion", "model": profile.model_id,
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": json.dumps(document)}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 34, "total_tokens": 46},
        }
        factory = qwen_landing_executor if provider == "qwen" else grok_landing_executor
        executor = factory(
            api_key=uuid4().hex, profile=profile,
            transport=_transport(profile.model_id, payload=response),
        )
        payload = b"A synthetic garden club brief"
        request = LandingNormalizationRequest(
            source(payload, kind="text", media_type="text/plain", job_id="http-draft"),
            profile.profile_digest,
        )
        outcome = HttpLandingNormalizer(profile, executor, clock=lambda: FIXED_TIME).normalize(
            request, lambda: payload,
        )
        return outcome, request

    def test_http_provider_normalizes_mixed_language_unsorted_duplicate_items(self):
        document = json.loads(draft())
        document["sections"][0]["items"] = ["a", "é", "a"]
        for provider in ("grok", "qwen"):
            with self.subTest(provider=provider):
                outcome, request = self.normalize(document, provider)
                self.assertEqual(("normalized", "normalized"),
                                 (outcome.state, outcome.reason_code))
                self.assertEqual(("é", "a"), outcome.spec.sections[0].items)
                self.assertEqual("normalized", outcome.evidence.disposition)
                self.assertEqual(request.source.input_digest, outcome.evidence.input_digest)
                self.assertEqual(request.profile_digest, outcome.evidence.profile_digest)
                self.assertEqual((12, 34),
                                 (outcome.evidence.usage_input_units, outcome.evidence.usage_output_units))
                self.assertRegex(outcome.evidence.provider_evidence_digest, r"^[0-9a-f]{64}$")

    def test_http_malformed_sections_return_controlled_outcome_with_evidence(self):
        document = json.loads(draft())
        for sections in (None, 3, True, {}, "invalid", [], document["sections"] * 13):
            with self.subTest(sections=sections):
                outcome, request = self.normalize({**document, "sections": sections})
                self.assertEqual(("needs_human", "http_outcome_unusable"),
                                 (outcome.state, outcome.reason_code))
                self.assertIsNone(outcome.spec)
                self.assertEqual("provider_unavailable", outcome.evidence.disposition)
                self.assertEqual(request.source.input_digest, outcome.evidence.input_digest)
                self.assertEqual(request.profile_digest, outcome.evidence.profile_digest)
                self.assertRegex(outcome.evidence.provider_evidence_digest, r"^[0-9a-f]{64}$")


class LandingLiveGrokQwenCompositionTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="landing-live-llm-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "blobs").mkdir(mode=0o700)
        (self.root / "scratch").mkdir(mode=0o700)
        (self.root / "artifacts").mkdir(mode=0o700)
        (self.root / "state").mkdir(mode=0o700)
        self.store = SQLiteLandingJobStore(self.root / "state", repository_root=REPO_ROOT)
        self.addCleanup(self.store.close)
        self.actor = Actor(
            "tenant-1",
            "operator",
            frozenset({"landing:submit", "landing:read"}),
            frozenset({TARGET_REPOSITORY_ID}),
        )
        self.blobs = PrivateLandingBlobStore(
            self.root / "blobs",
            repository_root=REPO_ROOT,
            clock=lambda: FIXED_TIME,
        )

    def _profile(self, provider="grok") -> HttpLandingProfile:
        return HttpLandingProfile.for_provider(provider, available=True)

    def test_malformed_sections_persist_controlled_reason_and_evidence(self) -> None:
        with sealed_target() as (target, base_sha, base_tree), patch.multiple(
            "adaptive_factory.landing_renderer", TARGET_BASE_SHA=base_sha, TARGET_BASE_TREE=base_tree,
        ), patch.multiple(
            "adaptive_factory.landing_service", TARGET_BASE_SHA=base_sha, TARGET_BASE_TREE=base_tree,
        ):
            for index, sections in enumerate((None, 3, True)):
                with self.subTest(sections=sections):
                    document = {**json.loads(draft()), "sections": sections}
                    response = {
                        "object": "chat.completion", "model": "qwen-plus",
                        "choices": [{"index": 0, "finish_reason": "stop",
                                     "message": {"role": "assistant", "content": json.dumps(document)}}],
                        "usage": {"prompt_tokens": 12, "completion_tokens": 34, "total_tokens": 46},
                    }
                    service = compose_landing_live_qwen(
                        api_key=uuid4().hex, binding=implemented_live_binding(enabled=True),
                        profile=self._profile("qwen"), source_repository=target,
                        scratch_root=self.root / "scratch", output_directory=self.root / "artifacts",
                        blobs=self.blobs, store=self.store, clock=lambda: FIXED_TIME,
                        transport=_transport("qwen-plus", payload=response),
                    )
                    job_id = f"malformed-sections-{index}"
                    created = service.submit(
                        job_id=job_id, repository_id=TARGET_REPOSITORY_ID,
                        exact_base_sha=base_sha, exact_base_tree=base_tree,
                        media_type="text/plain", chunks=(b"A synthetic garden club brief",),
                        actor=self.actor,
                    )
                    retained = self.store.get("tenant-1", TARGET_REPOSITORY_ID, job_id)
                    self.assertEqual(created.job, retained)
                    self.assertEqual(("needs_human", "http_outcome_unusable"),
                                     (retained.state, retained.reason_code))
                    self.assertRegex(retained.provider_evidence_digest, r"^[0-9a-f]{64}$")
                    self.assertIsNone(retained.artifact)

    def test_grok_compose_seals_complete_artifact_with_mocked_http(self) -> None:
        payload = b"Build a bounded landing candidate"
        with sealed_target() as (target, base_sha, base_tree), patch.multiple(
            "adaptive_factory.landing_renderer",
            TARGET_BASE_SHA=base_sha,
            TARGET_BASE_TREE=base_tree,
        ), patch.multiple(
            "adaptive_factory.landing_service",
            TARGET_BASE_SHA=base_sha,
            TARGET_BASE_TREE=base_tree,
        ):
            service = compose_landing_live_grok(
                api_key="test-grok",
                binding=implemented_live_binding(enabled=True),
                profile=self._profile(),
                source_repository=target,
                scratch_root=self.root / "scratch",
                output_directory=self.root / "artifacts",
                blobs=self.blobs,
                store=self.store,
                clock=lambda: FIXED_TIME,
                transport=_transport("grok-4"),
            )
            created = service.submit(
                job_id="job-grok-ready",
                repository_id=TARGET_REPOSITORY_ID,
                exact_base_sha=base_sha,
                exact_base_tree=base_tree,
                media_type="text/plain",
                chunks=(payload,),
                actor=self.actor,
            )
            self.assertEqual("artifact_ready", created.job.state)
            self.assertIsNone(created.job.result_view()["live_url"])
            self.assertEqual(
                tuple(sorted(DEPLOY_MEMBERS)),
                created.job.sealed_artifact.member_names,
            )

    def test_qwen_compose_seals_complete_artifact_with_mocked_http(self) -> None:
        payload = b"Build a bounded landing candidate"
        with sealed_target() as (target, base_sha, base_tree), patch.multiple(
            "adaptive_factory.landing_renderer",
            TARGET_BASE_SHA=base_sha,
            TARGET_BASE_TREE=base_tree,
        ), patch.multiple(
            "adaptive_factory.landing_service",
            TARGET_BASE_SHA=base_sha,
            TARGET_BASE_TREE=base_tree,
        ):
            service = compose_landing_live_qwen(
                api_key="test-qwen",
                binding=implemented_live_binding(enabled=True),
                profile=self._profile("qwen"),
                source_repository=target,
                scratch_root=self.root / "scratch",
                output_directory=self.root / "artifacts",
                blobs=self.blobs,
                store=self.store,
                clock=lambda: FIXED_TIME,
                transport=_transport("qwen-plus"),
            )
            created = service.submit(
                job_id="job-qwen-ready",
                repository_id=TARGET_REPOSITORY_ID,
                exact_base_sha=base_sha,
                exact_base_tree=base_tree,
                media_type="text/plain",
                chunks=(payload,),
                actor=self.actor,
            )
            self.assertEqual("artifact_ready", created.job.state)
            retained = created.job.sealed_artifact
            self.assertEqual(2, retained.to_dict()["schema_version"])
            self.assertEqual(2, retained.provider_evidence.schema_version)
            self.assertEqual("normalized", retained.provider_evidence.disposition)
            from adaptive_factory.landing_runtime import create_landing_artifact_builder
            from adaptive_factory.landing_service import LandingApplicationService
            from adaptive_factory.landing_artifact_retention import RetainedLandingArtifact
            from adaptive_factory.landing_artifact import LandingArtifactError
            from factory.tests.test_landing_runtime import BoundProvider, PROFILE_DIGEST
            native = LandingApplicationService(
                self.store, self.blobs, BoundProvider(), profile_digest=PROFILE_DIGEST,
                artifact_builder=create_landing_artifact_builder(
                    binding=implemented_live_binding(enabled=True), source_repository=target,
                    scratch_root=self.root / "scratch", output_directory=self.root / "artifacts",
                    clock=lambda: FIXED_TIME,
                ), clock=lambda: FIXED_TIME,
            ).submit(job_id="legacy-job", repository_id=TARGET_REPOSITORY_ID,
                     exact_base_sha=base_sha, exact_base_tree=base_tree,
                     media_type="text/plain", chunks=(payload,), actor=self.actor).job
            self.assertEqual("artifact_ready", native.state)
            self.assertEqual(1, native.sealed_artifact.to_dict()["schema_version"])
            legacy_bytes = canonical_json(native.sealed_artifact.to_dict())
            for envelope, nested in ((1, retained.provider_evidence.to_dict()),
                                     (2, native.sealed_artifact.provider_evidence.to_dict()),
                                     (3, retained.provider_evidence.to_dict())):
                with self.subTest(envelope=envelope, nested=nested["schema_version"]):
                    with self.assertRaises(LandingArtifactError):
                        RetainedLandingArtifact.from_dict({**retained.to_dict(), "schema_version": envelope,
                                                          "provider_evidence": nested})
            self.store.close()
            reopened = SQLiteLandingJobStore(self.root / "state", repository_root=REPO_ROOT)
            self.addCleanup(reopened.close)
            reloaded = reopened.get("tenant-1", TARGET_REPOSITORY_ID, "job-qwen-ready")
            self.assertEqual(retained, reloaded.sealed_artifact)
            reloaded.sealed_artifact.validate(reloaded.source)
            legacy = reopened.get("tenant-1", TARGET_REPOSITORY_ID, "legacy-job")
            self.assertEqual(legacy_bytes, canonical_json(legacy.sealed_artifact.to_dict()))
            reopened.close()
            from adaptive_factory.landing_backup import create_snapshot, restore_snapshot
            from adaptive_factory.landing_host import LandingHostConfig
            from adaptive_factory.settings import FactorySettings
            from adaptive_factory.landing_publication_cli import _bundle
            from adaptive_delivery.landing_publication_contracts import PublicationTargetV1
            publication = self.root / "publication"
            publication.mkdir(mode=0o700)
            backup_config = LandingHostConfig(FactorySettings(
                database_url="", socket_path=self.root / "socket", actors_file=self.root / "actors",
                landing_state_path=self.root / "state", landing_output_path=self.root / "artifacts",
                landing_source_path=target, landing_scratch_path=self.root / "scratch",
                landing_quarantine_path=self.root / "blobs",
            ), REPO_ROOT, publication)
            snapshot = self.root / "snapshot space%?#é"
            saved = create_snapshot(backup_config, snapshot)
            for root in (self.root / "state", self.root / "artifacts", publication):
                root.rename(root.with_name(root.name + "-old"))
            restore_snapshot(backup_config, snapshot, saved["manifest_sha256"])
            restored = SQLiteLandingJobStore(self.root / "state", repository_root=REPO_ROOT)
            self.addCleanup(restored.close)
            published_root = self.root / "publication-target"
            published_root.mkdir(mode=0o700)
            metadata = published_root.stat()
            import os
            publication_target = PublicationTargetV1(1, "fixture-target", str(published_root),
                "https://therealaidarkfactory.online", os.geteuid(), metadata.st_dev, metadata.st_ino)
            for job_id, version in (("legacy-job", 1), ("job-qwen-ready", 2)):
                result = restored.get("tenant-1", TARGET_REPOSITORY_ID, job_id)
                self.assertEqual(version, result.sealed_artifact.provider_evidence.schema_version)
                bundle = _bundle({"tenant_id": "tenant-1", "repository_id": TARGET_REPOSITORY_ID,
                                  "control_repository": str(REPO_ROOT), "publication_state_root": str(publication),
                                  "landing_state_root": str(self.root / "state")}, publication_target,
                                 {"tenant_id": "tenant-1", "repository_id": TARGET_REPOSITORY_ID, "job_id": job_id})
                self.assertEqual(result.artifact.artifact_digest, bundle.artifact_digest)
            self.assertIsNone(created.job.result_view()["live_url"])
            self.assertEqual(
                tuple(sorted(DEPLOY_MEMBERS)),
                created.job.sealed_artifact.member_names,
            )

    def test_compose_env_landing_unset_provider_returns_none(self) -> None:
        self.assertIsNone(
            compose_env_landing(self.blobs, profile=self._profile(), environ={})
        )

    def test_compose_env_landing_unknown_provider_fails_closed(self) -> None:
        with self.assertRaises(LandingProviderError) as raised:
            compose_env_landing(
                self.blobs,
                profile=self._profile(),
                environ={LANDING_PROVIDER_ENV: "claude"},
            )
        self.assertEqual("landing_provider", str(raised.exception))

    def test_explicit_qwen_region_rejects_conflicting_profile_before_credentials(self):
        for selected, supplied in (("qwen-intl", "qwen"), ("qwen", "qwen-intl")):
            with self.subTest(selected=selected), patch.object(
                live, "qwen_api_key", side_effect=AssertionError("credential acquired before region check")
            ):
                with self.assertRaisesRegex(LandingProviderError, "http_profile_identity"):
                    compose_env_landing(
                        self.blobs, profile=HttpLandingProfile.for_provider(supplied, available=True),
                        environ={LANDING_PROVIDER_ENV: selected},
                    )

    def test_compose_env_landing_grok_seals_with_mocked_http(self) -> None:
        payload = b"Build a bounded landing candidate"
        with sealed_target() as (target, base_sha, base_tree), patch.multiple(
            "adaptive_factory.landing_renderer",
            TARGET_BASE_SHA=base_sha,
            TARGET_BASE_TREE=base_tree,
        ), patch.multiple(
            "adaptive_factory.landing_service",
            TARGET_BASE_SHA=base_sha,
            TARGET_BASE_TREE=base_tree,
        ):
            service = compose_env_landing(
                self.blobs,
                store=self.store,
                profile=self._profile(),
                environ={
                    LANDING_PROVIDER_ENV: "grok",
                    GROK_API_KEY_ENV: "test-grok",
                    LANDING_SOURCE_ENV: str(target),
                    LANDING_SCRATCH_ENV: str(self.root / "scratch"),
                    LANDING_OUTPUT_ENV: str(self.root / "artifacts"),
                },
                clock=lambda: FIXED_TIME,
                transport=_transport("grok-4"),
            )
            self.assertIsNotNone(service)
            created = service.submit(
                job_id="job-env-grok",
                repository_id=TARGET_REPOSITORY_ID,
                exact_base_sha=base_sha,
                exact_base_tree=base_tree,
                media_type="text/plain",
                chunks=(payload,),
                actor=self.actor,
            )
            self.assertEqual("artifact_ready", created.job.state)
            self.assertIsNone(created.job.result_view()["live_url"])


class QwenCredentialAndProfileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="qwen-fixture-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "credentials.txt"
        self.value = uuid4().hex

    def write(self, text):
        self.path.write_text(text)
        self.path.chmod(0o600)

    def test_explicit_file_reads_only_standard_assignment_without_interpolation(self):
        for prefix, quote in (("", ""), ("export ", "'"), ("", '"')):
            with self.subTest(prefix=prefix, quote=quote):
                self.write(f"IGNORED_KEY=unrelated\n{prefix}DASHSCOPE_API_KEY={quote}{self.value}{quote}\n")
                self.assertEqual(self.value, live.qwen_api_key(env_file=self.path, environ={}))

    def test_file_rejects_missing_duplicate_empty_expansion_and_malformed_values(self):
        for text in ("OTHER=value", "DASHSCOPE_API_KEY=", "DASHSCOPE_API_KEY='mismatch",
                     "DASHSCOPE_API_KEY=$(command)", "DASHSCOPE_API_KEY=has spaces",
                     "DASHSCOPE_API_KEY=no\nDASHSCOPE_API_KEY=yes", "DASHSCOPE_API_KEY value"):
            with self.subTest(text=text):
                self.write(text)
                with self.assertRaises(LandingProviderError) as error:
                    live.qwen_api_key(env_file=self.path, environ={QWEN_API_KEY_ENV: self.value})
                self.assertEqual("credential_file_invalid", str(error.exception))

    def test_private_file_mode_symlink_size_and_path_rejection(self):
        self.write(f"DASHSCOPE_API_KEY={self.value}")
        self.path.chmod(0o644)
        with self.assertRaises(SettingsError):
            live.qwen_api_key(env_file=self.path)
        self.path.chmod(0o600)
        link = self.root / "link"
        link.symlink_to(self.path)
        for path in (link, Path("relative"), Path("/" + str(self.path))):
            with self.subTest(path=path), self.assertRaises(SettingsError):
                live.qwen_api_key(env_file=path)
        self.write("x" * 16_385)
        with self.assertRaises(SettingsError):
            live.qwen_api_key(env_file=self.path)

    def test_environment_alias_has_explicit_project_key_precedence(self):
        standard = uuid4().hex
        self.assertEqual(standard, live.qwen_api_key(environ={"DASHSCOPE_API_KEY": standard}))
        self.assertEqual(self.value, live.qwen_api_key(environ={"DASHSCOPE_API_KEY": standard, QWEN_API_KEY_ENV: self.value}))
        with self.assertRaises(LandingProviderError):
            live.qwen_api_key(environ={"DASHSCOPE_API_KEY": standard, QWEN_API_KEY_ENV: ""})

    def test_qwen_intl_is_pinned_and_distinct_from_existing_china_profile(self):
        profile = HttpLandingProfile.for_provider("qwen-intl", available=True)
        self.assertEqual("https://dashscope-intl.aliyuncs.com/compatible-mode/v1", profile.base_url)
        self.assertEqual("qwen-plus", profile.model_id)
        self.assertEqual(False, profile.to_facts()["enable_thinking"])
        self.assertEqual("json_object", profile.to_facts()["response_format"])
        self.assertNotIn("enable_thinking", HttpLandingProfile.for_provider("qwen").to_facts())
        self.assertNotEqual(HttpLandingProfile.for_provider("qwen", available=True).profile_digest, profile.profile_digest)
        with self.assertRaises(LandingProviderError):
            replace(profile, base_url="https://example.com/v1")

    def test_probe_uses_real_executor_decoder_and_reports_only_safe_facts(self):
        self.write(f"DASHSCOPE_API_KEY={self.value}")
        requests = []
        def handler(request):
            requests.append(request)
            body = json.loads(request.content)
            self.assertFalse(body["enable_thinking"])
            self.assertFalse(body["stream"])
            return _transport("qwen-plus").handle_request(request)
        result = live.probe_qwen(qwen_env_file=self.path, transport=httpx.MockTransport(handler))
        self.assertEqual("normalized", result["state"])
        self.assertEqual("qwen-intl", result["profile_id"])
        self.assertEqual((12, 34), (result["usage_input_units"], result["usage_output_units"]))
        self.assertEqual(1, len(requests))
        self.assertEqual("dashscope-intl.aliyuncs.com", requests[0].url.host)
        self.assertNotIn(self.value, json.dumps(result))
        self.assertEqual(64, len(result["spec_digest"]))

    def test_probe_cli_failure_never_prints_exception_or_credential(self):
        output = io.StringIO()
        with patch("sys.argv", ["probe", "--profile", "qwen-intl"]), patch.object(
            live, "probe_qwen", side_effect=LandingProviderError(self.value)
        ), redirect_stdout(output):
            self.assertEqual(1, live.main())
        self.assertEqual({"state": "failed", "reason": "qwen_probe_failed",
                          "category": "protocol", "http_status": None}, json.loads(output.getvalue()))
        self.assertNotIn(self.value, output.getvalue())

    def test_probe_cli_reports_authentication_class_without_the_body(self):
        output = io.StringIO()
        failure = live.HttpProviderFailure("executor_http", "authentication", 401)
        with patch("sys.argv", ["probe", "--profile", "qwen-omni-intl"]), patch.object(
            live, "probe_qwen", side_effect=failure
        ), redirect_stdout(output):
            self.assertEqual(1, live.main())
        printed = json.loads(output.getvalue())
        self.assertEqual({"state": "failed", "reason": "qwen_probe_failed",
                          "category": "authentication", "http_status": 401}, printed)
        self.assertNotIn(self.value, output.getvalue())
        self.assertNotIn("invalid_api_key", output.getvalue())

    def test_profile_facts_keep_the_backend_capability_contract_shape(self):
        # The v1 contract declares profiles as a closed enum of exact fact objects. The fitness
        # comparator cannot represent object-valued enum members, so the file is frozen and a new
        # profile cannot be added to the enum until issue #104 lands. Guard what stays guardable:
        # declared profiles stay real and byte-equal to their table facts, and an undeclared
        # profile must emit exactly the fact shape (key set and per-key JSON types) of a declared
        # sibling, so the new intl omni cannot drift from the grammar the contract describes.
        import json
        schema = json.loads((Path(live.__file__).parents[2]
                             / "contracts/jsonschema/landing-backend-capability.v1.schema.json").read_text())
        declared = {item["profile_id"]: item for item in schema["properties"]["profile"]["enum"]}
        self.assertEqual(set(), set(declared) - set(HTTP_PROFILES))
        for profile_id in HTTP_PROFILES:
            with self.subTest(profile=profile_id):
                facts = HttpLandingProfile.for_provider(profile_id, available=True).to_facts()
                if profile_id in declared:
                    self.assertEqual(declared[profile_id], facts)
                    continue
                twins = [item for item in declared.values() if sorted(item) == sorted(facts)]
                self.assertTrue(twins, "undeclared profile must reuse a declared fact shape exactly")
                twin = twins[0]
                for key, value in facts.items():
                    self.assertEqual(type(twin[key]).__name__, type(value).__name__, key)
                self.assertEqual(1, facts["schema_version"])

    def test_probe_failure_output_clamps_unknown_category_and_invalid_status(self):
        for category in ("DROP TABLE", "", None, 401, "permission_ok"):
            with self.subTest(category=category):
                fields = live._probe_failure_fields(live.HttpProviderFailure("executor_http", category, 403))
                self.assertEqual("protocol", fields["category"])
                self.assertEqual(403, fields["http_status"])
        for status in (0, 999, -1, "401", True, 1_000_000):
            with self.subTest(status=status):
                fields = live._probe_failure_fields(live.HttpProviderFailure("executor_http", "authentication", status))
                self.assertIsNone(fields["http_status"])
                self.assertEqual("authentication", fields["category"])
        # Classes the executor really produces must stay printable rather than collapse to protocol.
        for code, expected in (("executor_deadline", "deadline"), ("executor_transport", "transport"),
                               ("executor_usage", "accounting")):
            with self.subTest(code=code):
                self.assertEqual(expected, live._probe_failure_fields(LandingProviderError(code))["category"])

    def test_provider_enumerations_stay_subsets_of_the_profile_table(self):
        self.assertEqual(set(), set(live.PROBE_PROFILES) - set(HTTP_PROFILES))
        self.assertEqual(set(), set(LANDING_PROVIDERS) - set(HTTP_PROFILES) - {"unavailable"})

    def test_failover_chain_excludes_both_omni_profiles(self):
        # AC-003/FORBID-003: adding a profile must not silently join the durable failover chain.
        self.assertEqual(("qwen-intl", "grok-vision", "openai", "anthropic", "openrouter"), PROVIDER_ORDER)
        for name in ("qwen-omni", "qwen-omni-intl"):
            self.assertNotIn(name, PROVIDER_ORDER)

    def test_international_omni_profile_is_streaming_and_five_media(self):
        profile = HttpLandingProfile.for_provider("qwen-omni-intl", available=True)
        self.assertEqual("qwen", profile.provider_id)
        self.assertEqual("https://dashscope-intl.aliyuncs.com/compatible-mode/v1", profile.base_url)
        self.assertEqual("qwen3.5-omni-plus-2026-03-15", profile.model_id)
        self.assertTrue(profile.streaming)
        self.assertEqual(("audio", "docx", "image", "pdf", "text"), profile.media_kinds)
        # The mainland omni profile keeps its own endpoint and every existing digest.
        self.assertEqual("https://dashscope.aliyuncs.com/compatible-mode/v1",
                         HttpLandingProfile.for_provider("qwen-omni").base_url)
        self.assertNotEqual(profile.profile_digest,
                            HttpLandingProfile.for_provider("qwen-omni", available=True).profile_digest)

    def test_environment_composition_accepts_both_omni_profiles(self):
        # A selected profile must survive the provider gate and fail later, on the paths the
        # test does not supply; only an unknown name may be refused as a provider.
        for name in ("qwen-omni", "qwen-omni-intl"):
            with self.assertRaises(LandingProviderError) as raised:
                live.compose_env_landing(blobs=object(), environ={
                    "FACTORY_LANDING_PROVIDER": name, "DASHSCOPE_API_KEY": self.value})
            self.assertEqual("landing_path", str(raised.exception))
        with self.assertRaises(LandingProviderError) as refused:
            live.compose_env_landing(blobs=object(), environ={
                "FACTORY_LANDING_PROVIDER": "qwen-never", "DASHSCOPE_API_KEY": self.value})
        self.assertEqual("landing_provider", str(refused.exception))
    def test_probe_rejects_malformed_draft_and_usage(self):
        self.write(f"DASHSCOPE_API_KEY={self.value}")
        for payload in ({"object": "chat.completion", "model": "qwen-plus", "choices": []},
                        {"object": "chat.completion", "model": "qwen-plus", "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "{}"}}], "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 4}}):
            with self.subTest(payload=payload), self.assertRaises(LandingProviderError):
                live.probe_qwen(qwen_env_file=self.path, transport=_transport("qwen-plus", payload=payload))

    def test_probe_rejects_invalid_draft_after_valid_http_envelope(self):
        self.write(f"DASHSCOPE_API_KEY={self.value}")
        payload = {
            "object": "chat.completion", "model": "qwen-plus",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": "{}"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        }
        with self.assertRaisesRegex(LandingProviderError, "draft_fields"):
            live.probe_qwen(qwen_env_file=self.path, transport=_transport("qwen-plus", payload=payload))

    def test_malformed_provider_unicode_is_closed_at_decoder_and_probe_cli(self):
        self.write(f"DASHSCOPE_API_KEY={self.value}")
        payload = {
            "object": "chat.completion", "model": "qwen-plus",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": "\ud800"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        }
        # Escaping the surrogate models valid response JSON carrying invalid
        # Unicode text; the response still passes identity and usage checks.
        raw = json.dumps(payload).encode()
        transport = httpx.MockTransport(lambda request: httpx.Response(
            200, headers={"content-type": "application/json"}, stream=httpx.ByteStream(raw),
        ))
        executor = qwen_landing_executor(api_key=self.value, transport=transport)
        with self.assertRaisesRegex(LandingProviderError, "executor_result"):
            executor.run(_request(executor))
        real_probe = live.probe_qwen
        output = io.StringIO()
        with patch("sys.argv", ["probe", "--qwen-env-file", str(self.path)]), patch.object(
            live, "probe_qwen", side_effect=lambda **kwargs: real_probe(**kwargs, transport=transport)
        ), redirect_stdout(output):
            self.assertEqual(1, live.main())
        self.assertEqual({"state": "failed", "reason": "qwen_probe_failed",
                          "category": "protocol", "http_status": None}, json.loads(output.getvalue()))


if __name__ == "__main__":
    unittest.main()
