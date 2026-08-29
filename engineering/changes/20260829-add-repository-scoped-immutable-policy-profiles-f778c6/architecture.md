# Architecture — Add repository-scoped immutable policy profiles to the Python trust-ci webhook API and worker, selecting commands and holdout by exact repository, binding jobs to the selected profile digest, rejecting unknown repositories, and preserving schema-version-1 behavior with automated tests

## Current behavior

API and worker each load one frozen `Policy`. The API allowlists repositories but enqueues the same policy digest for all of them. The worker owns one `JobRunner`, compares every job to that global digest, and executes one holdout and command set.

## Proposed behavior

Introduce a frozen `PolicyCatalog` loaded from the same server-mounted policy path. It exposes exact repository resolution and exact bound-resolution by `(repository, digest)`. Each effective `PolicyProfile` contains the complete common execution envelope plus selected commands and holdout; its canonical SHA-256 remains the existing job `policy_digest` and Check Run epoch.

Legacy schema-v1 remains a supported input mode and is parsed through the existing normalization path. New catalog mode is mutually exclusive with legacy fields. Common fields stay process-wide in v1: status context, pipeline, leases/retries, sandbox runtime/image/resources, allowed environment, and approval rules. Profiles scope repository commands and holdout only.

## Components and boundaries

- `PolicyCatalog`: validates configuration, including exact repository-profile keys and mandatory absolute profile-scoped holdout host paths, computes catalog diagnostics, and resolves exact repositories and immutable job bindings.
- `PolicyProfile`: preserves the current runner-facing policy contract and full effective digest.
- Webhook API: verifies HMAC, parses event, resolves profile, rejects unknown repository, enqueues selected digest.
- Store: unchanged; persists exact repository and selected digest using existing fields and idempotency key.
- Worker: claims a job, resolves its exact bound profile, constructs/chooses `JobRunner`, and fails closed if unavailable.
- Runner: continues enforcing holdout-before-checkout-commands, source-mutation detection, approvals, attestation, and App publication using the selected profile.
- Deployed catalog/holdouts: remain server-mounted outside repository control. This PR supplies code/examples only.

## Data flow

`signed webhook -> exact repository parse -> catalog.resolve_repository -> enqueue(policy_digest) -> claim -> catalog.resolve_bound(repository,digest) -> selected holdout integrity/commands -> selected repository commands -> signed attestation -> App-owned exact-SHA Check Run`.

The API selects once. Every retry/replay resolves by the durable repository/digest pair and cannot silently advance to a newer assignment.

## API and event contracts

- GitHub webhook schema is unchanged.
- Unknown repositories retain HTTP 403 and create no job/check.
- `Job`, approval, and attestation schema version 1 retain the existing `policy_digest` meaning: the complete effective server policy for that exact job.
- Duplicate delivery under the same selected digest returns the existing job. A changed profile digest creates a new job/check epoch for the same head.
- Public job output remains sanitized; no commands, holdout paths, or secrets are exposed.

## Data impact

No migration. The existing `repository` plus `policy_digest` columns are the immutable profile identity. Historical rows are never rebound to a new profile.

## Decisions

1. Use one server-mounted immutable catalog rather than separate deployments: lower operational cost while retaining explicit repository isolation.
2. Use effective profile digests rather than a catalog-wide digest for jobs/checks: unrelated repository changes do not rotate all gates.
3. Reuse `policy_digest` and avoid profile IDs/database changes: the content digest is already the durable trusted identity.
4. Preserve legacy schema-v1 bit-for-bit and reject mixed forms: upgrades can deploy code first under the current policy.
5. Keep the execution envelope common in schema v1: per-profile images/leases would require separate queues or worker pools and is out of scope.

## Risks and mitigations

- API/worker skew: immutable catalog validation plus exact bound-resolution; mismatch fails before checkout.
- Incomplete digest material: build each profile from fully normalized effective policy and regression-test field sensitivity.
- Holdout path confusion: confine profile holdouts beneath validated trusted roots and reject traversal.
- Branch-protection deadlock: prove a new App-owned check before changing required contexts; deployment remains a separate human operation.
- Retired profile jobs: terminal non-success and fresh enqueue under the active epoch; no fallback execution.
