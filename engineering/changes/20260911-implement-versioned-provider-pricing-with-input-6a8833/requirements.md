# Requirements — Implement versioned provider pricing with input, output, reasoning, cached-input and cache-write token accounting plus deterministic cost calculation and durable usage storage.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Given ..., when ..., then ...

## Failure and edge cases

-

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security:
- Reliability:
- Performance:
- Observability:
# Acceptance

- V1 usage payloads and their stored facts remain unchanged.
- V2 usage has five mutually-exclusive nonnegative token buckets and a
  digest-bound closed price table; the broker derives micro-USD cost.
- Invalid table shape/digest, overflow, or component-aware replay mismatch
  fails closed without durable mutation.
- A forward-only migration stores V2 component detail without rewriting
  historical observations.
