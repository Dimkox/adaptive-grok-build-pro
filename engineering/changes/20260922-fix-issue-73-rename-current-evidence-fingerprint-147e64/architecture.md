# Architecture — Fix issue #73: rename current evidence fingerprint fields that trigger GitGuardian secret heuristics while preserving historical evidence immutability and schema/test compatibility.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Two immutable historical evidence artifacts contain the flagged key name. Current local delegated
grants serialize an `authorization` marker and a 64-hex `grant_binding_digest` in the same
envelope. GitGuardian's detector and allow-list remain external merge-environment behavior.

## Proposed behavior

`add_approval` writes `grant_binding_digest`. `has_valid_approval` and the landing publication
authority read either that current name or the legacy `tree_fingerprint` name, but reject a record
containing both. The digest's meaning and all repository/route/change/HEAD binding checks are
unchanged; no stored record is migrated in place.

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

- Historical artifacts are immutable evidence and are not edited.
- Receipt and verification `tree_fingerprint` contracts are outside this targeted grant change.
- Never treat local evidence or a GitGuardian-looking string as a security approval.

## Risks and mitigations
