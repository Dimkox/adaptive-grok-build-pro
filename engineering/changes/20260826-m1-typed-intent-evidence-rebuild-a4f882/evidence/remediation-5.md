# Remediation 5 — blocked M1 review wave 5

The three `review-*_reviewer-5.md` reports in this directory are preserved verbatim as historical evidence for reviewed HEAD `25b9562144c774e125851019c02de6eca7a4a828`; their `BLOCKED` verdicts were not rewritten and no passing receipt was created. Remediation 4 now reports its unittest result precisely as 192 total, 10 skipped, and 182 executed successfully.

## Source repairs

- `GitWorkspace` now creates a private trusted Git configuration home beside, never inside, the checkout. Host global/system Git configuration is explicitly disabled, XDG configuration is isolated, and command-scope configuration neutralizes hooks and fsmonitor while retaining the authenticated HTTP header only for fetch operations.
- A real repository regression commits a root `.gitconfig` with executable fsmonitor, hooks, and external-diff settings, then exercises exact diff, reset, and status paths. No marker executes, exact LF-containing paths remain intact, authenticated configuration remains present, and cleanup removes the trusted configuration home.
- Bounded subprocess cleanup tracks the original process-group ID independently from leader lifetime. It applies a bounded TERM grace period, checks group existence, escalates surviving members to SIGKILL, reaps the leader, fails closed if the group survives, tolerates ESRCH races, and refuses to target the worker's own process group.
- Real-process regressions cover stdout overflow, stderr overflow, and timeout with a promptly exiting leader plus a same-group descendant that ignores SIGTERM. Every path returns only after the descendant is gone; test cleanup also prevents a failed oracle from leaking its probe.

## Status

- Root unit suite: 223 passed with the default invocation.
- Trust CI suite: 195 tests total, with 10 honest conditional PostgreSQL skips and 185 executed successfully because `TRUST_CI_TEST_DATABASE_URL` was not configured.
- Focused policy/runner/workspace checks, Ruff, diff whitespace, compileall with external bytecode storage, and holdout bundle identity checks passed on the remediation tree.

Full exact-commit verification and fresh route-selected reviews are still required before Task 6, AC-006, or source-ready status can complete; deployed holdout/worker/policy activation remains explicitly incomplete.
