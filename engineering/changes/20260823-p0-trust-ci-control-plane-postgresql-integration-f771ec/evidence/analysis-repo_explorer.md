# Repo explorer — Trust CI implementation surface vs handoff steps 2–8

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Route: `f771ecaf458d`  
Branch: `feat/trust-ci-control-plane` at `04348dbde391eaccb574c96740e2fa7b2fa9825a`  
Inspected: 2026-08-23  

This is a read-only map of what exists in the tree. It is not merge authority and does not claim that live PostgreSQL, GitHub App, webhook, or branch-protection steps have been executed.

## 1. Verdict

The **control-plane code is present**. Compose, CLI, GitHub App JWT/installation-token/Checks API, HMAC webhook, isolated runner, external holdout, PostgreSQL schema/store, env templates, systemd units, backup/restore, and app-bound branch-protection **payloads** are in `trust-ci/`.

Handoff steps **2–8 are not done as live operations**. What remains is almost entirely **external activation**: a disposable Postgres that actually runs the 8 skipUnless tests, digest-pinned images, a real GitHub App and keys, a dedicated CI host, a non-draft webhook proof, human Ed25519 approvals, and then app-bound `main` protection.

Do not add GitHub Actions. `.github/` is absent. Product tests lock that.

## 2. Sources read

- `GROK_BUILD_HANDOFF.md`
- `engineering/runbooks/trust-ci-rollout.md`
- `trust-ci/README.md`
- `engineering/reviews/trust-ci-p0-local-verification.md`
- `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md`
- `docs/superpowers/plans/2026-08-23-trust-ci-control-plane.md`
- `trust-ci/` compose, Dockerfiles, env templates, systemd, SQL, CLI, API, worker, runner, tests
- `scripts/`, `Makefile`, `tests/test_structure.py`, `tests/test_deploy.py`
- change package under `engineering/changes/20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec/` (still a draft skeleton)

## 3. File surface

### 3.1 Compose and images

| File | Role |
| --- | --- |
| `trust-ci/compose.yaml` | Production topology. **No `build:`**. Requires digest-pinned images. Services: `postgres`, `migrate`, `api`, `docker-engine` (privileged rootless DinD), `runner-loader`, `worker`. API bound to `127.0.0.1:8080`. Two networks: `trust-ci` and `executor`. |
| `trust-ci/compose.build.yaml` | Build override for `migrate`/`api`/`worker`/`runner-image` (`profiles: ["build"]`). Requires `TRUST_CI_PYTHON_BASE_IMAGE`. Only `runner-image` sets a local tag (`adaptive-trust-ci-runner:2.1.0`). |
| `trust-ci/compose.test.yaml` | Disposable Postgres + test image. Service name is **`postgres-integration`**, not `tests`. |
| `trust-ci/.env.example` | Compose interpolation: base/Postgres/DinD/API/worker/runner image refs and `TRUST_CI_HOLDOUT_SOURCE_PATH`. |
| `trust-ci/Dockerfile.api` | API image. `postgresql-client`, **no Docker, no Git**. Entrypoint `adaptive-trust-ci`, default `api --host 0.0.0.0 --port 8080`. uid 10001. |
| `trust-ci/Dockerfile.worker` | Worker image. `git` + `docker.io` CLI. Default `worker`. uid 10001. |
| `trust-ci/Dockerfile.test` | Unittest image for live Postgres. Copies `src`, `tests`, `sql`. |
| `trust-ci/runner.Dockerfile` | Isolated runner. `git`, `php-cli`, `composer`, `nodejs`, `npm`, pinned `coverage`/`ruff`/`bandit`/`tomli`. Workdir `/workspace`. uid 10001. |

Correct production compose config (no build):

```bash
docker compose -f trust-ci/compose.yaml config
```

Correct **build** (README/runbook omit the override file):

```bash
docker compose -f trust-ci/compose.yaml -f trust-ci/compose.build.yaml --profile build build api worker runner-image
```

`Makefile` already uses the two-file merge for `docker-compose-build-config`. `trust-ci/README.md` and the rollout runbook still say `docker compose --profile build build api worker runner-image` against `compose.yaml` alone; that will not build, because production compose has no `build:` keys.

### 3.2 CLI (`adaptive-trust-ci`)

