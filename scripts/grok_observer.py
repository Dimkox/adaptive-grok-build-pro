#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

from adaptive_grok.external_observer import (  # noqa: E402
    ExternalObserver,
    GitHubTransport,
    ObserverError,
    canonical_bytes,
    load_document,
    load_status,
    parse_config,
    render_text,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit bounded PUBLIC_STATUS.v1 from public GitHub observations and typed local claims.")
    parser.add_argument("command", choices=("observe", "status", "render", "verify-state"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "observe":
            if args.config is None or args.evidence is None:
                raise ObserverError("config_and_evidence_required")
            config_raw = load_document(args.config, error="invalid_config")
            claims_raw = load_document(args.evidence, error="invalid_claims")
            cfg = parse_config(config_raw)
            transport = GitHubTransport(cfg.repository)
            status_value = ExternalObserver(args.root.resolve(), config_raw, claims_raw, transport).check(now=int(time.time()))
        else:
            status_value = load_status(args.root.resolve())
        if args.command == "render":
            sys.stdout.write(render_text(status_value))
        else:
            sys.stdout.buffer.write(canonical_bytes(status_value))
        return 0
    except ObserverError as exc:
        sys.stderr.write(f"observer_error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
