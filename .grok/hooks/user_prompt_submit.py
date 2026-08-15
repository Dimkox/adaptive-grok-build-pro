#!/usr/bin/env python3
from __future__ import annotations

from _lib import emit, is_child_payload, prompt_text, read_payload, root_from, session_id
from adaptive_grok.router import build_route, can_reuse_active_route, route_context
from adaptive_grok.state import get_active_route, set_active_route


def main() -> None:
    payload = read_payload()
    root = root_from(payload)
    prompt = prompt_text(payload)
    existing = get_active_route(root)
    if existing and (is_child_payload(payload) or can_reuse_active_route(prompt, existing, session_id(payload))):
        context = route_context(existing)
    else:
        route = build_route(root, prompt or 'development task', session_id(payload))
        set_active_route(root, route.to_dict())
        context = route_context(route)
    emit({
        'hookSpecificOutput': {
            'hookEventName': 'UserPromptSubmit',
            'additionalContext': context,
        }
    })


if __name__ == '__main__':
    main()
