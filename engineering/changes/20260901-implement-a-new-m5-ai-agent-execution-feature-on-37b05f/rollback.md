# Rollback Plan — M5 Isolated Provider Execution

Navigation: [package](brief.md) ↔ [schedule](schedule.md) ↔ [release](release.md) ↔ [evidence](evidence/README.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md).

Before deployment, rollback is deletion/reversion of the unmerged source commit. Migration `014` is unpublished and branch-only; M4 migration `013` remains immutable. After M5 is ever accepted, stop execution claims, preserve immutable packet/manifest/proposal/snapshot/result and recovery evidence, keep legacy M4 control operations available, and forward-fix with migration `015+`; never down-migrate or rewrite accepted `013`/`014`.

An upstream M4 SHA change pauses downstream writing and requires a three-way overlap plus contract-compatibility audit before another normal merge. It invalidates the task packet, manifest, proposal, result and any later M6/M7/M8/M9 evidence; do not relabel old digests or provider/fake facts as authority. Current predecessor `56e12b2b394436ee227c66d78b1caba8f7317c78` is only a local restack checkpoint.

Recovery verification must show no live execution allocations, every eligible incomplete manifest terminal/orphaned by one control-plane stage/event, no fabricated proposal or WorkspaceResult, M4 20/10/1 accounting consistent, legacy `/v1/claims` unchanged, and no provider/systemd/external-write capability active. Rootless isolation and the trusted live Git snapshot broker remain `BLOCKED`; production remains human-owned.