Entry: `trust-ci/src/adaptive_trust_ci/cli.py` via `trust-ci/pyproject.toml` script `adaptive-trust-ci = adaptive_trust_ci.cli:main`. Package version **2.1.0** (product `VERSION` is still **2.0.11**).

| Command | Purpose |
| --- | --- |
| `api` | FastAPI + uvicorn |
| `worker [--once]` | Claim/process loop |
| `migrate` / `migration-status` | Checksum-locked SQL |
| `policy-digest` | Server policy digest |
| `holdout-digest --path` | Deterministic bundle hash |
| `doctor` | Role-aware health (policy, holdout, Postgres, migrations, trust-store, CI signer, GitHub App key, sandbox runtime) |
| `keygen` | Ed25519 pair |
| `trust-store-validate` | Key lifecycle |
| `approval-create` / `approval-verify` / `approval-submit` | Human exact-SHA approvals |
| `attestation-verify` | Offline CI attestation |
| `branch-protect` | App-bound GitHub protection. Needs `TRUST_CI_GITHUB_ADMIN_TOKEN` + App ID |
| `backup-create` / `backup-verify` / `restore-drill` | Custom-format `pg_dump` + SHA-256 manifest |
| `kill-switch on\|off\|status` | Shared stop file, default `/run/adaptive-trust-ci/STOP` |

### 3.3 GitHub App, webhook, Checks, branch protection

| File | Present behavior |
| --- | --- |
| `trust-ci/src/adaptive_trust_ci/github_app.py` | RS256 JWT (`iat-60s`, `exp+9m`). Installation token POST with reduced permissions `checks:write`, `contents:read`, `pull_requests:read`. Cached until ~2 minutes before expiry. |
| `trust-ci/src/adaptive_trust_ci/github.py` | `ensure_check_run` / `complete_check_run` (Checks API). Reuses run by `external_id` = durable job ID. `configure_branch_protection` PUTs `required_status_checks.checks[{context, app_id}]`. |
| `trust-ci/src/adaptive_trust_ci/webhooks.py` | HMAC-SHA256 `X-Hub-Signature-256`. Events: `opened`, `synchronize`, `reopened`, `ready_for_review`. **Draft PRs ignored** except `closed` (cancel). |
| `trust-ci/src/adaptive_trust_ci/api.py` | Endpoints below. **No `GitHubClient` / `GitHubAppAuth`**. Cannot publish a check. |
| `trust-ci/src/adaptive_trust_ci/worker.py` | Builds App auth + Checks client. Refuses start unless `TRUST_CI_RUNNER_IMAGE` equals `policy.sandbox.image`. |
| `trust-ci/tests/test_github_app.py` | JWT, reduced permissions, cache, failed token |
| `trust-ci/tests/test_webhooks_github.py` | HMAC, draft ignore, Checks, app-bound protection payload |

API routes:

| Method | Path | Auth |
| --- | --- | --- |
| GET | `/health/live` | none |
| GET | `/health/ready` | none; 503 if kill-switch, DB down, or no active trust-store keys |
| POST | `/webhooks/github` | HMAC secret |
| POST | `/approvals` | Ed25519 envelope vs server trust store |
| GET | `/jobs/{job_id}` | bearer `TRUST_CI_READ_TOKEN`; command tails stripped |
| GET | `/attestations/{job_id}` | bearer |
| GET | `/metrics` | bearer; Prometheus text |

Check name is `policy.status_context` + `@` + first 12 hex of policy digest:

```text
adaptive-trust-ci/verified@<policy-sha12>
```

Branch-protection payload fields already encoded in `branch_protection_payload()`:

- `required_status_checks.strict = true`
- `checks = [{context: <epoch name>, app_id}]`
- `enforce_admins = true`
- `required_conversation_resolution = true`
- `required_linear_history = true`
- `allow_force_pushes = false`
- `allow_deletions = false`
- reviews count configurable (`--required-reviews`, default 0)

There is **no GitHub App registration, App ID, installation ID, or private key in the repository**. Templates still say `REPLACE_WITH_APP_ID`.

### 3.4 Runner, holdout, source mutation

