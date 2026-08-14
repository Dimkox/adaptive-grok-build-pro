#!/usr/bin/env python3
from __future__ import annotations

from _lib import agent_id, agent_type, emit, read_payload, root_from
from adaptive_grok.state import record_agent_stop


def main() -> None:
    payload = read_payload()
    root = root_from(payload)
    record_agent_stop(root, agent_id(payload), agent_type(payload))
    emit({
        'hookSpecificOutput': {
            'hookEventName': 'SubagentStop',
            'additionalContext': f'Stopped agent {agent_id(payload)}',
        }
    })


if __name__ == '__main__':
    main()
