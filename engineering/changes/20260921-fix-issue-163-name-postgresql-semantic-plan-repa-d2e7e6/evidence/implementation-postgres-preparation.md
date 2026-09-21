# Issue #163: pending PostgreSQL implementation notes

Static preparation only. No PostgreSQL test, SQL statement, container or product
implementation ran while the coordinator reserved the shared CPU lane. The
offline RED command remains pending as recorded in `implementation-red-plan.md`.

- Reuse `PostgresFactoryTests.semantic_repair_fixture`; it already injects a
  server-clock intake observation and produces real execution, subject, evidence
  and verdict records through capability-specific stores. A small optional test
  fixture database parameter can let the current-prefix tests reuse it against
  their actual001–021 database without applying022 prematurely. Do not call the
  fixture class `setUpClass`, which applies all current migrations.
- The #166 helper currently watches only the child function and six execution
  tables. Inspect both child and plan function OID/owner/ACL/security/search-path
  metadata; only the plan definition may change under022. Extend the snapshot to
  actual persisted semantic success/escalation records constructed with the old
  plan function. Keep historical021 behavior assertions and checksum evidence.
- For the second idempotency lookup, lock a fresh subject row on connection A,
  start the uniquely named coordinator request B, and observe B blocked behind A
  through `pg_stat_activity`/`pg_blocking_pids`. Execute the matching or conflicting
  same-key command on A while it holds the lock, then commit. This exercises the
  actual first-miss/subject-wait/second-hit ordering without fabricated ledger
  rows or arbitrary scheduling sleeps. Bound observation, SQL and thread cleanup.
- Deadline evidence can first record a successful repair using a short positive
  task wall budget, then wait for that recorded manifest deadline using observed
  server time and a client watchdog. Verify exact success replay after expiry and
  a distinct-key persisted `deadline_exhausted` escalation. Authority remains
  independently fresh; no production timeout or stored deadline needs changing.
  A NULL deadline is not constructible through the typed manifest contract;
  document any such unexecuted branch instead of weakening that contract.
- Early raw coordinator calls cover invalid command inputs, digest/closed shape,
  cycle linkage, absent task-bound subject and absent/mismatched verdict. Malformed
  canonical JSON reaches the existing exception arm. Existing integration cases
  already cover an idempotency conflict and two prior-proposal mismatches; retain
  those cases and replace their obsolete corruption expectations with exact codes.
- A temporary additional CHECK on the disposable child-proposal table can force a
  write-time check violation after the function's directive insertion, proving
  the existing exception subtransaction rolls it back. That test must remove only
  its own named constraint in cleanup; never disable production guards/triggers.
  Ordinary child conflicts need separate persistence assertions because a normal
  return does not have the exception arm's rollback semantics.

These are test-construction notes, not measured reachability or passing evidence.
All new runtime cases and current-prefix extensions remain pending.
