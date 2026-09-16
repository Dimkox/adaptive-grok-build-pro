# Tasks

- [x] Reproduce the gaps (no keep concept: silent overwrite risk; drift unnameable).
- [x] Implement reader/parser/plan; 7 keep arms; 24 installer tests OK; ruff clean.
- [x] QUICKSTART two-questions rule (README keeps product identity only).
- [x] `grok_verify --mode pr` PASS 16/16 on `9d83ba4` (changed=14); code review FAIL (1 Critical: target_state shadowing; suggestions) and test review FAIL (FIFO hang, 12/21 mutants survived) closed in the review-round commit with re-gated evidence below.
- [ ] Re-gate on the parity-fix head, refresh receipts, push; the exact-head App check on #115 merges (the first check FAILURE at 0812df2 was the snapshot parity arm - root-unittest on a clean checkout sees 346 payload entries, not my worktree's 352).
