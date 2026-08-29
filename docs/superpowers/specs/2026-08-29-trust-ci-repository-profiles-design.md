# Trust CI Repository Profiles Design

## Goal

Allow one independently deployed Trust CI authority to verify `Dimkox/adaptive-grok-build-pro` and `Dimkox/ii-tonya-platform` with different repository commands and external holdouts. Preserve exact-SHA App-owned checks, immutable policy epochs, signed approvals/attestations, and the existing schema-version-1 contract.

## Decision

Add one immutable server-mounted `PolicyCatalog`. It resolves an effective frozen `PolicyProfile` using an exact, case-sensitive GitHub `repository.full_name`. There is no wildcard, alias, case normalization, or default fallback.

The effective profile digest is SHA-256 over canonical normalized JSON containing the exact repository, common execution/security envelope, sandbox, approval rules, selected repository commands, and selected holdout definition. That digest remains the existing job `policy_digest` and produces `<status_context>@<digest[:12]>`.

## Compatibility

Schema-v1 has two mutually exclusive input modes:

1. Legacy mode retains `allowed_repositories`, global `commands`, and global `holdout`. It uses the current parser and canonical representation so existing digest and Check Run names remain bit-for-bit unchanged.
2. Catalog mode declares exact repository profiles for commands and holdout while retaining one common execution envelope.

Mixed forms are invalid. Code is rolled out under the legacy policy before a catalog is installed. Approval, attestation, webhook, job, and PostgreSQL schemas remain unchanged.

## Common and Profile-Scoped Fields

Common in schema-v1: status context, pipeline, checkout depth, lease/retry/output limits, allowed environment, sandbox runtime/image/resources, and approval rules. Keeping these common matches the current process-wide queue claim, runner image, and trust store.

Profile-scoped: exact repository, repository commands, and external holdout path/digest/commands. A common-field edit rotates every effective profile; editing repository A's scoped fields rotates A only.

## Data Flow

1. API verifies webhook HMAC before JSON parsing.
2. It parses the exact repository and resolves the current profile; unknown repositories return HTTP 403 without enqueue or Check Run.
3. It enqueues using the selected effective digest in the existing `policy_digest` field.
4. Worker claims the job and resolves `(job.repository, job.policy_digest)` against its loaded immutable catalog.
5. Missing, stale, removed, or mismatched bindings terminate non-success before checkout or commands. No current/default profile substitution is allowed.
6. `JobRunner` verifies the selected external holdout, runs holdout commands before repository commands, checks source mutation, validates approvals, signs the schema-v1 attestation, and publishes the selected epoch's App-owned exact-SHA Check Run.
7. Retry, lease reclaim, and publication replay use the same repository/digest binding and `external_id = job_id`.

## Storage

No migration is needed. `repository` plus `policy_digest` already identify the immutable effective profile and participate in idempotency. Historical jobs are never rebound. A profile change for the same head intentionally produces a new idempotency identity and Check Run epoch.

## Failure Behavior

- Unknown/case-variant repository: HTTP 403, no job/check.
- Mixed or invalid catalog: process fails startup/readiness.
- API/worker catalog skew or retired digest: terminal non-success before checkout.
- Holdout path/digest failure: terminal non-success before repository commands.
- Check publication failure: replay the signed result under the same job/profile; do not rerun commands.
- Public diagnostics never expose commands, holdout paths, secrets, or high-cardinality repository/job labels.

## Alternatives Rejected

- Catalog-wide job digest: safe but rotates every repository for an unrelated profile edit and proves less precisely what executed.
- Digest-addressed profile artifact registry: supports historical generations and rolling upgrades but adds artifact distribution, retention, and garbage collection not required now.
- Separate API/worker deployment per repository: strongest blast-radius separation but duplicates GitHub routing, secrets, monitoring, upgrades, and cost.

## Testing

Tests must prove legacy digest/check compatibility; exact profile selection; stable digest independent of catalog order; A-only versus common-field rotation; unknown/case/stale rejection; no cross-profile command or holdout execution; durable digest-aware idempotency; approval/check/attestation binding; and retry/replay preservation. Existing source-mutation, exact-SHA, App publication, and external holdout tests remain mandatory.

## Rollout and Rollback

This code change does not deploy or alter protected infrastructure. After merge, deploy compatible binaries under the legacy policy, validate a reviewed server-side catalog and holdouts offline, drain workers, switch API/workers atomically, and onboard one repository at a time. Prove the replacement App-owned check before changing branch protection.

Rollback drains workers and restores the previous reviewed binaries plus legacy policy as one unit. PostgreSQL rows and attestations are preserved; unavailable-digest jobs stay non-success and are re-enqueued at the exact SHA under the restored epoch.
