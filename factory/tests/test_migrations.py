import unittest

from adaptive_factory.migrations import AppliedMigration, MigrationError, discover_migrations, plan_migrations


class MigrationTests(unittest.TestCase):
    def test_packaged_migrations_are_contiguous_and_factory_only(self):
        migrations = discover_migrations()
        self.assertEqual([item.version for item in migrations], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
        self.assertEqual(len({item.sha256 for item in migrations}), 11)
        for item in migrations:
            self.assertIn("factory.", item.sql)
            self.assertNotIn("trust_ci", item.sql.lower())

    def test_matching_applied_migrations_are_idempotent(self):
        migrations = discover_migrations()
        applied = [AppliedMigration(item.version, item.name, item.sha256) for item in migrations[:2]]
        self.assertEqual(plan_migrations(migrations, applied), migrations[2:])

    def test_missing_renamed_or_checksum_changed_applied_migration_fails(self):
        migrations = discover_migrations()
        bad = (
            [AppliedMigration(2, migrations[1].name, migrations[1].sha256)],
            [AppliedMigration(1, "renamed.sql", migrations[0].sha256)],
            [AppliedMigration(1, migrations[0].name, "0" * 64)],
        )
        for applied in bad:
            with self.subTest(applied=applied), self.assertRaises(MigrationError):
                plan_migrations(migrations, applied)

    def test_sql_declares_skip_locked_fences_capacity_budgets_and_append_only_audit(self):
        sql = "\n".join(item.sql for item in discover_migrations()).lower()
        for marker in (
            "skip locked",
            "last_fence",
            "capacity_allocations",
            "budget_reservations",
            "kill_switches",
            "reconciliation_runs",
            "audit_log",
            "repair_limit",
            "m0_authority_observations",
            "command_results",
            "revoke update on factory.accepted_intents",
            "grant update (active_count) on factory.capacity_counters",
            "capacity_eligible_repositories",
            "capacity_allocate",
            "capacity_release",
            "revoke insert, update on factory.capacity_counters",
            "revoke update on factory.capacity_allocations",
            "m0_observation_policy_check_bound",
            "audit_log_task_order",
            "budget_reservations_task_run_active",
            "mandatory_cleanup",
            "for share",
            "accounting_blocked=true",
            "ready_for_human",
        ):
            self.assertIn(marker, sql)
        self.assertNotIn("on delete cascade", sql)


if __name__ == "__main__":
    unittest.main()
