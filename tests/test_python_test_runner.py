from __future__ import annotations

import contextlib
import io
from importlib import metadata
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.grok-stack'))

from adaptive_grok.verification import CheckResult, _python
from adaptive_grok import python_test_runner
from adaptive_grok.python_test_runner import RunnerError, execute, parallel_engine_ready, selected_workers


@contextlib.contextmanager
def fixture(*, workers: object = 2):
    with tempfile.TemporaryDirectory(prefix='grok-runner-test-') as directory:
        root = Path(directory)
        (root / 'tests').mkdir()
        (root / 'tests/__init__.py').write_text('')
        (root / '.grok-test-runner.json').write_text(
            json.dumps({'schema_version': 1, 'workers': workers})
        )
        (root / 'tests/test_sample.py').write_text(
            'import os\nfrom pathlib import Path\nimport unittest\n'
            'class Sample(unittest.TestCase):\n'
            + ''.join(
                f'    def test_{i}(self):\n'
                f'        with Path("result-{i}").open("x") as output:\n'
                f'            output.write(str(os.getpid()))\n'
                for i in range(4)
            )
        )
        environment = os.environ.copy()
        for key in ('GROK_TEST_WORKERS', '_GROK_TEST_CHILD'):
            environment.pop(key, None)
        with patch.dict(os.environ, environment, clear=True), patch(
            'adaptive_grok.verification._ruff',
            return_value=CheckResult('ruff', 'skip', 'fixture'),
        ), patch(
            'adaptive_grok.verification._bandit',
            return_value=CheckResult('bandit', 'skip', 'fixture'),
        ):
            yield root


@contextlib.contextmanager
def capacity_files(root: Path, files: dict[str, object], *, cpus: int = 22):
    """Supply complete proc/cgroup inputs without consulting this test host."""
    reads: list[str] = []
    real_open = Path.open

    def open_input(path, *args, **kwargs):
        if path == root / python_test_runner.CONFIG:
            return real_open(path, *args, **kwargs)
        name = str(path)
        reads.append(name)
        value = files.get(name, FileNotFoundError(name))
        if isinstance(value, BaseException):
            raise value
        mode = args[0] if args else kwargs.get('mode', 'r')
        return io.BytesIO(value.encode('utf-8')) if 'b' in mode else io.StringIO(value)

    with patch.object(Path, 'open', open_input), \
         patch.object(sys, 'platform', 'linux'), \
         patch.object(os, 'sched_getaffinity', return_value=set(range(cpus)), create=True):
        yield reads


def v2_capacity(*, membership: str = '/team/job', mount_root: str = '/',
                mountpoint: str = '/sys/fs/cgroup') -> dict[str, object]:
    return {
        '/proc/self/cgroup': f'0::{membership}\n',
        '/proc/self/mountinfo': (
            f'32 24 0:28 {mount_root} {mountpoint} rw,nosuid shared:7 - cgroup2 cgroup rw\n'
        ),
    }


