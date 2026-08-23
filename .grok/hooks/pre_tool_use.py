#!/usr/bin/env python3
"""PreToolUse — soft policy gate (fail-open)."""
from __future__ import annotations

import sys
from pathlib import Path

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
    from _lib import emit, read_payload, root_from, tool_input, tool_name
except Exception:
    # If even _lib is missing, never block the agent
    print('{"decision":"allow"}')
    raise SystemExit(0)


_CONTROL_PLANE_DENIAL = 'Blocked control-plane shell mutation; use a structured write with an exact protected-path grant.'
_CONTROL_PLANE_GUIDANCE = (
    'Blocked opaque control-plane shell mutation. Create one exact protected-path grant covering every target, '
    'then use Edit/Write/apply_patch. For an atomic multi-file batch, put the manifest outside the repository '
    'and run `python3 scripts/grok_protected_write.py --manifest <path>`.'
)


def actionable_reason(reason: str) -> str:
    return _CONTROL_PLANE_GUIDANCE if reason == _CONTROL_PLANE_DENIAL else reason


def main() -> None:
    try:
        payload = read_payload()
        root = root_from(payload)
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
            'tool_name': tool_name(payload),
            'tool_input': tool_input(payload),
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

        message = actionable_reason(reason or 'Blocked by Adaptive Grok policy')
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
