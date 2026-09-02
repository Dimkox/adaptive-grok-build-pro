# Architecture — M8 earned autonomy provisional M4 bridge

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

M8 is roadmap-only. This branch is an exact M4 descendant and contains no factual M7 cohort, trust profile, activation path or merge authority.

## Proposed behavior

```text
M4 identity -> M5 execution identity -> M6 validator identity
  -> factual M7 shadow evidence + opaque external verification receipts
  -> six closed M8 values -> deterministic recommendation-only L0/L1/L2
  -> atomic L0 demotion/halt -> future separately gated M9 feedback
```

## Components and boundaries

Future `factory/src/adaptive_factory/autonomy.py` owns immutable parsing, canonical identity, cohort aggregation, recommendations and demotion. Future `factory/contracts/jsonschema/earned-autonomy.v1.schema.json` follows the M6/M7 schema inventory and freezes the record shapes; no duplicate M8 schema is placed under `factory/contracts/schemas/`. No store, API, event, worker, key, network or external-effect adapter is added.

## Data flow

The tuple binds repository, `low_risk_text_only`, M4/M5/M6/M7 digests and exact M7 head, agent/provider/model/prompt identities, policy, runner image, holdout, authority observation, L2 ceiling and expiry. Every task/profile/decision carries its digest; expiry or any material change starts a new cohort.

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
- Opaque verified-input digests are never keys or signatures and are not verified here.
- Every trigger returns L0 plus halted state in the same immutable result; L3/L4 are unrepresentable.
- The explicit 2026-09-02 user override permits pure source RED→GREEN work with synthetic boundary fixtures; activation, factual qualification and profile acceptance remain blocked.

## Risks and mitigations

- Fabricated cohort: no data/example fixture is checked in; later intake is separately reviewed.
- Provisional lineage: exact M4 base is explicit; M5/M6/M7 absence blocks implementation/activation.
- Self-promotion: no activation method or external action capability exists in the design.
