# Reject unsatisfiable expectation-set members in typed specs at plan time

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260925-reject-unsatisfiable-expectation-set-members-in-113055`
Created: 2026-09-25T00:13:54+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Validate declared expectation sets in typed change specs so an unsatisfiable member is rejected at plan time (issue 202)

## Outcome

A typed specification that declares an exact set of expected outcomes is refused while it is still a plan
unless every declared member carries a liveness proof, and the refusal names the member and says why. An
author who cannot produce such a proof for a member takes the documented third door — declare the set as an
upper bound and assert non-emptiness — instead of waiting for an implementer to discover the deadweight and
then either deviate from typed authority or break a higher rule to satisfy the literal text.

## Scope

### In scope

- `expectation_set_findings` in `.grok-stack/adaptive_grok/spec.py`, applied to all three criterion
  collections in both the draft and the gate profile.
- Exact-set obligation: every declared member must be named by `test` evidence of the same criterion.
- Upper-bound obligation: non-emptiness must be asserted, otherwise the criterion is unfalsifiable.
- False-positive control: placeholder, numeric, single-character, empty and JSON brace groups are not sets.
- One new test module `tests/test_spec_expectation_sets.py`, plus the obligation text in
  `.grok-stack/templates/change/requirements.md` and the `criterion` description in
  `schemas/change-spec.schema.json`.

### Out of scope

- Issue #202 proposal item 2 (require the referenced detector's read-path at the scope gate): that gate lives
  in `.grok-stack/adaptive_grok/verification_scope.py`, owned by another contour in flight.
- Issue #202 proposal item 3 (producer-output fixture for universal-literal contract rules): measured against
  this tree, the prose form of that rule newly rejects 9 criteria across 9 historical packages, which the
  contract forbids — historical evidence is not rewritten to satisfy a new rule.
- Any edit to `verification.py`, `receipts.py`, `criterion_coverage`, the attestation coverage projection,
  `trust-ci/**`, or the deployed holdout.

## Constraints

- Backward compatibility: the document shape is frozen. The independent holdout accepts a criterion containing
  exactly `id`, `statement` and `evidence`, so the obligation rides on existing prose and existing evidence
  kinds rather than a new field; a new field would make a spec locally valid and externally rejectable. All
  106 recorded packages must return byte-identical validator errors before and after the change.
- Data/privacy: no new I/O, no credentials, no network. The check reads only the already-bounded spec document.
- Performance: a linear scan over criterion statements already capped at 4096 characters each and 500 criteria
  per collection, with no additional filesystem access.
- Operational: findings surface through the existing `change-spec-invalid` verifier finding; no new receipt
  kind, no migration, no flag. Reverting the rule restores the previous behavior exactly.

## Verification

- `python3 -m unittest tests.test_spec_expectation_sets -q`
- `python3 scripts/grok_spec.py validate engineering/changes/20260925-reject-unsatisfiable-expectation-set-members-in-113055/change-spec.yaml --gate --json`
- `python3 -m ruff check .grok-stack/adaptive_grok scripts tests`
- `python3 scripts/grok_verify.py --mode pr`
