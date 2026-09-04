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
    from _lib import RootContext, emit, read_payload, root_context, session_id, tool_input, tool_name
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


def _ledger_reason(action: str) -> str:
    if action == 'external-write':
        return 'External write denied by repository policy.'
    if action == 'protected-path-write':
        return 'Protected path write denied by repository policy.'
    if action.startswith('git-push') or action in {
        'pull-request-merge', 'docker-push', 'npm-publish', 'github-release', 'workflow-dispatch'
    }:
        return f'Production action {action} denied by repository policy.'
    return f'Action {action} denied by repository policy.'


def _denial_fingerprints(
    session: str,
    tool: str,
    input_data: dict[str, Any],
    reason: str,
    context: RootContext,
    action: str,
) -> tuple[str, str]:
    roots = {
        'session_root': str(context.session_root) if context.session_root else None,
        'effective_root': str(context.effective_root) if context.effective_root else None,
        'resolution_status': context.resolution_status,
    }
    exact = _fingerprint({
        'session_id': session,
        'tool_name': tool,
        'tool_input': input_data,
        'reason': _ledger_reason(action),
        'reason_sha256': hashlib.sha256(reason.encode('utf-8')).hexdigest(),
        'root_context': roots,
    })
    objective = _fingerprint({
        'session_id': session,
        'tool_name': tool,
        'reason': reason,
        'action': action,
        'root_context': roots,
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
    evidence: dict[str, Any],
) -> int:
    previous = entries.get(fingerprint, {})
    previous_count = previous.get('count', 0) if isinstance(previous, dict) else 0
    count = int(previous_count) + 1 if isinstance(previous_count, int) else 1
    entries[fingerprint] = {
        'count': count,
        'session_id': session,
        'tool_name': tool,
        'updated_at': now,
        **evidence,
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
    context: RootContext,
    action: str,
) -> tuple[int, int]:
    from adaptive_grok.state import runtime_lock
    from adaptive_grok.util import dump_json, load_json, runtime_dir

    now = time.time()
    exact_fingerprint, objective_fingerprint = _denial_fingerprints(
        session,
        tool,
        input_data,
        reason,
        context,
        action,
    )
    path = runtime_dir(root) / 'tool-denials.json'
    command = input_data.get('command')
    evidence = {
        'session_cwd': context.session_cwd,
        'session_root': str(context.session_root) if context.session_root else None,
        'command_workdirs': context.command_workdirs,
        'effective_root': str(context.effective_root) if context.effective_root else None,
        'resolution_status': context.resolution_status,
        'action': action,
        'reason': _ledger_reason(action),
        'reason_sha256': hashlib.sha256(reason.encode('utf-8')).hexdigest(),
        'tool_input_sha256': _fingerprint(input_data),
        'command_sha256': hashlib.sha256(command.encode('utf-8')).hexdigest() if isinstance(command, str) else None,
    }
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
            evidence=evidence,
        )
        objective_count = _increment_entry(
            objective_entries,
            objective_fingerprint,
            session=session,
            tool=tool,
            now=now,
            evidence=evidence,
        )
        dump_json(path, {
            'schema_version': 3,
            'exact': _cap_entries(exact_entries),
            'objectives': _cap_entries(objective_entries),
        })
    return exact_count, objective_count


def main() -> None:
    try:
        payload = read_payload()
        current_tool = tool_name(payload)
        current_input = tool_input(payload)
        context = root_context(payload, current_input, current_tool)
        try:
            from adaptive_grok.policy import evaluate_pre_tool, sensitive_action
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

        classification_root = context.effective_root or context.session_root or Path.cwd()
        action = sensitive_action(classification_root, {
            'tool_name': current_tool,
            'tool_input': current_input,
        })
        if current_tool == 'Bash' and context.has_ambiguous_command_evidence and action is None:
            action = 'ambiguous-sensitive-shell'
        root = context.effective_root or context.session_root
        if action and not context.sensitive_safe:
            allowed = False
            reason = f'Sensitive action {action} denied: root resolution status is {context.resolution_status}.'
        elif root is None:
            allowed, reason = True, None
        else:
            try:
                allowed, reason = evaluate_pre_tool(root, {
                    'tool_name': current_tool,
                    'tool_input': current_input,
                })
            except Exception:
                if action:
                    allowed, reason = False, f'Sensitive action {action} denied: policy evaluation failed closed.'
                else:
                    raise
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
            ledger_root = context.ledger_root
            if ledger_root is None:
                raise RuntimeError('no recognized repository root for denial ledger')
            exact_count, objective_count = _record_denial(
                ledger_root,
                session_id(payload),
                current_tool,
                current_input,
                message,
                context,
                action or 'policy-denial',
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
