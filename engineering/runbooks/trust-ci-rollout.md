# Trust CI rollout and rollback

## Objective

Deploy the self-hosted exact-SHA GitHub App Check Run `adaptive-trust-ci/verified@<policy-sha12>`, validate it on a disposable pull request, bind branch protection to its GitHub App ID, and only then protect `main`. GitHub Actions remain absent.

## Preconditions

- dedicated CI host without production workloads;
- reviewed `trust-ci/runtime/policy.json` with immutable runner image digest;
- reviewed external holdout bundle outside the repository checkout, with its exact digest in policy;
- API-only webhook secret and human public-key trust store;
- worker-only CI attestation key;
- worker-only GitHub App ID, installation ID and RSA private key;
- separate human security-approval private key stored off-server;
- temporary human administration token available only for branch protection;
- HTTPS reverse proxy and PostgreSQL backup destination.

The Trust CI GitHub App must have `Checks: read/write`, `Contents: read`, and `Pull requests: read`. The worker requests an installation token reduced to exactly those permissions. The API receives no GitHub credentials and cannot publish a successful check.

## Deploy

```bash
cd trust-ci
mkdir -p runtime/control runtime/holdout
cp env/common.env.example env/common.env
cp env/api.env.example env/api.env
cp env/worker.env.example env/worker.env
cp env/postgres.env.example env/postgres.env
cp config/policy.example.json runtime/policy.json
cp config/trust-store.example.json runtime/trust-store.json
```

Replace placeholders, install the external holdout bundle, generate the CI and human keys, configure the GitHub App, then build and pin every image:

```bash
docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image
docker image inspect "$TRUST_CI_API_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_WORKER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_RUNNER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'

adaptive-trust-ci holdout-digest --path /opt/adaptive-trust-ci-holdout
# Put exact image and holdout sha256 values into deployment env and runtime/policy.json.

docker compose up -d postgres migrate api worker
docker compose ps
curl -fsS http://127.0.0.1:8080/health/ready
```

Configure an HTTPS GitHub pull-request webhook at `/webhooks/github` with the API-only HMAC secret.

## Prove the App-owned policy epoch before protection

1. Open a disposable pull request changing an unprotected documentation file.
2. Confirm PostgreSQL contains one queued/running job for the exact head SHA.
3. Confirm the worker, not the API, creates a Check Run named `adaptive-trust-ci/verified@<policy-sha12>` with `external_id` equal to the durable job ID.
4. Confirm GitHub shows the Check Run as owned by the Trust CI GitHub App.
5. Confirm runner logs show the immutable image digest, external holdout execution, `--network none`, no secrets, and no Docker socket inside the runner.
6. Fetch `/attestations/<job_id>` and verify it offline with the CI public key.
7. Update the same PR. Confirm the old SHA and old Check Run cannot satisfy the new SHA.
8. Change any deployed policy or holdout input. Confirm the policy digest and required check name change.
9. Change a `trust-ci/**` file. Confirm the Check Run enters `action_required` until an exact Ed25519 human approval is submitted, then restarts the same durable Check Run.
10. Run a fixture that changes a tracked source file and exits `0`. Confirm Trust CI still fails with a source-integrity result.

Do not continue if any step is ambiguous.

## Protect main

Use a temporary human administration token. Do not grant repository administration to the long-lived Trust CI GitHub App.

```bash
TRUST_CI_GITHUB_ADMIN_TOKEN=<temporary-admin-token> \
TRUST_CI_GITHUB_APP_ID='<app-id>' \
adaptive-trust-ci branch-protect \
  --policy "$PWD/runtime/policy.json" \
  --repository Dimkox/adaptive-grok-build-pro \
  --branch main \
  --required-reviews 0
```

The command writes `required_status_checks.checks` with both the exact policy-epoch check name and `app_id`. Verify with a fresh pull request that:

- the same check text from another actor does not satisfy protection;
- direct push, force push and branch deletion fail;
- merge without the exact App-owned check fails;
- unresolved conversations block merge;
- administrators cannot bypass the rule.

## PostgreSQL acceptance

Before production, run the real PostgreSQL harness, not only `MemoryStore` tests:

```bash
make trust-ci-postgres-test
# or, from repository root:
# docker compose -f trust-ci/compose.test.yaml up \
#   --build --abort-on-container-exit --exit-code-from postgres-integration
```

The harness must prove duplicate-webhook idempotency, `FOR UPDATE SKIP LOCKED` exclusivity with concurrent workers, heartbeat and lease expiry, worker-death reclaim, bounded attempts to `dead`, nonce replay rejection, PostgreSQL restart recovery, and signed-attestation replay after GitHub publication failure.

## Delegated release operations

Explicit or standing user consent may be materialized locally through `scripts/grok_approve.py`. Every grant is bound to exact repository, route, change, Git HEAD, tree fingerprint, named action/resource and TTL. These grants may authorize branch push, tag push or GitHub Release publication, but never create or replace the external App-owned Check Run or a human-signed security approval.

## Emergency stop

```bash
adaptive-trust-ci kill-switch on
```

This blocks new jobs, approvals and worker claims. It does not remove branch protection or convert failures into success. Existing Check Runs remain as recorded.

## Database backup

```bash
docker compose exec -T postgres \
  pg_dump --format=custom --no-owner --file=/tmp/trust-ci.dump "$POSTGRES_DB"
docker compose cp postgres:/tmp/trust-ci.dump ./runtime/trust-ci.dump
```

Store the dump separately from the CI attestation key, GitHub App key and human keys. Perform a restore drill before declaring a recovery objective.

## Rollback

Rollback service code by deploying the previous reviewed API/worker images, previous holdout and previous server policy. Any policy or holdout rollback changes the policy epoch; enqueue fresh jobs for open pull requests and update branch protection only after the restored App-owned check is observed.

If the service is unavailable and repository access must be restored:

1. enable the kill switch;
2. retain PostgreSQL and attestation data;
3. use a human administration token to temporarily remove only the exact required policy-epoch check from `main` protection;
4. repair or restore the service;
5. prove the App-owned check on a disposable PR again;
6. reapply branch protection with the restored policy check name and App ID.

Never replace the external gate with a local receipt, delegated local grant, repository JSON, prompt instruction, legacy commit status or manually forged success result.

## Acceptance criteria

- no `.github/workflows/` exists;
- API cannot read GitHub App credentials, CI private key or Docker socket;
- worker cannot read webhook secret or human trust store;
- runner receives no token, key, socket or network;
- external holdout and policy digests are verified before checkout execution;
- tracked source mutation is a deterministic failure;
- job state survives API/worker/PostgreSQL restart;
- expired leases are reclaimed exactly once and attempt-limited;
- approvals are bound to repository, PR, base SHA, head SHA, policy digest and scope;
- Check Run success is backed by a stored signed attestation;
- branch protection requires the exact policy-epoch check from the configured GitHub App ID;
- `main` requires a pull request plus that App-owned check.
