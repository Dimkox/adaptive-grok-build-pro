# M9 staged delivery on corrected exact M8 a937ac8

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260904-m9-staged-delivery-on-exact-m8-f53275d-331ca7`
Created: 2026-09-04T03:24:24+00:00
Risk: high
Complexity: high-risk
Domains: ai, data, security, api

## Problem

Implement feature M9 AI agent staged delivery and recovery control on corrected exact M8 head `a937ac8d200a4e143c295fabd482b19bc8cc4286`. Add closed signed-artifact metadata, deterministic staged decisions, least-authority recovery, an in-memory dry-run adapter, and canonical M8 producer linkage. Preserve unchanged PostgreSQL migrations `001`-`018` and security isolation across M4-M8. Repository-local code only; operational actions remain unreachable.

## Outcome

Exact M8 gains a repository-local M9 library that validates signed artifact and authority metadata, evaluates one bounded dry-run delivery step, records an immutable evidence chain through a reviewed in-memory adapter, and selects only least-authority recovery. Production remains structurally unreachable and every operational action remains outside this source checkpoint.

## Scope

### In scope

- Closed immutable version-1 artifact, exposure, promotion, observation, decision, recovery, evidence, and M8 handoff records.
- A thin M8 bridge over the integrated `adaptive_factory.autonomy` producer types; all M8 values and digests are reparsed or recomputed and durable acceptance/currentness remain unavailable.
- Deterministic preview, staging, and bounded-canary evaluation with exactly one permitted step per call and a human boundary before production.
- A locked in-memory dry-run controller/adapter with at-most-once application, bounded inputs and evidence, full digest chaining, expiry rechecks, and deterministic recovery.
- Focused synthetic tests, truthful architecture and project-state documentation, and a clean local `verifying` checkpoint.

### Out of scope

- Any operational adapter, network, subprocess, credential, key, real environment, database, migration, persistence, provider call, service activation, production effect, or external write.
- Automatic production or final-canary advancement, artifact publication, deployment, push, pull request, merge, tag, release, or claim of external acceptance.
- Duplicate M8/M7 producer models, caller-supplied M8 eligibility/currentness/acceptance, or modification of M4-M8 behavior and migrations `001`-`018`.

## Constraints

- Backward compatibility: M9 is additive on corrected exact M8 `a937ac8d200a4e143c295fabd482b19bc8cc4286`; canonical `6b42ba6` is snapshot source, not lineage authority.
- Data/privacy: records accept only bounded identifiers, digests, timestamps, authority resources, thresholds, observations, and reason codes; no secret or customer payload is introduced.
- Performance: observation, prior-evidence, and controller chains are bounded to 128 entries; all decisions are deterministic and local.
- Operational: only the exact sealed fake adapter may receive dry-run effects; production and all external capabilities are absent.
