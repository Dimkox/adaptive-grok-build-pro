"""Offline-only L5 host test scaffolding: private roots, synthetic actors, SQLite store.

This is test support, not a test module. It must import only the standard
library plus offline-safe product modules so dependency-free boundary suites
(backup/restore) can reuse the fixture without fastapi, uvicorn, httpx or
psycopg. The real-FastAPI half stays in ``factory/tests/test_landing_host.py``,
which subclasses this fixture and adds ``build_app``.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

from adaptive_factory.landing_renderer import TARGET_REPOSITORY_ID
from adaptive_factory.landing_sqlite_store import SQLiteLandingJobStore
from adaptive_factory.models import Actor


ROOT_FIELDS = (
    "state_path", "quarantine_path", "source_path", "scratch_path",
    "output_path", "publication_state_path", "control_repository",
)
PATH_FIELDS = (*ROOT_FIELDS, "actors_file", "socket_path")


class HostFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="landing-host-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config_path = self.root / "host.json"
        self.data = {
            "schema_version": 1,
            "live_enabled": False,
            "selected_profile": "qwen-omni",
            **{name: str(self.root / name) for name in PATH_FIELDS},
        }
        # The offline profile needs no source checkout. No real actor/key files
        # are used: the host's authentication boundary gets synthetic actors.
        for name in ROOT_FIELDS:
            if name != "source_path":
                Path(self.data[name]).mkdir(mode=0o700)
        self.token = uuid4().hex
        self.actors = {
            self.token: Actor("tenant-host", "client", frozenset({"landing:submit", "landing:read"}),
                         frozenset({TARGET_REPOSITORY_ID})),
        }
        self.write_config()

    def write_config(self, data=None, *, raw=None, path=None):
        target = path or self.config_path
        target.write_bytes(raw if raw is not None else json.dumps(self.data if data is None else data).encode())
        target.chmod(0o600)
        return target

    def reopen_store(self):
        store = SQLiteLandingJobStore(
            Path(self.data["state_path"]), repository_root=Path(self.data["control_repository"]),
        )
        self.addCleanup(store.close)
        return store
