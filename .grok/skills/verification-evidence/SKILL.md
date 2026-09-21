---
name: verification-evidence
description: Use whenever tests, review, CI evidence, or completion claims must be checked and bound to the current repository state.
---

# Verification and Evidence

Run `python scripts/grok_verify.py --mode pr`. Verification receipts include a repository fingerprint. Any subsequent change makes them stale.

Dispatch every review agent selected by the route. Each must inspect the actual final tree and return the complete report to the coordinator out-of-band. The coordinator persists all reports in the change package after all reviews finish, then reruns final verification. Record passing reports with `scripts/grok_review.py`. Completion requires zero gaps in `python scripts/grok_status.py`.

Code and test reviewers run bounded, change-relevant mutation probes only in a reviewer-owned private scratch copy outside the reviewed worktree. Keep the candidate unchanged; scratch must be below a trusted non-sticky parent with mode `0700` and reproduce the exact candidate, including relevant staged, unstaged, and untracked changes. Bind the report to HEAD and candidate tree fingerprint before/after. Unsafe scratch, an incomplete snapshot, or a changed fingerprint makes the result inconclusive/stale. Configured read-only mode is not an OS-enforced isolation boundary. Reports include scratch path, literal `reviewed-tree-modified: no`, executed claims, exact commands and concise output, killed/survived/inconclusive mutants, and unexecuted claims with reasons.

Never claim a command passed unless its current result is available. Never reuse review evidence from a different tree.
