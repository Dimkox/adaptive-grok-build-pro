from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.manifest import generate_manifest
from adaptive_grok.util import find_root


if __name__ == '__main__':
    root = find_root(ROOT)
    manifest = generate_manifest(root)
    print(manifest)
