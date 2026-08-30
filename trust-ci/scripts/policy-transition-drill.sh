#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd "$root"
PYTHONPATH=trust-ci/src:trust-ci/tests \
  trust-ci/.venv/bin/python -m unittest -v \
  test_policy_transition.DisposablePolicyTransitionTests
printf 'automated-only policy transition drill: PASS\n'
