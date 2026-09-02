# M8 Earned and Revocable Autonomy Design

## Outcome and boundary

M8 is a pure local evaluator design, not an activation system. Its only eligible class is frozen as `low_risk_text_only`; six closed canonical v1 values bind complete cohort evidence to one exact material tuple and may issue recommendation-only `L0`, `L1`, or `L2` results. L3/L4, merge, network, credentials, persistence and production are absent.

This design is provisional on exact M4 `9fe779ab9f90719201acfd01160d3452658ff075`. Implementation and cohort completion are **BLOCKED** until accepted M5/M6 and factual accepted M7 are dependency-restacked and at least 30 real human-accepted eligible tasks exist for one tuple. The repository contains no factual cohort rows.

## Canonical records

- `AutonomyTupleV1`: repository, `low_risk_text_only`, M4/M5/M6/M7 identities and exact M7 head, agent/provider/model/prompt identities, policy, runner image, holdout, opaque verified authority observation, L2 ceiling and expiry.
- `CohortTaskEvidenceV1`: exact tuple digest, distinct task/run/head identities, eligible/human-accepted/audit outcomes, opaque human/attestation verification receipt digests and bounded quality/security/cost/latency/demotion facts.
- `CohortEvidenceV1`: tuple, ordered distinct tasks, configured class thresholds, factual M7-restack observation, cohort window and canonical digest.
- `AutonomyProfileV1`: exact tuple/cohort digests, current L0/L1/L2, computed bounded metrics, expiry and halted state.
- `PromotionRecommendationV1`: current/recommended level, closed reason codes, expiry, `external_action_authorized=false` and separate-activation requirement.
- `DemotionDecisionV1`: exact profile/tuple, fixed trigger, prior/L0 levels, effective time, halt=true and `external_action_authorized=false`.

Every record is versioned, immutable, closed and bounded. Unknown/missing fields, free text, invalid Unicode/time, duplicates, mixed tuples, unsupported levels/classes or excessive counts fail closed. Canonical JSON uses sorted keys and integer/rational arithmetic; p95 uses deterministic nearest-rank.

## Qualification and recommendation

A cohort can qualify only when M7 is factually restacked, the tuple is unexpired, every field is present, at least 30 distinct eligible tasks have real human acceptance, and all configured quality/security/cost/latency limits pass. Security failures, authorization failures and duplicate dispatches have zero tolerance. Sampled human audit covers at least 20% of cohort tasks and at least one task on every represented UTC day.

Promotion is gradual: one level per evaluation, capped at L2 and never an action. A missing gate holds current/L0. Expired or materially changed tuples cannot reuse a profile. Repository data and opaque receipt digests do not verify themselves or activate anything; verification and activation remain external trusted responsibilities.

## Immediate demotion

Fixed priority is security failure, authorization failure, incorrect merge, rollback, escaped defect, invalid attestation, policy bypass, unexplained regression. Any trigger returns the updated L0/halted profile and `DemotionDecisionV1` together. A halted profile cannot produce a new action recommendation inside its deterministic envelope.

## Rollout, rollback and M9

After the block clears, contracts/tests precede implementation under strict RED→GREEN TDD. M9 may later consume an exact unexpired profile and append delivery/rollback/regression outcomes, but gets no deployment authority from M8. Rollback is a reviewed revert before adoption or closed v2 forward adapter after adoption; factual evidence is never rewritten.
