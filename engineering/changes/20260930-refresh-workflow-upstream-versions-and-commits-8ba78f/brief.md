# Refresh workflow upstream versions and commits

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260930-refresh-workflow-upstream-versions-and-commits-8ba78f`
Created: 2026-09-30T19:12:50+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Реализовать новые advisory workflow source pins и parser samples для Superpowers 6.4.2, BMAD current main и Spec Kit 1.0.13 с exact upstream commit provenance и обратным чтением старых документов

## Outcome

Workflow-source metadata and named parser samples are current for Superpowers 6.4.2, BMAD 6.12.0 plus observed main, and Spec Kit 1.0.13 plus observed main, without making upstream documents authoritative or install targets.

## Scope

### In scope

- Stable release tag, peeled commit, main-head observation, and date for all three sources.
- README/config/test lockstep and exact-revision parser samples.
- Backward parsing of previously supported documents.

### Out of scope

- Installing or vendoring upstream frameworks.
- Treating floating main as a stable release or runtime authority.
- Route, approval, receipt, governance, or merge authority from imported documents.

## Constraints

- Backward compatibility:
- Data/privacy:
- Performance:
- Operational:
