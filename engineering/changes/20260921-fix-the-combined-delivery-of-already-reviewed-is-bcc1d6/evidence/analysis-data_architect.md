# Combined delivery: data architecture analysis

Route `bcc1d645c438`; role `data_architect`; static analysis only, 2026-09-21. No tests, imports, compilation, Docker, database operations, product edits or delegation performed.

## Decision and inspected identities

No data integration blocker found in the exact candidates listed in `candidates.json`. Reuse #166 unchanged; no migration 022, migrator rewrite, data backfill, deployment or additional infrastructure belongs in this batch.

- Combined base `839d3aa26bc90417424d814ee48d8b5cd3be367e` and candidate source base `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48` have the identical full Git tree `e2a807845c77af0c6023c53fcd30972ede9fb8bd`.
- #166 head `23eb62dc21a090e6bf086cbc2a568d83417b0a2e` contributes only `factory/tests/test_execution_persistence_postgres.py` to product/test source: Git blob `501f5203d3eb97bba19c382b47a8d45f5526ac61`, SHA-256 `4ae68ffb74f4f9ec1398f3c5d96513bb6b35be1337dad6614a2af70160409236`.
- At both bases and #166 head, migrator blob is `c09472cd15255c503ab6f8e728b8aa3be4eeecbb`; resources subtree is `7c95e0de1536b0cc5e790a9bb25992209bff8d3f`. SQL 001–021 and production migration logic are unchanged.
- Other exact candidates change routing/artifact display, change-spec receipt enumeration, consumer documentation rendering, fingerprint/JSON handling and architecture reference analysis. None changes factory production source, SQL resources, disposable runner, restart probe or PostgreSQL test discovery.

## Invariants retained by the existing fixture

1. **Authentic prefix:** schema 001–014 is built with packaged SQL and authentic version/name/digest ledger entries. The existing service/store population helper creates actual task, accepted-intent, run, execution packet, manifest and proposal rows; its historical compatibility shim is removed. Applying `packaged[14:-1]` therefore leaves the actual 001–020 prefix on this checkout, not a fresh empty database or fabricated current ledger.
2. **Exactly one pending resource:** prefix identity equals every `discover_migrations()[:-1]` entry before execution. The real migrator must apply exactly the final packaged migration, then return an empty tuple on replay. Derived identities avoid changing #166 when a future suffix is added; the historical 021 assertion remains explicitly resource-bound.
3. **Preservation:** snapshots compare the complete ledger including existing `applied_at`, full JSON contents of six populated tables, and the exact `semantic_bind_repair_child(character,text)` OID, owner, sorted ACL, SECURITY DEFINER flag and search path. Effective EXECUTE must remain `(coordinator=True, validator=False, adjudicator=False, runtime=False)`. For suffix 021, function text changes and the same coordinator call changes from SQL NULL to `{"repair_child_rejection":"command_input_invalid"}`.
4. **Real drift rejection:** corrupting the penultimate checksum invokes the production planner, requires the precise drift exception and unchanged snapshot, then restores the authentic checksum and requires successful upgrade/replay. This negative control cannot pass through mocked migration success.
5. **Observed contention:** holder and worker use the actual `ADVISORY_LOCK_KEY`; observation requires the uniquely named worker's ungranted advisory lock, Lock wait event and exact blocker PID. The production five-second statement/lock limits remain unchanged. These are per-statement/acquisition limits, not a whole-transaction guarantee.
6. **Bounded recovery:** release-after-observation must succeed; sustained contention accepts only PostgreSQL `57014`/`55P03`, requires at least four seconds elapsed and an unchanged snapshot, then a successful retry. Three-second observation, twelve-second primary join, less-than-fifteen-second assertion and ten-second final join fail closed on starvation. Cleanup releases the holder first, terminates only the uniquely named worker within the owned database if needed, checks session disappearance, and runs registered database cleanup after connection contexts close.

## Interaction with the other fixes

