# Architecture — Consolidate repository-owned remaining issue fixes into one bounded batch from current main, preserve external blockers, run one final PR verification and prepare one successor PR

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

## Bounded implementation decision

This candidate changes only repository-owned authority wording and runtime evidence semantics. It does not modify deployed Trust CI policy, external holdouts, provider services, or user-level shell tooling. #39 and #48 remain explicitly external because no matching implementation exists in this tree.
