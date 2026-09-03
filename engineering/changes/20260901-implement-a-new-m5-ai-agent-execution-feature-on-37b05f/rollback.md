# Rollback Plan — M5 Isolated Provider Execution

Navigation: [package](brief.md) ↔ [schedule](schedule.md) ↔ [release](release.md) ↔ [evidence](evidence/README.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md).

Before deployment, rollback is reversion of the unmerged successor; no M5 migration has been accepted, published or deployed. Migrations `014`-`016` remain immutable within current provisional lineage. Unpublished `017` adds recovery/metrics and requires PostgreSQL 17 before mutation. No synthetic attestation, proposal or result and no universal production-upgrade claim are allowed. If `014`-`017` are ever accepted, stop execution claims, preserve immutable evidence and cleanup history, keep legacy M4 control operations available, and forward-fix with `018+`; never down-migrate or rewrite M4 `013` or accepted M5 migrations.

## Provisional data rollout envelope

- Before: `014` is provisional and unpublished. Production volume and distribution are unknown; a rollout must first inventory packet, manifest, proposal-by-kind, and result counts plus representative per-run maxima. Execution rows are bounded per run, but that is not a production-volume claim.
- Apply: quiesce execution claims and old finalizers. The migrator uses a five-second lock/statement timeout; `015` first takes `ACCESS EXCLUSIVE` locks on proposals then results, requires zero workspace results and zero legacy artifact proposals, performs no backfill, and installs canonical constraints/functions/roles before DROP-only `016` runs in the same transaction.
- Cost and stop conditions: new unique constraints and validation may scan compatible non-final rows. Stop on any timeout, nonzero gate, unsafe role topology, constraint/validation error, or unexpected count/digest change; the whole `015`+`016` transaction must roll back with schema version and evidence unchanged.
- After: require exact schema version `17`; only the named successor constraints/recovery capabilities remain; runtime and artifact-attestor roles/capability queries match their least-privilege contracts; the recovery metric epoch starts at zero with no historical backfill; and every preserved packet, manifest, proposal, attestation and result count/digest matches the pre-apply inventory. No live traffic resumes until those checks and the two-restart drill pass.

Recovery verification must show canonical M4 release/accounting, cancelled/orphaned terminal stages without fabricated proposals/results, exact-handle at-least-once cleanup with fenced outcome history, replay no-op, legacy `/v1/claims` unchanged, and no provider/systemd/external-write capability active. Operational activation remains blocked without a trusted rootless broker and live OS isolation.
