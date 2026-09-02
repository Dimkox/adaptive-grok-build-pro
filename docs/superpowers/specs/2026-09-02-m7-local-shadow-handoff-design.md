# M7 Local Shadow Handoff — Design

## Status and authority

Approved local-source design under route `e5911c3f8721`, now represented by provisional pure source/schema commits through `5615933`. It does not accept provisional M5/M6, activate runtime integration, authorize remote operations, or replace exact-SHA Trust CI and human merge.

## Decision

Implement M7 provisionally as two dependency-free local modules: frozen closed canonical contracts and a deterministic bounded cohort evaluator. Consume explicit M4/M5/M6 bridge values without importing provisional producer code, but classify those opaque values as transport claims. Expose only an immutable `blocked_pending_durable_lookup` inspection bundle and fixed manual operator instructions; readiness requires future durable canonical producer lookup plus dependency-ordered external acceptance.

## Alternatives

1. Import provisional M5/M6 classes: rejected because both branches descend from `94fc5ad` and would turn a provisional shape into acceptance.
2. Add database/API/worker publication now: rejected because no accepted predecessor chain or transactional integration contract exists.
3. Closed bridges on M4, selected after the block clears: keeps source provider-independent, makes each dependency explicit and fails closed if restacked facts differ.

## Public model

- `M4ControlPlaneBridgeV1`: preserves factual task/run/owner/fence plus M4 intent and lease-packet fields.
- `M5ExecutionBridgeV1`: preserves the separate legacy-intent and TaskPacket identities, manifest/snapshot/result digests, packet authority input SHA and snapshot/result SHAs.
- `M6SemanticBridgeV1`: preserves exact envelope/binding/validation-inputs/subject/evidence-set/verdict producer names, subject/result SHA linkage and a canonical closed pass verdict.
- `ShadowTaskEvidenceV1`: exact cross-stage identity root; it contains no product SHA, dependency-state, synthetic receipt or caller-authored authority field.
- `OperatorHandoffProposalV1`: subject digest, `external_capability=absent`, `recommended_action=human_review`, fixed sorted instruction enums.
- `ReadyForPrBundleV1`: roadmap-compatible historical name; closed `status=blocked_pending_durable_lookup`; digest covers every nested canonical field but grants no readiness.
- `ShadowCohortKeyV1`: repository, change class, provider-neutral agent/validator/model/prompt/policy/runner/holdout/authority tuple.
- `ShadowOutcomeV1`: bounded human decision and numeric quality/safety/cost/latency evidence without bodies or PII.
- Aggregate/evaluation: literal integer counts/millionths and sorted failure classes; maximum recommendation `eligible_for_human_l2_review`.

## Invalidation, replay and gate

Shared bridge fields match exactly. Snapshot input equals TaskPacket authority; snapshot result equals WorkspaceResult and M6 subject head. M6 must carry the exact deterministic closed pass verdict, whose body/digest and envelope digest are recomputed. Other opaque digests do not become authority until durable integration loads their canonical producer bodies. Outcomes are unique by outcome ID and bundle digest.

The evaluator accepts only `ShadowCohortV1` and recomputes the aggregate from its exact outcomes; a directly constructed aggregate is never an authorization input. It then encodes the roadmap gate: at least 30 human-merged accepted tasks; 14 observation days or a release cycle; 30 baseline tasks; acceptance ≥90%; rework ≤10%; false negatives ≤5%, false positives/disagreement ≤10%; p95 repairs ≤2 and max 3; all budget/deadline/SLO bounds; ≥30% median review reduction; zero critical/high misses, security misses, unauthorized effects, rollbacks, escaped defects, duplicates and unaccounted calls; 100% injection containment. A pass recommends only human L2 review and cannot promote policy.

## M4 → M9 connectivity

M4 provides durable task/run/fence/packet identity. Accepted restacked M5 later provides isolated manifest/result/authority evidence. Accepted restacked M6 later provides semantic subject/verdict/evidence. M7 freezes those facts into human-owned shadow evidence. M8 may consume exact cohort evidence but remains L2-capped. M9 gains no capability from M7: exact merged SHA, signed artifact, canary policy and production promotion remain separately authenticated and human-owned.

## Rollout and rollback

Current rollout is inert provisional local library/schema source only. Activation is BLOCKED: future rollout restacks M4 → M5 → M6 → M7, reconciles producer fields, declares final architecture ownership and reruns every check/review. Rollback is an exact commit revert; no migration, network or production state exists.
