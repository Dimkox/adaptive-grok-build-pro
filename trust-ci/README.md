# Adaptive Trust CI

Self-hosted, independent merge-trust boundary for Adaptive Grok Build Pro. It does **not** use GitHub Actions.

The service consumes HMAC-verified GitHub pull-request webhooks, stores jobs and leases in PostgreSQL, checks out the exact webhook SHA on a trusted worker, verifies an external holdout bundle, executes mandatory checks in a separate no-network container, rejects source mutation, signs the result with Ed25519, and publishes a GitHub App-owned Check Run:

```text
adaptive-trust-ci/verified@<first-12-hex-of-policy-sha256>
```

The suffix is a policy epoch. A green check produced under an older policy or holdout digest cannot satisfy the current protected-branch requirement.

## Repository-scoped policy profiles

Schema version 1 supports two mutually exclusive policy shapes. Legacy mode uses `allowed_repositories`, root `commands`, and root `holdout`; it preserves the existing policy digest and Check Run name, omits `holdout.host_path`, and uses `TRUST_CI_HOLDOUT_HOST_PATH`. Catalog mode uses `repository_profiles`, whose objects contain exactly `repository`, `commands`, and `holdout`; each holdout has a mandatory absolute, profile-scoped `host_path` for the Docker daemon. At worker startup, catalog local and daemon paths must be strict descendants of the independently configured `TRUST_CI_HOLDOUT_PATH` and `TRUST_CI_HOLDOUT_HOST_PATH`, with identical relative suffixes; roots, traversal, outside-root paths, and mismatches fail closed before dependencies are built. Status, pipeline, retry/lease limits, sandbox, environment, and approval rules remain common. The complete effective profile, including canonical local/host paths and holdout digest, is hashed, so its digest remains the durable job binding and produces its own `adaptive-trust-ci/verified@<policy-sha12>` Check Run.

Catalog lookup has no wildcard, alias, normalization, or default fallback. Unknown or case-variant repositories are rejected before enqueue; a worker resolves the durable `(repository, policy_digest)` pair before checkout and finishes stale or unavailable bindings as non-success. A change to one profile rotates only that profile’s epoch; a common-field change rotates every profile.

Repository profiles are a code/config capability in this repository, pending a separately reviewed and approved server-side policy and external holdout installation. The example at `config/policy.example.json` is illustrative only: the adaptive example digest matches the checked-in example bundle, while the second profile’s digest is a shape-valid placeholder; it is not a deployed policy and does not claim that either repository has been enabled.

### Profile rollout and rollback

Roll out compatible API and worker binaries first while the legacy policy remains active. Configure and verify the paired trusted roots before atomically installing the reviewed catalog and external holdouts for API and workers. Separately review the server-mounted catalog and each external holdout, drain workers, then verify each repository’s App-owned exact-SHA Check Run and signed attestation before changing branch protection. On failure, drain workers and restore the previous reviewed binaries plus legacy policy as one unit; preserve PostgreSQL jobs and attestations, and re-enqueue unavailable-digest work only at the exact SHA under the restored epoch.

Local Grok hooks, prompt files, change packages, delegated local grants and `.grok-stack/runtime` remain useful workflow inputs. They are not merge authority.

## Trust boundary

Trusted:

- deployed API and worker images;
- server-mounted `policy.json`;
- server-mounted external holdout bundle and its policy-bound digest;
- PostgreSQL state;
- CI Ed25519 private key mounted only into the worker;
- GitHub App RSA private key mounted only into the worker;
- human public-key trust store mounted only into the API;
- branch protection requiring the exact policy-epoch check from the configured GitHub App ID.

Untrusted:

- every file from the pull request, including tests, prompts, hooks and the repository copy of CI source code;
- local receipts and delegated grants created inside the repository;
- agent output;
- command stdout/stderr.

The worker has Docker-socket access and is therefore a privileged component. Pull-request code never receives the socket, GitHub App token, GitHub App key, webhook secret, attestation key, human trust store or network access. Run the worker on a dedicated CI host without production workloads.

## Components

