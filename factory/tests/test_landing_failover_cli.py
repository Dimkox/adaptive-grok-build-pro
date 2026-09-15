"""Real Unix-socket caller path, process absence, and CLI redaction."""

from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler
import io
import json
from pathlib import Path
import socketserver
import tempfile
import threading
import unittest

from adaptive_factory.contracts import canonical_json
from adaptive_factory.landing_failover import FailoverCoordinator
from adaptive_factory.landing_failover_cli import main
from adaptive_factory.landing_failover_config import FailoverConfig
from adaptive_factory.landing_failover_journal import CallerJournal
from factory.tests.test_landing_failover import configuration, ScriptedBackends


class UnixCallerTests(unittest.TestCase):
    def test_absent_primary_real_unix_secondary_lost_post_recovers_existing_winner(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = configuration(root, count=2)
            # systemd removes RuntimeDirectory on service stop; the whole
            # primary socket parent may be absent before config is loaded.
            document["backends"][0]["socket_path"] = str(root / "run" / "stopped-primary" / "control.sock")
            config = FailoverConfig.from_dict(document)
            for backend in config.backends:
                backend.token_file.write_text("t" * 32)
                backend.token_file.chmod(0o600)
            script = ScriptedBackends({"grok-vision": "success"})
            secondary = script.factory(config.backends[1], config=config)
            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass
                def do_GET(self):
                    payload = secondary.capability() if self.path == "/v2/landing-backend" else secondary.observe(self.path.split("/")[3])
                    raw = canonical_json(payload)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                def do_POST(self):
                    self.server.expected_headers = (self.headers.get("X-Expected-Actor-ID"), self.headers.get("X-Expected-Profile-Digest"))
                    payload = self.rfile.read(int(self.headers["Content-Length"]))
                    secondary.submit(self.headers["Idempotency-Key"], payload, self.headers["Content-Type"])
                    # The provider result is committed, but the caller loses HTTP202.
                    self.close_connection = True
                    self.connection.close()
            server = socketserver.UnixStreamServer(str(config.backends[1].socket_path), Handler)
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
            thread.start()
            try:
                with CallerJournal(config) as journal:
                    caller = FailoverCoordinator(config, journal)
                    result = caller.submit("real-unix", b"private synthetic source", "text/plain")
                    self.assertEqual("artifact_ready", result["state"])
                    self.assertEqual("not_submitted", result["attempts"][0]["state"])
                    self.assertEqual("grok", result["winner"]["provider_id"])
                    self.assertEqual(["grok-vision"], script.calls)
                    self.assertEqual((config.actor_id, config.backends[1].profile_digest), server.expected_headers)
                    self.assertEqual(result, caller.resume("real-unix"))
                    self.assertEqual(["grok-vision"], script.calls)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)

    def test_cli_all_absent_has_five_slots_and_never_prints_input_or_tokens(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = configuration(root)
            for item in config["backends"]:
                leaf = Path(item["token_file"])
                leaf.write_text("secret" * 8)
                leaf.chmod(0o600)
            config_path = root / "config.json"
            config_path.write_text(json.dumps(config))
            config_path.chmod(0o600)
            payload = root / "brief.txt"
            payload.write_text("private source must not be logged")
            payload.chmod(0o600)
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(["--config", str(config_path), "submit", "--job-id", "cli-test", "--input", str(payload)])
            result = json.loads(output.getvalue())
            self.assertEqual(2, code)
            self.assertEqual("exhausted", result["state"])
            self.assertEqual(5, len(result["attempts"]))
            self.assertNotIn(payload.read_text(), output.getvalue())
            self.assertNotIn("secret" * 8, output.getvalue())


if __name__ == "__main__":
    unittest.main()
