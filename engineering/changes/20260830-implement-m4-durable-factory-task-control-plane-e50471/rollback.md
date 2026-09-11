# Rollback plan — M4 Durable Factory Task Control Plane

## Trigger conditions

- Lease/fence, capacity, budget, audit, authorization, or cross-trust isolation invariant fails.
- Migration checksum/drift, reconciliation imbalance, or restart recovery cannot be proven.
- Final fingerprint/check/approval no longer matches the reviewed tree.

## Application rollback

Enable the global kill switch, stop new intake/claims, stop the local API/scheduler, and retain all durable rows, audit, logs, and evidence. Revert source only through a new PR; never reuse stale receipts or approvals.

## Data recovery / forward fix

Before first disposable intake, the explicitly named disposable `factory` schema may be removed through approved test cleanup. After durable intake, never down-migrate or delete audit: restore the verified backup into a separate database for comparison or forward-fix with migration `004+` under a fresh review and approval.

## Verification after rollback

Prove the kill switch blocks claims, no live allocation remains, audit is readable and append-only, source/backup identities are recorded without credentials, Trust CI state is unchanged, and recovery/reconciliation is idempotent before any restart.
