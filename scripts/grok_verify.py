from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

import argparse
import json
import sys

from adaptive_grok.receipts import receipt_echo
from adaptive_grok.util import find_root
from adaptive_grok.verification import verify

parser = argparse.ArgumentParser(description='Run route-selected verification and record a fingerprint-bound receipt.')
parser.add_argument(
    '--mode',
    choices=['fast', 'pr', 'release', 'focused-static-seo-landing'],
    default='pr',
)
parser.add_argument('--profile', action='append', dest='profiles')
parser.add_argument('--no-record', action='store_true')
parser.add_argument('--json', action='store_true')
args = parser.parse_args()
root = find_root()
report = verify(root, args.mode, args.profiles, record=not args.no_record)
if args.json:
    print(json.dumps(report, ensure_ascii=True, indent=2))
else:
    for item in report['checks']:
        print(f"{item['status'].upper():4} {item['name']}: {item['summary']}")
        for finding in item.get('details', []):
            print(f"     {finding.get('severity', '').upper()} {finding.get('path')}: {finding.get('message')}")
    scope = report.get('verification_scope') or {}
    print(
        f"RESULT: {report['status'].upper()} | mode={report['mode']} "
        f"profiles={','.join(report['profiles'])} | changed={len(report['changed_files'])} "
        f"checked={len(scope.get('checked_files', []))} "
        f"focused_tests={','.join(scope.get('focused_tests', [])) or 'none'}"
    )
# The canonical identifier line: a report pastes this instead of retyping a fingerprint. It
# goes to stderr under --json so the JSON on stdout stays machine-parseable.
if not args.no_record:
    print(
        receipt_echo(root, 'verification', expect_tree_fingerprint=report.get('tree_fingerprint')),
        file=sys.stderr if args.json else sys.stdout,
    )
raise SystemExit(0 if report['status'] == 'pass' else 1)
