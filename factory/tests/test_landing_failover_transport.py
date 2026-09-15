"""Real Unix I/O deadlines and recovery after an interrupted HTTP exchange."""

from contextlib import contextmanager
from pathlib import Path
import socketserver
import tempfile
import threading
import time
import unittest

from adaptive_factory.contracts import canonical_json
from adaptive_factory.landing_failover import FailoverCoordinator
from adaptive_factory.landing_failover_config import FailoverConfig
from adaptive_factory.landing_failover_journal import CallerJournal
from adaptive_factory.landing_failover_transport import BackendAmbiguous, BackendUnavailable, UnixLandingBackend
from factory.tests.test_landing_failover import configuration, ScriptedBackends


@contextmanager
def unix_responder(path, respond):
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            try:
                line = self.rfile.readline().decode("ascii").split()
                if not line:
                    return
                method, target, _ = line
                headers = {}
                while (line := self.rfile.readline()) not in (b"\r\n", b""):
                    key, value = line.decode("ascii").split(":", 1)
                    headers[key.lower()] = value.strip()
                self.server.requests.append((method, target, headers))
                respond(self, method, target, headers)
            except (BrokenPipeError, ConnectionResetError):
                pass  # The deadline cancels and closes the client socket.
    server = socketserver.ThreadingUnixStreamServer(str(path), Handler)
    server.requests = []
    server.stop = threading.Event()
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
    thread.start()
    try:
        yield server
    finally:
        server.stop.set()
        server.shutdown()
        server.server_close()
        thread.join(2)


def json_reply(handler, value, status=200):
    raw = canonical_json(value)
    handler.wfile.write(f"HTTP/1.1 {status} OK\r\nContent-Type: application/json\r\nContent-Length: {len(raw)}\r\nConnection: close\r\n\r\n".encode() + raw)


def trickle_headers(handler, status=200):
    handler.wfile.write(f"HTTP/1.1 {status} OK\r\nX-Trickle: ".encode())
    for _ in range(40):
        if handler.server.stop.wait(0.1):
            return
        handler.wfile.write(b"a")
    handler.wfile.write(b"\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}")


class UnixDeadlineTests(unittest.TestCase):
    def fixture(self, root):
        config = FailoverConfig.from_dict(configuration(root, count=2))
        for backend in config.backends:
            backend.token_file.write_text("t" * 32)
            backend.token_file.chmod(0o600)
        return config

    def test_real_exchange_cancels_headers_body_and_blocked_request_writes(self):
        for operation, mode in (("capability", "headers"), ("submit", "headers"),
                                ("observe", "headers"), ("observe", "body"), ("submit", "write")):
            with self.subTest(operation=operation, mode=mode), tempfile.TemporaryDirectory() as temporary:
                config = self.fixture(Path(temporary))
                def respond(handler, method, target, headers):
                    if mode == "write":
                        handler.server.stop.wait(2)
                    elif mode == "headers":
                        trickle_headers(handler, 202 if method == "POST" else 200)
                    else:
                        handler.wfile.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 42\r\n\r\n")
                        for _ in range(40):
                            if handler.server.stop.wait(0.1):
                                return
                            handler.wfile.write(b" ")
                        handler.wfile.write(b"{}")
                with unix_responder(config.backends[0].socket_path, respond) as server:
                    backend = UnixLandingBackend(config.backends[0], config=config,
                                                 timeout_seconds=3 if operation == "capability" else 0.3)
                    started = time.monotonic()
                    try:
                        expected = BackendUnavailable if operation == "capability" else BackendAmbiguous
                        with self.assertRaises(expected):
                            if operation == "submit":
                                backend.submit("child", b"x" * 1_048_576 if mode == "write" else b"brief", "text/plain")
                            elif operation == "observe":
                                backend.observe("child")
                            else:
                                backend.capability()
                        self.assertLess(time.monotonic() - started, 2.8 if operation == "capability" else 1.2)
                        self.assertEqual(1, len(server.requests))
                        self.assertEqual("POST" if operation == "submit" else "GET", server.requests[0][0])
                    finally:
                        backend.close()

    def test_trickled_capability_selects_grok_without_primary_post(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            script = ScriptedBackends({"grok-vision": "success"})
            def factory(backend, **kwargs):
                return UnixLandingBackend(backend, **kwargs) if backend.profile_id == "qwen-intl" else script.factory(backend, **kwargs)
            with unix_responder(config.backends[0].socket_path, lambda handler, *_: trickle_headers(handler)) as server:
                with CallerJournal(config) as journal:
                    started = time.monotonic()
                    result = FailoverCoordinator(config, journal, backend_factory=factory).submit("slow-cap", b"brief", "text/plain")
                    self.assertLess(time.monotonic() - started, 2.8)
                    self.assertEqual("artifact_ready", result["state"])
                    self.assertEqual("grok", result["winner"]["provider_id"])
                    self.assertEqual("not_submitted", result["attempts"][0]["state"])
                    self.assertEqual(["grok-vision"], script.calls)
                    self.assertEqual(["GET"], [item[0] for item in server.requests])

    def test_trickled_post_response_resumes_same_child_without_second_post(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            script = ScriptedBackends({"qwen-intl": "success"})
            primary = script.factory(config.backends[0], config=config)
            def respond(handler, method, target, headers):
                if target == "/v2/landing-backend":
                    json_reply(handler, primary.capability())
                elif method == "POST":
                    payload = handler.rfile.read(int(headers["content-length"]))
                    primary.submit(headers["idempotency-key"], payload, headers["content-type"])
                    trickle_headers(handler, 202)
                else:
                    json_reply(handler, primary.observe(target.split("/")[3]))
            def factory(backend, **kwargs):
                return UnixLandingBackend(backend, config=config, timeout_seconds=0.3)
            with unix_responder(config.backends[0].socket_path, respond) as server:
                with CallerJournal(config) as journal:
                    caller = FailoverCoordinator(config, journal, backend_factory=factory)
                    uncertain = caller.submit("slow-post", b"brief", "text/plain")
                    self.assertEqual("needs_human", uncertain["state"])
                    self.assertEqual("dispatching", uncertain["attempts"][0]["state"])
                with CallerJournal(config) as journal:
                    result = FailoverCoordinator(config, journal, backend_factory=factory).resume("slow-post")
                    self.assertEqual("artifact_ready", result["state"])
                    self.assertEqual(uncertain["attempts"][0]["child_id"], result["winner"]["child_id"])
                    self.assertEqual(["qwen-intl"], script.calls)
                    self.assertEqual(1, sum(method == "POST" for method, *_ in server.requests))


if __name__ == "__main__":
    unittest.main()
