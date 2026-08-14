#!/usr/bin/env python3
from __future__ import annotations

from _lib import agent_id, agent_type, emit, read_payload, root_from
from adaptive_grok.policy import WRITE_ROLES
from adaptive_grok.state import get_active_route, record_agent_start


def main() -> None:
    payload = read_payload()
    root = root_from(payload)
    kind = agent_type(payload)
    record_agent_start(root, agent_id(payload), kind)
    route = get_active_route(root) or {}
    role = 'implementation' if kind in WRITE_ROLES or kind == route.get('write_agent') else 'analysis-or-review'
    emit({
        'hookSpecificOutput': {
            'hookEventName': 'SubagentStart',
            'additionalContext': (
                f'Active route {route.get("route_id", "none")}: start {role} agent {kind}. '
                f'Allowed agents: {", ".join(route.get("allowed_agents") or [])}.'
            ),
        }
    })


if __name__ == '__main__':
    main()
