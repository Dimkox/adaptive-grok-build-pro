# Code review — disposable PostgreSQL container reclaim

- Repository: `/home/pall/grok-projects/adaptive-grok-build-reclaim128`
- Branch: `fix/issue-128-disposable-container-reclaim`
- HEAD: `890ec02b1502d1866aa4aaf0e328c1ea82710024`
- Commit: `890ec02b` `fix: prove disposable container cleanup outcomes`
- Comparison base used for scope: merge-base `5713b407818dbb6c2d1acfcb0b0d9661c32e1153` (`origin/main`)
- Reviewer: read-only except this report. Product code was not edited. No commit, no push, `scripts/grok_verify.py` was not run.

## Verdict

No blocking defect in the reclaim predicate, the minted-id cleanup path, or the cancellation path. The implementation matches the change-spec acceptance criteria on this HEAD: label-scoped startup reclaim, trusted age window, exact name/image/nonce shape, tri-state removal proof, cidfile recovery, and non-zero cancellation.

`reviewed-tree-modified: no`

VERDICT: PASS

## Candidate identity

Worktree status before this report, from `git status --porcelain=v1`:

```
?? engineering/changes/20260924-reclaim-leaked-disposable-postgresql-runs-at-har-725300/evidence/next-gap.md
```

That untracked note is not part of HEAD and is not product code. This report is the only file written by the review.

Source hashes of the executable reclaim surface, taken from the worktree before any scratch copy:

| Path | sha256 |
| --- | --- |
| `factory/tests/run_disposable_exit.py` | `0693b4e83fe4160301dde660d77e28a6d232f27c28242f67859fcd69f8977a98` |
| `factory/tests/test_migrations.py` | `d1e456cf88326e63cdc3f03ada5fd26d641ddf0976b2ff60240007e767ac3760` |
| `tests/test_disposable_exit_reclaim.py` | `bc19e106beb1239f5be56d7f44699a6745dfc6d99580497c2ca8023b2d74f090` |

Scratch copy (not a second worktree, not mutated): `/home/pall/.review-scratch-890ec02b`, mode `0700`, parent `/home/pall` mode `750` and not sticky. The copy contains those three files plus `factory/tests/__init__.py`. Differential mutants were not applied. See unexecuted claims.

## What was reviewed

Startup reclaim and exact-id cleanup in `factory/tests/run_disposable_exit.py`, the hermetic arms in `tests/test_disposable_exit_reclaim.py`, and the harness contract in `factory/tests/test_migrations.py` (`test_exit_runner_orders_bound_preflight_before_mutating_suite`, `test_exit_runner_reclaims_its_own_container_when_binding_fails`, `test_exit_runner_container_binding_and_cleanup_are_exact_id_scoped`, `test_exit_runner_never_deletes_by_name_when_container_creation_fails`). Change-spec AC-001..AC-005, INV-001..INV-003, and FORBID-001..FORBID-003 were the acceptance bar. Docs were checked only where they state a safety property the code must keep.

## Claims probed

Executed on the candidate (not on a mutant):

```
python3 -m unittest tests.test_disposable_exit_reclaim \
  factory.tests.test_migrations.MigrationTests.test_exit_runner_reclaims_its_own_container_when_binding_fails \
  factory.tests.test_migrations.MigrationTests.test_exit_runner_container_binding_and_cleanup_are_exact_id_scoped \
  factory.tests.test_migrations.MigrationTests.test_exit_runner_never_deletes_by_name_when_container_creation_fails \
  factory.tests.test_migrations.MigrationTests.test_exit_runner_orders_bound_preflight_before_mutating_suite
```

Observed: `Ran 41 tests in 0.022s` / `OK`. One uncaptured startup line was printed by the binding-failure migration test, which does not stub `reclaim_orphan_runs` and therefore feeds the mocked container id into `docker ps`:

```
RECLAIM skipped container=aaa… name=unknown … reason=cannot inspect
RECLAIM summary skipped=1
```

That is fail-closed (field count is not 6, so no `docker rm`). The test still requires `_remove_bound_container(..., minted=True)` for the minted id. Not a product defect.

