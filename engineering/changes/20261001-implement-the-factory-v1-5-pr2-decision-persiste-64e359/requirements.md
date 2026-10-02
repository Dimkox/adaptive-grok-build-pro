# Requirements — Implement the Factory v1.5 PR2 decision persistence contour on current main: transplant the five existing decision persistence commits from the isolated branch, resolve bounded API and data persistence conflicts, preserve behavior and tests, and deliver the isolated candidate

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] AC-001: closed deterministic DecisionRecordV1 has executable schema/runtime parity tests.
- [ ] AC-002: state, event, audit, command result and decision commit or roll back atomically.
- [ ] AC-003: exact replay succeeds; changed replay conflicts under serialized concurrency.
- [ ] AC-004: append-only supersession stays inside repository/task/run and records survive two restarts.
- [ ] AC-005: timing/cost helpers retain unknown/incomplete semantics without claiming durable accounting.
- [ ] AC-006: additive migration and legacy callers remain compatible; final verifier/reviews pass.

## Failure and edge cases

- Malformed, secret or foreign records, stale fences, wrong identities and unsupported sources fail closed.
- Same ID with changed digest and same request key with changed payload conflict.
- Migration 022→023 and fresh install succeed; no down-migration is attempted.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: runtime cannot directly mutate decision history; records carry no operational authority.
- Reliability: one transaction, exact replay, append-only supersession and restart persistence.
- Performance: keyed advisory locking; no unbounded scan or backfill.
- Observability: deterministic record digest and existing audit/event correlation.
