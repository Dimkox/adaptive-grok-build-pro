import unittest
from contextlib import redirect_stderr
from io import StringIO
from unittest.mock import patch

from adaptive_factory.migrations import AppliedMigration, MigrationError, discover_migrations, plan_migrations
from factory.tests import run_disposable_exit


class MigrationTests(unittest.TestCase):
    def test_exit_runner_accepts_only_repo_owned_postgres_images(self):
        self.assertEqual(
            run_disposable_exit._parse_args([]).postgres_image,
            "postgres:17-alpine",
        )
        self.assertEqual(
            run_disposable_exit._parse_args([
                "--postgres-image", "postgres:15-alpine",
            ]).postgres_image,
            "postgres:15-alpine",
        )
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            run_disposable_exit._parse_args([
                "--postgres-image", "postgres:latest",
            ])

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
        self.assertEqual([item.version for item in migrations], list(range(1, 15)))
        self.assertEqual(len({item.sha256 for item in migrations}), 14)
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
        ):
            self.assertIn(marker, sql)
        self.assertNotIn("on delete cascade", sql)

    def test_execution_migration_is_additive_and_capability_shaped(self):
        migration = next(item for item in discover_migrations() if item.version == 13)
        self.assertEqual(migration.name, "013_execution_plane.sql")
        lowered = migration.sql.lower()
        self.assertNotIn("drop ", lowered)
        self.assertNotIn("alter table factory.tasks", lowered)
        for marker in (
            "execution_packets",
            "execution_manifests",
            "execution_stage_events",
            "execution_proposals",
            "execution_artifact_attestations",
            "factory_artifact_attestor",
            "execution_record_artifact_attestation",
            "execution_start",
            "execution_advance",
            "execution_propose",
            "execution_proposal_context",
            "workspace_results",
            "execution_finalize_context",
            "execution_finalize_commit",
            "execution_result_for_run",
            "execution_recovery_candidates",
            "execution_orphan_terminalize",
            "execution_recovery_cleanup_failed",
            "execution_recovery_cleanup_succeeded",
            "execution_recovery_cleanup_failures",
            "security definer set search_path=pg_catalog,factory",
            "revoke all",
        ):
            self.assertIn(marker, lowered)

    def test_semantic_migration_is_additive_append_only_and_capability_shaped(self):
        migration = discover_migrations()[-1]
        self.assertEqual(migration.name, "014_semantic_validation_bridge.sql")
        lowered = migration.sql.lower()
        for forbidden in (
            "drop ",
            "cascade",
            "alter table factory.workspace_results",
            "grant all",
        ):
            self.assertNotIn(forbidden, lowered)
        for marker in (
            "factory_semantic_coordinator",
            "factory_semantic_validator",
            "factory_semantic_adjudicator",
            "nologin noinherit",
            "semantic_command_results",
            "semantic_subjects",
            "semantic_assignments",
            "semantic_findings",
            "semantic_coverage",
            "semantic_verdicts",
            "semantic_directives",
            "semantic_child_proposals",
            "semantic_child_task_bindings",
            "intake_actor_kind",
            "semantic_recovery_records",
            "semantic_metric_events",
            "semantic_execution_material",
            "semantic_publish_subject",
            "semantic_subject_by_digest",
            "semantic_create_assignment",
            "semantic_append_evidence",
            "semantic_adjudication_material",
            "semantic_append_verdict",
            "semantic_verdict_by_subject",
            "semantic_escalations",
            "semantic_plan_repair",
            "semantic_bind_repair_child",
            "semantic_task_claimable",
            "security definer set search_path=pg_catalog,factory",
            "revoke insert, update, delete",
            "revoke all",
        ):
            self.assertIn(marker, lowered)

    def test_semantic_evidence_functions_are_reserved_to_distinct_capabilities(self):
        migration = discover_migrations()[-1].sql.lower()
        self.assertIn(
            "grant execute on function factory.semantic_create_assignment",
            migration,
        )
        self.assertIn(
            ") to factory_semantic_coordinator;",
            migration,
        )
        self.assertIn(
            "grant execute on function factory.semantic_append_evidence",
            migration,
        )
        self.assertIn(
            ") to factory_semantic_validator;",
            migration,
        )
        self.assertIn(
            "grant execute on function factory.semantic_append_verdict",
            migration,
        )
        self.assertIn(
            ") to factory_semantic_adjudicator;",
            migration,
        )
        for forbidden in (
            "semantic_append_evidence(\n  char,char,text,char,char,char,text\n) to factory_semantic_coordinator",
            "semantic_append_verdict(\n  char,char,text,char,char,text,char,text\n) to factory_semantic_validator",
            "semantic_append_verdict(\n  char,char,text,char,char,text,char,text\n) to factory_runtime",
            "semantic_plan_repair(\n  char,char,text,uuid\n) to factory_semantic_validator",
            "semantic_plan_repair(\n  char,char,text,uuid\n) to factory_semantic_adjudicator",
            "semantic_plan_repair(\n  char,char,text,uuid\n) to factory_runtime",
        ):
            self.assertNotIn(forbidden, migration)
        self.assertIn(
            "grant execute on function factory.semantic_plan_repair",
            migration,
        )


if __name__ == "__main__":
    unittest.main()
