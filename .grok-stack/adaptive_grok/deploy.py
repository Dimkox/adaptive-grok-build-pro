from __future__ import annotations

from pathlib import Path
from typing import Any

from .receipts import validate_evidence, write_receipt
from .state import get_active_change, get_active_route
from .util import load_json

ALLOWED_STATUSES = {'ready', 'released'}


def _version(root: Path) -> str:
    try:
        return (root / 'VERSION').read_text(encoding='utf-8').strip() or '0.0.0'
    except OSError:
        return '0.0.0'


def _fail(error: str) -> dict[str, Any]:
    return {'ok': False, 'error': error}


def _human_commands(version: str) -> list[str]:
    return [
        'python3 scripts/grok_verify.py --mode release --strict --json',
        f'gh workflow run release.yml --ref main -f version={version}',
    ]


def _change_state(root: Path) -> tuple[dict[str, Any] | None, str | None]:
    active = get_active_change(root)
    if not active:
        return None, None
    change_id = str(active.get('change_id') or '')
    rel = active.get('path') or (
        f'engineering/changes/{change_id}' if change_id else ''
    )
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
    commands = _human_commands(version)
    if not record:
        return {
            'ok': True,
            'recorded': False,
            'commands': commands,
            'change_id': change_id,
            'version': version,
        }

    write_receipt(
        root,
        'deploy',
        'prepared',
        details={
            'commands': commands,
            'version': version,
            'change_id': change_id,
            'authorization': 'not-granted',
        },
    )
    return {
        'ok': True,
        'recorded': True,
        'commands': commands,
        'change_id': change_id,
        'version': version,
        'authorization': 'not-granted',
    }
