import unittest
from unittest.mock import patch

from adaptive_factory.migrations import AppliedMigration, MigrationError, discover_migrations, plan_migrations
from factory.tests import run_disposable_exit


class MigrationTests(unittest.TestCase):
    def test_exit_runner_waits_for_final_pid1_postmaster_and_readiness(self):
        completed = type("Completed", (), {"returncode": 0})()
        with patch.object(run_disposable_exit.subprocess, "run", side_effect=[completed, completed]) as run:
            self.assertTrue(run_disposable_exit._final_postgres_ready("factory-test"))
        self.assertIn("postmaster.pid", run.call_args_list[0].args[0][-1])
        self.assertEqual(run.call_args_list[1].args[0][3], "pg_isready")

        not_final = type("Completed", (), {"returncode": 1})()
        with patch.object(run_disposable_exit.subprocess, "run", return_value=not_final) as run:
            self.assertFalse(run_disposable_exit._final_postgres_ready("factory-test"))
        self.assertEqual(run.call_count, 1)

    def test_packaged_migrations_are_contiguous_and_factory_only(self):
        migrations = discover_migrations()
        self.assertEqual([item.version for item in migrations], list(range(1, 17)))
        self.assertEqual(len({item.sha256 for item in migrations}), 16)
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
            "superseded",
            "metrics_snapshot",
            "increment_fence_rejected",
            "read_metrics_snapshot",
            "revoke select, insert, update, delete on factory.metric_counters",
            "infrastructure_retries",
        ):
            self.assertIn(marker, sql)
        self.assertNotIn("on delete cascade", sql)

    def test_execution_migrations_are_immutable_forward_only_and_capability_shaped(self):
        execution, canonical, contract = discover_migrations()[-3:]
        self.assertEqual(execution.name, "014_execution_plane.sql")
        self.assertEqual(
            execution.sha256,
            "997f3010ebdfc203931b6a629ec79d515e10b6614f3c13e0763f8a16cbea5b01",
        )
        self.assertEqual(canonical.name, "015_execution_canonical_persistence.sql")
        self.assertEqual(contract.name, "016_contract_execution_canonical_persistence.sql")
        lowered = "\n".join((execution.sql, canonical.sql, contract.sql)).lower()
        self.assertNotIn("drop table", canonical.sql.lower())
        self.assertNotIn("delete from", canonical.sql.lower())
        self.assertNotIn("drop constraint", canonical.sql.lower())
        contract_statements = tuple(
            line.strip()
            for line in contract.sql.splitlines()
            if line.strip() and not line.lstrip().startswith("--")
        )
        self.assertEqual(
            contract_statements,
            (
                "ALTER TABLE factory.execution_proposals",
                "DROP CONSTRAINT execution_proposals_body_check;",
                "ALTER TABLE factory.workspace_results",
                "DROP CONSTRAINT workspace_results_workspace_snapshot_digest_key;",
            ),
        )
        self.assertNotIn("alter table factory.tasks", lowered)
        self.assertNotIn("data_exception", canonical.sql.lower())
        self.assertEqual(canonical.sql.lower().count("exception when"), 1)
        self.assertIn("pg_input_is_valid(p_request->>'task_id','uuid')", lowered)
        self.assertIn("pg_input_is_valid(p_request->>'fence','bigint')", lowered)
        executable = [
            line.strip()
            for line in canonical.sql.splitlines()
            if line.strip() and not line.lstrip().startswith("--")
        ]
        self.assertEqual(
            executable[0],
            "LOCK TABLE factory.execution_proposals, factory.workspace_results IN ACCESS EXCLUSIVE MODE;",
        )
        self.assertIn("migration 015 refuses legacy finalized workspace rows", lowered)
        self.assertIn("migration 015 refuses unattested legacy artifact proposals", lowered)
        self.assertNotIn(
            "drop constraint workspace_results_run_manifest_digest_fkey",
            lowered,
        )
        self.assertNotIn(
            "drop constraint workspace_results_run_id_terminal_proposal_digest_fkey",
            lowered,
        )
        for marker in (
            "execution_packets",
            "execution_manifests",
            "execution_stage_events",
            "execution_proposals",
            "execution_start",
            "execution_advance",
            "execution_propose",
            "execution_proposal_context",
            "workspace_results",
            "execution_finalize_context",
            "execution_finalize_commit",
            "execution_result_for_run",
            "security definer set search_path=pg_catalog,factory",
            "revoke all",
        ):
            self.assertIn(marker, lowered)


if __name__ == "__main__":
    unittest.main()
