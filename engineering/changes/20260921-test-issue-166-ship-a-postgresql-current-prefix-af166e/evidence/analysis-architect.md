# Architect analysis — issue #166

## Verified gap and correction

`PostgresMigrator.apply()` reads real `factory.schema_migrations` rows, compares the recorded `(version, name, sha256)` prefix through `plan_migrations()`, and applies pending SQL in one transaction with 5-second per-statement lock and statement timeouts. Existing PostgreSQL tests cover populated older-prefix upgrades, while the fresh-cluster path applies all resources together. No shipped test seeds a real 001–020 prefix and then asks the migrator to apply only 021. The #155 evidence calls its successful current-prefix run a scratch probe, correctly limiting its claim.

The issue's assertion that `CREATE OR REPLACE FUNCTION` *necessarily* takes an `ACCESS EXCLUSIVE` lock that blocks executing calls is unproven by this tree. Do not encode that mechanism as a test expectation. Test observed migration outcome, elapsed bound, and transactional recovery under actual supported contention instead.

## Tests-only design

Add one isolated disposable PostgreSQL case, reusing the test suite's database creation and cleanup helpers. Load the on-disk `discover_migrations()` resources through the penultimate resource, executing their SQL and inserting each real `(version, name, sha256)` row. Assert this is the expected pre-upgrade state, including the old `factory.semantic_bind_repair_child(char,text)` OID and ACL/effective privilege matrix. Invoke the real `PostgresMigrator.apply()` against that database; assert the pending result is exactly the checkout's final resource, the new row has its on-disk digest, earlier rows are unchanged, the function OID and privileges are preserved, and a second apply returns no work. This is the specific 001–020→021 regression on the present checkout; avoid frozen whole-tree hashes and derive expected resource identity from `discover_migrations()`.

Use a second connection and explicit synchronization to keep a read-only function caller active while migration starts. Bound waits with thread/future timeouts and release the caller in `finally`; assert either successful completion within the supported timing window or, if a reproducible conflicting lock is deliberately arranged, a bounded timeout with intact prefix and successful retry after release. A migration-advisory-lock holder is a deterministic way to exercise the 5-second bound, but it tests the migrator's lock acquisition rather than a claimed function-level lock. Keep those assertions distinct. Do not assert an exact total 5-second runtime because the two timeouts apply to individual statements, not the whole transaction.

## Scope and future durability

Change test and disposable-harness expectations only where they pin current migration count; `run_disposable_exit.py` itself has no count pin, while `FreshClusterArtifactAttestorMigrationTests.setUpClass()` does. Future resources may change which migration is last, so the test should clearly identify the function-replacing target and use checkout-derived `(version, name, sha256)` expectations instead of silently assuming every future last resource replaces this function. All resources 001–021 and production migrator behavior remain immutable. Failure leaves only a disposable database, cleaned up in `finally`.
