# Acceptance criteria

Reconstruct approved M7.1 durable evidence lookup in factory, additive migration026(current max+1), four mandatory CR001/TR001/SEC001/SEC002 repairs, repository-qualified append-only identities, bounded queries and disposable local PostgreSQL upgrade/restart/privilege/Unicode controls. Preserve001-025. No live DB, provider calls, or operational activation.

factory/tests/test_shadow_lookup.py and test_shadow_lookup_postgres.py; migration/restart/disposable M7 runner tests. Canonical digest/body/selector corruption and latest-row no-fallback; NFC and decomposed SQL; tenant/repository/role isolation; index EXPLAIN, bounds, checksum drift and privilege refusal.

Source rollback uses a PR revert; additive database recovery retains durable rows and forward migration. Local evidence never authorizes protected merge or live rollout.
