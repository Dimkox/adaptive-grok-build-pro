# Requirements — M6 Provider-Independent Semantic Validation Provisional Slice

> Typed authority: [`change-spec.yaml`](change-spec.yaml). `M6-001..012` map in order to typed `AC-001..012`, because the repository schema requires `AC-[0-9]+` IDs.

## Acceptance criteria

- [ ] M6-001: five closed, bounded v1 JSON schemas and parsers produce stable canonical digests.
- [ ] M6-002: requirement references have typed kinds; coverage matches the subject requirement set exactly at `1_000_000` millionths.
- [ ] M6-003: input-order-independent adjudication exposes duplicates, correlations, contradictions, and unsupported passes.
- [ ] M6-004: provider output cannot select state; precedence is `needs_human > repair > pass`.
- [ ] M6-005: validator identity, role, read-only capability, definition/model digest, and independent context are proven.
- [ ] M6-006: repair cycles `1..3` retain the original writer and require a fresh context.
- [ ] M6-007: typed finding recurrence despite wording changes and any requested fourth cycle escalate.
- [ ] M6-008: increased risk, excessive diff, architecture/authority/base mutation, exhausted budget/deadline, or wrong writer escalate.
- [ ] M6-009: relevant requirement-set, subject, or digest mutation invalidates prior evidence.
- [ ] M6-010: the layer is pure, local, provider-independent, and lacks write/network/credential/external capability.
- [ ] M6-011: M5 bridge/migration/API/fence/idempotency/restart tasks remain explicitly BLOCKED.
- [ ] M6-012: local evidence claims only this provisional slice, never full M6 or M7 completion.

Unknown/missing fields, unknown versions, duplicates/unsorted sets, invalid Unicode/IDs/SHA/digests, non-exact coverage, stale bindings, identity collision, forbidden validator capability, reused context, cycle zero/four, recurrence, and exhausted limits fail closed. Narrative is bounded but excluded from recurrence identity. Collections cap at 256; results expose bounded reason codes and no chain-of-thought.

Connectivity: [README](../../../README.md) ↔ [roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m6-semantic-validation-provisional-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m6-semantic-validation-provisional.md) ↔ [package](brief.md) / [release](release.md) / [rollback](rollback.md) / [evidence](evidence/README.md).
