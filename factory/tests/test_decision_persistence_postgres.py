"""Focused real-PostgreSQL coverage for Factory v1.5 decision persistence."""

import unittest

from factory.tests import test_postgres_integration as postgres_suite
from factory.tests.decision_persistence_cases import assert_v15_decision_persistence


class DecisionPersistencePostgresTests(postgres_suite.PostgresFactoryTests):
    def test_v15_decision_persistence(self):
        import psycopg

        assert_v15_decision_persistence(
            self,
            database_url=postgres_suite.DATABASE_URL,
            worker=postgres_suite.WORKER,
            now=postgres_suite.NOW,
            psycopg=psycopg,
        )


def load_tests(loader, standard_tests, pattern):
    del loader, standard_tests, pattern
    return unittest.TestSuite(
        [DecisionPersistencePostgresTests("test_v15_decision_persistence")]
    )
