# M7 local shadow handoff

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown cannot override typed IDs, risk, criteria, forbidden outcomes, or approval scopes.

Change ID: `20260902-implement-a-new-m7-ai-agent-shadow-handoff-featu-e5911c`  
Route: `e5911c3f8721`  
Approved scope: canonical M0–M9 design and parallel local-source implementation, supplied by the user on 2026-09-02  
Hard deadline: **2026-09-08 00:00 UTC+3**

## Problem and outcome

M7 must turn exact M4/M5/M6 evidence into a provider-independent immutable local handoff and aggregate real human shadow outcomes. The observable result is a closed `ready_for_human` bundle, immutable manual operator instructions, bounded non-PII outcomes and deterministic cohort failure classes—not a remote PR capability.

## Scope

In scope: pure frozen contracts, public JSON Schemas, exact SHA/digest bindings, deterministic stale/replay/incomplete/contradiction rejection, bounded integer metrics, documentation and M4→M9 connectivity. Out of scope: store/service/API/runtime wiring, migrations, providers, credentials, network, push, PR APIs, checks, merge, release, deployment, PII, raw prompts, bodies, logs, reasoning traces and any M5–M9 completion claim.

## Dependency ruling

The exact local M4 base is `9fe779ab9f90719201acfd01160d3452658ff075`. Provisional M5 `a98bbaace6a65e45808a71ecc6963bbdafc78082` and provisional M6 `befbd0bdbac5d47351ac80868f36e07487d2512b` both descend from old anchor `94fc5ad878e6b15df6418303caada49a3b93bf4c`, not accepted local M4, and M6 is not a factually accepted descendant of M5. Bridge schemas are development interfaces only; product implementation and durable/runtime integration are **BLOCKED** until dependency-ordered restack and fresh evidence.
