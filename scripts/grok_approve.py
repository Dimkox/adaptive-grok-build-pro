"""Offline human approval interface; this script cannot mint a local authority token."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

from adaptive_grok.ci_cli import main

if __name__ == "__main__":
    mapping = {
        "request": "approval-request",
        "sign": "approval-sign",
        "import": "approval-import",
        "keygen": "keygen",
    }
    argv = sys.argv[1:]
    if not argv or argv[0] not in mapping:
        raise SystemExit("usage: grok_approve.py {request|sign|import|keygen} ...")
    raise SystemExit(main([mapping[argv[0]], *argv[1:]]))
