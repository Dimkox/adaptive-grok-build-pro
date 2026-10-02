# PR3c route-selected analysis summary

All six analyses were read-only against base `d2230d59e29b5b6a843d0565ce4b6f339734ea88` and source `efc003f5787765da75a2af43de39cc02f2c4e977`.

- `repo_explorer`: source is a five-file `+577/-6` delta; migration/store apply mechanically, both main test files conflict. Direct cherry-pick is unsafe because its SQL under-validates the hardened V2 contract and it lacks a real PostgreSQL restart test.
- `task_analyst`: order is red tests, additive migration, store, service/API activation, real-PG verification. Exact committed replay precedes live-authority validation; new admissions remain fenced.
- `architect`: store owns the transaction, SQL owns final current-run authority, service owns actor/repository/grant checks. Outbox schema stays empty; rollback is endpoint disable plus forward corrective migration.
- `docs_researcher`: this slice supports F06/F11/F17 and AC14/15/24/27/82 only in its bounded result-admission aspect. It does not claim dispatch, delivery, live interception, BB qualification, U3 completion, or U4/macOS readiness.
- `data_architect`: bind reads by repository + task + digest; test real restart, rollback, concurrency, authority, privileges, and zero outbox. Do not drop evidence tables after use.
- `integration_architect`: preserve PR234 parsing/auth/correlation seams; update OpenAPI for real 200/404/409 behavior and retain 503 only for backend unavailability.

Decision: adapt rather than cherry-pick. Correct the tenant-read and SQL-validation gaps, retain all seven unavailable qualification flags, and introduce no dispatcher or live interception.
