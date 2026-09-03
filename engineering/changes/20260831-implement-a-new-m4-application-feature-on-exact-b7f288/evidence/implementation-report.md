# M4 implementation report

## Result

M4 is implemented as a separate local `factory/` package on accepted M3 base `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`. It validates immutable M1/M2/M3/M0-bound intake, persists isolated PostgreSQL operational truth, schedules fenced bounded leases, and exposes authenticated scoped control over an explicit Unix socket. It has no provider execution, repository command, GitHub/external write, deployment, systemd, production or Trust CI authority.

## Delivered behavior

- Closed typed intake, handoff, actor, task, run, attempt, event and command records with canonical digests, separate complete-intent/semantic-work/transport-command identities, atomic supersession and bounded validation.
- Thirteen contiguous checksum-locked factory migrations, repository/full-policy/action-bound transaction-serialized M0 authority, complete schema-008 unsafe-accounting quarantine, audit-v2 evidence, task-history indexes, capability-shaped capacity and fixed-metrics authority, effective least-privilege `factory_runtime` execution and no `trust_ci` privileges.
- Transactional `FOR UPDATE SKIP LOCKED` claims, monotonic per-task fences, database-time leases/deadlines and 20 global readers / 10 per repository / one writer capacity.
- Initial attempt plus two infrastructure retries, terminal dead/needs-human handling, 14,400-second and USD 25/token/output/event/repair ceilings, durable fail-closed missing accounting and idempotent usage observations.
- Global/repository kills, complete task/run/correlation-bound hash-chained audit, and capacity-before-task reconciliation capped at 100 candidates under one five-second PostgreSQL 17 operation deadline.
- Constant-time scoped bearer authentication, actor/repository-bound worker mutations, bounded streaming bodies, durable idempotency/correlation, bounded run/attempt/event history, fenced phase transitions, accounting endpoints, and CLI control over Unix HTTP only.
- One checked closed-inline OpenAPI document describes all 17 stable operations; runtime generation is disabled, every response is correlated, and normalized bounded errors preserve code/detail and the 401 bearer challenge.
- Runnable `adaptive-factory-server` composition that pre-binds only an owned mode-`0660` Unix socket, absolute owner-pinned no-follow actor/token ancestry, plus dependency-aware readiness and the three declared redacted metric families.
- Reproducible `adaptive-factory-admin` local bootstrap/migration interface with distinct owner/runtime DSNs, bounded `NOINHERIT` runtime login membership and effective-role readiness validation.
- Architecture model/rules/diagrams, K22 README graph, roadmap/status, installer inventory, verifier integration, release and forward-recovery documentation.

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
- `905249a` — frozen release-observability review evidence.
- `034168b` — bounded fixed-key release metrics inventory and rejection signals.
- `7eaccd6` — frozen observability-boundary review evidence.
- `94fc5ad` — transactional fixed-row metrics snapshot, closed runtime capabilities and bounded rejection accounting.
- `4f75558` — explicit best-effort rejection handling, final-PID1 PostgreSQL readiness and M4-M9 program connectivity.
- `ea5ef4f` — deadline/accounting reconciliation lifecycle repair.
- `3b13742` — separate semantic work and transport command identity.
- `a48c78f` — immutable versioned lifecycle snapshots.
- `85523e8` — bounded authorized lifecycle history.
- `a1f64e9` — central fenced operation-scoped task transitions.
- `18e75b3` — sole checked closed-inline 17-operation HTTP contract.
- `5dac08e` — exact runtime/parser/configuration parity for the checked contract.

## Independent-review remediation

The first five reviews correctly failed head `01643c6`. Regression-first repairs now atomically close leased cancel/supersede resources; isolate orphan reconciliation; settle and bound cost/token/wall accounting; require accounting before completion; preserve exact command replay; normalize CLI/API keys; bind workers and kill scopes to authenticated repository authority; require persisted M0 authority; execute under narrow database grants; and provide an actual UDS-only composition root.

The final fix wave accepted every finding in the five overwritten FAIL reports; there was no technical pushback. It now binds duplicate identity to the complete frozen intent, validates M0 repository/full-policy/action inside intake's insertion transaction, denies repo-scoped global reconciliation/metrics, closes every command input before coercion, authenticates all audit evidence fields, blocks cross-attempt unresolved accounting from retry/completion, eliminates reconcile/cancel lock reversal, and adds representative indexed-plan evidence.

The mandatory exit runner creates an exact disposable PostgreSQL 17 container, executes API and database tests under effective roles, restarts PostgreSQL, reconnects through a fresh store, proves one repair then a zero-repair replay, and removes the exact container. New acceptance cases directly exercise event/repair/deadline boundaries, repository-kill isolation, defensive 100+1 paging, the exact five-second setting, authority revocation races, real UDS authentication and shipped owner/runtime bootstrap.

The second residual wave uses forward-only migration `010` without changing applied `009`: both M0 authority forms now hold a row lock that conflicts with non-key revocation through intake commit; a real non-empty schema-008 upgrade quarantines unresolved prior-attempt accounting before claim; and mandatory release/reconcile/cancel events plus audit survive an exhausted ordinary-event budget while capacity returns exactly once.

