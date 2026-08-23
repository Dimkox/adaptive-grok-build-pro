from __future__ import annotations

import importlib.metadata
import importlib.util
import platform
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .util import command_exists, load_json, run

VERSION_RE = re.compile(r'(\d+(?:\.\d+){0,3})')


@dataclass
class ToolCheck:
    id: str
    name: str
    status: str
    message: str
    required: bool
    found: str | None = None
    command: str | None = None
    minimum: str | None = None
    built: str | None = None
    fallback: str | None = None
    install: str | None = None
    offer: str | None = None


def parse_version(text: str) -> str | None:
    match = VERSION_RE.search(text or '')
    return match.group(1) if match else None


def version_tuple(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for item in value.split('.'):
        if not item.isdigit():
            break
        parts.append(int(item))
    return tuple(parts or (0,))


def version_meets(found: str, minimum: str) -> bool:
    return version_tuple(found) >= version_tuple(minimum)


def install_platform() -> str:
    system = platform.system().lower()
    if system.startswith('linux'):
        return 'linux'
    if system == 'darwin':
        return 'darwin'
    if system == 'windows':
        return 'windows'
    return 'generic'


def install_command(spec: dict[str, Any], host: str | None = None) -> str:
    table = spec.get('install') or {}
    key = host or install_platform()
    return str(table.get(key) or table.get('generic') or '')


def is_manual_url(command: str | None) -> bool:
    """HTTP(S) pins are documentation, never a shell payload."""
    lowered = (command or '').strip().lower()
    return lowered.startswith('http://') or lowered.startswith('https://')


def load_toolchain(root: Path) -> dict[str, Any]:
    data = load_json(root / '.grok-stack/config/toolchain.json', {}) or {}
    return data if isinstance(data, dict) else {}


def detect_command(spec: dict[str, Any]) -> tuple[str | None, str | None]:
    for name in spec.get('commands') or []:
        if not command_exists(str(name)):
            continue
        args = [str(name), *list(spec.get('version_args') or ['--version'])]
        proc = run(args, cwd=Path.cwd(), timeout=10)
        text = (proc.stdout or '') + '\n' + (proc.stderr or '')
        version = parse_version(text)
        return str(name), version
    return None, None


def _offer(
    name: str,
    fallback: str,
    built: str,
    install: str,
) -> str:
    prefix = f'Install fallback {name} {fallback} (or newer, built on {built})'
    return f'{prefix}: {install}' if install else prefix


def check_tool(spec: dict[str, Any], *, host: str | None = None) -> ToolCheck:
    tool_id = str(spec.get('id') or 'tool')
    name = str(spec.get('name') or tool_id)
    required = bool(spec.get('required'))
    minimum = str(spec.get('minimum') or '')
    built = str(spec.get('built') or '')
    fallback = str(spec.get('fallback') or minimum or built)
    install = install_command(spec, host)
    command, found = detect_command(spec)
    offer = _offer(name, fallback, built, install)
    if not command:
        return ToolCheck(
            id=tool_id,
            name=name,
            status='fail' if required else 'info',
            message=(
                f'missing; required>={minimum} (built {built}); {offer}'
                if required
                else (
                    'not installed; optional for '
                    f'{spec.get("profile") or "matching profiles"}; '
                    f'required>={minimum} if used (built {built}); {offer}'
                )
            ),
            required=required,
            minimum=minimum,
            built=built,
            fallback=fallback,
            install=install,
            offer=offer,
        )
    if found and minimum and not version_meets(found, minimum):
        return ToolCheck(
            id=tool_id,
            name=name,
            status='fail' if required else 'info',
            message=(
                f'{command} {found} < minimum {minimum} '
                f'(built {built}); {offer}'
            ),
            required=required,
            found=found,
            command=command,
            minimum=minimum,
            built=built,
            fallback=fallback,
            install=install,
            offer=offer,
        )
    extra = ''
    if found and built and version_tuple(found) < version_tuple(built):
        extra = f'; older than built pin {built}, still supported'
    return ToolCheck(
        id=tool_id,
        name=name,
        status='pass',
        message=(
            f'{command} {found or "present"} '
            f'(>= {minimum}, built {built}){extra}'
        ),
        required=required,
        found=found,
        command=command,
        minimum=minimum,
        built=built,
        fallback=fallback,
        install=install,
        offer=None,
    )


def check_python_module(
    spec: dict[str, Any],
    *,
    host: str | None = None,
    version_info: tuple[int, ...] | None = None,
    module_available: bool | None = None,
    found_version: str | None = None,
) -> ToolCheck | None:
    """Check a conditional Python backport declared in toolchain.json."""
    threshold = str(spec.get('required_below_python') or '')
    current = tuple(version_info or sys.version_info[:3])
    if threshold and current >= version_tuple(threshold):
        return None

    tool_id = str(spec.get('id') or spec.get('module') or 'python-module')
    module = str(spec.get('module') or tool_id)
    name = str(spec.get('name') or module)
    required = bool(spec.get('required', True))
    minimum = str(spec.get('minimum') or '')
    built = str(spec.get('built') or '')
    fallback = str(spec.get('fallback') or minimum or built)
    install = install_command(spec, host).replace(
        '{python}',
        shlex.quote(sys.executable),
    )
    offer = _offer(name, fallback, built, install)

    available = (
        importlib.util.find_spec(module) is not None
        if module_available is None
        else module_available
    )
    if not available:
        return ToolCheck(
            id=tool_id,
            name=name,
            status='fail' if required else 'info',
            message=(
                f'missing Python module {module}; required>={minimum} '
                f'for Python < {threshold}; {offer}'
            ),
            required=required,
            minimum=minimum,
            built=built,
            fallback=fallback,
            install=install,
            offer=offer,
        )

    found = found_version
    if found is None:
        try:
            found = importlib.metadata.version(module)
        except importlib.metadata.PackageNotFoundError:
            found = None
    if found and minimum and not version_meets(found, minimum):
        return ToolCheck(
            id=tool_id,
            name=name,
            status='fail' if required else 'info',
            message=(
                f'Python module {module} {found} < minimum {minimum}; {offer}'
            ),
            required=required,
            found=found,
            command=f'python module {module}',
            minimum=minimum,
            built=built,
            fallback=fallback,
            install=install,
            offer=offer,
        )
    return ToolCheck(
        id=tool_id,
        name=name,
        status='pass',
        message=(
            f'Python module {module} {found or "present"} '
            f'(>= {minimum}, built {built})'
        ),
        required=required,
        found=found,
        command=f'python module {module}',
        minimum=minimum,
        built=built,
        fallback=fallback,
        install=install,
        offer=None,
    )


def check_toolchain(root: Path, *, host: str | None = None) -> list[ToolCheck]:
    data = load_toolchain(root)
    checks = [
        check_tool(spec, host=host)
        for spec in data.get('tools') or []
        if isinstance(spec, dict)
    ]
    for spec in data.get('python_modules') or []:
        if not isinstance(spec, dict):
            continue
        result = check_python_module(spec, host=host)
        if result is not None:
            checks.append(result)
    return checks


def offer_install_lines(checks: list[ToolCheck]) -> list[str]:
    lines: list[str] = []
    for item in checks:
        if item.offer and item.status != 'pass':
            lines.append(f'{item.id}: {item.offer}')
    return lines


def pull_dependencies(
    root: Path,
    *,
    apply: bool,
    include_optional: bool,
    dry_run: bool,
    host: str | None = None,
    runner=None,
) -> list[dict[str, Any]]:
    """Install missing or old tools; URLs remain manual references."""

    def default_runner(command: str):
        return run(['bash', '-lc', command], cwd=root, timeout=600)

    execute = runner or default_runner
    results: list[dict[str, Any]] = []
    for tool in check_toolchain(root, host=host):
        if tool.status == 'pass':
            continue
        if not tool.required and not include_optional:
            results.append(
                {
                    'id': tool.id,
                    'action': 'skip-optional',
                    'ok': True,
                    'command': tool.install,
                }
            )
            continue
        if not apply:
            results.append(
                {
                    'id': tool.id,
                    'action': 'skip-disabled',
                    'ok': True,
                    'command': tool.install,
                }
            )
            continue
        if dry_run:
            results.append(
                {
                    'id': tool.id,
                    'action': 'would-install',
                    'ok': True,
                    'command': tool.install,
                }
            )
            continue
        if not tool.install:
            results.append(
                {
                    'id': tool.id,
                    'action': 'manual',
                    'ok': False,
                    'command': None,
                }
            )
            continue
        if is_manual_url(tool.install):
            results.append(
                {
                    'id': tool.id,
                    'action': 'manual-url',
                    'ok': False,
                    'command': tool.install,
                }
            )
            continue
        proc = execute(tool.install)
        code = getattr(proc, 'returncode', 1)
        results.append(
            {
                'id': tool.id,
                'action': 'install',
                'ok': code == 0,
                'command': tool.install,
                'code': code,
            }
        )
    return results
