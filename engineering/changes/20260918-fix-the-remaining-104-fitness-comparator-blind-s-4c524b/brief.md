# Fix the remaining #104 fitness comparator blind spot: OpenAPI contracts that reference the landing backend capability JSON Schema become unsupported when that schema changes. Extend the bounded compatibility subset to analyze the referenced composition constructs accurately, with regression coverage; do not change producer-output policy or declare new profile facts.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260918-fix-the-remaining-104-fitness-comparator-blind-s-4c524b`
Created: 2026-09-18T20:07:35+00:00
Risk: medium
Complexity: standard
Domains: api, ai

## Problem

Fix the remaining #104 fitness comparator blind spot: OpenAPI contracts that reference the landing backend capability JSON Schema become unsupported when that schema changes. Extend the bounded compatibility subset to analyze the referenced composition constructs accurately, with regression coverage; do not change producer-output policy or declare new profile facts.

## Outcome

Architecture fitness can analyze edits to the landing capability contract and its dependent OpenAPI/schema graph, producing directionally sound results for supported `anyOf` unions instead of stopping at a false unsupported verdict.

## Scope

### In scope

- `.grok-stack/adaptive_grok/architecture.py`: inventory-bounded `$defs`/JSON Pointer resolution, exact declared-ID resolution, bounded `anyOf` inclusion, and `date-time` contract metadata.
- `tests/test_architecture_model.py`: reproduction, directional, resolver, adversarial, and regression coverage.

### Out of scope

- Contract documents, profile facts, compatibility policy/rules, Trust CI deployment, and runtime behavior.

## Constraints

- Backward compatibility: existing results remain unchanged except where the analyzer currently returns unsupported for supported references/compositions; proven incompatibilities remain findings.
- Data/privacy: no data or provider input changes; reference resolution cannot access the network or undeclared files.
- Performance: existing depth and node caps remain authoritative; union pair attempts are charged to the shared budget.
- Operational: source-only analyzer change with revert rollback; no deployment or external write.
