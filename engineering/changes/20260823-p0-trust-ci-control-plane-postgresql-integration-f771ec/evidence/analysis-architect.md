# Analysis — architect

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Route: `f771ecaf458d` · write=`null` · reviews=`code_reviewer`+`test_reviewer`+`security_reviewer`+`data_reviewer`  
Human gate: `scope_and_design_approval`  
Branch / PR: `feat/trust-ci-control-plane` / draft `#2`

Read-only. No product-code edits. No `.env`. No push / merge / deploy / GitHub App mutation from this agent.

Narrow question: What is the bounded operational sequence from the existing design/plan/handoff for PostgreSQL integration, GitHub App, deploy, and branch protection? What must stay outside the PR trust domain? What residual risks and fail-closed constraints must the parent preserve?

---

## Ruling (one screen)

**This is operational activation of an already-implemented control plane, not a product rewrite.** `write_agent` is null. Do not dispatch an implementer. Do not add GitHub Actions. Do not replace PostgreSQL with repository JSON/SQLite. Do not merge PR `#2` as closure.

Later operational docs supersede the original design’s “merge the code before branch protection”:

| Source | Sequence |
| --- | --- |
| Design `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md` Rollout §1 | Merge through a PR, then protect `main` |
| Plan Task 9 | Open PR from `feat/trust-ci-control-plane`; do not merge directly |
| Handoff / `trust-ci/README.md` / `engineering/runbooks/trust-ci-rollout.md` / `AGENTS.md` Independent merge trust | Keep `#2` draft → deploy independently → prove App-owned policy-epoch check on an exact SHA → then protect `main` → then mark `#2` ready. Merge stays human-owned. |

**Follow the later sequence.** Merging before the live App-owned check exists would put Trust CI on `main` without a gate. Applying protection before the check is observed can lock the repository.

Chicken-and-egg resolution: build and deploy from the reviewed `feat/trust-ci-control-plane` tree; do not wait for `#2` to land on `main`. The service lives outside the PR trust domain. `#2` then consumes the live check like any other PR.

| In | Out |
| --- | --- |
| Reproduce baseline on the current SHA | New product features, new pipeline types, auto-merge |
| Live PostgreSQL integration (unskip + restart probe) | MemoryStore-only “green” as production evidence |
| Pin immutable API/worker/runner/postgres/dind images | Mutable `:latest` / unpinned tags in deployed policy |
| Create/install GitHub App; worker-only App key | Granting `administration` to the long-lived App |
| Deploy isolated CI host: Postgres, migrate, API, worker, holdout, TLS | Colocating privileged DinD with production workloads |
| Prove webhook → exact-SHA Check Run → offline attestation | Treating local receipts / `grok_approve.py` as the verdict |
| App-bound `branch-protect` **after** the check is observed | Protecting `main` first; GHA required checks |
| Update draft `#2` with external evidence; mark ready only then | Agent merge, tag, release, production mutation |

Stop before GitHub App creation, deploy, webhook registration, or `branch-protect` unless the user has an exact delegated local grant for that named action and resource. Human Ed25519 approval keys are never generated, read, requested, submitted, or simulated in the agent environment.

---

## 0. What is already done vs what this change owns

Implemented on `feat/trust-ci-control-plane` (handoff “Current code state” + tree):

- PostgreSQL jobs, attempts, leases, heartbeats, nonce uniqueness, events, signed attestations
- HMAC webhook intake; API does not import `GitHubClient` / `GitHubAppAuth`
- Worker GitHub App JWT + reduced installation token; Checks API; policy-epoch check name
- App-bound branch-protection payload
- Isolated no-network runner, external holdout, source-mutation failure, Ed25519 approvals/attestations
- Kill switch, checksum-locked migrations, backup/restore CLI, metrics, isolated DinD (not raw socket on worker)

Local preflight already recorded (`engineering/reviews/trust-ci-p0-local-verification.md`):

```text
root suite: 32 passed
Trust CI suite: 97 executed, PostgreSQL live tests skipped (no TRUST_CI_TEST_DATABASE_URL)
compileall: passed
```

