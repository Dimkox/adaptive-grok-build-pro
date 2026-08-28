# M3-M9 production delivery continuation

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260826-m3-m9-production-delivery-continuation-355689`
Created: 2026-08-28T12:58:26+00:00
Risk: high
Complexity: high-risk
Domains: ai, security

## Problem

Architect and implement an AI/LLM model-agnostic autonomous local software factory with Codex as the first provider adapter, prompt-injection-resistant immutable task packets, secret and network isolation, a persistent systemd supervisor, durable bounded leases/retries, up to 20 read-note agents, exactly one application-code writer, and no autonomous external writes

## Outcome

Deliver M3 as the next independently verified milestone, then use its exact `GovernanceHandoffV1` as the gate for separate M4–M9 branches. The final M9 outcome is exact-SHA signed preview/staging/canary delivery with exercised rollback and human-owned production promotion.

## Scope

### In scope

- Finish the existing M3 plan on the exact M2-A stack base.
- Restore the reviewed provider-neutral factory design that the M3 plan names as its binding spec.
- Preserve a dependency-ordered, separately gated M4–M9 delivery map.
- Produce local verification and independent review evidence for the exact M3 tree.

### Out of scope

- Combining M3–M9 into one branch or PR.
- Deploying Trust CI policy, holdout, keys, databases, systemd, preview, staging, canary, or production in the M3 change.
- Agent-owned push, merge, release, production promotion, or human-approval signing.

## Constraints

- Backward compatibility: M1/M2 contracts remain versioned and unknown versions fail closed.
- Data/privacy: prompts, raw reasoning, secrets, and external credential material are never governance records.
- Performance: all repository input is size/depth/count bounded and deterministically normalized.
- Operational: one application-code writer; route-selected independent reviews; PR-only delivery; external Trust CI remains merge authority.
