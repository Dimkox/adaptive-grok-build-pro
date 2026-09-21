"""Bounded local observations, separate from receipt and merge authority."""
from __future__ import annotations

import errno
import json
import os
import re
import stat
from datetime import datetime
from pathlib import Path
from typing import Any

from .architecture_diff import ArchitectureError, _git_command, _git_environment, _run_capped
from .receipts import RECEIPT_KINDS
from .spec import MAX_SPEC_BYTES, SpecError, _bounded_walk, _parse_canonical_json, parse_yaml_subset, validate_spec
from .util import now_utc

MAX_FILE_BYTES = 262_144
MAX_TOTAL_BYTES = 1_048_576
MAX_FILES = 64
MAX_FINDINGS = 100
MAX_DIRTY_PATHS = 256
MAX_GIT_BYTES = 262_144
MAX_FILESYSTEM_NAME_BYTES = 4096
MAX_PATH_REPRESENTATION_BYTES = 32_768
GIT_TIMEOUT_SECONDS = 2.0
PACKAGE_MARKDOWN = (
    'brief.md', 'requirements.md', 'architecture.md', 'tasks.md',
    'test-plan.md', 'release.md', 'rollback.md', 'evidence/README.md',
)
STAGES = frozenset({
    'draft', 'scoped', 'approved', 'implementing', 'blocked', 'verifying',
    'reviewing', 'ready', 'released', 'archived', 'cancelled',
})
SCOPE_STAGES = frozenset({'scoped', 'approved', 'implementing', 'verifying', 'reviewing', 'ready'})
_SHA = re.compile(r'[0-9a-f]{40}')
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}')
_CHANGE_ID = re.compile(r'[A-Za-zА-Яа-яЁё0-9][A-Za-zА-Яа-яЁё0-9_-]{0,127}')
_TEMPLATE = re.compile(
    r'\{\{(?:CHANGE_ID|TITLE|TASK|CREATED_AT|RISK|COMPLEXITY|DOMAINS|GOVERNANCE_AUTHORITY_NOTICE)\}\}'
)


class InspectionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _relative(value: Any) -> list[str]:
    if not isinstance(value, str) or not value or len(value) > 512 or '\\' in value:
        raise InspectionError('file_unsafe', 'expected a bounded repository-relative path')
    parts = value.split('/')
    if any(part in {'', '.', '..'} or any(ord(char) < 32 for char in part) for part in parts):
        raise InspectionError('file_unsafe', 'path traversal or control characters are forbidden')
    return parts


