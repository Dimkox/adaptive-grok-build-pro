from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

import json

from adaptive_grok.doctor import run_doctor
from adaptive_grok.git_audit import audit_git_state, format_audit
from adaptive_grok.toolchain import check_toolchain, offer_install_lines
from adaptive_grok.util import find_root

parser = argparse.ArgumentParser(description='Health check. Prints toolchain pins, a read-only Git delivery audit, and install offers for missing or old tools.')
parser.add_argument(
    '--offer-install',
    action='store_true',
    help='Print fallback/newer install commands for tools that are missing or below minimum.',
)
parser.add_argument(
    '--git-audit',
    action='store_true',
    help='Print the full read-only worktree/branch/stash delivery screen, including human-owned next steps.',
)
parser.add_argument(
    '--git-audit-json',
    action='store_true',
    help='Print only the machine-readable delivery audit (JSON) and exit 0.',
)
parser.add_argument(
    '--no-git-audit',
    action='store_true',
    help='Skip the Git delivery audit entirely (faster, blind to unpushed work).',
)
args = parser.parse_args()
root = find_root()

if args.git_audit_json:
    print(json.dumps(audit_git_state(root), ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0)

detail = args.git_audit and not args.no_git_audit
items = run_doctor(root, git_audit=not (detail or args.no_git_audit))
for item in items:
    print(f'{item.status.upper():4} {item.name}: {item.message}')
report = None
if detail:
    report = audit_git_state(root)
    print()
    print(format_audit(report))
    if report.get('error'):
        print(f'AUDIT UNAVAILABLE: {report["error"]}', file=sys.stderr)
offers = offer_install_lines(check_toolchain(root))
if args.offer_install or offers:
    if offers:
        print('OFFER install fallback (or newer):')
        for line in offers:
            print(f'  {line}')
    elif args.offer_install:
        print('OFFER: all declared tools meet the minimum pin.')
raise SystemExit(1 if any(item.status == 'fail' for item in items) else 0)
