#!/usr/bin/env python3
"""Explicit CLI opt-in for the supported Linux process adapter."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from linux_process_adapter import LinuxProcessRuntimeAdapter
from setup_manager import InstallerError, main as setup_main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--runtime-config", type=Path, required=True)
    known, remaining = parser.parse_known_args(argv)
    try:
        adapter = LinuxProcessRuntimeAdapter(known.root, known.runtime_config)
        return setup_main([*remaining, "--root", str(known.root)], adapter=adapter)
    except (InstallerError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"schema_version": "factory-error/v1",
                          "error": exc.code if isinstance(exc, InstallerError) else "OPERATION_FAILED"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