class PythonTestCapacityTests(unittest.TestCase):
    def test_auto_applies_nested_v2_quota_and_tighter_visible_ancestors(self) -> None:
        for leaf, parent, expected in (
            ('200000 100000', 'max 100000', 2),
            ('800000 100000', '200000 100000', 2),
            ('max 100000', '300000 100000', 3),
            ('max 100000', 'max 100000', 22),
            ('50000 100000', 'max 100000', 1),
            ('150000 100000', 'max 100000', 1),
            ('250000 100000', 'max 100000', 2),
        ):
            files = v2_capacity()
            files.update({'/sys/fs/cgroup/team/job/cpu.max': leaf,
                          '/sys/fs/cgroup/team/cpu.max': parent})
            with self.subTest(leaf=leaf, parent=parent), fixture(workers='auto') as root, \
                 capacity_files(root, files) as reads:
                self.assertEqual(selected_workers(root), expected)
                self.assertEqual(set(reads), set(files) | {'/sys/fs/cgroup/cpu.max'})

    def test_auto_intersects_affinity_quota_and_existing_ceiling(self) -> None:
        for cpus, quota, expected in ((2, '800000 100000', 2), (96, 'max 100000', 28),
                                     (96, '250000 100000', 2)):
            files = v2_capacity(membership='/')
            files['/sys/fs/cgroup/cpu.max'] = quota
            with self.subTest(cpus=cpus, quota=quota), fixture(workers='auto') as root, \
                 capacity_files(root, files, cpus=cpus):
                self.assertEqual(selected_workers(root), expected)

    def test_auto_handles_absent_v2_controls_without_skipping_parent(self) -> None:
        for membership, extra, expected in (
            ('/team/job', {'/sys/fs/cgroup/team/cpu.max': '200000 100000'}, 2),
            ('/', {}, 22),
            ('/team/job', {}, 22),
        ):
            files = v2_capacity(membership=membership)
            files.update(extra)
            with self.subTest(membership=membership, extra=extra), fixture(workers='auto') as root, \
                 capacity_files(root, files):
                self.assertEqual(selected_workers(root), expected)

    def test_auto_maps_mount_roots_escapes_and_component_boundaries(self) -> None:
        for membership, mount_root, mountpoint, leaf, expected in (
            ('/slice/job', '/slice', '/cgroup', '/cgroup/job/cpu.max', 2),
            ('/slice/job', '/slice', '/cpu\\040space', '/cpu space/job/cpu.max', 2),
            ('/slice/job', '/slice', '/cpu\\134name', '/cpu\\name/job/cpu.max', 2),
            ('/teammate/job', '/team', '/cgroup', None, 1),
            ('/', '/host/slice', '/cgroup', None, 1),
            ('/../job', '/', '/cgroup', None, 1),
            ('/', '/..', '/cgroup', None, 1),
            ('/team/./job', '/', '/cgroup', None, 1),
        ):
            files = v2_capacity(membership=membership, mount_root=mount_root, mountpoint=mountpoint)
            if leaf:
                files[leaf] = '200000 100000'
            with self.subTest(membership=membership, mountpoint=mountpoint), \
                 fixture(workers='auto') as root, capacity_files(root, files) as reads:
                self.assertEqual(selected_workers(root), expected)
                if leaf:
                    self.assertEqual(set(reads), set(files) | {str(Path(leaf).parent.parent / 'cpu.max')})
                else:
                    self.assertEqual(set(reads), {'/proc/self/cgroup', '/proc/self/mountinfo'})

    def test_auto_checks_wider_mount_even_when_bind_subtree_appears_first(self) -> None:
        files = v2_capacity(membership='/team/job')
        files['/proc/self/mountinfo'] = (
            '40 24 0:28 /team/job /bind rw - cgroup2 cgroup rw\n'
            + files['/proc/self/mountinfo']
            + '41 24 0:28 /sibling /irrelevant rw - cgroup2 cgroup rw\n'
        )
        files.update({'/bind/cpu.max': 'max 100000',
                      '/sys/fs/cgroup/team/job/cpu.max': 'max 100000',
                      '/sys/fs/cgroup/team/cpu.max': '200000 100000',
                      '/irrelevant/cpu.max': '100000 100000'})
        with fixture(workers='auto') as root, capacity_files(root, files) as reads:
            self.assertEqual(selected_workers(root), 2)
            self.assertNotIn('/irrelevant/cpu.max', reads)
            self.assertNotIn('/cpu.max', reads)

    def test_auto_resolves_v1_cpu_controller_in_combined_and_hybrid_layouts(self) -> None:
        for hybrid in (False, True):
            files = {
                '/proc/self/cgroup': '7:cpu,cpuacct:/slice/job\n9:cpuset:/other\n',
                '/proc/self/mountinfo': (
                    '31 24 0:27 /slice /cpu-mount rw - cgroup cgroup rw,cpuacct,cpu\n'
                    '33 24 0:29 / /not-cpu rw - cgroup cgroup rw,cpuset\n'
                ),
                '/cpu-mount/job/cpu.cfs_quota_us': '-1\n',
                '/cpu-mount/job/cpu.cfs_period_us': '100000\n',
                '/cpu-mount/cpu.cfs_quota_us': '250000\n',
                '/cpu-mount/cpu.cfs_period_us': '100000\n',
            }
            if hybrid:
                files['/proc/self/cgroup'] += '0::/unified\n'
                files['/proc/self/mountinfo'] += '32 24 0:28 / /v2 rw - cgroup2 cgroup rw\n'
                files['/v2/unified/cpu.max'] = '100000 100000'
            with self.subTest(hybrid=hybrid), fixture(workers='auto') as root, \
                 capacity_files(root, files) as reads:
                self.assertEqual(selected_workers(root), 2)
                self.assertEqual(set(reads), {name for name in files if not name.startswith('/v2')})

    def test_auto_distinguishes_v1_unlimited_missing_and_invalid_pairs(self) -> None:
        for quota, period, expected in (
            ('-1', '100000', 22), ('250000', '100000', 2), ('50000', '100000', 1),
            ('-2', '100000', 1), ('0', '100000', 1), ('2', '0', 1),
            ('100000', None, 1), (None, '100000', 1), ('1 2', '100000', 1),
        ):
            files = {'/proc/self/cgroup': '7:cpu:/\n',
                     '/proc/self/mountinfo': '31 24 0:27 / /cpu rw - cgroup cgroup rw,cpu\n'}
            if quota is not None:
                files['/cpu/cpu.cfs_quota_us'] = quota
            if period is not None:
                files['/cpu/cpu.cfs_period_us'] = period
            with self.subTest(quota=quota, period=period), fixture(workers='auto') as root, \
                 capacity_files(root, files):
                self.assertEqual(selected_workers(root), expected)

    def test_auto_uses_one_worker_for_unknown_or_malformed_relevant_evidence(self) -> None:
        for value in ('', 'max', 'max 0', '0 100000', '-1 100000', '2 nope', '2 1 extra',
                      '１２ １００', '2.5 1', PermissionError('unreadable'), '9' * 8192):
            files = v2_capacity()
            files.update({'/sys/fs/cgroup/team/job/cpu.max': '800000 100000',
                          '/sys/fs/cgroup/team/cpu.max': value})
            with self.subTest(value=str(value)[:40]), fixture(workers='auto') as root, \
                 capacity_files(root, files):
                self.assertEqual(selected_workers(root), 1)
        for path, value in (
            ('/proc/self/cgroup', FileNotFoundError('missing')),
            ('/proc/self/mountinfo', PermissionError('unreadable')),
            ('/proc/self/cgroup', '0::/team/job\n0::/different\n'),
            ('/proc/self/cgroup', '0:cpu:/team/job\n'),
            ('/proc/self/cgroup', 'broken\n'),
            ('/proc/self/mountinfo', '32 24 0:28 / /cpu rw - cgroup2\n'),
            ('/proc/self/mountinfo', '32 24 invalid / /cpu rw - cgroup2 cgroup rw\n'),
            ('/proc/self/mountinfo', '32 24 0:28 / /cpu\\999 rw - cgroup2 cgroup rw\n'),
            ('/proc/self/mountinfo',
             '32 24 0:28 / /cpu rw - cgroup2 cgroup rw\n'
             '33 24 0:29 / /other rw - cgroup2 cgroup rw\n'),
            ('/proc/self/mountinfo', 'x' * (1024 * 1024 + 1)),
        ):
            files = v2_capacity()
            files[path] = value
            with self.subTest(path=path, value=str(value)[:40]), fixture(workers='auto') as root, \
                 capacity_files(root, files):
                self.assertEqual(selected_workers(root), 1)

    def test_auto_bounds_hierarchy_depth_and_mount_count(self) -> None:
        for kind in ('deep', 'mounts'):
            files = v2_capacity(membership='/' + '/'.join(['x'] * 2048) if kind == 'deep' else '/')
            if kind == 'mounts':
                files['/proc/self/mountinfo'] = ''.join(
                    f'{i + 32} 24 0:28 / /cpu-{i} rw - cgroup2 cgroup rw\n' for i in range(2048)
                )
            with self.subTest(kind=kind), fixture(workers='auto') as root, \
                 capacity_files(root, files) as reads:
                self.assertEqual(selected_workers(root), 1)
                self.assertLessEqual(len(reads), 1024)
        files = v2_capacity(membership='/' + '/'.join(['x'] * 64))
        files['/proc/self/mountinfo'] = ''.join(
            f'{i + 32} 24 0:28 / /cpu-{i} rw - cgroup2 cgroup rw\n' for i in range(17)
        )
        with fixture(workers='auto') as root, capacity_files(root, files) as reads:
            self.assertEqual(selected_workers(root), 1)
            self.assertLessEqual(len(reads), 1026)

    def test_explicit_default_child_and_other_platform_paths_avoid_capacity_reads(self) -> None:
        for configured, override, child, expected in (
            (0, None, False, 0), (64, None, False, 64), (2, '64', False, 64),
            ('auto', '0', False, 0), ('auto', None, True, 0),
        ):
            with self.subTest(configured=configured, override=override, child=child), \
                 fixture(workers=configured) as root, capacity_files(root, {}) as reads:
                env = {'_GROK_TEST_CHILD': '1'} if child else {}
                if override is not None:
                    env['GROK_TEST_WORKERS'] = override
                with patch.dict(os.environ, env):
                    self.assertEqual(selected_workers(root), expected)
                self.assertEqual(reads, [])
        with fixture() as root:
            (root / python_test_runner.CONFIG).unlink()
            with capacity_files(root, {}) as reads:
                self.assertIsNone(selected_workers(root))
                self.assertEqual(reads, [])
        with fixture(workers='auto') as root, capacity_files(root, {}) as reads, \
             patch.object(sys, 'platform', 'darwin'):
            self.assertEqual(selected_workers(root), 22)
            self.assertEqual(reads, [])
        with fixture(workers='auto') as root, capacity_files(root, {}) as reads, \
             patch.object(os, 'name', 'nt'):
            self.assertEqual(selected_workers(root), 0)
            self.assertEqual(reads, [])

    def test_environment_auto_uses_quota_and_affinity_errors_use_cpu_count(self) -> None:
        files = v2_capacity(membership='/')
        files['/sys/fs/cgroup/cpu.max'] = '200000 100000'
        with fixture(workers=64) as root, capacity_files(root, files), \
             patch.dict(os.environ, {'GROK_TEST_WORKERS': 'auto'}):
            self.assertEqual(selected_workers(root), 2)
        for cpus, expected in ((4, 4), (None, 1)):
            with self.subTest(cpus=cpus), fixture(workers='auto') as root, \
                 capacity_files(root, v2_capacity(membership='/')), \
                 patch.object(os, 'sched_getaffinity', side_effect=OSError('unavailable')), \
                 patch.object(os, 'cpu_count', return_value=cpus):
                self.assertEqual(selected_workers(root), expected)


