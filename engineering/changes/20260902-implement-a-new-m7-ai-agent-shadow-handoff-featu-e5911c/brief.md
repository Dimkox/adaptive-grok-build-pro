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

The exact historical M7 base is `9fe779ab9f90719201acfd01160d3452658ff075`. Current provisional M5 is `141e51e75b2bb337fa3bb1544639c6c46c287309`; provisional M6 `5c5c37136f20404a927fd2ad7621ad0f7fcae8e6` still has mutual M5 merge-base `61db79f07904ae5facb244c34b26c8383504dd88` and exposes no factual M5 result linkage. Pure bridge/evaluator/schema source is present through `5615933`, but those bridges remain development interfaces; activation, completion and durable/runtime integration are **BLOCKED** until dependency-ordered restack and fresh evidence.
