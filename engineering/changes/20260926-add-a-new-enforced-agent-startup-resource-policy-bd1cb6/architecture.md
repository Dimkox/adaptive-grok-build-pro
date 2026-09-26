# Architecture — Add a new enforced agent-startup resource policy and structure contract: parallelize all independent route-permitted work, expose 12 worker slots plus controller, launch eligible CPU-heavy child processes across all verified 28 logical CPUs, keep one writer per isolated contour, and label operator-delegated pre-verification branch pushes as unverified in AGENTS.md README.md START_HERE.md and focused structure coverage

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Main 33a4d3ec already contains the closed docs/state verification selector; the existing branch documents measured startup resources but does not yet require invoking that selector as startup step two.

## Proposed behavior

Documentation-only ordering: measure capacity, inspect routes/dependencies and dispatch eligible isolated work, then invoke the existing standard PR verifier before heavy verification. Selection remains owned by the merged executable code, which this change does not edit.

## Components and boundaries

## Data flow

## API and event contracts

No API/event/schema/producer/consumer change. The api route domain is inherited repository classification, not an added interface requirement. External Trust CI and approvals remain outside local evidence authority.

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

Risk: an agent may generalize historical timing or component evidence into a manual skip. Mitigation: all three entry documents explicitly defer to the closed fail-closed selector and preserve historical identities and exact-head merge gates.
