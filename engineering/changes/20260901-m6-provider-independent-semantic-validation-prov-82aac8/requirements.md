# Requirements — M6 M5-Aligned Semantic Validation

> Typed authority: [`change-spec.yaml`](change-spec.yaml). `M6-001..016` map in order to `AC-001..016`.

- [x] M6-001: existing closed semantic contracts/adjudication/repair remain backward compatible and deterministic.
- [x] M6-002: a closed bridge binds exact M5 task/run/fence/packet/manifest/snapshot/result/proposal/artifact-attestation/SHA/status/failure fields without inference.
- [x] M6-003: only verified writer results with exact `m4_status=ready_for_human` become subjects; failed M5 dispositions are preserved and rejected.
- [x] M6-004: M5-missing holdout/review/typed requirements/risk/diff-limit/writer-context enter only through a separately authenticated closed request bound to the exact result.
- [x] M6-005: migration 014 is additive and stores immutable subjects, assignments, findings, coverage, verdicts, directives, child proposals, escalations, and recovery facts.
- [x] M6-006: exact idempotent replay succeeds; same key/result with a different canonical request/body/digest fails closed.
- [x] M6-007: coordinator, validator, and adjudicator capabilities are disjoint; runtime/public/writer have no semantic-table DML and validator cannot adjudicate.
- [x] M6-008: contract-first APIs preserve M5 behavior, authorize repository/scope, close every shape, and expose no raw provider/prompt/log/secret/reasoning body.
- [x] M6-009: verdicts are recomputed from persisted exact evidence and expose duplicates, correlations, contradictions, unsupported passes, and missing coverage.
- [ ] M6-010: repair cycles `1..3` bind the exact parent M5 result, original writer, fresh context, unchanged base/architecture/authority, budget and deadline.
- [ ] M6-011: cycle four, recurrence, wrong writer/context, risk/diff/base/architecture/authority/fence/head/budget/deadline/staleness violations append `needs_human` and create no child.
- [x] M6-012: source/SHA/digest mutation requires a new M5 result and newly generated deterministic/holdout/semantic/review evidence.
- [ ] M6-013: restart/recovery is bounded, replay-safe, observable, and cannot duplicate a verdict or child proposal.
- [ ] M6-014: metrics have fixed low-cardinality labels only; identifiers, digests, paths, findings, prompts, and error prose are never labels.
- [ ] M6-015: migration/installer/rollback are source-only, additive, least-privilege, and tested without shared database or external action.
- [ ] M6-016: evidence claims bounded provisional M6 source only; restack, full verification/review, Trust CI, M7, and release remain later gates.

Unknown versions/fields, malformed Unicode/IDs/SHA/digests, cross-run substitutions, mismatched AC sets, direct table mutation, unsupported capability, stale binding, divergent replay, fourth/recurring repair, and exhausted limits fail closed. Collections and narratives remain bounded; chain-of-thought, secrets and PII are prohibited.

Connectivity: [README](../../../README.md) ↔ [roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m6-semantic-validation-provisional-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m6-semantic-validation-provisional.md) ↔ [package](brief.md) / [release](release.md) / [rollback](rollback.md) / [evidence](evidence/README.md).
