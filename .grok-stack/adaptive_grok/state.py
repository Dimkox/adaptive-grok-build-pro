from __future__ import annotations

import fnmatch
import os
import re
import secrets
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from .util import (
    dump_json,
    git_head,
    git_output,
    load_json,
    now_utc,
    runtime_dir,
    tree_fingerprint,
)

APPROVAL_SCOPES = {'production', 'external-write', 'protected-path'}
APPROVAL_SOURCES = {'standing-user-consent', 'explicit-user-consent'}
SCOPE_ACTIONS = {
    'production': {
        'git-push-branch',
        'git-push-tag',
        'pull-request-merge',
        'docker-push',
        'npm-publish',
        'github-release',
    },
    'external-write': {'external-write'},
    'protected-path': {'protected-path-write'},
}


def _process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _stale_lock(lock: Path) -> bool:
    try:
        raw = lock.read_text(encoding='utf-8').strip()
        pid = int(raw)
    except (OSError, ValueError):
        return True
    return not _process_alive(pid)


@contextmanager
def runtime_lock(root: Path, name: str = 'state', timeout: float = 5.0) -> Iterator[None]:
    lock = runtime_dir(root) / f'.{name}.lock'
    deadline = time.monotonic() + timeout
    fd: int | None = None
    while fd is None:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            if _stale_lock(lock):
                try:
                    lock.unlink()
                    continue
                except FileNotFoundError:
                    continue
                except OSError:
                    pass
            if time.monotonic() >= deadline:
                raise TimeoutError(f'could not acquire runtime lock: {lock}')
            time.sleep(0.05)
    try:
        os.write(fd, f'{os.getpid()}\n'.encode())
        yield
    finally:
        os.close(fd)
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def active_route_path(root: Path) -> Path:
    return runtime_dir(root) / 'active-route.json'


def get_active_route(root: Path) -> dict[str, Any] | None:
    data = load_json(active_route_path(root))
    return data if isinstance(data, dict) else None


def set_active_route(root: Path, route: dict[str, Any]) -> None:
    with runtime_lock(root, 'route'):
        dump_json(active_route_path(root), route)
        route_dir = runtime_dir(root) / 'routes'
        route_dir.mkdir(parents=True, exist_ok=True)
        dump_json(route_dir / f"{route['route_id']}.json", route)


def update_route(root: Path, **updates: Any) -> dict[str, Any] | None:
    with runtime_lock(root, 'route'):
        route = get_active_route(root)
        if not route:
            return None
        route.update(updates)
        route['updated_at'] = now_utc()
        dump_json(active_route_path(root), route)
        dump_json(runtime_dir(root) / 'routes' / f"{route['route_id']}.json", route)
        return route


def agent_state_path(root: Path) -> Path:
    return runtime_dir(root) / 'agent-state.json'


def get_agent_state(root: Path) -> dict[str, Any]:
    data = load_json(agent_state_path(root), {'active': {}, 'history': []})
    return data if isinstance(data, dict) else {'active': {}, 'history': []}


def record_agent_start(root: Path, agent_id: str, agent_type: str) -> None:
    with runtime_lock(root, 'agents'):
        state = get_agent_state(root)
        active = state.setdefault('active', {})
        active[agent_id] = {'agent_type': agent_type, 'started_at': now_utc()}
        state.setdefault('history', []).append({'event': 'start', 'agent_id': agent_id, 'agent_type': agent_type, 'at': now_utc()})
        state['history'] = state['history'][-200:]
        dump_json(agent_state_path(root), state)


def record_agent_stop(root: Path, agent_id: str, agent_type: str) -> bool:
    """Record a stop once. Returns True on the first stop, False if already stopped."""
    with runtime_lock(root, 'agents'):
        state = get_agent_state(root)
        active = state.setdefault('active', {})
        first = agent_id in active
        active.pop(agent_id, None)
        if first:
            state.setdefault('history', []).append({
                'event': 'stop',
                'agent_id': agent_id,
                'agent_type': agent_type,
                'at': now_utc(),
            })
            state['history'] = state['history'][-200:]
            dump_json(agent_state_path(root), state)
        return first


def active_write_agents(root: Path, write_roles: set[str]) -> list[str]:
    state = get_agent_state(root)
    return [
        data.get('agent_type', '')
        for data in state.get('active', {}).values()
        if data.get('agent_type') in write_roles
    ]


def approvals_path(root: Path) -> Path:
    return runtime_dir(root) / 'approvals.json'


def _repository_identity(root: Path) -> str:
    remote = git_output(root, 'config', '--get', 'remote.origin.url') or ''
    match = re.search(r'(?:github\.com[:/])([^/\s]+/[^/\s]+?)(?:\.git)?$', remote.strip())
    if not match:
        raise RuntimeError('remote.origin.url must identify a GitHub owner/repository')
    return match.group(1).removesuffix('.git')


def _active_change_id(root: Path) -> str | None:
    change = get_active_change(root) or {}
    value = change.get('change_id')
    return str(value) if value else None