def _identity(info: os.stat_result) -> tuple[int, ...]:
    return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def read_package_file(root: Path, relative: str, limit: int = MAX_FILE_BYTES) -> bytes:
    """Open every component without following links; never block on a FIFO."""
    parts = _relative(relative)
    if any(not hasattr(os, flag) for flag in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK', 'O_CLOEXEC')):
        raise InspectionError('file_unavailable', 'safe descriptor reads are unavailable on this platform')
    if os.open not in os.supports_dir_fd:
        raise InspectionError('file_unavailable', 'descriptor-relative reads are unavailable')
    descriptors: list[int] = []
    directories: list[tuple[int, str, tuple[int, ...]]] = []
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        directory = os.open(root, flags | os.O_DIRECTORY)
        descriptors.append(directory)
        for component in parts[:-1]:
            child = os.open(component, flags | os.O_DIRECTORY, dir_fd=directory)
            descriptors.append(child)
            directories.append((directory, component, _identity(os.fstat(child))))
            directory = child
        descriptor = os.open(parts[-1], flags | os.O_NONBLOCK, dir_fd=directory)
        descriptors.append(descriptor)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise InspectionError('file_unsafe', 'selected input is not a regular file')
        if before.st_size > limit:
            raise InspectionError('file_too_large', 'selected input exceeds its byte limit')
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65_536, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > limit:
                raise InspectionError('file_too_large', 'selected input exceeds its byte limit')
        if (
            _identity(before) != _identity(os.fstat(descriptor))
            or _identity(before) != _identity(os.stat(parts[-1], dir_fd=directory, follow_symlinks=False))
            or total != before.st_size
            or any(
                identity != _identity(os.stat(name, dir_fd=parent, follow_symlinks=False))
                for parent, name, identity in directories
            )
        ):
            raise InspectionError('file_changed', 'selected input changed during the read')
        return b''.join(chunks)
    except InspectionError:
        raise
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            code, message = 'file_missing', 'selected input is missing'
        elif exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            code, message = 'file_unsafe', 'selected input has an unsafe path component'
        else:
            code, message = 'file_unavailable', 'selected input cannot be read safely'
        raise InspectionError(code, message) from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _finding(code: str, path: str, message: str, severity: str = 'error', **context: Any) -> dict[str, Any]:
    return {'code': code, 'path': path, 'message': message, 'severity': severity, **context}


def _current_lines(text: str):
    fence: tuple[str, int] | None = None
    for number, line in enumerate(text.splitlines(), 1):
        # Quoted/indented examples and fenced history are explanatory, not slots.
        if line.lstrip().startswith('>') or line.startswith(('    ', '\t')):
            continue
        stripped = line.strip()
        match = re.match(r'^(`{3,}|~{3,})', stripped)
        if fence:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= fence[1]:
                fence = None
            continue
        if match:
            fence = (match.group(1)[0], len(match.group(1)))
            continue
        # Match inline backtick runs without an unbounded regex backreference.
        plain: list[str] = []
        position = 0
        while True:
            opening = stripped.find('`', position)
            if opening < 0:
                plain.append(stripped[position:])
                break
            marker_end = opening + 1
            while marker_end < len(stripped) and stripped[marker_end] == '`':
                marker_end += 1
            closing = stripped.find(stripped[opening:marker_end], marker_end)
            if closing < 0:
                plain.append(stripped[position:])
                break
            plain.append(stripped[position:opening])
            position = closing + marker_end - opening
        yield number, ''.join(plain)


def _timestamp(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 64:
        return False
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is not None
    except ValueError:
        return False


def inspect_package(root: Path, route: dict[str, Any] | None, active: dict[str, Any] | None) -> dict[str, Any]:
    """Inspect only the selected package and explicitly referenced current records."""
    result: dict[str, Any] = {
        'observed_at': now_utc(),
        'status': 'unknown', 'stage': None, 'change_id': None, 'path': None,
        'required_stage': False, 'findings': [], 'obligations': [], 'initial_checkpoint': None,
    }
    findings = result['findings']

    def add(code: str, path: str, message: str, severity: str = 'error', **context: Any) -> None:
        if len(findings) < MAX_FINDINGS:
            findings.append(_finding(code, path, message, severity, **context))
        elif findings[-1]['code'] != 'inspection_limit':
            findings[-1] = _finding('inspection_limit', result['path'] or '', 'finding limit exceeded')

    if not active:
        add('no_active_package', '', 'no active package is selected', 'info')
        return result
    try:
        parts = _relative(active.get('path'))
        change_id = active.get('change_id')
        if len(parts) != 3 or parts[:2] != ['engineering', 'changes'] or parts[2] != change_id:
            raise InspectionError('file_unsafe', 'active package must be engineering/changes/<change-id>')
        if not isinstance(change_id, str) or not _CHANGE_ID.fullmatch(change_id):
            raise InspectionError('file_unsafe', 'active change identity is invalid')
    except InspectionError as exc:
        add(exc.code, '', str(exc))
        return result
    relative = '/'.join(parts)
    result.update(change_id=change_id, path=relative)
    cache: dict[str, bytes | None] = {}
    total_bytes = 0

    def read(name: str, limit: int = MAX_FILE_BYTES) -> bytes | None:
        nonlocal total_bytes
        if name in cache:
            return cache[name]
        if len(cache) >= MAX_FILES or total_bytes >= MAX_TOTAL_BYTES:
            add('inspection_limit', relative, 'package file or aggregate byte limit exceeded')
            return None
        cache[name] = None
        try:
            raw = read_package_file(root, f'{relative}/{name}', limit)
            total_bytes += len(raw)
            if total_bytes > MAX_TOTAL_BYTES:
                raise InspectionError('inspection_limit', 'package aggregate byte limit exceeded')
            cache[name] = raw
            return raw
        except InspectionError as exc:
            add(exc.code, f'{relative}/{name}', str(exc))
            return None

    state: dict[str, Any] = {}
    raw = read('state.json')
    if raw is not None:
        try:
            state = _parse_canonical_json(raw, Path('state.json'))
            if state.get('schema_version') != 1 or not isinstance(state.get('status'), str) or state['status'] not in STAGES:
                raise SpecError('invalid state envelope')
            result['stage'] = state['status']
            history = state.get('history', [])
            if not isinstance(history, list) or any(not isinstance(item, dict) for item in history):
                raise SpecError('invalid state history')
            result['required_stage'] = state['status'] in SCOPE_STAGES or (
                state['status'] == 'blocked' and any(isinstance(item.get('to'), str) and item['to'] in SCOPE_STAGES for item in history)
            )
            if state['status'] == 'blocked' and not result['required_stage']:
                # A legal blocked transition always follows implementation; incomplete history is not a waiver.
                result['required_stage'] = True
            if state.get('change_id') != change_id or (
                route and (state.get('route_id') != route.get('route_id') or route.get('change_id', change_id) != change_id)
            ):
                add('package_identity_mismatch', f'{relative}/state.json', 'package and route identities differ')
        except SpecError:
            add('state_invalid', f'{relative}/state.json', 'package state is malformed or has an invalid stage')
    severity = 'error' if result['required_stage'] else 'expected' if result['stage'] == 'draft' else 'warning'
    raw = read('change-spec.yaml', MAX_SPEC_BYTES)
    if raw is not None:
        try:
            try:
                spec = _parse_canonical_json(raw, Path('change-spec.yaml'))
            except SpecError:
                if raw.lstrip().startswith((b'{', b'[')):
                    raise
                spec = parse_yaml_subset(raw.decode('utf-8', 'strict'))
                _bounded_walk(spec)
                if not isinstance(spec, dict) or spec.get('schema_version') != 1:
                    raise SpecError('invalid historical spec')
            if spec.get('change_id') != change_id:
                add('package_identity_mismatch', f'{relative}/change-spec.yaml', 'specification change identity differs')
            if spec.get('schema_version') == 1:
                add('legacy_spec', f'{relative}/change-spec.yaml', 'historical spec cannot establish current typed completeness', 'warning')
            else:
                validate_spec(spec, schema_only=True)
                for field in ('success_metric', 'target'):
                    if spec['objective'][field] == 'UNKNOWN':
                        add('objective_unresolved', f'{relative}/change-spec.yaml', 'objective is not resolved', severity, field=f'objective.{field}')
                if not spec['acceptance_criteria']:
                    add('acceptance_criteria_missing', f'{relative}/change-spec.yaml', 'no typed acceptance criteria are declared', severity)
        except (SpecError, UnicodeError, OSError, RecursionError):
            add('spec_invalid', f'{relative}/change-spec.yaml', 'typed specification cannot be validated')

    checkpoints = state.get('checkpoints', [])
    invalid_checkpoints = (
        not isinstance(checkpoints, list) or len(checkpoints) > 2
        or any(
            not isinstance(row, dict) or not isinstance(row.get('kind'), str)
            or row['kind'] not in {'initial', 'implementation'}
            or row.get('change_id') != change_id or row.get('route_id') != state.get('route_id')
            or not _timestamp(row.get('observed_at'))
            or (row.get('head') is not None and (not isinstance(row['head'], str) or not _SHA.fullmatch(row['head'])))
            for row in checkpoints
        )
    )
    if invalid_checkpoints or len({row['kind'] for row in checkpoints}) != len(checkpoints):
        add('checkpoint_invalid', f'{relative}/state.json', 'checkpoint collection is invalid')
        result['initial_checkpoint'] = {'head': None}
    else:
        initial = [row for row in checkpoints if row.get('kind') == 'initial']
        if initial:
            result['initial_checkpoint'] = {'head': initial[0].get('head')}
    if state.get('checkpoint_mirror_pending'):
        add('checkpoint_mirror_pending', f'{relative}/state.json', 'canonical checkpoint awaits its evidence README mirror')

    text_files = list(PACKAGE_MARKDOWN)
    accounting = state.get('evidence_accounting')
    if accounting is None:
        add('legacy_evidence_accounting', f'{relative}/state.json', 'this package has no typed evidence accounting; no migration was performed', 'warning')
    elif (
        not isinstance(accounting, dict) or accounting.get('schema_version') != 1
        or not isinstance(accounting.get('obligations'), list) or len(accounting['obligations']) > MAX_FILES
    ):
        add('obligation_invalid', f'{relative}/state.json', 'evidence accounting must be a bounded version 1 obligation list')
    else:
        ids: set[str] = set()
        receipt_kinds: set[str] = set()
        for row in accounting['obligations']:
            try:
                if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not _ID.fullmatch(row['id']):
                    raise InspectionError('obligation_invalid', 'obligation identity is invalid')
                if row['id'] in ids or not isinstance(row.get('kind'), str) or row['kind'] not in {'receipt', 'run'}:
                    raise InspectionError('obligation_invalid', 'obligation kind or uniqueness is invalid')
                ids.add(row['id'])
                if row['kind'] == 'receipt':
                    kind = row.get('receipt_kind')
                    if not isinstance(kind, str) or kind not in RECEIPT_KINDS or kind in receipt_kinds:
                        raise InspectionError('obligation_invalid', 'receipt obligation kind is invalid or duplicated')
                    receipt_kinds.add(kind)
                result['obligations'].append({
                    key: row.get(key)
                    for key in ('id', 'kind', 'receipt_kind', 'status', 'reason', 'outcome', 'recorded_at', 'reference')
                })
                if row.get('status') == 'not_run':
                    if not isinstance(row.get('reason'), str) or not row['reason'].strip() or len(row['reason']) > 4096:
                        raise InspectionError('obligation_invalid', 'not_run requires a nonempty bounded reason')
                elif row.get('status') == 'recorded':
                    if not isinstance(row.get('outcome'), str) or row['outcome'] not in {'pass', 'fail'} or not _timestamp(row.get('recorded_at')):
                        raise InspectionError('obligation_invalid', 'recorded evidence requires an outcome and observation time')
                    command = row.get('command')
                    if row['kind'] == 'run' and (
                        not isinstance(command, list) or not 1 <= len(command) <= 32
                        or any(not isinstance(arg, str) or not arg or len(arg) > 512 for arg in command)
                    ):
                        raise InspectionError('obligation_invalid', 'a recorded run requires bounded command arguments')
                    reference = row.get('reference')
                    ref_parts = _relative(reference)
                    if (
                        not 2 <= len(ref_parts) <= 5 or ref_parts[0] != 'evidence'
                        or Path(reference).suffix not in {'.md', '.json'}
                        or any(part.startswith('.') or re.search(r'(^|[-_.])(secrets?|credentials?|private[-_]?keys?|dumps?)([-_.]|$)', part, re.I) for part in ref_parts)
                    ):
                        raise InspectionError('file_unsafe', 'evidence reference must name an allowed current package report')
                    report = read(reference)
                    if report is not None and not report.strip():
                        add('evidence_reference_empty', f'{relative}/{reference}', 'recorded evidence reference is empty')
                    if reference not in text_files:
                        text_files.append(reference)
                else:
                    raise InspectionError('obligation_invalid', 'obligation status must be not_run or recorded')
            except InspectionError as exc:
                add(exc.code, f'{relative}/state.json', str(exc), field='evidence_accounting.obligations')
        required = (route or {}).get('required_evidence', [])
        if (
            not isinstance(required, list) or len(required) > len(RECEIPT_KINDS)
            or any(not isinstance(kind, str) or kind not in RECEIPT_KINDS for kind in required)
            or len(set(required)) != len(required)
        ):
            add('obligation_invalid', f'{relative}/state.json', 'route receipt obligation list is invalid')
        else:
            for kind in sorted(set(required) - receipt_kinds):
                add('obligation_missing', f'{relative}/state.json', f'required receipt kind has no accounting: {kind}', severity)

    for name in text_files:
        raw = read(name)
        if raw is None:
            continue
        try:
            text = raw.decode('utf-8', 'strict')
        except UnicodeError:
            add('invalid_encoding', f'{relative}/{name}', 'selected text is not valid UTF-8')
            continue
        if name.endswith('.md'):
            for number, line in _current_lines(text):
                if line in {'<!--RUNTABLE-->', '- [ ] Given ..., when ..., then ...'} or _TEMPLATE.search(line):
                    add('template_unexpanded', f'{relative}/{name}', 'current template slot is unexpanded', severity, line=number)
    if any(item['severity'] == 'error' for item in findings):
        result['status'] = 'incomplete'
    elif not result['stage'] or any(item['code'] == 'legacy_spec' for item in findings):
        result['status'] = 'unknown'
    else:
        result['status'] = 'draft' if result['stage'] == 'draft' else 'complete'
    return result


def _git_read(root: Path, arguments: list[str]) -> tuple[int, bytes]:
    try:
        code, output, _ = _run_capped(
            _git_command(arguments, safe_directory=root), cwd=root,
            env=_git_environment(), stdout_limit=MAX_GIT_BYTES, stderr_limit=4096,
            timeout=GIT_TIMEOUT_SECONDS,
        )
        return code, output
    except (ArchitectureError, OSError) as exc:
        raise InspectionError('git_unavailable', 'bounded Git query failed or exceeded a limit') from exc


def _product_path(path: str) -> bool:
    parts = path.split('/')
    return not (
        path.startswith(('engineering/changes/', '.grok-stack/runtime/'))
        or any(part in {'.git', '__pycache__', '.pytest_cache', 'node_modules', 'vendor'} for part in parts)
        or path.endswith(('.pyc', '.pyo')) or path == '.coverage' or path.startswith('coverage/')
    )


def _filesystem_name(raw: bytes) -> str | dict[str, str]:
    """Preserve filename bytes without introducing forbidden JSON surrogates."""
    if not raw or len(raw) > MAX_FILESYSTEM_NAME_BYTES:
        raise InspectionError('git_name_limit', 'filesystem name exceeds the observation limit')
    try:
        return raw.decode('utf-8', 'strict')
    except UnicodeDecodeError:
        # A literal name resembling this record remains a string, so identities
        # cannot collide with escaped or replacement-character display names.
        return {'encoding': 'hex', 'value': raw.hex()}


def _dirty_paths(raw: bytes) -> list[str | dict[str, str]]:
    if raw and not raw.endswith(b'\0'):
        raise InspectionError('git_status_invalid', 'Git status output is incomplete')
    records = raw.split(b'\0')[:-1]
    paths: set[bytes] = set()
    index = 0
    count = 0
    while index < len(records):
        record = records[index]
        index += 1
        if len(record) < 4 or record[2:3] != b' ' or any(char not in b' MADRCUT?!' for char in record[:2]):
            raise InspectionError('git_status_invalid', 'Git status record is invalid')
        names = [record[3:]]
        if b'R' in record[:2] or b'C' in record[:2]:
            if index >= len(records):
                raise InspectionError('git_status_invalid', 'Git rename source is missing')
            names.append(records[index])
            index += 1
        for raw_path in names:
            count += 1
            if count > MAX_DIRTY_PATHS:
                raise InspectionError('git_status_limit', 'dirty path count exceeds the observation limit')
            path = os.fsdecode(raw_path)
            if not path or path.startswith('/') or any(part in {'', '.', '..'} for part in path.split('/')):
                raise InspectionError('git_status_invalid', 'Git emitted an invalid repository path')
            if _product_path(path):
                paths.add(raw_path)
    names: list[str | dict[str, str]] = []
    representation_bytes = 0
    for path_bytes in sorted(paths):
        name = _filesystem_name(path_bytes)
        # Bound the ASCII JSON form too: README mirrors use it, and hexadecimal
        # byte names expand. Reserve per-entry space for nested pretty printing.
        representation_bytes += len(json.dumps(name, ensure_ascii=True)) + 64
        if representation_bytes > MAX_PATH_REPRESENTATION_BYTES:
            raise InspectionError('git_path_representation_limit', 'encoded dirty paths exceed the checkpoint observation limit')
        names.append(name)
    return names


def collect_worktree(root: Path, route: dict[str, Any] | None, initial_checkpoint: dict[str, Any] | None = None) -> dict[str, Any]:
    """Observe bounded Git metadata without refreshing the index or inventing a base."""
    route_base = (route or {}).get('base_commit')
    base = initial_checkpoint.get('head') if initial_checkpoint is not None else route_base
    result: dict[str, Any] = {
        'observed_at': now_utc(), 'git_available': False, 'branch': None, 'detached': None,
        'head': None, 'route_base': route_base, 'diagnostic_base': base,
        'base_source': 'initial_checkpoint' if initial_checkpoint is not None else 'route_base',
        'commits_ahead': None, 'dirty_product_state': 'unknown', 'dirty_product_paths': [],
        'uncommitted_product_zero_ahead': None, 'findings': [],
    }

    def warn(code: str, message: str) -> None:
        result['findings'].append(_finding(code, '', message, 'warning'))

    try:
        code, output = _git_read(root, ['rev-parse', '--verify', 'HEAD^{commit}'])
        head = output.decode('ascii', 'strict').strip()
        if code or not _SHA.fullmatch(head):
            warn('git_head_unknown', 'Git repository or exact HEAD is unavailable')
            return result
        result.update(git_available=True, head=head)
        code, branch = _git_read(root, ['symbolic-ref', '--quiet', '--short', 'HEAD'])
        if code == 0 and branch.endswith(b'\n'):
            result.update(branch=_filesystem_name(branch[:-1]), detached=False)
        elif code == 1:
            result['detached'] = True
        else:
            warn('git_branch_unknown', 'current branch could not be observed')
        code, output = _git_read(root, ['status', '--porcelain=v1', '-z', '--untracked-files=all', '--ignore-submodules=all', '--renames'])
        if code:
            warn('git_status_unknown', 'working-tree status query failed')
        else:
            try:
                paths = _dirty_paths(output)
                result.update(dirty_product_paths=paths, dirty_product_state='dirty' if paths else 'clean')
            except InspectionError as exc:
                warn(exc.code, str(exc))
        if not isinstance(base, str) or not _SHA.fullmatch(base):
            warn('git_base_unknown', 'named diagnostic base is missing or invalid; no HEAD fallback was used')
        else:
            code, resolved = _git_read(root, ['rev-parse', '--verify', f'{base}^{{commit}}'])
            if code or resolved.strip() != base.encode('ascii'):
                warn('git_base_unknown', 'named diagnostic base is not an available commit')
            else:
                code, _ = _git_read(root, ['merge-base', '--is-ancestor', base, head])
                if code:
                    warn('git_base_unknown', 'named diagnostic base is not a known ancestor of HEAD')
                else:
                    code, count = _git_read(root, ['rev-list', '--count', f'{base}..{head}'])
                    if code or not re.fullmatch(rb'[0-9]{1,12}\n', count):
                        warn('git_count_unknown', 'commit count query failed or returned invalid output')
                    else:
                        result['commits_ahead'] = int(count)
        code, current = _git_read(root, ['rev-parse', '--verify', 'HEAD^{commit}'])
        if code or current.strip() != head.encode('ascii'):
            raise InspectionError('git_snapshot_changed', 'HEAD changed during the observation')
        if result['commits_ahead'] is not None and result['dirty_product_state'] != 'unknown':
            result['uncommitted_product_zero_ahead'] = result['commits_ahead'] == 0 and bool(result['dirty_product_paths'])
            if result['uncommitted_product_zero_ahead']:
                warn('uncommitted_product_zero_ahead', f"work needs a checkpoint: dirty product paths and zero commits since {result['base_source']}; interruption is only a candidate")
    except (InspectionError, UnicodeError) as exc:
        warn(exc.code if isinstance(exc, InspectionError) else 'git_output_invalid', 'Git observation is incomplete; unavailable values remain unknown')
        result.update(commits_ahead=None, dirty_product_state='unknown', uncommitted_product_zero_ahead=None)
    return result


def diagnostic_messages(package: dict[str, Any], worktree: dict[str, Any] | None = None) -> list[str]:
    findings = package['findings'] + (worktree['findings'] if worktree else [])
    return [f"{item['code']}: {item['message']}" for item in findings if item['severity'] in {'error', 'warning', 'expected'}][:12]


def receipt_inputs_unavailable(package: dict[str, Any]) -> bool:
    """Do not hand a known unsafe selected path to legacy receipt path readers."""
    return any(item['code'] in {
        'file_unsafe', 'file_unavailable', 'file_changed', 'file_too_large',
        'inspection_limit', 'state_invalid', 'spec_invalid', 'package_identity_mismatch',
    } for item in package['findings'])
