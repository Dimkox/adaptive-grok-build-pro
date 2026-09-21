# Fix issue #155: guards inside the semantic_bind_repair_child PostgreSQL function return a bare NULL, so bind_repair_child cannot distinguish a deadline or precondition rejection from a malformed payload and surfaces a misleading invalid_object ContractError; the mandatory disposable-exit PostgreSQL evidence run consequently flakes about one run in three under host load. Give each guard a machine-readable rejection reason or a distinct SQLSTATE, map it to typed StoreError reason codes while keeping invalid_object for genuinely malformed payloads, keep shipped migration history immutable by replacing the function in a new versioned resource, and make the affected integration fixture independent of wall-clock scheduling. Do not weaken the contract schema, the evidence gate, or the disposable-exit run.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260920-fix-issue-155-guards-inside-the-semantic-bind-re-c4e47e`
Created: 2026-09-20T00:59:05+00:00
Risk: medium
Complexity: high-risk
Domains: data, frontend, integration, api

## Problem

`factory.semantic_bind_repair_child(char,text)` refused a repair-child bind by returning a bare SQL `NULL` from any of its nine anonymous guard paths. That NULL travelled `store.bind_repair_child` → `RepairChildTaskBindingV1.from_dict(None)` → `semantic_contracts._object`, which raised `ContractError("invalid_object", "repair_child_task_binding")`; because `ContractError` subclasses `ValueError`, the `except (TypeError, ValueError)` in `store.py` swallowed it and re-raised the anonymous `StoreError("semantic repair child binding rejected")`. A precondition refusal (expired child deadline, stale authority) was therefore reported as a data-shape defect, pointing investigators at the contract module instead of the guard that fired.

The same absence of a reason channel left the mandatory disposable-exit PostgreSQL evidence run load-sensitive: the issue record shows one of three runs red, and only the slowest one.

## Outcome

An investigator reading a bind rejection sees *which* guard refused it. Every guard path now returns one closed-set reason (`{"repair_child_rejection": "<reason>"}`) at the SQL boundary, and `bind_repair_child` names that reason in its `StoreError`. `invalid_object` is reachable only for a genuinely malformed payload. The fixtures that read wall clock through the product's own freshness windows are re-based on the clocks the product itself uses, so the mandatory tier became deterministic without touching any timeout, window, or gate.

## Scope

### In scope

- New migration resource `factory/src/adaptive_factory/resources/021_semantic_repair_child_rejection_reasons.sql`: replaces the function body with reason-bearing guards — 12 reasons over the 9 NULL-returning paths.
- `factory/src/adaptive_factory/semantic_repair.py`: closed reason allowlist plus `repair_child_rejection_reason()`.
- `factory/src/adaptive_factory/store.py`: `bind_repair_child` classifies the envelope before `from_dict`, keeping malformed payloads on their own diagnosis.
- `factory/tests/test_postgres_integration.py`: server-clock seam and `CHILD_DEADLINE_SAFETY_SECONDS` for the repair-child fixture (the issue as filed), **plus** the request-time authority stamp for the HTTP intake fixture — see *Bounded scope ruling*.
- Tier assertions that hardcoded `20` applied migrations (`test_migrations.py`, `test_execution_persistence_postgres.py`, `test_server.py`, `postgres_restart_probe.py`).

### Out of scope

- `semantic_plan_repair` keeps the identical anonymous-NULL shape (`store.py` reports `stored semantic repair result is corrupt`); tracked as a follow-up issue rather than fixed silently inside this route.
- `contracts.py` freshness policy, the 300 s authority window, the disposable-exit harness protocol, and any timeout or `statement_timeout`/`lock_timeout` value.
- Contract schemas under `factory/contracts/`, `schemas/`, `architecture/`, and all `governance/` JSON: untouched.

## Bounded scope ruling

The declared success criterion (four consecutive mandatory-tier passes) was unreachable on this host for a reason unrelated to the bind guards: `test_postgres_integration.NOW` is captured at module import while the HTTP routes call `datetime.now()` per request, so once the 776-test tier passed 300 s the intake request was refused with `stale_m0`. The first streak attempt failed exactly there (`422 != 201` at `test_postgres_integration.py:1882`), and it blocks every other delivery that owes this evidence too. The repair is a fixture-only change following the precedent already in `test_api.py:286`; it widens no window, and the same test now asserts that a genuinely 400-second-old proof is still refused with `stale_m0`. Recorded here instead of being absorbed quietly: this is a second defect inside the route's contour that the original brief did not name. Measured before/after control is in [`evidence/postgres-evidence.md`](evidence/postgres-evidence.md) §13.

## Constraints

- Backward compatibility: migration history is append-only. `plan_migrations()` never re-applies a recorded version and `apply()` compares the recorded `(version, name, sha256)` prefix, so editing `018` in place would fail every existing database with `migration drift at version N`. The redefinition therefore ships as `021`.
- Data/privacy: reasons are fixed local codes; no provider text, no row content, no customer identifiers cross the boundary.
- Performance: `CREATE OR REPLACE FUNCTION` plus `REVOKE`/`GRANT` on the same signature — no data touch, no index work, comfortably inside the runner's 5 s statement timeout.
- Operational: signature `(char,text) → jsonb` unchanged, so the `pg_proc` privilege-matrix assertions and `018`'s grants stay valid; `CREATE OR REPLACE` preserves grants and `pg_proc` cardinality.
