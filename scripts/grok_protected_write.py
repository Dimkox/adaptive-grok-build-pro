#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.protected_write import ProtectedWriteError, apply_manifest
from adaptive_grok.util import find_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            'Apply an atomic multi-file control-plane edit from a manifest outside '
            'the repository. Every target requires an exact protected-path grant '
            'and an optimistic expected SHA-256.'
        )
    )
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        result = apply_manifest(find_root(ROOT), args.manifest, dry_run=args.dry_run)
    except ProtectedWriteError as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
