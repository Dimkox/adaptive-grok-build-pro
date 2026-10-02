# Implement new Factory runtime behavior for bounded pre-model result envelopes and deterministic result-channel sanitization, based on source commit aa53f300d and stacked on PR2c; add the closed schemas, Python feature modules and regression tests, excluding persistence and dispatch from this slice

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20261002-implement-new-factory-runtime-behavior-for-bound-dc082e`
Created: 2026-10-02T02:30:49+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Implement new Factory runtime behavior for bounded pre-model result envelopes and deterministic result-channel sanitization, based on source commit aa53f300d and stacked on PR2c; add the closed schemas, Python feature modules and regression tests, excluding persistence and dispatch from this slice

## Outcome

Factory gains closed, deterministic offline result envelopes and a fail-closed sanitizer foundation. Every real runtime result channel remains explicitly unavailable until a later qualified adapter wires pre-model interception.

## Scope

### In scope

- Add result envelope and channel-qualification schemas, semantic contracts and offline broker.
- Repair source hazards: structured secret leakage, duplicate JSON keys, invalid limits, unbounded empty chunks and oversized pre-copy buffering.
- Register the additive contracts/modules in architecture and inventory tests without redefining frozen predecessor pins.

### Out of scope

- Runtime interception, task admission, model dispatch, persistence, migrations, API/outbox and live adapter qualification.
- Full F25/U3/U6 or BB-R08 acceptance claims.

## Constraints

- Backward compatibility: additive sidecars; existing contract bytes/meaning remain unchanged.
- Data/privacy: no raw rejected payload or exception diagnostics may escape.
- Performance: bounded bytes, chunks, records and nesting; no network or paid model call.
- Operational: stacked on PR232; no runtime activation or deployment.
