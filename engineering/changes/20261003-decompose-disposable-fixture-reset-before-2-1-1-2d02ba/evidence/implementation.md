# Fixture reset prerequisite — focused writer evidence

Sole selected data_implementer, route `2d02ba9e25dc`, worktree `v211-fixture-reset`, branch `refactor/v211-disposable-fixture-reset`, exact dispatch/base `63799f8760d3a55028d83ab5ff0116ececf8f7d1`. Five selected analyses and frozen approved scope were read before implementation. Controller owns final full verifier, five independent reviews, evidence ledger and exact external trust; this report does not claim those are complete.

## Startup and historical selector

Fresh measurement before repository/route inspection at 2026-10-03T00:28:04Z: 14 physical cores, 28 online logical CPUs 0–27; nproc-all 28, default nproc 22/affinity 0,1,8–27. Actual cgroup v2 membership `/user.slice/user-1000.slice/session-2050.scope`, `/sys/fs/cgroup` mount; inherited cpuset 0–27; session/user-1000/user.slice quotas `max 100000`, no finite root quota. Child-only widening probe 0–27 returned nproc 28/affinity 0–27 in the same cgroup. Verified capacity 28, controller unchanged. Assignment used CPUs 12,13, at most two focused test processes, and one 2-CPU/768-MiB fixture. No subagents or per-contour full verifier. Baseline has no `scripts/grok_agent.py`; no lifecycle/generation state was fabricated.

Controller preserved exact original selector receipt in `initial-selector-receipt.json`: created 00:18:47Z, base=head `63799f8760d3a55028d83ab5ff0116ececf8f7d1`, tree fingerprint `ca2bfa31372ad6b3dcf168eb3a3c38850053636e4c1f62233b9654a661ca706d`, workflow-only 13-path inventory, docs-state-focused, path digest `6f76e5e787f64cfe31211debe9512c1b6cecfe1a2f0045726b88720c7fc9879b`. Initial draft FAILED, skipping python-unittest/coverage/factory-postgres-exit. This is historical draft evidence, not product acceptance or a current skip permission; current executable changes require the controller's full gate.

## Exact product contour and bounded ruling

Six product paths: leaf `factory/tests/postgres_fixture_reset.py`; focused source test `factory/tests/test_postgres_fixture_reset.py`; two callers `test_execution_persistence_postgres.py` and `postgres_restart_probe.py`; installer `scripts/install_into.py`; its exact binding `tests/test_installer.py`.

Ruling: frozen constant-only 025 design overrides advisory suggestions to share singleton/counter policy or discover versions. Helper accepts only a cursor and performs one execute of the exact closed 43-table TRUNCATE/RESTART IDENTITY. No imports, DSN, credentials, transaction/connection ownership, table discovery, arbitrary arguments, CASCADE, version query or 026 names. Exact SQL SHA-256 `a67d8339b86d2af81a72d3f8e953cf29ce8bb81067f1cefe4921555a0c075de9` was verified against independently AST-extracted baseline statements before editing and against the executed helper afterward.

Only each caller's matching first statement was replaced. AST comparisons after removing that one operation prove both entire caller functions unchanged otherwise: connection/transaction context, conditional execution singleton branch, unconditional restart singleton branch, all counters, observation parameters/return value and runtime setup. Imports are package-safe/sibling-safe. Existing caller target/container/role/version/time/lock guards remain intact. `test_postgres_integration.py` is byte-identical and deliberately retains its third duplicate. All 001–025 migration bytes remain identical; no 026 or rule/budget/runtime/selector/deployed trust change.

Ruling: install the required leaf, not its source-only characterization module, which deliberately exercises the non-installed execution fixture. The focused test remains normally discovered in source; no monolithic fixture is added to installed payloads. Generic and Bitrix real materialization verify leaf byte identity plus fresh-process package and sibling imports; the exact installed test-path union gains only the helper. This does not claim a full installed PostgreSQL restart run.

## Fresh RED/GREEN commands and observations

Python tests used `PYTHONPATH=factory/src:.` and `taskset -c 12,13`. Synthetic fixture connection values are intentionally omitted.

