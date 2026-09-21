# Issue 166 implementation evidence

Scope: tests only in `factory/tests/test_execution_persistence_postgres.py`; base `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. Packaged migrations and the production migrator are unchanged.

## Regression and negative control

The historical populated schema-14 fixture is advanced with real packaged SQL and real ledger identities through `discover_migrations()[:-1]`. The actual migrator must return exactly the final packaged resource; the full ledger identity, original timestamps, six populated tables, function OID/owner/normalized ACL/SECURITY DEFINER/search path, effective privilege matrix, and idempotence are compared. Current count and aggregate digest are not frozen. On the present 020→021 boundary, the old NULL result and new named rejection are characterized explicitly; future latest-prefix coverage remains active.

A real recorded prefix checksum is deliberately corrupted in the owned database. `MigrationError` must identify that version and leave the complete snapshot unchanged. Restoring the authentic checksum permits the real incremental upgrade. This is a negative control against the database ledger, not a deliberately failing coverage assertion or mocked migrator.

## Contention and recovery boundaries

Both concurrent cases hold the exact production migration advisory lock in a separate transaction. An observer must find the uniquely named worker's ungranted advisory lock, Lock wait event, and holder PID in `pg_blocking_pids` before proceeding. One case releases then requires success; the other retains the holder through the production server timeout, accepts only PostgreSQL timeout SQLSTATE 57014/55P03, and requires an unchanged full snapshot followed by successful retry and replay. A client watchdog expiry fails the test. Blocker release, bounded worker joining, exact worker backend termination on watchdog failure, session disappearance checks, and registered database cleanup limit failure fallout.

These cases test migration-lock contention, not live function-call locking. PostgreSQL 17 `ProcedureCreate` opens `pg_proc` with `RowExclusiveLock` (line 337) and keeps OID, ownership and ACL unchanged on replacement (lines 516–526); this does not justify the issue's claim that executing a function necessarily blocks replacement through ACCESS EXCLUSIVE. Source inspected directly: [PostgreSQL REL_17_STABLE pg_proc.c](https://raw.githubusercontent.com/postgres/postgres/REL_17_STABLE/src/backend/catalog/pg_proc.c). Production timeouts remain five seconds per statement/lock attempt, not a promised whole-transaction duration.

## Commands and outcomes

- `uv run --project factory python -m unittest factory.tests.test_migrations -v`: 24 passed, 0 skipped, exit 0.
- `python3 -m py_compile factory/tests/test_execution_persistence_postgres.py`: exit 0.
- `git diff --check`: exit 0.
- `python3 /home/pall/.cache/agbp-run/issues-wave-20260921/issue166/focused_postgres.py`: repository disposable-target preflight passed; all 3 PostgreSQL 17 tests passed (0 skipped) in 10.807 seconds; exit 0. Exact bound container cleanup verified absence, with tmpfs and no persistent volume. See `focused-postgres.json` for source/log hashes and container identity.
- First runner attempt: preflight rejected an issue-specific container name before tests; exact-ID cleanup passed. The cache harness was corrected to the required `adaptive-factory-exit-<12hex>` name, without changing repository safeguards. Failed and successful logs are retained separately.

Raw focused runner and logs belong in `/home/pall/.cache/agbp-run/issues-wave-20260921/issue166/`. The runner reuses the repository's exact-ID/nonce binding and target preflight, publishes only an ephemeral loopback port, and uses tmpfs rather than persistent PostgreSQL volumes. Full verifier and independent review are coordinator-owned and not yet claimed by this report.
