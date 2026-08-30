# Production-only human approvals

Status: user-approved design; implementation may proceed without further human/chat gates until the final production go/no-go ceremony.
Route: `75aa6daa89b1`. Base: `1c06299894279a88b881defa3f19b004fa742223`.

## Decision and outcome

The user approved moving all human signatures out of development and into one final production promotion/deploy ceremony. Development validation, pull-request delivery and merge run automatically from App-owned evidence; they never wait for a signature or chat approval. The App-owned `adaptive-trust-ci/verified@<policy-sha12>` Check Run, exact-SHA execution, external holdout, source-integrity checks, signed CI attestations and branch protection remain mandatory.

An ordinary PR will eventually reach a terminal Trust CI result using automated evidence alone. A production mutation will remain impossible until an authorized human signs a short-lived envelope for one exact merged commit, one immutable artifact digest, one environment and the active full policy epoch, and a separately authenticated deployer atomically consumes that authorization once.

## Scope

This change introduces a frozen `PromotionEnvelopeV1`, authoritative merged-commit and artifact provenance, PostgreSQL-backed acceptance/audit/one-time consumption, API and offline CLI contracts, deployer authorization integration, monitoring, runbooks, and the staged policy transition.

It does not auto-merge or deploy, hold a human private key, add GitHub Actions, grant production credentials to the API or worker, change production systems during repository implementation, delete legacy approvals, or widen beyond the configured repository and named environments. `POST /promotions` creates authorization data only; it never tags, uploads, publishes, applies infrastructure, changes a release, or writes an application production database.

## Trust boundaries and actors

- The webhook API owns the GitHub webhook HMAC and may append an unverified merge fact. It has no GitHub App key, CI signing key, human private key, or production credential.
- The worker owns the GitHub App credential and CI attestation signing key. It corroborates merge facts through GitHub's installation API, executes exact-SHA protected-branch validation, and records provenance. It cannot accept human promotion signatures or deploy.
- The promotion API owns a read-only human public-key trust store and narrowly scoped PostgreSQL functions. It verifies and records promotion envelopes. It has no signing or production credential.
- A human-controlled workstation owns the Ed25519 promotion private key. Agents, repository code, API and worker never read, generate, request, submit or simulate it.
- The deployer owns production credentials and a dedicated API identity. It can consume an existing authorization but cannot mint merge evidence, CI attestations, artifacts or human signatures.
- PostgreSQL, deployed policy/holdout, deployed images, public-key stores, GitHub App identity and branch protection remain outside the pull-request trust domain.

## Frozen contracts

### `PromotionPayloadV1`

The signed payload is strict canonical JSON with duplicate keys and unknown fields rejected:

| Field | V1 rule |
| --- | --- |
| `schema_version` | integer `1` |
| `promotion_id` | canonical lowercase UUID |
| `nonce` | base64url without padding, exactly 32 random bytes |
| `actor` | non-empty normalized trust-store identity, maximum 128 bytes |
| `key_id` | non-empty normalized trust-store key ID, maximum 128 bytes |
| `repository` | configured lowercase `owner/name` |
| `merged_commit_sha` | exactly 40 lowercase hexadecimal characters |
| `artifact_sha256` | exactly 64 lowercase hexadecimal characters; digest of the exact deployed bytes |
| `target_environment` | configured lowercase identifier; v1 production value is `production` |
| `policy_epoch` | full 64-character SHA-256 digest of the deployed policy |
| `source_attestation_id` | canonical UUID of the exact protected-branch attestation |
| `reason` | UTF-8, trimmed, 1–512 bytes |
| `issued_at` | RFC 3339 UTC instant with `Z`, second precision |
| `expires_at` | RFC 3339 UTC instant with `Z`, second precision |

`expires_at` must be later than `issued_at`; `issued_at` may be at most 60 seconds in the future. The server-owned environment policy sets the maximum TTL, 15 minutes for production and never more than one hour. SHA-256 Git object IDs require a future version; v1 is not widened in place.

### `PromotionEnvelopeV1`

The envelope contains exactly `payload`, `algorithm: "Ed25519"`, and `signature` encoded as base64url without padding. The signature covers the UTF-8 bytes of canonical JSON for the complete payload. This is a separate frozen contract from PR-scoped `ApprovalPayloadV1`; it has its own schema, model, verifier, storage and CLI.

The verifier requires an active public key at issue and verification time with explicit `promotion:production` scope. It compares repository, environment, policy epoch, source attestation and time limits with server-controlled values before recording authority. A valid signature for another target is invalid here.

### Protected-branch and artifact provenance

