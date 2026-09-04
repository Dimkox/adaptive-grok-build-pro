# M8 earned autonomy on exact M7 00e0e4f

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260904-m8-earned-autonomy-on-exact-m7-00e0e4f-3ec8b3`
Created: 2026-09-04T03:11:33+00:00
Risk: medium
Complexity: standard
Domains: ai, api

## Problem

Implement feature M8 AI agent earned autonomy on exact M7 head 00e0e4f9a6f50844bf9e0ffc7139d3283dda889f. Add a closed autonomy tuple, cohort evaluation, one-level recommendation capped at L2, an independent activation gate, deterministic priority-ordered demotion to L0, and canonical M7 producer linkage. Preserve predecessor source and migrations. Repository-local code only; no live execution or outside writes.

## Outcome

Exact M7 gains a repository-local M8 decision layer that evaluates a closed, factual cohort for a one-level autonomy recommendation capped at L2 and can deterministically halt and demote a profile to L0. The M7 bridge reuses the actual M7 producer contracts and recomputes their aggregate and evaluation; it does not duplicate M7 authority or make acceptance, currentness, activation, or external action available.

## Scope

### In scope

- One closed earned-autonomy version-1 schema and one thin M7-to-M8 bridge schema that resolves the canonical M7 schemas offline.
- An M8 autonomy tuple, per-task evidence, cohort, profile, promotion recommendation, and demotion-decision model.
- A thin bridge over actual `ReadyForPrBundleV1`, `ShadowOutcomeV1`, `ShadowCohortV1`, `aggregate_shadow_cohort`, and `evaluate_shadow_cohort`, adding only an M8 provider mapping and envelope.
- Deterministic bounded evaluation, one-level recommendation, separate-activation requirement, expiry/replay rejection, and priority-ordered L0 halt/demotion.
- Focused synthetic tests and additive architecture ownership.

### Out of scope

- Real human cohort acquisition, durable currentness or acceptance lookup, activation, profile persistence, runtime service/API wiring, provider execution, database work, and telemetry emission.
- Any level above L2, automatic promotion, automatic merge, external command, network, credential, delivery, or production capability.
- Modification or replacement of M4-M7 producer authority, migrations, contracts, tests, or runtime behavior.

## Constraints

- Backward compatibility: M8 is additive on exact M7 `00e0e4f9a6f50844bf9e0ffc7139d3283dda889f`; canonical `2cee9b9` is semantic source, not lineage authority.
- Data/privacy: task evidence is digest-, identifier-, bounded metric-, and timestamp-only; no prompts, reasoning traces, credentials, commands, or personal data are accepted.
- Performance: cohort size is bounded to 10,000 and all calculations use deterministic integer arithmetic without I/O.
- Operational: source-only outputs are recommendations with `separate_activation_required=true` and `external_action_authorized=false`; currentness and external acceptance remain unavailable.
