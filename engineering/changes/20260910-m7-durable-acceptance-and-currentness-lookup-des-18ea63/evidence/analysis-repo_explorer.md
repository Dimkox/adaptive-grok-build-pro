# M7 durable evidence lookup: repository trace

Route `18ea639b9d02`; base `64378d28c7b78cace463d96470c1898294b8f196`.
Design exploration only. No product edits, test execution, service calls or database access.

## Persisted producer material

- M4 accepted intents and tasks exist in `factory/src/adaptive_factory/resources/001_initial.sql:19` and `:38`; repository/source/generation, intent/packet identity, accounting and task state are durable. “Accepted intent” is intake acceptance, not delivered-business-task acceptance.
- M4 runs/attempts are in `factory/src/adaptive_factory/resources/002_runs_leases_capacity.sql:1`; ownership, writer role, task/run/fence and attempt outcomes are durable.
- Bounded history readers are `factory/src/adaptive_factory/store.py:2348` (`list_task_runs`) and `:2423` (`list_task_events`), exposed with authorization by `factory/src/adaptive_factory/service.py:380` and `:391`.
- M5 canonical packets/manifests/proposals/results begin at `factory/src/adaptive_factory/resources/014_execution_plane.sql:2`; immutable migration 015 adds canonical checks and separately privileged artifact attestation (`015_execution_canonical_persistence.sql:156`).
- M6 subjects retain repository/task/run/fence/input-head/result-head and exact producer digests in `factory/src/adaptive_factory/resources/018_semantic_validation_bridge.sql:46`; assignments/findings/coverage/verdicts follow, with verdicts at `:126`.
- The existing material lookup is `PostgresSemanticCoordinatorStore.execution_material` in `factory/src/adaptive_factory/store.py:399`, backed by SQL `semantic_execution_material` at `018_semantic_validation_bridge.sql:356`. It selects completed writer results and reparses all canonical objects (`store.py:337`). Subject/verdict lookups exist at `store.py:545` and `:646`.
- Completion clears `tasks.current_run_id/current_fence` at `015_execution_canonical_persistence.sql:1505`. New lookup must use the immutable completed run/result binding, not require a still-live lease.

## M7/M8 boundary that is missing

- `factory/src/adaptive_factory/shadow_contracts.py:428` binds the M4/M5/M6 evidence shapes together, including legacy intent versus execution packet and input versus result head identities.
- `ReadyForPrBundleV1` (`shadow_contracts.py:539`) is pure typed evidence; its only legal status is `blocked_pending_durable_lookup` (`:550`, `:588`, `:606`). No M7 bundle/outcome SQL persistence or service/store methods exist in the inspected source.
- `ShadowOutcomeV1` (`shadow_contracts.py:706`) accepts a caller-provided human evidence digest and `merged_accepted`/`not_merged` decision plus complete quality/effort metrics. Parsing validates shape and consistency (`:756`), not provenance or a durable human decision. Missing historical values must not be fabricated to fit this shape.
- `M7AutonomyBridgeV1` reparses canonical producer objects, deduplicates/sorts bundle identities and matches outcome bundle digests (`factory/src/adaptive_factory/m7_autonomy_bridge.py:95`). Its acceptance/currentness properties literally return False at `:168` and `:172`.
- M8 links task/run/result head and human-receipt digest back to bundle/outcome at `factory/src/adaptive_factory/autonomy.py:393`; it blocks on bundle status, acceptance and currentness at `:817` before any successful recommendation.
- Changing only the two booleans cannot work coherently: the canonical bundle type still permits only blocked status, and JSON-supplied availability would create authority from a caller assertion.

## Existing authority evidence is not the missing outcome

