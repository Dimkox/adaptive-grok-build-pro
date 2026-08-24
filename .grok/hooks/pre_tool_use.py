#!/usr/bin/env python3
"""PreToolUse — soft policy gate (fail-open)."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

# Make stack importable even when cwd is project root
_ROOT_CANDIDATES = [
    Path.cwd(),
    Path.cwd() / ".grok-stack",
]
for _p in _ROOT_CANDIDATES:
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

try:
    from _lib import emit, read_payload, root_from, session_id, tool_input, tool_name
except Exception:
    # If even _lib is missing, never block the agent
    print('{"decision":"allow"}')
    raise SystemExit(0)


_DENIAL_WINDOW_SECONDS = 15 * 60
_DENIAL_MAX_ENTRIES = 128
_EXACT_CIRCUIT_BREAKER_GUIDANCE = (
    'Circuit breaker: this exact tool invocation was denied again. Do not retry it, mutate it cosmetically, '
    'or create a speculative grant. Stop dependent subagents, mark this objective BLOCKED, and report the blocker.'
)
_OBJECTIVE_CIRCUIT_BREAKER_GUIDANCE = (
    'Circuit breaker: the rewritten invocation was denied for the same objective. Do not retry this objective '
    'again or create a speculative grant. Stop dependent subagents, mark this objective BLOCKED, '
    'and report the blocker.'
)
_CONTROL_PLANE_BATCH_GUIDANCE = (
    'Create one exact protected-path grant covering every target, then use Edit/Write/apply_patch. '
    'For an atomic multi-file batch, put the manifest outside the repository '
    'and run `python3 scripts/grok_protected_write.py --manifest <path>`.'
)


def _actionable_reason(reason: str) -> str:
    if 'control-plane shell mutation' not in reason:
        return reason
    if 'grok_protected_write.py' in reason:
        return reason
    return f'{reason} {_CONTROL_PLANE_BATCH_GUIDANCE}'


def _fingerprint(material: dict[str, Any]) -> str:
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
        default=str,
    ).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def _denial_fingerprints(
    session: str,
    tool: str,
    input_data: dict[str, Any],
    reason: str,
) -> tuple[str, str]:
    exact = _fingerprint({
        'session_id': session,
        'tool_name': tool,
        'tool_input': input_data,
        'reason': reason,
    })
    objective = _fingerprint({
        'session_id': session,
        'tool_name': tool,
        'reason': reason,
    })
    return exact, objective


def _fresh_entries(value: Any, now: float) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    fresh: dict[str, dict[str, Any]] = {}
    for key, entry in value.items():
        if not isinstance(entry, dict):
            continue
        updated_at = entry.get('updated_at')
        if isinstance(updated_at, (int, float)) and now - float(updated_at) <= _DENIAL_WINDOW_SECONDS:
            fresh[str(key)] = entry
    return fresh


def _increment_entry(
    entries: dict[str, dict[str, Any]],
    fingerprint: str,
    *,
    session: str,
    tool: str,
    now: float,
) -> int:
    previous = entries.get(fingerprint, {})
    previous_count = previous.get('count', 0) if isinstance(previous, dict) else 0
    count = int(previous_count) + 1 if isinstance(previous_count, int) else 1
    entries[fingerprint] = {
        'count': count,
        'session_id': session,
        'tool_name': tool,
        'updated_at': now,
    }
    return count


def _cap_entries(entries: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if len(entries) <= _DENIAL_MAX_ENTRIES:
        return entries
    ordered = sorted(
        entries.items(),
        key=lambda item: float(item[1].get('updated_at', 0)),
        reverse=True,
    )[:_DENIAL_MAX_ENTRIES]
    return dict(ordered)


def _record_denial(
    root: Path,
    session: str,
    tool: str,
    input_data: dict[str, Any],
    reason: str,
) -> tuple[int, int]:
    from adaptive_grok.state import runtime_lock
    from adaptive_grok.util import dump_json, load_json, runtime_dir

    now = time.time()
    exact_fingerprint, objective_fingerprint = _denial_fingerprints(
        session,
        tool,
        input_data,
        reason,
    )
    path = runtime_dir(root) / 'tool-denials.json'
    with runtime_lock(root, 'tool-denials'):
        data = load_json(path, {}) or {}
        if not isinstance(data, dict):
            data = {}
        exact_entries = _fresh_entries(data.get('exact', data.get('entries')), now)
        objective_entries = _fresh_entries(data.get('objectives'), now)
        exact_count = _increment_entry(
            exact_entries,
            exact_fingerprint,
            session=session,
            tool=tool,
            now=now,
        )
        objective_count = _increment_entry(
            objective_entries,
            objective_fingerprint,
            session=session,
            tool=tool,
            now=now,
        )
        dump_json(path, {
            'schema_version': 2,
            'exact': _cap_entries(exact_entries),
            'objectives': _cap_entries(objective_entries),
        })
    return exact_count, objective_count


def main() -> None:
    try:
        payload = read_payload()
        root = root_from(payload)
        current_tool = tool_name(payload)
        current_input = tool_input(payload)
        try:
            from adaptive_grok.policy import evaluate_pre_tool
        except Exception:
            # Soft: policy stack not importable → allow everything
            emit({
                'decision': 'allow',
                'hookSpecificOutput': {
                    'hookEventName': 'PreToolUse',
                    'permissionDecision': 'allow',
                },
            })
            return

        allowed, reason = evaluate_pre_tool(root, {
            'tool_name': current_tool,
            'tool_input': current_input,
        })
        if allowed:
            emit({
                'decision': 'allow',
                'hookSpecificOutput': {
                    'hookEventName': 'PreToolUse',
                    'permissionDecision': 'allow',
                },
            })
            return

        message = _actionable_reason(reason or 'Blocked by Adaptive Grok policy')
        try:
            exact_count, objective_count = _record_denial(
                root,
                session_id(payload),
                current_tool,
                current_input,
                message,
            )
        except Exception:
            exact_count, objective_count = 1, 1
        if exact_count >= 2:
            message = f'{_EXACT_CIRCUIT_BREAKER_GUIDANCE} Original denial: {message}'
        elif objective_count >= 2:
            message = f'{_OBJECTIVE_CIRCUIT_BREAKER_GUIDANCE} Original denial: {message}'

        emit({
            'decision': 'deny',
            'reason': message,
            'hookSpecificOutput': {
                'hookEventName': 'PreToolUse',
                'permissionDecision': 'deny',
                'permissionDecisionReason': message,
            },
        })
    except Exception:
        # Fail-open: never lock the agent on hook bugs
        emit({
            'decision': 'allow',
            'hookSpecificOutput': {
                'hookEventName': 'PreToolUse',
                'permissionDecision': 'allow',
            },
        })


if __name__ == '__main__':
    main()
