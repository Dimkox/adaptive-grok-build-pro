# M4 Durable Factory Task Control Plane

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown cannot override typed IDs or approval scopes.

Change ID: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
Route: `b7f288f1e81e`
Implementation base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
Clean-base fingerprint: `17f8ca8d94a118d02192e5fa0bd9cafc6e219354e390f1d640511d6e6a4fcaa2`

## Problem and outcome

Interactive work has no independent durable control plane. M4 adds a separate local `factory/` Python package backed by PostgreSQL `factory.*` so authenticated callers can submit immutable M1/M2/M3-bound work and operators can inspect, cancel, lease, fence, budget, kill, audit, and reconcile it after restart.

The positive M4 endpoint is `ready_for_human`. M4 has no provider, workspace, repository command, GitHub, deployment, Trust CI, systemd, connector, or production-write capability.

## Current delivery checkpoint

PR #21 at `571cad7877431ac5ab5779b53fe9f7effd6859ce` had only `root-unittest` fail within its App-owned Trust CI run: package Git helpers scrubbed configured `safe.directory`, so the UID-10001 runner rejected its differently owned `/workspace` checkout. GitGuardian separately reports FAILURE; its contents are not inspected or inferred. Local source fix `3b1f9a54a964d91f34cee2628374b17e7a42edeb` and rebuilt package commit `9727bc30c82bb44a86db0ef5b62e507b5527207a` pass verifier 14/14 at fingerprint `b0a230f6…`, root 537/537 and focused different-owner/package checks. This is an unpushed local candidate, not the final promised PR head: current docs/package parity may create a descendant SHA, which must receive fresh exact-head verification/reviews and an authorized PR update before App-owned recheck. No merge, tag, release or activation is claimed.

## Scope

In scope: closed contracts; immutable accepted intent/task/run/attempt facts; idempotent superseding intake; factory-only checksum migrations; `SKIP LOCKED` leases and monotonic fences; 20/10/1 capacity; initial plus two infrastructure retries; four-hour/USD 25/token/output/event/repair ceilings; kill switches; hash-chained audit; bounded reconciliation; scoped Unix-socket API/CLI; disposable PostgreSQL tests; architecture, verifier, installer, README and recovery documentation.

Out of scope: M5 execution, M6 validation, M7 delivery, M8 autonomy, M9 deployment, `baby-bot`, TCP exposure, Trust CI state or credentials, external writes and production mutations.

## Approved rulings and gates

- The user explicitly approved automatic execution and the existing M4 scope/design on 2026-08-31. This satisfies `scope_and_design_approval` only.
- The route was rebound before product code to accepted M3 merge `67714a1...`. The fingerprint was derived by the repository `tree_fingerprint` algorithm from that clean snapshot; the same bytes produce `17f8ca...`.
- M1/M2/M3 intake identities are consumed from their own frozen producer artifacts. The implementation-base SHA is not substituted for producer exact-base/head pairs; historical SHAs are never fabricated into an intake handoff.
- Migration permission is limited to a freshly created disposable local PostgreSQL test database. No existing, external, production, Trust CI, or shared database may be read or mutated.
- Runtime deadline is 14,400 seconds per task. The superseding `2026-09-04 23:59 UTC+3` whole-program deadline is delivery planning only, never a product field or a gate waiver.
