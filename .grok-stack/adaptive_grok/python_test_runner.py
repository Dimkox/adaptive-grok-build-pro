"""Isolated Core and Trust CI test sharding; local verification evidence only."""
from __future__ import annotations

import argparse
import configparser
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import metadata
import importlib.util
import json
import os
import re
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time

from ._cpu_capacity import linux_quota_capacity


PINS = {'pytest': '9.1.1', 'pytest-xdist': '3.8.0', 'pytest-cov': '7.1.0', 'coverage': '7.15.4'}
CONFIG = '.grok-test-runner.json'
TIMEOUT = 900
OUTPUT_LIMIT = 2 * 1024 * 1024


class RunnerError(ValueError):
    pass


def _closed_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RunnerError('duplicate test runner configuration key')
        result[key] = value
    return result


def selected_workers(root: Path) -> int | None:
    """No opt-in means the existing consumer runner remains authoritative."""
    path = root / CONFIG
    value: object = None
    if path.exists() or path.is_symlink():
        try:
            attributes = path.stat()
            if path.is_symlink() or not stat.S_ISREG(attributes.st_mode) or attributes.st_size > 4096:
                raise RunnerError('invalid test runner configuration file')
            config = json.loads(path.read_text(), object_pairs_hook=_closed_object)
            if not isinstance(config, dict) or set(config) != {'schema_version', 'workers'}:
                raise RunnerError('test runner configuration requires schema_version and workers')
            if type(config['schema_version']) is not int or config['schema_version'] != 1:
                raise RunnerError('unsupported test runner schema_version')
            value = config['workers']
            if value != 'auto' and (type(value) is not int or not 0 <= value <= 64):
                raise RunnerError('workers must be auto or an integer from 0 to 64')
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RunnerError('unreadable test runner configuration') from exc
    override = os.environ.get('GROK_TEST_WORKERS')
    if override is not None:
        if override != 'auto' and (not override.isascii() or not override.isdecimal() or len(override) > 2):
            raise RunnerError('GROK_TEST_WORKERS must be auto or an integer from 0 to 64')
        value = override if override == 'auto' else int(override)
        if value != 'auto' and value > 64:
            raise RunnerError('GROK_TEST_WORKERS exceeds 64')
    if value is None:
        return None
    if os.environ.get('_GROK_TEST_CHILD') == '1':
        return 0
    if value == 'auto':
        if os.name != 'posix':
            return 0
        try:
            available = len(os.sched_getaffinity(0))
        except (AttributeError, OSError):
            available = 0
        if available <= 0:
            available = os.cpu_count() or 1
        selected = min(28, max(1, available))
        if sys.platform == 'linux':
            quota = linux_quota_capacity()
            if quota is not None:
                selected = min(selected, quota)
        return selected
    return int(value)


@dataclass
class ProcessResult:
    command: list[str]
    returncode: int
    stdout: str = ''
    stderr: str = ''
    seconds: float = 0.0
    terminal_state: str = 'completed'
    cleanup_error: str = ''


class RunCancelled(SystemExit):
    """Signal exit with the last owned child's result still available."""

    def __init__(self, number: int, result: ProcessResult | None = None):
        super().__init__(128 + number)
        self.signal_number = number
        self.result = result
        self.checks: list[object] = []


@dataclass
class Cancellation:
    signal_number: int | None = None

    def __call__(self) -> int | None:
        return self.signal_number

    def check(self, result: ProcessResult | None = None) -> None:
        if self.signal_number is not None:
            if result is not None:
                result.terminal_state = 'cancelled'
            raise RunCancelled(self.signal_number, result)


_active_cancellation: Cancellation | None = None
_TERM_GRACE = 0.25
_KILL_REAP_TIMEOUT = 2.0


@dataclass
class CoreTestRun:
    tests: ProcessResult
    coverage: ProcessResult | None
    workers: int
    versions: dict[str, str]
    coverage_metadata: dict[str, object]


def _stop(process: subprocess.Popen) -> None:
    """Stop only the new session created by execute; repeated calls are safe."""
    if os.name == 'posix':
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        else:
            # Also terminate descendants when their group leader already exited.
            deadline = time.monotonic() + _TERM_GRACE
            while time.monotonic() < deadline:
                process.poll()
                try:
                    os.killpg(process.pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.01)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    elif process.poll() is None:
        process.kill()
    try:
        process.wait(timeout=_KILL_REAP_TIMEOUT)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=_KILL_REAP_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise RunnerError('owned process refused to exit after SIGKILL') from None


