# Requirements — Factory v1.5 fast working release

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Given route and repository facts, context selection produces a bounded canonical manifest and digest or a typed rejection.
- [ ] Given a state decision, one append-only factual record binds rule, facts, source/context identity, reason, and next permitted step idempotently.
- [ ] Given timing/cost gaps, summaries preserve unknown/incomplete rather than reporting zero or full cost.
- [ ] Given any supported tool-result channel, the pre-model envelope is allowed, redacted, rejected, or unavailable before reuse.
- [ ] Given semantic evidence, candidate SHA, context digest, criterion/rule, command/result, and report digest remain bound.
- [ ] Given insufficient ML history, prediction reports `not_qualified` and has no authority effect.
- [ ] Given owner exclusion, all Apple requirements report `excluded_by_owner`, never pass.
- [ ] Given incomplete external checks or M8 cohort, qualification remains pending/inactive.
- [ ] Given BB disabled or unqualified, native execution remains available and BB reports `not_run` without listeners or external effects.
- [ ] Existing contract readers and tests remain green.

## Failure and edge cases

- Unknown fields, invalid digests, duplicate IDs, oversized collections, traversal/secret paths, replay, unavailable observers, and partial cost coverage fail closed or remain explicitly unknown.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: no secret/customer payload export and no cross-tenant/repository context.
- Reliability: additive versioning, idempotent imports, forward recovery.
- Performance: explicit entry/byte bounds and bounded logs.
- Observability: phase timing, cost completeness, decision reasons, evidence digests, qualification status.
