"""Fault controls for the actual verifier/owned runner/receipt boundaries."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import stat
import runpy
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok import python_test_runner as runner
from adaptive_grok import receipts
from adaptive_grok import util
from adaptive_grok import verification as verifier
from adaptive_grok.router import build_route
from adaptive_grok.state import set_active_route
from tests._support import project_copy as full_project_copy


def project_copy(*, git: bool = False):
    return full_project_copy(git=git, minimal_runtime=True)


@contextlib.contextmanager
def routed_fixture():
    with project_copy(git=True) as root:
        route = build_route(root, 'Fix verifier recovery', 'recovery').to_dict()
        set_active_route(root, route)
        # Tool availability is unrelated to these deterministic boundary faults.
        previous = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
        try:
            for number in previous:
                signal.signal(number, lambda signum, frame: None)
            with patch.object(verifier, '_semgrep', return_value=None), \
                 patch.object(verifier, '_trivy_config', return_value=None):
                yield root, route
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)


@contextlib.contextmanager
def output_close_faults(failing_labels, *, signal_on_close=None):
    """Close real files, then fail the chosen stdout/stderr context exits."""
    original = runner.tempfile.TemporaryFile
    opened = 0
    closed = {}

    def factory(*args, **kwargs):
        nonlocal opened
        label = ('stdout', 'stderr')[opened % 2]
        opened += 1

        @contextlib.contextmanager
        def managed():
            try:
                with original(*args, **kwargs) as handle:
                    yield handle
            finally:
                closed[label] = handle.closed
                if label == signal_on_close:
                    os.kill(os.getpid(), signal.SIGTERM)
                if label in failing_labels:
                    raise OSError(f'{label} output close fault')

        return managed()

    with patch.object(runner.tempfile, 'TemporaryFile', factory):
        yield closed


class VerifierRecoveryTests(unittest.TestCase):
    def test_publication_error_retires_recorded_pass(self):
        class BrokenOutput(io.StringIO):
            def write(self, text):
                raise OSError('publication failed')

        with routed_fixture() as (root, route), patch.object(verifier, '_python', return_value=[]):
            report = verifier.verify(root, mode='fast')
            self.assertEqual(receipts.get_receipt(root, route['route_id'], 'verification')['status'], 'pass')
            with patch.object(verifier, 'verify', return_value=report), patch.object(util, 'find_root', return_value=root), \
                 patch.object(sys, 'argv', ['grok_verify.py', '--json']), \
                 contextlib.redirect_stdout(BrokenOutput()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    runpy.run_path(str(ROOT / 'scripts/grok_verify.py'), run_name='__main__')
            self.assertEqual(caught.exception.code, 1)
            stored = receipts.get_receipt(root, route['route_id'], 'verification')
            self.assertEqual(stored['status'], 'fail')
            self.assertEqual(stored['details']['checks'][-1]['name'], 'report-publication')

    def test_cancellation_during_report_publication_keeps_completed_pass(self):
        class InterruptedOutput(io.StringIO):
            def write(self, text):
                os.kill(os.getpid(), signal.SIGTERM)
                return super().write(text)

        with routed_fixture() as (root, route), patch.object(verifier, '_python', return_value=[]):
            report = verifier.verify(root, mode='fast')
            with patch.object(verifier, 'verify', return_value=report), patch.object(util, 'find_root', return_value=root), \
                 patch.object(sys, 'argv', ['grok_verify.py', '--json']), \
                 contextlib.redirect_stdout(InterruptedOutput()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    runpy.run_path(str(ROOT / 'scripts/grok_verify.py'), run_name='__main__')
            self.assertEqual(caught.exception.code, 143)
            stored = receipts.get_receipt(root, route['route_id'], 'verification')
            self.assertEqual(stored['status'], 'fail')
            self.assertEqual(stored['details']['check_status'], 'pass')
            self.assertEqual(stored['details']['terminal_state'], 'cancelled')

    def test_node_cancellation_keeps_prior_command_failure(self):
        with routed_fixture() as (root, _):
            (root / 'package.json').write_text(json.dumps({'scripts': {'lint': 'lint', 'test': 'test'}}))

            def controlled(command, cwd, environment, **kwargs):
                if command[-1] == 'lint':
                    return runner.ProcessResult(command, 8, stderr='specific lint failure')
                raise runner.RunCancelled(signal.SIGTERM, runner.ProcessResult(command, 143, stdout='partial test output'))

            with patch.object(verifier, 'execute', side_effect=controlled), patch.object(verifier, 'command_exists', return_value=True):
                with self.assertRaises(SystemExit) as caught:
                    verifier.verify(root, mode='fast', record=False)
            report = caught.exception.report
            self.assertEqual(report['check_status'], 'fail')
            self.assertEqual(next(c for c in report['checks'] if c['name'] == 'npm-lint')['stderr'], 'specific lint failure')
            self.assertEqual(next(c for c in report['checks'] if c['name'] == 'npm-test')['stdout'], 'partial test output')

    def test_cancellation_during_coverage_preserves_completed_core_failure(self):
        from tests.test_python_test_runner import fixture
        with fixture(workers=0) as root:
            (root / '.coveragerc').write_text('[run]\nbranch = True\n')

            def controlled(command, cwd, environment, **kwargs):
                if 'report' in command:
                    raise runner.RunCancelled(signal.SIGTERM, runner.ProcessResult(command, 143, stdout='partial coverage'))
                Path(environment['COVERAGE_FILE']).write_bytes(b'controlled coverage')
                return runner.ProcessResult(command, 7, stderr='specific test assertion')

            with patch.object(runner, 'execute', side_effect=controlled):
                with self.assertRaises(runner.RunCancelled) as caught:
                    verifier._python(root, 'pr')
            checks = [c.to_dict() for c in caught.exception.checks]
            self.assertEqual(next(c for c in checks if c['name'] == 'python-unittest')['stderr'], 'specific test assertion')
            self.assertEqual(next(c for c in checks if c['name'] == 'coverage')['status'], 'cancelled')

    def test_report_publication_failure_emits_retained_report_on_stderr(self):
        class BrokenOutput(io.StringIO):
            def write(self, text):
                raise OSError('publication failed')

        with routed_fixture() as (root, _), patch.object(verifier, '_python', return_value=[verifier.CheckResult('python-unittest', 'fail', 'specific assertion')]):
            report = verifier.verify(root, mode='fast', record=False)
        error_output = io.StringIO()
        with patch.object(verifier, 'verify', return_value=report), \
             patch.object(sys, 'argv', ['grok_verify.py', '--json', '--no-record']), \
             contextlib.redirect_stdout(BrokenOutput()), contextlib.redirect_stderr(error_output):
            with self.assertRaises(SystemExit) as caught:
                runpy.run_path(str(ROOT / 'scripts/grok_verify.py'), run_name='__main__')
        self.assertEqual(caught.exception.code, 1)
        retained = json.loads(error_output.getvalue())
        self.assertEqual(retained['check_status'], 'fail')
        self.assertEqual(next(c for c in retained['checks'] if c['name'] == 'python-unittest')['summary'], 'specific assertion')
        self.assertEqual(retained['checks'][-1]['name'], 'report-publication')

    def test_receipt_failure_keeps_completed_verdict_and_report(self):
        for error in (OSError('disk full'), RuntimeError('invalid receipt binding'),
                      ValueError('malformed report'), TypeError('invalid report field')):
            for verdict in ('pass', 'fail'):
                with self.subTest(error=type(error).__name__, verdict=verdict), routed_fixture() as (root, _):
                    completed = verifier.CheckResult('python-unittest', verdict, 'original verdict', stdout='retained')
                    with patch.object(verifier, '_python', return_value=[completed]), \
                         patch.object(verifier, 'write_receipt', side_effect=error):
                        report = verifier.verify(root, mode='fast')
                    self.assertEqual(report['status'], 'fail')
                    self.assertEqual(report['check_status'], verdict)
                    self.assertEqual(report['checks'][-1]['name'], 'receipt-recording')
                    original = next(check for check in report['checks'] if check['name'] == 'python-unittest')
                    self.assertEqual((original['status'], original['stdout']), (verdict, 'retained'))
                    json.dumps(report, ensure_ascii=True)

    def test_cancellation_before_dispatch_spawns_nothing_and_overwrites_old_pass(self):
        with routed_fixture() as (root, route):
            receipts.write_receipt(root, 'verification', 'pass')
            real_inventory = verifier._changed_file_inventory

            def cancel_before_checks(*args, **kwargs):
                result = real_inventory(*args, **kwargs)
                os.kill(os.getpid(), signal.SIGTERM)
                return result

            with patch.object(verifier, '_changed_file_inventory', side_effect=cancel_before_checks), \
                 patch.object(runner.subprocess, 'Popen', wraps=subprocess.Popen) as launch:
                with self.assertRaises(SystemExit) as caught:
                    verifier.verify(root, mode='fast')
            report = caught.exception.report
            self.assertEqual(report['terminal_state'], 'cancelled')
            self.assertEqual(caught.exception.code, 143)
            # Git inventory may launch Git; no test command was dispatched.
            self.assertFalse(any('-m' in call.args[0] for call in launch.call_args_list))
            stored = receipts.get_receipt(root, route['route_id'], 'verification')
            self.assertEqual(stored['status'], 'fail')
            self.assertEqual(stored['details']['terminal_state'], 'cancelled')

    def test_post_result_cancellation_preserves_test_failure(self):
        with routed_fixture() as (root, _):
            original_fingerprint = verifier.tree_fingerprint
            calls = 0

            def cancel_at_stability(path):
                nonlocal calls
                calls += 1
                result = original_fingerprint(path)
                if calls == 2:
                    os.kill(os.getpid(), signal.SIGINT)
                return result

            with patch.object(verifier, 'tree_fingerprint', side_effect=cancel_at_stability), \
                 patch.object(verifier, '_python', return_value=[verifier.CheckResult('python-unittest', 'fail', 'assertion failed')]):
                with self.assertRaises(SystemExit) as caught:
                    verifier.verify(root, mode='fast')
            report = caught.exception.report
            self.assertEqual((report['status'], report['check_status'], report['terminal_state']), ('fail', 'fail', 'cancelled'))
            self.assertEqual(next(c for c in report['checks'] if c['name'] == 'python-unittest')['summary'], 'assertion failed')

    def test_cancellation_during_publication_records_terminal_failure(self):
        with routed_fixture() as (root, route):
            original_replace = receipts.os.replace
            interrupted = False

            def cancel_on_replace(source, target, *args, **kwargs):
                nonlocal interrupted
                if str(target).endswith('/verification.json') and not interrupted:
                    interrupted = True
                    os.kill(os.getpid(), signal.SIGTERM)
                return original_replace(source, target, *args, **kwargs)

            with patch.object(verifier, '_python', return_value=[verifier.CheckResult('python-unittest', 'pass', 'complete')]), \
                 patch.object(receipts.os, 'replace', side_effect=cancel_on_replace):
                with self.assertRaises(SystemExit) as caught:
                    verifier.verify(root, mode='fast')
            report = caught.exception.report
            self.assertEqual(report['check_status'], 'pass')
            self.assertEqual(report['terminal_state'], 'cancelled')
            stored = receipts.get_receipt(root, route['route_id'], 'verification')
            self.assertEqual(stored['status'], 'fail')
            self.assertEqual(stored['details']['terminal_state'], 'cancelled')
            self.assertFalse(list((root / '.grok-stack/runtime/receipts' / route['route_id']).glob('.verification.json.*')))

    def test_focused_receipt_failure_retains_selected_scope(self):
        with routed_fixture() as (root, _):
            with patch.object(verifier, 'write_receipt', side_effect=OSError('disk full')):
                report = verifier.verify(root, mode='focused-static-seo-landing')
            self.assertEqual(report['status'], 'fail')
            self.assertEqual(report['mode'], 'focused-static-seo-landing')
            self.assertIn('verification_scope', report)
            self.assertEqual(report['checks'][-1]['name'], 'receipt-recording')


class OwnedRunnerRecoveryTests(unittest.TestCase):
    def test_output_close_keeps_completed_pass_and_failure(self):
        for labels in (('stdout',), ('stderr',), ('stdout', 'stderr')):
            for code in (0, 7):
                with self.subTest(labels=labels, code=code), tempfile.TemporaryDirectory() as directory, output_close_faults(labels) as closed:
                    result = runner.execute(
                        [sys.executable, '-c', f'import sys; print("specific original stdout"); print("specific original stderr", file=sys.stderr); sys.exit({code})'],
                        Path(directory), os.environ.copy(),
                    )
                    self.assertEqual(result.returncode, code)
                    self.assertEqual(result.stdout, 'specific original stdout\n')
                    self.assertEqual(result.stderr, 'specific original stderr\n')
                    for label in labels:
                        self.assertIn(f'{label} output close fault', result.cleanup_error)
                    self.assertEqual(closed, {'stdout': True, 'stderr': True})

    def test_output_close_keeps_primary_cancellation_and_result(self):
        original_stop = runner._stop

        def cancel_after_result(process):
            original_stop(process)
            os.kill(os.getpid(), signal.SIGTERM)

        for labels in (('stdout',), ('stderr',), ('stdout', 'stderr')):
            with self.subTest(labels=labels), tempfile.TemporaryDirectory() as directory, output_close_faults(labels) as closed, \
                 patch.object(runner, '_stop', side_effect=cancel_after_result):
                with self.assertRaises(runner.RunCancelled) as caught:
                    runner.execute([sys.executable, '-c', 'print("specific cancelled output"); raise SystemExit(7)'], Path(directory), os.environ.copy())
                self.assertEqual(caught.exception.code, 143)
                result = caught.exception.result
                self.assertEqual((result.returncode, result.terminal_state), (7, 'cancelled'))
                self.assertEqual(result.stdout, 'specific cancelled output\n')
                for label in labels:
                    self.assertIn(f'{label} output close fault', result.cleanup_error)
                    self.assertTrue(any(f'{label} output close fault' in note for note in caught.exception.__notes__))
                self.assertEqual(closed, {'stdout': True, 'stderr': True})

    def test_output_close_failure_keeps_missing_command_result(self):
        with tempfile.TemporaryDirectory() as directory, output_close_faults(('stdout', 'stderr')) as closed:
            result = runner.execute([str(Path(directory) / 'missing-owned-command')], Path(directory), os.environ.copy())
        self.assertEqual(result.returncode, 127)
        self.assertIn('missing-owned-command', result.stderr)
        self.assertIn('stdout output close fault', result.cleanup_error)
        self.assertIn('stderr output close fault', result.cleanup_error)
        self.assertEqual(closed, {'stdout': True, 'stderr': True})

    def test_output_close_failure_keeps_pre_result_primary_exception(self):
        with output_close_faults(('stdout', 'stderr')) as closed, \
             patch.object(runner.subprocess, 'Popen', side_effect=ValueError('specific pre-result failure')):
            with self.assertRaisesRegex(ValueError, 'specific pre-result failure') as caught:
                runner.execute([sys.executable, '-c', 'pass'], ROOT, os.environ.copy())
        for label in ('stdout', 'stderr'):
            self.assertTrue(any(f'{label} output close fault' in note for note in caught.exception.__notes__))
        self.assertEqual(closed, {'stdout': True, 'stderr': True})

    def test_output_close_failure_fails_gate_with_completed_exit_visible(self):
        for labels in (('stdout',), ('stderr',), ('stdout', 'stderr')):
            with self.subTest(labels=labels), tempfile.TemporaryDirectory() as directory, output_close_faults(labels):
                check = verifier._command_check(Path(directory), 'close-controlled', [sys.executable, '-c', 'print("specific completed pass")'])
                self.assertEqual(check.status, 'fail')
                self.assertEqual(check.summary, 'exit=0')
                self.assertEqual(check.stdout, 'specific completed pass\n')
                for label in labels:
                    self.assertIn(f'{label} output close fault', check.stderr)

    def test_signal_during_output_close_keeps_completed_result(self):
        for label in ('stdout', 'stderr'):
            with self.subTest(label=label), output_close_faults((label,), signal_on_close=label) as closed:
                with self.assertRaises(runner.RunCancelled) as caught:
                    runner.execute([sys.executable, '-c', 'print("completed before close signal"); raise SystemExit(7)'], ROOT, os.environ.copy())
                self.assertEqual(caught.exception.code, 143)
                self.assertEqual(caught.exception.result.returncode, 7)
                self.assertEqual(caught.exception.result.stdout, 'completed before close signal\n')
                self.assertIn(f'{label} output close fault', caught.exception.result.cleanup_error)
                self.assertEqual(closed, {'stdout': True, 'stderr': True})

    def test_completed_pass_remains_visible_when_cleanup_fails_gate(self):
        real_stop = runner._stop

        def failed_cleanup(process):
            real_stop(process)
            raise OSError('cleanup failed')

        with tempfile.TemporaryDirectory() as directory, patch.object(runner, '_stop', side_effect=failed_cleanup):
            root = Path(directory)
            result = runner.execute([sys.executable, '-c', 'print("completed pass")'], root, os.environ.copy())
            check = verifier._command_check(root, 'controlled-check', [sys.executable, '-c', 'pass'])
        self.assertEqual(result.returncode, 0)
        self.assertIn('completed pass', result.stdout)
        self.assertEqual(check.status, 'fail')
        self.assertEqual(check.summary, 'exit=0')
        self.assertIn('cleanup failed', check.stderr)

    def test_cancellation_before_spawn_has_result_and_restores_handlers(self):
        previous = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
        with runner._cancellation():
            os.kill(os.getpid(), signal.SIGTERM)
            with patch.object(runner.subprocess, 'Popen', wraps=subprocess.Popen) as launch:
                with self.assertRaises(SystemExit) as caught:
                    runner.execute([sys.executable, '-c', 'raise SystemExit(99)'], ROOT, os.environ.copy())
            self.assertFalse(launch.called)
            self.assertEqual(caught.exception.result.terminal_state, 'cancelled')
        for number, handler in previous.items():
            self.assertEqual(signal.getsignal(number), handler)

    def test_temporary_cleanup_failure_retains_completed_core_failure(self):
        from tests.test_python_test_runner import fixture
        cleanup = tempfile.TemporaryDirectory.cleanup

        def failed_cleanup(directory):
            cleanup(directory)
            raise OSError('scratch cleanup failed')

        with fixture(workers=0) as root:
            (root / 'tests/test_sample.py').write_text('import unittest\nclass T(unittest.TestCase):\n def test_bad(self): self.fail("specific failure")\n')
            with patch.object(tempfile.TemporaryDirectory, 'cleanup', failed_cleanup):
                result = runner.run_core_tests(root, 'fast', 0)
            self.assertNotEqual(result.tests.returncode, 0)
            self.assertIn('specific failure', result.tests.stderr)
            self.assertIn('scratch cleanup failed', result.tests.cleanup_error)

    def test_malformed_coverage_report_preserves_specific_test_verdict(self):
        from tests.test_python_test_runner import fixture
        for source in ('{"files":', '[]', '{"files": [], "meta": null}', '{"files": {}, "meta": {}, "totals": []}'):
            with self.subTest(source=source), fixture(workers=0) as root:
                (root / '.coveragerc').write_text('[run]\nbranch = True\n')

                def controlled_command(command, cwd, environment, **kwargs):
                    if '-o' in command:
                        Path(command[command.index('-o') + 1]).write_text(source)
                        return runner.ProcessResult(command, 0)
                    if 'report' in command:
                        return runner.ProcessResult(command, 0)
                    Path(environment['COVERAGE_FILE']).write_bytes(b'controlled coverage data')
                    return runner.ProcessResult(command, 7, stderr='specific assertion')

                with patch.object(runner, 'execute', side_effect=controlled_command):
                    result = runner.run_core_tests(root, 'pr', 0)
                self.assertEqual(result.tests.returncode, 7)
                self.assertEqual(result.tests.stderr, 'specific assertion')
                self.assertEqual(result.coverage.returncode, 1)
                self.assertIn('invalid current-run coverage', result.coverage.stderr)

    def test_completed_failure_survives_cleanup_error(self):
        real_stop = runner._stop

        def failed_cleanup(process):
            real_stop(process)
            raise OSError('cleanup failed')

        with tempfile.TemporaryDirectory() as directory, patch.object(runner, '_stop', side_effect=failed_cleanup):
            result = runner.execute([sys.executable, '-c', 'print("original output"); raise SystemExit(7)'], Path(directory), os.environ.copy())
        self.assertEqual(result.returncode, 7)
        self.assertIn('original output', result.stdout)
        self.assertIn('cleanup failed', result.cleanup_error)

    def test_running_term_resistant_child_is_reaped_and_unrelated_child_survives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pid_file = root / 'owned.pid'
            report_file = root / 'result.json'
            child = 'import os,signal,time; from pathlib import Path; signal.signal(signal.SIGTERM, signal.SIG_IGN); Path("owned.pid").write_text(str(os.getpid())); time.sleep(30)'
            controller_code = (
                'import json,os,sys\nfrom pathlib import Path\n'
                'from adaptive_grok.python_test_runner import execute\n'
                'try:\n'
                f' execute([sys.executable,"-c",{child!r}],Path.cwd(),os.environ.copy())\n'
                'except SystemExit as exc:\n'
                ' Path("result.json").write_text(json.dumps({"code":exc.code,"stdout":exc.result.stdout,"state":exc.result.terminal_state}))\n'
                ' raise\n'
            )
            unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], start_new_session=True)
            controller = subprocess.Popen([sys.executable, '-c', controller_code], cwd=root, env={**os.environ, 'PYTHONPATH': str(ROOT / '.grok-stack')})
            try:
                deadline = time.monotonic() + 5
                while not pid_file.exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(pid_file.exists())
                started = time.monotonic()
                controller.terminate()
                self.assertEqual(controller.wait(timeout=5), 143)
                self.assertLess(time.monotonic() - started, 5)
                owned_pid = int(pid_file.read_text())
                with self.assertRaises(ProcessLookupError):
                    os.kill(owned_pid, 0)
                self.assertIsNone(unrelated.poll())
                self.assertEqual(json.loads(report_file.read_text())['state'], 'cancelled')
            finally:
                for process in (controller, unrelated):
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
                if pid_file.exists():
                    try:
                        os.killpg(int(pid_file.read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_invalid_utf8_is_bounded_and_disclosed_without_losing_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            result = runner.execute([sys.executable, '-c', 'import os; os.write(1,b"partial-\\xff"); raise SystemExit(9)'], Path(directory), os.environ.copy())
        self.assertEqual(result.returncode, 9)
        self.assertEqual(result.stdout, r'partial-\xff')


class DurableReceiptRecoveryTests(unittest.TestCase):
    def test_first_post_link_stat_fault_preserves_in_place_foreign_bytes(self):
        replacements = (b'foreign in-place replacement', b'{"binding":{"kind":"foreignxxxxx"},"details":{},"schema_version":1}\n')
        for replacement in replacements:
            with self.subTest(replacement=replacement), routed_fixture() as (root, route):
                original_stat = receipts.os.stat
                failed = False
                def rewrite_then_fail_once(path, *args, **kwargs):
                    nonlocal failed
                    if not failed and isinstance(path, str) and len(path) == 69 and path.endswith('.json') and 'dir_fd' in kwargs:
                        failed = True
                        if replacement.startswith(b'{'):
                            self.assertEqual(len(replacement), original_stat(path, *args, **kwargs).st_size)
                            self.assertIsInstance(json.loads(replacement), dict)
                        descriptor = os.open(path, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW, dir_fd=kwargs['dir_fd'])
                        with os.fdopen(descriptor, 'wb') as handle:
                            handle.write(replacement)
                        raise OSError('first stat failed after in-place rewrite')
                    return original_stat(path, *args, **kwargs)
                with patch.object(receipts.os, 'stat', side_effect=rewrite_then_fail_once), self.assertRaisesRegex(OSError, 'first stat failed'):
                    receipts._publish_verification_report(root, route['route_id'], {'kind': 'verification', 'details': {}}, None)
                self.assertTrue(failed)
                files = list(receipts.receipt_dir(root, route['route_id']).glob('reports/*.json'))
                self.assertEqual(len(files), 1)
                self.assertEqual(files[0].read_bytes(), replacement)
                self.assertFalse(list(files[0].parent.glob('*.tmp')))

    def test_second_post_link_stat_fault_cleans_unchanged_bytes_across_ctime_boundary(self):
        with routed_fixture() as (root, route):
            original_stat = receipts.os.stat
            calls = 0
            first_metadata = None
            def fail_second_after_clock_boundary(path, *args, **kwargs):
                nonlocal calls, first_metadata
                if isinstance(path, str) and len(path) == 69 and path.endswith('.json') and 'dir_fd' in kwargs:
                    calls += 1
                    if calls == 1:
                        first_metadata = original_stat(path, *args, **kwargs)
                        time.sleep(0.025)
                        return first_metadata
                    if calls == 2:
                        current = original_stat(path, *args, **kwargs)
                        self.assertEqual((current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns),
                                         (first_metadata.st_dev, first_metadata.st_ino, first_metadata.st_size, first_metadata.st_mtime_ns))
                        self.assertNotEqual(current.st_ctime_ns, first_metadata.st_ctime_ns)
                        raise OSError('second stat failed after own temporary unlink')
                return original_stat(path, *args, **kwargs)
            with patch.object(receipts.os, 'stat', side_effect=fail_second_after_clock_boundary), self.assertRaisesRegex(OSError, 'second stat failed'):
                receipts._publish_verification_report(root, route['route_id'], {'kind': 'verification', 'details': {}}, None)
            self.assertGreaterEqual(calls, 2)
            self.assertFalse(list(receipts.receipt_dir(root, route['route_id']).rglob('reports/*.json')))
            self.assertFalse(list(receipts.receipt_dir(root, route['route_id']).rglob('*.tmp')))

    def test_report_helper_does_not_adopt_replacement_between_link_and_stat(self):
        with routed_fixture() as (root, route):
            original_link = receipts.os.link
            def replace_after_link(source, destination, **kwargs):
                original_link(source, destination, **kwargs)
                directory_fd = kwargs['dst_dir_fd']
                os.unlink(destination, dir_fd=directory_fd)
                descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
                with os.fdopen(descriptor, 'wb') as handle:
                    handle.write(b'foreign replacement')
            with patch.object(receipts.os, 'link', side_effect=replace_after_link), self.assertRaisesRegex(RuntimeError, 'identity changed'):
                receipts._publish_verification_report(root, route['route_id'], {'kind': 'verification', 'details': {}}, None)
            files = list(receipts.receipt_dir(root, route['route_id']).glob('reports/*.json'))
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].read_bytes(), b'foreign replacement')
            self.assertFalse(list(files[0].parent.glob('*.tmp')))

    def test_report_helper_post_link_stat_fault_cleans_descriptor_owned_artifact(self):
        with routed_fixture() as (root, route):
            original_stat = receipts.os.stat
            failed = False
            def fail_once(path, *args, **kwargs):
                nonlocal failed
                if not failed and isinstance(path, str) and len(path) == 69 and path.endswith('.json') and 'dir_fd' in kwargs:
                    failed = True
                    raise OSError('post-link stat fault')
                return original_stat(path, *args, **kwargs)
            with patch.object(receipts.os, 'stat', side_effect=fail_once), self.assertRaisesRegex(OSError, 'post-link stat fault'):
                receipts._publish_verification_report(root, route['route_id'], {'kind': 'verification', 'details': {}}, None)
            self.assertTrue(failed)
            self.assertFalse(list(receipts.receipt_dir(root, route['route_id']).rglob('reports/*.json')))
            self.assertFalse(list(receipts.receipt_dir(root, route['route_id']).rglob('*.tmp')))

    def test_report_helper_post_publication_cancellation_removes_owned_artifact(self):
        with routed_fixture() as (root, route):
            calls = 0
            def cancel_after_publication():
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError('cancel after digest publication')
            with self.assertRaisesRegex(RuntimeError, 'cancel after digest publication'):
                receipts._publish_verification_report(root, route['route_id'], {'kind': 'verification', 'details': {'captured': 'x' * receipts.MAX_RECEIPT_BYTES}}, cancel_after_publication)
            self.assertEqual(calls, 2)
            self.assertFalse(list(receipts.receipt_dir(root, route['route_id']).rglob('reports/*.json')))
            self.assertFalse(list(receipts.receipt_dir(root, route['route_id']).rglob('*.tmp')))

    def test_envelope_failures_do_not_accumulate_new_report_orphans(self):
        with routed_fixture() as (root, route):
            for attempt in range(3):
                with self.subTest(attempt=attempt), patch.object(receipts, '_publish_receipt', side_effect=OSError('envelope failed')):
                    with self.assertRaisesRegex(OSError, 'envelope failed'):
                        receipts.write_receipt(root, 'verification', 'pass', details={'captured': str(attempt) * receipts.MAX_RECEIPT_BYTES})
                self.assertIsNone(receipts.get_receipt(root, route['route_id'], 'verification'))
                self.assertFalse(list(receipts.receipt_dir(root, route['route_id']).rglob('reports/*.json')))

    def test_aborted_reused_report_preserves_preexisting_referenced_digest(self):
        with routed_fixture() as (root, route), patch.object(receipts, 'now_utc', return_value='2026-10-04T00:00:00Z'):
            details = {'captured': 'x' * receipts.MAX_RECEIPT_BYTES}
            path = receipts.write_receipt(root, 'verification', 'pass', details=details)
            envelope = json.loads(path.read_bytes())
            artifact = root / envelope['details']['_verification_report']['path']
            original_bytes = artifact.read_bytes()
            original_identity = artifact.stat().st_ino
            with patch.object(receipts, '_publish_receipt', side_effect=OSError('envelope failed')):
                with self.assertRaises(OSError):
                    receipts.write_receipt(root, 'verification', 'pass', details=details)
            self.assertEqual(artifact.read_bytes(), original_bytes)
            self.assertEqual(artifact.stat().st_ino, original_identity)
            self.assertEqual(list(artifact.parent.glob('*.json')), [artifact])

    def test_report_helper_abort_preserves_a_referenced_reused_artifact(self):
        with routed_fixture() as (root, route):
            details = {'captured': 'x' * receipts.MAX_RECEIPT_BYTES}
            path = receipts.write_receipt(root, 'verification', 'pass', details=details)
            envelope = json.loads(path.read_bytes())
            artifact = root / envelope['details']['_verification_report']['path']
            before = (artifact.read_bytes(), artifact.stat().st_ino)
            envelope['details'] = details
            calls = 0
            def cancel_after_publication():
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError('cancel reused artifact')
            with self.assertRaises(RuntimeError):
                receipts._publish_verification_report(root, route['route_id'], envelope, cancel_after_publication)
            self.assertEqual((artifact.read_bytes(), artifact.stat().st_ino), before)
            self.assertEqual(receipts.get_receipt(root, route['route_id'], 'verification')['details'], details)

    def test_abort_cleanup_does_not_unlink_identity_changed_report(self):
        with routed_fixture() as (root, route):
            artifact = None
            def replace_before_envelope_failure(*args):
                nonlocal artifact
                artifact = next(receipts.receipt_dir(root, route['route_id']).glob('reports/*.json'))
                artifact.write_bytes(b'foreign replacement bytes')
                raise OSError('envelope failed after report identity changed')
            with patch.object(receipts, '_publish_receipt', side_effect=replace_before_envelope_failure), self.assertRaises(OSError):
                receipts.write_receipt(root, 'verification', 'pass', details={'captured': 'x' * receipts.MAX_RECEIPT_BYTES})
            self.assertEqual(artifact.read_bytes(), b'foreign replacement bytes')

    def test_large_scope_metadata_roundtrips_through_bounded_report(self):
        with routed_fixture() as (root, route):
            route['required_evidence'] = ['verification']
            set_active_route(root, route)
            fingerprint = util.tree_fingerprint(root)
            head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
            paths = [f'engineering/changes/20260918-historical-delivery-provenance-and-acceptance-123abc/evidence/historical-{index:05d}-source-contract.md' for index in range(1442)]
            scope = {'profile': 'full-pr-suite', 'eligible': False, 'evidence_kind': 'verification:full-pr', 'reason_code': 'unsafe-file-status', 'reason': 'renamed historical inventory requires full verification', 'changed_paths_digest': 'a' * 64, 'checked_files': paths, 'rejected_files': paths[:488], 'skipped_checks': [], 'status_channels': {'comparison': 'trusted', 'staged': 'trusted', 'unstaged': 'trusted', 'untracked': 'trusted'}}
            report = {'status': 'pass', 'mode': 'pr', 'route_id': route['route_id'], 'tree_fingerprint': fingerprint, 'changed_files': paths, 'changed_file_inventory': {'bases': [{'base': head, 'target': head}], 'union_count': len(paths), 'status_channels': scope['status_channels']}, 'docs_state_scope': scope, 'checks': [verifier._docs_state_scope_check(scope).to_dict()]}
            self.assertEqual(len(scope['checked_files']), 1442)
            self.assertEqual(len(scope['rejected_files']), 488)
            self.assertGreater(len(json.dumps(report, ensure_ascii=True, separators=(',', ':')).encode()), receipts.MAX_RECEIPT_BYTES)
            verifier._record_verification_receipt(root, report, fingerprint)
            self.assertEqual(report['status'], 'pass', report['checks'][-1])
            receipt = receipts.get_receipt(root, route['route_id'], 'verification')
            self.assertEqual(receipt['details'], report)
            self.assertEqual(receipts.validate_evidence(root, route), [])

    def test_large_verification_report_preserves_complete_logs_and_scope(self):
        with routed_fixture() as (root, route):
            route['required_evidence'] = ['verification']
            set_active_route(root, route)
            fingerprint = util.tree_fingerprint(root)
            head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
            paths = [f'engineering/changes/example/evidence/checked-{index:05d}.md' for index in range(1500)]
            captured = 'captured output\n' * 750  # Each log respects the actual 12,000-character capture bound.
            scope = {'profile': 'full-pr', 'eligible': False, 'evidence_kind': 'verification:full-pr', 'reason_code': 'unsafe-file-status', 'changed_paths_digest': 'a' * 64, 'checked_files': paths, 'skipped_checks': ['historical-only-check']}
            checks = [verifier.CheckResult('python-unittest', 'pass', 'exit=0', command=['python3', '-m', 'unittest'], stdout=captured).to_dict()]
            checks.extend(verifier.CheckResult(f'captured-check-{index}', 'pass', 'exit=0', stdout=captured).to_dict() for index in range(8))
            checks.append(verifier.CheckResult('historical-only-check', 'skip', 'historical evidence is not current execution').to_dict())
            report = {'status': 'pass', 'mode': 'pr', 'route_id': route['route_id'], 'tree_fingerprint': fingerprint, 'changed_files': paths, 'changed_file_inventory': {'bases': [{'base': head, 'target': head}], 'union_count': len(paths)}, 'docs_state_scope': scope, 'checks': checks}
            self.assertGreater(len(json.dumps(report).encode()), receipts.MAX_RECEIPT_BYTES)
            verifier._record_verification_receipt(root, report, fingerprint)
            self.assertEqual(report['status'], 'pass', report['checks'][-1])
            receipt = receipts.get_receipt(root, route['route_id'], 'verification')
            self.assertIsNotNone(receipt)
            self.assertLessEqual((receipts.receipt_dir(root, route['route_id']) / 'verification.json').stat().st_size, receipts.MAX_RECEIPT_BYTES)
            self.assertEqual(receipt['tree_fingerprint'], fingerprint)
            self.assertEqual(receipt['git_head'], head)
            details = receipt['details']
            self.assertEqual(details['changed_file_inventory']['bases'], report['changed_file_inventory']['bases'])
            for field in ('profile', 'evidence_kind', 'reason_code', 'changed_paths_digest', 'skipped_checks'):
                self.assertEqual(details['docs_state_scope'][field], scope[field])
            self.assertEqual([(item['name'], item['status'], item['summary']) for item in details['checks']], [(item['name'], item['status'], item['summary']) for item in report['checks']])
            self.assertEqual(details['changed_files'], paths)
            self.assertEqual(details['docs_state_scope'], scope)
            self.assertEqual(details, report)
            reference = receipt['details_reference']
            artifact_bytes = (root / reference['path']).read_bytes()
            self.assertEqual(reference['bytes'], len(artifact_bytes))
            self.assertEqual(reference['sha256'], hashlib.sha256(artifact_bytes).hexdigest())
            self.assertEqual(json.loads(artifact_bytes)['details'], report)
            self.assertEqual(len(report['changed_files']), len(paths))
            self.assertEqual(report['checks'][0]['stdout'], captured)
            self.assertEqual(receipts.validate_evidence(root, route), [])
            with (root / 'VERSION').open('a', encoding='utf-8') as handle:
                handle.write('\nstale product edit\n')
            self.assertIn('verification: stale after repository changes', receipts.validate_evidence(root, route))

    def test_bounded_report_does_not_bypass_expected_tree_binding(self):
        with routed_fixture() as (root, route):
            report = {'status': 'pass', 'route_id': route['route_id'], 'checks': [verifier.CheckResult('python-unittest', 'pass', 'exit=0', stdout='x' * receipts.MAX_RECEIPT_BYTES).to_dict()]}
            verifier._record_verification_receipt(root, report, '0' * 64)
            self.assertEqual(report['status'], 'fail')
            self.assertEqual(report['checks'][-1]['name'], 'receipt-recording')
            self.assertIsNone(receipts.get_receipt(root, route['route_id'], 'verification'))
            self.assertFalse(list((root / '.grok-stack/runtime/receipts').rglob('reports/*.json')))

    def test_oversized_report_still_fails_and_invalidates_prior_receipt(self):
        with routed_fixture() as (root, route):
            fingerprint = util.tree_fingerprint(root)
            receipts.write_receipt(root, 'verification', 'pass')
            paths = [f'engineering/changes/example/evidence/checked-{index:05d}.md' for index in range(10000)]
            report = {'status': 'pass', 'route_id': route['route_id'], 'tree_fingerprint': fingerprint, 'changed_files': paths, 'checks': [verifier.CheckResult('python-unittest', 'pass', 'exit=0').to_dict()]}
            with patch.object(receipts, 'MAX_VERIFICATION_REPORT_BYTES', 65536):
                verifier._record_verification_receipt(root, report, fingerprint)
            self.assertEqual(report['status'], 'fail')
            self.assertEqual(report['evidence_status'], 'failed')
            self.assertEqual(report['changed_files'], paths)
            self.assertEqual(report['checks'][-1]['name'], 'receipt-recording')
            self.assertIn('verification report exceeds the byte limit', report['checks'][-1]['details'][0]['message'])
            self.assertIsNone(receipts.get_receipt(root, route['route_id'], 'verification'))

    def test_spilled_report_missing_tampered_and_unsafe_files_fail_closed(self):
        for mutation in ('missing', 'tampered', 'symlink-file', 'symlink-directory', 'fifo', 'oversized'):
            with self.subTest(mutation=mutation), routed_fixture() as (root, route):
                receipts.write_receipt(root, 'verification', 'pass', details={'captured': 'x' * receipts.MAX_RECEIPT_BYTES})
                receipt = receipts.get_receipt(root, route['route_id'], 'verification')
                artifact = root / receipt['details_reference']['path']
                content = artifact.read_bytes()
                if mutation == 'missing':
                    artifact.unlink()
                elif mutation == 'tampered':
                    artifact.write_bytes(content.replace(b'xxxx', b'yyyy', 1))
                elif mutation == 'symlink-file':
                    saved = artifact.with_suffix('.saved')
                    artifact.rename(saved)
                    artifact.symlink_to(saved)
                elif mutation == 'symlink-directory':
                    saved = artifact.parent.with_name('saved-reports')
                    artifact.parent.rename(saved)
                    artifact.parent.symlink_to(saved, target_is_directory=True)
                elif mutation == 'fifo':
                    artifact.unlink()
                    os.mkfifo(artifact)
                else:
                    artifact.write_bytes(b'x' * (receipts.MAX_VERIFICATION_REPORT_BYTES + 1))
                with self.assertRaises(RuntimeError):
                    receipts.get_receipt(root, route['route_id'], 'verification')
                gaps = receipts.validate_evidence(root, {**route, 'required_evidence': ['verification']})
                self.assertTrue(any('unsafe receipt' in gap for gap in gaps), gaps)

    def test_spilled_report_reference_and_all_envelope_bindings_are_closed(self):
        with routed_fixture() as (root, route):
            path = receipts.write_receipt(root, 'verification', 'pass', details={'captured': 'x' * receipts.MAX_RECEIPT_BYTES})
            original = json.loads(path.read_bytes())
            changes = [('path', '../outside.json'), ('sha256', 'f' * 64), ('bytes', True), ('bytes', 0), ('bytes', original['details']['_verification_report']['bytes'] + 1), ('contract', 'unknown'), ('extra', 'unknown')]
            for field, value in changes:
                with self.subTest(reference=field, value=value):
                    envelope = json.loads(json.dumps(original))
                    envelope['details']['_verification_report'][field] = value
                    path.write_text(json.dumps(envelope), encoding='utf-8')
                    with self.assertRaises(RuntimeError):
                        receipts.get_receipt(root, route['route_id'], 'verification')
            for field in ('route_id', 'kind', 'status', 'git_head', 'tree_fingerprint', 'criterion_ids', 'spec_digest', 'spec_fingerprint', 'architecture_digest', 'governance_digest'):
                with self.subTest(binding=field):
                    envelope = json.loads(json.dumps(original))
                    envelope[field] = ['AC-999'] if field == 'criterion_ids' else 'tampered'
                    path.write_text(json.dumps(envelope), encoding='utf-8')
                    with self.assertRaisesRegex(RuntimeError, 'binding does not match'):
                        receipts.get_receipt(root, route['route_id'], 'verification')
            path.write_text(json.dumps(original), encoding='utf-8')
            receipts.invalidate_receipts(root, route['route_id'], 'explicit invalidation')
            self.assertTrue(receipts.get_receipt(root, route['route_id'], 'verification')['stale'])
            self.assertTrue(any('explicitly invalidated' in gap for gap in receipts.validate_evidence(root, {**route, 'required_evidence': ['verification']})))
            self.assertLessEqual(path.stat().st_size, receipts.MAX_RECEIPT_BYTES)

    def test_spilled_report_rejects_invalid_json_even_with_matching_hash(self):
        for content in (b'{"schema_version":1,"schema_version":1}', b'{"schema_version":NaN}', b'[]', b'{"schema_version":1}'):
            with self.subTest(content=content), routed_fixture() as (root, route):
                path = receipts.write_receipt(root, 'verification', 'pass', details={'captured': 'x' * receipts.MAX_RECEIPT_BYTES})
                envelope = json.loads(path.read_bytes())
                reference = envelope['details']['_verification_report']
                digest = hashlib.sha256(content).hexdigest()
                reference.update(sha256=digest, bytes=len(content), path=f'.grok-stack/runtime/receipts/{route["route_id"]}/reports/{digest}.json')
                (root / reference['path']).write_bytes(content)
                path.write_text(json.dumps(envelope), encoding='utf-8')
                with self.assertRaises(RuntimeError):
                    receipts.get_receipt(root, route['route_id'], 'verification')

    def test_spilled_report_publication_faults_retire_prior_pass(self):
        for boundary in ('write', 'link', 'file-fsync', 'directory-fsync', 'cancel', 'post-rename-cancel'):
            with self.subTest(boundary=boundary), routed_fixture() as (root, route):
                receipts.write_receipt(root, 'verification', 'pass')
                original_fsync = receipts.os.fsync
                original_link = receipts.os.link
                report_renamed = False
                def observe_link(*args, **kwargs):
                    nonlocal report_renamed
                    result = original_link(*args, **kwargs)
                    if 'src_dir_fd' in kwargs:
                        report_renamed = True
                    return result
                def fsync_fault(fd):
                    mode = os.fstat(fd).st_mode
                    if boundary == 'file-fsync' and stat.S_ISREG(mode):
                        raise OSError('report file fsync fault')
                    if boundary == 'directory-fsync' and report_renamed and stat.S_ISDIR(mode):
                        raise OSError('report directory fsync fault')
                    return original_fsync(fd)
                def cancel():
                    if boundary == 'cancel' or report_renamed:
                        raise RuntimeError('report publication cancelled')
                fault = (patch.object(receipts, '_write_receipt_bytes', side_effect=OSError('report write fault'))
                         if boundary == 'write' else patch.object(receipts.os, 'link', side_effect=OSError('report publication fault'))
                         if boundary == 'link' else patch.object(receipts.os, 'fsync', side_effect=fsync_fault))
                observer = contextlib.nullcontext() if boundary == 'link' else patch.object(receipts.os, 'link', side_effect=observe_link)
                with fault, observer, self.assertRaises((OSError, RuntimeError)):
                    receipts.write_receipt(root, 'verification', 'pass', details={'captured': 'x' * receipts.MAX_RECEIPT_BYTES}, interrupt_check=cancel if boundary in ('cancel', 'post-rename-cancel') else None)
                self.assertIsNone(receipts.get_receipt(root, route['route_id'], 'verification'))
                self.assertFalse(list((root / '.grok-stack/runtime/receipts').rglob('*.tmp')))
                self.assertFalse(list((root / '.grok-stack/runtime/receipts').rglob('reports/*.json')))

    def test_verification_classification_serialization_faults_retire_prior_pass(self):
        for failure, error in (('circular', ValueError), ('unserializable', TypeError)):
            with self.subTest(failure=failure), routed_fixture() as (root, route):
                route['required_evidence'] = ['verification']
                set_active_route(root, route)
                receipts.write_receipt(root, 'verification', 'pass')
                self.assertEqual(receipts.validate_evidence(root, route), [])
                details = {}
                details['bad'] = details if failure == 'circular' else object()
                with self.assertRaises(error):
                    receipts.write_receipt(root, 'verification', 'pass', details=details)
                self.assertIsNone(receipts.get_receipt(root, route['route_id'], 'verification'))
                self.assertEqual(receipts.validate_evidence(root, route), ['verification: missing receipt'])
                self.assertFalse(list((root / '.grok-stack/runtime/receipts').rglob('*.tmp')))
                self.assertFalse(list((root / '.grok-stack/runtime/receipts').rglob('reports/*.json')))

    def test_report_publication_rejects_symlink_directory_without_external_write(self):
        with routed_fixture() as (root, route):
            receipts.write_receipt(root, 'verification', 'pass')
            outside = root / 'outside-reports'
            outside.mkdir()
            before = util.tree_fingerprint(root)
            (receipts.receipt_dir(root, route['route_id']) / 'reports').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(OSError):
                receipts.write_receipt(root, 'verification', 'pass', details={'captured': 'x' * receipts.MAX_RECEIPT_BYTES})
            self.assertEqual(list(outside.iterdir()), [])
            self.assertEqual(util.tree_fingerprint(root), before)
            self.assertIsNone(receipts.get_receipt(root, route['route_id'], 'verification'))

    def test_report_publication_rechecks_source_before_receipt(self):
        with routed_fixture() as (root, route):
            receipts.write_receipt(root, 'verification', 'pass')
            fingerprint = util.tree_fingerprint(root)
            def mutate():
                (root / 'VERSION').write_text('changed during publication\n', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'changed while verification report'):
                receipts.write_receipt(root, 'verification', 'pass', details={'captured': 'x' * receipts.MAX_RECEIPT_BYTES}, expected_tree_fingerprint=fingerprint, interrupt_check=mutate)
            self.assertIsNone(receipts.get_receipt(root, route['route_id'], 'verification'))

    def test_spilled_report_preserves_failed_cancelled_and_skipped_results(self):
        with routed_fixture() as (root, route):
            details = {'status': 'fail', 'terminal_state': 'cancelled', 'checks': [verifier.CheckResult(status, status, 'original result', stdout='x' * 12000).to_dict() for status in ('pass', 'fail', 'skip', 'cancelled')], 'captured': 'x' * receipts.MAX_RECEIPT_BYTES}
            receipts.write_receipt(root, 'verification', 'fail', details=details)
            receipt = receipts.get_receipt(root, route['route_id'], 'verification')
            self.assertEqual(receipt['status'], 'fail')
            self.assertEqual(receipt['details'], details)
            self.assertTrue(any('status=fail' in gap for gap in receipts.validate_evidence(root, {**route, 'required_evidence': ['verification']})))

    def test_other_receipt_kinds_do_not_spill(self):
        with routed_fixture() as (root, route):
            for kind in sorted(receipts.RECEIPT_KINDS - {'verification'}):
                with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'receipt exceeds the byte limit'):
                    receipts.write_receipt(root, kind, 'pass', details={'captured': 'x' * receipts.MAX_RECEIPT_BYTES})
            self.assertFalse(list((root / '.grok-stack/runtime/receipts').rglob('reports/*.json')))

    def test_same_tree_new_head_invalidates_receipt(self):
        with routed_fixture() as (root, route):
            receipt_route = {**route, 'required_evidence': ['verification']}
            receipts.write_receipt(root, 'verification', 'pass')
            self.assertEqual(receipts.validate_evidence(root, receipt_route), [])
            subprocess.run(['git', 'commit', '--allow-empty', '-qm', 'new exact head'], cwd=root, check=True)
            self.assertTrue(any('head' in gap for gap in receipts.validate_evidence(root, receipt_route)))

    def test_faults_never_leave_a_valid_pass_or_partial_receipt(self):
        for boundary in ('write', 'replace', 'file-fsync', 'directory-fsync'):
            with self.subTest(boundary=boundary), routed_fixture() as (root, route):
                receipts.write_receipt(root, 'verification', 'pass')
                original_fsync = receipts.os.fsync
                calls = 0

                def fsync_fault(fd):
                    nonlocal calls
                    calls += 1
                    if (boundary == 'file-fsync' and calls == 1) or (boundary == 'directory-fsync' and calls == 2):
                        raise OSError('durability fault')
                    return original_fsync(fd)

                target = receipts.receipt_dir(root, route['route_id']) / 'verification.json'
                fault = (patch.object(receipts, '_write_receipt_bytes', side_effect=OSError('write fault'), create=True)
                         if boundary == 'write' else patch.object(receipts.os, 'replace', side_effect=OSError('rename fault'))
                         if boundary == 'replace' else patch.object(receipts.os, 'fsync', side_effect=fsync_fault))
                with fault:
                    with self.assertRaises(OSError):
                        receipts.write_receipt(root, 'verification', 'pass')
                self.assertFalse(target.exists())
                self.assertFalse(list(target.parent.glob('.verification.json.*')))

    def test_receipt_binds_head_scope_inventory_and_terminal_state(self):
        with routed_fixture() as (root, route), patch.object(verifier, '_python', return_value=[]):
            report = verifier.verify(root, mode='fast')
            receipt = receipts.get_receipt(root, route['route_id'], 'verification')
            expected_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
            self.assertEqual(receipt['git_head'], expected_head)
            self.assertEqual(receipt['details']['terminal_state'], 'completed')
            self.assertEqual(receipt['details']['docs_state_scope'], report['docs_state_scope'])
            self.assertEqual(receipt['details']['checks'], report['checks'])
            self.assertEqual(receipt['tree_fingerprint'], report['tree_fingerprint'])
