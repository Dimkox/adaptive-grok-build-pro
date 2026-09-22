# Rollback plan — Release v2.0.19 from candidate 5d93fc3

## Trigger conditions

Stop on any stale fingerprint, failed verifier/review, missing App-owned exact-head check, missing signed approval, package mismatch, or publication target mismatch.

## Application rollback

Before publication, abandon the unmerged candidate and retain the immutable `v2.0.18` release. After publication, point consumers back to `v2.0.18`; never retag or overwrite either release.

## Data recovery / forward-fix

Release metadata is corrected by a new exact-SHA successor PR. Published ZIPs, sidecars and tags are content-addressed and are not rewritten. No database or service state is changed by this release.

## Verification after rollback

Re-run the relevant immutable-release and state tests against the retained v2.0.18 tag and record the new exact fingerprint; do not reuse stale candidate receipts.
