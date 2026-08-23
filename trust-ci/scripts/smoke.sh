#!/usr/bin/env bash
set -euo pipefail

base_url="${TRUST_CI_PUBLIC_BASE_URL:-http://127.0.0.1:8080}"
compose_file="${TRUST_CI_COMPOSE_FILE:-trust-ci/compose.yaml}"

python3 - <<'PY'
from pathlib import Path
root = Path.cwd()
workflows = root / '.github' / 'workflows'
if workflows.exists():
    raise SystemExit('GitHub Actions workflows are forbidden')
for required in (
    root / 'trust-ci/sql/001_schema.sql',
    root / 'trust-ci/config/policy.example.json',
    root / 'trust-ci/compose.yaml',
):
    if not required.is_file():
        raise SystemExit(f'missing: {required}')
PY

curl -fsS "${base_url%/}/health/live" >/dev/null
curl -fsS "${base_url%/}/health/ready" >/dev/null

docker compose -f "$compose_file" config >/dev/null
printf 'trust-ci smoke: PASS\n'
