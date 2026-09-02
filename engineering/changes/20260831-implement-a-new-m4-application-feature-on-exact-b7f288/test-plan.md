# Test plan — M4 Durable Factory Task Control Plane

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | competing claims, 20/10/1 capacity, expiry/reclaim and late fence rejection | real disposable PostgreSQL |
| P0 | role/schema separation; runtime cannot mutate audit or access Trust CI | migration/privilege integration |
| P0 | socket auth, scope/resource isolation, bounds/redaction and absent execution endpoints | API/contract tests |
| P0 | exact fixed metrics inventory and behavior for intake/queue/transitions, leases/fences, capacity/budget, retry/dead, kills, reconciliation/repair and every final 401/403 | unit + real disposable PostgreSQL API |
| P0 | runtime generic metric DML/function denial; fixed capability saturation/concurrency; one-row snapshot consistency, constant plan and bounded lock timeout | real disposable PostgreSQL role/concurrency/plan tests |
| P0 | stale-fence metric lock/error preserves the original prompt `409 stale_fence`; schema-008 upgrade ignores forged legacy counters and replays idempotently | unit + real disposable PostgreSQL upgrade/API tests |
| P0 | every runtime connection/read/mutation/readiness path is bounded and maps availability consistently; cancel authorization/replay/projection uses one transaction | real disposable PostgreSQL API connection/query contention |
| P0 | tracked candidate ZIP exactly equals current included-source inventory, embedded manifest and per-member bytes; stale same-version archives fail | package regression + sidecar/archive verification |
| P1 | duplicate intake and changed-authority supersession | service/PostgreSQL tests |
| P1 | accepted infrastructure retry limits 0/1/2 persist and allow exactly 1/2/3 total attempts on release, reconciliation and restart; other failures never retry | state/store/real PostgreSQL restart tests |
| P1 | schema-12 retry rows already exhausted under backfilled limits 0/1 terminalize once with mandatory event and hash-chained audit, no fence/lease and idempotent command replay | real PostgreSQL 12→13 upgrade tests |
| P1 | budget/accounting and kill switches stop claims | service/PostgreSQL tests |
| P1 | repeated restart reconciliation repairs exactly once | PostgreSQL restart probe |

TDD sequence: contracts -> state -> migrations -> intake -> leases/capacity/fences -> retry/budgets/kills/reconcile -> API/CLI -> architecture/tooling/docs. Each production behavior begins with an observed failing test. Root verification runs after final product changes. Review agents run separately after implementation; the write owner does not self-review.

Only `FACTORY_TEST_DATABASE_URL` pointing at a freshly created disposable database, or the package's fresh disposable Compose project, may be used. Never inspect `.env`, inherit Trust CI URLs, or clean an unverified target.
