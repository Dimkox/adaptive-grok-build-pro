# Adaptive Trust CI

Self-hosted, independent merge-trust boundary for Adaptive Grok Build Pro. It does **not** use GitHub Actions.

The service consumes HMAC-verified GitHub pull-request webhooks, stores jobs and leases in PostgreSQL, checks out the exact webhook SHA on a trusted worker, verifies an external holdout bundle, executes mandatory checks in a separate no-network container, rejects source mutation, signs the result with Ed25519, and publishes a GitHub App-owned Check Run:

```text
adaptive-trust-ci/verified@<first-12-hex-of-policy-sha256>
```

The suffix is a policy epoch. A green check produced under an older policy or holdout digest cannot satisfy the current protected-branch requirement.

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
schema_version
approval_id
repository
pr_number
base_sha
head_sha
policy_digest
scope
actor
key_id
nonce
reason
issued_at
expires_at
signature
```

Any new commit, base change, holdout change or policy change invalidates it.

### Source-checkout operator setup

Run this only on the human-controlled workstation from an exact reviewed checkout.
The private key, copied deployed policy, operator virtual environment and signed
envelopes must all stay outside the checkout and every agent/service workspace. The
service installation continues to use the full dependency set from `pyproject.toml`;
this minimal environment is only for human approval commands.

```bash
TRUST_CI_CHECKOUT=/absolute/path/to/reviewed/adaptive-grok-build-pro
TRUST_CI_OPERATOR_DIR=/absolute/human-controlled/path/outside-the-checkout
TRUST_CI_OPERATOR_VENV="$TRUST_CI_OPERATOR_DIR/venv"
install -d -m 700 "$TRUST_CI_OPERATOR_DIR"
python3 -m venv "$TRUST_CI_OPERATOR_VENV"
"$TRUST_CI_OPERATOR_VENV/bin/python" -m pip install 'cryptography==46.0.4'

cd "$TRUST_CI_CHECKOUT"
PYTHONPATH="$TRUST_CI_CHECKOUT/trust-ci/src" \
  "$TRUST_CI_OPERATOR_VENV/bin/python" -m adaptive_trust_ci.cli approval-create --help
PYTHONPATH="$TRUST_CI_CHECKOUT/trust-ci/src" \
  "$TRUST_CI_OPERATOR_VENV/bin/python" -m adaptive_trust_ci.cli approval-submit --help
```

Record and inspect `git -C "$TRUST_CI_CHECKOUT" rev-parse HEAD` before use. Do not
silently update this checkout between review and signing.

### Verify the policy epoch and exact review target

The service administrator exports the exact deployed policy and delivers it to the
human through the organization's authenticated, human-owned file-transfer channel.
The human places that handoff outside the checkout; this API intentionally does not
publish the policy document. A repository example policy is not a valid substitute.

```bash
TRUST_CI_POLICY_HANDOFF=/absolute/path/from-authenticated-human-handoff/policy.json
TRUST_CI_POLICY="$TRUST_CI_OPERATOR_DIR/deployed-policy.json"
TRUST_CI_URL=https://ci.example.com
install -m 600 "$TRUST_CI_POLICY_HANDOFF" "$TRUST_CI_POLICY"

TRUST_CI_POLICY_DIGEST="$(
  PYTHONPATH="$TRUST_CI_CHECKOUT/trust-ci/src" \
    "$TRUST_CI_OPERATOR_VENV/bin/python" -c \
    'import sys; from pathlib import Path; from adaptive_trust_ci.policy import Policy; print(Policy.load(Path(sys.argv[1])).digest)' \
    "$TRUST_CI_POLICY"
)"
TRUST_CI_READY_DIGEST="$(
  curl -fsS "$TRUST_CI_URL/health/ready" | \
    "$TRUST_CI_OPERATOR_VENV/bin/python" -c \
    'import json, sys; print(json.load(sys.stdin)["policy_digest"])'
)"
if [ "$TRUST_CI_POLICY_DIGEST" != "$TRUST_CI_READY_DIGEST" ]; then
  echo 'STOP: the reviewed policy does not match the deployed policy epoch' >&2
  exit 1
