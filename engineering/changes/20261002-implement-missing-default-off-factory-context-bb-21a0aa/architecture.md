# Architecture — Implement missing default-off factory context BB contracts rotator registry hardened VibeVM store and Linux setup manager source contours with tests while preserving migrations 023 through 025

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The PR3d stack already owns context/decision/result foundations and migrations 023-025. The release candidate lacks the isolated BB, rotator, VibeVM-store and Linux setup-manager source contours.

## Proposed behavior

Copy only final disjoint feature files from clean donor branches, manually compose current architecture/docs, add `factory/runtime` to managed installation, and preserve every existing migration and runtime default.

## Components and boundaries

- BB: contracts only; disabled/native fallback/not_run.
- Rotator: pinned offline registry only.
- VibeVM: explicit-root Linux package store only.
- Setup manager: opt-in offline lifecycle with injected runtime adapter; no standalone activation.

## Data flow

Typed local inputs flow through closed validators and deterministic stores. Optional backend and model registries return native/not-run/default-off results unless a later qualified activation supplies separate authority.

## API and event contracts

New JSON schemas are closed and versioned. No new external event producer, network client, migration, or live provider API is activated.

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

Do not cherry-pick or merge divergent histories. Regenerate architecture views from the final canonical model. U4/macOS remains excluded.

## Risks and mitigations

Pin drift, path escape, implicit activation, host broadening, and stale migration identity are covered by exact regressions and independent mutation probes. Live qualification remains explicitly unclaimed.
