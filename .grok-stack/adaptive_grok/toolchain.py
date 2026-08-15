from __future__ import annotations

import platform
import re
from dataclasses import dataclass, field
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


def check_tool(spec: dict[str, Any], *, host: str | None = None) -> ToolCheck:
    tool_id = str(spec.get('id') or 'tool')
    name = str(spec.get('name') or tool_id)
    required = bool(spec.get('required'))
    minimum = str(spec.get('minimum') or '')
    built = str(spec.get('built') or '')
    fallback = str(spec.get('fallback') or minimum or built)
    install = install_command(spec, host)
    command, found = detect_command(spec)
    offer = (
        f'Install fallback {name} {fallback} (or newer, built on {built}): {install}'
        if install else f'Install fallback {name} {fallback} (or newer, built on {built})'
    )
    if not command:
        return ToolCheck(
            id=tool_id,
            name=name,
            status='fail' if required else 'info',
            message=(
                f'missing; required>={minimum} (built {built}); {offer}'
                if required else
                f'not installed; optional for {spec.get("profile") or "matching profiles"}; '
                f'required>={minimum} if used (built {built}); {offer}'
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
            message=f'{command} {found} < minimum {minimum} (built {built}); {offer}',
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
        message=f'{command} {found or "present"} (>= {minimum}, built {built}){extra}',
        required=required,
        found=found,
        command=command,
        minimum=minimum,
        built=built,
        fallback=fallback,
        install=install,
        offer=None,
    )


def check_toolchain(root: Path, *, host: str | None = None) -> list[ToolCheck]:
    data = load_toolchain(root)
    return [check_tool(spec, host=host) for spec in data.get('tools') or [] if isinstance(spec, dict)]


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
    """Install missing/old tools. URLs are never executed; they stay manual."""

    def default_runner(command: str):
        return run(['bash', '-lc', command], cwd=root, timeout=600)

    execute = runner or default_runner
    results: list[dict[str, Any]] = []
    for tool in check_toolchain(root, host=host):
        if tool.status == 'pass':
            continue
        if not tool.required and not include_optional:
            results.append({'id': tool.id, 'action': 'skip-optional', 'ok': True, 'command': tool.install})
            continue
        if not apply:
            results.append({'id': tool.id, 'action': 'skip-disabled', 'ok': True, 'command': tool.install})
            continue
        if dry_run:
            results.append({'id': tool.id, 'action': 'would-install', 'ok': True, 'command': tool.install})
            continue
        if not tool.install:
            results.append({'id': tool.id, 'action': 'manual', 'ok': False, 'command': None})
            continue
        if is_manual_url(tool.install):
            results.append({'id': tool.id, 'action': 'manual-url', 'ok': False, 'command': tool.install})
            continue
        proc = execute(tool.install)
        code = getattr(proc, 'returncode', 1)
        results.append({'id': tool.id, 'action': 'install', 'ok': code == 0, 'command': tool.install, 'code': code})
    return results
