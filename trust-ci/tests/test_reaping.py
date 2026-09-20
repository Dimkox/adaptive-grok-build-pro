"""Issue #158: the long-lived Trust CI worker adopts children it never reaps.

The worker is PID 1 of its container, so the kernel reparents every orphan in that
namespace to it, and an adopted child that exits stays a zombie until the worker
calls ``waitpid()``.  These arms cover the reap, the anti-race property, and the
unchanged cancellation classification.

``adaptive_trust_ci.reap`` is imported *inside* the tests that need it, never at
module level: ``AdoptedChildReapingTests.test_lease_boundary_reaps_adopted_child``
must stay runnable against an unmodified tree so it can be proved red before green.
"""

from __future__ import annotations

import ast
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SRC_ROOT = Path(__file__).resolve().parents[1] / 'src' / 'adaptive_trust_ci'
REPO_ROOT = Path(__file__).resolve().parents[2]

# A child that forks a helper which outlives it: the shape of ``git fetch``
# leaving ``git remote-https`` behind, which is what issue #158 measures.
ORPHAN_LEAVING_SHELL = 'sleep 0.3 & exit 0'

_SCENARIO_SCRIPT = r"""
import ctypes, json, os, sys, time
from pathlib import Path
from types import SimpleNamespace

# PID 1 of a PID namespace is the kernel's reaper for it.  An unprivileged test
# gets the same adoption semantics from PR_SET_CHILD_SUBREAPER.
libc = ctypes.CDLL('libc.so.6', use_errno=True)
if libc.prctl(36, 1, 0, 0, 0) != 0:
    raise SystemExit('prctl(PR_SET_CHILD_SUBREAPER) failed')

from adaptive_trust_ci import workspace as workspace_module
from adaptive_trust_ci.lease import LeaseKeeper

ME = os.getpid()


def zombie_children():
    # /proc/<pid>/stat after the '(comm) ' prefix: 0=state 1=ppid 2=pgrp 3=session.
    found = []
    for entry in os.scandir('/proc'):
        if not entry.name.isdecimal():
            continue
        try:
            fields = Path(entry.path, 'stat').read_text(encoding='ascii').rsplit(') ', 1)[1].split()
        except (FileNotFoundError, IndexError, OSError):
            continue
        if fields[0] == 'Z' and fields[1] == str(ME):
            found.append(int(entry.name))
    return sorted(found)


def settle(want_zombies):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        seen = zombie_children()
        if bool(seen) == want_zombies:
            return seen
        time.sleep(0.02)
    return zombie_children()


# The worker's own git spawn helper runs a command that leaves a helper behind.
workspace_module._run_bounded_process(
    ['/bin/sh', '-c', sys.argv[2]],
    cwd=Path(os.getcwd()),
    env=dict(os.environ),
    timeout=20,
    stdout_limit=4096,
    stderr_limit=4096,
    stdout_consumer=lambda _chunk: None,
)

adopted = settle(True)
if sys.argv[1] == 'boundary':
    LeaseKeeper(SimpleNamespace(), 'job-id', 'worker-id', 60).check()
remaining = settle(False)
print(json.dumps({'mode': sys.argv[1], 'adopted': adopted, 'remaining': remaining}))
"""


def _run_adoption_scenario(mode: str, orphan_shell: str = ORPHAN_LEAVING_SHELL) -> dict[str, object]:
    """Run the adopt-then-reap scenario in a disposable subreaper process."""
    completed = subprocess.run(
        [sys.executable, '-c', _SCENARIO_SCRIPT, mode, orphan_shell],
        cwd=str(REPO_ROOT),
        env={**os.environ, 'PYTHONPATH': str(SRC_ROOT.parent)},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f'scenario process failed ({mode}): {completed.stderr[-2000:]}')
    return json.loads(completed.stdout.strip().splitlines()[-1])


def _proc_state(pid: int) -> str:
    try:
        fields = Path(f'/proc/{pid}/stat').read_text(encoding='ascii').rsplit(') ', 1)[1].split()
    except (FileNotFoundError, IndexError, OSError):
        return 'gone'
    return fields[0]


