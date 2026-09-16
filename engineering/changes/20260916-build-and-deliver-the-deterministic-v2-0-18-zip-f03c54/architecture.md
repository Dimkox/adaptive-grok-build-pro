# Architecture — v2.0.18 artifact child

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`R` made `2.0.18` the candidate and asserted the ZIP pair absent; no tracked bytes exist for it.

## Proposed behavior

The pair becomes tracked content built from a named commit, and `local_candidate` switches to `artifact_bytes_delivered`/`pending_tag_and_release`. Publication, external effect and activation remain unclaimed, and the child records nothing about its own merge.

## Components and boundaries

- `scripts/package_stack.py` builds from filtered git `HEAD` with canonical modes, no-follow descriptors and atomic publication; unchanged here.
- `packages/` becomes the only artifact-bearing path; `dist/` stays ignored scratch.
- `PROJECT_STATE.json` `local_candidate` plus the coupled test literals.
- Untouched: identity files, `published_release`, `prior_published_releases`, milestones, migrations, packaging code.

## Data flow

Merged `R` commit → two independent clones → identical ZIP → sidecar → tracked pair → `local_candidate` digests → later tag and Release assets.

## API and event contracts

None; the typed `contracts` block is empty by design.

## Governance context

Canonical governance JSON stays separately reviewed; no rule or digest is restated as authority here.

## Bitrix-specific impact

None (generic repository).

## Decisions

Build from clones rather than the live worktree so the archive is reproducible by a third party from `fc8d9e6…` alone.

## Risks and mitigations

- Non-reproducible bytes → dual-build digest equality gate.
- Early publication claim → `AC-003` and `FORBID-001` are test-pinned, and `SR` is the only commit allowed to set them.
- Local verifier red on the large binary → disclosed (issues #80/#101 (streaming analysis; the tracked pair now passes the local verifier)), with the external check as authority.