That is **not** the merge verdict. This change owns only the remaining external activation:

1. baseline reproduction on the live SHA
2. real PostgreSQL integration
3. immutable artifact pins
4. GitHub App
5. isolated deploy
6. webhook proof
7. approval proof
8. app-bound branch protection
9. PR `#2` evidence pack

If baseline or live Postgres exposes a product bug, stop and open a new route with a write owner. Do not patch Trust CI in this route.

---

## 1. Bounded operational sequence

Execute in order. Do not skip a prove-step. Do not protect `main` before step 8’s precondition. Record exact command output and current SHA; do not reuse an earlier run.

### 1. Reproduce the local baseline

Handoff §1. From repository root, current `HEAD`:

```bash
PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest discover -s tests -v
PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest discover -s trust-ci/tests -v
python3 -m compileall -q .grok-stack/adaptive_grok scripts trust-ci/src tests trust-ci/tests
python3 scripts/grok_verify.py --mode pr --no-record --json
```

Pass criteria: all non-Postgres tests pass; `git diff --check` clean; **no** `.github/workflows/`. Four-to-eight Postgres tests may still skip here. A skip is not a pass.

### 2. Run real PostgreSQL integration

Handoff §2 + runbook “PostgreSQL acceptance”. Two complementary harnesses; both are required before calling integration done.

**2a. Unskip the live unittest class.** Start a disposable PostgreSQL 16, export `TRUST_CI_TEST_DATABASE_URL`, rerun:

```bash
PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest -v tests.test_postgres_integration
```

The class is gated by `@unittest.skipUnless(DATABASE_URL, ...)`. Current tests that **must execute and pass** (more than the four named in the older verification note):

| Required scenario | Test |
| --- | --- |
| Migration registry current and idempotent | `test_migration_registry_is_current_and_idempotent` |
| Two workers claiming concurrently / `SKIP LOCKED` | `test_two_concurrent_workers_cannot_claim_same_live_job` |
| Lease expiry and reclaim | `test_expired_database_lease_is_reclaimed_by_another_worker` |
| Heartbeat ownership | `test_heartbeat_requires_current_lease_owner` |
| Attempt exhaustion to `dead` | `test_expired_lease_at_attempt_limit_becomes_dead` |
| Duplicate webhook identity | `test_duplicate_webhook_identity_returns_same_job` |
| Approval nonce replay | `test_approval_nonce_replay_is_rejected_by_database_constraint` |
| Attestation durability across store instances | `test_signed_attestation_survives_new_store_instance` |

**2b. PostgreSQL restart/recovery** is **not** in that class and **not** in `compose.test.yaml`. Run `trust-ci/tests/postgres_restart_probe.py`:

```text
seed → restart PostgreSQL → verify
```

Fail if the durable job disappears or its SHA/policy digest changes.

**2c. Production-shaped harness** after image pins exist:

```bash
trust-ci/scripts/postgres-integration.sh
```

Use the script, not the stale runbook line `--exit-code-from tests`. The live service name is `postgres-integration`. `compose.test.yaml` refuses to start without `TRUST_CI_POSTGRES_IMAGE` and `TRUST_CI_PYTHON_BASE_IMAGE` as `name@sha256:<64-hex>` (or `sha256:<64-hex>`).

Cleanup: the script traps `down --volumes --remove-orphans`. Do not leave a test database attached to the deploy compose project.

### 3. Build and pin immutable artifacts

Handoff §3. Production `compose.yaml` has **no** `build:` keys. Build through the override:

```bash
cd trust-ci
# TRUST_CI_PYTHON_BASE_IMAGE must already be an immutable digest.
docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image
```

Do **not** treat `docker compose --profile build build` against `compose.yaml` alone as sufficient; that file cannot build images.

Replace mutable tags with digests in **deployed** env and `runtime/policy.json` (never commit production env or private keys):

