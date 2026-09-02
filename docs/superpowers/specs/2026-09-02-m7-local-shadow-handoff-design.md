# M7 Local Shadow Handoff — Design

## Status and authority

Approved local-source design under route `e5911c3f8721`, implementing the canonical M0–M9 program decision supplied by the user. It does not accept provisional M5/M6, authorize remote operations, or replace exact-SHA Trust CI and human merge.

## Decision

After accepted dependency-ordered restack, implement M7 as two dependency-free local modules: frozen closed canonical contracts and a deterministic bounded cohort evaluator. Consume explicit M4/M5/M6 bridge values instead of importing provisional producer code. Expose only an immutable `ready_for_human` bundle and fixed manual operator instructions; keep runtime/durable wiring absent until factual producer contracts exist.

## Alternatives

1. Import provisional M5/M6 classes: rejected because both branches descend from `94fc5ad` and would turn a provisional shape into acceptance.
2. Add database/API/worker publication now: rejected because no accepted predecessor chain or transactional integration contract exists.
3. Closed bridges on M4, selected after the block clears: keeps source provider-independent, makes each dependency explicit and fails closed if restacked facts differ.

## Public model

- `M4ControlPlaneBridgeV1`, `M5ExecutionBridgeV1`, `M6SemanticBridgeV1`: repeat task/run/fence/packet/head identities and bind producer product SHAs plus stage digests.
- `ShadowTaskEvidenceV1`: exact cross-stage identity root plus local evidence, receipt-set and source-bundle digests.
- `OperatorHandoffProposalV1`: subject digest, `external_capability=absent`, `recommended_action=human_review`, fixed sorted instruction enums.
- `ReadyForPrBundleV1`: roadmap-compatible name; closed `status=ready_for_human`; digest covers every nested canonical field.
- `ShadowCohortKeyV1`: repository, change class, provider-neutral agent/validator/model/prompt/policy/runner/holdout/authority tuple.
- `ShadowOutcomeV1`: bounded human decision and numeric quality/safety/cost/latency evidence without bodies or PII.
- Aggregate/evaluation: literal integer counts/millionths and sorted failure classes; maximum recommendation `eligible_for_human_l2_review`.

## Invalidation, replay and gate

Shared bridge fields match exactly. M6 must be pass with complete coverage, zero unsupported passes and zero contradictions. Any field mutation rotates the digest. Outcomes are unique by outcome ID and bundle digest.

The evaluator encodes the roadmap gate: at least 30 human-merged accepted tasks; 14 observation days or a release cycle; 30 baseline tasks; acceptance ≥90%; rework ≤10%; false negatives ≤5%, false positives/disagreement ≤10%; p95 repairs ≤2 and max 3; all budget/deadline/SLO bounds; ≥30% median review reduction; zero critical/high misses, security misses, unauthorized effects, rollbacks, escaped defects, duplicates and unaccounted calls; 100% injection containment. A pass recommends only human L2 review and cannot promote policy.

## M4 → M9 connectivity

M4 provides durable task/run/fence/packet identity. Accepted restacked M5 later provides isolated manifest/result/authority evidence. Accepted restacked M6 later provides semantic subject/verdict/evidence. M7 freezes those facts into human-owned shadow evidence. M8 may consume exact cohort evidence but remains L2-capped. M9 gains no capability from M7: exact merged SHA, signed artifact, canary policy and production promotion remain separately authenticated and human-owned.

## Rollout and rollback

Current rollout is docs/spec/plan only and is BLOCKED before product code. Future rollout restacks M4 → M5 → M6 → M7, reconciles fields and reruns all checks. Rollback is an exact commit revert; no migration, network or production state exists.
