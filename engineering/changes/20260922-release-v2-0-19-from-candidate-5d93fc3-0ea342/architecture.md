# Architecture — Release v2.0.19 from candidate 5d93fc3

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`v2.0.18` is the newest published release. `main` is observed at `130ce4a42d9f9bbd1b56772d40b19ae530283205`; the candidate source adds the verified `5d93fc3d68869ab26799935adab5fa62be5e2a80` documentation/evidence closure. Release identity, source provenance, package bytes and publication facts are recorded in `PROJECT_STATE.json`.

## Proposed behavior

Use the existing two-stage release chain: release-sync R establishes the `2.0.19` candidate and lockstep records; artifact-child A is built only from the exact merged R tree and adds the ZIP pair. Only A's exact merged commit may receive tag `v2.0.19` and the GitHub Release. A later successor may record publication facts but must not restack the artifact.

## Components and boundaries

- Product identity: `VERSION`, `__version__`, README, changelog, roadmap, bootstrap handoffs and tests.
- Provenance: `PROJECT_STATE.json` and the durable change package.
- Verification/package: `scripts/grok_verify.py`, `scripts/package_stack.py`, Trust CI and the package manifest tests.
- Publication boundary: protected `main`, exact tag target and GitHub Release assets.

## Data flow

`main` base → isolated release-sync branch → exact-head PR check → protected merge → deterministic artifact-child build → exact-head PR check → protected merge → exact tag → GitHub Release with ZIP and sidecar. No path writes to a service or host.

## API and event contracts

No product API or event schema changes. The release contract is the existing `PROJECT_STATE`/package schema and the immutable ZIP/sidecar naming and digest binding.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: release-readiness, exact-SHA Trust CI, PR-only delivery.
- Applicable canonical example IDs/versions: v2.0.18 R/A/SR chain.
- Open or overdue debt IDs: operational pilot/M8/M9 remain unqualified; not release blockers for source publication.
- Expected governance handoff or receipt impact: verification, code/test/security/release receipts bound to final fingerprints.

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

Preserve `v2.0.18` as the rollback release. Separate source identity from artifact-child identity, and never claim an artifact or tag before its exact commit exists.

## Risks and mitigations

- Stale source: bind every action to the exact head and tree, with fresh external checks.
- Nondeterministic package: build twice from one sealed source and compare bytes/digests.
- Metadata drift: keep tests and `PROJECT_STATE` in the same release-sync change.
- Overreach: prohibit deployment and keep production-service state outside the tree.
