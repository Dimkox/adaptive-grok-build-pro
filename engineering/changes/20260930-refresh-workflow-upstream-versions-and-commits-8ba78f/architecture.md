# Architecture — Refresh workflow upstream versions and commits

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The advisory adapters accept version-neutral source manifests. Config records stable versions and named verification tests; README carries a dated table. Runtime parsing, route selection, canonical governance and receipt authority remain distinct.

## Proposed behavior

Add `upstream_commit` for each peeled stable tag and `observed_main_commit` for a separately dated main observation. Update stable versions only when a release exists. Bind all eight README columns to config and bind expected commits to independently observed literals in the contract test.

## Components and boundaries

Only toolchain metadata, README, parser characterization tests and this change package change. No runtime parser, installer, schema or trust-policy migration is required. Existing old-format tests stay named in `verification_tests` alongside current-revision samples.

## Data flow

## API and event contracts

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

- Stable BMAD remains 6.12.0; its main ticket template is advisory context without a native task contract.
- Superpowers 6.4.2 `Spec`/`Interfaces` plan text stays opaque; pointers are never automatically loaded.
- Compact upstream excerpts are embedded only in tests with exact path/commit provenance. Framework sources are neither installed nor vendored.

## Risks and mitigations

An upstream main may move immediately after observation. Full immutable commit IDs and the observation date preserve what was checked; no floating ref is used at runtime. Template excerpts characterize the accepted subset, not all upstream behavior.
