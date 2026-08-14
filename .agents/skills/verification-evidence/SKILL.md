---
name: verification-evidence
description: Use whenever tests, review, CI evidence, or completion claims must be checked and bound to the current repository state.
---

# Verification and Evidence

Run `python scripts/grok_verify.py --mode pr`. Verification receipts include a repository fingerprint. Any subsequent change makes them stale.

Dispatch every review agent selected by the route. Each must inspect the actual final tree and write a report. Record passing reports with `scripts/grok_review.py`. Completion requires zero gaps in `python scripts/grok_status.py`.

Never claim a command passed unless its current result is available. Never reuse review evidence from a different tree.
