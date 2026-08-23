# Integration analysis — GitHub App, webhook HMAC, Checks API, policy-epoch naming, branch protection

Agent: `integration_architect`
Route: `f771ecaf458d`
Change: `engineering/changes/20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`
Scope: read-only inspection of Trust CI GitHub integration. No GitHub Actions. No credentials, `.env`, or production keys were read.

## Verdict

The GitHub integration is already implemented as a self-hosted split: HMAC webhook intake on the API, GitHub App JWT → installation token → Checks API on the worker, policy-epoch check names, and an app-bound branch-protection payload. There is **no** `webhook` CLI command; webhooks are registered in the GitHub UI. Activating a real App does not require GitHub Actions. It does require a real App + installation, worker-only RSA key, API-only HMAC secret, HTTPS public URL, immutable images, a holdout whose validator matches this tree, observed App-owned checks on a disposable PR, then a one-shot human admin token for `branch-protect`.

One activation blocker is already in-tree: `trust-ci/holdout.example/validate.py` still string-matches `context': status_context` in `github.py`, but the live payload uses `normalized_name`. Deploying the example holdout against the current tree would fail holdout validation and prevent a successful check.

---

## 1. End-to-end GitHub integration flow

```text
GitHub repository webhook (pull_request, HMAC secret)
  -> API POST /webhooks/github
       verify X-Hub-Signature-256
       parse JobRequest (exact head/base SHA)
       allowlist repository
       idempotent enqueue in PostgreSQL
       return status_publisher=worker-github-app
       (API never calls GitHub Checks)
  -> Worker claims lease
       GitHubAppAuth: RSA JWT -> POST /app/installations/{id}/access_tokens
       GitHubClient.ensure_check_run (in_progress, name=policy.check_name, external_id=job_id)
       exact-SHA checkout with x-access-token
       holdout + isolated runner (no token, no network)
       Ed25519 attestation
       GitHubClient.complete_check_run (success|failure|action_required|…)
  -> Human CLI (separate admin token, not the App)
       adaptive-trust-ci branch-protect
       PUT /repos/{repo}/branches/{branch}/protection
       required check = policy.check_name bound to app_id
```

The webhook is a **repository webhook**, not a GitHub App webhook. The App is used only for installation tokens (clone + Checks API) and as the `app_id` bound into branch protection. HMAC secret and App private key are therefore split across API and worker.

---

## 2. GitHub App JWT and installation token

Source: `trust-ci/src/adaptive_trust_ci/github_app.py`, tests in `trust-ci/tests/test_github_app.py`.

### JWT (`generate_app_jwt`)

- Algorithm: RS256 (`cryptography` RSA PKCS1v15 + SHA-256). Non-RSA keys are rejected.
- Header: `{"alg":"RS256","typ":"JWT"}`.
- Payload:
  - `iss` = GitHub App ID as string
  - `iat` = now − 60 seconds (clock skew)
  - `exp` = now + 9 minutes (under GitHub’s 10-minute JWT cap)
- Encoding: URL-safe base64 without padding; header/payload serialized with `canonical_json` (sorted keys, compact separators).
- App ID must be a positive int (bool rejected). Invalid PEM → `ValueError('invalid GitHub App private key')`.

### Installation token (`GitHubAppAuth.installation_token`)

1. Read RSA PEM from `private_key_path` (worker-only mount).
2. Sign a JWT.
3. `POST {api_url}/app/installations/{installation_id}/access_tokens` with:
   ```json
   {
     "permissions": {
       "checks": "write",
       "contents": "read",
       "pull_requests": "read"
     }
   }
   ```
   Headers: `Authorization: Bearer <jwt>`, `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2026-03-10`, `User-Agent: adaptive-trust-ci/2.1.0`.
4. Expect HTTP 201, non-empty `token`, and `expires_at` strictly in the future.
5. Cache under a lock; reuse until expiry minus 2 minutes, then mint a new token.

The permission body is a **reduction**: even if the installed App is broader, the worker asks GitHub for only those three scopes. Tests assert both the reduced body and cache-then-refresh behavior.

Worker wiring (`worker.py`):

```text
GitHubAppAuth(app_id, installation_id, private_key_path)
  -> GitHubClient(token_provider=github_auth.installation_token)
  -> JobRunner(..., github_token_provider=github_auth.installation_token)
```

