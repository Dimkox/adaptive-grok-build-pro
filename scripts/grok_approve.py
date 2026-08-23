from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

import argparse
import json

from adaptive_grok.state import request_approval
from adaptive_grok.util import find_root

parser = argparse.ArgumentParser(
    description=(
        'Record a non-authorizing request for a human-owned protected action.'
    )
)
parser.add_argument(
    'scope',
    choices=['production', 'external-write', 'protected-path', '*'],
)
parser.add_argument('--reason', required=True)
parser.add_argument(
    '--ttl',
    type=int,
    default=15,
    help='Deprecated compatibility argument; requests do not grant access.',
)
args = parser.parse_args()
_ = args.ttl
result = request_approval(find_root(), args.scope, args.reason)
result.update(
    {
        'authorization': 'not-granted',
        'next_step': (
            'Use the protected pull-request or production Environment path.'
        ),
    }
)
print(json.dumps(result, ensure_ascii=False, indent=2))
