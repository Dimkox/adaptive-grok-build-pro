# M6 Provider-Independent Semantic Validation — Provisional M4 Slice

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown cannot override typed IDs or approval scopes.

Change ID: `20260901-m6-provider-independent-semantic-validation-prov-82aac8`  
Route: `82aac86a3bf9`  
Provisional base: `94fc5ad878e6b15df6418303caada49a3b93bf4c`  
Planning deadline: `2026-09-08T00:00:00+03:00` (calendar coordination only; never a product deadline or quality-gate waiver)

## Problem and outcome

The M4 tree has no M5 `TaskPacket`, `RunManifest`, or `WorkspaceResult`. Adding M6 storage, API, state transitions, or runtime wiring now would fabricate interfaces and collide with M4 meanings: `RunRole` has reader/writer, attempts `1..3` are infrastructure attempts, `repair_count` accounts for worker loss, and successful work ends at `ready_for_human`.

This provisional slice freezes only the stable provider-independent M6 core: five closed JSON schemas and strict parsers, typed requirement identity, exact-state subject binding, deterministic adjudication, validator separation proof, and pure same-original-writer/fresh-context repair policy for cycles `1..3`.

## Scope

In scope: semantic subject/finding/coverage/verdict/repair contracts; canonical digests; exact coverage; deterministic anomaly reporting and decision precedence; independent validator proof; recurrence and escalation; stale evidence; focused local tests and current-doc parity.

Out of scope and BLOCKED on factual M5: persistence/migrations, API/events, provider adapters/calls, TaskPacket/RunManifest/WorkspaceResult integration, roles/states, fences/idempotency, restart, cost/duration persistence, holdout/review execution. M7 PR evidence and all external operations are later work.

## Constraints

- Add-only pure modules/schemas; no M4 model, state, SQL, API, or OpenAPI changes.
- Local synthetic fixtures only; no credentials, provider streams, database or network.
- Canonical UTF-8 JSON, sorted unique sets, integer millionths, no clock/randomness in adjudication.
- Provider results are inputs, never transition or approval authority.
