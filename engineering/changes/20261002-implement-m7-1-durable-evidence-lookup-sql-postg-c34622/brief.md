# Approved source reconstruction — f-evidence

Change 20261002-implement-m7-1-durable-evidence-lookup-sql-postg-c34622. Overall target2.1.1with heartbeat/watchdog. Owner-approved October1recovery design supplies this contour. Current explicit user instructions: full dirty-tree recovery and release2.1.1; source-only plan does not authorize production mutation.

## Scope

Reconstruct approved M7.1 durable evidence lookup in factory, additive migration026(current max+1), four mandatory CR001/TR001/SEC001/SEC002 repairs, repository-qualified append-only identities, bounded queries and disposable local PostgreSQL upgrade/restart/privilege/Unicode controls. Preserve001-025. No live DB, provider calls, or operational activation.

## Product boundaries

factory/src/adaptive_factory/shadow_lookup.py; shadow_sources.py; m7_preflight.py; store.py; admin.py; resources/026_m7_durable_evidence.sql; factory/contracts/jsonschema/m7-durable-lookup.v1.schema.json; focused unit/PostgreSQL/restart/upgrade tests; necessary interface and installer bindings.

## Baseline and compatibility

Actual main/base e5856acfd4bc7a186f40a740b54ec86459462db5. Historical RC81cb7c21 is not its ancestor; reconstruct against current source without asserting tree equivalence. Preserve current callers/defaults and all old dirty source trees; import no aggregate/evidence/old receipt.
