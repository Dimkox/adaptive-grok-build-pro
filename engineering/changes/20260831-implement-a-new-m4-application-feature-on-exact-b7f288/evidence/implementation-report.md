# M4 implementation report

## Result

M4 is implemented as a separate local `factory/` package on accepted M3 base `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`. It validates immutable M1/M2/M3/M0-bound intake, persists isolated PostgreSQL operational truth, schedules fenced bounded leases, and exposes authenticated scoped control over an explicit Unix socket. It has no provider execution, repository command, GitHub/external write, deployment, systemd, production or Trust CI authority.

## Delivered behavior

- Closed typed intake, handoff, actor, task, run, attempt and command records with canonical digests, full-frozen-intent duplicate identity, atomic supersession and bounded 4xx validation.
- Eleven contiguous checksum-locked factory migrations, repository/full-policy/action-bound transaction-serialized M0 authority, complete schema-008 unsafe-accounting quarantine, audit-v2 evidence, task-history indexes, capability-shaped capacity authority, effective least-privilege `factory_runtime` execution and no `trust_ci` privileges.
- Transactional `FOR UPDATE SKIP LOCKED` claims, monotonic per-task fences, database-time leases/deadlines and 20 global readers / 10 per repository / one writer capacity.
- Initial attempt plus two infrastructure retries, terminal dead/needs-human handling, 14,400-second and USD 25/token/output/event/repair ceilings, durable fail-closed missing accounting and idempotent usage observations.
- Global/repository kills, complete task/run/correlation-bound hash-chained audit, and capacity-before-task reconciliation capped at 100 candidates and an exact five-second transaction timeout.
- Constant-time scoped bearer authentication, actor/repository-bound worker mutations, bounded streaming bodies, durable idempotency/correlation, accounting endpoints, checked-in OpenAPI, and CLI control over Unix HTTP only.
- Runnable `adaptive-factory-server` composition that pre-binds only an owned mode-`0660` Unix socket, absolute owner-pinned no-follow actor/token ancestry, plus dependency-aware readiness and the three declared redacted metric families.
- Reproducible `adaptive-factory-admin` local bootstrap/migration interface with distinct owner/runtime DSNs, bounded `NOINHERIT` runtime login membership and effective-role readiness validation.
- Architecture model/rules/diagrams, K17 README graph, roadmap/status, installer inventory, verifier integration, release and forward-recovery documentation.

## Commits

- `6c7aa3f` — freeze accepted M4 scope and exact-base package.
- `8ca3bca` — closed factory contracts.
- `abfdcaa` — closed task state/retry policy.
- `3d395a2` — durable migration foundation.
- `149424e` — PostgreSQL store, intake, leases, capacity and reconciliation.
- `c7bdb91` — scoped local API/CLI.
- `6a75ae3` — isolated executable architecture model.
- `1924cb2` — bounded delivery/docs/installer/verifier/accounting completion.
- `39dafa4` — exact verification-gate repairs.
- `01643c6` — frozen first-round implementation evidence.
- `9bc51e8` — first-review durable invariant, authorization and executable-boundary repairs.
- `f09c113` — full frozen authority, transactional M0, audit-v2, global-scope and closed-command repairs.
- `2c6521c` — accounting recovery, fixed lock order, acceptance boundaries, credential ancestry and local rollout bootstrap.
- `bd1eed9` — executable architecture ownership for the admin interface.
- `03a1080` — frozen fix-wave implementation evidence before exit verification.
- `b820bed` — additive migration, secret fixture and PostgreSQL readiness gate repairs.
- `dfe03f3` — calendar-independent bounded authority-expiry regression fixture.
- `066520d` — frozen second residual review wave evidence.
- `70cb209` — authority serialization, schema-008 accounting quarantine and mandatory cleanup semantics.

## Independent-review remediation

The first five reviews correctly failed head `01643c6`. Regression-first repairs now atomically close leased cancel/supersede resources; isolate orphan reconciliation; settle and bound cost/token/wall accounting; require accounting before completion; preserve exact command replay; normalize CLI/API keys; bind workers and kill scopes to authenticated repository authority; require persisted M0 authority; execute under narrow database grants; and provide an actual UDS-only composition root.

