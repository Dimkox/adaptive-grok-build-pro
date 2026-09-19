# Data review — #128 disposable PostgreSQL lifecycle

**Final result: PASS — no remaining data ownership, cleanup-bound, or shared-reaper-budget findings.** Reviewed tree fingerprint `e12d9925347349c9cbd03d629aced311a31918d427da436d98e4831be988c1ae` in `/tmp/adaptive-fix-disposable-exit`; recomputing `tree_fingerprint()` before this report update produced the same value. No product files were changed, and no full verifier or live Docker/PostgreSQL was run.

## Cancellation cleanup bound

The test `tests/test_verification_doctor.py::test_factory_exit_term_window_covers_harness_cleanup_within_outer_cap` derives a conservative 100-second harness unwind from the actual configured bounds:

`5s process-group TERM + 5 × 5s bounded kill/reap windows + 5s name resolution + 2 × 5s container validation + 20s container removal + 3 × 5s volume validation/reference checks + 20s volume removal = 100s`.

The final outer wrapper uses `_FACTORY_EXIT_TERM_GRACE = 101s`, and the test asserts strict `>` against that bound. `_FACTORY_EXIT_CLEANUP_RESERVE = 110s` covers the 101s TERM period, 2s escalation wait, 5s forced reap and 50ms outer polling quantum. With 490s work budget, the calculated maximum is `490 + 101 + 2 + 5 + 0.05 = 598.05s`, below the unchanged 600s outer cap. The corresponding test asserts the reserve and cap inequalities.

The prior P2 allegation about the `Popen` OSError branch was incorrect: that return is nested inside the `try` whose `finally` at `verification.py:445-447` restores both prior signal handlers. No handler-restoration finding remains.

## Shared recovery budget and ownership

`_reap_orphans` initializes one `reclaim_budget` before container recovery, decrements it only after a successfully reclaimed stale container+volume bundle, then uses the remaining budget for detached stale volumes. `factory/tests/test_migrations.py::test_exit_runner_shares_reclaim_candidate_budget_across_resource_types` models one stale container bundle and a separate detached stale volume; it expects only the bundle removed and checks there is no `docker volume rm` for the detached volume.

The safety boundary remains exact and fail-closed: containers are matched by full ID, name, image, nonce label and exact volume mount before removal; volumes are matched by exact name, local driver and nonce label, checked for container references, and revalidated before deletion. Ambiguous identity and reference/list failures preserve resources. Listing output and inspected rows remain capped, and stale recovery uses the documented 30-minute TTL.

No production or durable factory database/schema change was introduced; the migration-related diff is confined to tests in `factory/tests/test_migrations.py`.

## Scope and evidence

Independent static review of the frozen source and focused test definitions. The focused tests were not executed in this review. No Docker or PostgreSQL service was started.