- `factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:1` stores M0 observations; migration 009 adds repository/policy binding, and migration 010 validates unrevoked identity under a share lock.
- `factory/src/adaptive_factory/store.py:1904` uses that evidence solely for intake. Runtime has SELECT, not INSERT, on these tables (`005_security_accounting_commands.sql:68`). Bootstrap exceptions are scoped to `task:intake`; neither path proves human acceptance of a delivered result.
- M0 observations lack explicit result/task/run/bundle binding, base SHA, App/check-run identity, holdout identity and expiry/current observation lineage. An input-head observation must not validate a different output head.
- Read-only external attestation retrieval already exists at `trust-ci/src/adaptive_trust_ci/api.py:162`. `AttestationPayload` at `trust-ci/src/adaptive_trust_ci/models.py:269` binds repository/PR/base/head/policy/status and signed envelope identity, but does not include human task acceptance, explicit App ID or holdout digest. Required currentness fields cannot be inferred from absent fields.

## Smallest coherent next vertical

1. Add separate closed, versioned durable lookup/observation contracts rather than weakening immutable M7 v1 bundle status or admitting caller availability flags. Keep legacy unavailable results and the L2 ceiling.
2. Persist a canonical bundle registry by verified existing task/run/result/subject/verdict identity in the existing factory PostgreSQL schema. Resolve producer bodies through their existing authoritative tables/functions and recompute exact digests.
3. Persist business-outcome observations separately from external Trust CI observations; require their approved independent writer boundary and explicit source provenance. Never reinterpret a merge, ready state, technical check or M0 intake exception as business acceptance.
4. Lookup one exact bundle/profile subject with bounded reads; compare repository, immutable completed run, result SHA, required base/policy/holdout identities, external observation lineage, expiry and revocation. Return specific missing/stale/replayed/unavailable reasons and no external authorization.
5. Exact operation replay returns the same durable record; same idempotency identity with changed body fails. Cross-run/repository/result/profile substitution and older observations overwriting newer currentness fail transactionally.
6. Deliver additive lookup/preflight only in this first slice. Preserve M7/M8/M9 v1 serialization, fixed blocked/unavailable behavior and existing authority ceilings. Any later promotion consumer needs its own explicitly approved, versioned producer/bridge integration; it is not a boolean patch.
7. Use a forward-only migration after 018, narrowly scoped roles/functions, explicit uniqueness/FKs, bounded read indexes and append-only revocation/supersession facts. No deployed trust-policy mutation or live database migration belongs to this design slice.

## Focused future verification targets

- Preserve baseline `factory/tests/test_shadow_contracts.py:353` (pure bundle blocked/no remote surface), `:224` (caller authority fields rejected), `:244` (shared identities match), `:306` (nested digest coverage), and schema inventory checks at `:375`.
- Preserve `factory/tests/test_autonomy.py:357` (recomputed producer bodies; no caller acceptance/currentness fields), exact input/result distinction at `:370`, and existing M8 missing-receipt/cohort constraints.
- Add contract/service tests for authoritative lookup versus caller assertions, unknown outcomes, cross-binding, expiry, revocation, idempotency collision and unavailable defaults. No positive acceptance fixture should serve as factual cohort evidence.
- Add database tests alongside `factory/tests/test_execution_persistence_postgres.py`: distinct privilege boundaries, atomic rollback, direct-SQL forgery rejection, persisted duplicate detection and fresh-store restart rehydration. Existing exact-replay behavior is exercised at `:3315`.
- Extend migration checks in `factory/tests/test_migrations.py:358`, `:371`, `:516`; package SQL is contiguous/checksummed via `factory/src/adaptive_factory/migrations.py:47`.
- Extend the isolated PostgreSQL restart proof (`factory/tests/postgres_restart_probe.py:1148`) only after scope approval, preserving exact-container safety. Test completed-run lookup after current lease is cleared and invalidation after authority epoch/base changes.

Memory fact: M7 bundles/outcomes are presently pure evidence values; all factual persistence beneath them stops at M4/M5/M6, and completion clears the active lease pointer. A durable lookup must join immutable completed identities and separately sourced external/human observations.
