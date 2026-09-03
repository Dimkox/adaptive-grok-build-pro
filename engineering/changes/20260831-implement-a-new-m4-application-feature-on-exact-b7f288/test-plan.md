# Test plan — M4 Durable Factory Task Control Plane

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | competing claims, 20/10/1 capacity, expiry/reclaim and late fence rejection | real disposable PostgreSQL |
| P0 | role/schema separation; runtime cannot mutate audit or access Trust CI | migration/privilege integration |
| P0 | socket auth, scope/resource isolation, bounds/redaction and absent execution endpoints | API/contract tests |
| P0 | checked OpenAPI is the sole HTTP contract, contains exactly 17 stable operations with closed inline schemas/headers/statuses, and runtime `/openapi.json` is absent | API/contract + architecture compatibility tests |
| P0 | every declared success/error is correlated, normalized errors retain bounded code/detail and 401 retains `WWW-Authenticate`; body limits apply only to body-bearing methods | API tests |
| P0 | exact fixed metrics inventory and behavior for intake/queue/transitions, leases/fences, capacity/budget, retry/dead, kills, reconciliation/repair and every final 401/403 | unit + real disposable PostgreSQL API |
| P0 | runtime generic metric DML/function denial; fixed capability saturation/concurrency; one-row snapshot consistency, constant plan and bounded lock timeout | real disposable PostgreSQL role/concurrency/plan tests |
| P0 | stale-fence metric lock/error preserves the original prompt `409 stale_fence`; schema-008 upgrade ignores forged legacy counters and replays idempotently | unit + real disposable PostgreSQL upgrade/API tests |
| P0 | every runtime connection/read/mutation/readiness path is bounded and maps availability consistently; cancel authorization/replay/projection uses one transaction | real disposable PostgreSQL API connection/query contention |
| P0 | cancellation and supersession racing reservation preserve unresolved evidence, release capacity exactly once, mark accounting quarantine and replay idempotently | real disposable PostgreSQL reader/writer race matrix |
| P0 | deadline-crossing live leases and expired queued/retry tasks terminalize without page starvation; clean work becomes dead, unresolved accounting becomes needs-human/quarantined and late grants remain stale | real disposable PostgreSQL reconciliation |
| P0 | reconciliation has one deterministic five-second operation deadline; statement timeout preserves committed candidate progress while PostgreSQL 17 transaction timeout rolls back the partial batch | real disposable PostgreSQL timeout injection |
| P0 | exact restored M2, aggregate and nested factory budgets remain finite error rules; overlaps evaluate independently, combined scopes cannot evade parents/union, prefix siblings do not match and unknown line statistics fail closed | architecture model + real fitness evaluator tests |
| P0 | the approved budget-only amendment preserves exact factory/source/contract/test/migration tree and blob identities plus migrations `001`-`013` checksums | exact Git objects + migration manifest verification |
| P0 | tracked candidate ZIP exactly equals current included-source inventory, embedded manifest and per-member bytes; stale same-version archives fail | package regression + sidecar/archive verification |
| P1 | duplicate intake and changed-authority supersession | service/PostgreSQL tests |
| P1 | complete intent digest remains opaque packet identity; semantic work identity excludes request ID/full M0 proof; namespaced command replay deduplicates refreshed proof and conflicts on same-request changed body | contract + real PostgreSQL HTTP tests |
| P1 | intake transports the real correlation header into durable command/audit rows without changing intent/work identity | real disposable PostgreSQL HTTP tests |
| P1 | immutable task/run/attempt/event projections and closed event metadata survive bounded pagination/lookahead validation | model/API + real disposable PostgreSQL tests |
| P1 | accepted infrastructure retry limits 0/1/2 persist and allow exactly 1/2/3 total attempts on release, reconciliation and restart; other failures never retry | state/store/real PostgreSQL restart tests |
| P1 | schema-12 retry rows already exhausted under backfilled limits 0/1 terminalize once with mandatory event and hash-chained audit, no fence/lease and idempotent command replay | real PostgreSQL 12→13 upgrade tests |
| P1 | budget/accounting and kill switches stop claims | service/PostgreSQL tests |
| P1 | repeated restart reconciliation repairs exactly once | PostgreSQL restart probe |

TDD sequence: contracts -> state -> migrations -> intake -> leases/capacity/fences -> retry/budgets/kills/reconcile -> API/CLI -> architecture/tooling/docs. The approved budget amendment separately begins with an observed six-test RED against the old widened rule, then changes only the repository rule before documentation. Each production behavior begins with an observed failing test. Root verification runs after final product changes. Review agents run separately after implementation; the write owner does not self-review.

Only `FACTORY_TEST_DATABASE_URL` pointing at a freshly created disposable PostgreSQL 17 database, or the package's fresh disposable Compose project, may be used. This repair candidate bootstraps fresh schema `013` only; an older unaccepted candidate database is preserved solely as a killed comparison database and is never upgraded in place. Never inspect `.env`, inherit Trust CI URLs, or clean an unverified target.
