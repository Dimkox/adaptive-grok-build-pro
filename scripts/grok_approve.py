from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

import argparse
import json

from adaptive_grok.state import add_approval
from adaptive_grok.util import find_root

parser = argparse.ArgumentParser(description='Create a short-lived explicit approval for guarded side effects.')
parser.add_argument('scope', choices=['production', 'external-write', 'protected-path', '*'])
parser.add_argument('--reason', required=True)
parser.add_argument('--ttl', type=int, default=15, help='Minutes')
args = parser.parse_args()
print(json.dumps(add_approval(find_root(), args.scope, args.reason, args.ttl), ensure_ascii=False, indent=2))