def _wait_for_zombie(pid: int, *, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _proc_state(pid) == 'Z':
            return True
        time.sleep(0.02)
    return False


def _zombie_children_of(pid: int) -> list[int]:
    """Exited children of ``pid`` that nobody has reaped yet."""
    found = []
    for entry in os.scandir('/proc'):
        if not entry.name.isdecimal():
            continue
        try:
            fields = Path(entry.path, 'stat').read_text(encoding='ascii').rsplit(') ', 1)[1].split()
        except (FileNotFoundError, IndexError, OSError):
            continue
        if fields[0] == 'Z' and fields[1] == str(pid):
            found.append(int(entry.name))
    return sorted(found)


class AdoptedChildReapingTests(unittest.TestCase):
    """Arm 1: the reaping boundary removes adopted children, and it is what removes them."""

    def test_lease_boundary_reaps_adopted_child(self) -> None:
        report = _run_adoption_scenario('boundary')
        self.assertEqual(
            len(report['adopted']), 1,
            'scenario did not reproduce the leak: no exited child was ever adopted',
        )
        self.assertEqual(
            report['remaining'], [],
            'an adopted exited child survived the reaping boundary; it stays in the PID table '
            'for the lifetime of the container',
        )

    def test_control_without_a_reaping_boundary_keeps_the_zombie(self) -> None:
        """The same adoption in the same process, with no boundary call at all.

        This is the unmodified worker's behaviour and the reason arm 1 cannot pass
        vacuously: a zombie is never cleared by anything except its parent reaping.
        """
        report = _run_adoption_scenario('none')
        self.assertEqual(len(report['adopted']), 1)
        self.assertEqual(len(report['remaining']), 1, 'the adopted zombie disappeared without being reaped')

    def test_worker_loop_boundary_reaps_and_still_returns_after_one_pass(self) -> None:
        from adaptive_trust_ci import worker as worker_module

        store = SimpleNamespace(ping=lambda: None, claim=lambda *args, **kwargs: None)
        catalog = SimpleNamespace(lease_seconds=60)
        worker = worker_module.Worker(
            settings=SimpleNamespace(
                common=SimpleNamespace(stopped=False),
                poll_interval_seconds=0.01,
                worker_id='worker',
            ),
            store=store,
            catalog=catalog,
            runner_factory=lambda policy: None,
            stop_event=threading.Event(),
        )
        with mock.patch.object(worker_module, 'reap_adopted_children') as reaped:
            self.assertEqual(worker.run(once=True), 0)
        self.assertGreaterEqual(reaped.call_count, 1, 'the worker loop never reached a reaping boundary')


class TrackedChildStatusTests(unittest.TestCase):
    """Arm 2: the drain must never take a status a ``Popen`` is still owed."""

    def test_drain_preserves_the_return_code_of_a_tracked_child(self) -> None:
        from adaptive_trust_ci import reap

        observed: dict[str, object] = {}

        def owner() -> None:
            try:
                with reap.spawn_in_progress():
                    process = subprocess.Popen(
                        [sys.executable, '-c', 'import time; time.sleep(0.5); raise SystemExit(7)'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    # The guarded region stays open across the child's whole life,
                    # as ``sandbox.ContainerExecutor.run`` does across its poll loop.
                    observed['inside'] = reap.reap_adopted_children()
                    observed['returncode'] = process.wait(timeout=30)
            except BaseException as exc:  # surfaced by the main thread below
                observed['error'] = exc

        declined_before = reap.reap_stats()['declined']
        thread = threading.Thread(target=owner, name='tracked-child-owner')
        thread.start()
        sweeps = 0
        while thread.is_alive():
            self.assertEqual(reap.reap_adopted_children(), 0, 'a sweep ran while a child was tracked')
            sweeps += 1
            time.sleep(0.02)
        thread.join(timeout=60)

        self.assertNotIn('error', observed, f'owner thread failed: {observed.get("error")!r}')
        self.assertIn('returncode', observed)
        self.assertEqual(observed['inside'], 0)
        self.assertEqual(observed['returncode'], 7, 'the tracked child lost its real exit status')
        self.assertGreater(reap.reap_stats()['declined'], declined_before, 'the guard never declined')
        self.assertGreater(sweeps, 0, 'the drain never actually raced the tracked child')
        self.assertEqual(reap.spawns_in_progress(), 0, 'a spawn guard leaked, which would disable reaping forever')

    def test_naive_unbounded_sweep_does_steal_the_status(self) -> None:
        """Measures the hazard the guard exists for, instead of asserting it away.

        ``waitpid(-1, WNOHANG)`` while a tracked child is unwaited harvests that
        child, and ``subprocess`` then reports a status it never observed: CPython's
        ``Popen._try_wait`` maps ``ECHILD`` to ``sts = 0``, i.e. a failed command as
        a passing one -- the #103/#132 misclassification family.  If this test starts
        failing because ``wait()`` raises instead, CPython changed and the
        SIGCHLD-versus-drain decision has to be re-read, not the assertion relaxed.
        """
        process = subprocess.Popen(
            [sys.executable, '-c', 'import time; time.sleep(0.2); raise SystemExit(7)'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.assertTrue(_wait_for_zombie(process.pid), 'the tracked child never exited')
        stolen_pid, _status = os.waitpid(-1, os.WNOHANG)
        self.assertEqual(stolen_pid, process.pid, 'the naive sweep did not reach a tracked child')
        self.assertNotEqual(process.wait(timeout=30), 7, 'a stolen status was still reported correctly')

    def test_sweep_declines_entirely_while_any_spawn_is_in_progress(self) -> None:
        from adaptive_trust_ci import reap

        reaped_before = reap.reap_stats()['reaped']
        with reap.spawn_in_progress():
            self.assertEqual(reap.spawns_in_progress(), 1)
            self.assertEqual(reap.reap_adopted_children(), 0)
        self.assertGreater(reap.reap_stats()['declined'], 0)
        self.assertEqual(reap.reap_stats()['reaped'], reaped_before)
        self.assertEqual(reap.spawns_in_progress(), 0)


class CancellationClassificationTests(unittest.TestCase):
    """Arm 3: reaping must not move the #103/#132 kill/abort classification."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_timeout_path_still_classifies_as_timeout_and_releases_its_guard(self) -> None:
        from adaptive_trust_ci import reap
        from adaptive_trust_ci import workspace as workspace_module

        started = reap.reap_stats()
        with self.assertRaisesRegex(workspace_module.WorkspaceError, 'exceeded its timeout'):
            workspace_module._run_bounded_process(
                [sys.executable, '-c', 'import os, time\nos.close(1); os.close(2); time.sleep(30)'],
                cwd=Path(self.temp.name),
                env=dict(os.environ),
                timeout=0.2,
                stdout_limit=128,
                stderr_limit=128,
                stdout_consumer=lambda _chunk: None,
            )
        self.assertEqual(reap.spawns_in_progress(), 0, 'the timeout path leaked its spawn guard')
        self.assertEqual(reap.reap_stats()['declined'], started['declined'])
        self.assertEqual(reap.reap_stats()['errors'], started['errors'])

    def test_heartbeat_failure_still_raises_after_reaping(self) -> None:
        from adaptive_trust_ci import lease as lease_module

        keeper = lease_module.LeaseKeeper(SimpleNamespace(), 'job-id', 'worker-id', 60)
        keeper._error = RuntimeError('database is down')
        with mock.patch.object(lease_module, 'reap_adopted_children') as reaped:
            with self.assertRaisesRegex(RuntimeError, 'job lease heartbeat failed: database is down'):
                keeper.check()
        reaped.assert_called_once_with()

    def test_sigchld_disposition_is_never_taken_over(self) -> None:
        from adaptive_trust_ci import reap  # importing the reaper must not install a handler

        self.assertIs(signal.getsignal(signal.SIGCHLD), signal.SIG_DFL)
        reap.reap_adopted_children()
        self.assertIs(signal.getsignal(signal.SIGCHLD), signal.SIG_DFL)


class SpawnGuardCoverageTests(unittest.TestCase):
    """Arm 4: the safety argument only holds while every spawn site is guarded."""

    def _spawn_functions(self) -> dict[str, bool]:
        found: dict[str, bool] = {}
        for path in sorted(SRC_ROOT.glob('*.py')):
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                spawns = [
                    call for call in ast.walk(node)
                    if isinstance(call, ast.Call) and _subprocess_factory_name(call.func)
                ]
                if not spawns:
                    continue
                decorated = any(
                    (isinstance(item, ast.Name) and item.id == 'guarded_spawn')
                    or (isinstance(item, ast.Attribute) and item.attr == 'guarded_spawn')
                    for item in node.decorator_list
                )
                with_guard = any(
                    isinstance(item, ast.Call)
                    and isinstance(item.func, ast.Name)
                    and item.func.id == 'spawn_in_progress'
                    for item in ast.walk(node)
                )
                found[f'{path.name}:{node.name}'] = decorated or with_guard
        return found

    def test_every_spawn_call_site_is_inside_a_guarded_region(self) -> None:
        unguarded = sorted(name for name, guarded in self._spawn_functions().items() if not guarded)
        self.assertEqual(unguarded, [], f'unguarded spawn sites: {unguarded}')

    def test_guarded_sites_are_exactly_the_worker_spawn_helpers(self) -> None:
        self.assertEqual(sorted(self._spawn_functions()), [
            'backup.py:_run',
            'sandbox.py:_remove_container',
            'sandbox.py:run',
            'workspace.py:_run_bounded_process',
        ])


def _subprocess_factory_name(func: ast.expr) -> str:
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if func.value.id == 'subprocess' and func.attr in {'Popen', 'run', 'call', 'check_call', 'check_output'}:
            return func.attr
    return ''


class GuardedSandboxSpawnTests(unittest.TestCase):
    """The other worker spawn site is ``ContainerExecutor.run``; it had no coverage at all.

    A decorator that is silently not applied would keep the tracked-child property
    unguarded for the docker/podman path, so this pins the wiring *and* the behaviour.
    """

    def _sandbox(self, runtime: str):
        from adaptive_trust_ci.policy import SandboxSpec

        return SandboxSpec(
            runtime=runtime, image='runner@sha256:' + 'a' * 64, user='1000:1000',
            memory_mb=512, cpus=1.0, pids_limit=128, tmpfs_mb=64,
        )

    def test_run_is_really_wrapped_by_the_spawn_guard(self) -> None:
        from adaptive_trust_ci.sandbox import ContainerExecutor

        self.assertTrue(hasattr(ContainerExecutor.run, '__wrapped__'), 'guarded_spawn is not applied')

    def test_missing_runtime_classification_is_unchanged(self) -> None:
        from adaptive_trust_ci import reap
        from adaptive_trust_ci.policy import CommandSpec
        from adaptive_trust_ci.sandbox import ContainerExecutor

        result = ContainerExecutor(self._sandbox('definitely-not-a-real-runtime')).run(
            CommandSpec(name='unit', argv=('pytest',), timeout_seconds=30),
            Path('.'), {'TRUST_CI_JOB_ID': 'job-1'}, 4096,
            workspace_host_path=Path('/var/lib/adaptive-trust-ci/workspaces/job-1'),
        )
        self.assertEqual(result.exit_code, 127)
        self.assertEqual(result.status, 'fail')
        self.assertIn('required sandbox runtime not found', result.stderr_tail)
        self.assertEqual(reap.spawns_in_progress(), 0)

    def test_real_spawn_through_the_decorated_helper_reaps_its_child_and_releases_the_guard(self) -> None:
        from adaptive_trust_ci import reap
        from adaptive_trust_ci.policy import CommandSpec
        from adaptive_trust_ci.sandbox import ContainerExecutor

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / 'workspace'
            (workspace / '.git').mkdir(parents=True)
            runtime = root / 'fake-runtime'
            # Stands in for the docker CLI: writes output, leaves a helper behind, exits nonzero.
            runtime.write_text('#!/bin/sh\nprintf spawned\nsleep 0.3 & exit 3\n', encoding='utf-8')
            runtime.chmod(0o755)
            result = ContainerExecutor(self._sandbox(str(runtime))).run(
                CommandSpec(name='unit', argv=('pytest',), timeout_seconds=30),
                workspace, {'TRUST_CI_JOB_ID': 'job-1'}, 4096,
                workspace_host_path=Path('/var/lib/adaptive-trust-ci/workspaces/job-1'),
            )

        self.assertEqual(result.exit_code, 3, 'the sandbox child lost its real exit code')
        self.assertEqual(result.status, 'fail')
        self.assertIn('spawned', result.stdout_tail)
        self.assertEqual(reap.spawns_in_progress(), 0, 'the guarded region leaked its counter')
        # ``run()`` still owns and reaps what it spawned: nothing of ours is left in the PID table.
        # (The helper the stub left behind is adopted by the namespace reaper, not by this test
        # process, so it is asserted in arm 1 and in the real-PID-1 pair, not here.)
        self.assertEqual(_zombie_children_of(os.getpid()), [])


if __name__ == '__main__':
    unittest.main()
