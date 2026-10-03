"""Local, generation-fenced observations; native harness control belongs to the caller."""
from __future__ import annotations

import copy
import fcntl
import hashlib
import os
import re
import secrets
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .state import agent_state_path, get_active_route, get_agent_state, runtime_lock
from .util import dump_json, runtime_dir

ACTIVITIES = {'idle', 'tool', 'polling', 'waiting', 'test', 'analysis', 'io', 'model'}
CHECKPOINTS = {'contract', 'evidence', 'implementation', 'test-result', 'review-result', 'handoff'}
RESULTS = {'completed', 'failed', 'cancelled'}
IDENTITY = re.compile(r'[A-Za-z0-9_.:/-]{1,128}\Z')
TASK_SOURCE_IDENTITY = re.compile(r'[\w.:/-]{1,128}\Z')


@contextmanager
def _locked(root: Path):
    # A stable kernel lock closes the PID-file create/write and stale-unlink
    # races between simultaneous lifecycle callers; retain the legacy lock too.
    descriptor = os.open(runtime_dir(root) / '.agents.guard', os.O_CREAT | os.O_RDWR, 0o600)
    deadline = time.monotonic() + 5
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('agent-lock-timeout')
                time.sleep(0.05)
        with runtime_lock(root, 'agents'):
            yield
    finally:
        os.close(descriptor)


def _identity(value: str) -> str:
    if not isinstance(value, str) or not IDENTITY.fullmatch(value) or value == 'unknown':
        raise ValueError('invalid-identity')
    return value


def _task_identity(value: Any) -> str:
    # Change slugs deliberately preserve Cyrillic; diagnostics keep an opaque
    # ASCII binding without admitting free-text, controls or oversized sources.
    if not isinstance(value, str) or not TASK_SOURCE_IDENTITY.fullmatch(value) or value == 'unknown':
        raise ValueError('invalid-task-identity-source')
    return _identity(value) if value.isascii() else 'task:' + hashlib.sha256(value.encode('utf-8')).hexdigest()


