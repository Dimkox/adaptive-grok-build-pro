# Architecture — M7 local shadow handoff

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Decision

The provisional slice adds two pure modules beside M4: `shadow_contracts.py` for frozen closed values/bindings and `shadow_evaluation.py` for bounded aggregation/gates. Six public JSON Schemas mirror the same surfaces. Neither module is imported or wired to service/store/runtime; activation waits for the factual dependency restack.

```text
accepted M4 task/run/fence/packet
  + accepted M5 manifest/result/authority (future restack fact)
  + accepted M6 pass/verdict/evidence (future restack fact)
      -> ShadowTaskEvidenceV1
      -> OperatorHandoffProposalV1(external_capability=absent)
      -> ReadyForPrBundleV1(status=ready_for_human)
      -> human-owned ShadowOutcomeV1
      -> exact-tuple aggregate
      -> blocked | eligible_for_human_l2_review
```

The bridges repeat shared identities so task/run/fence/packet/head mismatch is observable. M6 must be pass with complete coverage, no contradiction and no unsupported pass. Any relevant mutation rotates the evidence/bundle digest. Outcomes are unique by outcome ID and bundle digest.

M8 may later consume immutable cohort evidence but M7 cannot create a trust profile. M9 receives no delivery capability from M7; exact merged SHA, signed artifact, canary policy and production promotion remain separately authenticated and human-owned.

Stable failures are `invalid_contract`, `dependency_not_accepted`, `stale_binding`, `incomplete_evidence`, `contradictory_evidence`, `semantic_not_pass`, `replay`, `cohort_mismatch`, `insufficient_sample`, `insufficient_observation`, `missing_baseline`, `quality_threshold`, `safety_violation`, `budget_or_deadline` and `containment_failure`.
