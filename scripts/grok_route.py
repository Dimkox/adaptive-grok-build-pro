from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

import argparse
import json

from adaptive_grok.router import build_route, route_context
from adaptive_grok.state import get_active_route, set_active_route, update_route
from adaptive_grok.util import find_root

parser = argparse.ArgumentParser(description='Create or inspect an adaptive task route.')
parser.add_argument('task', nargs='?', help='Development task text')
parser.add_argument('--session', default='manual')
parser.add_argument('--show', action='store_true')
parser.add_argument('--complete', action='store_true')
parser.add_argument('--cancel', action='store_true')
parser.add_argument('--json', action='store_true')
args = parser.parse_args()
root = find_root()
if args.complete:
    data = update_route(root, status='completed')
elif args.cancel:
    data = update_route(root, status='cancelled')
elif args.task:
    route = build_route(root, args.task, args.session)
    data = route.to_dict()
    set_active_route(root, data)
else:
    data = get_active_route(root)
if not data:
    raise SystemExit('No active route and no task supplied.')
print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else route_context(data))
