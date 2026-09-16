# Architecture — release-chain convention and inspected causes

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The landing-row convention exists only inside a `record_scope` string in `PROJECT_STATE.json`; `work_inventory` carries three `not inspected or inferred` placeholders although the retained job records name the causes.

## Proposed behavior

The convention is repeated where routed agents look (`START_HERE.md`, in the machine-readable-handoff paragraph), and the three placeholders become observed facts tied to their heads.

## Components and boundaries

`START_HERE.md`, `PROJECT_STATE.json` (`work_inventory` only), `tests/test_project_state.py`. No release, packaging, verification or runtime code.

## Data flow

Retained job records → quoted causes attributed to a specific head → inventory entries → the pins that assert them.

## API and event contracts

None.

## Governance context

Canonical governance JSON stays separately reviewed authority; nothing here changes a rule or digest.

## Bitrix-specific impact

None.

## Decisions

Keep the convention in prose in both places rather than introducing a new machine field: the ledger's own row #81 is a legitimate historical exception, so a hard schema rule would have to encode an exception anyway.

## Risks and mitigations

- Risk: a quoted cause is read as a current gate result. Mitigation: each entry keeps stating that the check is historical and that merge eligibility must be re-derived.
