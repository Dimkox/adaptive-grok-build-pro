#!/usr/bin/env python3
from __future__ import annotations

from _lib import emit, read_payload, root_from, stop_hook_active
from adaptive_grok.receipts import validate_evidence
from adaptive_grok.state import get_active_route, increment_stop_attempt, reset_stop_attempt, update_route


def main() -> None:
    payload = read_payload()
    root = root_from(payload)
    route = get_active_route(root)
    if not route or not route.get('required_evidence'):
        emit({})
        return
    gaps = validate_evidence(root, route)
    if gaps:
        increment_stop_attempt(root, route['route_id'])
        if stop_hook_active(payload):
            emit({
                'decision': 'block',
                'reason': 'Missing/stale evidence: ' + '; '.join(gaps),
            })
            return
        emit({
            'decision': 'block',
            'reason': 'Missing/stale evidence: ' + '; '.join(gaps),
        })
        return
    reset_stop_attempt(root, route['route_id'])
    update_route(root, status='completed')
    emit({})


if __name__ == '__main__':
    main()