| Claim | Result |
| --- | --- |
| Stale labelled run inside the age window is `docker rm -f -v` and reported `reclaimed` only after a no-such-object/container post-check | Passed in `test_a_stale_labeled_orphan_is_reclaimed_and_reported` and `test_failed_removal_plus_unavailable_postcheck_is_never_reclaimed` |
| Younger sibling and the current nonce are not removed | Passed in `test_a_concurrent_sibling_inside_the_age_bound_is_never_touched` and `test_a_run_younger_than_the_bound_with_my_nonce_is_never_a_candidate` |
| Foreign name shape, including `adaptive-factory-exit-cache-prod`, is skipped and not deleted | Passed in `test_a_labeled_persistent_database_outside_the_run_name_shape_is_never_deleted` |
| Age above `ORPHAN_MAX_AGE_SECONDS` is not deleted | Passed in `test_an_age_beyond_the_trusted_window_is_not_trusted_enough_to_delete` |
| Per-run count and time budget stop further removals | Passed in `test_the_reclaim_budget_bounds_one_invocation` and `test_the_time_budget_stops_reclaim_before_it_can_consume_the_gate` |
| `runner`/`clock` resolve at call time, so a patched `subprocess` is the function that runs | Passed in `test_the_module_level_docker_call_cannot_escape_a_patched_subprocess` |
| SIGTERM becomes `HarnessCancelled`, `finally` runs, handlers restore, cancellation exits 130 and still removes the minted id | Passed in `CancellationReachabilityTests` and `test_cancellation_exits_non_zero_and_still_reclaims_its_container` |
| Cancellation during `docker run` removes the id written to the private cidfile | Passed in `test_cancellation_during_docker_run_recovers_the_predeclared_cidfile` |
| A `leaked` startup record refuses `docker run` | Passed in `test_unproven_startup_reclaim_stops_before_a_new_container_is_created` |
| Well-formed contradictory metadata refuses minted deletion; structured failure or malformed metadata does not | Passed in `test_minted_removal_refuses_when_the_daemon_says_it_is_not_ours`, `test_transient_structured_inspect_then_id_only_recovery_does_not_mean_foreign`, `test_malformed_structured_inspect_is_unknown_not_positive_foreign_identity` |
| Binding failure still reclaims with `minted=True` and does not start the suite; creation failure does not `docker rm` by name | Passed in the two migration arms above |
| Own removal is `docker rm -f -v <64-hex>` and success requires the post-inspect absence stderr | Passed in `test_exit_runner_container_binding_and_cleanup_are_exact_id_scoped` and `test_a_container_that_survives_removal_is_reported_leaked_and_raises` |
| Age floor is larger than readiness + suite + two restart-probe ceilings (`30+480+2*300 < 7200`) | Passed in `test_the_orphan_bound_exceeds_the_real_durations_not_a_restated_literal` |

Static reading agrees with those results. `reclaim_orphan_runs` deletes only after a 64-hex id, `postgres:17-alpine`, `^adaptive-factory-exit-[0-9a-f]{12}$`, `^[0-9a-f]{32}$`, a nonce other than the current one, and an age in `[ORPHAN_MIN_AGE_SECONDS, ORPHAN_MAX_AGE_SECONDS]`. `_container_observation` maps only a non-zero inspect whose stderr matches `no such object|container` to `absent`; any other failure stays `unknown` and is reported `leaked`. `main` aborts before `docker run` when the leaked count is non-zero. `finally` always passes `minted=True`, refuses only `not-ours`, and reads the cidfile when stdout never bound an id. Signal restore is in an inner `finally`, so a removal error cannot leave `_cancel_on_signal` installed. No cron, prune, or name-scoped `docker rm` was reintroduced.

## Mutants

Not executed. A follow-up shell probe that would have rewritten the scratch harness and re-run the suite was denied by the local shell circuit breaker and was not retried. No mutant was applied, so there is no killed/survived/inconclusive differential result. The scratch file was left as the unmodified copy (`RESTORE` was not needed). Predicted suite outcomes below are static, not measurements:

| Mutant | Prediction from the tests as written | Note |
| --- | --- | --- |
| Replace `CONTAINER_NAME.fullmatch` with `startswith(CONTAINER_NAME_PREFIX)` | Killed by `test_a_labeled_persistent_database_outside_the_run_name_shape_is_never_deleted` | Safety predicate is pinned |
| Drop the max-age return | Killed by `test_an_age_beyond_the_trusted_window_is_not_trusted_enough_to_delete` | Pinned |
| Treat any non-`present` post-check as `reclaimed` | Killed by `test_failed_removal_plus_unavailable_postcheck_is_never_reclaimed` | Pinned |
| Treat `unknown` ownership as refusal | Killed by the transient and malformed minted-cleanup arms | Pinned |
| Drop `age < min_age_seconds` | Killed by the sibling arm | Pinned |
| Drop `nonce == current_nonce` | Killed by `test_a_run_younger_than_the_bound_with_my_nonce_is_never_a_candidate` (`min_age_seconds=0`) | Pinned. `test_this_runs_own_nonce_is_never_a_candidate` does not pin it: that fixture is 10s old, so the age floor alone would spare it |
| Drop the image conjunct only | **Would survive the suite** | `test_a_foreign_image_under_an_exit_prefix_shape_is_not_deleted` sets `nonce='other'`, which already fails `RUN_NONCE`. The image conjunct is still present in the product condition |
| Drop the nonce-shape conjunct only | **Would survive the suite** | No old, correctly named, correct-image fixture uses a nonce that is neither the current nonce nor 32 hex |
| Drop the non-64-hex guard in `_remove_bound_container` | **Would survive the suite** | The guard is implemented (`refusing to delete a container id this process did not mint`). The test plan names `test_minted_removal_skips_the_binding_check_but_not_the_id_shape_check`, and that test is not in the tree |
| Resolve `docker_run` through an import-time binding | Killed by the tripwire, which calls `reclaim_orphan_runs('mine')` with no runner | Not re-run as a mutant, because a bad mutant would reach the real Docker socket. The unmutated tripwire passed |

