# Test plan — M4 Durable Factory Task Control Plane

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | competing claims, 20/10/1 capacity, expiry/reclaim and late fence rejection | real disposable PostgreSQL |
| P0 | role/schema separation; runtime cannot mutate audit or access Trust CI | migration/privilege integration |
| P0 | socket auth, scope/resource isolation, bounds/redaction and absent execution endpoints | API/contract tests |
| P1 | duplicate intake and changed-authority supersession | service/PostgreSQL tests |
| P1 | third infrastructure failure dead; other failures never retry | state/store tests |
| P1 | budget/accounting and kill switches stop claims | service/PostgreSQL tests |
| P1 | repeated restart reconciliation repairs exactly once | PostgreSQL restart probe |

TDD sequence: contracts -> state -> migrations -> intake -> leases/capacity/fences -> retry/budgets/kills/reconcile -> API/CLI -> architecture/tooling/docs. Each production behavior begins with an observed failing test. Root verification runs after final product changes. Review agents run separately after implementation; the write owner does not self-review.

Only `FACTORY_TEST_DATABASE_URL` pointing at a freshly created disposable database, or the package's fresh disposable Compose project, may be used. Never inspect `.env`, inherit Trust CI URLs, or clean an unverified target.
