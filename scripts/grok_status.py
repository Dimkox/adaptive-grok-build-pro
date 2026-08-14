from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

import json

from adaptive_grok.receipts import validate_evidence
from adaptive_grok.state import get_active_change, get_active_route, get_agent_state
from adaptive_grok.util import find_root

root = find_root()
route = get_active_route(root)
print(json.dumps({
    'route': route,
    'change': get_active_change(root),
    'agents': get_agent_state(root),
    'evidence_gaps': validate_evidence(root, route) if route else [],
}, ensure_ascii=False, indent=2))
