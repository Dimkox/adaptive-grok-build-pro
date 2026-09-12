# Rollback and recovery

Before activation: keep provider selection unavailable and revert only this isolated source change if needed.

For a later authorized operator rollout: stop intake, disable live provider selection, shut down the owning server, preserve a coherent SQLite snapshot and artifact/quarantine/publication data, and restart only a compatible accepted build. Do not copy a running database file without WAL consistency, delete durable history or replay ambiguous provider calls. Dedicated runtime install/backup/restore source describes isolated Claw operations; no such host operation has occurred in this phase.

Versioned filesystem publication retains the exact prior release and supports an explicit grant-bound restore operation. An ambiguous activation/restore is reconciled through observation; it is never automatically replayed. This source capability is not a performed rollback or proof that Namecheap supports the required deployment layout. The frozen landing v1 API still reports no live URL.

Actual recovery exercise is deferred together with all other checks.
