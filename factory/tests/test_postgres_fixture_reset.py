"""Characterize the test-only reset boundary and its two real callers."""
import hashlib
import importlib
import os
from pathlib import Path
import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch

EXPECTED_SHA256 = "a67d8339b86d2af81a72d3f8e953cf29ce8bb81067f1cefe4921555a0c075de9"


class RecordingCursor:
    def __init__(self, marker=None, fail=False):
        self.calls = []
        self.marker = marker
        self.fail = fail
        self.failure = RuntimeError("synthetic reset failure")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, statement, parameters=None):
        self.calls.append((statement, parameters))
        if self.fail:
            raise self.failure

    def fetchone(self):
        return (self.marker,)


class RecordingConnection:
    def __init__(self, cursor):
        self.recording_cursor = cursor
        self.outcome = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        self.outcome = "rollback" if exc_type else "commit"
        return False

    def cursor(self):
        return self.recording_cursor


class FixtureResetTests(unittest.TestCase):
    def helper(self):
        try:
            return importlib.import_module("factory.tests.postgres_fixture_reset")
        except ModuleNotFoundError:
            self.fail("the isolated cursor reset seam is missing")

    def test_exact_025_statement_is_one_closed_cursor_operation(self):
        cursor = RecordingCursor()
        self.assertIsNone(self.helper().reset_fixture_tables(cursor))
        self.assertEqual(len(cursor.calls), 1)
        statement, parameters = cursor.calls[0]
        self.assertIsNone(parameters)
        self.assertEqual(hashlib.sha256(statement.encode()).hexdigest(), EXPECTED_SHA256)
        self.assertEqual(len(statement.split("factory.")) - 1, 43)
        self.assertTrue(statement.endswith(" RESTART IDENTITY"))
        self.assertNotIn("CASCADE", statement)

    def test_leaf_propagates_the_original_sql_failure(self):
        cursor = RecordingCursor(fail=True)
        with self.assertRaisesRegex(RuntimeError, "synthetic reset failure") as caught:
            self.helper().reset_fixture_tables(cursor)
        self.assertIs(caught.exception, cursor.failure)
        self.assertEqual(len(cursor.calls), 1)

    def call_wrapper(self, caller, cursor):
        from factory.tests import postgres_restart_probe as restart
        from factory.tests import test_execution_persistence_postgres as execution
        module = restart if caller == "restart" else execution
        self.assertTrue(hasattr(module, "reset_fixture_tables"), "caller must delegate to the leaf")
        connection = RecordingConnection(cursor)
        self.last_connection = connection
        with patch("psycopg.connect", return_value=connection):
            if caller == "restart":
                observation = restart._reset_database("synthetic-unused", execution.NOW)
            else:
                fixture = execution.ExecutionPersistencePostgresTests()
                with patch.object(fixture, "runtime_store", return_value=object()):
                    fixture.setUp()
                observation = cursor.calls[-1][1]
        return connection, observation

    def test_real_callers_retain_distinct_suffixes_and_observation_parameters(self):
        for caller, marker, singleton in (("execution", None, False),
                                         ("execution", "legacy", True),
                                         ("restart", None, True)):
            with self.subTest(caller=caller, marker=marker):
                cursor = RecordingCursor(marker=marker)
                connection, observation = self.call_wrapper(caller, cursor)
                statements = [row[0] for row in cursor.calls]
                self.assertEqual(hashlib.sha256(statements[0].encode()).hexdigest(), EXPECTED_SHA256)
                self.assertEqual("TRUNCATE factory.kill_switch_heads" in statements, singleton)
                self.assertEqual("INSERT INTO factory.metric_counters(singleton) VALUES (true)" in statements, singleton)
                self.assertIn("UPDATE factory.capacity_counters SET active_count=0", statements)
                self.assertTrue(statements[-1].lstrip().startswith("INSERT INTO factory.m0_authority_observations"))
                self.assertEqual(observation[6], "probe/repository" if caller == "restart" else "owner/repository")
                self.assertEqual(observation[2:6], ("adaptive-trust-ci/verified@06ecf1c875bc", "3" * 40,
                                                   "external-trust-ci-api", "7" * 64))
                self.assertEqual(connection.outcome, "commit")

    def test_caller_sql_failure_stops_suffix_and_exits_its_transaction(self):
        for caller in ("execution", "restart"):
            with self.subTest(caller=caller):
                cursor = RecordingCursor(fail=True)
                with self.assertRaisesRegex(RuntimeError, "synthetic reset failure") as caught:
                    self.call_wrapper(caller, cursor)
                self.assertIs(caught.exception, cursor.failure)
                self.assertEqual(len(cursor.calls), 1)
                self.assertEqual(self.last_connection.outcome, "rollback")

    def test_package_and_sibling_imports_resolve_the_same_leaf(self):
        helper = self.helper()
        result = subprocess.run([sys.executable, "-c",
            "import sys; from postgres_fixture_reset import reset_fixture_tables; "
            "assert not any(n == 'adaptive_factory' or n.startswith('adaptive_factory.') for n in sys.modules)"],
            cwd=Path(helper.__file__).parent, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(os.environ.get("FACTORY_TEST_DATABASE_URL"), "requires exact disposable PostgreSQL")
class FixtureResetPostgresTests(unittest.TestCase):
    def test_025_effects_rollback_unlisted_fk_and_runtime_refusal(self):
        import psycopg
        from psycopg import sql
        from psycopg.conninfo import conninfo_to_dict, make_conninfo
        from adaptive_factory.admin import provision_runtime_login
        from adaptive_factory.migrations import PostgresMigrator
        from factory.tests.postgres_fixture_reset import reset_fixture_tables
        from factory.tests.postgres_restart_probe import _assert_disposable_target
        url = os.environ["FACTORY_TEST_DATABASE_URL"]
        _assert_disposable_target(url, os.environ["FACTORY_TEST_POSTGRES_CONTAINER"],
            os.environ["FACTORY_TEST_POSTGRES_CONTAINER_ID"], os.environ["FACTORY_TEST_POSTGRES_NONCE"])
        migrator = PostgresMigrator(url)
        migrator.apply()
        before = migrator.status()
        self.assertEqual([row.version for row in before], list(range(1, 26)))
        login = "factory_reset_runtime_" + str(os.getpid())
        password = f"local-{uuid.uuid4().hex}"
        provision_runtime_login(url, login, password)
        runtime = make_conninfo(**{**conninfo_to_dict(url), "user": login, "password": password})
        try:
            with psycopg.connect(url, options="-c statement_timeout=10000 -c lock_timeout=3000") as db:
                db.execute("INSERT INTO factory.intake_identities VALUES('reset/repository','manual','retained')")
                db.commit()
                reset_fixture_tables(db.cursor())
                self.assertEqual(db.execute("SELECT count(*) FROM factory.intake_identities").fetchone()[0], 0)
                db.rollback()
                self.assertEqual(db.execute("SELECT source_id FROM factory.intake_identities WHERE repository_id='reset/repository'").fetchone()[0], "retained")
                db.execute("CREATE TABLE factory.fixture_reset_blocker(repository_id text,source_type text,source_id text, "
                    "FOREIGN KEY(repository_id,source_type,source_id) REFERENCES factory.intake_identities)")
                db.commit()
                with self.assertRaises(psycopg.errors.FeatureNotSupported):
                    reset_fixture_tables(db.cursor())
                db.rollback()
                self.assertEqual(db.execute("SELECT source_id FROM factory.intake_identities WHERE repository_id='reset/repository'").fetchone()[0], "retained")
                db.execute("DROP TABLE factory.fixture_reset_blocker")
                db.commit()
                with psycopg.connect(runtime, options="-c statement_timeout=10000 -c lock_timeout=3000") as denied:
                    denied.execute("SET ROLE factory_runtime")
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        reset_fixture_tables(denied.cursor())
                    denied.rollback()
                self.assertEqual(db.execute("SELECT source_id FROM factory.intake_identities WHERE repository_id='reset/repository'").fetchone()[0], "retained")
                reset_fixture_tables(db.cursor())
                db.commit()
                self.assertEqual(db.execute("SELECT count(*) FROM factory.intake_identities").fetchone()[0], 0)
            self.assertEqual(migrator.status(), before)
        finally:
            with psycopg.connect(url) as cleanup:
                cleanup.execute("DROP TABLE IF EXISTS factory.fixture_reset_blocker")
                cleanup.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(login)))