- #168 changes how the outer verifier inventories paths and serializes reports. It does not change generic subprocess execution, database URLs, migration checksums, SQL execution, timeout values or factory test discovery. Keep the fresh combined `source-stability` check and fingerprint-bound receipts; historical #166 receipts are not current combined-tree evidence.
- #162 adds the already-supported `data_review` receipt kind to the schema; it neither authorizes database changes nor alters independent Trust CI policy. The separate trusted-validator successor is excluded.
- #153/#161 render consumer AGENTS/factory README from descriptor-validated template bytes; this does not replace packaged SQL or database test files. Preserve the reviewed template implementation, without extending consumer installation scope.
- #156 and #147/#148 alter routing/architecture diagnostics, not database behavior. Use the established combined route instead of rerouting midway, and let the full combined gate exercise their interaction with changed-file classification and schema/reference checks.

## Existing evidence reused, with its limits

Inspected #166 independent data/test reviews and `evidence/focused-postgres.json`. Those record all three new PostgreSQL 17 cases passing with zero skips in 10.807 seconds, genuine checksum/advisory-lock observations and bound-container cleanup. The focused harness used tmpfs; this is not a claim that the unchanged full disposable runner uses tmpfs.

Read the final local report and metadata from `/home/pall/.cache/agbp-run/issues-wave-20260921/issue166/verify-final{,-meta}.json`: head `23eb62dc21a090e6bf086cbc2a568d83417b0a2e`, 07:02:36–07:10:57 UTC, exit 0, fingerprint `83353a7e7ee6980eeda8e9cb3a344e0a2e357882f9d9461cb48631ab8bcfff18`; factory unit, PostgreSQL exit and source-stability checks pass. The retained PostgreSQL tail reports 782 tests in 354.205 seconds, two pre-existing skips. These are historical candidate results, not execution by this analysis agent or proof for the new combined SHA.

The timeout scenario proves rollback/no change while waiting for migration admission; it does not exercise failure after partial suffix execution or contention with a live function invocation. Six populated tables do not represent production volume/distribution or full tenant isolation coverage. No new query plan, index, downtime, backfill or production rollback change is introduced by this test-only delta.

## Required combined verification

1. After integration, compare the #166 test byte identity and assert zero delta in `factory/src/adaptive_factory/migrations.py`, resources 001–021, `factory/tests/run_disposable_exit.py` and `factory/tests/postgres_restart_probe.py` against the combined base. Reject migration 022 or unrelated factory edits in this batch.
2. On the coordinator's exclusive heavy lane, run `GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr --json` on the frozen combined candidate. Require the real `factory-postgres-exit` check, not the repository-sandbox capability skip. Existing runner performs disposable target preflight, full factory discovery (480-second subprocess bound), actual restart/reconciliation and exact-ID/name/image/nonce-bound cleanup; the verifier's outer bound is 600 seconds.
3. Retain direct evidence that all three `test_populated_current_prefix_*` cases ran and passed, not skipped. If the verifier tail omits their names, capture the runner's full output or use one reserved focused run against that same combined test source; do not manufacture new coverage or rerun unchanged database suites without a specific evidence gap.
4. Require migration unit tests, effective-role checks, restart/reconciliation and source stability to pass. Existing version-21 assertions elsewhere remain correct because migration 022 is excluded; a later #163 integration must reconsider them separately.
5. Dispatch the selected independent data review after combined verification. Bind receipts to the final combined HEAD/fingerprint and obtain the exact-SHA external Trust CI check before merge. Old candidate receipts/checks cannot authorize this combined branch.

Rollback for this batch is reverting the integrated source/test/documentation change through a PR; no database migration or production-state rollback is required. Stop on changed SQL digests, privilege drift, unexpected fixture rows, skipped required PostgreSQL coverage, leaked owned sessions/resources or a failed watchdog.

Suggested shared-memory fact for the coordinator: when the integration base has an identical Git tree to a reviewed migration-test base and SQL/migrator identities remain unchanged, reuse the reviewed fixture unchanged; obtain fresh combined evidence instead of adding an unnecessary new migration or duplicating the test implementation.
