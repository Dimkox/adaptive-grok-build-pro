#!/usr/bin/env python3
"""Stop gate — soft (warn only, never block stop)."""
from __future__ import annotations

import sys
from pathlib import Path

for _p in (Path.cwd(), Path.cwd() / ".grok-stack"):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

try:
    from _lib import emit, read_payload, root_from
except Exception:
    print('{}')
    raise SystemExit(0)


def main() -> None:
    try:
        payload = read_payload()
        root = root_from(payload)
        try:
            from adaptive_grok.receipts import validate_evidence
            from adaptive_grok.state import get_active_route, reset_stop_attempt, update_route
        except Exception:
            emit({})
            return

        route = get_active_route(root)
        if not route or not route.get('required_evidence'):
            emit({})
            return

        gaps = validate_evidence(root, route)
        if gaps:
            # Soft: report gaps but DO NOT block stop (was hard block → agent loop)
            emit({
                'systemMessage': 'Adaptive note (non-blocking): missing/stale evidence: ' + '; '.join(gaps),
            })
            return

        reset_stop_attempt(root, route['route_id'])
        update_route(root, status='completed')
        emit({})
    except Exception:
        emit({})


if __name__ == '__main__':
    main()
