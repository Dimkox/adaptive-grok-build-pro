"""Fault controls for the actual verifier/owned runner/receipt boundaries."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import signal
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
