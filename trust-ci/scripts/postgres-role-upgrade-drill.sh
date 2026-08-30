#!/usr/bin/env bash
set -Eeuo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
project_name="adaptive-trust-ci-pgupgrade-${USER:-ci}-$$"
compose=(docker compose --project-name "$project_name" --project-directory "$root/trust-ci" -f "$root/trust-ci/compose.test.yaml")
cleanup() { "${compose[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT

"${compose[@]}" up -d --wait postgres-test
"${compose[@]}" exec -T postgres-test psql -U trust_ci_admin_test -d trust_ci_test -v ON_ERROR_STOP=1 \
  -c 'REVOKE ALL ON SCHEMA public FROM trust_ci_deployer; REVOKE CONNECT ON DATABASE trust_ci_test FROM trust_ci_deployer; DROP ROLE trust_ci_deployer'
"${compose[@]}" build postgres-integration
common_env=(
  --env TRUST_CI_TEST_DATABASE_URL=postgresql://trust_ci_migrator:trust_ci_migrator_test_password@postgres-test:5432/trust_ci_test
  --env TRUST_CI_TEST_ADMIN_DATABASE_URL=postgresql://trust_ci_admin_test:trust_ci_admin_test_password@postgres-test:5432/trust_ci_test
)
"${compose[@]}" run --rm "${common_env[@]}" postgres-integration python3 -m tests.postgres_upgrade_probe prepare
"${compose[@]}" exec -T --env PGHOST=127.0.0.1 postgres-test bash /opt/adaptive-trust-ci/postgres-upgrade/004_deployer_role.sh
"${compose[@]}" exec -T postgres-test psql -U trust_ci_admin_test -d trust_ci_test -v ON_ERROR_STOP=1 \
  -c 'ALTER ROLE trust_ci_deployer BYPASSRLS'
"${compose[@]}" exec -T --env PGHOST=127.0.0.1 postgres-test bash /opt/adaptive-trust-ci/postgres-upgrade/004_deployer_role.sh
"${compose[@]}" run --rm "${common_env[@]}" postgres-integration python3 -m tests.postgres_upgrade_probe verify
printf 'postgres 003-to-004 role upgrade drill: PASS\n'