The same provider is used for Checks API and for git fetch. Checkout never receives the RSA key; it receives a short-lived installation token as `Authorization: Basic base64(x-access-token:<token>)` on fetch only (`workspace.py`). Runner containers get neither.

---

## 3. Webhook HMAC

Source: `trust-ci/src/adaptive_trust_ci/webhooks.py`, API handler in `api.py`, tests in `test_webhooks_github.py` and `test_api.py`.

`verify_webhook_signature(secret, body, signature_header)`:

| Condition | Result |
| --- | --- |
| Empty secret | `WebhookError("webhook secret is not configured")` |
| Missing header or not `sha256=` prefix | malformed |
| Hex after prefix not length 64 | malformed |
| `hmac.compare_digest(expected, supplied)` fails | invalid |

Expected MAC is SHA-256 of the **raw body** with the UTF-8 secret. The API verifies the signature **before** JSON parsing.

`POST /webhooks/github` then:

1. Parses only `X-GitHub-Event: pull_request`.
2. Supported actions: `opened`, `synchronize`, `reopened`, `ready_for_review` → enqueue.
3. `closed` → `store.cancel_pr` (drafts are still cancelled).
4. Other events / unlisted actions → `{accepted: false, reason: "ignored-event"}`.
5. Draft PRs (non-closed) are ignored.
6. Policy `allowed_repositories` miss → HTTP 403.
7. Kill switch → HTTP 503 (no enqueue).
8. Duplicate identity (repo + PR + head SHA + pipeline + policy digest) reuses the job.

There is no GitHub App private key involvement in webhook intake. The secret is `TRUST_CI_WEBHOOK_SECRET` on the API only.

---

## 4. Checks API publication

Source: `trust-ci/src/adaptive_trust_ci/github.py` (`GitHubClient`), orchestrated by `runner.py`.

`GitHubClient` requires **exactly one** of `token` or `token_provider`. Worker uses the provider (fresh installation token per request, including cache). CLI `branch-protect` uses a static admin token.

### `ensure_check_run`

- `GET /repos/{repo}/commits/{sha}/check-runs?check_name={urlencoded name}&filter=latest&per_page=100`
- Reuse if `external_id` matches the durable `job_id` → `PATCH` back to `in_progress` (retry / approval requeue does not create a second check).
- Otherwise `POST /repos/{repo}/check-runs` with:
  - `name` = `policy.check_name`
  - `head_sha` = webhook head SHA
  - `status` = `in_progress`
  - `external_id` = job ID
  - `details_url` = `{public_base_url}/jobs/{job_id}`
  - `started_at` ISO-8601 UTC

### `complete_check_run`

Allowed conclusions: `success`, `failure`, `cancelled`, `timed_out`, `action_required`, `neutral`.

Runner mapping:

| Job outcome | Check conclusion |
| --- | --- |
| all commands pass + signed attestation | `success` |
| command / source-mutation / holdout / policy-digest mismatch | `failure` |
| missing human approval scopes | `action_required` |
| attempts exhausted (`publish_dead_job`) | `failure` |
| stored attestation replay | original attested status |

GitHub’s Checks API only lets the **creating App** update its own check run. Combined with branch protection `app_id`, a PAT, GHA, or another App posting the same text cannot satisfy the gate.

Transport: `urllib` 30s timeout, JSON body, non-2xx → `GitHubError`. API version header is hardcoded `2026-03-10`.

---

## 5. Policy-epoch check naming

Source: `trust-ci/src/adaptive_trust_ci/policy.py`.

- Policy field `status_context` is an **unversioned prefix**. It must be non-empty and must **not** contain `@` (`PolicyError`: epoch is appended automatically).
- Canonical SHA-256 digest is computed over the normalized policy object (sorted repos, sandbox, commands, holdout digest, approval rules, …).
- Required GitHub check name:

```text
{status_context}@{digest[:12]}
```

Example policy uses `status_context: "adaptive-trust-ci/verified"`, so the live gate is:

```text
adaptive-trust-ci/verified@<first-12-hex-of-policy-sha256>
```

Any deployed policy / holdout / runner-image change changes the digest and therefore the required check. An old green check cannot satisfy the new protected-branch rule. `/health/ready` reports `policy_digest` + unversioned `status_context`; Prometheus `adaptive_trust_ci_policy_info` reports the full `check_name` and `policy_epoch`.

`branch-protect` defaults `--context` to `policy.check_name` from `--policy` or `TRUST_CI_POLICY_PATH`. Passing a stale `--context` would bind the wrong epoch.

