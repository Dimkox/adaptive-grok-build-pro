#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

from adaptive_grok.stable_synthesis import Journal, Monitor, SynthesisError, synthesize  # noqa: E402
from adaptive_grok.util import load_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Local stable-workflow synthesis and read-only upstream review intake")
    sub = parser.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze")
    analyze.add_argument("intent", help="path to a local JSON intent")
    sub.add_parser("status")
    check = sub.add_parser("check")
    check.add_argument("--force", action="store_true")
    sub.add_parser("journal-verify")
    args = parser.parse_args()
    try:
        if args.command == "analyze":
            intent = load_json(Path(args.intent))
            result = synthesize(intent)
            payload = asdict(result)
        elif args.command == "status":
            payload = Monitor(ROOT).status()
        elif args.command == "check":
            payload = Monitor(ROOT).check(force=args.force)
        else:
            entries = Journal(ROOT).read()
            payload = {"ok": True, "entries": len(entries), "head_digest": entries[-1]["digest"] if entries else "0" * 64}
    except (SynthesisError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)[:160]}, sort_keys=True))
        return 2
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=lambda value: asdict(value)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
