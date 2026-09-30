# Requirements — Реализовать Factory v1.5 FPF U7 runtime: applicability selector, progressive dependency-complete reader, context budgeter, URI resolver, semantic projection, decision invalidation, adapter, offline snapshots, security boundary, A/B/C evaluation, upgrade fallback and deterministic tests

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] AC95 selects no FPF without a question and records a bounded reason when applicable.
- [x] AC96-AC99 preserve dependencies, total budget, canonical URIs and delivered bytes.
- [x] AC100-AC101 detect semantic loss and produce deterministic frozen generations.
- [x] AC102-AC105 bind evidence, stale decisions, honest handoff and project authority.
- [x] AC106-AC108 expose exact compatibility, offline blockers and security boundaries.
- [x] AC109-AC111 reject confounding/incomplete cost and protect correctness.
- [x] AC112-AC113 forbid self-update and make safe fallback next-attempt only.

## Failure and edge cases

- Missing dependencies, ambiguous URIs, exhausted bounds, semantic corruption,
  lost offline bytes, tenant mismatch, injection, incompatible profiles,
  confounded experiments and unsafe fallback fail closed.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: no network/process/hook surface and no authority effect.
- Reliability: canonical digests, frozen inputs and deterministic replay.
- Performance: finite reads, transitions, depth, bytes and model window.
- Observability: selection/delivery digests, qualification and unknown cost.
