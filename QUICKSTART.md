# Quickstart — Adaptive Grok Build Pro

0. Check tools (minimum or newer; doctor offers a fallback install if something is missing):
   ```bash
   python3 scripts/grok_doctor.py --offer-install
   ```

1. Install Grok Build:
   - Windows: `irm https://x.ai/cli/install.ps1 | iex`
   - macOS/Linux: `curl -fsSL https://x.ai/cli/install.sh | bash`

2. Auth: run `grok` once, sign in with SuperGrok account.

3. Install this stack into your repo:
   ```bash
   python3 scripts/install_into.py /path/to/repo
   # installs the stack and missing required tools (use --no-deps to copy only)
   ```

4. Work:
   ```bash
   cd /path/to/repo
   grok
   ```
   Prompt example: `Добавь обработчик события OnAfterUserAdd в local-модуль`

5. Optional explicit skill: `/adaptive-delivery`

6. Verify before finish:
   ```bash
   python3 scripts/grok_verify.py --mode pr
   ```
   Then `/release-readiness` and `python3 scripts/grok_deploy.py` to prepare human-owned publish commands (`--record` only with production approval).

7. Trust project hooks in the TUI: `/hooks-trust`

## Scope split

`install_into.py` copies the local Grok stack (skills, agents, hooks, scripts, `AGENTS.md`). It does **not** copy `trust-ci/`, this repository’s `README.md`, `QUICKSTART.md`, or `VERSION`. Consumer laptops do not stand up PostgreSQL.

Local `python3 scripts/grok_verify.py --mode pr` is preflight evidence. It is **not merge authority**. Merge trust, when deployed, is the GitHub App-owned check `adaptive-trust-ci/verified@<policy-sha12>` on the exact pull-request SHA.

This repository is **PR-only**. Do not `git push origin main`. Ship product changes on an isolated branch and a pull request.

Optional local quality tools used by `grok_verify --mode pr` (not required in `toolchain.json`): ruff, bandit, coverage (`fail_under` 74).

## Bitrix example

```bash
cd examples/bitrix-module
composer install
composer test
```

## Operator: Trust CI host

Dedicated Linux CI host with Docker Engine and Compose v2. Do not colocate privileged rootless DinD with production workloads. Terminate TLS in a reverse proxy (none is in-tree). Full operator contract: [`trust-ci/README.md`](trust-ci/README.md) and [`engineering/runbooks/trust-ci-rollout.md`](engineering/runbooks/trust-ci-rollout.md). Commands below match the Makefile; do not build against `compose.yaml` alone.

### PostgreSQL

One logical database `trust_ci`. Four login roles (`trust_ci_api`, `trust_ci_worker`, `trust_ci_migrator`, `trust_ci_backup`) are created by `trust-ci/postgres/init/001_roles.sh`. Schema is `sql/001_schema.sql` + `002_operational_indexes.sql` + `003_database_roles.sql`, applied by the `migrate` oneshot. The admin password is not the API/worker/migrator/backup password. The server is the Compose image `postgres:17.6-bookworm` (digest pinned at deploy), not a host `postgresql` package. Durable volume: `trust-ci-postgres`.

Copy templates. Do not commit filled files:

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

Replace every `REPLACE_WITH_*` placeholder, including image `name@sha256:` pins in `.env`. `runtime/trust-store.json` stays invalid until a real human public key is inserted.

### Live harness

From the repository root (exit code from `postgres-integration`, not `tests`):

```bash
make trust-ci-postgres-test
# or
./trust-ci/scripts/postgres-integration.sh
./trust-ci/scripts/postgres-restart-drill.sh
```

### Build and pin images

From the `trust-ci/` directory. `compose.yaml` has no `build:`; merge the build override:

```bash
docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image
docker image inspect "$TRUST_CI_API_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_WORKER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_RUNNER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
PYTHONPATH=src python3 -m adaptive_trust_ci.cli holdout-digest --path /absolute/reviewed/holdout
```

