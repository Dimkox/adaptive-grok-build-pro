# Proposed PR173 integration for issue163

Read-only preparation for route `806a83c58b91`. This proposal does not apply a
merge, modify the repository, execute a check or establish merged-base evidence.
The coordinator will authorize application only after PR173 is actually merged.

## Exact inputs and minimum resolution

- Issue163 source: `d80c5c8d8e5afe938d195401715daf5e69192a81`.
- Batch PR173 source: `23984e55560c6d559a46445061f10331ca05bcf9`.
- Actual merge base: `839d3aa26bc90417424d814ee48d8b5cd3be367e`.
- Conflicted product path: `factory/tests/test_execution_persistence_postgres.py`.
- Proposed resolved blob: `069af430af09598fe70d81a17e64a20a0bd74369`.
- Proposed resolved SHA-256: `62ad6b546dc4e6c8f0a7f2b6d0023fe2178b254d97bf5282481474db797ca47b`.

Keep this entire file byte-identical to the issue163 source. No novel hunk or
behavior is needed. The static three-tree merge shows overlapping additions to
the prefix fixture/snapshot/assertion block. They arise because the batch carries
the original issue166 implementation while issue163 already contains that exact
implementation and extends it for022.

The batch file is byte-identical to the issue166 prerequisite `23eb62dc21a090e6bf086cbc2a568d83417b0a2e`:
blob `501f5203d3eb97bba19c382b47a8d45f5526ac61`,
SHA-256 `4ae68ffb74f4f9ec1398f3c5d96513bb6b35be1337dad6614a2af70160409236`. Git confirms that prerequisite is
an ancestor of the issue163 source. `git diff 23eb62dc21a090e6bf086cbc2a568d83417b0a2e 23984e55560c6d559a46445061f10331ca05bcf9 -- factory/tests/test_execution_persistence_postgres.py` is empty.
Thus choosing the issue163 file retains the batch's complete test contribution
and its existing issue163 extension; choosing the older batch block would lose
plan-function and semantic-row coverage.

The patch alongside this report is an optional review artifact transforming the
exact batch blob into the proposed source blob. It contains only this test file.
It is not a patch against a worktree containing conflict markers. After explicit
application authorization, resolving this one path from the named source commit
is the smallest operation; do not replace other paths or use a blanket ours merge.
If the actual merged PR173 content differs from the named batch commit, re-evaluate
this proposal before application.

## Historical001–020 to021 remains a real upgrade

`test_populated_historical_prefix20_to21_preserves_child_upgrade_proof` selects
the actual packaged first21 immutable resources. Its fixture applies001–014 and
actual015–020 SQL with real name/hash ledger rows, then populates execution and
semantic rows. It does not invent an already-applied ledger or replace any SQL.
The scoped discovery patch only presents the historical resource tuple to the
real migrator, which must return precisely021, record it, and return empty on
replay. The old prefix is inspected before the migration.

For021, `semantic_bind_repair_child` changes from NULL to the named input refusal;
its OID, owner, ACL, SECURITY DEFINER and search path stay equal. The plan function
is also snapshotted and must remain byte-identical. All old ledger timestamps and
all populated rows must remain exactly equal. This explicit historical case
prevents latest=022 from silently dropping the former current-prefix021 proof.

## Current001–021 to022 and integrity obligations

The default fixture uses `discover_migrations()` and executes every resource
through the actual current prefix. On this source it therefore executes001–021,
then the real migrator must apply exactly022. It retains real001–021 ledger
identities/timestamps, populated success and escalation records and all sampled
execution/semantic rows.

The snapshot includes both the child and plan function OID/owner/ACL/security/
search-path/definition plus effective EXECUTE privileges. Only the targeted plan
function definition may change for022; the child definition stays identical.
The plan NULL probe changes to the named input refusal, then migration replay
must be empty and the complete snapshot unchanged.

The original six execution tables now coexist with populated semantic fixtures,
so the fixture intentionally requires nonempty rows rather than exactly one row
per table. Data preservation itself still uses exact complete before/after row
equality. No checksum, timestamp, privilege or replay assertion is relaxed.

The following inherited methods are byte-identical between batch and proposal
(after excluding only trailing blank separators between method definitions):

| Method | SHA-256 |
| --- | --- |
| `create_schema14_database` | `4a0a2f7624ad09434ed9b33498b32debd1c9d3ecd91a13a40549efd613a094a5` |
| `test_populated_current_prefix_upgrade_rejects_real_ledger_drift` | `0190c63608bbf5ce9de1b48ef717bee1a27c208976b2f4028e37b8e024ba3b87` |
| `current_prefix_advisory_contention` | `cf2d67127b015baa73b3e528e2bda0f9829a90c2d2be11bc695ae265cb6a4e6b` |
| `test_populated_current_prefix_advisory_wait_release_succeeds` | `9b76ebadf0c324a719daf2c3a1aed9d03301cd53441e597e025172e49336f744` |
| `test_populated_current_prefix_advisory_timeout_rolls_back_and_retries` | `3ac9f24aedc840c069afc89a4283efcc800ca9933c138db354753284ca50164e` |

This retains the real-ledger drift failure, observed advisory blocking, bounded
release success, timeout rollback, retry, worker watchdog and scoped cleanup.
The parameterized historical fixture does not alter those contention paths.

## Boundaries and next verification

No SQL resource is changed by this resolution, including immutable001–021 and
existing022. No application source, driver behavior, timeout, role or deployed
Trust CI state changes. Root handoff/document conflicts remain coordinator-owned.

This preparation ran only Git/text reads and wrote this report and optional
patch outside the repository. It ran no tests, imports of product modules,
compilation, lint, Docker or migration. No merge or merged-base validation is
claimed. After the authorized integration, confirm the resolved blob above and
retain the coordinator's required fresh full verification and independent review
on the resulting head/base; prior results are historical evidence only.
