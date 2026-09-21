from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

import json
import os

from adaptive_grok.package_status import collect_worktree, inspect_package, receipt_inputs_unavailable
from adaptive_grok.receipts import validate_evidence
from adaptive_grok.human_gates import ARTIFACT_NOTICE, gate_statuses
from adaptive_grok.state import get_active_change, get_active_route, get_agent_state
from adaptive_grok.util import find_root

root = find_root()
# Applies to existing receipt-validation Git reads as well as the new snapshot.
os.environ['GIT_OPTIONAL_LOCKS'] = '0'
route = get_active_route(root)
active = get_active_change(root)
package = inspect_package(root, route, active)
worktree = collect_worktree(root, route, package['initial_checkpoint'])
evidence_gaps = []
if route:
    evidence_gaps = (
        ['package: receipt validation unavailable until unsafe or unreadable selected inputs are resolved']
        if receipt_inputs_unavailable(package) else validate_evidence(root, route)
    )
print(json.dumps({
    'route': route,
    'change': active,
    'agents': get_agent_state(root),
    'human_gates': gate_statuses(root),
    'human_gate_notice': ARTIFACT_NOTICE,
    'evidence_gaps': evidence_gaps,
    'package_completeness': package,
    'package_incomplete': package['findings'],
    'worktree': worktree,
}, ensure_ascii=True, indent=2))
