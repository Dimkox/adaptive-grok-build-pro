# Grok Build handoff — self-hosted Trust CI

## Status — historical P0 handoff; Trust CI is deployed and serving (2026-09-13)

This file documents the P0 bootstrap of the self-hosted Trust CI control plane. It is no longer the working plan and none of its steps are open. The facts below are visible from this repository and from the service itself:

- PR #2 (`P0: self-hosted Trust CI control plane`) merged at `2026-08-23T22:05:31Z` as `73e4ae7c68a95d3a7440378964b8cc1879df9b89`, which is the original planning baseline recorded in `DARK_FACTORY_ROADMAP.md` section 2;
- the control-plane source lives on `main` under `trust-ci/` and runs on the CI host `claw` as `adaptive-trust-ci-api-1`, `adaptive-trust-ci-worker-1`, `adaptive-trust-ci-docker-engine-1` (isolated runner) and `adaptive-trust-ci-postgres-1` (`postgres:17.6-bookworm`) — the compose topology documented in `trust-ci/README.md`;
- the API serves `GET http://127.0.0.1:18080/health/ready` with `"status":"ready"`, policy digest `06ecf1c875bc12fa696956998983e04b102f28571a586bc3bb7a2fff5083fdb2`, `status_context` `adaptive-trust-ci/verified`, publisher `worker-github-app` and one active approval key;
- protected `main` binds the required status check `adaptive-trust-ci/verified@06ecf1c875bc` to GitHub App ID `4694114`, with strict up-to-date checks, administrator enforcement, and force pushes and branch deletion disabled;
- that check is the live merge gate and is minting verdicts today: it passed on the L5 union head `ac7ae2def67a267c227ab5703843337d4bb6f4be` (check run `103760385178`) before PR #75 merged as `eb9df64bca333f30ec58f8c725a021360e22ed92` at `2026-09-13T17:35:51Z`, and the evidence follow-up PR #72 merged as `e737dd5c338793e274285d657354e74ecc812f89` at `2026-09-13T18:26:32Z`.

Everything under "Non-negotiable constraints", "User standing consent" and the deployment prerequisites remains binding policy. The numbered execution order and the "Definition of done" below are completed history: read them as how the running service was proven, not as what to do next. See **Next actions** at the end of this file for the current work.

## Working branch

```text
main    (product source of truth; every change starts from a fresh branch cut from current main)
```

The former P0 branch:

```text
feat/trust-ci-control-plane
```

was merged and is retained history only — its tip `d0e251594c17884dbae4882ff3a8864edd8f0171` is an ancestor of `main`. Do not continue work on it.

Pull request:

```text
#2 — P0: self-hosted Trust CI control plane (no GitHub Actions) — MERGED 2026-08-23T22:05:31Z
```

The PR was intentionally draft until the external GitHub App-owned check was produced for its exact head SHA; that check now exists, is named `adaptive-trust-ci/verified@<policy-sha12>`, and is the app-bound required status on protected `main`.

## Pull into Grok Build

```bash
git fetch origin
git switch --create <branch-name> origin/main
git status --short --branch
```

Delivery is PR-only: push the branch, open a pull request, earn the App-owned policy-epoch check on the exact head SHA, and merge by human action after review. Direct push to `main` is prohibited and blocked by branch protection.

Do not start from `hardening/trust-boundary-v2-1`. That branch and closed PR #1 contain a GitHub Actions-based implementation that is superseded by this self-hosted contour.

## Read before changing anything

Read in this order:

```text
AGENTS.md
GROK_BUILD_HANDOFF.md
decisions.md
mistakes.md
docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md
docs/superpowers/plans/2026-08-23-trust-ci-control-plane.md
trust-ci/README.md
engineering/runbooks/trust-ci-rollout.md
engineering/reviews/trust-ci-p0-local-verification.md
```

## Non-negotiable constraints

- Do not add GitHub Actions, Dependabot workflows, or `.github/workflows/**`.
- Do not replace PostgreSQL durable state with repository-local JSON or SQLite.
- Do not let repository code, prompts, tests, hooks, local receipts, or local approvals create the authoritative merge verdict.
- Keep exact-SHA checkout and policy-digest binding.
- Keep the no-network isolated runner and the external digest-pinned holdout validator.
- A command that exits `0` after modifying tracked source must still fail the job.
- Human Trust CI approvals remain Ed25519-signed outside the agent environment.
- Final GitHub verdicts are GitHub App-owned Checks API runs.
- Branch protection must bind the required policy-epoch check to the trusted GitHub App ID.
- Direct push to `main`, workflow dispatch, merge, tag, release, and production mutation remain prohibited unless the user has explicitly delegated the exact operational action.

## User standing consent

The user has explicitly allowed delegated operational release work. Preserve that capability.

A local delegated grant must remain bound to:

```text
repository
active route/change
exact Git HEAD
tree fingerprint
explicit action
optional resource/path/tool/URL pattern
source of consent
TTL
```

A local grant may authorize the exact requested push, tag, release, protected-path edit, or external write. It must never create the external Trust CI verdict or substitute for a human-signed Trust CI approval.

## Current code state

Implemented in `trust-ci/` on `main` (service identity `2.1.0`, `trust-ci/pyproject.toml`):

