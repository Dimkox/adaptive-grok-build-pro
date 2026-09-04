# Integration architecture analysis — M4 local durable control plane

Route: b7f288f1e81e
Change: 20260831-implement-a-new-m4-application-feature-on-exact-b7f288
Method: read-only analysis; this report is the sole write.

## Decision and prerequisite

M4 must be a separate nested factory package with factory-only PostgreSQL state and an authenticated local Unix-socket API. It consumes frozen M1/M2/M3 evidence; it is not permitted to reconstruct missing prerequisites, share Trust-CI state, execute work, or perform an external action.

The requested implementation base is present as HEAD 67714a1f1b87effcfabe55d5ca2770d0a68d17c1, the accepted M3 merge on accepted M2 022411b. However the active route names 1c062998, which is not an ancestor of 67714a1 in either direction (merge base 069fe822). This is a hard exact-base gate: update/regenerate the route/change binding to the approved 67714a1 base before final architecture/governance verification, receipts, or M4 intake evidence. A handoff bound to 1c062998 cannot describe the M3 interfaces being consumed.

## Frozen handoff compatibility

| Producer | M4 required input | Required rejection gate |
| --- | --- | --- |
| M1 | Valid, frozen, placeholder-free typed change spec digest plus sorted unique acceptance IDs. | Missing/unknown/stale digest or template/package prose is not authority. |
| M2 | ArchitectureHandoffV1: contract version 1, architecture digest/evidence digest, exact base SHA, exact head SHA. | Reject unknown version, invalid SHA/digest, dirty/unavailable exact object, or stale evidence. |
| M3 | GovernanceHandoffV1 closed six-field schema: version, governance digest/evidence digest, M2 architecture digest, exact base/head SHA. | Reject schema weakening, unknown fields/version, or any mismatch with M2/intake base/head/digest. |
| M0 | Immutable availability observation, no older than 300 seconds. | Fail closed unless a named, time-bounded user bootstrap exception is recorded; health endpoint cannot proxy or fabricate M0 authority. |

TaskIntakeV1 must canonicalize and bind repository/source identity and digest, route/change IDs, exact base SHA, M1/M2/M3/policy digests, M0 observation, limits, and acceptance IDs. Its intent digest is canonical SHA-256; its idempotency key binds source type/id/digest, base SHA, and frozen M1/M2/M3/policy identities. Exact duplicate intake returns the active task; a changed source or authority supersedes nonterminal work rather than mutating accepted intent.

## API, CLI, and consumer contract

- Default transport is HTTP over operator-created /run/adaptive-factory/control.sock with dedicated group mode 0660. TCP is disabled by default and no non-loopback listener exists in M4.
- Bearer credentials are root/operator-provisioned regular no-follow files with mode 0600. Compare through hmac.compare_digest and map token digests to closed server-enforced scopes; never read tokens from task content, URL/query, logs, or fixtures.
- Versioned public/admin API is health plus submit, show, list, cancel. Worker/operator claims, heartbeat, proposal, kill/unkill, reconciliation, and migration remain separately scoped. All access, including show/list/cancel, is repository-authorized at the server boundary.
- Mutations require Idempotency-Key and X-Correlation-ID; persist actor/action/resource, idempotency outcome, correlation ID, event, and audit in one transaction. Requests cap at 1 MiB, reject unknown JSON, use opaque bounded cursors/pages, return bounded projections, and redact bodies, settings, query strings, and Authorization.
- The future baby-bot is only a deferred client with task:submit/read/list/cancel scopes. M4 neither reads/edits/restarts/deploys it nor authenticates Telegram. A later bot adapter must verify an explicit Telegram-admin allowlist before invoking M4.

No OpenAPI/API consumer migration is authorized beyond checked-in factory-control.v1. Existing Trust-CI OpenAPI and approval/attestation contracts remain unchanged.

## Durable state, retry, and correlation gates

PostgreSQL factory schema is sole authority for immutable accepted intents, task projection, run/attempt/fence/capacity, reservations/usage, kill/reconciliation, event, and hash-chained audit. It must be a separate database/schema, migration lock, roles, credentials, and migration history from trust_ci. Migrations are contiguous, checksum-immutable, forward-only, and factory-only.

Claim uses SKIP LOCKED and database-enforced 20 global reader / 10 per-repository reader / 1 writer limits. Heartbeat, proposal, phase transition, usage, release, retry, and terminal actions atomically check task/run, owner, unexpired lease, monotonic fence, packet digest, current state, budget, and proposal idempotency digest. Late/replayed/conflicting proposals fail, rather than overwrite evidence.

Only closed infrastructure failure classes retry: initial attempt plus at most two retries; third becomes dead. Contract/auth/policy/stale SHA/digest/budget/security/capability/protocol/provider-quality failures cannot be relabelled by untrusted provider text. Missing price/usage/metering blocks future reservation, never means zero cost. Kill switches stop new claims but retain evidence; reconciliation is ordered, idempotent, max 100 candidates, five-second statement timeout, and restart-safe.

## Non-capability and trust separation

M4 must have no provider/model adapter, shell/workspace/repository/Git command, GitHub fetch/push/PR/merge, connector, deployment/release, systemd, or external-write API/CLI path. Explicitly forbid paths equivalent to provider-run, git-push, pull-requests, deploy, and systemd. Provider output, issue projections, notes, logs, and later adapter results are untrusted data and cannot select transition/retry/budget/authority/capability.

Factory cannot import adaptive_trust_ci, query trust_ci tables, share database roles/credentials, access App/signing/approval keys, publish a Check Run, or treat Trust-CI status as factory state authority. Local verifier/reviews are preflight only; merge remains the deployed App-owned exact-head adaptive-trust-ci/verified@policy-sha12 check with its server policy/holdout/approval gates.

## Architecture/verifier integration gate

Before implementation is acceptable, extend the executable M2/M3 model with a factory-control trust domain and nodes for local API, scheduler/control logic, and factory datastore. Add versioned factory API/intake/claim/proposal contracts and bounded audit/task data classifications. Model only local authenticated Unix-socket and database-role edges, with no-network/local-only policies, bounded retries, idempotency/correlation, failure signals, and fail-closed terminal behavior.

The model must contain no factory edge to Trust-CI PostgreSQL, GitHub publication, Docker executor, isolated runner, provider, workspace, deployment, or systemd. Regenerate all five Mermaid projections from architecture/system.yaml and rules.yaml, then make diagram check pass. The root verifier should run factory unit tests and only run real PostgreSQL integration tests when explicit FACTORY_TEST_DATABASE_URL is supplied; the installer copies nested source/config examples but never .env, socket/token files, database URLs, volumes, or adopted migrations.

Required integration evidence: contracts/intake validation; duplicate/supersession; concurrent claim/20-10-1/fence; dead-letter/budget; kill/reconciliation/restart late-fence drill; API scopes/redaction/bounds; architecture model/diagram/inventory/installer checks; final root verifier and fresh reviews on one final fingerprint.

## Sources

- Active route/package and current accepted M3/M2 base lineage.
- M4 approved plan: docs/superpowers/plans/2026-08-28-m4-durable-factory-control-plane.md.
- M2/M3 architecture/governance/verifier contracts and tests.
