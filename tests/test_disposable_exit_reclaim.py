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
            OLD_ID: {'name': 'adaptive-factory-exit-old', 'nonce': 'oldnonce',
                     'created': _created(3 * 60 * 60)},
            FRESH_ID: {'name': 'adaptive-factory-exit-sibling', 'nonce': 'siblingnonce',
                       'created': _created(60)},
            OWN_ID: {'name': 'adaptive-factory-exit-own', 'nonce': 'mine',
                     'created': _created(10)},
            FOREIGN_ID: {'name': 'unrelated-web-app', 'nonce': 'someoneelse',
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
        self.assertEqual(reclaimed[0]['name'], 'adaptive-factory-exit-old')
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
            'name': 'adaptive-factory-exit-lookalike',
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

        self.assertEqual(len(printed), len(records))
        for line in printed:
            self.assertTrue(line.startswith('RECLAIM '), line)
        self.assertIn('container=' + OLD_ID, ''.join(printed))


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

    def test_minted_removal_skips_the_binding_check_but_not_the_id_shape_check(self) -> None:
        calls: list[list[str]] = []

        def recorder(command, **_kwargs):
            calls.append(list(command))
            return _Result()

        with patch.object(harness.subprocess, 'run', side_effect=recorder):
            harness._remove_bound_container(
                OLD_ID, 'adaptive-factory-exit-abc', 'nonce', minted=True
            )

        self.assertEqual(calls, [['docker', 'rm', '-f', '-v', OLD_ID]])

        with patch.object(harness.subprocess, 'run', side_effect=recorder) as run:
            with self.assertRaises(RuntimeError) as raised:
                harness._remove_bound_container(
                    'factory-test-container', 'name', 'nonce', minted=True
                )
        run.assert_not_called()
        self.assertIn('did not mint', str(raised.exception))

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
