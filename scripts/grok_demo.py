#!/usr/bin/env python3
from __future__ import annotations

import argparse
import errno
import sys
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

from adaptive_grok.demo_http import create_server  # noqa: E402
from adaptive_grok.util import find_root  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local read-only investor demo dashboard.")
    parser.add_argument("--port", type=int, default=8765, help="loopback port (default: 8765)")
    parser.add_argument("--open", action="store_true", help="open the local URL in the default browser")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = find_root(ROOT)
    try:
        server = create_server(root, port=args.port)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            print(f"Port {args.port} is in use; choose another with --port.", file=sys.stderr)
            return 2
        print("The local demo could not start.", file=sys.stderr)
        return 2
    except (RuntimeError, ValueError):
        print("The local demo could not validate its bundled resources.", file=sys.stderr)
        return 2
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"Adaptive Grok Build Pro demo: {url}", flush=True)
    print("Local read-only demo; press Ctrl-C to stop.", flush=True)
    if args.open:
        try:
            webbrowser.open(url)
        except OSError:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDemo stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
