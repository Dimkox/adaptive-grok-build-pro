# Task analysis: production-only human approval

Route: `75aa6daa89b1`
Role: `task_analyst` (read-only analysis)
Decision already approved by the user: build and prove the production-promotion gate first; only then remove interactive PR human scopes.

## Observable outcome

Ordinary pull requests can complete the App-owned, policy-epoch exact-SHA Trust CI check without an interactive human signature. A production mutation remains impossible until an authorized human submits one valid Ed25519-signed promotion for the exact merged commit, immutable artifact, target environment and deployed promotion-policy epoch. Verification or persistence failure is deny-by-default and auditable.

This changes where human authority is exercised, not whether production requires human authority. The required PR check remains `adaptive-trust-ci/verified@<policy-sha12>`, owned by the configured GitHub App and bound to the exact PR head SHA.

## Acceptance criteria

### A. Frozen promotion contract

1. A versioned canonical promotion payload/envelope contract exists. The signed payload contains at least: `schema_version`, unique promotion identity, strong unique `nonce`, repository, exact **merged** 40-hex commit SHA, lowercase 64-hex artifact SHA-256, normalized target environment, deployed promotion-policy SHA-256 epoch, actor/key identity, reason, UTC `issued_at`, UTC `expires_at`; the envelope adds only the Ed25519 signature and unambiguous signing metadata.
2. Canonical JSON bytes are deterministic. Unknown/missing fields, duplicate JSON keys, malformed encodings, wrong types, non-canonical identities, unsupported versions/algorithms and timestamps without timezone are rejected before authorization.
3. `expires_at > issued_at`; issuance cannot be unacceptably far in the future; TTL is positive and no greater than the server-side policy maximum. Client-supplied policy limits are never authoritative.
4. Repository, environment, key and policy are validated against independently deployed server configuration. A valid signature for another repository/environment/commit/artifact/policy epoch is rejected.

### B. `POST /promotions` authorization boundary

5. The API authenticates a human promotion solely through an active, server-mounted Ed25519 public key whose trust-store entry authorizes the `production` scope and requested environment. Private keys never enter the API/worker/container/repository/logs.
6. Signature verification covers the complete canonical payload. The API independently verifies that the commit is an exact commit merged into the configured protected branch and that the supplied artifact digest is the immutable artifact selected for that commit; caller assertions alone are insufficient.
7. Authorization fails closed for: unavailable database/trust store/policy/merge provenance/artifact provenance, invalid or revoked/expired/not-yet-valid key, signature failure, stale policy epoch, expired/future envelope, unknown environment, unmerged or moving ref, SHA/digest mismatch, missing automatic exact-SHA attestation, or an attestation that is not `passed` for that exact commit and policy.
8. Successful submission is atomic: exactly one durable promotion authorization is recorded and an audit event is committed in the same PostgreSQL transaction. The response is returned only after commit.
9. Reusing either promotion ID or nonce returns a deterministic conflict and never authorizes a second action, including under concurrent requests, retries, process restarts and multiple API replicas. Database unique constraints are the final replay boundary.
10. Exact duplicate retry behavior is explicitly frozen: either idempotently returns the already-created immutable record or consistently returns `409`; it must never create or extend authority. A different payload sharing an ID/nonce is always rejected.
11. The created authorization is immutable. It cannot be edited, retargeted, extended or rebound to another artifact/commit/environment. Revocation/cancellation, if introduced, is a separate append-only event and cannot erase history.
12. A promotion record authorizes only the named production operation/resource and has a bounded consume-once or explicit state-transition protocol. Merely storing a valid envelope must not itself deploy, publish, merge, tag, or mutate production.

### C. Persistence, least privilege and audit

