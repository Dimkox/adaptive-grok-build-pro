# M7 local shadow handoff

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown cannot override typed IDs, risk, criteria, forbidden outcomes, or approval scopes.

Change ID: `20260902-implement-a-new-m7-ai-agent-shadow-handoff-featu-e5911c`  
Route: `e5911c3f8721`  
Approved scope: canonical M0–M9 design and parallel local-source implementation, supplied by the user on 2026-09-02  
Hard deadline: **2026-09-08 00:00 UTC+3**

## Problem and outcome

M7 must preserve observable M4/M5/M6 producer identities in a provider-independent immutable local handoff and aggregate exact human shadow outcomes. The current pure bridge produces only a `blocked_pending_durable_lookup` inspection bundle because its opaque digests are caller claims; durable producer lookup and accepted dependency ancestry are mandatory before any readiness state.

## Scope

In scope: pure frozen contracts, public JSON Schemas, exact SHA/digest bindings, deterministic stale/replay/incomplete/contradiction rejection, bounded integer metrics, documentation and M4→M9 connectivity. Out of scope: store/service/API/runtime wiring, migrations, providers, credentials, network, push, PR APIs, checks, merge, release, deployment, PII, raw prompts, bodies, logs, reasoning traces and any M5–M9 completion claim.

## Dependency ruling

The exact historical M7 base is `9fe779ab9f90719201acfd01160d3452658ff075`. Producer shapes were re-audited only as provisional references at M5 `cbfca6550acaa50508eec5829df2724093e32076` and M6 `534b66753ca865974d520f60103b3a18292295ba`; neither SHA is payload authority or accepted dependency evidence. Activation, completion and durable/runtime integration are **BLOCKED** until dependency-ordered restack, durable exact-producer lookup and fresh external acceptance evidence.
