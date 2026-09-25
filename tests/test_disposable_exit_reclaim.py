from __future__ import annotations

import importlib.util
import os
import signal
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / 'factory' / 'tests' / 'run_disposable_exit.py'


def _load_harness():
    spec = importlib.util.spec_from_file_location('run_disposable_exit_probe', HARNESS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


harness = _load_harness()

# The reclaim predicate shares the probe's identity contract: 12-hex run suffix and
# 32-hex nonce. Fixtures must satisfy it, or they test the wrong branch.
EXIT_1 = 'adaptive-factory-exit-' + '0' * 11 + '1'
EXIT_2 = 'adaptive-factory-exit-' + '0' * 11 + '2'
EXIT_3 = 'adaptive-factory-exit-' + '0' * 11 + '3'
NONCE_1 = '1' * 32
NONCE_2 = '2' * 32
NONCE_4 = '4' * 32
OLD_ID = 'a' * 64
FRESH_ID = 'b' * 64
OWN_ID = 'c' * 64
FOREIGN_ID = 'd' * 64
NOW = 1_790_000_000.0


def _created(seconds_ago: float) -> str:
    """Render a timestamp the way Docker does: RFC3339 UTC with nine fractional digits."""
    from datetime import datetime, timezone

    base = datetime.fromtimestamp(NOW - seconds_ago, timezone.utc)
    return base.strftime('%Y-%m-%dT%H:%M:%S') + '.123456789Z'


class _Result:
    def __init__(self, stdout: str = '', returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = ''


class FakeDocker:
    """A docker stand-in that records every invocation the harness makes."""

    def __init__(self, runs: dict[str, dict[str, object]], *, removable: bool = True) -> None:
        self.runs = runs
        self.removable = removable
        self.commands: list[list[str]] = []
        self.removed: set[str] = set()

    def __call__(self, command: list[str], **_kwargs: object) -> _Result:
        self.commands.append(list(command))
        if command[:5] == ['docker', 'ps', '--all', '--quiet', '--no-trunc']:
            return _Result('\n'.join(self.runs))
        container_id = command[-1]
        record = self.runs.get(container_id)
        if command[1] == 'inspect' and command[2] == '--format':
            if record is None or record.get('unavailable'):
                return _Result(returncode=1)
            return _Result('\t'.join([
                container_id,
                f"/{record['name']}",
                str(record.get('image', harness.DISPOSABLE_IMAGE)),
                str(record.get('nonce', '')),
                str(record['created']),
                'true' if record.get('running', True) else 'false',
            ]))
        if command[1] == 'inspect':
            return _Result(returncode=0 if container_id not in self.removed else 1)
        if command[1] == 'rm':
            if not self.removable:
                return _Result(returncode=1)
            self.removed.add(container_id)
            return _Result(container_id)
        return _Result()

    @property
    def removals(self) -> list[str]:
        return [cmd[-1] for cmd in self.commands if cmd[1] == 'rm']


def _fake(runs: dict[str, dict[str, object]], *, removable: bool = True) -> FakeDocker:
    return FakeDocker(runs, removable=removable)


class ReclaimAtStartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runs = {
            OLD_ID: {'name': EXIT_1, 'nonce': NONCE_1, 'created': _created(3 * 60 * 60)},
            FRESH_ID: {'name': EXIT_2, 'nonce': NONCE_2, 'created': _created(60)},
            OWN_ID: {'name': EXIT_3, 'nonce': 'mine', 'created': _created(10)},
            FOREIGN_ID: {'name': 'unrelated-web-app', 'nonce': NONCE_4,
                         'created': _created(9 * 60 * 60)},
        }

    def _reclaim(self, **kwargs):
        fake = _fake(self.runs, **{'removable': kwargs.pop('removable', True)})
        records = harness.reclaim_orphan_runs(
            'mine', now=NOW, runner=fake, clock=lambda: NOW, **kwargs
        )
        return records, fake

    def test_the_listing_is_requested_untruncated_and_label_filtered(self) -> None:
        _records, fake = self._reclaim()

        listing = next(cmd for cmd in fake.commands if cmd[:2] == ['docker', 'ps'])
        self.assertIn('--no-trunc', listing)
        self.assertIn(f'label={harness.DISPOSABLE_LABEL}', listing)

    def test_a_stale_labeled_orphan_is_reclaimed_and_reported(self) -> None:
        records, fake = self._reclaim()

        reclaimed = [item for item in records if item.get('action') == 'reclaimed']
        self.assertEqual([item['container'] for item in reclaimed], [OLD_ID])
        self.assertEqual(reclaimed[0]['name'], EXIT_1)
        # Docker's fractional seconds make the truncated age at most one second below the
        # requested offset.
        self.assertIn(reclaimed[0]['age_seconds'], (3 * 60 * 60 - 1, 3 * 60 * 60))
        removal = next(cmd for cmd in fake.commands if cmd[1] == 'rm')
        self.assertEqual(removal[:4], ['docker', 'rm', '-f', '-v'])
        self.assertEqual(removal[-1], OLD_ID)

    def test_a_concurrent_sibling_inside_the_age_bound_is_never_touched(self) -> None:
        records, fake = self._reclaim()

        self.assertNotIn(FRESH_ID, {item.get('container') for item in records})
        self.assertNotIn(FRESH_ID, [cmd[-1] for cmd in fake.commands if cmd[1] == 'rm'])

    def test_this_runs_own_nonce_is_never_a_candidate(self) -> None:
        records, fake = self._reclaim()

        self.assertNotIn(OWN_ID, {item.get('container') for item in records})
        self.assertNotIn(OWN_ID, [cmd[-1] for cmd in fake.commands if cmd[1] == 'rm'])

    def test_a_labeled_run_with_a_foreign_shape_is_skipped_not_deleted(self) -> None:
        records, fake = self._reclaim()

        foreign = next(item for item in records if item['container'] == FOREIGN_ID)
        self.assertEqual(foreign['action'], 'skipped')
        self.assertEqual(foreign['reason'], 'foreign run shape')
        self.assertNotIn(FOREIGN_ID, [cmd[-1] for cmd in fake.commands if cmd[1] == 'rm'])

    def test_a_foreign_image_under_an_exit_prefix_shape_is_not_deleted(self) -> None:
        self.runs[FOREIGN_ID] = {
            'name': 'adaptive-factory-exit-' + '0' * 11 + '9',
            'nonce': 'other',
            'image': 'postgres:9.6',
            'created': _created(9 * 60 * 60),
        }
        records, fake = self._reclaim()

        foreign = next(item for item in records if item['container'] == FOREIGN_ID)
        self.assertEqual(foreign['action'], 'skipped')
        self.assertEqual(foreign['reason'], 'foreign run shape')
        self.assertNotIn(FOREIGN_ID, fake.removals)

    def test_removal_that_did_not_take_effect_is_reported_as_leaked(self) -> None:
        records, _fake = self._reclaim(removable=False)

        self.assertEqual(records[0]['action'], 'leaked')
        self.assertEqual(records[0]['removal_exit'], 1)
        self.assertNotEqual(records[0]['action'], 'reclaimed')

    def test_an_uninspectable_candidate_is_skipped_rather_than_deleted(self) -> None:
        self.runs['e' * 64] = {'name': 'ghost', 'created': _created(9 * 60 * 60), 'unavailable': True}
        records, fake = self._reclaim()

        ghost = [item for item in records if item['container'] == 'e' * 64]
        self.assertEqual(ghost[0]['action'], 'skipped')
        self.assertEqual(ghost[0]['reason'], 'cannot inspect')
        self.assertNotIn('e' * 64, [cmd[-1] for cmd in fake.commands if cmd[1] == 'rm'])

    def test_the_age_bound_is_a_single_documented_number(self) -> None:
        # The bound must exceed the harness's own 30 s readiness wait plus its 480 s suite
        # budget, or reclaim could cut off a live sibling.
        self.assertGreater(harness.ORPHAN_MIN_AGE_SECONDS, 480 + 30 + 60)
        records, fake = self._reclaim(min_age_seconds=30)

        self.assertIn(OLD_ID, {item['container'] for item in records})
        self.assertIn(FRESH_ID, {item['container'] for item in records if item.get('age_seconds', 0) >= 30})

    def test_the_reclaim_budget_bounds_one_invocation(self) -> None:
        records, fake = self._reclaim(limit=1)

        self.assertIn('skipped-limit', {item['action'] for item in records})
        self.assertEqual(1, len([cmd for cmd in fake.commands if cmd[1] == 'rm']))

    def test_every_reclaim_decision_is_reported_rather_than_silent(self) -> None:
        import io
        import contextlib

        records, _fake = self._reclaim()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            harness._report_reclaimed(records)
        printed = buffer.getvalue().splitlines()

        self.assertEqual(len(printed), len(records) + 1)
        for line in printed:
            self.assertTrue(line.startswith('RECLAIM '), line)
        self.assertIn('container=' + OLD_ID, ''.join(printed))
        # A leaked orphan must be countable at a glance, not inferred from the line spread.
        self.assertTrue(printed[-1].startswith('RECLAIM summary '), printed[-1])
        self.assertIn('reclaimed=1', printed[-1])

    def test_a_labeled_persistent_database_outside_the_run_name_shape_is_never_deleted(self) -> None:
        # The reviewer's constructed deletion: a hand-started long-lived database that
        # happens to carry the label and the exact image. A prefix test destroyed it;
        # the identity contract shared with the probe must spare it.
        runs = {OLD_ID: {'name': 'adaptive-factory-exit-cache-prod', 'nonce': NONCE_1,
                         'created': _created(400 * 24 * 60 * 60)}}
        fake = _fake(runs)

        records = harness.reclaim_orphan_runs('mine', now=NOW, runner=fake, clock=lambda: NOW)

        self.assertEqual(records[0]['action'], 'skipped')
        self.assertEqual(records[0]['reason'], 'foreign run shape')
        self.assertEqual(fake.removals, [])

    def test_an_age_beyond_the_trusted_window_is_not_trusted_enough_to_delete(self) -> None:
        # An absurd `Created` is evidence the clock or the field is wrong, and deleting a
        # LIVE sibling's PostgreSQL plus its anonymous PGDATA is the failure mode to avoid.
        runs = {OLD_ID: {'name': EXIT_1, 'nonce': NONCE_1,
                         'created': _created(400 * 24 * 60 * 60)}}
        fake = _fake(runs)

        records = harness.reclaim_orphan_runs('mine', now=NOW, runner=fake, clock=lambda: NOW)

        self.assertEqual(records[0]['reason'], 'age outside the trusted window')
        self.assertEqual(fake.removals, [])

    def test_the_time_budget_stops_reclaim_before_it_can_consume_the_gate(self) -> None:
        # The only caller answers its 600 s wall clock with SIGKILL, which no handler can
        # catch, so reclaim must stop itself.
        runs = {
            'f' * 64: {'name': EXIT_2, 'nonce': NONCE_2, 'created': _created(3 * 60 * 60)},
            'e' * 64: {'name': EXIT_3, 'nonce': NONCE_4, 'created': _created(3 * 60 * 60)},
        }
        fake = _fake(runs)
        ticks = iter([0.0, 10.0, 5_000.0, 5_000.1, 5_000.2, 5_000.3])

        records = harness.reclaim_orphan_runs(
            'mine', now=NOW, runner=fake, clock=lambda: next(ticks), time_budget_seconds=120,
        )

        self.assertIn('skipped-timeout', {item['action'] for item in records})
        self.assertLessEqual(len(fake.removals), 1)

    def test_the_module_level_docker_call_cannot_escape_a_patched_subprocess(self) -> None:
        # `runner=subprocess.run` bound at import let main()'s reclaim reach the real binary
        # while a test patched the module attribute, i.e. a unit test could delete a live
        # container. Defaults must resolve late, and the seam must be the only door.
        import inspect

        signature = inspect.signature(harness.reclaim_orphan_runs)
        self.assertIsNone(signature.parameters['runner'].default)
        self.assertIsNone(signature.parameters['clock'].default)

        class Tripwire:
            def run(self, command, **_kwargs):
                raise AssertionError(f'the real docker binary was reached: {command[:3]!r}')

        original = harness.subprocess
        try:
            harness.subprocess = Tripwire()
            with self.assertRaises(AssertionError) as raised:
                harness.reclaim_orphan_runs('mine')
            self.assertIn('real docker binary', str(raised.exception))
        finally:
            harness.subprocess = original


class CreationTimeParsingTests(unittest.TestCase):
    def test_nanosecond_utc_timestamps_are_truncated_not_rejected(self) -> None:
        age = harness._observed_age_seconds(_created(120), NOW)

        self.assertIsNotNone(age)
        self.assertAlmostEqual(age, 120, delta=1.0)

    def test_unparsable_or_empty_creation_time_is_unknown_not_zero(self) -> None:
        self.assertIsNone(harness._observed_age_seconds('', NOW))
        self.assertIsNone(harness._observed_age_seconds('not-a-time', NOW))

    def test_a_naive_timestamp_is_read_as_utc(self) -> None:
        age = harness._observed_age_seconds('2026-01-01T00:00:00.000000000', NOW + 10_000_000_000)

        self.assertIsNotNone(age)


class OwnedFromCreationTests(unittest.TestCase):
    def test_only_a_full_container_id_counts_as_minted(self) -> None:
        self.assertEqual(harness._minted_container_id(f'  {OLD_ID}\n'), OLD_ID)
        self.assertIsNone(harness._minted_container_id('a1b2c3d4e5f6'))
        self.assertIsNone(harness._minted_container_id(''))
        self.assertIsNone(harness._minted_container_id('Error: No such image'))

    def test_minted_removal_still_verifies_identity_before_it_destroys(self) -> None:
        # `minted=True` exists so a failed binding check cannot leak our own container.
        # It must not become a licence to delete whatever `docker run` happened to print:
        # a spoofed shim or a daemon returning a foreign id would otherwise destroy an
        # unrelated database plus its anonymous volume.
        calls: list[list[str]] = []

        def recorder(command, **_kwargs):
            calls.append(list(command))
            if command[1] == 'inspect' and command[2] == '--format':
                return _Result('	'.join([OLD_ID, '/' + EXIT_1, harness.DISPOSABLE_IMAGE,
                                          'true', 'keep']), 0)
            if command[1] == 'inspect':
                return _Result(returncode=1)
            return _Result(OLD_ID)

        with patch.object(harness.subprocess, 'run', side_effect=recorder):
            harness._remove_bound_container(OLD_ID, EXIT_1, 'keep', minted=True)

        self.assertIn(['docker', 'rm', '-f', '-v', OLD_ID], calls)

    def test_minted_removal_refuses_when_the_daemon_says_it_is_not_ours(self) -> None:
        calls: list[list[str]] = []

        def recorder(command, **_kwargs):
            calls.append(list(command))
            if command[1] == 'inspect' and command[2] == '--format':
                # Readable daemon, identity present, but the label/nonce is somebody else's.
                return _Result('	'.join(['b' * 64, '/adaptive-factory-exit-00000000000f',
                                          harness.DISPOSABLE_IMAGE, 'true',
                                          'someone-elses-nonce']), 0)
            return _Result(returncode=0)

        import io
        import contextlib

        buffer = io.StringIO()
        with patch.object(harness.subprocess, 'run', side_effect=recorder):
            with self.assertRaises(RuntimeError) as raised:
                with contextlib.redirect_stdout(buffer):
                    harness._remove_bound_container(OLD_ID, EXIT_1, 'keep', minted=True)

        self.assertIn('does not match the run', str(raised.exception))
        self.assertIn('RECLAIM refused', buffer.getvalue())
        self.assertNotIn('rm', [command[1] for command in calls])

    def test_a_container_that_survives_removal_is_reported_leaked_and_raises(self) -> None:
        # Trusting `rm`'s exit code alone was the reviewer's point: the only honest proof
        # is that the daemon can no longer see it.
        def recorder(command, **_kwargs):
            if command[1] == 'inspect' and command[2] == '--format':
                return _Result('	'.join([OLD_ID, '/' + EXIT_1, harness.DISPOSABLE_IMAGE,
                                          'true', 'keep']), 0)
            if command[1] == 'inspect':
                return _Result(returncode=0)
            return _Result(returncode=0)

        import io
        import contextlib

        buffer = io.StringIO()
        with patch.object(harness.subprocess, 'run', side_effect=recorder):
            with self.assertRaises(RuntimeError) as raised:
                with contextlib.redirect_stdout(buffer):
                    harness._remove_bound_container(OLD_ID, EXIT_1, 'keep', minted=True)

        self.assertIn('survived removal', str(raised.exception))
        self.assertIn('RECLAIM leaked', buffer.getvalue())

    def test_unbound_non_minted_container_is_still_refused(self) -> None:
        with patch.object(harness, '_binding_matches', return_value=False), patch.object(
            harness.subprocess, 'run'
        ) as run:
            with self.assertRaises(RuntimeError) as raised:
                harness._remove_bound_container(
                    OLD_ID, 'adaptive-factory-exit-abc', 'nonce'
                )
        run.assert_not_called()
        self.assertIn('unbound container', str(raised.exception))


class CancellationReachabilityTests(unittest.TestCase):
    """The bug was a finally that a cancelled run never reaches; this pins it being reached."""

    def setUp(self) -> None:
        self.previous_term = signal.getsignal(signal.SIGTERM)
        self.previous_int = signal.getsignal(signal.SIGINT)

    def tearDown(self) -> None:
        signal.signal(signal.SIGTERM, self.previous_term)
        signal.signal(signal.SIGINT, self.previous_int)

    def test_sigterm_becomes_an_exception_that_runs_the_finally(self) -> None:
        scope = harness._CancellationScope().install()
        cleaned: list[str] = []
        try:
            try:
                os.kill(os.getpid(), signal.SIGTERM)
                for _ in range(200):
                    if cleaned:
                        break
            finally:
                cleaned.append('container-removed')
        except harness.HarnessCancelled as cancelled:
            self.assertIn('signal', str(cancelled))
        else:
            self.fail('SIGTERM did not surface as an exception, so cleanup stays unreachable')
        self.assertEqual(cleaned, ['container-removed'])
        scope.restore()
        self.assertIs(signal.getsignal(signal.SIGTERM), self.previous_term)

    def test_handlers_are_restored_even_when_nothing_installs_them_twice(self) -> None:
        first = harness._CancellationScope().install()
        second = harness._CancellationScope().install()
        first.restore()
        second.restore()

        self.assertIs(signal.getsignal(signal.SIGTERM), self.previous_term)
        self.assertIs(signal.getsignal(signal.SIGINT), self.previous_int)

    def test_installation_off_the_main_thread_does_not_raise(self) -> None:
        outcome: list[str] = []

        def worker() -> None:
            try:
                scope = harness._CancellationScope().install()
                outcome.append('installed' if not scope.previous else 'claimed')
                scope.restore()
            except Exception as exc:  # pragma: no cover - the point is that this never fires
                outcome.append(f'raised:{exc!r}')

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=10)

        self.assertEqual(outcome, ['installed'])
        self.assertIs(signal.getsignal(signal.SIGTERM), self.previous_term)

    def test_the_harness_declares_its_dependency_on_the_caller_raising(self) -> None:
        source = HARNESS.read_text(encoding='utf-8')

        self.assertIn('#119', source)
        self.assertIn('verify()', source)


if __name__ == '__main__':
    unittest.main()


class ReclaimWiringTests(unittest.TestCase):
    """The wiring, not just the function: both load-bearing properties were unpinned."""

    @staticmethod
    def _completed(stdout='', returncode=0):
        return type('Completed', (), {'returncode': returncode, 'stdout': stdout})()

    def _main_docker_calls(self, root: Path, on_call=None):
        calls: list[list[str]] = []
        container_id = 'c' * 64

        def fake_run(command, **_kwargs):
            calls.append(list(command))
            if on_call is not None:
                outcome = on_call(list(command))
                if outcome is not None:
                    return outcome
            if command[1] == 'run':
                return self._completed(container_id + '\n')
            if command[1] == 'port':
                return self._completed('127.0.0.1:4321\n')
            if command[1] == 'inspect':
                return self._completed(returncode=1)
            return self._completed()

        return calls, fake_run, container_id

    def test_main_reclaims_and_installs_handlers_before_it_creates_anything(self) -> None:
        # Deleting either wiring line used to leave every test green: the reclaim call in
        # main() and the handler install are the feature, not the helper functions.
        import factory.tests.run_disposable_exit as production

        order: list[str] = []
        calls, fake_run, _cid = self._main_docker_calls(Path('.'))

        def spy_reclaim(nonce, **kwargs):
            order.append('reclaim')
            return []

        real_install = production._CancellationScope.install

        def spy_install(self):
            order.append('install')
            return real_install(self)

        def watch(command):
            if command[1] == 'run':
                order.append('docker-run')
            return None

        calls, fake_run, cid = self._main_docker_calls(Path('.'), on_call=watch)
        with _chdir(ROOT), patch.object(production.subprocess, 'run', side_effect=fake_run), \
             patch.object(production, 'reclaim_orphan_runs', side_effect=spy_reclaim), \
             patch.object(production._CancellationScope, 'install', spy_install), \
             patch.object(production, '_binding_matches', return_value=True), \
             patch.object(production, '_final_postgres_ready', return_value=True), \
             patch.object(production, '_run'), \
             patch.object(production, '_remove_bound_container'), \
             patch('builtins.print'):
            try:
                production.main()
            except Exception:  # the fake never runs a real suite; ordering is what matters
                pass

        self.assertEqual(order[:3], ['install', 'reclaim', 'docker-run'], order)

    def test_cancellation_exits_non_zero_and_still_reclaims_its_container(self) -> None:
        # The #119 defect is a cancelled run that records a pass. A `return 0` here must
        # not be able to hide behind a green suite.
        import factory.tests.run_disposable_exit as production

        def fire(command):
            if command[1] == 'port':
                os.kill(os.getpid(), signal.SIGTERM)
            return None

        calls, fake_run, cid = self._main_docker_calls(Path('.'), on_call=fire)
        removed: list[str] = []
        with _chdir(ROOT), patch.object(production.subprocess, 'run', side_effect=fake_run), \
             patch.object(production, 'reclaim_orphan_runs', return_value=[]), \
             patch.object(production, '_binding_matches', return_value=True), \
             patch.object(production, '_remove_bound_container', side_effect=lambda c, n, nonce, **k: removed.append(c)), \
             patch('builtins.print'):
            with self.assertRaises(SystemExit) as raised:
                production.main()

        self.assertEqual(raised.exception.code, 130, 'a cancelled gate run must not exit 0')
        self.assertEqual(removed, [cid])

    def test_a_run_younger_than_the_bound_with_my_nonce_is_never_a_candidate(self) -> None:
        # With the age floor removed for the probe, only the nonce exclusion can save this
        # process's own container. Before this arm, deleting that exclusion passed.
        runs = {OLD_ID: {'name': EXIT_1, 'nonce': 'mine', 'created': _created(5)}}
        fake = _fake(runs)

        records = harness.reclaim_orphan_runs(
            'mine', now=NOW, min_age_seconds=0, runner=fake, clock=lambda: NOW
        )

        self.assertEqual(records, [])
        self.assertEqual(fake.removals, [])

    def test_the_orphan_bound_exceeds_the_real_durations_not_a_restated_literal(self) -> None:
        total = (
            harness.READY_DEADLINE_SECONDS
            + harness.SUITE_TIMEOUT_SECONDS
            + 2 * harness.RESTART_PROBE_TIMEOUT_SECONDS
        )

        self.assertGreater(harness.ORPHAN_MIN_AGE_SECONDS, total)
        self.assertGreater(harness.ORPHAN_MAX_AGE_SECONDS, harness.ORPHAN_MIN_AGE_SECONDS)
        self.assertLess(harness.RECLAIM_TIME_BUDGET_SECONDS, 600)


class _chdir:
    """Context-managed cwd that always restores, so a failure cannot leak the directory."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.previous = ''

    def __enter__(self):
        import os

        self.previous = os.getcwd()
        os.chdir(self.path)
        return self

    def __exit__(self, *_):
        import os

        os.chdir(self.previous)
