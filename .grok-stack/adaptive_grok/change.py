from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path
from typing import Any

from .package_status import collect_worktree, read_package_file
from .state import active_route_path, get_active_route, route_id_block_reason, set_active_change, update_route
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
MAX_PACKAGE_ID_CHARS = 128
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
ABSOLUTE_PATH_TITLE = re.compile(r'^(?:~?/+)(?:[^/\s]+/+){1,}[^/\s]+(?:[/\s]|$)')
# Names the derived id can never produce (it always starts with eight digits), but a
# caller-supplied ``change_id`` can, and a Windows checkout could not read them back.
# `nul` is the one reserved Windows name that needs no extension: `nul`, `nul.txt` and
# `nul .txt` all address the device, and `con`/`prn`/`aux` are already covered.
RESERVED_WINDOWS_NAMES = re.compile(
    r'^(?:con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?$', re.IGNORECASE
)
PACKAGE_ID_PATTERN = re.compile(
    r'^[0-9]{8}-[A-Za-z0-9\u0400-\u04FF][A-Za-z0-9._\u0400-\u04FF-]{1,119}'
    r'[A-Za-z0-9_\u0400-\u04FF-]$'
)


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
        elif not char.isprintable():
            escape = 'u' if code <= 0xffff else 'U'
            width = 4 if code <= 0xffff else 8
            rendered.append(f'\\{escape}{code:0{width}x}')
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
        if not (
            char.isascii() and char.isalnum()
            or '\u0400' <= char <= '\u04ff'
            or char in ALLOWED_COMPONENT_PUNCTUATION
        ):
            return f'contains the unusable character {quoted_value(char)}'
    if len(change_id.encode('utf-8')) > MAX_COMPONENT_BYTES:
        return f'is longer than the {MAX_COMPONENT_BYTES}-byte filesystem component limit'
    if change_id[-1] in '. ' or RESERVED_WINDOWS_NAMES.match(change_id):
        return 'is a name a Windows host cannot create'
    return None


def package_id_block_reason(change_id: Any) -> str | None:
    """Return why a safe component still cannot be a persisted package identity."""
    reason = change_id_block_reason(change_id)
    if reason:
        return reason
    if len(change_id) > MAX_PACKAGE_ID_CHARS or not PACKAGE_ID_PATTERN.fullmatch(change_id):
        return 'does not match the persisted change-package identity contract'
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
    for char in title:
        if char not in '\t\n\r' and not char.isprintable():
            return f'contains the non-printable character {quoted_value(char)}'
    drive = DRIVE_PREFIX.search(title)
    if drive:
        return f'contains the drive prefix {quoted_value(drive.group())}'
    absolute = ABSOLUTE_PATH_TITLE.match(title.strip())
    if absolute:
        return 'is an absolute path: a filesystem location was handed where a summary belongs'
    return None


def route_payload_block_reason(
    value: Any,
    path: str = 'route',
) -> tuple[str, str] | None:
    """Find text or types that cannot safely reach route-backed templates and JSON."""
    if isinstance(value, str):
        for char in value:
            code = ord(char)
            if char in '\t\n\r':
                continue
            if code < 0x20 or code == 0x7f or 0x80 <= code <= 0x9f:
                return char, f'active route field {path} contains a control byte'
            if not char.isprintable():
                return char, f'active route field {path} contains a Unicode non-printable'
        return None
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                return repr(key), f'active route object {path} has a non-text key'
            key_path = f'{path}[{quoted_value(key)}]'
            blocked = route_payload_block_reason(key, f'{key_path} key')
            if blocked:
                return blocked
            blocked = route_payload_block_reason(item, key_path)
            if blocked:
                return blocked
        return None
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            blocked = route_payload_block_reason(item, f'{path}[{index}]')
            if blocked:
                return blocked
        return None
    if value is None or isinstance(value, (bool, int)):
        return None
    if isinstance(value, float):
        if math.isfinite(value):
            return None
        return repr(value), f'active route field {path} is not a finite JSON number'
    return repr(value), f'active route field {path} has unsupported type {type(value).__name__}'


def route_shape_block_reason(route: Any) -> tuple[str, str] | None:
    """Validate the field shapes consumed after scaffolding, before scaffolding starts."""
    if not isinstance(route, dict):
        return repr(route), 'active route is not a JSON object'
    for field in ('task', 'risk', 'complexity'):
        value = route.get(field)
        if not isinstance(value, str):
            return repr(value), f"active route field route['{field}'] is not text"
    for field, required in (
        ('domains', True),
        ('required_evidence', False),
        ('human_gates', False),
    ):
        if field not in route and not required:
            continue
        value = route.get(field)
        if not isinstance(value, list):
            return repr(value), f"active route field route['{field}'] is not a list"
        for index, item in enumerate(value):
            if not isinstance(item, str):
                return repr(item), f"active route field route['{field}'][{index}] is not text"
    for field in ('route_id', 'created_at'):
        if field not in route:
            return '<missing>', f"active route field route['{field}'] is missing"
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
    created_date = created_at[:10].replace('-', '')
    if re.fullmatch(r'[0-9]{8}', created_date) is None:
        _refuse(
            'build a change package from an unsafe created_at date',
            created_date,
            'is not an eight-digit calendar-date component',
        )
    components = (
        ('created_at date', created_date),
        ('title slug', slugify(title)),
        ('route id prefix', route_id[:6]),
    )
    for label, value in components:
        reason = change_id_block_reason(value)
        if reason:
            _refuse(f'build a change package from an unsafe {label}', value, reason)
    route_reason = route_id_block_reason(route_id)
    if route_reason:
        _refuse('build a change package from an unsafe route id', route_id, route_reason)
    change_id = '-'.join(value for _label, value in components)
    reason = package_id_block_reason(change_id)
    if reason:
        _refuse('name a change package', change_id, reason)
    return change_id


def package_dir(root: Path, change_id: Any) -> Path:
    """Resolve a package directory, failing closed unless it stays under the packages root."""
    reason = package_id_block_reason(change_id)
    if reason:
        _refuse('open change package', str(change_id), reason)
    try:
        expected_base = root.resolve() / PACKAGES_RELATIVE
        base = (root / PACKAGES_RELATIVE).resolve()
    except (OSError, RuntimeError) as exc:
        _refuse('open change package', change_id, f'package root cannot be resolved ({type(exc).__name__})')
    if base != expected_base:
        _refuse(
            'open change package',
            change_id,
            'package root resolves outside its declared repository location',
        )
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
    if route is None:
        if active_route_path(root).exists():
            _refuse(
                'create a change package from active route data',
                '<active-route.json>',
                'persisted active route is not a JSON object',
            )
        raise RuntimeError('No active route. Submit a development task or run scripts/grok_route.py first.')
    blocked_shape = route_shape_block_reason(route)
    if blocked_shape:
        value, reason = blocked_shape
        _refuse('create a change package from active route data', value, reason)
    title = title or route['task']
    reason = title_block_reason(title)
    if reason:
        _refuse('create a change package from title', str(title), reason)
    change_id = _derive_change_id(route['created_at'], title, route['route_id'])
    blocked_route = route_payload_block_reason(route)
    if blocked_route:
        value, reason = blocked_route
        _refuse('create a change package from active route data', value, reason)
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
