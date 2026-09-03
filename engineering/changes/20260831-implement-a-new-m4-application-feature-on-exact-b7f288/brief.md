# M4 Durable Factory Task Control Plane

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown cannot override typed IDs or approval scopes.

Change ID: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
Route: `b7f288f1e81e`
Implementation base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
Clean-base fingerprint: `17f8ca8d94a118d02192e5fa0bd9cafc6e219354e390f1d640511d6e6a4fcaa2`

## Problem and outcome

Interactive work has no independent durable control plane. M4 adds a separate local `factory/` Python package backed by PostgreSQL `factory.*` so authenticated callers can submit immutable M1/M2/M3-bound work and operators can inspect, cancel, lease, fence, budget, kill, audit, and reconcile it after restart.

The positive M4 endpoint is `ready_for_human`. M4 has no provider, workspace, repository command, GitHub, deployment, Trust CI, systemd, connector, or production-write capability.

## Scope

In scope: closed contracts; immutable accepted intent/task/run/attempt/event facts; separate full-intent, semantic-work and command replay identities; idempotent superseding intake; factory-only checksum migrations; `SKIP LOCKED` leases and monotonic fences; operation-scoped task transitions; 20/10/1 capacity; initial plus two infrastructure retries; four-hour/USD 25/token/output/event/repair ceilings; kill switches; hash-chained audit; bounded reconciliation; scoped Unix-socket API/CLI with bounded history; one checked closed inline OpenAPI contract and correlated errors; disposable PostgreSQL tests; architecture, verifier, installer, README and recovery documentation.

Out of scope: M5 execution, M6 validation, M7 delivery, M8 autonomy, M9 deployment, `baby-bot`, TCP exposure, Trust CI state or credentials, external writes and production mutations.

## Approved rulings and gates

- The user explicitly approved automatic execution and the existing M4 scope/design on 2026-08-31. This satisfies `scope_and_design_approval` only.
- The route was rebound before product code to accepted M3 merge `67714a1...`. The fingerprint was derived by the repository `tree_fingerprint` algorithm from that clean snapshot; the same bytes produce `17f8ca...`.
- M1/M2/M3 intake identities are consumed from their own frozen producer artifacts. The implementation-base SHA is not substituted for producer exact-base/head pairs; historical SHAs are never fabricated into an intake handoff.
- Migration permission is limited to a freshly created disposable local PostgreSQL test database. No existing, external, production, Trust CI, or shared database may be read or mutated.
- Runtime deadline is 14,400 seconds per task. The 2026-09-08 calendar deadline is delivery planning only, never a product field or a gate waiver.