| File | Role |
| --- | --- |
| `trust-ci/src/adaptive_trust_ci/runner.py` | Create/reuse Check Run → verify policy digest → verify holdout digest **before checkout** → exact-SHA workspace → required scopes → holdout commands then repo commands → mutation check → sign attestation → complete check. Replays stored attestation after GitHub publication failure. `needs_approval` → conclusion `action_required`. |
| `trust-ci/src/adaptive_trust_ci/workspace.py` | Trusted `git init` + authenticated fetch of PR head + detach at exact SHA. Token used only for fetch, not passed into runner env. |
| `trust-ci/src/adaptive_trust_ci/sandbox.py` | `docker run --network none --read-only --cap-drop ALL --security-opt no-new-privileges`, `.git` read-only, holdout `:ro` at `/holdout`, `--pull never`. No `GITHUB_TOKEN` / `TRUST_CI_GITHUB*` in command env. |
| `trust-ci/src/adaptive_trust_ci/holdout.py` | Deterministic digest over relative path + exec bit + content SHA-256. Symlinks forbidden. |
| `trust-ci/holdout.example/validate.py` | External holdout: forbids `.github/workflows`, requires App/worker split and `app_id` in protection payload. |
| `trust-ci/config/policy.example.json` | Holdout digest `28ee9c803043a482de50e2a9757fb5236e56a8c899b2ae97d4faf3f082333f30` matches `holdout.example`. Runner image is still `adaptive-trust-ci-runner@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST`. |

### 3.5 PostgreSQL

| File | Role |
| --- | --- |
| `trust-ci/sql/001_schema.sql` and `trust-ci/src/adaptive_trust_ci/resources/001_schema.sql` | Jobs, attempts, approvals (unique nonce), attestations, events, `trust_ci_claim_job` with `FOR UPDATE SKIP LOCKED` and attempt-limit → `dead`. |
| `trust-ci/sql/002_operational_indexes.sql` (packaged duplicate) | Lease, terminal, approval expiry, attempt, attestation indexes. |
| `trust-ci/src/adaptive_trust_ci/store.py` | `MemoryStore` + `PostgresStore`. |
| `trust-ci/src/adaptive_trust_ci/migrations.py` | Checksum-locked apply; advisory lock `0x41544349`. |
| `trust-ci/src/adaptive_trust_ci/lease.py` | Heartbeat thread while a job runs. |
| `trust-ci/tests/test_postgres_integration.py` | **8** live tests, all `@unittest.skipUnless(TRUST_CI_TEST_DATABASE_URL)`. |
| `trust-ci/tests/postgres_restart_probe.py` | Seed/verify job survival across `compose restart`. Not a unittest. |
| `trust-ci/scripts/postgres-integration.sh` | Isolated compose project, `--exit-code-from postgres-integration`, always `down --volumes`. |
| `trust-ci/scripts/postgres-restart-drill.sh` | Restart drill using the probe. |

Handoff text “four previously skipped integration tests” is **stale**. The class now has eight methods.

### 3.6 Env templates (do not commit filled copies)

Gitignore: `trust-ci/env/*.env`, `trust-ci/runtime/*`, `*.pem`. Tracked examples only.

