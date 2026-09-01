import json
import os
from pathlib import Path
import socket
import stat
import tempfile
import threading
import time
import unittest

import httpx
import uvicorn

from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.models import Actor
from adaptive_factory.server import ServerError, load_actors, prepare_unix_socket


class ServerTests(unittest.TestCase):
    def test_authenticated_request_reaches_real_unix_socket(self):
        class Service:
            @staticmethod
            def metrics(*, actor):
                return {"actor": actor.actor_id}

        token = "uds-operator-token-value"
        actor = Actor("uds-operator", "operator", frozenset({"factory:reconcile"}), frozenset({"*"}))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            path = root / "control.sock"
            listener = prepare_unix_socket(path)
            server = uvicorn.Server(
                uvicorn.Config(create_app(Service(), Authenticator({token: actor})), access_log=False, log_config=None)
            )
            thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
            thread.start()
            try:
                client = httpx.Client(transport=httpx.HTTPTransport(uds=str(path)), base_url="http://factory.local")
                deadline = time.monotonic() + 2
                while True:
                    try:
                        unauthorized = client.get("/metrics")
                        break
                    except httpx.ConnectError:
                        if time.monotonic() >= deadline:
                            self.fail("Unix socket server did not become ready")
                        time.sleep(0.02)
                self.assertEqual(unauthorized.status_code, 401)
                response = client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
                self.assertEqual(response.json(), {"actor": "uds-operator"})
                client.close()
            finally:
                server.should_exit = True
                thread.join(timeout=2)
                listener.close()

    def test_server_prepares_only_an_owned_mode_0660_unix_socket(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            path = root / "control.sock"
            listener = prepare_unix_socket(path)
            try:
                metadata = path.lstat()
                self.assertTrue(stat.S_ISSOCK(metadata.st_mode))
                self.assertEqual(stat.S_IMODE(metadata.st_mode), 0o660)
                self.assertEqual(metadata.st_uid, os.geteuid())
                self.assertEqual(listener.family, socket.AF_UNIX)
            finally:
                listener.close()
                path.unlink()
            regular = root / "not-a-socket"
            regular.write_text("do not replace", encoding="utf-8")
            with self.assertRaises(ServerError):
                prepare_unix_socket(regular)
            with self.assertRaises(ServerError):
                prepare_unix_socket(Path("relative.sock"))

    def test_actor_config_loads_no_follow_private_token_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            token = root / "worker.token"
            token.write_text("worker-token-value-123\n", encoding="utf-8")
            token.chmod(0o600)
            config = root / "actors.json"
            config.write_text(
                json.dumps({"actors": [{"actor_id": "worker", "kind": "worker", "scopes": ["task:claim"], "repositories": ["owner/repo"], "token_file": str(token)}]}),
                encoding="utf-8",
            )
            config.chmod(0o600)
            actors = load_actors(config)
            self.assertEqual(actors["worker-token-value-123"].actor_id, "worker")
            config.chmod(0o644)
            with self.assertRaises(ServerError):
                load_actors(config)

    def test_actor_config_rejects_relative_and_symlinked_ancestry(self):
        with self.assertRaises(ServerError):
            load_actors(Path("actors.json"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            private = root / "private"
            private.mkdir(mode=0o700)
            token = private / "token"
            token.write_text("actor-token-value-123\n", encoding="utf-8")
            token.chmod(0o600)
            config = private / "actors.json"
            config.write_text(
                json.dumps({"actors": [{
                    "actor_id": "actor", "kind": "operator", "scopes": ["factory:reconcile"],
                    "repositories": ["*"], "token_file": str(token),
                }]}),
                encoding="utf-8",
            )
            config.chmod(0o600)
            alias = root / "alias"
            alias.symlink_to(private, target_is_directory=True)
            with self.assertRaises(ServerError):
                load_actors(alias / "actors.json")


if __name__ == "__main__":
    unittest.main()