def _now(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError('timezone-required')
    return current.astimezone(timezone.utc)


def _timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else None
        return parsed.astimezone(timezone.utc) if parsed and parsed.tzinfo else None
    except (ValueError, OverflowError):
        return None


def _seconds(value: int, maximum: int = 86400) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError('invalid-budget')
    return value


def _save(root: Path, state: dict, event: str, agent_id: str, record: dict, now: datetime) -> dict:
    state.setdefault('history', []).append({
        'event': event, 'agent_id': agent_id, 'agent_type': record['agent_type'],
        'generation': record.get('generation'), 'route_id': record.get('route_id'),
        'generation_number': record.get('generation_number', 1),
        'task_id': record.get('task_id'), 'at': now.isoformat(timespec='seconds'),
    })
    state['history'] = state['history'][-200:]
    dump_json(agent_state_path(root), state)
    return copy.deepcopy(record)


def start_agent(root: Path, agent_id: str, agent_type: str, *, now: datetime | None = None,
                generation: str | None = None) -> dict:
    from .policy import write_roles

    agent_id, agent_type = _identity(agent_id), _identity(agent_type)
    current = _now(now)
    with _locked(root):
        route = get_active_route(root) or {}
        route_id = _identity(route.get('route_id') or 'unrouted')
        source_task_id = route['change_id'] if 'change_id' in route else route.get('session_id', route_id)
        task_id = _task_identity(source_task_id)
        state = get_agent_state(root)
        active = state.setdefault('active', {})
        existing = active.get(agent_id)
        if existing:
            if (existing.get('agent_type') != agent_type or
                    existing.get('route_id', route_id) != route_id or
                    existing.get('task_id', task_id) != task_id or
                    (generation is not None and existing.get('generation') != generation)):
                raise ValueError('instance-conflict')
            return copy.deepcopy(existing)
        roles = write_roles(root) | {route.get('write_agent')}
        if agent_type in roles and route.get('write_agent') and route['write_agent'] != agent_type:
            raise ValueError('writer-outside-route')
        if agent_type in roles and any(item.get('agent_type') in roles for item in active.values()):
            raise ValueError('writer-already-active')
        if route.get('allowed_agents') and agent_type not in route['allowed_agents']:
            raise ValueError('agent-outside-route')
        record = {
            'agent_type': agent_type, 'route_id': route_id, 'task_id': task_id,
            'workspace': str(root.resolve()), 'generation': _identity(generation or secrets.token_hex(16)),
            'generation_number': 1 + max((item.get('generation_number', 1)
                for item in state.get('history', []) if item.get('agent_id') == agent_id), default=0),
            'lifecycle': 'running', 'activity': 'idle',
            'started_at': current.isoformat(timespec='seconds'),
            'last_heartbeat_at': current.isoformat(timespec='seconds'),
            'last_progress_at': current.isoformat(timespec='seconds'),
            'last_activity_at': current.isoformat(timespec='seconds'),
        }
        active[agent_id] = record
        return _save(root, state, 'start', agent_id, record, current)


def _matching(root: Path, record: dict, generation: str, route_id: str, task_id: str) -> None:
    for value in (generation, route_id, task_id):
        _identity(value)
    route = get_active_route(root) or {}
    current_task = _task_identity(route['change_id'] if 'change_id' in route else
                                  route.get('session_id', route.get('route_id') or 'unrouted'))
    if (record.get('generation') != generation or record.get('route_id') != route_id or
            record.get('task_id') != task_id or current_task != task_id or
            (route.get('route_id') and route['route_id'] != route_id)):
        raise ValueError('stale-or-mismatched-instance')


def _request(record: dict, kind: str, current: datetime, ack_seconds: int) -> None:
    key = kind + '_request'
    prior = record.get(key)
    if prior and not prior.get('acknowledged_at'):
        raise ValueError('request-already-pending')
    record[key] = {'request_id': secrets.token_hex(16), 'generation': record['generation'],
                   'requested_at': current.isoformat(timespec='seconds'),
                   'deadline_at': (current + timedelta(seconds=_seconds(ack_seconds))).isoformat(timespec='seconds')}
    if kind == 'interrupt':
        record['lifecycle'] = 'interrupt-requested'


def _ack(record: dict, kind: str, request_id: str | None, current: datetime) -> None:
    request = record.get(kind + '_request') or {}
    requested = _timestamp(request.get('requested_at'))
    if (not request_id or request.get('request_id') != request_id or
            request.get('generation') != record['generation'] or not requested or current < requested):
        raise ValueError('acknowledgement-mismatch')
    if request.get('acknowledged_at'):
        raise ValueError('already-acknowledged')
    request['acknowledged_at'] = current.isoformat(timespec='seconds')
    record['last_heartbeat_at'] = current.isoformat(timespec='seconds')
    if kind == 'interrupt':
        record['lifecycle'] = 'interrupted'


def update_agent(root: Path, agent_id: str, generation: str, route_id: str, task_id: str,
                 event: str, *, now: datetime | None = None, activity: str | None = None,
                 duration_seconds: int | None = None, checkpoint: str | None = None,
                 request_id: str | None = None, ack_seconds: int = 60, **unsupported: Any) -> dict:
    if unsupported:
        raise ValueError('unsupported-diagnostic-fields')
    agent_id = _identity(agent_id)
    current = _now(now)
    with _locked(root):
        state = get_agent_state(root)
        record = state.get('active', {}).get(agent_id)
        if not isinstance(record, dict):
            raise ValueError('agent-not-active')
        _matching(root, record, generation, route_id, task_id)
        started = _timestamp(record.get('started_at'))
        prior_times = [_timestamp(record.get(key)) for key in
                       ('started_at', 'last_heartbeat_at', 'last_progress_at', 'last_activity_at')]
        for kind in ('status', 'interrupt'):
            request = record.get(kind + '_request') or {}
            prior_times.extend(_timestamp(request.get(key)) for key in ('requested_at', 'acknowledged_at'))
        if not started or any(current < prior for prior in prior_times if prior):
            raise ValueError('out-of-order-time')
        if event == 'resume':
            if record.get('lifecycle') != 'interrupted':
                raise ValueError('interruption-not-acknowledged')
            # Keep the same agent/task/workspace and writer slot; fence the prior executor.
            record.update(generation=secrets.token_hex(16), lifecycle='running', activity='idle',
                          generation_number=record.get('generation_number', 1) + 1)
            record.pop('status_request', None)
            record.pop('interrupt_request', None)
            record.pop('activity_until', None)
            record['last_heartbeat_at'] = current.isoformat(timespec='seconds')
            record['last_activity_at'] = current.isoformat(timespec='seconds')
        elif event in {'status-request', 'interrupt-request'}:
            if record.get('lifecycle') == 'interrupted':
                raise ValueError('agent-interrupted')
            _request(record, event.removesuffix('-request'), current, ack_seconds)
        elif event in {'status-ack', 'interrupt-ack'}:
            _ack(record, event.removesuffix('-ack'), request_id, current)
        elif event in {'heartbeat', 'progress', 'activity'}:
            if record.get('lifecycle') not in {'running', 'interrupt-requested'}:
                raise ValueError('agent-interrupted')
            if event == 'progress':
                if checkpoint not in CHECKPOINTS:
                    raise ValueError('invalid-checkpoint')
                record['last_progress_at'] = current.isoformat(timespec='seconds')
                record['checkpoint'] = checkpoint
            elif event == 'activity':
                if activity not in ACTIVITIES:
                    raise ValueError('invalid-activity')
                record['activity'] = activity
                record['last_activity_at'] = current.isoformat(timespec='seconds')
                record.pop('activity_until', None)
                if duration_seconds is not None:
                    if activity in {'idle', 'polling'}:
                        raise ValueError('unbounded-polling-not-progress')
                    record['activity_until'] = (current + timedelta(
                        seconds=_seconds(duration_seconds, 3600))).isoformat(timespec='seconds')
            record['last_heartbeat_at'] = current.isoformat(timespec='seconds')
        else:
            raise ValueError('invalid-event')
        return _save(root, state, event, agent_id, record, current)


def stop_agent(root: Path, agent_id: str, agent_type: str, *, generation: str | None = None,
               now: datetime | None = None, final: bool = False) -> bool:
    current = _now(now)
    with _locked(root):
        state = get_agent_state(root)
        record = state.setdefault('active', {}).get(agent_id)
        if not record or record.get('agent_type') != agent_type:
            return False
        if ((generation is not None and generation != record.get('generation')) or
                (generation is None and record.get('generation_number', 1) != 1)):
            return False
        if record.get('lifecycle') in {'interrupted', 'interrupt-requested'} and not final:
            return False
        state['active'].pop(agent_id)
        _save(root, state, 'stop', agent_id, record, current)
        return True


def record_terminal_report(root: Path, agent_id: str, generation: str, route_id: str, task_id: str,
                           result: str, *, now: datetime | None = None) -> None:
    if result not in RESULTS:
        raise ValueError('invalid-result')
    with _locked(root):
        state = get_agent_state(root)
        for record in reversed(state.get('history', [])):
            if record.get('event') == 'stop' and record.get('agent_id') == agent_id:
                _matching(root, record, generation, route_id, task_id)
                record['result'] = result
                record['reported_at'] = _now(now).isoformat(timespec='seconds')
                dump_json(agent_state_path(root), state)
                return
        raise ValueError('terminal-instance-not-found')


def observe_tool(root: Path, agent_id: str, generation: str | None, *, finished: bool = False) -> None:
    """Only explicit, known child identity is eligible. Tool input/output is never stored."""
    if not generation:
        return
    state = get_agent_state(root)
    active = state.get('active', {})
    if not isinstance(active, dict) or not isinstance(state.get('history', []), list):
        return
    record = active.get(agent_id)
    if not isinstance(record, dict) or not record:
        return
    try:
        update_agent(root, agent_id, generation, record['route_id'], record['task_id'], 'activity',
                     activity='idle' if finished else 'tool')
    except (KeyError, ValueError):
        return


def _diagnose(agent_id: str, record: dict, current: datetime, heartbeat_seconds: int,
              progress_seconds: int) -> dict:
    warnings: list[str] = []
    ages: dict[str, float | None] = {}
    until = _timestamp(record.get('activity_until'))
    activity_at = _timestamp(record.get('last_activity_at'))
    bounded = bool(until and activity_at and activity_at <= current <= until and
                   0 < (until - activity_at).total_seconds() <= 3600 and
                   record.get('activity') in ACTIVITIES - {'idle', 'polling'})
    for label, budget in [('heartbeat', heartbeat_seconds), ('progress', progress_seconds)]:
        observed = _timestamp(record.get(f'last_{label}_at'))
        age = (current - observed).total_seconds() if observed and observed <= current else None
        ages[label + '_age_seconds'] = age
        if age is None:
            warnings.append(label + '-unavailable')
        elif age > budget and not (label == 'progress' and bounded):
            warnings.append(label + '-overdue')
    for kind in ('status', 'interrupt'):
        request = record.get(kind + '_request')
        if isinstance(request, dict) and not request.get('acknowledged_at'):
            deadline = _timestamp(request.get('deadline_at'))
            if not deadline:
                warnings.append(kind + '-ack-unavailable')
            elif current > deadline:
                warnings.append(kind + '-ack-overdue')
    lifecycle = record.get('lifecycle', 'legacy')
    classification = ('uninstrumented' if not record.get('generation') else
                      'interrupted' if lifecycle == 'interrupted' else
                      'suspected-stall' if warnings else 'observed-running')
    return {'agent_id': agent_id, 'agent_type': record.get('agent_type'),
            'route_id': record.get('route_id'), 'task_id': record.get('task_id'),
            'generation': record.get('generation'), 'lifecycle': lifecycle,
            'activity': record.get('activity') if record.get('activity') in ACTIVITIES else 'unavailable',
            'classification': classification, 'bounded_activity': bounded,
            'warnings': warnings, **ages}


def watchdog(root: Path, *, now: datetime | None = None, heartbeat_seconds: int = 180,
             progress_seconds: int = 600) -> dict[str, Any]:
    current = _now(now)
    _seconds(heartbeat_seconds)
    _seconds(progress_seconds)
    state = get_agent_state(root)
    active = state.get('active', {})
    agents = [_diagnose(agent_id, record, current, heartbeat_seconds, progress_seconds)
              for agent_id, record in sorted(active.items())]
    terminal = []
    seen = set()
    for record in reversed(state.get('history', [])):
        identity = (record.get('agent_id'), record.get('generation'))
        if record.get('event') != 'stop' or identity in seen:
            continue
        seen.add(identity)
        result = record.get('result')
        terminal.append({'agent_id': identity[0], 'generation': identity[1],
                         'classification': 'terminal-' + result if result in RESULTS else 'terminal-report-missing'})
    return {'schema_version': 1, 'observed_at': current.isoformat(timespec='seconds'),
            'control': 'local-observation-only', 'budgets': {'heartbeat_seconds': heartbeat_seconds,
            'progress_seconds': progress_seconds}, 'agents': agents, 'terminal': terminal}
