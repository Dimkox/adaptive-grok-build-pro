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
            from adaptive_grok.package_status import collect_worktree, diagnostic_messages, inspect_package, receipt_inputs_unavailable
            from adaptive_grok.receipts import validate_evidence
            from adaptive_grok.state import get_active_change, get_active_route, reset_stop_attempt, update_route
        except Exception:
            emit({})
            return

        route = get_active_route(root)
        active = get_active_change(root)
        messages = []
        unsafe_inputs = False
        if active:
            package = inspect_package(root, route, active)
            worktree = collect_worktree(root, route, package['initial_checkpoint'])
            messages = diagnostic_messages(package, worktree)
            unsafe_inputs = receipt_inputs_unavailable(package)
        if not route:
            emit({'systemMessage': 'Adaptive note (non-blocking): ' + '; '.join(messages)} if messages else {})
            return
        gaps = (
            ['package: receipt validation unavailable until unsafe or unreadable selected inputs are resolved']
            if unsafe_inputs else validate_evidence(root, route) if route.get('required_evidence') else []
        )
        if gaps:
            messages.insert(0, 'missing/stale evidence: ' + '; '.join(gaps))
        if messages:
            emit({'systemMessage': 'Adaptive note (non-blocking): ' + '; '.join(messages)})
            return
        if not route.get('required_evidence'):
            emit({})
            return

        reset_stop_attempt(root, route['route_id'])
        update_route(root, status='completed')
        emit({})
    except Exception:
        emit({})


if __name__ == '__main__':
    main()
