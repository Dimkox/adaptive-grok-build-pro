# Rollback plan — M6 bounded semantic validation on exact M5 85cd434

## Trigger conditions

Contract drift, cross-repository or capability bypass, inconsistent verdict replay, more than three child cycles, partial semantic persistence, M5 data drift, or migration failure.

## Application rollback

Before any unpublished migration is applied outside disposable evidence, drop the unmerged M6 commits or keep semantic composition disabled. M4/M5 remain usable because their contracts and schema bytes are unchanged.

## Data recovery / forward-fix

Migration `018` is forward-only and append-only. A failed application rolls back transactionally to schema 17. After any future authorized persistent application, preserve facts and use a separately reviewed migration `019+`; never edit, down-migrate, or delete evidence.

## Verification after rollback

Confirm schema 17, unchanged M5 migration checksums and workspace-result digests, disabled semantic routes, healthy M5 readiness, and no semantic child or external action.