```text
TRUST_CI_POSTGRES_IMAGE
TRUST_CI_API_IMAGE
TRUST_CI_WORKER_IMAGE
TRUST_CI_RUNNER_IMAGE   # must equal policy.sandbox.image or worker refuses to start
TRUST_CI_DIND_IMAGE
holdout bundle digest
policy digest / check name adaptive-trust-ci/verified@<policy-sha12>
CI public attestation key
SBOM
vulnerability scan report
```

`policy.example.json` still contains `adaptive-trust-ci-runner@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST`. Deploying the example unchanged is expected to fail closed. Copy to `runtime/policy.json` on the CI host and pin the real digest there.

Rebuilding the runner, policy, or holdout **changes the policy epoch and the required check name**. Old jobs and approvals become invalid by design.

### 4. Create and install the GitHub App

Handoff §4. Dedicated App, repository permissions only:

```text
Checks: Read and write
Contents: Read-only
Pull requests: Read-only
Metadata: Read   # implicit on GitHub Apps
```

Do **not** grant Administration, Workflows, or Contents: write. Provision separately and split by role:

| Secret | Mounts into | Must not reach |
| --- | --- | --- |
| GitHub App ID + installation ID + RSA private key | worker only (`env/worker.env`, `/run/secrets/github-app-private-key.pem`) | API, runner, repository, agent |
| Webhook HMAC secret | API only (`env/api.env`) | worker, runner |
| CI Ed25519 signing key | worker only | API, runner, humans’ laptops except public key |
| Human approval private key | human workstation / HSM | API, worker, agent, git |
| Human public keys + `key_id` | API trust store | worker |
| Temporary `TRUST_CI_GITHUB_ADMIN_TOKEN` | one-shot `branch-protect` | long-lived App, compose env files |

The worker requests an installation token reduced to `checks:write`, `contents:read`, `pull_requests:read` even if the installed App is broader. Keep the installed App at those three. The API image has no GitHub credentials and cannot publish a Check Run.

### 5. Deploy the self-hosted service

Handoff §5 + runbook Deploy. Isolated CI host/VM, no production workloads.

Order on the host:

1. Copy env templates to untracked `trust-ci/env/*.env` and `runtime/policy.json` / `runtime/trust-store.json`. `chmod 600`.
2. Insert a real human **public** key into the trust store. Zero active keys → `/health/ready` is 503 (fail-closed).
3. Generate CI attestation key on the CI server or secret manager; mount private PEM worker-only; publish the public key for offline verify.
4. Install the reviewed holdout **outside** any checkout (`TRUST_CI_HOLDOUT_SOURCE_PATH` absolute). `adaptive-trust-ci holdout-digest --path …` must match policy `holdout.digest`.
5. `docker compose up -d postgres migrate api worker` using digest-pinned image env vars. `runner-loader` must resolve `TRUST_CI_RUNNER_IMAGE` to the same digest before the worker starts.
6. `curl -fsS http://127.0.0.1:8080/health/ready` then terminate TLS at a reverse proxy. Expose `/webhooks/github` and `/approvals`. Keep `/jobs/*`, `/attestations/*`, `/metrics` bearer-protected.
7. Confirm backup target and `adaptive-trust-ci-backup.timer` (or equivalent) exist. Store dumps separately from every private key class. Run a restore drill against a disposable DSN with `--confirm-disposable` before calling recovery proven.

`TRUST_CI_PUBLIC_BASE_URL` must be HTTPS outside localhost.

### 6. Register and prove the webhook flow

Handoff §6 + README “Use rollout order strictly”.

Webhook: `https://<ci-host>/webhooks/github`, `application/json`, secret = API-only `TRUST_CI_WEBHOOK_SECRET`, events = Pull requests.

Then update draft PR `#2` **or** a disposable docs-only PR and prove, in order:

```text
webhook accepted (HMAC)
exact SHA job stored in PostgreSQL (one row, idempotent on replay)
worker claims one lease (API does not publish)
immutable runner digest in logs
holdout executed from outside checkout
runner --network none, cap-drop ALL, no secrets, no Docker socket
tracked-source mutation of a fixture that exits 0 still fails (source-integrity)
signed attestation stored
App-owned check adaptive-trust-ci/verified@<policy-sha12> on the exact head SHA
external_id == durable job_id
GitHub shows the Trust CI App as owner, not a PAT and not Actions
offline attestation-verify with the CI public key
```

