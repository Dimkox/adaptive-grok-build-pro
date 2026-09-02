# Architecture — M8 earned autonomy provisional M4 bridge

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

This branch lacks M7 ancestry and contains no factual M7 cohort, accepted trust profile, activation path or merge authority. Exact M7 `4df2516` is a provisional producer-shape reference only.

## Proposed behavior

```text
full exact M7 4df wire (M4 -> M5 -> M6, bundle -> outcome -> cohort -> evaluation)
  -> bounded M8 validator/provider mapping + exact task receipt bindings
  -> six closed M8 values -> deterministic recommendation-only L0/L1/L2
  -> atomic L0 demotion/halt -> future separately gated M9 feedback
```

## Components and boundaries

`factory/src/adaptive_factory/autonomy.py` owns immutable M8 parsing, canonical identity, cohort aggregation, recommendations and demotion. Temporary `m7_autonomy_wire.py` owns only closed parsing and digest/equality recomputation for the exact `4df2516` wire; it has no caller-settable acceptance/currentness and grants no authority. The two schemas freeze these boundaries; no store, API, event, worker, key, network or external-effect adapter is added.

## Data flow

The tuple binds repository, `low_risk_text_only`, exact M7 cohort key/change class, agent and validator, a separate provider mapping, model/prompt/policy/runner/holdout/authority digests, L2 ceiling and expiry. Every task binds its task/run/result head and human receipt to an actual M7 bundle/outcome. Expiry or any material change starts a new cohort.

## API and event contracts

One additive closed JSON Schema v1; no HTTP API or event. Rates use integer arithmetic and p95 uses deterministic nearest-rank. Every represented UTC cohort day needs an audit sample.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- Repository evidence can produce only a recommendation; activation requires authority outside this package.
- Opaque digests are never keys or signatures; all producer digests that M7 defines as recomputable are recomputed here.
- External acceptance/currentness is not a wire field and therefore cannot be asserted by the caller; qualification is intentionally unreachable on `4df2516`.
- After factual M7 ancestry/restack, delete the temporary adapter and import producer contracts; keeping two implementations is prohibited.
- Every trigger returns L0 plus halted state in the same immutable result; L3/L4 are unrepresentable.
- The explicit 2026-09-02 user override permits pure source RED→GREEN work with synthetic boundary fixtures; activation, factual qualification and profile acceptance remain blocked.

## Risks and mitigations

- Fabricated cohort: no data/example fixture is checked in; later intake is separately reviewed.
- Provisional lineage: exact M4 base is explicit; M5/M6/M7 absence blocks implementation/activation.
- Self-promotion: no activation method or external action capability exists in the design.
