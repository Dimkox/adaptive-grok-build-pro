from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

import argparse

from adaptive_grok.receipts import write_receipt
from adaptive_grok.review_evidence import ReviewEvidenceError
from adaptive_grok.util import find_root

parser = argparse.ArgumentParser(description='Record a fingerprint-bound local review receipt from a validated structured report.')
parser.add_argument('kind', choices=['code_review', 'test_review', 'bitrix_review', 'security_review', 'data_review', 'release_review'])
parser.add_argument('--status', choices=['pass', 'fail'], required=True)
parser.add_argument('--report', required=True)
args = parser.parse_args()
root = find_root()
try:
    path = write_receipt(root, args.kind, args.status, args.report)
except (ReviewEvidenceError, RuntimeError, ValueError) as exc:
    raise SystemExit(f'Review report rejected: {exc}') from exc
print(path.relative_to(root))