Do not continue if any line is ambiguous.

### 7. Prove approval behavior

Handoff §7. Prefer a **disposable** PR so `#2` is not the only specimen.

| Case | Expected |
| --- | --- |
| Documentation-only diff | runs without approval; Check Run can succeed |
| `trust-ci/**` (or other `governance` glob) diff | Check Run `action_required`; job `needs_approval`; **no** tests convert that to success |
| Wrong signer scope | HTTP 403 |
| Tampered payload | 403 |
| Replayed nonce | 409 / `ReplayError` |
| New commit | old approval does not match new head SHA |
| Policy or holdout change | digest/epoch change; old approval invalid |
| Valid human-signed approval from **outside** the agent environment | API requeues **only** that exact SHA; worker restarts the **same** durable Check Run |

Agent must not create or hold the human private key. The human workstation runs `approval-create` / `approval-submit`.

### 8. Protect `main`

Handoff §8. **Precondition:** the App-owned policy-epoch check has appeared and succeeded on an exact SHA.

Temporary human administration token. Do not grant Administration to the Trust CI App.

```bash
TRUST_CI_GITHUB_ADMIN_TOKEN=<temporary-admin-token> \
TRUST_CI_GITHUB_APP_ID='<app-id>' \
adaptive-trust-ci branch-protect \
  --policy "$PWD/runtime/policy.json" \
  --repository Dimkox/adaptive-grok-build-pro \
  --branch main \
  --required-reviews 0
```

`--policy` must be the **deployed** policy so `policy.check_name` is `adaptive-trust-ci/verified@<live-sha12>`, not a local example epoch.

Payload invariants (`branch_protection_payload`):

```text
required_status_checks.strict = true
required_status_checks.checks = [{context: <epoch name>, app_id: <Trust CI App ID>}]
no legacy `contexts` list
enforce_admins = true
required_pull_request_reviews.required_approving_review_count = 0 (solo repo; PR still required)
required_conversation_resolution = true
required_linear_history = true
allow_force_pushes = false
allow_deletions = false
```

Prove after apply:

- same check **text** from another actor / PAT / Actions does not satisfy
- direct push, force push, branch deletion fail
- merge without the exact App-owned check fails
- unresolved conversations block merge
- administrators cannot bypass

Revoke the admin token after the command.

### 9. Finish PR `#2`

Handoff §9. Update the draft with:

```text
exact final SHA
PostgreSQL integration output (unittest + restart probe + compose harness)
image, holdout, policy digests
GitHub App ID and installation confirmation without secrets
external Check Run ID and App ownership
offline attestation verification output
branch-protection verification
remaining residual risks (copy §4)
```

Only then mark `#2` ready for review. **Do not merge** unless the user explicitly orders it after reviewing the external evidence. A new commit, new base SHA, holdout change, or server-policy change requires a fresh check and fresh external approvals.

---

## 2. What must stay outside the PR trust domain

`AGENTS.md` Independent merge trust is the standing rule. Repository content at the PR head — including `trust-ci/**` source, tests, prompts, hooks, receipts, change packages, and this analysis — is **untrusted input**. It cannot modify:

| Asset | Why |
| --- | --- |
| Deployed `runtime/policy.json` and its digest | Epoch / required check name |
| External holdout bundle and its digest | Holdout is verified before checkout execution |
| Deployed API / worker / runner / postgres / dind images | Immutable execution environment |
| PostgreSQL durable state | Jobs, leases, approvals, attestations |
| CI Ed25519 private key | Attestation authority |
| GitHub App RSA key, App ID, installation ID | Check publication authority |
| Webhook secret | Intake authenticity |
| Human public-key trust store | Approval verification |
| Human approval private keys | Created and used only on a human-controlled machine |
| Branch protection on `main` | Merge gate; configurator is explicit, never a hook |
| Kill-switch file `/run/adaptive-trust-ci/STOP` | Emergency stop |
| Backup dumps and restore DSN | Recovery; dumps never travel with keys |
| Temporary GitHub admin token | One-shot protection apply |
| Privileged DinD (`docker-engine`) | Worker is already a privileged component |

