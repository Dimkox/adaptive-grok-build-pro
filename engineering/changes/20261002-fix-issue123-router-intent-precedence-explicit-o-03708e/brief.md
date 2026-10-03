# Fix issue123 router intent precedence: explicit operational intent survives pull-request and review wording; exclude negated quoted and historical mentions and preserve ordinary routes.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20261002-fix-issue123-router-intent-precedence-explicit-o-03708e`
Created: 2026-10-02T22:27:55+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Fix issue123 router intent precedence: explicit operational intent survives pull-request and review wording; exclude negated quoted and historical mentions and preserve ordinary routes.

## Outcome

An explicit operational request selects the release workflow even when delivery uses a pull request or includes review/fix wording. Descriptive operational context retains the ordinary work type. Incident containment keeps priority and gains the explicit operational controls.

## Scope

### In scope

- Router intent selection and route obligation contract tests only.
- Fresh regression evidence against e5856acfd4bc7a186f40a740b54ec86459462db5, reconstructed from approved October 1 recovery design section B.

### Out of scope

- Classifier contour C, version/state changes, deployed settings, operational execution and immutable dirty source trees.

## Constraints

- Backward compatibility: retain route schema, ordinary PR/review, bugfix and incident behavior, and conservative risk/domain scanning.
- Data/privacy: local prompt processing; no external calls or secrets.
- Performance: bounded deterministic regex/clauses without a new parser, model or dependency.
- Operational: classification is evidence only; existing approval boundaries remain mandatory.
