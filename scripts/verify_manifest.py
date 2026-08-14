from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.manifest import verify_manifest

errors = verify_manifest(ROOT)
if errors:
    for error in errors:
        print(f'FAIL {error}')
    raise SystemExit(1)
print('PASS manifest integrity')
