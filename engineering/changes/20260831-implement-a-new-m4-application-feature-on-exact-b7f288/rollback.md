# Rollback plan — M4 Durable Factory Task Control Plane

Trigger on any fence/capacity/budget/audit/auth/isolation invariant failure, migration drift, reconciliation imbalance, restart failure or stale evidence. Enable global kill, stop new intake/claims and the local socket process, preserve rows/audit/logs/evidence, and revert source only through a new PR.

Before first intake, only the explicitly named disposable test database/schema may be destroyed. After durable intake, never down-migrate or delete audit: restore the verified backup into a separate database for comparison or apply a reviewed forward migration `004+`. Reprove kill, zero leaked allocations, readable append-only audit, Trust CI isolation and idempotent reconciliation before restart.
