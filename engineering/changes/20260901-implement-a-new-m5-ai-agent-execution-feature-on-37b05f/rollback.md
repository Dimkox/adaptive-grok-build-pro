# Rollback Plan — M5 Isolated Provider Execution

Navigation: [package](brief.md) ↔ [schedule](schedule.md) ↔ [release](release.md) ↔ [evidence](evidence/README.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md).

Before deployment, rollback is deletion/reversion of the unmerged source commit. After migration `013` is ever accepted, stop execution claims, preserve immutable packet/manifest/proposal evidence, keep legacy M4 control operations available, and forward-fix with migration `014+`; never down-migrate or rewrite `013`.

Recovery verification must show no live execution allocations, every incomplete manifest terminal/orphaned, M4 20/10/1 accounting consistent, legacy `/v1/claims` unchanged, and no provider/systemd/external-write capability active.
