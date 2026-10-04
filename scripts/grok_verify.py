from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

import argparse
import json
import os
import signal

from adaptive_grok.util import find_root
from adaptive_grok.python_test_runner import RunCancelled, RunnerError, _cancellation
from adaptive_grok.verification import CheckResult, VerificationCancelled, _record_verification_receipt, verify, verify_named_tests
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
parser.add_argument('--keep-going', action='store_true', help='collect diagnostic failures; safety preflight and admission still apply')
parser.add_argument('--test', action='append', dest='tests', help='explicit tests.test_module[.Class[.test_method]] observation in fast mode')
parser.add_argument('--budget', type=int, default=None, help='named smoke budget in seconds, from 1 to 180 (default 180)')
parser.add_argument(
    '--full-scope',
    action='store_true',
    help='force the full PR suite even when the inventory is documentation/state-only',
)
args = parser.parse_args()
if args.tests is not None and (args.mode != 'fast' or not args.no_record or args.profiles or args.full_scope or args.keep_going):
    parser.error('named tests require --mode fast --no-record without profiles, full-scope or keep-going')
if args.budget is not None and args.tests is None:
    parser.error('--budget requires explicit --test targets')
if args.full_scope:
    os.environ[FORCE_FULL_VARIABLE] = '1'
signal_exit = None
root = find_root()
try:
    if args.tests is not None:
        report = verify_named_tests(root, args.tests, budget=args.budget if args.budget is not None else 180)
    else:
        report = verify(root, args.mode, args.profiles, record=not args.no_record, keep_going=args.keep_going)
except RunnerError as exc:
    parser.error(str(exc))
except VerificationCancelled as exc:
    report = exc.report
    signal_exit = exc.code


def _emit_report():
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
            f"focused_tests={','.join(scope.get('focused_tests', [])) or 'none'} "
            f"terminal={report.get('terminal_state', 'completed')} "
            f"checks={report.get('check_status', report['status'])} "
            f"receipt={report.get('evidence_status', 'not_recorded')}"
        )


try:
    with _cancellation() as cancellation:
        _emit_report()
        cancellation.check()
except (RunCancelled, OSError, TypeError, ValueError) as exc:
    report.setdefault('check_status', report['status'])
    report['status'] = 'fail'
    if isinstance(exc, RunCancelled):
        signal_exit = signal_exit or exc.code
        report['terminal_state'] = 'cancelled'
        report['cancellation'] = {'signal': signal.Signals(exc.signal_number).name, 'stage': 'report-publication'}
    report['checks'].append(CheckResult('report-publication', 'cancelled' if isinstance(exc, RunCancelled) else 'fail',
                                       f'{type(exc).__name__}: {str(exc)[:512]}').to_dict())
    if not args.no_record and report.get('route_id') and report.get('tree_fingerprint'):
        _record_verification_receipt(root, report, report['tree_fingerprint'])
    try:
        print(json.dumps(report, ensure_ascii=True, indent=2), file=sys.stderr)
    except (OSError, TypeError, ValueError):
        pass
raise SystemExit(signal_exit if signal_exit is not None else (0 if report['status'] == 'pass' else 1))
