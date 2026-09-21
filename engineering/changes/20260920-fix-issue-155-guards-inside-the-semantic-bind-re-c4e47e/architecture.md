# Architecture — Fix issue #155: semantic_bind_repair_child guard rejections and PostgreSQL tier determinism

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`bind_repair_child(digest, payload)` issued `SELECT factory.semantic_bind_repair_child(%s,%s)` and passed whatever came back straight into `RepairChildTaskBindingV1.from_dict`. The SQL function signalled *every* refusal — wrong isolation level, malformed payload, proposal not pending, missing parent, superseded child, binding conflict, child already bound, 30 lineage mismatches, stale authority, exceeded deadline, exceeded limits, and the exception arm — by returning a bare `NULL`. One value therefore carried a dozen distinct meanings, and the Python side could only misread it as a shape error.

Two fixture clocks sat on the wrong side of the same boundary: the repair-child fixture compared a server-assigned `deadline_at` against a client clock captured before several connection setups, and the HTTP intake fixture stamped `m0_authority.observed_at` from a module-import clock while the API compared it against the request clock.

## Proposed behavior

The function keeps its signature `(char,text) → jsonb` and returns one of exactly two shapes:

- a binding document (four keys), or
- `{"repair_child_rejection": "<reason>"}` — a one-key envelope naming the guard that refused.

`store.bind_repair_child` now asks `semantic_repair.repair_child_rejection_reason()` first. If the document is exactly that envelope, the reason is folded through a closed allowlist and reported as `StoreError("semantic repair child binding rejected: <reason>")`. A document that is neither keeps the old diagnosis chain, so a genuinely malformed payload is reported as `semantic repair child binding payload is malformed` (with `invalid_object`/`unknown_fields` as the nested contract code), and a bare SQL `NULL` — only possible on a schema that never applied `021` — is reported as `store_returned_null` rather than as a shape defect. Nine guard paths produce twelve reasons because the 49-clause (48-`OR`) block is partitioned into four contiguous named groups (`lineage_mismatch`, `authority_not_fresh`, `deadline_exceeded`, `child_limits_exceeded`).

Fixtures stop reading the wrong clock: the repair-child deadline budget derives from one server-clock reading (injectable via `intake_now=`) minus `CHILD_DEADLINE_SAFETY_SECONDS = 120`, and the HTTP intake proof is stamped when the request is built.

## Components and boundaries

| component | responsibility | does not |
| --- | --- | --- |
| `resources/021_semantic_repair_child_rejection_reasons.sql` | decide *which* guard refused, at the SQL boundary, in the same transaction as the write | define the public vocabulary |
| `semantic_repair.py` | own the closed reason allowlist and the strict envelope reader; fold the unknown | accept any extra key or non-envelope document |
| `store.py:bind_repair_child` | classify envelope vs binding, phrase the `StoreError` | invent reasons |
| `test_postgres_integration.py` / tier tests | pin reason ↔ guard mapping, clause equivalence, clock independence | relax a window or timeout |

The boundary rule: SQL names the guard, Python owns the vocabulary. Neither trusts the other to stay in sync, and `test_migrations.py` asserts the SQL set and the Python set are equal.

## Data flow

```
bind_repair_child(digest, payload)
  → SELECT factory.semantic_bind_repair_child(digest, payload)   -- one jsonb
      ├─ guard 1..12 fails → {"repair_child_rejection": reason}  → allowlist fold → StoreError("… rejected: reason")
      ├─ malformed doc     → from_dict → ContractError invalid_object → StoreError("… rejected")   [unchanged]
      └─ accepted          → binding(4 keys) → RepairChildTaskBindingV1.from_dict → persisted binding
```

No new table, no new function, no data rewrite; the observation and lineage reads are the ones `018` already performed.

## API and event contracts