A human signature is not merge or artifact evidence. Authority is a three-link chain:

1. After webhook HMAC verification, `pull_request.closed` with `merged=true` appends a normalized merge fact. It binds delivery GUID and payload digest to repository ID/name, installation ID, PR number, head/base SHA, configured protected ref, `merge_commit_sha`, `merged_at`, and receipt time. Caller data remains `pending` and cannot authorize a promotion.
2. A leased worker uses the GitHub App installation API to fetch the same PR and exact commit object. Repository, PR, merged flag, protected base ref and merge SHA must match the stored fact. A protected-ref push is correlated when available; webhook loss is recovered by bounded PR reconciliation. Neither a mutable branch head nor a caller assertion is sufficient.
3. The worker validates the exact merged object in the isolated runner under the active policy and holdout, builds immutable bytes, verifies the signed supply-chain manifest, and writes a distinct frozen protected-branch attestation. It binds merge fact, repository, protected ref, merged SHA, full policy epoch, runner/holdout/image digests, artifact SHA-256 and result `passed`. The App-owned Check Run and Ed25519 attestation must refer to that exact SHA.
4. Evidence persistence is exact-tuple idempotent: a crash retry reuses the original matching signed envelope and rejects any digest/fact/signer mismatch. The App success result is emitted only after that durable transition; merge-fact completion remains lease-owned and safely retryable.

The exact merged SHA need not still be the protected branch tip. It must be the object independently confirmed by GitHub as having landed on that branch. Promotion acceptance joins the exact `source_attestation_id` and rejects any repository, commit, policy or artifact mismatch.

## Durable model and migration 004

Add one forward-only, checksum-locked migration named `004_production_promotions.sql`. Its bytes must be identical in `trust-ci/sql/` and `trust-ci/src/adaptive_trust_ci/resources/`. Historical migrations remain untouched. Migration 004 creates only new tables, indexes, constraints and narrowly granted functions, avoiding scans or rewrites of existing tables:

- `trust_ci_merge_facts`: immutable normalized webhook fact, unique delivery GUID, payload SHA-256, exact repository/PR/ref/SHA fields and received time.
- `trust_ci_protected_branch_evidence`: immutable GitHub API corroboration and passed exact-SHA/artifact attestation, foreign keys with `ON DELETE RESTRICT`, unique `(repository, protected_ref, merged_commit_sha, policy_epoch, artifact_sha256)`.
- `trust_ci_promotions`: immutable canonical payload, signature, payload SHA-256, idempotency key/digest and typed bindings; primary key `promotion_id`, globally unique nonce, payload digest and idempotency key; restrictive provenance foreign key.
- `trust_ci_promotion_consumptions`: append-once record keyed by `promotion_id`, with unique `operation_id`, consumed time and exact tuple copied for reconciliation. There is no unconsume or update of signed fields.
- `trust_ci_promotion_events`: append-only accepted, rejected, consumed, deployment-completed, deployment-failed and deployment-reconciled facts with correlation identifiers and bounded sanitized details.

Checks enforce normalized identities, lowercase SHA/digests, positive time windows and bounded text. Authorization queries use typed columns, never JSONB. A covering index supports exact `(promotion_id, repository, merged_commit_sha, artifact_sha256, target_environment, policy_epoch, expires_at)` consumption; operational indexes cover accepted-but-unconsumed expiry and ordered per-promotion events. Pre-rollout PostgreSQL evidence includes `EXPLAIN (ANALYZE, BUFFERS)` at projected high cardinality.

The migrator owns DDL. The webhook API can append merge facts through a constrained function. The worker can append corroborated provenance. The promotion API can execute acceptance and bounded rejection-audit functions. The deployer can execute only consume/reconciliation functions. Backup is read-only. Revoke function execution from `PUBLIC`; no runtime role receives `DELETE`, `TRUNCATE`, general table `UPDATE`, or the ability to forge another actor's event class.

Promotion identity, nonce and consumption records are retained for at least 400 days and never for less time than restorable backups can reintroduce requests. V1 performs no routine deletion. Later archival must be bounded, separately approved and checksum-verifiable.

## API contract

The checked-in OpenAPI 3.1 document and JSON schemas are the machine-readable authority; runtime documentation remains disabled.

### `POST /promotions`

Request body is `PromotionEnvelopeV1`, capped at 16 KiB, with `Content-Type: application/json` and a required 16–128 character `Idempotency-Key`. TLS/reverse-proxy controls and rate limits protect the endpoint; the Ed25519 envelope is the human authorization. No bearer token, signature or rejected raw body is logged.

