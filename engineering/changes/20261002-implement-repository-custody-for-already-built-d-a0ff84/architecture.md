# Architecture — Implement repository custody for already-built deterministic v2.1.0 package bytes from source e5856acfd4bc7a186f40a740b54ec86459462db5: add ZIP and checksum, update candidate state documentation and binding tests without publication or activation

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The artifact pair exists untracked and was built twice from exact clean source.

## Proposed behavior

Track the pair and bind it in state/docs/tests without changing runtime behavior.

## Components and boundaries

Repository package custody only. Delivery and activation stay outside this change.

## Data flow

Exact Git source produces deterministic ZIP bytes and a checksum sidecar.

## API and event contracts

No API or event change.

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

Keep delivery identities null until observed.

## Risks and mitigations

Tests bind hashes, source identity, publication false, and activation false.
