# Rollback plan — M7 bounded shadow handoff on exact M6 c6d48ff

## Trigger conditions

Rollback or forward-fix if a bridge accepts stale or caller-invented authority, a bundle can expose operational capability, aggregate forgery can influence a recommendation, deterministic replay differs, or existing M4-M6 files change.

## Application rollback

Before publication, revert the add-only M7 source/schema/test and architecture checkpoint commits. Exact M6 `c6d48ffd8594b3baab1a575021452ea5dfa2a98b` remains the intact predecessor.

## Data recovery / forward-fix

No migration, persisted record, backfill, or external write exists; data recovery is not applicable. Contract defects require a new version or a bounded pre-publication forward-fix with focused regression evidence.

## Verification after rollback

Confirm all ten M7 product paths and additive M7 architecture entries are absent, `git diff` against exact M6 is empty, and the M6 tree fingerprint is restored.
