# Implement restart-safe qualified native result dispatch

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20261002-implement-restart-safe-qualified-native-result-d-d349f5`
Created: 2026-10-02T11:40:02+00:00
Risk: medium
Complexity: standard
Domains: data, api, event

## Problem

Implement PostgreSQL migration and database-backed restart-safe qualified native result dispatch by adapting aefbde3ed c5fe8f397 8ffd66982 onto PR235: durable outbox claim retry ambiguous recovery, API event contract, explicit network allowlist; no provider model invocation, live interception, U4 or macOS work

## Outcome

An explicitly enabled, separately credentialed local dispatcher can hand an already-admitted
result to one trusted Unix socket and durably observe the exact outcome across crashes. The
foundation remains dormant because no qualification or enqueue authority exists.

## Scope

### In scope

- Additive migration 025 with composite source identity, fenced SKIP LOCKED claims, finite
  send/observation budgets, monotonic ambiguity and a dedicated dispatcher capability.
- Closed internal UDS handoff/observation v1 wire, exact response binding and fake-UDS/real-PG tests.
- Qualification v2 that keeps all seven channels unavailable.

### Out of scope

- Automatic enqueue, triggers, backfill, receiver/provider/model invocation or live interception.
- BB/FPF/VibeVM activation, U3/U6/U7 completion, production qualification and U4/macOS.

## Constraints

- Backward compatibility: migration 024 and PR235 admission bytes remain unchanged.
- Data/privacy: only sanitized envelopes cross the UDS; bearer material is never persisted/logged.
- Performance: bounded batches use a partial index and SKIP LOCKED.
- Operational: default off; lease covers HTTP timeout plus processing margin; forward-fix rollback.
