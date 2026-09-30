import unittest
from adaptive_factory.migrations import discover_migrations


class BBIdentityTests(unittest.TestCase):
    def test_durable_external_mapping_has_unique_active_owner_and_owner_only_disposition(self):
        migration = next((m for m in discover_migrations() if m.version == 25), None)
        self.assertIsNotNone(migration, "BB-R05 must persist external ownership, not only a digest")
        for marker in (
            "bb_external_bindings",
            "bb_external_identity_active",
            "pg_advisory_xact_lock",
            "bb_claim_external",
            "bb_resolve_external",
            "stop_evidence_digest",
            "export_evidence_digest",
        ):
            self.assertIn(marker, migration.sql)
        self.assertNotIn("GRANT INSERT", migration.sql)
        self.assertNotIn("GRANT UPDATE", migration.sql)


if __name__ == "__main__":
    unittest.main()
