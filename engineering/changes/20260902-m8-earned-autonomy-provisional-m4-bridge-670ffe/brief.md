# M8 earned autonomy provisional M4 bridge

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260902-m8-earned-autonomy-provisional-m4-bridge-670ffe`
Created: 2026-09-02T00:27:20+00:00
Risk: high
Complexity: high-risk
Domains: ai, security, api

Implementation base: `9fe779ab9f90719201acfd01160d3452658ff075`  
Branch: `milestone/m8-earned-autonomy-provisional-m4`

## Problem and outcome

Freeze a dependency-free local M8 contract/evaluator design that can later consume factual M7 shadow evidence and issue only deterministic `L0`, `L1`, or `L2` recommendations. It cannot activate autonomy, merge, push, call a provider, verify signatures, or perform an external action.

## Scope

### In scope

- Six frozen canonical records, one `low_risk_text_only` class and an exact tuple.
- At least 30 distinct real human-accepted eligible tasks; complete-data, quality, security, cost, latency and >=20% daily audit gates.
- Recommendation-only gradual promotion, tuple expiry/non-reuse and atomic fail-closed demotion.
- Bounded non-PII metrics, schema/test design and M4→M9 documentation.
- Under the explicit 2026-09-02 user override, pure local contracts, a deterministic evaluator and atomic demotion may be implemented against opaque exact predecessor identities and clearly labeled synthetic boundary fixtures.

### Out of scope

- Cohort population, keys/signature verification, activation, persistence, APIs, PR/GitHub/Trust CI writes, L3/L4, auto-merge, deployment, production, credentials and network.

## Constraints

- Backward compatibility: additive v1 only; later M7 mismatch requires a reviewed v2 adapter.
- Data/privacy: bounded opaque IDs/digests and aggregate integers only; no names, email, free text, PII, secrets or keys.
- Performance: future evaluator must cap a cohort at 10,000 tasks and use integer arithmetic.
- Operational: the live route copy's unrelated `base_commit=78ad2f...` is contextual routing data, not ancestry. Product claims bind to exact M4 `9fe779ab...`.

## Split gate

Pure source implementation is allowed by the explicit 2026-09-02 user override, without implying predecessor acceptance. Activation, completion, factual cohort qualification, profile issuance/acceptance and every external effect remain **BLOCKED** until accepted M5 and M6 are restacked, factual accepted M7 is restacked through M4→M5→M6→M7, and at least 30 real human acceptances exist for one exact tuple. No cohort row is checked in; synthetic test fixtures are algorithmic boundary data only.
