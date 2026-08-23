# Trust CI rollout and rollback

## Objective

Deploy the self-hosted exact-SHA status `adaptive-trust-ci/verified`, validate it on a pull request, and only then protect `main`. GitHub Actions remain absent.

## Preconditions

- reviewed `trust-ci/runtime/policy.json` with immutable runner image ID;
- API-only webhook secret and public-key trust store;
- worker-only CI signing key;
- separate human approval private key stored off-server;
- service GitHub token without repository administration permission;
- temporary human administration token available only for the protection step;
- HTTPS reverse proxy and PostgreSQL backup destination.

## Deploy

```bash
cd trust-ci
mkdir -p runtime/control
cp env/common.env.example env/common.env
cp env/api.env.example env/api.env
cp env/worker.env.example env/worker.env
cp env/postgres.env.example env/postgres.env
cp config/policy.example.json runtime/policy.json
cp config/trust-store.example.json runtime/trust-store.json
```

Replace placeholders, generate keys, then build and pin the runner:

```bash
docker compose --profile build build runner-image
docker image inspect adaptive-trust-ci-runner:2.1.0 --format '{{.Id}}'
# Put the exact sha256:... into runtime/policy.json.

docker compose up -d --build postgres migrate api worker
docker compose ps
curl -fsS http://127.0.0.1:8080/health/ready
```

Configure an HTTPS GitHub pull-request webhook at `/webhooks/github` with the API-only HMAC secret.

## Prove the external status before protection

1. Open a disposable pull request changing an unprotected documentation file.
2. Confirm PostgreSQL contains a queued/running job for the exact head SHA.
3. Confirm runner logs show `--network none`, immutable image ID and no secret environment.
4. Confirm GitHub shows `adaptive-trust-ci/verified` on the exact head SHA.
5. Fetch `/attestations/<job_id>` and verify it offline with the CI public key.
6. Update the same PR. Confirm the old SHA cannot satisfy the new SHA.
7. Change a `trust-ci/**` file. Confirm the job enters `needs_approval` until an Ed25519 human approval is submitted.

Do not continue if any step is ambiguous.

## Protect main

Use a temporary human administration token. Do not grant administration scope to the long-lived service token.

```bash
TRUST_CI_GITHUB_TOKEN='<temporary-admin-token>' \
TRUST_CI_DATABASE_URL='<dsn>' \
TRUST_CI_POLICY_PATH="$PWD/runtime/policy.json" \
TRUST_CI_PUBLIC_BASE_URL='https://ci.example.com' \
adaptive-trust-ci branch-protect \
  --repository Dimkox/adaptive-grok-build-pro \
  --branch main \
  --required-reviews 0
```

Verify protection using a fresh pull request. Direct push, force push, branch deletion and merge without the external status must fail.

## Emergency stop

```bash
adaptive-trust-ci kill-switch on
```

This blocks new jobs, approvals and worker claims. It does not remove branch protection or convert failures into success. Existing GitHub statuses remain as recorded.

## Database backup

```bash
docker compose exec -T postgres \
  pg_dump --format=custom --no-owner --file=/tmp/trust-ci.dump "$POSTGRES_DB"
docker compose cp postgres:/tmp/trust-ci.dump ./runtime/trust-ci.dump
```

Store the dump separately from CI and human keys.

## Rollback

Rollback service code by deploying the previous reviewed API/worker images and the previous server policy. Policy rollback changes the policy digest; enqueue fresh jobs for open pull requests.

If the service is unavailable and repository access must be restored:

1. enable the kill switch;
2. retain PostgreSQL and attestation data;
3. use a human administration token to temporarily remove only the required status context from `main` protection;
4. repair or restore the service;
5. prove the status on a disposable PR again;
6. reapply branch protection.

Never replace the external gate with a local receipt, repository approval JSON, prompt instruction or manually forged success status.

## Acceptance criteria

- no `.github/workflows/` exists;
- API cannot read the CI private key or Docker socket;
- worker cannot read webhook secret or human trust store;
- runner receives no token, key, socket or network;
- job state survives API/worker restart;
- expired leases are reclaimed and attempt-limited;
- approvals are bound to repository, PR, base SHA, head SHA, policy digest and scope;
- commit status success is backed by a stored signed attestation;
- `main` requires PR plus `adaptive-trust-ci/verified`.
