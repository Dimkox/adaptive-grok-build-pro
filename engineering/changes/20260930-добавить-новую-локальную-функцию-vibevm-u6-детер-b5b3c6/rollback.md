# Rollback plan — Добавить новую локальную функцию VibeVM U6: детерминированный package graph resolver, lock cache offline replay, bounded unpack projection, boot checks, atomic generations, scoped caches, export fallback и тесты

## Trigger conditions

Integrity/access regression, unsafe projection, incomplete generation or native-core compatibility regression.

## Application rollback

Keep the adapter disabled. If a prior generation is qualified and not revoked, atomically select it; otherwise leave the capability blocked and use the independent native core.

## Data recovery / forward-fix

Immutable admitted objects and generations are retained as evidence. Never rewrite cache bytes or delete the sole audit copy during rollback.

## Verification after rollback

Re-read the active generation, verify all referenced object digests and native export, and confirm the in-flight snapshot identity did not change.
