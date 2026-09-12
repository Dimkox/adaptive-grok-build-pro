"""Isolated Core and Trust CI test sharding; local verification evidence only."""
from __future__ import annotations

import argparse
import configparser
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import metadata
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time


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
        available = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else (os.cpu_count() or 1)
        return min(28, max(1, available)) if os.name == 'posix' else 0
    return int(value)


@dataclass
class ProcessResult:
    command: list[str]
    returncode: int
    stdout: str = ''
    stderr: str = ''
    seconds: float = 0.0


@dataclass
class CoreTestRun:
    tests: ProcessResult
    coverage: ProcessResult | None
    workers: int
    versions: dict[str, str]
    coverage_metadata: dict[str, object]


def _stop(process: subprocess.Popen) -> None:
    if os.name == 'posix':
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.kill()
    process.wait(timeout=10)


@contextmanager
def _cancellation():
    if threading.current_thread() is not threading.main_thread():
        raise RunnerError('test process ownership requires the main thread')
    interrupted = False
    previous = signal.getsignal(signal.SIGTERM)

    def cancel(signum, frame):
        nonlocal interrupted
        interrupted = True

    signal.signal(signal.SIGTERM, cancel)
    try:
        yield lambda: interrupted
    finally:
        signal.signal(signal.SIGTERM, previous)
        if interrupted:
            raise SystemExit(128 + signal.SIGTERM)


def execute(command: list[str], root: Path, environment: dict[str, str], *, timeout: int = TIMEOUT) -> ProcessResult:
    """Bound output and stop this invocation's process group on interruption."""
    started = time.monotonic()
    with _cancellation() as cancelled, tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            process = subprocess.Popen(
                command, cwd=root, env=environment, stdout=stdout, stderr=stderr,
                start_new_session=os.name == 'posix',
            )
        except OSError as exc:
            return ProcessResult(command, 127, stderr=str(exc))
        reason = ''
        try:
            while process.poll() is None:
                if cancelled():
                    reason = 'test process cancelled by SIGTERM'
                if time.monotonic() - started > timeout:
                    reason = 'test process timeout'
                if os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size > OUTPUT_LIMIT:
                    reason = 'test process output limit exceeded'
                if reason:
                    _stop(process)
                    break
                time.sleep(0.05)
        except BaseException:
            _stop(process)
            raise
        _stop(process)
        if os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size > OUTPUT_LIMIT:
            reason = 'test process output limit exceeded'
        stdout.seek(0)
        stderr.seek(0)
        out = stdout.read(OUTPUT_LIMIT).decode('utf-8', errors='replace')
        err = stderr.read(OUTPUT_LIMIT).decode('utf-8', errors='replace')
        return ProcessResult(command, 124 if reason else process.returncode, out, err + reason, time.monotonic() - started)


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


def _pytest_command(workers: int, distribution: str) -> list[str]:
    if os.name != 'posix':
        raise RunnerError('parallel process cleanup requires POSIX; use GROK_TEST_WORKERS=0')
    return [sys.executable, '-m', 'pytest', '-c', os.devnull, '-p', 'xdist.plugin', '-p', 'no:cacheprovider',
            '--import-mode=prepend', '--rootdir=.', '-o', 'python_files=test*.py', '-q', '-n', str(workers),
            f'--dist={distribution}', '--max-worker-restart=0', '--durations=20', '-ra']


def run_core_tests(root: Path, mode: str, workers: int) -> CoreTestRun:
    measured = mode in {'pr', 'release'}
    versions = _tool_versions(list(PINS) if workers else (['coverage'] if measured else []))
    config = root / '.coveragerc'
    if measured and not config.is_file():
        raise RunnerError('required .coveragerc is missing')
    with tempfile.TemporaryDirectory(prefix='grok-core-coverage-') as directory:
        data_file = Path(directory) / '.coverage'
        report_file = Path(directory) / 'coverage.json'
        environment = _environment(root, data_file)
        if workers:
            command = _pytest_command(workers, 'worksteal')
            if measured:
                command += ['-p', 'pytest_cov.plugin', '--cov', f'--cov-config={config}', '--cov-report=term']
            command += ['tests']
        else:
            command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests']
            if measured:
                command = [sys.executable, '-m', 'coverage', 'run', f'--rcfile={config}', *command[1:]]
        tests = execute(command, root, environment)
        coverage = None
        facts: dict[str, object] = {}
        if measured:
            coverage_command = [sys.executable, '-m', 'coverage', 'report', f'--rcfile={config}']
            if not data_file.is_file():
                coverage = ProcessResult(coverage_command, 1, stderr='current run produced no coverage data')
            else:
                coverage = execute(coverage_command, root, environment, timeout=120)
                exported = execute([sys.executable, '-m', 'coverage', 'json', f'--rcfile={config}', '-o', str(report_file)], root, environment, timeout=120)
                try:
                    document = json.loads(report_file.read_text())
                    settings = configparser.ConfigParser()
                    settings.read(config)
                    expected_branch = settings.getboolean('run', 'branch', fallback=False)
                    if not document['files'] or document['meta']['branch_coverage'] != expected_branch:
                        raise ValueError('coverage source or branch data missing')
                    facts = {'totals': document['totals'], 'branch_coverage': expected_branch, 'files': sorted(document['files'])}
                except (OSError, ValueError, KeyError, configparser.Error) as exc:
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
        workers = selected_workers(root) or 0
        result = run_trust_tests(root, workers)
    except RunnerError as exc:
        print(f'Trust CI tests failed: {exc}', file=sys.stderr)
        return 1
    print(f'Trust CI: workers={workers}; seconds={result.seconds:.3f}; exit={result.returncode}')
    print(result.stdout, end='')
    print(result.stderr, end='', file=sys.stderr)
    return result.returncode if result.returncode >= 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
