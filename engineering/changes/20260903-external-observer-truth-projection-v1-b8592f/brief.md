# External Observer truth projection v1

Change `20260903-external-observer-truth-projection-v1-b8592f`, route `b8592fb2815a`, medium risk, API/integration. Design: [external observer](../../../docs/superpowers/specs/2026-09-03-external-observer-truth-projection-design.md). Plan: [implementation plan](../../../docs/superpowers/plans/2026-09-03-external-observer-truth-projection.md).

## Problem and outcome

Mutable PR/SHA facts are hand-authored across `PROJECT_STATE.json`, README prose and local receipts without one freshness invariant. The outcome is a deterministic, bounded, read-only truth projection for an operator-configured repository/main/candidate PR/required Check Run/newest stable release plus independent milestone claims, emitted as canonical `PUBLIC_STATUS.v1` JSON and derived human text.

The observer reports whether claims match current public facts; it never makes delivery true. Exact equality establishes identity freshness, compare topology proves ancestry/release lag, and implemented/reviewed/check-verified/delivered/released remain separate.

## Scope

In scope: a closed config schema and placeholder example with actual selection owned by the operator; typed claims and output; bounded local claim readers; a fixed public GitHub GET adapter; coherent opening/closing rereads; PR/check/tag/compare validation; stale/unknown recovery; deterministic JSON/text; CLI; distinct service/domain architecture node; fake-only tests; optional inert nonprivileged service source.

Out of scope: GitHub Actions, credentials, arbitrary repositories/PR discovery as authority, webhooks/GraphQL/git subprocess, external writes, automatic source/pin/README/PROJECT_STATE/receipt changes, PR/push/merge/release/deploy, Trust CI or human approval authority, private attestation access, Factory/M5 behavior, production operations or retroactive historical milestone delivery claims.

## Constraints and schedule

Backward compatibility is additive; existing change-spec v1, controller, Trust CI and runtime receipts remain unchanged. Only normalized public metadata and digests may persist in ignored runtime state; no raw bodies, credentials, PII or high-cardinality labels. Limits are fixed at configuration/contract boundaries and the entire run is bounded.

Hard deadline is `2026-09-04 23:59 UTC+3`. Observer docs/code/evidence precede M5; accepted M5 still requires accepted M4. The hourly plan is authoritative planning, not a completion promise or external-write grant.
