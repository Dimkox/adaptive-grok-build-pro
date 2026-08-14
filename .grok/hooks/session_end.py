#!/usr/bin/env python3
from __future__ import annotations

from _lib import emit, read_payload, root_from
from adaptive_grok.util import dump_json, now_utc, runtime_dir


def main() -> None:
    payload = read_payload()
    root = root_from(payload)
    dump_json(runtime_dir(root) / 'last-session-end.json', {
        'ended_at': now_utc(),
        'reason': payload.get('reason'),
    })
    emit({})


if __name__ == '__main__':
    main()
