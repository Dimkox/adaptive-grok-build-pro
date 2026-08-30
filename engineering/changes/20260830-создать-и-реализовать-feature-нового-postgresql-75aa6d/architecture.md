# Architecture — production-only human approvals

## Current behavior

The current service persists PR jobs, approvals, attestations, leases, and events. `ApprovalPayloadV1` is PR/base/head/scope shaped, and the closed-merge webhook does not yet provide an authoritative durable merged-commit bridge.

## Proposed behavior

## Components and boundaries

## Data flow

## API and event contracts

No Bitrix impact.

## Decisions

## Risks and mitigations
Trust CI validates PR heads and can require human scopes based on changed paths. It has no authoritative merged-commit bridge or artifact-bound production authorization; closed webhook events are discarded. PR approval v1 is PR/base/head/scope shaped and is not a production contract.
Persist an HMAC-authenticated merge fact, independently corroborate it through GitHub App API, validate/build the exact merged object, and attest its artifact. Accept a separate human-signed promotion only against that chain, then allow a dedicated deployer to consume it once before any side effect. Remove PR-time approval rules only after shadow/deny-only proof.
- API: webhook intake and promotion validation; neither has production credentials.
- Worker: GitHub corroboration, exact-SHA runner and protected-branch/artifact attestation.
- PostgreSQL migration 004: merge facts, protected-branch evidence, immutable promotions, one-time consumptions and append-only events.
- Human CLI: offline create/verify and explicit HTTPS submit; private key stays human-controlled.
- Deployer adapter: computes actual tuple, consumes once, then executes/reconciles external effect.
- External control plane: deployed policy, trust stores and branch protection remain outside repository authority.
`closed+merged webhook -> immutable pending fact -> GitHub API corroboration -> exact-SHA protected-branch job -> signed artifact attestation -> human envelope -> POST acceptance -> atomic consume -> external effect -> terminal audit event`.
OpenAPI and JSON/event schemas are added as versioned repository contracts. `POST /promotions` returns 201 on first acceptance, 200 only for identical idempotency-key replay, 409 for identity/nonce/payload conflicts, stable fail-closed problem codes otherwise. Internal consume requires deployer authentication and exact tuple plus operation ID; it records authorization state only.
- Use distinct frozen promotion and protected-branch evidence contracts; never widen PR Approval v1.
- Webhook fact alone is insufficient; GitHub App API corroboration plus exact-SHA attestation is mandatory.
- Keep signed promotion immutable and model consumption as a separate insert, making replay history append-only.
- Exact duplicate HTTP retry is idempotent retrieval; all cryptographic reuse under another key is conflict.
- Migration is additive and forward-recovered; legacy approvals remain for rollback.
- Policy transition: development validation, PR delivery and merge never require a human signature. External control-plane automation activates and proves `approval_rules: []`, then the production GitHub adapter verifies exact App-bound `old → old+new → new` protection and rolls failures back to `old+new`. If the deployed legacy epoch still asks for approval, that cutover is blocked rather than bypassed with a PR signature. Exactly one human-signed `promotion:production` envelope remains at final production consume/deploy.
- Webhook loss/spoofing: HMAC intake, immutable digest, independent API corroboration and bounded reconciliation.
- Crash window after protected validation: exact-tuple get-or-insert returns the original matching envelope; success publication follows durable evidence and lease-owned completion is replayable.
- Verification boundary: clean exact-SHA repository checks run with installed Python in the read-only/no-network sandbox; Docker-backed PostgreSQL/recovery drills remain Trust-CI-owned trusted-host evidence at the same fingerprint with no socket mount.
- Replay/race: global database uniqueness plus one-row consumption insert in one transaction.
- External-effect atomicity gap: consume-before-effect, unique operation ID, fail-closed crash semantics and reconciliation.
- Control-plane outage: kill switch and deny, never local/in-memory authority.

The complete binding design is `docs/superpowers/specs/2026-08-30-production-only-human-approvals-design.md`.

The executable TDD implementation map, producer-consumer preflight, M2–M9 stacking, and exact verification handoff are in `docs/superpowers/plans/2026-08-30-production-only-human-approvals.md`.