13. Versioned forward-only migrations create promotion authorization and event data with database checks for identities, digests, timestamps and allowed statuses; unique indexes cover promotion identity and nonce. Queries for authorization/consumption have supporting indexes and bounded plans.
14. Database roles remain separated: the API may validate/create promotion requests and read the minimum provenance; the production executor may atomically consume an eligible authorization; backup/migrator privileges remain distinct. Neither API nor PR runner receives production credentials.
15. Audit events are append-only business facts such as `promotion.accepted`, `promotion.rejected` and `promotion.consumed`, with correlation/promotion ID, actor/key ID, repository, exact commit, artifact digest, environment, policy epoch, result and stable reason code. Signatures, tokens, private material and request secrets are never logged.
16. Rejections that reach the authorization boundary are observable without persisting untrusted oversized payloads. Metrics cover accepted/rejected/replayed/expired/stale-policy requests, database failures and consumption outcomes, with alerts on authorization bypass symptoms and sustained failures.
17. PostgreSQL restart and concurrent-submit tests prove durability and replay rejection. Migration tests cover a populated database, repeat invocation, role grants, rollback/forward-recovery and no destructive/unbounded SQL.

### D. Proof before removing PR approvals

18. Before any PR approval rule is removed, the production gate passes unit, API contract, signature/timestamp/policy, concurrency/replay, PostgreSQL integration/restart, authorization-consumption and negative-path tests. Independent code, test, security, data and release reviews pass on the same fingerprint.
19. A disposable/non-production end-to-end drill proves: App-owned exact-SHA check succeeds; a merged test commit and exact test artifact cannot be promoted without a valid envelope; mismatched/replayed/expired/stale-policy envelopes fail; one correct envelope authorizes exactly one test-environment consumption; complete audit evidence survives restart.
20. The deployed production gate is health-checked and remains fail-closed before the deployed change-validation policy is altered. Its runbook, kill switch, monitoring, backup/restore and forward-recovery procedure are exercised.
21. Only after criteria 1–20 are evidenced may a second policy epoch remove `governance`, `database` and `production` interactive approval rules from the **pull-request validation** path. Automated required commands, external holdout, isolated exact-SHA checkout, source-mutation detection, signed CI attestation, GitHub App publisher identity, branch protection and policy-epoch check naming remain mandatory.
22. Policy migration validation proves a PR touching every formerly approval-triggering glob reaches pass/fail from automated checks alone and never `needs_approval`; failures still produce a terminal non-success Check Run. This does not weaken local delegated-operation grants or production authorization.
23. Branch protection is changed, if needed, only after the new exact policy-epoch check has passed on a disposable PR and is confirmed App-owned. There is never a window where protected `main` lacks a required App-owned exact-SHA check.

## Explicit non-goals

- No auto-merge, auto-deploy, tag push, release publication, production database write or infrastructure apply in this change.
- No repository, local receipt, prompt, hook, delegated local grant or agent signature becomes human/production authority.
- No agent reads, generates, requests, submits or simulates a human private key or approval.
- No removal or weakening of automated Trust CI commands, holdout validation, isolated runner, exact-SHA binding, signed attestation, source-integrity checks, GitHub App identity binding or branch protection.
- No reuse of the existing PR `ApprovalPayload` with ambiguous semantics; production promotion has a separate versioned contract and storage lifecycle.
- No arbitrary artifact registry or deployment platform integration unless separately specified. The first slice may verify a single configured immutable artifact-provenance adapter, but it must fail closed when that adapter is unavailable.
- No broad migration of historical PR approvals, no destructive cleanup of their tables and no deletion of old audit/attestation evidence.
- No widening from one configured repository/environment without an explicit policy and tenant-boundary design.

## Staged migration and gates

### Stage 0 — Freeze design (current stage)

- Freeze payload/envelope, OpenAPI/errors, audit event schemas, trust-store environment scope, artifact/merge provenance adapter, consume semantics and migration plan.
- Human gate: the user's approval of “option 1” satisfies intent, but the durable scope/design package must state the exact contracts and threat model before implementation transitions to approved.
- External-write/migration gate: no production SQL or deployed control-plane change is authorized by design approval.

### Stage 1 — Add dormant gate

