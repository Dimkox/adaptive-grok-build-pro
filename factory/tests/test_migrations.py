import unittest
from unittest.mock import patch
import subprocess
import os
import re
import signal
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

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
        nonce = "b" * 32
        volume = f"adaptive-factory-exit-volume-{nonce}"
        replies = [
            SimpleNamespace(returncode=0, stdout=volume),
            SimpleNamespace(returncode=0, stdout=container_id),
            SimpleNamespace(returncode=0, stdout="127.0.0.1:5432\n"),
        ]
        def docker_run(command, **kwargs):
            if command[:3] == ["docker", "exec", container_id]:
                return SimpleNamespace(returncode=0, stdout="")
            if command[:3] == ["docker", "ps", "-a"]:
                return SimpleNamespace(returncode=0, stdout="")
            return replies.pop(0)
        with patch.object(run_disposable_exit, "uuid") as uuid_mock, patch.object(
            uuid_mock, "uuid4", side_effect=[SimpleNamespace(hex=nonce), SimpleNamespace(hex="c" * 32)]
        ), patch.object(run_disposable_exit, "_reap_orphans", return_value=[]), patch.object(
            run_disposable_exit, "_docker_run", side_effect=docker_run
        ) as docker_run_mock, patch.object(
            run_disposable_exit, "_volume_binding_matches", return_value=True
        ), patch.object(run_disposable_exit, "_container_binding", return_value=True), patch.object(
            run_disposable_exit, "_final_postgres_ready", return_value=True
        ), patch.object(run_disposable_exit, "_run") as run, patch.object(
            run_disposable_exit, "_cleanup_owned", return_value=[f"container={container_id}", f"volume={volume}"]
        ), patch("builtins.print") as printed:
            self.assertEqual(run_disposable_exit.main(), 0)
        docker_commands = [call.args[0] for call in docker_run_mock.call_args_list]
        self.assertEqual(docker_commands[1][0:2], ["docker", "run"])
        self.assertIn("--mount", docker_commands[1])
        self.assertIn(f"type=volume,src={volume},dst=/var/lib/postgresql/data", docker_commands[1])
        self.assertEqual(docker_commands[2], ["docker", "port", container_id, "5432/tcp"])
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn("--preflight-only", commands[0])
        self.assertIn("unittest", commands[1])
        self.assertEqual([call.kwargs["timeout"] for call in run.call_args_list], [30, 430, 40])
        self.assertEqual(printed.call_args_list[-1].args,
                         ("PASS: disposable PostgreSQL + API + effective roles + actual restart/reconciliation",))

    def test_exit_runner_reports_leaked_id_without_cleanup_when_binding_fails(self):
        container_id, nonce = "a" * 64, "b" * 32
        volume = f"adaptive-factory-exit-volume-{nonce}"
        with patch.object(run_disposable_exit, "uuid") as uuid_mock, patch.object(
            uuid_mock, "uuid4", side_effect=[SimpleNamespace(hex=nonce), SimpleNamespace(hex="c" * 32)]
        ), patch.object(run_disposable_exit, "_reap_orphans", return_value=[]), patch.object(
            run_disposable_exit, "_docker_run", side_effect=[
                SimpleNamespace(returncode=0, stdout=volume),
                SimpleNamespace(returncode=0, stdout=container_id),
            ]
        ), patch.object(run_disposable_exit, "_volume_binding_matches", return_value=True), patch.object(
            run_disposable_exit, "_container_binding", return_value=False
        ), patch.object(run_disposable_exit, "_cleanup_owned", return_value=[]) as cleanup, patch.object(
            run_disposable_exit, "_run"
        ) as run:
            self.assertEqual(run_disposable_exit.main(), 1)
        run.assert_not_called()
        cleanup.assert_called_once()

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
        volume = f"adaptive-factory-exit-volume-{nonce}"
        valid = f"{container_id}\t/{name}\tpostgres:17-alpine\trunning\t{nonce}\tvolume:{volume}:/var/lib/postgresql/data\n"
        variants = (
            valid.replace(container_id, "c" * 64, 1),
            valid.replace(f"/{name}", "/other", 1),
            valid.replace("postgres:17-alpine", "postgres:18-alpine", 1),
            valid.replace("\trunning\t", "\tremoving\t", 1),
            valid.replace(nonce, "d" * 32, 1),
            valid.replace(f"volume:{volume}", "volume:other", 1),
        )
        for output in variants:
            with self.subTest(output=output), patch.object(
                run_disposable_exit, "_docker_run",
                return_value=SimpleNamespace(returncode=0, stdout=output),
            ):
                self.assertFalse(run_disposable_exit._container_binding(
                    container_id, name, nonce, volume, require_running=True
                ))

        output = valid.replace("\trunning\t", "\texited\t", 1)
        with patch.object(run_disposable_exit, "_docker_run", return_value=SimpleNamespace(
            returncode=0, stdout=output
        )):
            self.assertTrue(run_disposable_exit._container_binding(
                container_id, name, nonce, volume, require_running=False
            ))
        def valid_binding():
            return patch.object(
                run_disposable_exit, "_container_binding", return_value=True
            )
        with valid_binding(), patch.object(run_disposable_exit, "_docker_run", return_value=SimpleNamespace(
            returncode=0, stdout=""
        )) as docker:
            self.assertTrue(run_disposable_exit._remove_container(container_id, name, nonce, volume))
        self.assertEqual(docker.call_args.args[0], ["docker", "rm", "-f", container_id])
        self.assertEqual(docker.call_args.kwargs["timeout"], run_disposable_exit._CLEANUP_COMMAND_TIMEOUT)

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
            if command[:3] == ["docker", "volume", "create"]:
                raise subprocess.CalledProcessError(125, command)
            return SimpleNamespace(returncode=1, stdout="", stderr="")

        with patch.object(run_disposable_exit, "_reap_orphans", return_value=[]), patch.object(
            run_disposable_exit.subprocess, "run", side_effect=failed_create
        ):
            self.assertEqual(run_disposable_exit.main(), 1)
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
        self.assertEqual(run.call_args_list[0].kwargs["timeout"], 5)
        self.assertEqual(run.call_args_list[1].kwargs["timeout"], 5)

        not_final = type("Completed", (), {"returncode": 1})()
        with patch.object(run_disposable_exit.subprocess, "run", return_value=not_final) as run:
            self.assertFalse(run_disposable_exit._final_postgres_ready("factory-test"))
        self.assertEqual(run.call_count, 1)

    def test_exit_runner_removes_only_fully_bound_container_and_volume(self):
        container_id, nonce = "a" * 64, "b" * 32
        name = f"adaptive-factory-exit-{nonce[:12]}"
        volume = f"adaptive-factory-exit-volume-{nonce}"
        with patch.object(run_disposable_exit, "_resolve_container_id", return_value=container_id), patch.object(
            run_disposable_exit, "_container_binding", return_value=True
        ), patch.object(run_disposable_exit, "_remove_container", return_value=True) as remove_container, patch.object(
            run_disposable_exit, "_remove_volume", return_value=True
        ) as remove_volume:
            cleaned = run_disposable_exit._cleanup_owned(name, nonce, volume, container_id)
        self.assertEqual(cleaned, [f"container={container_id}", f"volume={volume}"])
        remove_container.assert_called_once()
        self.assertEqual(remove_container.call_args.args, (container_id, name, nonce, volume))
        remove_volume.assert_called_once_with(volume, nonce, timeout=20)

    def test_exit_runner_retries_delayed_name_visibility_then_removes_exact_bindings(self):
        container_id, nonce = "a" * 64, "b" * 32
        name, volume = f"adaptive-factory-exit-{nonce[:12]}", f"adaptive-factory-exit-volume-{nonce}"
        with patch.object(run_disposable_exit, "_resolve_container_id", side_effect=[None, container_id]) as resolve, patch.object(
            run_disposable_exit, "_container_binding", return_value=True
        ) as binding, patch.object(run_disposable_exit, "_docker_run", return_value=SimpleNamespace(
            returncode=0, stdout="", stderr=""
        )) as docker, patch.object(run_disposable_exit, "_remove_volume", return_value=True), patch.object(
            run_disposable_exit.time, "sleep"
        ):
            cleaned = run_disposable_exit._cleanup_owned(name, nonce, volume, None)
        self.assertEqual(cleaned, [f"container={container_id}", f"volume={volume}"])
        self.assertEqual(resolve.call_count, 2)
        self.assertEqual(binding.call_count, 2)
        self.assertEqual(docker.call_args.args[0], ["docker", "rm", "-f", container_id])

    def test_exit_runner_caps_container_reaper_bytes_and_rows(self):
        nonce_values = [f"{value:032x}" for value in range(1, 101)]
        rows = "\n".join(
            f"{'a' * 64}\tadaptive-factory-exit-{nonce[:12]}\tpostgres:17-alpine\texited\t{nonce}\t2000-01-01 00:00:00 +0000 UTC"
            for nonce in nonce_values
        ) + "\n"
        calls = []
        def listed(command, **kwargs):
            calls.append((command, kwargs))
            if command[:3] == ["docker", "ps", "-a"]:
                return SimpleNamespace(returncode=0, stdout=rows)
            if command[:3] == ["docker", "volume", "ls"]:
                return SimpleNamespace(returncode=0, stdout="")
            return SimpleNamespace(returncode=0, stdout="")
        with patch.object(run_disposable_exit, "_docker_run", side_effect=listed), patch.object(
            run_disposable_exit, "_container_binding", return_value=False
        ), patch.object(run_disposable_exit, "_parse_docker_created", wraps=run_disposable_exit._parse_docker_created) as parse_time, patch(
            "builtins.print"
        ):
            run_disposable_exit._reap_orphans("f" * 32)
        self.assertEqual(parse_time.call_count, 20)
        listing_kwargs = calls[0][1]
        self.assertIsNotNone(listing_kwargs.get("max_output_bytes"))
        self.assertGreater(listing_kwargs["max_output_bytes"], 0)

    def test_docker_bounded_listing_stops_at_output_limit(self):
        command = [sys.executable, "-c", "import sys; sys.stdout.write('x' * 1000000)"]
        result = run_disposable_exit._docker_run(command, timeout=5, max_output_bytes=128)
        self.assertEqual(result.returncode, 125)
        self.assertTrue(getattr(result, "output_limit_exceeded", False))
        self.assertLessEqual(len(result.stdout.encode()), 128)

    def test_exit_runner_reports_container_list_overflow_as_backlog_and_continues(self):
        overflow = SimpleNamespace(returncode=125, stdout="partial", stderr="too large", output_limit_exceeded=True)
        calls = []

        def listed(command, **kwargs):
            calls.append(command)
            if command[:3] == ["docker", "ps", "-a"]:
                return overflow
            if command[:3] == ["docker", "volume", "ls"]:
                return overflow
            self.fail(f"unexpected Docker command: {command}")

        with patch.object(run_disposable_exit, "_docker_run", side_effect=listed), patch(
            "builtins.print"
        ) as printed:
            self.assertEqual(run_disposable_exit._reap_orphans("e" * 32), [])
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][:3], ["docker", "ps", "-a"])
        self.assertEqual(calls[1][:3], ["docker", "volume", "ls"])
        messages = [str(call.args[0]) for call in printed.call_args_list]
        self.assertTrue(any("BACKLOG labelled_containers=unknown" in line and "output_limit" in line for line in messages))
        self.assertTrue(any("BACKLOG labelled_volumes=unknown" in line and "output_limit" in line for line in messages))

    def test_bounded_docker_listing_keyboard_interrupt_stops_process_group(self):
        with tempfile.TemporaryDirectory() as raw:
            pid_file = Path(raw) / "listing.pid"
            child_pid_file = Path(raw) / "child.pid"
            child_code = (
                "import os,pathlib,signal,time\n"
                "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                f"pathlib.Path({str(child_pid_file)!r}).write_text(str(os.getpid()))\n"
                "time.sleep(30)\n"
            )
            root_code = (
                "import os,pathlib,subprocess,sys,time\n"
                f"pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
                f"subprocess.Popen([sys.executable, '-c', {child_code!r}], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
                f"deadline = time.monotonic() + 2\nwhile not pathlib.Path({str(child_pid_file)!r}).exists() and time.monotonic() < deadline: time.sleep(.01)\n"
                "print('ready', flush=True)\n"
                "while True: time.sleep(.01)\n"
            )
            command = [sys.executable, "-c", root_code]
            original_popen = subprocess.Popen

            def started_popen(*args, **kwargs):
                process = original_popen(*args, **kwargs)
                deadline = time.monotonic() + 2
                while (not pid_file.exists() or not child_pid_file.exists()) and time.monotonic() < deadline:
                    time.sleep(0.01)
                if not pid_file.exists() or not child_pid_file.exists():
                    self.fail("listing subprocess did not become ready")
                return process

            pids = []
            try:
                with patch.object(run_disposable_exit.subprocess, "Popen", side_effect=started_popen), patch.object(
                    run_disposable_exit.selectors.DefaultSelector, "select", side_effect=KeyboardInterrupt
                ):
                    with self.assertRaises(KeyboardInterrupt):
                        run_disposable_exit._docker_run(command, timeout=10, max_output_bytes=128)
                pids = [int(pid_file.read_text()), int(child_pid_file.read_text())]
                for pid in pids:
                    with self.assertRaises(ProcessLookupError):
                        os.kill(pid, 0)
            finally:
                for process_file in (pid_file, child_pid_file):
                    if process_file.exists():
                        try:
                            os.kill(int(process_file.read_text()), signal.SIGKILL)
                        except ProcessLookupError:
                            pass

    def test_bounded_docker_listing_interrupt_during_selector_setup_stops_process_group(self):
        with tempfile.TemporaryDirectory() as raw:
            pid_file = Path(raw) / "listing.pid"
            child_pid_file = Path(raw) / "child.pid"
            child_code = (
                "import os,pathlib,signal,time\n"
                "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                f"pathlib.Path({str(child_pid_file)!r}).write_text(str(os.getpid()))\n"
                "time.sleep(30)\n"
            )
            root_code = (
                "import os,pathlib,subprocess,sys,time\n"
                f"pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
                f"subprocess.Popen([sys.executable, '-c', {child_code!r}], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
                f"deadline = time.monotonic() + 2\nwhile not pathlib.Path({str(child_pid_file)!r}).exists() and time.monotonic() < deadline: time.sleep(.01)\n"
                "print('ready', flush=True)\n"
                "while True: time.sleep(.01)\n"
            )
            command = [sys.executable, "-c", root_code]
            original_popen = subprocess.Popen

            def started_popen(*args, **kwargs):
                process = original_popen(*args, **kwargs)
                deadline = time.monotonic() + 2
                while (not pid_file.exists() or not child_pid_file.exists()) and time.monotonic() < deadline:
                    time.sleep(0.01)
                if not pid_file.exists() or not child_pid_file.exists():
                    self.fail("listing subprocess did not become ready")
                return process

            try:
                with patch.object(run_disposable_exit.subprocess, "Popen", side_effect=started_popen), patch.object(
                    run_disposable_exit.selectors.DefaultSelector, "register", side_effect=KeyboardInterrupt
                ):
                    with self.assertRaises(KeyboardInterrupt):
                        run_disposable_exit._docker_run(command, timeout=10, max_output_bytes=128)
                for pid_file in (pid_file, child_pid_file):
                    with self.assertRaises(ProcessLookupError):
                        os.kill(int(pid_file.read_text()), 0)
            finally:
                for process_file in (pid_file, child_pid_file):
                    if process_file.exists():
                        try:
                            os.kill(int(process_file.read_text()), signal.SIGKILL)
                        except ProcessLookupError:
                            pass

    def test_exit_runner_volume_inspect_uses_docker_labels_map_template(self):
        volume, nonce = "adaptive-factory-exit-volume-" + "b" * 32, "b" * 32
        output = f"{volume}\tlocal\t{nonce}\t2026-09-18T00:00:00Z\n"
        with patch.object(run_disposable_exit, "_docker_run", return_value=SimpleNamespace(
            returncode=0, stdout=output
        )) as docker:
            self.assertEqual(run_disposable_exit._inspect_volume(volume), (volume, "local", nonce, "2026-09-18T00:00:00Z"))
        template = docker.call_args.args[0][4]
        self.assertIn(f'index .Labels "{run_disposable_exit._LABEL}"', template)

    def test_exit_runner_container_inspect_uses_config_labels_map_template(self):
        container_id, nonce = "a" * 64, "b" * 32
        name, volume = f"adaptive-factory-exit-{nonce[:12]}", f"adaptive-factory-exit-volume-{nonce}"
        output = f"{container_id}\t/{name}\tpostgres:17-alpine\trunning\t{nonce}\tvolume:{volume}:/var/lib/postgresql/data\n"
        with patch.object(run_disposable_exit, "_docker_run", return_value=SimpleNamespace(
            returncode=0, stdout=output
        )) as docker:
            self.assertTrue(run_disposable_exit._container_binding(container_id, name, nonce, volume))
        template = docker.call_args.args[0][3]
        self.assertIn(f'index .Config.Labels "{run_disposable_exit._LABEL}"', template)

    def test_exit_runner_parses_timezone_offset_and_reclaims_verified_stale_container(self):
        container_id, nonce = "a" * 64, "b" * 32
        name = f"adaptive-factory-exit-{nonce[:12]}"
        volume = f"adaptive-factory-exit-volume-{nonce}"
        created = run_disposable_exit._parse_docker_created("2000-01-01 00:00:00 +0000 UTC")
        from datetime import timezone
        self.assertEqual(created.tzinfo, timezone.utc)
        row = f"{container_id}\t{name}\tpostgres:17-alpine\texited\t{nonce}\t2000-01-01 00:00:00 +0000 UTC\n"
        def listed(command, **kwargs):
            if command[:3] == ["docker", "ps", "-a"]:
                return SimpleNamespace(returncode=0, stdout=row)
            if command[:3] == ["docker", "volume", "ls"]:
                return SimpleNamespace(returncode=0, stdout="")
            self.fail(f"unexpected Docker command: {command}")
        with patch.object(run_disposable_exit, "_docker_run", side_effect=listed), patch.object(
            run_disposable_exit, "_container_binding", return_value=True
        ) as binding, patch.object(run_disposable_exit, "_volume_binding_matches", return_value=True), patch.object(
            run_disposable_exit, "_remove_container", return_value=True
        ) as remove_container, patch.object(run_disposable_exit, "_remove_volume", return_value=True) as remove_volume, patch(
            "builtins.print"
        ) as printed:
            reclaimed = run_disposable_exit._reap_orphans("c" * 32)
        self.assertEqual(len(reclaimed), 1)
        self.assertRegex(reclaimed[0], re.escape(f"container={container_id} volume={volume} nonce={nonce} age_seconds=") + r"\d+$")
        binding.assert_called_once_with(container_id, name, nonce, volume, timeout=5)
        remove_container.assert_called_once_with(container_id, name, nonce, volume)
        remove_volume.assert_called_once_with(volume, nonce, timeout=20)
        self.assertTrue(any("RECLAIMED" in str(call.args[0]) for call in printed.call_args_list))

    def test_exit_runner_reaper_preserves_stale_row_when_exact_binding_fails(self):
        container_id, nonce = "a" * 64, "b" * 32
        name = f"adaptive-factory-exit-{nonce[:12]}"
        row = f"{container_id}\t{name}\tpostgres:17-alpine\trunning\t{nonce}\t2000-01-01 00:00:00 +0000 UTC\n"
        def listed(command, **kwargs):
            if command[:3] == ["docker", "ps", "-a"]:
                return SimpleNamespace(returncode=0, stdout=row)
            if command[:3] == ["docker", "volume", "ls"]:
                return SimpleNamespace(returncode=0, stdout="")
            return SimpleNamespace(returncode=0, stdout="")
        with patch.object(run_disposable_exit, "_docker_run", side_effect=listed) as docker, patch.object(
            run_disposable_exit, "_container_binding", return_value=False
        ), patch.object(run_disposable_exit, "_remove_container") as remove_container, patch.object(
            run_disposable_exit, "_remove_volume"
        ) as remove_volume:
            self.assertEqual(run_disposable_exit._reap_orphans("c" * 32), [])
        remove_container.assert_not_called()
        remove_volume.assert_not_called()
        self.assertFalse(any(call.args[0][:3] == ["docker", "rm", "-f"] for call in docker.call_args_list))
        container_list = next(call.args[0] for call in docker.call_args_list if call.args[0][:3] == ["docker", "ps", "-a"])
        self.assertIn(f'{{{{.Label "{run_disposable_exit._LABEL}"}}}}', container_list[-1])
        volume_list = next(call.args[0] for call in docker.call_args_list if call.args[0][:3] == ["docker", "volume", "ls"])
        self.assertIn(f'{{{{.Label "{run_disposable_exit._LABEL}"}}}}', volume_list[-1])

    def test_exit_runner_reports_reaper_backlog_and_processes_only_one_candidate(self):
        nonces = ("b" * 32, "c" * 32)
        rows = "\n".join(
            f"{'a' * 64}\tadaptive-factory-exit-{nonce[:12]}\tpostgres:17-alpine\texited\t{nonce}\t2000-01-01 00:00:00 +0000 UTC"
            for nonce in nonces
        ) + "\n"
        def listed(command, **kwargs):
            if command[:3] == ["docker", "ps", "-a"]:
                return SimpleNamespace(returncode=0, stdout=rows)
            if command[:3] == ["docker", "volume", "ls"]:
                return SimpleNamespace(returncode=0, stdout="")
            return SimpleNamespace(returncode=0, stdout="")
        with patch.object(run_disposable_exit, "_docker_run", side_effect=listed), patch.object(
            run_disposable_exit, "_container_binding", return_value=False
        ) as binding, patch("builtins.print") as printed:
            self.assertEqual(run_disposable_exit._reap_orphans("d" * 32), [])
        binding.assert_called_once()
        self.assertTrue(any("BACKLOG" in str(call.args[0]) for call in printed.call_args_list))

    def test_exit_runner_shares_reclaim_candidate_budget_across_resource_types(self):
        container_id, nonce = "a" * 64, "b" * 32
        name = f"adaptive-factory-exit-{nonce[:12]}"
        bound_volume = f"adaptive-factory-exit-volume-{nonce}"
        orphan_nonce = "c" * 32
        orphan_volume = f"adaptive-factory-exit-volume-{orphan_nonce}"
        container_row = (
            f"{container_id}\t{name}\t{run_disposable_exit._IMAGE}\t"
            f"exited\t{nonce}\t2000-01-01 00:00:00 +0000 UTC"
        )
        volume_rows = f"{bound_volume}\t{nonce}\n{orphan_volume}\t{orphan_nonce}"

        def listed(command, **kwargs):
            if command[:3] == ["docker", "ps", "-a"]:
                return SimpleNamespace(returncode=0, stdout=container_row)
            if command[:3] == ["docker", "volume", "ls"]:
                return SimpleNamespace(returncode=0, stdout=volume_rows)
            return SimpleNamespace(returncode=0, stdout="")

        def inspect_volume(volume, *, timeout=5):
            label_nonce = nonce if volume == bound_volume else orphan_nonce
            return (volume, "local", label_nonce, "2000-01-01T00:00:00Z")

        with patch.object(run_disposable_exit, "_docker_run", side_effect=listed) as docker, patch.object(
            run_disposable_exit, "_container_binding", return_value=True
        ), patch.object(run_disposable_exit, "_volume_binding_matches", return_value=True), patch.object(
            run_disposable_exit, "_remove_container", return_value=True
        ), patch.object(run_disposable_exit, "_remove_volume", return_value=True) as remove_volume, patch.object(
            run_disposable_exit, "_inspect_volume", side_effect=inspect_volume
        ), patch.object(run_disposable_exit, "_volume_has_container_reference", return_value=False), patch(
            "builtins.print"
        ) as printed:
            reclaimed = run_disposable_exit._reap_orphans("d" * 32)

        self.assertEqual(len(reclaimed), 1)
        self.assertIn(f"container={container_id} volume={bound_volume}", reclaimed[0])
        remove_volume.assert_called_once()
        self.assertFalse(any(command[:3] == ["docker", "volume", "rm"] for command in (
            call.args[0] for call in docker.call_args_list
        )))
        self.assertTrue(any("stale_volumes=2" in str(call.args[0]) and "reclaiming=0" in str(call.args[0])
                            for call in printed.call_args_list))

    def test_exit_runner_partial_create_is_unwound_and_exact_volume_mount_is_used(self):
        nonce = "b" * 32
        volume = f"adaptive-factory-exit-volume-{nonce}"
        container_id = "a" * 64
        commands = []
        def docker(command, **kwargs):
            commands.append(command)
            if command[:3] == ["docker", "volume", "create"]:
                return SimpleNamespace(returncode=0, stdout=volume)
            if command[:2] == ["docker", "run"]:
                return SimpleNamespace(returncode=0, stdout=container_id)
            if command[:2] == ["docker", "port"]:
                return SimpleNamespace(returncode=1, stdout="")
            return SimpleNamespace(returncode=0, stdout="")
        with patch.object(run_disposable_exit, "uuid") as uuid_mock, patch.object(
            uuid_mock, "uuid4", side_effect=[SimpleNamespace(hex=nonce), SimpleNamespace(hex="c" * 32)]
        ), patch.object(run_disposable_exit, "_reap_orphans", return_value=[]), patch.object(
            run_disposable_exit, "_docker_run", side_effect=docker
        ), patch.object(run_disposable_exit, "_volume_binding_matches", return_value=True), patch.object(
            run_disposable_exit, "_container_binding", return_value=True
        ), patch.object(run_disposable_exit, "_cleanup_owned", return_value=["volume"] ) as cleanup:
            self.assertEqual(run_disposable_exit.main(), 1)
        self.assertIn("--mount", commands[1])
        self.assertIn(f"type=volume,src={volume},dst=/var/lib/postgresql/data", commands[1])
        self.assertEqual(cleanup.call_args.args[0], f"adaptive-factory-exit-{nonce[:12]}")
        self.assertEqual(cleanup.call_args.args[1:], (nonce, volume, container_id))

    def test_packaged_migrations_are_contiguous_and_factory_only(self):
        migrations = discover_migrations()
        self.assertEqual([item.version for item in migrations], list(range(1, 21)))
        self.assertEqual(len({item.sha256 for item in migrations}), 20)
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


if __name__ == "__main__":
    unittest.main()
