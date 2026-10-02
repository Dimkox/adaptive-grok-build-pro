# Add Factory v1.5 decision accounting boundary behavior from source commit 531089f to the PR2 persistence foundation: enforce bounded cost and duration values and exact persisted accounting invariants as a new feature slice, with regression tests and isolated PR delivery

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20261002-add-factory-v1-5-decision-accounting-boundary-be-797c13`
Created: 2026-10-02T00:47:25+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Add Factory v1.5 decision accounting boundary behavior from source commit 531089f to the PR2 persistence foundation: enforce bounded cost and duration values and exact persisted accounting invariants as a new feature slice, with regression tests and isolated PR delivery

## Outcome

Factory cost summaries cannot report a value that PostgreSQL signed-bigint accounting cannot represent. Incomplete cost and timing remain factual instead of being promoted to invented totals.

## Scope

### In scope

- Add the cumulative signed-64-bit guard from source commit `531089f`.
- Adapt its cost, timing and parser regression matrix to PR2's shared dependency-free test layout.
- Preserve PR2 decision persistence, replay, fencing and audit behavior.

### Out of scope

- Durable cost/time persistence, provider-attempt ledgers, budget reservation and BB-R11/BB-R12 completion.
- Full U2, U3, U5-U7 or release completion claims.
- Schema, migration, HTTP/event, authorization or deployment changes.

## Constraints

- Backward compatibility: valid in-range summaries keep their existing shape; only previously unrepresentable aggregates become errors.
- Data/privacy: no new data or external transmission.
- Performance: one constant-time bound check per known charge.
- Operational: stacked on PR231; no merge or production action in this change.
