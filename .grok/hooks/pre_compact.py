#!/usr/bin/env python3
from __future__ import annotations

from _lib import emit, first, read_payload, root_from
from adaptive_grok.state import get_active_change, get_active_route
from adaptive_grok.util import dump_json, now_utc, runtime_dir


def main() -> None:
    payload = read_payload()
    root = root_from(payload)
    dump_json(runtime_dir(root) / 'handoff.json', {
        'created_at': now_utc(),
        'trigger': first(payload.get('trigger'), 'unknown'),
        'route': get_active_route(root),
        'change': get_active_change(root),
    })
    emit({'continue': True})


if __name__ == '__main__':
    main()
