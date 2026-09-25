from __future__ import annotations

import json
import re
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

# A change package is exactly one directory component under this root.  Issue #53:
# a caller once handed a literal Windows path to the writer and the tree grew a
# directory named ``C:\Users\…``, leaking a host username into a public repository.
PACKAGES_RELATIVE = Path('engineering/changes')
MAX_COMPONENT_BYTES = 255
ALLOWED_COMPONENT_PUNCTUATION = '-._'
MAX_REFUSAL_ECHO_CHARS = 160
# Tab, newline and carriage return are ordinary whitespace in pasted or multi-line task
# prose; every other C0, DEL and C1 byte is a control byte that must never reach a name.
TITLE_CONTROL_BYTES = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')
# ``https://`` is prose; a standalone ``D:/`` or ``C:\`` is a path handed to a title.
DRIVE_PREFIX = re.compile(r'(?<![0-9A-Za-z])[A-Za-z]:[\\/]')
# A title that *is* a POSIX absolute path (two or more segments) leaks the host layout into
# the public package name the same way ``C:\Users\…`` did; a bare ``/goal``-style command
# word, a relative ``scripts/grok_verify.py`` mention or prose that merely contains such a
# path later on does not.
ABSOLUTE_PATH_TITLE = re.compile(r'^(?:~?/[A-Za-z0-9._-]+){2,}(?:[/\s]|$)')
# Names the derived id can never produce (it always starts with eight digits), but a
# caller-supplied ``change_id`` can, and a Windows checkout could not read them back.
RESERVED_WINDOWS_NAMES = re.compile(r'^(?:con|prn|aux|com[0-9]|lpt[0-9])(?:\..*)?$', re.IGNORECASE)


def printable_value(value: str, limit: int = MAX_REFUSAL_ECHO_CHARS) -> str:
    """Render hostile text inside a refusal message without emitting control bytes.

    Non-ASCII stays visible (historical package names are Cyrillic and must remain
    readable); only bytes a terminal would act on are escaped.  The echo is bounded so a
    long prompt — which may carry a credential — cannot be copied wholesale to stderr.
    """
    clipped = value if len(value) <= limit else value[:limit] + '…[truncated]'
    rendered: list[str] = []
    for char in clipped:
        code = ord(char)
        if char == '\n':
            rendered.append('\\n')
        elif char == '\r':
            rendered.append('\\r')
        elif char == '\t':
            rendered.append('\\t')
        elif code < 0x20 or code == 0x7f or 0x80 <= code <= 0x9f:
            rendered.append(f'\\x{code:02x}')
        else:
            rendered.append(char)
    return ''.join(rendered)


def quoted_value(value: str) -> str:
    """A refusal message token: quoted, printable and bounded by ``printable_value`` alone."""
    return f"'{printable_value(value)}'"


def change_id_block_reason(change_id: Any) -> str | None:
    """Return why ``change_id`` cannot name one package directory, or ``None`` when it can."""
    if not isinstance(change_id, str) or not change_id:
        return 'is not a non-empty string'
    if change_id != change_id.strip():
        return 'starts or ends with whitespace'
    if set(change_id) <= {'.'}:
        return 'is a directory traversal marker'
    if change_id[0] == '-':
        # A name starting with a dash is eaten by option parsers in front of it.
        return 'starts with a dash'
    for char in change_id:
        code = ord(char)
        if char in '/\\':
            return f'contains the path separator {quoted_value(char)}'
        if char == ':':
            return "contains ':' (a drive or alternate-stream prefix)"
        if code < 0x20 or code == 0x7f or 0x80 <= code <= 0x9f:
            return f'contains control byte \\x{code:02x}'
        if not (char.isalnum() or char in ALLOWED_COMPONENT_PUNCTUATION):
            return f'contains the unusable character {quoted_value(char)}'
    if len(change_id.encode('utf-8')) > MAX_COMPONENT_BYTES:
        return f'is longer than the {MAX_COMPONENT_BYTES}-byte filesystem component limit'
    if change_id[-1] in '. ' or RESERVED_WINDOWS_NAMES.match(change_id):
        return 'is a name a Windows host cannot create'
    return None


def title_block_reason(title: Any) -> str | None:
    """Refuse a title that is a filesystem path rather than a summary (issue #53).

    Silently slugging such input would hide the writer bug that produced it and embed the
    host username in the public tree.  A colon or a forward slash inside ordinary prose stays
    allowed: ``slugify`` cannot turn them into a traversal, so refusing them would only break
    task text such as ``fix: see scripts/grok_verify.py``.
    """
    if not isinstance(title, str) or not title.strip():
        return 'is not a non-empty string'
    if '\\' in title:
        return 'contains a backslash: a filesystem path was handed where a summary belongs'
    control = TITLE_CONTROL_BYTES.search(title)
    if control:
        return f'contains control byte \\x{ord(control.group()):02x}'
    drive = DRIVE_PREFIX.search(title)
    if drive:
        return f'contains the drive prefix {quoted_value(drive.group())}'
    absolute = ABSOLUTE_PATH_TITLE.match(title.strip())
    if absolute:
        return 'is an absolute path: a filesystem location was handed where a summary belongs'
    return None


def _refuse(what: str, value: str, reason: str) -> None:
    raise ValueError(
        f'refusing to {what} {quoted_value(value)}: it {reason}. '
        'A change package is one directory component under '
        f'{PACKAGES_RELATIVE.as_posix()}/, named from a summary, never a path.'
    )


def _derive_change_id(created_at: Any, title: str, route_id: Any) -> str:
    for label, value in (('created_at', created_at), ('route_id', route_id)):
        if not isinstance(value, str):
            _refuse(f'build a change package from a route {label}', repr(value), 'is not text')
    components = (
        ('created_at date', created_at[:10].replace('-', '')),
        ('title slug', slugify(title)),
        ('route id prefix', route_id[:6]),
    )
    for label, value in components:
        reason = change_id_block_reason(value)
        if reason:
            _refuse(f'build a change package from an unsafe {label}', value, reason)
    change_id = '-'.join(value for _label, value in components)
    reason = change_id_block_reason(change_id)
    if reason:
        _refuse('name a change package', change_id, reason)
    return change_id


def package_dir(root: Path, change_id: Any) -> Path:
    """Resolve a package directory, failing closed unless it stays under the packages root."""
    reason = change_id_block_reason(change_id)
    if reason:
        _refuse('open change package', str(change_id), reason)
    base = (root / PACKAGES_RELATIVE).resolve()
    candidate = root / PACKAGES_RELATIVE / change_id
    try:
        resolved = candidate.resolve()
    except (OSError, RuntimeError) as exc:
        # A symlink loop or an unreadable parent must not answer with a traceback that
        # prints the absolute host path — the leak issue #53 is about.
        _refuse('open change package', change_id, f'cannot be resolved ({type(exc).__name__})')
    if resolved.parent != base:
        _refuse('open change package', change_id, 'resolves outside the packages directory')
    return candidate


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
    reason = title_block_reason(title)
    if reason:
        _refuse('create a change package from title', str(title), reason)
    change_id = _derive_change_id(route['created_at'], title, route['route_id'])
    path = package_dir(root, change_id)
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
    path = package_dir(root, change_id) / 'state.json'
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
