from __future__ import annotations

import contextlib
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
from adaptive_grok.python_test_runner import execute, selected_workers


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


class PythonTestRunnerTests(unittest.TestCase):
    def assert_descendant_stopped(self, pid_file: Path) -> None:
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
                self.assertEqual(len(list(trust.glob('*.pid'))), 6)
                for name in ('alpha', 'beta'):
                    self.assertEqual(len({p.read_text() for p in trust.glob(f'{name}-*.pid')}), 1)
                self.assertEqual(len({p.read_text() for p in trust.glob('*.pid')}), workers or 1)
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
            with patch('os.sched_getaffinity', return_value=set(range(22))):
                self.assertEqual(selected_workers(root), 22)
            with patch('os.sched_getaffinity', return_value=set(range(96))):
                self.assertEqual(selected_workers(root), 28)

    def test_missing_parallel_dependency_fails_without_serial_retry(self) -> None:
        with fixture() as root:
            with patch('adaptive_grok.python_test_runner.metadata.version', side_effect=metadata.PackageNotFoundError):
                result = next(check for check in _python(root) if check.name == 'python-unittest')
            self.assertEqual(result.status, 'fail')
            self.assertIn('python-test-requirements.txt', result.summary)
            self.assertFalse(list(root.glob('result-*')))

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
                    if command[1:3] == ['-m', 'pytest']:
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
            self.assertEqual(len({p.read_text() for p in outputs}), 2)

    def test_invalid_worker_setting_fails_before_running_tests(self) -> None:
        with fixture(workers='invalid') as root:
            result = next(check for check in _python(root) if check.name == 'python-unittest')
            self.assertEqual(result.status, 'fail')
            self.assertFalse(list(root.glob('result-*')))
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
