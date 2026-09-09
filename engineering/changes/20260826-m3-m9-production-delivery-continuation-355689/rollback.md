# Rollback plan — M3-M9 production delivery continuation

## Trigger conditions

Contract incompatibility, unsafe lifecycle promotion, stale digest acceptance, verifier regression, or independent Critical/Important finding.

## Application rollback

Rollback is forward-only. Before merge, add an explicit revert commit on the bounded M3 branch or close the candidate PR. After merge, use a reviewed forward-fix or revert PR; never rewrite protected history or silently restore an older governance digest.

## Data recovery / forward-fix

M3 adds repository records only and no database. Preserve evidence, revoke unsafe governance records explicitly, rotate the digest, regenerate the handoff/receipts, and renew every affected exact-fingerprint review.

## Verification after rollback

Run focused governance/architecture/receipt tests, one final PR verifier, and renew affected reviews and exact-SHA Trust CI evidence.
