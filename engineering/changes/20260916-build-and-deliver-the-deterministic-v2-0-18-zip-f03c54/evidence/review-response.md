# Review response — v2.0.18 artifact child (A)

Both route reviews PASS on `497de07` and independently re-derived the core claims — the release reviewer and
the security reviewer each rebuilt the archive from fresh clones at `fc8d9e6…` and matched the tracked blob
byte-for-byte (`0bc6adc9…`), and the security reviewer added falsification arms: dirty-tree build refused,
child-tip and one-byte-edit builds diverge — INV-002 (tree-bound reproducibility) proven, not asserted.

## Release review (PASS: 2 Important, 4 Minor, 2 informational) and Security review (PASS: 2 suggestions, 4 nice-to-have)

| # | Finding | Disposition |
| --- | --- | --- |
| F1 | Important — `GROK_BUILD_HANDOFF.md:303` still said "ZIP, sidecar, tag and GitHub Release do not exist" | **Fixed**: bytes are now stated as tracked and twice-reproducible; only tag/Release remain asserted absent. |
| F2 | Important — `START_HERE.md:16` claimed the records "assert that its artifact bytes do not exist yet" | **Fixed** with the delivered/pending split. Both were under-claims (safe direction) but self-contradicting against the edited adjacent lines. |
| F3 | Minor/security-suggestion — mirrored docs carried route id `f03c541d1848`; authoritative is `f03c541d184f` | **Fixed** in `brief.md`/`tasks.md`. Root cause: my mirror-substitution map paired the old id's last chars wrongly. |
| F4 | Minor — three package docs still promised the "known local-only red" on the >10 MB binary (issue #80), with a clumsy grafted parenthetical | **Fixed**: the red no longer exists (#80 closed by #101 streaming analysis) and the full local gate passed on this wave — the docs now say so plainly. My first mirror pass created the mangled sentences; corrected here. |
| F5 | Minor — R package `tasks.md` left its delivery boxes unchecked after #107 merged | **Fixed**: ticked with head, merge SHA and check-run id; remaining lifecycle rows move to the SR paperwork wave as the v2.0.17 chain did. |
| F6 | Minor (pre-existing, outside diff) — `packages/README.md:3` attributed the **v2.0.16** digests to **v2.0.17** (introduced by `cfc4a57`, #100) | **Fixed** against `published_release` and the live release assets, with the correction disclosed inline in the file. |
| F7 | Minor — `artifact_child.requirement` named only "commit and tree" as self-withheld | **Fixed**: all four withheld identities named (`merge_commit`, `tree`, `checked_head`, `pull_request`), matching what the tests pin. |
| S1 | Suggestion — bytes were staged-then-copied, while packages guidance warns ad-hoc copies must not separate provenance | **Closed by durable log**: `evidence/build-provenance.md` records clones, command, digests, `cmp` identity, falsification arms and cleanup; tracked blob digest equals the build digest, re-verified by both reviewers independently. |
| S2 | Suggestion — no build log in evidence | Fixed by the same file. |
| S3 | Nice-to-have — dead `pending_unpublished_artifact_child` test arm | **Kept**: it is the form SR/A-again waves restore at publication time only in the sense of branch existence, and #99 shipped with the same reachable-if-reverted shape; removing it weakens revert-detectability. Noted, not changed. |
| S4 | Nice-to-have — adjacent record flips not itemized in brief scope; `last_success` casing; parent route naming in `local_candidate` | Accepted as-is: precedent-identical shapes, test-pinned; naming every coupled flip would drift from the mirrored spec wording without adding guard. |

## Coverage limits stated plainly

- Both reviewers could not and did not run `grok_verify` (it writes fingerprint-bound receipts); the
  verification receipt is recorded **after** this review-round commit on the exact pushed head, per the
  fingerprint ordering rule — the pre-report PASS on `497de07` is disclosed history, not the binding evidence.
- Tag and GitHub Release still do not exist anywhere; this wave proves bytes-in-tree only.