- PostgreSQL jobs, attempts, leases, heartbeats, approval replay protection, events, and signed attestations;
- HMAC-verified pull-request webhook intake;
- exact detached-SHA checkout;
- bounded retry and dead-letter behavior;
- GitHub App JWT and installation-token flow;
- Checks API publication;
- policy-epoch check naming;
- app-bound branch-protection payload;
- immutable runner image requirement;
- external holdout bundle outside the pull-request checkout;
- source-mutation detection;
- Ed25519 approvals and attestations;
- signer-level scope authorization;
- API/worker separation;
- no-network runner;
- kill switch;
- protected job/attestation endpoints;
- local exact-action delegated grants.

## Fresh local verification already recorded

```text
root delegated-approval/policy suite: 32 passed
Trust CI suite: 97 executed, 93 passed
PostgreSQL live integration tests: 4 skipped because TRUST_CI_TEST_DATABASE_URL was unavailable
compileall: passed
git diff --check: passed
```

This is local preflight evidence only.

## Grok Build execution order

### 1. Reproduce the local baseline

```bash
PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest discover -s tests -v
PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest discover -s trust-ci/tests -v
python3 -m compileall -q .grok-stack/adaptive_grok scripts trust-ci/src tests trust-ci/tests
python3 scripts/grok_verify.py --mode pr --no-record --json
```

Do not claim success from an earlier run. Record the exact command output and current SHA.

### 2. Run real PostgreSQL integration tests

Start a disposable PostgreSQL instance, export `TRUST_CI_TEST_DATABASE_URL`, then rerun the Trust CI test suite. The four previously skipped integration tests must execute and pass.

Required scenarios:

```text
two workers claiming concurrently
lease expiry and reclaim
heartbeat ownership
attempt exhaustion to dead
approval nonce replay rejection
attestation durability
PostgreSQL restart/recovery
```

### 3. Build and pin immutable artifacts

Build API, worker, runner, and holdout artifacts. Replace mutable image tags with immutable digests in the deployed server-side policy. Generate and retain:

```text
image digests
policy digest
SBOM
vulnerability scan report
CI public attestation key
holdout bundle digest
```

Do not commit private keys or production environment files.

### 4. Create the GitHub App

Required repository permissions:

```text
Checks: read/write
Contents: read
Pull requests: read
Metadata: read
```

Provision separately:

```text
GitHub App ID
installation ID
worker-only private key
API-only webhook secret
```

The API must not be able to publish a final successful check. The worker/publisher is the only component with the App key.

### 5. Deploy the self-hosted service

Deploy on an isolated CI host or VM:

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

### 6. Register and prove the webhook flow

Register a pull-request webhook with HMAC secret. Update the pull request and verify (live intake is the GitHub App `pull_request` webhook plus loopback HMAC characterization, and this is the flow the deployed service has run for every pull request since, including the L5 union #75; no repository webhook is added):

```text
webhook accepted
exact SHA job stored
worker claims one lease
repository checks run without network or secrets
holdout validation runs outside checkout
signed attestation stored
App-owned policy-epoch check appears on the exact SHA
```

Verify the attestation offline with the CI public key.

### 7. Prove approval behavior

On a disposable PR:

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

### 8. Protect main

Only after the external App-owned check has appeared and succeeded, apply branch protection:

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

Test that direct push and merge without the external check fail.

### 9. Finish the pull request

Update the PR with:

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

Only then mark the pull request ready for review. Do not merge automatically unless the user explicitly orders it after reviewing the external evidence.

## Definition of done

The work is complete only when all of these are true:

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

Each condition above held when P0 closed and PR #2 carried the final evidence; they remain the standing acceptance bar for the running service, and `.github/workflows/` still does not exist in this repository.

## Next actions (observed 2026-09-23)

1. Continue from [START_HERE.md](START_HERE.md) and [PROJECT_STATE.json](PROJECT_STATE.json). `v2.0.18` remains published and immutable; the `v2.0.19` candidate is the isolated `release/v2.0.19-factory-bugfixes` tree with bounded local guards related to #35/#39 and owned fixes #73/#167. Issue #48 is reserved for a separate Trust CI-only change under `FIT-TRUST-CI-SEPARATION`. Preserve every published release's bytes and tag.
2. Source `main` was observed at `130ce4a42d9f9bbd1b56772d40b19ae530283205` after PR #185. #36 remains an external/no-owner disposition through #186, M8/DEV work is excluded, and runtime defaults remain off; future external actions need their own exact authority.
3. Establish the next unmet product outcome: a full external pilot with maintainer acceptance. M8 cohort/activation and general M9 qualification remain separate gates. L5 `artifact_ready` does not establish factory publication, hosting or those milestone outcomes.
4. The next release chain is the isolated `v2.0.19` issue-fix candidate followed by an artifact-child PR. The candidate's bounded local/owned scope is related to #35/#39 plus #73/#167; #48 is excluded from this mixed tree, and #35/#36/#39/#48 stay linked to #186 for external-owner closure. Displayed checks remain observations and do not establish eligibility for the new release PR. The exact App-owned check and fresh grants are required at each protected boundary.
5. Trust CI operations stay outside the pull-request trust domain. Deployed policy, holdout, images, PostgreSQL state, App keys, human trust stores and branch protection retain the independent approval and policy-epoch rules in `AGENTS.md`. Human approval private keys remain outside the agent environment.
