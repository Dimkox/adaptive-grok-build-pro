# Tasks — 20260916-fix-architecture-stream-oversized-tracked-binari-1895e1

- [x] Route the defect (`1895e17ff333`, medium, evidence verification + code_review + test_review).
- [x] Reproduce issue #80 against the unpatched module in a tree tracking the 10,940,676-byte v2.0.17 ZIP.
- [x] Extract the no-follow walk without changing `_worktree_blob` behaviour (missing file still yields None; the adoption-marker regression this exposed is fixed and covered by the existing test).
- [x] Add streaming profiles and switch the changed-artifact loop to size/digest/binary, keeping line stats text-only.
- [x] Prove the streamed digest equals the buffered `sha256` for the real tracked ZIP, in commit and worktree modes.
- [x] Add fitness tests: oversized binary streamed+verified (incl. a tampered digest), oversized text still refused.
- [x] `tests.test_architecture_fitness` 103 tests OK; `tests.test_architecture_model` OK; `ruff` clean.
- [x] Independent code review (PASS, 1 Important: the first `Popen` bypassed `_run_capped`'s deadline/caps/reaping; rewritten as `_stream_git_blob`) and test review (PASS, 2 Important: the widened-constant mutation stayed green, and late-NUL plus the truncation guard were untested) — dispositions in `evidence/review-response.md`.
- [x] Follow-up commit adds the constant pin, the late-NUL case, the oversized `modified` case and a forced-short-read truncation test: `tests.test_architecture_fitness` 106 tests OK, 166 adjacent tests OK.
- [ ] Deliver as a pull request and merge only on the exact-head App check.
- [ ] Comment the outcome on issue #80 and close it after the merge.
