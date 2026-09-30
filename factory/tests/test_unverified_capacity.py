"""Source contract checks complement the real PostgreSQL admission/reconnect tests."""
import unittest
from unittest.mock import patch

from adaptive_factory.migrations import discover_migrations


class UnverifiedCapacityTests(unittest.TestCase):
    def test_owner_configuration_rejects_unbounded_or_boolean_limits_before_connect(self):
        from adaptive_factory.admin import configure_unverified_limit, BootstrapError
        with patch("psycopg.connect") as connect:
            for limit in (0, 65, True, "4"):
                with self.assertRaises(BootstrapError):
                    configure_unverified_limit("owner", "owner/repo", "a" * 64, limit)
            connect.assert_not_called()

    def test_durable_capacity_is_additive_and_not_runtime_writable(self):
        migration = next((m for m in discover_migrations() if m.version == 24), None)
        self.assertIsNotNone(migration, "F07 requires durable admission, not lease capacity")
        source = migration.sql
        for marker in (
            "max_unverified_inflight", "BETWEEN 1 AND 64", "DEFAULT 32",
            "pg_advisory_xact_lock", "BEFORE INSERT ON factory.execution_packets",
            "AFTER INSERT ON factory.workspace_results",
            "AFTER INSERT ON factory.semantic_verdicts",
            "unverified_capacity_exhausted", "unverified_resolutions",
            "GRANT SELECT ON factory.unverified_limits",
        ):
            self.assertIn(marker, source)
        self.assertNotIn("GRANT UPDATE", source)
        self.assertNotIn("GRANT DELETE", source)
        self.assertNotIn("GRANT INSERT", source)


if __name__ == "__main__":
    unittest.main()
