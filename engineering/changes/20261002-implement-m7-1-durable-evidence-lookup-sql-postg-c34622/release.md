# Release plan — Implement M7.1 durable evidence lookup: SQL PostgreSQL database migration 026, tenant repository isolation, canonical selector digest integrity, bounded queries, SECURITY DEFINER safe privileges and restart Unicode tests.

## Deployment

Source-only isolated-branch PR reconstruction. No production database application, deployed Trust CI change, source binding activation, provider/network integration, tag or release publication is authorized by this package. Migration 026 is additive; 001–025 are byte-identical to the protected starting baseline. Use the existing checksum-verifying migrator only after separately authorized deployment, with a recovery point and isolated data/Trust CI database roles. Applying 026 creates isolated NOLOGIN capability/owner roles and empty durable tables; it seeds no source bindings.

## Feature flags / staged rollout

The default reader remains unavailable. Explicit administrator provisioning and repository-scoped source bindings are required before any M7 facts exist. A durable lookup is advisory evidence: it preserves blocked handoff/M8-not-evaluated/no-authority behavior and cannot substitute an external exact-SHA Trust CI attestation or signed human approval.

## Metrics and alerts

Observe explicit found, not_found, stale, ambiguous, invalid and unavailable lookup outcomes; treat invalid/ambiguous facts and replay integrity refusals as stop signals. Monitor database statement/lock timeouts and migration checksum drift. No production latency, availability or operational qualification is claimed by the disposable synthetic evidence.

## Go/no-go criteria

Focused reconstruction checks passed as recorded in implementation.md. Final full PR verifier, all route-selected independent reviews, exact final-tree receipts, and the external App-owned exact-head Trust CI check plus required approvals remain controller/external prerequisites. No go-live or merge authority follows from this writer's tests.
