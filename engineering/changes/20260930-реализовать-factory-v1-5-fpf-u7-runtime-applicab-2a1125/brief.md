# Реализовать Factory v1.5 FPF U7 runtime: applicability selector, progressive dependency-complete reader, context budgeter, URI resolver, semantic projection, decision invalidation, adapter, offline snapshots, security boundary, A/B/C evaluation, upgrade fallback and deterministic tests

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260930-реализовать-factory-v1-5-fpf-u7-runtime-applicab-2a1125`
Created: 2026-09-30T19:41:02+00:00
Risk: high
Complexity: high-risk
Domains: security, api

## Problem

Реализовать Factory v1.5 FPF U7 runtime: applicability selector, progressive dependency-complete reader, context budgeter, URI resolver, semantic projection, decision invalidation, adapter, offline snapshots, security boundary, A/B/C evaluation, upgrade fallback and deterministic tests

## Outcome

Factory can selectively use an admitted frozen FPF slice through a bounded,
offline, data-only path while native execution and project authority remain intact.

## Scope

### In scope

- AC95-AC113 source mechanisms: selector, reader, resolver, budget, projection,
  evidence/handoff, adapter matrix, replay, security, A/B/C and fallback.

### Out of scope

- Upstream installation/licensing, live provider work, production activation,
  network/process hooks and AC114 live qualification.

## Constraints

- Backward compatibility: additive module; existing contracts unchanged.
- Data/privacy: exact tenant and snapshot binding; no authority from reference data.
- Performance: finite byte/read/depth/transition/model-window limits.
- Operational: optional/default-off; frozen upgrades, never self-update.
