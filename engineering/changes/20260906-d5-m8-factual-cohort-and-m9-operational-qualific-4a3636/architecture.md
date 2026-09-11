# Architecture — D5 qualification accounting

Authority: analysis-architect.md on `fd51dcf`.

## Current behavior

`evaluate_autonomy` already fail-closes: L2 cap, separate activation required, no external action. M7 bridge hardcodes acceptance/currentness false. M9 `DryRunController` accepts only `FakeEnvironmentAdapter`; production is unreachable. Factual cohort records on main: **0**.

## Proposed behavior

Additive factual/operational layer. Do not reimplement algorithms.

```
AutonomyTupleV1.digest
  → FactualCohortLedgerV1 (empty default, count=0)
  → evaluate_activation → activated=false
  → evaluate_m9_operational_qualification → qualified=false
```

## Components

- `factory/src/adaptive_factory/factual_cohort.py` — ledger + append reject + `evaluate_activation`
- `delivery/src/adaptive_delivery/operational_qualification.py` — M9 four-class predicate wrapping M8 activation
- Tests beside existing suites; reuse synthetic fixtures only as **negative** cases
- Persistence: operator/temp JSON or in-memory; no committed DB; no SQL 019

## Frozen

`evaluate_autonomy`, `demote_profile`, `m7_autonomy_bridge` booleans, `DryRunController`, migrations 001–018, VERSION 2.0.15.

## Risks

- Backdoor `qualified` when autonomy says `m7_bundle_blocked` → accounting must not override algorithm reasons.
- Empty `CohortEvidenceV1` mutation of M7 minItems → forbidden; empty lives only on the ledger.
