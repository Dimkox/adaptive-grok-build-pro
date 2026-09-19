# Tasks — Fix cancelled disposable PostgreSQL harness cleanup, orphan recovery, and timeout reporting (#128)

- [x] Freeze contracts and expected behavior, including the generic verifier command timeout tree.
- [x] Add failing tests for descendant timeout and cancellation cleanup, delayed exact name lookup, byte-overflow backlog reporting, and bounded Docker listing.
- [x] Implement bounded process-group stop/reap on timeout and cancellation, cleanup retry, and safe listing overflow/backlog behavior.
- [x] Enforce strict cleanup TERM headroom over the conservative harness unwind bound, fit escalation/reap/poll windows within the 600-second cap, and share one reaper candidate allowance globally across resource categories; follow-up regressions and the final two-test deadline check pass.
- [x] Run focused quality checks: 22 targeted regressions, Ruff on all changed Python files, change-spec gate validation, bytecode compilation, and `git diff --check` (details in `evidence/implementation.md`).
- [x] Rerun deadline/reclaimer regressions and affected lint/spec checks after the data-review fixes.
- [ ] Run the selected full quality profile once, serialized by the coordinator; no repeated full verifier cycle.
- [ ] Complete independent reviews.
- [ ] Bind evidence to the final tree fingerprint.
