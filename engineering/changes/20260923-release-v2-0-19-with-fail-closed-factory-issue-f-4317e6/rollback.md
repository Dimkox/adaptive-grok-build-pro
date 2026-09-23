# Rollback plan — Release v2.0.19 with fail-closed factory issue fixes

## Trigger conditions

Any failed exact-SHA check, stale receipt, regression in a retained fail-closed path, or mismatch
between release metadata and the verified source tree blocks publication.

## Application rollback

Before merge, supersede/close the candidate PR without changing protected branches. After merge,
use a new revert/forward-fix PR; never move an immutable tag or rewrite a published archive.

## Data recovery / forward-fix

No data migration or production state mutation is introduced. If the grant-field migration exposes
an old-reader issue, restore compatibility in a new PR; do not rewrite historical evidence.

## Verification after rollback

Repeat issue-specific tests, full PR verification, independent reviews, exact fingerprint receipts,
and the external App-owned check for the rollback/forward-fix head.
