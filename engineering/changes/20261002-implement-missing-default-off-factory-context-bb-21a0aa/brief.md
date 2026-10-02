# Implement missing default-off factory context BB contracts rotator registry hardened VibeVM store and Linux setup manager source contours with tests while preserving migrations 023 through 025

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20261002-implement-missing-default-off-factory-context-bb-21a0aa`
Created: 2026-10-02T13:22:37+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Implement missing default-off factory context BB contracts rotator registry hardened VibeVM store and Linux setup manager source contours with tests while preserving migrations 023 through 025

## Outcome

The 2.1.0 source tree contains bounded U5/U6 contracts and deterministic stores plus an opt-in Linux/offline setup path. All new provider-facing behavior stays default-off and unqualified.

## Scope

### In scope

- BB contracts, prediction contracts, FPF snapshot, pinned rotator registry, VibeVM store, Linux setup/runtime, offline builder, installer ownership, architecture, tests, and release truth.

### Out of scope

- U4/macOS, live provider execution, qualification, migration changes, activation, merge, tag, publication, and deployment.

## Constraints

- Backward compatibility: migrations 023-025 remain byte-identical; additions are default-off.
- Data/privacy: no live provider or production data.
- Performance: deterministic bounded local operations.
- Operational: Linux-only opt-in setup; no implicit daemon or credential authority.
