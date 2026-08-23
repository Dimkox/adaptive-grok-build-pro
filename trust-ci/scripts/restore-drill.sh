#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  printf 'usage: %s <backup.dump> <backup.manifest.json>\n' "$0" >&2
  exit 64
fi

: "${TRUST_CI_RESTORE_DATABASE_URL:?set disposable TRUST_CI_RESTORE_DATABASE_URL}"

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
compose_file="$root/trust-ci/compose.yaml"
dump="$(realpath "$1")"
manifest="$(realpath "$2")"

if [[ "$(dirname "$dump")" != "$(dirname "$manifest")" ]]; then
  printf 'dump and manifest must be in the same directory\n' >&2
  exit 65
fi

backup_dir="$(dirname "$dump")"
dump_name="$(basename "$dump")"
manifest_name="$(basename "$manifest")"

cd "$root/trust-ci"

docker compose -f "$compose_file" run --rm --no-deps \
  --volume "$backup_dir:/restore:ro" \
  api backup-verify \
  --dump "/restore/$dump_name" \
  --manifest "/restore/$manifest_name"

docker compose -f "$compose_file" run --rm --no-deps \
  --env TRUST_CI_RESTORE_DATABASE_URL="$TRUST_CI_RESTORE_DATABASE_URL" \
  --volume "$backup_dir:/restore:ro" \
  api restore-drill \
  --dump "/restore/$dump_name" \
  --manifest "/restore/$manifest_name" \
  --confirm-disposable
