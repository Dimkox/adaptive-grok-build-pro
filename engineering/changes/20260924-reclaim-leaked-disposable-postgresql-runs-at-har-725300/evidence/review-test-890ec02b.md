# Test review — does `tests/test_disposable_exit_reclaim` lock issue #128?

Reviewer role: test review, read-only on the candidate. No product edit, no commit, no push, no `grok_verify.py`.

| Identity | Value |
| --- | --- |
| HEAD | `890ec02b1502d1866aa4aaf0e328c1ea82710024` |
| Commit tree | `2e9b8ef4a3489abd648b270877a62a6747c9ece5` |
| Harness blob | `eb19e33622485751bdc846318003c7ff806511f3` `factory/tests/run_disposable_exit.py` |
| Test blob | `bda43d38b7c54940a860ede9e1a4b0b9e350067e` `tests/test_disposable_exit_reclaim.py` |
| Content sha256 of both the HEAD harness and the scratch copy | `0693b4e83fe4160301dde660d77e28a6d232f27c28242f67859fcd69f8977a98` (equal) |
| Worktree before this report | product blobs matched HEAD; only pre-existing untracked `evidence/next-gap.md` |
| Scratch | `/home/pall/.cache/grok-test-review-128-890ec02b` (`drwx------`, not sticky). Mutants were copies under that parent. The candidate worktree was not edited. |

