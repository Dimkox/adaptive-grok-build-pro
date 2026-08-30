#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
scratch="$(mktemp -d)"
cleanup() {
  rm -rf -- "$scratch"
}
trap cleanup EXIT

checkout="$scratch/checkout"
mkdir -p "$checkout"
tar -C "$root" \
  --exclude=.git --exclude=.venv --exclude='*/.venv' --exclude=.coverage \
  -cf - . | tar -C "$checkout" -xf -

test ! -e "$checkout/trust-ci/.venv"
git -C "$checkout" init -q
git -C "$checkout" config user.name clean-runner
git -C "$checkout" config user.email clean-runner@example.invalid
git -C "$checkout" add -A
git -C "$checkout" commit -qm baseline
printf '\nclean-runner-simulation\n' >> "$checkout/trust-ci/README.md"

fake_bin="$scratch/bin"
mkdir -p "$fake_bin"
printf '#!/bin/sh\nexit 97\n' > "$fake_bin/docker"
chmod +x "$fake_bin/docker"

(
  cd "$checkout"
  env \
    GROK_VERIFY_CAPABILITY=repository-sandbox \
    PATH="$fake_bin:$PATH" \
    PYTHONPATH=. \
    python3 scripts/grok_verify.py --mode pr --no-record --json \
      > "$scratch/report.json"
)

python3 - "$scratch/report.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding='utf-8'))
names = {item['name'] for item in report['checks']}
if report['status'] != 'pass':
    raise SystemExit('clean repository verification failed')
if report.get('execution_capability') != 'repository-sandbox':
    raise SystemExit('repository-sandbox capability was not recorded')
if 'trust-ci-production-promotion' in names:
    raise SystemExit('host PostgreSQL bundle leaked into repository sandbox')
PY

printf 'clean exact-SHA repository runner simulation: PASS\n'
