# Quickstart — Adaptive Grok Build Pro

0. Check tools (minimum or newer; doctor offers a fallback install if something is missing):
   ```bash
   python3 scripts/grok_doctor.py --offer-install
   ```

### Try the local browser demo

From this checkout, start the Python-only dashboard with no install or frontend build:

```bash
python3 scripts/grok_demo.py --open
```

It prints and serves `http://127.0.0.1:8765/` on loopback only. The tour uses bundled sample evidence, a fixed non-authoritative route seed, in-memory computed previews, and read-only summaries from this checkout; server/application initialization invokes no Git command or subprocess and makes no external request or write. `--open` may ask the operating system to open the configured local browser. Bundled and local evidence is not merge authority and is not the App-owned exact-SHA Trust CI check. Press `Ctrl-C` to stop. See [docs/INVESTOR_DEMO.md](docs/INVESTOR_DEMO.md) for the five-minute walkthrough and port troubleshooting.

1. Install Grok Build:
   - Windows: `irm https://x.ai/cli/install.ps1 | iex`
   - macOS/Linux: `curl -fsSL https://x.ai/cli/install.sh | bash`

2. Auth: run `grok` once, sign in with SuperGrok account.

3. Plan an update for an existing repository without changing it:
   ```bash
   python3 scripts/install_into.py --plan /path/to/your/repo
   ```

   Existing repositories are read-only installer inputs. The plan is a deterministic managed-file manifest plus dependency advice; it performs no writes and executes no dependency command. The historical positional command and `--dry-run` are planning aliases. `--force` is rejected; update an existing consumer by applying the plan through a normal reviewed source-change commit.

   To create a complete installation, choose an absent path:

   ```bash
   python3 scripts/install_into.py --materialize-new /path/to/new/repo
   ```

   This materialization mode is supported only on Linux with descriptor-relative `O_NOFOLLOW`/`O_DIRECTORY` operations and both libc and the target filesystem supporting `renameat2(RENAME_NOREPLACE)`. If any required capability is unavailable or the filesystem rejects it, materialization exits nonzero and fails closed without publishing the target; there is no fallback to replace, merge, or in-place copying. Use `--plan` plus a normal reviewed source-change for an existing consumer or for a platform/filesystem without those capabilities.

   New-target materialization uses an owned sibling stage and fail-closed no-replace publication. It refuses an existing, symlink, or special-file target. If the original identity of a newly created staging entry cannot be proven after a constructor failure, the installer preserves that unresolved entry, reports `manual cleanup required: installer ownership is unresolved`, and never deletes a same-named replacement.

   The payload delivers the architecture CLI, parser/evaluators, strict schemas, and non-authoritative examples. Every plan and payload excludes the target-owned `architecture/system.yaml`, `architecture/rules.yaml`, and `architecture/adoption.json`. It also excludes `trust-ci/` and `.github/workflows/`.

### Optional manual executable-architecture adoption

An installed repository without `architecture/adoption.json` remains backward-compatible and reports architecture as `not_configured`. Adoption is an explicit repository-owner decision: copy the examples, replace every example identity/path/policy with reviewed target truth, validate them, render/review the projections, and create the marker last. Do not use the README K16 graph or generated diagrams as model input.

```bash
cd /path/to/repo
mkdir -p architecture
cp .grok-stack/templates/architecture/system.example.yaml architecture/system.yaml
cp .grok-stack/templates/architecture/rules.example.yaml architecture/rules.yaml

# Review and replace ARCH-REPLACE-ME, owners, paths, contracts, trust/data/secret
# declarations, and every applicable policy before continuing.
python3 scripts/grok_architecture.py validate --json
python3 scripts/grok_architecture.py summary --json
python3 scripts/grok_architecture.py drift --json
# This prints all five bounded artifacts and does not write repository files.
python3 scripts/grok_architecture.py diagram --json
# Apply approved projection text through normal reviewed source edits, then compare.
python3 scripts/grok_architecture.py diagram --check --json
```

After review succeeds, create `architecture/adoption.json` manually with exactly the same `architecture_id` as both model documents. For the unmodified examples, the strict canonical marker bytes are exactly:

```json
{
  "architecture_id": "ARCH-REPLACE-ME",
  "schema_version": 1,
  "state": "adopted"
}
```

The marker requires sorted keys, two-space JSON, and exactly one final newline. Commit the marker with both reviewed target documents; marker present plus either missing/invalid document fails closed. The diagram command is read-only: checked-in projection changes are ordinary reviewed source edits. The marker, diagrams, Markdown, and receipts do not replace the system/rules authority, and local checks do not replace the App-owned exact-SHA Trust CI check.

Exact-state evidence uses literal 40-character commit SHAs. Use `--worktree` only for diagnostics; it never claims an exact head SHA:

```bash
python3 scripts/grok_architecture.py diff --base <40-char-sha> --head <40-char-sha> --json
python3 scripts/grok_architecture.py fitness --base <40-char-sha> --head <40-char-sha> --pre-risk red --json
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

`install_into.py --plan` inspects an existing target read-only. On Linux with the descriptor and `renameat2(RENAME_NOREPLACE)` capabilities stated above, `install_into.py --materialize-new` publishes the local Grok stack (skills, agents, hooks, scripts, `AGENTS.md`) only at an absent target. It does **not** copy `trust-ci/`, `.github/workflows/`, target-owned architecture authority, this repository’s `README.md`, `QUICKSTART.md`, or `VERSION`. Consumer laptops do not stand up PostgreSQL.

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
