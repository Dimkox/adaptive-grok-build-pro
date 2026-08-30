from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .bitrix_checks import check_bitrix
from .receipts import write_receipt
from .state import get_active_route
from .util import changed_files, command_exists, now_utc, read_text_limited, run, tree_fingerprint


@dataclass
class CheckResult:
    name: str
    status: str
    summary: str
    command: list[str] | None = None
    stdout: str = ''
    stderr: str = ''
    duration_hint: str | None = None
    details: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _command_check(root: Path, name: str, command: list[str], timeout: int = 300) -> CheckResult:
    proc = run(command, cwd=root, timeout=timeout)
    return CheckResult(
        name=name,
        status='pass' if proc.returncode == 0 else 'fail',
        summary=f'exit={proc.returncode}',
        command=command,
        stdout=proc.stdout[-12000:],
        stderr=proc.stderr[-12000:],
    )


def _git_diff_check(root: Path) -> CheckResult:
    if not command_exists('git'):
        return CheckResult('git-diff-check', 'skip', 'git not available')
    return _command_check(root, 'git-diff-check', ['git', 'diff', '--check'], 60)


def _secret_scan(root: Path, files: list[str]) -> CheckResult:
    patterns = {
        'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
        'aws-access-key': re.compile(r'AKIA[0-9A-Z]{16}'),
        'generic-secret': re.compile(r'(?i)(?:api[_-]?key|secret|password|token)\s*[:=]\s*["\'][^"\']{12,}["\']'),
    }
    findings: list[dict[str, str]] = []
    for rel in files:
        path = root / rel
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        text = read_text_limited(path)
        for label, pattern in patterns.items():
            if pattern.search(text):
                findings.append({'severity': 'error', 'code': label, 'path': rel, 'message': 'Potential committed secret.'})
    return CheckResult('secret-scan', 'fail' if findings else 'pass', f'{len(findings)} potential secrets', details=findings)


def _php_lint(root: Path, files: list[str]) -> CheckResult:
    php_files = [rel for rel in files if rel.lower().endswith('.php') and (root / rel).is_file()]
    if not php_files:
        return CheckResult('php-lint', 'skip', 'no changed PHP files')
    if not command_exists('php'):
        return CheckResult('php-lint', 'fail', 'PHP is required to lint changed PHP files')
    failures: list[dict[str, str]] = []
    outputs: list[str] = []
    for rel in php_files:
        proc = run(['php', '-l', rel], cwd=root, timeout=30)
        outputs.append((proc.stdout + proc.stderr).strip())
        if proc.returncode != 0:
            failures.append({'severity': 'error', 'code': 'php-syntax', 'path': rel, 'message': (proc.stdout + proc.stderr).strip()})
    return CheckResult('php-lint', 'fail' if failures else 'pass', f'{len(php_files)} files linted', stdout='\n'.join(outputs[-100:]), details=failures)


def _bitrix(root: Path, files: list[str]) -> CheckResult:
    findings = check_bitrix(root, files)
    errors = [item for item in findings if item.severity == 'error']
    return CheckResult(
        'bitrix-policy',
        'fail' if errors else 'pass',
        f'{len(errors)} errors, {len(findings) - len(errors)} warnings',
        details=[item.to_dict() for item in findings],
    )


def _contracts(root: Path, files: list[str]) -> CheckResult:
    findings: list[dict[str, str]] = []
    checked = 0
    for rel in files:
        lower = rel.lower()
        path = root / rel
        if not path.is_file():
            continue
        if lower.endswith(('.json', '.schema.json')) and ('contract' in lower or 'schema' in lower):
            checked += 1
            try:
                json.loads(path.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, OSError) as exc:
                findings.append({'severity': 'error', 'code': 'invalid-json-contract', 'path': rel, 'message': str(exc)})
        if lower.endswith(('.yaml', '.yml')) and any(token in lower for token in ('openapi', 'asyncapi', 'contract')):
            checked += 1
            text = read_text_limited(path)
            try:
                json_document = json.loads(text)
            except json.JSONDecodeError:
                json_document = None
            if isinstance(json_document, dict):
                has_openapi = 'openapi' in json_document
                has_asyncapi = 'asyncapi' in json_document
                has_paths = 'paths' in json_document
                has_channels = 'channels' in json_document
            else:
                has_openapi = 'openapi:' in text
                has_asyncapi = 'asyncapi:' in text
                has_paths = 'paths:' in text
                has_channels = 'channels:' in text
            if not has_openapi and not has_asyncapi:
                findings.append({'severity': 'error', 'code': 'contract-version', 'path': rel, 'message': 'Missing openapi: or asyncapi: top-level version.'})
            if has_asyncapi and not has_channels:
                findings.append({'severity': 'error', 'code': 'asyncapi-channels', 'path': rel, 'message': 'AsyncAPI document has no channels.'})
            if has_openapi and not has_paths:
                findings.append({'severity': 'error', 'code': 'openapi-paths', 'path': rel, 'message': 'OpenAPI document has no paths.'})
    return CheckResult('contract-structure', 'fail' if findings else 'pass', f'{checked} contracts checked', details=findings)


