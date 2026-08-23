#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
compose_file="$root/trust-ci/compose.test.yaml"
project_name="adaptive-trust-ci-pgtest-${USER:-ci}-$$"

cleanup() {
  docker compose \
    --project-name "$project_name" \
    -f "$compose_file" \
    down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

cleanup

docker compose \
  --project-name "$project_name" \
  -f "$compose_file" \
  up \
  --build \
  --abort-on-container-exit \
  --exit-code-from postgres-integration \
  postgres-integration
