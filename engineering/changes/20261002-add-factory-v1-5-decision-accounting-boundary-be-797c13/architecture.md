# Architecture — Add Factory v1.5 decision accounting boundary behavior from source commit 531089f to the PR2 persistence foundation: enforce bounded cost and duration values and exact persisted accounting invariants as a new feature slice, with regression tests and isolated PR delivery

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Individually valid nonnegative USD-micros charges are added without revalidating the cumulative value, so two valid values can produce an integer larger than PostgreSQL signed bigint.

## Proposed behavior

Validate the cumulative known amount after each addition with the existing integer contract. Adapt source tests into `decision_contract_cases.py`; keep the discovery shim and in-process subset validator.

## Components and boundaries

- Runtime: `factory/src/adaptive_factory/decision_contracts.py` only.
- Tests: shared decision contract cases reached by Factory and root discovery.
- Unchanged: schema, migration 023, service/store persistence and public APIs.

## Data flow

Cost entry validation → cumulative addition → cumulative signed-bigint validation → factual summary. Unknown/estimated coverage continues to control completeness independently.

## API and event contracts

No wire or event change. The Python helper narrows invalid input admission only.

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

- Adapt, do not raw-cherry-pick, because PR2 moved tests into a shared module.
- Skip the source audit fix already present in PR2 and its obsolete implementation report.
- Do not attribute durable accounting or full U2/BB qualification to this slice.

## Risks and mitigations

- New rejection surprises a caller: current helper has no production callers; explicit error is safer than an unpersistable value.
- Discovery drift: exercise the same cases through both import surfaces.
