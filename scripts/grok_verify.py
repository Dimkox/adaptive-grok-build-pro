from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

import argparse
import json

from adaptive_grok.util import find_root
from adaptive_grok.verification import verify

parser = argparse.ArgumentParser(
    description=(
        'Run route-selected verification and record a fingerprint-bound '
        'receipt.'
    )
)
parser.add_argument('--mode', choices=['fast', 'pr', 'release'], default='pr')
parser.add_argument('--profile', action='append', dest='profiles')
parser.add_argument('--no-record', action='store_true')
parser.add_argument(
    '--strict',
    action='store_true',
    help='Fail when authoritative Python quality tools are unavailable.',
)
parser.add_argument('--json', action='store_true')
args = parser.parse_args()
report = verify(
    find_root(),
    args.mode,
    args.profiles,
    record=not args.no_record,
    strict=args.strict,
)
if args.json:
    print(json.dumps(report, ensure_ascii=False, indent=2))
else:
    for item in report['checks']:
        print(
            f"{item['status'].upper():4} "
            f"{item['name']}: {item['summary']}"
        )
        for finding in item.get('details', []):
            print(
                f"     {finding.get('severity', '').upper()} "
                f"{finding.get('path')}: {finding.get('message')}"
            )
    print(
        f"RESULT: {report['status'].upper()} | "
        f"strict={report['strict']} | "
        f"profiles={','.join(report['profiles'])} | "
        f"changed={len(report['changed_files'])}"
    )
raise SystemExit(0 if report['status'] == 'pass' else 1)
