"""Repository entrypoint for explicit local landing publication operations."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for component in (ROOT / ".grok-stack", ROOT / "delivery/src", ROOT / "factory/src"):
    sys.path.insert(0, str(component))

from adaptive_factory.landing_publication_cli import main

if __name__ == "__main__":
    raise SystemExit(main(control_root=ROOT))
