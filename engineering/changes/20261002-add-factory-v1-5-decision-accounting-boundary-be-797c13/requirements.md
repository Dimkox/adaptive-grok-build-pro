# Requirements — Add Factory v1.5 decision accounting boundary behavior from source commit 531089f to the PR2 persistence foundation: enforce bounded cost and duration values and exact persisted accounting invariants as a new feature slice, with regression tests and isolated PR delivery

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Aggregate `2**63 - 1` succeeds; any larger aggregate raises `ContractError` naming `total_usd_micros`.
- [x] Overflow is rejected for complete and incomplete/estimated summaries even when each charge is individually valid.
- [x] Actual/estimated/unknown, duplicate, currency, pricing identity, timestamp and human-time cases run through Factory and root discovery.
- [ ] Existing decision persistence/replay/fencing tests remain green; no durable accounting claim is introduced.

## Failure and edge cases

- Boolean, negative and oversized individual values remain invalid.
- Unknown amounts remain `None`; estimated or missing expected usage prevents a complete total.
- Non-USD currency and duplicate usage identity remain fail-closed.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: no authority or external execution is introduced.
- Reliability: cumulative validation prevents later database-range mismatch.
- Performance: linear aggregation with constant-time validation.
- Observability: explicit `ContractError` field identity and dual discovery coverage.
