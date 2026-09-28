# Requirements — {{TITLE}}

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Given ..., when ..., then ...

A criterion that declares a set of expected outcomes must stay falsifiable and
achievable. Naming an exact set — `the cutover reds are exactly {key-a, key-b}` —
obliges a per-member executable liveness probe: the same criterion must reference
one repository-contained `unittest.TestCase` selector whose AST calls
`exercise_expectation_member("key-a", observe=…, mutate=…, undo=…)`. The validator
resolves this structure without importing the test; the ordinary test run proves
the member absent before mutation, present after mutation, and fully restored by
undo. A member no detector can produce cannot be proven that way, so declare the
set as an upper bound (`observed ⊆ {…}`) and assert non-emptiness. Quantifier cues
apply only to their brace group's sentence.

## Failure and edge cases

- 

## Governance context

{{GOVERNANCE_AUTHORITY_NOTICE}}

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security:
- Reliability:
- Performance:
- Observability:
