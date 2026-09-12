from __future__ import annotations

import http.client
import importlib
import json
import subprocess
import sys
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))
NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)


def _runtime_snapshot() -> tuple[tuple[str, bytes, int], ...]:
    runtime = ROOT / ".grok-stack/runtime"
    return tuple(
        (path.relative_to(runtime).as_posix(), path.read_bytes(), path.stat().st_mtime_ns)
        for path in sorted(runtime.rglob("*"))
        if path.is_file()
    )


class RunningDemo:
    def __enter__(self):
        try:
            module = importlib.import_module("adaptive_grok.demo_http")
        except ModuleNotFoundError:
            raise AssertionError("adaptive_grok.demo_http must provide the loopback API") from None
        self.server = module.create_server(ROOT, port=0, now_provider=lambda: NOW)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, method: str, path: str, body: bytes | None = None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        request_headers = dict(headers or {})
        request_headers.setdefault("Host", f"127.0.0.1:{self.port}")
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        data = response.read()
        values = {name.lower(): value for name, value in response.getheaders()}
        connection.close()
        return response.status, values, data


class DemoHttpTests(unittest.TestCase):
    def test_health_snapshot_and_preview_endpoints_have_closed_shapes(self) -> None:
        with RunningDemo() as demo:
            status, headers, raw = demo.request("GET", "/api/v1/health")
            self.assertEqual(status, 200)
            self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
            health = json.loads(raw)
            self.assertEqual(health["status"], "ready")
            self.assertFalse(health["external_writes"])

            status, _, raw = demo.request("GET", "/api/v1/snapshot")
            self.assertEqual(status, 200)
            snapshot = json.loads(raw)
            self.assertEqual(snapshot["mode"], "bundled_sample")

            payload = json.dumps({"schema_version": 1, "prompt": "Add a responsive API dashboard"}).encode()
            status, _, raw = demo.request(
                "POST",
                "/api/v1/preview",
                payload,
                {"Content-Type": "application/json", "X-Adaptive-Demo": "1"},
            )
            self.assertEqual(status, 200)
            preview = json.loads(raw)
            self.assertEqual(preview["mode"], "computed_preview")
            self.assertEqual(preview["verification"]["status"], "not_run")

    def test_security_headers_are_present_and_cors_is_absent_on_success_and_error(self) -> None:
        with RunningDemo() as demo:
            for method, path in (("GET", "/api/v1/health"), ("GET", "/missing")):
                status, headers, _ = demo.request(method, path)
                self.assertIn(status, (200, 404))
                self.assertIn("default-src 'self'", headers["content-security-policy"])
                self.assertEqual(headers["x-content-type-options"], "nosniff")
                self.assertEqual(headers["referrer-policy"], "no-referrer")
                self.assertEqual(headers["cache-control"], "no-store")
                self.assertNotIn("access-control-allow-origin", headers)

    def test_dashboard_and_only_allowlisted_assets_are_served(self) -> None:
        with RunningDemo() as demo:
            expected = {
                "/": "text/html; charset=utf-8",
                "/assets/app.css": "text/css; charset=utf-8",
                "/assets/api.js": "text/javascript; charset=utf-8",
                "/assets/render.js": "text/javascript; charset=utf-8",
                "/assets/app.js": "text/javascript; charset=utf-8",
            }
            for path, content_type in expected.items():
                status, headers, body = demo.request("GET", path)
                self.assertEqual(status, 200, path)
                self.assertEqual(headers["content-type"], content_type)
                self.assertTrue(body)

    def test_host_origin_content_type_and_custom_header_are_enforced(self) -> None:
        with RunningDemo() as demo:
            payload = b'{"schema_version":1,"prompt":"hello"}'
            cases = (
                ({"Host": "evil.example"}, 403, "forbidden_request"),
                ({"Origin": "https://evil.example"}, 403, "forbidden_request"),
                ({"Content-Type": "text/plain", "X-Adaptive-Demo": "1"}, 415, "unsupported_media_type"),
                ({"Content-Type": "application/json"}, 403, "forbidden_request"),
            )
            for headers, expected, code in cases:
                status, _, raw = demo.request("POST", "/api/v1/preview", payload, headers)
                self.assertEqual(status, expected)
                self.assertEqual(json.loads(raw)["error"]["code"], code)

            origin = f"http://127.0.0.1:{demo.port}"
            status, _, _ = demo.request(
                "POST",
                "/api/v1/preview",
                payload,
                {"Origin": origin, "Content-Type": "application/json", "X-Adaptive-Demo": "1"},
            )
            self.assertEqual(status, 200)

    def test_preview_rejects_malformed_duplicate_unknown_control_and_oversized_input(self) -> None:
        with RunningDemo() as demo:
            headers = {"Content-Type": "application/json", "X-Adaptive-Demo": "1"}
            cases = (
                (b"{", 400, "invalid_json"),
                (b'{"schema_version":1,"prompt":"a","prompt":"b"}', 400, "invalid_json"),
                (b'{"schema_version":1,"prompt":"a","path":"/tmp"}', 422, "invalid_prompt"),
                (b'{"schema_version":2,"prompt":"a"}', 422, "invalid_prompt"),
                (b'{"schema_version":1,"prompt":""}', 422, "invalid_prompt"),
                (b'{"schema_version":1,"prompt":"a\\u0000b"}', 422, "invalid_prompt"),
                (b"\xff", 400, "invalid_json"),
                (b" " * 16385, 413, "payload_too_large"),
            )
            for payload, expected, code in cases:
                status, _, raw = demo.request("POST", "/api/v1/preview", payload, headers)
                self.assertEqual(status, expected, payload[:80])
                self.assertEqual(json.loads(raw)["error"]["code"], code)

    def test_methods_versions_and_traversal_are_not_exposed(self) -> None:
        with RunningDemo() as demo:
            for path in (
                "/api/v2/health", "/assets/../sample/task.json", "/assets/%2e%2e/task.json",
                "/assets//app.js", "/assets/%5capp.js", "/assets/app.js?file=../task.json",
                "/assets/", "/favicon.ico",
            ):
                status, _, raw = demo.request("GET", path)
                self.assertEqual(status, 404, path)
                self.assertEqual(json.loads(raw)["error"]["code"], "not_found")
            for method in ("PUT", "PATCH", "DELETE", "OPTIONS"):
                status, headers, raw = demo.request(method, "/api/v1/preview")
                self.assertEqual(status, 405)
                self.assertEqual(headers["allow"], "GET, POST")
                self.assertEqual(json.loads(raw)["error"]["code"], "method_not_allowed")

    def test_application_and_server_initialization_do_not_run_subprocesses(self) -> None:
        demo = importlib.import_module("adaptive_grok.demo")
        demo_http = importlib.import_module("adaptive_grok.demo_http")
        server = None
        with patch.object(subprocess, "run", side_effect=AssertionError("demo initialization invoked subprocess")):
            try:
                app = demo.DemoApplication(ROOT, now_provider=lambda: NOW)
                server = demo_http.create_server(ROOT, port=0, now_provider=lambda: NOW)
            except AssertionError as exc:
                self.fail(str(exc))
            finally:
                if server is not None:
                    server.server_close()
        self.assertEqual(app.snapshot()["mode"], "bundled_sample")
        self.assertEqual(server.app.snapshot()["mode"], "bundled_sample")

    def test_requests_do_not_run_subprocesses_or_mutate_runtime_state(self) -> None:
        before = _runtime_snapshot()
        with RunningDemo() as demo:
            payload = json.dumps({"schema_version": 1, "prompt": "Add a local API view"}).encode()
            with patch.object(subprocess, "run", side_effect=AssertionError("request invoked subprocess")):
                for method, path, body, headers in (
                    ("GET", "/api/v1/snapshot", None, None),
                    ("POST", "/api/v1/preview", payload, {"Content-Type": "application/json", "X-Adaptive-Demo": "1"}),
                ):
                    status, _, _ = demo.request(method, path, body, headers)
                    self.assertEqual(status, 200)
        self.assertEqual(_runtime_snapshot(), before)

    def test_launcher_help_and_openapi_contract_exist(self) -> None:
        launcher = ROOT / "scripts/grok_demo.py"
        self.assertTrue(launcher.is_file(), "one-command launcher is required")
        result = subprocess.run(
            [sys.executable, str(launcher), "--help"], cwd=ROOT, text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--open", result.stdout)
        self.assertIn("--port", result.stdout)

        contract_path = ROOT / "engineering/contracts/openapi/adaptive-demo.v1.json"
        self.assertTrue(contract_path.is_file(), "OpenAPI v1 contract is required")
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        self.assertEqual(contract["openapi"], "3.1.0")
        self.assertEqual(set(contract["paths"]), {
            "/api/v1/health", "/api/v1/snapshot", "/api/v1/preview",
        })
        self.assertEqual(set(contract["paths"]["/api/v1/preview"]), {"post"})


if __name__ == "__main__":
    unittest.main()
