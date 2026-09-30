# Architecture — Реализовать Factory v1.5 F24 F26 paired A/B/C qualification harness: frozen 12-case corpus, Pump Selector fixtures/oracle, behavior impact selector, immutable baseline, thresholds, budgets and deterministic tests

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Factory v1.5 can compose evidence, but has no accepted executable F24/F26 paired harness. Consequently it cannot prove that the same twelve domain cases, independent oracle, thresholds and budgets were used across A/B/C.

## Proposed behavior

Add a package-owned deterministic qualification module. It loads immutable corpus and baseline resources by pinned SHA-256, selects impact from actual changes, executes injected adapters in isolated logical attempts, applies a Pump Selector oracle, and emits a canonical observation-only report. The runner has no provider implementation and performs no external writes.

## Components and boundaries

- `behavior_qualification.py`: strict contracts, impact selector, resource loader, Pump oracle, paired runner and gates.
- `pump-selector-qualification-v1.json`: twelve frozen synthetic domain cases.
- `pump-selector-baseline-v1.json`: separately accepted expected baseline identities and scores.
- The executor boundary returns observations only. It cannot mutate trusted inputs through the API.

## Data flow

Pinned resources -> digest verification -> impact selection -> A/B/C executor calls -> independent oracle -> completeness/quality/budget gates -> immutable canonical report.

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

- Fixture gaming: stable IDs, pinned bytes and an independently stored baseline.
- Confounded comparison: common-pin equality and declared-factor validation.
- Cheap-but-wrong candidate: domain/safety gates precede efficiency.
- Partial execution: exact required case/mode/attempt accounting.