- Implement migrations, model/verifier/store/API/audit/metrics and a production-consumer authorization interface behind a default-off deployment flag or otherwise unreachable production configuration.
- Keep all existing PR `approval_rules` unchanged. This stage must not alter deployed policy/trust store/branch protection or perform external writes.
- Run local and isolated PostgreSQL evidence plus selected independent reviews.

### Stage 2 — Deploy and prove gate while old PR gate remains

- Build immutable API/worker artifacts and deploy migrations/service configuration through the existing controlled infrastructure procedure.
- Human/external gates: explicit migration/external-write authorization for the exact database/service targets; production-action authorization for rollout; existing Trust CI approvals required by the currently deployed PR policy.
- Execute non-production E2E and restart/backup/restore drills. Production endpoint remains unusable or deny-only until readiness criteria pass.
- Stop condition: any verification, provenance, audit, replay, restore, monitoring or role-isolation failure. Roll back application/config or forward-fix additive schema; do not remove PR approvals.

### Stage 3 — One final bootstrap approval and policy-epoch switch

- Prepare a separate, exact policy change that removes interactive PR approval rules only. It must retain every automated authority listed in criterion 21.
- **Bootstrap paradox:** `trust-ci/**`, policy and migration files are themselves classified as `governance`/`database`/`production` under the current deployed policy. Therefore the change that removes those requirements cannot legitimately approve itself. It requires one final external human-signed approval under the old policy for the exact PR/base/head/policy epoch, followed by the App-owned exact-SHA success and normal protected merge.
- Deploy the new server policy externally, yielding a new policy digest and required check name. Validate the new App-owned check on a disposable PR, then atomically update branch protection from the old app-bound context to the new app-bound context without an unprotected interval. Repository code cannot perform or authorize these operations.

### Stage 4 — Post-switch proof and steady state

- Run formerly sensitive-glob canary PRs and prove no interactive approval is requested while all automatic checks and negative failures remain enforced.
- Human approval is now required at `POST /promotions` immediately before production authorization, not during ordinary PR validation. The production executor must match the stored exact commit/artifact/environment/policy and atomically consume authorization.
- Keep historical approval records and the old policy epoch for audit. Monitor rejection/replay/consume metrics and retain a documented switchback to the last known-good policy epoch.

## Human and external gates summary

| Gate | When | Authority/evidence |
| --- | --- | --- |
| Scope/design | Before Stage 1 | User-approved exact contracts, threat model and staged plan in the durable change package |
| Migration/external write | Stage 2 | Explicit operation/resource authorization; reviewed migration and recovery evidence |
| Production gate rollout | Stage 2 | Human production go/no-go for exact immutable artifacts/config/environment |
| Final old-policy approval | Stage 3, once | Human-signed old-policy scope(s), bound to exact base/head/repository/policy epoch; cannot be created by an agent |
| App-owned merge check | Every PR, before and after switch | `adaptive-trust-ci/verified@<policy-sha12>` success on exact head SHA from configured GitHub App |
| Branch-protection/policy mutation | Stage 3 | Human/administrator external operation after disposable-PR proof; no repository-local authority |
| Every production promotion | Stage 4 onward | Fresh human Ed25519 envelope for exact merged commit, artifact, environment and active production-policy epoch |

## Principal risks and rulings

- **Approval relocation accidentally becomes approval removal.** Ruling: PR checks stay automated and immutable; production authorization is independently verified and consume-once.
- **A signed request targets unmerged or substituted bits.** Ruling: verify protected-branch merge provenance, exact artifact digest and successful exact-commit App attestation using server-controlled sources.
- **Replay/race across replicas.** Ruling: transaction plus unique constraints and atomic consume transition are the final authority, not in-memory checks.
- **Policy self-modification.** Ruling: old deployed policy remains authority through its own replacement merge; one final human approval is unavoidable.
- **Control-plane outage interpreted as permission.** Ruling: unavailable dependencies reject promotion and page operators; there is no fail-open/break-glass path in this feature.
- **Rollback reopens production.** Ruling: rollback defaults to disabling promotion/consumption; schema is additive and retained. Switching PR approvals back on is safer than bypassing the production gate.
