# repo_explorer: M0.1 compose gap (no compose-up)

Route `6346a398114f`. Secrets unread (no `.env`/pem/glider content).

## trust-ci/env filenames

Present: `api.env.example`, `backup.env.example`, `common.env.example`, `migration.env.example`, `postgres.env.example`, `supply-chain.env.example`, `worker.env.example`.

Absent (compose `env_file`): `postgres.env`, `common.env`, `migration.env`, `api.env`, `worker.env`. Also absent: `backup.env` (not in compose.yaml). No hidden `.env` under this dir.

## trust-ci/runtime filenames

Present: `.gitkeep`, `github-app-private-key.pem`. No other files.

## Images `*:2.1.0` RepoDigests vs Id

`docker image inspect --format '{{.RepoDigests}}'` (all three exist):

- api: `ghcr.io/dimkox/adaptive-trust-ci-api@sha256:70a8…` — **yes** name@sha256 form; full string **≠** `.Id` (`sha256:70a8…` same hex, no registry prefix).
- worker: `ghcr.io/dimkox/adaptive-trust-ci-worker@sha256:bffd…` — same: form OK, ≠ `.Id`.
- runner: `ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900c…` — same: form OK, ≠ `.Id`.

## TRUST_CI_* in compose.yaml

Required (`:?`): `TRUST_CI_POSTGRES_IMAGE`, `TRUST_CI_API_IMAGE`, `TRUST_CI_DIND_IMAGE`, `TRUST_CI_WORKER_IMAGE`, `TRUST_CI_RUNNER_IMAGE`, `TRUST_CI_HOLDOUT_SOURCE_PATH`.

Optional default: `TRUST_CI_API_HOST_PORT` (`18080`). Host `trust-ci/.env` **absent** (filename only).

## Ports

- **18080**: not listening; curl connection refused → **free**.
- **8080**: listen `127.0.0.1:8080`; HTML meta “SearXNG — a privacy-respecting, open metasearch engine” / generator searxng → **is SearXNG**.

## Gap for `docker compose up`

Copy five compose env files from examples; provide host interpolation for the six required `TRUST_CI_*`; holdout path; dind image not inspected here. Do not start stack in this pass.
