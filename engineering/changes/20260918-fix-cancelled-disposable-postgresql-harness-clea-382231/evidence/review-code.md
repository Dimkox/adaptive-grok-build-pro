# Code review — #128 follow-up

**Verdict: PASS.** The final follow-up closes both reviewed findings: TERM grace strictly exceeds the conservative harness-unwind bound, the worst-case modeled total stays below the unchanged outer cap, and the orphan-reclaim candidate allowance is shared globally across resource categories.

## Findings

- The regression now derives a conservative 100-second unwind bound: process-group stop/reap allowance, bounded delayed name resolution, exact container validation/removal, and exact volume validation/reference-check/removal. `_FACTORY_EXIT_TERM_GRACE` is 101 seconds and the assertion is strict (`assertGreater`).
- The outer work window is `600 - 110 = 490` seconds. Adding 101 seconds TERM grace, 2 seconds escalation wait, 5 seconds forced reap, and 0.05 seconds polling gives **598.05 seconds ≤ 600 seconds**. The 110-second cleanup reserve also covers TERM + escalation + reap (108 seconds).
- `_reap_orphans` initializes one `_REAP_CANDIDATES` allowance. A reclaimed container+volume bundle consumes one slot before the detached-volume sweep; remaining detached volumes are limited by the remaining allowance. The regression confirms a reclaimed bundle prevents a detached-volume reclaim in the same invocation and reports backlog.

## Verification

- Focused regressions for the strict TERM/unwind and outer-cap invariant, shared cross-resource reclaim cap, and bounded one-candidate backlog — **3 passed**.
- `git diff --check` — **passed**.
- No full verifier or live Docker/PostgreSQL run was performed.
