# Independent code review of head `ff3191c3` — verdict fail (2 block, 6 major, 3 minor)

Report retained from the wave's code reviewer; every item is dispositioned below.

| Finding | Disposition on the new commit |
| --- | --- |
| **[block]** `runner=subprocess.run` bound at import → `main()`'s reclaim escapes a patched `subprocess`; a reproduced `docker rm -f -v` fired from inside a unit test | Fixed: `runner`/`clock` default to `None` and resolve at call time. Pinned by `test_the_module_level_docker_call_cannot_escape_a_patched_subprocess`, which swaps the module attribute for a tripwire and asserts the real binary is never reached |
| **[block]** predicate used `name.startswith(prefix)` + "any non-empty nonce" → constructed deletion of `adaptive-factory-exit-helper-prod` carrying the label, the exact image and >2 h age | Fixed: fullmatch `adaptive-factory-exit-[0-9a-f]{12}` and nonce `[0-9a-f]{32}`, i.e. the identity contract the probe already enforces. Pinned by `test_a_labeled_persistent_database_outside_the_run_name_shape_is_never_deleted` (reviewer's own shape) |
| **[major]** no upper age bound: an RTC/NTP-forward clock or bogus `Created` marks a live sibling ancient and destroys it with its PGDATA volume | Fixed: `ORPHAN_MAX_AGE_SECONDS` (30 d) outside which age is untrusted and the candidate is skipped. Pinned by `test_an_age_beyond_the_trusted_window_is_not_trusted_enough_to_delete` |
| **[major]** reclaim budget counted deletions only; per-candidate inspect unbounded, and worst case blew the 600 s wall clock whose timeout is SIGKILL | Fixed: `RECLAIM_TIME_BUDGET_SECONDS = 120` with a `skipped-timeout` record. Pinned by `test_the_time_budget_stops_reclaim_before_it_can_consume_the_gate` |
| **[major]** `minted=not binding_verified` meant a verified run's cleanup needed a fresh successful inspect, so a transient daemon failure refused to delete this process's own container | Fixed: `minted=True` unconditionally in the finally (the id came from this process's own `docker run` stdout); the non-64-hex refusal stays for every caller |
| **[major]** `finally` restored handlers after removal, so any raise in removal leaked `_cancel_on_signal` into the process — and factory suites call `main()` in-process | Fixed: removal wrapped in its own `try/finally` so restore always runs |
| **[minor]** `leaked` printed only; a failed removal never aggregated anywhere | Fixed: `RECLAIM summary action=N` line, and the report returns the leaked count |
| **[minor]** non-64-hex listing line silently dropped, so reclaim could no-op without saying why | Fixed: recorded as `skipped` with the reason the identity cannot be proved |
| **[minor]** dead `_cleanup` (name-scoped `docker rm -f`, no `-v`) survived in `main`'s absence but kept a test, contradicting the exact-id claim | Deleted, with its test; deletion is exact-id scoped only |

Accepted with reasoning, not fixed: the reviewer's note that the "signal→exception makes the finally reachable" claim does not cover the gate's own SIGKILL at 600 s is correct and documented — an uncatchable kill still leaves the orphan to the next run's reclaim, which is why reclaim exists at all. The stated age-bound justification was wrong (real internal worst case ≈1210 s, not 480+30 s) and is corrected in the constant's comment; the margin is safe either way.

Confirmed by the reviewer as genuinely repaired: the rewritten binding-failure arm cannot pass on a no-op, and `git show cb9af407` proves the original asserted the leak.
