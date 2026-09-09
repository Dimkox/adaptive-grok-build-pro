from __future__ import annotations

import json
import uuid
from datetime import timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from .demo import DemoApplication


MAX_BODY_BYTES = 16 * 1024
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
    "form-action 'self'"
)
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/assets/app.css": ("assets/app.css", "text/css; charset=utf-8"),
    "/assets/api.js": ("assets/api.js", "text/javascript; charset=utf-8"),
    "/assets/render.js": ("assets/render.js", "text/javascript; charset=utf-8"),
    "/assets/app.js": ("assets/app.js", "text/javascript; charset=utf-8"),
}


def _duplicate_reject(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


class DemoHTTPServer(HTTPServer):
    def __init__(self, address, app: DemoApplication, asset_root: Path):
        self.app = app
        self.asset_root = asset_root
        super().__init__(address, DemoRequestHandler)


class DemoRequestHandler(BaseHTTPRequestHandler):
    server: DemoHTTPServer
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _security_headers(self) -> None:
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")

    def _send_bytes(self, status: int, body: bytes, content_type: str, *, allow: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if allow is not None:
            self.send_header("Allow", allow)
        self._security_headers()
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, status: int, value: dict[str, Any], *, allow: str | None = None) -> None:
        body = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        self._send_bytes(status, body, "application/json; charset=utf-8", allow=allow)

    def _error(self, status: int, code: str, message: str, *, retryable: bool = False, allow: str | None = None) -> None:
        now = self.server.app.now_provider().astimezone(timezone.utc)
        self._send_json(
            status,
            {
                "schema_version": 1,
                "request_id": uuid.uuid4().hex,
                "generated_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
                "external_writes": False,
                "error": {"code": code, "message": message, "retryable": retryable},
            },
            allow=allow,
        )

    def _origin_allowed(self) -> bool:
        expected_host = f"127.0.0.1:{self.server.server_port}"
        if self.headers.get("Host") != expected_host:
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin == f"http://{expected_host}"

    def _guard_origin(self) -> bool:
        if self._origin_allowed():
            return True
        self._error(403, "forbidden_request", "Request origin is not allowed.")
        return False

    def do_GET(self) -> None:  # noqa: N802
        if not self._guard_origin():
            return
        if self.path == "/api/v1/health":
            self._send_json(200, self.server.app.health())
            return
        if self.path == "/api/v1/snapshot":
            self._send_json(200, self.server.app.snapshot())
            return
        if self.path == "/api/v1/preview":
            self._error(405, "method_not_allowed", "Method is not allowed.", allow="POST")
            return
        static = STATIC_FILES.get(self.path)
        if static is not None:
            relative, content_type = static
            try:
                body = (self.server.asset_root / relative).read_bytes()
            except OSError:
                self._error(503, "snapshot_unavailable", "Dashboard asset is unavailable.", retryable=True)
                return
            self._send_bytes(200, body, content_type)
            return
        self._error(404, "not_found", "Resource was not found.")

    def do_POST(self) -> None:  # noqa: N802
        if not self._guard_origin():
            return
        if self.path != "/api/v1/preview":
            self._error(404, "not_found", "Resource was not found.")
            return
        if self.headers.get("X-Adaptive-Demo") != "1":
            self._error(403, "forbidden_request", "Demo request header is required.")
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._error(415, "unsupported_media_type", "Content-Type must be application/json.")
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._error(400, "invalid_json", "A valid JSON body is required.")
            return
        if length < 0 or length > MAX_BODY_BYTES:
            self._error(413, "payload_too_large", "Request body exceeds 16 KiB.")
            return
        body = self.rfile.read(length)
        if len(body) != length:
            self._error(400, "invalid_json", "A valid JSON body is required.")
            return
        try:
            value = json.loads(body.decode("utf-8", errors="strict"), object_pairs_hook=_duplicate_reject)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            self._error(400, "invalid_json", "A valid JSON object is required.")
            return
        if not isinstance(value, dict) or set(value) != {"schema_version", "prompt"} or value.get("schema_version") != 1:
            self._error(422, "invalid_prompt", "Preview fields or schema version are invalid.")
            return
        try:
            result = self.server.app.preview(value.get("prompt"))
        except (TypeError, ValueError):
            self._error(422, "invalid_prompt", "Prompt must contain 1 to 4000 characters.")
            return
        except (OSError, RuntimeError):
            self._error(500, "internal_error", "Preview could not be computed.", retryable=True)
            return
        self._send_json(200, result)

    def _method_not_allowed(self) -> None:
        if not self._guard_origin():
            return
        self._error(405, "method_not_allowed", "Method is not allowed.", allow="GET, POST")

    do_PUT = _method_not_allowed
    do_PATCH = _method_not_allowed
    do_DELETE = _method_not_allowed
    do_OPTIONS = _method_not_allowed
    do_HEAD = _method_not_allowed


def create_server(
    root: Path,
    *,
    port: int = 8765,
    now_provider=None,
) -> DemoHTTPServer:
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")
    app = DemoApplication(root, now_provider=now_provider)
    asset_root = app.root / ".grok-stack/demo"
    return DemoHTTPServer(("127.0.0.1", port), app, asset_root)