```text
GitHub pull-request webhook
    -> API: HMAC validation, repository allowlist, idempotent enqueue
    -> PostgreSQL: jobs, leases, attempts, approvals, attestations
    -> trusted worker: GitHub App installation token + exact-SHA checkout
    -> external holdout digest verification
    -> isolated runner container: network=none, cap-drop=ALL, read-only .git
    -> tracked-source mutation check
    -> Ed25519 attestation
    -> GitHub App Check Run adaptive-trust-ci/verified@<policy-sha12>
    -> app-bound protected main branch
```

The API image has no Docker client, GitHub credentials or CI private key. It can enqueue work and accept signed approvals, but it cannot publish a successful GitHub check. The worker has no webhook secret or human trust store. Human approval private keys remain on a separate human-controlled machine.

## Prerequisites

- dedicated Linux CI host with Docker Engine and Compose v2;
- PostgreSQL through the included Compose topology or an external managed PostgreSQL;
- HTTPS reverse proxy for the API;
- GitHub App installed on the repository with `Checks: read/write`, `Contents: read`, and `Pull requests: read`;
- GitHub App ID, installation ID and RSA private key mounted only into the worker;
- a separate temporary human administration token when branch protection is configured;
- outbound GitHub access from the API for webhook delivery responses and from the worker for checkout/Checks API;
- no outbound network from runner containers.

The worker requests a short-lived installation token with the reduced permissions `checks:write`, `contents:read`, and `pull_requests:read`, even if the installed App has broader permissions.

## Bootstrap

Copy the environment templates. Do not commit the resulting files:

```bash
cd trust-ci
mkdir -p runtime/control runtime/holdout
cp .env.example .env
cp env/common.env.example env/common.env
cp env/api.env.example env/api.env
cp env/worker.env.example env/worker.env
cp env/migration.env.example env/migration.env
cp env/postgres.env.example env/postgres.env
cp env/backup.env.example env/backup.env
cp config/policy.example.json runtime/policy.json
cp config/trust-store.example.json runtime/trust-store.json
chmod 600 env/*.env .env 2>/dev/null || true
```

Replace every placeholder. `runtime/trust-store.json` remains invalid until a real human public key is inserted.

### Build and pin the images

The deployment and policy refuse mutable runner tags. Build API, worker and runner images, obtain immutable digests, and place those digests into the deployment environment and `runtime/policy.json`:

```bash
docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image
docker image inspect "$TRUST_CI_API_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_WORKER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_RUNNER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
```

Inspect `$TRUST_CI_*_IMAGE`; do not inspect `adaptive-trust-ci-api:2.1.0`. Put measured `name@sha256:` values into untracked deploy env and host `runtime/policy.json`. Rebuilding the runner or changing any policy or holdout input changes the policy digest, changes the required check name, and intentionally invalidates old jobs and approvals.

### Install the external holdout bundle

The holdout lives outside the repository checkout and cannot be modified by a pull request. Populate the host directory mounted read-only into the worker, then calculate its deterministic digest:

```bash
adaptive-trust-ci holdout-digest --path /opt/adaptive-trust-ci-holdout
```

Set the absolute in-worker holdout path, host mount path and exact digest in the deployed policy and worker environment. The worker fails closed before checkout if the bundle digest does not match.

### Generate the CI attestation key

Generate on the CI server or in a secret manager. The private key is mounted only into the worker:

```bash
adaptive-trust-ci keygen \
  --private runtime/trust-ci-signing-key.pem \
  --public runtime/trust-ci-signing-key.pub.pem
chmod 600 runtime/trust-ci-signing-key.pem
```

Publish the public key with release documentation for offline attestation verification.

### Configure the GitHub App

Create and install a GitHub App dedicated to Trust CI. Grant only:

```text
Checks: Read and write
Contents: Read-only
Pull requests: Read-only
```

Store its RSA private key at the worker-only path configured by `TRUST_CI_GITHUB_APP_PRIVATE_KEY_PATH`. Configure `TRUST_CI_GITHUB_APP_ID` and `TRUST_CI_GITHUB_INSTALLATION_ID`. The API service must not receive these values or the private key.

### Generate a human approval key

Generate this key on the human-controlled workstation, not on the CI server and not inside an agent workspace:

```bash
adaptive-trust-ci keygen \
  --private ~/.config/adaptive-trust-ci/dmitry.pem \
  --public ~/.config/adaptive-trust-ci/dmitry.pub.pem
```

Copy only the public key and printed `key_id` into the server-side `runtime/trust-store.json`. The private key must never be readable by API, worker, Grok, Codex or repository hooks.

