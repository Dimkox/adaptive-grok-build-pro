# Architecture — Publish unverified transport branch for the assembled 2.1.0 release candidate; no merge tag or release

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The isolated branch contains the 2.1.0 source candidate. No merge, tag, release, deployment, or live qualification has occurred.

## Proposed behavior

Persist local evidence, rerun exact-head verification, then transport the branch and open a PR under the explicit delegated action.

## Components and boundaries

The source candidate owns U0-U3 and U5-U7. U4/macOS is excluded. Optional provider-facing paths are default-off and authority-free.

## Data flow

Local source and tests produce local receipts. A PR head is evaluated by external App-owned Trust CI. Local evidence cannot replace that check.

## API and event contracts

No new external delivery API is created. Existing source contracts and migrations remain authoritative.

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

PR-only delivery. No direct protected-branch push, merge, tag, release, activation, or deployment.

## Risks and mitigations

Stale evidence is mitigated by final verification after evidence persistence. Misleading qualification is mitigated by explicit default-off/unqualified language.
