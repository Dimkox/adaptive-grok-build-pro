# Implement durable Factory v1.5 result admission persistence

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20261002-implement-durable-factory-v1-5-result-admission-4bcad9`
Created: 2026-10-02T07:10:37+00:00
Risk: medium
Complexity: standard
Domains: data, api

## Problem

Implement durable transactional Factory v1.5 result admission persistence and dormant outbox from source commit efc003f57, stacked on PR234; add migration and real PostgreSQL replay, tenant, restart and concurrency tests while keeping dispatch and live interception disabled

## Outcome

Authenticated workers can atomically persist and exactly replay a bounded V2 result; authorized readers can retrieve the immutable envelope after restart. No result is dispatched.

## Scope

### In scope

- Migration 024, transactional store/service/API activation, bounded read, OpenAPI responses, and PostgreSQL concurrency/restart evidence.

### Out of scope

- Provider/model dispatch, live interception, BB activation, channel qualification, U4/macOS, and milestone completion claims.

## Constraints

- Backward compatibility: V1 and all seven unavailable qualification rows remain unchanged.
- Data/privacy: canonical envelopes are secret-checked in Python and PostgreSQL; reads require repository authority.
- Performance: natural-source and command identities serialize with transaction-scoped advisory locks; statements stay bounded.
- Operational: additive migration only; runtime receives function execution and bounded reads, not raw DML.