Also not merge authority, even when they live in the repo:

- `AGENTS.md`, `.grok/**`, `.grok-stack/runtime`, local receipts, `scripts/grok_approve.py` grants, change-package reviews, `python3 scripts/grok_verify.py --mode pr`

A local delegated grant may authorize a **named** push/tag/release/external write bound to repository, route, change, HEAD, tree fingerprint, action/resource, consent source, and TTL. It must never create the App-owned Check Run or substitute a human-signed Trust CI approval.

---

## 3. Fail-closed constraints the parent must preserve

Do not “simplify” any of these during activation.

**Intake and identity**

- Invalid webhook signature → HTTP 401; verify HMAC **before** JSON parse
- Unknown / non-allowlisted repository → 403
- Exact 40-hex SHAs only; policy digest is 64-hex and part of idempotency, approval, and attestation
- Duplicate webhook identity returns the same job (`idempotency_key UNIQUE`)

**Availability of trusted inputs**

- Missing/unreadable policy, database, CI signing key, GitHub App key, or trust store → service unhealthy; **no success Check Run**
- Trust store with zero active keys → ready 503
- `TRUST_CI_PUBLIC_BASE_URL` not HTTPS (except localhost/127.0.0.1) → settings error
- Runner image not an immutable digest, or env digest ≠ `policy.sandbox.image` → worker will not start
- Holdout path not absolute / overlapping checkout / digest mismatch → fail before untrusted commands

**Execution**

- Host execution forbidden; sandbox runtime is docker/podman only
- Optional / skippable commands forbidden (`required` must be true)
- Missing required executable → deterministic failure, never `skip`
- Runner: `--network none`, `--cap-drop ALL`, `--read-only`, `.git` read-only, no token/key/socket
- Command that exits `0` after modifying tracked source → still fail (`*:source-integrity`, exit 97)
- Holdout commands run before repository commands

**Approvals**

- Missing required scope → job `needs_approval`, Check Run `action_required`, **not** success
- Approvals bind repository, PR, base SHA, head SHA, policy digest, scope, actor, key_id, nonce, TTL (≤ policy max, default 1800s)
- Replay nonce / approval ID → reject
- New commit, new base, policy change, holdout change → old approval dead; no separate revocation required
- Human private keys never in API, worker, checkout, or agent workspace

**Publication and merge**

- API cannot publish a Check Run (holdout asserts `GitHubClient` / `GitHubAppAuth` absent from `api.py`)
- Worker is the only publisher; one durable Check Run per job (`external_id = job_id`); retries PATCH the same run
- Inability to publish GitHub status → job cannot become `passed`
- After a stored signed attestation, replay into the same Check Run; do not rerun untrusted code for a publication outage
- Required check name is `adaptive-trust-ci/verified@<first-12-hex-of-policy-sha256>`; a green check from an older epoch cannot satisfy the current rule
- Branch protection binds **both** that name **and** the Trust CI App ID
- Kill switch blocks new jobs, approvals, and claims; it does not remove protection or convert failure into success
- Local Grok hooks remain fail-open for usability and are **not** the merge decision
- No `.github/workflows/**`, Dependabot workflows, or workflow_dispatch

**Data**

- PostgreSQL is the only durable job store; `FOR UPDATE SKIP LOCKED` claims
- Lease expiry reclaims while `attempts < max_attempts`; else `dead` / `attempts-exhausted-after-worker-loss`
- Schema migrations are checksum-locked; edited historical SQL is a startup failure
- Backup manifests contain hashes, not credentials; restore requires `--confirm-disposable`

---

## 4. Residual risks the parent must preserve (not silently “fix”)

These remain after a successful activation. Do not expand this change to close them unless a later routed write task is approved.

