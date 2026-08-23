# Adaptive Trust CI

Self-hosted, independent merge-trust boundary for Adaptive Grok Build Pro. It does **not** use GitHub Actions.

The service consumes signed GitHub pull-request webhooks, stores jobs and leases in PostgreSQL, checks out the exact webhook SHA on a trusted worker, executes repository commands in a separate no-network container, signs the result with Ed25519, and publishes the required commit status:

```text
adaptive-trust-ci/verified
```

Local Grok hooks, prompt files, change packages and `.grok-stack/runtime` remain useful workflow inputs. They are not merge authority.

## Trust boundary

Trusted:

- deployed API and worker images;
- server-mounted `policy.json`;
- PostgreSQL state;
- CI Ed25519 private key mounted only into the worker;
- human public-key trust store mounted only into the API;
- branch protection requiring the exact external status context.

Untrusted:

- every file from the pull request, including tests, prompts, hooks and CI source code;
- local receipts and approvals created inside the repository;
- agent output;
- command stdout/stderr.

The worker has Docker-socket access and is therefore a privileged component. Pull-request code never receives the socket, GitHub token, webhook secret, signing key, human trust store or network access.

## Components

```text
GitHub webhook
    -> API: HMAC validation, allowlist, idempotent enqueue
    -> PostgreSQL: jobs, leases, attempts, approvals, attestations
    -> trusted worker: exact-SHA checkout only
    -> isolated runner container: network=none, cap-drop=ALL, read-only .git
    -> Ed25519 attestation
    -> GitHub commit status adaptive-trust-ci/verified
    -> protected main branch
```

The API image has no Docker client or CI private key. The worker has no webhook secret or human trust store. Human approval private keys must remain on a separate human-controlled machine.

## Prerequisites

- Linux host with Docker Engine and Compose v2;
- PostgreSQL 17 through the included Compose topology or an external managed PostgreSQL;
- HTTPS reverse proxy for the API;
- fine-grained GitHub token for repository contents read, pull requests read and commit statuses read/write;
- a separate temporary administration token when branch protection is configured;
- outbound GitHub access from API/worker;
- no outbound network from runner containers.

## Bootstrap

Copy the environment templates. Do not commit the resulting files:

```bash
cd trust-ci
mkdir -p runtime/control
cp env/common.env.example env/common.env
cp env/api.env.example env/api.env
cp env/worker.env.example env/worker.env
cp env/postgres.env.example env/postgres.env
cp config/policy.example.json runtime/policy.json
cp config/trust-store.example.json runtime/trust-store.json
chmod 600 env/*.env runtime/* 2>/dev/null || true
```

Replace every placeholder. `runtime/trust-store.json` is a template until a real public key is inserted.

### Build and pin the runner

The policy refuses mutable image tags. Build the runner, obtain its immutable image ID, and put that exact `sha256:...` value into `runtime/policy.json`:

```bash
docker compose --profile build build runner-image
docker image inspect adaptive-trust-ci-runner:2.1.0 --format '{{.Id}}'
```

Rebuilding the image changes the policy digest and intentionally invalidates approvals and existing jobs.

### Generate the CI attestation key

Run this on the CI server. The private key is mounted only into the worker:

```bash
docker compose build api
mkdir -p runtime
docker compose run --rm --no-deps api \
  keygen \
  --private /tmp/trust-ci-signing-key.pem \
  --public /tmp/trust-ci-signing-key.pub.pem
```

For an actual deployment, generate into a host directory or secret manager mount rather than the disposable container filesystem. Final permissions for the private key must be `0600`. Place the private key at `runtime/trust-ci-signing-key.pem`; publish the public key alongside release documentation for offline attestation verification.

### Generate a human approval key

Generate this key on the human-controlled workstation, not on the CI server and not inside an agent workspace:

```bash
adaptive-trust-ci keygen \
  --private ~/.config/adaptive-trust-ci/dmitry.pem \
  --public ~/.config/adaptive-trust-ci/dmitry.pub.pem
```

Copy only the public key and the printed `key_id` into the server-side `runtime/trust-store.json`. The private key must never be readable by API, worker, Grok, Codex or repository hooks.

### Start the service

```bash
docker compose up -d --build postgres migrate api worker
docker compose ps
curl -fsS http://127.0.0.1:8080/health/ready
```

