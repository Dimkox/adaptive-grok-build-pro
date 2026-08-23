# Grok Build handoff — self-hosted Trust CI

## Working branch

```text
feat/trust-ci-control-plane
```

Pull request:

```text
#2 — P0: self-hosted Trust CI control plane (no GitHub Actions)
```

The PR is intentionally draft until the external GitHub App-owned check is produced for its exact head SHA.

## Pull into Grok Build

```bash
git fetch origin
git switch feat/trust-ci-control-plane
git pull --ff-only origin feat/trust-ci-control-plane
git status --short --branch
```

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

Implemented in the branch:

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

Register a pull-request webhook with HMAC secret. Update PR #2 and verify:

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

### 9. Finish PR #2

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

Only then mark PR #2 ready for review. Do not merge automatically unless the user explicitly orders it after reviewing the external evidence.

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
