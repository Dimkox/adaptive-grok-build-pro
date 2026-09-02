# Rollback Plan — M5 Isolated Provider Execution

Navigation: [package](brief.md) ↔ [schedule](schedule.md) ↔ [release](release.md) ↔ [evidence](evidence/README.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md).

Before deployment, rollback is reversion of the unmerged slice; slice 01 has no M5 database state. After successor migration `014` is ever accepted, stop execution claims, preserve immutable packet/manifest/proposal evidence, keep legacy M4 control operations available, and forward-fix with migration `015+`; never down-migrate or rewrite M4 `013` or M5 `014`.

Recovery verification must show no live execution allocations, every incomplete manifest terminal/orphaned, M4 20/10/1 accounting consistent, legacy `/v1/claims` unchanged, and no provider/systemd/external-write capability active.
