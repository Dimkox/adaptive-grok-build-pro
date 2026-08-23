#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
compose_file="$root/trust-ci/compose.test.yaml"
project_name="adaptive-trust-ci-pgrestart-${USER:-ci}-$$"

compose() {
  docker compose --project-name "$project_name" -f "$compose_file" "$@"
}

cleanup() {
  compose down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

cleanup
compose up -d --wait postgres-test
compose run --rm postgres-integration python3 -m tests.postgres_restart_probe seed
compose restart postgres-test
compose up -d --wait postgres-test
compose run --rm postgres-integration python3 -m tests.postgres_restart_probe verify
printf 'postgres restart drill: PASS\n'
