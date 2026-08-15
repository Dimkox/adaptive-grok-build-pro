from __future__ import annotations

from pathlib import Path
from typing import Any

from .receipts import validate_evidence, write_receipt
from .state import get_active_change, get_active_route, has_valid_approval
from .util import git_output, load_json

ALLOWED_STATUSES = {'ready', 'released'}


def _version(root: Path) -> str:
    try:
        return (root / 'VERSION').read_text(encoding='utf-8').strip() or '0.0.0'
    except OSError:
        return '0.0.0'


def _fail(error: str) -> dict[str, Any]:
    return {'ok': False, 'error': error}


def _human_commands(root: Path, version: str) -> list[str]:
    branch = git_output(root, 'rev-parse', '--abbrev-ref', 'HEAD') or 'HEAD'
    zip_name = f'adaptive-grok-build-pro-v{version}.zip'
    return [
        'python3 scripts/package_stack.py',
        f'cp dist/{zip_name}* packages/',
        f'git tag -a v{version} -m "v{version}"',
        f'git push origin {branch}',
        f'git push origin v{version}',
        f'gh release create v{version} packages/{zip_name} packages/{zip_name}.sha256 --notes-file dist/RELEASE-NOTES.md',
    ]


def _change_state(root: Path) -> tuple[dict[str, Any] | None, str | None]:
    active = get_active_change(root)
    if not active:
        return None, None
    change_id = str(active.get('change_id') or '')
    rel = active.get('path') or (f'engineering/changes/{change_id}' if change_id else '')
    if not rel:
        return None, change_id or None
    state = load_json(root / str(rel) / 'state.json')
    if not isinstance(state, dict):
        return None, change_id or None
    return state, change_id or str(state.get('change_id') or '') or None


def prepare_deploy(root: Path, *, record: bool) -> dict[str, Any]:
    route = get_active_route(root)
    if not route:
        return _fail('no active route')
    gaps = validate_evidence(root, route)
    if gaps:
        return _fail('missing or stale evidence: ' + '; '.join(gaps))
    state, change_id = _change_state(root)
    if not state or not change_id:
        return _fail('no active change')
    status = state.get('status')
    if status not in ALLOWED_STATUSES:
        return _fail(f'change status is {status}, expected ready or released')
    version = _version(root)
    commands = _human_commands(root, version)
    if not record:
        return {
            'ok': True,
            'recorded': False,
            'commands': commands,
            'change_id': change_id,
            'version': version,
        }
    if not has_valid_approval(root, 'production'):
        return _fail('production approval required to record deploy preparation')
    write_receipt(
        root,
        'deploy',
        'prepared',
        details={'commands': commands, 'version': version, 'change_id': change_id},
    )
    return {
        'ok': True,
        'recorded': True,
        'commands': commands,
        'change_id': change_id,
        'version': version,
    }
