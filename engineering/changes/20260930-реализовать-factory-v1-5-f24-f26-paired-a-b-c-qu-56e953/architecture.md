# Architecture — Реализовать Factory v1.5 F24 F26 paired A/B/C qualification harness: frozen 12-case corpus, Pump Selector fixtures/oracle, behavior impact selector, immutable baseline, thresholds, budgets and deterministic tests

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Factory v1.5 can compose evidence, but has no accepted executable F24/F26 paired harness. Consequently it cannot prove that the same twelve domain cases, independent oracle, thresholds and budgets were used across A/B/C.

## Proposed behavior

Add a package-owned deterministic qualification module. Local resources are fixtures only: an externally supplied `QualificationTrustAuthority` must bind their exact corpus, baseline and closed oracle identities plus the enabled profile ID before a pass is possible. Without that authority the result is `not_qualified`. The runner derives impact from hashed text changes, executes isolated attempts, applies semantic oracles and mutants, and performs no external writes.

## Components and boundaries

- `behavior_qualification.py`: strict contracts, hash-verifying impact selector, anchored resource loader, distinct Pump/lifecycle/routing/recovery/cross-conflict oracles, generic closed comparator profile, paired runner and gates.
- `pump-selector-qualification-v1.json`: four Pump Selector, four factory and four cross-component/rule-conflict frozen cases.
- `pump-selector-baseline-v1.json`: separately accepted expected baseline identities and scores.
- The executor boundary returns observations only. It cannot mutate trusted inputs through the API.
- `make_comparator_profile` is an additive comparison seam for BB/native observation. A profile contains an `oracle_id`, never a callable or enable flag; only the external authority can enable its exact ID. BB therefore defaults to `not_qualified`.

## Data flow

Local resources -> external authority identity resolution -> impact selection -> A/B/C executor calls -> closed oracle registry -> completeness/quality/budget gates -> immutable canonical report.

## API and event contracts

No HTTP or event contract changes. The Python contract is additive, closed and versioned. Retries are bounded and all attempts remain in evidence.

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

- Reuse the existing factory package and qualification concepts; do not add an evaluator service or database.
- Use deterministic synthetic Pump Selector fixtures before any separately authorized live profile qualification.
- Keep unknown numeric observations as JSON null and authority effect as `none`.

## Risks and mitigations

- Fixture gaming: stable IDs, external authority-bound corpus/baseline/oracle identities, exact domain schemas and executable negative controls. Repository constants are not qualification authority.
- Confounded comparison: common-pin equality and declared-factor validation; strict benefit requires both context-load and reread reductions.
- Cheap-but-wrong candidate: domain/safety gates precede efficiency.
- Partial execution: exact required case/mode/attempt accounting.
