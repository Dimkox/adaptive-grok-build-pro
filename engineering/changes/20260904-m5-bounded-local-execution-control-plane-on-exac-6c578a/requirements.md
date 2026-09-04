# Requirements — M5 bounded local execution control plane on exact M4 67dc4dd

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] `AC-001` — Preserve migrations `001`-`013`, the exact 17-operation M4 control contract, and every M4 identity, authorization, state, fence, capacity, budget, accounting, history, retry, reconciliation, deadline, and kill-switch invariant.
- [ ] `AC-002` — Prove transactional fresh and schema-13 upgrade through migrations `014`-`017` on disposable PostgreSQL 17, including checksum, role, timeout, canonicalization, and failure-atomicity guards.
- [ ] `AC-003` — Persist one immutable task packet and manifest per live grant, with separate domain digests bound to exact server-owned authority and conflicting replay denied.
- [ ] `AC-004` — Project exact-version fixture input through closed, bounded, offline adapters; reject malformed, unknown, oversized, mismatched, private, ineligible, and post-terminal data with no executable or network path.
- [ ] `AC-005` — Enforce authenticated `task:execute`, repository authorization, durable role, owner, task, run, live fence, allocation, and workspace identity on every execution mutation.
- [ ] `AC-006` — Preserve M4-only startup when disabled and expose exactly six logical operations in each closed M5 v1/v2 contract only under complete injected local composition.
- [ ] `AC-007` — Persist sequential proposals and atomically finalize one trusted result plus one existing M4 disposition under a live fence.
- [ ] `AC-008` — Prove bounded, fenced, factual and idempotent recovery across two disposable PostgreSQL restarts without synthetic evidence.
- [ ] `AC-009` — Bind focused checks, final exact-head verification, and every route-selected review to one clean final tree.

## Failure and edge cases

- Checksum drift, PostgreSQL below 17, unsafe database role topology, incomplete execution composition, unknown provider/version, stale authority, conflicting idempotency replay, and unavailable or mismatched trusted evidence fail before partial durable effects.
- A review finding reopens implementation only when it demonstrates a core-flow break, authority/tenant-isolation bypass, data loss/corruption, or mandatory verifier failure. Other findings enter the bounded optimization backlog.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none currently published in `governance/rules/index.json`.
- Canonical-example deviations and evidence: none asserted; governance fitness will rederive applicability from the final diff.
- Intentional debt created, repaid, or accepted: none; deferred features are explicit non-goals rather than accepted debt.

## Non-functional requirements

- Security: server-owned selection and finalization, repository tenancy, disjoint runtime/attestor roles, closed inputs, no provider/network/credential path.
- Reliability: immutable evidence, exact replay, atomic terminalization, forward-only migrations, bounded factual recovery.
- Performance: bounded payloads, proposal counts, keyset recovery pages, claim durations, statement/lock timeouts, and fixed-cardinality metrics.
- Observability: claim, terminal, recovery, cleanup, denial, retry, and quarantine outcomes are distinguishable without sensitive payloads.