Unchanged. The HTTP surface (`/v1/tasks` and friends), the OpenAPI document, the JSON Schema contracts and every event payload keep their current shape — this route changes a stored function's diagnostic channel and the test fixtures that drive it. `FORBID-001` pins that no `factory/contracts/`, `schemas/` or `architecture/` file was edited.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none — no governance file is in the diff.
- Applicable canonical example IDs/versions: none.
- Open or overdue debt IDs: none opened by this change. Accepted debt recorded in `requirements.md`: `semantic_plan_repair`'s identical anonymous-NULL shape.
- Expected governance handoff or receipt impact: `data_review`, `security_review`, `code_review`, `test_review` receipts plus `verification`, all bound to one final fingerprint.

## Bitrix-specific impact

- Modules/events/agents/components affected: none — this is not a Bitrix route in substance.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: PostgreSQL migration `021` applies automatically through `PostgresMigrator.apply()`; uninstall is unchanged (no new object).
- Core modification: forbidden unless explicitly approved. Not applicable and not done.

## Decisions

1. **One-key JSON envelope, not distinct SQLSTATEs.** The function's declared return type is `jsonb`, callers already consume JSON, and a SQLSTATE channel would have to survive psycopg exception mapping plus a new privilege/error surface. The envelope cannot collide with a binding because the payload guard already requires exactly four keys.
2. **Follow the shape #154 actually shipped, not the names the brief invented.** `DraftRejection`/`WorkerRejection` do not exist in this tree (`grep` returns nothing; `git show f12807c` touched only `landing_http.py` and landing tests). The real precedent is `_DRAFT_FAILURE_REASONS` + `_draft_failure_reason()` — a fixed internal→public dict that folds the unknown — reused here as `REPAIR_CHILD_REJECTIONS` with `UNKNOWN_REPAIR_CHILD_REJECTION = "binding_rejected"`.
3. **Reason names extend the existing semantic vocabulary**, matching `ESCALATION_REASONS` style (`authority_not_fresh` beside `context_not_fresh`, `deadline_exceeded` beside `deadline_exhausted`).
4. **First matching guard wins** for a multi-violation row; scenario tests pin the specific reason per case.
5. **`store_write_rejected` stays coarse** (six constraint classes) rather than splitting the `EXCEPTION` arm; named for review.
6. **Bounded scope expansion, recorded:** the HTTP intake clock coupling is fixed in this route because the mandatory tier cannot pass otherwise. Fixture-only, precedent-following, plus a new assertion that an expired proof is still refused (`FORBID-002` guard against "make it green by weakening the gate").
7. **`store_returned_null` is a Python-side diagnostic, not a thirteenth SQL reason.** A NULL response can only come from a schema that has not applied `021`; naming it inside the SQL allowlist would imply the function can emit it, which it cannot. It is asserted offline against a mocked connection so the false "malformed payload" diagnosis cannot return.
8. **Counts derived, not bumped:** every `20` that meant "current" now derives from `discover_migrations()`; the two places that assert a fixed prefix pin `21` explicitly.

## Risks and mitigations

| risk | mitigation |
| --- | --- |
| Re-grouping the 49-clause `OR` block changes which rows are rejected | accepted that a multi-violation row's *reason* depends on group order; equivalence of accept/reject argued structurally and pinned by a clause-text equality test in `test_migrations.py` (`FORBID-003`) |
| A folded reason hides a new guard | SQL/Python allowlist equality is asserted; an unknown reason folds to a fixed code rather than passing through |
| Migration `021` fails on an existing cluster | verified live on a cluster with `001-020` applied; `apply()` runs it under `pg_advisory_xact_lock` inside 5 s |
| Privilege drift | signature unchanged, `REVOKE`/`GRANT` repeated on the same signature, `pg_proc` matrix assertion still green |
| 120 s child-budget margin too loose/tight | every remaining fixture round trip is capped by the store's 5 s timeouts, and the parent horizon is 14 400 s; arithmetic is left for review, not the constant |
| The mandatory harness now derives its readiness pin from `discover_migrations()` | disclosed as a review target: the evidence depends on the resource count instead of pinning it |
| Request-time authority stamping could mask a real expiry bug | the same test asserts 422 `stale_m0` for a 400 s-old proof |