Validation order is: request framing and strict decoding; kill switch/readiness; server policy/repository/environment/time; trust-store key lifecycle/scope; Ed25519 signature; exact merge/artifact/attestation bindings; atomic persistence. Database, policy, trust store or provenance unavailability denies.

The acceptance transaction locks/rechecks exact provenance, inserts the immutable promotion, and appends one `promotion.accepted` event before commit. It returns `201` with promotion identity, exact tuple, expiry and `consumed: false`. An exact retry with the same idempotency key and canonical request digest returns the stored representation as `200` with `idempotent_replay: true`; it neither creates nor extends authority. Reusing the key with different bytes, or reusing promotion ID/nonce/payload digest under another key, returns `409`.

Stable `application/problem+json` errors expose a correlation ID and bounded code: `400 malformed_envelope|unsupported_contract`, `401 signature_invalid` (also unknown/revoked/wrong-scope keys to avoid an oracle), `403 target_forbidden|policy_mismatch|provenance_mismatch`, `409 idempotency_conflict|promotion_replay`, `422 envelope_not_current`, `429 rate_limited`, and `503 authorization_unavailable|promotion_disabled`. None performs a production side effect.

### `POST /promotions/{promotion_id}/consume`

This internal endpoint requires the dedicated deployer identity using mTLS or the existing constant-time bearer mechanism, rate limiting, and a required globally unique `operation_id`. Its body repeats repository, merged SHA, artifact SHA-256, environment and policy epoch calculated by the deployer from the exact bytes and target it is about to use.

One transaction rechecks the exact promotion/provenance tuple, current policy and time, inserts the unique consumption row, and appends `promotion.consumed`. Exactly one inserted row returns `200`; absent, expired, mismatched, already-consumed or stale-policy authority returns `409`/`403` and denies. Database failure returns `503`. The endpoint changes authorization/audit state only; it has no production credential and performs no deployment.

Consume happens immediately before the first production side effect. A crash after consume is intentionally fail-closed: there is no unconsume and no automatic second envelope. The deployer reconciles the external system using `operation_id`, avoiding duplicate non-idempotent writes, and appends a terminal deployment event through its constrained interface.

### Webhook and reconciliation behavior

The webhook returns `2xx` only after merge fact plus enqueue/outbox state commit. Duplicate delivery GUID with identical digest is a no-op; the same GUID with another digest is a security conflict. Worker retries dependency failures from durable `next_attempt_at` eligibility with bounded 5–300 second exponential backoff; process restart cannot erase it and the normal poll delay prevents hot loops. Identity mismatches are permanent and alerting. The bounded scheduled reconciler lists recently updated merged PRs from a durable watermark, requeues retry-exhausted facts through a constrained dead-letter transition, and repairs missed webhook facts without trusting a mutable branch tip.

## CLI contract

- `adaptive-trust-ci promotion-create` runs only on a human-controlled machine, accepts every payload field explicitly, enforces strict syntax/time limits, reads a named external private-key path, writes one envelope with mode `0600`, and never contacts production.
- `adaptive-trust-ci promotion-verify` performs offline canonical/schema/signature verification against an explicit public trust store and expected tuple; it prints no private material.
- `adaptive-trust-ci promotion-submit` sends one existing envelope and explicit idempotency key over HTTPS, prints the bounded response/correlation ID, and never fabricates or refreshes an envelope.
- Consumption is invoked by the deploy adapter with its machine identity, not by the human signing CLI. Existing approval commands remain for rollback compatibility but become inactive in change validation after cutover.

CLI exit codes are stable: `0` success/idempotent retrieval, `2` local usage or contract failure, `3` rejected authorization, `4` conflict/replay, and `5` dependency/network failure. Private keys and envelopes are never accepted from environment variables or command-line literal values.

## Audit and observability

Every security-relevant decision has a versioned append-only event with event ID/type/time, promotion/correlation/operation IDs when known, actor/key ID, repository, exact SHA, artifact digest, environment, policy epoch, outcome and stable reason code. Rejections are recorded in a separate bounded transaction without the raw body. If rejection audit storage fails, rejection still stands and a metric/page signal fires.

Metrics include merge-fact pending age/count, reconciliation lag, protected-branch validation outcomes, promotion accepted/rejected/replay/expired counts, accept/consume latency, database/trust/provenance errors, accepted-but-unconsumed count, consumed-without-terminal-event age, and audit persistence failures. Repository, SHA, promotion and operation IDs belong in structured logs/audit, not Prometheus labels. Alerts fire on any authorization without an exact provenance join, delivery hash conflict, nonce conflict anomaly, stalled reconciliation, restore inconsistency or fail-closed dependency outage.

