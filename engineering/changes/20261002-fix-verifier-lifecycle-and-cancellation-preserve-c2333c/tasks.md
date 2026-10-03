# Concrete work and ownership

1. Controller: record CPU discovery, route c2333ca04e25 and initial selector; preserve four independent analysis reports. Done before writer dispatch.
2. Sole selected writer: inspect current boundaries and historical source deltas path-by-path; write fresh fault controls and observe RED. Done.
3. Sole selected writer: implement owned runner cancellation/cleanup, partial check retention, finalization envelopes and durable HEAD-bound receipts. Done.
4. Sole selected writer: run focused recovery plus existing runner/verifier/receipt suites; lint and diff hygiene; persist exact results in evidence/implementation-general_implementer.md. Done:172 focused tests pass, lint/spec/diff checks pass.
5. Sole selected writer: commit only this contour and package; merge actual origin/main after the scoped clean commit. Done: scoped40f754380f61bd299296f5c50ee34858c2505478; base63799f8760d3a55028d83ab5ff0116ececf8f7d1; mergeHEAD30297838c1a08a0ebe3944af07dfb69968202587.
6. Controller: initial full PR gate passed on that merge HEAD; both independent reviews then failed on the output-file-close boundary. Those complete reports are preserved without rewriting their findings. Initial gate/reviews are historical for the repair and do not authorize completion.
7. Sole selected writer: reproduce output-close loss with six regression methods, protect both output contexts, run focused controls, preserve failed reports and repair evidence, and commit a clean handoff. Fresh RED:6 tests/16 errors; GREEN:6 tests then30 recovery/lifecycle tests. Exact commands, bytes and limits are in evidence/output-close-repair.md.
8. Controller: collect contours into the user-approved combined source PR (artifact PR separate), run fresh full verification and all selected independent reviews on the exact aggregate HEAD, refresh receipts, then enforce external Trust CI/approvals. No individual full-suite rerun, push or external write is performed by this writer.

No additional writers or agents were spawned in this candidate. Tests use two pinned CPUs and fixture-owned maximum two xdist workers; all prior dirty source worktrees stay untouched.