class PythonTestRunnerTests(unittest.TestCase):
    def assert_descendant_stopped(self, pid_file: Path) -> None:
        if sys.platform != 'linux':
            self.skipTest('process-group verification reads /proc; Linux-only')
        status = Path('/proc') / pid_file.read_text() / 'status'
        for _ in range(100):
            try:
                if 'Z (zombie)' in status.read_text():
                    return
            except FileNotFoundError:
                return
            time.sleep(0.01)
        self.fail('owned descendant continued after process cleanup')

    def test_trust_cli_uses_own_imports_and_keeps_each_file_on_one_worker(self) -> None:
        for workers in (2, 0):
            with self.subTest(workers=workers), fixture(workers=workers) as root:
                trust = root / 'trust-ci'
                (trust / 'src').mkdir(parents=True)
                (trust / 'src/subject.py').write_text('value = 42\n')
                (trust / 'tests').mkdir()
                (trust / 'tests/__init__.py').write_text('')
                (trust / 'tests/_support.py').write_text('from subject import value\n')
                (trust / 'pytest.ini').write_text('[pytest]\naddopts = -k test_0\n')
                for name in ('alpha', 'beta'):
                    (trust / f'tests/test_{name}.py').write_text(
                        'import os, unittest\nfrom pathlib import Path\nfrom _support import value\n'
                        'class T(unittest.TestCase):\n'
                        + ''.join(
                            f' def test_{i}(self):\n'
                            f'  self.assertEqual(value, 42)\n'
                            f'  with Path("{name}-{i}.pid").open("x") as output:\n'
                            f'   output.write(str(os.getpid()))\n'
                            for i in range(3)
                        )
                    )
                command = [sys.executable, '-m', 'adaptive_grok.python_test_runner', '--suite', 'trust-ci']
                environment = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / '.grok-stack')}
                result = execute(command, root, environment)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual({p.name for p in trust.glob('*.pid')},
                                 {f'{name}-{i}.pid' for name in ('alpha', 'beta') for i in range(3)})
                for name in ('alpha', 'beta'):
                    self.assertEqual(len({p.read_text() for p in trust.glob(f'{name}-*.pid')}), 1)
                effective, engine = python_test_runner.select_engine(workers, measured=False)
                self.assertIn(f'requested_workers={workers}; workers={effective}; engine={engine}', result.stdout)
                self.assertFalse(list(root.glob('result-*')), 'Core tests must not be collected by Trust CI')
                (trust / 'tests/test_alpha.py').write_text('raise RuntimeError("expected collection failure")\n')
                failed = execute(command, root, environment)
                self.assertNotEqual(failed.returncode, 0)

    def test_unittest_filename_pattern_is_preserved(self) -> None:
        with fixture() as root:
            (root / 'tests/test_sample.py').rename(root / 'tests/testsample.py')
            result = next(check for check in _python(root) if check.name == 'python-unittest')
            self.assertEqual(result.status, 'pass', result.stdout + result.stderr)
            self.assertEqual(len(list(root.glob('result-*'))), 4)

    def test_absent_opt_in_and_private_child_flag_preserve_consumer(self) -> None:
        with fixture() as root:
            (root / '.grok-test-runner.json').unlink()
            with patch.dict(os.environ, {'_GROK_TEST_CHILD': '1'}):
                self.assertIsNone(selected_workers(root))
                result = next(check for check in _python(root) if check.name == 'python-unittest')
            self.assertEqual(result.status, 'pass', result.stderr)
            self.assertEqual(len({p.read_text() for p in root.glob('result-*')}), 1)

    def test_serial_rollback_and_child_cap_do_not_start_a_pool(self) -> None:
        with fixture() as root:
            with patch.dict(os.environ, {'GROK_TEST_WORKERS': '0'}):
                result = next(check for check in _python(root) if check.name == 'python-unittest')
            self.assertEqual(result.status, 'pass', result.stderr)
            self.assertEqual(len({p.read_text() for p in root.glob('result-*')}), 1)
            with patch.dict(os.environ, {'_GROK_TEST_CHILD': '1', 'GROK_TEST_WORKERS': '22'}):
                self.assertEqual(selected_workers(root), 0)

    def test_auto_uses_available_logical_cpus_with_a_bound(self) -> None:
        with fixture(workers='auto') as root:
            with capacity_files(root, v2_capacity(membership='/'), cpus=22):
                self.assertEqual(selected_workers(root), 22)
            with capacity_files(root, v2_capacity(membership='/'), cpus=96):
                self.assertEqual(selected_workers(root), 28)

    def test_unimportable_parallel_engine_degrades_to_one_serial_pass(self) -> None:
        # Retake of defect 33: an interpreter that cannot import the xdist engine
        # (the Trust CI image case) must run one disclosed sequential pass, not fail.
        with fixture() as root:
            with patch('importlib.util.find_spec', return_value=None):
                result = next(check for check in _python(root) if check.name == 'python-unittest')
            self.assertEqual(result.status, 'pass', result.stderr + result.stdout)
            self.assertEqual(len(list(root.glob('result-*'))), 4)
            self.assertEqual(len({p.read_text() for p in root.glob('result-*')}), 1)
            self.assertIn('unittest-degraded', result.details[0]['versions'])

    # Retained PR135 regressions originate at 7a7851af5d11e8ce5c3af23ab46214ae7ae4cdc8.
    def test_non_posix_cleanup_capability_degrades_core_and_trust_before_launch(self) -> None:
        # Emulate Windows through the runner capability seam, without changing
        # os.name globally (which would alter pathlib and subprocess behavior).
        with fixture() as root, \
             patch.object(python_test_runner, '_parallel_process_cleanup_supported',
                          return_value=False, create=True), \
             patch.object(python_test_runner, 'parallel_engine_ready', return_value=True), \
             patch.object(python_test_runner.metadata, 'version',
                          side_effect=lambda name: python_test_runner.PINS[name]):
            self.assertEqual(python_test_runner.select_engine(2, measured=False),
                             (0, 'unittest-degraded'))
            core = python_test_runner.run_core_tests(root, 'fast', 2)
            self.assertEqual(core.tests.returncode, 0, core.tests.stdout + core.tests.stderr)
            self.assertEqual(core.workers, 0)
            self.assertEqual(core.versions['engine'], 'unittest-degraded')
            self.assertEqual(core.tests.command[1:4], ['-m', 'unittest', 'discover'])
            self.assertEqual({p.name for p in root.glob('result-*')}, {f'result-{i}' for i in range(4)})
            self.assertEqual(len({p.read_text() for p in root.glob('result-*')}), 1)

            trust = root / 'trust-ci'
            (trust / 'tests').mkdir(parents=True)
            (trust / 'tests/test_trust.py').write_text(
                'import unittest\nclass Trust(unittest.TestCase):\n'
                ' def test_pass(self): self.assertTrue(True)\n'
            )
            result = python_test_runner.run_trust_tests(root, 2)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.command[1:4], ['-m', 'unittest', 'discover'])
            self.assertEqual(python_test_runner.select_engine(0, measured=False), (0, 'unittest'))

            output = io.StringIO()
            with patch.object(Path, 'cwd', return_value=root), \
                 patch.object(sys, 'argv', ['python_test_runner', '--suite', 'trust-ci']), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(python_test_runner.main(), 0)
            self.assertIn('workers=0; engine=unittest-degraded', output.getvalue())

    def test_posix_cleanup_capability_keeps_xdist_and_strict_pins(self) -> None:
        with patch.object(python_test_runner, '_parallel_process_cleanup_supported',
                          return_value=True, create=True), \
             patch.object(python_test_runner, 'parallel_engine_ready', return_value=True):
            self.assertEqual(python_test_runner.select_engine(2, measured=True), (2, 'pytest-xdist'))
        for distribution in ('worksteal', 'loadfile'):
            with self.subTest(distribution=distribution):
                command = python_test_runner._pytest_command(2, distribution)
                self.assertEqual(command[command.index('-n') + 1], '2')
                self.assertIn(f'--dist={distribution}', command)

    def test_non_posix_measured_core_degrades_with_coverage_without_xdist_pins(self) -> None:
        with fixture() as root:
            (root / 'subject.py').write_text('value = 42\n')
            sample = root / 'tests/test_sample.py'
            sample.write_text('import subject\n' + sample.read_text())
            (root / '.coveragerc').write_text(
                '[run]\nbranch = True\nsource = subject\n[report]\nfail_under = 74\n'
            )
            real_version = metadata.version

            def coverage_only_version(name):
                if name != 'coverage':
                    raise AssertionError(f'unexpected dependency pin check: {name}')
                return real_version(name)

            with patch.object(python_test_runner, '_parallel_process_cleanup_supported',
                              return_value=False, create=True), \
                 patch.object(python_test_runner, 'parallel_engine_ready', return_value=True), \
                 patch.object(python_test_runner.metadata, 'version', side_effect=coverage_only_version):
                core = python_test_runner.run_core_tests(root, 'pr', 2)
            self.assertEqual(core.tests.returncode, 0, core.tests.stdout + core.tests.stderr)
            self.assertEqual(core.tests.command[1:4], ['-m', 'coverage', 'run'])
            self.assertEqual(core.workers, 0)
            self.assertEqual(core.versions, {'coverage': real_version('coverage'),
                                             'engine': 'unittest-degraded'})
            self.assertIsNotNone(core.coverage)
            self.assertEqual(core.coverage.returncode, 0, core.coverage.stdout + core.coverage.stderr)
            self.assertTrue(core.coverage_metadata['files'])

    def test_empty_serial_core_and_trust_collection_cannot_pass(self) -> None:
        for workers in (0, 2):
            for suite in ('core', 'trust'):
                with self.subTest(workers=workers, suite=suite), fixture() as root, \
                     patch.object(python_test_runner, 'parallel_engine_ready', return_value=False):
                    tests = root / 'tests' if suite == 'core' else root / 'trust-ci/tests'
                    tests.mkdir(parents=True, exist_ok=True)
                    (tests / 'test_sample.py').write_text('# deliberately empty collection\n')
                    result = (python_test_runner.run_core_tests(root, 'fast', workers).tests
                              if suite == 'core' else python_test_runner.run_trust_tests(root, workers))
                    self.assertIn('Ran 0 tests', result.stderr)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_empty_measured_serial_collection_cannot_qualify_import_coverage(self) -> None:
        for workers in (0, 2):
            with self.subTest(workers=workers), fixture() as root, \
                 patch.object(python_test_runner, 'parallel_engine_ready', return_value=False):
                (root / 'subject.py').write_text('value = 42\n')
                (root / 'tests/test_sample.py').write_text('import subject\n')
                (root / '.coveragerc').write_text(
                    '[run]\nbranch = True\nsource = subject\n[report]\nfail_under = 74\n'
                )
                core = python_test_runner.run_core_tests(root, 'pr', workers)
                self.assertIn('Ran 0 tests', core.tests.stderr)
                self.assertNotEqual(core.tests.returncode, 0, core.tests.stdout + core.tests.stderr)
                self.assertIsNotNone(core.coverage)
                self.assertNotEqual(core.coverage.returncode, 0, core.coverage.stdout + core.coverage.stderr)

    def test_degraded_serial_failures_propagate_without_retry(self) -> None:
        for source in (
            'import unittest\nclass T(unittest.TestCase):\n def test_bad(self): self.fail("expected")\n',
            'raise RuntimeError("collection failure")\n',
            'import os, unittest\nclass T(unittest.TestCase):\n def test_exit(self): os._exit(86)\n',
        ):
            for suite in ('core', 'trust'):
                with self.subTest(source=source, suite=suite), fixture() as root, \
                     patch.object(python_test_runner, 'parallel_engine_ready', return_value=False), \
                     patch.object(python_test_runner, 'execute', wraps=execute) as launched:
                    directory = root if suite == 'core' else root / 'trust-ci'
                    tests = directory / 'tests'
                    tests.mkdir(parents=True, exist_ok=True)
                    (tests / 'test_sample.py').write_text(
                        'from pathlib import Path\nPath("collection-attempt").touch(exist_ok=False)\n' + source
                    )
                    result = (python_test_runner.run_core_tests(root, 'fast', 2).tests
                              if suite == 'core' else python_test_runner.run_trust_tests(root, 2))
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertTrue((directory / 'collection-attempt').is_file())
                    self.assertEqual(launched.call_count, 1)

    def test_degraded_serial_preserves_nested_pattern_and_single_collection(self) -> None:
        with fixture() as root, \
             patch.object(python_test_runner, 'parallel_engine_ready', return_value=False):
            sample = root / 'tests/test_sample.py'
            sample.write_text('from pathlib import Path\nPath("collected-once").touch(exist_ok=False)\n'
                              + sample.read_text())
            sample.rename(root / 'tests/testsample.py')
            nested = root / 'tests/nested'
            nested.mkdir()
            (nested / '__init__.py').write_text('')
            (nested / 'test_nested.py').write_text(
                'import unittest\nfrom pathlib import Path\nclass Nested(unittest.TestCase):\n'
                ' def test_nested(self): Path("result-nested").touch(exist_ok=False)\n'
            )
            result = python_test_runner.run_core_tests(root, 'fast', 2)
            self.assertEqual(result.tests.returncode, 0, result.tests.stdout + result.tests.stderr)
            self.assertEqual({p.name for p in root.glob('result-*')},
                             {f'result-{i}' for i in range(4)} | {'result-nested'})
            self.assertTrue((root / 'collected-once').is_file())

    def test_importable_but_wrong_versioned_parallel_dependency_still_fails(self) -> None:
        # Degradation is capability-only: with the engine importable, the declared
        # pinned contract stays strict — missing/mismatched versions fail, no serial retry.
        with fixture() as root:
            for label, version_effect in (
                ('missing', metadata.PackageNotFoundError),
                ('mismatched', lambda _name: '0.0.1'),
            ):
                with self.subTest(pinning=label), \
                     patch('adaptive_grok.python_test_runner.parallel_engine_ready', return_value=True), \
                     patch('adaptive_grok.python_test_runner._parallel_process_cleanup_supported', return_value=True), \
                     patch('adaptive_grok.python_test_runner.metadata.version', side_effect=version_effect):
                    result = next(check for check in _python(root) if check.name == 'python-unittest')
                self.assertEqual(result.status, 'fail', label)
                self.assertIn('python-test-requirements.txt' if label == 'missing' else 'requires tested version',
                              result.summary)
                self.assertFalse(list(root.glob('result-*')))

    def test_repo_root_without_optin_keeps_legacy_verifier_path(self) -> None:
        # AC-003 parity where it matters: THIS repository has no .grok-test-runner.json,
        # so grok_verify's python-unittest/coverage checks must take the legacy serial
        # commands and never enter the runner/pin machinery, even with GROK env noise.
        repo_root = Path(__file__).resolve().parents[1]
        self.assertFalse((repo_root / '.grok-test-runner.json').exists())
        self.assertIsNone(selected_workers(repo_root))
        seen: list[list[str]] = []

        def capture(root, name, command, timeout=300, *, env=None):
            seen.append(list(command))
            return CheckResult(name, 'pass', 'exit=0', command=command)

        environment = os.environ.copy()
        environment.pop('GROK_TEST_WORKERS', None)
        with patch.dict(os.environ, environment, clear=True), \
             patch('adaptive_grok.verification._command_check', side_effect=capture):
            results = {check.name: check for check in _python(repo_root, mode='pr')}
        self.assertIn('python-unittest', results)
        self.assertFalse(any('pytest' in cmd for cmd in seen), seen)
        self.assertIn(['coverage', 'run'], [cmd[:2] for cmd in seen], seen)
        self.assertTrue(any('discover' in cmd and '-s' in cmd and 'tests' in cmd for cmd in seen), seen)

    def test_inherited_pytest_selection_cannot_omit_tests(self) -> None:
        with fixture() as root:
            (root / 'pytest.ini').write_text('[pytest]\naddopts = -k test_0\nnorecursedirs = nested\n')
            nested = root / 'tests/nested'
            nested.mkdir()
            (nested / '__init__.py').write_text('')
            (nested / 'test_nested.py').write_text(
                'import unittest\nfrom pathlib import Path\nclass Nested(unittest.TestCase):\n'
                ' def test_nested(self):\n  Path("result-nested").touch(exist_ok=False)\n'
            )
            with patch.dict(os.environ, {'PYTEST_ADDOPTS': '-k nonexistent', 'PYTEST_PLUGINS': 'nonexistent_plugin'}):
                result = next(check for check in _python(root) if check.name == 'python-unittest')
            self.assertEqual(result.status, 'pass', result.stderr)
            self.assertEqual(len(list(root.glob('result-*'))), 5)

    def test_sigterm_cancels_owned_group_and_restores_previous_handler(self) -> None:
        with fixture() as root:
            pid_file = root / 'terminated-child.pid'
            child_code = f'import os,time; from pathlib import Path; Path({str(pid_file)!r}).write_text(str(os.getpid())); time.sleep(60)'
            code = (
                'import os,sys\nfrom pathlib import Path\n'
                'from adaptive_grok.python_test_runner import execute\n'
                f'execute([sys.executable,"-c",{child_code!r}],Path.cwd(),os.environ.copy())\n'
            )
            environment = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / '.grok-stack')}
            controller = subprocess.Popen([sys.executable, '-c', code], cwd=root, env=environment)
            try:
                for _ in range(500):
                    if pid_file.exists():
                        break
                    time.sleep(0.01)
                self.assertTrue(pid_file.exists(), 'controlled child did not start')
                controller.terminate()
                self.assertNotEqual(controller.wait(timeout=5), 0)
                self.assert_descendant_stopped(pid_file)
            finally:
                if controller.poll() is None:
                    controller.kill()
                    controller.wait(timeout=5)
                if pid_file.exists():
                    child_pid = int(pid_file.read_text())
                    try:
                        if os.getpgid(child_pid) == child_pid:
                            os.killpg(child_pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            previous = signal.getsignal(signal.SIGTERM)
            self.assertEqual(execute([sys.executable, '-c', 'pass'], root, environment).returncode, 0)
            self.assertIs(signal.getsignal(signal.SIGTERM), previous)
            self.assertEqual(execute([str(root / 'missing-command')], root, environment).returncode, 127)
            self.assertIs(signal.getsignal(signal.SIGTERM), previous)

    def test_assertion_collection_and_worker_failures_propagate(self) -> None:
        for source in (
            'import unittest\nclass T(unittest.TestCase):\n def test_bad(self): self.fail("expected")\n',
            'raise RuntimeError("collection failure")\n',
            '# no tests collected\n',
            'import os, unittest\nclass T(unittest.TestCase):\n def test_exit(self): os._exit(86)\n',
        ):
            with self.subTest(source=source), fixture() as root:
                (root / 'tests/test_sample.py').write_text(source)
                result = next(check for check in _python(root) if check.name == 'python-unittest')
                self.assertEqual(result.status, 'fail', result.stdout)

    def test_output_limit_applies_even_when_process_exits_quickly(self) -> None:
        with fixture() as root, patch('adaptive_grok.python_test_runner.OUTPUT_LIMIT', 16):
            result = execute([sys.executable, '-c', 'print("x" * 10000)'], root, os.environ.copy())
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('output limit', result.stderr)

    def test_timeout_stops_owned_descendant_process(self) -> None:
        with fixture() as root:
            pid_file = root / 'child.pid'
            code = (
                'import subprocess, sys, time\nfrom pathlib import Path\n'
                'child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])\n'
                f'Path({str(pid_file)!r}).write_text(str(child.pid))\n'
                'time.sleep(60)\n'
            )
            result = execute([sys.executable, '-c', code], root, os.environ.copy(), timeout=1)
            self.assertEqual(result.returncode, 124)
            self.assertIn('timeout', result.stderr)
            self.assert_descendant_stopped(pid_file)

    def test_controller_exit_stops_owned_descendant_process(self) -> None:
        with fixture() as root:
            pid_file = root / 'orphan.pid'
            code = (
                'import subprocess, sys\nfrom pathlib import Path\n'
                'child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])\n'
                f'Path({str(pid_file)!r}).write_text(str(child.pid))\n'
            )
            result = execute([sys.executable, '-c', code], root, os.environ.copy())
            self.assertEqual(result.returncode, 0)
            self.assert_descendant_stopped(pid_file)

    def test_coverage_below_threshold_and_worker_data_loss_fail(self) -> None:
        for scenario in ('below-threshold', 'missing-worker'):
            with self.subTest(scenario=scenario), fixture() as root:
                (root / 'subject.py').write_text(
                    'value = 1\n' + (
                        'def unused():\n' + ''.join(f'    value = {i}\n' for i in range(20))
                        if scenario == 'below-threshold' else ''
                    )
                )
                sample = root / 'tests/test_sample.py'
                sample.write_text('import subject\n' + sample.read_text())
                (root / '.coveragerc').write_text(
                    '[run]\nbranch = True\nsource = subject\n[report]\nfail_under = 74\n'
                )
                if scenario == 'missing-worker' and not parallel_engine_ready(measured=True):
                    self.skipTest('xdist worker data-loss is unobservable on a degraded serial engine')
                if scenario == 'missing-worker':
                    (root / 'conftest.py').write_text(
                        'import pytest\n@pytest.hookimpl(tryfirst=True, optionalhook=True)\n'
                        'def pytest_testnodedown(node, error):\n'
                        '    node.workeroutput.pop("cov_worker_node_id", None)\n'
                    )
                results = {check.name: check for check in _python(root, mode='pr')}
                self.assertEqual(results['coverage'].status, 'fail', results)

    def test_missing_and_corrupt_current_coverage_fail(self) -> None:
        for scenario in ('missing', 'corrupt'):
            with self.subTest(scenario=scenario), fixture() as root:
                (root / 'subject.py').write_text('value = 1\n')
                sample = root / 'tests/test_sample.py'
                sample.write_text('import subject\n' + sample.read_text())
                (root / '.coveragerc').write_text(
                    '[run]\nbranch = True\nsource = subject\n[report]\nfail_under = 74\n'
                )

                def damage_current_data(command, cwd, environment, **kwargs):
                    result = execute(command, cwd, environment, **kwargs)
                    if command[1:3] == ['-m', 'pytest'] or command[1:4] == ['-m', 'coverage', 'run']:
                        data = Path(environment['COVERAGE_FILE'])
                        if scenario == 'missing':
                            data.unlink()
                        else:
                            data.write_bytes(b'broken coverage data')
                    return result

                with patch('adaptive_grok.python_test_runner.execute', side_effect=damage_current_data):
                    results = {check.name: check for check in _python(root, mode='pr')}
                self.assertEqual(results['python-unittest'].status, 'pass', results)
                self.assertEqual(results['coverage'].status, 'fail', results)

    def test_nested_legacy_coverage_keeps_parent_data(self) -> None:
        with fixture() as root:
            (root / '.grok-test-runner.json').unlink()
            (root / 'subject.py').write_text('value = 1\n')
            sample = root / 'tests/test_sample.py'
            sample.write_text('import subject\n' + sample.read_text())
            (root / '.coveragerc').write_text(
                '[run]\nbranch = True\nsource = subject\n[report]\nfail_under = 74\n'
            )
            parent = root / 'parent.coverage'
            parent.write_bytes(b'parent-owned-evidence')
            with patch.dict(os.environ, {'COVERAGE_FILE': str(parent), '_GROK_TEST_CHILD': '1'}):
                results = {check.name: check for check in _python(root, mode='pr')}
            self.assertEqual(results['coverage'].status, 'pass', results)
            self.assertEqual(parent.read_bytes(), b'parent-owned-evidence')

    def test_opted_in_verifier_shards_each_method_once(self) -> None:
        with fixture() as root:
            result = next(check for check in _python(root) if check.name == 'python-unittest')
            self.assertEqual(result.status, 'pass', result.stderr + result.stdout)
            outputs = list(root.glob('result-*'))
            self.assertEqual({p.name for p in outputs}, {f'result-{i}' for i in range(4)})
            workers, engine = python_test_runner.select_engine(2, measured=False)
            self.assertEqual(json.loads(result.details[0]['versions'])['engine'], engine)
            if workers:
                self.assertEqual(result.command[result.command.index('-n') + 1], '2')
                self.assertIn('--dist=worksteal', result.command)
            else:
                self.assertEqual(len({p.read_text() for p in outputs}), 1)

    def test_invalid_worker_setting_fails_before_running_tests(self) -> None:
        for bad in ('invalid', 65, -1, 1.5, True):
            with self.subTest(workers=bad), fixture(workers=bad) as root:
                result = next(check for check in _python(root) if check.name == 'python-unittest')
                self.assertEqual(result.status, 'fail')
                self.assertFalse(list(root.glob('result-*')))
        with fixture() as root:
            config = root / '.grok-test-runner.json'
            config.write_text(json.dumps({'schema_version': 2, 'workers': 2}))
            self.assertRaises(RunnerError, selected_workers, root)
            config.write_text(json.dumps({'schema_version': 1, 'workers': 2, 'extra': 1}))
            self.assertRaises(RunnerError, selected_workers, root)
        with fixture(workers=0) as root, patch.dict(os.environ, {'GROK_TEST_WORKERS': '65'}):
            self.assertRaises(RunnerError, selected_workers, root)
        with fixture(workers=0) as root, patch.dict(os.environ, {'GROK_TEST_WORKERS': 'invalid'}):
            self.assertRaises(RunnerError, selected_workers, root)
        with fixture() as root:
            config = root / '.grok-test-runner.json'
            config.unlink()
            os.mkfifo(config)
            result = execute(
                [sys.executable, '-c',
                 'from pathlib import Path; from adaptive_grok.python_test_runner import selected_workers; selected_workers(Path.cwd())'],
                root, {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / '.grok-stack')}, timeout=1,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertNotEqual(result.returncode, 124, 'nonregular configuration must fail without blocking')

    def test_parallel_coverage_preserves_parent_and_existing_data(self) -> None:
        with fixture() as root:
            (root / 'subject.py').write_text('value = 1\n')
            sample = root / 'tests/test_sample.py'
            sample.write_text('import subject\n' + sample.read_text())
            (root / '.coveragerc').write_text(
                '[run]\nbranch = True\nsource = subject\n'
                '[report]\nfail_under = 74\n'
            )
            parent = root / 'parent.coverage'
            prior = root / '.coverage'
            parent.write_bytes(b'parent-owned-evidence')
            prior.write_bytes(b'previous-run-evidence')
            with patch.dict(os.environ, {'COVERAGE_FILE': str(parent)}):
                results = {check.name: check for check in _python(root, mode='pr')}
            self.assertEqual(results['python-unittest'].status, 'pass', results)
            self.assertEqual(results['coverage'].status, 'pass', results)
            self.assertEqual(parent.read_bytes(), b'parent-owned-evidence')
            self.assertEqual(prior.read_bytes(), b'previous-run-evidence')


if __name__ == '__main__':
    unittest.main()