## Staged implementation, automated policy cutover and one final production signature

1. **Local dormant build:** implement contracts, migration, provenance pipeline, endpoint, consume boundary, metrics and kill switches. Exercise real ephemeral PostgreSQL, shadow decisions, deny-only behavior, webhook reconciliation, merge strategies, artifact substitution, concurrency, restart/restore, role isolation and rollback locally or in isolated exact-SHA automation. Do not migrate an external database, deploy a service, mutate branch protection, sign as a human or change deployed policy from repository code.
2. **Automated change-validation cutover:** deploy the already reviewed policy with `approval_rules: []` through the external Trust CI control-plane automation, prove its new App-owned epoch check on a disposable PR, then use the GitHub adapter to read the exact old App-bound context, PUT/read-back exact `old+new`, and PUT/read-back exact `new`. Failure rolls back to verified `old+new`, never an empty or text-only context set. This is an operational prerequisite for autonomous development, not a signature ceremony or a repository-local mutation. If the currently deployed policy still returns `needs_approval`, development delivery is blocked on that external cutover; no PR approval envelope is requested as a workaround.
3. **Automated development delivery:** every implementation PR, including this integration PR, reaches terminal pass/fail from automated exact-SHA evidence alone and merges through the normal protected automation. After merge, the worker records the authoritative protected-branch/artifact attestation. No user/chat approval or human signature occurs in validation, PR delivery or merge.
4. **Single final production ceremony:** after an exact merged commit and immutable artifact are already attested, one human makes the sole go/no-go decision and creates exactly one fresh `promotion:production` envelope. The system independently verifies it, atomically consumes it once immediately before the first production side effect, deploys the exact artifact, and records terminal audit/reconciliation evidence. Any mismatch or dependency failure aborts with zero production writes.
5. **Steady state:** ordinary PRs remain fully automated. Every production deploy requires one new `promotion:production` envelope and atomic one-time consumption; no other human signature is part of the workflow.

## Rollback and recovery

Before the final ceremony, rollback means revise/revert development normally or restore the previous reviewed automated-only policy epoch while preserving an App-owned required check. During the production ceremony, any failure before consume aborts without deployment; after consume, recovery reconciles the exact operation ID and never recreates authority.

After consume/deploy, activate the production kill switch first on any fault, restore reviewed images/data as documented, and keep or restore the old PR-approval policy until the new automated-only epoch is proven. If the new epoch was already activated, restore the previous policy, prove its App-owned exact check, and move branch protection back without an unprotected interval. Any epoch change invalidates outstanding promotions. Never recover availability by accepting an old/unsigned envelope, deleting nonce/consumption history, or bypassing exact-SHA/artifact verification.

Schema recovery is forward-only: never edit or down-migrate 004. Apply a new checksum-locked migration for corrections. After database restore, reconcile consumption `operation_id` values with external deployment history before re-enabling production; a restore must not reset replay or consume-once authority.

## Test and evidence gates

P0 automated evidence must prove strict schema/canonical signature tamper rejection for every field; key lifecycle/scope; all time boundaries; exact webhook/API/commit/attestation/artifact joins; squash/rebase/merge behavior; webhook loss reconciliation; policy rotation; idempotent retry and conflicting replay under concurrency; one successful consume across replicas; atomic accepted/consumed events; process/database restart; transaction loss; role isolation; migration mirror/checksum/repeatability; bounded query plans; supply-chain byte substitution denial; and zero external writes on every denial.

The final production ceremony is forbidden until unit, contract, real PostgreSQL, restart/restore, negative E2E, local shadow/deny-only and rollback evidence pass on one fingerprint, followed by independent code, test, security, data and release reviews. Exact-SHA repository checks run with installed `python3` in the read-only/no-network sandbox; trusted-host PostgreSQL/recovery orchestration is separate fingerprint evidence and never receives control from the untrusted checkout or mounts a Docker socket into it. The post-activation proof must show formerly approval-triggering paths complete automated validation without `needs_approval`, while an automatic failure still produces terminal non-success.

## Go/no-go invariants

Go only when the frozen final stack is automated-green; the gate is fail-closed and observable; exact merge/artifact provenance, local consume-once and restore drills pass; the old policy remains active until the single ceremony; and rollback keeps branch protection bound to an observed App-owned check.

No-go on any placeholder authority, mutable ref/artifact, API/worker production credential, signing key in the agent/host service, reusable consumption, missing audit, unavailable recovery evidence, policy removal before gate proof, or operator documentation that still conflates PR approval with production promotion.