The final fix wave accepted every finding in the five overwritten FAIL reports; there was no technical pushback. It now binds duplicate identity to the complete frozen intent, validates M0 repository/full-policy/action inside intake's insertion transaction, denies repo-scoped global reconciliation/metrics, closes every command input before coercion, authenticates all audit evidence fields, blocks cross-attempt unresolved accounting from retry/completion, eliminates reconcile/cancel lock reversal, and adds representative indexed-plan evidence.

The mandatory exit runner creates an exact disposable PostgreSQL 17 container, executes API and database tests under effective roles, restarts PostgreSQL, reconnects through a fresh store, proves one repair then a zero-repair replay, and removes the exact container. New acceptance cases directly exercise event/repair/deadline boundaries, repository-kill isolation, defensive 100+1 paging, the exact five-second setting, authority revocation races, real UDS authentication and shipped owner/runtime bootstrap.

The second residual wave uses forward-only migration `010` without changing applied `009`: both M0 authority forms now hold a row lock that conflicts with non-key revocation through intake commit; a real non-empty schema-008 upgrade quarantines unresolved prior-attempt accounting before claim; and mandatory release/reconcile/cancel events plus audit survive an exhausted ordinary-event budget while capacity returns exactly once.

The third residual wave leaves applied migration `010` immutable and adds forward-only migration `011`. A schema-008 blocked claimable row with zero aggregates becomes explicit `needs_human/accounting_blocked`, while a human-ready row with live prior-attempt accounting is preserved in a non-positive accounting quarantine; readiness additionally rejects any reintroduced unsafe `ready_for_human` projection.

Before PR delivery, the fourth residual wave corrects unreleased migration `011` under the explicit disposable-only exception. An unsafe older human-ready generation becomes `superseded/accounting_blocked` when a newer generation exists, retaining reservations, usage, run and audit evidence without colliding with the one-active-identity index; a lone unsafe positive generation remains `needs_human/accounting_blocked`. Readiness accepts retained superseded accounting only with that explicit quarantine marker and fails closed if it is removed.

## Verification evidence

- Final remediation factory suite: 63/63 passed in 32.699s against fresh disposable PostgreSQL 17, including API integration, both authority interleavings/forms, schema-008 upgrade safety, exhausted-event cleanup, effective-role denials, accounting recovery, deadlock regression, repository kill, bounded reconciliation, query plans, bootstrap and UDS authentication.
- Actual restart probe: PostgreSQL container restarted, one expired holder reclaimed, second reconciliation repaired zero, a higher fence issued, and the late holder was rejected.
- Representative `EXPLAIN (ANALYZE, BUFFERS)` assertions selected the claim, audit, usage, active-reservation and reconciliation indexes added or retained for their exact predicates.
- Root regression run: 488 tests in 314.727s found one undeclared admin source; after binding it to the existing factory service node, the focused regression, architecture validate, repository drift and all five diagram checks passed.
- Residual focused PostgreSQL tests passed 5/5; migration tests passed 4/4, installer tests passed 17/17, the dependency-free factory suite passed 24/24, Ruff passed, and the full root suite passed 488/488 in 299.731s. `python3 scripts/grok_verify.py --mode pr` runs after this report commit to bind the final-tree verdict.
- Final recovery focused PostgreSQL upgrade/bootstrap tests passed 2/2 in 1.664s; migration/contract/state/service tests passed 24/24, installer tests passed 17/17 and Ruff passed. The fresh PostgreSQL exit passed 63/63 in 50.054s with the restart probe, and the root suite passed 488/488 in 313.667s on product commit `3bbafeb`.

## Disposable migration evidence and cleanup

Only exact disposable local PostgreSQL containers created by the focused and exit runners were mutated. The named fix-wave containers, including `m4-factory-pg-residual3`, and all dynamic exit containers were removed; generated `.venv`/egg-info artifacts were moved to trash, and no shared database, Trust CI state, external system or production resource was touched.

## Rollout, rollback and remaining authority

Source rollout only: no service was activated and no migration was run outside disposable databases. Recovery after durable intake is global kill, stop local intake/claims, preserve audit/state, restore backup into a separate comparison database and forward-fix with migration `012+`; destructive down-migration is prohibited.

Independent route reviews, PR delivery, the App-owned policy-epoch check on the exact PR head, signed approval scopes, merge and any deployment remain outside this implementation report and are not claimed here. The calendar deadline does not change the product runtime contract or bypass those gates.
