#!/usr/bin/env python3
from __future__ import annotations

from _lib import emit, read_payload, root_from
from adaptive_grok.router import route_context
from adaptive_grok.state import get_active_change, get_active_route


def main() -> None:
    payload = read_payload()
    root = root_from(payload)
    route = get_active_route(root)
    change = get_active_change(root)
    if route:
        extra = f' Active route {route.get("route_id")}. Change: {(change or {}).get("change_id", "none")}.'
        context = route_context(route) + extra
    else:
        context = 'No active route. Submit a development task to classify work.'
    emit({
        'hookSpecificOutput': {
            'hookEventName': 'SessionStart',
            'additionalContext': context,
        }
    })


if __name__ == '__main__':
    main()