The three predicted survivors are test gaps, not observed product mis-deletions. On the unmutated source, a foreign image and a non-32-hex nonce both fall through the same `foreign run shape` return before `docker rm`, and a short id raises before `subprocess.run`.

## Unexecuted claims

- Differential mutation of the scratch harness. Blocked before execution; not retried. Scratch safety was established (copy outside the worktree, mode `0700`, non-sticky parent) but no mutant process ran.
- Live `docker` behavior: no daemon calls were made. Absence matching is pinned to the stderr regex the tests feed, not to a live Docker version string.
- `python3 scripts/grok_verify.py` was intentionally not run.
- A second fingerprint command after the unit run was not issued. No product path was written by the reviewer before this report, so the candidate bytes above are the reviewed bytes. This report is the sole added worktree path.

## Non-blocking limitations

1. The 120s budget is checked only between candidates, and the comparison is `>` rather than `>=` (`reclaim_orphan_runs`). One candidate already inside the budget can still spend its own `docker inspect` (15s) + `rm` (60s) + `inspect` (15s). Worst case is about 180–210s, not 120s. That stays under the caller's 600s SIGKILL, and the time-budget test allows one in-flight removal, but a full graveyard plus `docker run` can shrink the 480s suite window. SIGKILL still skips `finally`; the next run's age sweep is the backstop the design already accepts.
2. `docker ps` failure returns `[]` with no `RECLAIM` line (`listed.returncode != 0`). A failed post-removal inspect stops startup; a failed listing does not. Nothing is deleted. A later `docker run` is the practical backstop if the daemon is down.
3. Stdout/cidfile disagreement raises before `bound_container_id` is set, and `finally` then removes only the cidfile id. The stdout id is not passed to `_remove_bound_container`. Honest Docker writes the same id to both. If they ever diverge, one id can leak until it is older than two hours; a cidfile id whose structured inspect is `unknown` can still be removed under the minted tri-state rule.
4. `_binding_observation` hardcodes `"postgres:17-alpine"` while reclaim uses `DISPOSABLE_IMAGE`. They are the same string today. If only the constant changed, startup binding would fail and minted cleanup would treat the new image as `not-ours` and refuse to delete the container just created.
5. `RESTART_PROBE_TIMEOUT_SECONDS` is not passed into `_run`. The probe calls use the default `timeout=300`, which matches the constant. `test_the_orphan_bound_exceeds_the_real_durations_not_a_restated_literal` compares constants to each other, not to that default.
6. Young valid siblings and the current nonce return `None` and are omitted from the decision log. That matches the tests and does not delete anything. The docstring on `reclaim_orphan_runs` still says every candidate yields an entry.
7. Age equality uses `age < min` / `age > max`, so an age exactly equal to the two-hour floor is eligible. The requirements text says "older than". At a two-hour boundary, with a 600s caller kill, this does not cut off a live sibling. The tests treat the floor as inclusive.
8. `tests/test_disposable_exit_reclaim.py` calls `unittest.main()` before `ReclaimWiringTests` is defined. Import/discover, which is how the suite above ran, still loads that class. Running the file as `__main__` would exit before those arms exist.

## Accepted tradeoff, not a defect

`decisions.md` (2026-09-26) and AC-004 say only well-formed contradictory metadata is `not-ours`. `_verify_ownership` therefore deletes a minted id when structured inspect is `unknown` and an id-only inspect either fails or echoes that same id. A spoofed `docker run` stdout that names a foreign id is refused when that inspect returns a readable different name, image, or nonce. It is not refused when the structured inspect cannot be parsed. That is the leak-versus-foreign-delete choice the tests lock in. FORBID-001 is narrower than this tri-state rule; the code follows AC-004, not a positive proof of label on the unknown path.

`reviewed-tree-modified: no`

VERDICT: PASS
