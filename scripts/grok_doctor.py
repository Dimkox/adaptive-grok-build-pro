from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.doctor import run_doctor
from adaptive_grok.util import find_root

items = run_doctor(find_root())
for item in items:
    print(f'{item.status.upper():4} {item.name}: {item.message}')
raise SystemExit(1 if any(item.status == 'fail' for item in items) else 0)