### Start the service

```bash
docker compose up -d postgres migrate api worker
docker compose ps
curl -fsS http://127.0.0.1:18080/health/ready
```

Terminate TLS in a reverse proxy. Expose `/webhooks/github` and `/approvals`; expose `/jobs/*` and `/attestations/*` only according to the repository privacy model. Command output tails are stored in PostgreSQL but omitted from the public job endpoint.

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
3. open or update a disposable pull request;
4. confirm the exact policy-epoch Check Run appears on the exact head SHA and is owned by the Trust CI GitHub App;
5. verify its signed attestation offline;
6. only then configure branch protection.

Applying branch protection before observing the App-owned check can lock the repository.

Use a temporary human administration token for this one command. Do not grant repository administration to the long-lived Trust CI GitHub App:

```bash
TRUST_CI_GITHUB_ADMIN_TOKEN=<temporary-admin-token> \
TRUST_CI_GITHUB_APP_ID='<app-id>' \
adaptive-trust-ci branch-protect \
  --policy "$PWD/runtime/policy.json" \
  --repository Dimkox/adaptive-grok-build-pro \
  --branch main \
  --required-reviews 0
```

The configurator uses `required_status_checks.checks` with both the exact policy-epoch check name and the GitHub App ID. A status or check with the same text from another actor does not satisfy the requirement. Protection also requires a pull request, strict up-to-date checks, conversation resolution and linear history, enforces administrators, and blocks force pushes and branch deletion.

## Human security approvals

The runner derives external approval scopes from the actual base/head diff. An approval binds:

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

Any new commit, base change, holdout change or policy change invalidates it.

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
  --reason 'Reviewed the exact governance diff and deployed policy epoch' \
  --ttl 900 \
  --output approval.json

adaptive-trust-ci approval-submit \
  --approval approval.json \
  --url https://ci.example.com
```

The API verifies the signature against its server-mounted public-key store, rejects ID/nonce replay, and requeues only the matching exact SHA. The worker restarts the same durable App-owned Check Run rather than creating a duplicate.

## Delegated local operational consent

`scripts/grok_approve.py` is separate from Trust CI security approvals. It may materialize explicit or standing user consent for a named local action such as branch push, tag push or GitHub Release publication. The grant is bound to repository, route, change, exact HEAD, tree fingerprint, action/resource list and TTL. It cannot create the external Check Run or satisfy a signed Trust CI approval.

## Emergency stop

The kill switch blocks new jobs, approvals and worker claims without disabling guardrails:

```bash
adaptive-trust-ci kill-switch on
adaptive-trust-ci kill-switch status
adaptive-trust-ci kill-switch off
```

The default file is `/run/adaptive-trust-ci/STOP` and is shared by API and worker. Disabling local hooks is not an emergency stop; it removes local protection and has no authority over this service.

## Verification

From the repository root:

```bash
PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest discover -s trust-ci/tests
python3 -m compileall -q trust-ci/src
```

PostgreSQL integration and Compose validation:

```bash
make trust-ci-postgres-test
# or: docker compose -f trust-ci/compose.test.yaml up --build --abort-on-container-exit --exit-code-from postgres-integration
docker compose -f trust-ci/compose.yaml -f trust-ci/compose.build.yaml --profile build build api worker runner-image
docker compose -f trust-ci/compose.yaml config
```

The authoritative production gate is the App-owned, policy-epoch, signed exact-SHA Check Run produced by the deployed service. Local test output is development evidence only.

## Backup and recovery

Back up PostgreSQL and each key class separately:

- database: jobs, leases, approvals and attestations;
- CI attestation private key: worker-only secret backup;
- GitHub App private key: worker-only secret backup or managed secret;
- human private keys: offline, never server-side;
- trust store, holdout and policy: reviewed server configuration and artifacts.

After database recovery, expired leases are reclaimed with `FOR UPDATE SKIP LOCKED`. Jobs at their attempt limit become `dead`. Existing signed attestations are replayed into the same durable App-owned Check Run instead of rerunning untrusted code after a publication outage.

## Deliberate non-features

The first production contour does not auto-merge, auto-deploy or mutate production. Merge remains human-owned. Release operations may be explicitly delegated by the user through exact local grants, but they never alter merge trust. GitHub Actions are not installed or required.
