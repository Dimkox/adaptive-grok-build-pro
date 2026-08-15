from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.doctor import run_doctor
from adaptive_grok.toolchain import check_toolchain, offer_install_lines
from adaptive_grok.util import find_root

parser = argparse.ArgumentParser(description='Health check. Prints toolchain pins and install offers for missing or old tools.')
parser.add_argument(
    '--offer-install',
    action='store_true',
    help='Print fallback/newer install commands for tools that are missing or below minimum.',
)
args = parser.parse_args()
root = find_root()
items = run_doctor(root)
for item in items:
    print(f'{item.status.upper():4} {item.name}: {item.message}')
offers = offer_install_lines(check_toolchain(root))
if args.offer_install or offers:
    if offers:
        print('OFFER install fallback (or newer):')
        for line in offers:
            print(f'  {line}')
    elif args.offer_install:
        print('OFFER: all declared tools meet the minimum pin.')
raise SystemExit(1 if any(item.status == 'fail' for item in items) else 0)
