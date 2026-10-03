# Approved source reconstruction — f-evidence

Change 20261002-implement-m7-1-durable-evidence-lookup-sql-postg-c34622. Overall target2.1.1with heartbeat/watchdog. Owner-approved October1recovery design supplies this contour. Current explicit user instructions: full dirty-tree recovery and release2.1.1; source-only plan does not authorize production mutation.

## Scope

Reconstruct approved M7.1 durable evidence lookup in factory, additive migration026(current max+1), four mandatory CR001/TR001/SEC001/SEC002 repairs, repository-qualified append-only identities, bounded queries and disposable local PostgreSQL upgrade/restart/privilege/Unicode controls. Preserve001-025. No live DB, provider calls, or operational activation.

## Product boundaries

factory/src/adaptive_factory/shadow_lookup.py; shadow_sources.py; m7_preflight.py; store.py; admin.py; resources/026_m7_durable_evidence.sql; factory/contracts/jsonschema/m7-durable-lookup.v1.schema.json; focused unit/PostgreSQL/restart/upgrade tests; necessary interface and installer bindings.

## Baseline and compatibility

Actual main/base e5856acfd4bc7a186f40a740b54ec86459462db5. Historical RC81cb7c21 is not its ancestor; reconstruct against current source without asserting tree equivalence. Preserve current callers/defaults and all old dirty source trees; import no aggregate/evidence/old receipt.

## Frozen predecessor fixture mapping (preparation only)

Original F source `e3509dcf40e9b67e1ee6b51fbbaa208d5ba26a69`, original comparison base `63799f8760d3a55028d83ab5ff0116ececf8f7d1`, is restacked locally onto frozen core `c50e083cc7980c3bb049af0f9382721a0f957417`. Core acceptance and the actual accepted F PR base remain pending; route/base authority is unchanged. The two extracted legacy callers remain byte-identical to c50; their existing cursor's bounded installed migration-ledger version query selects schema025/026 through the test-only `postgres_fixture_reset.py` closed025/026 seam, with exactly six tables derived from immutable026 and the original025 statement preserved. `test_postgres_integration.py` remains a separate schema/fixture binding. Retain typed concurrent-refusal retries, transaction ownership, lock/time bounds, architecture preflight/fitness refusals and both installer additions. New fixture helper/version tests supplement all original F requirements; they do not replace upgrade, actual PostgreSQL/restart, Unicode, privilege, plan, full exact-base verification or five independent reviews. See integration-addendum.md for identities and pending acceptance.