---

## 6. App-bound branch-protection payload

Source: `github.branch_protection_payload` / `GitHubClient.configure_branch_protection`. Tests: `test_webhooks_github.py`, `test_ops.py`.

`PUT /repos/{repository}/branches/{urlencoded-branch}/protection` body:

```json
{
  "required_status_checks": {
    "strict": true,
    "checks": [{"context": "<policy.check_name>", "app_id": <github_app_id>}]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": <0-6>,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": false
}
```

Invariants:

- Uses modern `checks[]` with `app_id`. Does **not** send the legacy `contexts` array, so a same-named status from another actor does not count.
- Payload string contains no `"actions"` (test lock against GitHub Actions).
- `strict: true` requires the branch to be up to date.
- `required_reviews` default 0 (solo repo still requires a PR + the App check).
- This call is **not** made with the Trust CI App token. It requires `TRUST_CI_GITHUB_ADMIN_TOKEN` (temporary human admin). The long-lived App is intentionally not granted Administration.

---

## 7. How the API cannot publish a final successful check, and only the worker has the App key

This is enforced by **code + settings + compose + tests + holdout**, not by a stripped API binary (the API image still contains `github.py` / `github_app.py` because it installs the same package).

### Code

- `api.py` does not import `GitHubClient` or `GitHubAppAuth`. It never calls Checks API. Every mutating response sets `status_publisher: "worker-github-app"`.
- `ApiSettings` has webhook secret, trust-store path, read token. **No** App ID, installation ID, or private-key path.
- `WorkerSettings` **requires** App ID, installation ID, and private-key path. Worker does **not** load webhook secret or trust store.
- Holdout (`holdout.example/validate.py`) fails closed if `GitHubClient` or `GitHubAppAuth` appear in `api.py`, and requires `GitHubAppAuth` in `worker.py`.

### Deployment

`trust-ci/compose.yaml`:

| Mount / env | api | worker |
| --- | --- | --- |
| `env/api.env` (`WEBHOOK_SECRET`, `TRUST_STORE_PATH`, `READ_TOKEN`) | yes | no |
| `env/worker.env` (`GITHUB_APP_*`, signing key path) | no | yes |
| `runtime/trust-store.json` | yes (ro) | no |
| `runtime/github-app-private-key.pem` | **no** | yes (ro) `/run/secrets/...` |
| `runtime/trust-ci-signing-key.pem` | no | yes (ro) |
| Docker / DinD (`DOCKER_HOST`) | no | yes |
| `env/common.env` (DB, policy, public URL, kill switch) | yes | yes |

`test_ops.py` asserts `github-app-private-key.pem:/run/secrets` appears in the worker service and **not** in the compose file before `worker:`.

Images:

- `Dockerfile.api`: postgresql-client, no git/docker, entrypoint `adaptive-trust-ci api`.
- `Dockerfile.worker`: git + docker CLI, entrypoint `adaptive-trust-ci worker`.

### Runtime

- Runner env is a sanitized allowlist; secret-like names (`TOKEN|SECRET|PASSWORD|KEY|…`) are rejected. Tests assert no `GITHUB_TOKEN` / `TRUST_CI_GITHUB` in sandbox argv.
- Installation token is used for git fetch headers only; it is not written into the workspace or passed into `--network none` runner containers.

Compromise caveat: isolation is config + “API process never instantiates a client”. If an operator put the App key into `common.env` **and** mounted the PEM into the API, a compromised API could import `GitHubClient`. Compose examples and tests exist specifically to prevent that.

---

## 8. Environment variables and GitHub permissions

### Common (`env/common.env.example`) — API and worker

| Variable | Purpose |
| --- | --- |
| `TRUST_CI_DATABASE_URL` | PostgreSQL |
| `TRUST_CI_POLICY_PATH` | Server-mounted policy |
| `TRUST_CI_PUBLIC_BASE_URL` | HTTPS (localhost HTTP allowed); used as check `details_url` |
| `TRUST_CI_KILL_SWITCH_PATH` | Shared STOP file (default `/run/adaptive-trust-ci/STOP`) |

### API-only (`env/api.env.example`)

| Variable | Purpose |
| --- | --- |
| `TRUST_CI_WEBHOOK_SECRET` | HMAC for `X-Hub-Signature-256` |
| `TRUST_CI_TRUST_STORE_PATH` | Human Ed25519 public keys |
| `TRUST_CI_READ_TOKEN` | Bearer for `/jobs`, `/attestations`, `/metrics` |
| `TRUST_CI_ROLE=api` | `doctor` subset |

