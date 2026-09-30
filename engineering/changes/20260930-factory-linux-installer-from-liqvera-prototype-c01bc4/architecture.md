# Architecture — Factory Linux installer from Liqvera prototype

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`install_into.py` safely materializes a complete stack into an absent target. `factory/runtime/install-claw.sh` prepares an inactive exact-SHA L5 release. Neither provides a reusable packaged-release lifecycle manager.

## Proposed behavior

Add a separate stdlib host-side setup manager under `factory/runtime/`, adapted from Liqvera's verified lifecycle patterns but parameterized for Factory artifacts and existing entrypoints.

## Components and boundaries

- Strict release manifest/archive verifier.
- Read-only host/root preflight.
- Locked durable operation state and immutable release staging.
- Product adapter for existing Factory/L5 entrypoints and health observation.
- Lifecycle CLI with safe update/reversal/removal semantics.

## Data flow

External digest + archive -> independent verification -> preflight -> immutable staging -> start/health -> atomic `current` switch -> durable state. Failures leave prior release authoritative.

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

- Reuse Liqvera safety patterns, not its service topology or product configuration.
- Fail closed on update until real backup/migration compatibility evidence exists.
- Keep activation/deployment human-owned and separate.

## Risks and mitigations

- Proprietary source: owner explicitly directed transfer; record exact provenance and do not claim upstream open licensing.
- Host mutation: tests use temporary roots and injected adapters; no live host actions during verification.
