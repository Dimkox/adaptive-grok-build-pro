# Adaptive Trust CI Control Plane — Design

## Purpose

Move merge and release trust out of Grok prompts, repository-local runtime files, and self-issued local approvals into an independently deployed CI control plane. The control plane must run without GitHub Actions, verify an exact commit SHA in an isolated workspace, persist job state outside the repository, require cryptographically signed human approvals for protected changes, and publish a required GitHub commit status that branch protection can enforce.

## Scope

This design adds a standalone `trust-ci/` service to Adaptive Grok Build Pro. It covers:

- GitHub webhook intake and HMAC verification;
- durable PostgreSQL job, lease, attempt, approval, event, and attestation state;
- exact-SHA isolated verification workers;
- Ed25519 approval and attestation signatures;
- server-side policy, mounted outside the checked-out repository;
- required commit-status publication;
- a branch-protection configurator;
- operational Docker Compose and systemd deployment examples;
- local integration changes that treat hooks, receipts, and prompt files as advisory.

It does not add GitHub Actions, auto-merge, production deployment, or a general-purpose build scheduler. The first release has one pipeline type, `pull_request`, and deliberately keeps merge human-owned.

## Trust model

### Trusted

- the deployed Trust CI container image;
- the mounted Trust CI policy file;
- the PostgreSQL database;
- the Trust CI Ed25519 private key;
- approved human public keys in the mounted trust store;
- the GitHub token held by Trust CI;
- protected-branch rules requiring the Trust CI status context.

### Untrusted

- repository content at the PR head SHA, including `AGENTS.md`, `.grok/**`, `.grok-stack/**`, local receipts, tests, and build scripts;
- issue, PR, webhook, log, MCP, and model output;
- approvals created by repository-local scripts;
- the agent that authored the change.

Repository commands may contribute evidence, but they cannot change the server-side policy, approval trust store, CI signing key, branch-protection requirement, or durable job record.

## Components

### API service

A FastAPI service accepts GitHub webhooks and signed approval envelopes. It verifies `X-Hub-Signature-256`, validates repository allowlists, derives an idempotency key from repository, PR number, head SHA, pipeline, and policy digest, persists the job, and publishes a pending commit status.

The approval endpoint validates an Ed25519 signature, actor/key binding, allowed scopes, nonce uniqueness, TTL, repository, and exact head SHA. A valid approval requeues matching `needs_approval` jobs.

### PostgreSQL state store

PostgreSQL is the source of truth for jobs and their state, attempts and bounded retries, leases and heartbeats, approvals and replay protection, signed attestations, and audit events. Workers claim jobs with `FOR UPDATE SKIP LOCKED`. Lease expiry permits recovery after worker death. Unique idempotency keys prevent duplicate webhook delivery from creating duplicate work.

### Worker

A worker claims one job, posts a pending status, creates an isolated temporary checkout, fetches the exact base and head SHAs, checks out the head in detached mode, verifies `HEAD`, computes the changed paths, evaluates server-side protected-path rules, and checks for exact-SHA approvals.

If approval is missing, the job moves to `needs_approval`; no test command is allowed to convert that state to success. If approvals are satisfied, the worker executes the server-configured mandatory command list with a sanitized environment and bounded output. Repository-local `.env` files and GitHub credentials are never passed to test commands.

### Signed approval CLI

The human CLI creates an approval payload containing approval ID and nonce, actor and key ID, repository, PR number, base and head SHA, scope and reason, and issue and expiry times. The payload is serialized as canonical JSON and signed with Ed25519. The private key stays outside the repository and should be stored on a human workstation or hardware-backed secret store. The CLI can emit the envelope to stdout or submit it directly to Trust CI.

### Signed attestation

A successful worker signs an attestation containing the exact SHAs, policy digest, job ID, command results, timing, and output hashes. The database stores the signed envelope. GitHub receives only a status and a link to the job; the attestation remains independently verifiable.

### GitHub integration

Trust CI uses the REST API to publish the status context `adaptive-trust-ci/verified`. A configurator applies branch protection to `main` with strict required status checks, pull requests required before merging, zero mandatory human reviews by default for a solo repository while still requiring a PR, administrator enforcement, conversation resolution, linear history, and force pushes and deletions disabled. The configurator is explicit and idempotent. It never runs from an agent hook.

## Job state machine

```text
queued
  -> leased
  -> running
  -> passed
  -> failed
  -> needs_approval
  -> cancelled
  -> dead
```

A `leased` or `running` job whose lease expires is reclaimable while `attempts < max_attempts`. A retryable infrastructure failure returns the job to `queued`; a deterministic check failure becomes `failed`; exhausted jobs become `dead`. A new PR head SHA creates a new idempotent job and cancels stale active jobs for the earlier SHA.

## Approval scopes

The initial server policy defines `protected-path`, `production`, and `external-write`. Approvals bind to one exact head SHA. Any new commit invalidates them without requiring a revocation operation.

## Server-side policy

The deployed policy is loaded from `TRUST_CI_POLICY_PATH`, normally a read-only mount outside the repository checkout. The repository ships only `policy.example.json`. Policy includes allowed repositories, status context, checkout depth, lease and retry limits, mandatory commands, path-to-scope rules, output limits, and allowed environment variables. The policy digest is part of every job, approval decision, and attestation.

## Failure behavior

The trust boundary is fail-closed:

- invalid webhook signature: HTTP 401;
- unknown repository: HTTP 403;
- unavailable policy, database, signing key, or trust store: service unhealthy and no success status;
- missing required executable: deterministic failure;
- skipped mandatory command: impossible by schema;
- missing signed approval: `needs_approval` and non-success GitHub status;
- inability to publish GitHub status: job cannot become `passed` until status publication succeeds;
- worker crash: lease expiry and bounded retry;
- malformed or replayed approval: rejection and audit event.

Local Grok hooks remain fail-open for usability, but they are not part of the merge trust decision.

## Security constraints

- No GitHub token in subprocess arguments or child test environments.
- No private approval key in the repository or CI worker checkout.
- CI signing key is distinct from human approval keys.
- All approvals and attestations use canonical JSON.
- Comparison uses exact 40-hex SHAs.
- Approval TTL is at most 30 minutes by default.
- Nonces and approval IDs are unique in PostgreSQL.
- GitHub webhook bodies are verified before JSON parsing.
- API read endpoints require an administrative bearer token; health does not.
- Branch protection is enforced for administrators.

## Testing

The standalone service has unit tests for canonical signing and tamper detection; expiry, scope, actor, key, nonce, and exact-SHA validation; webhook HMAC and idempotent enqueue; job leasing, expiry, retry, and stale-head cancellation; protected-path policy resolution; missing-approval and successful-runner paths; attestation verification; branch-protection payload generation; and PostgreSQL schema invariants.

Tests use an in-memory store and fake GitHub transport. PostgreSQL integration is exercised operationally through the Compose smoke command and schema migration.

## Rollout

1. Merge the code through a PR before branch protection is enabled.
2. Deploy PostgreSQL and Trust CI on a separate host or isolated service account.
3. Generate a CI signing key and at least one human approval key.
4. Install the human public key in the mounted trust store.
5. Mount a reviewed policy derived from `policy.example.json`.
6. Register the GitHub webhook and secret.
7. Open a test PR and confirm pending/success status publication.
8. Run the branch-protection configurator for `main`.
9. Confirm a direct push and merge without the Trust CI context are rejected.
10. Keep auto-merge and production deployment disabled until shadow-mode metrics are collected.
