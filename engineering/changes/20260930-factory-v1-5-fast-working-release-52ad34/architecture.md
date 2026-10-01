# Architecture — Factory v1.5 fast working release

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The factory already has typed tasks, routing, bounded execution, semantic validation/repair, pricing, shadow evaluation, delivery handoff, and exact-SHA trust boundaries. It lacks one integrated versioned context/result/decision/qualification layer required by v1.5.

## Proposed behavior

Add strict sidecar contracts at existing seams. Preserve native behavior as the core path; optional package adapters remain default-off and unqualified until evidence exists.

## Components and boundaries

- `context_contracts`: selected project facts and canonical context identity.
- `decision_contracts`: factual append-only decision/timing/cost records.
- `result_contracts`: sanitized tool-result and semantic execution bindings.
- `prediction_contracts`: observation-only, dependency-free artifact validation.
- `qualification`: honest aggregation for operator/API/handoff.

## Data flow

Route/source/rules -> context manifest -> execution/broker result envelope -> semantic evidence -> factual decision/accounting -> qualification/handoff. Trust CI remains external merge authority.

## API and event contracts

New schemas are versioned sidecars. Existing execution v1/v2 event meanings and closed enums do not change.

The public context-manifest JSON Schema is a structural consumer contract, not standalone admission. Every schema-valid manifest must also pass `ContextManifestV1.from_dict`, which enforces UTF-8 byte bounds, secret detection, safe paths, content digests, and exact rule/source linkage.

The decision-record v1 sidecar is likewise structural at the JSON Schema boundary and semantically admitted by `DecisionRecordV1.from_dict`. State decisions bind the current and target state, lease owner, repository, task, run, attempt, and fence inside the same PostgreSQL transaction as the phase transition. Corrections append a same-task/run superseding record; update/delete privileges are withheld.

Migration 023 is the first installable decision-store lineage. The earlier monolithic `feature/factory-v15-fast-release` tree is a preserved, explicitly non-installable diagnostic preview (`release_candidate_ready=false`); databases created from it are unsupported and must be recreated, never upgraded by rewriting an applied 023. In this contour persistence is deliberately narrower than the wire contract: only the built-in state-transition rule can be stored, context/profile use the fixed unavailable-binding digest, evidence must be empty, and prediction/qualification sources fail closed until their authoritative registries arrive.

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

- U4/macOS is excluded by explicit owner decision on 2026-09-30.
- Use native context packaging for the fast release; optional FPF/VibeVM is retained only as default-off qualification surface.
- No ML dependency: U5 validates observation artifacts and returns `not_qualified` without suitable data.

## Risks and mitigations

- Large scope: deliver one minimal vertical with strict boundaries and focused tests.
- Stale branches: start from fetched `origin/main`; port no unproven branch wholesale.
- False completion: qualification distinguishes implemented, excluded, deferred, inactive, and externally pending.
