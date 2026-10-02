# Fix PROJECT_STATE 2.1.0 release candidate identity so the new source-only candidate has no artifact hashes while preserving the immutable 2.0.19 artifact record

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20261002-fix-project-state-2-1-0-release-candidate-identi-7e4b7e`
Created: 2026-10-02T13:13:53+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Fix PROJECT_STATE 2.1.0 release candidate identity so the new source-only candidate has no artifact hashes while preserving the immutable 2.0.19 artifact record

## Outcome

`PROJECT_STATE.json` keeps the published v2.0.19 artifact immutable and records v2.1.0 only as a source candidate with no artifact, PR, merge, or check claims.

## Scope

### In scope

- Published v2.0.19 identity and source-only v2.1.0 candidate fields.

### Out of scope

- Product runtime, release publication, artifact generation, merge, tag, and deployment.

## Constraints

- Backward compatibility: do not rewrite the published v2.0.19 record.
- Data/privacy: state/documentation only.
- Performance: no runtime effect.
- Operational: candidate claims remain evidence-bound and source-only.