@contextmanager
def _cancellation():
    global _active_cancellation
    if threading.current_thread() is not threading.main_thread():
        raise RunnerError('test process ownership requires the main thread')
    if _active_cancellation is not None:
        yield _active_cancellation
        return
    cancellation = Cancellation()
    previous = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}

    def cancel(signum, frame):
        if cancellation.signal_number is None:
            cancellation.signal_number = signum

    for number in previous:
        signal.signal(number, cancel)
    _active_cancellation = cancellation
    try:
        yield cancellation
    finally:
        _active_cancellation = None
        for number, handler in previous.items():
            signal.signal(number, handler)


@contextmanager
def _output_file(retained: dict[str, ProcessResult], label: str, cancellation: Cancellation):
    """Close each output file without replacing a result or primary exception."""
    manager = tempfile.TemporaryFile()
    handle = manager.__enter__()
    primary: BaseException | None = None
    try:
        yield handle
    except BaseException as exc:
        primary = exc
        raise
    finally:
        try:
            manager.__exit__(type(primary) if primary else None, primary,
                             primary.__traceback__ if primary else None)
        except Exception as cleanup:
            diagnostic = f'{label} output cleanup failed: {type(cleanup).__name__}: {cleanup}'[:512]
            result = retained.get('result')
            if result is None and isinstance(primary, RunCancelled):
                result = primary.result
            if result is not None:
                result.cleanup_error = '; '.join(filter(None, (result.cleanup_error, diagnostic)))
            elif primary is None:
                raise
            if primary is not None:
                primary.add_note(diagnostic)
        if primary is None and retained.get('result') is not None:
            cancellation.check(retained['result'])


def execute(command: list[str], root: Path, environment: dict[str, str], *, timeout: int = TIMEOUT) -> ProcessResult:
    """Bound output and stop this invocation's process group on interruption."""
    started = time.monotonic()
    retained: dict[str, ProcessResult] = {}
    with _cancellation() as cancelled, _output_file(retained, 'stdout', cancelled) as stdout, \
            _output_file(retained, 'stderr', cancelled) as stderr:
        cancelled.check(ProcessResult(command, 128 + (cancelled() or 0), terminal_state='cancelled'))
        try:
            process = subprocess.Popen(
                command, cwd=root, env=environment, stdout=stdout, stderr=stderr,
                start_new_session=os.name == 'posix',
            )
        except OSError as exc:
            result = ProcessResult(command, 127, stderr=str(exc))
            retained['result'] = result
            return result
        reason = ''
        cleanup_error = ''
        try:
            while process.poll() is None:
                if cancelled():
                    reason = f'test process cancelled by {signal.Signals(cancelled()).name}'
                    break
                elif time.monotonic() - started > timeout:
                    reason = 'test process timeout'
                elif os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size > OUTPUT_LIMIT:
                    reason = 'test process output limit exceeded'
                if reason:
                    break
                time.sleep(0.05)
        except BaseException as exc:
            try:
                _stop(process)
            except Exception as cleanup:
                exc.add_note(f'owned process cleanup failed: {cleanup}')
            raise
        original_returncode = process.returncode
        try:
            _stop(process)
        except Exception as exc:
            cleanup_error = f'{type(exc).__name__}: {exc}'[:512]
        if os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size > OUTPUT_LIMIT:
            reason = 'test process output limit exceeded'
        stdout.seek(0)
        stderr.seek(0)
        out = stdout.read(OUTPUT_LIMIT).decode('utf-8', errors='backslashreplace')
        err = stderr.read(OUTPUT_LIMIT).decode('utf-8', errors='backslashreplace')
        code = original_returncode if original_returncode is not None else process.returncode
        if cancelled():
            code = code if original_returncode is not None else 128 + cancelled()
        elif reason:
            code = 124
        if code is None:
            code = 1
        result = ProcessResult(command, code, out, err + reason, time.monotonic() - started,
                               'timeout' if reason == 'test process timeout' else 'completed', cleanup_error)
        retained['result'] = result
        cancelled.check(result)
        return result


def _environment(root: Path, data_file: Path) -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith(('PYTEST_', 'COVERAGE_', 'COV_CORE_')) and key != 'GROK_TEST_WORKERS'
    }
    environment.update(
        PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONDONTWRITEBYTECODE='1',
        _GROK_TEST_CHILD='1', COVERAGE_FILE=str(data_file),
        PYTHONPATH=os.pathsep.join((str(root), str(root / 'tests'), str(root / '.grok-stack'), environment.get('PYTHONPATH', ''))),
    )
    return environment


