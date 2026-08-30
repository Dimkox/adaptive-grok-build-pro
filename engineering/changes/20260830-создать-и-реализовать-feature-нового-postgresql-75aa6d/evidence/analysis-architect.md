# Architecture analysis: production promotion authorization

Route `75aa6daa89b1`; read-only architecture review of the current Trust CI and deploy boundaries.

## Recommendation

Add a separate, frozen `PromotionEnvelopeV1`; do not extend `ApprovalPayloadV1`.

The existing approval contract is intrinsically a pull-request contract: it requires `pr_number`, `base_sha`, `head_sha`, `scope`, and is consumed by the change-validation worker. Making those fields optional or overloading `scope=production` would weaken validation, blur two different authorities, and make existing v1 signatures/schema/storage ambiguous. A promotion is instead a one-time authorization for a concrete artifact entering a concrete environment after merge. It can reuse canonical JSON, Ed25519 primitives, trust-store key lifecycle, and key IDs, but needs its own model, verifier, table, API, CLI, and tests.

## Frozen contract

Signed payload, with `additionalProperties: false` semantics:

- `schema_version: 1`
- `promotion_id: UUID`
- `nonce`: cryptographically random, at least 128 bits
- `actor`, `key_id`, non-empty `reason`
- `repository: owner/name`
- `merged_commit_sha`: exact lowercase 40-hex Git object ID supported by current v1
- `artifact_sha256`: exact lowercase 64-hex digest of the bytes to deploy
- `environment`: exact server-policy allowlisted target, e.g. `production`
- `policy_epoch`: full 64-hex deployed policy digest, never only the 12-character check suffix
- `source_attestation_id`: passed App-owned Trust CI attestation proving the same repository, commit and policy epoch
- `issued_at`, `expires_at`: timezone-aware UTC instants

The Ed25519 signature covers canonical JSON of the entire payload. The verifier requires the key to be active at issue and verification time and explicitly authorized for `promotion:<environment>`. Use a separate promotion TTL cap; production should default to 15 minutes and never exceed one hour. SHA-256 Git repositories need a future `PromotionEnvelopeV2`, not widening v1 fields.

`source_attestation_id` is required because a human signature alone does not establish that the commit passed the App-owned checks. `POST /promotions` must resolve it from PostgreSQL and require a `passed` attestation whose repository, head SHA and policy digest exactly equal the payload. To make “merged commit” truthful, the deployment workflow must use a Trust CI attestation for the actual protected-branch commit. A PR-head attestation is sufficient only when the merge method preserves that exact object ID; squash/rebase/merge commits require verification of the resulting protected-branch commit. Trusting a caller-supplied “merged” label is forbidden.

## State and transaction boundaries

Add an append-only migration for `trust_ci_promotions` with typed columns plus the immutable payload and signature. Required constraints include primary-key `promotion_id`, global `UNIQUE(nonce)`, digest/SHA/expiry checks, `expires_at > issued_at`, foreign key to `source_attestation_id`, state `accepted|consumed|expired|revoked`, nullable `consumed_at`, and a consistency check tying `consumed` to `consumed_at`. Index the authorization lookup by `(repository, merged_commit_sha, artifact_sha256, environment, policy_epoch, state, expires_at)`.

Add `trust_ci_promotion_events` as append-only audit state, keyed by monotonically increasing event ID and optionally referencing a promotion. Store event type, timestamp, actor/key ID, request correlation ID, and bounded non-secret details. Never log bearer tokens, private material, or raw signature bytes. Rejected attempts also need events with normalized reason codes such as `bad_signature`, `untrusted_key`, `wrong_epoch`, `wrong_environment`, `source_not_verified`, `expired`, and `replay`.

`POST /promotions` performs structural and cryptographic validation before opening a transaction, then in one database transaction:

1. lock/read the exact source attestation and current policy epoch;
2. recheck source status and every binding;
3. insert the immutable promotion, letting the UUID/nonce uniqueness constraints arbitrate concurrent replay;
4. append `promotion.accepted`;
5. commit, then return `201` with identity and expiry only.

Malformed, unauthorized, expired, old/future, wrong-policy, wrong-environment, missing-attestation, duplicate-ID and duplicate-nonce requests fail closed. Duplicate submission is `409`, not idempotent success. Database unavailability is `503`, never an in-memory fallback.

Acceptance alone must not be reusable deploy authority. The deployment adapter needs an atomic one-time consume operation immediately before its first production side effect (an internal store method exposed through an authenticated deploy endpoint or equivalent trusted boundary). In one transaction it executes a conditional `UPDATE ... WHERE state='accepted' AND issued_at <= now() AND expires_at > now()` and appends `promotion.consumed`; zero updated rows means deny. Crash after consumption but before deployment is safely fail-closed and requires a new human-signed nonce. Do not implement “unconsume”.

