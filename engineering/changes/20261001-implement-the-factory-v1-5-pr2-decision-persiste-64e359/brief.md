# Implement the Factory v1.5 PR2 decision persistence contour on current main: transplant the five existing decision persistence commits from the isolated branch, resolve bounded API and data persistence conflicts, preserve behavior and tests, and deliver the isolated candidate

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20261001-implement-the-factory-v1-5-pr2-decision-persiste-64e359`
Created: 2026-10-01T21:15:52+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Implement the Factory v1.5 PR2 decision persistence contour on current main: transplant the five existing decision persistence commits from the isolated branch, resolve bounded API and data persistence conflicts, preserve behavior and tests, and deliver the isolated candidate

## Outcome

Factory persists one closed factual state-transition decision atomically with phase evidence, replays it deterministically, and retains it across restarts without changing existing HTTP callers.

## Scope

### In scope

- Replay exactly the five PR2 commits onto merged PR230 main.
- Add executable JSON Schema parity and two-restart decision durability coverage.
- Preserve append-only, fenced, exact-request PostgreSQL semantics.

### Out of scope

- Full U2, generic decision sources, read/export API, durable cost/time accounting and real evidence/context/profile registries.
- U3, BB behavior, U5-U7 and owner-excluded U4/macOS.
- Merge, release, tag or deployment.

## Constraints

- Backward compatibility: keep `/v1/transitions` unchanged and `decision_record` optional for typed Python callers.
- Data/privacy: closed schema, semantic secret/path checks and repository/task/run binding.
- Performance: advisory-lock serialization is scoped to the idempotency key.
- Operational: migration 023 is additive and forward-only; preserve every other worktree.
