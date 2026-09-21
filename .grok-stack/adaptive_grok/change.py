from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .package_status import collect_worktree, read_package_file
from .state import get_active_route, set_active_change, update_route
from .spec import dump_canonical_spec, generate_spec
from .util import atomic_write_text, dump_json, now_utc, slugify

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


def _checkpoint(root: Path, route: dict[str, Any], change_id: str, kind: str) -> dict[str, Any]:
    observation = collect_worktree(root, route)
    return {
        'kind': kind,
        'change_id': change_id,
        'route_id': route['route_id'],
        'observed_at': observation['observed_at'],
        'branch': observation['branch'],
        'head': observation['head'],
        'detached': observation['detached'],
        'git_available': observation['git_available'],
        'git_findings': [item['code'] for item in observation['findings']],
        'dirty_product_state': observation['dirty_product_state'],
        'dirty_product_paths': observation['dirty_product_paths'],
        'note': 'draft; implementation not started' if kind == 'initial' else 'implementation started; preserve work before handoff',
    }


def _mirror_checkpoints(path: Path, state: dict[str, Any]) -> None:
    """State is canonical; a failed README write is explicit and retryable."""
    if not state.get('checkpoint_mirror_pending'):
        return
    readme = path / 'evidence/README.md'
    root = path.parents[2]
    content = read_package_file(root, readme.relative_to(root).as_posix()).decode('utf-8', 'strict')
    for checkpoint in state.get('checkpoints', []):
        marker = f"<!-- checkpoint:{checkpoint['kind']} -->"
        if marker in content:
            continue
        content += f"\n{marker}\n## {checkpoint['kind'].capitalize()} checkpoint\n\n"
        content += 'Local observation only; not verification or publication evidence.\n\n'
        content += '```json\n' + json.dumps(checkpoint, ensure_ascii=True, indent=2) + '\n```\n'
        if checkpoint['kind'] == 'initial':
            content += '\nInitial evidence accounting (current records are in `state.json`):\n\n```json\n'
            content += json.dumps(state['evidence_accounting'], ensure_ascii=True, indent=2) + '\n```\n'
    atomic_write_text(readme, content)
    state['checkpoint_mirror_pending'] = False
    dump_json(path / 'state.json', state)


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
        _mirror_checkpoints(path, state)
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
    from .human_gates import route_gate_digest

    human_gates = route.get('human_gates', [])
    state = {
        'schema_version': 1,
        'change_id': change_id,
        'title': title,
        'route_id': route['route_id'],
        'human_gates': human_gates,
        'human_gates_digest': route_gate_digest(route['route_id'], human_gates),
        'status': 'draft',
        'created_at': now_utc(),
        'updated_at': now_utc(),
        'history': [{'from': None, 'to': 'draft', 'at': now_utc(), 'reason': 'created'}],
        'checkpoints': [_checkpoint(root, route, change_id, 'initial')],
        'checkpoint_mirror_pending': True,
        'evidence_accounting': {
            'schema_version': 1,
            'obligations': [
                {'id': kind, 'kind': 'receipt', 'receipt_kind': kind, 'status': 'not_run', 'reason': 'implementation not started'}
                for kind in route.get('required_evidence', [])
            ],
        },
    }
    dump_json(path / 'state.json', state)
    set_active_change(root, {'change_id': change_id, 'path': path.relative_to(root).as_posix()})
    update_route(root, change_id=change_id)
    _mirror_checkpoints(path, state)
    return state


def transition(root: Path, change_id: str, target: str, reason: str) -> dict[str, Any]:
    path = root / 'engineering/changes' / change_id / 'state.json'
    if not path.is_file():
        raise FileNotFoundError(path)
    state = json.loads(path.read_text(encoding='utf-8'))
    current = state['status']
    if target == current and state.get('checkpoint_mirror_pending'):
        _mirror_checkpoints(path.parent, state)
        update_route(root, status=target)
        return state
    if target not in TRANSITIONS.get(current, set()):
        raise ValueError(f'Invalid transition {current} -> {target}')
    from .human_gates import gate_transition_block_reason

    gate_reason = gate_transition_block_reason(root, target, change_id)
    if gate_reason:
        raise ValueError(gate_reason)
    if target == 'implementing' and not any(row.get('kind') == 'implementation' for row in state.get('checkpoints', [])):
        route = get_active_route(root) or {'route_id': state.get('route_id')}
        state.setdefault('checkpoints', []).append(_checkpoint(root, route, change_id, 'implementation'))
        state['checkpoint_mirror_pending'] = True
    state['status'] = target
    state['updated_at'] = now_utc()
    state.setdefault('history', []).append({'from': current, 'to': target, 'at': now_utc(), 'reason': reason})
    dump_json(path, state)
    _mirror_checkpoints(path.parent, state)
    update_route(root, status=target)
    return state
