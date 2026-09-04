# Rollback plan — M5 bounded local execution control plane on exact M4 67dc4dd

## Trigger conditions

M4 regression, authorization or tenant-boundary breach, identity mismatch, migration precondition/checksum failure, partial terminal state, inability to recover factually, or incomplete trusted startup composition.

## Application rollback

Before any persistent application, revert the unmerged M5 source lineage or keep execution disabled; M4 remains usable. During a future authorized activation, first disable new execution claims and M5 route composition while retaining the full M4 control plane.

## Data recovery / forward-fix

Migrations `014`-`017` are forward-only. On transactional migration failure, retain the prior schema/checksum set. If schema 17 has ever been applied, quiesce claims, preserve every execution table and evidence row, reconcile outstanding runs, and correct with migration `018+`; never down-migrate, drop evidence, or rewrite `001`-`017`.

## Verification after rollback

Verify the exact M4 control route inventory, schema/checksum set, task/run/allocation consistency, absence of new execution claims, durable audit/history availability, and completion or fenced recovery of every previously active execution. Bind any corrective verification and reviews to the new exact tree.
