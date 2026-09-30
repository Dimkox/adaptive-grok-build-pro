# Architecture — Реализовать Factory v1.5 F24 F26 paired A/B/C qualification harness: frozen 12-case corpus, Pump Selector fixtures/oracle, behavior impact selector, immutable baseline, thresholds, budgets and deterministic tests

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Factory v1.5 can compose evidence, but has no accepted executable F24/F26 paired harness. Consequently it cannot prove that the same twelve domain cases, independent oracle, thresholds and budgets were used across A/B/C.

## Proposed behavior

Add a package-owned deterministic evidence module. Local resources are fixtures only, and no local or caller-supplied object can produce `pass`. A successful candidate run emits only `ready_for_external_qualification` with exact corpus, baseline, oracle and profile identities; failures emit `not_qualified`. External Trust CI/holdout qualification is out-of-process, remains `NOT_RUN` here, and is the sole qualification authority.

## Components and boundaries

- `behavior_qualification.py`: strict contracts, hash-verifying impact selector, anchored resource loader, distinct Pump/lifecycle/routing/recovery/cross-conflict oracles, generic closed comparator profile, paired runner and gates.
- `pump-selector-qualification-v1.json`: four Pump Selector, four factory and four cross-component/rule-conflict frozen cases.
- `pump-selector-baseline-v1.json`: separately accepted expected baseline identities and scores.
- The executor boundary returns observations only. It cannot mutate trusted inputs through the API.
- `make_comparator_profile` is an additive comparison seam for BB/native observation. A profile contains a registry-resolved `oracle_id`, never a callable or enable flag. BB may produce candidate evidence, but remains disabled and unqualified until the out-of-process authority evaluates its exact identity.

## Data flow

Local resources -> impact selection -> A/B/C executor calls -> closed oracle registry -> completeness/quality/budget gates -> immutable candidate evidence -> separately operated external Trust CI/holdout.

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

- Fixture gaming: stable IDs, reported corpus/baseline/oracle identities, exact domain schemas and executable negative controls. Only the out-of-process holdout can accept them; repository code and caller objects are not qualification authority.
- Confounded comparison: common-pin equality and declared-factor validation; strict benefit requires both context-load and reread reductions.
- Cheap-but-wrong candidate: domain/safety gates precede efficiency.
- Partial execution: exact required case/mode/attempt accounting.