def run_named_tests(root: Path, targets: list[str], *, budget: int = 180) -> ProcessResult:
    """Run explicit Core unittest names as a bounded observation, without coverage."""
    if type(budget) is not int or not 1 <= budget <= 180:
        raise RunnerError('named test budget must be an integer from 1 to 180 seconds')
    if not targets or any(
        not isinstance(target, str)
        or not re.fullmatch(r'tests\.test_[A-Za-z0-9_]+(?:\.[A-Za-z_][A-Za-z0-9_]*){0,2}', target)
        or not (root / 'tests' / (target.split('.')[1] + '.py')).is_file()
        for target in targets
    ):
        raise RunnerError('named tests require nonempty existing tests.test_module[.Class[.test_method]] targets')
    with tempfile.TemporaryDirectory(prefix='grok-named-smoke-') as directory:
        return execute([sys.executable, '-m', 'unittest', *targets], root,
                       _environment(root, Path(directory) / '.coverage'), timeout=budget)


def _tool_versions(required: list[str]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in required:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError as exc:
            raise RunnerError(f'{name} missing; install .grok-stack/config/python-test-requirements.txt with this Python') from exc
        if versions[name] != PINS[name]:
            raise RunnerError(f'{name} requires tested version {PINS[name]}; found {versions[name]}')
    return versions


def parallel_engine_ready(measured: bool) -> bool:
    """Every module the xdist engine needs, importable by THIS interpreter."""
    modules = ("pytest", "xdist", *(("pytest_cov",) if measured else ()))
    return all(importlib.util.find_spec(name) is not None for name in modules)


def _parallel_process_cleanup_supported() -> bool:
    """Whether this host can safely own and clean up the parallel process group."""
    return os.name == 'posix'


def select_engine(workers: int, measured: bool) -> tuple[int, str]:
    """Capability-selected engine: xdist only when importable and safely cleanable.

    Retake of closed defect 33: the Trust CI runner image has no pytest, so a
    requested-parallel run must degrade to one disclosed sequential unittest
    pass before execution, never after a failure, and never claim the parallel
    backend it did not use.
    """
    if workers > 0 and measured and not parallel_engine_ready(measured) and _parallel_process_cleanup_supported():
        return workers, "coverage-unittest-parallel"
    if workers > 0 and (
        not parallel_engine_ready(measured) or not _parallel_process_cleanup_supported()
    ):
        return 0, "unittest-degraded"
    if workers > 0:
        return workers, "pytest-xdist"
    return 0, "unittest"


def _pytest_command(workers: int, distribution: str) -> list[str]:
    if os.name != 'posix':
        raise RunnerError('parallel process cleanup requires POSIX; use GROK_TEST_WORKERS=0')
    return [sys.executable, '-m', 'pytest', '-c', os.devnull, '-p', 'xdist.plugin', '-p', 'no:cacheprovider',
            '--import-mode=prepend', '--rootdir=.', '-o', 'python_files=test*.py', '-q', '-n', str(workers),
            f'--dist={distribution}', '--max-worker-restart=0', '--durations=20', '-ra']


def _unittest_files(root: Path) -> list[str]:
    tests = root / 'tests'
    return [path.name for path in sorted(tests.glob('test*.py')) if path.is_file()]


def _read_limited(path: Path) -> str:
    try:
        with path.open('rb') as handle:
            return handle.read(OUTPUT_LIMIT).decode('utf-8', errors='backslashreplace')
    except OSError as exc:
        return f'{type(exc).__name__}: {exc}'


def _parallel_coverage_unittest(root: Path, config: Path, data_file: Path, workers: int, environment: dict[str, str]) -> ProcessResult:
    test_files = _unittest_files(root)
    command = [
        sys.executable, '-m', 'coverage', 'run', '--parallel-mode', f'--rcfile={config}',
        '-m', 'unittest', 'discover', '-s', 'tests', '-p', '<test-file>',
    ]
    if not test_files:
        return ProcessResult(command, 5, stderr='no unittest modules discovered')
    started = time.monotonic()
    active: list[tuple[str, subprocess.Popen, Path, Path]] = []
    completed: list[ProcessResult] = []
    cleanup_errors: list[str] = []
    next_file = 0
    workers = max(1, min(workers, len(test_files)))
    with _cancellation() as cancelled, tempfile.TemporaryDirectory(prefix='grok-core-parallel-') as out_dir:
        output_root = Path(out_dir)
        try:
            while next_file < len(test_files) or active:
                cancelled.check()
                while next_file < len(test_files) and len(active) < workers:
                    test_file = test_files[next_file]
                    next_file += 1
                    stdout = output_root / f'{test_file}.stdout'
                    stderr = output_root / f'{test_file}.stderr'
                    out_handle = stdout.open('wb')
                    err_handle = stderr.open('wb')
                    try:
                        process = subprocess.Popen(
                            [
                                sys.executable, '-m', 'coverage', 'run', '--parallel-mode',
                                f'--rcfile={config}', '-m', 'unittest', 'discover',
                                '-s', 'tests', '-p', test_file,
                            ],
                            cwd=root,
                            env={**environment, '_GROK_TEST_CHILD': '1'},
                            stdout=out_handle,
                            stderr=err_handle,
                            start_new_session=True,
                        )
                    except OSError as exc:
                        out_handle.close()
                        err_handle.close()
                        completed.append(ProcessResult(command, 127, stderr=f'{test_file}: {exc}'))
                        continue
                    out_handle.close()
                    err_handle.close()
                    active.append((test_file, process, stdout, stderr))
                for item in list(active):
                    test_file, process, stdout, stderr = item
                    if process.poll() is None:
                        continue
                    active.remove(item)
                    completed.append(ProcessResult(
                        [
                            sys.executable, '-m', 'coverage', 'run', '--parallel-mode',
                            f'--rcfile={config}', '-m', 'unittest', 'discover',
                            '-s', 'tests', '-p', test_file,
                        ],
                        process.returncode if process.returncode is not None else 1,
                        stdout=_read_limited(stdout),
                        stderr=_read_limited(stderr),
                    ))
                if time.monotonic() - started > TIMEOUT:
                    for _test_file, process, _stdout, _stderr in active:
                        _stop(process)
                    return ProcessResult(command, 124, stderr='parallel coverage unittest timeout',
                                         seconds=time.monotonic() - started, terminal_state='timeout')
                if active:
                    time.sleep(0.05)
        except BaseException:
            for test_file, process, _stdout, _stderr in active:
                try:
                    _stop(process)
                except Exception as exc:
                    cleanup_errors.append(f'{test_file}: {type(exc).__name__}: {exc}'[:256])
            raise
    failed = [result for result in completed if result.returncode != 0]
    stdout = ''.join(result.stdout[-4000:] for result in failed[-20:])
    stderr = ''.join(result.stderr[-4000:] for result in failed[-20:])
    if failed:
        return ProcessResult(command, failed[0].returncode, stdout=stdout, stderr=stderr,
                             seconds=time.monotonic() - started)
    combine = execute(
        [sys.executable, '-m', 'coverage', 'combine', f'--rcfile={config}', str(data_file.parent)],
        root,
        environment,
        timeout=120,
    )
    return ProcessResult(command, combine.returncode, stdout=combine.stdout, stderr=combine.stderr,
                         seconds=time.monotonic() - started,
                         cleanup_error=combine.cleanup_error)


@contextmanager
def _run_directory(prefix: str, retained: dict[str, ProcessResult]):
    """Cleanup cannot replace a completed test verdict or a signal exception."""
    directory = tempfile.TemporaryDirectory(prefix=prefix)
    primary: BaseException | None = None
    try:
        yield directory.name
    except BaseException as exc:
        primary = exc
        raise
    finally:
        try:
            directory.cleanup()
        except Exception as cleanup:
            result = retained.get('tests')
            if result is not None:
                result.cleanup_error = f'{type(cleanup).__name__}: {cleanup}'[:512]
            elif isinstance(primary, RunCancelled) and primary.result is not None:
                primary.result.cleanup_error = f'{type(cleanup).__name__}: {cleanup}'[:512]
            elif primary is None:
                raise
            if primary is not None:
                primary.add_note(f'coverage scratch cleanup failed: {cleanup}')


def run_core_tests(root: Path, mode: str, workers: int) -> CoreTestRun:
    measured = mode in {'pr', 'release'}
    workers, engine = select_engine(workers, measured)
    if engine == 'pytest-xdist':
        version_requirements = list(PINS)
    elif measured:
        version_requirements = ['coverage']
    else:
        version_requirements = []
    versions = _tool_versions(version_requirements)
    versions['engine'] = engine
    config = root / '.coveragerc'
    if measured and not config.is_file():
        raise RunnerError('required .coveragerc is missing')
    retained: dict[str, ProcessResult] = {}
    with _run_directory('grok-core-coverage-', retained) as directory:
        data_file = Path(directory) / '.coverage'
        report_file = Path(directory) / 'coverage.json'
        environment = _environment(root, data_file)
        if workers and engine == 'pytest-xdist':
            command = _pytest_command(workers, 'worksteal')
            if measured:
                command += ['-p', 'pytest_cov.plugin', '--cov', f'--cov-config={config}', '--cov-report=term']
            command += ['tests']
        elif workers and engine == 'coverage-unittest-parallel':
            command = [
                sys.executable, '-m', 'coverage', 'run', '--parallel-mode', f'--rcfile={config}',
                '-m', 'unittest', '<module>',
            ]
        else:
            command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests']
            if measured:
                command = [sys.executable, '-m', 'coverage', 'run', f'--rcfile={config}', *command[1:]]
        if workers and engine == 'coverage-unittest-parallel':
            tests = _parallel_coverage_unittest(root, config, data_file, workers, environment)
        else:
            tests = execute(command, root, environment)
        retained['tests'] = tests
        coverage = None
        facts: dict[str, object] = {}
        if measured:
            coverage_command = [sys.executable, '-m', 'coverage', 'report', f'--rcfile={config}']
            if not data_file.is_file():
                coverage = ProcessResult(coverage_command, 1, stderr='current run produced no coverage data')
            else:
                try:
                    coverage = execute(coverage_command, root, environment, timeout=120)
                    exported = execute([sys.executable, '-m', 'coverage', 'json', f'--rcfile={config}', '-o', str(report_file)], root, environment, timeout=120)
                except RunCancelled as exc:
                    exc.core_run = CoreTestRun(tests, exc.result, workers, versions, facts)
                    raise
                try:
                    document = json.loads(report_file.read_text())
                    settings = configparser.ConfigParser()
                    settings.read(config)
                    expected_branch = settings.getboolean('run', 'branch', fallback=False)
                    if (not isinstance(document, dict)
                            or not isinstance(document.get('files'), dict) or not document['files']
                            or not isinstance(document.get('meta'), dict)
                            or type(document['meta'].get('branch_coverage')) is not bool
                            or document['meta']['branch_coverage'] != expected_branch
                            or not isinstance(document.get('totals'), dict)):
                        raise ValueError('coverage source or branch data missing')
                    facts = {'totals': document['totals'], 'branch_coverage': expected_branch, 'files': sorted(document['files'])}
                except (OSError, ValueError, TypeError, KeyError, configparser.Error) as exc:
                    coverage.returncode = 1
                    coverage.stderr += f'\ninvalid current-run coverage: {exc}'
                if exported.returncode or tests.returncode or 'failed to return coverage data' in tests.stdout + tests.stderr:
                    coverage.returncode = 1
                    coverage.stderr += '\ncoverage does not qualify an unsuccessful or incomplete test run'
        return CoreTestRun(tests, coverage, workers, versions, facts)


def run_trust_tests(root: Path, workers: int) -> ProcessResult:
    """Keep Trust imports and database test methods in their own suite/process."""
    suite = root / 'trust-ci'
    if not (suite / 'tests').is_dir():
        raise RunnerError('trust-ci/tests is missing')
    workers, _engine = select_engine(workers, measured=False)
    _tool_versions(['pytest', 'pytest-xdist'] if workers else [])
    command = (_pytest_command(workers, 'loadfile') + ['tests']) if workers else [
        sys.executable, '-m', 'unittest', 'discover', '-s', 'tests',
    ]
    with tempfile.TemporaryDirectory(prefix='grok-trust-tests-') as directory:
        environment = _environment(suite, Path(directory) / '.coverage')
        environment['PYTHONPATH'] = os.pathsep.join(str(path) for path in (suite / 'src', suite / 'tests', suite))
        return execute(command, suite, environment)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=['trust-ci'], required=True)
    parser.parse_args()
    try:
        root = Path.cwd().resolve()
        requested = selected_workers(root) or 0
        workers, engine = select_engine(requested, measured=False)
        result = run_trust_tests(root, requested)
    except RunnerError as exc:
        print(f'Trust CI tests failed: {exc}', file=sys.stderr)
        return 1
    print(f'Trust CI: requested_workers={requested}; workers={workers}; engine={engine}; '
          f'seconds={result.seconds:.3f}; exit={result.returncode}')
    print(result.stdout, end='')
    print(result.stderr, end='', file=sys.stderr)
    if result.cleanup_error:
        print(f'owned test cleanup failed: {result.cleanup_error}', file=sys.stderr)
        return 1
    return result.returncode if result.returncode >= 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
