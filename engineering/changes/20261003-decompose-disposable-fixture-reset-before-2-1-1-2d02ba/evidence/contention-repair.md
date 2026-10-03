# Scoped contention acceptance repair

Sole data_implementer, same route `2d02ba9e25dc`, branch `refactor/v211-disposable-fixture-reset`. Follow-up to clean `783542d9e972ea782d1350911f37efe2fcae0695`; comparison base remains actual `63799f8760d3a55028d83ab5ff0116ececf8f7d1`. Controller's refreshed frozen AC-006 scope/local disposable-plan gates were read before repair. Controller retains full verifier, independent reviews, final exact-tree receipts and external trust authority.

## Fresh startup and diagnosis

2026-10-03T00:47:54Z measurement recorded locally before route inspection: lscpu shows14 physical cores/28 online logical CPUs0-27; nproc-all28, default22, affinity0,1,8-27. Actual cgroup v2 membership `/user.slice/user-1000.slice/session-2050.scope`, mount `/sys/fs/cgroup`; inherited effective cpuset0-27; session/user-1000/user.slice cpu.max=`max 100000`, no finite root quota. Child-only taskset0-27 probe returned28 CPUs/affinity0-27 in the same cgroup; parent affinity unchanged. Verified effective capacity28, assignment12,13/max2 focused test workers plus one2-CPU/768-MiB fixture; no subagents or per-contour full gate. Commands: date -u, lscpu -e, nproc --all/nproc, taskset -pc, /proc/self/cgroup, findmnt and membership/ancestor cpuset/quota reads, bounded child affinity probe.

The preserved controller diagnosis `hb-contention-diagnosis.md` is prior exact-HB evidence, not a current candidate pass: winner COMMIT/WalSync retained the counter lock beyond the unchanged500ms contender budget. Original executor.map aborted before canonical SQL assertions on a legitimate LockNotAvailable→StoreUnavailable refusal. Slow WalSync cause remains undiagnosed; this is a test-acceptance repair, not a production runtime defect or operational qualification.

Original historical initial selector remains the package's exact draft receipt; no repeat or extra skip permission. Executable product inventory requires the controller's fresh full gate.

## Minimal product repair

Only follow-up product path: `factory/tests/test_execution_persistence_postgres.py`, already in approved source contour. Test-only `_claim_recovery_or_lock_refusal` returns an explicit refusal only for StoreUnavailable with direct psycopg.errors.LockNotAvailable cause, and rethrows all other failures. Both initial futures finish; acceptance requires exactly one actual ExecutionRecoveryClaim, rejects other return types, and retains all original terminal-stage/job/claim/release-event/audit SQL counts. A refused attempt gets one fresh bounded call after initial contention ends, which must return None rather than another claim. No whole-test retry, backoff policy, production retry or timeout relaxation.

Deterministic controls cover explicit typed refusal plus unrelated StoreUnavailable without cause, wrapped QueryCanceled/UniqueViolation/OperationalError, and direct integrity/timeout/SQL errors. A real-PG injected refusal executes the actual repaired method, its real winning transaction and fresh retry, and all unchanged canonical SQL assertions; it is explicitly injection, not a fabricated actual SQL refusal. The separate positively confirmed holder causes the actual SQL refusal.

## RED/GREEN evidence

Commands use `PYTHONPATH=factory/src:. taskset -c 12,13`.

- RED `python3 -m unittest factory.tests.test_execution_persistence_postgres.RecoveryContentionAcceptanceTests -v`:2 tests,1 expected failure `typed lock refusal aborted concurrent acceptance`; unrelated-error control passed. Transparent test-only seam initially retained original direct-call/abort policy.
- GREEN same2 tests: pass, including8 unexpected-error subcases with original exception identity. Final focused `python3 -m unittest factory.tests.test_execution_persistence_postgres.RecoveryContentionAcceptanceTests factory.tests.test_postgres_fixture_reset factory.tests.test_migrations -q`:39 tests in0.173s, OK/one explicit DB-dependent skip. Skip is not pass.
- Existing `_assert_disposable_target` plus final-postmaster readiness: PASS before real tests. One selected unittest invocation ran4 actual PG tests in5.064s, OK/no skips: `FixtureResetPostgresTests.test_025_effects_rollback_unlisted_fk_and_runtime_refusal`; `ExecutionPersistencePostgresTests.test_confirmed_recovery_lock_refusal_rolls_back_then_retries_once`; `.test_two_reconcilers_preserve_sql_assertions_after_injected_lock_refusal`; `.test_two_reconcilers_create_one_terminal_stage_and_cleanup_claim`.
- Holder control positively observed claimant blocked by exact holder PID via pg_blocking_pids, then retained the lock for600ms under a2s server-side holder transaction ceiling. Actual typed refusal left counts `(0,0,0,0,0)`, run/allocation unreleased, capacity1. After holder release, a fresh call returned actual claim with counts `(1,1,1,1,1)`, release flags set/capacity0; another call returned None with those effects unchanged. Absence of confirmed blocking fails rather than becoming success. No retries until test pass.
- Final 025 reset control above freshly covers the three repository-qualified seed assertions that were unexecuted at the previous handoff. Owner reset/rollback, unlisted-FK refusal, runtime denial and migration ledger preservation pass.
- Scoped ruff all six product paths: all checks passed; git diff --check clean. AST comparison against actual base proves both reset caller functions identical after stripping only their shared reset operation. Third integration fixture and resources001-025 have empty exact-base diff; no026.

## Exact disposable lifecycle and limits

An initially malformed manually counted13-character name was refused before any test/DB mutation; exact guarded cleanup removed ID `59adf88e79bf1eff081183b90500b1a73d3ee6320bbe979ce444aa66cf113df0`. Name/nonce regexes were then positively checked before creation; guards were not changed.

Actual test fixture: ID `907fcc65c88ab64f1e4c409dcb67cbc919168ca2fcec7312bb5da593e46b277a`, name `adaptive-factory-exit-2d02bac0ffee`, nonce `2d02ba9e25dc20261003010000000000`, postgres:17-alpine, --cpus=2/--memory=768m, dynamically allocated loopback-only port, factory_exit DB/login. Exact ID/name/image/nonce/port/server/final-postmaster guard passed. Existing `_remove_bound_container` completed in finally after the4-test run; DB slot released. No DSN/password, broad cleanup or live-state operation is recorded/performed.

## Exact-base budgets and remaining work

Final `taskset -c 12,13 python3 scripts/grok_architecture.py fitness --base 63799f8760d3a55028d83ab5ff0116ececf8f7d1 --worktree --pre-risk red --json`: exit0/fitness_status pass, no code-budget findings. Charged full-file bytes use max(base,current), AST uses actual fitness complexity nodes on final changed sources: architecture54,714bytes/297AST; all governed415,954/593; factory/tests361,240/296 (limits unchanged: all1.3m/5000, factory1.15m/1700, tests800k/600). Source/contracts/pilot charged zero. Assembled successor budgets are controller-owned and must be freshly measured, not inferred from this isolated contour.

Unexecuted: current full PR suite/coverage/restart runner, independent reviews and final receipts, exact assembled-core fitness, production I/O cause/performance,026 and live/release/external trust acceptance. Prior two actual restart/installed-binding controls remain historical evidence at783542d9e, with those product paths unchanged in this follow-up; they are not fresh full-candidate verification. No scope files changed by writer; controller's frozen scope/gate updates are committed with this repair. Source rollback restores this test-only acceptance diff, retaining unchanged runtime/migrations/guards. Skills influenced the work through deterministic RED, cause-specific minimal repair and evidence-bound focused verification; no self-review or completion authority claimed.
