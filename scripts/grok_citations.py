from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

import argparse
import json
import os

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
    help='exit 0 even when identifiers are unresolved or a document could not be read',
)
parser.add_argument(
    '--max-bytes',
    type=int,
    default=2 * 1024 * 1024,
    help='read ceiling applied to every input, stdin included (default: 2 MiB)',
)
args = parser.parse_args()
if args.max_bytes < 1:
    raise SystemExit('--max-bytes must be at least 1')

root = find_root()


def label_for(name: str, path: Path) -> str:
    """Name a document so two files called report.md stay distinguishable.

    The repository-relative path is used when the document is inside the repository; anything
    else keeps the path as the operator typed it, because a bare ``report.md`` from outside the
    tree would collide with a different ``report.md`` inside it.
    """
    try:
        relative = os.path.relpath(path.resolve(), root).replace(os.sep, '/')
    except ValueError:
        return Path(name).as_posix()
    if relative.startswith('..' + os.sep) or relative == '..':
        return Path(name).as_posix()
    return relative


documents: list[tuple[str, str]] = []
unreadable: list[str] = []
for name in args.documents or ['-']:
    if name == '-':
        # The ceiling has to apply here too: an unreadable document may not be reported as an
        # audited one, and stdin is the one input the operator cannot spot by looking at a path.
        raw = sys.stdin.buffer.read(args.max_bytes + 1)
        if len(raw) > args.max_bytes:
            unreadable.append(f'<stdin>: more than {args.max_bytes} bytes on stdin')
            continue
        documents.append(('<stdin>', raw.decode('utf-8', errors='replace')))
        continue
    path = Path(name)
    try:
        if not path.is_file():
            raise OSError('not a regular file')
        size = path.stat().st_size
        if size > args.max_bytes:
            raise OSError(f'{size} bytes exceeds --max-bytes {args.max_bytes}')
        documents.append((label_for(name, path), path.read_text(encoding='utf-8', errors='replace')))
    except OSError as exc:
        unreadable.append(f'{name}: {exc}')

report = audit_documents(root, documents, unreadable=unreadable)
unresolved = report['unresolved']
unreadable = report['unreadable_documents']
declined = report['declined_runs']

if args.json:
    print(json.dumps(report, ensure_ascii=True, indent=2))
else:
    for item in unresolved:
        print(f"MISSING {item['token']} cited at {item['document']}:{item['line']}")
    for note in unreadable:
        print(f'NOT READ {note}')
    if declined:
        breakdown = ' '.join(f'{reason}={count}' for reason, count in report['declined_by_reason'].items())
        print(f'DECLINED {declined} hex run(s) not judged as identifiers ({breakdown})')
    flags = []
    if report['corpus_truncated']:
        flags.append(' corpus-truncated=true')
    if report['git_probes_capped']:
        flags.append(' git-probes-capped=true')
    print(
        f"CITATION {report['status'].upper()}: citations={report['citation_count']} "
        f"distinct={report['distinct_tokens']} unresolved-citations={report['unresolved_count']} "
        f"unresolved-tokens={report['unresolved_distinct_tokens']} declined={declined} "
        f"documents={len(documents)} not-read={len(unreadable)} "
        f"corpus={report['corpus_identifiers']} identifier(s) in {report['corpus_files']} file(s)"
        f"{''.join(flags)}"
    )

if report['status'] == 'error':
    raise SystemExit(0 if args.warn_only else 2)
if unresolved and not args.warn_only:
    raise SystemExit(1)
raise SystemExit(0)
