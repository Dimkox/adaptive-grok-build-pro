# Acceptance criteria

Reconstruct approved M7.1 durable evidence lookup in factory, additive migration026(current max+1), four mandatory CR001/TR001/SEC001/SEC002 repairs, repository-qualified append-only identities, bounded queries and disposable local PostgreSQL upgrade/restart/privilege/Unicode controls. Preserve001-025. No live DB, provider calls, or operational activation.

factory/tests/test_shadow_lookup.py and test_shadow_lookup_postgres.py; migration/restart/disposable M7 runner tests. Canonical digest/body/selector corruption and latest-row no-fallback; NFC and decomposed SQL; tenant/repository/role isolation; index EXPLAIN, bounds, checksum drift and privilege refusal.

Source rollback uses a PR revert; additive database recovery retains durable rows and forward migration. Local evidence never authorizes protected merge or live rollout.


## Mandatory source and disposable-fixture bindings

Register only m7_preflight.py, shadow_lookup.py and shadow_sources.py under the existing Factory control architecture owner; retain rules, edges and generated-view semantics. Add the corresponding exact additive module-inventory expectation in tests/test_architecture_model.py only if required by its binding assertion. Repair legacy synthetic PostgreSQL test setup to truncate the new M7 foreign-key dependent tables explicitly with the old table set, and bind M7 restart/preflight fixture checks to the exact named disposable database identity supplied by the mandatory exit runner. Production refusal, existing time/lock budgets, migrations001-025 and deployed state remain unchanged. Reproduce the original architecture and legacy/new mixed PostgreSQL fixture failures before repair; run focused legacy and M7 integration controls on the actual runner fixture. No broad CASCADE cleanup or live database operation is authorized.
