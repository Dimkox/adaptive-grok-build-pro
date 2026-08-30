#!/usr/bin/env bash
set -euo pipefail

for tool in docker python3 cosign sha256sum; do
  command -v "$tool" >/dev/null 2>&1 || {
    printf 'required tool is missing: %s\n' "$tool" >&2
    exit 69
  }
done

: "${TRUST_CI_SUPPLY_CHAIN_DIR:?set signed supply-chain directory}"
: "${COSIGN_PUBLIC_KEY:?set cosign public key path}"
: "${TRUST_CI_PROMOTION_ARTIFACT_PATH:?set exact promotion artifact path}"
: "${TRUST_CI_PROMOTION_MANIFEST_SHA256:?set verified promotion manifest SHA-256}"

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
bundle="$(realpath "$TRUST_CI_SUPPLY_CHAIN_DIR")"
compose_env="$(realpath "${TRUST_CI_COMPOSE_ENV_FILE:-$root/trust-ci/.env}")"
deployed_policy="$(realpath "${TRUST_CI_DEPLOY_POLICY_PATH:-$root/trust-ci/runtime/policy.json}")"
promotion_artifact="$(realpath "$TRUST_CI_PROMOTION_ARTIFACT_PATH")"

for required in \
  "$bundle/supply-chain.manifest.json" \
  "$bundle/supply-chain.manifest.json.sha256" \
  "$bundle/supply-chain.manifest.json.sig" \
  "$bundle/artifacts.sha256" \
  "$bundle/policy.json" \
  "$promotion_artifact" \
  "$compose_env" \
  "$deployed_policy"; do
  [[ -f "$required" ]] || {
    printf 'missing supply-chain input: %s\n' "$required" >&2
    exit 66
  }
done

(
  cd "$bundle"
  sha256sum --check supply-chain.manifest.json.sha256
  cosign verify-blob \
    --key "$COSIGN_PUBLIC_KEY" \
    --signature supply-chain.manifest.json.sig \
    supply-chain.manifest.json >/dev/null
)

mapfile -t images < <(
  python3 - \
    "$bundle/supply-chain.manifest.json" \
    "$bundle/policy.json" \
    "$bundle/artifacts.sha256" \
    "$deployed_policy" \
    "$compose_env" \
    "$promotion_artifact" \
    "$TRUST_CI_PROMOTION_MANIFEST_SHA256" <<'PY'
import hashlib
import json
import re
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
bundle_policy_path = Path(sys.argv[2])
artifacts_path = Path(sys.argv[3])
deployed_policy_path = Path(sys.argv[4])
compose_env_path = Path(sys.argv[5])
promotion_artifact_path = Path(sys.argv[6]).resolve()
expected_manifest_sha256 = sys.argv[7]
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
bundle_policy = json.loads(bundle_policy_path.read_text(encoding='utf-8'))
deployed_policy = json.loads(deployed_policy_path.read_text(encoding='utf-8'))
if manifest.get('schema_version') != 1:
    raise SystemExit('unsupported supply-chain manifest')

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

if not re.fullmatch(r'[0-9a-f]{64}', expected_manifest_sha256):
    raise SystemExit('configured promotion manifest digest is malformed')
if sha(manifest_path) != expected_manifest_sha256:
    raise SystemExit('configured promotion manifest digest is not the signed manifest')

if manifest.get('policy_sha256') != sha(bundle_policy_path):
    raise SystemExit('bundle policy hash does not match signed manifest')
if manifest.get('artifacts_file') != artifacts_path.name:
    raise SystemExit('artifact checksum filename does not match signed manifest')
if manifest.get('artifacts_sha256') != sha(artifacts_path):
    raise SystemExit('artifact checksum file does not match signed manifest')
try:
    relative_artifact = promotion_artifact_path.relative_to(manifest_path.parent.resolve()).as_posix()
except ValueError as exc:
    raise SystemExit('promotion artifact escaped signed bundle') from exc
artifact_entries = {}
for raw in artifacts_path.read_text(encoding='utf-8').splitlines():
    digest, separator, relative = raw.partition('  ')
    if separator != '  ' or not re.fullmatch(r'[0-9a-f]{64}', digest) or not relative:
        raise SystemExit('artifact checksum index is malformed')
    if relative in artifact_entries:
        raise SystemExit('artifact checksum index contains duplicates')
    artifact_entries[relative] = digest
if artifact_entries.get(relative_artifact) != sha(promotion_artifact_path):
    raise SystemExit('promotion artifact does not match signed artifact index')
if sha(bundle_policy_path) != sha(deployed_policy_path):
    raise SystemExit('deployed policy is not the signed bundle policy')
images = manifest.get('images')
if not isinstance(images, dict) or set(images) != {'api', 'worker', 'runner'}:
    raise SystemExit('manifest image set is incomplete')
pattern = re.compile(r'^.+@sha256:[0-9a-f]{64}$')
for name, image in images.items():
    if not isinstance(image, str) or pattern.fullmatch(image) is None:
        raise SystemExit(f'{name} image is not immutable')
if bundle_policy.get('sandbox', {}).get('image') != images['runner']:
    raise SystemExit('signed policy runner_image does not match manifest')
if deployed_policy.get('sandbox', {}).get('image') != images['runner']:
    raise SystemExit('deployed policy runner_image does not match manifest')

environment = {}
for raw in compose_env_path.read_text(encoding='utf-8').splitlines():
    line = raw.strip()
    if not line or line.startswith('#'):
        continue
    if '=' not in line:
        raise SystemExit(f'invalid compose environment line: {raw!r}')
    key, value = line.split('=', 1)
    environment[key.strip()] = value.strip()
expected = {
    'TRUST_CI_API_IMAGE': images['api'],
    'TRUST_CI_WORKER_IMAGE': images['worker'],
    'TRUST_CI_RUNNER_IMAGE': images['runner'],
}
for key, value in expected.items():
    if environment.get(key) != value:
        raise SystemExit(f'{key} does not match signed manifest')
for name in ('api', 'worker', 'runner'):
    print(images[name])
PY
)

if [[ ${#images[@]} -ne 3 ]]; then
  printf 'supply-chain verifier did not receive exactly three image references\n' >&2
  exit 65
fi

(
  cd "$bundle"
  sha256sum --check artifacts.sha256
)

for image in "${images[@]}"; do
  cosign verify --key "$COSIGN_PUBLIC_KEY" "$image" >/dev/null
  docker pull "$image" >/dev/null
done

printf 'supply-chain verification: PASS\n'