def _sql_safety(root: Path, files: list[str]) -> CheckResult:
    findings: list[dict[str, str]] = []
    for rel in files:
        if not rel.lower().endswith(('.sql', '.php')) or not (root / rel).is_file():
            continue
        text = read_text_limited(root / rel)
        for pattern, code in [
            (r'(?i)\bDROP\s+(?:TABLE|DATABASE|SCHEMA)\b', 'destructive-ddl'),
            (r'(?i)\bTRUNCATE\s+TABLE\b', 'truncate'),
            (r'(?i)\bDELETE\s+FROM\s+\S+\s*;', 'unbounded-delete'),
            (r'(?i)\bUPDATE\s+\S+\s+SET\b(?![\s\S]*\bWHERE\b)', 'unbounded-update'),
        ]:
            if re.search(pattern, text):
                findings.append({'severity': 'error', 'code': code, 'path': rel, 'message': 'Potentially destructive or unbounded SQL requires explicit migration approval.'})
    return CheckResult('sql-safety', 'fail' if findings else 'pass', f'{len(findings)} unsafe SQL findings', details=findings)


def _composer(root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    if not (root / 'composer.json').is_file():
        return results
    if command_exists('composer'):
        results.append(_command_check(root, 'composer-validate', ['composer', 'validate', '--no-check-publish'], 120))
    else:
        results.append(CheckResult('composer-validate', 'skip', 'composer not available'))
    for name, path, args in [
        ('phpunit', 'vendor/bin/phpunit', ['vendor/bin/phpunit']),
        ('phpstan', 'vendor/bin/phpstan', ['vendor/bin/phpstan', 'analyse', '--no-progress']),
        ('phpcs', 'vendor/bin/phpcs', ['vendor/bin/phpcs']),
        ('deptrac', 'vendor/bin/deptrac', ['vendor/bin/deptrac', 'analyse']),
    ]:
        if (root / path).is_file():
            results.append(_command_check(root, name, args, 600))
    return results


QUALITY_PY_PATHS = (
    '.grok-stack/adaptive_grok',
    'scripts',
    'tests',
    '.grok/hooks',
    'user_prompt_submit.py',
    'pre_tool_use.py',
    'post_tool_use.py',
    'pre_compact.py',
    'session_start.py',
    'session_end.py',
    'stop_gate.py',
    'subagent_start.py',
    'subagent_stop.py',
)

_SEMGREP_CONFIGS = ('semgrep.yaml', '.semgrep.yml', '.semgrep.yaml')
_TRIVY_FILES = ('Dockerfile', 'dockerfile', 'Containerfile')


def _existing_quality_paths(root: Path) -> list[str]:
    return [rel for rel in QUALITY_PY_PATHS if (root / rel).exists()]


def _ruff(root: Path) -> CheckResult:
    paths = _existing_quality_paths(root)
    if not paths:
        return CheckResult('ruff', 'skip', 'no python quality paths')
    if not command_exists('ruff'):
        return CheckResult('ruff', 'skip', 'ruff not available')
    return _command_check(root, 'ruff', ['ruff', 'check', *paths], 300)


def _bandit(root: Path) -> CheckResult:
    paths = [rel for rel in _existing_quality_paths(root) if rel != 'tests' and not rel.startswith('tests/')]
    if not paths:
        return CheckResult('bandit', 'skip', 'no non-test python paths')
    if not command_exists('bandit'):
        return CheckResult('bandit', 'skip', 'bandit not available')
    command = ['bandit', '-q', '-r', *paths]
    if (root / 'bandit.yaml').is_file():
        command = ['bandit', '-c', 'bandit.yaml', '-q', '-r', *paths]
    return _command_check(root, 'bandit', command, 300)


def _semgrep(root: Path) -> CheckResult | None:
    config: str | None = None
    for name in _SEMGREP_CONFIGS:
        if (root / name).is_file():
            config = name
            break
    if config is None:
        semgrep_dir = root / '.semgrep'
        if semgrep_dir.is_dir():
            try:
                next(semgrep_dir.iterdir())
            except StopIteration:
                pass
            else:
                config = '.semgrep'
    if config is None:
        return None
    if not command_exists('semgrep'):
        return CheckResult('semgrep', 'skip', 'semgrep not available')
    return _command_check(root, 'semgrep', ['semgrep', 'scan', '--error', '--config', config], 600)


def _trivy_config(root: Path) -> CheckResult | None:
    has_file = any((root / name).is_file() for name in _TRIVY_FILES)
    has_compose = bool(list(root.glob('docker-compose*.yml')) or list(root.glob('docker-compose*.yaml')))
    if not has_file and not has_compose:
        return None
    if not command_exists('trivy'):
        return CheckResult('trivy-config', 'skip', 'trivy not available')
    return _command_check(root, 'trivy-config', ['trivy', 'config', '--exit-code', '1', '.'], 600)


def _node(root: Path, mode: str) -> list[CheckResult]:
    package = root / 'package.json'
    if not package.is_file():
        return []
    try:
        scripts = json.loads(package.read_text(encoding='utf-8')).get('scripts', {})
    except (json.JSONDecodeError, OSError, AttributeError):
        return [CheckResult('package-json', 'fail', 'invalid package.json')]
    runner = 'npm' if command_exists('npm') else None
    if not runner:
        return [CheckResult('node-tooling', 'skip', 'npm not available')]
    names = ['lint', 'typecheck', 'test', 'prettier', 'format']
    if mode in {'pr', 'release'}:
        names.append('build')
    results: list[CheckResult] = []
    for name in names:
        if name in scripts:
            command = ['npm', 'run', name]
            if name == 'test':
                command.append('--')
                command.append('--runInBand') if 'jest' in str(scripts[name]) else None
            results.append(_command_check(root, f'npm-{name}', command, 900))
    return results


def _python(root: Path, mode: str = 'fast') -> list[CheckResult]:
    results: list[CheckResult] = [_ruff(root), _bandit(root)]
    has_project = any((root / item).exists() for item in ('pyproject.toml', 'requirements.txt', 'setup.py'))
    tests_dir = root / 'tests'
    has_unittest_files = tests_dir.is_dir() and any(tests_dir.glob('test*.py'))
    if has_project and command_exists('pytest') and tests_dir.is_dir():
        results.append(_command_check(root, 'pytest', ['pytest', '-q'], 900))
        if mode in {'pr', 'release'}:
            if command_exists('coverage'):
                results.append(CheckResult('coverage', 'skip', 'pytest runner owns tests; measure unittest trees only'))
            else:
                results.append(CheckResult('coverage', 'skip', 'coverage not available'))
        return results
    if has_unittest_files:
        if mode in {'pr', 'release'} and command_exists('coverage'):
            results.append(
                _command_check(
                    root,
                    'python-unittest',
                    ['coverage', 'run', '--rcfile=.coveragerc', '-m', 'unittest', 'discover', '-s', 'tests'],
                    900,
                )
            )
            results.append(
                _command_check(
                    root,
                    'coverage',
                    ['coverage', 'report', '--rcfile=.coveragerc'],
                    120,
                )
            )
        else:
            results.append(
                _command_check(
                    root,
                    'python-unittest',
                    [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'],
                    900,
                )
            )
            if mode in {'pr', 'release'}:
                results.append(CheckResult('coverage', 'skip', 'coverage not available'))
    return results


def verify(root: Path, mode: str = 'pr', profiles: list[str] | None = None, record: bool = True) -> dict[str, object]:
    route = get_active_route(root)
    active_profiles = profiles or (route.get('quality_profiles', ['base']) if route else ['base'])
    base = route.get('base_commit') if route else None
    files = changed_files(root, base)

    results: list[CheckResult] = [
        _git_diff_check(root),
        _secret_scan(root, files),
        _contracts(root, files),
        _sql_safety(root, files),
    ]
    if 'php' in active_profiles or 'bitrix' in active_profiles or any(rel.endswith('.php') for rel in files):
        results.append(_php_lint(root, files))
        results.extend(_composer(root))
    if 'bitrix' in active_profiles:
        results.append(_bitrix(root, files))
    if 'frontend' in active_profiles or (root / 'package.json').is_file():
        results.extend(_node(root, mode))
    semgrep = _semgrep(root)
    if semgrep is not None:
        results.append(semgrep)
    trivy = _trivy_config(root)
    if trivy is not None:
        results.append(trivy)
    results.extend(_python(root, mode))
    if (
        mode in {'pr', 'release'}
        and 'data' in active_profiles
        and any(path.startswith('trust-ci/') for path in files)
        and (root / 'trust-ci/scripts/verify-production-promotion.sh').is_file()
        and os.environ.get('GROK_VERIFY_CAPABILITY') != 'repository-sandbox'
    ):
        results.append(
            _command_check(
                root,
                'trust-ci-production-promotion',
                ['bash', 'trust-ci/scripts/verify-production-promotion.sh'],
                3600,
            )
        )

    failures = [result for result in results if result.status == 'fail']
    report = {
        'schema_version': 1,
        'created_at': now_utc(),
        'execution_capability': os.environ.get('GROK_VERIFY_CAPABILITY', 'trusted-host'),
        'mode': mode,
        'profiles': active_profiles,
        'route_id': route.get('route_id') if route else None,
        'tree_fingerprint': tree_fingerprint(root),
        'changed_files': files,
        'status': 'pass' if not failures else 'fail',
        'checks': [item.to_dict() for item in results],
    }
    if record and route:
        write_receipt(root, 'verification', report['status'], details=report)
    return report