### Worker-only (`env/worker.env.example`)

| Variable | Purpose |
| --- | --- |
| `TRUST_CI_GITHUB_APP_ID` | JWT `iss` and branch-protect `app_id` |
| `TRUST_CI_GITHUB_INSTALLATION_ID` | Token mint path |
| `TRUST_CI_GITHUB_APP_PRIVATE_KEY_PATH` | RSA PEM (GitHub-issued) |
| `TRUST_CI_SIGNING_KEY_PATH` | CI Ed25519 attestation key |
| `TRUST_CI_RUNNER_IMAGE` | Must equal `policy.sandbox.image` (digest-pinned) |
| `TRUST_CI_WORKSPACE_ROOT` / `_HOST_ROOT` | Checkout + DinD mount |
| `TRUST_CI_HOLDOUT_HOST_PATH` | Host path of holdout as seen by dockerd |
| `TRUST_CI_WORKER_ID` | Lease owner |
| `TRUST_CI_POLL_INTERVAL_SECONDS` | Claim loop (0.1–300, default 2) |
| `TRUST_CI_ROLE=worker` | `doctor` subset |

Compose interpolation (`trust-ci/.env.example`): immutable `TRUST_CI_{API,WORKER,RUNNER,POSTGRES,DIND,PYTHON_BASE}_IMAGE` digests and `TRUST_CI_HOLDOUT_SOURCE_PATH`.

### One-shot human CLI (not in service env files)

| Variable | Purpose |
| --- | --- |
| `TRUST_CI_GITHUB_ADMIN_TOKEN` | **Required only** for `branch-protect` |
| `TRUST_CI_GITHUB_APP_ID` | If `--app-id` omitted |
| `TRUST_CI_POLICY_PATH` | If `--policy` omitted |

Do not put the admin token in `worker.env` or `api.env`.

### GitHub App repository permissions (create/install)

Required by handoff / README / rollout:

```text
Checks: Read and write
Contents: Read-only
Pull requests: Read-only
Metadata: Read (implicit)
```

Worker token request further reduces to `checks:write`, `contents:read`, `pull_requests:read`.

**Do not** grant the App Administration, Contents write, Workflows, or Secrets. Branch protection is applied with a temporary human admin token (classic PAT with `repo` + admin, or fine-grained “Administration: Read and write” on that repository), then revoked.

Repository webhook (separate from App permissions):

```text
Payload URL: https://<TRUST_CI_PUBLIC_BASE_URL>/webhooks/github
Content type: application/json
Secret: same value as TRUST_CI_WEBHOOK_SECRET
Events: Pull requests only
```

---

## 9. CLI commands: `branch-protect`, webhook, `holdout-digest`, `keygen`

Entry point: `adaptive-trust-ci` → `adaptive_trust_ci.cli:main`.

### `branch-protect` — exists

```bash
TRUST_CI_GITHUB_ADMIN_TOKEN=<temporary-admin-token> \
TRUST_CI_GITHUB_APP_ID='<app-id>' \
adaptive-trust-ci branch-protect \
  --policy "$PWD/runtime/policy.json" \
  --repository Dimkox/adaptive-grok-build-pro \
  --branch main \
  --required-reviews 0
```

Flags: `--repository` (required), `--branch` (default `main`), `--required-reviews` (default 0), `--context` (optional override of `policy.check_name`), `--policy`, `--app-id`. Uses `GitHubClient(token=admin_token)`, **not** the App JWT. Exits if admin token missing: `TRUST_CI_GITHUB_ADMIN_TOKEN is required only for this administration command`.

### `webhook` — does **not** exist

`cli.py` has no `webhook` subparser. Webhook registration is a GitHub UI (or GitHub REST) operator step documented in `trust-ci/README.md` and `engineering/runbooks/trust-ci-rollout.md`. Closest related commands:

- `adaptive-trust-ci api` — process that **receives** webhooks
- `adaptive-trust-ci doctor` — with `TRUST_CI_ROLE=api` validates policy/DB/trust-store, not GitHub delivery

There is no command that creates the GitHub webhook.

### `holdout-digest` — exists

```bash
adaptive-trust-ci holdout-digest --path /opt/adaptive-trust-ci-holdout
```

