# M6 M5-Aligned Semantic Validation — Provisional Source

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown cannot override typed IDs or approval scopes.

Change ID: `20260901-m6-provider-independent-semantic-validation-prov-82aac8`  
Route: `82aac86a3bf9`  
Phase A merge: `c398ea06daa635ad679e22c8cd29dbf74d2ae12c`

Merged M5 candidate: `141e51e75b2bb337fa3bb1544639c6c46c287309`

Planning deadline: `2026-09-08T00:00:00+03:00`

Connectivity: [README](../../../README.md) ↔ [roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m6-semantic-validation-provisional-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m6-semantic-validation-provisional.md) ↔ this package / [release](release.md) / [rollback](rollback.md) / [evidence](evidence/README.md).

## Outcome

M6 consumes a fully verified immutable M5 `TaskPacketV1`/`RunManifestV1`/`WorkspaceSnapshotV1`/`WorkspaceResultV1` bundle, binds every exact task/run/fence/SHA/result/evidence fact, accepts only separately authenticated facts that M5 does not contain, and publishes append-only independent semantic findings, coverage, verdicts, and finite repair proposals.

M5 `ready_for_human`, failure classes/reasons, infrastructure attempts, and `repair_count` are preserved. Validator/adjudicator roles cannot write application code, execute providers, mutate M5 evidence, use Git/Trust CI/human approval, or access network/credentials. Cycle four, recurrence, stale evidence, risk/architecture/base/fence/budget/deadline violations escalate to `needs_human`.

## Boundary

In scope: exact bridge, forward migration 014, capability-shaped store/service/API, deterministic adjudication, cycles 1..3 child proposals, restart recovery, fixed low-cardinality metrics, installer/architecture/docs, and focused tests.

Out of scope: live providers/models, shared database, production, credentials, external writes, M7 activation/compatibility claim, push/PR/merge/release/Trust CI/human approval. M4 and M5 remain unaccepted/unpublished; M6 must later restack in dependency order.
