#!/usr/bin/env python3
from __future__ import annotations

from _lib import emit, read_payload, root_from, tool_input, tool_name
from adaptive_grok.policy import evaluate_pre_tool


def main() -> None:
    payload = read_payload()
    root = root_from(payload)
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
    message = reason or 'Blocked by Adaptive Grok policy'
    emit({
        'decision': 'deny',
        'reason': message,
        'hookSpecificOutput': {
            'hookEventName': 'PreToolUse',
            'permissionDecision': 'deny',
            'permissionDecisionReason': message,
        },
    })


if __name__ == '__main__':
    main()