Prints the deterministic SHA-256 of the tree (paths + executable bits + file hashes; symlinks forbidden). That digest must be copied into deployed `policy.holdout.digest`. Worker `verify_bundle` fails closed on mismatch **before** checkout execution.

### `keygen` — exists, but it is **not** GitHub App keygen

```bash
adaptive-trust-ci keygen --private <path.pem> --public <path.pub.pem>
```

Generates an **Ed25519** pair (`Signer.generate`), writes 0600 private, prints `key_id`. Used for:

1. Worker CI attestation key (`TRUST_CI_SIGNING_KEY_PATH`)
2. Human approval keys (private stays off-server; public + `key_id` go into `trust-store.json`)

GitHub App RSA keys are created by GitHub when the App is registered (download `.pem`). `doctor` (worker/all role) only **validates** that PEM by calling `generate_app_jwt`; it does not generate it.

Other relevant commands: `api`, `worker`, `migrate`, `policy-digest`, `doctor`, `approval-*`, `attestation-verify`, `kill-switch`, backups. None of them publish a GitHub check except `worker`.

---

## 10. What is needed to activate a real GitHub App and bind branch protection (no GitHub Actions)

Do **not** add `.github/workflows/`. Tests already fail if that directory exists. The merge gate is the App-owned Check Run, not Actions.

### A. Provision the App (human, in GitHub UI)

1. Create a dedicated GitHub App (name e.g. Adaptive Trust CI).
2. Permissions: Checks RW, Contents R, Pull requests R (Metadata R implicit).
3. **No** Administration, no Workflows, no Contents write.
4. Webhook of the App itself can stay unused; this codebase uses a **repository** webhook.
5. Generate and download the App RSA private key. Store it only as `trust-ci/runtime/github-app-private-key.pem` (or a secret manager) on the CI host. Never commit it; never mount it into `api`.
6. Install the App on `Dimkox/adaptive-grok-build-pro`.
7. Record numeric **App ID** and **installation ID** into `env/worker.env` only.
8. Confirm `policy.example.json` `allowed_repositories` matches the real `owner/repo`.

### B. Split secrets

| Secret | Where |
| --- | --- |
| App RSA PEM + App ID + installation ID | worker only |
| Webhook HMAC | API `TRUST_CI_WEBHOOK_SECRET` **and** GitHub webhook secret (same value) |
| CI Ed25519 private | worker `keygen` |
| Human Ed25519 private | human workstation only |
| Human public + key_id | API trust store |
| Temporary admin token | operator shell for `branch-protect` only, then revoke |

### C. Deploy the control plane first

1. Pin immutable API/worker/runner/postgres/dind image digests in compose `.env` and `runtime/policy.json` (`sandbox.image` must equal `TRUST_CI_RUNNER_IMAGE`).
2. Install holdout **outside** the checkout; set `policy.holdout.digest` from `holdout-digest`.
3. **Fix the holdout/source mismatch before first real job** (see §11).
4. `docker compose up -d postgres migrate api worker`.
5. `curl -fsS https://ci.example.com/health/ready` must show `status_publisher: worker-github-app` and current `policy_digest`.
6. Terminate TLS on a reverse proxy. Public URL must be HTTPS (`TRUST_CI_PUBLIC_BASE_URL`). Expose `/webhooks/github` and `/approvals`; protect `/jobs` and `/metrics` with the read token.

### D. Register webhook, then prove the check **before** protecting `main`

Rollout order is mandatory (`trust-ci/README.md`, `engineering/runbooks/trust-ci-rollout.md`):