- RED `python3 -m unittest factory.tests.test_postgres_fixture_reset -v`: five tests, eight failures (including subtests) for absent cursor seam/caller delegation before behavior edits. GREEN current helper+caller characterization proves exact SQL, one cursor operation, original exception object propagation, preserved suffix/seed parameters and caller-owned context exit on error. Recording cursors characterize the real caller functions; they are not represented as real PostgreSQL rollback evidence.
- RED `python3 -m unittest tests.test_installer.InstallerTests.test_installed_fixture_reset_leaf_is_byte_identical_and_importable tests.test_installer.InstallerTests.test_payload_is_sorted_safe_duplicate_free_and_profile_explicit -v`: two tests, three failures before the managed helper entry. GREEN: two tests in 2.608 s. Real generic/Bitrix materialization and both fresh-process import modes executed.
- Final focused `python3 -m unittest factory.tests.test_postgres_fixture_reset factory.tests.test_migrations -q`: 37 tests, 0.579 s, OK with one explicit DB-dependent skip. The five deterministic helper tests and 31 existing migration/target-guard tests ran; skip is not pass.
- `python3 -m factory.tests.postgres_restart_probe --preflight-only`: PASS exact disposable PostgreSQL identity.
- Real guarded `python3 -m unittest factory.tests.test_postgres_fixture_reset.FixtureResetPostgresTests factory.tests.test_execution_persistence_postgres.ExecutionPersistencePostgresTests.test_runtime_cannot_persist_noncanonical_packet_or_manifest factory.tests.test_execution_persistence_postgres.ExecutionPersistencePostgresTests.test_direct_runtime_enforces_capabilities_and_per_kind_limits -v`: three tests, 2.724 s, OK. Effects: full 025 ledger retained; reset empties fixture state; caller rollback restores seed; an exactly owned unlisted FK blocker causes atomic refusal rather than catalog cleanup/CASCADE; runtime TRUNCATE remains denied and rows retained; explicit committed reset works. The blocker and synthetic role were removed in that guarded fixture. After this run only three seed assertions were made repository-qualified for full-suite independence; final real-DB invocation of that assertion-only strengthening remains for the controller.
- Direct-script `python3 factory/tests/postgres_restart_probe.py`: PASS two actual PostgreSQL restarts, exact runtime/attestor roles, cancelled/orphaned recovery, ambiguous cleanup-fence replay, no fabricated proposal/result/attestation, higher M4 fence. It resolves the new sibling helper import.
- Scoped ruff on all six product paths: all checks passed. `git diff --check`: clean.

## Disposable fixture and resource limits

Only exact container ID `dec486345fdd4146c6ef87df8b653437de1517006f58d308b2d763540bc0ff2c`, name `adaptive-factory-exit-2d02ba9e25dc`, image `postgres:17-alpine`, nonce `2d02ba9e25dc20261003003400000000`; creation bounded to two CPUs/768 MiB and loopback-only port. Existing guard checks exact metadata, published port, factory_exit database/login, PostgreSQL 17/system identity and final PID1 postmaster. Actual restarts may change ports. Existing binding-checked `_remove_bound_container` removed only this container after tests; DB slot released to controller. No broad cleanup or production target operation.

New real-DB test connection statements/locks are bounded to 10 s/3 s; caller budgets remain unchanged. No production/backfill/query-plan change is introduced: the only SQL is the same owner-only disposable fixture TRUNCATE, which can take exclusive fixture locks. Unknown dependency fails closed. Future 026 handling is explicitly unimplemented and belongs to F.

## Exact-base budgets and remaining acceptance

Architecture drift and generated diagram checks pass; generated diagrams unchanged. Final `taskset -c 12,13 python3 scripts/grok_architecture.py fitness --base 63799f8760d3a55028d83ab5ff0116ececf8f7d1 --worktree --pre-risk red --json` passed with exit 0 after the assertion strengthening. Exact unchanged-policy byte/AST calculation on final six-path product inventory:

| Budget | Charged bytes / limit | AST / limit |
| --- | --- | --- |
| Architecture | 54,714 / 1,000,000 | 297 / 5,000 |
| All governed | 409,215 / 1,300,000 | 575 / 5,000 |
| Factory | 354,501 / 1,150,000 | 278 / 1,700 |
| Factory tests | 354,501 / 800,000 | 278 / 600 |

Factory source/contracts and pilot charged zero. Charge uses max(base,current) full file sizes and the actual fitness complexity-node definition, not changed lines or projected future bases. No policy limit was increased or hidden. Source/helper tests are normally discoverable and require final full verification; controller may bind the new test into the typed spec and refresh gates before that run.

Unexecuted: full individual PR verifier, independent reviews, final exact-tree receipts, full installed restart execution, production-scale locking, 026 compatibility, external App trust/approvals and release/publication. Source-only rollback restores the helper/caller imports/installer binding together; it is not a safe post-026 database downgrade. Frozen workflow scope/rollback/tasks remain controller-owned and unchanged by the writer.
