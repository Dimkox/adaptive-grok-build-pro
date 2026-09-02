# Rollback Plan — M5 Isolated Provider Execution

Navigation: [package](brief.md) ↔ [schedule](schedule.md) ↔ [release](release.md) ↔ [evidence](evidence/README.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md).

Before deployment, rollback is reversion of the unmerged slice; no M5 migration has been accepted, published or deployed. Migration `014` remains immutable. A future rollout must quiesce old finalizers before forward-only expand `015` locks proposals then results. It upgrades compatible live non-final `014` packet/manifest/proposal evidence, but atomically refuses any legacy `workspace_results` row or unattested `014` artifact proposal before DDL or data mutation; DROP-only contract `016` then retires only the superseded proposal-body and snapshot-uniqueness constraints in the same migrator transaction. No synthetic attestation and no universal production-upgrade claim are allowed. After `015`/`016` are ever accepted, stop execution claims, preserve immutable evidence, keep legacy M4 control operations available, and forward-fix with `017+`; never down-migrate or rewrite M4 `013` or M5 `014`-`016`.

## Provisional data rollout envelope

- Before: `014` is provisional and unpublished. Production volume and distribution are unknown; a rollout must first inventory packet, manifest, proposal-by-kind, and result counts plus representative per-run maxima. Execution rows are bounded per run, but that is not a production-volume claim.
- Apply: quiesce execution claims and old finalizers. The migrator uses a five-second lock/statement timeout; `015` first takes `ACCESS EXCLUSIVE` locks on proposals then results, requires zero workspace results and zero legacy artifact proposals, performs no backfill, and installs canonical constraints/functions/roles before DROP-only `016` runs in the same transaction.
- Cost and stop conditions: new unique constraints and validation may scan compatible non-final rows. Stop on any timeout, nonzero gate, unsafe role topology, constraint/validation error, or unexpected count/digest change; the whole `015`+`016` transaction must roll back with schema version and evidence unchanged.
- After: require exact schema version `16`; only the named successor constraints remain; runtime and artifact-attestor roles/capability queries match their least-privilege contracts; and every preserved non-final packet, manifest, proposal count and canonical digest matches the pre-apply inventory. No live traffic resumes until those checks pass.

Recovery verification must show no live execution allocations, every incomplete manifest terminal/orphaned, M4 20/10/1 accounting consistent, legacy `/v1/claims` unchanged, and no provider/systemd/external-write capability active.
