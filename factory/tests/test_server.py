import json
import os
from pathlib import Path
import socket
import stat
import tempfile
import unittest

from adaptive_factory.server import ServerError, load_actors, prepare_unix_socket


class ServerTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