Terminate TLS in a reverse proxy and expose only `/webhooks/github`, `/approvals`, `/health/*`, `/jobs/*` and `/attestations/*` as needed. Command output tails are stored in PostgreSQL but are deliberately omitted from the public job endpoint.

## GitHub configuration

Create a repository webhook:

```text
Payload URL: https://ci.example.com/webhooks/github
Content type: application/json
Secret: TRUST_CI_WEBHOOK_SECRET
Events: Pull requests
```

Use rollout order strictly:

1. deploy API, PostgreSQL and worker;
2. install the webhook;
3. open or update a test pull request;
4. confirm `adaptive-trust-ci/verified` appears on the exact head SHA;
5. only then configure branch protection.

Applying branch protection before the external status has been observed can lock the repository.

Use a temporary human administration token for this one command; do not grant administration permission to the long-lived service token:

```bash
TRUST_CI_GITHUB_TOKEN='<temporary-admin-token>' \
TRUST_CI_DATABASE_URL='<same-dsn>' \
TRUST_CI_POLICY_PATH="$PWD/runtime/policy.json" \
TRUST_CI_PUBLIC_BASE_URL='https://ci.example.com' \
adaptive-trust-ci branch-protect \
  --repository Dimkox/adaptive-grok-build-pro \
  --branch main \
  --required-reviews 0
```

This requires pull requests, strict up-to-date external status checks, conversation resolution, linear history, administrator enforcement, and blocks force pushes/deletion. Zero GitHub review approvals avoids a solo-maintainer deadlock; signed scoped approvals remain separate.

## Human approvals

The runner derives approval scopes from the actual base/head diff. An approval binds:

```text
repository
pull_request
base_sha
head_sha
policy_digest
scope
actor
key_id
nonce
issued_at
expires_at
signature
```

Any new commit or policy change invalidates it.

Create and submit an approval from the human workstation:

```bash
adaptive-trust-ci approval-create \
  --private-key ~/.config/adaptive-trust-ci/dmitry.pem \
  --policy ./policy.downloaded-from-server.json \
  --actor dmitry \
  --repository Dimkox/adaptive-grok-build-pro \
  --pr-number 123 \
  --base-sha '<40-hex-base-sha>' \
  --head-sha '<40-hex-head-sha>' \
  --scope governance \
  --reason 'Reviewed the exact governance diff and runner policy' \
  --ttl 900 \
  --output approval.json

adaptive-trust-ci approval-submit \
  --approval approval.json \
  --url https://ci.example.com
```

The API verifies the signature against its server-mounted public-key store, rejects ID/nonce replay, and requeues only the matching exact SHA.

## Emergency stop

The kill switch blocks new jobs, approvals and worker claims without disabling guardrails:

```bash
adaptive-trust-ci kill-switch on
adaptive-trust-ci kill-switch status
adaptive-trust-ci kill-switch off
```

The default file is `/run/adaptive-trust-ci/STOP` and is shared by API and worker. Disabling hooks is not an emergency stop; it removes local protection and has no authority over this service.

## Verification

From the repository root:

```bash
PYTHONPATH=trust-ci/src python3 -m unittest discover -s trust-ci/tests
python3 -m compileall -q trust-ci/src
```

Container and Compose validation:

```bash
docker compose -f trust-ci/compose.yaml config
docker compose -f trust-ci/compose.yaml build api worker
docker compose -f trust-ci/compose.yaml --profile build build runner-image
```

The authoritative production gate is the signed status produced by the deployed service for the exact PR SHA. Local test output is development evidence only.

## Backup and recovery

Back up PostgreSQL and the two key classes separately:

- database: jobs, leases, approvals and attestations;
- CI signing private key: worker-only secret backup;
- human private keys: offline, never server-side;
- trust store and policy: reviewed server configuration.

After database recovery, expired leases are reclaimed with `FOR UPDATE SKIP LOCKED`. Jobs at their attempt limit become `dead`. Existing signed attestations are replayed to GitHub instead of rerunning untrusted code after a status-publication outage.

## Deliberate non-features

The first production contour does not auto-merge, auto-deploy or mutate production. A human owns merge and release promotion. GitHub Actions are not installed or required.