Issue [#128](https://github.com/Dimkox/adaptive-grok-build-pro/issues/128) requires four things: reclaim labelled disposable containers and volumes at harness start when they are older than a documented bound and are not this run's nonce, and log each decision; turn cancellation into an exception so the existing `finally` runs and the dependency on `verify()` is stated; a test arm that leaves an orphan and asserts the next invocation reclaims it before creating its own container; no host cron.

Baseline on the candidate and on the unmodified scratch copy:

`python3 -m unittest tests.test_disposable_exit_reclaim`

`Ran 37 tests in 0.017s` / `OK` (both trees). All 37 methods are collected when the module is imported. That green run is not a lock.

## Claims probed

Each mutant was applied only to a scratch copy of `factory/tests/run_disposable_exit.py`. The suite was `python3 -m unittest tests.test_disposable_exit_reclaim` with cwd set to that copy. Killed means the suite exited non-zero. Survived means `OK`.

| Mutant | Result | Observed |
| --- | --- | --- |
| Delete the startup `reclaim_orphan_runs(nonce)` call and the unproven-leak abort | KILLED | `test_main_reclaims_and_installs_handlers_before_it_creates_anything`, `test_unproven_startup_reclaim_stops_before_a_new_container_is_created` |
| Move that call to after `bound_container_id = container_id` | KILLED | same two tests |
| Call `reclaim_orphan_runs(nonce, min_age_seconds=10**12)` | **SURVIVED** | 37 OK. Direct effect of those arguments on a 3 h labelled orphan: `removals=[]`, `records=[]` |
| Call `reclaim_orphan_runs(nonce, limit=0)` | **SURVIVED** | 37 OK. Same orphan: `removals=[]`, action `skipped-limit` |
| Drop `if age < min_age_seconds: return None` | KILLED | sibling, stale-orphan, and report-count tests |
| Drop `if nonce == current_nonce: return None` | KILLED | `test_this_runs_own_nonce_is_never_a_candidate`, `test_a_run_younger_than_the_bound_with_my_nonce_is_never_a_candidate` |
| Drop `if age > max_age_seconds` | KILLED | `test_an_age_beyond_the_trusted_window_is_not_trusted_enough_to_delete` |
| `_cancel_on_signal` returns instead of raising | KILLED | `test_sigterm_becomes_an_exception_that_runs_the_finally`, `test_cancellation_exits_non_zero_and_still_reclaims_its_container` |
| `except HarnessCancelled` returns 0 | KILLED | both cancellation `SystemExit` tests |
| Reclaim `docker rm -f` without `-v` | KILLED | stale-orphan and unavailable-postcheck tests |
| Any non-zero inspect counts as absent | KILLED | `test_failed_removal_plus_unavailable_postcheck_is_never_reclaimed` |
| `docker ps` listing omits the label filter | KILLED | `test_the_listing_is_requested_untruncated_and_label_filtered` |
| `docker run` omits `--cidfile` | KILLED | `test_cancellation_during_docker_run_recovers_the_predeclared_cidfile` |
| Delete the `#119` / `verify()` dependency paragraph | KILLED | `test_the_harness_declares_its_dependency_on_the_caller_raising` |
| Drop `image != DISPOSABLE_IMAGE` | **SURVIVED** | 37 OK. A `postgres:9.6` container with a valid 12-hex name and 32-hex nonce was then `reclaimed` |
| Drop `RUN_NONCE.fullmatch` | **SURVIVED** | 37 OK. Nonce `not-a-nonce` on a valid name and the disposable image was then `reclaimed` |
| Treat `age is None` as `min_age_seconds + 1` and continue | **SURVIVED** | 37 OK. Created `not-a-time` was then `reclaimed`. Baseline copy of the same fixture stays `skipped` / `unparsable creation time` |
| Replace `cancellation.restore()` in `main` with `pass` | **SURVIVED** | 37 OK |
| `finally` calls `_remove_bound_container(..., minted=False)` | **SURVIVED** | 37 OK |

The two call-site survivors are the issue lock. `test_main_reclaims_and_installs_handlers_before_it_creates_anything` replaces `reclaim_orphan_runs` with a spy that records only that the name ran, before `docker run`. It does not execute the real function and does not check the nonce or the age, limit, or budget arguments. The helper tests call `reclaim_orphan_runs` themselves, with explicit `runner`/`now` and the function defaults. Nothing in this module fails if `main` passes a threshold or a limit that reclaims nothing. That is the regression #128 asked to pin: an orphan left by a cancelled run is not removed before the next container is created. One argument at the only production call site restores it, and the suite stays green.

`test_a_foreign_image_under_an_exit_prefix_shape_is_not_deleted` does not lock the image predicate. Its fixture nonce is `other`, which already fails `RUN_NONCE`, so deleting the image comparison still yields `foreign run shape` and zero removals. The same gap is why dropping the nonce fullmatch survives: the persistent-database fixture is rejected by the name regex, and the foreign-image fixture is rejected by its nonce. Both are named as if they pinned AC-002 / FORBID-001. They do not.

`test_unparsable_or_empty_creation_time_is_unknown_not_zero` only checks `_observed_age_seconds`. No reclaim fixture feeds a bad timestamp, so a reclaim path that deletes when age is unknown stays green. On the baseline copy that same fixture is skipped.

`test_sigterm_becomes_an_exception_that_runs_the_finally` and `test_handlers_are_restored_even_when_nothing_installs_them_twice` restore the scope object themselves. No test reads `signal.getsignal` after `main()`. Removing `cancellation.restore()` from `main` therefore survives, including the in-process handler leak the harness comment says the factory suite must not keep.

`minted=False` survives here because the cancellation tests either ignore `**kwargs` or present a matching binding, so removal still happens. Ownership-from-creation when the binding check fails is not locked by this module. The assertion `remove.call_args.kwargs["minted"] is True` lives in `factory/tests/test_migrations.py::test_exit_runner_reclaims_its_own_container_when_binding_fails`. That file was read, not executed, and it is outside the module this review was asked to judge.

## What this module does lock

The helper predicate, when called with its own defaults, cannot drop the age floor, the current-nonce exclusion, the max-age ceiling, `-v`, the label filter, or the "generic Docker failure is not absence" rule without going red. `main` must still mention `reclaim_orphan_runs` before `docker run`, must install a handler that raises, must exit non-zero on `HarnessCancelled`, must pass a cidfile through cancellation-during-create, and must keep the `#119` / `verify()` sentences. Those kills are real. They are not the integrated arm the issue required.

## Unexecuted claims

- Issue item 4 / INV-002 (no host cron, sweeper, or broad `docker prune`): no test asserts that absence. A static read of `factory/tests/run_disposable_exit.py` found no `cron`, `crontab`, or `prune` text. No mutant added one.
- Direct script execution. `unittest.main()` is at line 567 and `ReclaimWiringTests` is defined at line 571. Import collection runs all 37 tests; this review did not execute the file as `__main__`. Script execution would not collect the six wiring tests. That is a footgun, not the fail above.
- `factory/tests/test_migrations.py` was not run.

reviewed-tree-modified: no

VERDICT: FAIL
