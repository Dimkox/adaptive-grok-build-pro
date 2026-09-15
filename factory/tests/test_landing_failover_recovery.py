"""Crash, journal ownership, input lifetime and binding failure tests."""

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from adaptive_factory.landing_failover import FailoverCoordinator
from adaptive_factory.landing_failover_config import FailoverConfig
from adaptive_factory.landing_failover_journal import CallerJournal
from adaptive_factory.landing_failover_transport import BackendAmbiguous
from adaptive_factory.landing_service import LandingServiceError
from adaptive_factory.settings import SettingsError
from factory.tests.test_landing_failover import configuration, ScriptedBackends


class SimulatedCrash(BaseException):
    pass


class CallerRecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config = FailoverConfig.from_dict(configuration(self.root))

    def test_crash_after_dispatch_commit_never_allocates_a_replacement_attempt(self):
        script = ScriptedBackends({"qwen-intl": "success"})
        calls = []
        def crashing_factory(backend, **kwargs):
            client = script.factory(backend, **kwargs)
            def crash(*args):
                calls.append("possible-send")
                raise SimulatedCrash()
            client.submit = crash
            return client
        with CallerJournal(self.config) as journal:
            with self.assertRaises(SimulatedCrash):
                FailoverCoordinator(self.config, journal, backend_factory=crashing_factory).submit("crash", b"brief", "text/plain")
            record, _ = journal.load("crash")
            self.assertEqual("dispatching", record["attempts"][0]["state"])
        def observation_factory(backend, **kwargs):
            client = script.factory(backend, **kwargs)
            def observe(child):
                calls.append(("observe", child))
                raise BackendAmbiguous("not_found")
            client.observe = observe
            return client
        with CallerJournal(self.config) as journal:
            result = FailoverCoordinator(self.config, journal, backend_factory=observation_factory).resume("crash")
            self.assertEqual("needs_human", result["state"])
            self.assertEqual(1, len(result["attempts"]))
        self.assertEqual(1, calls.count("possible-send"))
        self.assertEqual([], script.calls)

    def test_private_journal_rejects_concurrent_writer_and_dangling_database_symlink(self):
        with CallerJournal(self.config):
            with self.assertRaisesRegex(LandingServiceError, "store_writer_active"):
                CallerJournal(self.config)
        other = self.root / "other"
        other.mkdir(mode=0o700)
        alternate = configuration(other)
        config = FailoverConfig.from_dict(alternate)
        (config.journal_path / "failover.sqlite3").symlink_to(other / "outside.sqlite3")
        with self.assertRaisesRegex(SettingsError, "symlink"):
            CallerJournal(config)
        self.assertFalse((other / "outside.sqlite3").exists())

    def test_terminal_winner_purges_spool_and_corrupted_record_cannot_replay(self):
        script = ScriptedBackends({"qwen-intl": "success"})
        with CallerJournal(self.config) as journal:
            result = FailoverCoordinator(self.config, journal, backend_factory=script.factory).submit("done", b"brief", "text/plain")
            self.assertEqual("artifact_ready", result["state"])
            self.assertIsNone(journal.load("done")[1])
            journal.connection.execute("UPDATE requests SET record=? WHERE job_id='done'", (b'{}',))
            with self.assertRaisesRegex(SettingsError, "record invalid"):
                journal.load("done")

    def test_expired_ambiguous_request_is_purged_without_new_provider_calls(self):
        script = ScriptedBackends({"qwen-intl": "success"})
        def crashing_factory(backend, **kwargs):
            client = script.factory(backend, **kwargs)
            def crash(*args):
                raise SimulatedCrash()
            client.submit = crash
            return client
        with CallerJournal(self.config, clock=lambda: 1000) as journal:
            with self.assertRaises(SimulatedCrash):
                FailoverCoordinator(self.config, journal, backend_factory=crashing_factory, clock=lambda: 1000).submit("expired", b"brief", "text/plain")
        with CallerJournal(self.config, clock=lambda: 5000) as journal:
            result = FailoverCoordinator(self.config, journal, backend_factory=script.factory, clock=lambda: 5000).resume("expired")
            self.assertEqual("expired", result["state"])
            self.assertIsNone(journal.load("expired")[1])
        self.assertEqual([], script.calls)

    def test_swapped_capability_and_unsupported_media_cannot_dispatch(self):
        script = ScriptedBackends({"qwen-intl": "success"})
        def wrong_factory(backend, **kwargs):
            client = script.factory(backend, **kwargs)
            client.capability = lambda: {"profile_digest": "0" * 64}
            return client
        with CallerJournal(self.config) as journal:
            caller = FailoverCoordinator(self.config, journal, backend_factory=wrong_factory)
            self.assertEqual("stopped", caller.submit("wrong", b"brief", "text/plain")["state"])
            with self.assertRaisesRegex(SettingsError, "unsupported"):
                caller.submit("audio", b"audio", "audio/wav")
        self.assertEqual([], script.calls)

    def test_absent_socket_tail_does_not_hide_untrusted_ancestors(self):
        document = configuration(self.root)
        unsafe = self.root / "run" / "unsafe"
        unsafe.mkdir(mode=0o777)
        unsafe.chmod(0o777)
        document["backends"][0]["socket_path"] = str(unsafe / "absent" / "control.sock")
        with self.assertRaisesRegex(SettingsError, "ancestry"):
            FailoverConfig.from_dict(document)
        link = self.root / "run" / "linked"
        link.symlink_to(self.root / "missing")
        document["backends"][0]["socket_path"] = str(link / "absent" / "control.sock")
        with self.assertRaisesRegex(SettingsError, "ancestry"):
            FailoverConfig.from_dict(document)


if __name__ == "__main__":
    unittest.main()
