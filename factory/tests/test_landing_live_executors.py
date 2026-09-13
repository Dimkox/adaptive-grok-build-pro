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
from adaptive_factory.landing_http import HTTP_NORMALIZER_PROMPT, HTTP_PROTOCOL_VERSION, HttpLandingProfile, HttpLandingExecutionRequest
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
        self.assertEqual({"state": "failed", "reason": "qwen_probe_failed"}, json.loads(output.getvalue()))
        self.assertNotIn(self.value, output.getvalue())

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
        self.assertEqual({"state": "failed", "reason": "qwen_probe_failed"}, json.loads(output.getvalue()))


if __name__ == "__main__":
    unittest.main()