def add_approval(
    root: Path,
    scope: str,
    reason: str,
    ttl_minutes: int = 15,
    *,
    actions: list[str] | tuple[str, ...] | set[str] | None = None,
    resources: list[str] | tuple[str, ...] | set[str] | None = None,
    source: str = 'standing-user-consent',
) -> dict[str, Any]:
    """Materialize an explicitly delegated local grant for one exact repository tree."""
    normalized_scope = scope.strip()
    normalized_reason = reason.strip()
    normalized_source = source.strip()
    if normalized_scope not in APPROVAL_SCOPES:
        raise ValueError(f'unsupported approval scope: {scope}')
    if not normalized_reason:
        raise ValueError('approval reason must not be empty')
    if normalized_source not in APPROVAL_SOURCES:
        raise ValueError(f'unsupported approval source: {source}')
    if isinstance(ttl_minutes, bool) or not 1 <= ttl_minutes <= 1440:
        raise ValueError('ttl_minutes must be between 1 and 1440')

    normalized_actions = sorted({str(item).strip() for item in (actions or []) if str(item).strip()})
    if not normalized_actions:
        raise ValueError('at least one explicit delegated action is required')
    unsupported = set(normalized_actions) - SCOPE_ACTIONS[normalized_scope]
    if unsupported:
        raise ValueError(f'actions are outside scope {normalized_scope}: {sorted(unsupported)}')

    normalized_resources = sorted({str(item).replace('\\', '/').strip() for item in (resources or []) if str(item).strip()})
    if normalized_scope in {'external-write', 'protected-path'} and not normalized_resources:
        raise ValueError(f'{normalized_scope} grants require explicit resources')

    head = git_head(root)
    if not head:
        raise RuntimeError('an exact Git HEAD is required for delegated approval')
    route = get_active_route(root) or {}
    now = datetime.now(timezone.utc)
    approval = {
        'schema_version': 2,
        'id': secrets.token_hex(8),
        'authorization': 'delegated-local-grant',
        'source': normalized_source,
        'scope': normalized_scope,
        'actions': normalized_actions,
        'resources': normalized_resources,
        'reason': normalized_reason,
        'repository': _repository_identity(root),
        'route_id': route.get('route_id'),
        'change_id': _active_change_id(root),
        'git_head': head,
        'tree_fingerprint': tree_fingerprint(root),
        'created_at': now.isoformat(timespec='seconds'),
        'expires_at': (now + timedelta(minutes=ttl_minutes)).isoformat(timespec='seconds'),
    }
    with runtime_lock(root, 'approvals'):
        approvals = load_json(approvals_path(root), [])
        if not isinstance(approvals, list):
            approvals = []
        approvals.append(approval)
        dump_json(approvals_path(root), approvals[-200:])
    return approval


def has_valid_approval(
    root: Path,
    scope: str,
    *,
    action: str | None = None,
    resource: str | None = None,
) -> bool:
    """Validate a delegated grant against the current route, repository, HEAD and tree."""
    approvals = load_json(approvals_path(root), [])
    if not isinstance(approvals, list):
        return False
    try:
        repository = _repository_identity(root)
    except RuntimeError:
        return False
    head = git_head(root)
    if not head:
        return False
    route = get_active_route(root) or {}
    bindings = {
        'repository': repository,
        'route_id': route.get('route_id'),
        'change_id': _active_change_id(root),
        'git_head': head,
        'tree_fingerprint': tree_fingerprint(root),
    }
    now = datetime.now(timezone.utc)
    kept: list[dict[str, Any]] = []
    matched = False
    normalized_resource = resource.replace('\\', '/') if resource else None
    for approval in approvals:
        try:
            expires = datetime.fromisoformat(str(approval['expires_at']))
        except (KeyError, TypeError, ValueError):
            continue
        if expires < now:
            continue
        kept.append(approval)
        if approval.get('schema_version') != 2:
            continue
        if approval.get('authorization') != 'delegated-local-grant':
            continue
        if approval.get('scope') != scope:
            continue
        if any(approval.get(key) != value for key, value in bindings.items()):
            continue
        if action and action not in set(approval.get('actions') or []):
            continue
        patterns = [str(item).replace('\\', '/') for item in approval.get('resources') or []]
        if normalized_resource is not None and not any(fnmatch.fnmatchcase(normalized_resource, pattern) for pattern in patterns):
            continue
        matched = True
    if len(kept) != len(approvals):
        dump_json(approvals_path(root), kept)
    return matched


def active_change_path(root: Path) -> Path:
    return runtime_dir(root) / 'active-change.json'


def set_active_change(root: Path, data: dict[str, Any]) -> None:
    dump_json(active_change_path(root), data)


def get_active_change(root: Path) -> dict[str, Any] | None:
    data = load_json(active_change_path(root))
    return data if isinstance(data, dict) else None


def stop_attempts_path(root: Path) -> Path:
    return runtime_dir(root) / 'stop-attempts.json'


def increment_stop_attempt(root: Path, route_id: str) -> int:
    with runtime_lock(root, 'stop'):
        data = load_json(stop_attempts_path(root), {})
        if not isinstance(data, dict):
            data = {}
        value = int(data.get(route_id, 0)) + 1
        data[route_id] = value
        dump_json(stop_attempts_path(root), data)
        return value


def reset_stop_attempt(root: Path, route_id: str) -> None:
    with runtime_lock(root, 'stop'):
        data = load_json(stop_attempts_path(root), {})
        if isinstance(data, dict):
            data.pop(route_id, None)
            dump_json(stop_attempts_path(root), data)
