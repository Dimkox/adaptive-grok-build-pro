# Implement bounded Factory v1.5 result admission contract API

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20261002-implement-bounded-factory-v1-5-result-admission-0fb1eb`
Created: 2026-10-02T04:39:46+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Implement the bounded Factory v1.5 result admission contract and HTTP API from source commit b0579a390, stacked on PR233; preserve hardened offline result sanitization, keep persistence and dispatch excluded, add closed OpenAPI/schema contracts and regression tests

## Outcome

A closed V2 identity envelope and authenticated POST/GET contract are available for integration, while the real service truthfully returns `503 result_admission_unavailable` until durable storage exists.

## Scope

### In scope

- Add immutable `ResultEnvelopeV2` without changing V1.
- Add strict bounded API parsing, authorization, identity binding, correlation and canonical contracts.
- Register the V2 schema with the proposal broker and the HTTP contract with the local API.

### Out of scope

- Persistence, replay, outbox, dispatch, model/provider calls and live interception.
- U4/macOS/Apple qualification and broad milestone completion claims.

## Constraints

- Backward compatibility: V1 and all seven unavailable channel qualifications remain unchanged.
- Data/privacy: errors contain only bounded codes/details and never body, token or idempotency material.
- Performance: the existing 1 MiB request middleware bound applies before JSON parsing.
- Operational: no store capability is invoked; activation requires a later persistence slice.
