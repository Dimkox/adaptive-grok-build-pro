# Docs: Trust CI M0.1 deploy (README + trust-ci-rollout.md)

Sources: `trust-ci/README.md`, `engineering/runbooks/trust-ci-rollout.md`. No secrets.

## M0.1 sequence (health first)

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

Replace placeholders. Pin images (inspect `$TRUST_CI_*_IMAGE`, not floating tags):

```bash
docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image
docker image inspect "$TRUST_CI_API_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_WORKER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_RUNNER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
```

Holdout (host path outside repo):

```bash
adaptive-trust-ci holdout-digest --path /opt/adaptive-trust-ci-holdout
```

Put `name@sha256:` image values and holdout digest into untracked deploy env and `runtime/policy.json`.

```bash
docker compose up -d postgres migrate api worker
docker compose ps
curl -fsS http://127.0.0.1:18080/health/ready
```

## After health only

Rollout order: (1) deploy API/Postgres/worker, (2) webhook `/webhooks/github`, (3) disposable PR, (4) App-owned `adaptive-trust-ci/verified@<policy-sha12>` on exact SHA, (5) offline attestation, (6) **then** `adaptive-trust-ci branch-protect`. Webhook and branch-protect are after health. Protection before observing the check can lock the repo.
