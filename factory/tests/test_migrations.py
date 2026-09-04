import unittest
from unittest.mock import patch
import subprocess

from adaptive_factory.migrations import AppliedMigration, MigrationError, discover_migrations, plan_migrations
from factory.tests import postgres_restart_probe, run_disposable_exit


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
    def test_exit_runner_orders_bound_preflight_before_mutating_suite(self):
        container_id = "a" * 64
        created = type("Completed", (), {"returncode": 0, "stdout": container_id})()
        port = type(
            "Completed", (), {"returncode": 0, "stdout": "127.0.0.1:5432\n"}
        )()
        with patch.object(
            run_disposable_exit.subprocess, "run", side_effect=[created, port]
        ) as subprocess_run, patch.object(
            run_disposable_exit, "_binding_matches", return_value=True
        ), patch.object(
            run_disposable_exit, "_final_postgres_ready", return_value=True
        ), patch.object(run_disposable_exit, "_run") as run, patch.object(
            run_disposable_exit, "_remove_bound_container"
        ) as remove, patch("builtins.print") as printed:
            self.assertEqual(run_disposable_exit.main(), 0)
        self.assertEqual(
            subprocess_run.call_args_list[1].args[0],
            ["docker", "port", container_id, "5432/tcp"],
        )
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn("--preflight-only", commands[0])
        self.assertIn("unittest", commands[1])
        self.assertNotIn("--preflight-only", commands[2])
        self.assertEqual(remove.call_args.args[0], container_id)
        printed.assert_called_once_with(
            "PASS: disposable PostgreSQL + API + effective roles + actual "
            "restart/reconciliation"
        )

    def test_exit_runner_reports_leaked_id_without_cleanup_when_binding_fails(self):
        container_id = "a" * 64
        created = type("Completed", (), {"returncode": 0, "stdout": container_id})()
        with patch.object(
            run_disposable_exit.subprocess, "run", return_value=created
        ), patch.object(
            run_disposable_exit, "_binding_matches", return_value=False
        ), patch.object(run_disposable_exit, "_run") as run, patch.object(
            run_disposable_exit, "_remove_bound_container"
        ) as remove:
            with self.assertRaisesRegex(RuntimeError, f"leaked id={container_id}"):
                run_disposable_exit.main()
        run.assert_not_called()
        remove.assert_not_called()

    def test_restart_probe_database_identity_is_exact_postgresql_17_cluster(self):
        valid = ("factory_exit", "factory_exit", 170_006, "cluster-1")
        self.assertTrue(
            postgres_restart_probe._database_session_is_bound(valid, "cluster-1")
        )
        invalid = (
            ("other", "factory_exit", 170_006, "cluster-1"),
            ("factory_exit", "other", 170_006, "cluster-1"),
            ("factory_exit", "factory_exit", 160_009, "cluster-1"),
            ("factory_exit", "factory_exit", 180_000, "cluster-1"),
            ("factory_exit", "factory_exit", 170_006, "cluster-2"),
        )
        for identity in invalid:
            with self.subTest(identity=identity):
                self.assertFalse(
                    postgres_restart_probe._database_session_is_bound(
                        identity, "cluster-1"
                    )
                )

    def test_restart_database_revalidates_binding_and_targets_only_full_id(self):
        container_id = "a" * 64
        name = "adaptive-factory-exit-012345abcdef"
        nonce = "b" * 32
        owner = "postgresql://factory_exit:password@127.0.0.1:5432/factory_exit"
        runtime = postgres_restart_probe._database_url_for_login(
            owner, "runtime", "runtime-password"
        )
        attestor = postgres_restart_probe._database_url_for_login(
            owner, "attestor", "attestor-password"
        )
        with patch.object(
            postgres_restart_probe, "_assert_disposable_target"
        ) as validate, patch.object(
            postgres_restart_probe, "_postmaster_started_at", side_effect=[1, 2]
        ), patch.object(
            postgres_restart_probe.subprocess, "run"
        ) as run, patch.object(
            postgres_restart_probe, "_published_port", return_value=6543
        ) as published_port, patch.object(
            postgres_restart_probe, "_wait_for_database"
        ):
            moved = postgres_restart_probe._restart_database(
                name, container_id, nonce, owner, runtime, attestor
            )
        self.assertEqual(
            run.call_args.args[0], ["docker", "restart", container_id]
        )
        self.assertEqual(published_port.call_args.args, (container_id,))
        self.assertEqual(validate.call_count, 2)
        self.assertEqual(validate.call_args_list[0].args, (owner, name, container_id, nonce))
        self.assertEqual(validate.call_args_list[1].args[1:], (name, container_id, nonce))
        from psycopg.conninfo import conninfo_to_dict

        self.assertEqual(
            tuple(conninfo_to_dict(value)["port"] for value in moved),
            ("6543", "6543", "6543"),
        )

    def test_restart_probe_rejects_bad_container_metadata_before_database_access(self):
        container_id = "a" * 64
        name = "adaptive-factory-exit-012345abcdef"
        nonce = "b" * 32
        valid = [container_id, f"/{name}", "postgres:17-alpine", "true", nonce]
        variants = []
        for index, replacement in enumerate(
            ("c" * 64, "/other", "postgres:18-alpine", "false", "d" * 32)
        ):
            changed = list(valid)
            changed[index] = replacement
            variants.append("\t".join(changed))
        for metadata in variants:
            completed = type("Completed", (), {"stdout": metadata})()
            with self.subTest(metadata=metadata), patch.object(
                postgres_restart_probe.subprocess, "run", return_value=completed
            ) as run, self.assertRaises(RuntimeError):
                postgres_restart_probe._assert_disposable_target(
                    "postgresql://factory_exit:pw@127.0.0.1:5432/factory_exit",
                    name,
                    container_id,
                    nonce,
                )
            self.assertEqual(run.call_count, 1)

    def test_exit_runner_container_binding_and_cleanup_are_exact_id_scoped(self):
        container_id = "a" * 64
        name = "adaptive-factory-exit-012345abcdef"
        nonce = "b" * 32
        valid = f"{container_id}\t/{name}\tpostgres:17-alpine\ttrue\t{nonce}\n"
        variants = (
            valid.replace(container_id, "c" * 64, 1),
            valid.replace(f"/{name}", "/other", 1),
            valid.replace("postgres:17-alpine", "postgres:18-alpine", 1),
            valid.replace("\ttrue\t", "\tfalse\t", 1),
            valid.replace("\ttrue\t", "\tunknown\t", 1),
            valid.replace(nonce, "d" * 32, 1),
        )
        for output in variants:
            completed = type(
                "Completed", (), {"returncode": 0, "stdout": output}
            )()
            with self.subTest(output=output), patch.object(
                run_disposable_exit.subprocess, "run", return_value=completed
            ):
                self.assertFalse(
                    run_disposable_exit._binding_matches(
                        container_id, name, nonce, require_running=True
                    )
                )

        for state, expected in (("false", True), ("unknown", False), ("", False)):
            metadata = (
                f"{container_id}\t/{name}\tpostgres:17-alpine\t{state}\t{nonce}\n"
            )
            completed = type(
                "Completed", (), {"returncode": 0, "stdout": metadata}
            )()
            with self.subTest(cleanup_state=state), patch.object(
                run_disposable_exit.subprocess, "run", return_value=completed
            ):
                self.assertIs(
                    run_disposable_exit._binding_matches(
                        container_id, name, nonce, require_running=False
                    ),
                    expected,
                )

        inspected = type("Completed", (), {"returncode": 0, "stdout": valid})()
        removed = type("Completed", (), {"returncode": 0, "stdout": ""})()
        with patch.object(
            run_disposable_exit.subprocess,
            "run",
            side_effect=[inspected, removed],
        ) as run:
            run_disposable_exit._remove_bound_container(container_id, name, nonce)
        self.assertEqual(run.call_args_list[-1].args[0], ["docker", "rm", "-f", container_id])
        self.assertEqual(run.call_args_list[0].args[0][-1], container_id)

        with patch.object(
            run_disposable_exit, "_binding_matches", return_value=False
        ), patch.object(run_disposable_exit.subprocess, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "leaked id"):
                run_disposable_exit._remove_bound_container(
                    container_id, name, nonce
                )
            run.assert_not_called()

    def test_restart_releaser_wraps_real_broker_with_exact_at_least_once_outcomes(self):
        from adaptive_factory.workspace import WorkspaceHandle, WorkspaceReleaseOutcome

        first_handle = WorkspaceHandle("task-a", "run-a", "workspace:" + "a" * 64)
        second_handle = WorkspaceHandle("task-b", "run-b", "workspace:" + "b" * 64)
        unknown = WorkspaceHandle("task-c", "run-c", "workspace:" + "c" * 64)
        backend = postgres_restart_probe.WorkspaceBackend()
        backend.register(first_handle)
        backend.register(second_handle)
        first = postgres_restart_probe.AmbiguousWorkspaceReleaser(
            backend, ambiguous=first_handle
        )
        self.assertEqual(
            first.release(second_handle, timeout_seconds=4.0),
            WorkspaceReleaseOutcome("released"),
        )
        with self.assertRaises(TimeoutError):
            first.release(first_handle, timeout_seconds=3.0)
        second = postgres_restart_probe.AmbiguousWorkspaceReleaser(backend)
        self.assertEqual(
            second.release(first_handle, timeout_seconds=2.0),
            WorkspaceReleaseOutcome("already_absent"),
        )
        before = tuple(backend.outcomes)
        with self.assertRaises(RuntimeError):
            second.release(unknown, timeout_seconds=2.0)
        self.assertEqual(tuple(backend.outcomes), before)
        self.assertEqual(
            backend.outcomes,
            [
                (second_handle, 4.0, "released"),
                (first_handle, 3.0, "released"),
                (first_handle, 2.0, "already_absent"),
            ],
        )

    def test_exit_runner_never_deletes_by_name_when_container_creation_fails(self):
        commands = []

        def failed_create(command, **kwargs):
            commands.append(command)
            if command[:2] == ["docker", "run"]:
                raise subprocess.CalledProcessError(125, command)
            return type("Completed", (), {"returncode": 0, "stdout": ""})()

        with patch.object(run_disposable_exit.subprocess, "run", side_effect=failed_create):
            with self.assertRaises(subprocess.CalledProcessError):
                run_disposable_exit.main()
        self.assertFalse(any(command[:2] == ["docker", "rm"] for command in commands))

    def test_restart_probe_rejects_ambiguous_or_non_loopback_port_bindings(self):
        invalid = (
            "127.0.0.1:5432\n[::]:5432\n",
            "0.0.0.0:5432\n",
            "[::1]:5432\n",
            "localhost:5432\n",
            "",
            "127.0.0.1:0\n",
            "127.0.0.1:65536\n",
        )
        for published in invalid:
            completed = type("Completed", (), {"stdout": published})()
            with self.subTest(published=published), patch.object(
                postgres_restart_probe.subprocess, "run", return_value=completed
            ), self.assertRaises(RuntimeError):
                postgres_restart_probe._published_port("a" * 64)
            with self.subTest(runner=published), self.assertRaises(RuntimeError):
                run_disposable_exit._published_loopback_port(published)
        self.assertEqual(
            run_disposable_exit._published_loopback_port("127.0.0.1:5432\n"),
            5432,
        )

    def test_restart_probe_rebuilds_distinct_capability_urls_after_port_change(self):
        owner = "postgresql://owner:owner-password@127.0.0.1:5432/factory_exit"
        runtime = postgres_restart_probe._database_url_for_login(
            owner, "factory_probe_runtime", "runtime-password"
        )
        attestor = postgres_restart_probe._database_url_for_login(
            owner, "factory_probe_attestor", "attestor-password"
        )
        moved = tuple(
            postgres_restart_probe._database_url_at_port(value, 6543)
            for value in (owner, runtime, attestor)
        )

        from psycopg.conninfo import conninfo_to_dict

        parsed = tuple(conninfo_to_dict(value) for value in moved)
        self.assertEqual(
            tuple((value["user"], value["port"]) for value in parsed),
            (
                ("owner", "6543"),
                ("factory_probe_runtime", "6543"),
                ("factory_probe_attestor", "6543"),
            ),
        )
        self.assertEqual(
            tuple(value["host"] for value in parsed),
            ("127.0.0.1",) * 3,
        )

    def test_exit_runner_waits_for_final_pid1_postmaster_and_readiness(self):
        completed = type("Completed", (), {"returncode": 0})()
        with patch.object(run_disposable_exit.subprocess, "run", side_effect=[completed, completed]) as run:
            self.assertTrue(run_disposable_exit._final_postgres_ready("factory-test"))
        self.assertIn("postmaster.pid", run.call_args_list[0].args[0][-1])
        self.assertEqual(run.call_args_list[1].args[0][3], "pg_isready")
        self.assertEqual(run.call_args_list[0].kwargs["timeout"], 10)
        self.assertEqual(run.call_args_list[1].kwargs["timeout"], 10)

        not_final = type("Completed", (), {"returncode": 1})()
        with patch.object(run_disposable_exit.subprocess, "run", return_value=not_final) as run:
            self.assertFalse(run_disposable_exit._final_postgres_ready("factory-test"))
        self.assertEqual(run.call_count, 1)

    def test_exit_runner_removes_its_exact_container_and_restart_volume(self):
        removed = type("Completed", (), {"returncode": 0})()
        absent = type("Completed", (), {"returncode": 1})()
        with patch.object(
            run_disposable_exit.subprocess,
            "run",
            side_effect=[removed, removed, absent, absent],
        ) as run:
            run_disposable_exit._cleanup(
                "factory-test-container",
                "factory-test-volume",
            )
        self.assertEqual(
            [call.args[0] for call in run.call_args_list],
            [
                ["docker", "rm", "-f", "factory-test-container"],
                ["docker", "volume", "rm", "factory-test-volume"],
                ["docker", "inspect", "factory-test-container"],
                ["docker", "volume", "inspect", "factory-test-volume"],
            ],
        )

    def test_packaged_migrations_are_contiguous_and_factory_only(self):
        migrations = discover_migrations()
        self.assertEqual([item.version for item in migrations], list(range(1, 19)))
        self.assertEqual(len({item.sha256 for item in migrations}), 18)
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

    def test_semantic_migration_is_additive_append_only_and_capability_shaped(self):
        migration = discover_migrations()[-1]
        self.assertEqual(migration.name, "018_semantic_validation_bridge.sql")
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
            "semantic_repair_intake_status",
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
        self.assertIn(") to factory_semantic_coordinator;", migration)
        self.assertIn(
            "grant execute on function factory.semantic_append_evidence",
            migration,
        )
        self.assertIn(") to factory_semantic_validator;", migration)
        self.assertIn(
            "grant execute on function factory.semantic_append_verdict",
            migration,
        )
        self.assertIn(") to factory_semantic_adjudicator;", migration)
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
