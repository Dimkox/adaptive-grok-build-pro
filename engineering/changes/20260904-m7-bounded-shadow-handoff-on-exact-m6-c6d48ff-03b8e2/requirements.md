# Requirements — M7 bounded shadow handoff on exact M6 c6d48ff

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Six closed version-1 schemas and matching immutable Python values reject unknown fields, versions, malformed identities, and non-canonical ordering.
- [ ] M4 legacy intent and M5 task-packet identities remain distinct; M5 input/result heads remain distinct and are factually bound to the matching M6 input/result facts.
- [ ] M6 envelope, verdict body, verdict digest, evidence-set binding, and nested object digests are recomputed locally; callers cannot supply dependency-authority or evidence-authority overrides.
- [ ] A ready-for-PR bundle is content-addressed, deeply immutable, fixed at `blocked_pending_durable_lookup`, and contains only a subject-bound manual operator proposal with `external_capability=absent`.
- [ ] Cohort aggregation rejects replay, mixed cohort keys, stale bindings, unbounded collections, non-canonical ordering, forged aggregates, and outcome bodies or personal data.
- [ ] Evaluation recomputes aggregates from a cohort and returns only `blocked` or `eligible_for_human_l2_review`; eligibility requires the complete fixed sample, observation, quality, budget, safety, review-time, and containment bounds.

## Failure and edge cases

- Any predecessor identity mismatch, non-writer producer fact, non-pass M6 verdict, altered nested value, or digest mismatch fails closed.
- Duplicate outcome or bundle identity is replay; mixed exact cohort tuples are rejected.
- Fewer than 30 accepted outcomes, less than 14 days without a completed release cycle, fewer than 30 baseline observations, any safety or budget violation, or incomplete injection containment blocks the recommendation.
- Thresholds are integer millionths; median and p95 use deterministic nearest-rank calculation.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: existing architecture ownership, closed-contract, deterministic-evidence, and no-external-authority rules remain authoritative.
- Canonical-example deviations and evidence: none; final canonical M7 `4df2516b` supplies the exact add-only semantic files.
- Intentional debt created, repaid, or accepted: durable lookup, runtime composition, real human evidence, and delivery proof are explicitly deferred, not represented as complete.

## Non-functional requirements

- Security: untrusted producer or outcome bodies cannot alter policy or carry operational capabilities.
- Reliability: every public value is immutable and content-addressed; all semantically unordered inputs require canonical order.
- Performance: at most 10,000 outcomes or baseline values and no external I/O.
- Observability: aggregate and evaluation digests, sorted failure codes, bounded counters, and explicit recommendation are reproducible from the same closed cohort.
