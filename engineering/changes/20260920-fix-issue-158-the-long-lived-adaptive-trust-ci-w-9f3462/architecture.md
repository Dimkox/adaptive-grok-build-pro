# Architecture — Fix issue #158: the long-lived adaptive-trust-ci worker accumulates unreaped [git] defunct children (measured 4 over ~24h, NRestarts=0), so every subprocess path must reap on all outcomes including the accepted 'zombie_only' classification; locate the real leak empirically rather than assuming a missing wait, add a test whose control fails on current code, and keep exit-status classification and all attestation/policy semantics untouched.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

## Proposed behavior

## Components and boundaries

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

## Risks and mitigations
