# Tasks

- [x] Reproduce RED: three arms fail pre-fix (raw RuntimeError + poll None + leaked fd).
- [x] Implement typed setup, terminal stop guard, nested close; 109/109 module tests green.
- [x] Correct the false os.name-dispatch claim on issue #109 publicly.
- [x] Independent reviews: code review PASS on `22f4926` (tree carried byte-identically into the
      message-amended `8b4d82a`); test review PASS on `8b4d82a` with an executed red/green matrix
      (three distinct base-side red causes), zero child/fd leaks, 6-mutant matrix. Reports and
      dispositions in `evidence/`.
- [x] Close the test review's Finding 1: the vacuous `assertIn("setup", …)` now pins the literal
      `"streamed blob setup failed"`, and re-running mutant M4 (message renamed) turns arm 1 RED
      where it previously survived.
- [ ] Re-gate `grok_verify --mode pr` on this head, record verification/code_review/test_review
      receipts, push, open the PR; merge only on the exact-head App check.
