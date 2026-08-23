#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--confirm-push" || $# -ne 1 ]]; then
  printf 'usage: %s --confirm-push\n' "$0" >&2
  exit 64
fi

for tool in docker python3 trivy syft cosign sha256sum git; do
  command -v "$tool" >/dev/null 2>&1 || {
    printf 'required tool is missing: %s\n' "$tool" >&2
    exit 69
  }
done

: "${TRUST_CI_PYTHON_BASE_IMAGE:?set immutable Python base image}"
: "${TRUST_CI_API_REPOSITORY:?set API registry repository without tag}"
: "${TRUST_CI_WORKER_REPOSITORY:?set worker registry repository without tag}"
: "${TRUST_CI_RUNNER_REPOSITORY:?set runner registry repository without tag}"
: "${TRUST_CI_RELEASE_VERSION:?set release version}"
: "${TRUST_CI_POLICY_TEMPLATE:?set reviewed policy template path}"
: "${TRUST_CI_SUPPLY_CHAIN_DIR:?set output directory}"
: "${COSIGN_PRIVATE_KEY:?set human-controlled cosign private key path}"

if [[ ! "$TRUST_CI_PYTHON_BASE_IMAGE" =~ @sha256:[0-9a-f]{64}$ ]]; then
  printf 'TRUST_CI_PYTHON_BASE_IMAGE must be name@sha256 digest\n' >&2
  exit 65
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
output="$(realpath -m "$TRUST_CI_SUPPLY_CHAIN_DIR")"
policy_template="$(realpath "$TRUST_CI_POLICY_TEMPLATE")"
mkdir -p "$output/metadata" "$output/sbom" "$output/scan"
chmod 700 "$output"

build_image() {
  local name="$1"
  local repository="$2"
  local dockerfile="$3"
  local metadata="$output/metadata/$name.json"
  local tagged="$repository:$TRUST_CI_RELEASE_VERSION"

  if [[ "$repository" == *'@'* || "$repository" == *' '* ]]; then
    printf 'registry repository must not include digest or spaces: %s\n' "$repository" >&2
    exit 65
  fi

  docker buildx build \
    --progress=plain \
    --file "$root/trust-ci/$dockerfile" \
    --build-arg "PYTHON_BASE_IMAGE=$TRUST_CI_PYTHON_BASE_IMAGE" \
    --tag "$tagged" \
    --push \
    --sbom=true \
    --provenance=mode=max \
    --metadata-file "$metadata" \
    "$root/trust-ci" >&2

  local digest
  digest="$(python3 - "$metadata" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
digest = data.get('containerimage.digest')
if not digest and isinstance(data.get('containerimage.descriptor'), dict):
    digest = data['containerimage.descriptor'].get('digest')
if not isinstance(digest, str) or not digest.startswith('sha256:') or len(digest) != 71:
    raise SystemExit('buildx metadata has no exact image digest')
print(digest)
PY
)"
  local immutable="$repository@$digest"

  trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed \
    --format json --output "$output/scan/$name.trivy.json" "$immutable" >&2
  syft "$immutable" -o cyclonedx-json="$output/sbom/$name.cdx.json" >&2
  cosign sign --yes --key "$COSIGN_PRIVATE_KEY" "$immutable" >&2
  printf '%s\n' "$immutable"
}

api_image="$(build_image api "$TRUST_CI_API_REPOSITORY" Dockerfile.api)"
worker_image="$(build_image worker "$TRUST_CI_WORKER_REPOSITORY" Dockerfile.worker)"
runner_image="$(build_image runner "$TRUST_CI_RUNNER_REPOSITORY" runner.Dockerfile)"

policy_output="$output/policy.json"
python3 - "$policy_template" "$policy_output" "$runner_image" <<'PY'
import json
import os
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
runner = sys.argv[3]
data = json.loads(source.read_text(encoding='utf-8'))
if not isinstance(data, dict) or not isinstance(data.get('sandbox'), dict):
    raise SystemExit('policy template has no sandbox object')
data['sandbox']['image'] = runner
payload = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w', encoding='utf-8') as handle:
    handle.write(payload)
    handle.flush()
    os.fsync(handle.fileno())
PY

(
  cd "$output"
  sha256sum policy.json sbom/*.json scan/*.json > artifacts.sha256
)

manifest="$output/supply-chain.manifest.json"
python3 - "$manifest" "$policy_output" "$output/artifacts.sha256" "$api_image" "$worker_image" "$runner_image" "$root" <<'PY'
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

manifest = Path(sys.argv[1])
policy = Path(sys.argv[2])
artifacts = Path(sys.argv[3])
api = sys.argv[4]
worker = sys.argv[5]
runner = sys.argv[6]
root = Path(sys.argv[7])

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

head = subprocess.run(
    ['git', 'rev-parse', 'HEAD'],
    cwd=root,
    text=True,
    capture_output=True,
    check=True,
).stdout.strip()
data = {
    'schema_version': 1,
    'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    'git_head': head,
    'policy_file': policy.name,
    'policy_sha256': sha(policy),
    'artifacts_file': artifacts.name,
    'artifacts_sha256': sha(artifacts),
    'images': {'api': api, 'worker': worker, 'runner': runner},
    'sbom_directory': 'sbom',
    'scan_directory': 'scan',
}
payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode() + b'\n'
fd = os.open(manifest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'wb') as handle:
    handle.write(payload)
    handle.flush()
    os.fsync(handle.fileno())
PY

(
  cd "$output"
  sha256sum supply-chain.manifest.json > supply-chain.manifest.json.sha256
  cosign sign-blob --yes --key "$COSIGN_PRIVATE_KEY" \
    --output-signature supply-chain.manifest.json.sig \
    supply-chain.manifest.json >&2
)

printf 'supply-chain release created: %s\n' "$output"
printf 'api=%s\nworker=%s\nrunner=%s\n' "$api_image" "$worker_image" "$runner_image"
