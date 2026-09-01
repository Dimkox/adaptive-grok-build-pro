# M4 exact-head data review — FAIL

## Review binding

- Route: `b7f288f1e81e`
- Change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
- Accepted M3 base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Exact reviewed product HEAD: `fa043d48430963f82c52a76fbdabe2c35cd3d995`
- Exact Git tree: `d8024cc0a188b4d58006a87fca5685e66471346a`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..fa043d48430963f82c52a76fbdabe2c35cd3d995`
- Metrics repair range: `daa3930cb84ba6547171583e41bcf0dee2ab1314..fa043d48430963f82c52a76fbdabe2c35cd3d995`
- Exact-head verifier receipt: PASS, tree fingerprint `9ec2ce27d8dd0e0ee896573d282f4e0dcef2349a05914659d9bdac1e8dc37d75`
- Reviewer: route-selected read-only `data_reviewer`

The HEAD, Git tree and repository fingerprint above were clean and mutually bound before concurrent final reviewers began rewriting their evidence reports. This review inspected the committed product tree, not those later report-only worktree changes.

## Verdict

**FAIL — two related Important data/operational findings remain in the new metrics query path.**

- Critical data findings: **0**
- Important data findings: **2**

The fixed metric inventory, redaction and cardinality are sound, and the previous schema-008 recovery defects remain closed. The new store projection is not a coherent database snapshot and its exact full-history aggregates have no execution bound.

## Important findings

### DATA-006 — one metrics response can combine mutually impossible database states

`PostgresFactoryStore.metrics()` opens the normal connection and executes eight separate aggregate statements (`factory/src/adaptive_factory/store.py:112-150`). `_connect()` only executes `SET ROLE`; it does not select a stronger transaction isolation level (`store.py:55-64`). PostgreSQL therefore uses the default `READ COMMITTED` behavior, where each statement receives a new snapshot.

The families expose values whose relationships are committed atomically by the product, especially live runs and live capacity allocations. A real PostgreSQL 17 interleaving on exact HEAD proved the response path can split that transaction boundary:

```text
transaction_isolation='read committed'
live_leases_first_statement=1
concurrent committed cancel/release
active_capacity_later_statement=0
```

There is no committed point in this history at which the factory had one live lease and zero live allocation: cancel closes both in one transaction. The same issue applies to task state versus transition count, reservation/observation projections and reconciliation totals. The current inventory test drives operations to completion before scraping, so it cannot detect a torn multi-statement observation.

Impact: the release-required operational surface can report a false capacity/lease or state/event imbalance during normal concurrent work. Operators cannot distinguish that torn scrape from the exact invariant drift that readiness, rollback and incident procedures require them to detect.

Required repair: execute all store-derived metric reads against one explicit read-only repeatable snapshot, or return them from one SQL statement with one statement snapshot. Add a two-connection regression that pauses between the relevant reads, commits release/reconcile concurrently and proves the returned store-derived values correspond to one committed side of the transition. The separately process-local `auth_rejected` value may remain explicitly non-atomic with PostgreSQL state because its restart/reset boundary is already documented.

### DATA-007 — release polling performs unbounded full-history scans with no statement timeout

The new projection computes exact global `count(*)`/`sum(...)` values over `tasks`, `task_events`, `runs`, `usage_observations` and `reconciliation_runs` for every authenticated scrape (`store.py:114-150`). `task_events` and `usage_observations` are append-only histories with no global row or retention bound; a task alone permits up to 100,000 events, and the number of tasks is unbounded. Exact global count/sum cannot be made independent of retained history by the existing task-scoped indexes.

Unlike intake, claim, list and reconcile, `metrics()` sets neither a local lock timeout nor a statement timeout. The exact PostgreSQL probe reported:

```text
statement_timeout='0'
EXPLAIN count(task_events): Seq Scan
EXPLAIN sum(usage_observations.output_bytes): Seq Scan
```

The small fixture's sub-2-KiB response proves bounded output cardinality, not bounded database work. A routine monitoring poll can consume work proportional to all retained evidence, hold its transaction snapshot/connection without a deadline and repeat that load at the scrape interval. This conflicts with the M4 data design's five-second store-operation bound and undermines the control plane precisely when history is large or the database is degraded.

Required repair: set the documented transaction-local five-second statement bound before the first metrics read and avoid repeated exact scans of append-only history. Fixed durable counters/rollups updated in the same business transactions are the natural fit for cumulative event/usage/reconciliation totals; current gauges may use indexed bounded projections. Add a populated-scale/plan regression and an effective-timeout assertion for the supported metrics call. If exact scans are retained, the change package must state a defensible volume bound and prove they finish below the timeout at that bound.

## Metrics properties that passed

- The API returns exactly three fixed families with a closed set of fixed keys. No repository, source, task, run, actor, credential or reason becomes a label or key, so response cardinality is bounded.
- Missing, invalid and scope-denied authentication increments only a saturated, lock-protected process-local integer. Its restart reset is documented, and credential bytes are not returned.
- Durable stale-fence rejection uses one allow-listed `(metric_name,outcome)` row and saturates at signed `bigint`; concurrent increments are atomic through `INSERT ... ON CONFLICT DO UPDATE`.
- Reservation/observation values use integer units, and PostgreSQL `sum(bigint)` avoids aggregate overflow. The JSON key count and response shape remain fixed even as values grow.
- Wildcard operator authorization remains required before the store projection is invoked.

## Existing migration, accounting and recovery closure rechecked

- Migrations remain contiguous `001..011`, checksum-locked and atomic under the factory advisory lock. Migrations and schema are unchanged in the metrics repair range.
- Migration `011` still hashes to `ff358ea06a5497d9d215f8fef7ab3540b0b4af993c806985e9d5ae6d46b01bea`. A real schema-008 history still upgrades through `[009,010,011]`, preserves reservation/run/attempt/usage evidence, quarantines unsafe generation 1 as `superseded/accounting_blocked`, leaves same-identity generation 2 uniquely claimable and replays with no pending migration.
- Claim remains `SKIP LOCKED`, unblocked, zero-reservation and live-reservation guarded. Completion requires task-wide settled accounting. Capacity functions retain canonical lock order, ceilings and underflow protection.
- M0 `FOR SHARE` authority serialization, mandatory cleanup outside the ordinary event budget, command replay, hash-chained audit, reconciliation limits, restart fencing and readiness accounting/capacity checks are unchanged and passed the fresh suite.

## Independent verification evidence

- `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..fa043d48430963f82c52a76fbdabe2c35cd3d995` — PASS.
- The exact-head fingerprint-bound verifier receipt is PASS for `fa043d48430963f82c52a76fbdabe2c35cd3d995` and `9ec2ce27d8dd0e0ee896573d282f4e0dcef2349a05914659d9bdac1e8dc37d75`.
- `python3 factory/tests/run_disposable_exit.py` — PASS, 65/65 in 56.272s on fresh disposable PostgreSQL 17; the actual restart repaired one expired lease, replay repaired zero, a higher fence was issued and the late holder was rejected.
- Independent two-connection PostgreSQL 17 probe — FAIL as DATA-006: `READ COMMITTED` returned `live_leases=1` before a committed cancel and `active_capacity=0` afterward inside the same metrics-style transaction.
- The same probe — FAIL as DATA-007: effective `statement_timeout=0`; exact event count and observed-output sum selected sequential scans.
- Both exact disposable probe containers and isolated environments were removed. No shared, external, Trust CI or production database was read or mutated.

This review changed only this report. It did not modify product code, migrations, receipts, Git history or external state. Any repair changes the product fingerprint and requires fresh verification plus all selected reviews.

**Final data-review result: FAIL for exact product HEAD `fa043d48430963f82c52a76fbdabe2c35cd3d995`.**
