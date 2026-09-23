#!/usr/bin/env bash
set -euo pipefail

base_url="${TRUST_CI_PUBLIC_BASE_URL:-http://127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}}"
compose_file="${TRUST_CI_COMPOSE_FILE:-trust-ci/compose.yaml}"
: "${TRUST_CI_READ_TOKEN:?export TRUST_CI_READ_TOKEN for the authenticated metrics probe}"

resolve_command() {
  local name="$1"
  local resolved=''
  local candidate=''
  local search_dirs="${TRUST_CI_TOOL_PATHS-}"

  if [[ -n "$search_dirs" ]]; then
    while IFS= read -r candidate; do
      [[ -n "$candidate" ]] || continue
      candidate="${candidate%/}/$name"
      if [[ -x "$candidate" && ! -d "$candidate" ]]; then
        printf '%s\n' "$candidate"
        return 0
      fi
    done < <(tr ':' '\n' <<<"$search_dirs")
  fi

  resolved="$(command -v -- "$name" 2>/dev/null || true)"
  if [[ -n "$resolved" && -x "$resolved" ]]; then
    printf '%s\n' "$resolved"
    return 0
  fi

  search_dirs="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
  while IFS= read -r candidate; do
    [[ -n "$candidate" ]] || continue
    candidate="${candidate%/}/$name"
    if [[ -x "$candidate" && ! -d "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done < <(tr ':' '\n' <<<"$search_dirs")

  printf 'required command not found: %s\n' "$name" >&2
  return 127
}

python3_bin="$(resolve_command python3)"
curl_bin="$(resolve_command curl)"
grep_bin="$(resolve_command grep)"
docker_bin="$(resolve_command docker)"

"${python3_bin}" - <<'PY'
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

health_live="$("${curl_bin}" -fsS "${base_url%/}/health/live")"
[[ -n "$health_live" ]] || {
  printf 'health/live returned an empty response\n' >&2
  exit 1
}

health_ready="$("${curl_bin}" -fsS "${base_url%/}/health/ready")"
[[ -n "$health_ready" ]] || {
  printf 'health/ready returned an empty response\n' >&2
  exit 1
}

metrics="$("${curl_bin}" -fsS \
  -H "Authorization: Bearer $TRUST_CI_READ_TOKEN" \
  "${base_url%/}/metrics")"
[[ -n "$metrics" ]] || {
  printf 'metrics returned an empty response\n' >&2
  exit 1
}
"${grep_bin}" -q '^adaptive_trust_ci_policy_info' <<<"$metrics" || {
  printf 'metrics missing adaptive_trust_ci_policy_info marker\n' >&2
  exit 1
}

rendered="$("${docker_bin}" compose -f "$compose_file" config)"
[[ -n "$rendered" ]] || {
  printf 'docker compose config returned an empty response\n' >&2
  exit 1
}
"${grep_bin}" -q 'docker-engine:' <<<"$rendered" || {
  printf 'rendered Compose missing docker-engine service\n' >&2
  exit 1
}
"${grep_bin}" -q 'DOCKER_HOST: tcp://docker-engine:2375' <<<"$rendered" || {
  printf 'rendered Compose missing isolated Docker host\n' >&2
  exit 1
}
if "${grep_bin}" -q '/var/run/docker.sock' <<<"$rendered"; then
  printf 'worker topology still exposes the host Docker socket\n' >&2
  exit 1
fi

"${docker_bin}" compose -f "$compose_file" run --rm --no-deps api migration-status >/dev/null
"${docker_bin}" compose -f "$compose_file" ps >/dev/null
printf 'trust-ci smoke: PASS\n'
