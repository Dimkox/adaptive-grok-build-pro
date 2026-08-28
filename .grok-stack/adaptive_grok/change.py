from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .state import get_active_route, set_active_change, update_route
from .spec import dump_canonical_spec, generate_spec
from .util import dump_json, now_utc, slugify

GOVERNANCE_AUTHORITY_NOTICE = (
    "Canonical governance JSON under `governance/` remains separately reviewed "
    "authority. Any rule, example, debt, or digest named here is non-authoritative "
    "context until the verifier rederives current governance evidence."
)

TRANSITIONS = {
    'draft': {'scoped', 'cancelled'},
    'scoped': {'approved', 'draft', 'cancelled'},
    'approved': {'implementing', 'cancelled'},
    'implementing': {'verifying', 'blocked', 'cancelled'},
    'blocked': {'implementing', 'cancelled'},
    'verifying': {'reviewing', 'implementing', 'blocked'},
    'reviewing': {'ready', 'implementing', 'blocked'},
    'ready': {'released', 'implementing'},
    'released': {'archived'},
    'archived': set(),
    'cancelled': set(),
}


def start_change(root: Path, title: str | None = None) -> dict[str, Any]:
    route = get_active_route(root)
    if not route:
        raise RuntimeError('No active route. Submit a development task or run scripts/grok_route.py first.')
    title = title or route['task']
    change_id = f"{route['created_at'][:10].replace('-', '')}-{slugify(title)}-{route['route_id'][:6]}"
    path = root / 'engineering/changes' / change_id
    if path.exists():
        state = json.loads((path / 'state.json').read_text(encoding='utf-8'))
        set_active_change(root, {'change_id': change_id, 'path': path.relative_to(root).as_posix()})
        return state
    template = root / '.grok-stack/templates/change'
    shutil.copytree(template, path)
    generated_route = {**route, 'change_id': change_id}
    (path / 'change-spec.yaml').write_text(
        dump_canonical_spec(generate_spec(generated_route)),
        encoding='utf-8',
    )
    replacements = {
        '{{CHANGE_ID}}': change_id,
        '{{TITLE}}': title,
        '{{TASK}}': route['task'],
        '{{CREATED_AT}}': now_utc(),
        '{{RISK}}': route['risk'],
        '{{COMPLEXITY}}': route['complexity'],
        '{{DOMAINS}}': ', '.join(route['domains']),
        '{{GOVERNANCE_AUTHORITY_NOTICE}}': GOVERNANCE_AUTHORITY_NOTICE,
    }
    for file in path.rglob('*'):
        if file.is_file():
            if file.name == 'change-spec.yaml':
                continue
            try:
                content = file.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                continue
            for key, value in replacements.items():
                content = content.replace(key, str(value))
            file.write_text(content, encoding='utf-8')
    dump_json(path / 'route.json', route)
    state = {
        'schema_version': 1,
        'change_id': change_id,
        'title': title,
        'route_id': route['route_id'],
        'status': 'draft',
        'created_at': now_utc(),
        'updated_at': now_utc(),
        'history': [{'from': None, 'to': 'draft', 'at': now_utc(), 'reason': 'created'}],
    }
    dump_json(path / 'state.json', state)
    set_active_change(root, {'change_id': change_id, 'path': path.relative_to(root).as_posix()})
    update_route(root, change_id=change_id)
    return state


def transition(root: Path, change_id: str, target: str, reason: str) -> dict[str, Any]:
    path = root / 'engineering/changes' / change_id / 'state.json'
    if not path.is_file():
        raise FileNotFoundError(path)
    state = json.loads(path.read_text(encoding='utf-8'))
    current = state['status']
    if target not in TRANSITIONS.get(current, set()):
        raise ValueError(f'Invalid transition {current} -> {target}')
    state['status'] = target
    state['updated_at'] = now_utc()
    state.setdefault('history', []).append({'from': current, 'to': target, 'at': now_utc(), 'reason': reason})
    dump_json(path, state)
    update_route(root, status=target)
    return state
