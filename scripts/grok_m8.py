#!/usr/bin/env python3
"""Offline consumer for the checked-in owner-confirmed local M8 policy."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "factory/src"))
from adaptive_factory.owner_autonomy import OwnerCaseV1, OwnerPolicyV1, OwnerRuntime, current_context


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("status", "activate", "admit", "revoke"))
    parser.add_argument("--action", default="local_read")
    args = parser.parse_args()
    try:
        policy = OwnerPolicyV1.from_dict(json.loads((ROOT / "factory/runtime/owner-autonomy-policy.v1.json").read_text()))
        runtime = OwnerRuntime(ROOT / ".grok-stack/runtime/owner-autonomy")
        now = datetime.now(timezone.utc)
        if args.operation == "revoke":
            result = runtime.revoke(policy, now=now)
        else:
            case = OwnerCaseV1.from_project_state(json.loads((ROOT / "PROJECT_STATE.json").read_text()))
            context = current_context(ROOT)
            if args.operation == "admit":
                result = runtime.admit(policy, case, context, args.action, now=now)
            else:
                result = getattr(runtime, args.operation)(policy, case, context, now=now)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        result = {"schema_version": 1, "allowed": False, "level": "L0", "authority_ceiling": "L2",
                  "reason": "input_unavailable", "external_authority": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["allowed"] or (args.operation == "revoke" and result["reason"] == "revoked") else 2


if __name__ == "__main__":
    raise SystemExit(main())
