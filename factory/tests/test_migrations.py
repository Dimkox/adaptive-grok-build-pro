import hashlib
import re
import traceback
import unittest
from unittest.mock import MagicMock, patch
import subprocess
from urllib.parse import urlsplit

from adaptive_factory import semantic_repair
from adaptive_factory.contracts import ContractError
from adaptive_factory.migrations import AppliedMigration, MigrationError, discover_migrations, plan_migrations
from adaptive_factory.semantic_repair import (
    REPAIR_CHILD_REJECTION_CHANNEL,
    REPAIR_CHILD_REJECTIONS,
    RepairChildTaskBindingV1,
    UNKNOWN_REPAIR_CHILD_REJECTION,
    repair_child_rejection_reason,
)
from adaptive_factory.store import PostgresSemanticCoordinatorStore, StoreError
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
            # Reclaim is isolated here on purpose. Before this contour it escaped the patch
            # entirely (the default runner was bound at import), so this fixture's two-item
            # side effect silently matched real `docker run`/`docker port` calls while a
            # unit test could have deleted live containers on the host. Isolating it makes
            # the ordering under test explicit instead of accidental.
            run_disposable_exit, "reclaim_orphan_runs", return_value=[]
        ), patch.object(
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
        self.assertEqual(run.call_args_list[1].kwargs["timeout"], 480)
        self.assertNotIn("--preflight-only", commands[2])
        self.assertEqual(remove.call_args.args[0], container_id)
        printed.assert_called_once_with(
            "PASS: disposable PostgreSQL + API + effective roles + actual "
            "restart/reconciliation"
        )

    def test_exit_runner_reclaims_its_own_container_when_binding_fails(self):
        container_id = "a" * 64
        created = type("Completed", (), {"returncode": 0, "stdout": container_id})()
        with patch.object(
            run_disposable_exit.subprocess, "run", return_value=created
        ), patch.object(
            run_disposable_exit, "_binding_matches", return_value=False
        ), patch.object(run_disposable_exit, "_run") as run, patch.object(
            run_disposable_exit, "_remove_bound_container"
        ) as remove:
            with self.assertRaisesRegex(RuntimeError, f"reclaimed id={container_id}"):
                run_disposable_exit.main()
        run.assert_not_called()
        # Ownership begins at `docker run`. This arm used to assert the opposite:
        # `remove.assert_not_called()` pinned the leak itself as the contract, which is why
        # a rejected binding kept leaving a live PostgreSQL plus volume behind (issue 128).
        self.assertEqual(remove.call_args.args[0], container_id)
        self.assertIs(remove.call_args.kwargs["minted"], True)

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
        self.assertEqual(
            tuple(str(urlsplit(value).port) for value in moved),
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
        # Removal is not believed on its exit code: the honest proof is that the daemon can
        # no longer see the container, so the sequence needs a third answer.
        absent = type("Completed", (), {"returncode": 1, "stdout": ""})()
        with patch.object(
            run_disposable_exit.subprocess,
            "run",
            side_effect=[inspected, removed, absent],
        ) as run:
            run_disposable_exit._remove_bound_container(container_id, name, nonce)
        # `-v` is required, not cosmetic: `docker rm -f` releases the container and leaves the
        # anonymous volume Postgres was initialised into, which is the half of the leak that
        # fills the disk. Deletion stays exact-id scoped, never by name.
        self.assertEqual(
            run.call_args_list[1].args[0], ["docker", "rm", "-f", "-v", container_id]
        )
        self.assertEqual(run.call_args_list[0].args[0][-1], container_id)
        self.assertEqual(run.call_args_list[-1].args[0][:2], ["docker", "inspect"])

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

        parsed = tuple(urlsplit(value) for value in moved)
        self.assertEqual(
            tuple((value.username, str(value.port)) for value in parsed),
            (
                ("owner", "6543"),
                ("factory_probe_runtime", "6543"),
                ("factory_probe_attestor", "6543"),
            ),
        )
        self.assertEqual(
            tuple(value.hostname for value in parsed),
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

    def test_packaged_migrations_are_contiguous_and_factory_only(self):
        migrations = discover_migrations()
        self.assertEqual([item.version for item in migrations], list(range(1, 23)))
        self.assertEqual(len({item.sha256 for item in migrations}), 22)
        for item in migrations:
            self.assertIn("factory.", item.sql)
            self.assertNotIn("trust_ci", item.sql.lower())

    def test_matching_applied_migrations_are_idempotent(self):
        migrations = discover_migrations()
        applied = [AppliedMigration(item.version, item.name, item.sha256) for item in migrations[:2]]
        self.assertEqual(plan_migrations(migrations, applied), migrations[2:])

    @staticmethod
    def _function_text(sql, signature):
        marker = f"FUNCTION factory.{signature}("
        start = sql.index(marker)
        start = sql.rindex("CREATE", 0, start)
        return sql[start : sql.index("\n$$;", start) + len("\n$$;")]

    @staticmethod
    def _guard_lines(function_sql):
        """Guard-logic lines only, normalised so block headers compare equal."""
        lines = []
        for line in function_sql.splitlines():
            stripped = line.strip()
            if (
                not stripped
                or stripped.startswith(("--", "CREATE "))
                or "repair_child_rejection" in stripped
                or "RETURN NULL" in stripped
                or "ELSE NULL" in stripped
            ):
                continue
            lines.append(re.sub(r"^(?:IF|OR) ", "", stripped))
        return lines

    def test_repair_child_rejection_resource_is_additive_and_typed(self):
        migrations = {item.version: item for item in discover_migrations()}
        original = migrations[18].sql
        upgrade = next(
            item.sql
            for item in migrations.values()
            if item.name
            == "021_semantic_repair_child_rejection_reasons.sql"
        )
        self.assertEqual(migrations[18].name, "018_semantic_validation_bridge.sql")
        self.assertIn(
            "CREATE FUNCTION factory.semantic_bind_repair_child(", original
        )
        self.assertIn(
            "CREATE OR REPLACE FUNCTION factory.semantic_bind_repair_child(",
            upgrade,
        )
        # The shipped resource stays byte-identical; only the newest resource may
        # redefine the function, so an existing database replans instead of drifting.
        # Destructive statements are judged on the resource itself, outside any function
        # body: the redefined function keeps its own legitimate binding INSERT.
        outside = re.sub(r"(?s)\$\$.*?\$\$;", "", upgrade)
        lowered = outside.lower()
        for forbidden in (
            "drop table",
            "drop index",
            "drop function",
            "drop constraint",
            "delete from",
            "truncate",
            "alter table",
            "insert into",
            "update factory.",
            "create index",
            "vacuum",
            "lock table",
        ):
            self.assertNotIn(forbidden, lowered, forbidden)
        function_sql = self._function_text(
            upgrade, "semantic_bind_repair_child"
        )
        self.assertNotIn("RETURN NULL", function_sql)
        self.assertIn("SECURITY DEFINER SET search_path=pg_catalog,factory", function_sql)
        self.assertIn(
            "GRANT EXECUTE ON FUNCTION factory.semantic_bind_repair_child(char,text)\n"
            "  TO factory_semantic_coordinator;",
            upgrade,
        )
        # Guard conditions are carried over verbatim: only the refusal channel changed.
        self.assertEqual(
            self._guard_lines(
                self._function_text(original, "semantic_bind_repair_child")
            ),
            self._guard_lines(function_sql),
        )

    def test_repair_child_rejection_reasons_match_the_python_allowlist(self):
        upgrade = next(
            item.sql
            for item in discover_migrations()
            if item.name
            == "021_semantic_repair_child_rejection_reasons.sql"
        )
        emitted = set(
            re.findall(r"'repair_child_rejection','([a-z_]+)'", upgrade)
        )
        self.assertEqual(
            emitted,
            set(REPAIR_CHILD_REJECTIONS) - {UNKNOWN_REPAIR_CHILD_REJECTION},
        )
        self.assertEqual(len(emitted), 12)

    def test_repair_child_rejection_channel_stays_disjoint_from_bindings(self):
        """INV-001 / AC-002: neither channel can be read as the other, in either direction."""
        self.assertEqual(
            repair_child_rejection_reason(
                {REPAIR_CHILD_REJECTION_CHANNEL: "deadline_exceeded"}
            ),
            "deadline_exceeded",
        )
        for unfriendly in (
            {REPAIR_CHILD_REJECTION_CHANNEL: {"reason": "deadline_exceeded"}},
            {REPAIR_CHILD_REJECTION_CHANNEL: ["deadline_exceeded"]},
            {REPAIR_CHILD_REJECTION_CHANNEL: 7},
            {REPAIR_CHILD_REJECTION_CHANNEL: ""},
            {REPAIR_CHILD_REJECTION_CHANNEL: "drop_table_please"},
        ):
            with self.subTest(unfriendly=unfriendly):
                # A hostile or unknown payload never becomes a real reason and never
                # becomes "not a rejection" either: it folds to the fixed local code.
                self.assertEqual(
                    repair_child_rejection_reason(unfriendly),
                    UNKNOWN_REPAIR_CHILD_REJECTION,
                )
        for not_an_envelope in (None, "repair_child_rejection", 7, [7], {}, {"a": 1}):
            with self.subTest(not_an_envelope=not_an_envelope):
                self.assertIsNone(repair_child_rejection_reason(not_an_envelope))
        # A document that is a well-formed binding *and* carries the rejection key is
        # refused by both readers: the envelope check needs the exact single key, and the
        # closed contract rejects the extra field. Neither path can report success.
        smuggled = {
            "schema_version": 1,
            "child_proposal_digest": "a" * 64,
            "child_task_id": "0f5f7c2e-3f3f-4a5b-9c1d-2e3f4a5b6c7d",
            "child_intent_digest": "b" * 64,
            REPAIR_CHILD_REJECTION_CHANNEL: "deadline_exceeded",
        }
        self.assertIsNone(repair_child_rejection_reason(smuggled))
        with self.assertRaises(ContractError) as raised:
            RepairChildTaskBindingV1.from_dict(smuggled)
        self.assertEqual(raised.exception.code, "unknown_fields")
        # The same four keys without the rejection field must parse, so the guard above is
        # about the extra key and not about the fixture document being invalid anyway.
        binding = dict(smuggled)
        binding.pop(REPAIR_CHILD_REJECTION_CHANNEL)
        self.assertEqual(RepairChildTaskBindingV1.from_dict(binding).child_task_id,
                         "0f5f7c2e-3f3f-4a5b-9c1d-2e3f4a5b6c7d")

    def test_bind_repair_child_separates_an_unexplained_store_refusal(self):
        # A schema that never applied 021 still answers a refusal with a bare SQL NULL.
        # That is a store refusal with no reason, not a malformed payload, and the two
        # diagnoses must not be interchangeable.
        store = PostgresSemanticCoordinatorStore(
            "postgresql://unused.invalid:5432/unused"
        )
        binding = RepairChildTaskBindingV1(
            1, "a" * 64, "0f5f7c2e-3f3f-4a5b-9c1d-2e3f4a5b6c7d", "b" * 64
        )
        for response, expected in (
            ((None,), "rejected: store_returned_null"),
            (({"unexpected": 1},), "payload is malformed"),
            (
                ({REPAIR_CHILD_REJECTION_CHANNEL: "deadline_exceeded"},),
                "rejected: deadline_exceeded",
            ),
        ):
            with self.subTest(response=response[0]):
                cursor = MagicMock()
                cursor.fetchone.return_value = response
                connection = MagicMock()
                connection.__enter__.return_value = connection
                connection.cursor.return_value.__enter__.return_value = cursor
                with patch.object(store, "_connect", return_value=connection):
                    with self.assertRaises(StoreError) as raised:
                        store.bind_repair_child(binding)
                self.assertIn(expected, str(raised.exception))
                # The NULL arm must never borrow the shape diagnosis, and vice versa.
                self.assertEqual(
                    "malformed" in str(raised.exception),
                    expected == "payload is malformed",
                )
                if expected == "payload is malformed":
                    self.assertIsInstance(raised.exception.__cause__, ContractError)
                else:
                    self.assertIsNone(raised.exception.__cause__)
                    self.assertIsNone(raised.exception.__context__)
                    self.assertNotIn(
                        "invalid_object",
                        "".join(traceback.format_exception(raised.exception)),
                    )

    def test_repair_child_guard_structure_maps_each_reason_to_one_clause_group(self):
        # `_guard_lines` compares predicate text only: 021 legitimately adds three block
        # boundaries, so boundary loss, a mislabelled group, and an inverted replay CASE
        # are pinned structurally here instead.
        migrations = {item.version: item for item in discover_migrations()}
        upgrade = self._function_text(
            migrations[21].sql, "semantic_bind_repair_child"
        )
        expected_clauses = {
            "authority_not_fresh": 2,
            "binding_payload_invalid": 8,
            "child_already_bound": 2,
            "child_limits_exceeded": 13,
            "child_task_unavailable": 3,
            "command_input_invalid": 5,
            "deadline_exceeded": 2,
            "lineage_mismatch": 32,
            "parent_task_missing": 1,
            "proposal_not_pending": 2,
        }
        measured = {
            reason: len(re.findall(r"\bOR\b", predicate)) + 1
            for predicate, reason in re.findall(
                r"IF\s+(.*?)\s*THEN\s+RETURN\s+jsonb_build_object\("
                r"'repair_child_rejection','([a-z_]+)'\);\s*END IF;",
                upgrade,
                re.S,
            )
        }
        self.assertEqual(measured, expected_clauses)
        for reason in set(REPAIR_CHILD_REJECTIONS) - {UNKNOWN_REPAIR_CHILD_REJECTION}:
            self.assertEqual(
                upgrade.count(f"'repair_child_rejection','{reason}'"),
                1,
                reason,
            )
        # The already-bound replay path returns the stored body and rejects only on a
        # mismatch; swapping the arms would silently hand back NULL as a binding.
        self.assertIn(
            "THEN v_existing.body ELSE jsonb_build_object("
            "'repair_child_rejection','binding_conflict') END;",
            " ".join(upgrade.split()),
        )
        # The superseded body is frozen: `_guard_lines` only detects drift in 021, so a
        # clause deleted from 018 and 021 together would satisfy both readers. Byte-exact on
        # purpose — 018 is shipped, so any edit to it is `plan_migrations` checksum drift for
        # every existing database and must fail here, not only at apply time.
        self.assertEqual(
            hashlib.sha256(
                self._function_text(
                    migrations[18].sql, "semantic_bind_repair_child"
                ).encode("utf-8")
            ).hexdigest(),
            "49400d2fcf408aff60ae94d6d13491ba8d910b37a614b75f642270f5dfc0dbb5",
        )

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
        execution, canonical, contract, recovery = migrations[13:17]
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
        migration = next(
            item for item in discover_migrations()
            if item.name == "018_semantic_validation_bridge.sql"
        )
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
        migration = next(
            item.sql.lower() for item in discover_migrations()
            if item.name == "018_semantic_validation_bridge.sql"
        )
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


class RepairPlanMigrationTests(unittest.TestCase):
    ORDERED_REASONS = (
        "command_input_invalid", "repair_payload_invalid", "cycle_lineage_invalid",
        "idempotency_conflict", "subject_not_found", "verdict_mismatch",
        "execution_material_missing", "previous_proposal_mismatch",
        "child_handoff_mismatch", "lineage_mismatch", "baseline_risk_invalid",
        "idempotency_conflict", "directive_conflict", "child_proposal_conflict",
        "store_operation_rejected",
    )

    def plan_migration(self):
        migrations = discover_migrations()
        self.assertEqual(migrations[-1].version, 22)
        self.assertEqual(migrations[-1].name,
                         "022_semantic_repair_plan_rejection_reasons.sql")
        return migrations, migrations[-1]

    def test_original_prefix_is_frozen_and_only_the_plan_upgrade_is_pending(self):
        migrations, latest = self.plan_migration()
        historical = PRE_RECOVERY_MIGRATIONS + (
            (17, "017_execution_recovery_topology.sql", "4114b0a1d3b5e8ab86227b0bd2dd459d62d023d033d1ff2b9b5bdc66aaa07da1"),
            (18, "018_semantic_validation_bridge.sql", "33053563dce7c34edfa9301130272adb34651d44dd1f2bc305ba3eec01382c70"),
            (19, "019_usage_token_components.sql", "e0cf573b2bd183f5bf6291f02d330e98edf7d4e00d34944daba5719eee91c790"),
            (20, "020_execution_v2_priced_usage.sql", "524c94bf95f38f8a339c3f5b1165d7f7b7fffc81eb7fd8a2faff4362f33d2ae3"),
            (21, "021_semantic_repair_child_rejection_reasons.sql", "868bc21f47351f92b79acb8bd8e9390c62b43803c0b5761400e32c7143d56d5e"),
        )
        self.assertEqual(tuple((m.version, m.name, m.sha256) for m in migrations[:-1]),
                         historical)
        applied = [AppliedMigration(*item) for item in historical]
        self.assertEqual(plan_migrations(migrations, applied), (latest,))
        applied.append(AppliedMigration(latest.version, latest.name, latest.sha256))
        self.assertEqual(plan_migrations(migrations, applied), ())

    def test_plan_function_reverses_exactly_to_the_frozen_original_body(self):
        migrations, latest = self.plan_migration()
        original = MigrationTests._function_text(migrations[17].sql, "semantic_plan_repair")
        replacement = MigrationTests._function_text(latest.sql, "semantic_plan_repair")
        self.assertEqual(hashlib.sha256(original.encode("utf-8")).hexdigest(),
                         "5ceffc2373c2cb7849f3accc79ed9b6b9b51024ce7b36f975c50ca71530e7d32")
        expression = r"jsonb_build_object\('repair_plan_rejection','([a-z_]+)'\)"
        self.assertEqual(tuple(re.findall(expression, replacement)), self.ORDERED_REASONS)
        self.assertEqual(len(set(self.ORDERED_REASONS)), 14)
        restored, replacements = re.subn(expression, "NULL", replacement)
        self.assertEqual(replacements, 15)
        restored = restored.replace("CREATE OR REPLACE FUNCTION", "CREATE FUNCTION", 1)
        self.assertEqual(restored, original)
        self.assertNotRegex(replacement, r"(?:RETURN|ELSE)\s+NULL\b")
        replay = ("THEN v_prior.response_body ELSE jsonb_build_object("
                  "'repair_plan_rejection','idempotency_conflict') END;")
        self.assertEqual(" ".join(replacement.split()).count(replay), 2)

    def test_plan_sql_vocabulary_matches_only_the_plan_python_channel(self):
        _migrations, latest = self.plan_migration()
        self.assertTrue(hasattr(semantic_repair, "REPAIR_PLAN_REJECTIONS"))
        emitted = set(re.findall(r"'repair_plan_rejection','([a-z_]+)'", latest.sql))
        self.assertEqual(emitted, set(self.ORDERED_REASONS))
        self.assertEqual(emitted, semantic_repair.REPAIR_PLAN_REJECTIONS - {"planning_rejected"})
        self.assertNotIn("deadline_exhausted", emitted)
        self.assertNotIn("store_returned_null", emitted)
        self.assertNotIn("repair_child_rejection", latest.sql)

    def test_plan_upgrade_changes_no_schema_or_capability_boundary(self):
        _migrations, latest = self.plan_migration()
        function = MigrationTests._function_text(latest.sql, "semantic_plan_repair")
        self.assertTrue(function.startswith("CREATE OR REPLACE FUNCTION factory.semantic_plan_repair("))
        self.assertIn("p_idempotency_key char(64),p_request_digest char(64),\n"
                      "  p_request_canonical text,p_task_id uuid\n) RETURNS jsonb", function)
        self.assertIn("LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$", function)
        outside = latest.sql.replace(function, "")
        outside = re.sub(r"(?m)^--[^\n]*", "", outside).strip()
        self.assertEqual(outside,
            "REVOKE ALL ON FUNCTION factory.semantic_plan_repair(char,char,text,uuid) FROM PUBLIC;\n"
            "GRANT EXECUTE ON FUNCTION factory.semantic_plan_repair(char,char,text,uuid)\n"
            "  TO factory_semantic_coordinator;")


if __name__ == "__main__":
    unittest.main()
