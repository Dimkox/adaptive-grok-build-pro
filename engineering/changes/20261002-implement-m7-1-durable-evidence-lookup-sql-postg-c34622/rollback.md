# Rollback plan — Implement M7.1 durable evidence lookup: SQL PostgreSQL database migration 026, tenant repository isolation, canonical selector digest integrity, bounded queries, SECURITY DEFINER safe privileges and restart Unicode tests.

## Trigger conditions

Checksum drift; invalid or ambiguous latest evidence; tenant/source privilege failure; timeout/resource regression; or any failure of full verification, independent review or external merge trust.

## Application rollback

Before database application, revert this isolated source change through a reviewed PR. After 026 is applied, disable M7 callers/source bindings under separately authorized administration and retain a 026-compatible application or forward fix: an older 025-only application's schema-readiness check is expected to fail closed against a newer migration ledger. Do not pretend that an application-only revert removes 026 safely.

## Data recovery / forward-fix

No backfill or existing-row rewrite is performed. Preserve append-only M7 evidence and replay rows; do not edit historical checksums, drop durable tables, drop global roles, or downgrade the ledger. Use a separately reviewed additive migration for a repair. Any actual restore/destructive operation needs its own exact authorization and recovery evidence, outside this source-only package.

## Verification after rollback

Verify default-unavailable behavior, existing factory readiness, migration ledger/checksums, no enabled unintended source bindings, and unchanged M7 evidence cardinality. Re-run the exact candidate verifier and external Trust CI after any source repair; old receipts do not apply to the changed tree.
