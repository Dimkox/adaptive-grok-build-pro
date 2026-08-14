from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

import argparse
import json

from adaptive_grok.change import start_change, transition
from adaptive_grok.state import get_active_change
from adaptive_grok.util import find_root

parser = argparse.ArgumentParser(description='Manage durable engineering change packages.')
sub = parser.add_subparsers(dest='command', required=True)
start = sub.add_parser('start')
start.add_argument('--title')
move = sub.add_parser('transition')
move.add_argument('change_id')
move.add_argument('target')
move.add_argument('--reason', required=True)
sub.add_parser('show')
args = parser.parse_args()
root = find_root()
if args.command == 'start':
    result = start_change(root, args.title)
elif args.command == 'transition':
    result = transition(root, args.change_id, args.target, args.reason)
else:
    result = get_active_change(root)
print(json.dumps(result, ensure_ascii=False, indent=2))