Migration execution remains migrator-owned. Prefer granting the API only `SELECT/INSERT` required for submission and `EXECUTE` on a narrowly scoped security-definer consume function, rather than general `UPDATE` on promotion/audit tables. Mirror each packaged SQL migration in the repository’s expected resource location and preserve checksum locking.

## Fail-closed deployment integration

The deploy adapter must independently calculate the artifact SHA-256 from the exact bytes it will publish, resolve the exact protected-branch commit, and send/consume the matching promotion. It proceeds only on a fresh authenticated success matching all locally expected fields. Timeout, TLS/auth error, kill switch, database error, missing/expired/consumed promotion, field mismatch, policy-epoch change, artifact mutation, or source-attestation mismatch aborts before any tag, upload, release, infrastructure apply, or application write.

The authorization check and the side effect cannot be one PostgreSQL transaction across external systems. The safe minimum is consume-before-effect plus an operation id/correlation ID recorded in the audit event. Retries must reconcile the external system using that operation ID; they must not consume a second authorization automatically or repeat a non-idempotent write. Success/failure/reconciliation events should be appended without mutating the signed envelope.

The production API should remain signature-authenticated for human authority and additionally require an authenticated deployment caller for consumption. Rate-limit both entry points, cap request size, use constant-time bearer comparison, and expose counts for accepted/rejected/consumed/expired, reason codes, consume latency, DB errors, and accepted-but-not-completed promotions.

## Staged policy switch

1. Ship the additive schema, envelope/verifier, `POST /promotions`, audit, consume boundary, deploy adapter, metrics, and kill switch while existing PR `approval_rules` remain unchanged.
2. Apply the migration and deploy the API with promotion acceptance enabled but production consumption disabled. Exercise signature, wrong-key/scope, TTL, nonce replay, wrong epoch/environment/artifact/source, concurrency, restart, and audit durability against a non-production environment.
3. Enable production consumption in fail-closed mode while retaining current PR approvals (temporary dual gate). Perform a canary/no-op promotion and rollback drill.
4. Obtain the one final human approval for the deployed policy change. Only after the production gate and monitoring are healthy, deploy a new policy epoch whose `approval_rules` no longer require interactive `governance`, `database`, or `production` approvals in the pull-request validation pipeline.
5. Run automatic Trust CI on a disposable PR, observe the new App-owned `adaptive-trust-ci/verified@<new-epoch>` check on the exact SHA, then update branch protection to that exact App ID/context. Never remove the old required context before the new one is proven.

The policy switch removes only interactive approvals from change validation. Holdout validation, exact-SHA checkout, source-mutation detection, immutable runner/image pins, signed attestation, and App-owned branch protection stay mandatory. Production writes remain impossible without a fresh promotion envelope.

## Rollback

- Before step 4: disable promotion consumption or roll back the application image; existing PR approvals still protect changes. Preserve the additive tables and audit history.
- After step 4: activate the production kill switch first. Roll back to reviewed API/worker/deploy images and forward-fix the schema; never drop promotion/audit data.
- If the promotion gate cannot be restored promptly, restore the previous PR-approval policy as a temporary safety gate. This creates another policy epoch, so prove its App-owned check before changing branch protection.
- Any policy rollback invalidates outstanding promotions because their full policy epoch no longer matches. Never accept an old envelope and never bypass the promotion gate to recover availability.

## P0 acceptance tests

- Canonical-signature tamper tests for every signed field; key lifecycle and environment scope checks.
- Exact source-attestation/repository/commit/policy binding, including merge-commit versus PR-head mismatch.
- Duplicate UUID and nonce under concurrent PostgreSQL submissions; exactly one succeeds and one accepted audit event exists.
- Concurrent consume: exactly one caller succeeds; expiry at the boundary, replay, restart, and connection-loss cases deny.
- Artifact bytes changed after signing, target/environment changed, or deployed policy rotated: deploy adapter performs zero external writes.
- Migration/role tests prove API cannot broadly mutate/delete promotions or audit events.
- Staged-policy tests prove PR changes pass without interactive approval only under the new policy epoch, while production still requires a promotion.

## Non-goals

No private-key handling by agents or the server, no repository-controlled trust store/policy mutation, no generic reusable approval token, no automatic production approval, no GitHub Actions, no deploy side effects inside `POST /promotions`, and no destructive rollback migration.
