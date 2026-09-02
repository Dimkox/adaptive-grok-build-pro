# Architecture — M7 local shadow handoff

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Decision

The provisional slice adds two pure modules beside M4: `shadow_contracts.py` for frozen closed values/bindings and `shadow_evaluation.py` for bounded aggregation/gates. Six public JSON Schemas mirror the same surfaces. Neither module is imported or wired to service/store/runtime; activation waits for the factual dependency restack.

```text
M4 task/run/owner/fence + intent/lease packet digest
  + M5 legacy-intent binding + TaskPacket/manifest/snapshot/result digests
      input: packet authority head == snapshot input head
      result: snapshot result head == WorkspaceResult head
  + M6 envelope/binding/validation-inputs/subject/evidence-set/verdict digests
      M6 subject head == M5 result head; exact closed pass verdict
      -> ShadowTaskEvidenceV1
      -> OperatorHandoffProposalV1(external_capability=absent)
      -> ReadyForPrBundleV1(status=blocked_pending_durable_lookup)
      -> human-owned ShadowOutcomeV1
      -> exact-tuple aggregate
      -> blocked | eligible_for_human_l2_review
```

The bridges repeat only factual shared identities. M4's legacy intent/lease packet digest binds M5/M6 `legacy_intent_digest`, while the M5 `task_packet_digest` remains a separate field. Input authority SHA is distinct from result SHA; snapshot, WorkspaceResult, M6 binding and M6 subject equality rules make the direction explicit. M6 exposes the producer names `envelope_digest`, `binding_digest`, `validation_inputs_digest`, `subject_digest`, `evidence_set_digest` and `verdict_digest`; the envelope and closed pass verdict are recomputed locally.

Binding, validation-input and evidence-set bodies are not present in this pure slice, so their hexadecimal values remain non-authoritative transport claims. Consequently the bundle cannot expose readiness. A future durable integration must load canonical producer bodies by exact identity, recompute every digest, and independently prove accepted dependency commits before changing that gate.

M8 may later consume immutable cohort evidence but M7 cannot create a trust profile. M9 receives no delivery capability from M7; exact merged SHA, signed artifact, canary policy and production promotion remain separately authenticated and human-owned.

Stable failures are `invalid_contract`, `stale_binding`, `digest_mismatch`, `semantic_not_pass`, `replay`, `cohort_mismatch`, `insufficient_sample`, `insufficient_observation`, `missing_baseline`, `quality_threshold`, `safety_violation`, `budget_or_deadline` and `containment_failure`.
