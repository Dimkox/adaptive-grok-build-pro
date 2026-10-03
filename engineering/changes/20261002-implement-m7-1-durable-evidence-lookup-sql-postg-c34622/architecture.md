# Bounded design

factory/src/adaptive_factory/shadow_lookup.py; shadow_sources.py; m7_preflight.py; store.py; admin.py; resources/026_m7_durable_evidence.sql; factory/contracts/jsonschema/m7-durable-lookup.v1.schema.json; focused unit/PostgreSQL/restart/upgrade tests; necessary interface and installer bindings.

Reconstruct approved M7.1 durable evidence lookup in factory, additive migration026(current max+1), four mandatory CR001/TR001/SEC001/SEC002 repairs, repository-qualified append-only identities, bounded queries and disposable local PostgreSQL upgrade/restart/privilege/Unicode controls. Preserve001-025. No live DB, provider calls, or operational activation.

Use existing runtime/storage/API boundaries, no new service/framework/provider dependency. Each accepted identity is exact and validated using current authorized source/public material. Concurrent mutation, unavailable sources and corrupted binding fail closed; lookup never confers execution or merge authority.


## Mandatory source and disposable-fixture bindings

Register only m7_preflight.py, shadow_lookup.py and shadow_sources.py under the existing Factory control architecture owner; retain rules, edges and generated-view semantics. Add the corresponding exact additive module-inventory expectation in tests/test_architecture_model.py only if required by its binding assertion. Repair legacy synthetic PostgreSQL test setup to truncate the new M7 foreign-key dependent tables explicitly with the old table set, and bind M7 restart/preflight fixture checks to the exact named disposable database identity supplied by the mandatory exit runner. Production refusal, existing time/lock budgets, migrations001-025 and deployed state remain unchanged. Reproduce the original architecture and legacy/new mixed PostgreSQL fixture failures before repair; run focused legacy and M7 integration controls on the actual runner fixture. No broad CASCADE cleanup or live database operation is authorized.