| File | Variables |
| --- | --- |
| `trust-ci/.env.example` | `TRUST_CI_PYTHON_BASE_IMAGE`, `TRUST_CI_POSTGRES_IMAGE`, `TRUST_CI_DIND_IMAGE`, `TRUST_CI_API_IMAGE`, `TRUST_CI_WORKER_IMAGE`, `TRUST_CI_RUNNER_IMAGE`, `TRUST_CI_RUNNER_BUILD_TAG`, `TRUST_CI_TEST_BUILD_TAG`, `TRUST_CI_HOLDOUT_SOURCE_PATH` |
| `trust-ci/env/common.env.example` | `TRUST_CI_DATABASE_URL`, `TRUST_CI_POLICY_PATH`, `TRUST_CI_PUBLIC_BASE_URL`, `TRUST_CI_KILL_SWITCH_PATH` |
| `trust-ci/env/api.env.example` | `TRUST_CI_WEBHOOK_SECRET`, `TRUST_CI_TRUST_STORE_PATH`, `TRUST_CI_READ_TOKEN`, `TRUST_CI_ROLE=api` |
| `trust-ci/env/worker.env.example` | `TRUST_CI_SIGNING_KEY_PATH`, `TRUST_CI_GITHUB_APP_ID`, `TRUST_CI_GITHUB_INSTALLATION_ID`, `TRUST_CI_GITHUB_APP_PRIVATE_KEY_PATH`, `TRUST_CI_WORKSPACE_ROOT`, `TRUST_CI_WORKSPACE_HOST_ROOT`, `TRUST_CI_HOLDOUT_HOST_PATH`, `TRUST_CI_WORKER_ID`, `TRUST_CI_POLL_INTERVAL_SECONDS`, `TRUST_CI_ROLE=worker` |
| `trust-ci/env/postgres.env.example` | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` |
| `trust-ci/env/backup.env.example` | `TRUST_CI_BACKUP_DIR`, `TRUST_CI_BACKUP_DATABASE_LABEL`, `TRUST_CI_COMPOSE_DIRECTORY` |

Additional runtime env (not in `env/*.example`):

| Variable | Where |
| --- | --- |
| `TRUST_CI_RUNNER_IMAGE` | Injected by `compose.yaml` into worker/runner-loader; also required by `WorkerSettings` (must be `name@sha256:` or `sha256:`) |
| `TRUST_CI_TEST_DATABASE_URL` | Live tests / restart probe |
| `TRUST_CI_GITHUB_ADMIN_TOKEN` | `branch-protect` only; temporary human admin token |
| `TRUST_CI_BACKUP_DIR` / `TRUST_CI_RESTORE_DATABASE_URL` | Backup CLI |
| `TRUST_CI_ROLE` | `doctor` (`api` / `worker` / `all`) |
| `TRUST_CI_COMPOSE_FILE` | `scripts/smoke.sh` |

API and worker secrets are **split**: webhook secret + trust store only on API; App key + CI signing key only on worker. Compose mounts match that split.

`runtime/` is gitignored and empty of secrets/policy. Compose **will not start** until these host files exist:

```text
trust-ci/runtime/policy.json
trust-ci/runtime/trust-store.json
trust-ci/runtime/trust-ci-signing-key.pem
trust-ci/runtime/github-app-private-key.pem
trust-ci/runtime/control/   (kill-switch dir)
```

plus a reviewed holdout tree at `TRUST_CI_HOLDOUT_SOURCE_PATH`.

### 3.7 Systemd, backup, smoke

| File | Role |
| --- | --- |
| `trust-ci/systemd/adaptive-trust-ci-compose.service` | `docker compose up -d postgres migrate api worker` (Compose still starts `depends_on` DinD + runner-loader). `WorkingDirectory=/opt/adaptive-grok-build-pro/trust-ci`. |
| `trust-ci/systemd/adaptive-trust-ci-backup.service` | Daily `backup-create` via `docker compose run --rm --no-deps api`. |
| `trust-ci/systemd/adaptive-trust-ci-backup.timer` | `02:17 UTC` + 15m jitter. |
| `trust-ci/scripts/restore-drill.sh` | `backup-verify` then `restore-drill --confirm-disposable`. |
| `trust-ci/scripts/smoke.sh` | Forbids `.github/workflows`, curls `/health/live` and `/health/ready`, `compose config`. |

Gap: `ExecReload=... docker compose up -d --build ...` on a no-build production compose. Harmless if only `compose.yaml` is used; dangerous if someone later merges `compose.build.yaml` into the unit.

### 3.8 Tests and local verify commands

Trust CI unittests (MemoryStore / fakes unless noted), ~110 `test_*` methods across:

```text
trust-ci/tests/test_api.py
trust-ci/tests/test_backup.py
trust-ci/tests/test_github_app.py
trust-ci/tests/test_key_rotation.py
trust-ci/tests/test_metrics.py
trust-ci/tests/test_migrations.py
trust-ci/tests/test_ops.py
trust-ci/tests/test_policy.py
trust-ci/tests/test_postgres_integration.py   # 8 skipUnless live DB
trust-ci/tests/test_runner.py
trust-ci/tests/test_signing.py
trust-ci/tests/test_store.py
trust-ci/tests/test_webhooks_github.py
```

Root product tests that lock Trust CI presence / no GHA:

```text
tests/test_structure.py   # trust-ci files, immutable sandbox, no .github/workflows
tests/test_deploy.py      # external_status_required adaptive-trust-ci/verified
```

Handoff step 1 (baseline; not executed in this analysis pass):

```bash
PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest discover -s tests -v
PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest discover -s trust-ci/tests -v
python3 -m compileall -q .grok-stack/adaptive_grok scripts trust-ci/src tests trust-ci/tests
python3 scripts/grok_verify.py --mode pr --no-record --json
```

Makefile extras:

```bash
make trust-ci-test
make trust-ci-compile
make trust-ci-compose          # compose.yaml config only; needs digest env
make docker-compose-build-config
make trust-ci-postgres-test    # compose.test.yaml, exit-code-from postgres-integration
make trust-ci-holdout-digest
```

`scripts/grok_verify.py` does **not** discover `trust-ci/tests`. Step 1’s second unittest command is mandatory.

Prior local evidence (`engineering/reviews/trust-ci-p0-local-verification.md` and handoff) is **stale relative to current test count**: it recorded 97 Trust CI tests with 4 Postgres skips. The tree now has eight skipUnless Postgres tests plus additional ops/backup/metrics/key-rotation coverage.

### 3.9 Intentionally absent

| Item | Status |
| --- | --- |
| `.github/workflows/**` | Absent. Tests fail if added. |
| Reverse-proxy config (Caddy/nginx/Traefik) | Missing. Docs say “terminate TLS in a reverse proxy”; no unit file or compose service. |
| SBOM generator / vulnerability scan script | Missing. Handoff step 3 asks to retain SBOM + vuln report. |
| Prometheus scrape / log stack | `/metrics` exists; no scrape config. |
| Filled `env/*.env`, keys, `runtime/policy.json` | Correctly gitignored / not present. |
| Live GitHub App, webhook, Check Run, branch protection | Not in tree; cannot be inferred from code. |
| `lookup.get_job_for_exact` wired into `/approvals` | Helper exists; API still uses `get_job_for_sha` (repo+head only). |

## 4. Handoff steps 2–8 — present vs missing

### Step 2 — Real PostgreSQL integration

**Present (code):**

- 8 live tests in `test_postgres_integration.py`:
  - migration registry idempotent
  - two workers cannot claim the same live job (`FOR UPDATE SKIP LOCKED`)
  - expired lease reclaim
  - heartbeat requires owner
  - attempt exhaustion → `dead`
  - duplicate webhook identity
  - nonce replay rejected
  - signed attestation survives new store instance
- Restart/recovery: `trust-ci/scripts/postgres-restart-drill.sh` + `postgres_restart_probe.py` (not part of unittest discover)
- Runner: `trust-ci/scripts/postgres-integration.sh` and `make trust-ci-postgres-test`

**Missing (execution + harness mismatches):**

- `TRUST_CI_TEST_DATABASE_URL` is unset in this workspace; those 8 tests skip.
- `compose.test.yaml` interpolates `TRUST_CI_POSTGRES_IMAGE` and `TRUST_CI_PYTHON_BASE_IMAGE`. `.env.example` still has `REPLACE_WITH_*_DIGEST`. A real digest (or a throwaway local tag for the test-only compose) must be supplied before `docker compose -f trust-ci/compose.test.yaml up` works.
- Rollout runbook command is wrong: `--exit-code-from tests`. The service is `postgres-integration`. Use Makefile or `postgres-integration.sh`.
- Restart drill is a separate script; it will not run just because unittest discover is re-run with a DSN.
- Attestation replay after GitHub publication failure is covered in `test_runner.py` (fakes), not in the live Postgres class.

Required commands once images/DSN exist:

```bash
# A. compose harness (preferred; self-cleaning)
./trust-ci/scripts/postgres-integration.sh
# or
make trust-ci-postgres-test

# B. restart/recovery (handoff required scenario)
./trust-ci/scripts/postgres-restart-drill.sh

# C. same suite as handoff, with DSN
export TRUST_CI_TEST_DATABASE_URL='postgresql://trust_ci_test:trust_ci_test_password@127.0.0.1:5432/trust_ci_test'
PYTHONPATH=trust-ci/src python3 -m unittest discover -s trust-ci/tests -v
```

### Step 3 — Build and pin immutable artifacts

**Present:** Dockerfiles, `compose.build.yaml`, digest-required `compose.yaml`, policy sandbox image regex, `holdout-digest` CLI, `keygen`, example holdout digest locked by `test_ops.py`.

**Missing:**

- No built local images or recorded digests in the change package.
- `policy.example.json` runner image is a placeholder, so it is not a deployable policy until replaced.
- README inspect names `adaptive-trust-ci-api:2.1.0` / `adaptive-trust-ci-worker:2.1.0`, but `compose.build.yaml` does not set those image names for api/worker. After build, tag/inspect the actual `TRUST_CI_API_IMAGE` / `TRUST_CI_WORKER_IMAGE` values.
- No SBOM or vuln-scan command/output.
- CI public attestation key not generated (and must not be committed if generated).

Minimum command sequence (after copying `.env.example` → `trust-ci/.env` with **real** base digests):

```bash
cd trust-ci
docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image
docker image inspect "$TRUST_CI_API_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_WORKER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_RUNNER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
PYTHONPATH=src python3 -m adaptive_trust_ci.cli holdout-digest --path /absolute/reviewed/holdout
# write those sha256 values into deployed runtime/policy.json and compose env
```

Do not commit private keys or filled `env/*.env`.

### Step 4 — Create the GitHub App

**Present:** JWT, installation-token reduction, Checks API client, worker-only key path, doctor check `github-app-key`, tests.

**Missing (all live):**

- GitHub App creation/install on `Dimkox/adaptive-grok-build-pro`
- App ID, installation ID
- worker-only RSA private key at `runtime/github-app-private-key.pem`
- API-only webhook secret in `env/api.env`
- Confirmation that App permissions are exactly Checks R/W, Contents R, Pull requests R, Metadata R
- Confirmation API container env has **none** of App ID / installation ID / App key

This step cannot be completed from repository files. It needs a human GitHub account and an isolated secret store.

### Step 5 — Deploy the self-hosted service

**Present:** Production compose, systemd unit, backup timer, migrate oneshot, healthchecks, isolated DinD (no `/var/run/docker.sock` on API/worker), smoke script, backup CLI.

**Missing:**

- Dedicated CI host / VM
- Filled env files, policy, trust store, keys, holdout mount
- HTTPS reverse proxy (no config in tree)
- Backup destination actually mounted and restore-drilled
- Metrics/logs consumers
- `docker compose up -d postgres migrate api worker` (and resulting `curl /health/ready`) evidence
- systemd enablement evidence

Deploy recipe already documented:

```bash
cd trust-ci
mkdir -p runtime/control runtime/holdout
cp env/common.env.example env/common.env
cp env/api.env.example env/api.env
cp env/worker.env.example env/worker.env
cp env/postgres.env.example env/postgres.env
cp config/policy.example.json runtime/policy.json
cp config/trust-store.example.json runtime/trust-store.json
# replace placeholders, install holdout, generate keys, pin image digests
docker compose up -d postgres migrate api worker
docker compose ps
curl -fsS http://127.0.0.1:8080/health/ready
```

`/health/ready` fails closed until Postgres is up **and** the trust store has at least one active human public key.

### Step 6 — Register and prove the webhook flow

**Present:** HMAC parser, idempotent enqueue, worker claim, no-network runner, holdout-before-checkout, attestation store, Checks publication, `attestation-verify` CLI.

**Critical operational conflict:**

- Handoff: PR **#2 is draft** until the App-owned check appears on its exact SHA.
- Code: `parse_pull_request_event` returns `None` for draft PRs (`test_draft_pull_request_is_ignored`). Updating draft PR #2 **will not enqueue a job**.

Rollout runbook is the safer order: prove the App-owned check on a **non-draft disposable documentation PR** first. Do not mark #2 ready-for-review just to force a webhook unless that is an explicit human decision.

Also missing live: webhook URL, HMAC secret on GitHub, job row for an exact SHA, Check Run ID, offline attestation verification output.

Webhook config to register (after HTTPS proxy):

```text
Payload URL: https://<ci-host>/webhooks/github
Content type: application/json
Secret: TRUST_CI_WEBHOOK_SECRET
Events: Pull requests
```

### Step 7 — Prove approval behavior

**Present in tests/CLI:**

- documentation-only / unmatched paths → no scope (`test_unmatched_paths_need_no_approval`)
- `trust-ci/**` → `governance` (`policy.example.json`)
- missing approval → Check Run `action_required` + job `needs_approval`
- valid exact-SHA approval allows execution
- wrong signer scope, tamper, expiry, TTL, actor mismatch (`test_signing.py`)
- nonce replay (`MemoryStore` + live Postgres unique constraint)
- trust-store revocation without API restart (`test_api.py`)
- policy digest / head SHA / base SHA mismatch rejects
- `approval-create` / `approval-submit`

**Missing:** a live disposable PR demonstrating each bullet in the handoff, plus a human private key that is **not** on the CI host and **not** in this workspace.

`trust-ci/**` is in the governance glob, so **this branch’s own diff requires a signed governance approval** before the runner will execute repository checks. A docs-only disposable PR does not.

### Step 8 — Protect `main`

**Present:** CLI `branch-protect`, payload with epoch check + `app_id`, tests, runbook.

Command (only after a successful App-owned check is observed):

```bash
TRUST_CI_GITHUB_ADMIN_TOKEN=<temporary-admin-token> \
TRUST_CI_GITHUB_APP_ID='<app-id>' \
adaptive-trust-ci branch-protect \
  --policy /path/to/deployed/runtime/policy.json \
  --repository Dimkox/adaptive-grok-build-pro \
  --branch main \
  --required-reviews 0
```

**Missing:** live application and the negative tests (direct push, merge without the App check, same check text from another actor). Applying this before the check exists can lock `main`.

Do not grant `administration` to the long-lived Trust CI GitHub App. The admin token is one-shot and human.

## 5. Docs / handoff inconsistencies (do not “fix” by adding GHA)

| Topic | Reality in tree | Stale text |
| --- | --- | --- |
| Postgres skip count | 8 skipUnless tests | Handoff / local review: 4 skipped |
| Compose test service | `postgres-integration` | Runbook: `--exit-code-from tests` |
| Image build | Need `-f compose.yaml -f compose.build.yaml` | README/runbook: `--profile build` on compose.yaml alone |
| Image inspect tags | api/worker image names come from env | README inspects `adaptive-trust-ci-api:2.1.0` |
| Draft PR #2 | Webhook ignores drafts | Handoff step 6 says update PR #2 |
| Design spec | Still talks commit **status** and a generic GitHub token | Implementation is GitHub **App Checks** |
| Design scopes | Spec: `protected-path` / `production` / `external-write` | Example policy: `governance` / `database` / `production` |
| Postgres version | `.env.example`: `postgres:17.6-bookworm` | Spec/plan: PostgreSQL 16 |
| Product identity | `VERSION` = 2.0.11 | Trust CI package = 2.1.0; plan task 8 not fully reflected in product identity |
| Change package | `state.json` status `draft`; brief/tasks empty | Handoff treats the branch as already implemented locally |

## 6. Suggested execution order for the write owner

Stay inside `allowed_agents`. This analysis does not implement.

1. Reproduce handoff step 1 against **this** SHA; store stdout in this evidence directory. Do not reuse the old 97/4 numbers.
2. Copy `trust-ci/.env.example` locally, pin real base/Postgres image digests, run `./trust-ci/scripts/postgres-integration.sh` then `./trust-ci/scripts/postgres-restart-drill.sh`. Require all 8 skipUnless tests to execute.
3. Build with the two-file compose merge; pin runner/API/worker/holdout digests into a **server-side** policy (not committed). Generate CI keypair on the CI host.
4. Human creates the GitHub App and webhook secret; worker-only key never enters the API env or this checkout.
5. Deploy compose + reverse proxy on an isolated host; `curl /health/ready`.
6. Prove the App-owned epoch check on a **non-draft disposable docs PR**. Verify attestation offline. Only then consider PR #2 (`ready_for_review` is a human gate because of the draft filter).
7. Prove governance approval on a `trust-ci/**` (or other scoped) disposable PR.
8. Only after a green App-owned check: `branch-protect` on `main` with the deployed policy digest and App ID.

## 7. Residual risks already visible in code

- Privileged rootless DinD (`docker-engine`) with plaintext TCP 2375 on the `executor` network. Documented; keep off production workload hosts.
- systemd `ExecReload --build` vs digest-pinned production compose.
- `/approvals` looks up by repository+head SHA only (`get_job_for_sha`), not the stricter `lookup.get_job_for_exact`.
- Runner image still a placeholder in the shipped example policy; deploying the example as-is fails closed (good) but is not a pin.
- No reverse-proxy or SBOM artifacts, so steps 3 and 5 cannot be checked off from this repository alone.
- Local `grok_approve.py` grants remain non-authoritative; they must not be used as a substitute for the App check or human Ed25519 approval.