The third residual wave leaves applied migration `010` immutable and adds forward-only migration `011`. A schema-008 blocked claimable row with zero aggregates becomes explicit `needs_human/accounting_blocked`, while a human-ready row with live prior-attempt accounting is preserved in a non-positive accounting quarantine; readiness additionally rejects any reintroduced unsafe `ready_for_human` projection.

Before PR delivery, the fourth residual wave corrects unreleased migration `011` under the explicit disposable-only exception. An unsafe older human-ready generation becomes `superseded/accounting_blocked` when a newer generation exists, retaining reservations, usage, run and audit evidence without colliding with the one-active-identity index; a lone unsafe positive generation remains `needs_human/accounting_blocked`. Readiness accepts retained superseded accounting only with that explicit quarantine marker and fails closed if it is removed.

The fifth residual wave closes AC-013 observability without adding a dependency or metric-label surface. The existing three authenticated families now expose fixed store-derived intake/queue/transition, lease/capacity, budget, retry/dead, kill and reconciliation/repair values plus a durable stale-fence rejection counter; missing, invalid and scope-denied credentials increment a redacted process-local total despite disabled access logging. Only that authentication total resets on server restart.

The sixth residual wave closes the observability authority and consistency boundary with forward migration `012`. Runtime can no longer read or mutate generic counter rows; it receives only a fixed snapshot function and a no-argument saturating fence-rejection capability, while the pre-`012` rows remain locked untrusted evidence and the trusted fence epoch begins at zero. One owner-maintained 21-column singleton is backfilled under an atomic disposable-only cutover and maintained in the same transactions as authoritative writes, eliminating mixed multi-query snapshots and full-history metric scans.

Every final application 401/403 now increments exactly once at the HTTP response boundary, including actor-kind, repository and trusted-authority denial, without labels or credentials. Snapshot reads have fixed 5-second statement and 500-millisecond lock bounds; stale-fence instrumentation has shorter connection/lock/statement bounds and is best effort after the authoritative decision, so counter failure cannot replace or materially delay exact `409 stale_fence`. The first full PostgreSQL run reproduced a counter-trigger/capacity lock inversion; restricting reconciliation counter work to completed-state deltas restored the established capacity-first order and the regression passed on a recreated disposable database.

The first exact verifier after wave six passed 12/14 gates but rejected two exit-harness details. Bandit B110 identified the silent best-effort exception handler, and the fresh disposable database accepted a temporary readiness probe before closing the first host connection during the official image's final-postmaster handoff. Product commit `4f75558` makes handling explicit while preserving the identical authoritative fence error, and proves the final PostgreSQL postmaster is PID 1 plus ready rather than trusting a fixed delay.

Current documentation connects M4 control/evidence through the provisional M5 packet/execution result and M6 semantic verdict, then roadmap-only M7 ready-for-PR shadow bundle, M8 exact-profile cohort/demotion and M9 exact signed-artifact delivery/recovery. Each edge names digest/SHA binding, gate, invalidation, rollback and forbidden authority; the hard deadline is **2026-09-08 00:00 UTC+3**, M5 remains rootless-host blocked, current authority caps M8 at L2, and production promotion remains human-owned. None of these connections claims M4-M9 completion, push, external check, merge or deployment.

## Resumed data and architecture repairs

The current repair makes deadline/accounting reconciliation cursor-stable and quarantines unresolved cancel/supersede evidence; separates immutable full intent from semantic work and transport replay; adds frozen task/run/attempt/event projections with bounded authorized history; and routes every task-state mutation through one operation-scoped transition policy while preserving lock order and the seven-field lease grant. The checked OpenAPI document is now the sole schema surface and declares the exact 17-operation runtime, closed inline bodies/results/errors and correlation headers; generated `/openapi.json` is disabled.

Focused PostgreSQL 17 evidence culminated in a 64/64 full integration pass in 57.594 seconds. The HTTP intake case proves fresh equivalent authority returns the same task, same-request changed body conflicts, a semantic change supersedes exactly once, and actual correlation headers persist independently in command/audit rows. Dependency-free factory tests report 67 passes plus 64 expected PostgreSQL skips, architecture tests report 53/53, and lint/compile/diff checks pass; these are implementation evidence, not final verifier/review receipts or external authority.

The final contract-parity pass binds every operation to its exact scope and correlation policy, canonical lowercase dashed UUIDs, closed redacted correlated 500 responses, strict actor/repository identifiers and PostgreSQL/Python integer bounds. Dependency-free factory discovery then ran 141 tests with 77 passes plus 64 expected PostgreSQL skips in 1.445 seconds; architecture-model, fitness and governance tests passed 150/150 in 139.751 seconds. This pass changed no database transaction or SQL path, so the already-green 64/64 PostgreSQL evidence remains the applicable data-path proof; final exact-head verification and independent reviews are still pending.

## Verification evidence