1. **Privileged DinD.** `compose.yaml` `docker-engine` is `privileged: true` with unauthenticated TCP `2375` on the `executor` network. Worker has no raw `/var/run/docker.sock` (good), but the daemon is still a high-value process. Hardening plan Task 5 wanted a **restricted Docker API proxy**; that proxy is not what shipped. Keep the worker off production hosts. Do not mount the socket into API or runner.

2. **Restart probe gap vs compose harness.** `compose.test.yaml` runs only `tests.test_postgres_integration`. Parent must still run `postgres_restart_probe` around a real restart. Do not delete the probe to make the harness look complete.

3. **Stale runbook command.** `--exit-code-from tests` does not match the service name. Use `trust-ci/scripts/postgres-integration.sh`.

4. **Stale README build command.** `docker compose --profile build build` against `compose.yaml` alone cannot build. Parent must use `compose.build.yaml` + pinned `TRUST_CI_PYTHON_BASE_IMAGE`.

5. **Handoff “4 skipped tests” is stale.** The live class now has eight tests. Unskip all of them. Do not stop at four.

6. **Example policy cannot be deployed as-is.** Runner digest placeholder, example holdout digest, example public URL. Copy-and-pin on the host. Do not commit `runtime/policy.json` with production digests if that file is gitignored; do not commit secrets if it is not.

7. **Product VERSION vs Trust CI 2.1.0.** Root `VERSION` is `2.0.11`; Trust CI package/API reports `2.1.0`. Identity work is already on the branch. This activation does not bump or retag the product.

8. **Solo-repo review count is 0.** Protection still requires a PR + App-owned check + admin enforcement. If a second human reviewer is later required, that is a protection-policy change, not a code change.

9. **Policy/holdout rollback changes the epoch.** Restoring old images without updating branch protection to the restored check name will lock merges. Runbook rollback: kill switch → keep Postgres/attestations → human admin removes **only** the exact required check → repair → prove on a disposable PR → re-apply protection with restored name + App ID. Never substitute a local receipt or forged success.

10. **Admin-token blast radius.** `branch-protect` uses a PAT/admin token that can rewrite protection. Short TTL, one command, then revoke.

11. **Shadow-mode / no auto-merge.** Design forbids auto-merge and production deploy in this contour. Keep them disabled.

12. **Attestation replay after GitHub outage** is implemented in `JobRunner.process` when a stored envelope exists. It is not covered by `test_postgres_integration`. Prove it operationally (step 6) or treat it as residual until a live publication-failure drill is recorded.

13. **`scope_and_design_approval`.** Adaptive-delivery requires this bounded design to be recorded before operational writes. This report is that design. External writes still need exact delegated grants.

14. **Original design merge-first.** If a later agent cites design Rollout §1 against the handoff, the handoff/runbook/AGENTS.md win. Record that ruling in the change package if challenged.

---

## 5. Parent stop / go conditions

**Go to step 1 (baseline)** with no further design debate.

**Do not go to steps 4–8** without: baseline green on the current SHA; live Postgres tests + restart probe green; image/holdout/policy digests in hand; isolated host; and an exact delegated grant per external action.

**Do not protect `main`** without a GitHub-visible App-owned `adaptive-trust-ci/verified@<live-policy-sha12>` on an exact SHA, owned by the Trust CI App ID that will be bound.

**Do not merge `#2`** from this route. `write_agent` is null; merge is a separately ordered human action after the external check and this evidence pack exist.

**Fail closed / stop the wave if:** GitHub Actions appear; a private key or `.env` is about to be committed or read; an agent is asked to sign a Trust CI approval; PostgreSQL is about to be replaced with JSON/SQLite; branch protection is requested before the App-owned check exists; or a product-code fix is required (new route, new write owner).

---

## 6. Mapping back to change-package stubs

The change package `brief.md` / `requirements.md` / `architecture.md` / `tasks.md` / `test-plan.md` / `rollback.md` / `release.md` are still empty templates. Parent should copy this ruling into them after the human gate, without widening scope. Rollback authority remains `engineering/runbooks/trust-ci-rollout.md` “Rollback”, not a new procedure.
