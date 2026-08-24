#!/usr/bin/env bash
set -euo pipefail

base_url="${TRUST_CI_PUBLIC_BASE_URL:-http://127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}}"
compose_file="${TRUST_CI_COMPOSE_FILE:-trust-ci/compose.yaml}"
: "${TRUST_CI_READ_TOKEN:?export TRUST_CI_READ_TOKEN for the authenticated metrics probe}"

python3 - <<'PY'
from pathlib import Path
root = Path.cwd()
workflows = root / '.github' / 'workflows'
if workflows.exists():
    raise SystemExit('GitHub Actions workflows are forbidden')
for required in (
    root / 'trust-ci/sql/001_schema.sql',
    root / 'trust-ci/sql/002_operational_indexes.sql',
    root / 'trust-ci/config/policy.example.json',
    root / 'trust-ci/compose.yaml',
    root / 'trust-ci/scripts/postgres-integration.sh',
    root / 'trust-ci/scripts/postgres-restart-drill.sh',
    root / 'trust-ci/scripts/restore-drill.sh',
):
    if not required.is_file():
        raise SystemExit(f'missing: {required}')
PY

curl -fsS "${base_url%/}/health/live" >/dev/null
curl -fsS "${base_url%/}/health/ready" >/dev/null
curl -fsS \
  -H "Authorization: Bearer $TRUST_CI_READ_TOKEN" \
  "${base_url%/}/metrics" \
  | grep -q '^adaptive_trust_ci_policy_info'

rendered="$(docker compose -f "$compose_file" config)"
printf '%s\n' "$rendered" | grep -q 'docker-engine:'
printf '%s\n' "$rendered" | grep -q 'DOCKER_HOST: tcp://docker-engine:2375'
if printf '%s\n' "$rendered" | grep -q '/var/run/docker.sock'; then
  printf 'worker topology still exposes the host Docker socket\n' >&2
  exit 1
fi

docker compose -f "$compose_file" run --rm --no-deps api migration-status >/dev/null
docker compose -f "$compose_file" ps >/dev/null
printf 'trust-ci smoke: PASS\n'
