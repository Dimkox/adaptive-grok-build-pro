from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

import argparse
import json

from adaptive_grok.deploy import prepare_deploy
from adaptive_grok.util import find_root

parser = argparse.ArgumentParser(description='Prepare human-owned publish commands. Never executes tag, push, or release.')
parser.add_argument('--record', action='store_true', help='Write a deploy/prepared receipt. Requires production approval.')
parser.add_argument('--json', action='store_true')
args = parser.parse_args()
report = prepare_deploy(find_root(), record=args.record)
if args.json:
    print(json.dumps(report, ensure_ascii=False, indent=2))
elif report.get('ok'):
    for command in report.get('commands', []):
        print(command)
else:
    print(report.get('error', 'deploy prepare failed'), file=sys.stderr)
raise SystemExit(0 if report.get('ok') else 1)
