# Rollback plan — M4 Durable Factory Task Control Plane

Trigger on any fence/capacity/budget/audit/auth/isolation invariant failure, migration drift, reconciliation imbalance, restart failure or stale evidence. Enable global kill, stop new intake/claims and the local socket process, preserve rows/audit/logs/evidence, and revert source only through a new PR.

Before first intake, only the explicitly named disposable test database/schema may be destroyed. After durable intake, never down-migrate or delete audit: restore the verified backup into a separately named comparison database or apply a reviewed forward migration `009+`. The local rollout owner records a successful logical-backup restore, schema-version/readiness check, effective-role denial probe, exact live-allocation/counter agreement, audit-chain verification and two-pass reconciliation smoke result before restart. The second reconciliation must repair zero rows; any mismatch remains no-go.
