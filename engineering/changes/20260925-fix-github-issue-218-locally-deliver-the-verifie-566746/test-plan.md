# Test plan — issue #218 clean squash delivery

## Focused adversarial matrix before the full verifier

| Risk | Probe | Required result |
| --- | --- | --- |
| Ordering | Both reviewers' exact unequal repeated-clean examples | Direct classifier never clean |
| Hostile attributes | Real unstaged, staged and committed moves with `* -whitespace` | fast/PR final diff gate rejects; diagnostics omit source lines |
| Closed scope | Recompute a committed ambiguous move | Stored complete claim rejected |
| Compatibility/work bounds | Existing longest-order, clean insertion, duplicate/move and shared chain/endpoint budget tests | Pass; exhaustion remains typed incomplete |
| Endpoint memory | Oversized blob and several individually acceptable blobs exceeding aggregate ceiling | No body batch requested; metadata-only failure |
| Worktree memory | Two individually acceptable files over a lowered aggregate ceiling | Read bytes stay bounded; coverage incomplete |
| Worktree paths | Multiple dirty/untracked files over lowered path ceiling | Stop before further file reads; coverage incomplete |
| Receipt recomputation | Stored complete scope with dirty files now over aggregate ceiling | Independent recomputation rejects |
| Safe reads | Symlink, broken link, FIFO and replacement during read | Existing fail-closed behavior retained |

Run complete affected verifier, receipt and Git utility modules; include hooks/architecture compatibility when needed by the final contour. The writer records exact RED and GREEN output, runs `git diff --check`, validates the typed spec and the thirteen-path plus package source-relative inventory. It does not run the full verifier or record completion.

## Coordinator-owned completion

After this focused matrix is green, run one preliminary full `python3 scripts/grok_verify.py --mode pr --no-record`. Then obtain all route reviews on a frozen exact snapshot, including private-scratch code/test mutation probes. Persist reports and finish tracked accounting, transition ready, amend the one-child candidate, run final recording verification on clean exact HEAD, then record verification-bound review receipts and read-only zero-gap status. A blocking finding returns to the sole writer; no blanket rescan/review expansion without a new justified concern.

Historical staged-tree equality and old PASS runs remain history. External Trust CI, remote publication, deployment and #219 are not executed or inferred from local evidence.
