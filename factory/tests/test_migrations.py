import unittest
from unittest.mock import patch

from adaptive_factory.migrations import AppliedMigration, MigrationError, discover_migrations, plan_migrations
from factory.tests import run_disposable_exit


PRE_RECOVERY_MIGRATIONS = (
    (1, "001_initial.sql", "99f9d27962550ad7b25ac0fe2e426f3a764fee4141ecadd83a852a9ffafbdd58"),
    (2, "002_runs_leases_capacity.sql", "2937eff5051561c0fd5a7a7aeb5c4abedf9cee851015c82e151959b6361589ea"),
    (3, "003_budgets_kills_reconciliation.sql", "44673bfe411c0f81380156ffe820bf5a037d8d221a7817b36e00689a0561a147"),
    (4, "004_event_and_repair_budgets.sql", "451f1e7985e4791048009aff089262e30c0bf7c3e9fba29d43ab8dbb79c678de"),
    (5, "005_security_accounting_commands.sql", "a91af691a25fce9f3651188f216650999f672f8bdd856c13f6b58f6efe6b2a4c"),
    (6, "006_runtime_policy_privileges.sql", "1033584169acedbf18e29291102a3adee9342fcb35adc6a4113f4848efa65f5b"),
    (7, "007_capacity_authority.sql", "d8f0b5c7ad5336851e1f39388b6343b55883541eac8568681e892da87fe62f13"),
    (8, "008_allocation_release_authority.sql", "87ac3304c8f6fb4df3ba37e5eff23419fe5d70ff1446c7f4afa90cdf99716268"),
    (9, "009_authority_audit_and_history_indexes.sql", "2e37378af506bf18ab11705430b6876136ac3918d3d1e5699e7d63848b946e6a"),
    (10, "010_authority_accounting_and_cleanup.sql", "0190888c9344c9878b734c72a8c140e6529088b7659d34608a686695c0004063"),
    (11, "011_legacy_accounting_quarantine.sql", "ff358ea06a5497d9d215f8fef7ab3540b0b4af993c806985e9d5ae6d46b01bea"),
    (12, "012_bounded_metrics_snapshot.sql", "887e59f809d5f4d31c619eccd568c35ced18a98fe047814f6020b91d28d5f2ce"),
    (13, "013_persisted_infrastructure_retry_limit.sql", "523d0b16521a258a8b922410b555c93d986b896e908011b2b0563a1c7b8f7fcb"),
    (14, "014_execution_plane.sql", "997f3010ebdfc203931b6a629ec79d515e10b6614f3c13e0763f8a16cbea5b01"),
    (15, "015_execution_canonical_persistence.sql", "e2c8ca88a7a7013da29a8d0ab440ccb5791100400b4f75b5ad5e815ba6fb0c94"),
    (16, "016_contract_execution_canonical_persistence.sql", "3b6d6104a0074b5357915583385aa433f71ccf9755f101cf9a7d6322fcc75b54"),
)


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
        self.assertEqual([item.version for item in migrations], list(range(1, 18)))
        self.assertEqual(len({item.sha256 for item in migrations}), 17)
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
        migrations = discover_migrations()
        self.assertEqual(
            tuple((item.version, item.name, item.sha256) for item in migrations[:16]),
            PRE_RECOVERY_MIGRATIONS,
        )
        execution, canonical, contract, recovery = migrations[-4:]
        self.assertEqual(execution.name, "014_execution_plane.sql")
        self.assertEqual(
            execution.sha256,
            "997f3010ebdfc203931b6a629ec79d515e10b6614f3c13e0763f8a16cbea5b01",
        )
        self.assertEqual(canonical.name, "015_execution_canonical_persistence.sql")
        self.assertEqual(contract.name, "016_contract_execution_canonical_persistence.sql")
        self.assertEqual(recovery.name, "017_execution_recovery_topology.sql")
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
        recovery_sql = recovery.sql.lower()
        self.assertLess(
            recovery_sql.index("server_version_num"),
            recovery_sql.index("lock table"),
        )
        self.assertIn("requires postgresql 17 or newer", recovery_sql)
        for marker in (
            "execution_recovery_jobs",
            "execution_recovery_candidates",
            "execution_recovery_claim",
            "execution_recovery_cleanup_succeeded",
            "execution_recovery_cleanup_failed",
            "read_combined_metrics_snapshot",
            "language plpgsql stable security definer set search_path=pg_catalog,factory",
            "security definer set search_path=pg_catalog,factory",
            "skip locked",
        ):
            self.assertIn(marker, recovery_sql)
        for forbidden in ("drop table", "drop column", "delete from", "truncate"):
            self.assertNotIn(forbidden, recovery_sql)
        self.assertNotIn("select count(*) from factory.execution_", recovery_sql)
        self.assertNotIn("create or replace function", recovery_sql)


if __name__ == "__main__":
    unittest.main()
