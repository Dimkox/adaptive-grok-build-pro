from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
# Offline operator tests exercise the existing sibling delivery and routing
# modules from this checkout; no installed runtime dependency is introduced.
for source in (ROOT / "factory/src", ROOT / "delivery/src", ROOT / ".grok-stack"):
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