- Final remediation factory suite: 63/63 passed in 32.699s against fresh disposable PostgreSQL 17, including API integration, both authority interleavings/forms, schema-008 upgrade safety, exhausted-event cleanup, effective-role denials, accounting recovery, deadlock regression, repository kill, bounded reconciliation, query plans, bootstrap and UDS authentication.
- Actual restart probe: PostgreSQL container restarted, one expired holder reclaimed, second reconciliation repaired zero, a higher fence issued, and the late holder was rejected.
- Representative `EXPLAIN (ANALYZE, BUFFERS)` assertions selected the claim, audit, usage, active-reservation and reconciliation indexes added or retained for their exact predicates.
- Root regression run: 488 tests in 314.727s found one undeclared admin source; after binding it to the existing factory service node, the focused regression, architecture validate, repository drift and all five diagram checks passed.
- Residual focused PostgreSQL tests passed 5/5; migration tests passed 4/4, installer tests passed 17/17, the dependency-free factory suite passed 24/24, Ruff passed, and the full root suite passed 488/488 in 299.731s. `python3 scripts/grok_verify.py --mode pr` runs after this report commit to bind the final-tree verdict.
- Final recovery focused PostgreSQL upgrade/bootstrap tests passed 2/2 in 1.664s; migration/contract/state/service tests passed 24/24, installer tests passed 17/17 and Ruff passed. The fresh PostgreSQL exit passed 63/63 in 50.054s with the restart probe, and the root suite passed 488/488 in 313.667s on product commit `3bbafeb`.
- Active-generation recovery passed the exact schema-008 PostgreSQL reproduction 1/1 in 1.887s and the combined upgrade/bootstrap run 2/2 in 1.773s. The fresh PostgreSQL exit passed 63/63 in 34.667s with the restart probe, and the root suite passed 488/488 in 324.581s on product commit `d15302f`; the final exact-tree verifier runs after this evidence commit.
- Release-observability focused verification passed the API auth regression 1/1, the real PostgreSQL inventory regression 1/1 twice, API/server/service 21/21 and Ruff. The final fresh PostgreSQL exit passed 65/65 in 35.924s with the restart probe, and the root suite passed 488/488 in 312.686s on product commit `034168b`; the exact-tree verifier runs only after the final evidence commit.
- The first exact-tree verifier passed every gate except secret scan, which conservatively matched direct deterministic credential assignments in the two new test files. Fixture construction is now split while retaining byte-identical runtime credentials and redaction assertions; no scanner rule or production authentication behavior was changed.
- Post-repair evidence is zero secret-scan findings for both changed tests, the focused authentication/redaction case 1/1, and a second fresh PostgreSQL exit 65/65 in 41.762s with the restart probe. The final exact-tree verifier runs after this evidence is committed.
- Observability-boundary focused evidence passed the real PostgreSQL migration/role/snapshot/fence-lock/upgrade/deadlock set 6/6 in 6.570s, exclusive snapshot-lock timeout 1/1, API/service regressions 2/2 and Ruff. The final named PostgreSQL suite passed 69/69 in 39.794s; the separately fresh disposable exit passed 69/69 in 39.993s plus actual restart, one repair, replay no-op, higher fence and late-holder rejection.
- The root suite passed 488/488 in 305.256s on clean product commit `94fc5ad`; the exact changed-tree secret scan reports zero potential secrets. The final exact-tree verifier runs once after this evidence-only commit.
- Exact verifier on `a3b8e87` passed 12/14 gates and failed only Bandit B110 plus the fresh image handoff described above; its root coverage gate passed 488/488 in 501.064s and source stability passed. After repair, focused tests passed 14/14, Bandit/Ruff and architecture validate/drift/diagram checks passed, and fresh disposable PostgreSQL exit passed 70/70 in 39.705s plus the full restart/reconciliation probe on product commit `4f75558`.

## Disposable migration evidence and cleanup

Only exact disposable local PostgreSQL containers created by the focused and exit runners were mutated. The named fix-wave containers, including `m4-factory-pg-wave6-red`, and all dynamic exit containers were removed; generated `.venv`/egg-info/`__pycache__` artifacts were moved to trash, and no shared database, Trust CI state, external system or production resource was touched.

## Rollout, rollback and remaining authority

Source rollout only: no service was activated and no migration was run outside disposable databases. Recovery after durable intake is global kill, stop local intake/claims, preserve audit/state, restore backup into a separate comparison database and use a separately reviewed dependency-coordinated forward repair; destructive down-migration is prohibited. This product/documentation freeze is the direct input to the immediately following artifact-only commit, which rebuilds the tracked `2.0.13` archive plus sidecar without changing source; final exact-head verification and independent reviews remain pending.

M5 branch `milestone/m5-isolated-execution-provisional-m4` (route `37b05f579320`) and M6 branch `milestone/m6-semantic-validation-provisional-m4` (route `82aac86a3bf9`) are provisional parallel work based on M4 product `94fc5ad`; both must restack onto their accepted predecessors. This is a repository-local dependency handoff, not a push, external check or delivery claim.

Independent route reviews, PR delivery, the App-owned policy-epoch check on the exact PR head, signed approval scopes, merge and any deployment remain outside this implementation report and are not claimed here. The calendar deadline does not change the product runtime contract or bypass those gates.
