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

## Current delivery status

M3 Tasks 1–7 are implemented and independently task-reviewed through product commit `73a45d1feea639247fe5f66052f4a72cd6e98f9a`; the latest review-only head is `e7c903d837af437904b2e43a909b9e1a5bb67fc6`. Focused evidence proves the strict records/loader, lifecycle, governance authority gates, example/debt semantics, exact handoff builder, executable architecture fitness, governance-bound receipts, installer boundary, and stale-source protections.

Task 8 final verification and the code/test/security/release review wave remain open and must bind the post-package final fingerprint. M4 is the next separate stacked PR after M3 passes its local and external gates. M5–M9 remain roadmap/design only; no merge, deployment, external authority, or production result is claimed.

Restack note (2026-08-31): the checkpoint identities above remain historical evidence only. Accepted M2 advanced to exact commit `022411b05924618cfde0cb97b8c8aff4955e6013`, so the active restack package must integrate that predecessor and regenerate verification, reviews, architecture/governance evidence, and any handoff for the resulting exact M3 head; none of the earlier exact-state artifacts are reused.

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