1. Deploy API + PostgreSQL + worker.
2. Create repository webhook (PR events, HMAC).
3. Open/update a **disposable** documentation PR (or draft PR #2 once ready).
4. Confirm: webhook 200, one PostgreSQL job for that exact head SHA, worker lease, Check Run named `adaptive-trust-ci/verified@<policy-sha12>` on that SHA, **owned by the Trust CI App**, `external_id` = job ID.
5. `attestation-verify` the stored envelope with the CI public key.
6. Prove a new SHA does not inherit the old check; prove `trust-ci/**` goes `action_required` until a human Ed25519 approval.
7. **Only then** run `branch-protect` with a temporary admin token against the **deployed** policy file (same digest the worker used).
8. Verify: same check text from another actor does not satisfy; direct push / force push / delete fail; merge without the App-owned epoch check fails.

Protecting `main` before the App-owned check is observed can lock the repository because GitHub will require a context that has never been produced.

### E. Bind PR #2 without Actions

PR #2 stays draft until the App-owned check exists for its exact head SHA. Branch protection, once applied, requires that name **and** that App ID. Local `grok_verify` / receipts / delegated grants remain non-authoritative.

---

## 11. Integration gaps and activation risks

1. **Holdout vs `github.py` mismatch (blocker).**  
   `holdout.example/validate.py` requires the literal  
   `'checks': [{'context': status_context, 'app_id': app_id}]`  
   in `github.py`. Live code uses `normalized_name`. The example holdout digest matches the example bundle files (`test_ops`), but `validate.py` is executed **against the PR workspace**. First real job using the example holdout will fail holdout validation and never publish `success`. Align the holdout string (or the source identifier) and recompute `policy.holdout.digest` before activation.

2. **No webhook provisioner.** Operators must create the GitHub webhook manually. Documented, but easy to skip or to point at HTTP.

3. **`keygen` does not create the GitHub App RSA key.** Operators who run `keygen` into `github-app-private-key.pem` will fail `doctor` / token mint (Ed25519 ≠ RSA).

4. **Design spec is stale.** `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md` still describes commit-status publication from the API. Implementation is worker-only Checks API. Follow `trust-ci/README.md` and the rollout runbook.

5. **Hardcoded `X-GitHub-Api-Version: 2026-03-10`.** Confirm this version is accepted by api.github.com at activation time; a 400 from GitHub would block both token mint and check publication.

6. **API image still contains GitHub client modules.** Trust depends on not loading them and not mounting the key. Keep compose tests; do not merge App secrets into `common.env`.

7. **`branch-protect` is not idempotent-safe against human UI drift.** It PUTs a full protection object. Re-run after policy epoch change (new digest → new required context). Re-run after App recreation (new `app_id`).

8. **Public URL and details links.** Checks include `details_url` under `TRUST_CI_PUBLIC_BASE_URL`. If that URL is unreachable or still `https://ci.example.com`, GitHub will show a dead link; publication itself can still succeed.

9. **Draft PRs.** Intake ignores drafts (except `closed`). PR #2 is draft by handoff until the check exists — GitHub will not enqueue until it is marked ready or the webhook is tested with a non-draft disposable PR.

10. **Installation token vs private repos.** `contents:read` is required to fetch `refs/pull/N/head`. Public clone would still use the installation token path.

---

## 12. Files inspected

- `trust-ci/src/adaptive_trust_ci/github.py`
- `trust-ci/src/adaptive_trust_ci/github_app.py`
- `trust-ci/src/adaptive_trust_ci/webhooks.py`
- `trust-ci/src/adaptive_trust_ci/cli.py`
- `trust-ci/src/adaptive_trust_ci/api.py`
- `trust-ci/src/adaptive_trust_ci/worker.py`
- `trust-ci/src/adaptive_trust_ci/runner.py`
- `trust-ci/src/adaptive_trust_ci/workspace.py`
- `trust-ci/src/adaptive_trust_ci/settings.py`
- `trust-ci/src/adaptive_trust_ci/policy.py`
- `trust-ci/src/adaptive_trust_ci/holdout.py`
- `trust-ci/tests/test_github_app.py`
- `trust-ci/tests/test_webhooks_github.py`
- `trust-ci/tests/test_api.py`
- `trust-ci/tests/test_ops.py`
- `trust-ci/tests/test_policy.py`
- `trust-ci/env/*.example`
- `trust-ci/.env.example`
- `trust-ci/config/policy.example.json`
- `trust-ci/compose.yaml`
- `trust-ci/Dockerfile.api`, `Dockerfile.worker`
- `trust-ci/holdout.example/validate.py`
- `trust-ci/README.md`
- `engineering/runbooks/trust-ci-rollout.md`
- `GROK_BUILD_HANDOFF.md`
- `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md` (stale vs implementation)

## 13. Recommendation for this change

Code for JWT, HMAC, Checks, epoch naming, and app-bound protection is present and unit-tested. Activation work is operational, not a GitHub Actions feature:

1. Repair holdout/`github.py` string lock so a real job can pass holdout.
2. Provision App + installation; mount key only on worker.
3. Deploy, register repository webhook, prove App-owned epoch check on a non-draft SHA.
4. Run `adaptive-trust-ci branch-protect` with a throwaway admin token.
5. Keep PR #2 draft until that exact-SHA check is visible; never add `.github/workflows/`.
