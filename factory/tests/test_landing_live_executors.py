"""Grok/Qwen live executors; HTTP is mocked and never leaves process."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

import httpx

from adaptive_factory.landing_artifact import DEPLOY_MEMBERS
from adaptive_factory.landing_intake import PrivateLandingBlobStore
from adaptive_factory.landing_live_executors import (
    CURRENT_LANDING_HOST_REQUIREMENTS,
    CURRENT_PYTHON_SHA256,
    GROK_API_KEY_ENV,
    OpenAICompatibleLandingExecutor,
    QWEN_API_KEY_ENV,
    api_key_from_environ,
    compose_landing_live_grok,
    compose_landing_live_qwen,
    grok_landing_executor,
    qwen_landing_executor,
)
from adaptive_factory.landing_normalizer import (
    LANDING_NORMALIZATION_DRAFT_SCHEMA_SHA256,
    LANDING_NORMALIZER_PROMPT_SHA256,
    CodexExecutionRequest,
    CodexLandingProfile,
)
from adaptive_factory.landing_provider import LandingProviderError
from adaptive_factory.landing_renderer import TARGET_REPOSITORY_ID
from adaptive_factory.landing_runtime import implemented_live_binding
from adaptive_factory.models import Actor
from factory.tests.test_landing_normalizer import draft
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
        if payload is not None:
            return httpx.Response(status, json=payload)
        return httpx.Response(
            status,
            json={"choices": [{"message": {"content": draft().decode("utf-8")}}]},
        )

    return httpx.MockTransport(handler)


def _request() -> CodexExecutionRequest:
    stdin = json.dumps(
        {"instruction": "return landing json", "request": {"media_kind": "text"}},
        ensure_ascii=False,
    ).encode("utf-8")
    return CodexExecutionRequest(
        profile_digest="a" * 64,
        argv=("unused",),
        stdin=stdin,
        image_bytes=None,
        timeout_seconds=30,
        max_stdout_bytes=262_144,
        max_stderr_bytes=65_536,
    )


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
        self.assertEqual("base_url", str(raised.exception))

    def test_grok_mock_transport_returns_draft_json(self) -> None:
        executor = grok_landing_executor(api_key="test-grok", transport=_transport("grok-4"))
        result = executor.run(_request())
        self.assertEqual(0, result.exit_code)
        self.assertEqual(draft(), result.stdout)

    def test_qwen_mock_transport_returns_draft_json(self) -> None:
        executor = qwen_landing_executor(api_key="test-qwen", transport=_transport("qwen-plus"))
        self.assertEqual(draft(), executor.run(_request()).stdout)

    def test_http_error_status_fails_closed(self) -> None:
        executor = grok_landing_executor(
            api_key="test-grok",
            transport=_transport("grok-4", status=500, payload={"error": "no"}),
        )
        with self.assertRaises(LandingProviderError) as raised:
            executor.run(_request())
        self.assertEqual("executor_http", str(raised.exception))

    def test_transport_error_fails_closed(self) -> None:
        class Boom(httpx.BaseTransport):
            def handle_request(self, request: httpx.Request) -> httpx.Response:
                raise httpx.ConnectError("boom", request=request)

        executor = grok_landing_executor(api_key="test-grok", transport=Boom())
        with self.assertRaises(LandingProviderError) as raised:
            executor.run(_request())
        self.assertEqual("executor_transport", str(raised.exception))

    def test_malformed_body_fails_closed(self) -> None:
        executor = qwen_landing_executor(
            api_key="test-qwen",
            transport=_transport("qwen-plus", payload={"choices": []}),
        )
        with self.assertRaises(LandingProviderError) as raised:
            executor.run(_request())
        self.assertEqual("executor_result", str(raised.exception))


class LandingLiveGrokQwenCompositionTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="landing-live-llm-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.executable = self.root / "codex"
        self.executable.write_bytes(b"sealed-codex-fixture")
        self.executable.chmod(0o700)
        (self.root / "blobs").mkdir(mode=0o700)
        (self.root / "scratch").mkdir(mode=0o700)
        (self.root / "artifacts").mkdir(mode=0o700)
        self.actor = Actor(
            "tenant-1",
            "operator",
            frozenset({"landing:submit", "landing:read"}),
            frozenset({TARGET_REPOSITORY_ID}),
        )
        self.blobs = PrivateLandingBlobStore(
            self.root / "blobs",
            repository_root=REPO_ROOT,
        )

    def _profile(self) -> CodexLandingProfile:
        return CodexLandingProfile.from_facts(
            {
                "schema_version": 1,
                "profile_id": "codex-landing-offline-fixture",
                "provider_id": "codex-offline-fixture",
                "model_id": "fixture-model-v1",
                "cli_version": "0.153.4",
                "executable": str(self.executable),
                "executable_sha256": hashlib.sha256(self.executable.read_bytes()).hexdigest(),
                "prompt_template_digest": LANDING_NORMALIZER_PROMPT_SHA256,
                "tool_policy_digest": "3" * 64,
                "output_schema_digest": LANDING_NORMALIZATION_DRAFT_SCHEMA_SHA256,
                "decoder_digest": "5" * 64,
                "timeout_seconds": 30,
                "max_stdout_bytes": 262_144,
                "max_stderr_bytes": 65_536,
                "available": True,
            }
        )

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
                profile=self._profile(),
                source_repository=target,
                scratch_root=self.root / "scratch",
                output_directory=self.root / "artifacts",
                blobs=self.blobs,
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
            self.assertIsNone(created.job.result_view()["live_url"])
            self.assertEqual(
                tuple(sorted(DEPLOY_MEMBERS)),
                created.job.sealed_artifact.member_names,
            )


if __name__ == "__main__":
    unittest.main()
