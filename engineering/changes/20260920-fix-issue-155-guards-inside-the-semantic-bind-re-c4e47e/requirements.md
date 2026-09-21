# Requirements — Fix issue #155: semantic_bind_repair_child guard rejections and PostgreSQL tier determinism

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] **AC-001** Every NULL-returning guard path returns a machine-readable reason, and `bind_repair_child` names that reason in its `StoreError` (`semantic repair child binding rejected: authority_not_fresh`) instead of a bare shape error.
- [x] **AC-002** `invalid_object` stays reserved for genuinely malformed payloads: the rejection reader accepts a document only when it is *exactly* the one-key envelope, so anything else still reaches `from_dict`.
- [x] **AC-003** Shipped history stays immutable — `018` byte-untouched, the redefinition ships as `021_semantic_repair_child_rejection_reasons.sql`, and a cluster that already applied `001-020` upgrades with no drift error (verified live).
- [x] **AC-004** Both wall-clock couplings are gone: the repair-child binding survives an injected 2 s scheduling delay inside its intake window, and the HTTP intake authority is stamped at request time.
- [ ] **AC-005** Four consecutive mandatory disposable-exit tier passes on the delivered tree, each attempt recorded with duration and loadavg. Left unticked deliberately: this criterion is closed by the `verification` receipt, which can only be taken after the final commit.
- [x] **AC-006** Every reviewer-visible claim is a measurement from this host — including the guard enumeration that corrects the issue's "~15 guards" estimate to 9 NULL-returning paths, 70 guard clauses, one 49-clause `OR` block.

## Failure and edge cases

- A document that is neither a binding nor the exact envelope must keep the `invalid_object` diagnosis and must not fold into `binding_rejected`.
- An unknown reason arriving from SQL must fold to the fixed local code `binding_rejected`; it must never be echoed into exception text.
- A negative authority age (proof stamped in the future) and an age beyond 300 s must both still be refused with `stale_m0`. Request-time stamping must not become a route to accepting an expired proof.
- A row violating several guards reports the first matching guard's reason — a deliberate precedence choice, reviewable, not incidental.
- `store_write_rejected` still collapses six constraint classes into one reason; it is coarser than the guard groups and is named as a review target rather than quietly split.
- A cluster whose schema predates resource 021 can still answer with a bare SQL NULL. `bind_repair_child` reports that as `store_returned_null` — a store-side diagnostic, deliberately NOT part of the twelve-code SQL vocabulary, so a not-yet-migrated database is never described as having a malformed payload.
- Tests that pinned `20` applied migrations must derive from `discover_migrations()` where the number only ever meant "current", and stay pinned where the test asserts a fixed prefix.
- Cancellation inside the disposable tier still owns its container lifecycle (issue #128 is separate and unfixed here).

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none asserted — this route changes no `governance/` file and no declared contract; `git diff --numstat` over `governance/`, `factory/contracts/`, `schemas/` and `architecture/` returns zero.
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: accepted debt — `semantic_plan_repair` keeps the same anonymous-NULL shape and is filed as its own issue; the route deliberately does not fold that fix in.

## Non-functional requirements

- Security: closed allowlist of local reason codes; no external or row-derived text in diagnostics; no new SQL function, view, type or privilege surface — the signature and grant set are unchanged.
- Reliability: the mandatory PostgreSQL evidence tier must be deterministic on a loaded host without relaxing any timeout, window, or gate.
- Performance: no query-plan impact — the replacement adds no table access; the same 49 comparisons in that block run, re-grouped into named blocks.
- Observability: `SIG-001` (a named reason present in every bind rejection) and `SIG-002` (per-attempt duration and loadavg of the mandatory tier, with the product-tree fingerprint stamped around the streak) in `change-spec.yaml`.
