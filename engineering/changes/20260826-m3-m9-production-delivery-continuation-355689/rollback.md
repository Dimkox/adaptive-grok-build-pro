# Rollback plan — M3-M9 production delivery continuation

## Trigger conditions

Contract incompatibility, unsafe lifecycle promotion, stale digest acceptance, verifier regression, or independent Critical/Important finding.

## Application rollback

Before merge, revert the bounded M3 commits on its branch. After merge, use a reviewed forward-fix/revert PR; never rewrite protected history.

## Data recovery / forward-fix

M3 adds repository records only and no database. Preserve evidence, revoke unsafe governance records explicitly, rotate the digest, and regenerate receipts.

## Verification after rollback

Run focused governance/architecture/receipt tests, one final PR verifier, and renew affected reviews and exact-SHA Trust CI evidence.
