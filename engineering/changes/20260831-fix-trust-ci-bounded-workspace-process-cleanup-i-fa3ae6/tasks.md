# Tasks — Fix Trust CI bounded workspace process cleanup in the immutable read-only runner: zombie-only descendants after SIGKILL must not mask the original stdout/stderr/timeout failure, while live or uncertain survivors remain fail-closed. Deliver as an isolated stacked Trust-CI-only bugfix on M2 with regression tests.

- [x] Freeze contracts, scope, rollback, observability, and expected behavior.
- [x] Capture deterministic RED for zombie-only, live, and uncertain outcomes.
- [x] Implement the bounded classifier without changing TERM/KILL/reap.
- [x] Run focused workspace, diff, spec, and pinned-runner checks.
- [x] Stabilize the frozen-adoption receipt test to assert binding evidence rather than cumulative stacked-branch fitness.
- [x] Address TR-001 with direct deterministic classifier tests for parser, member state, races, bounds, deadline, and final-probe outcomes.
- [ ] Run the route verifier and independent code/test reviews on the final fingerprint.
- [ ] Bind final evidence and retain PR App-owned exact-SHA check as a separate merge gate.
