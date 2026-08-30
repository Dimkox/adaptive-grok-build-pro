#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
compose_file="$root/trust-ci/compose.test.yaml"
project_name="adaptive-trust-ci-pgrestore-${USER:-ci}-$$"
backup_dir="$(mktemp -d)"

compose() {
  docker compose --project-name "$project_name" -f "$compose_file" "$@"
}

cleanup() {
  compose down --volumes --remove-orphans >/dev/null 2>&1 || true
  rm -rf -- "$backup_dir"
}
trap cleanup EXIT

compose up -d --wait postgres-test postgres-restore-test
compose build postgres-integration
compose run --rm postgres-integration python3 -m tests.postgres_restart_probe seed
dump="$backup_dir/disposable.dump"
manifest="$backup_dir/disposable.manifest.json"
compose exec -T postgres-test pg_dump \
  --username trust_ci_admin_test --dbname trust_ci_test \
  --format custom --no-owner >"$dump"
python3 - "$dump" "$manifest" <<'PY'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

dump = Path(sys.argv[1])
manifest = Path(sys.argv[2])
manifest.write_text(json.dumps({
    'schema_version': 1,
    'created_at': datetime.now(timezone.utc).isoformat(),
    'database_label': 'disposable-drill',
    'dump_file': dump.name,
    'format': 'custom',
    'size_bytes': dump.stat().st_size,
    'sha256': hashlib.sha256(dump.read_bytes()).hexdigest(),
}, sort_keys=True, separators=(',', ':')) + '\n', encoding='utf-8')
PY
compose run --rm --no-deps \
  --volume "$backup_dir:/backup:ro" \
  postgres-integration python3 -m adaptive_trust_ci.cli backup-verify \
  --dump "/backup/$(basename "$dump")" \
  --manifest "/backup/$(basename "$manifest")"
compose cp "$dump" postgres-restore-test:/tmp/disposable.dump
compose exec -T postgres-restore-test pg_restore \
  --username trust_ci_restore_admin --dbname trust_ci_restore \
  --clean --if-exists --no-owner --exit-on-error \
  /tmp/disposable.dump
compose run --rm --no-deps \
  --env TRUST_CI_TEST_DATABASE_URL=postgresql://trust_ci_restore_admin:trust_ci_restore_admin_password@postgres-restore-test:5432/trust_ci_restore \
  postgres-integration python3 -m tests.postgres_restart_probe verify
compose exec -T --env PGPASSWORD=trust_ci_worker_test_password postgres-restore-test \
  psql --host 127.0.0.1 --username trust_ci_worker --dbname trust_ci_restore \
  --no-psqlrc --set ON_ERROR_STOP=1 --command 'SELECT count(*) FROM trust_ci_jobs;'
compose exec -T --env PGPASSWORD=trust_ci_deployer_test_password postgres-restore-test \
  psql --host 127.0.0.1 --username trust_ci_deployer --dbname trust_ci_restore \
  --no-psqlrc --set ON_ERROR_STOP=1 --command \
  "SELECT count(*) FROM trust_ci_get_promotion_consumption('11111111-1111-4111-8111-111111111111','33333333-3333-4333-8333-333333333333');"
compose exec -T --env PGPASSWORD=trust_ci_api_test_password postgres-restore-test \
  psql --host 127.0.0.1 --username trust_ci_api --dbname trust_ci_restore \
  --no-psqlrc --set ON_ERROR_STOP=1 --command \
  "SELECT count(*) FROM trust_ci_list_promotion_events('11111111-1111-4111-8111-111111111111', 10);"
printf 'postgres backup/restore drill: PASS\n'