Inspect `$TRUST_CI_*_IMAGE`. Do not inspect `adaptive-trust-ci-api:2.1.0` / `adaptive-trust-ci-worker:2.1.0` — `compose.build.yaml` does not set those tags for api/worker. Put immutable digests into `.env` and `runtime/policy.json`. Rebuilding the runner or changing policy/holdout changes the policy digest and the required check name.

### Keys

Keep the split. Never commit private keys.

- CI attestation key: worker-only (`adaptive-trust-ci keygen`).
- GitHub App RSA key: worker-only. The API must not receive App ID, installation ID, or the App private key.
- Human Ed25519 approval key: human workstation only. An agent must not generate, read, or submit it.

```bash
adaptive-trust-ci keygen \
  --private runtime/trust-ci-signing-key.pem \
  --public runtime/trust-ci-signing-key.pub.pem
chmod 600 runtime/trust-ci-signing-key.pem
```

Human key (on the human machine, not in an agent workspace):

```bash
adaptive-trust-ci keygen \
  --private ~/.config/adaptive-trust-ci/operator.pem \
  --public ~/.config/adaptive-trust-ci/operator.pub.pem
```

Copy only the public key and printed `key_id` into server-side `runtime/trust-store.json`.

### Start and health

```bash
docker compose -f compose.yaml up -d postgres migrate api worker
curl -fsS http://127.0.0.1:18080/health/ready
```

`/health/ready` stays **503** until PostgreSQL is up **and** the trust store has an active human public key. The systemd unit `trust-ci/systemd/adaptive-trust-ci-compose.service` also starts `docker-engine` + `runner-loader` after `verify-supply-chain.sh`. Manual `up` of `postgres migrate api worker` is enough to exercise API readiness; jobs that need a runner require the systemd set (or `docker-engine` and `runner-loader` as well).

### Webhook, then prove, then branch-protect

1. Deploy API, PostgreSQL and worker.
2. Register the HMAC GitHub webhook on `/webhooks/github` (pull-request events).
3. Prove the App-owned check first on a disposable docs PR (draft or not). Do not treat a draft as the first live proof of branch protection.
4. Confirm Check Run `adaptive-trust-ci/verified@<policy-sha12>` on the exact head SHA, owned by the Trust CI GitHub App.
5. Verify the signed attestation offline.
6. Only then consider `adaptive-trust-ci branch-protect`. Applying branch protection before the App-owned check exists can lock the repository.

### Backup, kill-switch, supply-chain

```bash
adaptive-trust-ci backup-create
adaptive-trust-ci restore-drill --confirm-disposable
adaptive-trust-ci kill-switch on
adaptive-trust-ci kill-switch status
adaptive-trust-ci kill-switch off
```

A systemd timer runs daily backup. Operator-only image release:

```bash
trust-ci/scripts/supply-chain-release.sh --confirm-push
```

That script requires host tools **docker**, **trivy**, **syft**, and **cosign**. Optional extra scanner (not a product pin, not in `toolchain.json`): grype. Pointers: [`trust-ci/README.md`](trust-ci/README.md), [`engineering/runbooks/trust-ci-rollout.md`](engineering/runbooks/trust-ci-rollout.md).

### Scanner host install

Official commands (also offered by `python3 scripts/grok_doctor.py --offer-install` for optional tools):

```bash
# Docker Engine + Compose v2 (Ubuntu 24.04)
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2

# Syft
curl -sSfL https://get.anchore.io/syft | sudo sh -s -- -b /usr/local/bin

# Trivy (Aqua contrib install script)
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sudo sh -s -- -b /usr/local/bin v0.74.0

# Cosign (Sigstore GitHub releases; pin fallback 2.4.x)
curl -sSfL https://github.com/sigstore/cosign/releases/download/v2.4.3/cosign-linux-amd64 -o /tmp/cosign
sudo install -m 0755 /tmp/cosign /usr/local/bin/cosign
```
