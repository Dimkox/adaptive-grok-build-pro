# Requirements — {{TITLE}}

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Given ..., when ..., then ...

A criterion that declares a set of expected outcomes must stay falsifiable and
achievable. Naming an exact set — `the cutover reds are exactly {key-a, key-b}` —
obliges a per-member liveness proof: the same criterion must carry `test` evidence
naming every member, i.e. a probe that actually produces it. A member no rule of
the stack can ever produce (for example one whose detector reads a frozen
historical artifact) cannot be proven that way, so declare the set as an upper
bound (`observed ⊆ {…}`) and assert non-emptiness; an upper bound without that
assertion is satisfied by an empty observation and is rejected too.

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
