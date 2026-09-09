from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from adaptive_factory.landing_contracts import LandingInputV1
from adaptive_factory.contracts import canonical_json
from adaptive_factory.landing_intake import PrivateLandingBlobStore
from adaptive_factory.landing_renderer import TARGET_REPOSITORY_ID
from adaptive_factory.landing_service import (
    LandingApplicationService,
    LandingJobRecord,
    LandingServiceError,
)
from adaptive_factory.landing_sqlite_store import SQLiteLandingJobStore
from adaptive_factory.models import Actor


REPOSITORY_ID = "github.com/Dimkox/ai-dark-factory-landing"
BASE_SHA = "699010380f4f90a0193a9c22090c35e6aded7d2c"
BASE_TREE = "f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4"


def source(
    *,
    tenant_id: str = "tenant-1",
    repository_id: str = REPOSITORY_ID,
    job_id: str = "job-1",
    payload: bytes = b"durable landing request",
) -> LandingInputV1:
    return LandingInputV1.from_facts(
        {
            "schema_version": 1,
            "job_id": job_id,
            "tenant_id": tenant_id,
            "repository_id": repository_id,
            "exact_base_sha": BASE_SHA,
            "exact_base_tree": BASE_TREE,
            "site_id": "therealaidarkfactory.online",
            "media_kind": "text",
            "media_type": "text/plain",
            "byte_length": len(payload),
            "content_sha256": hashlib.sha256(payload).hexdigest(),
            "quarantine_ref_digest": hashlib.sha256(
                b"quarantine:" + payload
            ).hexdigest(),
            "received_at": "2026-09-05T12:00:00Z",
            "expires_at": "2026-09-06T12:00:00Z",
        }
    )


class SQLiteLandingJobStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="landing-sqlite-")
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name)
        self.root = self.parent / "runtime"
        self.repository_root = Path(__file__).resolve().parents[2]

    def store(self, *, recovery_limit: int = 100) -> SQLiteLandingJobStore:
        value = SQLiteLandingJobStore(
            self.root,
            repository_root=self.repository_root,
            recovery_limit=recovery_limit,
            clock=lambda: datetime(2026, 9, 5, 12, 30, tzinfo=timezone.utc),
        )
        self.addCleanup(value.close)
        return value

    def _raw_database(self, root: Path) -> sqlite3.Connection:
        root.mkdir(mode=0o700)
        path = root / "landing.sqlite3"
        connection = sqlite3.connect(path)
        path.chmod(0o600)
        return connection

    def test_initializes_private_wal_full_schema_and_rejects_unsafe_or_unknown_root(self):
        store = self.store()
        self.assertEqual(0o700, os.stat(self.root).st_mode & 0o777)
        self.assertEqual(0o600, os.stat(store.database_path).st_mode & 0o777)
        with sqlite3.connect(store.database_path) as connection:
            self.assertEqual("wal", connection.execute("PRAGMA journal_mode").fetchone()[0])
            self.assertEqual(2, connection.execute("PRAGMA synchronous").fetchone()[0])
            self.assertEqual(1, connection.execute("PRAGMA user_version").fetchone()[0])
        store.close()

        with sqlite3.connect(store.database_path) as connection:
            connection.execute("PRAGMA user_version = 2")
        with self.assertRaisesRegex(LandingServiceError, "store_schema"):
            SQLiteLandingJobStore(
                self.root,
                repository_root=self.repository_root,
            )

        with self.assertRaisesRegex(LandingServiceError, "store_inside_repository"):
            SQLiteLandingJobStore(
                self.repository_root / "unsafe-landing-state",
                repository_root=self.repository_root,
            )
        link = self.parent / "runtime-link"
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(LandingServiceError, "store_symlink"):
            SQLiteLandingJobStore(link, repository_root=self.repository_root)
        linked_parent = self.parent / "linked-parent"
        linked_parent.symlink_to(self.parent / "real-parent", target_is_directory=True)
        (self.parent / "real-parent").mkdir()
        with self.assertRaisesRegex(LandingServiceError, "store_symlink"):
            SQLiteLandingJobStore(
                linked_parent / "nested",
                repository_root=self.repository_root,
            )

    def test_schema_identity_inventory_keys_foreign_key_and_strictness_are_exact(self):
        mixed = self.parent / "mixed"
        with self._raw_database(mixed) as connection:
            connection.execute("PRAGMA user_version = 1")
        with self.assertRaisesRegex(LandingServiceError, "store_schema"):
            SQLiteLandingJobStore(mixed, repository_root=self.repository_root)

        nonempty = self.parent / "nonempty"
        with self._raw_database(nonempty) as connection:
            connection.execute("CREATE TABLE unrelated (value TEXT)")
        with self.assertRaisesRegex(LandingServiceError, "store_schema"):
            SQLiteLandingJobStore(nonempty, repository_root=self.repository_root)

        drifted = self.parent / "drifted"
        valid = SQLiteLandingJobStore(drifted, repository_root=self.repository_root)
        valid.close()
        with sqlite3.connect(valid.database_path) as connection:
            connection.execute("ALTER TABLE landing_jobs ADD COLUMN unowned TEXT")
        with self.assertRaisesRegex(LandingServiceError, "store_schema"):
            SQLiteLandingJobStore(drifted, repository_root=self.repository_root)

    def test_decoded_source_is_bound_to_physical_row_identity(self):
        first = source(job_id="job-a", payload=b"first")
        second = source(tenant_id="tenant-2", job_id="job-b", payload=b"second")
        store = self.store()
        for item in (first, second):
            store.create_or_replay(
                LandingJobRecord(item, "accepted", None, None),
                command_key=item.job_id,
                request_digest=item.input_digest,
            )
        store.close()
        with sqlite3.connect(store.database_path) as connection:
            connection.execute(
                """UPDATE landing_jobs SET source_json = ?
                    WHERE tenant_id = ? AND repository_id = ? AND job_id = ?""",
                (
                    canonical_json(second.to_dict()),
                    first.tenant_id,
                    first.repository_id,
                    first.job_id,
                ),
            )
        reopened = self.store(recovery_limit=0)
        with self.assertRaisesRegex(LandingServiceError, "store_identity"):
            reopened.get(first.tenant_id, first.repository_id, first.job_id)

    def test_submit_and_terminal_replay_survive_restart_and_changed_material_conflicts(self):
        original = source()
        store = self.store()
        accepted, created = store.create_or_replay(
            LandingJobRecord(original, "accepted", None, None),
            command_key="job-1",
            request_digest=original.input_digest,
        )
        self.assertTrue(created)
        normalizing = store.put(replace(accepted, state="normalizing"))
        terminal = store.put(
            replace(
                normalizing,
                state="provider_unavailable",
                reason_code="profile_unavailable",
            )
        )
        store.close()

        reopened = self.store()
        replay, created = reopened.create_or_replay(
            LandingJobRecord(original, "accepted", None, None),
            command_key="job-1",
            request_digest=original.input_digest,
        )
        self.assertFalse(created)
        self.assertEqual(terminal, replay)

        changed = source(payload=b"different request")
        with self.assertRaisesRegex(LandingServiceError, "idempotency_conflict"):
            reopened.create_or_replay(
                LandingJobRecord(changed, "accepted", None, None),
                command_key="job-1",
                request_digest=changed.input_digest,
            )

    def test_cancel_replay_is_durable_full_key_bound_and_stale_writes_fail(self):
        original = source()
        store = self.store()
        accepted, _ = store.create_or_replay(
            LandingJobRecord(original, "accepted", None, None),
            command_key="job-1",
            request_digest=original.input_digest,
        )
        stale = accepted
        normalizing = store.put(replace(accepted, state="normalizing"))
        with self.assertRaisesRegex(LandingServiceError, "stale_job"):
            store.put(replace(stale, state="needs_human", reason_code="stale"))

        cancel_digest = hashlib.sha256(b"cancel:job-1").hexdigest()
        cancelled = store.cancel_or_replay(
            normalizing,
            command_key="cancel-1",
            request_digest=cancel_digest,
        )
        store.close()
        reopened = self.store()
        replay = reopened.cancel_or_replay(
            reopened.get("tenant-1", REPOSITORY_ID, "job-1"),
            command_key="cancel-1",
            request_digest=cancel_digest,
        )
        self.assertEqual(cancelled, replay)
        with self.assertRaisesRegex(LandingServiceError, "idempotency_conflict"):
            reopened.cancel_or_replay(
                replay,
                command_key="cancel-1",
                request_digest="f" * 64,
            )
        with self.assertRaisesRegex(LandingServiceError, "not_found"):
            reopened.get("tenant-2", REPOSITORY_ID, "job-1")
        with self.assertRaisesRegex(LandingServiceError, "not_found"):
            reopened.get("tenant-1", "other/repository", "job-1")

    def test_startup_recovery_is_bounded_and_never_replays_processing_work(self):
        store = self.store()
        pending = source(job_id="job-0", payload=b"accepted payload")
        store.create_or_replay(
            LandingJobRecord(pending, "accepted", None, None),
            command_key=pending.job_id,
            request_digest=pending.input_digest,
        )
        for index, state in enumerate(
            ("normalizing", "generating", "evaluating", "provider_unavailable"), 1
        ):
            item = source(job_id=f"job-{index}", payload=f"payload-{index}".encode())
            accepted, _ = store.create_or_replay(
                LandingJobRecord(item, "accepted", None, None),
                command_key=item.job_id,
                request_digest=item.input_digest,
            )
            current = accepted
            for transition in {
                "normalizing": ("normalizing",),
                "generating": ("normalizing", "generating"),
                "evaluating": ("normalizing", "generating", "evaluating"),
                "provider_unavailable": ("normalizing", "provider_unavailable"),
            }[state]:
                current = store.put(replace(current, state=transition))
        store.close()

        reopened = self.store(recovery_limit=3)
        accepted_after_restart = reopened.get(
            "tenant-1", REPOSITORY_ID, "job-0"
        )
        recovered = [
            reopened.get("tenant-1", REPOSITORY_ID, f"job-{index}")
            for index in range(1, 5)
        ]
        self.assertEqual("needs_human", accepted_after_restart.state)
        self.assertEqual(
            "input_unavailable_after_restart", accepted_after_restart.reason_code
        )
        self.assertEqual(2, sum(item.state == "needs_human" for item in recovered))
        self.assertEqual(1, sum(item.state in {"normalizing", "generating", "evaluating"} for item in recovered))
        self.assertEqual("provider_unavailable", recovered[-1].state)
        self.assertEqual("provider_outcome_ambiguous", recovered[0].reason_code)
        self.assertEqual("local_run_interrupted", recovered[1].reason_code)

    def test_recovered_submit_returns_terminal_without_provider_or_builder_replay(self):
        now = datetime(2026, 9, 5, 12, 30, tzinfo=timezone.utc)
        payload = b"crash-bound landing input"
        blobs = PrivateLandingBlobStore(
            self.parent / "blobs",
            repository_root=self.repository_root,
            clock=lambda: now,
        )
        stored_source = blobs.accept(
            job_id="job-recovered",
            tenant_id="tenant-1",
            repository_id=TARGET_REPOSITORY_ID,
            exact_base_sha=BASE_SHA,
            exact_base_tree=BASE_TREE,
            site_id="therealaidarkfactory.online",
            media_kind="text",
            media_type="text/plain",
            chunks=(payload,),
            received_at=now,
            expires_at=now.replace(day=6),
        )
        store = self.store()
        accepted, _ = store.create_or_replay(
            LandingJobRecord(stored_source, "accepted", None, None),
            command_key=stored_source.job_id,
            request_digest=stored_source.input_digest,
        )
        store.put(replace(accepted, state="normalizing"))
        store.close()

        class NeverProvider:
            calls = 0

            def normalize(self, *_args):
                self.calls += 1
                raise AssertionError("provider replayed")

        class NeverBuilder:
            calls = 0

            def build(self, *_args):
                self.calls += 1
                raise AssertionError("builder replayed")

        provider = NeverProvider()
        builder = NeverBuilder()
        reopened = self.store()
        service = LandingApplicationService(
            reopened,
            PrivateLandingBlobStore(
                self.parent / "blobs",
                repository_root=self.repository_root,
                clock=lambda: now,
            ),
            provider,
            profile_digest="7" * 64,
            artifact_builder=builder,
            clock=lambda: now,
        )
        replay = service.submit(
            job_id="job-recovered",
            repository_id=TARGET_REPOSITORY_ID,
            exact_base_sha=BASE_SHA,
            exact_base_tree=BASE_TREE,
            media_type="text/plain",
            chunks=(payload,),
            actor=Actor(
                "tenant-1",
                "operator",
                frozenset({"landing:submit"}),
                frozenset({TARGET_REPOSITORY_ID}),
            ),
        )
        self.assertFalse(replay.created)
        self.assertEqual(
            ("needs_human", "provider_outcome_ambiguous"),
            (replay.job.state, replay.job.reason_code),
        )
        self.assertEqual((0, 0), (provider.calls, builder.calls))


if __name__ == "__main__":
    unittest.main()
