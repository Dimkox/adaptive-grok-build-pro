# Реализовать runtime U2 predictor и explainer для Factory v1.5: data assembly, bounded training/prediction pilot, versioned model artifact, SHAP-style observation-only explanation, deterministic tests; без authority effect

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260930-реализовать-runtime-u2-predictor-и-explainer-для-84d907`
Created: 2026-09-30T19:41:00+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Реализовать runtime U2 predictor и explainer для Factory v1.5: data assembly, bounded training/prediction pilot, versioned model artifact, SHAP-style observation-only explanation, deterministic tests; без authority effect

## Outcome

Factory can reproducibly assemble and qualify an offline first-check-failure pilot, then produce a versioned prediction and full additive explanation. The result is explicitly observational and cannot change workflow authority.

## Scope

### In scope

- Bounded temporal dataset assembly and label separation.
- Deterministic baseline/logistic training, model identity, and qualification metrics.
- Closed-contract prediction and additive log-odds explanation generation.
- Tests and honest not-qualified/unavailable fallback.

### Out of scope

- Model activation, online serving, policy/routing influence, causal claims, external data collection, and M8 qualification.

## Constraints

- Backward compatibility: existing v1 schemas are consumed unchanged; no existing caller is modified.
- Data/privacy: accepts bounded numeric feature snapshots and identifiers only; performs no I/O.
- Performance: 4096 examples, 32 features, and 256 iterations maximum.
- Operational: optional/offline and default-unused; failures do not block the rule-based workflow.
