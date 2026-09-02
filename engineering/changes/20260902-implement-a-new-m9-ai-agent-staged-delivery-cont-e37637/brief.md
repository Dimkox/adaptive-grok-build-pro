# M9 Staged Delivery and Recovery — Source-Only Checkpoint

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, approval scopes, external Trust CI, or human production authority.

Change ID: `20260902-implement-a-new-m9-ai-agent-staged-delivery-cont-e37637`  
Route: `e376373492fe`  
Provisional source base: `9fe779ab9f90719201acfd01160d3452658ff075`  
Created: 2026-09-02T00:37:13+00:00  
Risk: high  
Complexity: high-risk  
Domains: ai, security, api

## Problem

The roadmap defines accepted M9 delivery after accepted M8 evidence. The 2026-09-02 user ruling permits pure local Tasks 1–4 with synthetic opaque exact identities, but invented M8, signature, cohort, artifact, environment or recovery facts must never become promotion authority.

## Outcome

Implement the first four local-only TDD tasks: closed records, deterministic evaluation, narrowing recovery and a dry-run state machine through preview, staging, bounded canary and a human-owned production boundary. Synthetic fixtures carry opaque exact identities only. This checkpoint creates no factual artifact, signature, cohort, environment, deployment, recovery proof, acceptance, release or external action.

## Scope

### In scope

- Closed field-level definitions for `SignedArtifactRefV1`, `DeliveryPromotionV1`, `EnvironmentObservationV1`, `ExposurePlanV1`, `DeliveryDecisionV1`, `RecoveryDecisionV1`, and `DeliveryEvidenceV1`.
- Deterministic gate semantics for health, error, latency, security and business observations.
- Exact M4→M5→M6→M7→M8→M9 dependency and invalidation map.
- TDD implementation of Tasks 1–4 for pure contracts, evaluator, recovery, dry-run controller and in-memory fake environment adapter.
- Schedule, release, rollback, evidence ledger and explicit blocker ownership through the hard deadline **2026-09-08 00:00 UTC+3**.
- README and roadmap status parity for this documentation-only checkpoint.

### Out of scope

- Task 5 schema/architecture integration, runtime state or activation.
- Real or simulated cryptographic signing, private/public key handling, signature verification, approval minting, or signed-envelope construction.
- Fabricated M8 trust profiles, cohorts, observations, artifacts, environments, canary results or recovery results.
- Infrastructure/provider/network/connector/system-command paths, credentials, process execution or production mutation.
- Push, pull request, merge, tag, release, deployment, Trust CI mutation or branch-protection change.

## Constraints

- Backward compatibility: all source contracts use explicit `V1` names, closed fields and additive-new-version evolution; no existing contract is changed.
- Data/privacy: only bounded identifiers, digests, timestamps, numeric aggregates and closed reason codes; no PII, secret, prompt, reasoning, log body or untrusted response body.
- Performance: the future evaluator is pure and bounded by fixed environment, metric and evidence cardinalities; no retries or polling in the core.
- Operational: production is always `needs_human` and unreachable by the current route. Automatic recovery can only halt, decrease bounded exposure, or restore the exact prior signed artifact already bound in the promotion.

## Status

Source-only Tasks 1–4 are authorized in separate TDD commits. Task 5 integration, factual accepted M8 restack, externally verified signed inputs and prior artifact, a separately authorized nonproduction environment, exercised recovery, activation, reviews/receipts, PR/merge, Trust CI and production are incomplete or `BLOCKED`; see [`ledger.md`](ledger.md).
