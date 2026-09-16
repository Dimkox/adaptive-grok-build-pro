# Tasks — 20260916-fix-architecture-stream-oversized-tracked-binari-1895e1

- [x] Route the defect (`1895e17ff333`, medium, evidence verification + code_review + test_review).
- [x] Reproduce issue #80 against the unpatched module in a tree tracking the 10,940,676-byte v2.0.17 ZIP.
- [x] Extract the no-follow walk without changing `_worktree_blob` behaviour (missing file still yields None; the adoption-marker regression this exposed is fixed and covered by the existing test).
- [x] Add streaming profiles and switch the changed-artifact loop to size/digest/binary, keeping line stats text-only.
- [x] Prove the streamed digest equals the buffered `sha256` for the real tracked ZIP, in commit and worktree modes.
- [x] Add fitness tests: oversized binary streamed+verified (incl. a tampered digest), oversized text still refused.
- [x] `tests.test_architecture_fitness` 103 tests OK; `tests.test_architecture_model` OK; `ruff` clean.
- [ ] Independent code review and test review, then `grok_verify --mode pr` on the frozen tree.
- [ ] Deliver as a pull request and merge only on the exact-head App check.
- [ ] Comment the outcome on issue #80 and close it after the merge.
