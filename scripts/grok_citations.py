from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

import argparse
import json

from adaptive_grok.citations import audit_documents
from adaptive_grok.util import find_root

parser = argparse.ArgumentParser(
    description=(
        'Report identifier tokens cited in a document that exist in no machine-state '
        'receipt, digest or Git object. Existence only: a real id can still be cited for '
        'the wrong claim.'
    )
)
parser.add_argument('documents', nargs='*', help='report/PR-body/commit-message files, or - for stdin')
parser.add_argument('--json', action='store_true')
parser.add_argument(
    '--warn-only',
    action='store_true',
    help='exit 0 even when unresolved identifiers are reported',
)
parser.add_argument('--max-bytes', type=int, default=2 * 1024 * 1024)
args = parser.parse_args()

root = find_root()
documents: list[tuple[str, str]] = []
unreadable: list[str] = []
for name in args.documents or ['-']:
    if name == '-':
        documents.append(('<stdin>', sys.stdin.read()))
        continue
    path = Path(name)
    try:
        if not path.is_file():
            raise OSError('not a regular file')
        size = path.stat().st_size
        if size > args.max_bytes:
            raise OSError(f'{size} bytes exceeds --max-bytes {args.max_bytes}')
        documents.append((path.name, path.read_text(encoding='utf-8', errors='replace')))
    except OSError as exc:
        unreadable.append(f'{name}: {exc}')

report = audit_documents(root, documents)
report['unreadable_documents'] = unreadable
unresolved = report['unresolved']

if args.json:
    print(json.dumps(report, ensure_ascii=True, indent=2))
else:
    for item in unresolved:
        print(f"MISSING {item['token']} cited at {item['document']}:{item['line']}")
    for note in unreadable:
        print(f'UNREADABLE {note}', file=sys.stderr)
    print(
        f"CITATION {report['status'].upper()}: {report['citation_count']} token citation(s) "
        f"({report['distinct_tokens']} distinct) from {len(documents)} document(s); "
        f"{report['unresolved_count']} unresolved against "
        f"{report['corpus_identifiers']} identifier(s) in {report['corpus_files']} machine-state file(s)"
    )

if unresolved and not args.warn_only:
    raise SystemExit(1)
raise SystemExit(0)
