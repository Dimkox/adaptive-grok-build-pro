#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 scripts/grok_doctor.py --offer-install
python3 scripts/install_into.py "$ROOT" --force
python3 -m unittest discover -s tests -v
printf '
Ready. Start Grok Build from: %s
Trust project config/hooks, then describe a development task.
' "$ROOT"
