from __future__ import annotations

import json
import re
import shutil
import unicodedata
from pathlib import Path
from typing import Any

from .state import get_active_route, set_active_change, update_route
from .spec import dump_canonical_spec, generate_spec
from .util import dump_json, now_utc

_CYRILLIC_ASCII = str.maketrans({
    **dict(zip('абвгдезийклмнопрстуфхцчшщъыьэюя', 'abvgdeziyklmnoprstufhcyshshyyeyuya')),
    **dict(zip('АБВГДЕЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'ABVGDEZIYKLMNOPRSTUFHCYSHSHYYEYUYA')),
    'ё': 'e', 'Ё': 'E', 'ж': 'zh', 'Ж': 'Zh', 'й': 'y', 'Й': 'Y',
    'х': 'kh', 'Х': 'Kh', 'ц': 'ts', 'Ц': 'Ts', 'ч': 'ch', 'Ч': 'Ch',
    'ш': 'sh', 'Ш': 'Sh', 'щ': 'shch', 'Щ': 'Shch', 'ю': 'yu', 'Ю': 'Yu',
    'я': 'ya', 'Я': 'Ya', 'ъ': '', 'Ъ': '', 'ь': '', 'Ь': '',
})

_SENSITIVE_SLUG_PARTS = (
    re.compile(r'(?i)\b(?:bearer|token|api[_ -]?key|secret|password|passwd)\s*[:=]?\s*[^\s,;]+'),
    re.compile(r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'),
    re.compile(r'(?i)\bhttps?://[^\s,;]+'),
)


def _safe_path_slug(value: str, *, max_length: int = 28) -> str:
    """Return a readable English/ASCII slug without common secret-like values."""
    for pattern in _SENSITIVE_SLUG_PARTS:
        value = pattern.sub(' ', value)
    value = value.translate(_CYRILLIC_ASCII)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^A-Za-z0-9]+', '-', value).strip('-').lower()
    return value[:max_length].rstrip('-') or 'change'


def _change_path_id(route: dict[str, Any], title: str) -> str:
    created = str(route.get('created_at', ''))[:10]
    date = re.fullmatch(r'\d{4}-\d{2}-\d{2}', created)
    date_part = created.replace('-', '') if date else '00000000'
    intent = _safe_path_slug(str(route.get('intent', 'change')), max_length=12)
    route_id = str(route.get('route_id', ''))
    route_part = route_id if re.fullmatch(r'[0-9a-fA-F]{12}', route_id) else '000000000000'
    summary = _safe_path_slug(title, max_length=28)
    return f'{date_part}-{summary}-{intent}-{route_part}'[:64].rstrip('-')

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
    change_id = _change_path_id(route, title)
    path = root / 'engineering/changes' / change_id
    if path.exists():
        state = json.loads((path / 'state.json').read_text(encoding='utf-8'))
        existing_route = path / 'route.json'
        existing_route_id = None
        if existing_route.is_file():
            try:
                existing_route_id = json.loads(existing_route.read_text(encoding='utf-8')).get('route_id')
            except (OSError, UnicodeError, json.JSONDecodeError):
                existing_route_id = None
        if existing_route_id != route.get('route_id'):
            raise FileExistsError(f'change-package ID collision with a different route: {change_id}')
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
