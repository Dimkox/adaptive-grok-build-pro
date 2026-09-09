# Rollback plan — Fix the M3 branch after accepted M2 changed: merge exact M2 head 022411b05924618cfde0cb97b8c8aff4955e6013 into M3, resolve integration conflicts without changing M3 requirements, add or update regression tests if needed, run verification and reviews, and prepare PR #11 for fresh exact-SHA Trust CI; no external writes without exact delegated grants.

## Trigger conditions

Any lost M2/M3 invariant, invalid schema/digest/base/head binding, verifier failure,
or review finding that cannot be repaired without expanding the approved scope.

## Application rollback

Before external delivery, abandon the isolated restack branch and recreate it
from preserved M3 head `d4cc01fe8d6ec82cce93106191774fc32e8dbb46`.
After delivery or merge, use a separately reviewed revert or forward-fix PR; do
not rewrite protected/shared history.

## Data recovery / forward-fix

No data mutation exists. Preserve historical evidence and regenerate all
exact-state artifacts after any forward fix. Never roll back by changing deployed
Trust-CI policy, holdout, keys, approvals, or branch protection.

## Verification after rollback

Re-run focused M2/M3 cohorts, full PR verification, independent reviews, and any
required external exact-SHA Trust CI on the new final head.
