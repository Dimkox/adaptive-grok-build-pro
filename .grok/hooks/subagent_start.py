#!/usr/bin/env python3
from __future__ import annotations

from _lib import agent_generation, agent_id, agent_type, emit, read_payload, root_from
from adaptive_grok.policy import WRITE_ROLES
from adaptive_grok.state import get_active_route, record_agent_start


def main() -> None:
    payload = read_payload()
    root = root_from(payload)
    kind = agent_type(payload)
    child = agent_id(payload)
    if child == 'unknown':
        emit({})
        return
    try:
        record = record_agent_start(root, child, kind, generation=agent_generation(payload))
    except (ValueError, TimeoutError):
        emit({'systemMessage': 'Local agent start rejected: instance conflict or writer already active.'})
        return
    route = get_active_route(root) or {}
    role = 'implementation' if kind in WRITE_ROLES or kind == route.get('write_agent') else 'analysis-or-review'
    emit({
        'hookSpecificOutput': {
            'hookEventName': 'SubagentStart',
            'additionalContext': (
                f'Active route {route.get("route_id", "none")}: start {role} agent {kind}. '
                f'Allowed agents: {", ".join(route.get("allowed_agents") or [])}.'
                f' Local instance: agent_id={child}, generation={record.get("generation", "legacy")}, '
                f'route_id={record.get("route_id")}, task_id={record.get("task_id")}. '
                'Report heartbeat and explicit useful checkpoints via scripts/grok_agent.py; '
                'tool activity alone is not progress.'
            ),
        }
    })


if __name__ == '__main__':
    main()
