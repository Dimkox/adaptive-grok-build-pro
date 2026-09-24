from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

import argparse
import json
import os

from adaptive_grok.util import find_root
from adaptive_grok.verification import verify
from adaptive_grok.verification_scope import FORCE_FULL_VARIABLE

parser = argparse.ArgumentParser(description='Run route-selected verification and record a fingerprint-bound receipt.')
parser.add_argument(
    '--mode',
    choices=['fast', 'pr', 'release', 'focused-static-seo-landing'],
    default='pr',
)
parser.add_argument('--profile', action='append', dest='profiles')
parser.add_argument('--no-record', action='store_true')
parser.add_argument('--json', action='store_true')
parser.add_argument(
    '--full-scope',
    action='store_true',
    help='force the full PR suite even when the inventory is documentation/state-only',
)
args = parser.parse_args()
if args.full_scope:
    os.environ[FORCE_FULL_VARIABLE] = '1'
report = verify(find_root(), args.mode, args.profiles, record=not args.no_record)
if args.json:
    print(json.dumps(report, ensure_ascii=True, indent=2))
else:
    for item in report['checks']:
        print(f"{item['status'].upper():4} {item['name']}: {item['summary']}")
        for finding in item.get('details', []):
            print(f"     {finding.get('severity', '').upper()} {finding.get('path')}: {finding.get('message')}")
    scope = report.get('verification_scope') or report.get('docs_state_scope') or {}
    print(
        f"RESULT: {report['status'].upper()} | mode={report['mode']} "
        f"scope={scope.get('profile', 'not-run')} "
        f"evidence={scope.get('evidence_kind', 'not-run')} "
        f"reason={scope.get('reason_code', 'not-run')} "
        f"| profiles={','.join(report['profiles'])} | changed={len(report['changed_files'])} "
        f"checked={len(scope.get('checked_files', []))} "
        f"focused_tests={','.join(scope.get('focused_tests', [])) or 'none'}"
    )
raise SystemExit(0 if report['status'] == 'pass' else 1)
