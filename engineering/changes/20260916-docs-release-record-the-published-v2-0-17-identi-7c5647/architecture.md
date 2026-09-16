# Architecture — v2.0.17 published-release successor

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The tree records v2.0.17 as an unpublished candidate while the tag and Release already exist.

## Proposed behavior

The published release becomes the record of fact: `published_release` v2.0.17, v2.0.16 archived, candidate published, delivery pointers advanced, docs reconciled.

## Components and boundaries

- `PROJECT_STATE.json` release records and `active_delivery`.
- Bootstrap docs (README, START_HERE, ROADMAP, CHANGELOG, HANDOFF) and `packages/README.md`.
- Coupled tests: `test_structure`, `test_project_state`, `test_manifest_package`.
- Untouched: product code, packaging, artifact bytes, `integrated_stack` (historical v2.0.13 M-stack), migrations.

## Data flow

Remote truth (peeled tag, release API, check run, tracked blobs) → this record → docs → tests. Nothing is copied from chat.

## API and event contracts

None.

## Governance context

Canonical governance JSON stays separately reviewed; nothing here is restated as authority.

## Bitrix-specific impact

None (generic repository).

## Decisions

Publish the record rather than re-tagging: the tag target stays the artifact-child merge, and the successor owns the merge identities the child could not self-record.

## Risks and mitigations

- Divergence between the record and the remote: every identifier is re-derivable and four of them are recomputed from tracked bytes by tests.
- Over-claiming operations: `FORBID-001` plus `operational_activation=false` and the dated observation dossier that shows the units still run pre-#93 releases.
