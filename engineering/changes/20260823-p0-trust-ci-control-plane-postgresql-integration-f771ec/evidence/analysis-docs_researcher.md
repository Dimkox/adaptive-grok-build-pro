# Docs research: remaining Trust CI steps 1–9

Change: `engineering/changes/20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Route: `f771ecaf458d`  
Agent: `docs_researcher` (read-only)  
Date: 2026-08-23

This report recovers requirements from repository docs, ADRs, and contracts. It does not invent APIs, image digests, GitHub App IDs, or check-run IDs. No ADR files exist under `engineering/adr/`. The active change package is still template-empty (`brief.md`, `requirements.md`, `architecture.md`, `tasks.md`, `test-plan.md`, `rollback.md`, `release.md`).

## Sources read

Primary (named by `GROK_BUILD_HANDOFF.md` “Read before changing anything”):

| File | Role |
| --- | --- |
| `GROK_BUILD_HANDOFF.md` | Current operational sequence for remaining work. Authority for “steps 1–9” below. |
| `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md` | Original design spec. |
| `docs/superpowers/plans/2026-08-23-trust-ci-control-plane.md` | Original implementation plan (code Tasks 1–9). |
| `trust-ci/README.md` | Deployed-service operator contract. |
| `engineering/runbooks/trust-ci-rollout.md` | Rollout/rollback runbook. |
| `engineering/reviews/trust-ci-p0-local-verification.md` | Recorded local preflight, plus a shorter remaining-activation list. |

Supporting contracts (digest/permission placeholders only):

- `trust-ci/config/policy.example.json`
- `trust-ci/.env.example`
- `trust-ci/env/api.env.example`
- `trust-ci/env/worker.env.example`
- `trust-ci/env/common.env.example`

Related but not one of the six: `docs/superpowers/plans/2026-08-23-trust-ci-operations-hardening.md` is a later hardening plan (checksum-locked migrations, metrics, backup drill, key rotation, Docker API proxy). It is not required by handoff steps 1–9 and is not treated as remaining P0 scope here.

## Which “1–9” is remaining work

There are at least four numbered lists. They are **not** the same sequence.

1. **Remaining operational work (this change):** `GROK_BUILD_HANDOFF.md` section “Grok Build execution order”, steps 1–9. The handoff’s “Current code state” already lists the control-plane code as implemented. The remaining work is baseline reproduction, live PostgreSQL, pin artifacts, GitHub App, deploy, webhook proof, approval proof, protect `main`, finish draft PR #2.
2. **Original code-build plan:** `docs/superpowers/plans/2026-08-23-trust-ci-control-plane.md` Tasks 1–9 (package skeleton → open PR). That is the historical implementation plan, not the remaining operational sequence.
3. **Design-spec rollout:** `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md` “Rollout” steps 1–10, which start with merging the code before branch protection.
4. **Shorter remaining lists:** `engineering/reviews/trust-ci-p0-local-verification.md` “Remaining external activation” 1–7; `trust-ci/README.md` “GitHub configuration” rollout order 1–6; `engineering/runbooks/trust-ci-rollout.md` “Prove the App-owned policy epoch” 1–10 then “Protect main”.

Unless a later source explicitly supersedes a field, treat `GROK_BUILD_HANDOFF.md` as the remaining-step list, and treat README + runbook as the operator evidence for steps 3–8.

## Non-negotiable constraints (union)

From `GROK_BUILD_HANDOFF.md` “Non-negotiable constraints”:

- Do not add GitHub Actions, Dependabot workflows, or `.github/workflows/**`.
- Do not replace PostgreSQL durable state with repository-local JSON or SQLite.
- Repository code, prompts, tests, hooks, local receipts, and local approvals cannot create the authoritative merge verdict.
- Keep exact-SHA checkout and policy-digest binding.
- Keep the no-network isolated runner and the external digest-pinned holdout validator.
- A command that exits `0` after modifying tracked source must still fail the job.
- Human Trust CI approvals remain Ed25519-signed outside the agent environment.
- Final GitHub verdicts are GitHub App-owned Checks API runs.
- Branch protection must bind the required policy-epoch check to the trusted GitHub App ID.
- Direct push to `main`, workflow dispatch, merge, tag, release, and production mutation remain prohibited unless the user has explicitly delegated the exact operational action.

Shared across README, runbook, design spec, and implementation plan:

- Trust CI policy, keys, holdout, and trust store are mounted outside the pull-request checkout.
- PostgreSQL is the authoritative job/approval/attestation store; claims use `FOR UPDATE SKIP LOCKED`.
- API and worker are separated. The API must not publish a final successful check. The worker/publisher is the only component with the GitHub App key (`GROK_BUILD_HANDOFF.md` step 4; `trust-ci/README.md`; `engineering/runbooks/trust-ci-rollout.md`).
- Human approval private keys stay on a human-controlled machine, never in API, worker, agent workspace, or repository.
- Local `scripts/grok_approve.py` grants are not Trust CI security approvals and cannot create the Check Run.
- First production contour does not auto-merge or auto-deploy (`trust-ci/README.md` “Deliberate non-features”; design spec Scope).
- Do not colocate a Docker-socket worker with production workloads (`GROK_BUILD_HANDOFF.md` step 5; `trust-ci/README.md` “Trust boundary”).
- Do not commit private keys or production environment files (`GROK_BUILD_HANDOFF.md` step 3; `trust-ci/README.md` Bootstrap).

## GitHub App permissions

No document records a real App ID, installation ID, or private-key path. All are placeholders.

### Required repository permissions

`GROK_BUILD_HANDOFF.md` step 4:

```text
Checks: read/write
Contents: read
Pull requests: read
Metadata: read
```

`trust-ci/README.md` “Configure the GitHub App” (and Prerequisites, slightly shorter wording):

```text
Checks: Read and write
Contents: Read-only
Pull requests: Read-only
```

`engineering/runbooks/trust-ci-rollout.md` Preconditions:

> The Trust CI GitHub App must have `Checks: read/write`, `Contents: read`, and `Pull requests: read`.

**Conflict:** only the handoff lists `Metadata: read`. README and runbook omit it. None of the six docs mention Administration, Contents write, or Checks-only-write. README and runbook additionally require that the **long-lived App must not have repository administration**; branch protection uses a **temporary human administration token**.

### Provision separately (handoff step 4)

```text
GitHub App ID
installation ID
worker-only private key
API-only webhook secret
```

README env names (not values): `TRUST_CI_GITHUB_APP_PRIVATE_KEY_PATH`, `TRUST_CI_GITHUB_APP_ID`, `TRUST_CI_GITHUB_INSTALLATION_ID`. API must not receive these. Worker.env.example placeholders: `REPLACE_WITH_APP_ID`, `REPLACE_WITH_INSTALLATION_ID`.

### Installation-token reduction

`trust-ci/README.md`:

> The worker requests a short-lived installation token with the reduced permissions `checks:write`, `contents:read`, and `pull_requests:read`, even if the installed App has broader permissions.

Runbook: “The worker requests an installation token reduced to exactly those permissions.” Handoff does not mention the reduced installation token.

### Design-spec mismatch

`docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md` trusted set includes “the GitHub token held by Trust CI” and GitHub integration is **commit-status** context `adaptive-trust-ci/verified`, not a GitHub App Check Run. The implementation plan Task 4 is “commit-status publication.” Later operator docs and the handoff require a GitHub **App** and **Checks API**. Treat the later App/Checks contract as current.

## Image / policy / holdout digests

**None of the six documents contain a real API, worker, runner, policy, or SBOM digest.** They require generating and pinning digests at deploy time. Do not invent hashes.

### What must be generated and retained

`GROK_BUILD_HANDOFF.md` step 3:

```text
image digests
policy digest
SBOM
vulnerability scan report
CI public attestation key
holdout bundle digest
```

SBOM and vulnerability scan report appear **only** in the handoff. README and runbook do not list them.

### How to obtain them (README + runbook)

Build commands (mutable tags used only to inspect, then pin):

```bash
docker compose --profile build build api worker runner-image
docker image inspect adaptive-trust-ci-api:2.1.0 --format '{{.Id}}'
docker image inspect adaptive-trust-ci-worker:2.1.0 --format '{{.Id}}'
docker image inspect adaptive-trust-ci-runner:2.1.0 --format '{{.Id}}'
adaptive-trust-ci holdout-digest --path /opt/adaptive-trust-ci-holdout
```

Runbook: “Put exact image and holdout sha256 values into deployment env and `runtime/policy.json`.”

README: “The deployment and policy refuse mutable runner tags.” Rebuilding the runner or changing any policy or holdout input **changes the policy digest, changes the required check name, and invalidates old jobs and approvals.**

Check-run name format (`trust-ci/README.md`):

```text
adaptive-trust-ci/verified@<first-12-hex-of-policy-sha256>
```

Policy example ships `status_context` as the prefix only (`trust-ci/config/policy.example.json`: `"status_context": "adaptive-trust-ci/verified"`). The epoch suffix is appended from the digest. Design spec and implementation plan still say the required context is `adaptive-trust-ci/verified` **without** the epoch suffix — superseded by README/runbook/handoff.

### Contract placeholders (not deployed values)

`trust-ci/config/policy.example.json`:

- Runner image: `adaptive-trust-ci-runner@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST`
- Holdout digest field: `"digest": "28ee9c803043a482de50e2a9757fb5236e56a8c899b2ae97d4faf3f082333f30"` — this is the **example** bundle digest in the shipped example policy, not a recorded production pin. Do not treat it as evidence that step 3 is done.

`trust-ci/.env.example` (Compose interpolation; every production image must be `name@sha256`):

- `TRUST_CI_PYTHON_BASE_IMAGE=python:3.12-slim-bookworm@sha256:REPLACE_WITH_BASE_DIGEST`
- `TRUST_CI_POSTGRES_IMAGE=postgres:17.6-bookworm@sha256:REPLACE_WITH_POSTGRES_DIGEST`
- `TRUST_CI_DIND_IMAGE=docker:29-dind-rootless@sha256:REPLACE_WITH_DIND_DIGEST`
- `TRUST_CI_API_IMAGE=registry.example.com/adaptive-trust-ci-api@sha256:REPLACE_WITH_API_DIGEST`
- `TRUST_CI_WORKER_IMAGE=registry.example.com/adaptive-trust-ci-worker@sha256:REPLACE_WITH_WORKER_DIGEST`
- `TRUST_CI_RUNNER_IMAGE=registry.example.com/adaptive-trust-ci-runner@sha256:REPLACE_WITH_RUNNER_DIGEST`
- Build tags only: `adaptive-trust-ci-runner:2.1.0`, `adaptive-trust-ci-test:2.1.0`

No document records the current policy-epoch 12-hex, Check Run ID, or GitHub App ID.

## Local preflight already recorded (not remaining, not merge authority)

Both `GROK_BUILD_HANDOFF.md` and `engineering/reviews/trust-ci-p0-local-verification.md` say this is local preflight only.

| Claim | Handoff | Verification review |
| --- | --- | --- |
| Root delegated-approval/policy suite | 32 passed | 32 passed |
| Trust CI suite | 97 executed, 93 passed | 97 passed |
| PostgreSQL live tests | 4 skipped; `TRUST_CI_TEST_DATABASE_URL` unavailable | 4 skipped; same reason |
| compileall | passed | passed |
| `git diff --check` | passed | not listed |
| GitHub Actions | forbidden (constraints) | “remain forbidden and absent” |

**Conflict:** handoff says 97 executed / 93 passed (consistent with 4 skipped). The verification review says “97 passed” **and** “4 skipped.” Treat 93 passed + 4 skipped as the precise recorded result; “97 passed” is overstated.

Verification commands in the review omit `python3 scripts/grok_verify.py --mode pr --no-record --json`, which the handoff step 1 requires.

## Remaining steps 1–9 — evidence, constraints, DoD

Authority: `GROK_BUILD_HANDOFF.md` “Grok Build execution order”. Other docs add operator detail or conflict as noted.

### Step 1. Reproduce the local baseline

Required commands (`GROK_BUILD_HANDOFF.md`):

```bash
PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest discover -s tests -v
PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest discover -s trust-ci/tests -v
python3 -m compileall -q .grok-stack/adaptive_grok scripts trust-ci/src tests trust-ci/tests
python3 scripts/grok_verify.py --mode pr --no-record --json
```

Evidence required:

- Exact command output from **this** run, not an earlier one.
- Current Git SHA.
- Do not claim success from the 2026-08-23 recorded preflight.

README verification is narrower (`PYTHONPATH=trust-ci/src:trust-ci/tests`, compileall only `trust-ci/src`) and is **not** a substitute for handoff step 1.

### Step 2. Run real PostgreSQL integration tests

Handoff:

- Start a disposable PostgreSQL instance.
- Export `TRUST_CI_TEST_DATABASE_URL`.
- Rerun the Trust CI test suite.
- The four previously skipped integration tests **must execute and pass**.

Required scenarios (handoff):

```text
two workers claiming concurrently
lease expiry and reclaim
heartbeat ownership
attempt exhaustion to dead
approval nonce replay rejection
attestation durability
PostgreSQL restart/recovery
```

Runbook “PostgreSQL acceptance” additionally requires `docker compose -f trust-ci/compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests` and these proofs:

- duplicate-webhook idempotency
- `FOR UPDATE SKIP LOCKED` exclusivity with concurrent workers
- heartbeat and lease expiry
- worker-death reclaim
- bounded attempts to `dead`
- nonce replay rejection
- PostgreSQL restart recovery
- signed-attestation replay after GitHub publication failure

README repeats the same `compose.test.yaml` command plus `compose.yaml config` and image builds.

**Conflicts / gaps:**

- Design spec “Testing” says tests use an **in-memory store** and fake GitHub; PostgreSQL is only “Compose smoke command and schema migration.” That is superseded for remaining work: live tests are mandatory.
- Handoff names `TRUST_CI_TEST_DATABASE_URL`; runbook/README name `compose.test.yaml`. Both must be satisfied unless a later ruling records they are the same harness.
- Runbook adds duplicate-webhook idempotency, worker-death reclaim, and attestation replay after GitHub publication failure; handoff’s “attestation durability” is not spelled as publication-failure replay.

### Step 3. Build and pin immutable artifacts

Handoff: build API, worker, runner, and holdout artifacts; replace mutable tags with immutable digests in the **deployed server-side policy**; retain image digests, policy digest, SBOM, vuln scan, CI public attestation key, holdout digest. Do not commit private keys or production env files.

README/runbook: inspect `:2.1.0` image IDs, compute holdout digest, write sha256 values into env and `runtime/policy.json`. Policy/holdout change must change the required check name.

Evidence for later PR update (handoff step 9): “image and holdout digests.”

No document gives the actual hashes to copy.

### Step 4. Create the GitHub App

Handoff permissions and separately provisioned secrets as above. Constraint: API cannot publish a final successful check; only worker has the App key.

README webhook (used in step 6, created around App/API deploy):

```text
Payload URL: https://ci.example.com/webhooks/github
Content type: application/json
Secret: TRUST_CI_WEBHOOK_SECRET
Events: Pull requests
```

Evidence for step 9: “GitHub App ID and installation confirmation **without secrets**.”

### Step 5. Deploy the self-hosted service

Handoff deploy set, isolated CI host or VM:

```text
PostgreSQL
migration job
API
worker
immutable runner image
external holdout bundle
HTTPS reverse proxy
backup target
metrics and logs
```

Do not colocate a Docker-socket worker with production workloads.

Runbook/README start sequence: copy env templates, replace placeholders, install holdout, generate CI and human keys, configure App, pin images, then:

```bash
docker compose up -d postgres migrate api worker
docker compose ps
curl -fsS http://127.0.0.1:8080/health/ready
```

README: terminate TLS in a reverse proxy; expose `/webhooks/github` and `/approvals`; expose `/jobs/*` and `/attestations/*` only according to privacy model. Command output tails stored in PostgreSQL but omitted from the public job endpoint.

Design spec Scope says the design “does not add … production deployment.” That is the original code-drop scope, not a ban on this remaining operational deploy. The same spec’s Rollout still deploys PostgreSQL and Trust CI on a separate host.

### Step 6. Register and prove the webhook flow

Handoff: register HMAC pull-request webhook; update PR #2; verify:

```text
webhook accepted
exact SHA job stored
worker claims one lease
repository checks run without network or secrets
holdout validation runs outside checkout
signed attestation stored
App-owned policy-epoch check appears on the exact SHA
```

Also: verify the attestation offline with the CI public key.

Runbook “Prove the App-owned policy epoch before protection” is stricter and adds proofs the handoff puts in steps 6–8:

1. Disposable PR changing an unprotected documentation file.
2. PostgreSQL contains one queued/running job for the exact head SHA.
3. **Worker, not API**, creates Check Run `adaptive-trust-ci/verified@<policy-sha12>` with `external_id` equal to the durable job ID.
4. GitHub shows the Check Run owned by the Trust CI GitHub App.
5. Runner logs show immutable image digest, external holdout execution, `--network none`, no secrets, and no Docker socket inside the runner.
6. Fetch `/attestations/<job_id>` and verify offline with CI public key.
7. Update the same PR; old SHA / old Check Run cannot satisfy the new SHA.
8. Change any deployed policy or holdout input; policy digest and required check name change.
9. Change a `trust-ci/**` file; Check Run enters `action_required` until exact Ed25519 approval, then restarts the **same durable** Check Run.
10. Fixture that changes a tracked source file and exits `0` still fails with a source-integrity result.

“Do not continue if any step is ambiguous.” Applying branch protection before observing the App-owned check can lock the repository (`trust-ci/README.md`).

**Tension:** handoff step 6 says “Update PR #2”. Runbook step 1 says a **disposable** documentation PR. Both can be true (prove on a disposable PR, then update #2), but the handoff’s step 9 still requires the App-owned check on PR #2’s exact final SHA.

### Step 7. Prove approval behavior

Handoff, on a disposable PR:

```text
documentation-only diff runs without approval
trust-ci/** diff enters needs_approval
wrong signer scope is rejected
tampered payload is rejected
replayed nonce is rejected
new commit invalidates old approval
policy digest change invalidates old approval
valid human-signed approval requeues only the exact SHA
```

README approval binding fields:

```text
repository
pull_request
base_sha
head_sha
policy_digest
scope
actor
key_id
nonce
issued_at
expires_at
signature
```

“Any new commit, base change, holdout change or policy change invalidates it.” Human CLI: `adaptive-trust-ci approval-create` / `approval-submit`. Default max TTL in design spec: 30 minutes. README example TTL: `--ttl 900`. Policy example: `max_approval_ttl_seconds: 1800`.

**Scope-name conflict:** design spec initial scopes are `protected-path`, `production`, `external-write`. Shipped example policy scopes are `governance`, `database`, `production`. README example uses `--scope governance`. Do not invent `protected-path` as a live API if the example policy is the contract.

### Step 8. Protect main

Handoff: **only after** the external App-owned check has appeared and succeeded, apply:

```text
pull request required
strict up-to-date check required
required check = exact policy-epoch name
required check bound to GitHub App ID
administrator enforcement
conversation resolution
linear history
force pushes disabled
branch deletion disabled
```

Then test that direct push and merge without the external check fail.

README/runbook command (temporary human admin token, not the long-lived App):

```bash
TRUST_CI_GITHUB_ADMIN_TOKEN=<temporary-admin-token> \
TRUST_CI_GITHUB_APP_ID='<app-id>' \
adaptive-trust-ci branch-protect \
  --policy "$PWD/runtime/policy.json" \
  --repository Dimkox/adaptive-grok-build-pro \
  --branch main \
  --required-reviews 0
```

Runbook extra proofs after protection:

- same check text from another actor does not satisfy protection
- direct push, force push and branch deletion fail
- merge without the exact App-owned check fails
- unresolved conversations block merge
- administrators cannot bypass the rule

Implementation plan still says branch protection requires `adaptive-trust-ci/verified` without epoch or App ID. Superseded.

### Step 9. Finish PR #2

Handoff: keep #2 draft until the App-owned check exists for the exact head SHA. Update the PR with:

```text
exact final SHA
PostgreSQL integration output
image and holdout digests
GitHub App ID and installation confirmation without secrets
external check run ID
attestation verification output
branch-protection verification
remaining residual risks
```

Only then mark PR #2 ready for review. **Do not merge automatically unless the user explicitly orders it after reviewing the external evidence.**

Working branch: `feat/trust-ci-control-plane`. PR: `#2 — P0: self-hosted Trust CI control plane (no GitHub Actions)`. Do not start from `hardening/trust-boundary-v2-1` / closed PR #1 (GitHub Actions implementation, superseded).

## Definition of done

### Handoff “Definition of done” (completion gate for this remaining work)

Work is complete only when **all** of these are true:

```text
no GitHub Actions workflows exist
all local suites pass
all PostgreSQL integration tests pass
external service survives restart
exact-SHA App-owned check succeeds
signed attestation verifies offline
protected-path approval flow is proven
main requires the app-bound policy-epoch check
direct push and bypass attempts fail
PR #2 contains the final evidence
```

### Runbook “Acceptance criteria” (operator/security DoD)

- no `.github/workflows/` exists
- API cannot read GitHub App credentials, CI private key or Docker socket
- worker cannot read webhook secret or human trust store
- runner receives no token, key, socket or network
- external holdout and policy digests are verified before checkout execution
- tracked source mutation is a deterministic failure
- job state survives API/worker/PostgreSQL restart
- expired leases are reclaimed exactly once and attempt-limited
- approvals are bound to repository, PR, base SHA, head SHA, policy digest and scope
- Check Run success is backed by a stored signed attestation
- branch protection requires the exact policy-epoch check from the configured GitHub App ID
- `main` requires a pull request plus that App-owned check

### Verification review remaining list (subset, not a DoD)

1. create and install the GitHub App
2. provide App ID, installation ID and worker-only private key
3. run the PostgreSQL integration suite against a disposable live database
4. deploy PostgreSQL, API, worker, immutable runner image and holdout bundle
5. register the HMAC-protected pull-request webhook
6. prove the App-owned check on a disposable PR
7. bind branch protection to the exact policy-epoch check and App ID

This list omits handoff step 1 (fresh baseline), step 3 SBOM/vuln scan, step 7 full approval matrix, step 8 bypass tests, and step 9 PR evidence bundle. It is a reminder, not a replacement DoD.

### Design-spec fail-closed behaviors still in force

Invalid webhook HMAC → HTTP 401; unknown repository → HTTP 403; unavailable policy/database/signing key/trust store → unhealthy, no success status; missing required executable → deterministic failure; skipped mandatory command impossible by schema; missing signed approval → `needs_approval` and non-success GitHub status; inability to publish GitHub status → job cannot become `passed`; worker crash → lease expiry and bounded retry; malformed/replayed approval → rejection and audit event.

## Conflicts to resolve before implementation (do not silently pick)

1. **Commit status vs Check Run / GitHub token vs GitHub App.** Design spec + implementation plan: status context `adaptive-trust-ci/verified` via a GitHub token. Handoff + README + runbook: App-owned Check Run `adaptive-trust-ci/verified@<policy-sha12>` bound to App ID. Current operator contract wins; design spec is stale on this point.
2. **Metadata permission.** Only handoff requires `Metadata: read`. README/runbook omit it.
3. **Required check name.** Implementation plan: `adaptive-trust-ci/verified`. Operator docs: epoch suffix from first 12 hex of policy sha256.
4. **PostgreSQL test harness.** Handoff: `TRUST_CI_TEST_DATABASE_URL` + four previously skipped tests + listed scenarios. Runbook/README: `trust-ci/compose.test.yaml` with a longer scenario list. Both are required unless a change-package ruling records they are identical.
5. **Local suite counts.** Handoff 93 passed / 4 skipped vs verification review “97 passed” and 4 skipped. Re-run step 1 rather than citing either number as current.
6. **Prove-on-which-PR.** Handoff step 6: update PR #2. Runbook: disposable documentation PR first. Handoff step 9 still needs the check on #2’s final SHA.
7. **Merge-before-protect vs stay-draft.** Design spec rollout 1: “Merge the code through a PR before branch protection is enabled.” Handoff: keep #2 draft until the App-owned check exists; do not merge unless the user explicitly orders it after external evidence. README: observe App-owned check **before** configuring protection, because applying protection first can lock the repository.
8. **Approval scope names.** Design spec `protected-path` / `production` / `external-write` vs example policy `governance` / `database` / `production`. Handoff DoD still says “protected-path approval flow is proven.”
9. **Step 3 artifacts.** Only handoff requires SBOM and vulnerability scan report.
10. **Deploy completeness.** Handoff requires backup target, metrics, and logs. README start command is `postgres migrate api worker` plus reverse proxy; metrics are not specified as a first-contour API. The hardening plan adds Prometheus `/metrics` later and is out of this remaining 1–9 list.
11. **Historical `decisions.md` 2026-08-17** (“always push main and release”) conflicts with AGENTS.md / handoff PR-only merge trust. AGENTS.md and handoff outrank that decision for this work.

## What is not in the six docs (so it is not a recovered fact)

- Actual API/worker/runner/base/postgres/dind sha256 digests.
- Actual policy digest or policy-epoch 12-hex.
- Actual GitHub App ID, installation ID, Check Run ID, webhook delivery ID, or job ID.
- Confirmation that a live PostgreSQL suite has ever passed.
- Confirmation that branch protection is already applied.
- An ADR under `engineering/adr/`.
- Filled acceptance criteria in this change package.

Those absences mean steps 2–9 are still open. Step 1 must be reproduced against the current SHA before citing local green.

## Route / change-package notes (not DoD)

Active route `f771ecaf458d` lists analysis agents including `docs_researcher`, `write_agent: null`, `intent: review`, human gate `scope_and_design_approval`, required local evidence `verification`, `code_review`, `test_review`, `security_review`, `data_review`. That local evidence is still advisory relative to the App-owned check.
