"""Account for one explicit local evidence snapshot without changing runtime state."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".grok-stack"))

from adaptive_grok.history import HistoryError, load_history, summarize_history


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline historical evidence accounting; no M8 qualification or authority effects.")
    parser.add_argument("snapshot", help="Explicit UTF-8 JSON snapshot file (maximum 8 MiB).")
    args = parser.parse_args()
    try:
        report = summarize_history(load_history(args.snapshot))
    except HistoryError as exc:
        print(f"history: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
