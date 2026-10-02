# Requirements — Implement durable Factory v1.5 result admission persistence

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Valid current leased-run V2 envelopes commit atomically with command replay metadata and `outbox_created=false`.
- [x] Exact command replay is stable after expiry/restart; changed command or natural-source material conflicts without overwrite.
- [x] Retrieval is bound to repository, task and digest; cross-repository requests are indistinguishable from not found.
- [x] PostgreSQL independently enforces canonical shape, authority, bounds and secret controls; runtime cannot mutate tables directly.

## Failure and edge cases

- Concurrent identical admissions create one row; competing envelopes have one winner.
- Post-result failure rolls back both result and command rows.
- Stale fence, expired lease/deadline, finished attempt and mismatched packet/actor fail closed.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: FACTORY-STATE-TRANSITION and existing execution authority rules; no governance JSON changes.
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: outbox table is deliberately dormant pending separately qualified dispatch.

## Non-functional requirements

- Security: security-definer function, closed contracts, tenant-bound reads, no raw runtime DML.
- Reliability: atomic transaction, immutable rows, exact replay, restart durability.
- Performance: bounded 1 MB payload, 64-depth/100k-record structured JSON, five-second concurrency probes.
- Observability: created/replay/conflict outcomes and zero outbox cardinality are test-visible without payload logging.