fi
```

Raw-file `sha256sum` is not equivalent: Trust CI digests normalized canonical policy
JSON. Before signing, the human independently checks in GitHub the repository, PR
number, exact base SHA, exact head SHA, actual diff, missing scopes, Check Run owner
and policy-epoch check name. A new commit, base update, policy/holdout epoch change or
expired envelope requires a fresh review and fresh envelope.

### Create and submit one envelope per scope

Each envelope authorizes exactly one scope. The two-scope example below must be run
by the human only, after the checks above. It intentionally uses separate output
files, approval IDs and nonces for `database` and `governance`; never edit or reuse a
signed envelope.

```bash
TRUST_CI_REPOSITORY=Dimkox/adaptive-grok-build-pro
TRUST_CI_PR_NUMBER=123
TRUST_CI_BASE_SHA='<40-hex-base-sha-reviewed-by-the-human>'
TRUST_CI_HEAD_SHA='<40-hex-head-sha-reviewed-by-the-human>'
TRUST_CI_HUMAN_KEY=/absolute/human-only/path/dmitry.pem
umask 077

PYTHONPATH="$TRUST_CI_CHECKOUT/trust-ci/src" \
"$TRUST_CI_OPERATOR_VENV/bin/python" -m adaptive_trust_ci.cli approval-create \
  --private-key "$TRUST_CI_HUMAN_KEY" \
  --policy "$TRUST_CI_POLICY" \
  --actor dmitry \
  --repository "$TRUST_CI_REPOSITORY" \
  --pr-number "$TRUST_CI_PR_NUMBER" \
  --base-sha "$TRUST_CI_BASE_SHA" \
  --head-sha "$TRUST_CI_HEAD_SHA" \
  --scope database \
  --reason 'Reviewed the exact database diff and deployed policy epoch' \
  --ttl 900 \
  --output "$TRUST_CI_OPERATOR_DIR/approval-database-$TRUST_CI_HEAD_SHA.json"

PYTHONPATH="$TRUST_CI_CHECKOUT/trust-ci/src" \
"$TRUST_CI_OPERATOR_VENV/bin/python" -m adaptive_trust_ci.cli approval-submit \
  --approval "$TRUST_CI_OPERATOR_DIR/approval-database-$TRUST_CI_HEAD_SHA.json" \
  --url "$TRUST_CI_URL"

PYTHONPATH="$TRUST_CI_CHECKOUT/trust-ci/src" \
"$TRUST_CI_OPERATOR_VENV/bin/python" -m adaptive_trust_ci.cli approval-create \
  --private-key "$TRUST_CI_HUMAN_KEY" \
  --policy "$TRUST_CI_POLICY" \
  --actor dmitry \
  --repository "$TRUST_CI_REPOSITORY" \
  --pr-number "$TRUST_CI_PR_NUMBER" \
  --base-sha "$TRUST_CI_BASE_SHA" \
  --head-sha "$TRUST_CI_HEAD_SHA" \
  --scope governance \
  --reason 'Reviewed the exact governance diff and deployed policy epoch' \
  --ttl 900 \
  --output "$TRUST_CI_OPERATOR_DIR/approval-governance-$TRUST_CI_HEAD_SHA.json"

PYTHONPATH="$TRUST_CI_CHECKOUT/trust-ci/src" \
"$TRUST_CI_OPERATOR_VENV/bin/python" -m adaptive_trust_ci.cli approval-submit \
  --approval "$TRUST_CI_OPERATOR_DIR/approval-governance-$TRUST_CI_HEAD_SHA.json" \
  --url "$TRUST_CI_URL"
```

Create only the scopes actually reported missing. Each scope must be authorized for
the signing key in the server-side public trust store. The API verifies the signature,
exact target, policy/TTL and replay state before accepting it. A successful response
contains `accepted`, `approval_id`, `scope`, `requeued_jobs` and
`status_publisher`; `requeued_jobs: 0` can mean the accepted scope arrived while the
job was already queued or running.

Do not automatically retry an ambiguous timeout: a committed envelope is single-use.
HTTP 400 means malformed input or an unconfigured scope; 403 means the key, actor,
scope, signature, exact target, policy or TTL check failed; 404 means no applicable
job exists; 409 means approval-ID/nonce replay; and 503 means the kill switch or
control plane is unavailable. Understand the mismatch and create a fresh envelope
only after re-reviewing the current target.

After all missing scopes are accepted, verify in GitHub that the same durable Check
Run, owned by the configured Trust CI GitHub App and named for the current policy
epoch, resumes on the exact head SHA and succeeds. HTTP acceptance alone is not merge
authority. Retain or delete expired envelope files according to the human audit
policy; if this CLI release is faulty, stop signing and return to the previous
reviewed operator CLI version without weakening policy, trust-store, branch
protection or approval scopes.

The minimal operator-path regression is safe to run without operational credentials;
it creates only a disposable test key and submits only to a loopback test server:

```bash
cd "$TRUST_CI_CHECKOUT"
PYTHONPATH=trust-ci/src:trust-ci/tests \
  "$TRUST_CI_OPERATOR_VENV/bin/python" -m unittest -v trust-ci/tests/test_cli.py
```

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
