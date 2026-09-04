# Rollback plan — M2-A Executable Architecture

## Trigger conditions

- Canonical digest or diagram output is not reproducible.
- M1 validation/receipt compatibility regresses.
- Architecture rules silently pass unsupported/applicable input or lower risk.
- Queue provenance becomes order-dependent, misses relevant uncertainty, or taints an unrelated operation.
- Installer mutates an existing target, executes dependency advice, publishes over a target, or includes target-owned architecture authority.
- Adoption marker and model identity disagree or adoption can be disabled by deleting model files.

## Application rollback

Before target adoption, revert the M2-A source slice to completed-M1 SHA `25bfbe59ea188d9687b20a9caad19e7db3d031f8`. For a consumer that has not committed `architecture/adoption.json`, removing unreviewed example copies is safe because architecture remains `not_configured`. No migration or service rollback is needed.

The queue/installer safety pivot is source-only and rolls back before release by reverting its tracked pivot commits. That restores the prior implementation but requires no database, queue, runtime, generated-file, or external-state recovery because repository verification performs no consumer materialization.

Existing targets are never modified, so there are no bytes for the installer to restore. A failure before publication removes only entries whose original descriptor identity is still proven. If constructor identity is unresolved, the installer deliberately preserves the current name and emits `manual cleanup required: installer ownership is unresolved`; an operator must inspect that sibling entry before any cleanup. After successful absent-target publication, the installer offers no automatic rollback: retain or remove the new tree only through a separate reviewed filesystem operation.

## Data recovery / forward-fix

No database/schema/backfill or external state is changed. After adoption, do not delete the marker to bypass the gate; restore/fix the reviewed model and rules or forward-fix with a new explicit contract version. Once another milestone consumes architecture contract v1, preserve v1 meaning and forward-fix or introduce a new explicit contract version.

## Verification after rollback

Run root tests, compileall, PR verification, M1 spec gate checks, queue exact-delta tests, and installer plan/materialization compatibility. Never reuse M2-A receipts after a tree or contract change.
