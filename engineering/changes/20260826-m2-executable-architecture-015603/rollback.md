# Rollback plan — M2-A Executable Architecture

## Trigger conditions

- Canonical digest or diagram output is not reproducible.
- M1 validation/receipt compatibility regresses.
- Architecture rules silently pass unsupported/applicable input or lower risk.
- Installer creates or overwrites a target model.
- Adoption marker and model identity disagree or adoption can be disabled by deleting model files.

## Application rollback

Before target adoption, revert the M2-A source slice to completed-M1 SHA `25bfbe59ea188d9687b20a9caad19e7db3d031f8`. For a consumer that has not committed `architecture/adoption.json`, removing unreviewed example copies is safe because architecture remains `not_configured`. No migration or service rollback is needed.

## Data recovery / forward-fix

No database/schema/backfill or external state is changed. After adoption, do not delete the marker to bypass the gate; restore/fix the reviewed model and rules or forward-fix with a new explicit contract version. Once another milestone consumes architecture contract v1, preserve v1 meaning and forward-fix or introduce a new explicit contract version.

## Verification after rollback

Run root tests, compileall, PR verification, M1 spec gate checks, and installer compatibility. Never reuse M2-A receipts after a tree or contract change.
