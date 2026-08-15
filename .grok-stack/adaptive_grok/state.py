from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .util import dump_json, load_json, now_utc, runtime_dir


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


def add_approval(root: Path, scope: str, reason: str, ttl_minutes: int) -> dict[str, Any]:
    import secrets
    from datetime import datetime, timedelta, timezone

    with runtime_lock(root, 'approvals'):
        approvals = load_json(approvals_path(root), [])
        if not isinstance(approvals, list):
            approvals = []
        now = datetime.now(timezone.utc)
        approval = {
            'id': secrets.token_hex(6),
            'scope': scope,
            'reason': reason,
            'created_at': now.isoformat(timespec='seconds'),
            'expires_at': (now + timedelta(minutes=ttl_minutes)).isoformat(timespec='seconds'),
        }
        approvals.append(approval)
        dump_json(approvals_path(root), approvals[-100:])
        return approval


def has_valid_approval(root: Path, scope: str) -> bool:
    from datetime import datetime, timezone

    approvals = load_json(approvals_path(root), [])
    if not isinstance(approvals, list):
        return False
    now = datetime.now(timezone.utc)
    valid: list[dict[str, Any]] = []
    matched = False
    for approval in approvals:
        try:
            expires = datetime.fromisoformat(approval['expires_at'])
        except (KeyError, TypeError, ValueError):
            continue
        if expires >= now:
            valid.append(approval)
            if approval.get('scope') in {scope, '*'}:
                matched = True
    if len(valid) != len(approvals):
        dump_json(approvals_path(root), valid)
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
