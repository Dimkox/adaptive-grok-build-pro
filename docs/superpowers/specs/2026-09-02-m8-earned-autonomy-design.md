# M8 Earned and Revocable Autonomy Design

## Outcome and boundary

M8 is a pure local evaluator design, not an activation system. Its only eligible class is frozen as `low_risk_text_only`; six closed canonical v1 values bind complete cohort evidence to one exact material tuple and may issue recommendation-only `L0`, `L1`, or `L2` results. L3/L4, merge, network, credentials, persistence and production are absent.

This design is provisional on exact M7 producer checkpoint `4df2516fa3a137fa730d08733fb9e338768232fb`, observed from a sibling worktree but not present in this branch's ancestry. The explicit 2026-09-02 user override permits pure local contracts/evaluator/demotion implementation and a bounded read-only wire adapter against synthetic algorithmic boundary fixtures. Activation, completion, factual cohort qualification and profile issuance/acceptance remain **BLOCKED**: every exact M7 bundle has `blocked_pending_durable_lookup`, and M7 exposes no durable external acceptance/currentness result.

## Canonical records

- `M7AutonomyWireHandoffV1`: full closed M7 bundle(s), outcome cohort, recomputed aggregate/evaluation and an explicit validator-to-provider mapping. It recomputes every M4/M5/M6/M7 digest and equality chain but has no caller-settable acceptance/currentness field and is not authority.
- `AutonomyTupleV1`: repository, `low_risk_text_only`, exact M7 cohort/change class, agent/validator/provider/model/prompt identities, policy, runner, holdout, authority digest, provider-mapping digest, L2 ceiling and expiry.
- `CohortTaskEvidenceV1`: exact tuple digest, distinct task/run/result-head identities, exact M7 bundle/outcome digests, human receipt bound to the M7 outcome, audit outcomes and bounded M8 measurements. Caller `eligible` and `human_accepted` booleans do not exist.
- `CohortEvidenceV1`: tuple, ordered distinct tasks, complete wire handoff, configured class thresholds, cohort window and canonical digest.
- `AutonomyProfileV1`: exact tuple/cohort digests, current L0/L1/L2, computed bounded metrics, expiry and halted state.
- `PromotionRecommendationV1`: current/recommended level, closed reason codes, expiry, `external_action_authorized=false` and separate-activation requirement.
- `DemotionDecisionV1`: exact profile/tuple, fixed trigger, prior/L0 levels, effective time, halt=true and `external_action_authorized=false`.

Every record is versioned, immutable, closed and bounded. Unknown/missing fields, free text, invalid Unicode/time, duplicates, mixed tuples, unsupported levels/classes or excessive counts fail closed. Canonical JSON uses sorted keys and integer/rational arithmetic; p95 uses deterministic nearest-rank.

## Qualification and recommendation

A cohort can qualify only after a future durable M7 acceptance/currentness source replaces the provisional bridge, the tuple is unexpired, every field is present, at least 30 distinct tasks have real M7 human acceptance, and all configured quality/security/cost/latency limits pass. Security failures, authorization failures and duplicate dispatches have zero tolerance. Sampled human audit covers at least 20% of cohort tasks and at least one task on every represented UTC day. Qualification is intentionally unreachable with the exact `4df2516` wire.

Promotion is gradual: one level per evaluation, capped at L2 and never an action. A missing gate holds current/L0. Expired or materially changed tuples cannot reuse a profile. Repository data and opaque receipt digests do not verify themselves or activate anything; verification and activation remain external trusted responsibilities.

## Immediate demotion

Fixed priority is security failure, authorization failure, incorrect merge, rollback, escaped defect, invalid attestation, policy bypass, unexplained regression. Any trigger returns the updated L0/halted profile and `DemotionDecisionV1` together. A halted profile cannot produce a new action recommendation inside its deterministic envelope.

## Rollout, rollback and M9

Under the source-only override, contracts/tests precede Tasks 1–3 implementation under strict RED→GREEN TDD. `m7_autonomy_wire.py` is temporary compatibility code: the factual M7 ancestry/restack must delete it and replace it with direct producer-contract imports plus durable lookups; keeping two implementations is forbidden. M9 may later consume an exact unexpired accepted profile and append delivery/rollback/regression outcomes, but gets no deployment authority from M8. Rollback is a reviewed revert before adoption or a closed forward adapter after adoption; factual evidence is never rewritten.
