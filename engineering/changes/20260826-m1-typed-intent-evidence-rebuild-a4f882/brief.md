# M1 Typed Intent Evidence Rebuild

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260826-m1-typed-intent-evidence-rebuild-a4f882`
Created: 2026-08-26T01:44:30+00:00
Risk: high
Complexity: high-risk
Domains: security

## Problem

Implement M1 Typed Intent and Evidence from the approved roadmap and design, including security-sensitive strict validation of untrusted specs, criterion-bound receipts, independent holdout enforcement, and backward-compatible signed Trust CI attestation metadata

## Outcome

Every standard/high-risk change has a strict machine-readable intent contract, and both local and independent evidence identify the acceptance criteria they prove.

## Scope

### In scope

- M1 Tasks 1-6 from the approved implementation plan.
- Strict canonical JSON-compatible YAML validation with bounded parsing.
- Route-driven generation, CLI, criterion-bound receipts, independent holdout checks, and Trust CI attestation metadata.
- Backward-compatible reading of unchanged historical specs and signed schema-v1 attestations.
- Root README/roadmap/current-state updates after implementation evidence is green.

### Out of scope

- M2-M9 capabilities.
- Deployment of changed Trust CI policy, holdout bundles, images, trust stores, or branch protection.
- Push, merge, release, or production mutation without their exact delegated operations and external gates.
- Mass migration of unchanged historical change packages.

## Constraints

- Backward compatibility: unchanged legacy specs remain readable; existing signed attestations remain verifiable.
- Data/privacy: specs and connector output are untrusted data; no secrets are read or logged.
- Performance: parsing is size/depth/count bounded and standard-library only.
- Operational: local verification is preflight; the App-owned exact-SHA Trust CI check remains merge authority.
