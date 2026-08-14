#!/usr/bin/env python3
from __future__ import annotations

from _lib import emit, read_payload, root_from
from adaptive_grok.receipts import invalidate_receipts
from adaptive_grok.state import get_active_route
from adaptive_grok.util import dump_json, load_json, runtime_dir, tree_fingerprint


def main() -> None:
    payload = read_payload()
    root = root_from(payload)
    marker = runtime_dir(root) / 'last-fingerprint.json'
    current = tree_fingerprint(root)
    previous = load_json(marker, {}) or {}
    last = previous.get('tree_fingerprint') if isinstance(previous, dict) else None
    route = get_active_route(root)
    if last and last != current and route:
        invalidate_receipts(root, route['route_id'], 'repository tree changed after tool use')
    dump_json(marker, {'tree_fingerprint': current})
    emit({
        'hookSpecificOutput': {
            'hookEventName': 'PostToolUse',
            'additionalContext': '',
        }
    })


if __name__ == '__main__':
    main()
